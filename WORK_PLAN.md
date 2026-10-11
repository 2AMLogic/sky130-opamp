# Work Plan

This roadmap is generated from the repository's current Loom label state.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs stuck under a `loom:operator` merge-risk hold — implementation work is done, only a human merge decision is missing.

- **#93**: ratification: install ee-key and market-key reviewer trees; fix stale DR Status lines (#49)

## Operator Priority

Issues the operator starred (`loom:operator-priority`); land these first.

_None._

## Ready

Human-approved issues ready for implementation (`loom:issue`).

- **#110**: sim: evaluate independent supply extremes across the PVT process grid

## In Progress

Issues currently being built (`loom:building`).

- **#185**: Measure input-range contribution to the falling slew gap

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

_None._

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#93**: ratification: install ee-key and market-key reviewer trees; fix stale DR Status lines (#49)

## Proposed

Issues carrying `loom:curated`.

- **#3**: Track the gap to T1 sim-validated / bronze (klayout-tools design-evidence tiers) *(curated)*
- **#46**: T1 item 2, first increment: bring up the layout flow and lay out the first-stage matched groups (input pair and PMOS mirror), DRC clean and LVS matched *(curated)*
- **#49**: Install ratification/ee-key and ratification/market-key reviewer trees (product#151) *(curated)*
- **#121**: Extend opamp_stage1 with the grid-legal PMOS mirror and seven-pin LVS signoff *(curated)*
- **#147**: Offset closure: scoped technique study (trim / chopping / auto-zero) after sizing was found insufficient *(curated)*

## Proposed (Architect / Hermit)

- **#68**: tests: add simulator-free unit tests for psrr_noise_sweep.py *(architect)*
- **#190**: Reject malformed MOS geometry before manufacturing-grid arithmetic *(architect)*

## Epics

_None._

## Backlog Balance

| Tier | Count |
|------|-------|
| Operator merge-risk holds | 1 |
| Operator priority | 0 |
| Ready (`loom:issue`) | 1 |
| In Progress (`loom:building`) | 1 |
| PRs awaiting review | 0 |
| Approved PRs awaiting merge | 1 |
| Curated | 5 |
| Architect / Hermit proposals | 2 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
