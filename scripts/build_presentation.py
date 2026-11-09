import sys
import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# Palette: Dark sleek executive engineering theme
C_BG = RGBColor(15, 18, 24)        # Deep Charcoal
C_CARD = RGBColor(26, 31, 41)      # Dark Slate Card
C_BORDER = RGBColor(46, 56, 74)    # Card Border
C_ACCENT = RGBColor(0, 212, 255)   # Vivid Cyan / Teal Accent
C_YELLOW = RGBColor(255, 204, 0)   # Yellow
C_GREEN = RGBColor(46, 204, 113)   # Green
C_WHITE = RGBColor(245, 247, 250)  # Near White
C_MUTED = RGBColor(140, 153, 171)  # Muted Gray

blank_layout = prs.slide_layouts[6]

def add_base_slide(title_text, subtitle_text):
    slide = prs.slides.add_slide(blank_layout)
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid()
    bg.fill.fore_color.rgb = C_BG
    bg.line.fill.background()

    # Header bar
    top_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(1.1))
    top_bar.fill.solid()
    top_bar.fill.fore_color.rgb = RGBColor(20, 24, 32)
    top_bar.line.fill.background()

    # Title box
    tx_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.12), Inches(11.5), Inches(0.85))
    tf = tx_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title_text
    p.font.name = 'Arial'
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = C_WHITE

    p2 = tf.add_paragraph()
    p2.text = subtitle_text
    p2.font.name = 'Arial'
    p2.font.size = Pt(13)
    p2.font.color.rgb = C_ACCENT

    # Footer
    ft_box = slide.shapes.add_textbox(Inches(0.8), Inches(7.05), Inches(11.5), Inches(0.4))
    ft = ft_box.text_frame
    p_ft = ft.paragraphs[0]
    p_ft.text = "TurtleBot3 AutoRace 2020 Autonomous Driving Architecture | ROS 2 Humble"
    p_ft.font.name = 'Arial'
    p_ft.font.size = Pt(10)
    p_ft.font.color.rgb = C_MUTED
    return slide

def add_card(slide, left, top, width, height, title, bullets, border_color=C_BORDER):
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = C_CARD
    card.line.color.rgb = border_color
    card.line.width = Pt(1.5)

    tx_box = slide.shapes.add_textbox(left + Inches(0.2), top + Inches(0.15), width - Inches(0.4), height - Inches(0.3))
    tf = tx_box.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = title
    p.font.name = 'Arial'
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_ACCENT

    for b in bullets:
        p_b = tf.add_paragraph()
        p_b.text = "• " + b[0]
        p_b.font.name = 'Arial'
        p_b.font.size = Pt(12.5)
        p_b.font.bold = True
        p_b.font.color.rgb = C_WHITE
        p_b.space_before = Pt(6)

        if len(b) > 1:
            p_sub = tf.add_paragraph()
            p_sub.text = "    " + b[1]
            p_sub.font.name = 'Arial'
            p_sub.font.size = Pt(11)
            p_sub.font.color.rgb = C_MUTED

# ==========================================================
# SLIDE 1: Title Slide
# ==========================================================
s1 = prs.slides.add_slide(blank_layout)
bg1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
bg1.fill.solid()
bg1.fill.fore_color.rgb = C_BG
bg1.line.fill.background()

t_box = s1.shapes.add_textbox(Inches(1.2), Inches(1.8), Inches(10.5), Inches(3.5))
tf1 = t_box.text_frame
tf1.word_wrap = True
p = tf1.paragraphs[0]
p.text = "TurtleBot3 AutoRace 2020"
p.font.name = 'Arial'
p.font.size = Pt(44)
p.font.bold = True
p.font.color.rgb = C_WHITE

p = tf1.add_paragraph()
p.text = "End-to-End Autonomous Driving Architecture in ROS 2 Humble"
p.font.name = 'Arial'
p.font.size = Pt(22)
p.font.color.rgb = C_ACCENT
p.space_after = Pt(24)

p = tf1.add_paragraph()
p.text = "Perception (HSV & SIFT) | Motion Control (Pure Pursuit & PD) | Dynamic LiDAR Navigation"
p.font.name = 'Arial'
p.font.size = Pt(15)
p.font.color.rgb = C_MUTED

# ==========================================================
# SLIDE 2: Project Overview & Core Architecture
# ==========================================================
s2 = add_base_slide("Executive System Overview", "From Raw Simulation Template to Full Autonomous Stack")
add_card(s2, Inches(0.8), Inches(1.4), Inches(5.6), Inches(5.4), "Upstream ROBOTIS vs Our System", [
    ("Upstream ROBOTIS: A Testing Template", "Provided Gazebo 3D meshes and disjointed starter scripts; robot could not finish a lap."),
    ("Competing /cmd_vel Motor Contention", "Original nodes published concurrently to wheels, causing violent vibrations and stalling."),
    ("Our Single-Writer Architecture", "Centralized arbitration in mission_supervisor.py guarantees smooth, jitter-free execution."),
    ("Full Multi-Task Autonomy", "Navigates start gate, signs, construction slalom, parking, level crossing, and tunnel.")
])
add_card(s2, Inches(6.8), Inches(1.4), Inches(5.6), Inches(5.4), "Core Technology Stack", [
    ("Middleware: ROS 2 Humble (DDS)", "Decentralized peer-to-peer discovery with deterministic publisher/subscriber pipelines."),
    ("Docker Isolation (autorace:humble)", "100% reproducible Ubuntu 22.04 environment with host X11 forwarding."),
    ("Computer Vision (OpenCV 4.x)", "Inverse Perspective Mapping, HSV color masks, SIFT feature matching & RANSAC homography."),
    ("Actuation & Sensors", "Fisheye camera (30 FPS), 360° 2D LiDAR (/scan), differential drive odometry (/odom).")
])

# ==========================================================
# SLIDE 3: Task 1: Traffic Light Start Gate
# ==========================================================
s3 = add_base_slide("Task 1: Traffic Light Start Gate", "Autonomous Race Initiation via HSV Color Segmentation | Location (1.30, -1.95)")
add_card(s3, Inches(0.8), Inches(1.4), Inches(5.6), Inches(5.4), "Perception & State Logic", [
    ("Upper-Right Camera ROI Crop", "Isolates the overhead signal [y:20-180, x:220-320], ignoring ground and asphalt reflections."),
    ("HSV Color Space Thresholding", "Green Hue filtered in [40, 100], Saturation in [120, 255], Value in [120, 255]."),
    ("Largest-Blob Contour Area Filter", "cv2.findContours() requires connected green area > 25 pixels, rejecting scattered noise."),
    ("10 Hz Heartbeat & State Latching", "Publishes continuously on /detect/traffic_light_state; latches open once green is confirmed.")
])
add_card(s3, Inches(6.8), Inches(1.4), Inches(5.6), Inches(5.4), "Robot Control & Operational Flow", [
    ("Zero Motor Creep at Start Line", "Robot holds stationary at (0.80, -1.75) while signal cycles Red (5s) -> Yellow (1s)."),
    ("Deterministic Launch Trigger", "Immediate transition to STATE=lane:following at v = 0.10 m/s upon green light detection."),
    ("Fail-Safe Design", "If light detection is occluded mid-turn, the latched green state prevents sudden emergency stops.")
])

# ==========================================================
# SLIDE 4: Task 2: Lane Keeping & Inverse Perspective Mapping (Slide 1/2)
# ==========================================================
s4 = add_base_slide("Task 2: Lane Keeping (IPM & Segmentation)", "Transforming Perspective Camera Feeds into Top-Down Metric Guidance")
add_card(s4, Inches(0.8), Inches(1.4), Inches(5.6), Inches(5.4), "Inverse Perspective Mapping (IPM)", [
    ("Vanishing Point Removal", "Perspective camera causes parallel lines to converge; IPM warps perspective into orthographic view."),
    ("Homography Transform Matrix", "3x3 matrix projects camera ground plane into top-down /camera/image_projected."),
    ("Metric Alignment", "Parallel lane boundaries appear as vertical parallel stripes, enabling accurate curve fitting.")
])
add_card(s4, Inches(6.8), Inches(1.4), Inches(5.6), Inches(5.4), "Dual-Color Road Segmentation", [
    ("Left Boundary: Yellow Line Mask", "Filtered in HSV space with Hue [10, 127], Saturation [70, 255], Value [95, 255]."),
    ("Right Boundary: White Line Mask", "Filtered with low Saturation [0, 70] and high Lightness [180, 255] to capture clean white."),
    ("Binary Threshold Fusion", "Outputs high-contrast binary pixel matrices for left and right track bounds.")
])

# ==========================================================
# SLIDE 5: Task 2: Lane Keeping & PD Control (Slide 2/2)
# ==========================================================
s5 = add_base_slide("Task 2: Curve Fitting & PD Motion Control", "Sliding Window Polynomials, Anti-Stall Law, and Live HUD Telemetry")
add_card(s5, Inches(0.8), Inches(1.4), Inches(5.6), Inches(5.4), "Sliding Window Polynomial Curve Fitting", [
    ("Histogram Peak Detection", "Finds the base coordinate of left and right lanes at the bottom of the image."),
    ("2nd-Degree Polynomial (x = Ay² + By + C)", "Fits quadratic curvature to track sharp S-curves smoothly through 9 sliding windows."),
    ("Centerline Calculation", "Desired vehicle track: x_center(y) = (x_left(y) + x_right(y)) / 2."),
    ("Lateral Error", "error = x_center - (image_width / 2) evaluated at lookahead row y=350.")
])
add_card(s5, Inches(6.8), Inches(1.4), Inches(5.6), Inches(5.4), "PD Control & Curve Anti-Stall Law", [
    ("PD Steering Controller", "Angular velocity: ω = -Kp * error - Kd * (d(error)/dt) with Kp=0.0035, Kd=0.0005."),
    ("Curve Anti-Stall Speed Law", "Fixed ROBOTIS bug where speed hit 0 m/s on curves: guaranteed v >= 0.04 m/s maintains momentum."),
    ("Live HUD Telemetry Banner", "Renders STAGE, SPEED, and color-coded LiDAR proximity warnings directly onto camera feed.")
])

# ==========================================================
# SLIDE 6: Task 3: Traffic Sign Detection (SIFT & Clean Yellow Box)
# ==========================================================
s6 = add_base_slide("Task 3: Traffic Sign Detection & Pauses", "SIFT Matching, RANSAC Homography, and Clean Yellow Bounding Box")
add_card(s6, Inches(0.8), Inches(1.4), Inches(5.6), Inches(5.4), "Classical SIFT Perception Pipeline", [
    ("Scale-Invariant Feature Transform", "Extracts keypoints and 128D descriptor vectors invariant to scale, rotation, and lighting."),
    ("FLANN k-NN Matching (k=2)", "Fast Library for Approximate Nearest Neighbors finds candidate matching points in microseconds."),
    ("Lowe's Ratio Test (d1 < 0.78 * d2)", "Discards over 90% of ambiguous background matches, retaining only distinct sign inliers."),
    ("RANSAC Homography Matrix M", "Finds the robust perspective matrix projecting the sign template into camera view.")
])
add_card(s6, Inches(6.8), Inches(1.4), Inches(5.6), Inches(5.4), "Clean Yellow Box & Mission Execution", [
    ("Yellow Boundary Projection", "Suppressed noisy cv2.drawMatches() dots/lines; projects only 4 template corners with cv2.polylines()."),
    ("Clean Visual Aesthetic", "Draws crisp yellow rectangle (0, 255, 255) and label, perfectly visible in RQt dashboards."),
    ("3.0-Second Stationary Pause", "Robot decelerates to 0.05 m/s, aligns heading, and halts for 3.0s to allow clear evaluation."),
    ("Supported Signs", "Intersection, Right Turn, Construction, Parking, Stop Sign, and Tunnel.")
])

# ==========================================================
# SLIDE 7: Task 4: Construction Barrier Slalom (LiDAR Avoidance)
# ==========================================================
s7 = add_base_slide("Task 4: Construction Barrier Slalom", "Dynamic 2D LiDAR Clustering & Real-Time S-Curve Trajectory Planning")
add_card(s7, Inches(0.8), Inches(1.4), Inches(5.6), Inches(5.4), "The Slalom Challenge", [
    ("Three Alternating Barricades", "East corridor contains 3 white barriers: #1 at y=0.54 (right), #2 at y=1.00 (left), #3 at y=1.44 (right)."),
    ("Narrow Lane Corridor [1.38m - 1.88m]", "Leaves minimal clearance (~20cm) on either side of the robot chassis."),
    ("Blind Camera Zone", "Construction walls lack standard road markings; vision alone causes catastrophic collisions.")
])
add_card(s7, Inches(6.8), Inches(1.4), Inches(5.6), Inches(5.4), "Dynamic LiDAR Slalom Solution", [
    ("Front-Cone LaserScan Processing", "Filters 360° point cloud within +/-30° cone for ranges 0.12m < r < 0.75m."),
    ("Dynamic Corridor Shifting", "Projects hits into world coordinates (x, y); dynamically picks target x=1.77m (left) or x=1.47m (right)."),
    ("Pure Pursuit Trajectory Control", "Computes lookahead curvature kappa = 2*sin(alpha)/Ld for smooth S-curve transitions."),
    ("3D RViz Obstacle Markers", "Publishes red cylinder markers on /mission/obstacle_markers for visual verification.")
])

# ==========================================================
# SLIDE 8: Task 5: Autonomous Parking Docking
# ==========================================================
s8 = add_base_slide("Task 5: Autonomous Bay Parking", "Sign Recognition, Corridor Alignment, and Precise Reverse Docking")
add_card(s8, Inches(0.8), Inches(1.4), Inches(5.6), Inches(5.4), "Parking Detection & Approach", [
    ("Parking Sign Identification", "Detects Parking template at (0.74, 1.95) with SIFT; halts for 3.0-second confirmation pause."),
    ("Aisle Entry Navigation", "Switches from lane-keeping to precision waypoint guidance into central alley (0.50, 1.25)."),
    ("LiDAR Stall Verification", "Scans West bay (0.25, 0.75) and East bay (0.75, 0.75) to verify stall clearance.")
])
add_card(s8, Inches(6.8), Inches(1.4), Inches(5.6), Inches(5.4), "Docking Maneuver & Modes", [
    ("90-Degree Reverse Docking", "Executes calculated pivot reverse into stall (0.28, 0.75) with rear LiDAR safety check."),
    ("Simulation Mode 1 (Parking Terminal)", "Robot halts completely inside bay and reports STATE=done:parked."),
    ("Simulation Mode 2 (Full Loop)", "Robot pauses 3.0s, reverses out to aisle, turns North, and resumes track circuit.")
])

# ==========================================================
# SLIDE 9: Task 6 & 7: Level Crossing & Dark Tunnel
# ==========================================================
s9 = add_base_slide("Tasks 6 & 7: Level Crossing & Dark Tunnel", "Dynamic Gate Thresholding and Subterranean Obstacle Avoidance")
add_card(s9, Inches(0.8), Inches(1.4), Inches(5.6), Inches(5.4), "Task 6: Level-Crossing Stop Bar", [
    ("Moving Railway Barrier (-0.80, 1.26)", "Mechanical wooden arm cyclically lowers across the roadway, blocking traffic."),
    ("Narrow-Cone LiDAR Monitoring", "Evaluates forward laser ranges (+/-15°). If range < 0.45m, gate is down -> commands v = 0.0 m/s."),
    ("Automatic Gate Clearance Resume", "Monitors until range > 0.80m for 3 consecutive frames, then accelerates smoothly across.")
])
add_card(s9, Inches(6.8), Inches(1.4), Inches(5.6), Inches(5.4), "Task 7: Dark Tunnel Obstacles", [
    ("Low-Illumination Corridor", "Southwest tunnel [x: -1.75 to -0.30] lacks reliable lane line illumination."),
    ("LiDAR Wall Balancing & Repulsion", "Balances left and right wall distances while avoiding 3 internal cylindrical pillars."),
    ("Full 360° Circuit Completion", "Exits tunnel corridor and crosses Start/Finish line (0.80, -1.75), reporting STATE=done:lap-complete.")
])

# ==========================================================
# SLIDE 10: Verification, Tooling & Educational Assets
# ==========================================================
s10 = add_base_slide("Verification & Reproduction Tools", "Built for 100% Deterministic Evaluation and Zero-to-Hero Mastery")
add_card(s10, Inches(0.8), Inches(1.4), Inches(5.6), Inches(5.4), "Workflow & CI Testing Suite", [
    ("Unified Runner CLI (./run.sh)", "One command to run parking, full-loop, status, stop, clean-docker, or quiz."),
    ("Headless Regression CI (./run.sh verify)", "Automated pytest script running in headless Gazebo; asserts completion within 150s."),
    ("GitHub Actions CI (.github/workflows)", "Colcon builds and flake8 linting executed automatically on every push."),
    ("DevContainer Specification", "One-click setup in VS Code / Cursor with Python and ROS 2 extensions pre-configured.")
])
add_card(s10, Inches(6.8), Inches(1.4), Inches(5.6), Inches(5.4), "Educational Learning Suite", [
    ("Interactive Perception Notebook", "notebooks/perception_walkthrough.ipynb: Test HSV and SIFT cell-by-cell without Gazebo."),
    ("Self-Quiz CLI (./run.sh quiz)", "Randomized oral defense quiz engine based on docs/STUDY_AND_ORAL_DEFENSE_GUIDE.md."),
    ("Animated HD Demonstration Video", "docs/media/autorace_pipeline_animated.mp4: Full 1080p animated breakdown of all 3 stages."),
    ("Ground Truth Task Map", "docs/media/track_task_map.png: High-resolution Cartesian coordinate reference.")
])

# ==========================================================
# SLIDE 11: Visual Autonomous Mission Flowchart Slide
# ==========================================================
s11 = prs.slides.add_slide(blank_layout)
bg11 = s11.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
bg11.fill.solid()
bg11.fill.fore_color.rgb = C_BG
bg11.line.fill.background()

fc_img_path = '/home/steve/dev/ros2_exmaple/turtlebot3_autorace/docs/media/mission_flowchart_widescreen.png'
if os.path.exists(fc_img_path):
    s11.shapes.add_picture(fc_img_path, Inches(0.2), Inches(0.15), width=Inches(12.933))

# ==========================================================
# SLIDE 12: Visual System Architecture Diagram Slide
# ==========================================================
s12 = prs.slides.add_slide(blank_layout)
bg12 = s12.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
bg12.fill.solid()
bg12.fill.fore_color.rgb = C_BG
bg12.line.fill.background()

arch_img_path = '/home/steve/dev/ros2_exmaple/turtlebot3_autorace/docs/media/architecture_diagram.png'
if os.path.exists(arch_img_path):
    s12.shapes.add_picture(arch_img_path, Inches(0.2), Inches(0.15), width=Inches(12.933))

# Save presentation
out_path = '/home/steve/dev/ros2_exmaple/turtlebot3_autorace/docs/TurtleBot3_AutoRace_2020_Presentation.pptx'
prs.save(out_path)
print(f"Presentation saved successfully to: {out_path}")
