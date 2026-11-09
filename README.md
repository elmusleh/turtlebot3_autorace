# TurtleBot3 AutoRace 2020 (ROS 2 Humble)

[![ROS 2 Humble CI](https://github.com/elmusleh/turtlebot3_autorace/actions/workflows/ros2_ci.yml/badge.svg)](https://github.com/elmusleh/turtlebot3_autorace/actions/workflows/ros2_ci.yml)
[![ROS 2 Humble](https://img.shields.io/badge/ROS_2-Humble-3498DB.svg)](https://docs.ros.org/en/humble/)
[![Gazebo Classic](https://img.shields.io/badge/Simulator-Gazebo_11-FF6F00.svg)](https://gazebosim.org/)
[![License](https://img.shields.io/badge/License-Apache_2.0-green.svg)](./LICENSE)

A complete, production-grade autonomous driving pipeline for the **TurtleBot3 AutoRace 2020** track in Gazebo Classic (ROS 2 Humble), built for deterministic performance and reproducible demonstrations.

---

## 🌟 Key Features

1. **Traffic Light Start Gate**
   - HSV color-mask detection (`RED` -> `YELLOW` -> `GREEN`).
   - Starts moving only when green is triggered.
2. **Bird's-Eye Lane Tracking & HUD Telemetry**
   - Inverse perspective mapping (bird's-eye projection).
   - Real-time HUD banner rendered on `/detect/image_lane`:
     `STAGE: <state> | SPEED: <m/s> | LIDAR: <m>`
3. **Yellow-Box Traffic Sign Recognition with Stationary Pauses**
   - Unified SIFT + RANSAC homography across **all 7 AutoRace signs** (`intersection`, `left`, `right`, `construction`, `parking`, `stop`, `tunnel`).
   - Draws **only a clean yellow bounding box (`(0, 255, 255)`)** and sign name label on `/detect/image_traffic_sign`.
   - Robot approaches at `0.05 m/s`, aligns camera heading directly at the sign, and pauses completely stationary for **3.0 seconds** so visual detection is crystal clear.
4. **Dynamic LiDAR Construction Barrier Slalom**
   - Navigates the staggered 3-barrier slalom corridor.
   - 2D LiDAR cluster projection dynamically checks the corridor and shifts target lanes if barrier positions change.
5. **Two Full Simulation Modes**
   - **Simulation 1 (Parking)**: Completes Start -> Intersection -> Slalom -> Autonomous Parking in top bay (`STATE=done:parked`).
   - **Simulation 2 (Full Loop)**: Completes the full 360° circuit through the top chicane, stop sign, moving level-crossing barrier, S-curve, dark tunnel (dodging 3 cylinders), back to the start line (`STATE=done:lap-complete`).
6. **Built-in MP4 Video Recording**
   - Automatically records side-by-side lane + sign detection into `demo_recording.mp4`.

---

## 🚀 Quick Start

All operations are controlled via the root CLI script [`./run.sh`](./run.sh):

```bash
cd ~/dev/ros2_exmaple/turtlebot3_autorace

# 1. Run Simulation 1: Parking Mission
./run.sh parking

# 2. Run Simulation 2: Full 360° Course Loop
./run.sh full-loop

# 3. Check Live Robot State & Topics
./run.sh status

# 4. Stop Simulation & Clean up Containers
./run.sh stop
```

---

## 📁 Repository Structure

```text
turtlebot3_autorace/
├── BEGINNER_GUIDE.md             # Complete Zero-to-Hero educational guide
├── README.md                     # This file
├── run.sh                        # Unified executable CLI launcher
├── Dockerfile.humble             # Docker container definition (Ubuntu 22.04 + ROS 2 Humble)
├── scripts/                      # Runner & tmux pipeline scripts
│   ├── run_autorace_humble.sh    # Simulation 1 (Parking mode)
│   ├── run_autorace_full_loop.sh # Simulation 2 (Full-Loop mode)
│   └── run_tb3_race_tmux.sh      # 5-window tmux orchestrator inside Docker
├── tools/                        # Verification & monitoring utilities
│   ├── state_monitor.py          # Real-time terminal state logger
│   └── verify_full_course.py     # Automated CI verification runner (supports --headless)
├── turtlebot3_autorace/          # Metapackage index
├── turtlebot3_autorace_camera/   # Intrinsic lens rectification & extrinsic bird's-eye projection
├── turtlebot3_autorace_detect/   # Lane detection (with HUD), traffic light, & sign detectors
└── turtlebot3_autorace_mission/  # Mission supervisor, course_2020.yaml, & MP4 recorder
```

---

## 🛠️ CLI Command Reference (`./run.sh`)

| Command | Action |
| :--- | :--- |
| `./run.sh parking` | Starts Simulation 1 (Parking Mission) in Gazebo + RQt views |
| `./run.sh full-loop` | Starts Simulation 2 (Full Loop) through Level Crossing & Tunnel |
| `./run.sh verify` | Runs automated verification on active simulation |
| `./run.sh verify --headless` | Launches headless simulation and validates 0 collisions & completion |
| `./run.sh status` | Displays active ROS 2 nodes and key topics |
| `./run.sh stop` | Kills tmux sessions and removes Docker simulation containers |
| `./run.sh humble bash` | Enters an interactive bash shell in the ROS 2 Humble container |
| `./run.sh humble build` | Builds all packages via `colcon build` in container |
| `./run.sh humble test` | Runs containerized test verification |

---

## ⚙️ Customization & Parameters

All track geometry, speeds, and pause times are defined in:
[`turtlebot3_autorace_mission/param/course_2020.yaml`](./turtlebot3_autorace_mission/param/course_2020.yaml)

- **Change sign reading pause time**:
  ```yaml
  sign_stop_seconds: 3.0   # Adjust to 4.0 or 5.0 for longer demonstrations
  ```
- **Change continuous laps**:
  ```yaml
  loop_forever: true       # Robot runs infinite laps around the track
  ```
- **Change driving speeds**:
  Edit `speed: 0.12` on any individual waypoint.

After editing `course_2020.yaml`:
```bash
./run.sh humble build
```

---

## 📖 In-Depth Beginner Guide

For an exhaustive explanation of how ROS 2 nodes, topics, camera transformations, and computer vision work under the hood, read [**`BEGINNER_GUIDE.md`**](./BEGINNER_GUIDE.md).
