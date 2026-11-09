#!/bin/bash
# ==============================================================================
# run_autorace_humble.sh — Simulation 1 (Ends with Autonomous Parking)
# Tasks: Traffic light -> Lane following -> Slow Sign Reading -> Barrier Slalom -> Parking
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
WS_DIR="/home/steve/dev/ros2_exmaple/ros2_humble_ws"
COURSE_MODE="${COURSE_MODE:-parking}"

# Scoped X11 cookie authentication
XAUTH_FILE="/tmp/.docker.autorace.xauth"
touch "$XAUTH_FILE"
chmod 600 "$XAUTH_FILE"
if command -v xauth >/dev/null 2>&1 && [ -n "${DISPLAY:-}" ]; then
    xauth nlist "${DISPLAY}" 2>/dev/null | sed -e 's/^..../ffff/' | xauth -f "$XAUTH_FILE" nmerge - 2>/dev/null || true
fi
xhost +SI:localuser:root >/dev/null 2>&1 || xhost +local:root >/dev/null 2>&1 || true

# Clean up any leftover containers
docker ps -q --filter "ancestor=autorace:humble" | xargs -r docker rm -f 2>/dev/null || true

echo "=========================================================="
echo " Starting TurtleBot3 AutoRace 2020 (Mode: ${COURSE_MODE})"
echo " Project : ${PROJECT_DIR}"
echo " Tasks included:"
echo "   1. Gazebo Simulation (turtlebot3_autorace_2020 world)"
echo "   2. Camera Pipeline (Intrinsic + Extrinsic Compensation)"
echo "   3. Lane Detection (with HUD Banner) & Traffic Light State"
echo "   4. Slow Sign Reading (3.0s pause + Yellow Box Overlay)"
echo "   5. Dynamic LiDAR Slalom + Mission (${COURSE_MODE}) + MP4 Recorder"
echo "=========================================================="

HOST_UID="$(id -u)"
HOST_GID="$(id -g)"

docker run -it --rm \
  --user 0:0 \
  --entrypoint /bin/bash \
  --net=host \
  --ipc=host \
  --privileged \
  -e HOME=/root \
  -e DISPLAY="${DISPLAY:-:0}" \
  -e XAUTHORITY="$XAUTH_FILE" \
  -e QT_X11_NO_MITSHM=1 \
  -e TURTLEBOT3_MODEL=burger_cam \
  -e COURSE_MODE="${COURSE_MODE}" \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v "${XAUTH_FILE}:${XAUTH_FILE}:ro" \
  -v /dev/dri:/dev/dri:rw \
  -v "${WS_DIR}:/root/ros2_humble_ws" \
  -v "${PROJECT_DIR}:/root/ros2_humble_ws/src/turtlebot3_autorace" \
  -v "${PROJECT_DIR}/scripts/run_tb3_race_tmux.sh:/root/ros2_humble_ws/run_tb3_race_tmux.sh" \
  -v "${PROJECT_DIR}/tools:/root/ros2_humble_ws/tools" \
  -w /root/ros2_humble_ws \
  autorace:humble \
  -c "trap 'chown -R ${HOST_UID}:${HOST_GID} /root/ros2_humble_ws /root/ros2_humble_ws/src/turtlebot3_autorace 2>/dev/null || true' EXIT; COURSE_MODE=${COURSE_MODE} bash /root/ros2_humble_ws/run_tb3_race_tmux.sh"
