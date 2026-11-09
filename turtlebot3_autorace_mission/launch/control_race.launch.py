#!/usr/bin/env python3
"""
Race controller: lane following + mission supervisor speed/stop gate.

control_lane publishes on /control/cmd_vel; mission_supervisor is the sole
owner of /cmd_vel and coordinates traffic light waiting, slow sign reading
pauses, roundabout navigation, dynamic LiDAR + slalom barrier avoidance, and
either autonomous parking (`course_mode:=parking`) or the full course loop
through the level crossing and tunnel (`course_mode:=full_loop`).
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    default_yaml = os.path.join(
        get_package_share_directory('turtlebot3_autorace_mission'),
        'param',
        'course_2020.yaml',
    )

    return LaunchDescription([
        DeclareLaunchArgument('max_vel', default_value='0.14'),
        DeclareLaunchArgument('stop_states', default_value='red,yellow'),
        DeclareLaunchArgument('wall_dist', default_value='0.40'),
        DeclareLaunchArgument('course_mode', default_value='parking'),
        DeclareLaunchArgument('sign_stop_seconds', default_value='3.0'),
        DeclareLaunchArgument('course_config', default_value=default_yaml),

        Node(
            package='turtlebot3_autorace_mission',
            executable='control_lane',
            name='control_lane',
            output='screen',
            remappings=[
                ('/control/lane', '/detect/lane'),
            ],
        ),
        Node(
            package='turtlebot3_autorace_mission',
            executable='mission_supervisor',
            name='mission_supervisor',
            output='screen',
            parameters=[{
                'max_vel': LaunchConfiguration('max_vel'),
                'stop_states': LaunchConfiguration('stop_states'),
                'wall_dist': LaunchConfiguration('wall_dist'),
                'course_mode': LaunchConfiguration('course_mode'),
                'sign_stop_seconds': LaunchConfiguration('sign_stop_seconds'),
                'course_config': LaunchConfiguration('course_config'),
            }],
        ),
    ])
