# ADR 0002 — The traffic-light detector publishes a heartbeat

**Status:** Accepted (in force)

## Context

`traffic_light_state` originally published only when the detected colour
**changed** (change-driven publishing, which is the natural implementation).

`mission_supervisor` treats light state as stale after `state_timeout` = 2 s, and
stale state is not a stop state. The sequence that produced a real failure:

1. Light turns red → detector publishes `red` once.
2. Detector sees red continuously and publishes nothing more.
3. 2 s later the supervisor's state is stale → not in `stop_states` → drives.
4. The robot drives through the red light.

The bug is not "the detector is wrong". The bug is that **silence was
indistinguishable from death**, and the consumer resolved the ambiguity in the
direction of motion.

## Decision

`traffic_light_state` publishes the current state unconditionally at
`publish_rate` = 5 Hz (`red` / `yellow` / `green` / `none`). The value is not
change-driven.

`mission_supervisor` keeps the staleness rule, but now staleness means the node is
dead, not that the light is fine.

## Consequences

**Good**
- A dead detector and a steady red light now look different: dead → stop.
- Lost frames / brief dropouts do not resynchronise the state machine.
- The same rule can be reused by any consumer without extra logic.

**Bad**
- 5 Hz of constant traffic for a value that rarely changes (negligible at this
  scale).
- The detector must therefore always be running while the robot drives; if it is
  killed, the robot stops rather than continuing — intended, but worth knowing
  when debugging "why did it stop".

## Generalisation

Applied to every control-relevant input:

| Input | Staleness | Result |
| --- | --- | --- |
| `/detect/traffic_light_state` | `state_timeout` 2.0 s | treated as unknown → stop |
| `/control/cmd_vel` | `cmd_timeout` 0.5 s | `hold:no-lane-cmd` |
| `/scan` | not consumed → front guard uses last value only for "blocked" | — |
