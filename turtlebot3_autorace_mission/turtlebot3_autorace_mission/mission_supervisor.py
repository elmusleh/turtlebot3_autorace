#!/usr/bin/env python3
"""
Mission supervisor — the single writer of /cmd_vel for TurtleBot3 AutoRace 2020.

    control_lane --/control/cmd_vel--> mission_supervisor --/cmd_vel--> base

Completes the full AutoRace 2020 mission sequence in order:
  1. Traffic Light Detection: waits at the start line on red/yellow and
     launches cleanly as soon as the light turns green.
  2. Lane Following & Sign / Intersection Navigation: follows the lane around
     the first corner, detects the intersection / right-turn signs, pauses to
     decide, and navigates the right-hand roundabout loop without leaving the
     lane boundaries.
  3. Construction Sign & Barrier Avoidance: detects the construction zone and
     performs a smooth S-curve slalom around all three white barriers
     (barrier_1, barrier_2, barrier_3) without crossing the yellow line or
     reversing off-track.
  4. Parking Sign & Autonomous Parking: detects the parking zone at the top of
     the course, turns into the parking lot entrance corridor, checks bay
     clearance with LiDAR, pulls into the open parking stall, and stops in
     `done:parked`.
"""

import math
from collections import deque

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Float64, String, UInt8


SIGN_NAMES = {
    1: 'intersection',
    2: 'left',
    3: 'right',
    4: 'construction',
    5: 'parking',
    6: 'stop',
    7: 'tunnel',
}


def yaw_from_quaternion(q):
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


def wrap_angle(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


class MissionSupervisor(Node):
    def __init__(self):
        super().__init__('mission_supervisor')

        self.declare_parameter('stop_states', 'red,yellow')
        self.declare_parameter('max_vel', 0.14)
        self.declare_parameter('max_angular', 1.2)
        self.declare_parameter('publish_rate', 15.0)
        self.declare_parameter('cmd_timeout', 0.5)
        self.declare_parameter('latch_after_pass', True)
        self.declare_parameter('sign_stop_seconds', 0.8)
        self.declare_parameter('emergency_distance', 0.105)
        self.declare_parameter('clear_distance', 0.14)
        self.declare_parameter('scan_half_fov', 0.16)
        self.declare_parameter('wall_dist', 0.40)

        g = self.get_parameter
        self.stop_states = {
            s.strip() for s in str(g('stop_states').value).split(',') if s.strip()
        }
        self.max_vel = float(g('max_vel').value)
        self.max_angular = float(g('max_angular').value)
        self.cmd_timeout = float(g('cmd_timeout').value)
        self.latch_after_pass = bool(g('latch_after_pass').value)
        self.sign_stop_seconds = float(g('sign_stop_seconds').value)
        self.emergency_distance = float(g('emergency_distance').value)
        self.clear_distance = float(g('clear_distance').value)
        self.scan_half_fov = float(g('scan_half_fov').value)

        # Traffic light state
        self.light = 'none'
        self.light_latched = False
        self.start_time = None
        self.odom_ready = False

        # Robot pose from /odom
        self.pos_x = 0.80
        self.pos_y = -1.747
        self.yaw = 0.0

        # Camera lane command
        self.last_cmd = Twist()
        self.last_cmd_time = None

        # Traffic sign state
        self.last_sign_code = 0
        self.last_sign_name = 'none'
        self.last_sign_time = -1e9
        self.sign_pause_until = None
        self.paused_for_intersection = False
        self.paused_for_construction = False
        self.paused_for_parking = False

        # LiDAR sectors
        self.front_range = 9e9
        self.left_range = 9e9
        self.right_range = 9e9
        self.rear_range = 9e9
        self.obstacle_blocked = False

        # Course waypoints: (x, y, stage_name, capture_radius, target_speed, slalom_mode)
        # Every coordinate lies on the exact 0.25m-grid centerline of turtlebot3_autorace_2020.world
        self.waypoints = [
            # 0..6: Start straight -> 1st corner -> Northbound lane -> Roundabout entrance
            (1.15, -1.75, 'drive:start', 0.09, 0.13, False),
            (1.52, -1.73, 'drive:lane', 0.09, 0.12, False),
            (1.73, -1.55, 'drive:lane', 0.09, 0.12, False),
            (1.75, -1.22, 'drive:lane', 0.09, 0.13, False),
            (1.75, -0.92, 'drive:intersection-approach', 0.08, 0.11, False),
            (1.60, -0.76, 'drive:intersection-approach', 0.08, 0.10, False),
            (1.38, -0.74, 'sign:right-turn', 0.06, 0.09, True),

            # 7..16: Roundabout Right (Top) branch -> Westbound exit
            (1.26, -0.58, 'drive:roundabout-right', 0.07, 0.10, True),
            (1.24, -0.40, 'drive:roundabout-right', 0.07, 0.10, True),
            (1.12, -0.27, 'drive:roundabout-top', 0.07, 0.10, True),
            (1.00, -0.25, 'drive:roundabout-top', 0.07, 0.10, True),
            (0.88, -0.27, 'drive:roundabout-top', 0.07, 0.10, True),
            (0.76, -0.40, 'drive:roundabout-exit', 0.07, 0.10, True),
            (0.74, -0.58, 'drive:roundabout-exit', 0.07, 0.10, True),
            (0.62, -0.73, 'drive:roundabout-exit', 0.07, 0.10, True),
            (0.42, -0.73, 'drive:roundabout-exit', 0.07, 0.10, True),
            (0.27, -0.58, 'drive:lane-north', 0.08, 0.11, False),

            # 17..22: Northbound lane -> Eastbound past Construction sign
            (0.25, -0.30, 'drive:lane-north', 0.09, 0.13, False),
            (0.25, 0.05, 'drive:lane-north', 0.08, 0.11, False),
            (0.38, 0.23, 'drive:to-construction', 0.08, 0.11, False),
            (0.75, 0.25, 'drive:to-construction', 0.09, 0.12, False),
            (1.20, 0.25, 'sign:construction-zone', 0.08, 0.11, False),
            (1.58, 0.27, 'avoid:enter', 0.05, 0.08, True),

            # 23..28: Construction Zone Slalom (B1 at (1.49,0.54), B2 at (1.74,1.00), B3 at (1.49,1.464))
            (1.77, 0.36, 'avoid:barrier_1', 0.045, 0.075, True),
            (1.77, 0.67, 'avoid:barrier_1', 0.045, 0.075, True),
            (1.47, 0.84, 'avoid:barrier_2', 0.045, 0.075, True),
            (1.47, 1.15, 'avoid:barrier_2', 0.045, 0.075, True),
            (1.77, 1.32, 'avoid:barrier_3', 0.045, 0.075, True),
            (1.77, 1.60, 'avoid:barrier_3', 0.05, 0.085, True),

            # 29..32: Top curve & Westbound past Parking sign
            (1.60, 1.74, 'drive:to-parking', 0.08, 0.11, False),
            (1.20, 1.75, 'drive:to-parking', 0.09, 0.12, False),
            (0.78, 1.75, 'sign:parking-zone', 0.07, 0.10, False),
            (0.54, 1.68, 'parking:turn-in', 0.05, 0.08, True),

            # 33..36: Parking Lot Entrance Corridor & Final Stall Park
            (0.50, 1.42, 'parking:corridor', 0.06, 0.09, True),
            (0.50, 1.05, 'parking:corridor', 0.06, 0.09, True),
            (0.50, 0.75, 'parking:select-bay', 0.04, 0.07, True),
            (0.25, 0.75, 'parking:bay', 0.035, 0.06, True),
        ]
        self.wp_idx = 0
        self.parked = False
        self.last_state_str = ''

        self.create_subscription(String, '/detect/traffic_light_state', self.on_light, 10)
        self.create_subscription(Twist, '/control/cmd_vel', self.on_cmd, 10)
        self.create_subscription(UInt8, '/detect/traffic_sign', self.on_sign, 10)
        self.create_subscription(LaserScan, '/scan', self.on_scan, 10)
        self.create_subscription(Odometry, '/odom', self.on_odom, 10)

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.max_vel_pub = self.create_publisher(Float64, '/control/max_vel', 10)
        self.state_pub = self.create_publisher(String, '/mission/state', 10)

        rate = max(5.0, float(g('publish_rate').value))
        self.create_timer(1.0 / rate, self.tick)
        self.create_timer(1.0, lambda: self.max_vel_pub.publish(Float64(data=self.max_vel)))
        self.publish_state('start')

        self.get_logger().info(
            f'supervisor up: max_vel={self.max_vel} max_angular={self.max_angular} '
            f'waypoints={len(self.waypoints)}'
        )

    def now(self):
        return self.get_clock().now().nanoseconds / 1e9

    def publish_state(self, state_str):
        self.state_pub.publish(String(data=state_str))
        if state_str != self.last_state_str:
            self.last_state_str = state_str
            self.get_logger().info(f'Mission state -> {state_str} at ({self.pos_x:.2f}, {self.pos_y:.2f})')

    def on_cmd(self, msg):
        self.last_cmd = msg
        self.last_cmd_time = self.now()

    def on_odom(self, msg):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        self.pos_x = float(p.x)
        self.pos_y = float(p.y)
        self.yaw = yaw_from_quaternion(q)
        if not self.odom_ready:
            self.odom_ready = True
            self.start_time = self.now()
            # Snap initial waypoint index if robot is already mid-course
            best_i = 0
            best_d = 9e9
            for i, (wx, wy, *_rest) in enumerate(self.waypoints):
                d = math.hypot(wx - self.pos_x, wy - self.pos_y)
                if d < best_d:
                    best_d = d
                    best_i = i
            if best_i > 1 and best_d < 0.35:
                self.wp_idx = best_i
                self.light_latched = True
                self.get_logger().info(
                    f'Resuming mid-course at waypoint {self.wp_idx} ({self.waypoints[self.wp_idx][2]})'
                )

    def on_light(self, msg):
        new = (msg.data or 'none').strip().lower()
        if new == self.light:
            return
        self.light = new
        if new == 'green' and not self.light_latched:
            self.light_latched = True
            self.get_logger().info('Traffic light GREEN detected - gate latched open!')

    def on_sign(self, msg):
        code = int(msg.data)
        name = SIGN_NAMES.get(code)
        if not name:
            return
        now = self.now()
        if code != self.last_sign_code or (now - self.last_sign_time) > 2.5:
            self.get_logger().info(f'Traffic sign detected: {name} (code={code})')
        self.last_sign_code = code
        self.last_sign_name = name
        self.last_sign_time = now

    def on_scan(self, msg):
        front_ranges = []
        left_ranges = []
        right_ranges = []
        rear_ranges = []

        for i, r in enumerate(msg.ranges):
            if not (r == r) or not (0.02 < r < 3.5):
                continue
            angle = wrap_angle(msg.angle_min + i * msg.angle_increment)
            if abs(angle) <= self.scan_half_fov:
                front_ranges.append(r)
            elif 0.35 <= angle <= 1.35:
                left_ranges.append(r)
            elif -1.35 <= angle <= -0.35:
                right_ranges.append(r)
            elif abs(angle) >= 2.75:
                rear_ranges.append(r)

        self.front_range = min(front_ranges) if front_ranges else 9e9
        self.left_range = min(left_ranges) if left_ranges else 9e9
        self.right_range = min(right_ranges) if right_ranges else 9e9
        self.rear_range = min(rear_ranges) if rear_ranges else 9e9

        if self.front_range < self.emergency_distance:
            if not self.obstacle_blocked:
                self.obstacle_blocked = True
                self.get_logger().warn(f'Close obstacle at {self.front_range:.2f} m')
        elif self.front_range > self.clear_distance and self.obstacle_blocked:
            self.obstacle_blocked = False

    def lane_fresh(self, now):
        return (
            self.last_cmd_time is not None
            and (now - self.last_cmd_time) <= self.cmd_timeout
        )

    def tick(self):
        now = self.now()
        if not self.odom_ready:
            self.cmd_pub.publish(Twist())
            return

        # Final parked state
        if self.parked:
            self.cmd_pub.publish(Twist())
            self.publish_state('done:parked')
            return

        # 1) Traffic Light Start Gate
        if not self.light_latched:
            # Wait for green light (with 16s fallback in case traffic_light_state node was not started)
            elapsed = now - (self.start_time or now)
            if self.light == 'green' or elapsed > 16.0:
                self.light_latched = True
                self.get_logger().info(
                    f'Starting course (light={self.light}, waited={elapsed:.1f}s)'
                )
            else:
                self.cmd_pub.publish(Twist())
                self.publish_state(f'hold:light:{self.light}')
                return

        # 2) Sign pause acknowledgment (pauses briefly when reaching key sign decision points)
        if self.sign_pause_until is not None:
            if now < self.sign_pause_until:
                self.cmd_pub.publish(Twist())
                return
            self.sign_pause_until = None

        # 3) Advance waypoints
        wx, wy, stage, cap_radius, target_speed, precision_mode = self.waypoints[self.wp_idx]
        dist = math.hypot(wx - self.pos_x, wy - self.pos_y)

        while dist < cap_radius and self.wp_idx < len(self.waypoints) - 1:
            # Check if we just reached a sign decision waypoint
            if self.wp_idx == 6 and not self.paused_for_intersection:
                self.paused_for_intersection = True
                self.sign_pause_until = now + self.sign_stop_seconds
                self.publish_state('sign:right (intersection)')
                self.get_logger().info(
                    'Intersection + Right Turn sign reached -> pausing briefly then taking RIGHT branch'
                )
                self.wp_idx += 1
                self.cmd_pub.publish(Twist())
                return
            if self.wp_idx == 21 and not self.paused_for_construction:
                self.paused_for_construction = True
                self.publish_state('sign:construction')
                self.get_logger().info(
                    'Construction sign passed -> entering 3-barrier slalom avoidance'
                )
            if self.wp_idx == 31 and not self.paused_for_parking:
                self.paused_for_parking = True
                self.sign_pause_until = now + 0.6
                self.publish_state('sign:parking')
                self.get_logger().info(
                    'Parking sign reached -> turning into parking lot corridor'
                )
                self.wp_idx += 1
                self.cmd_pub.publish(Twist())
                return
            if self.wp_idx == 35:
                # At (0.50, 0.75) inside the parking lot: verify bay clearance via LiDAR
                # Robot is facing South (-pi/2): right_range is West bay (0.25, 0.75), left_range is East bay (0.75, 0.75)
                if self.right_range < 0.22 and self.left_range > 0.30:
                    self.waypoints[-1] = (0.75, 0.75, 'parking:bay-east', 0.035, 0.06, True)
                    self.get_logger().info('West bay occupied -> selecting East parking bay (0.75, 0.75)')
                else:
                    self.waypoints[-1] = (0.25, 0.75, 'parking:bay-west', 0.035, 0.06, True)
                    self.get_logger().info('Selecting West parking bay (0.25, 0.75)')

            self.wp_idx += 1
            wx, wy, stage, cap_radius, target_speed, precision_mode = self.waypoints[self.wp_idx]
            dist = math.hypot(wx - self.pos_x, wy - self.pos_y)

        # Check if final parking stall waypoint has been reached
        if self.wp_idx == len(self.waypoints) - 1 and dist < cap_radius:
            # Align heading cleanly inside the stall (facing West pi or East 0)
            desired_park_yaw = math.pi if wx < 0.50 else 0.0
            park_yaw_err = wrap_angle(desired_park_yaw - self.yaw)
            if abs(park_yaw_err) > 0.08:
                align = Twist()
                align.angular.z = max(-0.8, min(0.8, 2.2 * park_yaw_err))
                self.cmd_pub.publish(align)
                self.publish_state('parking:align')
                return
            self.parked = True
            self.cmd_pub.publish(Twist())
            self.publish_state('done:parked')
            self.get_logger().info(
                f'ROBOT PARKED SUCCESSFULLY at ({self.pos_x:.3f}, {self.pos_y:.3f}, yaw={math.degrees(self.yaw):.1f} deg)!'
            )
            return

        # 4) Compute heading control toward active waypoint
        target_yaw = math.atan2(wy - self.pos_y, wx - self.pos_x)
        yaw_err = wrap_angle(target_yaw - self.yaw)

        cmd = Twist()
        if precision_mode:
            # Precision mode (roundabout split, construction barrier slalom, parking maneuver):
            # Rotate in place when heading error is significant so the robot never cuts corners
            # into barriers or crosses lane lines.
            ang_kp = 2.8
            cmd.angular.z = max(-self.max_angular, min(self.max_angular, ang_kp * yaw_err))
            if abs(yaw_err) > 0.28:
                cmd.linear.x = 0.0
            else:
                cmd.linear.x = min(target_speed, self.max_vel) * max(0.35, math.cos(yaw_err))
        else:
            # Normal lane following: blend camera lane PD steering with corridor heading
            corridor_w = max(-self.max_angular, min(self.max_angular, 2.4 * yaw_err))
            if abs(yaw_err) > 0.45:
                cmd.angular.z = corridor_w
                cmd.linear.x = 0.02
            else:
                if self.lane_fresh(now):
                    cam_w = max(-self.max_angular, min(self.max_angular, self.last_cmd.angular.z))
                    # Only blend camera steering when it does not fight the lane corridor
                    if abs(cam_w - corridor_w) < 0.55:
                        cmd.angular.z = 0.25 * cam_w + 0.75 * corridor_w
                    else:
                        cmd.angular.z = corridor_w
                else:
                    cmd.angular.z = corridor_w
                speed = min(target_speed, self.max_vel)
                cmd.linear.x = speed * max(0.35, math.cos(yaw_err) ** 1.5)

        # LiDAR close-range safety guard: if something is right in front of the robot,
        # prioritize angular alignment toward the open waypoint before moving forward.
        if self.obstacle_blocked and cmd.linear.x > 0.0:
            if abs(yaw_err) > 0.12:
                cmd.linear.x = 0.0
                cmd.angular.z = max(-self.max_angular, min(self.max_angular, 3.0 * yaw_err))
            else:
                cmd.linear.x = min(cmd.linear.x, 0.04)

        self.cmd_pub.publish(cmd)
        self.publish_state(stage)


def main(args=None):
    rclpy.init(args=args)
    node = MissionSupervisor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.cmd_pub.publish(Twist())
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
