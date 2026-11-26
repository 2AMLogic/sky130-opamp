# Work Plan

Snapshot of the repository's Loom label state at the generating Guide tick — see this file's last commit date. Rows may have moved since; the live label state is authoritative.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

- **#304**: spec: re-evaluate Consumers verdicts on DR-013 evidence, record measured opamp_core extent
- **#355**: Characterize the sampled noise minimum and keep thermal-floor signoff open
- **#370**: refactor(sim): key the remaining PVT point joins through sim/lib/point_identity
- **#372**: docs: re-ground DR-017's −0% rejection on the exact-bound argument
- **#374**: docs(dr-017): list DR-007 in the Related entries
- **#403**: fix: normalize PVT report lookups and ICMR coverage checks

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

- **#282**: Reconcile the PSRR spec row against the committed PSRR benches and propose a target *(held)*

## Important

`loom:important`; taken before unlabelled work.

- **#196**: Measure paired offset drift before prototyping foreground trim *(held)*
- **#274**: Grade the input-referred white-noise floor on T1 item 5
- **#360**: Design iteration: screen a power-neutral class-AB output candidate for the output-current-limited fall slew
- **#396**: Improve DC PSRR on both rails toward the proposed 70 dB floor

## Ready

Ready counts issues with `loom:issue`. It excludes issues on hold (`loom:blocked`, `loom:operator`, or `loom:frozen`), issues already being built (`loom:building`), and issues an open approved PR (`loom:pr`) will close. The Approved section lists those PRs and their issues.

- **#360**: Design iteration: screen a power-neutral class-AB output candidate for the output-current-limited fall slew
- **#408**: Remove the process-wide PVT report list so each campaign grades only its own measurements

## In Progress

Issues currently being built (`loom:building`).

- **#274**: Grade the input-referred white-noise floor on T1 item 5
- **#284**: Record the measured opamp_core area in the spec and refresh the Consumers verdicts to current evidence
- **#336**: xschem pin migration: migrate sky130-opamp to the fleet 3.4.7
- **#342**: Single-source the simulator-free gate: tests.yml calls design/bin/check_ci.py; drop the workflow-comparison tests
- **#347**: Merge queue: add the merge_group trigger and adapt the PR-metadata gates
- **#353**: DR-017 lower-side rationale cites the superseded DR-002 grid without saying so
- **#369**: Consolidate the remaining six (corner, temp_c, vdd_v) point-key copies in pvt_sweep.py and pex_measure.py onto sim/lib/point_identity.py
- **#373**: DR-017 cites DR-007 inline but omits it from the Related list
- **#396**: Improve DC PSRR on both rails toward the proposed 70 dB floor
- **#402**: Use shared point identity for PVT report lookups, Cartesian supplies and ICMR row matching

## PRs Awaiting Review

PRs with `loom:review-requested`. Judge can review a held PR once its operator hold is lifted.

- **#337**: ci: build fleet-pinned xschem 3.4.7 from source instead of noble apt 3.4.4 *(held)*
- **#344**: ci: single-source the simulator-free gate in check_ci.py; drop the workflow-parity tests *(held)*
- **#348**: ci: run append-only check in the merge queue, failing closed on an unresolvable base *(held)*
- **#407**: feat: record M3/M4/M5 length candidate for DC PSRR and reject on GBW/slew regression

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#287**: feat(spec): record measured PSRR and propose a 70 dB DC target in DR-019 — closes #282
- **#304**: spec: re-evaluate Consumers verdicts on DR-013 evidence, record measured opamp_core extent — closes #284
- **#355**: Characterize the sampled noise minimum and keep thermal-floor signoff open
- **#370**: refactor(sim): key the remaining PVT point joins through sim/lib/point_identity — closes #369
- **#372**: docs: re-ground DR-017's −0% rejection on the exact-bound argument — closes #353
- **#374**: docs(dr-017): list DR-007 in the Related entries — closes #373
- **#403**: fix: normalize PVT report lookups and ICMR coverage checks — closes #402

## Proposed

Issues carrying `loom:curated`.

- **#3**: Track the gap to T1 sim-validated / bronze (klayout-tools design-evidence tiers) *(curated)* *(held)*
- **#188**: Auditor: refine worktree-write-confinement for sweep checkpoint writes *(curated)* *(held)*
- **#196**: Measure paired offset drift before prototyping foreground trim *(curated)* *(held)*
- **#274**: Grade the input-referred white-noise floor on T1 item 5 *(curated)*
- **#282**: Reconcile the PSRR spec row against the committed PSRR benches and propose a target *(curated)* *(held)*
- **#284**: Record the measured opamp_core area in the spec and refresh the Consumers verdicts to current evidence *(curated)*
- **#336**: xschem pin migration: migrate sky130-opamp to the fleet 3.4.7 *(curated)*
- **#342**: Single-source the simulator-free gate: tests.yml calls design/bin/check_ci.py; drop the workflow-comparison tests *(curated)*
- **#347**: Merge queue: add the merge_group trigger and adapt the PR-metadata gates *(curated)*
- **#353**: DR-017 lower-side rationale cites the superseded DR-002 grid without saying so *(curated)*
- **#358**: T1 item 5: grade the output-swing row with klt sim's slope_band form now that klayout-tools#5518 is closed *(curated)* *(held)*
- **#361**: T1 item 5: commit a CMRR klt sim envelope with DR-008's proposed limits on the current DUT, then open DR-008's ratification PR *(curated)* *(held)*
- **#373**: DR-017 cites DR-007 inline but omits it from the Related list *(curated)*
- **#396**: Improve DC PSRR on both rails toward the proposed 70 dB floor *(curated)*
- **#402**: Use shared point identity for PVT report lookups, Cartesian supplies and ICMR row matching *(curated)*

## Proposed (Architect / Hermit)

- **#394**: Drop the two ignored options from the current-offset DUT check *(hermit)* *(held)*

## Epics

_None._

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 6 |
| Very important | 1 |
| Important | 4 |
| Ready (`loom:issue`, excluding holds, builds in progress, and issues awaiting merge) | 2 |
| In Progress (`loom:building`) | 10 |
| PRs awaiting review | 4 |
| Approved PRs awaiting merge | 7 |
| Curated | 15 |
| Architect / Hermit proposals | 1 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
