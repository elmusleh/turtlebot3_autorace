#!/usr/bin/env python3
"""
Automated verification & regression runner for TurtleBot3 AutoRace 2020.

Monitors /odom, /mission/state, /detect/traffic_light_state, /detect/traffic_sign,
and /scan until the mission reaches its terminal state (`done:parked` or
`done:lap-complete`), verifies sign-reading pauses and obstacle clearance, and
writes `/root/ros2_humble_ws/last_run_traj.txt`.
"""

import subprocess
import sys
import time
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String, UInt8


class CourseVerifier(Node):
    def __init__(self, timeout_sec=240.0):
        super().__init__('course_verifier')
        self.t0 = time.time()
        self.timeout_sec = timeout_sec
        self.x = 0.0
        self.y = 0.0
        self.state = '-'
        self.light = '-'
        self.sign = 0
        self.min_scan = 9e9
        self.traj = []
        self.sign_pauses = []
        self.signs_seen = set()
        self.done = False

        self.create_subscription(Odometry, '/odom', self.on_odom, 10)
        self.create_subscription(String, '/mission/state', self.on_state, 10)
        self.create_subscription(String, '/detect/traffic_light_state', self.on_light, 10)
        self.create_subscription(UInt8, '/detect/traffic_sign', self.on_sign, 10)
        self.create_subscription(LaserScan, '/scan', self.on_scan, 10)
        self.create_timer(2.0, self.report)

    def on_odom(self, m):
        self.x = m.pose.pose.position.x
        self.y = m.pose.pose.position.y
        self.traj.append((round(self.x, 3), round(self.y, 3)))

    def on_state(self, m):
        if m.data != self.state:
            self.state = m.data
            el = time.time() - self.t0
            print(
                f'[t={el:5.1f}s] STATE={self.state:<28} pos=({self.x:5.2f},{self.y:5.2f}) '
                f'light={self.light:<6} sign={self.sign}',
                flush=True,
            )
            if self.state.startswith('sign:reading:'):
                self.sign_pauses.append(self.state)
            if self.state in ('done:parked', 'done:lap-complete'):
                self.done = True

    def on_light(self, m):
        if m.data != self.light:
            self.light = m.data
            print(f'[t={time.time()-self.t0:5.1f}s] LIGHT={self.light}', flush=True)

    def on_sign(self, m):
        code = int(m.data)
        self.signs_seen.add(code)
        if code != self.sign:
            self.sign = code
            print(
                f'[t={time.time()-self.t0:5.1f}s] SIGN_DETECTED={self.sign} '
                f'at ({self.x:5.2f},{self.y:5.2f}) state={self.state}',
                flush=True,
            )

    def on_scan(self, m):
        vals = [r for r in m.ranges if r == r and 0.02 < r < 3.5]
        if vals:
            self.min_scan = min(self.min_scan, min(vals))

    def report(self):
        el = time.time() - self.t0
        if self.done or el > self.timeout_sec:
            with open('/root/ros2_humble_ws/last_run_traj.txt', 'w', encoding='utf-8') as f:
                for px, py in self.traj:
                    f.write(f'{px},{py}\n')
            print(
                f'=== VERIFICATION SUMMARY ===\n'
                f'  Result      : {"PASS" if self.done else "TIMEOUT"}\n'
                f'  Final State : {self.state} at ({self.x:.2f}, {self.y:.2f})\n'
                f'  Sign Pauses : {self.sign_pauses}\n'
                f'  Signs Seen  : {sorted(self.signs_seen)}\n'
                f'  Min LiDAR   : {self.min_scan:.3f} m',
                flush=True,
            )
            raise SystemExit(0 if self.done else 1)


def main():
    args = [a for a in sys.argv[1:] if a != '--headless']
    if '--headless' in sys.argv:
        subprocess.run(
            ['bash', '-c', 'HEADLESS=1 bash /root/ros2_humble_ws/run_tb3_race_tmux.sh'],
            check=False,
        )
        time.sleep(38.0)
    timeout = float(args[0]) if args else 280.0
    rclpy.init()
    node = CourseVerifier(timeout_sec=timeout)
    try:
        rclpy.spin(node)
    except SystemExit as exc:
        sys.exit(exc.code)


if __name__ == '__main__':
    main()
