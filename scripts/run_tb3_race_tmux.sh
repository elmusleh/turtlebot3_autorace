#!/bin/bash
# ======================================================================
#  run_tb3_race_tmux.sh — AutoRace task 1 with every node visible in tmux
#
#  Windows:
#    0 sim      Gazebo autorace_2020 world
#    1 camera   rectified image | extrinsic compensation
#    2 detect   lane | traffic-light state | YOLO | template sign detector
#    3 control  supervisor+lane controller | live state monitor | cmd_vel rate
#    4 views    rqt_image_view of the annotated topics
#
#  Panes are addressed by captured pane_id (not index), because
#  `select-layout tiled` renumbers pane indices and later send-keys would
#  otherwise land in the wrong pane.
#
#  Usage: MISSION=construction bash /root/ros2_humble_ws/run_tb3_race_tmux.sh
# ======================================================================
set -u

WS=/root/ros2_humble_ws
SESSION=${SESSION:-race}
MISSION=${MISSION:-intersection}
COURSE_MODE=${COURSE_MODE:-parking}
HEADLESS=${HEADLESS:-0}

export TURTLEBOT3_MODEL=burger_cam
export GAZEBO_MODEL_PATH=$WS/install/turtlebot3_gazebo/share/turtlebot3_gazebo/models
export GAZEBO_PLUGIN_PATH=$WS/build/turtlebot3_gazebo:${GAZEBO_PLUGIN_PATH:-}
export DISPLAY=${DISPLAY:-:0}

SRC="source /opt/ros/humble/setup.bash; source $WS/install/setup.bash; export TURTLEBOT3_MODEL=burger_cam; export GAZEBO_MODEL_PATH=$GAZEBO_MODEL_PATH; export GAZEBO_PLUGIN_PATH=$GAZEBO_PLUGIN_PATH; export DISPLAY=$DISPLAY"

command -v tmux >/dev/null 2>&1 || { apt-get update -qq && apt-get install -y -qq tmux; }

# ---- stop leftovers from a previous run ------------------------------
# A killed tmux session leaves gzserver/nodes behind; two simulators then
# publish competing /odom and camera data. Bracketed patterns keep this
# script from matching its own command line.
echo "[..] cleaning up previous simulation processes"
for pat in "[g]zserver" "[g]zclient" "[r]os2 launch" "[r]obot_state_publisher" \
           "[s]pawn_entity.py" "[c]ontrol_lane" "[m]ission_supervisor" \
           "[d]etect_lane" "[t]raffic_light_state" "[y]olo_sign_detector" \
           "[i]mage_projection" "[i]mage_compensation" "[r]ectify_node" \
           "[d]ebayer_node" "[s]tate_monitor" "[d]etect_.*_sign" \
           "[c]omponent_container" "[r]epublish" \
           "[s]can_probe" "[c]ount_sniff" "[t]rack_odom" "[y]aw_probe" \
           "[r]everse_audit" "[s]can_quadrant_probe"; do
    pkill -9 -f "$pat" 2>/dev/null
done
sleep 2
# Stale FastRTPS shm from SIGKILLed nodes breaks new participants
# ("fastrtps_port<n>: open_and_lock_file failed") and can silently kill the
# camera pipeline. Safe to remove while nothing ROS is running.
rm -f /dev/shm/fastrtps_* /dev/shm/sem.fastrtps_* 2>/dev/null

tmux kill-session -t "$SESSION" 2>/dev/null

# ---- window 0: simulation --------------------------------------------
SIM=$(tmux new-session -d -s "$SESSION" -n sim -x 220 -y 55 -P -F "#{pane_id}")
if [ "$HEADLESS" = "1" ]; then
    tmux send-keys -t "$SIM" "$SRC; echo '=== GAZEBO HEADLESS (autorace_2020) ==='; ros2 launch turtlebot3_gazebo turtlebot3_autorace_2020.launch.py gui:=false" C-m
    pkill -9 -f "[g]zclient" 2>/dev/null || true
else
    tmux send-keys -t "$SIM" "$SRC; echo '=== GAZEBO (autorace_2020) ==='; ros2 launch turtlebot3_gazebo turtlebot3_autorace_2020.launch.py" C-m
fi

# ---- window 1: camera pipeline ---------------------------------------
CAM=$(tmux new-window -t "$SESSION" -n camera -P -F "#{pane_id}")
tmux send-keys -t "$CAM" "$SRC; echo '=== waiting 20s for Gazebo ==='; sleep 20; echo '=== INTRINSIC RECTIFY ==='; ros2 launch turtlebot3_autorace_camera intrinsic_rectify.launch.py" C-m
CAMB=$(tmux split-window -h -t "$CAM" -P -F "#{pane_id}")
tmux send-keys -t "$CAMB" "$SRC; sleep 24; echo '=== EXTRINSIC COMPENSATION -> /camera/image_compensated ==='; ros2 launch turtlebot3_autorace_camera extrinsic_compensation.launch.py" C-m

# ---- window 2: detection ---------------------------------------------
DET=$(tmux new-window -t "$SESSION" -n detect -P -F "#{pane_id}")
tmux send-keys -t "$DET" "$SRC; sleep 30; echo '=== LANE DETECTION ==='; ros2 launch turtlebot3_autorace_detect detect_lane.launch.py" C-m
DET_LIGHT=$(tmux split-window -h -t "$DET" -P -F "#{pane_id}")
tmux send-keys -t "$DET_LIGHT" "$SRC; sleep 32; echo '=== TRAFFIC LIGHT STATE ==='; ros2 launch turtlebot3_autorace_detect detect_traffic_light_state.launch.py" C-m
DET_YOLO=$(tmux split-window -v -t "$DET_LIGHT" -P -F "#{pane_id}")
tmux send-keys -t "$DET_YOLO" "$SRC; sleep 34; echo '=== YOLO SIGN DETECTION ==='; ros2 launch turtlebot3_autorace_detect detect_yolo_sign.launch.py" C-m
DET_SIGN=$(tmux split-window -v -t "$DET" -P -F "#{pane_id}")
tmux send-keys -t "$DET_SIGN" "$SRC; sleep 36; echo '=== TEMPLATE SIGN DETECTOR (mission=$MISSION) ==='; ros2 launch turtlebot3_autorace_detect detect_sign.launch.py mission:=$MISSION" C-m
tmux select-layout -t "$DET" tiled

# ---- window 3: control + monitors ------------------------------------
CTL=$(tmux new-window -t "$SESSION" -n control -P -F "#{pane_id}")
tmux send-keys -t "$CTL" "$SRC; sleep 38; echo '=== SUPERVISOR + CONTROL_LANE (course_mode=$COURSE_MODE) ==='; ros2 launch turtlebot3_autorace_mission control_race.launch.py course_mode:=$COURSE_MODE" C-m
CTL_MON=$(tmux split-window -h -t "$CTL" -P -F "#{pane_id}")
tmux send-keys -t "$CTL_MON" "$SRC; sleep 40; echo '=== LIVE STATE (light / sign / mission) ==='; python3 $WS/tools/state_monitor.py" C-m
CTL_HZ=$(tmux split-window -v -t "$CTL_MON" -P -F "#{pane_id}")
tmux send-keys -t "$CTL_HZ" "$SRC; sleep 42; echo '=== LIVE /cmd_vel RATE ==='; ros2 topic hz /cmd_vel" C-m
tmux select-layout -t "$CTL" tiled

# ---- window 4: GUI views ---------------------------------------------
if [ "$HEADLESS" != "1" ]; then
    VW=$(tmux new-window -t "$SESSION" -n views -P -F "#{pane_id}")
    tmux send-keys -t "$VW" "$SRC; echo '=== RQT: camera (compensated) ==='; ros2 run rqt_image_view rqt_image_view /camera/image_compensated" C-m
    VW_RV=$(tmux split-window -h -t "$VW" -P -F "#{pane_id}")
    tmux send-keys -t "$VW_RV" "$SRC; echo '=== RVIZ2 ==='; rviz2 -d $WS/install/turtlebot3_gazebo/share/turtlebot3_gazebo/rviz/tb3_gazebo.rviz" C-m
    VW_LT=$(tmux split-window -v -t "$VW_RV" -P -F "#{pane_id}")
    tmux send-keys -t "$VW_LT" "$SRC; echo '=== RQT: lane detection (annotated) ==='; ros2 run rqt_image_view rqt_image_view /detect/image_lane" C-m
    VW_SG=$(tmux split-window -v -t "$VW" -P -F "#{pane_id}")
    tmux send-keys -t "$VW_SG" "$SRC; echo '=== RQT: sign detection (annotated) ==='; ros2 run rqt_image_view rqt_image_view /detect/image_traffic_sign" C-m
    tmux select-layout -t "$VW" tiled
fi

tmux set-option -t "$SESSION" -g remain-on-exit on \; set-option -g mouse on \; set-option -g history-limit 20000
tmux select-window -t "$SESSION:control"

echo "[OK] tmux session '$SESSION' ready (mission=$MISSION)"
echo "     windows: sim | camera | detect | control | views"
echo "     attach : tmux attach -t $SESSION"

if [ -t 0 ] && [ -t 1 ]; then
    tmux attach-session -t "$SESSION"
fi
