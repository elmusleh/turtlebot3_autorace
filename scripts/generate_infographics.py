import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

plt.style.use('dark_background')

# ==============================================================================
# FIGURE 1: Full System Architecture & Data Flow Diagram
# ==============================================================================
fig, ax = plt.subplots(figsize=(16, 9), dpi=200)
ax.set_facecolor('#0f1218')
fig.patch.set_facecolor('#0a0c10')

# Title
ax.text(0.5, 0.96, "TurtleBot3 AutoRace 2020: Autonomous System Architecture", 
        fontsize=20, weight='bold', color='#ffffff', ha='center', va='center')
ax.text(0.5, 0.92, "ROS 2 Humble Middleware | Distributed Sensor Processing to Central Single-Writer Arbitration", 
        fontsize=12, color='#00d4ff', ha='center', va='center')

def draw_block(ax, x, y, w, h, title, subtitle, bg_col, edge_col):
    box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.03",
                                facecolor=bg_col, edgecolor=edge_col, linewidth=2)
    ax.add_patch(box)
    ax.text(x + w/2, y + h*0.65, title, fontsize=12, weight='bold', color='#ffffff', ha='center', va='center')
    ax.text(x + w/2, y + h*0.35, subtitle, fontsize=9.5, color='#cbd5e1', ha='center', va='center')

# 1. Simulator Layer (Left)
draw_block(ax, 0.05, 0.65, 0.22, 0.18, "Gazebo 3D Simulator", "turtlebot3_autorace_2020.world\nPhysics & Sensor Plugins", "#1e293b", "#38bdf8")
draw_block(ax, 0.05, 0.38, 0.22, 0.16, "TurtleBot3 Burger Cam", "Diff-Drive Robot Model\nFisheye + 360° 2D LiDAR", "#1e293b", "#38bdf8")
draw_block(ax, 0.05, 0.12, 0.22, 0.16, "Simulation Clock / ROS", "DDS Discovery & ROS 2 Humble\nDocker (autorace:humble)", "#1e293b", "#38bdf8")

# 2. Perception Nodes (Center Left)
draw_block(ax, 0.36, 0.72, 0.26, 0.15, "Camera Calibration", "intrinsic_rectify & extrinsic\nIPM Bird's-Eye View", "#162e24", "#34d399")
draw_block(ax, 0.36, 0.52, 0.26, 0.15, "detect_lane.py", "Dual HSV (Yellow/White)\nSliding Window Polynomial + HUD", "#162e24", "#34d399")
draw_block(ax, 0.36, 0.32, 0.26, 0.15, "detect_intersection_sign.py", "SIFT + FLANN + RANSAC\nClean Yellow Bounding Box", "#162e24", "#34d399")
draw_block(ax, 0.36, 0.12, 0.26, 0.15, "traffic_light_state.py", "ROI Crop + HSV Green Filter\nHeartbeat & Latching", "#162e24", "#34d399")

# 3. Mission Supervisor (Center Right)
draw_block(ax, 0.70, 0.25, 0.25, 0.55, "mission_supervisor.py", 
           "THE ARBITRATION BRAIN\n\n• 15 Hz Finite State Machine\n• Single-Writer Principle\n• Dynamic LiDAR Slalom\n• Pure Pursuit Waypoints\n• Level-Crossing Wait\n• 3.0s Sign Pause Timer\n• Bay Parking Docking", 
           "#2e1a2f", "#f43f5e")

# Flow Arrows with Labels
arrow_props = dict(arrowstyle="->,head_width=0.4,head_length=0.6", lw=2, color='#38bdf8')
ax.annotate("", xy=(0.36, 0.80), xytext=(0.27, 0.75), arrowprops=arrow_props)
ax.text(0.315, 0.80, "/camera/image_raw", fontsize=8.5, color='#94a3b8', ha='center')

ax.annotate("", xy=(0.36, 0.60), xytext=(0.36, 0.75), arrowprops=dict(arrowstyle="->", lw=2, color='#34d399'))
ax.text(0.40, 0.68, "/camera/image_projected", fontsize=8, color='#94a3b8')

ax.annotate("", xy=(0.36, 0.40), xytext=(0.27, 0.75), arrowprops=arrow_props)
ax.annotate("", xy=(0.36, 0.20), xytext=(0.27, 0.75), arrowprops=arrow_props)

# Arrows to Supervisor
p_arrow = dict(arrowstyle="->,head_width=0.4,head_length=0.6", lw=2.5, color='#34d399')
ax.annotate("", xy=(0.70, 0.62), xytext=(0.62, 0.60), arrowprops=p_arrow)
ax.text(0.66, 0.63, "/detect/lane", fontsize=8.5, color='#a7f3d0', ha='center')

ax.annotate("", xy=(0.70, 0.48), xytext=(0.62, 0.40), arrowprops=p_arrow)
ax.text(0.66, 0.47, "/detect/traffic_sign", fontsize=8.5, color='#a7f3d0', ha='center')

ax.annotate("", xy=(0.70, 0.35), xytext=(0.62, 0.20), arrowprops=p_arrow)
ax.text(0.66, 0.30, "/traffic_light_state", fontsize=8.5, color='#a7f3d0', ha='center')

# LaserScan and Odom directly from sim to supervisor
s_arrow = dict(arrowstyle="->,head_width=0.4,head_length=0.6", lw=2, color='#fbbf24', linestyle='--')
ax.annotate("", xy=(0.70, 0.68), xytext=(0.27, 0.46), arrowprops=s_arrow)
ax.text(0.48, 0.58, "/scan (360° LiDAR) & /odom (Pose)", fontsize=9, color='#fef08a', weight='bold')

# Command feedback to robot wheels
c_arrow = dict(arrowstyle="->,head_width=0.5,head_length=0.8", lw=3.5, color='#f43f5e')
ax.annotate("", xy=(0.27, 0.40), xytext=(0.70, 0.28), arrowprops=c_arrow)
ax.text(0.48, 0.28, "/cmd_vel (Twist: linear.x, angular.z)", fontsize=10.5, color='#fda4af', weight='bold', ha='center')

ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis('off')

plt.tight_layout()
plt.savefig('/home/steve/dev/ros2_exmaple/turtlebot3_autorace/docs/media/architecture_diagram.png', dpi=200)
plt.close()
print("Saved /home/steve/dev/ros2_exmaple/turtlebot3_autorace/docs/media/architecture_diagram.png")


# ==============================================================================
# FIGURE 2: Multi-Stage Task Progression Timeline & Track Infographic
# ==============================================================================
fig, ax = plt.subplots(figsize=(16, 9), dpi=200)
ax.set_facecolor('#0f1218')
fig.patch.set_facecolor('#0a0c10')

ax.text(0.5, 0.95, "AutoRace 2020: 7-Stage Autonomous Mission Sequence", 
        fontsize=20, weight='bold', color='#ffffff', ha='center')
ax.text(0.5, 0.90, "Ground-Truth Trigger Conditions, Sensing Modalities & Control Responses", 
        fontsize=12, color='#00d4ff', ha='center')

stages = [
    ("TASK 1\nTraffic Light", "Pose: (0.80, -1.75)\nHue: [40, 100]\nLaunch on Green", "#22c55e", 0.08),
    ("TASK 2\nLane Tracking", "Bird's-Eye IPM\nx = Ay² + By + C\nPD Steering Law", "#06b6d4", 0.22),
    ("TASK 3\nTraffic Signs", "SIFT + RANSAC\nClean Yellow Box\n3.0s Stop Pause", "#eab308", 0.36),
    ("TASK 4\nBarrier Slalom", "360° LiDAR Cluster\nCorridor Shift:\nx=1.77m <-> 1.47m", "#f97316", 0.50),
    ("TASK 5\nBay Parking", "Turn South Aisle\n90° Reverse Pivot\nHold at (0.28, 0.75)", "#a855f7", 0.64),
    ("TASK 6\nLevel Crossing", "Stop Bar at (-0.80)\nLiDAR range < 0.45m\nWait until raised", "#ef4444", 0.78),
    ("TASK 7\nDark Tunnel", "Pillar Avoidance\nWall Balancing\nLoop Completion", "#3b82f6", 0.92)
]

# Connecting timeline arrow
ax.annotate("", xy=(0.95, 0.55), xytext=(0.05, 0.55),
            arrowprops=dict(arrowstyle="->,head_width=0.6,head_length=1.0", lw=4, color='#334155'))

for title, desc, col, x_pos in stages:
    # Circle marker
    ax.scatter(x_pos, 0.55, color=col, s=700, edgecolors='white', lw=2.5, zorder=5)
    
    # Upper Title Card
    ax.text(x_pos, 0.66, title, fontsize=11, weight='bold', color=col, ha='center', va='bottom',
            bbox=dict(boxstyle="round,pad=0.4", fc="#1e293b", ec=col, lw=1.5))
    
    # Lower Detail Card
    ax.text(x_pos, 0.44, desc, fontsize=9.5, color='#f1f5f9', ha='center', va='top',
            bbox=dict(boxstyle="round,pad=0.5", fc="#161b22", ec="#30363d", lw=1.2))

# Bottom Summary Banner
banner = patches.FancyBboxPatch((0.08, 0.06), 0.84, 0.16, boxstyle="round,pad=0.02,rounding_size=0.03",
                               facecolor='#1e293b', edgecolor='#00d4ff', lw=1.5)
ax.add_patch(banner)
ax.text(0.5, 0.16, "Single Unified State Machine: mission_supervisor.py", fontsize=13, weight='bold', color='#00d4ff', ha='center')
ax.text(0.5, 0.10, "Guarantees zero command collisions on /cmd_vel while seamlessly blending vision PD lane centering with waypoint Pure-Pursuit.",
        fontsize=10.5, color='#94a3b8', ha='center')

ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis('off')

plt.tight_layout()
plt.savefig('/home/steve/dev/ros2_exmaple/turtlebot3_autorace/docs/media/mission_progression_infographic.png', dpi=200)
plt.close()
print("Saved /home/steve/dev/ros2_exmaple/turtlebot3_autorace/docs/media/mission_progression_infographic.png")
