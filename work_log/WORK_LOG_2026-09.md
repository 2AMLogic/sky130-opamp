# Work Log Archive — 2026-09

Sections moved byte-for-byte from [WORK_LOG.md](../WORK_LOG.md) by `loom-daemon work-docs archive`.

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
