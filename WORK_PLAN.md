# Work Plan

Snapshot of the repository's Loom label state at the generating Guide tick — see this file's last commit date. Rows may have moved since; the live label state is authoritative.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

- **#287**: feat(spec): fill the PSRR row from a current-DUT grid and propose DR-015
- **#304**: spec: re-evaluate Consumers verdicts on DR-013 evidence, record measured opamp_core extent
- **#355**: spec: grade the noise row as the sampled floor per DR-018 with live fleet evidence
- **#365**: sim: input-stage icmr-rebias screen — 17-point fleet evidence, collation, DR-015 (proposed)
- **#370**: refactor(sim): key the remaining PVT point joins through sim/lib/point_identity
- **#372**: docs: re-ground DR-017's −0% rejection on the exact-bound argument
- **#374**: docs(dr-017): list DR-007 in the Related entries

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

- **#282**: Reconcile the PSRR spec row against the committed PSRR benches and propose a target

## Important

`loom:important`; taken before unlabelled work.

- **#196**: Measure paired offset drift before prototyping foreground trim *(held)*
- **#274**: Grade the input-referred white-noise floor on T1 item 5
- **#359**: Design iteration: screen an input-stage candidate that widens the common-mode range, against the ratified output-swing row (and the SS / -40 C fall-slew share)
- **#360**: Design iteration: screen a power-neutral class-AB output candidate for the output-current-limited fall slew

## Ready

Ready counts issues with `loom:issue`. It excludes issues on hold (`loom:blocked`, `loom:operator`, or `loom:frozen`), issues already being built (`loom:building`), and issues an open approved PR (`loom:pr`) will close. The Approved section lists those PRs and their issues.

- **#360**: Design iteration: screen a power-neutral class-AB output candidate for the output-current-limited fall slew

## In Progress

Issues currently being built (`loom:building`).

- **#274**: Grade the input-referred white-noise floor on T1 item 5
- **#278**: Remove the hand-rolled local ngspice executor from pvt_sweep.py: every record since 2026-10-10 used the klt path
- **#284**: Record the measured opamp_core area in the spec and refresh the Consumers verdicts to current evidence
- **#336**: xschem pin migration: migrate sky130-opamp to the fleet 3.4.7
- **#342**: Single-source the simulator-free gate: tests.yml calls design/bin/check_ci.py; drop the workflow-comparison tests
- **#347**: Merge queue: add the merge_group trigger and adapt the PR-metadata gates
- **#353**: DR-017 lower-side rationale cites the superseded DR-002 grid without saying so
- **#358**: T1 item 5: grade the output-swing row with klt sim's slope_band form now that klayout-tools#5518 is closed
- **#359**: Design iteration: screen an input-stage candidate that widens the common-mode range, against the ratified output-swing row (and the SS / -40 C fall-slew share)
- **#369**: Consolidate the remaining six (corner, temp_c, vdd_v) point-key copies in pvt_sweep.py and pex_measure.py onto sim/lib/point_identity.py
- **#373**: DR-017 cites DR-007 inline but omits it from the Related list

## PRs Awaiting Review

PRs with `loom:review-requested`. Judge can review a held PR once its operator hold is lifted.

- **#337**: ci: build fleet-pinned xschem 3.4.7 from source instead of noble apt 3.4.4 *(held)*
- **#344**: ci: single-source the simulator-free gate in check_ci.py; drop the workflow-parity tests *(held)*
- **#348**: ci: run append-only check in the merge queue, failing closed on an unresolvable base *(held)*
- **#378**: refactor: remove the local ngspice executor from pvt_sweep.py, klt sim becomes the only executor

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#287**: feat(spec): fill the PSRR row from a current-DUT grid and propose DR-015 — closes #282
- **#304**: spec: re-evaluate Consumers verdicts on DR-013 evidence, record measured opamp_core extent — closes #284
- **#355**: spec: grade the noise row as the sampled floor per DR-018 with live fleet evidence — closes #274
- **#365**: sim: input-stage icmr-rebias screen — 17-point fleet evidence, collation, DR-015 (proposed) — closes #359
- **#370**: refactor(sim): key the remaining PVT point joins through sim/lib/point_identity — closes #369
- **#372**: docs: re-ground DR-017's −0% rejection on the exact-bound argument — closes #353
- **#374**: docs(dr-017): list DR-007 in the Related entries — closes #373

## Proposed

Issues carrying `loom:curated`.

- **#3**: Track the gap to T1 sim-validated / bronze (klayout-tools design-evidence tiers) *(curated)* *(held)*
- **#188**: Auditor: refine worktree-write-confinement for sweep checkpoint writes *(curated)* *(held)*
- **#196**: Measure paired offset drift before prototyping foreground trim *(curated)* *(held)*
- **#274**: Grade the input-referred white-noise floor on T1 item 5 *(curated)*
- **#278**: Remove the hand-rolled local ngspice executor from pvt_sweep.py: every record since 2026-10-10 used the klt path *(curated)*
- **#282**: Reconcile the PSRR spec row against the committed PSRR benches and propose a target *(curated)*
- **#284**: Record the measured opamp_core area in the spec and refresh the Consumers verdicts to current evidence *(curated)*
- **#336**: xschem pin migration: migrate sky130-opamp to the fleet 3.4.7 *(curated)*
- **#342**: Single-source the simulator-free gate: tests.yml calls design/bin/check_ci.py; drop the workflow-comparison tests *(curated)*
- **#347**: Merge queue: add the merge_group trigger and adapt the PR-metadata gates *(curated)*
- **#353**: DR-017 lower-side rationale cites the superseded DR-002 grid without saying so *(curated)*
- **#358**: T1 item 5: grade the output-swing row with klt sim's slope_band form now that klayout-tools#5518 is closed *(curated)*
- **#359**: Design iteration: screen an input-stage candidate that widens the common-mode range, against the ratified output-swing row (and the SS / -40 C fall-slew share) *(curated)*
- **#361**: T1 item 5: commit a CMRR klt sim envelope with DR-008's proposed limits on the current DUT, then open DR-008's ratification PR *(curated)* *(held)*
- **#373**: DR-017 cites DR-007 inline but omits it from the Related list *(curated)*

## Proposed (Architect / Hermit)

- **#298**: Drop the 263 legacy waveform.raw.json blobs: 116 MiB (72% of tracked bytes) that no record cites *(hermit)* *(held)*
- **#301**: Consolidate the two comment-unaware SPICE continuation parsers in sim/offset-capability (the #237 remainder) *(hermit)*
- **#377**: Consolidate duplicated gm/ID sweep and grid-sizing helpers across sim/opamp-characterization/variants/ *(hermit)*

## Epics

_None._

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 7 |
| Very important | 1 |
| Important | 4 |
| Ready (`loom:issue`, excluding holds, builds in progress, and issues awaiting merge) | 1 |
| In Progress (`loom:building`) | 11 |
| PRs awaiting review | 4 |
| Approved PRs awaiting merge | 7 |
| Curated | 15 |
| Architect / Hermit proposals | 3 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
