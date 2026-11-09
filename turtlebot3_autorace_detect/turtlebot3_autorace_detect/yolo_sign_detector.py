#!/usr/bin/env python3
"""
YOLO-based traffic sign detection for TurtleBot3 AutoRace.

Publishes Detection2DArray on /yolo/sign_detections plus a simple
std_msgs/String state on /yolo/sign_state so mission control can react.

CPU notes:
  Gazebo and YOLO share the same CPU, so running inference on every frame
  at full resolution tanks the real-time factor (the sim looks "slow").
  process_every_n + a small imgsz keep the sim fast.
"""

import os

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import CompressedImage, Image
from std_msgs.msg import String
from cv_bridge import CvBridge
from vision_msgs.msg import Detection2D, Detection2DArray, ObjectHypothesisWithPose

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:  # pragma: no cover - only when ultralytics is missing
    YOLO_AVAILABLE = False
    YOLO = None


# COCO names that matter for driving, mapped into our vocabulary.
# A COCO yolov8n model only knows these; it does NOT know "left turn" or
# "speed limit", so we must never invent those labels.
COCO_ALIASES = {
    'stop sign': 'stop_sign',
    'traffic light': 'traffic_light',
}
# only these are worth acting on
RELEVANT_SIGNS = {'stop_sign', 'traffic_light'}


class YOLOSignDetector(Node):
    def __init__(self):
        super().__init__('yolo_sign_detector')

        self.declare_parameter('model_path', '')
        self.declare_parameter('confidence_threshold', 0.5)
        self.declare_parameter('device', 'cpu')
        self.declare_parameter('input_topic', '/camera/image_compensated/compressed')
        self.declare_parameter('output_topic', '/yolo/sign_detections')
        self.declare_parameter('publish_annotated', True)
        self.declare_parameter('process_every_n', 3)   # skip frames to save CPU
        self.declare_parameter('imgsz', 320)           # inference resolution

        self.confidence_threshold = float(
            self.get_parameter('confidence_threshold').value)
        self.device = self.get_parameter('device').value
        self.publish_annotated = bool(self.get_parameter('publish_annotated').value)
        self.process_every_n = max(1, int(self.get_parameter('process_every_n').value))
        self.imgsz = int(self.get_parameter('imgsz').value)

        self.bridge = CvBridge()
        self.frame_i = 0
        self.model = None
        self.model_loaded = False
        self.names = {}
        self.load_model()

        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )

        input_topic = self.get_parameter('input_topic').value
        msg_type = CompressedImage if 'compressed' in input_topic else Image
        self.create_subscription(msg_type, input_topic, self.image_callback, qos)

        output_topic = self.get_parameter('output_topic').value
        self.detection_pub = self.create_publisher(Detection2DArray, output_topic, qos)
        self.annotated_pub = self.create_publisher(
            CompressedImage, '/yolo/annotated_image/compressed', qos)
        self.sign_state_pub = self.create_publisher(String, '/yolo/sign_state', qos)

        self.get_logger().info(
            f'YOLO sign detector: in={input_topic} every_n={self.process_every_n} '
            f'imgsz={self.imgsz} available={YOLO_AVAILABLE}')

    def load_model(self):
        if not YOLO_AVAILABLE:
            self.get_logger().warn('ultralytics missing: pip3 install ultralytics')
            return
        model_path = self.get_parameter('model_path').value
        try:
            self.model = YOLO(model_path if model_path and os.path.exists(model_path)
                              else 'yolov8n.pt')
            self.model.to(self.device)
            self.names = dict(self.model.names or {})
            self.model_loaded = True
            self.get_logger().info(
                f'YOLO model ready: {self.model.ckpt_path} ({len(self.names)} classes)')
        except Exception as exc:  # noqa: BLE001
            self.get_logger().error(f'Failed to load YOLO model: {exc}')

    def image_callback(self, msg):
        if not self.model_loaded:
            return
        self.frame_i += 1
        if self.frame_i % self.process_every_n != 0:
            return

        try:
            if isinstance(msg, CompressedImage):
                frame = cv2.imdecode(np.frombuffer(msg.data, np.uint8),
                                     cv2.IMREAD_COLOR)
                header = msg.header
            else:
                frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
                header = msg.header
            if frame is None:
                return

            results = self.model(frame, conf=self.confidence_threshold,
                                 imgsz=self.imgsz, verbose=False)
        except Exception as exc:  # noqa: BLE001
            self.get_logger().error(f'Detection error: {exc}')
            return

        detections = Detection2DArray()
        detections.header = header

        best_name, best_conf = None, 0.0
        for result in results:
            boxes = getattr(result, 'boxes', None)
            if boxes is None:
                continue
            for box in boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].cpu().numpy()]
                raw = str(self.names.get(cls_id, cls_id)).lower()
                name = COCO_ALIASES.get(raw, raw)

                det = Detection2D()
                det.header = header
                det.bbox.center.position.x = (x1 + x2) / 2.0
                det.bbox.center.position.y = (y1 + y2) / 2.0
                det.bbox.size_x = x2 - x1
                det.bbox.size_y = y2 - y1
                hyp = ObjectHypothesisWithPose()
                hyp.hypothesis.class_id = name
                hyp.hypothesis.score = conf
                det.results.append(hyp)
                detections.detections.append(det)

                if conf > best_conf:
                    best_name, best_conf = name, conf

        self.detection_pub.publish(detections)

        if best_name in RELEVANT_SIGNS:
            self.sign_state_pub.publish(String(data=best_name))
            self.get_logger().info(f'sign: {best_name} ({best_conf:.2f})')

        if self.publish_annotated:
            annotated = results[0].plot() if results else frame
            annotated_msg = self.bridge.cv2_to_compressed_imgmsg(annotated, 'jpg')
            annotated_msg.header = header
            self.annotated_pub.publish(annotated_msg)


def main(args=None):
    rclpy.init(args=args)
    node = YOLOSignDetector()
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
