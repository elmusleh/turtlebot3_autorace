# 07 — Safety and the LiDAR

The LDS-01 publishes `/scan` at 360°. Every collision guard in this project is
built on it, and every one of them was added because the robot hit something.

## The angle convention bug (read this first)

This world's LiDAR publishes angles over **[0, 2π) with `angle_min = 0`** — not
[-π, π). Measured:

```
rear ray at +321 deg (angle_min=+0 deg)
rear ray at +209 deg (angle_min=+0 deg)
```

Code that assumed the usual convention failed in two silent ways:

- `-1.0 <= angle < -0.15` (the "right" sector) **never matched anything**, because
  every angle is positive. The side-wall corrector therefore only ever saw the
  left wall and steered asymmetrically.
- Rays at 340–360° were dropped from the forward cone (`abs(angle) <= 0.20` does
  not match 357°).

Every sector test now wraps first:

```python
angle = math.atan2(math.sin(msg.angle_min + i * msg.angle_increment),
                   math.cos(msg.angle_min + i * msg.angle_increment))
```

Verification after the fix (`scan_quadrant_probe.py`):

```
[01:22:22] front=1.78 left=0.82 right=0.29 rear=inf
[01:22:30] front=1.05 left=0.60 right=1.31 rear=0.24
```

All four sectors now report real distances.

## Sectors

| Sector | Angle range | Used for |
| --- | --- | --- |
| Front | \|angle\| ≤ `scan_half_fov` (0.20 rad ≈ 11°) | Emergency stop, coast clearance |
| Left | 0.15 … `wall_fov` (1.0 rad ≈ 57°) | Wall avoidance |
| Right | −`wall_fov` … −0.15 | Wall avoidance |
| Rear | \|angle\| ≥ π − 0.35 (±20° of straight back) | **Reverse guard** |
| Free profile | 5° bins over ±90° | Coast direction, dead-end detection |

Ranges outside `0.02 < r < 3.5` and `NaN` values are ignored.

## Guard 1 — forward emergency stop

| Parameter | Value |
| --- | --- |
| `emergency_distance` | 0.16 m |
| `clear_distance` | 0.30 m |

Below 0.16 m in the forward cone → `hold:obstacle`, zero velocity. It resumes
only when the front clears 0.30 m (hysteresis prevents chatter at the boundary).

History: the first version used a ±26° cone and 0.28 m, which tripped on the lane
wall 22–42° off axis and froze the robot. Narrowed to ±11° / 0.16 m.

## Guard 2 — rear guard on reversal (the barrier-bar crash)

The recovery manoeuvre reverses ~0.2 m. Originally **nothing** looked behind, so
"back away from the bars" drove straight into the bars behind the robot.

Two guards now apply:

| Guard | Parameter | Behaviour |
| --- | --- | --- |
| Before reversing | `recovery_rear_clear` 0.30 m | If the rear is closer, refuse to reverse and turn in place instead |
| During reversing | `recovery_rear_abort` 0.14 m | Stop immediately, then turn |

Log messages:

```
recovery 2/8: rear blocked at 0.21 m - turning in place instead of reversing
rear blocked at 0.12 m - reversal aborted
```

**Verified** with `reverse_audit.py` over 150 s:

```
reverse commands seen: 57
reversal episodes: 3
  01:28:51 v=-0.10 rear=0.52 m  OK
  01:29:07 v=-0.10 rear=0.50 m  OK
  01:29:16 v=-0.10 rear=0.50 m  OK
closest rear distance during any reversal: 0.50 m
reversals with rear < 0.30 m: 0
```

([ADR 0007](adr/0007-rear-guard.md))

## Guard 3 — wall avoidance

`control_lane` happily steers into the tunnel wall because the yellow line
disappears under the robot's nose there. The supervisor adds a lateral term:

| Parameter | Value |
| --- | --- |
| `wall_dist` | 0.45 m |
| `wall_gain` | 1.2 |
| `wall_fov` | 1.0 rad |

```
left  closer than wall_dist → corr -= (wall_dist - left)  * gain
right closer than wall_dist → corr += (wall_dist - right) * gain
speed capped at 0.6 × max_vel while correcting
```

**Both sides close** (e.g. between barrier bars): no steering correction at all —
steering there pushes the other flank into the bars — speed capped at
0.4 × max_vel.

## Guard 4 — no lane command, no movement

`cmd_timeout` 0.5 s. If `/control/cmd_vel` goes quiet, the supervisor publishes
zero and reports `hold:no-lane-cmd`. Silence is never interpreted as "carry on".

## Guard 5 — watchdog

The supervisor publishes at 10 Hz. A crashed or hung supervisor simply stops
publishing, which stops the base.

## What is *not* guarded

- **Side collisions while driving forward.** Wall avoidance is a gentle
  correction, not a clamp: if a bar appears within 0.2 m beside the robot while
  moving at 0.16 m/s, the correction may not be enough. A hard `angular.z` clamp
  when a flank is under 0.20 m is on the roadmap.
- **Top/bottom of frame:** no 3D sensing, so nothing above the LiDAR plane matters
  (fine for the barrier bars, which are within the scan plane).
