# 08 — Navigation behaviour

This document covers *how* the robot moves when things are imperfect: when the
lane detector blinks, when a corridor ends, when it wedges itself somewhere.
The nominal case (lane visible, light green) is just: follow the lane at up to
0.16 m/s.

## The problem this solves

The lane detector is the weak link. When it reports `Lane state: 0` the naive
options are both bad:

- keep driving blind → leaves the track, hits walls
- stop and rotate until the lane returns → the "spinning in place to look around"
  behaviour, which is slow and looks lost

Instead the robot uses the LiDAR to decide, which is independent of the camera.

## Decision tree for a lost lane

```
lane command stale?
├── Front clearance > coast_clear (0.75 m)?
│      └── COAST: creep at 0.07 m/s, steer toward the most-open 5° bin
│
├── Best free range in ±90° < pocket_range (1.2 m)?
│      └── DEAD END: reverse out (rear-guarded), then turn away
│
├── Open-space turn budget left?
│      └── TURN toward the most-open direction (short, goal-directed)
│
└── Nothing applies
       └── hold:no-lane-cmd (zero velocity)
```

### Coast

The key insight: the lane detector usually recovers within a few tens of
centimetres of travel. Stopping wastes that opportunity.

**It is bounded**: coasting lasts at most `coast_max_time` (2.5 s). Beyond that
the robot stops and reports `hold:no-lane-cmd`. This came from a real failure —
a crashed lane detector left the robot following "most open direction" for
minutes, which drove it off the marked track entirely. Coasting is a short
bridge across a dropout, not a navigation mode.

- State: `coast`
- Speed: `coast_speed` 0.07 m/s
- Steering: `best_free_dir × 1.5`, clamped to `max_angular`
- Requires: > `coast_clear` (0.75 m) of forward clearance

`best_free_dir` is chosen from 5° bins over ±90° by score
`min(range, 2.5) − 0.6 × |angle|` — i.e. "most open, but prefer straight". The
angle penalty stops the robot from chasing a slightly wider gap off to the side.

### Take your right at the long white block

After the junction the reference is the white edge line, and the course rule at the
long white block is to pass on the **right**.

```
white mode active AND front_range < block_distance (0.90 m)
    → steer right (or left if there is more room on the left)
    → creep at 0.05 m/s
    → state: pass:right / pass:left
until the front range opens past the block
```

It differs from the generic recovery in two ways: it never reverses, and it commits
to one side instead of alternating.

### Junction vs dead end — the distinction that fixed the spinning

| Situation | LiDAR signature | Action |
| --- | --- | --- |
| T junction / corner | Corridor open to one side (≥ 1.2 m) | Rotate toward the open side, then coast into it |
| Dead-end pocket | Nothing open within ±90° (≈ 0.7 m everywhere) | **Reverse out.** Rotating in a pocket cannot help |

Observed pocket causing the old behaviour:

```
front=0.67 left=0.67 right=0.71 rear=inf
```

Every direction ~0.7 m: a box. The old code rotated; the new code backs out.

### Open-space turn

- State: `turn`
- Target: `best_free_dir` (clamped to ±1.4 rad), or ±0.9 rad alternating if the
  best direction is too close to straight ahead
- `min_time` 0.35 s, so it is a short turn, not a full sweep
- Budget: `search_max` 3, refilled after 45 s without an escape or on progress

### Recovery (reverse + turn)

Triggered by:
- obstacle held for `recovery_after` (1.5 s), or
- dead-end detection, or
- lane lost for more than 5 s with a long time since the last escape

Sequence:

```
1. rear_min < recovery_rear_clear (0.30 m)?
       yes → turn in place (no reversal)
       no  → reverse at 0.10 m/s for 2.0 s (~0.2 m)
              └── aborts instantly if rear_min < 0.14 m
2. turn recovery_turn_angle (0.7 rad ≈ 40°)
       direction alternates with each recovery so it does not
       re-enter the same dead end
```

### Escape budget that refills with progress

Both `recoveries` and `searches` reset when the robot has travelled **2 m** since
the last reset:

```
progress made (4.1 m) - resetting escape budget (was 3 recoveries, 1 searches)
```

Without this, one bad corner consumed the run's 8 recoveries and the robot parked
for the remainder of the run.

## Speed policy

| State | Speed |
| --- | --- |
| `drive` | up to `max_vel` 0.16 m/s (clamped from the lane controller) |
| `drive`, one side close | 0.6 × `max_vel` |
| `drive`, both sides close | 0.4 × `max_vel` |
| `coast` | 0.07 m/s |
| `turn` | 1.2 rad/s, no forward motion |
| `recover:back` | −0.10 m/s |

History: `max_vel` was 0.22, which overshot curves and pinned the robot against
the tunnel wall. It was dropped to 0.12, then raised to 0.16 once coasting and
wall avoidance were in place.

## Measured effect of these changes

| Change | Distance in a fixed run |
| --- | --- |
| baseline (stop and sweep on lane loss) | 5.4 m / 155 s, then parked |
| + LiDAR-based coast + faster rates | 7.0 m / 155 s |
| + pocket detection | 8.47 m / 180 s |
| + escape-budget reset | **11.45 m / 240 s, still moving at the end** |

State mix over the last 600 monitor samples:

```
54 drive · 20 coast · 19 turn · 17 hold:sign · 15 hold:no-lane-cmd
 7 recover:back · 4 hold:obstacle · 2 hold:light · 1 hold:light:red
```

So ~53 % of the time is spent driving/coasting and ~14 % turning.

([ADR 0008](adr/0008-coast-instead-of-spin.md))

## What "good" looks like in the monitor

```
LIGHT=none SIGN=3 MISSION=drive      ← normal
LIGHT=none SIGN=3 MISSION=coast      ← lane blinked, still moving on LiDAR
LIGHT=none SIGN=3 MISSION=turn       ← sign manoeuvre or open-space turn
LIGHT=red  SIGN=0 MISSION=hold:light:red   ← correct stop
LIGHT=none SIGN=0 MISSION=hold:obstacle    ← LiDAR guard
```

Frequent `hold:no-lane-cmd` means coasting is failing (front clearance under
0.75 m) and the lane detector is genuinely lost — check the tunnel section.
