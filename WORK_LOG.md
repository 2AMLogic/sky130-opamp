# Work Log

Chronological record of merged pull requests and closed issues, maintained by the Loom Guide role. Newest entries appear first.

## Archives

- [2026-09](work_log/WORK_LOG_2026-09.md)

### 2026-11-26

- **PR #406**: fix: share MOS card parsing across op-amp variants
- **Issue #405** (closed): Consolidate duplicated variant MOS-card helpers, continuation parsers, and dead bindings onto variants/_gmid.py
- **PR #401**: fix: reject mc-only CLI flags on sink_bias_margin static subcommand
- **Issue #400** (closed): Drop the four ignored mc-only flags from sink_bias_margin.py static
- **PR #399**: fix: log fleet capacity waits from the ICMR-aware slew submitter too
- **Issue #395** (closed): Share the PVT capacity-retry loop so ICMR-aware slew logs its waits
- **PR #398**: fix: reuse the shared gm/ID sweep loader in input-stage sizing
- **Issue #397** (closed): Restore input-stage sizing by reusing the shared gm/ID sweep loader
- **PR #393**: perf: compute buffer headroom only for fixed-CM comparisons
- **Issue #391** (closed): Skip buffer headroom extraction when the fixed-common-mode comparison is disabled

### 2026-11-25

- **PR #365**: sim: input-stage icmr-rebias screen — 17-point fleet evidence, collation, DR-015 (proposed)
- **Issue #359** (closed): Design iteration: screen an input-stage candidate that widens the common-mode range, against the ratified output-swing row (and the SS / -40 C fall-slew share)

### 2026-11-24

- **PR #363**: feat(sim): emit the ratified output-swing row natively as gated slope_band entries
- **PR #378**: refactor: remove the local ngspice executor from pvt_sweep.py, klt sim becomes the only executor
- **Issue #278** (closed): Remove the hand-rolled local ngspice executor from pvt_sweep.py: every record since 2026-10-10 used the klt path
- **PR #384**: chore: drop 262 uncited waveform.raw.json dumps from sim records
- **Issue #298** (closed): Drop the 263 legacy waveform.raw.json blobs: 116 MiB (72% of tracked bytes) that no record cites
- **PR #386**: refactor: derive stage_reference logical_lines from shared spice_text joiner
- **Issue #385** (closed): Fold layout stage_reference.logical_lines into shared lib/spice_text.join_continuations

### 2026-11-23

- **PR #381**: refactor: consolidate SPICE continuation joining into lib/spice_text.py
- **Issue #301** (closed): Consolidate the two comment-unaware SPICE continuation parsers in sim/offset-capability (the #237 remainder)
- **Issue #383** (closed): Guide doc-maintenance appended 87 foreign work-log entries to WORK_LOG.md (PR #382)
- **PR #380**: refactor: extract shared gm/ID helpers into variants/_gmid.py
- **Issue #377** (closed): Consolidate duplicated gm/ID sweep and grid-sizing helpers across sim/opamp-characterization/variants/

### 2026-11-22

- **PR #375**: refactor: consolidate duplicate check_toolchain into layout/bin/_klt_common.py
- **Issue #371** (closed): Consolidate compose-cell.py and probe-passives.py's duplicate check_toolchain into layout/bin/_klt_common.py (the #227 remainder)
- **PR #350**: spec: propose DR-016 grading band for the slew-rate row
- **Issue #289** (closed): The ratified slew row is also an "≈" row: item 5 grades rise SR at zero tolerance (19.88 vs 20.0 V/µs) while the spec calls it met
- **PR #320**: manifests: attest sim/lib/corners.py in the item-9 inventory
- **Issue #302** (closed): T1 item 9: no sim/lib module is attested, so the ratified corner table leaves the hashed surface once it has an owner module
- **PR #352**: spec: propose DR-017 grading band for the quiescent-power row
- **Issue #277** (closed): Propose a quiescent-power tolerance and report the T1 item-5 grade under it

### 2026-11-17

- **Issue #339** (closed): WORK_PLAN's Ready bucket reports 0 while #302 carries loom:issue
- **PR #333**: chore(loom): resync installed Loom to v0.19.1306

### 2026-11-16

- **PR #327**: chore(loom): resync installed Loom to v0.19.1302

### 2026-11-15

- **PR #325**: fix(sim): gate psrr_noise_sweep's batch block on the backend, not --runner-version-check
- **Issue #315** (closed): psrr_noise_sweep emits its batch block only with --runner-version-check, so the default fleet submit carries no capacity_wait_s
- **PR #323**: docs: drop stale T1-item-2-unmet and GDS-null clauses from sub-block READMEs
- **Issue #319** (closed): Three sibling sub-block READMEs still say T1 item 2 is `unmet` and the integrator GDS is null
- **PR #322**: refactor: import BATCH_CAPACITY_WAIT_S from spice_harness in pvt_sweep
- **Issue #321** (closed): Remove pvt_sweep's duplicate BATCH_CAPACITY_WAIT_S: #297 landed, grandfathering is over
- **PR #305**: fix(sim): plumb batch.capacity_wait_s (600) into the remaining klt sim request builders
- **Issue #293** (closed): Plumb batch.capacity_wait_s into the remaining klt sim campaign runners
- **PR #318**: docs: drop integrator-null and item-2-unmet prose overtaken by PR #310
- **Issue #311** (closed): ROADMAP.md 'Now 3' and layout/opamp_out/README.md still say the integrator GDS is null
- **PR #317**: fix: single-source the last two escaped corner-list copies into sim/lib/corners.py
- **Issue #296** (closed): Two more re-typed copies of the ratified corner list escaped #288's scope: offset_probe.py and sizing_check.py
- **PR #314**: docs: label Magic drc_total separately from drc listall why box counts in layout evidence
- **Issue #294** (closed): layout/: Magic drc_total and per-rule box counts are presented as if additive in evidence READMEs
- **PR #306**: refactor: single-source DUT-include rewrite and validate report loop in dut_identity
- **Issue #295** (closed): Consolidate the duplicated DUT-include rewriting and the triplicated validate loop into sim/lib/dut_identity.py
- **PR #310**: manifests: populate integrator gds and area from the assembled core layout
- **Issue #283** (closed): Bring manifests/integrator.json and the status prose up to the assembled opamp_core layout
- **PR #297**: refactor(sim): give the ratified PVT corner/temp/supply table one owner
- **Issue #288** (closed): Single-source the PVT corner/temp/supply table into sim/lib: four copies, one with the DR citation
- **PR #312**: docs: replace WORK_PLAN currency claim with snapshot wording
- **Issue #303** (closed): WORK_PLAN.md asserts 'current' label state but carries no generation timestamp
- **PR #308**: test: hold pin-sync negative control to 1:1 anchor/location correspondence
- **PR #300**: refactor(sim): give the PVT point-identity convention one owner that both validators share
- **Issue #299** (closed): Pin-sync negative control: make the 1:1 anchor invariant a distinctness check, not a count check
- **Issue #291** (closed): Single-source the (corner, temp_c, vdd_v) point-identity convention: three copies, and the two validating copies already disagree

### 2026-11-14

- **PR #292**: docs(opamp_comp): record klt 0.8.0 as measured-and-rejected for the resistor-head DRC blocker
- **PR #290**: test: extract the shared pin-sync harness and deepen the PDK negative control
- **PR #280**: docs: roadmap as of 2026-11-13
- **Issue #286** (closed): Consolidate the duplicated pin-sync test harness: test_pdk_pin_sync and test_klt_pin_sync have drifted
- **Issue #281** (closed): Clear the Magic resistor-head DRC failure in opamp_comp now that klayout-tools#3077 is closed

### 2026-11-13

- **PR #275**: feat(item5): grade the ratified spec rows inside the klt sim envelopes and cite them
- **Issue #246** (closed): T1 item 5 (corner verification): re-run the PVT characterization through klt sim envelopes and cite them per ratified row
- **Issue #273** (closed): Follow-on: Work identified in PR #272

### 2026-11-06

- **PR #269**: refactor: share sha256 and SPICE continuation helpers in design/bin/_common.py
- **Issue #237** (closed): Consolidate duplicated logical_lines and sha256 helpers across flow scripts

### 2026-11-03

- **Issue #263** (closed): main red: klt signoff drifted on T1 item 10 (.gitignore hash) after Loom resync

### 2026-11-02

- **PR #264**: docs(offset): propose costed B2/B3/B4 drift continuation plan
- **Issue #265** (closed): signoff red on main: T1 item 10 attest envelope drifted (.gitignore hash)

### 2026-10-31

- **PR #260**: feat(sim): split item-7 pex deltas into representation vs parasitic terms
- **Issue #250** (closed): pex: attribute item-7 deltas (run --device-only-leg) and add negative control

### 2026-10-30

- **PR #258**: feat(sim): record 15-corner batch noise grid (62.5-82.2 uVrms, 100 Hz-1 MHz)
- **PR #257**: refactor: remove unused identity-unchecked latest_ac_csv
- **Issue #256** (closed): Remove dead pvt_sweep.latest_ac_csv (superseded by select_ac_reference)
- **Issue #54** (closed): Add PSRR and input-referred noise benches to the PVT characterization

### 2026-10-27

- **PR #254**: refactor: share Magic DRC pipeline between layout scripts
- **Issue #251** (closed): Consolidate duplicated Magic DRC pipeline across layout scripts
- **PR #248**: feat(sim): cite klt pex run on the opamp_core layout for T1 item 7
- **Issue #247** (closed): T1 item 7 (post-layout verification): klt pex of opamp_core against the ratified rows

### 2026-10-25

- **PR #244**: feat: attest T1 items 9 and 10 with klt 0.8.0 envelopes
- **Issue #223** (closed): T1 items 9/10: produce attestation envelopes once a klt release has --attest (phase B of #221)

### 2026-10-23

- **PR #241**: feat(sim): store new evidence bytes in the artifact store, commit manifests
- **Issue #240** (closed): Adopt the common artifact store for sim evidence (manifests in git, bytes via klt artifact)

### 2026-10-20

- **PR #234**: chore: remove unreferenced constants and dead alias in sim scripts
- **Issue #233** (closed): Remove unreferenced constants and dead alias in sim scripts (two look like enforced tolerances)

### 2026-10-17

- **PR #231**: feat(manifests): cite opamp_core extract/DRC/LVS/ERC evidence for T1 items 2, 3, 4, 11
- **PR #229**: refactor: reuse attribution.logical_lines in sizing_feasibility
- **PR #228**: refactor(layout): probe-passives uses shared run_klt
- **PR #225**: feat(layout): assemble opamp_core from the four verified sub-blocks
- **PR #224**: spec: add T1 item 9/10 attestation inventories and DR-014 wait-for-release record
- **Issue #222** (closed): Cite the assembled core for T1 items 2, 3, 4 and 11 (DRC/LVS/ERC)
- **Issue #227** (closed): Consolidate probe-passives.py's duplicate run_klt/check_toolchain into layout/bin/_klt_common.py
- **Issue #226** (closed): Consolidate duplicated SPICE logical_lines helpers (6 copies, 2 identical)
- **Issue #221** (closed): Cite T1 items 9 and 10 with artifact-anchored inventories (klt signoff --attest)
- **Issue #220** (closed): Assemble the full opamp_core layout from the four verified sub-blocks (T1 item 2)

### 2026-10-14

- **Issue #35** (closed): README: embed the fleet burndown chart (one line)

### 2026-10-13

- **PR #216**: tests: unit tests for psrr_noise_sweep.py
- **Issue #68** (closed): tests: add simulator-free unit tests for psrr_noise_sweep.py
- **PR #93**: ratification: install ee-key and market-key reviewer trees; fix stale DR Status lines (#49)
- **Issue #49** (closed): Install ratification/ee-key and ratification/market-key reviewer trees (product#151)

### 2026-10-12

- **PR #212**: Enable committed sub-block composition and explicit internal LVS nets
- **Issue #210** (closed): Enable committed sub-block composition and explicit internal LVS nets
- **PR #209**: Lay out the canonical output stage XM6/XM7 as opamp_out sub-block
- **PR #207**: Lay out the canonical bias/tail mirror XMB1/XM5 as a verified sub-block (#204)
- **PR #206**: grid_check: reject missing/empty required dimensions (#205)
- **PR #202**: Sink bias-margin study: ic075 screen, 15-point expansion, mismatch probe (#197)
- **Issue #208** (closed): Lay out the canonical XM6/XM7 output stage as a verified sub-block
- **Issue #203** (closed): Auditor guard review: preserve installed Loom file ownership
- **Issue #27** (closed): layout: provide klt erc power-delivery evidence (T1 item 11) once layout exists
- **Issue #204** (closed): Lay out the canonical bias and tail mirror as a verified sub-block
- **Issue #205** (closed): Reject missing and empty required dimensions in the manufacturing-grid gate
- **Issue #197** (closed): Screen lower-overhead signal-dependent sink bias on the current DUT
- **Issue #46** (closed): T1 item 2, first increment: bring up the layout flow and lay out the first-stage matched groups (input pair and PMOS mirror), DRC clean and LVS matched

### 2026-10-11

- **PR #200**: Measure paired offset drift before prototyping foreground trim (partial: 1 of 4 conditions)

- **PR #198**: Reject malformed MOS geometry before manufacturing-grid arithmetic
- **PR #195**: Offset technique study: trim, chopping, auto-zero, consumer-side (#147)
- **PR #194**: sim+spec: independent-supply cartesian PVT baseline campaigns and section-2 coverage figures (#110)
- **PR #193**: Measure input-range contribution to the falling slew gap (tran_sr_icmr)
- **PR #192**: layout: PMOS mirror XM3/XM4 and seven-pin LVS signoff in opamp_stage1 (#121)
- **Issue #190** (closed): Reject malformed MOS geometry before manufacturing-grid arithmetic
- **Issue #189** (closed): Auditor: retain stash-scope:create-redirect guard
- **Issue #185** (closed): Measure input-range contribution to the falling slew gap
- **Issue #147** (closed): Offset closure: scoped technique study (trim / chopping / auto-zero) after sizing was found insufficient
- **Issue #121** (closed): Extend opamp_stage1 with the grid-legal PMOS mirror and seven-pin LVS signoff
- **Issue #110** (closed): sim: evaluate independent supply extremes across the PVT process grid
- **Issue #50** (closed): Sizing on the 0.005 um grid: M3/M4/M6 (W=4.634) and MB1/M5/M7 (W=7.819) cannot be drawn DRC-clean; decide grid-legal widths, then lay out the PMOS mirror into layout/opamp_stage1
- **PR #187**: Bind spec section 2 figures to DUT scope and identity (#186)
- **PR #184**: DR-013: grid-legal canonical MOS widths (4.635/7.820 um) with fleet PVT evidence (#120)
- **PR #183**: Fixed-input-common-mode output-swing diagnostic and 5x3 fleet attribution record
- **PR #182**: fix: refuse multi-unit local ngspice grids on the batch backend in pvt_sweep
- **PR #180**: fix: reject non-object JSON reports at the klt_sim boundary
- **PR #177**: Keep generic signoff evidence paths inside the checkout
- **PR #174**: spec figures: verify the supply attributed to binding extrema
- **Issue #186** (closed): Verify current-design DUT provenance for spec figure citations
- **Issue #181** (closed): Diagnose output-stage swing limits at fixed input common-mode
- **Issue #179** (closed): Reject non-object JSON reports at the shared klt simulation boundary
- **Issue #176** (closed): Keep generic signoff evidence paths inside the checkout
- **Issue #175** (closed): Auditor: preserve unresolved recursive deletion protection
- **Issue #172** (closed): spec figures: verify the supply attributed to binding extrema
- **Issue #171** (closed): Auditor guard review: keep stash-scope:create-redirect flagged
- **Issue #170** (closed): Auditor guard review: keep worktree-write-confinement-unresolved-var flagged
- **Issue #169** (closed): Auditor guard review: keep gh-api-rawfield-body-literal-at flagged
- **Issue #163** (closed): pvt_sweep: refuse a multi-unit local ngspice grid when the backend is batch
- **Issue #120** (closed): Select and verify grid-legal canonical widths for the DR-007 mirror and output groups
- **Issue #47** (closed): T1 item 5: evaluate the two structural fixes DR-007 names for the falling slew-rate gap and draft the superseding topology record


### 2026-10-11

- **PR #168**: Layout: routed Rz/Cc compensation block with passive LVS verification (#167)
- **Issue #167** (closed): Layout: build a routed Rz/Cc compensation block with passive LVS verification

### 2026-10-10

- **PR #166**: Signal-dependent output sink candidate and proposed topology comparison (DR-012)
- **PR #165**: Test tail_clamp_sizing.py against committed netlists (#164)
- **PR #162**: Key variant comparison by (corner, temp_c, vdd_v)
- **PR #160**: Detect uncommitted evidence edits in the local append-only gate
- **Issue #79** (closed): Evaluate a signal-dependent output sink and draft the topology comparison decision
- **Issue #164** (closed): tests: add simulator-free unit tests for tail_clamp_sizing.py
- **Issue #150** (closed): Auditor: retain shared-worktree stash restriction
- **Issue #161** (closed): Preserve supply voltage in variant comparison identity
- **Issue #158** (closed): Detect uncommitted evidence edits in the local append-only gate
- **PR #157**: Reject malformed manifest entries in the generic evidence freshness gate
- **PR #156**: Tail-clamp candidate for the fall-slew gap: measured negative result (#78)
- **PR #154**: Extract generic-evidence artifact hash gate into a tested local checker (#152)
- **PR #153**: Bind PSRR/noise campaigns and validation runs to an immutable DUT snapshot
- **PR #148**: pvt_sweep: bind historical AC cross-checks to matching DUT and supply points
- **PR #146**: offset: matched-group sizing feasibility for the proposed offset allocation (#144)
- **PR #145**: layout: unit-test probe-passives.py (#142)
- **PR #141**: docs: reconcile signoff guide with partial layout, measured offset and klt 0.7.0 pin
- **PR #140**: Restore grid_check in local CI runner; detect workflow omissions
- **PR #139**: docs: restore CMRR in issue #53 README section and add 1 MHz erratum
- **PR #136**: Add fleet execution for AC, slew and swing characterization with selectable netlists
- **PR #135**: Grid-legal compensation resistor (XRz L=9.765) and passive realizability probes
- **PR #134**: Identify sizing_check as historical DR-002 replay
- **Issue #155** (closed): Reject malformed manifest entries in the standalone artifact freshness gate
- **Issue #152** (closed): Expose generic-evidence artifact freshness as a tested local checker
- **Issue #151** (closed): Bind PSRR/noise campaigns and validation runs to an immutable DUT snapshot
- **Issue #149** (closed): Auditor: guard worktree-write-confinement rejects scoped sweep checkpoint writes
- **Issue #144** (closed): Quantify matched-group sizing feasibility for the proposed offset allocation
- **Issue #143** (closed): Bind historical AC cross-checks to matching DUT and supply points
- **Issue #142** (closed): layout: unit-test probe-passives.py and de-duplicate its klt/Magic helpers
- **Issue #138** (closed): Reconcile current signoff prerequisites with partial layout and measured offset
- **Issue #137** (closed): Restore passive-grid checking and detect workflow omissions in the local CI runner
- **Issue #132** (closed): Identify sizing_check widths and corners as historical DR-002 replay
- **Issue #131** (closed): Verify grid-legal compensation resistor geometry and passive realizability
- **Issue #130** (closed): Auditor guard review: worktree-write-confinement
- **Issue #78** (closed): Characterize a tail clamp or degeneration candidate for the falling slew gap
- **Issue #77** (closed): Add fleet execution for AC, slew and swing characterization with selectable netlists
- **Issue #71** (closed): sim/opamp-characterization: README issue-#53 section has 'CMRR' replaced by a record id; record 566b9a5 overstates 1 MHz CMRR flatness

- **PR #129**: test: assert klt version pin is identical across signoff workflow and manifest
- **PR #128**: tests: unit tests for layout/bin/_klt_common.run_klt
- **PR #125**: fix(integrator_check): resolve artifact paths, reject partial-layout aliases
- **PR #124**: fix(netlist_check): parameter-specific derived-parameter tolerances
- **PR #123**: ci: run layout flow unit tests in the unit-tests job
- **Issue #127** (closed): tests: assert the klt version pin is identical across the signoff workflow and manifest
- **Issue #126** (closed): tests: add simulator-free unit tests for layout/bin/_klt_common.run_klt
- **Issue #116** (closed): Reject aliased partial-layout paths and directories in integrator GDS validation
- **Issue #59** (closed): netlist_check: tighten derived-parameter tolerance (0.5% lets small hand edits of ad/pd/nrd pass)
- **Issue #57** (closed): Run layout flow unit tests in CI
- **Issue #112** (closed): Auditor guard review: worktree-write-confinement should remain enforced

### 2026-10-09

- **PR #118**: sim: attribute the offset Monte Carlo sigma to device groups (#107)
- **PR #115**: sim: bind offset Monte Carlo chunks and resume to one DUT snapshot
- **PR #114**: sim: opt-in Cartesian supply mode for PVT runner (#110)
- **PR #111**: Wire package.json test/check:ci to real simulator-free checks
- **PR #109**: spec: propose offset target via DR-009; reconcile offset row with N=300 MC campaign
- **PR #106**: Preserve exact DUT netlist per PVT campaign and check current-design identity
- **Issue #107** (closed): sim: attribute the 8.6 mV offset Monte Carlo sigma to device groups
- **Issue #113** (closed): sim: bind offset Monte Carlo chunks and resume to one DUT snapshot
- **Issue #101** (closed): Wire package.json test/check:ci to the real simulator-free checks
- **Issue #108** (closed): spec: reconcile the offset row with the N=300 Monte Carlo campaign via a decision record
- **Issue #104** (closed): Preserve the exact DUT netlist for PVT campaigns and check current-design identity
- **PR #103**: tests: add unit tests for gm/ID sweep.py derive_points and interp
- **PR #100**: Make PSRR and noise cross-check disagreements fail validation
- **PR #99**: Validate PVT matrix completeness before accepting spec figures
- **PR #95**: sim: PVT grid record for closed-loop step bench (#86)
- **PR #94**: sim: closed-loop small-step overshoot/settling bench to cross-check AC phase margin (#86)
- **PR #92**: sim: offset Monte Carlo campaign N=300 TT/SS/FF (+SF/FS) on the batch fleet (#85)
- **PR #91**: docs(sim): log third batch noise-grid attempt for #54
- **Issue #102** (closed): tests: add unit tests for gm/ID sweep.py derive_points and interp
- **Issue #96** (closed): Auditor guard review: worktree-write-confinement-unresolved-var should remain blocked
- **Issue #98** (closed): Make PSRR and noise cross-check disagreements fail validation
- **Issue #97** (closed): Validate PVT matrix completeness before accepting spec figures
- **Issue #86** (closed): sim: add a closed-loop small-step (overshoot/settling) bench to cross-check AC phase margin across PVT
- **Issue #85** (closed): sim: run the offset Monte Carlo campaign (TT/SS/FF, batch fleet) on the #52 capability probe
- **PR #87**: test: assert sky130 PDK pin is identical across CI, sim and layout configs
- **PR #89**: spec: check target-spec §2 measured figures against committed PVT records
- **PR #88**: docs(spec): add prior-art survey of public sky130 op-amps
- **PR #84**: Reserve unique simulation record namespaces before writing evidence
- **PR #83**: docs(sim): log second noise-grid re-attempt, fleet runner still klt 0.5.0 (Part of #54)
- **PR #80**: Keep integrator maturity and port metadata consistent with cited sources
- **PR #70**: spec: reconcile ICMR/CMRR rows with record 20261009-103006-566b9a5; DR-008 proposes CMRR target (#66)
- **PR #72**: ci: enforce append-only evidence under sim/ (#67)
- **PR #69**: refactor(sim): consolidate klt sim wrappers and KLT_CMD into spice_harness (#65)
- **PR #64**: sim: seeded-mismatch capability probe for offset Monte Carlo (#52)
- **PR #63**: feat(sim): ICMR and CMRR benches over the PVT grid (issue #53)
- **PR #62**: docs(sim): log noise-grid re-attempt, fleet runner still klt 0.5.0 (Part of #54)
- **PR #61**: test: simulator-free unit tests + CI job (#56)
- **PR #60**: feat(sim): PSRR+/PSRR- and input-referred noise benches as klt sim requests (#54)
- **PR #58**: feat: guard opamp_core.spice against schematic drift in CI; cite for T1 item 1
- **PR #51**: feat: layout flow bring-up and stage-1 input pair (DRC/LVS clean)
- **Issue #81** (closed): tests: assert the sky130 PDK pin is identical across CI, sim and layout configs
- **Issue #82** (closed): spec: mechanically check target-spec §2 measured figures against the committed PVT records
- **Issue #76** (closed): docs: add a prior-art survey — cite and honestly compare against public sky130 op-amp art (CLAUDE.md requirement, currently undelivered)
- **Issue #75** (closed): Reserve unique simulation record namespaces before writing evidence
- **Issue #74** (closed): Keep integrator maturity and port metadata consistent with cited sources
- **Issue #73** (closed): Auditor guard review: gh-api-rawfield-body-literal-at should remain blocked
- **Issue #66** (closed): spec: reconcile the input common-mode range and CMRR rows with the issue #53 PVT records
- **Issue #67** (closed): CI: enforce append-only evidence under sim/ records, corners and netlist snapshots
- **Issue #65** (closed): Consolidate four duplicated klt sim wrappers and KLT_CMD into spice_harness.py
- **Issue #52** (closed): Offset: verify pinned-PDK mismatch and seeded klt sim capability before the Monte Carlo campaign
- **Issue #53** (closed): Add input common-mode range (ICMR) and CMRR benches to the PVT characterization
- **Issue #56** (closed): Add simulator-free CI tests for the Python harness and DR-002 sizing check (T1 items 9/10)
- **Issue #55** (closed): Guard design/netlist/opamp_core.spice against schematic drift in CI and cite it for T1 item 1

### 2026-10-01

- **PR #44**: manifest: cite the PVT characterization report as T1 item 8 evidence
- **PR #42**: design: resize opamp_core per DR-007 to close the GBW/rise-SR gaps
- **Issue #43** (closed): manifest: cite the PVT characterization report as T1 item 8 evidence (the one T1 item achievable without layout)
- **Issue #22** (closed): design: resize opamp_core devices to close the GBW / fall-slew-rate / output-swing gaps issue #20 reconciled

### 2026-09-30

- **PR #21**: spec: reconcile target-spec.md's six [P] rows against measured PVT data
- **Issue #20** (closed): spec: reconcile target-spec.md's six [P] performance rows against sim/opamp-characterization measured PVT data

### 2026-09-29

- **PR #41**: refactor: extract shared --check-env tool/PDK report into sim/lib/spice_harness.py
- **Issue #40** (closed): Extract check_env's duplicated tool/PDK-availability report into sim/lib/spice_harness.py

### 2026-09-28

- **PR #39**: docs: add DR-006 recording the keep-ngspice-default solver-tolerance convention
- **Issue #38** (closed): ngspice solver-tolerance convention: keep the default (coordination from sg13g2-opamp DR-0005)
