# Work Plan

Snapshot of the repository's Loom label state at the generating Guide tick — see this file's last commit date. Rows may have moved since; the live label state is authoritative.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

- **#287**: feat(spec): fill the PSRR row from a current-DUT grid and propose DR-015
- **#304**: spec: re-evaluate Consumers verdicts on DR-013 evidence, record measured opamp_core extent
- **#320**: manifests: attest sim/lib/corners.py in the item-9 inventory

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

- **#282**: Reconcile the PSRR spec row against the committed PSRR benches and propose a target

## Important

`loom:important`; taken before unlabelled work.

- **#196**: Measure paired offset drift before prototyping foreground trim *(held)*
- **#274**: Grade the ratified input-referred-noise row on T1 item 5 (bench landed in #54; needs a graded quantity and limits) *(held)*
- **#277**: Reconcile the ratified quiescent-power row with its T1 item-5 grading: what tolerance does its "≈" carry? *(held)*

## Ready

Human-approved issues (`loom:issue`) ready for implementation — excluding held (`loom:blocked`/`loom:operator`/`loom:frozen`), `loom:building`, and issues closed by an open `loom:pr` PR (listed under Approved).

_None._

## In Progress

Issues currently being built (`loom:building`).

- **#282**: Reconcile the PSRR spec row against the committed PSRR benches and propose a target
- **#284**: Record the measured opamp_core area in the spec and refresh the Consumers verdicts to current evidence
- **#336**: xschem pin migration: migrate sky130-opamp to the fleet 3.4.7

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

- **#337**: ci: build fleet-pinned xschem 3.4.7 from source instead of noble apt 3.4.4

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#287**: feat(spec): fill the PSRR row from a current-DUT grid and propose DR-015 — closes #282
- **#304**: spec: re-evaluate Consumers verdicts on DR-013 evidence, record measured opamp_core extent — closes #284
- **#320**: manifests: attest sim/lib/corners.py in the item-9 inventory — closes #302

## Proposed

Issues carrying `loom:curated`.

- **#3**: Track the gap to T1 sim-validated / bronze (klayout-tools design-evidence tiers) *(curated)* *(held)*
- **#188**: Auditor: refine worktree-write-confinement for sweep checkpoint writes *(curated)* *(held)*
- **#196**: Measure paired offset drift before prototyping foreground trim *(curated)* *(held)*
- **#274**: Grade the ratified input-referred-noise row on T1 item 5 (bench landed in #54; needs a graded quantity and limits) *(curated)* *(held)*
- **#282**: Reconcile the PSRR spec row against the committed PSRR benches and propose a target *(curated)*
- **#284**: Record the measured opamp_core area in the spec and refresh the Consumers verdicts to current evidence *(curated)*
- **#302**: T1 item 9: no sim/lib module is attested, so the ratified corner table leaves the hashed surface once it has an owner module *(curated)*
- **#336**: xschem pin migration: migrate sky130-opamp to the fleet 3.4.7 *(curated)*

## Proposed (Architect / Hermit)

- **#278**: Remove the hand-rolled local ngspice executor from pvt_sweep.py: every record since 2026-10-10 used the klt path *(hermit)* *(held)*
- **#298**: Drop the 263 legacy waveform.raw.json blobs: 116 MiB (72% of tracked bytes) that no record cites *(hermit)* *(held)*
- **#301**: Consolidate the two comment-unaware SPICE continuation parsers in sim/offset-capability (the #237 remainder) *(hermit)* *(held)*

## Epics

_None._

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 3 |
| Very important | 1 |
| Important | 3 |
| Ready (`loom:issue`, net of holds/building/merge-pending) | 0 |
| In Progress (`loom:building`) | 3 |
| PRs awaiting review | 1 |
| Approved PRs awaiting merge | 3 |
| Curated | 8 |
| Architect / Hermit proposals | 3 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
