#!/usr/bin/env python3

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'model_path', default_value='',
            description='Custom YOLO weights (.pt). Empty = yolov8n COCO model'),
        DeclareLaunchArgument('confidence_threshold', default_value='0.5'),
        DeclareLaunchArgument('device', default_value='cpu'),
        DeclareLaunchArgument(
            'input_topic', default_value='/camera/image_compensated',
            description='Camera topic (raw Image; no compressed variant exists)'),
        DeclareLaunchArgument('output_topic', default_value='/yolo/sign_detections'),
        DeclareLaunchArgument('publish_annotated', default_value='true'),
        DeclareLaunchArgument(
            'process_every_n', default_value='3',
            description='Run inference on every Nth frame (CPU relief for Gazebo)'),
        DeclareLaunchArgument(
            'imgsz', default_value='320', description='Inference resolution'),

        Node(
            package='turtlebot3_autorace_detect',
            executable='yolo_sign_detector',
            name='yolo_sign_detector',
            output='screen',
            parameters=[{
                'model_path': LaunchConfiguration('model_path'),
                'confidence_threshold': LaunchConfiguration('confidence_threshold'),
                'device': LaunchConfiguration('device'),
                'input_topic': LaunchConfiguration('input_topic'),
                'output_topic': LaunchConfiguration('output_topic'),
                'publish_annotated': LaunchConfiguration('publish_annotated'),
                'process_every_n': LaunchConfiguration('process_every_n'),
                'imgsz': LaunchConfiguration('imgsz'),
            }],
        ),
    ])
