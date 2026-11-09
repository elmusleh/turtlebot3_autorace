# 04 — Camera pipeline

The camera is the most fragile part of this stack, and every downstream failure
was originally a camera failure. This document explains what the chain is, why it
was rebuilt, and what to check when images stop.

## Chain

```
/camera/image_raw  (rgb8, ~30 Hz, no compressed sibling)
        │
        └─ rectify_node ────────────────► /camera/image_rect        (~29.9 Hz, rgb8)
                                             │
                                             ├─ /camera/image_rect/compressed (~30 Hz)
                                             │      │
                                             │      ├─ image_projection ──► /camera/image_projected
                                             │      │                          └─► detect_lane
                                             │      │
                                             │      └─ image_compensation ─► /camera/image_compensated
                                             │                                 ├─► traffic_light_state
                                             │                                 ├─► detect_intersection_sign
                                             │                                 └─► yolo_sign_detector
                                             └─ /camera/image_rect  (raw, currently unsubscribed)
```

Two branches, not one chain:

| Branch | Node | Output | Consumed by |
| --- | --- | --- | --- |
| Lane | `image_projection` | `/camera/image_projected` | `detect_lane` |
| Objects | `image_compensation` | `/camera/image_compensated` | light, sign, YOLO |

Both read `/camera/image_rect/compressed` (their default input), which is why that
remap is essential.

Everything downstream of `image_compensated` — the light and sign detectors, and
YOLO — goes blind if that topic dies, and the robot then sits in
`hold:no-lane-cmd` (via the lane branch) or drives without light gating.

## Why it had to be rebuilt

### 1. The camera publishes `rgb8` with no colour image

`burger_cam` produces `rgb8`. The stock calibration launch expects an
`image_rect_color` topic that simply never exists for this camera:

```
$ ros2 topic list | grep camera
/camera/image_raw
/camera/image_rect
/camera/image_rect/compressed
/camera/image_compensated
```

There is no `/camera/image_rect_color`. Any launch file that waits for it starves
and the pipeline never starts. ([ADR 0004](adr/0004-compensation-reads-rect.md))

### 2. The stock intrinsic launch hangs

`intrinsic_camera_calibration.launch.py` loads the rectify component into a
`rclcpp_components` container, which hangs at load in this image. Replaced by a
standalone node launch:

```python
# patches/ros2_ws/launch/intrinsic_rectify.launch.py
Node(package='image_proc', executable='rectify_node', ...)
```

Result: `/camera/image_rect` at 29.932 Hz. ([ADR 0003](adr/0003-standalone-rectify-node.md))

### 3. `image_compensation` subscribes to a compressed topic by default

The upstream `image_compensation` node subscribes to
`/camera/image_input/compressed`. Feeding it only the raw `Image` leaves it
silent. Both remaps are required:

```python
remappings=[
    ('/camera/image_input', '/camera/image_rect'),
    ('/camera/image_input/compressed', '/camera/image_rect/compressed'),
]
```

That second line was the difference between "compensation never publishes" and
30 Hz output.

### 4. Stale FastRTPS shared memory kills the pipeline silently

After a `SIGKILL`, `/dev/shm/fastrtps_*` can be left behind and new participants
fail with `fastrtps_port7413: open_and_lock_file failed`. The launcher removes
them before starting:

```bash
rm -f /dev/shm/fastrtps_* /dev/shm/sem.fastrtps_*
```

### 5. Two simulators = random behaviour

A killed tmux session leaves `gzserver` alive. Two `gzserver` processes publish
two `/odom` streams and two `/camera/image_raw` streams; the robot then appears to
teleport and the light appears to change too fast. The launcher kills all known
simulation processes first (patterns are bracketed like `[g]zserver` so the script
does not match itself).

## Health checks

```bash
# Rates
docker exec ros2-humble bash -c '
  source /opt/ros/humble/setup.bash; source /root/ros2_humble_ws/install/setup.bash
  timeout 6 ros2 topic hz /camera/image_rect'
docker exec ros2-humble bash -c '
  source /opt/ros/humble/setup.bash; source /root/ros2_humble_ws/install/setup.bash
  timeout 6 ros2 topic hz /camera/image_compensated'

# Is anything actually listening?
docker exec ros2-humble bash -c '
  source /opt/ros/humble/setup.bash; source /root/ros2_humble_ws/install/setup.bash
  ros2 topic info -v /camera/image_compensated | head -20'

# Only one simulator?
docker exec ros2-humble bash -c 'pgrep -a gzserver | wc -l'   # expect 1
```

Healthy values: `/camera/image_rect` ≈ 29.9 Hz, `/camera/image_compensated`
30–33.6 Hz, exactly one `gzserver`.

## Known limitation

This project does **not** run the upstream extrinsic calibration GUI. The
compensation node runs with its default parameters, which means `detect_lane`'s
back-projection is only approximately correct. That mismatch is the leading
hypothesis for the lane detector losing the line at the tunnel.
See [13-roadmap.md](13-roadmap.md).

## Debugging tips

- Watch pane 0 of the `views` window: it shows `/camera/image_compensated`
  directly. If that image is black, the problem is upstream of detection.
- If the image is fine but `Lane state: 0` persists, the problem is the detector's
  parameters or the projection — not the camera.
- `ros2 topic info -v` reveals whether the subscribers are wrong (a node
  listening on `/camera/image_rect_color` shows up as a starving subscription).
