# ADR 0007 — Guard the rear before reversing

**Status:** Accepted (in force)

## Context

Reported failure: *"the robot hit the white obstacle bars because it moved away when
it was too close, while moving behind it, it hit it."*

The recovery manoeuvre exists to escape a dead end: reverse ~0.2 m, then turn. It
was written when only the forward direction was being sensed, so it published
`linear.x = -0.10` with **no rear check at all**. Backing away from the barrier
bars drove straight into the bars behind the robot.

While fixing it, a second bug surfaced: the "right" side had never been measured,
because this LiDAR publishes angles over `[0, 2π)` (`angle_min = 0`) and the
negative-angle test could never match. Wall avoidance had therefore been
correcting against the left wall only.

## Decision

1. **Rear sector** in `on_scan`: `|angle| ≥ π − 0.35` (±20° of straight back),
   stored as `rear_min`.
2. **Refuse** to start a reversal when `rear_min < recovery_rear_clear` (0.30 m);
   turn in place instead.
3. **Abort** a reversal already in progress when `rear_min < recovery_rear_abort`
   (0.14 m): publish zero, then turn.
4. **Both flanks close** → no steering correction (it would push the other side into
   the bars), only a speed reduction to 0.4 × `max_vel`.
5. **Wrap all scan angles** with `atan2(sin(a), cos(a))` before any sector test.

## Consequences

**Good**
- Measured with `reverse_audit.py` over 150 s: 57 reverse commands, 3 reversal
  episodes, minimum rear distance **0.50 m**, **0** reversals with less than 0.30 m
  behind.
- Side symmetry restored: `left` and `right` both report real ranges.

**Bad**
- In a tight pocket where the rear is also blocked, the robot can only rotate, and
  may not escape without more comprehensive manoeuvring (currently it retries with
  alternating turn direction and a refilling budget).

## Regression test

```bash
python3 -u /root/reverse_audit.py 150
# PASS: reversals with rear < 0.30 m: 0
```
