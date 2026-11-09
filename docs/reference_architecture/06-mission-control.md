# 06 — Mission control (the supervisor)

**File:** `patches/ros2_ws/nodes/mission_supervisor.py`
**Launch:** `patches/ros2_ws/launch/control_race.launch.py`

## Role

`mission_supervisor` is the **only** publisher of `/cmd_vel`. It subscribes to the
lane controller's intent (`/control/cmd_vel`) and decides whether — and in what
form — that intent reaches the base.

This single-owner design is the reason several otherwise contradictory
requirements can coexist: red-light stop, sign pause, LiDAR stop, turn manoeuvre,
lane following, and a watchdog.

It also publishes `/control/max_vel` (`std_msgs/Float64`) at 1 Hz, so
`control_lane` knows the same speed ceiling the supervisor enforces. Verified in
the live graph: `/control_lane` subscribes `/control/max_vel`,
`/mission_supervisor` publishes it.

## Decision order (every tick, 10 Hz)

The order matters: earlier checks win. This is the actual sequence in `tick()`.

| # | Check | Outcome |
| --- | --- | --- |
| 1 | Has the robot made 2 m of progress since the last budget reset? | Reset `recoveries` and `searches` to 0 |
| 2 | Is a reversal in progress? | Publish `-recovery_back_speed`, or abort and turn if the rear is blocked |
| 3 | Is a rotation in progress? | Publish `angular.z = turn_rate` until the minimum time **and** lane re-acquisition, capped hard |
| 4 | Compute `hold_reason()` and lane staleness | — |
| 5 | Sign decision: lane stale or blocked for `lane_lost_before_turn`? | Decide via majority vote; if an arrow → `start_turn()` |
| 6 | Is there a hold reason? | Publish zero Twist, state `hold:<reason>`; recover after `recovery_after` if it is an obstacle |
| 7 | Lane command stale? | Coast / dead-end recovery / open-space turn / `hold:no-lane-cmd` |
| 8 | Otherwise: drive | Clamp, wall-avoidance, publish `drive` |

Everything ends in exactly one `Twist` published to `/cmd_vel` — never two
conflicting reasons.

## Stop reasons (`hold_reason()`)

| Reason string | Cause |
| --- | --- |
| `light:red` | Last light state is in `stop_states` (`red,yellow`) |
| `light:yellow` | Same, yellow |
| `sign` | Paused at a sign for `sign_stop_seconds` to decide |
| `obstacle` | LiDAR guard tripped (something inside `emergency_distance` forward) |

`hold:no-lane-cmd` is not a `hold_reason()` — it comes from the staleness path.

## Traffic-light gating

- `stop_states = "red,yellow"` → both stop the robot.
- **Heartbeat + staleness:** the light detector publishes at 5 Hz. If nothing
  arrives for `state_timeout` (2 s), the state is treated as unknown, not as
  "green".
- `none` (no light in view) allows driving after `unknown_hold` (1.0 s). This is
  what lets the robot start before the light is visible and continue after it
  passes.
- **Latch:** `latch_after_pass = True` means once the robot has driven past a
  green light, the light is no longer consulted — so a red light behind it cannot
  stop the run.

## Sign decision

```
lane stale or blocked for lane_lost_before_turn (0.8 s)
    → sign_seen within the last 5 s?
        → majority vote over the last 2 s (≥ 60 %)
            → arrow?  (1 = intersection never turns)
                → distance since last turn ≥ turn_rearm_distance (1.2 m)?
                    → start_turn()
```

Signals to the turn:

| Sign | Action |
| --- | --- |
| `1` intersection | Pause only, **no turn** |
| `2` left arrow | Rotate `+abs(turn_angle)` |
| `3` right arrow | Rotate `-abs(turn_angle)` |

`turn_angle` defaults to `-1.57` rad (90° right).

### Why each guard exists

| Guard | Failure it prevents |
| --- | --- |
| Majority vote | Template matcher flickers 2↔3; a single message sent the robot left at a right-only sign |
| `1` never turns | The plain junction sign was treated as a direction and spun the robot 139° off the lane |
| Full angle always executed | Cutting the turn at 41° (when the lane briefly reappeared) left the robot pointing diagonally at the junction |
| `turn_rearm_distance` | After a correct 90° turn the sign was still in view and triggered another 129° turn, facing backwards |
| `max_turns` = 2 | A hard cap so a mis-detection cannot spin the course forever |

([ADR 0006](adr/0006-sign-turn-semantics.md))

## Turn execution

```python
full     = abs(angle) / turn_speed          # always performed
max_time = max(full * 1.4, min_time + 0.3)  # extension if the lane is missing
rate     = copysign(turn_speed, angle)      # negative = clockwise = right
```

The turn ends when **both** `rotated > min_time` **and** the lane detector has
published recently, or when `max_time` is reached. Completion is logged with the
achieved angle and whether the lane came back:

```
DECIDE right (turn 1/2): rotating -90 deg at 1.2 rad/s (1.3s min, 1.8s max)
turn complete (93 deg) - lane re-acquired
```

## Speed and steering limits

| Parameter | Value | Effect |
| --- | --- | --- |
| `max_vel` | 0.16 m/s (launch) | Forward speed clamp — the lane controller's request is clipped, never trusted |
| `max_angular` | — | Steering clamp |
| `cmd_timeout` | 0.5 s | No lane command → stop (`hold:no-lane-cmd`) |
| `publish_rate` | 10 Hz | Watchdog: a dead supervisor stops publishing, and the base stops |

Negative linear velocity from the lane controller is clamped to 0
(`max(0.0, ...)`) — the only reverse commands in the system are the deliberate,
rear-guarded recovery reversals.

## Mission states seen by the monitor

```
drive · coast · turn · recover:back · recover:turn
hold:light:red · hold:light:yellow · hold:sign · hold:obstacle · hold:no-lane-cmd
```

## Full parameter reference

| Parameter | Default | Meaning |
| --- | --- | --- |
| `stop_states` | `red,yellow` | Light states that stop the robot |
| `publish_rate` | 10.0 | `/cmd_vel` and `/mission/state` rate |
| `state_timeout` | 2.0 | Light heartbeat staleness |
| `unknown_hold` | 1.0 | Grace period when the light is `none` |
| `latch_after_pass` | True | Ignore the light after passing it |
| `cmd_timeout` | 0.5 | Lane command staleness |
| `max_vel` | 0.16 | Forward clamp |
| `emergency_distance` | 0.16 | Forward LiDAR stop distance |
| `clear_distance` | 0.30 | Forward distance to declare the path clear again |
| `scan_half_fov` | 0.20 | Forward cone half-angle (≈11°) |
| `wall_dist` | 0.45 | Side distance at which correction starts |
| `wall_gain` | 1.2 | Side correction gain |
| `wall_fov` | 1.0 | Side sector half-angle (≈57°) |
| `turn_on_sign` | True | Enable sign-driven turns |
| `turn_angle` | -1.57 | Radians; negative = right |
| `turn_speed` | 1.2 | Rad/s |
| `max_turns` | 2 | Turn budget per run |
| `lane_lost_before_turn` | 0.8 | Lane-stale time before a turn is considered |
| `sign_cooldown` | 6.0 | Minimum spacing between decisions |
| `sign_rearm` | 3.0 | Sign must be absent this long to re-arm |
| `turn_rearm_distance` | 1.2 | Distance to drive before the same junction can turn again |
| `recovery_enabled` | True | Allow the reverse-and-turn escape |
| `recovery_after` | 1.5 | Blocked time before recovery |
| `recovery_back_speed` | 0.10 | Reverse speed |
| `recovery_back_time` | 2.0 | Reverse duration (≈0.2 m) |
| `recovery_turn_angle` | 0.7 | Turn after reversing (side alternates) |
| `recovery_max` | 8 | Recovery budget |
| `recovery_rear_clear` | 0.30 | Refuse to reverse if the rear is closer than this |
| `recovery_rear_abort` | 0.14 | Abort a reversal already in progress |
| `search_enabled` | True | Open-space turns when the lane is lost |
| `search_after` | 1.0 | Lane-stale time before acting |
| `search_max` | 3 | Open-space turn budget |
| `coast_enabled` | True | Keep moving along the open corridor |
| `coast_speed` | 0.07 | Coast speed |
| `coast_clear` | 0.75 | Required forward clearance to coast |
| `pocket_range` | 1.2 | Below this best-free range it is a dead end |
| `escape_reset_after` | 45.0 | Idle time before the search budget refills |
