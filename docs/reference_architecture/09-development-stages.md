# 09 — Development stages (step by step)

The project was not built from a design document; it was built by chasing
failures. This document records each stage in the order it happened: the symptom
observed, the root cause found, the change made, and how it was verified.

Reading this top to bottom is the fastest way to understand why the code looks the
way it does.

| Stage | Theme | Outcome |
| --- | --- | --- |
| 0 | Environment | Container + workspace build reproducibly |
| 1 | Upstream demos | Gazebo, teleop, RViz runnable from one script |
| 2 | Camera pipeline | `/camera/image_compensated` alive at 30 Hz |
| 3 | Traffic light state | A topic that actually says red/yellow/green |
| 4 | Command gating | One owner of `/cmd_vel` |
| 5 | Observability | All nodes visible in tmux |
| 6 | GUIs | rqt + RViz open instantly, terminal attaches |
| 7 | Sign perception | Direction ids, majority vote, YOLO advisory |
| 8 | Junction manoeuvre | Correct right turn at the T junction |
| 9 | Safety | LiDAR angle fix, rear guard, wall avoidance |
| 10 | Navigation smartness | Coast instead of spin, pocket detection |
| 11 | Verification tooling | Probes for every claim |
| 12 | Documentation | This documentation set |

---

## Stage 0 — Environment

**Symptom:** nothing ran; the project was a collection of notes and a PDF of a
previous chat.

**Work:**
- `install.sh` — checks prerequisites (docker, git, xhost), clones TurtleBot3 +
  AutoRace into `~/ros2_humble_ws`, creates and starts the `ros2-humble`
  container from `osrf/ros:humble-desktop-full`, installs Gazebo Classic,
  builds the workspace, prints next steps.
- `ros2_docker.sh` — host entry point: `start/stop/restart/shell/status/clean`,
  environment helpers, topic and log helpers.

**Verified:** container up, `colcon build` clean.

**Gotcha learned:** the host workspace is root-owned; every edit must go through
`docker exec` / `docker cp`.

---

## Stage 1 — Upstream demos

**Symptom:** needed a baseline that proves simulation, camera and control work
before adding anything.

**Work:** demo menu (`demo1`…`demo5`), teleop, RViz, rqt helpers, `stopall` /
`startall` for full-stack lifecycle.

**Verified:** Gazebo world loads, teleop moves the robot, RViz shows the model.

---

## Stage 2 — Camera pipeline

**Symptom:** detection nodes started but never produced output. The image topics
downstream of the camera were silent.

**Diagnosis — four separate faults, found one at a time:**

1. `burger_cam` publishes `rgb8`, so `/camera/image_rect_color` **never exists**.
   Every launch that waits for it starves.
2. `intrinsic_camera_calibration.launch.py` loads the rectify component into a
   `rclcpp_components` container that hangs at load in this image.
3. `image_compensation` subscribes to `/camera/image_input/compressed` by
   default; feeding only the raw `Image` topic leaves it silent.
4. Stale FastRTPS shared memory (`/dev/shm/fastrtps_*`) from SIGKILLed nodes
   breaks new participants: `fastrtps_port7413: open_and_lock_file failed`.

**Changes:**
- `intrinsic_rectify.launch.py` — standalone `rectify_node` instead of the
  composable container.
- `extrinsic_compensation.launch.py` — reads `/camera/image_rect` and remaps
  **both** `/camera/image_input` and `/camera/image_input/compressed`.
- Launcher removes `/dev/shm/fastrtps_*` before starting.

**Verified:**

```
/camera/image_rect          ≈ 29.932 Hz
/camera/image_rect/compressed ≈ 30.02 Hz
/camera/image_compensated   30–33.6 Hz
```

([ADR 0003](adr/0003-standalone-rectify-node.md), [ADR 0004](adr/0004-compensation-reads-rect.md))

---

## Stage 3 — Traffic light state

**Symptom:** the robot drove through a red light. The stock `detect_traffic_light`
node draws an annotation but publishes **no state topic** — nothing in the system
knew the light colour.

**Work:** new node `traffic_light_state.py`.

**Then three more failures, in sequence:**

1. **Robot drove on red.** Cause: the node published only on change; the consumer
   treated 2 s of silence as stale and resumed. Fix: publish a 5 Hz heartbeat at
   all times.
2. **`red` latched permanently.** Cause: the static red start barrier at the
   bottom of the frame is a big red blob. Fix: crop ROI
   (`roi_top` 0.28, `roi_bottom` 0.72, `roi_left` 0.47) and add a shape filter
   (`lamp_area`: area 120–4000 px², aspect 0.45–2.2, extent ≥ 0.45).
3. **`yellow` latched while driving.** Cause: the yellow centre line entering the
   ROI is a long thin band. The same shape filter fixes it ("a lamp is compact,
   road paint is not").

Also: Gazebo renders green at hue ≈ **102**, so the green HSV range had to be
widened or green was never detected.

**Verified:** red → `hold:light:red`, green → `drive`, latch after passing.
Plugin cycle confirmed in `traffic_light_plugin.cpp`: red 5 s → yellow 1 s →
green 5 s.

([ADR 0002](adr/0002-traffic-light-heartbeat.md))

---

## Stage 4 — Command gating

**Symptom:** even with a working light state, nothing could *stop* the robot: the
lane controller published `/cmd_vel` directly.

**Work:** `mission_supervisor.py` becomes the only publisher of `/cmd_vel`;
`control_lane` is remapped to publish `/control/cmd_vel` (intent). The supervisor
applies: light gating, sign pause, LiDAR stop, clamps, watchdog.

**Verified:** `ros2 topic info /cmd_vel` shows one publisher; stops are absolute.

([ADR 0001](adr/0001-single-cmd-vel-owner.md))

---

## Stage 5 — Observability (tmux)

**Symptom:** "add the terminal windows in tmux to show the output."

**Work:** `run_tb3_race_tmux.sh` with five windows (`sim`, `camera`, `detect`,
`control`, `views`).

**Failure found during this stage:** `tmux select-layout tiled` **renumbers pane
indices**, so a later `send-keys -t session:window.3` landed in the wrong pane and
a launch never ran. Fix: capture `#{pane_id}` for every pane into a variable and
address panes by id, never by index.

**Second failure:** a killed session left `gzserver` alive; two simulators then
published two `/odom` and two camera streams, producing impossible robot
behaviour (teleporting, light changing too fast). Fix: pre-launch `pkill -9` of
every known process (bracketed patterns so the script does not match itself) plus
the FastRTPS shm purge.

**Verified:** one `gzserver`, correct per-window commands.

---

## Stage 6 — GUIs and terminal attach

**Symptom:** "The terminal, rqt, Rviz2 etc are not open instantly."

**Diagnosis — three faults:**
1. `rqt_image_view` was **not installed** in the image. The pane died instantly
   with `command not found`, so no image window ever appeared. Fix:
   `apt-get install ros-humble-rqt-image-view ros-humble-rqt-common-plugins`.
2. GUIs were launched after a long sleep. Fix: launch them at t=0; they stay blank
   and populate themselves when data arrives.
3. `./ros2_docker.sh race` returned to the prompt instead of attaching. Fix:
   attach directly when stdin/stdout are a TTY.

Also learned: `rqt_image_view` is a **plugin**, not a PATH binary — it must be
started as `ros2 run rqt_image_view rqt_image_view <topic>`.

**Verified:** 2× `rqt_image_view` + `rviz2` running ~15 s after launch.

---

## Stage 7 — Sign perception

**Symptom:** "the robot is not detecting signs and fall and flying in a wrong way",
then "the robot stopped in front of the sign".

**Diagnosis:**
- The default mission was `construction`, whose template set does **not** contain
  the T-junction arrow → `/detect/traffic_sign` stayed `0` forever, so nothing
  triggered. Fix: default mission `intersection`.
- The `TrafficSign` enum is `1 = intersection`, `2 = left`, `3 = right`.
- The matcher **flickers** between 2 and 3 on the same sign. Fix: 4 s history,
  ≥ 60 % majority over 2 s before acting.
- YOLO was added as an independent visual check (`yolo_sign_detector.py`), with
  `process_every_n=3` and `imgsz=320` to keep the CPU usable; it is advisory only
  because COCO has no arrow-sign class.

**Verified:** `Detect right sign` continuous; `SIGN=3` dominant in the monitor.

([ADR 0005](adr/0005-intersection-default-mission.md))

---

## Stage 8 — Junction manoeuvre

**Symptom:** "The robot stopped in front of the sign to move only right direction
in the T junction" (it stopped, then later turned the wrong way).

**Four distinct bugs, each found by reading a run log:**

| Bug | Evidence | Fix |
| --- | --- | --- |
| Turn cut short at 41° | `turn complete (41 deg) - lane re-acquired` while still facing the wall | Always execute the full signalled angle; extension only up to 1.4× |
| Plain junction sign treated as a direction | `turn complete (139 deg)` after a blind 2.4 s rotation | Sign `1` never turns |
| Same sign triggered a second turn | `DECIDE right (turn 1/2)` → immediately another `DECIDE right (turn 2/2)` 129° | Require `turn_rearm_distance` 1.2 m driven since the last turn |
| Wrong direction taken on a right-only sign | `DECIDE left` on the right sign | Majority vote over recent frames |

**Verified:**

```
DECIDE right (turn 1/2): rotating -90 deg at 1.2 rad/s (1.3s min, 1.8s max)
turn complete (93 deg) - lane re-acquired

yaw probe: start +103.2 deg → net turn -104.1 deg → RIGHT (clockwise)
```

([ADR 0006](adr/0006-sign-turn-semantics.md))

---

## Stage 9 — Safety

**Symptom A:** "the robot is not moving" — it stopped 0.120 m from the sign post
and never recovered. The LiDAR guard was a one-way trap.
**Fix:** recovery manoeuvre (reverse ~0.2 m, then turn); later refined.

**Symptom B:** "the robot hit the white obstacle bars … while moving behind it."
**Root cause:** the guard only looked forward; the recovery reversed **blind**.
**Fix:** rear sector + `recovery_rear_clear` 0.30 m refusal + `recovery_rear_abort`
0.14 m mid-reversal abort.

**Symptom C (found while fixing B):** the "right" side never measured anything.
**Root cause:** this LiDAR publishes **[0, 2π) with `angle_min = 0`**, so
`-1.0 <= angle < -0.15` can never match, and rays at 340–360° were dropped from
the forward cone. Side steering was therefore left-only and asymmetric.
**Fix:** wrap angles with `atan2(sin, cos)` before every sector test.

**Verified:** `reverse_audit.py` over 150 s — 3 reversal episodes, minimum rear
distance **0.50 m**, zero reversals with less than 0.30 m behind.

([ADR 0007](adr/0007-rear-guard.md))

---

## Stage 10 — Navigation smartness

**Symptom:** "the robot is not identifing the correct path quickly, it sometimes
spin on its position to see around. Can it be faster and smarter?"

**Diagnosis:** the lane-loss path was "stop and rotate in fixed sweeps", which is
both slow and looks lost, and it ignored the LiDAR entirely.

**Changes:**
- **Coast** along the most-open LiDAR direction at 0.07 m/s instead of stopping.
- **Junction vs dead end** discrimination via `pocket_range` (1.2 m): pockets get
  a reverse, junctions get a short turn.
- **Escape budget refills** after 2 m of progress.
- **Faster:** `max_vel` 0.12 → 0.16 m/s, `turn_speed` 0.9 → 1.2 rad/s, sign pause
  2.0 → 1.2 s, `search_after` 2.5 → 1.0 s.

**Verified — distance per run:**

```
5.4 m / 155 s  (before)
7.0 m / 155 s  (+ coast, faster rates)
8.47 m / 180 s (+ pocket detection)
11.45 m / 240 s, still moving at the end (+ budget reset)
```

State mix: ~53 % driving/coasting, ~14 % turning.

([ADR 0008](adr/0008-coast-instead-of-spin.md))

---

## Stage 11 — Verification tooling

Every claim above is reproducible because each one has a probe:

| Tool | Answers |
| --- | --- |
| `track_odom.py` | How far did it travel? Where did it stall? |
| `yaw_probe.py` | Which way did it actually turn, and by how much? |
| `reverse_audit.py` | Did any reversal happen with something behind? |
| `scan_quadrant_probe.py` | Are all four LiDAR sectors measured correctly? |
| `state_monitor.py` | What is the mission state right now, in one line? |
| `ros2 topic hz` | Is the camera/`cmd_vel` actually alive? |

See [10-verification.md](10-verification.md).

---

## Stage 12 — Documentation

This directory. Written after the fact so the next engineer does not have to
rediscover: the `[0, 2π)` LiDAR convention, the `rgb8` camera's missing colour
topic, the `rqt_image_view` plugin invocation, the pane-id renumbering trap, and
the sign-flicker majority vote.
