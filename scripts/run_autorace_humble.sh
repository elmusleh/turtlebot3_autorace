#!/bin/bash
# ==============================================================================
# run_autorace_humble.sh — Simulation 1 (Ends with Autonomous Parking)
# Tasks: Traffic light -> Lane following -> Slow Sign Reading -> Barrier Slalom -> Parking
# ==============================================================================
set -e

REPO_DIR="/home/steve/dev/ros2_exmaple/ros2_humble_ws"
COURSE_MODE="${COURSE_MODE:-parking}"

# Scoped X11 cookie authentication (replaces broad xhost +local:root)
XAUTH_FILE="/tmp/.docker.autorace.xauth"
touch "$XAUTH_FILE"
chmod 600 "$XAUTH_FILE"
if command -v xauth >/dev/null 2>&1 && [ -n "${DISPLAY:-}" ]; then
    xauth nlist "${DISPLAY}" 2>/dev/null | sed -e 's/^..../ffff/' | xauth -f "$XAUTH_FILE" nmerge - 2>/dev/null || true
fi
xhost +SI:localuser:"$(id -un)" >/dev/null 2>&1 || true

# Clean up any leftover containers
docker ps -q --filter "ancestor=autorace:humble" | xargs -r docker rm -f 2>/dev/null || true

echo "=========================================================="
echo " Starting TurtleBot3 AutoRace 2020 (Mode: ${COURSE_MODE})"
echo " Tasks included:"
echo "   1. Gazebo Simulation (turtlebot3_autorace_2020 world)"
echo "   2. Camera Pipeline (Intrinsic + Extrinsic Compensation)"
echo "   3. Lane Detection (with HUD Banner) & Traffic Light State"
echo "   4. Slow Sign Reading (3.0s pause + Yellow Box Overlay)"
echo "   5. Dynamic LiDAR Slalom + Mission (${COURSE_MODE}) + MP4 Recorder"
echo "=========================================================="

docker run -it --rm \
  --user "$(id -u):$(id -g)" \
  --entrypoint /bin/bash \
  --net=host \
  --ipc=host \
  --privileged \
  -e HOME=/home/ros \
  -e DISPLAY="${DISPLAY:-:0}" \
  -e XAUTHORITY="$XAUTH_FILE" \
  -e QT_X11_NO_MITSHM=1 \
  -e TURTLEBOT3_MODEL=burger_cam \
  -e COURSE_MODE="${COURSE_MODE}" \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v "${XAUTH_FILE}:${XAUTH_FILE}:ro" \
  -v /dev/dri:/dev/dri:rw \
  -v "${REPO_DIR}:/root/ros2_humble_ws" \
  -w /root/ros2_humble_ws \
  autorace:humble \
  -c "COURSE_MODE=${COURSE_MODE} bash /root/ros2_humble_ws/run_tb3_race_tmux.sh"
