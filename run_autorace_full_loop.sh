#!/bin/bash
# ==============================================================================
# run_autorace_full_loop.sh — Simulation 2 (Completes Full 360° Course Loop)
# Tasks: Traffic Light -> Intersection -> Construction Slalom -> Parking Sign
#        -> Chicane -> Stop Sign -> Level Crossing -> S-Curve -> Tunnel Sign
#        -> Dark Tunnel Obstacle Avoidance -> Finish at Start Line
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export COURSE_MODE=full_loop
exec "${SCRIPT_DIR}/run_autorace_humble.sh" "$@"
