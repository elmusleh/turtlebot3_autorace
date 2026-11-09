# 13 — Roadmap and known gaps

Ordered by impact on completing the course, not by effort.

## P1 — Lane detection at the tunnel (root cause of most remaining slowness)

**Problem.** `detect_lane` reports `Lane state: 0` at the tunnel and whenever the
line runs under the robot's nose. Every coast, open-space turn and recovery in the
logs traces back to this.

**Likely cause.** The upstream detector is designed to run on properly
extrinsic-calibrated, back-projected images. This project replaced that with a
compensation node running default parameters, so the projection is approximate.

**Options, cheapest first:**
1. Tune `param/lane/lane.yaml` (ROI, HSV thresholds) for the tunnel's dark floor
   and the line position at the frame edge.
2. Run the lane detector on both the normal and a contrast-boosted copy of the
   frame, and use whichever returns both lines.
3. Run the real calibration once (intrinsic + extrinsic) and feed the detector
   correctly projected images. Highest quality, most work.

**Success metric:** `Lane state` stays non-zero through the tunnel section on a
full lap.

## P2 — Geometric arrow detector (replace the flickering templates)

**Problem.** The template matcher alternates left/right on the same sign, which
forces the majority vote and can still pick wrong.

**Proposal.** Detect the blue sign (HSV blue blob, area/aspect filtered), then
compute the white arrow's centroid relative to the blob centre — right of centre =
right arrow. Publish the same `UInt8` contract (1/2/3) so nothing downstream
changes.

**Why it is better:** stable id, independent of the mission template set, and it
works when the sign is partly cropped.

**Success metric:** `SIGN` holds one value for the whole approach; no `DECIDE
left` on a right-only sign.

## P3 — Turn termination without overshoot  ✅ (substantially done)

**Problem.** When the lane detector stays silent during the rotation, the turn ran
to the 1.4× cap (observed 129–131° instead of 90°) and the robot ended misaligned,
then coasted to recover.

**Done.** `turn_overshoot` = 1.0 — a scripted sign turn performs exactly the
signalled angle plus 0.15 s of tick quantisation. Measured **103°** (was 117–131°).
`after_turn_settle` (4 s) also suppresses open-space turns right after a sign turn;
previously 48–76° follow-up rotations compounded the error.

**Still open:** an obstacle immediately after the turn can still trigger a recovery
rotation — the settle only covers search turns.

## P4 — Side-collision clamp

**Problem.** Wall avoidance is a correction, not a limit. A bar appearing within
0.2 m beside the robot while moving forward may still be hit.

**Proposal.** When `wall_left` or `wall_right` < 0.20 m, clamp `angular.z` to the
direction away from it (and reduce speed further), rather than adding a term that
the lane controller can outvote.

## P5 — Full-course missions

Today the default mission is `intersection` with `max_turns = 2`. Parking, tunnel
and level-crossing missions exist as template sets but are not tuned.

**Proposal.** Per-mission parameter sets (launch arguments already support this)
plus a mission sequence runner that advances when a stage completes.

## P6 — Run summary and regression baseline

**Proposal.** On shutdown, log one line: distance, turns, recoveries, coast time,
holds by reason. Run it in CI-ish fashion (headless, fixed duration) and compare
against the current baseline (11.45 m / 240 s) to catch regressions.

## P7 — Documentation upkeep

Keep `docs/` and `.ai-sync/` current in the same commit as the behaviour change.
A stale handoff costs more than a missing one.

---

## Explicitly not planned

- Real-hardware support (different sensors, different timing).
- Machine-learning lane following (the LiDAR fallback covers the gaps cheaply).
- Rewriting the upstream AutoRace packages — this project patches around them via
  new nodes and launch files, which keeps upgrades possible.
