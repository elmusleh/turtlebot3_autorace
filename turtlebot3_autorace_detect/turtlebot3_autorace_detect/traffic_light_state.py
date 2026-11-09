#!/usr/bin/env python3
"""
Traffic light state detector for TurtleBot3 AutoRace.

Publishes std_msgs/String on /detect/traffic_light_state:
    red | yellow | green | none

Key behaviours (each one exists because of a real failure mode):
  * Heartbeat: the state is republished at a fixed rate, not just on change.
    A consumer that treats silence as "stale" would otherwise drive off on red,
    because the sim light stays red for 5 s without emitting anything new.
  * Largest-blob area instead of raw pixel count, so scattered red pixels on a
    wall cannot fake a red light.
  * Hold time: a missed frame does not immediately become "none".

The Gazebo traffic light cycles red 5 s -> yellow 1 s -> green 5 s
(turtlebot3_gazebo/src/traffic_light_plugin.cpp).
"""

import cv2
from cv_bridge import CvBridge
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage, Image
from std_msgs.msg import String


class TrafficLightState(Node):
    def __init__(self):
        super().__init__('traffic_light_state')

        # HSV thresholds (OpenCV: H 0-179, S/V 0-255)
        self.declare_parameter('red.hue_l', 0)
        self.declare_parameter('red.hue_h', 12)
        self.declare_parameter('red.saturation_l', 120)
        self.declare_parameter('red.saturation_h', 255)
        self.declare_parameter('red.lightness_l', 120)
        self.declare_parameter('red.lightness_h', 255)

        self.declare_parameter('yellow.hue_l', 19)
        self.declare_parameter('yellow.hue_h', 35)
        self.declare_parameter('yellow.saturation_l', 150)
        self.declare_parameter('yellow.saturation_h', 255)
        self.declare_parameter('yellow.lightness_l', 150)
        self.declare_parameter('yellow.lightness_h', 255)

        self.declare_parameter('green.hue_l', 40)
        self.declare_parameter('green.hue_h', 100)
        self.declare_parameter('green.saturation_l', 120)
        self.declare_parameter('green.saturation_h', 255)
        self.declare_parameter('green.lightness_l', 90)
        self.declare_parameter('green.lightness_h', 255)

        self.declare_parameter('min_blob_area', 120.0)   # px^2 of the light disc
        self.declare_parameter('max_blob_area', 4000.0)  # a lamp never fills the ROI
        self.declare_parameter('confirm_frames', 3)      # agreement before switching
        self.declare_parameter('hold_time', 0.6)         # s to keep a lost colour
        self.declare_parameter('publish_rate', 5.0)      # Hz heartbeat
        self.declare_parameter('process_every_n', 2)
        self.declare_parameter('publish_debug_image', True)
        # The lamp sits on the right-hand post, mid-frame. Without this ROI the
        # big red start barrier at the bottom of the image is mistaken for a
        # red light and the robot never leaves on green.
        self.declare_parameter('roi_top', 0.28)
        self.declare_parameter('roi_bottom', 0.72)
        self.declare_parameter('roi_left', 0.47)
        self.declare_parameter('roi_right', 1.0)
        self.declare_parameter(
            'input_topic', '/camera/image_compensated')  # this node has no compressed variant

        g = self.get_parameter
        self.ranges = {
            'red': ((g('red.hue_l').value, g('red.saturation_l').value,
                     g('red.lightness_l').value),
                    (g('red.hue_h').value, g('red.saturation_h').value,
                     g('red.lightness_h').value)),
            'yellow': ((g('yellow.hue_l').value, g('yellow.saturation_l').value,
                        g('yellow.lightness_l').value),
                       (g('yellow.hue_h').value, g('yellow.saturation_h').value,
                        g('yellow.lightness_h').value)),
            'green': ((g('green.hue_l').value, g('green.saturation_l').value,
                       g('green.lightness_l').value),
                      (g('green.hue_h').value, g('green.saturation_h').value,
                       g('green.lightness_h').value)),
        }
        self.min_blob_area = float(g('min_blob_area').value)
        self.max_blob_area = float(g('max_blob_area').value)
        self.confirm_frames = max(1, int(g('confirm_frames').value))
        self.hold_time = float(g('hold_time').value)
        self.process_every_n = max(1, int(g('process_every_n').value))
        self.publish_debug = bool(g('publish_debug_image').value)
        self.input_topic = str(g('input_topic').value)
        self.roi = (float(g('roi_top').value), float(g('roi_bottom').value),
                    float(g('roi_left').value), float(g('roi_right').value))

        self.state = 'none'
        self.candidate_hist = []
        self.frame_i = 0
        self.last_seen_time = None
        self.last_areas = {'red': 0.0, 'yellow': 0.0, 'green': 0.0}
        self.bridge = CvBridge()

        self.create_subscription(
            CompressedImage if 'compressed' in self.input_topic else Image,
            self.input_topic, self.on_image, 1)

        self.state_pub = self.create_publisher(
            String, '/detect/traffic_light_state', 10)
        self.debug_pub = self.create_publisher(
            CompressedImage, '/detect/image_traffic_light_state/compressed', 1)

        rate = max(1.0, float(g('publish_rate').value))
        self.create_timer(1.0 / rate, self.heartbeat)

        self.get_logger().info(
            f'Traffic light state detector up (min_blob_area={self.min_blob_area} '
            f'confirm={self.confirm_frames} rate={rate}Hz)')

    # ------------------------------------------------------------- heartbeat
    def heartbeat(self):
        """Republish the current state so consumers never see a stale silence."""
        self.state_pub.publish(String(data=self.state))

    # ----------------------------------------------------------------- image
    def on_image(self, msg):
        self.frame_i += 1
        if self.frame_i % self.process_every_n != 0:
            return
        if isinstance(msg, CompressedImage):
            frame = cv2.imdecode(np.frombuffer(msg.data, np.uint8),
                                 cv2.IMREAD_COLOR)
        else:
            frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        if frame is not None:
            self.process(frame)

    def process(self, frame):
        h, w = frame.shape[:2]
        top, bottom, left, right = self.roi
        region = frame[int(h * top):int(h * bottom), int(w * left):int(w * right)]
        hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
        areas = {}
        for colour, (lo, hi) in self.ranges.items():
            mask = cv2.inRange(hsv, np.array(lo, np.uint8), np.array(hi, np.uint8))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
            cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
            areas[colour] = self.lamp_area(cnts)
        self.last_areas = areas

        best = max(areas, key=lambda colour: areas[colour])
        seen = best if areas[best] >= self.min_blob_area else None
        now = self.get_clock().now().nanoseconds / 1e9

        if seen:
            self.last_seen_time = now
        elif self.last_seen_time is not None and (now - self.last_seen_time) > self.hold_time:
            seen = 'none'
        else:
            seen = self.state          # brief dropout: keep what we had

        self.candidate_hist.append(seen)
        if len(self.candidate_hist) > self.confirm_frames:
            self.candidate_hist.pop(0)

        if (len(self.candidate_hist) == self.confirm_frames
                and len(set(self.candidate_hist)) == 1
                and seen != self.state):
            self.set_state(seen, areas)

        if self.publish_debug:
            self.publish_debug_image(frame, areas, seen)

    def lamp_area(self, cnts):
        """Largest contour that looks like a lamp disc, not a painted stripe.

        The yellow centre line is also "yellow" in HSV and sweeps through the
        ROI as the robot turns. A lamp is compact (aspect ~1, filling most of
        its bounding box); road paint is a long thin band.
        """
        best = 0.0
        for cnt in cnts:
            area = cv2.contourArea(cnt)
            if not (self.min_blob_area <= area <= self.max_blob_area):
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            if bw == 0 or bh == 0:
                continue
            aspect = bw / bh
            extent = area / (bw * bh)
            if not (0.35 <= aspect <= 2.5):
                continue
            if extent < 0.40:
                continue
            best = max(best, area)
        return best

    # ------------------------------------------------------------------ state
    def set_state(self, new_state, areas):
        old, self.state = self.state, new_state
        self.get_logger().info(
            f'traffic light: {old} -> {new_state} '
            f'(areas red={areas["red"]:.0f} yellow={areas["yellow"]:.0f} '
            f'green={areas["green"]:.0f})')
        self.state_pub.publish(String(data=new_state))

    def publish_debug_image(self, frame, areas, seen):
        vis = frame.copy()
        h, w = vis.shape[:2]
        top, bottom, left, right = self.roi
        cv2.rectangle(vis, (int(w * left), int(h * top)),
                      (int(w * right), int(h * bottom)), (255, 255, 0), 1)
        text = (f'{seen}  R{areas["red"]:.0f} Y{areas["yellow"]:.0f} '
                f'G{areas["green"]:.0f}')
        colour = {'red': (0, 0, 255), 'yellow': (0, 255, 255),
                  'green': (0, 255, 0)}.get(seen, (200, 200, 200))
        cv2.putText(vis, text, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, colour, 2)
        try:
            self.debug_pub.publish(
                self.bridge.cv2_to_compressed_imgmsg(vis, 'jpg'))
        except Exception:  # noqa: BLE001
            pass


def main(args=None):
    rclpy.init(args=args)
    node = TrafficLightState()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
