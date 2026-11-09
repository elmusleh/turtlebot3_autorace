import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# Set dark/modern aesthetic
plt.style.use('dark_background')

# 1. Map Diagram
fig, ax = plt.subplots(figsize=(10, 10), dpi=150)
ax.set_facecolor('#111318')
fig.patch.set_facecolor('#0d0f12')

# Draw outer track boundary (4x4m)
ax.plot([-2.0, 2.0, 2.0, -2.0, -2.0], [-2.0, -2.0, 2.0, 2.0, -2.0], color='#444c56', lw=3, label='Track Bounds (4m x 4m)')

# Draw Centerline schematic
ax.plot([0.8, 1.3, 1.77, 1.77, 1.47, 1.77, 1.47, 0.5, -0.8, -1.5, -1.5, 0.8],
        [-1.75, -1.75, -1.0, 0.3, 0.7, 1.0, 1.4, 1.75, 1.26, 0.5, -1.5, -1.75],
        '--', color='#388bfd', lw=2, alpha=0.7, label='Centerline Waypoint Path')

# Mark tasks with distinct colored markers and text
tasks = [
    ("START LINE (0.80, -1.75)\nYaw = 0.0 (East)", (0.80, -1.75), '#2ea043', 'Task 0: Start Gate'),
    ("TRAFFIC LIGHT (1.30, -1.95)\nHSV Green Filter", (1.30, -1.95), '#56d364', 'Task 1: Traffic Light'),
    ("INTERSECTION SIGN (1.95, -1.00)\nSIFT Match + 3s Pause", (1.95, -1.00), '#e3b341', 'Task 3A: Intersection Sign'),
    ("TURN RIGHT SIGN (1.08, -0.73)\nSIFT Match + 3s Pause", (1.08, -0.73), '#d29922', 'Task 3B: Right Turn Sign'),
    ("CONSTRUCTION SIGN (1.00, 0.04)\nArm LiDAR Slalom", (1.00, 0.04), '#f0883e', 'Task 3C: Construction Sign'),
    ("BARRIERS (1.49, 0.54) & (1.76, 1.00)\nLiDAR Dynamic Avoidance", (1.62, 0.90), '#ff7b72', 'Task 4: Barrier Slalom'),
    ("PARKING SIGN (0.74, 1.95)\nBay 1: (0.25, 0.75)", (0.74, 1.95), '#a371f7', 'Task 5: Parking Sign & Bay'),
    ("STOP BAR & SIGN (-0.80, 1.26)\nMoving Gate Threshold", (-0.80, 1.26), '#f85149', 'Task 6: Level Crossing'),
    ("TUNNEL ENTRANCE (-1.54, 0.00)\nLiDAR Wall & Obstacle Follower", (-1.54, 0.00), '#79c0ff', 'Task 7: Dark Tunnel')
]

for label, (x, y), col, title in tasks:
    ax.scatter(x, y, color=col, s=180, edgecolors='white', lw=1.5, zorder=5)
    ax.annotate(f"{title}\n{label}", (x, y), xytext=(10, 10), textcoords="offset points",
                bbox=dict(boxstyle="round,pad=0.4", fc="#161b22", ec=col, lw=1.5, alpha=0.9),
                fontsize=8, color='#f0f6fc', weight='bold')

# Coordinate axes lines
ax.axhline(0, color='#30363d', linestyle=':', lw=1)
ax.axvline(0, color='#30363d', linestyle=':', lw=1)

ax.set_xlim(-2.2, 2.5)
ax.set_ylim(-2.3, 2.4)
ax.set_title("TurtleBot3 AutoRace 2020: Ground Truth Map & Task POIs", fontsize=15, color='#f0f6fc', weight='bold', pad=15)
ax.set_xlabel("X Axis (East -> West) [meters]", fontsize=11, color='#8b949e')
ax.set_ylabel("Y Axis (South -> North) [meters]", fontsize=11, color='#8b949e')
ax.grid(True, color='#21262d', linestyle='--', alpha=0.7)
ax.legend(loc='lower left', facecolor='#161b22', edgecolor='#30363d', fontsize=9)

plt.tight_layout()
plt.savefig('/home/steve/dev/ros2_exmaple/turtlebot3_autorace/docs/media/track_task_map.png', dpi=180)
plt.close()
print("Saved /home/steve/dev/ros2_exmaple/turtlebot3_autorace/docs/media/track_task_map.png")
