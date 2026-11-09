# 10 — Verification

Every behavioural claim in these docs was measured with one of the probes below.
They live in `patches/ros2_ws/` and are copied into the container at `/root/`.

## Standard invocation

```bash
docker exec -it ros2-humble bash -c '
  source /opt/ros/humble/setup.bash
  source /root/ros2_humble_ws/install/setup.bash
  python3 -u /root/<probe>.py <args>'
```

---

## `track_odom.py <seconds>`

Samples `/odom` every 5 s and reports position, cumulative distance, and stall
detection. This is the top-level metric: **how far does the robot actually get**.

```bash
python3 -u /root/track_odom.py 240
```

```
[01:43:15] x=  1.150 y= -0.267 travelled= 1.409 m
[01:44:05] x=  1.581 y=  0.251 travelled= 5.335 m
[01:45:20] x=  0.418 y= -0.110 travelled= 9.715 m
[01:46:35] x=  0.872 y= -1.101 travelled=11.213 m
TOTAL travelled: 11.45 m over 240s (6954 odom msgs)
```

If consecutive samples share the same position, the robot is stalled; the last
position tells you where.

---

## `yaw_probe.py <seconds> [step]`

Prints heading (yaw) from `/odom` and the net rotation. This is how "did it turn
right?" is answered objectively.

```bash
python3 -u /root/yaw_probe.py 70 5
```

```
start yaw= +103.2 deg
[01:33:01] yaw= +169.4 deg (delta  +66.2) x=1.54 y=-0.72
NET TURN: -104.1 deg -> RIGHT (clockwise)
```

Yaw is computed from the quaternion with `atan2(2(wz + xy), 1 − 2(y² + z²))`.
Note that per-sample deltas wrap at ±180° — trust the **NET TURN** line.

---

## `reverse_audit.py <seconds>`

The regression test for the barrier-bar crash. Subscribes to `/cmd_vel` and
`/scan`; for every command with negative `linear.x` it records the rear distance
at that moment.

```bash
python3 -u /root/reverse_audit.py 150
```

```
reverse commands seen: 57
reversal episodes: 3
  01:28:51 v=-0.10 rear=0.52 m  OK
  01:29:07 v=-0.10 rear=0.50 m  OK
  01:29:16 v=-0.10 rear=0.50 m  OK
closest rear distance during any reversal: 0.50 m
reversals with rear < 0.30 m: 0
```

**Pass criteria:** `reversals with rear < 0.30 m: 0`.

---

## `scan_quadrant_probe.py <seconds>`

Prints front / left / right / rear minima from `/scan` and, on the second line,
which ray produced the rear minimum. It exists because the LiDAR angle convention
was wrong for a long time without anything failing loudly.

```bash
python3 -u /root/scan_quadrant_probe.py 24
```

```
[01:22:22] front=1.78 left=0.82 right=0.29 rear=inf
[01:22:30] front=1.05 left=0.60 right=1.31 rear=0.24
            rear ray at +321 deg (angle_min=+0 deg)
```

**Pass criteria:** all four sectors eventually report finite values. If `right`
is always `inf`, the angle wrapping is broken again.

---

## `state_monitor.py`

One line per second — the fastest way to see what the mission layer thinks.

```
[01:40:20] LIGHT=none   SIGN=3 MISSION=drive
[01:40:22] LIGHT=none   SIGN=3 MISSION=hold:obstacle
```

---

## Rate checks

```bash
timeout 6 ros2 topic hz /camera/image_rect          # expect ≈ 29.9 Hz
timeout 6 ros2 topic hz /camera/image_compensated   # expect 30–33.6 Hz
timeout 6 ros2 topic hz /cmd_vel                    # expect 10 Hz
```

## Single-writer check

```bash
ros2 topic info -v /cmd_vel
```

**Pass criteria:** exactly one publisher, `mission_supervisor`.

## One-simulator check

```bash
pgrep -a gzserver | wc -l     # expect 1
```

## Log checks

```bash
./ros2_docker.sh racewin                # panes + their commands
./ros2_docker.sh logs                   # window list
./ros2_docker.sh logs all               # everything, banner-separated
```

Decision log lines worth grepping:

```
DECIDE                          # sign decisions
turn complete                   # achieved angle + lane re-acquired/missing
recovery N/M                    # escape manoeuvres
rear blocked / reversal aborted # rear guard fired
progress made                   # escape budget reset
open-space turn                 # LiDAR-driven turn
```

---

## Reading exit codes

`grep -c pattern` exits **1 when the count is zero** — so "0 crashes found" looks
like a failed command in a `&&` chain or a background job. Add `|| true` when a
zero match is the desired result:

```bash
# this reports failure (exit 1) but printed the good answer: 0
grep -cE "UnboundLocal|has died" pane.txt

# this reports success
grep -cE "UnboundLocal|has died" pane.txt || true
```

## Verification summary (2026-10-28)

| Property | Result |
| --- | --- |
| `/camera/image_rect` | 29.932 Hz |
| `/camera/image_compensated` | 30–33.6 Hz |
| `/cmd_vel` | 10 Hz, single publisher |
| Light gating | red/yellow stop, green drive, latch after pass |
| Sign decision | majority vote, right confirmed on a right-only sign |
| Junction turn | 93° executed, net yaw −104° (right) |
| Reversal safety | min rear 0.50 m, 0 violations |
| Distance per 240 s | 11.45 m, still moving at the end |
| `bash -n` + `shellcheck -S warning` on `ros2_docker.sh` | clean |
