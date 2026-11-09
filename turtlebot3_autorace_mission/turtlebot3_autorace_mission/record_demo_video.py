#!/usr/bin/env python3
"""
Side-by-side demonstration video recorder for TurtleBot3 AutoRace 2020.

Subscribes to:
  - /detect/image_lane/compressed (bird's-eye lane + HUD telemetry banner)
  - /detect/image_traffic_sign/compressed (front camera + yellow-box sign detection)
  - /mission/state (flushes and finalizes the MP4 automatically on `done:*`)

Horizontally concatenates both streams into a 1280x480 15 FPS MP4 video at
`output_path` (default: /root/ros2_humble_ws/demo_recording.mp4).
"""

import os
import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
from std_msgs.msg import String


class RecordDemoVideo(Node):

    def __init__(self):
        super().__init__('record_demo_video')

        self.declare_parameter('enabled', True)
        self.declare_parameter('output_path', '/root/ros2_humble_ws/demo_recording.mp4')
        self.declare_parameter('fps', 15.0)
        self.declare_parameter('frame_height', 480)
        self.declare_parameter('panel_width', 640)

        self.enabled = bool(self.get_parameter('enabled').value)
        self.output_path = str(self.get_parameter('output_path').value)
        self.fps = float(self.get_parameter('fps').value)
        self.frame_h = int(self.get_parameter('frame_height').value)
        self.panel_w = int(self.get_parameter('panel_width').value)

        self.lane_frame = None
        self.sign_frame = None
        self.writer = None
        self.frame_count = 0
        self.closed = False

        if not self.enabled:
            self.get_logger().info('Demo video recording disabled (enabled=false).')
            return

        os.makedirs(os.path.dirname(os.path.abspath(self.output_path)), exist_ok=True)

        self.create_subscription(
            CompressedImage, '/detect/image_lane/compressed', self._on_lane, 5
        )
        self.create_subscription(
            CompressedImage, '/detect/image_traffic_sign/compressed', self._on_sign, 5
        )
        self.create_subscription(String, '/mission/state', self._on_state, 10)
        self.create_timer(1.0 / max(1.0, self.fps), self._write_tick)

        self.get_logger().info(
            f'Recording side-by-side demo video to {self.output_path} '
            f'({self.panel_w * 2}x{self.frame_h} @ {self.fps:.0f} FPS)'
        )

    def _decode(self, msg):
        arr = np.frombuffer(msg.data, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return None
        return cv2.resize(img, (self.panel_w, self.frame_h), interpolation=cv2.INTER_AREA)

    def _on_lane(self, msg):
        img = self._decode(msg)
        if img is not None:
            self.lane_frame = img

    def _on_sign(self, msg):
        img = self._decode(msg)
        if img is not None:
            self.sign_frame = img

    def _on_state(self, msg):
        if msg.data.startswith('done:') and not self.closed:
            self._close_writer(reason=msg.data)

    def _write_tick(self):
        if self.closed or not self.enabled:
            return
        if self.lane_frame is None and self.sign_frame is None:
            return

        left = (
            self.lane_frame
            if self.lane_frame is not None
            else np.zeros((self.frame_h, self.panel_w, 3), dtype=np.uint8)
        )
        right = (
            self.sign_frame
            if self.sign_frame is not None
            else np.zeros((self.frame_h, self.panel_w, 3), dtype=np.uint8)
        )
        combined = np.hstack((left, right))

        if self.writer is None:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.writer = cv2.VideoWriter(
                self.output_path, fourcc, self.fps, (self.panel_w * 2, self.frame_h)
            )

        self.writer.write(combined)
        self.frame_count += 1

    def _close_writer(self, reason='shutdown'):
        if self.writer is not None and not self.closed:
            self.writer.release()
            self.closed = True
            self.get_logger().info(
                f'Finalized demo video ({self.frame_count} frames, reason={reason}): '
                f'{self.output_path}'
            )

    def destroy_node(self):
        self._close_writer(reason='destroy_node')
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = RecordDemoVideo()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node._close_writer(reason='exit')
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
