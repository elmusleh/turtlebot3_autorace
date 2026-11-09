#!/usr/bin/env python3
"""
Extrinsic compensation with a working input topic.

The upstream extrinsic_camera_calibration.launch.py expects
/camera/image_rect_color, but the Gazebo camera publishes rgb8, so
rectify_node only ever produces /camera/image_rect (already colour) and
/camera/image_rect_color is never created. Both compensation nodes therefore
starve and /camera/image_compensated is silent, which silently disables every
detector downstream.

This launch reads /camera/image_rect directly and publishes
/camera/image_compensated for the detection nodes.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    calibration_mode = LaunchConfiguration('calibration_mode')
    input_image = LaunchConfiguration('input_image')
    input_image_compressed = LaunchConfiguration('input_image_compressed')

    share = get_package_share_directory('turtlebot3_autorace_camera')
    compensation_param = os.path.join(
        share, 'calibration', 'extrinsic_calibration', 'compensation.yaml')
    projection_param = os.path.join(
        share, 'calibration', 'extrinsic_calibration', 'projection.yaml')

    image_projection_node = Node(
        package='turtlebot3_autorace_camera',
        executable='image_projection',
        namespace='camera',
        name='image_projection',
        output='screen',
        parameters=[projection_param,
                    {'is_extrinsic_camera_calibration_mode': calibration_mode}],
        remappings=[
            ('/camera/image_input', input_image),
            ('/camera/image_input/compressed', input_image_compressed),
            ('/camera/image_output', '/camera/image_projected'),
            ('/camera/image_calib', '/camera/image_extrinsic_calib'),
        ],
    )

    image_compensation_node = Node(
        package='turtlebot3_autorace_camera',
        executable='image_compensation',
        namespace='camera',
        name='image_compensation',
        output='screen',
        parameters=[{'is_extrinsic_camera_calibration_mode': calibration_mode},
                    compensation_param],
        remappings=[
            ('/camera/image_input', input_image),
            ('/camera/image_input/compressed', input_image_compressed),
            ('/camera/image_output', '/camera/image_compensated'),
        ],
    )

    return LaunchDescription([
        DeclareLaunchArgument('calibration_mode', default_value='False'),
        DeclareLaunchArgument(
            'input_image', default_value='/camera/image_rect',
            description='Rectified colour image (rgb8) from rectify_node'),
        DeclareLaunchArgument(
            'input_image_compressed', default_value='/camera/image_rect/compressed',
            description='image_compensation subscribes to the COMPRESSED variant by '
                        'default, so it must be remapped too'),
        image_projection_node,
        image_compensation_node,
    ])
