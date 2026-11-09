# TurtleBot3 AutoRace 2020: Comprehensive Oral Defense & Q&A Study Guide

This document prepares you for **any technical question or interview inquiry** about the AutoRace autonomous driving project, written in plain English with rigorous engineering depth.

---

## 📑 Quick Navigation
1. [Core High-Level System Architecture](#1-core-high-level-system-architecture)
2. [Visual Media & Assets Created for Demonstrations](#2-visual-media--assets-created-for-demonstrations)
3. [Top 20 Technical Q&A for Oral Examinations & Interviews](#3-top-20-technical-qa-for-oral-examinations--interviews)
4. [Mathematical Cheat Sheet](#4-mathematical-cheat-sheet)

---

## 1. Core High-Level System Architecture

```text
               +---------------------------------------+
               |         Gazebo 3D Simulator           |
               | (World: turtlebot3_autorace_2020.world|
               +---------------------------------------+
                 |                 |                 |
     /camera/image_raw      /odom (Odometry)    /scan (2D LiDAR)
                 |                 |                 |
                 v                 |                 |
    +-------------------------+    |                 |
    | Camera Calibration Node |    |                 |
    | (Intrinsic & Extrinsic) |    |                 |
    +-------------------------+    |                 |
        |                 |        |                 |
 /camera/image_projected  |        |                 |
   (Bird's-Eye View)      |        |                 |
        |      /camera/image_compensated            |
        v                 v        |                 |
 +-------------+   +-------------+ |                 |
 | detect_lane |   | detect_sign | |                 |
 +-------------+   +-------------+ |                 |
        |                 |        |                 |
  /detect/lane   /detect/traffic_sign                |
        |                 |        |                 |
        +--------+--------+        |                 |
                 |                 |                 |
                 v                 v                 v
        +-----------------------------------------------+
        |              mission_supervisor               |
        |     (Finite State Machine & Pure Pursuit)     |
        +-----------------------------------------------+
                               |
                           /cmd_vel
                               |
                               v
               +-------------------------------+
               |    Robot Differential Drive   |
               | (Linear & Angular Velocities) |
               +-------------------------------+
```

---

## 2. Visual Media & Assets Created for Demonstrations

All media assets are stored inside [`docs/media/`](file:///home/steve/dev/ros2_exmaple/turtlebot3_autorace/docs/media):

1. **[`docs/media/track_task_map.png`](file:///home/steve/dev/ros2_exmaple/turtlebot3_autorace/docs/media/track_task_map.png)**:
   - High-resolution, dark-mode 2D map showing every ground-truth asset coordinate `(x, y)`:
     - Start Gate `(0.80, -1.75)`
     - Traffic Light `(1.30, -1.95)`
     - Intersection Sign `(1.95, -1.00)`
     - Right Turn Sign `(1.08, -0.73)`
     - Construction Barriers `(1.49, 0.54)` to `(1.49, 1.44)`
     - Parking Stall `(0.25, 0.75)`
     - Level Crossing Stop Bar `(-0.80, 1.26)`
     - Dark Tunnel Entrance `(-1.54, 0.00)`
2. **[`docs/media/traffic_signs_overview.png`](file:///home/steve/dev/ros2_exmaple/turtlebot3_autorace/docs/media/traffic_signs_overview.png)**:
   - Visual grid of the 6 core AutoRace traffic sign templates with clean yellow bounding boxes.
3. **[`docs/media/autorace_pipeline_animated.mp4`](file:///home/steve/dev/ros2_exmaple/turtlebot3_autorace/docs/media/autorace_pipeline_animated.mp4)**:
   - A 12-second animated HD demonstration video (30 FPS) visualizing:
     - Stage 1: Traffic light ROI cropping, green thresholding, and start launch.
     - Stage 2: Bird's-eye lane polynomial tracking, SIFT feature matching, and yellow bounding box display.
     - Stage 3: LiDAR 360° point cloud clustering, barrier dodging, and emergency HUD alerting.
4. **[`notebooks/perception_walkthrough.ipynb`](file:///home/steve/dev/ros2_exmaple/turtlebot3_autorace/notebooks/perception_walkthrough.ipynb)**:
   - Standalone Jupyter Notebook to run and visualize HSV color masking, SIFT+RANSAC homography, and Pure Pursuit math cell-by-cell.

---

## 3. Top 20 Technical Q&A for Oral Examinations & Interviews

### Category 1: ROS 2 & System Fundamentals

#### Q1: What is the difference between ROS 1 and ROS 2?
> **Answer**: ROS 1 relied on a centralized `roscore` master process; if `roscore` crashed, all communications failed. ROS 2 is built on DDS (Data Distribution Service), an industry-standard decentralized protocol that discovers nodes peer-to-peer with zero central master, provides deterministic real-time communication, and supports native multi-robot security.

#### Q2: What is the ROS 2 message type published on `/cmd_vel`?
> **Answer**: `geometry_msgs/msg/Twist`. It contains two 3D vectors:
> - `linear`: `(x, y, z)` in m/s (we only drive forward/backward on `linear.x`).
> - `angular`: `(x, y, z)` in rad/s (we only rotate about the vertical yaw axis on `angular.z`).

#### Q3: Why does our supervisor publish `/cmd_vel` rather than the individual lane or sign detector nodes?
> **Answer**: This follows the **Single-Writer Principle**. If multiple nodes publish competing motor commands on `/cmd_vel`, the robot wheels stutter and shake violently. The `mission_supervisor` acts as the single arbitrator that blends camera lane tracking with waypoint guidance, sign holding pauses, and obstacle avoidance into one clean command stream.

#### Q4: Why is Docker used instead of running ROS 2 natively on the host OS?
> **Answer**: AutoRace 2020 relies on Gazebo Classic 11 plugins, which are native to ROS 2 Humble on Ubuntu 22.04 (Jammy). On modern Linux distributions (such as Ubuntu 24.04 Noble running ROS 2 Jazzy), Gazebo Classic is deprecated. The Docker container (`autorace:humble`) provides a 100% reproducible, isolated environment that forwards GUI windows via the host X11 display.

---

### Category 2: Computer Vision & Perception

#### Q5: What is Inverse Perspective Mapping (IPM)?
> **Answer**: IPM applies a geometric homography transformation matrix to warp the front-facing perspective camera frame into an orthographic "bird's-eye view" (top-down). In perspective view, parallel lane lines appear to converge at a vanishing point. In IPM, parallel lane lines remain strictly parallel, allowing accurate polynomial curve fitting.

#### Q6: Why do we use HSV color space instead of RGB for lane detection?
> **Answer**: In RGB, a change in lighting (shadows, glares, daylight variations) simultaneously alters Red, Green, and Blue values. In HSV (Hue, Saturation, Value), color type (**Hue**) is decoupled from brightness (**Value**). This makes color filtering of yellow lanes ($H \in [18, 38]$) and white lanes robust against lighting changes.

#### Q7: How does SIFT feature matching work for traffic signs?
> **Answer**: 
> 1. SIFT (Scale-Invariant Feature Transform) detects distinctive scale-space extrema (corners and blobs) that are invariant to rotation, scaling, and illumination.
> 2. Each keypoint is encoded as a 128-dimensional descriptor vector.
> 3. FLANN matches descriptors between the template image and the camera frame using nearest-neighbor search ($k=2$).
> 4. Lowe's Ratio Test ($d_1 < 0.78 \cdot d_2$) rejects ambiguous background matches.

#### Q8: Why do we calculate a Homography matrix with RANSAC?
> **Answer**: Even after Lowe's ratio test, outliers exist. RANSAC (Random Sample Consensus) randomly selects minimal subsets of 4 matching points, calculates a candidate homography transformation $M$, and counts the number of inliers. The optimal homography matrix $M$ accurately projects the 4 physical corners of the template sign into the live camera frame, enabling us to draw a precise bounding box.

#### Q9: How did you ensure only a clean yellow bounding box is displayed without cluttered dots and lines?
> **Answer**: In `detect_intersection_sign.py`, instead of calling `cv2.drawMatches()` (which draws messy colored lines and internal dot clusters across the whole image), we pass the 4 corners of the template sign through `cv2.perspectiveTransform(corners, M)` and draw **only** the outer polygon border using `cv2.polylines(box, isClosed=True, color=(0, 255, 255), thickness=3)`.

---

### Category 3: LiDAR & Obstacle Navigation

#### Q10: What sensor message does the 360° LiDAR publish?
> **Answer**: `sensor_msgs/msg/LaserScan`. Key fields include:
> - `angle_min`, `angle_max`: Angular sweep bounds ($-\pi$ to $+\pi$).
> - `angle_increment`: Angular resolution between consecutive laser beams.
> - `ranges`: Floating-point array of measured distances in meters.

#### Q11: How do you convert a 1D polar LiDAR reading into 2D Cartesian world coordinates $(x, y)$?
> **Answer**:
> For beam index $i$ with range $r$:
> 1. Beam relative angle: $\alpha = \text{angle\_min} + i \cdot \text{angle\_increment}$.
> 2. Beam global heading: $\psi = \theta_{\text{robot}} + \alpha$.
> 3. Global obstacle position:
>    $$x_{\text{obs}} = x_{\text{robot}} + r \cos(\psi)$$
>    $$y_{\text{obs}} = y_{\text{robot}} + r \sin(\psi)$$

#### Q12: How does the robot slalom between the 3 construction barriers?
> **Answer**: The 3 construction barriers are located in the East corridor at $y = 0.54\text{m}$, $1.00\text{m}$, and $1.44\text{m}$. By clustering LiDAR returns in the forward cone, the supervisor checks whether an obstacle occupies the current lane corridor. If an obstacle is on the right, it shifts the target centerline to $x = 1.77\text{m}$; if on the left, it shifts to $x = 1.47\text{m}$, generating a smooth S-curve trajectory.

#### Q13: How does the robot handle the moving Level-Crossing barrier?
> **Answer**: At $x \approx -0.80, y \approx 1.26$, the supervisor evaluates the narrow forward cone ($\pm 15^\circ$). If the nearest distance is $< 0.45\text{m}$, the wooden gate is down, and the robot commands linear speed $v = 0.0\text{ m/s}$. When the barrier arm raises, the range exceeds $0.80\text{m}$ for 3 consecutive frames, and the robot proceeds through the crossing.

---

### Category 4: Motion Control & Waypoint Guidance

#### Q14: What is Pure Pursuit control?
> **Answer**: Pure Pursuit is a geometric path-tracking algorithm. It calculates the curvature $\kappa$ required to steer the robot from its current position to a designated "lookahead" waypoint $(g_x, g_y)$ on the path:
> $$\kappa = \frac{2 \sin(\alpha)}{L_d}, \quad \omega = v \cdot \kappa$$
> where $\alpha$ is the angular error to the target, $L_d$ is the lookahead distance, and $v$ is the linear driving velocity.

#### Q15: How does the robot convert Quaternions from `/odom` into a usable steering heading?
> **Answer**: Odometry orientation is given as Quaternion $(q_x, q_y, q_z, q_w)$. We compute the 2D Euler Yaw angle ($\theta$) via:
> $$\theta = \text{atan2}(2(q_w q_z + q_x q_y), 1 - 2(q_y^2 + q_z^2))$$

#### Q16: How do you prevent angle wrap-around discontinuities (e.g., from $+\pi$ to $-\pi$)?
> **Answer**: We use the standard angle normalization function:
> ```python
> def wrap_angle(angle):
>     return math.atan2(math.sin(angle), math.cos(angle))
> ```
> This ensures heading errors always take the shortest angular path within $[-\pi, +\pi]$.

---

### Category 5: Practical Workflow & Reproduction

#### Q17: What happens when you execute `./run.sh parking`?
> **Answer**: It invokes `scripts/run_autorace_humble.sh`, which starts the `autorace:humble` Docker container with X11 display and host network passthrough. Inside, a `tmux` session orchestrates:
> - Pane 0: Gazebo simulation + world spawn.
> - Pane 1: Camera intrinsic distortion rectification & bird's-eye projection.
> - Pane 2: Computer vision detectors (traffic light, lane tracking, sign detector).
> - Pane 3: `mission_supervisor` node.
> - Pane 4: RQt visualization dashboards.

#### Q18: What happens when you execute `./run.sh verify`?
> **Answer**: It launches Gazebo headlessly (`gui:=false`) and runs `tools/verify_full_course.py`. The monitor listens to `/mission/state` and `/odom` and asserts completion of the course within 150 seconds, exiting with status code `0` on success or non-zero on failure.

#### Q19: Where are velocity limits and sign pause durations configured?
> **Answer**: Centralized in [`turtlebot3_autorace_mission/param/course_2020.yaml`](file:///home/steve/dev/ros2_exmaple/turtlebot3_autorace/turtlebot3_autorace_mission/param/course_2020.yaml). Parameters can be modified directly without recompiling packages.

#### Q20: How do you clean up dangling Docker build caches?
> **Answer**: Run `./run.sh clean-docker`, which executes `docker image prune -f` and `docker builder prune -f`, reclaiming multiple gigabytes of disk space safely.

---

## 4. Mathematical Cheat Sheet

| Formula | Mathematical Representation | Code Implementation |
| :--- | :--- | :--- |
| **Euler Yaw from Quaternion** | $\theta = \text{atan2}(2(wz + xy), 1 - 2(y^2 + z^2))$ | `math.atan2(2*(w*z + x*y), 1 - 2*(y**2 + z**2))` |
| **Lowe's Ratio Test** | $d_1 < 0.78 \cdot d_2$ | `[m for m, n in matches if m.distance < 0.78 * n.distance]` |
| **2nd-Order Polynomial Lane** | $x(y) = A y^2 + B y + C$ | `np.polyfit(y_vals, x_vals, 2)` |
| **PD Steering Controller** | $\omega = -K_p \cdot e - K_d \cdot \frac{de}{dt}$ | `w = -Kp * error - Kd * (error - prev_error) / dt` |
| **Pure Pursuit Curvature** | $\kappa = \frac{2 \sin(\alpha)}{L_d}$ | `kappa = 2.0 * math.sin(alpha) / lookahead_dist` |
| **Angular Velocity Command** | $\omega = v \cdot \kappa$ | `cmd_vel.angular.z = cmd_vel.linear.x * kappa` |
