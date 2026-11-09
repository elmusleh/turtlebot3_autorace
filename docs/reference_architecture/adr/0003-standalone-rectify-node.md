# ADR 0003 — A standalone `rectify_node` instead of a component container

**Status:** Accepted (in force)

## Context

The upstream calibration pipeline brings up image rectification as an
`rclcpp_components` component loaded into a container
(`intrinsic_camera_calibration.launch.py`).

In this image the container hangs at load. The visible symptom is that
`/camera/image_rect` never appears; every downstream detector (lane, light, signs)
then starts and idles forever, and the robot sits in `hold:no-lane-cmd`. Nothing
reports an error — the pipeline is simply absent.

## Decision

Launch `rectify_node` as a **plain node process** in its own launch file,
`intrinsic_rectify.launch.py`, with the camera info and calibration file passed as
parameters.

## Consequences

**Good**
- Works reliably: measured `/camera/image_rect` at **29.932 Hz**.
- If it dies, the tmux pane shows a process exit instead of a silently missing
  topic inside a container.
- Easy to restart independently of the rest of the pipeline.

**Bad**
- Loses intra-process communication benefits of components (irrelevant here at
  30 Hz / 640×480).
- Diverges from upstream documentation, so an upgrade needs this checked.

## Verification

```bash
timeout 6 ros2 topic hz /camera/image_rect        # ≈ 29.9 Hz
ros2 node list | grep rectify                      # /rectify_node
```
