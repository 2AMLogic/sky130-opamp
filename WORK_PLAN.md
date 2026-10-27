# Work Plan

This roadmap is generated from the repository's current Loom label state.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

_None._

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

_None._

## Important

`loom:important`; taken before unlabelled work.

- **#54**: Add PSRR and input-referred noise benches to the PVT characterization
- **#196**: Measure paired offset drift before prototyping foreground trim

## Ready

Human-approved issues ready for implementation (`loom:issue`).

- **#196**: Measure paired offset drift before prototyping foreground trim

## In Progress

Issues currently being built (`loom:building`).

- **#246**: T1 item 5 (corner verification): re-run the PVT characterization through klt sim envelopes and cite them per ratified row
- **#247**: T1 item 7 (post-layout verification): klt pex of opamp_core against the ratified rows

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

_None._

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

_None._

## Proposed

Issues carrying `loom:curated`.

- **#3**: Track the gap to T1 sim-validated / bronze (klayout-tools design-evidence tiers) *(curated)*
- **#188**: Auditor: refine worktree-write-confinement for sweep checkpoint writes *(curated)*
- **#196**: Measure paired offset drift before prototyping foreground trim *(curated)*

## Proposed (Architect / Hermit)

- **#237**: Consolidate duplicated logical_lines and sha256 helpers across flow scripts *(hermit)*

## Epics

_None._

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 0 |
| Very important | 0 |
| Important | 2 |
| Ready (`loom:issue`) | 1 |
| In Progress (`loom:building`) | 2 |
| PRs awaiting review | 0 |
| Approved PRs awaiting merge | 0 |
| Curated | 3 |
| Architect / Hermit proposals | 1 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
