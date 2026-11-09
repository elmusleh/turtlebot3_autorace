# ADR 0004 — Compensation reads the rectified image, with both remaps

**Status:** Accepted (in force)

## Context

Two facts about this camera broke the upstream extrinsic compensation launch:

1. `burger_cam` publishes **`rgb8`**, so `/camera/image_rect_color` never exists.
   Any launch waiting for the colour rectified image waits forever. Measured topic
   list:

   ```
   /camera/image_raw
   /camera/image_rect
   /camera/image_rect/compressed
   /camera/image_compensated
   ```

2. The `image_compensation` node subscribes to
   **`/camera/image_input/compressed`** by default, not to the raw `Image` topic.
   Remapping only `/camera/image_input` leaves the node with no input, so it never
   publishes — another silent failure.

## Decision

`extrinsic_compensation.launch.py`:

- feeds the node from `/camera/image_rect` (which exists), and
- remaps **both** input topics:

```python
remappings=[
    ('/camera/image_input', '/camera/image_rect'),
    ('/camera/image_input/compressed', '/camera/image_rect/compressed'),
]
```

## Consequences

**Good**
- The pipeline runs: `/camera/image_compensated` at 30–33.6 Hz, which is what every
  detector subscribes to.
- Works with an `rgb8` camera without needing a colour conversion stage.

**Bad / accepted risk**
- Compensation runs with **default extrinsic parameters**, so the projection is
  approximate. `detect_lane` was designed for properly calibrated
  back-projection; this mismatch is the leading suspect for the lane detector
  losing the line at the tunnel (see [roadmap](../13-roadmap.md) P1).
- A real fix means running the upstream calibration toolkit once. Deferred
  deliberately because it is a GUI-driven, one-off procedure with its own failure
  modes, and the current approximation keeps the course runnable.

## Verification

```bash
timeout 6 ros2 topic hz /camera/image_rect          # ≈ 29.9 Hz
timeout 6 ros2 topic hz /camera/image_rect/compressed
timeout 6 ros2 topic hz /camera/image_compensated   # 30–33.6 Hz
ros2 topic info -v /camera/image_compensated | head -20
```
