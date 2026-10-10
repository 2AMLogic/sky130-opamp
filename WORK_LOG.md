# Work Log

Chronological record of merged pull requests and closed issues, maintained by the Loom Guide role. Newest entries appear first.

### 2026-10-10

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
