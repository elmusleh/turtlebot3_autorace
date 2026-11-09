# 01 — Project overview

## What this project is

A reproducible ROS 2 Humble + Gazebo environment in Docker for driving a
TurtleBot3 (`burger_cam`) autonomously around the TurtleBot3 **AutoRace 2020**
track, plus the control and perception layer needed to make that actually behave
like a mission instead of a random walk.

The upstream AutoRace packages provide detectors and a lane controller, but they
do not provide a mission layer: nothing stops the robot at a red light, nothing
pauses at a sign, and nothing turns at a junction. This project adds that layer
and fixes the camera pipeline it depends on.

```
                 ┌──────────────── the mission layer (this project) ─────────────────┐
 Gazebo ──/camera─┼─► rectify ─┬─► projection ─► detect_lane ─► control_lane ─┐       │
        └─/scan───┤            └─► compensation ─► light / sign / YOLO ───────┤       │
        └─/odom───┼─► LiDAR sectors ─────────────────────────┐                 ▼       │
                  │                                        └─► mission_supervisor      │
                  │                                            (sole /cmd_vel        │
                  │                                             writer) ──────►  ─────┼─► base
                  └────────────────────────────────────────────────────────────────────┘
```

## Goal and scope

**Goal:** complete the AutoRace course in simulation without:
- driving through a red or yellow light,
- ignoring a direction sign or turning the wrong way at a T junction,
- leaving the lane, flipping, or colliding with the white barrier bars.

**In scope**
- Containerised environment that installs and builds in one command.
- Working camera pipeline (raw → rectified → compensated) for a camera that has
  no `image_rect_color` output.
- Traffic-light gating, sign recognition, junction manoeuvre.
- Collision avoidance using the LDS-01 LiDAR (front, sides, rear).
- Live observability: every node visible in tmux, rqt and RViz2 open from the
  first second.

**Out of scope (for now)**
- The parking, tunnel and level-crossing missions beyond being launchable.
- Full extrinsic calibration through the upstream CalibrationToolkit GUI (this
  project uses a compensation node with default parameters instead — see
  [ADR 0004](adr/0004-compensation-reads-rect.md)).
- Real hardware.

## What works today (measured)

| Capability | Status | Evidence |
| --- | --- | --- |
| Container + workspace build | working | `./ros2_docker.sh install`, `colcon build` |
| Camera pipeline | working | `/camera/image_rect` ≈ 29.9 Hz, `/camera/image_compensated` 30–33.6 Hz |
| Lane following | working | `control_lane` publishes `/control/cmd_vel` at 10 Hz |
| Traffic-light stop/go | working | red → `hold`, green → `drive`, one-shot latch after passing |
| Sign detection | working | `Detect right sign` continuous; supervisor majority-vote |
| Junction turn | working | `DECIDE right` → `turn complete (93 deg) - lane re-acquired` |
| Collision guards | working | rear-guarded reversals: minimum rear distance 0.50 m over 3 episodes |
| Distance per 240 s run | 11.45 m | `track_odom.py` |

## What does not work reliably yet

1. **Lane detection at the tunnel.** `detect_lane` is the upstream node and
   expects the original calibration/back-projection chain. It reports
   `Lane state: 0` in the tunnel and under the robot's nose, which is the
   underlying reason the robot needs to coast and re-acquire.
2. **Turn overshoot.** A sign turn is signalled 90° and may extend to 1.4×
   (≈126°) if the lane detector stays silent — observed `turn complete (129 deg)`.
   That leaves the robot misaligned and it then coasts/turns to recover.
3. **Tight corners.** The robot can wedge into a corner with ~0.13 m clearance
   where reversing is blocked; the escape budget refills on progress, so it keeps
   trying, but it costs time.

See [13-roadmap.md](13-roadmap.md).

## Design principles

1. **One writer of `/cmd_vel`.** Everything that wants to move the robot
   publishes intent (`/control/cmd_vel`), and one node decides what reaches the
   base. Without this, red-light stops and LiDAR stops fight with the lane
   controller. ([ADR 0001](adr/0001-single-cmd-vel-owner.md))
2. **Safety is not a mode.** Stops are evaluated every tick from live sensor
   state, not entered as a separate mode that something forgets to leave.
3. **Silence is not consent.** A detector that stops publishing must not be read
   as "go" — every consumer has a staleness timeout, and critical detectors
   publish a heartbeat. ([ADR 0002](adr/0002-traffic-light-heartbeat.md))
4. **Every fix gets a probe.** If a behaviour cannot be measured, it cannot be
   claimed. All probes live in `patches/ros2_ws/`. ([10-verification.md](10-verification.md))
