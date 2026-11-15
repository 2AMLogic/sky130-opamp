# Work Plan

Snapshot of the repository's Loom label state at the generating Guide tick — see this file's last commit date. Rows may have moved since; the live label state is authoritative.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

- **#287**: feat(spec): fill the PSRR row from a current-DUT grid and propose DR-015
- **#304**: spec: re-evaluate Consumers verdicts on DR-013 evidence, record measured opamp_core extent

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

- **#282**: Reconcile the PSRR spec row against the committed PSRR benches and propose a target

## Important

`loom:important`; taken before unlabelled work.

- **#196**: Measure paired offset drift before prototyping foreground trim
- **#274**: Grade the ratified input-referred-noise row on T1 item 5 (bench landed in #54; needs a graded quantity and limits)
- **#277**: Reconcile the ratified quiescent-power row with its T1 item-5 grading: what tolerance does its "≈" carry?

## Ready

Human-approved issues ready for implementation (`loom:issue`).

- **#294**: layout/: Magic drc_total and per-rule box counts are presented as if additive in evidence READMEs

## In Progress

Issues currently being built (`loom:building`).

- **#282**: Reconcile the PSRR spec row against the committed PSRR benches and propose a target
- **#283**: Bring manifests/integrator.json and the status prose up to the assembled opamp_core layout
- **#284**: Record the measured opamp_core area in the spec and refresh the Consumers verdicts to current evidence
- **#288**: Single-source the PVT corner/temp/supply table into sim/lib: four copies, one with the DR citation
- **#293**: Plumb batch.capacity_wait_s into the remaining klt sim campaign runners
- **#295**: Consolidate the duplicated DUT-include rewriting and the triplicated validate loop into sim/lib/dut_identity.py

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

_None._

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#287**: feat(spec): fill the PSRR row from a current-DUT grid and propose DR-015
- **#297**: refactor(sim): give the ratified PVT corner/temp/supply table one owner
- **#304**: spec: re-evaluate Consumers verdicts on DR-013 evidence, record measured opamp_core extent
- **#306**: refactor: single-source DUT-include rewrite and validate report loop in dut_identity
- **#310**: manifests: populate integrator gds and area from the assembled core layout

## Proposed

Issues carrying `loom:curated`.

- **#3**: Track the gap to T1 sim-validated / bronze (klayout-tools design-evidence tiers) *(curated)*
- **#188**: Auditor: refine worktree-write-confinement for sweep checkpoint writes *(curated)*
- **#196**: Measure paired offset drift before prototyping foreground trim *(curated)*
- **#274**: Grade the ratified input-referred-noise row on T1 item 5 (bench landed in #54; needs a graded quantity and limits) *(curated)*
- **#282**: Reconcile the PSRR spec row against the committed PSRR benches and propose a target *(curated)*
- **#283**: Bring manifests/integrator.json and the status prose up to the assembled opamp_core layout *(curated)*
- **#284**: Record the measured opamp_core area in the spec and refresh the Consumers verdicts to current evidence *(curated)*
- **#293**: Plumb batch.capacity_wait_s into the remaining klt sim campaign runners *(curated)*
- **#294**: layout/: Magic drc_total and per-rule box counts are presented as if additive in evidence READMEs *(curated)*

## Proposed (Architect / Hermit)

- **#278**: Remove the hand-rolled local ngspice executor from pvt_sweep.py: every record since 2026-10-10 used the klt path *(hermit)*
- **#298**: Drop the 263 legacy waveform.raw.json blobs: 116 MiB (72% of tracked bytes) that no record cites *(hermit)*
- **#301**: Consolidate the two comment-unaware SPICE continuation parsers in sim/offset-capability (the #237 remainder) *(hermit)*

## Epics

_None._

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 2 |
| Very important | 1 |
| Important | 3 |
| Ready (`loom:issue`) | 1 |
| In Progress (`loom:building`) | 6 |
| PRs awaiting review | 0 |
| Approved PRs awaiting merge | 5 |
| Curated | 9 |
| Architect / Hermit proposals | 3 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
