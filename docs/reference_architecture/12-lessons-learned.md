# 12 — Lessons learned

Rules extracted from actual failures in this project. Each one cost time; each one
is cheap to respect next time.

## Sensor conventions are not optional — verify them, don't assume them

This world's LDS-01 publishes angles over **[0, 2π) with `angle_min = 0`**, not
[-π, π). Code written for the textbook convention silently detected:
- no right wall at all (all angles positive → the negative test never matched),
- a truncated forward cone (340–360° dropped).

Nothing crashed. The robot just steered badly for hours.

> **Rule:** print `angle_min`, `angle_increment` and the angle that produced the
> minimum range before writing any sector logic. Then wrap with
> `atan2(sin(a), cos(a))` and never think about it again.

## Silence is not consent

The light detector originally published only when the value changed. A consumer
that timed out after 2 s then treated "no message" as "not red" and drove off.

> **Rule:** anything that permits motion must have a heartbeat, and anything that
> consumes it must treat staleness as **stop**, never as "unknown → proceed".

## A stop with no recovery path is a trap

The forward LiDAR guard stopped the robot 0.120 m from the sign post. There was no
code path out of that state, so "the robot is not moving" was not a bug in
movement — it was a bug in stopping.

> **Rule:** every stop state needs an exit condition. If the world can put the
> robot into a state, the robot must be able to leave it.

## Check behind before you reverse

The reverse was written when the robot still faced the world; the rear was never
sensed. Backing away from the barrier bars drove into the bars behind.

> **Rule:** a robot with a 360° sensor should use all 360° of it. Any motion whose
> direction is not "forward" gets its own guard.

## One writer per command topic

Two publishers on `/cmd_vel` means no component can guarantee a stop. Moving
`control_lane` to `/control/cmd_vel` (intent) and letting one node decide was the
change that made red-light stops reliable.

> **Rule:** separation of **intent** from **authority**. Detectors state facts;
> one node commands; nothing else touches the actuator topic.

## A turn needs a termination condition that is not "the clock"

Fixed-angle turns were wrong in both directions: 41° stopped too early (the lane
briefly reappeared), 139° went too far (nothing reappeared). The workable design
is: always do the signalled angle, allow a bounded extension, and prefer the
sensor's "lane is back" as the early exit.

> **Rule:** timed manoeuvres need a sensor-based success criterion plus a hard
> cap — not just a duration.

## Distinguish "junction" from "dead end"

Rotating in a pocket is wasted time; driving into a pocket is a crash. The LiDAR
free-space profile (`best range within ±90°`) separates the two cases with one
number.

> **Rule:** before choosing a manoeuvre, classify the geometry. The same
> "lane lost" state has two very different correct responses.

## Budgets must refill, or one bad corner ends the run

`recoveries` was capped at 8 and never reset, so the first few obstacles consumed
the run's entire allowance.

> **Rule:** counters that gate behaviour should reset on evidence of progress
> (metres travelled), not only on time.

## Platform quirks are real requirements

| Quirk | Consequence if ignored |
| --- | --- |
| `burger_cam` is `rgb8` | `/camera/image_rect_color` never exists; pipeline starves |
| `rqt_image_view` is a plugin | `command -v` finds nothing; the pane dies silently |
| `tmux select-layout tiled` renumbers panes | launches land in the wrong pane |
| `setuptools ≥ 84` | `colcon build` fails after installing ultralytics |
| `numpy ≥ 2` | torch/ultralytics import errors |

> **Rule:** when something "should work", verify the platform actually provides
> it (`command -v`, `ros2 pkg executables`, `ros2 topic list`) before debugging
> your own code.

## Template matching flickers — vote

The sign matcher alternated between left and right on one physical sign. Acting on
one message sent the robot the wrong way.

> **Rule:** for a classification used to make an irreversible decision, aggregate
> over a window and require a clear majority.

## If you cannot measure it, you cannot claim it

Every real fix in this project has a probe: `track_odom` (distance), `yaw_probe`
(direction), `reverse_audit` (rear safety), `scan_quadrant_probe` (sector
correctness). The improvements are quoted as numbers, not adjectives.

> **Rule:** write the measurement before the fix. It tells you when you are done,
> and it stops you from "fixing" a symptom you cannot see.

## Clean shutdown is part of the runtime

A killed tmux session leaves `gzserver` behind; two simulators publish two `/odom`
streams and the robot appears to teleport. Stale FastRTPS shm breaks new
participants.

> **Rule:** provide and use a single stop command that kills panes, session,
> processes, and shared memory (`./ros2_docker.sh racestop`).
