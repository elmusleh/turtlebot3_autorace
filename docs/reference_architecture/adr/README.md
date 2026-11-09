# Architecture Decision Records

Short records of decisions that shaped this project. Each one states the context
(the failure that forced it), the decision, and the consequences — including the
bad ones.

| ADR | Title | Status |
| --- | --- | --- |
| [0001](0001-single-cmd-vel-owner.md) | `mission_supervisor` is the sole writer of `/cmd_vel` | Accepted |
| [0002](0002-traffic-light-heartbeat.md) | The traffic-light detector publishes a heartbeat | Accepted |
| [0003](0003-standalone-rectify-node.md) | A standalone `rectify_node` instead of a component container | Accepted |
| [0004](0004-compensation-reads-rect.md) | Compensation reads the rectified image, with both remaps | Accepted |
| [0005](0005-intersection-default-mission.md) | `intersection` is the default mission | Accepted |
| [0006](0006-sign-turn-semantics.md) | Turn semantics: direction from the sign, angle always complete, one turn per junction | Accepted |
| [0007](0007-rear-guard.md) | Guard the rear before reversing | Accepted |
| [0008](0008-coast-instead-of-spin.md) | Coast on LiDAR free space instead of spinning in place | Accepted |

## Format

```
# ADR NNNN — Title
**Status:** Proposed | Accepted | Superseded by NNNN
## Context      what forced a decision
## Decision     what was decided, precisely
## Consequences good, bad, risks
## Alternatives rejected (optional)
## Verification (optional)  how the decision is checked
```

## When to add one

Add an ADR when a change:
- introduces or removes a single-owner invariant (like `/cmd_vel`),
- changes a topic contract that other packages depend on,
- makes a trade-off you would otherwise have to re-explain (accuracy vs. effort,
  safety vs. progress),
- fixes a bug whose cause was a **platform quirk** rather than a logic error.

Do not add one for parameter tuning; that belongs in
[06-mission-control.md](../06-mission-control.md) and
[08-navigation-behavior.md](../08-navigation-behavior.md).
