# 11 — Troubleshooting

Every entry below is a failure that actually happened in this project.

## Robot and mission

### The robot does not move at all

Check, in order:

1. **Is the container running?** `./ros2_docker.sh status`
2. **Is the tmux session alive?** `./ros2_docker.sh racewin` (no session → relaunch)
3. **Is `/cmd_vel` publishing?** `ros2 topic hz /cmd_vel` — should be 10 Hz
4. **What is the mission state?** control pane 1 (`LIGHT/SIGN/MISSION`)

| State | Meaning | Action |
| --- | --- | --- |
| `hold:light:red` / `yellow` | Waiting for green | Wait; the cycle is red 5 s → yellow 1 s → green 5 s |
| `hold:sign` | Paused to decide | Normal, 1.2 s |
| `hold:obstacle` | LiDAR stop | Something is inside 0.16 m in front |
| `hold:no-lane-cmd` | No lane command | Lane detector lost; see below |

### It stops at the junction and never turns

- The sign id must be a **direction** (`2`/`3`); `1` (plain intersection sign)
  deliberately never turns.
- Check `SIGN=` in the monitor. If it is always `0`, the identifier is not
  arriving: verify `mission=intersection` (construction templates do not contain
  the arrow).
- If `SIGN` flickers 2↔3, the majority vote may fail to reach 60 % — check the
  detector pane for how long it holds each value.

### It turns the wrong way at a T junction

The template matcher flickers between left and right. Confirm the decision line:

```
DECIDE right (turn 1/2): rotating -90 deg ...
```

If it says `left`, the detector's majority in that 2 s window was wrong. Fallback
levers: raise the vote window, or replace the template detector with a geometric
one (roadmap).

### It turns, then turns again and ends up facing backwards

`turn_rearm_distance` (1.2 m) should prevent this. If it still happens, the robot
travelled more than 1.2 m while the sign stayed in view — the re-arm needs to be
distance **and** time based.

### It spins in place instead of driving

- Frequent `turn` states with no movement: the lane is lost and the LiDAR thinks
  there is a corridor. Check `scan_quadrant_probe.py` output.
- If all four sectors are very small (~0.7 m), the robot is in a pocket and should
  now reverse out. If it does not, check `recovery_rear_clear` — the rear may be
  blocked, in which case turning in place is the only option.

### It hits the white barrier bars

1. Run `reverse_audit.py` — if any reversal shows `rear < 0.30 m`, the rear guard
   is not working.
2. Check `scan_quadrant_probe.py` — if `rear` is always `inf`, the rear sector is
   broken (angle wrapping).
3. If it happens while driving *forward*, that is the unguarded case: wall
   avoidance is a correction, not a clamp. Lower `wall_dist` or `max_vel`.

---

## Camera

### No image in rqt / rqt pane died instantly

```bash
docker exec ros2-humble bash -c 'command -v rqt_image_view'
ros2 pkg executables rqt_image_view      # must print rqt_image_view
```

If missing:

```bash
docker exec ros2-humble bash -c \
  'apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y \
     ros-humble-rqt-image-view ros-humble-rqt-common-plugins'
```

Remember it must be run as `ros2 run rqt_image_view rqt_image_view /topic`.

### `/camera/image_compensated` is silent

| Check | Expected |
| --- | --- |
| `ros2 topic hz /camera/image_rect` | ≈ 29.9 Hz |
| `/camera/image_rect/compressed` exists | yes |
| `image_compensation` remaps both raw and compressed | see [04](04-camera-pipeline.md) |
| `/dev/shm/fastrtps_*` removed before launch | yes |

### Two simulators / robot teleports / light changes too fast

```bash
pgrep -a gzserver | wc -l     # must be 1
```

If not:

```bash
./ros2_docker.sh racestop      # kills panes, session, nodes, purges shm
./ros2_docker.sh race
```

---

## Build and environment

### `colcon build` fails after installing ultralytics

`setuptools` 84 removed `setup.py develop`. Pin the environment:

```bash
pip install 'setuptools==79.0.1' 'packaging==24.2'
```

### `fastrtps_port<NNNN> open_and_lock_file failed`

Stale shared memory from SIGKILLed processes:

```bash
rm -f /dev/shm/fastrtps_* /dev/shm/sem.fastrtps_*
```

The tmux launcher does this automatically.

### numpy / cv2 import errors in YOLO

This stack needs `numpy<2`:

```bash
pip install 'numpy==1.26.4' 'opencv-python<4.10'   # cv2 4.9.0
```

Current container versions: `ultralytics 8.4.191`, `torch 2.14.1+cu130`,
`cv2 4.9.0`, `numpy 1.26.4`.

### Permission denied editing a file

`~/ros2_humble_ws` is root-owned. Edit via the container:

```bash
docker cp file.py ros2-humble:/root/ros2_humble_ws/src/...
docker exec -i ros2-humble python3 - <<'EOF'
# patch inside the container
EOF
```

---

## tmux and GUIs

### A window is empty / a launch never ran

`select-layout tiled` **renumbers pane indices**. The launcher addresses panes by
captured `#{pane_id}`; if you add a pane manually, do the same.

### The terminal returns to the prompt instead of attaching

`cmd_race` only auto-attaches when stdin and stdout are TTYs. From a script, use
`./ros2_docker.sh raceattach`.

### GUIs are blank

Normal at first: they open at t=0 and populate when data arrives. If they stay
blank after ~30 s, the camera pipeline is down — see above.

---

## Diagnostic command cheat sheet

```bash
./ros2_docker.sh status                 # container + AutoRace
./ros2_docker.sh racewin                # windows/panes
./ros2_docker.sh logs all               # every pane buffer
./ros2_docker.sh racestop               # clean stop
docker exec ros2-humble pgrep -a gzserver
docker exec ros2-humble bash -c 'source /opt/ros/humble/setup.bash; ros2 node list'
docker exec ros2-humble bash -c 'source /opt/ros/humble/setup.bash; ros2 topic list'
```
