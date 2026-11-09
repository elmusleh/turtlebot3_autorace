#!/usr/bin/env python3
"""Print /detect/traffic_light_state, /detect/traffic_sign, /mission/state live.

Used in the tmux 'control' window as a human-readable monitor. Avoids
`ros2 topic echo`, which can fail against a daemon from another ROS distro.
"""

import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, UInt8


SIGN_LABELS = {
    0: 'none',
    1: 'intersection',
    2: 'left',
    3: 'right',
    4: 'construction',
    5: 'parking',
    6: 'stop',
    7: 'tunnel',
}


class StateMonitor(Node):
    def __init__(self):
        super().__init__('state_monitor')
        self.light = '-'
        self.sign = 0
        self.mission = '-'
        self.dirty = True
        self.create_subscription(String, '/detect/traffic_light_state',
                                 lambda m: self.update('light', m.data), 10)
        self.create_subscription(UInt8, '/detect/traffic_sign',
                                 lambda m: self.update('sign', m.data), 10)
        self.create_subscription(String, '/mission/state',
                                 lambda m: self.update('mission', m.data), 10)
        self.create_timer(0.5, self.render)

    def update(self, field, value):
        if getattr(self, field) != value:
            setattr(self, field, value)
            self.dirty = True

    def render(self):
        if not self.dirty:
            return
        self.dirty = False
        sign_str = f'{self.sign}:{SIGN_LABELS.get(int(self.sign), "?")}'
        print(f'[{time.strftime("%H:%M:%S")}] '
              f'LIGHT={self.light:<6} SIGN={sign_str:<15} '
              f'MISSION={self.mission}', flush=True)


rclpy.init()
node = StateMonitor()
try:
    rclpy.spin(node)
except (KeyboardInterrupt, Exception):
    pass
