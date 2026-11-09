# 05 — Perception

Three detectors run in the `detect` window. Only two of them are control inputs;
YOLO is advisory.

| Detector | Topic | Used by the supervisor? |
| --- | --- | --- |
| `traffic_light_state` | `/detect/traffic_light_state` | **Yes** — gates all driving |
| `detect_intersection_sign` (template) | `/detect/traffic_sign` | **Yes** — triggers the junction turn |
| `yolo_sign_detector` | `/yolo/sign_detections` | No — logged/visual only |

---

## 1. Traffic light state

**File:** `patches/ros2_ws/nodes/traffic_light_state.py`
**Launch:** `detect_traffic_light_state.launch.py`

### Why it exists

The upstream `detect_traffic_light` node draws an annotation but publishes **no
state topic**. Nothing in the system could answer "is it green?" — which is why
the robot originally drove through a red light. This node answers exactly that
question and nothing else.

### How it works

1. Subscribe to `/camera/image_compensated` (both `Image` and `CompressedImage`).
2. Crop the region of interest where the lamp actually appears:

   | Parameter | Value | Why |
   | --- | --- | --- |
   | `roi_top` | 0.28 | above this is sky/wall |
   | `roi_bottom` | 0.72 | below this is the static red start barrier |
   | `roi_left` | 0.47 | lamp is on the right half |
   | `roi_right` | 1.0 | — |

   Without this crop, the permanently red start barrier in the bottom of the
   frame latched `red` forever.

3. Threshold in HSV. Green in this world renders at hue ≈ 102 (not the textbook
   ~60), so the green range is widened accordingly.
4. Keep only blobs that look like a lamp (`lamp_area()`):
   - area between `min_blob_area` 120 and `max_blob_area` 4000 px²,
   - aspect ratio 0.45–2.2,
   - extent (`area / (w*h)`) ≥ 0.45.

   The extent/aspect filter is what stops the yellow centre line and the red
   barrier from being read as a lamp: "a lamp is compact, road paint is a long
   thin band."
5. Debounce: `confirm_frames` 3 consecutive frames with `hold_time` 0.6 s.
6. Publish `red` / `yellow` / `green` / `none` on `/detect/traffic_light_state` at
   `publish_rate` 5 Hz — **as a heartbeat**, even when the value does not change.
7. Optionally publish an annotated image to
   `/detect/image_traffic_light_state/compressed` (`publish_debug_image`), which
   `rqt_image_view` shows in the `views` window.

### The heartbeat decision

The first version published only on change. The supervisor treated "no message
for 2 s" as stale and stopped treating the light as red — so the robot drove off
on red. A detector that is *thinking* and a detector that is *dead* must look
different. The 5 Hz heartbeat makes them look different.
([ADR 0002](adr/0002-traffic-light-heartbeat.md))

### Ground truth for behaviour

The Gazebo plugin (`turtlebot3_gazebo/src/traffic_light_plugin.cpp`) runs a fixed
cycle:

```
red 5 s → yellow 1 s → green 5 s → (repeat)
```

Any report of "the light changes too fast" was a **detection** problem (red
barrier, wrong green hue, or two simulators), never a plugin problem.

---

## 1b. The lane detector used to crash when it lost the lane

`detect_lane` (upstream) set `self.is_center_x_exist = True` **unconditionally**,
but `centerx` is only computed inside three inner branches. When none of them ran
— i.e. exactly when the lane is not visible — the publish path executed
`centerx.item(350)` on an unbound variable:

```
UnboundLocalError: local variable 'centerx' referenced before assignment
msg_desired_center.data = centerx.item(350)
[ERROR] process has died [pid 61554, exit code 1]
```

With no respawn, that permanently removed the lane input. The supervisor then had
no lane command, fell back to coasting and open-space turns, and the robot drove
**off the marked lane** — reported as "the robot crossed and walked away from the
yellow and white lines".

**Fixes** (both in `patches/ros2_ws/upstream/`):

1. `detect_lane.py` — the flag now starts `False` and is set only in the branches
   that actually compute `centerx` (5 places), plus both publishes are guarded
   with `centerx is not None`. Losing the lane now reports `lane_state = 0`
   instead of killing the node.
2. `detect_lane.launch.py` — `respawn=True, respawn_delay=2.0`, so any future
   exception in this node self-heals instead of ending the run.

Verified: `/detect/lane` 9.75 Hz, `lane_state = 2` with both lines visible, and
zero `UnboundLocal`/`died` lines over multi-minute runs.

## 1c. Reference line changes after the junction

The course rule: after the T junction the **white edge line** is the reference,
until the long white block, where the rule is "take your right".

`detect_lane` has no flag for "white only", so the supervisor empties the yellow
HSV range at runtime via `/detect_lane/set_parameters`
(`hue_l = 179 > hue_h = 10` ⇒ no pixel can match), which forces the detector's
white-only branch (`lane_state = 3`, centre = white fit − 280 px).

* Switch happens when a **sign** turn completes (`white_line_after_turn`).
* Verified live: yellow reliability 100 → **0**, white reliability 100,
  `lane_state = 3`, lane still publishing at 10 Hz.
* Reversible: setting the range back restores yellow+white following.

At the block (`block_distance` 0.90 m ahead, white mode active) the supervisor
publishes `pass:right` and creeps past on the right — see
[08](08-navigation-behavior.md).

**Upstream node:** `detect_intersection_sign` (run via `detect_sign.launch.py`)

Publishes `std_msgs/UInt8` on `/detect/traffic_sign`:

| Value | Meaning |
| --- | --- |
| 0 | nothing |
| 1 | intersection (plain "junction ahead" sign) |
| 2 | left arrow |
| 3 | right arrow |

### The mission switch matters

`detect_sign.launch.py mission:=<name>` selects the template set. The
**construction** set does not contain the T-junction arrow, so with
`mission=construction` the topic stays `0` forever and the robot simply stops at
the junction. The launch default is therefore `intersection`.
([ADR 0005](adr/0005-intersection-default-mission.md))

### Known weakness: it flickers

The matcher alternates `2` and `3` on the same physical sign, frame to frame:

```
[01:26:11] LIGHT=none SIGN=3 MISSION=drive
[01:26:12] LIGHT=none SIGN=2 MISSION=drive
[01:26:12] LIGHT=none SIGN=3 MISSION=drive
```

Acting on a single message sent the robot the wrong way. The supervisor now keeps
a 4 s history and requires ≥ 60 % agreement over the last 2 s
(`sign_majority`) before turning. A geometric replacement is on the roadmap.

---

## 3. YOLO sign detector (advisory)

**File:** `patches/ros2_ws/nodes/yolo_sign_detector.py`
**Launch:** `detect_yolo_sign.launch.py`

Ultralytics YOLOv8 on `/camera/image_compensated`, publishing
`vision_msgs/Detection2DArray` on `/yolo/sign_detections` (plus a `String`
`/yolo/sign_state` and an annotated `CompressedImage` for rqt). Deliberately **not**
wired to control — COCO has no concept of a left/right arrow sign, so it cannot
decide a junction. It documents what the camera sees and gives an independent
visual check.

Practical details:

- `imgsz=320`, `process_every_n=3` to keep the CPU usable alongside Gazebo.
- Class aliasing for the classes that do exist:
  `COCO_ALIASES = {'stop sign': 'stop_sign', 'traffic light': 'traffic_light'}`.
- One `process_every_n` block is skipped while it warms up; the log prints
  `YOLO model ready: ... (N classes)` when it is live.
- Container versions: `ultralytics 8.4.191`, `torch 2.14.1+cu130`, `cv2 4.9.0`,
  `numpy 1.26.4` (`numpy<2` is required by this torch/ultralytics pair).

Installing ultralytics pulls a newer `setuptools` that breaks `colcon build`
(`setup.py develop` was removed). The environment is pinned to
`setuptools 79.0.1` and `packaging 24.2`.

---

## Which detector would I trust for the junction?

Today: the template detector **with majority voting**, because it is the only one
that emits a direction. The correct long-term answer is a small geometric
detector (blue sign blob → white arrow centroid left/right of the blob centre),
which removes both the flicker and the mission-template dependency.
