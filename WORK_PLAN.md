# Work Plan

This roadmap is generated from the repository's current Loom label state.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs stuck under a `loom:operator` merge-risk hold — implementation work is done, only a human merge decision is missing.

_None._

## Operator Priority

Issues the operator starred (`loom:operator-priority`); land these first.

_None._

## Ready

Human-approved issues ready for implementation (`loom:issue`).

- **#54**: Add PSRR and input-referred noise benches to the PVT characterization

## In Progress

Issues currently being built (`loom:building`).

- **#85**: sim: run the offset Monte Carlo campaign (TT/SS/FF, batch fleet) on the #52 capability probe
- **#86**: sim: add a closed-loop small-step (overshoot/settling) bench to cross-check AC phase margin across PVT

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

_None._

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

_None._

## Proposed

Issues carrying `loom:curated`.

- **#3**: Track the gap to T1 sim-validated / bronze (klayout-tools design-evidence tiers) *(curated)*
- **#46**: T1 item 2, first increment: bring up the layout flow and lay out the first-stage matched groups (input pair and PMOS mirror), DRC clean and LVS matched *(curated)*
- **#47**: T1 item 5: evaluate the two structural fixes DR-007 names for the falling slew-rate gap and draft the superseding topology record *(curated)*

## Proposed (Architect / Hermit)

- **#68**: tests: add simulator-free unit tests for psrr_noise_sweep.py *(architect)*

## Epics

_None._

## Backlog Balance

| Tier | Count |
|------|-------|
| Operator merge-risk holds | 0 |
| Operator priority | 0 |
| Ready (`loom:issue`) | 1 |
| In Progress (`loom:building`) | 2 |
| PRs awaiting review | 0 |
| Approved PRs awaiting merge | 0 |
| Curated | 3 |
| Architect / Hermit proposals | 1 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
