import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

plt.style.use('dark_background')

# ==============================================================================
# PART 1: Vertical Executive Flowchart Poster (High-Res 200 DPI)
# ==============================================================================
fig, ax = plt.subplots(figsize=(14, 18), dpi=200)
ax.set_facecolor('#0B0E14')
fig.patch.set_facecolor('#080A0F')

# Header Banner
header_box = patches.FancyBboxPatch((0.04, 0.925), 0.92, 0.055,
                                    boxstyle="round,pad=0.01,rounding_size=0.015",
                                    facecolor='#131822', edgecolor='#00D4FF', linewidth=2)
ax.add_patch(header_box)
ax.text(0.5, 0.96, "TURTLEBOT3 AUTORACE 2020 — AUTONOMOUS MISSION FLOWCHART",
        fontsize=18, weight='bold', color='#FFFFFF', ha='center', va='center')
ax.text(0.5, 0.938, "End-to-End State Machine Pipeline: From Start Line to Full 360° Track Completion",
        fontsize=11.5, color='#00D4FF', ha='center', va='center')

# Column Headers
col_headers = [
    (0.22, "MISSION STAGE & POSE", "#94A3B8"),
    (0.53, "SENSOR & PERCEPTION TRIGGER", "#38BDF8"),
    (0.81, "ROBOT CONTROL ACTION", "#34D399")
]
for cx, ctext, ccol in col_headers:
    ax.text(cx, 0.902, ctext, fontsize=11, weight='bold', color=ccol, ha='center', va='center')

# Start Pill
start_pill = patches.FancyBboxPatch((0.05, 0.855), 0.34, 0.032,
                                    boxstyle="round,pad=0.008,rounding_size=0.016",
                                    facecolor='#065F46', edgecolor='#10B981', linewidth=2.2)
ax.add_patch(start_pill)
ax.text(0.22, 0.871, "[START LINE]  Pose: (0.80, -1.75), Yaw = 0.0 rad",
        fontsize=10.0, weight='bold', color='#ECFDF5', ha='center', va='center')

# 7 Tasks Data
tasks = [
    {
        "num": "TASK 1",
        "title": "Traffic Light Start Gate",
        "pose": "Location: (1.30, -1.95)",
        "color": "#22C55E",
        "bg": "#11221C",
        "trigger_title": "Detect Green HSV Blob",
        "trigger_sub": "Crop ROI -> H:[40,100] -> Blob Area > 25px",
        "action_title": "Latch Gate & Launch Forward",
        "action_sub": "Release hold -> Drive at v = 0.10 m/s"
    },
    {
        "num": "TASK 2",
        "title": "Lane PD Following",
        "pose": "East Straight & Curves",
        "color": "#06B6D4",
        "bg": "#0F222A",
        "trigger_title": "IPM Bird's-Eye + Dual HSV",
        "trigger_sub": "Yellow/White Masks -> 2nd-Order Poly Fit",
        "action_title": "PD Steering + Anti-Stall",
        "action_sub": "ω = -Kp·e - Kd·ė  |  v >= 0.04 m/s on curves"
    },
    {
        "num": "TASK 3",
        "title": "SIFT Traffic Sign Reading",
        "pose": "Intersection (1.95, -1.00) & Right (1.08, -0.73)",
        "color": "#EAB308",
        "bg": "#241F10",
        "trigger_title": "SIFT + FLANN + RANSAC",
        "trigger_sub": "Lowe Ratio 0.78 -> Clean Yellow Box Overlay",
        "action_title": "Align Camera + 3.0s Pause",
        "action_sub": "Halt 3.0s for RQt verification -> Execute turn"
    },
    {
        "num": "TASK 4",
        "title": "Construction Barrier Slalom",
        "pose": "Barriers: (1.49, 0.54), (1.76, 1.00), (1.49, 1.44)",
        "color": "#F97316",
        "bg": "#261810",
        "trigger_title": "2D LiDAR Cluster Detection",
        "trigger_sub": "Front Cone (±30°) -> 3 Wall Obstacles",
        "action_title": "Dynamic S-Curve Dodge",
        "action_sub": "Shift corridor x=1.77m <-> 1.47m (Pure Pursuit)"
    },
    {
        "num": "TASK 5",
        "title": "Autonomous Bay Parking",
        "pose": "Sign (0.74, 1.95) -> Bay (0.28, 0.75)",
        "color": "#A855F7",
        "bg": "#20142B",
        "trigger_title": "Read Parking Sign + LiDAR Check",
        "trigger_sub": "SIFT Match -> Scan West/East Stall Occupancy",
        "action_title": "Back Into Bay & Hold 3.0s",
        "action_sub": "90° Reverse Pivot -> Park (or exit for Full Loop)"
    },
    {
        "num": "TASK 6",
        "title": "Level Crossing Stop Bar",
        "pose": "Stop Gate: (-0.80, 1.26)",
        "color": "#EF4444",
        "bg": "#281316",
        "trigger_title": "LiDAR Detects Wooden Barrier",
        "trigger_sub": "Narrow Slice (±15°): Blocked if dist < 0.45m",
        "action_title": "Wait Until Gate Raised",
        "action_sub": "Hold v = 0.0 m/s -> Resume when dist > 0.80m"
    },
    {
        "num": "TASK 7",
        "title": "Dark Tunnel Navigation",
        "pose": "Tunnel Entrance: (-1.54, 0.00)",
        "color": "#3B82F6",
        "bg": "#111C2D",
        "trigger_title": "360° LiDAR Wall & Pillar Scan",
        "trigger_sub": "Camera dark -> Track walls & 3 cylinder obstacles",
        "action_title": "Obstacle Repulsion + Waypoints",
        "action_sub": "Navigate cylinder corridor -> Return to Start"
    }
]

y_top = 0.765
row_step = 0.105
box_h = 0.076

# Arrow from Start Line to Task 1
ax.annotate("", xy=(0.22, y_top + box_h), xytext=(0.22, 0.855),
            arrowprops=dict(arrowstyle="->,head_width=0.45,head_length=0.55", lw=2.8, color='#10B981'))

for idx, t in enumerate(tasks):
    y = y_top - idx * row_step
    col = t["color"]
    bg = t["bg"]

    # 1. Left Box: Stage Node
    b1 = patches.FancyBboxPatch((0.05, y), 0.34, box_h,
                                boxstyle="round,pad=0.008,rounding_size=0.012",
                                facecolor=bg, edgecolor=col, linewidth=2.2)
    ax.add_patch(b1)

    # Badge for TASK #
    badge = patches.FancyBboxPatch((0.062, y + box_h - 0.028), 0.075, 0.020,
                                   boxstyle="round,pad=0.003,rounding_size=0.006",
                                   facecolor=col, edgecolor=col, linewidth=1)
    ax.add_patch(badge)
    ax.text(0.10, y + box_h - 0.018, t["num"], fontsize=9, weight='bold', color='#080A0F', ha='center', va='center')

    ax.text(0.15, y + box_h - 0.018, t["title"], fontsize=11.5, weight='bold', color='#FFFFFF', ha='left', va='center')
    ax.text(0.065, y + 0.020, t["pose"], fontsize=9.2, color='#CBD5E1', ha='left', va='center')

    # Horizontal Arrow 1: Stage -> Trigger
    ax.annotate("", xy=(0.415, y + box_h/2), xytext=(0.392, y + box_h/2),
                arrowprops=dict(arrowstyle="->,head_width=0.35,head_length=0.45", lw=2.2, color=col))

    # 2. Middle Box: Sensor Trigger
    b2 = patches.FancyBboxPatch((0.415, y), 0.23, box_h,
                                boxstyle="round,pad=0.008,rounding_size=0.012",
                                facecolor='#141B26', edgecolor='#334155', linewidth=1.6)
    ax.add_patch(b2)
    ax.text(0.53, y + box_h*0.66, t["trigger_title"], fontsize=10.2, weight='bold', color='#38BDF8', ha='center', va='center')
    ax.text(0.53, y + box_h*0.30, t["trigger_sub"], fontsize=8.6, color='#94A3B8', ha='center', va='center')

    # Horizontal Arrow 2: Trigger -> Action
    ax.annotate("", xy=(0.67, y + box_h/2), xytext=(0.647, y + box_h/2),
                arrowprops=dict(arrowstyle="->,head_width=0.35,head_length=0.45", lw=2.2, color='#38BDF8'))

    # 3. Right Box: Control Action
    b3 = patches.FancyBboxPatch((0.67, y), 0.28, box_h,
                                boxstyle="round,pad=0.008,rounding_size=0.012",
                                facecolor='#111E20', edgecolor='#10B981', linewidth=1.6)
    ax.add_patch(b3)
    ax.text(0.81, y + box_h*0.66, t["action_title"], fontsize=10.2, weight='bold', color='#34D399', ha='center', va='center')
    ax.text(0.81, y + box_h*0.30, t["action_sub"], fontsize=8.6, color='#CBD5E1', ha='center', va='center')

    # Vertical Spine Arrow to next task
    if idx < len(tasks) - 1:
        next_y = y_top - (idx + 1) * row_step
        ax.annotate("", xy=(0.22, next_y + box_h), xytext=(0.22, y),
                    arrowprops=dict(arrowstyle="->,head_width=0.45,head_length=0.55", lw=2.8, color=col))
        if idx == 4:
            # Special note between Task 5 and Task 6
            ax.text(0.235, y - 0.015, "(Mode 1: Done Parked  |  Mode 2: Continue Loop)",
                    fontsize=8.5, style='italic', color='#C084FC', ha='left', va='center')

# Final Arrow from Task 7 to Finish Pill
last_y = y_top - (len(tasks) - 1) * row_step
ax.annotate("", xy=(0.22, 0.082), xytext=(0.22, last_y),
            arrowprops=dict(arrowstyle="->,head_width=0.45,head_length=0.55", lw=2.8, color='#3B82F6'))

# Finish Pill
finish_pill = patches.FancyBboxPatch((0.05, 0.042), 0.34, 0.036,
                                     boxstyle="round,pad=0.008,rounding_size=0.016",
                                     facecolor='#1E3A8A', edgecolor='#60A5FA', linewidth=2.2)
ax.add_patch(finish_pill)
ax.text(0.22, 0.060, "[LAP COMPLETE]  Back at Start Line (0.80, -1.75)",
        fontsize=10.0, weight='bold', color='#EFF6FF', ha='center', va='center')

# Summary Legend Box at Bottom Right
summary_box = patches.FancyBboxPatch((0.415, 0.042), 0.535, 0.036,
                                     boxstyle="round,pad=0.008,rounding_size=0.012",
                                     facecolor='#131822', edgecolor='#334155', linewidth=1.5)
ax.add_patch(summary_box)
ax.text(0.682, 0.060, "Single-Writer Arbitrator: mission_supervisor.py (15 Hz)  ->  Publishes /cmd_vel & /mission/state",
        fontsize=9.5, weight='bold', color='#00D4FF', ha='center', va='center')

ax.set_xlim(0, 1)
ax.set_ylim(0.02, 1.0)
ax.axis('off')

plt.tight_layout()
out_poster = '/home/steve/dev/ros2_exmaple/turtlebot3_autorace/docs/media/mission_flowchart_poster.png'
plt.savefig(out_poster, dpi=200)
plt.close()
print(f"Saved {out_poster}")


# ==============================================================================
# PART 2: Widescreen 16:9 Presentation Flowchart Slide Image (High-Res 200 DPI)
# ==============================================================================
fig, ax = plt.subplots(figsize=(16, 9), dpi=200)
ax.set_facecolor('#0B0E14')
fig.patch.set_facecolor('#080A0F')

# Header
ax.text(0.5, 0.95, "TurtleBot3 AutoRace 2020: Complete Autonomous Mission Flowchart",
        fontsize=19, weight='bold', color='#FFFFFF', ha='center', va='center')
ax.text(0.5, 0.91, "Sequential State Transitions, Sensor Triggers, and Control Actions Across the Track",
        fontsize=11.5, color='#00D4FF', ha='center', va='center')

# Column Labels
ax.text(0.19, 0.865, "MISSION STAGE", fontsize=10.5, weight='bold', color='#94A3B8', ha='center')
ax.text(0.51, 0.865, "PERCEPTION TRIGGER", fontsize=10.5, weight='bold', color='#38BDF8', ha='center')
ax.text(0.81, 0.865, "CONTROL RESPONSE", fontsize=10.5, weight='bold', color='#34D399', ha='center')

# Start Pill at Top Left
sp = patches.FancyBboxPatch((0.05, 0.81), 0.28, 0.038,
                            boxstyle="round,pad=0.005,rounding_size=0.015",
                            facecolor='#065F46', edgecolor='#10B981', linewidth=2)
ax.add_patch(sp)
ax.text(0.19, 0.829, "[START LINE] (0.80, -1.75)", fontsize=10, weight='bold', color='#ECFDF5', ha='center', va='center')

y0 = 0.715
dy = 0.096
bh = 0.068

ax.annotate("", xy=(0.19, y0 + bh), xytext=(0.19, 0.81),
            arrowprops=dict(arrowstyle="->,head_width=0.35,head_length=0.4", lw=2.2, color='#10B981'))

for idx, t in enumerate(tasks):
    y = y0 - idx * dy
    col = t["color"]
    bg = t["bg"]

    # Stage Box
    b1 = patches.FancyBboxPatch((0.04, y), 0.30, bh,
                                boxstyle="round,pad=0.005,rounding_size=0.01",
                                facecolor=bg, edgecolor=col, linewidth=2)
    ax.add_patch(b1)
    ax.text(0.055, y + bh*0.64, f"{t['num']}: {t['title']}", fontsize=10.2, weight='bold', color='#FFFFFF', ha='left', va='center')
    ax.text(0.055, y + bh*0.26, t["pose"], fontsize=8.3, color='#CBD5E1', ha='left', va='center')

    # Arrow Stage -> Trigger
    ax.annotate("", xy=(0.37, y + bh/2), xytext=(0.342, y + bh/2),
                arrowprops=dict(arrowstyle="->,head_width=0.3,head_length=0.4", lw=2, color=col))

    # Trigger Box
    b2 = patches.FancyBboxPatch((0.37, y), 0.27, bh,
                                boxstyle="round,pad=0.005,rounding_size=0.01",
                                facecolor='#141B26', edgecolor='#334155', linewidth=1.5)
    ax.add_patch(b2)
    ax.text(0.505, y + bh*0.64, t["trigger_title"], fontsize=9.8, weight='bold', color='#38BDF8', ha='center', va='center')
    ax.text(0.505, y + bh*0.26, t["trigger_sub"], fontsize=8.2, color='#94A3B8', ha='center', va='center')

    # Arrow Trigger -> Action
    ax.annotate("", xy=(0.67, y + bh/2), xytext=(0.642, y + bh/2),
                arrowprops=dict(arrowstyle="->,head_width=0.3,head_length=0.4", lw=2, color='#38BDF8'))

    # Action Box
    b3 = patches.FancyBboxPatch((0.67, y), 0.29, bh,
                                boxstyle="round,pad=0.005,rounding_size=0.01",
                                facecolor='#111E20', edgecolor='#10B981', linewidth=1.5)
    ax.add_patch(b3)
    ax.text(0.815, y + bh*0.64, t["action_title"], fontsize=9.8, weight='bold', color='#34D399', ha='center', va='center')
    ax.text(0.815, y + bh*0.26, t["action_sub"], fontsize=8.2, color='#CBD5E1', ha='center', va='center')

    if idx < len(tasks) - 1:
        ny = y0 - (idx + 1) * dy
        ax.annotate("", xy=(0.19, ny + bh), xytext=(0.19, y),
                    arrowprops=dict(arrowstyle="->,head_width=0.35,head_length=0.4", lw=2.2, color=col))

last_y_wide = y0 - (len(tasks) - 1) * dy
ax.annotate("", xy=(0.19, 0.068), xytext=(0.19, last_y_wide),
            arrowprops=dict(arrowstyle="->,head_width=0.35,head_length=0.4", lw=2.2, color='#3B82F6'))

fp = patches.FancyBboxPatch((0.04, 0.025), 0.30, 0.040,
                            boxstyle="round,pad=0.005,rounding_size=0.015",
                            facecolor='#1E3A8A', edgecolor='#60A5FA', linewidth=2)
ax.add_patch(fp)
ax.text(0.19, 0.045, "[LAP COMPLETE] Back at Start Line", fontsize=10, weight='bold', color='#EFF6FF', ha='center', va='center')

sb = patches.FancyBboxPatch((0.37, 0.025), 0.59, 0.040,
                            boxstyle="round,pad=0.005,rounding_size=0.01",
                            facecolor='#131822', edgecolor='#00D4FF', linewidth=1.5)
ax.add_patch(sb)
ax.text(0.665, 0.045, "Mode 1 (./run.sh parking) stops at Task 5  |  Mode 2 (./run.sh full-loop) completes all 7 Tasks",
        fontsize=9.5, weight='bold', color='#00D4FF', ha='center', va='center')

ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis('off')

plt.tight_layout()
out_wide = '/home/steve/dev/ros2_exmaple/turtlebot3_autorace/docs/media/mission_flowchart_widescreen.png'
plt.savefig(out_wide, dpi=200)
plt.close()
print(f"Saved {out_wide}")
