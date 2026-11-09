# ADR 0001 — `mission_supervisor` is the sole writer of `/cmd_vel`

**Status:** Accepted (in force)

## Context

The upstream `control_lane` node publishes directly to `/cmd_vel`. Requirements
added on top of lane following — stop at red, pause at a sign, stop for an
obstacle, execute a scripted turn, stop when data goes stale — all need to
override what the lane controller wants.

With two publishers on `/cmd_vel` the last writer wins. A stop is never final: the
lane controller (running at 10 Hz) immediately publishes a new drive command and
the robot creeps through the red light.

## Decision

`control_lane` is remapped to publish **intent** on `/control/cmd_vel`.
`mission_supervisor` subscribes to it and is the **only** publisher of `/cmd_vel`.
The supervisor decides, every tick, whether the intent is allowed and in what
form, applying:

- traffic-light gating (with heartbeat + staleness),
- sign pause and turn execution,
- LiDAR stop and recovery manoeuvres,
- speed and steering clamps,
- watchdog on stale lane commands.

## Consequences

**Good**
- Stops are absolute and composable: light, obstacle, sign, staleness all reduce to
  one decision point.
- `ros2 topic info /cmd_vel` shows exactly one publisher — a cheap invariant.
- Negative lane velocities can be clamped to zero in one place, so the only
  deliberate reverses are the rear-guarded recoveries.

**Bad**
- One more node in the loop adds a 10 Hz latency step; a turn cannot start faster
  than the supervisor tick.
- All stop logic lives in a single large node, which needs to stay disciplined
  (see the ordered decision list in [06](../06-mission-control.md)).

## Alternatives rejected

- *Reconfigure `control_lane` to subscribe to a stop flag* — couples every reason
  to one boolean and loses priority ordering.
- *Twist mux (`twist_mux`)* — viable, but priority muxing is coarser than the
  state-aware decisions needed here (e.g. turn vs coast vs recovery).
