# Quick Reference Notes & Feature Changelog

This document tracks all new tools, scripts, and educational modules added to make TurtleBot3 AutoRace 2020 100% self-contained and beginner-accessible.

---

## 🚀 Newly Added Learning & Defense Tools

### 1. Interactive Oral Defense Self-Quiz (`./run.sh quiz`)
- **What it is**: A randomized CLI self-quiz engine based on the questions from [`docs/STUDY_AND_ORAL_DEFENSE_GUIDE.md`](./docs/STUDY_AND_ORAL_DEFENSE_GUIDE.md).
- **Why it matters**: Tests your recall of ROS 2 concepts, computer vision mathematics, and obstacle avoidance logic before presentations or interviews.
- **How to run**:
  ```bash
  cd ~/dev/ros2_exmaple/turtlebot3_autorace
  ./run.sh quiz
  ```
- **Source Code**: [`tools/quiz_me.py`](./tools/quiz_me.py).

---

### 2. Animated Educational Demonstration Video
- **File**: [`docs/media/autorace_pipeline_animated.mp4`](./docs/media/autorace_pipeline_animated.mp4)
- **Features**:
  - Full 1080p, 30 FPS animated breakdown.
  - Stage 1: Traffic light ROI cropping & HSV Green thresholding.
  - Stage 2: Top-down bird's-eye polynomial lane tracking & SIFT clean yellow bounding box sign recognition.
  - Stage 3: LiDAR point cloud clustering, barrier dodging, and emergency HUD alerting.

---

### 3. High-Resolution Reference Diagrams
- **Ground Truth Task Map**: [`docs/media/track_task_map.png`](./docs/media/track_task_map.png) — Cartesian world coordinates `(x, y)` for all track POIs.
- **Traffic Signs Overview**: [`docs/media/traffic_signs_overview.png`](./docs/media/traffic_signs_overview.png) — Template sign matrix with clean yellow bounding boxes.

---

### 4. Interactive Jupyter Perception Playground
- **File**: [`notebooks/perception_walkthrough.ipynb`](./notebooks/perception_walkthrough.ipynb)
- **Features**:
  - Step-by-step OpenCV code cells for testing HSV filters, homography matrices, and Pure Pursuit math without starting Gazebo or Docker.

---

### 5. Automated Docker Cleanup
- **Command**: `./run.sh clean-docker`
- **Action**: Clears dangling builder caches and intermediate layers to maintain disk space.

---

### 6. VS Code / Cursor DevContainer Support
- **File**: [`.devcontainer/devcontainer.json`](./.devcontainer/devcontainer.json)
- **Action**: One-click opening into the isolated ROS 2 Humble container with all ROS and Python extensions pre-configured.
