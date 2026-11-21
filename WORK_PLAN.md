# Work Plan

Snapshot of the repository's Loom label state at the generating Guide tick — see this file's last commit date. Rows may have moved since; the live label state is authoritative.

<!-- guide:plan-body:start -->
_Generated: 2026-11-21T05:40:26Z (snapshot; compare against live labels)_
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

- **#287**: feat(spec): fill the PSRR row from a current-DUT grid and propose DR-015
- **#304**: spec: re-evaluate Consumers verdicts on DR-013 evidence, record measured opamp_core extent
- **#320**: manifests: attest sim/lib/corners.py in the item-9 inventory
- **#350**: spec: propose DR-016 grading band for the slew-rate row
- **#352**: spec: propose DR-017 grading band for the quiescent-power row
- **#355**: spec: grade the noise row as the sampled floor per DR-018 with live fleet evidence

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

- **#282**: Reconcile the PSRR spec row against the committed PSRR benches and propose a target

## Important

`loom:important`; taken before unlabelled work.

- **#196**: Measure paired offset drift before prototyping foreground trim *(held)*
- **#274**: Grade the input-referred white-noise floor on T1 item 5
- **#277**: Propose a quiescent-power tolerance and report the T1 item-5 grade under it
- **#359**: Design iteration: screen an input-stage candidate that widens the common-mode range, against the ratified output-swing row (and the SS / -40 C fall-slew share)
- **#360**: Design iteration: screen a power-neutral class-AB output candidate for the output-current-limited fall slew

## Ready

Human-approved issues (`loom:issue`) ready for implementation — excluding held (`loom:blocked`/`loom:operator`/`loom:frozen`), `loom:building`, and issues closed by an open `loom:pr` PR (listed under Approved).

- **#360**: Design iteration: screen a power-neutral class-AB output candidate for the output-current-limited fall slew

## In Progress

Issues currently being built (`loom:building`).

- **#274**: Grade the input-referred white-noise floor on T1 item 5
- **#277**: Propose a quiescent-power tolerance and report the T1 item-5 grade under it
- **#282**: Reconcile the PSRR spec row against the committed PSRR benches and propose a target
- **#284**: Record the measured opamp_core area in the spec and refresh the Consumers verdicts to current evidence
- **#289**: The ratified slew row is also an "≈" row: item 5 grades rise SR at zero tolerance (19.88 vs 20.0 V/µs) while the spec calls it met
- **#336**: xschem pin migration: migrate sky130-opamp to the fleet 3.4.7
- **#342**: Single-source the simulator-free gate: tests.yml calls design/bin/check_ci.py; drop the workflow-comparison tests
- **#347**: Merge queue: add the merge_group trigger and adapt the PR-metadata gates
- **#358**: T1 item 5: grade the output-swing row with klt sim's slope_band form now that klayout-tools#5518 is closed
- **#359**: Design iteration: screen an input-stage candidate that widens the common-mode range, against the ratified output-swing row (and the SS / -40 C fall-slew share)

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

- **#337**: ci: build fleet-pinned xschem 3.4.7 from source instead of noble apt 3.4.4 *(held)*
- **#344**: ci: single-source the simulator-free gate in check_ci.py; drop the workflow-parity tests *(held)*
- **#348**: ci: run append-only check in the merge queue, failing closed on an unresolvable base *(held)*

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#287**: feat(spec): fill the PSRR row from a current-DUT grid and propose DR-015 — closes #282
- **#304**: spec: re-evaluate Consumers verdicts on DR-013 evidence, record measured opamp_core extent — closes #284
- **#320**: manifests: attest sim/lib/corners.py in the item-9 inventory — closes #302
- **#350**: spec: propose DR-016 grading band for the slew-rate row — closes #289
- **#352**: spec: propose DR-017 grading band for the quiescent-power row — closes #277
- **#355**: spec: grade the noise row as the sampled floor per DR-018 with live fleet evidence — closes #274

## Proposed

Issues carrying `loom:curated`.

- **#3**: Track the gap to T1 sim-validated / bronze (klayout-tools design-evidence tiers) *(curated)* *(held)*
- **#188**: Auditor: refine worktree-write-confinement for sweep checkpoint writes *(curated)* *(held)*
- **#196**: Measure paired offset drift before prototyping foreground trim *(curated)* *(held)*
- **#274**: Grade the input-referred white-noise floor on T1 item 5 *(curated)*
- **#277**: Propose a quiescent-power tolerance and report the T1 item-5 grade under it *(curated)*
- **#282**: Reconcile the PSRR spec row against the committed PSRR benches and propose a target *(curated)*
- **#284**: Record the measured opamp_core area in the spec and refresh the Consumers verdicts to current evidence *(curated)*
- **#289**: The ratified slew row is also an "≈" row: item 5 grades rise SR at zero tolerance (19.88 vs 20.0 V/µs) while the spec calls it met *(curated)*
- **#302**: T1 item 9: no sim/lib module is attested, so the ratified corner table leaves the hashed surface once it has an owner module *(curated)*
- **#336**: xschem pin migration: migrate sky130-opamp to the fleet 3.4.7 *(curated)*
- **#342**: Single-source the simulator-free gate: tests.yml calls design/bin/check_ci.py; drop the workflow-comparison tests *(curated)*
- **#347**: Merge queue: add the merge_group trigger and adapt the PR-metadata gates *(curated)*
- **#358**: T1 item 5: grade the output-swing row with klt sim's slope_band form now that klayout-tools#5518 is closed *(curated)*
- **#359**: Design iteration: screen an input-stage candidate that widens the common-mode range, against the ratified output-swing row (and the SS / -40 C fall-slew share) *(curated)*
- **#361**: T1 item 5: commit a CMRR klt sim envelope with DR-008's proposed limits on the current DUT, then open DR-008's ratification PR *(curated)* *(held)*

## Proposed (Architect / Hermit)

- **#278**: Remove the hand-rolled local ngspice executor from pvt_sweep.py: every record since 2026-10-10 used the klt path *(hermit)* *(held)*
- **#298**: Drop the 263 legacy waveform.raw.json blobs: 116 MiB (72% of tracked bytes) that no record cites *(hermit)* *(held)*
- **#301**: Consolidate the two comment-unaware SPICE continuation parsers in sim/offset-capability (the #237 remainder) *(hermit)* *(held)*

## Epics

_None._

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 6 |
| Very important | 1 |
| Important | 5 |
| Ready (`loom:issue`, net of holds/building/merge-pending) | 1 |
| In Progress (`loom:building`) | 10 |
| PRs awaiting review | 3 |
| Approved PRs awaiting merge | 6 |
| Curated | 15 |
| Architect / Hermit proposals | 3 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
