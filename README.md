# TurtleBot3 AutoRace 2020 (ROS 2 Humble)

Autonomous driving pipeline for the **TurtleBot3 AutoRace 2020** course in Gazebo (ROS 2 Humble):
- **Traffic Light Recognition** (`RED` -> `YELLOW` -> `GREEN` start gate)
- **Bird's-Eye Lane Detection** with live **HUD Telemetry Banner** (`/detect/image_lane`)
- **SIFT + Homography Traffic Sign Detection** with a clean **Yellow Bounding Box Overlay** (`/detect/image_traffic_sign`) and a **3.0-second stationary reading pause** facing each sign
- **Precision Construction Barrier Slalom** with dynamic 2D LiDAR cluster verification
- **Two Mission Modes**:
  1. **Simulation 1 — Autonomous Parking (`./run_autorace_humble.sh`)**: Completes Traffic Light -> Intersection -> Right Sign -> Construction Sign & Barrier Slalom -> Parking Sign -> Parks in the top parking bay (`STATE=done:parked`).
  2. **Simulation 2 — Full 360° Course Loop (`./run_autorace_full_loop.sh`)**: Continues past the Parking Sign through the Top Chicane -> Stop Sign -> Moving Level-Crossing Bar -> S-Curve -> Tunnel Sign -> Dark Tunnel Obstacle Avoidance (`OBS1`–`OBS3`) -> Start/Finish Line (`STATE=done:lap-complete`).

> 📚 **New to ROS 2?** Read [**`BEGINNER_GUIDE.md`**](./BEGINNER_GUIDE.md) for a complete, step-by-step explanation from absolute zero.

---

## Quick Start

```bash
cd ~/dev/ros2_exmaple/turtlebot3_autorace

# Simulation 1: Ends parked in the top parking bay
./run_autorace_humble.sh

# Simulation 2: Completes the full 360-degree course loop through the level crossing & tunnel
./run_autorace_full_loop.sh
```

---

## Repository Structure

```text
turtlebot3_autorace/
├── BEGINNER_GUIDE.md                  # Zero-to-Hero ROS 2 & AutoRace walkthrough
├── README.md                          # Project overview & quick start
├── Dockerfile.humble                  # ROS 2 Humble + Gazebo + OpenCV Docker definition
├── run_autorace_humble.sh             # Launches Simulation 1 (Parking mode)
├── run_autorace_full_loop.sh          # Launches Simulation 2 (Full-Loop mode)
├── run_tb3_race_tmux.sh               # 5-window tmux pipeline inside Docker
├── tools/
│   ├── state_monitor.py               # Live terminal monitor for light, sign, and stage
│   └── verify_full_course.py          # Automated verification & headless regression test
├── turtlebot3_autorace/               # Metapackage definition
├── turtlebot3_autorace_camera/        # Intrinsic & extrinsic bird's-eye camera calibration
├── turtlebot3_autorace_detect/        # Lane, traffic light, and yellow-box sign detectors
└── turtlebot3_autorace_mission/       # Mission supervisor, lane controller, MP4 recorder, and course_2020.yaml
```
