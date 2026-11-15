# Work Plan

This roadmap is generated from the repository's current Loom label state.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

_None._

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

- **#282**: Reconcile the PSRR spec row against the committed PSRR benches and propose a target

## Important

`loom:important`; taken before unlabelled work.

- **#196**: Measure paired offset drift before prototyping foreground trim
- **#274**: Grade the ratified input-referred-noise row on T1 item 5 (bench landed in #54; needs a graded quantity and limits)
- **#277**: Reconcile the ratified quiescent-power row with its T1 item-5 grading: what tolerance does its "≈" carry?
- **#281**: Clear the Magic resistor-head DRC failure in opamp_comp now that klayout-tools#3077 is closed

## Ready

Human-approved issues ready for implementation (`loom:issue`).

_None._

## In Progress

Issues currently being built (`loom:building`).

_None._

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

- **#280**: docs: roadmap as of 2026-11-13

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

_None._

## Proposed

Issues carrying `loom:curated`.

- **#3**: Track the gap to T1 sim-validated / bronze (klayout-tools design-evidence tiers) *(curated)*
- **#188**: Auditor: refine worktree-write-confinement for sweep checkpoint writes *(curated)*
- **#196**: Measure paired offset drift before prototyping foreground trim *(curated)*
- **#274**: Grade the ratified input-referred-noise row on T1 item 5 (bench landed in #54; needs a graded quantity and limits) *(curated)*

## Proposed (Architect / Hermit)

- **#278**: Remove the hand-rolled local ngspice executor from pvt_sweep.py: every record since 2026-10-10 used the klt path *(hermit)*

## Epics

_None._

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 0 |
| Very important | 1 |
| Important | 4 |
| Ready (`loom:issue`) | 0 |
| In Progress (`loom:building`) | 0 |
| PRs awaiting review | 1 |
| Approved PRs awaiting merge | 0 |
| Curated | 4 |
| Architect / Hermit proposals | 1 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
