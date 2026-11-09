# ADR 0005 — `intersection` is the default mission

**Status:** Accepted (in force)

## Context

`detect_sign.launch.py mission:=<name>` selects a **template set** for the sign
detector. The sets are per-course-section: `construction`, `intersection`,
`parking`, `tunnel`, `level_crossing`.

The T-junction arrow sign in the AutoRace 2020 course is not in the
**construction** template set. With the original default
(`mission=construction`), `/detect/traffic_sign` stayed `0` for the entire run:

```
SIGN=0  SIGN=0  SIGN=0 ...
```

The robot reached the junction, found no lane ahead, and simply stopped. Nothing
was broken in the control layer — the information never arrived.

## Decision

Make **`intersection`** the default everywhere:

| Location | Change |
| --- | --- |
| `ros2_docker.sh` `cmd_race()` | `local mission="${1:-intersection}"` |
| dispatch | `race) cmd_race "${2:-intersection}"` |
| `run_tb3_race_tmux.sh` | `MISSION=${MISSION:-intersection}` |
| docs / usage | `./ros2_docker.sh race [mission]` |

## Consequences

**Good**
- The T-junction arrow is recognised: `Detect right sign` continuous, `SIGN=3`
  dominant.
- Missions remain selectable per run: `./ros2_docker.sh race tunnel`.

**Bad**
- Running a different section now requires naming it explicitly; the default is not
  a universal superset.
- The template sets are mutually exclusive by design upstream; a course that mixes
  sections (construction *and* junction) would need the detector to switch at
  runtime — not implemented.

## Note on shell safety

The first implementation wrote `Mission=${MISSION:-intersection}` (capital `M`).
The launcher runs under `set -u`, so the lower-case `MISSION` reference later in
the script would have aborted the run. Caught and corrected immediately —
worth remembering when editing `${VAR:-default}` lines.
