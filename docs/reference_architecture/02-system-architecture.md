# 02 — System architecture

## Layers

```
┌──────────────────────────────────────────────────────────────────────────┐
│ SIMULATION     Gazebo Classic · turtlebot3_autorace_2020 world           │
│                burger_cam robot · traffic-light plugin · barrier models  │
│                publishes: /camera/image_raw · /scan · /odom · /clock     │
└──────────────────────────────────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼───────────────────────────────────────┐
│ PERCEPTION     rectify_node → /camera/image_rect (+ /compressed)          │
│                  ├─ image_projection → /camera/image_projected            │
│                  │     └─ detect_lane → /detect/lane (Float64)            │
│                  └─ image_compensation → /camera/image_compensated        │
│                        ├─ traffic_light_state → /detect/traffic_light_state│
│                        ├─ detect_intersection_sign → /detect/traffic_sign │
│                        └─ yolo_sign_detector → /yolo/sign_detections      │
└──────────────────────────────────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼───────────────────────────────────────┐
│ CONTROL        control_lane → /control/cmd_vel   (lane following only)    │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │  intent
┌──────────────────────────────────▼───────────────────────────────────────┐
│ MISSION        mission_supervisor → /cmd_vel  (SOLE writer)               │
│                gates: light state · sign decision · LiDAR guard ·         │
│                staleness timeout · speed/steering clamps · watchdog       │
└──────────────────────────────────────────────────────────────────────────┘
                                   │
                              base controller (diff drive)
```

Lane following and object detection are **two separate branches** of the camera
pipeline, not one chain. `detect_lane` subscribes to `/camera/image_projected`;
the light and sign detectors subscribe to `/camera/image_compensated`. This is
verified from the running graph — see [Live graph](#live-graph-generated).

## Launch → node mapping

What each launch file starts and where the executable comes from. This mapping is
stable and hand-maintained; the **runtime** graph — who publishes what right now —
is generated from the live system in [Live graph](#live-graph-generated).

| Launch | Package:executable | Purpose |
| --- | --- | --- |
| `turtlebot3_autorace_2020.launch.py` | `turtlebot3_gazebo` | Gazebo world, `burger_cam`, traffic-light plugin |
| `intrinsic_rectify.launch.py` | `image_proc:rectify_node` | raw → rectified |
| `extrinsic_compensation.launch.py` | `turtlebot3_autorace_camera:image_compensation` | rectified → compensated |
| `detect_lane.launch.py` | `turtlebot3_autorace_detect:detect_lane` | lane detection |
| `detect_traffic_light_state.launch.py` | `turtlebot3_autorace_detect:traffic_light_state` | light state topic (this project) |
| `detect_sign.launch.py mission:=…` | `turtlebot3_autorace_detect:detect_intersection_sign` | template sign ids |
| `detect_yolo_sign.launch.py` | `turtlebot3_autorace_detect:yolo_sign_detector` | advisory YOLO detections (this project) |
| `control_race.launch.py` | `turtlebot3_autorace_mission:control_lane` + `mission_supervisor` | lane intent + the sole `/cmd_vel` writer |

## Topic semantics

Purpose, expected rate, and payload meaning. Rates are measured on this machine;
types and live publisher/subscriber counts are generated below.

| Topic | Rate | Meaning / notes |
| --- | --- | --- |
| `/camera/image_raw` | ~30 Hz | `rgb8`; no colour or compressed sibling — see [04](04-camera-pipeline.md) |
| `/camera/image_rect` | 29.9 Hz measured | Rectified; **this** is what compensation reads |
| `/camera/image_rect/compressed` | 30.0 Hz measured | Required by `image_compensation`'s default input |
| `/camera/image_compensated` | 30–33.6 Hz measured | Everything the light/sign detectors use |
| `/camera/image_projected` | ~30 Hz | Projected view — **the lane detector's input** |
| `/detect/lane` | ~30 Hz | `Float64` lane value driving `control_lane` |
| `/detect/lane_state` | ~30 Hz | `UInt8` lane availability (no subscriber today — see roadmap) |
| `/control/cmd_vel` | 10 Hz | Lane intent only — not the actuator topic |
| `/control/max_vel` | 1 Hz | Supervisor → `control_lane` speed cap |
| `/cmd_vel` | 10 Hz | **Owned exclusively by `mission_supervisor`** |
| `/detect/traffic_light_state` | 5 Hz heartbeat | `red` · `yellow` · `green` · `none` |
| `/detect/traffic_sign` | on detection | `1` intersection · `2` left · `3` right · `0` none |
| `/mission/state` | 10 Hz | Human-readable state for the monitor |
| `/yolo/sign_detections` | ~10 Hz | `vision_msgs/Detection2DArray`; advisory only |
| `/yolo/sign_state` | on change | `String` sign state from the YOLO detector |

## Live graph (generated)

Refresh with `./patches/ros2_ws/gen_ros_tables.sh` while the stack is up. The
generator reads `ros2 node list`, `ros2 node info` and `ros2 topic list -t` from
the running container, so this table cannot drift from reality — and it asserts
the invariants that actually break things: duplicate node names (stale process),
more than one `/cmd_vel` publisher, more than one publisher per camera topic.

<!-- BEGIN GENERATED: live graph -->
<!-- generated 2026-10-28 03:02 by patches/ros2_ws/gen_ros_tables.py; do not edit by hand -->
*Captured from the running container on 2026-10-28 03:02 (21 distinct nodes).*

### Live nodes and their topics

| Node | Publishes | Subscribes |
| --- | --- | --- |
| `/camera/image_compensation` | `/camera/image_compensated` | `/camera/image_rect/compressed` |
| `/camera/image_projection` | `/camera/image_projected` | `/camera/image_rect/compressed` |
| `/camera/rectify_node` | `/camera/image_rect/compressedDepth`, `/camera/image_rect/compressed`, `/camera/image_rect/theora`, `/camera/image_rect` | `/camera/camera_info`, `/camera/image_raw` |
| `/camera_driver` | `/camera/camera_info`, `/camera/image_raw/compressedDepth`, `/camera/image_raw/compressed`, `/camera/image_raw/theora`, `/camera/image_raw` | — |
| `/control_lane` | `/control/cmd_vel` | `/avoid_active`, `/avoid_control`, `/control/max_vel`, `/detect/lane` |
| `/detect_intersection_sign` | `/detect/image_traffic_sign/compressed`, `/detect/traffic_sign` | `/camera/image_compensated` |
| `/detect_lane` | `/detect/image_lane/compressed`, `/detect/lane_state`, `/detect/lane`, `/detect/white_line_reliability`, `/detect/yellow_line_reliability` | `/camera/image_projected` |
| `/gazebo` | `/performance_metrics` | — |
| `/mission_supervisor` | `/cmd_vel`, `/control/max_vel`, `/mission/state` | `/control/cmd_vel`, `/detect/traffic_light_state`, `/detect/traffic_sign`, `/odom`, `/scan` |
| `/robot_state_publisher` | `/robot_description` | `/joint_states` |
| `/rqt_gui_cpp_node_61040` | — | `/detect/image_traffic_light_state/compressed` |
| `/rqt_gui_cpp_node_61041` | — | `/camera/image_compensated` |
| `/rviz` | `/clicked_point`, `/move_base_simple/goal` | `/odom`, `/robot_description`, `/scan` |
| `/state_monitor` | — | `/detect/traffic_light_state`, `/detect/traffic_sign`, `/mission/state` |
| `/traffic_light_state` | `/detect/image_traffic_light_state/compressed`, `/detect/traffic_light_state` | `/camera/image_compensated` |
| `/transform_listener_impl_5b4a0207dc80` | — | — |
| `/turtlebot3_diff_drive` | `/odom` | `/cmd_vel` |
| `/turtlebot3_imu` | `/imu` | — |
| `/turtlebot3_joint_state` | `/joint_states` | — |
| `/turtlebot3_laserscan` | `/scan` | — |
| `/yolo_sign_detector` | `/yolo/annotated_image/compressed`, `/yolo/sign_detections`, `/yolo/sign_state` | `/camera/image_compensated` |

### Live topics (type, publishers, subscribers)

| Topic | Type | Pub | Sub |
| --- | --- | --- | --- |
| `/avoid_active` | `std_msgs/msg/Bool` | 0 | 1 |
| `/avoid_control` | `geometry_msgs/msg/Twist` | 0 | 1 |
| `/camera/camera_info` | `sensor_msgs/msg/CameraInfo` | 1 | 1 |
| `/camera/image_compensated` | `sensor_msgs/msg/Image` | 1 | 4 |
| `/camera/image_projected` | `sensor_msgs/msg/Image` | 1 | 1 |
| `/camera/image_raw` | `sensor_msgs/msg/Image` | 1 | 1 |
| `/camera/image_raw/compressed` | `sensor_msgs/msg/CompressedImage` | 1 | 0 |
| `/camera/image_raw/compressedDepth` | `sensor_msgs/msg/CompressedImage` | 1 | 0 |
| `/camera/image_raw/theora` | `theora_image_transport/msg/Packet` | 1 | 0 |
| `/camera/image_rect` | `sensor_msgs/msg/Image` | 1 | 0 |
| `/camera/image_rect/compressed` | `sensor_msgs/msg/CompressedImage` | 1 | 2 |
| `/camera/image_rect/compressedDepth` | `sensor_msgs/msg/CompressedImage` | 1 | 0 |
| `/camera/image_rect/theora` | `theora_image_transport/msg/Packet` | 1 | 0 |
| `/clicked_point` | `geometry_msgs/msg/PointStamped` | 1 | 0 |
| `/clock` | `rosgraph_msgs/msg/Clock` | 1 | 7 |
| `/cmd_vel` | `geometry_msgs/msg/Twist` | 1 | 2 |
| `/control/cmd_vel` | `geometry_msgs/msg/Twist` | 1 | 1 |
| `/control/max_vel` | `std_msgs/msg/Float64` | 1 | 1 |
| `/detect/image_lane/compressed` | `sensor_msgs/msg/CompressedImage` | 1 | 0 |
| `/detect/image_traffic_light_state/compressed` | `sensor_msgs/msg/CompressedImage, sensor_msgs/msg/Image` | 1 | 1 |
| `/detect/image_traffic_sign/compressed` | `sensor_msgs/msg/CompressedImage` | 1 | 0 |
| `/detect/lane` | `std_msgs/msg/Float64` | 1 | 1 |
| `/detect/lane_state` | `std_msgs/msg/UInt8` | 1 | 0 |
| `/detect/traffic_light_state` | `std_msgs/msg/String` | 1 | 2 |
| `/detect/traffic_sign` | `std_msgs/msg/UInt8` | 1 | 2 |
| `/detect/white_line_reliability` | `std_msgs/msg/UInt8` | 1 | 0 |
| `/detect/yellow_line_reliability` | `std_msgs/msg/UInt8` | 1 | 0 |
| `/imu` | `sensor_msgs/msg/Imu` | 1 | 0 |
| `/joint_states` | `sensor_msgs/msg/JointState` | 1 | 1 |
| `/mission/state` | `std_msgs/msg/String` | 1 | 1 |
| `/move_base_simple/goal` | `geometry_msgs/msg/PoseStamped` | 1 | 0 |
| `/odom` | `nav_msgs/msg/Odometry` | 1 | 2 |
| `/parameter_events` | `rcl_interfaces/msg/ParameterEvent` | 22 | 13 |
| `/performance_metrics` | `gazebo_msgs/msg/PerformanceMetrics` | 1 | 0 |
| `/robot_description` | `std_msgs/msg/String` | 1 | 1 |
| `/rosout` | `rcl_interfaces/msg/Log` | 23 | 0 |
| `/scan` | `sensor_msgs/msg/LaserScan` | 1 | 2 |
| `/tf` | `tf2_msgs/msg/TFMessage` | 2 | 1 |
| `/tf_static` | `tf2_msgs/msg/TFMessage` | 1 | 1 |
| `/yolo/annotated_image/compressed` | `sensor_msgs/msg/CompressedImage` | 1 | 0 |
| `/yolo/sign_detections` | `vision_msgs/msg/Detection2DArray` | 1 | 0 |
| `/yolo/sign_state` | `std_msgs/msg/String` | 1 | 0 |

### Health assertions

- ✔ no duplicate node names
- ✔ `/cmd_vel` has exactly one publisher
- ✔ camera topics have exactly one publisher each
<!-- END GENERATED: live graph -->


## Ownership rules (the important part)

1. **`/cmd_vel` has exactly one publisher: `mission_supervisor`.**
   `control_lane` was remapped off `/cmd_vel` for this reason. This is what makes
   a stop final: the lane controller cannot "helpfully" keep driving through a
   red light. ([ADR 0001](adr/0001-single-cmd-vel-owner.md))

2. **Detectors publish state, never commands.** `traffic_light_state` says
   `red`; it does not brake. Deciding is the supervisor's job, so all stop
   reasons compose.

3. **Missing data has a direction.** Stale light state or a stale lane command
   makes the robot *stop* (`state_timeout` 2.0 s, `cmd_timeout` 0.5 s), never
   continue. The one exception is the light: `none` (no light in view) allows
   driving after `unknown_hold` 1.0 s — see [06](06-mission-control.md).

## Launch topology

| Launch file | Brings up |
| --- | --- |
| `turtlebot3_autorace_2020.launch.py` | Gazebo world + burger_cam + traffic light plugin |
| `intrinsic_rectify.launch.py` | Standalone `rectify_node` (not the composable container) |
| `extrinsic_compensation.launch.py` | `image_compensation` with raw **and** compressed remaps |
| `detect_lane.launch.py` | Upstream lane detector |
| `detect_traffic_light_state.launch.py` | `traffic_light_state` (min_blob_area, confirm_frames, process_every_n, publish_debug_image) |
| `detect_sign.launch.py mission:=…` | Template sign detector; the mission selects the template set |
| `detect_yolo_sign.launch.py` | YOLOv8 detector (confidence_threshold, device, output_topic, publish_annotated) |
| `control_race.launch.py` | `control_lane` + `mission_supervisor` (max_vel, stop_states, wall_dist) |

`control_race.launch.py` passes `max_vel=0.16`, `stop_states=red,yellow`,
`wall_dist=0.45` to the supervisor and remaps `control_lane`'s `/control/lane`
subscription to `/detect/lane`.

## Startup ordering

The tmux launcher staggers the nodes because Gazebo takes ~20 s to come up and
each detector needs an image topic before it can initialise:

| t (s) | Node |
| --- | --- |
| 0 | Gazebo |
| 0 | rqt_image_view ×2, rviz2 (GUI panes open immediately, stay blank until data) |
| 20 | rectify_node |
| 24 | image_compensation |
| 30 | detect_lane |
| 32 | traffic_light_state |
| 34 | yolo_sign_detector |
| 36 | template sign detector |
| 38 | control_race (control_lane + mission_supervisor) |
| 40 | state monitor |
| 42 | `/cmd_vel` rate monitor |

Before starting, the launcher kills leftover simulation processes and removes
stale FastRTPS shared memory — two simulators publishing competing `/odom` is a
failure mode that looks like random robot behaviour.
