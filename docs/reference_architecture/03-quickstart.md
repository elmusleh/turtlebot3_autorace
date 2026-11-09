# 03 — Quickstart

## Prerequisites

- Linux with Docker (`docker ps` works without sudo)
- An X display for rqt/RViz2 (`xhost +local:docker` may be needed)
- ~10 GB free disk (image + workspace + Gazebo models)

## Install (once)

```bash
cd ~/Notebooks/Projects/ros2_examples
./install.sh
```

`install.sh` checks prerequisites, clones TurtleBot3 + AutoRace into
`~/ros2_humble_ws`, creates and starts the `ros2-humble` container
(`osrf/ros:humble-desktop-full`), installs Gazebo Classic and dependencies,
builds the workspace, and prints the next steps.

The host workspace is `~/ros2_humble_ws`; inside the container it is
`/root/ros2_humble_ws`. Edit files through the container (`docker exec` /
`docker cp`) — the host copy is root-owned.

## Apply this project's fixes

```bash
cp patches/ros2_ws/nodes/*.py   ~/ros2_humble_ws/src/turtlebot3_autorace/turtlebot3_autorace_detect/turtlebot3_autorace_detect/   # adjust per file
```

The authoritative list of where each file belongs is in
`patches/ros2_ws/README.md`. After copying, rebuild only what changed:

```bash
docker exec ros2-humble bash -c '
  source /opt/ros/humble/setup.bash
  cd /root/ros2_humble_ws
  colcon build --packages-select turtlebot3_autorace_mission --symlink-install'
```

`--symlink-install` matters: Python node edits then take effect without a
rebuild.

## Run the AutoRace

```bash
./ros2_docker.sh race              # mission=intersection (default)
./ros2_docker.sh race tunnel       # other mission template set
```

That starts a tmux session named `race` and **attaches to it immediately** when
run from a real terminal. Windows:

| Window | Name | Contents |
| --- | --- | --- |
| 0 | `sim` | Gazebo + spawn |
| 1 | `camera` | pane 0 rectify · pane 1 compensation |
| 2 | `detect` | pane 0 lane · pane 1 traffic light · pane 2 YOLO · pane 3 template signs |
| 3 | `control` | pane 0 supervisor + control_lane · pane 1 live state monitor · pane 2 `/cmd_vel` rate |
| 4 | `views` | pane 0 rqt camera · pane 1 RViz2 · pane 2 rqt annotated light |

tmux keys: `Ctrl-b w` window list · `Ctrl-b 0..4` go to window · `Ctrl-b d`
detach · `Ctrl-b z` zoom a pane.

The GUIs open at t=0 and stay blank until data arrives — that is intentional, so
you can watch from the first second instead of waiting 45 s.

## Other commands

```bash
./ros2_docker.sh raceattach     # re-attach to the running session
./ros2_docker.sh racewin        # list windows/panes with their commands
./ros2_docker.sh racestop       # Ctrl-C every pane, kill session, kill nodes
./ros2_docker.sh logs           # list race windows + /tmp/*.log
./ros2_docker.sh logs all       # dump every pane buffer
./ros2_docker.sh status         # container + AutoRace status
./ros2_docker.sh shell          # shell inside the container
./ros2_docker.sh stop           # stop the container
```

Run `./ros2_docker.sh` with no arguments for the interactive menu (container
1–6, tools 7–13, demos 14–16, AutoRace `r/t/w/k`, quick actions `a–f`,
`i` install, `0` exit).

## Watching it think

The monitor in `control` pane 1 prints one line per second:

```
[01:40:20] LIGHT=none   SIGN=3 MISSION=drive
[01:40:22] LIGHT=none   SIGN=3 MISSION=hold:obstacle
```

| `MISSION=` | Meaning |
| --- | --- |
| `drive` | Lane following, light green/none, path clear |
| `coast` | Lane momentarily lost, LiDAR corridor open — still moving |
| `turn` | Executing a sign manoeuvre or an open-space turn |
| `recover:back` / `recover:turn` | Backing out of a dead end, then turning (rear-guarded) |
| `hold:light:red` / `hold:light:yellow` | Stopped at the light |
| `hold:sign` | Paused at a sign to decide |
| `hold:obstacle` | LiDAR guard stop |
| `hold:no-lane-cmd` | No fresh lane command — stopped for safety |

`SIGN=` is the raw sign id (`0` none, `1` intersection, `2` left, `3` right). It
flickers between 2 and 3 on the same sign — that is known, and the supervisor
takes a majority vote instead of trusting one message.

## Stopping cleanly

```bash
./ros2_docker.sh racestop
```

Ctrl-C every pane, kill the tmux session, kill the node processes, and remove
stale FastRTPS shared memory. Always use this instead of closing the terminal —
a killed session leaves `gzserver` running and the next launch then has two
simulators fighting over `/odom`.

## When something looks wrong

Go straight to [11-troubleshooting.md](11-troubleshooting.md). The three most
common causes are: a leftover simulator, stale FastRTPS shm, and a missing
`rqt_image_view` package (each one has a one-line fix documented there).
