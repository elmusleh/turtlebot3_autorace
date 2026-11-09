#!/bin/bash
# ==============================================================================
# run_autorace_full_loop.sh — Simulation 2 (Full 360° Course Loop to Start Line)
# Tasks: Traffic light -> Intersection -> Construction Slalom -> Parking Sign
#        -> Chicane -> Stop Sign & Level Crossing Bar -> S-Curve -> Tunnel Sign
#        -> Dark Tunnel (3 cylindrical obstacles) -> Finish at Start Line
# ==============================================================================
set -e

export COURSE_MODE="full_loop"
exec "/home/steve/dev/ros2_exmaple/run_autorace_humble.sh" "$@"
