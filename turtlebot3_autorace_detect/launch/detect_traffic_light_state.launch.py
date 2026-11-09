#!/usr/bin/env python3
"""Launch the traffic light state detector (publishes red/yellow/green/none)."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('min_blob_area', default_value='120.0'),
        DeclareLaunchArgument('confirm_frames', default_value='3'),
        DeclareLaunchArgument('process_every_n', default_value='2'),
        DeclareLaunchArgument('publish_debug_image', default_value='true'),
        DeclareLaunchArgument(
            'input_topic', default_value='/camera/image_compensated',
            description='Camera topic. Raw Image: the camera package publishes no '
                        'compressed variant of image_compensated.'),

        Node(
            package='turtlebot3_autorace_detect',
            executable='traffic_light_state',
            name='traffic_light_state',
            output='screen',
            parameters=[{
                'input_topic': LaunchConfiguration('input_topic'),
                'min_blob_area': LaunchConfiguration('min_blob_area'),
                'confirm_frames': LaunchConfiguration('confirm_frames'),
                'process_every_n': LaunchConfiguration('process_every_n'),
                'publish_debug_image': LaunchConfiguration('publish_debug_image'),
            }],
        ),
    ])
