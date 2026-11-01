# Work Log

Chronological record of merged pull requests and closed issues, maintained by the Loom Guide role. Newest entries appear first.

### 2026-10-31

- **PR #260**: feat(sim): split item-7 pex deltas into representation vs parasitic terms
- **Issue #250** (closed): pex: attribute item-7 deltas (run --device-only-leg) and add negative control

### 2026-10-30

- **PR #287**: fix(layout): regenerate pilot evidence under klt 0.8.0 on the curated gf180mcu deck
- **Issue #282** (closed): Regenerate layout/pilot evidence under klt 0.8.0
- **PR #258**: feat(sim): record 15-corner batch noise grid (62.5-82.2 uVrms, 100 Hz-1 MHz)
- **PR #257**: refactor: remove unused identity-unchecked latest_ac_csv
- **Issue #256** (closed): Remove dead pvt_sweep.latest_ac_csv (superseded by select_ac_reference)
- **Issue #54** (closed): Add PSRR and input-referred noise benches to the PVT characterization

### 2026-10-27

- **PR #281**: chore(klt): bump pinned klayout-tools to 0.8.0 and regenerate signoff record
- **Issue #280** (closed): Bump klayout-tools pin 0.7.0 → 0.8.0
- **PR #254**: refactor: share Magic DRC pipeline between layout scripts
- **Issue #251** (closed): Consolidate duplicated Magic DRC pipeline across layout scripts
- **PR #248**: feat(sim): cite klt pex run on the opamp_core layout for T1 item 7
- **Issue #247** (closed): T1 item 7 (post-layout verification): klt pex of opamp_core against the ratified rows

### 2026-10-25

- **PR #244**: feat: attest T1 items 9 and 10 with klt 0.8.0 envelopes
- **Issue #223** (closed): T1 items 9/10: produce attestation envelopes once a klt release has --attest (phase B of #221)

### 2026-10-23

- **PR #276**: ci: raise selftest job timeout to 60 minutes
- **PR #272**: feat(sim): store new run evidence in the artifact store, commit manifests
- **Issue #275** (closed): ci: selftest 'Prove the selftest can fail' step cancelled at ~30m on docs-only PR #273
- **Issue #271** (closed): Adopt the common artifact store for sim evidence (manifests in git, bytes via klt artifact)
- **PR #241**: feat(sim): store new evidence bytes in the artifact store, commit manifests
- **Issue #240** (closed): Adopt the common artifact store for sim evidence (manifests in git, bytes via klt artifact)

### 2026-10-20

- **PR #269**: refactor(sim): share the MC mismatch-switch guard in harness
- **PR #267**: docs(spec): add noise/offset consumer-derived requirement basis (DR-0007 draft)
- **PR #234**: chore: remove unreferenced constants and dead alias in sim scripts
- **Issue #233** (closed): Remove unreferenced constants and dead alias in sim scripts (two look like enforced tolerances)

### 2026-10-19

- **PR #264**: sim: staged-model f6eeac7 re-runs of gain-gbw-pm-mc and cmrr; stage models in run_klt_retrying

### 2026-10-18

- **PR #261**: refactor: share retained-CSV loading across report crosschecks
- **PR #259**: sim: cmrr-mc Monte Carlo re-run under f6eeac7 with client models staged
- **PR #256**: docs(sim): record c6d73a3 vs f6eeac7 model-file comparison
- **PR #252**: sim: nominal offset Monte Carlo re-run under open_pdks f6eeac7
- **PR #250**: sim: re-run five cited experiments under open_pdks f6eeac7
- **Issue #260** (closed): Hoist duplicated retained-CSV preamble from five report crosschecks into report_common

### 2026-10-17

- **PR #245**: refactor: hoist per-bench fingerprint wrappers into harness.fingerprint_api
- **PR #243**: build: re-pin open_pdks to f6eeac7 via ciel, search ~/.ciel before ~/.volare
- **PR #236**: refactor(sim): hoist corner indexing, point persistence and re-derivation into harness
- **PR #230**: refactor(sim): hoist duplicated transient and MC runner helpers into harness
- **PR #221**: refactor: split characterization_report.py into sibling modules
- **PR #220**: refactor(sim): share Ibias/CL testbench override helpers via harness
- **Issue #238** (closed): Hoist duplicated MC snapshot writer and request sanitiser into sim/harness.py
- **Issue #237** (closed): Collapse 14 copy-pasted fingerprint wrappers in sim/*/measurement_config.py into a harness factory
- **Issue #235** (closed): Hoist transient-runner corner indexing, point persistence and re-derivation loops into sim/harness
- **Issue #232** (closed): Hoist duplicated MC submit() and parse_scalars() into sim/harness
- **Issue #229** (closed): Consolidate remaining byte-identical runner helpers (step-response/overdrive-recovery, MC runners) into sim/harness.py
- **Issue #225** (closed): Consolidate triplicated describe_backend/_fmt and inline remote lookups into sim/harness.py
- **Issue #219** (closed): Split sim/report/characterization_report.py (4,915 lines) into sibling modules
- **Issue #218** (closed): Consolidate duplicated Ibias/CL testbench override helpers into sim/harness.py
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

### 2026-10-16

- **PR #211**: sim(cmrr-mc): record seed re-probe on fleet klt 0.7.0 (still not partition-invariant)

### 2026-10-15

- **PR #79**: feat(#77): GF180 layout device pilot (isolated cells, regen recipe, DRC/LVS evidence)
- **Issue #105** (closed): Consolidate duplicated guard_dut and guard_testbench core into sim/harness.py

### 2026-10-14

- **PR #203**: Record enable-acquisition evidence at all 45 PVT points (#191)
- **Issue #191** (closed): sim: characterize supply and external-bias enable acquisition across PVT
- **Issue #35** (closed): README: embed the fleet burndown chart (one line)

### 2026-10-13

- **PR #199**: sim: configuration freshness for CMRR-MC and gain/GBW/PM-MC (#197)
- **Issue #198** (closed): report: integrate ungraded follower step-response evidence
- **PR #216**: tests: unit tests for psrr_noise_sweep.py
- **Issue #68** (closed): tests: add simulator-free unit tests for psrr_noise_sweep.py
- **PR #93**: ratification: install ee-key and market-key reviewer trees; fix stale DR Status lines (#49)
- **Issue #49** (closed): Install ratification/ee-key and ratification/market-key reviewer trees (product#151)

### 2026-10-12

- **PR #196**: sim(psrr-mc): full T/VDD grid mismatch characterization tooling (#190)
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

- **PR #188**: sim: input-overdrive and output-saturation recovery across the PVT grid
- **PR #186**: sim: fingerprint the input-common-mode measurement configuration
- **PR #185**: report: include the committed PSRR mismatch Monte Carlo record in the characterization report
- **PR #181**: feat(#99): commit the full PSRR+/PSRR- mismatch Monte Carlo record
- **PR #178**: report: integrate the gain/GBW/PM mismatch Monte Carlo record as ungraded, hash-pinned evidence
- **PR #176**: sim: re-measure step response and ibias/CL sensitivity on the retuned DUT
- **PR #175**: report: integrate ungraded full-passive PSRR evidence (bound-free supplementary adapter)
- **PR #171**: sim/report: check live verdict prose against the characterization report
- **PR #170**: fix: reject gain verdict-token, binding-corner and stretch-count contradictions in extract_gain
- **PR #169**: fix(sim): pin offset driver to full PVT grid in one-command campaign
- **PR #164**: sim: standalone full RZ/CC x PVT PSRR study at 1 kHz and 10 kHz
- **PR #163**: docs: correct pre-retune verdict prose in spec/target-spec.md and manifests/README.md
- **PR #158**: docs: guard confinement reproduction and evidence package (#146)
- **PR #152**: sim: extend independent RZ/CC verification to the full 405-cell PVT envelope
- **PR #151**: test(sim/psrr-mc): offset-sigma gate test, IMBALANCE_RAILS pin, gate mutation (#99, partial)
- **PR #149**: sim(cmrr-mc): seed partition-invariance probe for #140 (seeds NOT invariant; chunked grid parked)
- **PR #143**: docs(#141): reconcile sim/README coverage-and-gaps with selected records
- **Issue #184** (closed): report: derive offset temperature drift and systematic-vs-statistical split from the committed offset Monte Carlo
- **Issue #183** (closed): sim: input-overdrive and output-saturation recovery across the PVT grid
- **Issue #182** (closed): report: include the committed PSRR mismatch Monte Carlo record in the characterization report
- **Issue #180** (closed): sim: add measurement-configuration freshness for input common-mode evidence
- **Issue #173** (closed): report: integrate ungraded full-passive PSRR evidence
- **Issue #168** (closed): report: validate gain verdict tokens and binding corners against per-point evidence
- **Issue #160** (closed): signoff: determine which klt envelopes honestly back T1 items 1, 9 and 10, cite them or file the tool gap
- **Issue #159** (closed): ci: fail PRs that modify or delete committed sim/ evidence (enforce append-only beyond write time)
- **Issue #156** (closed): sim/report: extend the spec citation drift check to catch stale verdict prose
- **Issue #154** (closed): docs: correct pre-retune verdict prose in spec/target-spec.md and manifests/README.md (PM no longer fails)
- **Issue #153** (closed): Consolidate duplicated MC stats helpers (percentile/_skew/extract) in cmrr-mc and psrr-mc
- **Issue #146** (closed): Auditor: capture reproducible scratch-path and checkpoint guard cases for upstream review
- **Issue #141** (closed): docs: reconcile sim/README.md coverage-and-gaps section with the 45-point offset record and post-retune results
- **Issue #139** (closed): Re-measure step-response and ibias/CL sensitivity on the retuned compensation DUT
- **Issue #99** (closed): sim: PSRR+ / PSRR- mismatch Monte Carlo
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
- **PR #168**: Layout: routed Rz/Cc compensation block with passive LVS verification (#167)
- **Issue #167** (closed): Layout: build a routed Rz/Cc compensation block with passive LVS verification

### 2026-10-10

- **PR #138**: design(#42): retune Miller compensation so phase margin meets 60 deg at 45/45 PVT points
- **PR #137**: feat(#114): ibias and CL sensitivity record
- **PR #132**: ci(#131): extend regression-check mutations to ibias-cl-sensitivity and shared sim modules
- **PR #130**: report: derive and hash supplementary passive-corner evidence (#121)
- **PR #127**: feat(#124): report the committed CMRR mismatch Monte Carlo record
- **PR #126**: sim: gain/GBW/PM at the LDO 1.20 V input (fixed-VCM option + 45-point record)
- **PR #122**: feat(#114): ibias and CL sensitivity experiment (record pending)
- **PR #119**: feat(#97): passive-corner side-study record for slew/swing/power
- **PR #116**: sim: closed-loop follower step response (overshoot, settling) across the PVT grid (#113)
- **PR #110**: docs(#95): cite passive-corner study in README and aggregate report
- **PR #108**: ci(#107): extend ci_regression_check.sh teeth coverage to every sim experiment
- **PR #104**: refactor(#94): consolidate materialise() work-dir staging into harness.stage_workdir
- **PR #86**: feat(#84): validate integrator view against interface and signoff tier
- **PR #81**: Reject characterization evidence that no longer matches the current DUT
- **PR #78**: ci(#76): check committed netlist matches xschem export of the schematic
- **Issue #133** (closed): docs: reconcile README, sim/README and target-spec status with the committed slew/swing/power passive-corner study
- **Issue #129** (closed): sim: mismatch Monte Carlo of gain, GBW and phase margin (statistical evidence for the PM/GBW rows)
- **Issue #125** (closed): sim: characterize gain GBW and PM at the LDO 1.20 V input operating point
- **Issue #124** (closed): report: include separately scoped mismatch CMRR evidence
- **Issue #114** (closed): sim: ibias and CL sensitivity of GBW, PM, slew and power (evidence for the PM shortfall)
- **Issue #106** (closed): sim: extend offset Monte Carlo to the 45-point T/VDD grid (N=300 per point)
- **Issue #95** (closed): README and aggregate report: cite the passive-corner study instead of claiming passives were never swept
- **Issue #94** (closed): Consolidate duplicated materialise() work-dir staging into sim/harness.py
- **Issue #90** (closed): Include measured input common-mode evidence in the aggregate report without ratifying its bound
- **Issue #89** (closed): Extend measurement freshness checks to the remaining selected characterization experiments
- **Issue #88** (closed): Auditor: review stash guard denial during isolated driver validation
- **Issue #84** (closed): Validate the integrator view against the committed interface and signoff tier
- **Issue #83** (closed): Auditor Capability Request: Python unavailable for local report validation
- **Issue #61** (closed): spec: ratify CMRR and PSRR bounds with a mismatch-aware CMRR statistic (DR-3 residuals e3, e4)
- **Issue #42** (closed): Design: phase margin misses the ratified 60 deg target at 30/45 PVT points (worst 57.34 deg at FS / 125 C / 2.97 V)
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

- **PR #74**: sim(gain-gbw-pm): RZ x CC passive-corner axis and record (#70)
- **PR #73**: signoff: bump pinned klt grader to 0.7.0 and regenerate the signoff record
- **PR #67**: sim+spec: follower-biased input common-mode range (45 PVT x VCM scan) and proposed ICMR row via DR-0005 (#60)
- **PR #65**: refactor(sim): move duplicated klt sim wrapper helpers into harness.py
- **PR #57**: feat(sim): slew-rate, output-swing and quiescent-power testbenches (#44)
- **PR #56**: ci: run sim/selftest.sh in CI with pinned tools/PDK and strict prerequisites
- **PR #55**: docs: reconcile current-status prose with committed characterization evidence
- **PR #54**: chore(ratification): install ee-key and market-key reviewer trees (#41)
- **PR #53**: feat(sim): aggregate T1 characterization report from committed records
- **PR #49**: feat(sim): CMRR and PSRR testbenches and 45-point records (#39)
- **PR #48**: feat(sim): input-referred noise bench and 45-point evidence (#46)
- **PR #47**: feat(sim): input-offset mismatch Monte Carlo of the committed schematic (#45)
- **PR #43**: feat(sim): gain/GBW/PM of the committed schematic over the 45-point PVT grid (#38)
- **Issue #70** (closed): T1 item 5: quantify RZ/CC passive-corner sensitivity of phase margin, GBW and slew (DR-3 section d obligation)
- **Issue #69** (closed): docs: reconcile README and target-spec status for slew, swing and power with committed PASS records
- **Issue #60** (closed): spec: add an input common-mode range row (testbench + decision record) — consumers currently grade it unknown
- **Issue #58** (closed): Consolidate duplicated klt sim wrapper helpers into sim/harness.py
- **Issue #51** (closed): Reconcile current-status documentation with committed characterization evidence
- **Issue #45** (closed): T1 item 5: add mismatch Monte Carlo input-offset experiment to discharge residual (e2)
- **Issue #44** (closed): T1 item 5: add slew-rate, output-swing and quiescent-power testbenches for the three ratified-but-unmeasured rows
- **Issue #41** (closed): Install ratification/ee-key and ratification/market-key reviewer trees (product#151)
- **Issue #39** (closed): T1 items 5 and 9: add CMRR and PSRR testbenches on the committed schematic so the two open spec rows can be given bounds
- **PR #118**: sim: attribute the offset Monte Carlo sigma to device groups (#107)
- **PR #115**: sim: bind offset Monte Carlo chunks and resume to one DUT snapshot
- **PR #114**: sim: opt-in Cartesian supply mode for PVT runner (#110)
- **PR #111**: Wire package.json test/check:ci to real simulator-free checks
- **PR #109**: spec: propose offset target via DR-009; reconcile offset row with N=300 MC campaign
- **PR #106**: Preserve exact DUT netlist per PVT campaign and check current-design identity
- **Issue #107** (closed): sim: attribute the 8.6 mV offset Monte Carlo sigma to device groups
- **PR #115**: sim: bind offset Monte Carlo chunks and resume to one DUT snapshot
- **PR #114**: sim: opt-in Cartesian supply mode for PVT runner (#110)
- **PR #111**: Wire package.json test/check:ci to real simulator-free checks
- **PR #109**: spec: propose offset target via DR-009; reconcile offset row with N=300 MC campaign
- **PR #106**: Preserve exact DUT netlist per PVT campaign and check current-design identity
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

### 2026-10-03

- **PR #36**: refactor: consolidate sim-harness helpers into sim/harness.py

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

### 2026-09-23

- **PR #37**: docs: record DR-005 declining the 3.3 V I/O-device flavor
- **Issue #36** (closed): spec: both same-PDK consumers need a 3.3 V-rail / 5 V-gate amplifier position this block's 1.8 V-core scope does not serve (2am rule 9 step 4)

### 2026-09-22

- **PR #34**: docs: name consumers in spec, publish integrator view (2am rule 9)
- **PR #33**: docs: correct fall-slew ratio wording in characterization evidence
- **Issue #31** (closed): 2am: reuse rule 9 — name this block's consumers in the spec, carry their requirement rows, publish the integrator view as data
- **Issue #30** (closed): docs: fix fall-slew-ratio wording in sim/opamp-characterization README (1.73/17.26 is 10%, not under 9%)

### 2026-09-21

- **PR #29**: docs: ratify target-spec partially via DR-003 (13 rows, 4 open)
- **PR #28**: feat: make the klt signoff block manifest the T1 verdict of record
- **Issue #26** (closed): spec: ratify target-spec.md — it is DRAFT, which blocks T1 item 5 (and items 6/7/8 that grade against its rows)
- **Issue #25** (closed): Commit a klt signoff block manifest so this block's T1 state is graded, not hand-read

### 2026-09-16

- **PR #24**: refactor: extract shared PDK/ngspice-harness helpers into sim/lib/spice_harness.py
- **PR #19**: test: add op-amp-level PVT testbenches for DR-002's sizing estimates
- **Issue #23** (closed): Extract shared PDK/ngspice-harness helpers duplicated across sweep.py and pvt_sweep.py
- **Issue #17** (closed): sim: build PVT-corner testbenches to verify DR-002's schematic-level sizing estimates

### 2026-09-15

- **PR #18**: spec: add input-common-mode-range row, reconcile §2 with DR-002 sizing
- **PR #15**: design: size devices from the gm/ID sweep and capture the op-amp schematic (DR-002)
- **PR #12**: spec: ratify target-spec.md performance rows, promote DR-001
- **Issue #16** (closed): spec: add an input-common-mode-range row and reconcile §2 rows with DR-002's committed sizing
- **Issue #13** (closed): design: schematic capture — size devices from gm/ID sweep and DR-001, draft xschem schematic
- **Issue #14** (closed): design: schematic entry for the two-stage Miller-compensated op-amp (DR-001 topology, xschem)
- **Issue #10** (closed): spec: ratify target-spec.md performance rows — size from gm/ID data, promote DR-001
- **Issue #11** (closed): Ratify spec/target-spec.md: fill [TBD] performance rows and promote DR-001

### 2026-09-09

- **PR #9**: spec: decide two-stage topology and CL target (DR-001)
- **PR #7**: feat(sim): gm/ID characterization sweep for sky130 1.8V-core MOS devices
- **Issue #8** (closed): spec: DR-001 — two-stage topology (input-pair polarity, output stage, cascode-or-not) and CL target, informed by the gm/ID study (#6)
- **Issue #6** (closed): sim: gm/ID characterization sweep of sky130 1.8 V-core MOS + corner-grid confirmation — the first engineering task (porting-plan §4)

