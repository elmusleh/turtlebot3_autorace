# ADR 0008 — Coast on LiDAR free space instead of spinning in place

**Status:** Accepted (in force)

## Context

Reported behaviour: *"the robot is not identifing the correct path quickly, it
sometimes spin on its position to see around. Can it be faster and smarter?"*

The lane-loss path was: wait `search_after`, rotate a fixed angle, repeat. Problems:

1. **It stopped to think.** The lane detector usually recovers within a few tens of
   centimetres of travel; stopping wasted exactly the motion that would have
   restored the signal.
2. **It ignored the LiDAR.** The scan was already being used for the front guard,
   but not for "where is the corridor".
3. **It could not tell a junction from a dead end.** Both looked like "lane lost",
   so both got rotations — including rotating inside a 0.7 m box, which can never
   work.

## Decision

Use a free-space profile from `/scan` (5° bins over ±90°, best range per bin,
scored `min(range, 2.5) − 0.6 × |angle|` so straight-ahead is preferred) and branch:

| Condition | Action |
| --- | --- |
| Forward clearance > `coast_clear` (0.75 m) | **Coast**: 0.07 m/s, steer toward `best_free_dir` × 1.5 |
| `best_free_range` < `pocket_range` (1.2 m) | **Dead end**: reverse (rear-guarded) then turn |
| Otherwise | **Open-space turn** toward `best_free_dir`, `min_time` 0.35 s, budget 3 |

Plus faster global rates: `max_vel` 0.12 → 0.16 m/s, `turn_speed` 0.9 → 1.2 rad/s,
`search_after` 2.5 → 1.0 s, sign pause 2.0 → 1.2 s.

And a budget that refills on progress: every 2 m travelled resets `recoveries` and
`searches`.

## Consequences

**Good — measured on the same world and start**

| Configuration | Distance per run |
| --- | --- |
| stop-and-sweep baseline | 5.4 m / 155 s, then parked |
| + coast & faster rates | 7.0 m / 155 s |
| + pocket detection | 8.47 m / 180 s |
| + budget reset | **11.45 m / 240 s, still moving at the end** |

State mix afterwards: ~53 % `drive`/`coast`, ~14 % `turn`, the rest holds.

**Bad / risks**
- Coasting is a LiDAR corridor follower, not lane following — if the lane is lost
  for a long time the robot follows walls rather than the marked route.
- `coast_clear` 0.75 m is tuned for this world's corridor widths; a narrower course
  would need it lowered.
- Open-space turns can still be wrong if the corridor is ambiguous (two openings of
  similar width).

## Alternatives considered

- *Sweep faster* — reduces the time cost but keeps the stop, and still cannot tell a
  junction from a pocket. Rejected.
- *Blind dead-reckoning through dropouts* — no correction signal, accumulates error
  and drives into walls. Rejected.
