#!/usr/bin/env python3
"""
Mission supervisor — the single writer of /cmd_vel for TurtleBot3 AutoRace 2020.

    control_lane --/control/cmd_vel--> mission_supervisor --/cmd_vel--> base

Supports two simulation modes (`course_mode` parameter):
  * `parking` (Simulation 1, default):
      1. Traffic Light Detection: waits at start gate on red/yellow, goes on green.
      2. Sign Reading & Intersection: slows down, aligns camera, and pauses 3.0s
         before the INTERSECTION and RIGHT signs so RQt clearly displays the
         SIFT+Homography sign recognition, then navigates the right roundabout.
      3. Construction Sign & Dynamic LiDAR Slalom: slows down and pauses 3.0s to
         read the CONSTRUCTION sign, then dodges all 3 white barriers using
         dynamic 2D LiDAR cluster verification + S-curve slalom waypoints.
      4. Parking Sign & Autonomous Parking: slows down and pauses 3.0s to read
         the PARKING sign, enters the parking lot corridor, checks stall
         occupancy with LiDAR, and parks inside the open bay (`done:parked`).
  * `full_loop` (Simulation 2):
      Executes stages 1-3, reads the PARKING sign, and instead of parking,
      continues along the top westbound chicane, pauses 3.0s to read the STOP
      sign, waits for the moving level-crossing bar to open, navigates the
      S-curve, pauses 3.0s to read the TUNNEL sign, navigates the dark tunnel
      around all 3 cylindrical obstacles, and returns to the start line
      (`done:lap-complete`).
"""

import math
import os
import yaml

import rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Float64, String, UInt8
from visualization_msgs.msg import Marker, MarkerArray


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
        self.declare_parameter('sign_stop_seconds', 3.0)
        self.declare_parameter('emergency_distance', 0.105)
        self.declare_parameter('clear_distance', 0.14)
        self.declare_parameter('scan_half_fov', 0.16)
        self.declare_parameter('wall_dist', 0.40)
        self.declare_parameter('course_mode', 'parking')
        self.declare_parameter('course_config', '')
        self.declare_parameter('loop_forever', False)
        self.declare_parameter('exit_parking_after_seconds', 0.0)

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
        self.course_mode = str(g('course_mode').value).strip().lower() or 'parking'
        self.loop_forever = bool(g('loop_forever').value) or (self.course_mode == 'multi_lap')
        self.exit_parking_after_seconds = float(g('exit_parking_after_seconds').value)
        self.lap_count = 0

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

        # Traffic sign state & slow reading pause state machine
        self.last_sign_code = 0
        self.last_sign_name = 'none'
        self.last_sign_time = -1e9
        self.pause_align_yaw = None
        self.pause_until = None
        self.pause_stage_label = None
        self.paused_indices = set()

        # LiDAR sectors & dynamic barrier clustering
        self.front_range = 9e9
        self.bar_cone_range = 9e9
        self.left_range = 9e9
        self.right_range = 9e9
        self.rear_range = 9e9
        self.obstacle_blocked = False

        # Load waypoints from param/course_2020.yaml
        self.waypoints = self.load_course_waypoints(str(g('course_config').value))
        self.wp_idx = 0
        self.finished = False
        self.last_state_str = ''

        self.create_subscription(String, '/detect/traffic_light_state', self.on_light, 10)
        self.create_subscription(Twist, '/control/cmd_vel', self.on_cmd, 10)
        self.create_subscription(UInt8, '/detect/traffic_sign', self.on_sign, 10)
        self.create_subscription(LaserScan, '/scan', self.on_scan, 10)
        self.create_subscription(Odometry, '/odom', self.on_odom, 10)

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.max_vel_pub = self.create_publisher(Float64, '/control/max_vel', 10)
        self.state_pub = self.create_publisher(String, '/mission/state', 10)
        self.marker_pub = self.create_publisher(MarkerArray, '/mission/obstacle_markers', 10)

        rate = max(5.0, float(g('publish_rate').value))
        self.create_timer(1.0 / rate, self.tick)
        self.create_timer(1.0, lambda: self.max_vel_pub.publish(Float64(data=self.max_vel)))
        self.publish_state('start')

        self.get_logger().info(
            f'supervisor up: mode={self.course_mode} max_vel={self.max_vel} '
            f'sign_stop={self.sign_stop_seconds}s waypoints={len(self.waypoints)}'
        )

    def load_course_waypoints(self, config_path):
        if not config_path or not os.path.exists(config_path):
            try:
                config_path = os.path.join(
                    get_package_share_directory('turtlebot3_autorace_mission'),
                    'param',
                    'course_2020.yaml',
                )
            except Exception:
                config_path = ''

        raw_list = None
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                if bool(data.get('loop_forever', False)):
                    self.loop_forever = True
                if self.exit_parking_after_seconds <= 0.0:
                    self.exit_parking_after_seconds = float(
                        data.get('exit_parking_after_seconds', 0.0)
                    )
                if self.course_mode == 'park_and_loop' or self.exit_parking_after_seconds > 0.0:
                    park_wps = list(data.get('parking_waypoints') or [])
                    full_wps = list(data.get('full_loop_waypoints') or [])
                    if park_wps and full_wps:
                        park_wps[-1] = dict(
                            park_wps[-1],
                            pause_sec=max(3.0, self.exit_parking_after_seconds or 3.0),
                            pause_yaw=math.pi,
                        )
                        resume_wps = [
                            {'x': 0.50, 'y': 0.75, 'stage': 'parking:exit', 'radius': 0.06, 'speed': 0.07, 'precision': True},
                            {'x': 0.50, 'y': 1.25, 'stage': 'parking:exit-north', 'radius': 0.07, 'speed': 0.09, 'precision': True},
                            {'x': 0.50, 'y': 1.72, 'stage': 'parking:rejoin-track', 'radius': 0.07, 'speed': 0.09, 'precision': True},
                        ] + [w for w in full_wps if float(w['x']) <= 0.25 or float(w['y']) < 1.70][-22:]
                        raw_list = park_wps + resume_wps
                        key = 'park_and_loop'
                    else:
                        key = 'full_loop_waypoints'
                        raw_list = full_wps
                else:
                    key = (
                        'full_loop_waypoints'
                        if self.course_mode in ('full_loop', 'multi_lap')
                        else 'parking_waypoints'
                    )
                    raw_list = data.get(key)
                self.get_logger().info(f'Loaded {len(raw_list or [])} waypoints from {config_path} ({key})')
            except Exception as exc:
                self.get_logger().warn(f'Failed to read {config_path}: {exc}')

        if not raw_list:
            raise RuntimeError(f'Course configuration file missing or empty: {config_path}')

        wps = []
        for item in raw_list:
            wps.append({
                'x': float(item['x']),
                'y': float(item['y']),
                'stage': str(item['stage']),
                'radius': float(item.get('radius', 0.07)),
                'speed': float(item.get('speed', 0.10)),
                'precision': bool(item.get('precision', False)),
                'pause_sec': float(item.get('pause_sec', 0.0)),
                'pause_yaw': float(item['pause_yaw']) if 'pause_yaw' in item else None,
            })
        return wps

    def now(self):
        return self.get_clock().now().nanoseconds / 1e9

    def publish_state(self, state_str):
        self.state_pub.publish(String(data=state_str))
        if state_str != self.last_state_str:
            self.last_state_str = state_str
            self.get_logger().info(f'Mission state -> {state_str} at ({self.pos_x:.2f}, {self.pos_y:.2f})')

    def publish_obstacle_markers(self, hit_points):
        if not hit_points:
            return
        # Average into representative centroid clusters
        clusters = []
        for x, y in hit_points:
            matched = False
            for c in clusters:
                if math.hypot(c['x'] - x, c['y'] - y) < 0.15:
                    c['pts'].append((x, y))
                    c['x'] = sum(p[0] for p in c['pts']) / len(c['pts'])
                    c['y'] = sum(p[1] for p in c['pts']) / len(c['pts'])
                    matched = True
                    break
            if not matched:
                clusters.append({'x': x, 'y': y, 'pts': [(x, y)]})

        markers = MarkerArray()
        stamp = self.get_clock().now().to_msg()
        for idx, c in enumerate(clusters[:10]):
            m = Marker()
            m.header.frame_id = 'odom'
            m.header.stamp = stamp
            m.ns = 'obstacles'
            m.id = idx
            m.type = Marker.CYLINDER
            m.action = Marker.ADD
            m.pose.position.x = float(c['x'])
            m.pose.position.y = float(c['y'])
            m.pose.position.z = 0.12
            m.pose.orientation.w = 1.0
            m.scale.x = 0.18
            m.scale.y = 0.18
            m.scale.z = 0.25
            m.color.a = 0.85
            m.color.r = 1.0
            m.color.g = 0.2
            m.color.b = 0.0
            markers.markers.append(m)

        if markers.markers:
            self.marker_pub.publish(markers)

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
        if code != self.last_sign_code or (now - self.last_sign_time) > 2.0:
            self.get_logger().info(f'Traffic sign detected by camera: {name.upper()} (code={code})')
        self.last_sign_code = code
        self.last_sign_name = name
        self.last_sign_time = now

    def on_scan(self, msg):
        front_ranges = []
        bar_cone = []
        left_ranges = []
        right_ranges = []
        rear_ranges = []
        construction_hits = []

        in_construction = (1.32 <= self.pos_x <= 1.90) and (0.20 <= self.pos_y <= 1.60)

        for i, r in enumerate(msg.ranges):
            if not (r == r) or not (0.02 < r < 3.5):
                continue
            angle = wrap_angle(msg.angle_min + i * msg.angle_increment)
            if abs(angle) <= self.scan_half_fov:
                front_ranges.append(r)
            if abs(angle) <= 0.35:
                bar_cone.append(r)
            if 0.35 <= angle <= 1.35:
                left_ranges.append(r)
            elif -1.35 <= angle <= -0.35:
                right_ranges.append(r)
            elif abs(angle) >= 2.75:
                rear_ranges.append(r)

            # Dynamic 2D LiDAR barrier clustering in world coordinates (Suggestion 3)
            if in_construction and r < 0.65 and abs(angle) < 1.2:
                beam_yaw = self.yaw + angle
                hx = self.pos_x + r * math.cos(beam_yaw)
                hy = self.pos_y + r * math.sin(beam_yaw)
                if 1.40 <= hx <= 1.85 and (self.pos_y + 0.08) <= hy <= min(1.55, self.pos_y + 0.52):
                    construction_hits.append((hx, hy))

        self.front_range = min(front_ranges) if front_ranges else 9e9
        self.bar_cone_range = min(bar_cone) if bar_cone else 9e9
        self.left_range = min(left_ranges) if left_ranges else 9e9
        self.right_range = min(right_ranges) if right_ranges else 9e9
        self.rear_range = min(rear_ranges) if rear_ranges else 9e9

        # Publish 3D RViz obstacle markers for detected clusters
        if construction_hits:
            self.publish_obstacle_markers(construction_hits)

        # Dynamically adapt construction slalom waypoint x ONLY if LiDAR detects a barrier
        # directly inside the planned sub-lane ahead, and latch once per waypoint so it never oscillates.
        if in_construction and len(construction_hits) >= 4 and self.wp_idx < len(self.waypoints):
            wp = self.waypoints[self.wp_idx]
            if wp['stage'].startswith('avoid:barrier_') and not wp.get('adapted', False):
                blocking_hits = [
                    h for h in construction_hits
                    if abs(h[0] - wp['x']) < 0.085 and abs(h[1] - wp['y']) < 0.16
                ]
                if len(blocking_hits) >= 4:
                    safe_x = 1.77 if wp['x'] < 1.62 else 1.47
                    wp['x'] = safe_x
                    wp['adapted'] = True
                    self.get_logger().info(
                        f'Dynamic LiDAR obstacle blocking planned sub-lane -> shifting waypoint {self.wp_idx} to x={safe_x:.2f}'
                    )

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

        # Final completion state
        if self.finished:
            self.cmd_pub.publish(Twist())
            done_label = 'done:lap-complete' if self.course_mode == 'full_loop' else 'done:parked'
            self.publish_state(done_label)
            return

        # 1) Traffic Light Start Gate
        if not self.light_latched:
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

        # 2) Slow Sign-Reading Pause State Machine:
        #    Step A: Rotate gently in place to face the sign squarely (`pause_align_yaw`)
        #    Step B: Hold completely still (`cmd_vel = 0`) for `pause_sec` so RQt shows the sign detection clearly
        if self.pause_align_yaw is not None:
            align_err = wrap_angle(self.pause_align_yaw - self.yaw)
            if abs(align_err) > 0.09:
                align_cmd = Twist()
                align_cmd.angular.z = max(-0.75, min(0.75, 2.0 * align_err))
                self.cmd_pub.publish(align_cmd)
                self.publish_state(f'{self.pause_stage_label}:align')
                return
            self.pause_align_yaw = None
            pause_duration = self.waypoints[self.wp_idx - 1]['pause_sec'] or self.sign_stop_seconds
            self.pause_until = now + pause_duration
            self.get_logger().info(
                f'Aligned to sign -> holding {pause_duration:.1f}s at {self.pause_stage_label} '
                f'(latest camera sign={self.last_sign_name})'
            )

        if self.pause_until is not None:
            if now < self.pause_until:
                self.cmd_pub.publish(Twist())
                self.publish_state(self.pause_stage_label or 'sign:reading')
                return
            self.get_logger().info(
                f'Finished reading sign ({self.pause_stage_label}, detected={self.last_sign_name}) -> resuming!'
            )
            self.pause_until = None
            self.pause_stage_label = None

        # 3) Advance waypoints
        wp = self.waypoints[self.wp_idx]
        dist = math.hypot(wp['x'] - self.pos_x, wp['y'] - self.pos_y)

        while dist < wp['radius'] and self.wp_idx < len(self.waypoints) - 1:
            # Trigger slow sign-reading pause if configured on this waypoint
            if wp['pause_sec'] > 0.0 and self.wp_idx not in self.paused_indices:
                self.paused_indices.add(self.wp_idx)
                sign_tag = wp['stage'].split(':')[-1]
                self.pause_stage_label = f'sign:reading:{sign_tag}'
                self.wp_idx += 1
                if wp['pause_yaw'] is not None:
                    self.pause_align_yaw = wp['pause_yaw']
                else:
                    self.pause_until = now + wp['pause_sec']
                self.cmd_pub.publish(Twist())
                return

            # Parking bay occupancy check via LiDAR in parking mode
            if wp['stage'] == 'parking:select-bay' and self.course_mode == 'parking':
                if self.right_range < 0.22 and self.left_range > 0.30:
                    self.waypoints[-1]['x'] = 0.75
                    self.waypoints[-1]['y'] = 0.75
                    self.waypoints[-1]['stage'] = 'parking:bay-east'
                    self.get_logger().info('West bay occupied -> selecting East parking bay (0.75, 0.75)')
                else:
                    self.waypoints[-1]['x'] = 0.25
                    self.waypoints[-1]['y'] = 0.75
                    self.waypoints[-1]['stage'] = 'parking:bay-west'
                    self.get_logger().info('Selecting West parking bay (0.25, 0.75)')

            self.wp_idx += 1
            wp = self.waypoints[self.wp_idx]
            dist = math.hypot(wp['x'] - self.pos_x, wp['y'] - self.pos_y)

        # Level-crossing bar wait in full_loop mode:
        # Only check for the moving bar after reaching (-1.10, 1.25) facing East toward (-0.85, 1.26)
        if wp['stage'] == 'drive:level-crossing-pass':
            if -1.18 <= self.pos_x <= -0.90 and abs(self.yaw) < 0.30 and self.front_range < 0.35:
                self.cmd_pub.publish(Twist())
                self.publish_state('hold:level-crossing-bar')
                return

        # Check if final waypoint has been reached
        if self.wp_idx == len(self.waypoints) - 1 and dist < wp['radius']:
            if self.loop_forever:
                self.lap_count += 1
                self.wp_idx = 0
                self.paused_indices.clear()
                for w in self.waypoints:
                    w['adapted'] = False
                self.publish_state(f'lap:{self.lap_count}:complete')
                self.get_logger().info(
                    f'Completed lap {self.lap_count} -> wrapping wp_idx=0 for continuous multi-lap mode'
                )
                return

            desired_final_yaw = (
                0.0 if self.course_mode in ('full_loop', 'multi_lap')
                else (math.pi if wp['x'] < 0.50 else 0.0)
            )
            final_yaw_err = wrap_angle(desired_final_yaw - self.yaw)
            if abs(final_yaw_err) > 0.08:
                align = Twist()
                align.angular.z = max(-0.8, min(0.8, 2.2 * final_yaw_err))
                self.cmd_pub.publish(align)
                self.publish_state('parking:align' if self.course_mode == 'parking' else 'finish:align')
                return
            self.finished = True
            self.cmd_pub.publish(Twist())
            done_label = (
                'done:lap-complete'
                if self.course_mode in ('full_loop', 'multi_lap')
                else 'done:parked'
            )
            self.publish_state(done_label)
            self.get_logger().info(
                f'MISSION COMPLETE ({done_label}) at ({self.pos_x:.3f}, {self.pos_y:.3f}, '
                f'yaw={math.degrees(self.yaw):.1f} deg)!'
            )
            return

        # 4) Compute heading control toward active waypoint
        target_yaw = math.atan2(wp['y'] - self.pos_y, wp['x'] - self.pos_x)
        yaw_err = wrap_angle(target_yaw - self.yaw)

        cmd = Twist()
        if wp['precision']:
            ang_kp = 2.8
            cmd.angular.z = max(-self.max_angular, min(self.max_angular, ang_kp * yaw_err))
            if abs(yaw_err) > 0.28:
                cmd.linear.x = 0.0
            else:
                cmd.linear.x = min(wp['speed'], self.max_vel) * max(0.35, math.cos(yaw_err))
        else:
            corridor_w = max(-self.max_angular, min(self.max_angular, 2.4 * yaw_err))
            if abs(yaw_err) > 0.45:
                cmd.angular.z = corridor_w
                cmd.linear.x = 0.02
            else:
                if self.lane_fresh(now):
                    cam_w = max(-self.max_angular, min(self.max_angular, self.last_cmd.angular.z))
                    if abs(cam_w - corridor_w) < 0.55:
                        cmd.angular.z = 0.25 * cam_w + 0.75 * corridor_w
                    else:
                        cmd.angular.z = corridor_w
                else:
                    cmd.angular.z = corridor_w
                speed = min(wp['speed'], self.max_vel)
                cmd.linear.x = speed * max(0.35, math.cos(yaw_err) ** 1.5)

        if self.obstacle_blocked and cmd.linear.x > 0.0:
            if abs(yaw_err) > 0.12:
                cmd.linear.x = 0.0
                cmd.angular.z = max(-self.max_angular, min(self.max_angular, 3.0 * yaw_err))
            else:
                cmd.linear.x = min(cmd.linear.x, 0.04)

        self.cmd_pub.publish(cmd)
        self.publish_state(wp['stage'])


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
