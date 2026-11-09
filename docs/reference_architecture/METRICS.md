# METRICS — run log

One line per measured run. The point is to answer *"is it better?"* with a
number instead of an impression, and to keep [roadmap](13-roadmap.md) P6 honest.

## How to add a row

Run the stack, let it drive, then:

```bash
# 1. distance (samples /odom; run while the robot drives)
docker exec -it ros2-humble bash -c '
  source /opt/ros/humble/setup.bash; source /root/ros2_humble_ws/install/setup.bash
  python3 -u /root/track_odom.py 240'      # prints "TOTAL travelled: N m over T s"

# 2. optionally the rear-safety audit
docker exec -it ros2-humble bash -c '
  source /opt/ros/humble/setup.bash; source /root/ros2_humble_ws/install/setup.bash
  python3 -u /root/reverse_audit.py 150'

# 3. fold everything into a row (counts are read from the tmux panes)
./patches/ros2_ws/run_summary.sh --distance 11.45 --duration 240 \
    --rear-min 0.50 --notes "+ escape-budget reset"
```

`run_summary.sh` counts sign turns, turn outcomes, open-space turns, recoveries,
coast samples and holds-by-reason straight from the terminal buffers, so the row
reflects what actually happened rather than what was intended.

## Column meanings

| Column | Source | Meaning |
| --- | --- | --- |
| Date | host clock | when the run ended |
| Mission | launch argument | template set in use |
| Dur | `track_odom` | seconds of observation |
| Dist | `track_odom` | metres travelled — the headline number |
| Sign turns | `DECIDE` lines | sign-driven turns executed |
| Lane re-acq / miss | `turn complete` lines | how many turns ended with the lane back |
| Open turns | `open-space turn` lines | LiDAR-driven turns (lane lost, no sign) |
| Recov | `recovery N/M` lines | escape manoeuvres (reverse + turn) |
| Coast | `MISSION=coast` samples (1 Hz) | seconds spent creeping on LiDAR instead of stopping |
| Holds | `MISSION=hold:*` samples | stall budget; dominated by `hold:sign` normally |
| Rear min | `reverse_audit` | closest anything got behind the robot while reversing |
| Notes | hand | what changed in this build |

## Runs

<!-- BEGIN RUNS -->
| Date | Mission | Dur (s) | Dist (m) | Sign turns | Lane re-acq / miss | Open turns | Recov | Coast | Holds | Rear min (m) | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-10-28 00:32 | construction | 95 | 0.20 | — | — | — | — | — | — | — | stalled at the junction: no arrow detection, no recovery path |
| 2026-10-28 01:17 | intersection | 165 | 5.40 | 1 | — | — | — | — | — | — | first full-angle right turn; stalled at the tunnel (`Lane state: 0`) |
| 2026-10-28 01:36 | intersection | 155 | 7.01 | 2 | 1 / 1 | 10 | 7 | 2 | 5 | — | coast + faster rates; dead-end spinning still present |
| 2026-10-28 01:41 | intersection | 180 | 8.47 | 2 | 1 / 1 | — | 8 | — | 5 | — | pocket detection (reverse instead of rotate in a dead end) |
| 2026-10-28 01:46 | intersection | 240 | 11.45 | 2 | 2 / 0 | 10 | 7 | 20 | 4 | — | ⚠ **invalid as progress**: the lane detector had crashed, so this distance was driven *off* the marked lane (user report: "crossed and walked away from the yellow and white lines") |
| 2026-10-28 02:09 | intersection | 180 | 5.32 | 1 | 1 / 0 | 0 | 0 | 0 | 20 | — | lane detector fixed (crash removed); robot now obeys the lane and stops at the tunnel instead of wandering |
| 2026-10-28 02:25 | intersection | 230 | — | 1 | 0 / 1 | 3 | 2 | — | 5 | — | white-line reference after the junction; sign turn 103° (was 117–131°) |
<!-- END RUNS -->

## Reverse-safety audits

Separate from distance runs: `reverse_audit.py` subscribes to `/cmd_vel` and
`/scan` and reports the rear distance for every reverse command. **Pass = zero
reversals with a rear distance below 0.30 m.**

| Date | Reverse commands | Episodes | Closest rear (m) | Violations | Notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-28 01:29 | 57 | 3 | 0.50 | 0 | rear guard verified after the barrier-bar collision fix |

## Baseline to beat

**11.45 m / 240 s** (intersection mission, 2026-10-28) — but read the warning
below before using it as a target.

### ⚠ A distance number is only meaningful if the robot stayed on the lane

The 11.45 m run looked like a 2× improvement over 5.4 m. It was not: the lane
detector had crashed early in that run (`UnboundLocalError: centerx`), so the
robot had no lane reference at all and drove on LiDAR free-space guesses. The user
saw exactly that — "the robot crossed and walked away from the yellow and white
lines".

Once the detector was fixed, the same configuration covered **5.32 m** and stopped
at the tunnel, which is *correct* behaviour: it obeys the lane and refuses to
guess.

**Rule: never record a distance without also recording whether the lane detector
was alive.** The `Notes` column must say so.

## Method notes

- Distances come from `/odom` integration in `track_odom.py`; the simulator's own
  odometry drifts slightly, so compare runs of equal duration, not absolute paths.
- Sample counts are 1 Hz (the state monitor), so "Coast 20" means ~20 s of coasting.
- A run that ends with the robot still moving is worth more than the distance
  suggests: the 11.45 m row was still travelling when sampling stopped.
- Runs before 2026-10-28 01:17 used the older control stack and are kept only as
  history — do not compare them against current builds.
