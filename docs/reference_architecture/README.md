# Documentation — ROS 2 TurtleBot3 AutoRace

This directory documents the project end to end: what it is, how it is built, how
the robot decides what to do, how every feature was verified, and the order in
which the pieces were developed (including the bugs that forced each change).

Everything here describes **this repository as it runs today** — the container
`ros2-humble`, the `turtlebot3_autorace_2020` Gazebo world, and the `burger_cam`
robot.

---

## Read in this order

### I have 10 minutes
1. [Project overview](01-project-overview.md) — what the system does
2. [Quickstart](03-quickstart.md) — run it
3. [Troubleshooting](11-troubleshooting.md) — when it misbehaves

### I need to change the behaviour
1. [System architecture](02-system-architecture.md) — who publishes what
2. [Mission control](06-mission-control.md) — the supervisor state machine
3. [Navigation behaviour](08-navigation-behavior.md) — coast / turn / recover
4. [Perception](05-perception.md) — light and sign detection

### I need to understand why the code looks like this
1. [Development stages](09-development-stages.md) — chronological, symptom → fix
2. [Lessons learned](12-lessons-learned.md) — the non-obvious traps
3. [ADRs](adr/) — the decisions worth defending
4. [Verification](10-verification.md) — the measurements behind every claim

---

## Document map

| File | Purpose |
| --- | --- |
| [01-project-overview.md](01-project-overview.md) | Goal, scope, what works, what does not |
| [02-system-architecture.md](02-system-architecture.md) | Packages, nodes, topics, data flow, ownership rules |
| [03-quickstart.md](03-quickstart.md) | Install, start, run the race, GUIs, stop |
| [04-camera-pipeline.md](04-camera-pipeline.md) | raw → rectified → compensated, and why |
| [05-perception.md](05-perception.md) | Traffic light state, template sign detector, YOLO |
| [06-mission-control.md](06-mission-control.md) | `/cmd_vel` gating, light latch, sign decisions, clamps |
| [07-safety-lidar.md](07-safety-lidar.md) | LiDAR sectors, angle convention, all collision guards |
| [08-navigation-behavior.md](08-navigation-behavior.md) | Coast, junction vs pocket, recovery, escape budget |
| [09-development-stages.md](09-development-stages.md) | Stage-by-stage build history with root causes |
| [10-verification.md](10-verification.md) | Probes, metrics, and how to re-run them |
| [11-troubleshooting.md](11-troubleshooting.md) | Symptom → cause → fix table |
| [12-lessons-learned.md](12-lessons-learned.md) | Engineering rules extracted from the failures |
| [13-roadmap.md](13-roadmap.md) | Known gaps and the next improvements |
| [adr/](adr/) | Architecture Decision Records (0001–0008) |

## Conventions used in these documents

- **Verified** means a command was run and its real output is quoted.
- Measured numbers come from runs on this machine (2026-10-28), not estimates.
- `¶` free-standing claims are avoided: every non-obvious statement names the
  file or topic it comes from.
- Parameters are ROS parameters on the node, and can also be set from the launch
  files in `patches/ros2_ws/launch/`.

## Where the code lives

| Location | Content |
| --- | --- |
| `ros2_docker.sh` | Host entry point: container management, demos, AutoRace commands, interactive menu |
| `install.sh` | One-shot installer for a new machine |
| `patches/ros2_ws/nodes/` | Nodes added or rewritten for this project |
| `patches/ros2_ws/launch/` | Launch files added or rewritten |
| `patches/ros2_ws/*.py` | Measurement / verification probes |
| `patches/ros2_ws/run_tb3_race_tmux.sh` | The AutoRace tmux session launcher |
| `.ai-sync/` | Handoff state: current status, plan, progress, session logs |

Inside the container the same files are installed under
`/root/ros2_humble_ws/src/turtlebot3_autorace/` (source) and
`/root/ros2_humble_ws/install/` (build output, `--symlink-install`).
