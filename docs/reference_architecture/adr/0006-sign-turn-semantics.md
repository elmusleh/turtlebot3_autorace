# ADR 0006 — Turn semantics: direction from the sign, angle always complete, one turn per junction

**Status:** Accepted (in force)

## Context

Making the robot turn at a T junction produced four separate wrong behaviours, each
observed in a log before being fixed.

### 1. Wrong direction from a plain sign

`/detect/traffic_sign` carries `1 = intersection`, `2 = left`, `3 = right`. The
first implementation treated any non-left id as "the configured default direction",
so the plain junction sign (`1`) started a rotation:

```
DECIDE intersection -> rotating -1.5 rad
turn complete (139 deg) - lane missing
```

139° away from the lane.

**Decision:** only arrows turn. `1` = pause and continue if a lane exists.

### 2. Turn cut short

The turn ended as soon as the lane detector published once. At a junction the old
lane can reappear briefly while the robot is mid-rotation:

```
turn complete (41 deg) - lane re-acquired
```

41° left the robot pointing diagonally at the wall.

**Decision:** always execute the signalled angle (`min_time = |angle| / turn_speed`)
and *then* allow a bounded extension (up to 1.4×) if the lane has not returned.

### 3. Same sign, second turn

After a correct 93° turn, the sign was still in view and re-armed:

```
DECIDE right (turn 1/2)
DECIDE right (turn 2/2) -> turn complete (129 deg)
```

Ending facing backwards.

**Decision:** a junction may trigger at most one turn until the robot has driven
`turn_rearm_distance` = 1.2 m away from it (distance from `/odom`), in addition to
the sign being absent for `sign_rearm`.

### 4. Wrong arrow, right sign

The template matcher flickers between `2` and `3` on the same physical sign, so a
single message was not evidence of anything.

**Decision:** majority vote over the last 2 s with ≥ 60 % agreement
(`sign_majority`), using a 4 s history.

## Decision (consolidated)

A sign turn happens only when **all** of:

1. the majority-voted id is `2` or `3`,
2. the sign was seen within 5 s,
3. the turn budget (`max_turns` = 2) is not exhausted,
4. `turns_done == 0` **or** ≥ `turn_rearm_distance` metres driven since the last
   turn.

It then rotates the **full** `turn_angle` (default −1.57 rad = 90° right), with an
early exit on lane re-acquisition only after the minimum time, and a hard cap at
1.4×.

## Consequences

**Good**
- Verified direction: net yaw −104.1° (right) via `yaw_probe.py`.
- Verified completion: `turn complete (93 deg) - lane re-acquired`.
- No more double turns at a single junction.

**Bad / open**
- If the lane stays invisible, the turn extends to the 1.4× cap (~126°) and can
  still overshoot — see [roadmap](../13-roadmap.md) P3.
- `max_turns = 2` is a global budget, not per junction; a longer course needs
  raising it.
