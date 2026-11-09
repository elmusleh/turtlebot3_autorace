import cv2
import numpy as np

width, height = 1280, 720
fps = 30
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out_path = '/home/steve/dev/ros2_exmaple/turtlebot3_autorace/docs/media/autorace_pipeline_animated.mp4'
writer = cv2.VideoWriter(out_path, fourcc, fps, (width, height))

# Load sign templates
tmpl_dir = '/home/steve/dev/ros2_exmaple/turtlebot3_autorace/turtlebot3_autorace_detect/image/'
inter_sign = cv2.imread(f"{tmpl_dir}/intersection.png")
if inter_sign is not None:
    inter_sign = cv2.resize(inter_sign, (140, 140))

# 3 stages:
# Stage 1: Traffic Light & Launch (0 - 4s)
# Stage 2: Lane Detection & SIFT Yellow Bounding Box (4 - 8s)
# Stage 3: LiDAR Barrier Slalom & Level Crossing (8 - 12s)

total_frames = fps * 12

for f in range(total_frames):
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:] = (18, 20, 24)
    t = f / fps

    # Top Brand Header
    cv2.rectangle(frame, (0, 0), (width, 80), (12, 14, 18), -1)
    cv2.putText(frame, "TurtleBot3 AutoRace 2020: Autonomous Pipeline Walkthrough", (40, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1.05, (255, 255, 255), 2, cv2.LINE_AA)

    # Subtitle with time
    cv2.putText(frame, f"Time: {t:.1f}s | ROS 2 Humble Architecture", (width - 380, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (140, 160, 180), 1, cv2.LINE_AA)

    if t < 4.0:
        # STAGE 1: Traffic Light
        progress = t / 4.0
        light_color = (0, 230, 80) if t > 2.0 else (0, 0, 240)
        light_state = "GREEN (LAUNCH!)" if t > 2.0 else "RED (HOLD AT START)"
        
        cv2.putText(frame, "STAGE 1: Traffic Light Detection (/detect/traffic_light_state)", (60, 140),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 255, 255), 2, cv2.LINE_AA)
        
        # Draw Traffic Light Housing
        cv2.rectangle(frame, (100, 180), (220, 480), (30, 30, 30), -1)
        cv2.circle(frame, (160, 240), 38, (0, 0, 255) if t <= 2.0 else (0, 0, 80), -1)
        cv2.circle(frame, (160, 330), 38, (0, 60, 60), -1)
        cv2.circle(frame, (160, 420), 38, (0, 255, 0) if t > 2.0 else (0, 80, 0), -1)

        # Draw Robot at Start
        rx = int(350 + (t - 2.0) * 180) if t > 2.0 else 350
        cv2.rectangle(frame, (rx - 40, 320), (rx + 40, 400), (0, 140, 255), -1)
        cv2.putText(frame, "TurtleBot3", (rx - 38, 365), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        
        # Telemetry panel
        cv2.rectangle(frame, (600, 180), (1200, 480), (28, 32, 40), -1)
        cv2.putText(frame, f"Traffic Light Status: {light_state}", (630, 230),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, light_color, 2)
        cv2.putText(frame, "Camera ROI: Upper-Right [y: 20:180, x: 220:320]", (630, 280),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 200, 200), 1)
        cv2.putText(frame, "HSV Filter: Green Hue [35, 85], Sat [70, 255]", (630, 325),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 200, 200), 1)
        cv2.putText(frame, f"Robot Linear Speed: {'0.10 m/s' if t > 2.0 else '0.00 m/s'}", (630, 375),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)
        cv2.putText(frame, "Latched State: " + ("UNLOCKED (Running)" if t > 2.0 else "LOCKED (Waiting)"), (630, 425),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.70, light_color, 2)

    elif t < 8.0:
        # STAGE 2: Sign Detection & Lane Tracking
        cv2.putText(frame, "STAGE 2: Lane Following (PD) + SIFT Sign Recognition", (60, 140),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 255, 255), 2, cv2.LINE_AA)

        # Draw Bird's Eye View Lane Simulation
        cv2.rectangle(frame, (80, 180), (520, 580), (10, 14, 18), -1)
        # Yellow left line
        cv2.line(frame, (160, 180), (140, 580), (0, 230, 255), 6)
        # White right line
        cv2.line(frame, (440, 180), (460, 580), (255, 255, 255), 6)
        # Center polynomial target
        cv2.line(frame, (300, 180), (300, 580), (0, 255, 120), 2)
        cv2.putText(frame, "Bird's-Eye View (IPM)", (100, 215), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 1)

        # Draw Traffic Sign with Clean Yellow Bounding Box
        if inter_sign is not None:
            frame[240:380, 620:760] = inter_sign
            # Yellow box
            cv2.rectangle(frame, (615, 235), (765, 385), (0, 255, 255), 3)
            cv2.putText(frame, "INTERSECTION", (620, 225), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)

        # Explanation box
        cv2.rectangle(frame, (800, 180), (1220, 580), (28, 32, 40), -1)
        cv2.putText(frame, "Perception Details:", (830, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
        cv2.putText(frame, "* SIFT Keypoints: 120 extracted", (830, 265), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (200, 200, 200), 1)
        cv2.putText(frame, "* FLANN Matcher: k-NN (k=2)", (830, 305), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (200, 200, 200), 1)
        cv2.putText(frame, "* Lowe's Ratio Test: d1 < 0.78 * d2", (830, 345), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (200, 200, 200), 1)
        cv2.putText(frame, "* RANSAC Homography: Inliers >= 12", (830, 385), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (200, 200, 200), 1)
        cv2.putText(frame, "* Clean Yellow Box: (0, 255, 255)", (830, 425), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
        cv2.putText(frame, "* State: sign:reading:intersection", (830, 475), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
        cv2.putText(frame, "* Pause: 3.0s stationary hold", (830, 515), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 140), 2)

    else:
        # STAGE 3: LiDAR Obstacle Avoidance & Slalom
        cv2.putText(frame, "STAGE 3: LiDAR Barrier Avoidance & 3D Obstacle Clustering", (60, 140),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 255, 255), 2, cv2.LINE_AA)

        # Draw 2D LiDAR Polar Map
        center = (300, 380)
        cv2.circle(frame, center, 160, (40, 45, 55), 2)
        cv2.circle(frame, center, 100, (40, 45, 55), 2)
        cv2.circle(frame, center, 40, (40, 45, 55), 2)
        cv2.circle(frame, center, 8, (0, 255, 120), -1)  # Robot

        # Draw simulated obstacle clusters
        barrier_angle = -0.3 + 0.1 * np.sin(t * 3)
        ox = int(center[0] + 110 * np.sin(barrier_angle))
        oy = int(center[1] - 110 * np.cos(barrier_angle))
        cv2.circle(frame, (ox, oy), 16, (0, 80, 255), -1)
        cv2.putText(frame, "Barrier 1 (0.54m)", (ox + 18, oy + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 80, 255), 2)

        # Explanation box
        cv2.rectangle(frame, (620, 180), (1220, 580), (28, 32, 40), -1)
        cv2.putText(frame, "Dynamic Obstacle Handling:", (650, 225), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
        cv2.putText(frame, "* /scan Sensor: 360-deg 2D LaserScanner", (650, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 200, 200), 1)
        cv2.putText(frame, "* Front Cone: -30 deg to +30 deg ROI", (650, 315), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 200, 200), 1)
        cv2.putText(frame, "* Sub-Lane Shifting: x = 1.77m <-> 1.47m", (650, 360), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
        cv2.putText(frame, "* RViz Topic: /mission/obstacle_markers", (650, 405), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
        cv2.putText(frame, "* HUD Warning: Orange text if dist < 0.35m", (650, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 80, 255), 2)
        cv2.putText(frame, "* Pure Pursuit Controller: w = v * (2*sin(a) / Ld)", (650, 500), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 140), 2)

    # Global Bottom Telemetry Footer
    cv2.rectangle(frame, (0, height - 55), (width, height), (12, 14, 18), -1)
    status_text = "STAGE: avoid:barrier_1 | SPEED: 0.08 m/s | LIDAR: 0.38 m" if t > 8 else (
        "STAGE: sign:reading:intersection | SPEED: 0.00 m/s | LIDAR: 0.82 m" if t > 4 else
        "STAGE: start:traffic_light | SPEED: 0.00 m/s | LIDAR: 1.25 m"
    )
    cv2.putText(frame, status_text, (40, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA)

    writer.write(frame)

writer.release()
print("Saved /home/steve/dev/ros2_exmaple/turtlebot3_autorace/docs/media/autorace_pipeline_animated.mp4")
