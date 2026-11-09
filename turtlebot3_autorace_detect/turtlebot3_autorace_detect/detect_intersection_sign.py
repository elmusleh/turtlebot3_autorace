#!/usr/bin/env python3
#
# Copyright 2018 ROBOTIS CO., LTD.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author: Leon Jung, Gilbert, Ashe Kim, Jun

from enum import Enum
import os
import time

import cv2
from cv_bridge import CvBridge
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
from sensor_msgs.msg import Image
from std_msgs.msg import UInt8


class DetectSign(Node):

    def __init__(self):
        super().__init__('detect_sign')

        self.sub_image_type = 'raw'
        self.pub_image_type = 'compressed'

        if self.sub_image_type == 'compressed':
            self.sub_image_original = self.create_subscription(
                CompressedImage,
                '/detect/image_input/compressed',
                self.cbFindTrafficSign,
                10
            )
        else:
            self.sub_image_original = self.create_subscription(
                Image,
                '/detect/image_input',
                self.cbFindTrafficSign,
                10
            )

        self.pub_traffic_sign = self.create_publisher(UInt8, '/detect/traffic_sign', 10)
        self.pub_image_traffic_sign = self.create_publisher(
            CompressedImage,
            '/detect/image_output/compressed', 10
        )
        self.pub_image_traffic_sign_raw = self.create_publisher(
            Image, '/detect/image_output', 10
        )

        self.cvBridge = CvBridge()
        self.TrafficSign = Enum(
            'TrafficSign',
            'intersection left right construction parking stop tunnel'
        )
        self.counter = 1
        self.last_match_img = None
        self.last_match_until = 0.0

        self.templates = {}
        self.fnPreproc()

        self.get_logger().info('DetectSign Node Initialized (all 7 course signs active)')

    def fnPreproc(self):
        self.sift = cv2.SIFT_create(nfeatures=500, contrastThreshold=0.02, edgeThreshold=15)

        try:
            from ament_index_python.packages import get_package_share_directory
            dir_path = os.path.join(
                get_package_share_directory('turtlebot3_autorace_detect'), 'image'
            )
        except Exception:
            dir_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'image'
            )

        sign_files = [
            ('intersection', 'intersection.png', self.TrafficSign.intersection.value, 7, 6),
            ('left', 'left.png', self.TrafficSign.left.value, 8, 7),
            ('right', 'right.png', self.TrafficSign.right.value, 8, 6),
            ('construction', 'construction.png', self.TrafficSign.construction.value, 6, 5),
            ('parking', 'parking.png', self.TrafficSign.parking.value, 5, 4),
            ('stop', 'stop.png', self.TrafficSign.stop.value, 6, 5),
            ('tunnel', 'tunnel.png', self.TrafficSign.tunnel.value, 6, 5),
        ]

        for name, filename, code, min_good, min_inliers in sign_files:
            path = os.path.join(dir_path, filename)
            img = cv2.imread(path, 0)
            if img is None:
                self.get_logger().warn(f'Failed to load template: {path}')
                continue
            kp, des = self.sift.detectAndCompute(img, None)
            if des is None or len(kp) < 4:
                continue
            self.templates[name] = {
                'img': img,
                'kp': kp,
                'des': des,
                'code': code,
                'min_good': min_good,
                'min_inliers': min_inliers,
            }

        FLANN_INDEX_KDTREE = 0
        index_params = {'algorithm': FLANN_INDEX_KDTREE, 'trees': 5}
        search_params = {'checks': 50}
        self.flann = cv2.FlannBasedMatcher(index_params, search_params)

    def _check_template(self, kp1, des1, tmpl, frame_shape):
        des_t = tmpl['des']
        kp_t = tmpl['kp']
        img_t = tmpl['img']
        if des1 is None or len(kp1) < tmpl['min_good']:
            return None

        try:
            matches = self.flann.knnMatch(des1, des_t, k=2)
        except Exception:
            return None

        good = []
        for pair in matches:
            if len(pair) == 2:
                m, n = pair
                if m.distance < 0.72 * n.distance:
                    good.append(m)

        if len(good) < tmpl['min_good']:
            return None

        src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp_t[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

        M, mask = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, 4.5)
        if M is None or mask is None:
            return None

        mask_list = mask.ravel().tolist()
        inliers = int(np.sum(mask_list))
        if inliers < tmpl['min_inliers']:
            return None
        if inliers / float(len(good)) < 0.45:
            return None

        th, tw = img_t.shape[:2]
        corners = np.float32([[0, 0], [0, th - 1], [tw - 1, th - 1], [tw - 1, 0]]).reshape(-1, 1, 2)
        try:
            proj = cv2.perspectiveTransform(corners, M)
        except Exception:
            return None

        poly = np.int32(proj)
        if not cv2.isContourConvex(poly):
            return None

        area = float(cv2.contourArea(poly))
        fh, fw = frame_shape[:2]
        if not (300.0 <= area <= (fh * fw * 0.48)):
            return None

        x, y, bw, bh = cv2.boundingRect(poly)
        if bw <= 8 or bh <= 8:
            return None
        aspect = float(bw) / float(bh)
        if not (0.30 <= aspect <= 2.8):
            return None
        extent = area / float(bw * bh)
        if extent < 0.38:
            return None

        return {
            'good': good,
            'mask': mask_list,
            'inliers': inliers,
            'poly': poly,
            'bbox': (x, y, bw, bh),
        }

    def cbFindTrafficSign(self, image_msg):
        if self.counter % 2 != 0:
            self.counter += 1
            return
        self.counter = 1

        if self.sub_image_type == 'compressed':
            np_arr = np.frombuffer(image_msg.data, np.uint8)
            cv_image_input = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        else:
            cv_image_input = self.cvBridge.imgmsg_to_cv2(image_msg, 'bgr8')

        if cv_image_input is None:
            return

        kp1, des1 = self.sift.detectAndCompute(cv_image_input, None)

        best_name = None
        best_res = None
        best_score = -1

        for name, tmpl in self.templates.items():
            res = self._check_template(kp1, des1, tmpl, cv_image_input.shape)
            if res is not None and res['inliers'] > best_score:
                best_score = res['inliers']
                best_name = name
                best_res = res

        now = time.time()
        out_img = cv_image_input

        if best_name is not None and best_res is not None:
            tmpl = self.templates[best_name]
            msg_sign = UInt8()
            msg_sign.data = int(tmpl['code'])
            self.pub_traffic_sign.publish(msg_sign)
            self.get_logger().info(
                f'Detect {best_name.upper()} sign (code={tmpl["code"]}, inliers={best_res["inliers"]})'
            )

            vis = cv_image_input.copy()
            bx, by, bw, bh = best_res['bbox']
            yellow = (0, 255, 255)
            cv2.rectangle(vis, (bx, by), (bx + bw, by + bh), yellow, 3, cv2.LINE_AA)
            label = f'{best_name.upper()}'
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            ty = max(th + 8, by - 6)
            cv2.rectangle(vis, (bx, ty - th - 6), (bx + tw + 10, ty + 4), (0, 0, 0), -1)
            cv2.putText(
                vis, label, (bx + 5, ty - 2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, yellow, 2, cv2.LINE_AA
            )
            out_img = vis
            self.last_match_img = out_img
            self.last_match_until = now + 2.8
        elif self.last_match_img is not None and now < self.last_match_until:
            out_img = self.last_match_img

        self.pub_image_traffic_sign.publish(
            self.cvBridge.cv2_to_compressed_imgmsg(out_img, 'jpg')
        )
        self.pub_image_traffic_sign_raw.publish(
            self.cvBridge.cv2_to_imgmsg(out_img, 'bgr8')
        )


def main(args=None):
    rclpy.init(args=args)
    node = DetectSign()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
