#!/usr/bin/env python3
"""
Intrinsic rectification as a standalone node.

The upstream intrinsic_camera_calibration.launch.py loads image_proc's
RectifyNode + DebayerNode into a rclcpp_components container, which
intermittently hangs at component load (no /camera/image_rect is ever
published and every downstream detector goes silent). image_proc also ships
standalone executables, so we run rectify_node directly instead: fewer
moving parts, no container handshake, same output topics.

Publishes: /camera/image_rect, /camera/image_rect_color
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    rectify = Node(
        package='image_proc',
        executable='rectify_node',
        name='rectify_node',
        namespace='camera',
        output='screen',
        parameters=[{'queue_size': 20}],
        remappings=[
            ('image', '/camera/image_raw'),
            ('camera_info', '/camera/camera_info'),
            ('image_rect', '/camera/image_rect'),
            ('image_rect_color', '/camera/image_rect_color'),
        ],
    )
    return LaunchDescription([rectify])
