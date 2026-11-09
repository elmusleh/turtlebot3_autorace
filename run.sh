#!/usr/bin/env bash
# ==============================================================================
# run.sh — Unified CLI for TurtleBot3 AutoRace 2020
#
# Provides high-level commands for both:
#   1. ROS 2 Humble AutoRace (Docker-based Gazebo Classic simulation & course)
#   2. Local host utilities (build, test, status, stop, clean)
# ==============================================================================

set +u
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="${AUTORACE_WS:-${REPO_DIR}/ros2_humble_ws}"
DOMAIN_ID="${ROS_DOMAIN_ID:-70}"

usage() {
  cat <<EOF
TurtleBot3 AutoRace CLI

Usage: ./run.sh <command> [args]

Main Simulation Commands:
  parking         Launch Simulation 1: Traffic Light -> Lane -> Sign Pause -> Slalom -> Parking
  full-loop       Launch Simulation 2: Full 360° course through Level Crossing & Tunnel
  verify          Run automated course verification / regression monitor (optional: --headless)
  quiz            Run interactive oral defense & Q&A self-quiz CLI
  status          Show nodes/topics currently active
  stop            Stop and clean up all running simulation processes & containers
  clean-docker    Prune dangling Docker images and builder cache

Humble Docker Subcommands:
  humble build    Rebuild the workspace inside the Humble container
  humble bash     Open an interactive bash shell in the Humble container
  humble test     Run headless verification test inside container
  humble run <cmd> Run any custom ROS 2 command inside the container

Development / Local Commands:
  build           Build local workspace with colcon
  help            Show this help menu

Examples:
  ./run.sh parking
  ./run.sh full-loop
  ./run.sh verify
  ./run.sh humble bash
  ./run.sh stop
EOF
}

cmd_parking() {
  echo "== Launching Simulation 1: Parking Mode =="
  COURSE_MODE=parking "${REPO_DIR}/scripts/run_autorace_humble.sh" "$@"
}

cmd_full_loop() {
  echo "== Launching Simulation 2: Full Course Loop =="
  "${REPO_DIR}/scripts/run_autorace_full_loop.sh" "$@"
}

cmd_verify() {
  local cid
  cid=$(docker ps -q --filter ancestor=autorace:humble | head -n1)
  if [ -z "$cid" ]; then
    echo "No running autorace:humble container found. Starting verification..."
    python3 "${REPO_DIR}/tools/verify_full_course.py" "$@"
  else
    echo "Running verification inside active container $cid..."
    docker exec -it "$cid" bash -c "source /opt/ros/humble/setup.bash && source /root/ros2_humble_ws/install/setup.bash && python3 /root/ros2_humble_ws/tools/verify_full_course.py $*"
  fi
}

cmd_humble() {
  local subcmd="${1:-bash}"
  shift || true

  local docker_run_args=(
    --rm
    --net=host
    --ipc=host
    --privileged
    -e DISPLAY="${DISPLAY:-:0}"
    -e QT_X11_NO_MITSHM=1
    -e TURTLEBOT3_MODEL="${TURTLEBOT3_MODEL:-burger_cam}"
    -e ROS_DOMAIN_ID="${DOMAIN_ID}"
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw
    -v /dev/dri:/dev/dri:rw
    -v "${WS_DIR}:/root/ros2_humble_ws"
    -v "${REPO_DIR}:/root/ros2_humble_ws/src/turtlebot3_autorace"
    -w /root/ros2_humble_ws
  )

  case "$subcmd" in
    build)
      docker run "${docker_run_args[@]}" autorace:humble \
        /bin/bash -c "source /opt/ros/humble/setup.bash && cd /root/ros2_humble_ws && colcon build --symlink-install --packages-select turtlebot3_autorace_camera turtlebot3_autorace_detect turtlebot3_autorace_mission"
      ;;
    bash)
      docker run -it "${docker_run_args[@]}" autorace:humble \
        /bin/bash -c "source /opt/ros/humble/setup.bash; [ -f /root/ros2_humble_ws/install/setup.bash ] && source /root/ros2_humble_ws/install/setup.bash; exec bash"
      ;;
    test)
      docker run -it "${docker_run_args[@]}" autorace:humble \
        /bin/bash -c "source /opt/ros/humble/setup.bash && source /root/ros2_humble_ws/install/setup.bash && python3 /root/ros2_humble_ws/tools/verify_full_course.py 240"
      ;;
    run)
      docker run -it "${docker_run_args[@]}" autorace:humble \
        /bin/bash -c "source /opt/ros/humble/setup.bash; [ -f /root/ros2_humble_ws/install/setup.bash ] && source /root/ros2_humble_ws/install/setup.bash; $*"
      ;;
    *)
      echo "Unknown humble subcommand: $subcmd"
      echo "Usage: ./run.sh humble [build|bash|test|run <cmd>]"
      return 1
      ;;
  esac
}

cmd_status() {
  local cid
  cid=$(docker ps -q --filter ancestor=autorace:humble | head -n1)
  if [ -n "$cid" ]; then
    echo "== Active Container: $cid =="
    docker exec "$cid" bash -c "source /opt/ros/humble/setup.bash; echo '--- ROS 2 Nodes ---'; ros2 node list 2>/dev/null; echo '--- Key Topics ---'; ros2 topic list 2>/dev/null | grep -E 'odom|scan|image|cmd_vel|state|sign|lane'"
  else
    echo "No container running. Checking host ROS..."
    if command -v ros2 >/dev/null 2>&1; then
      echo "== Nodes =="
      ros2 node list 2>/dev/null || echo "(none)"
      echo "== Key topics =="
      ros2 topic list 2>/dev/null | grep -E "odom|scan|image_raw|cmd_vel" || echo "(none)"
    else
      echo "ROS 2 not active on host."
    fi
  fi
}

cmd_stop() {
  echo "== Stopping all AutoRace simulations & processes =="
  docker ps -q --filter ancestor=autorace:humble | xargs -r docker rm -f 2>/dev/null || true
  tmux kill-session -t race 2>/dev/null || true
  tmux kill-session -t autorace 2>/dev/null || true
  pkill -9 -f "gzserver" 2>/dev/null || true
  pkill -9 -f "gzclient" 2>/dev/null || true
  pkill -9 -f "gz sim" 2>/dev/null || true
  echo "Stopped."
}

cmd_clean_docker() {
  echo "== Pruning dangling Docker images and build cache =="
  docker image prune -f
  docker builder prune -f 2>/dev/null || true
  echo "Docker clean complete."
}

cmd_quiz() {
  python3 "${REPO_DIR}/tools/quiz_me.py"
}

cmd_build() {
  cmd_humble build
}

case "${1:-help}" in
  parking|sim-parking) shift; cmd_parking "$@" ;;
  full-loop|loop|sim-loop) shift; cmd_full_loop "$@" ;;
  verify) shift; cmd_verify "$@" ;;
  quiz) shift; cmd_quiz "$@" ;;
  humble) shift; cmd_humble "$@" ;;
  build) shift; cmd_build "$@" ;;
  status) cmd_status ;;
  clean-docker) cmd_clean_docker ;;
  stop) cmd_stop ;;
  help|--help|-h) usage ;;
  *) echo "Unknown command: $1"; usage; exit 1 ;;
esac
