# Target specification — sky130-opamp

- **Status**: **RATIFIED (partial)** — per
  [`DR-003-target-spec-ratification.md`](decision-records/DR-003-target-spec-ratification.md)
  (2026-09-21 ratification pass, issue #26): 13 of this table's 17 rows
  are **RATIFIED** with per-row dispositions recorded in that record (all
  five §1 operating-condition rows, plus §2's open-loop DC gain, GBW,
  phase margin, slew rate, input-referred noise, input common-mode range,
  output swing, and quiescent power); §2's input-referred offset, CMRR,
  PSRR, and area rows stay **OPEN**, explicitly, not silently. Per the
  ratification-via-PR standing policy
  ([2AMLogic/2am#357](https://github.com/2AMLogic/2am/issues/357)), the
  ratification act is the approval of the PR that carries DR-003, not
  this file's edit alone. **No row's numeric value changed in
  ratification**: six ratified §2 rows carry measured evidence, two are
  ratified as targets with explicitly no "met" claim, and the measured
  non-compliance (GBW, fall slew rate, output swing) keeps its targets
  un-lowered per `CLAUDE.md`'s no-relaxation rule — the compliance path
  is the resize pass (#22), never a spec edit. This table was DRAFT from
  its 2026-09-06 bootstrap (issue #2) until this pass. The two earlier
  decision records keep their own status lines unchanged:
  [`DR-001-topology-and-cl.md`](decision-records/DR-001-topology-and-cl.md)
  (`submitted for ratification` — it covers the two-stage topology's
  input-pair polarity, first-stage load, output-stage class, compensation
  scheme, and the `CL` row below) and
  [`DR-002-device-sizing.md`](decision-records/DR-002-device-sizing.md)
  (`proposed` — device sizing). See §5 below for the current per-row
  ratification map.
- **Date**: 2026-09-06 (bootstrap); **2026-09-15 sizing pass** — every §2
  performance row is now either a proposed `[P]` sizing estimate cited to
  `sim/gm-id-characterization/records/20260909-062847-35a9d46-{summary,full-sweep}.csv`
  (per `CLAUDE.md`'s "gm/ID first" rule) and to
  [`DR-001`](decision-records/DR-001-topology-and-cl.md)'s topology/
  structural ratios, or an explicit `[TBD]` with a stated reason it cannot
  yet be filled from that data. This pass performs **no schematic
  capture, no layout, no simulation beyond the already-committed gm/ID
  device sweep** — every number below is a sizing estimate under DR-001's
  chosen topology, not a measured or simulated result. See
  [§2a](#2a-sizing-basis-for-the-2026-09-15-pass-illustrative-non-binding)
  for the shared assumptions and per-row derivation.
- **2026-09-16 reconciliation pass (issue #20)**: the six `[P]`-tagged §2
  performance rows (open-loop DC gain, GBW, phase margin, slew rate, output
  swing, quiescent power) are now reconciled against measured, PVT-cornered
  circuit-level evidence —
  [`sim/opamp-characterization/records/20260916-032327-edc9f22`](../sim/opamp-characterization/records/20260916-032327-edc9f22.md)
  (issue #17 / PR #19) — in place of, or alongside, the `DR-002` hand
  estimates those rows previously cited alone. Two rows (phase margin,
  quiescent power) **confirm** their `DR-002` estimate; four (open-loop
  gain's binding corner, GBW, slew rate, output swing magnitude)
  **contradict** some part of it, most severely GBW (measured worst-case
  ≈53% of target) and fall slew rate (measured worst-case under 9% of
  target). Per `CLAUDE.md`, this pass does **not** lower either target to
  match the measurement, does **not** touch `DR-002`, the schematic, or
  device sizing, and does **not** itself ratify anything (the `Status`
  field above was still `DRAFT` when this pass was written; ratification
  is `DR-003`'s separate pass, issue #26 — see §5) — see each row below
  and the note following §2's table.
- **2026-10-01 resize reconciliation pass (issue #22)**: the same six rows
  are re-reconciled against a second full PVT grid —
  [`sim/opamp-characterization/records/20261001-074923-c317ff9`](../sim/opamp-characterization/records/20261001-074923-c317ff9.md)
  — measured on the **DR-007 device resize**
  ([`DR-007`](decision-records/DR-007-device-resize-gbw-slew-swing.md),
  which supersedes `DR-002`'s sizing per its own superseding-record
  convention). GBW and rise slew rate move to **met** at every point; fall
  slew rate and output swing **partially close** (every grid point
  improves, targets unmet at the worst corners); phase margin and
  quiescent power hold; open-loop gain stays met everywhere but its worst
  case drops 69.72 → 61.64 dB (margin 9.7 → 1.6 dB — the recorded cost of
  DR-007's PMOS channel-length trade). Per `CLAUDE.md`, no target is
  changed by this pass either; the compliance deltas below cite the new
  record per cell.
- **2026-10-09 ICMR / CMRR reconciliation pass (issue #66)**: the input
  common-mode range and CMRR rows are reconciled against
  [`sim/opamp-characterization/records/20261009-103006-566b9a5`](../sim/opamp-characterization/records/20261009-103006-566b9a5.md)
  (issue #53), the first ICMR and common-mode AC benches. ICMR moves from
  target-only to **measured, met at every corner** (target unchanged).
  CMRR moves from `[TBD]` to **measured**, with a numeric target
  **proposed** as `[P]` by
  [`DR-008`](decision-records/DR-008-cmrr-target.md) (status *proposed*);
  it stays OPEN under DR-003 until DR-008's named ratification act (a
  separate operator-approved PR; merging this PR is not it). No ratified target is
  changed. PSRR and input-referred noise are left for issue #54's
  follow-on.
- **2026-10-09 offset reconciliation pass (issue #108)**: the
  input-referred offset row is reconciled against the N = 300 mismatch
  Monte Carlo campaign (issue #85, record
  [`campaign-20261009-offset-mc300.md`](../sim/offset-capability/records/campaign-20261009-offset-mc300.md)).
  Offset moves from `[TBD]` to **measured, not met**: the numeric target
  σ ≤ 0.275 mV is the consumer-derived `sky130-bandgap` allocation,
  **proposed** as `[P]` by
  [`DR-009`](decision-records/DR-009-offset-target.md) (status *proposed*),
  kept rather than lowered to the measured σ ≈ 8.4–8.7 mV. It stays OPEN
  under DR-003 until DR-009's named ratification act (a separate
  operator-approved PR; merging this PR is not it). No ratified target is
  changed.
- **Assembled by**: Loom Builder agent, issue #2 (bootstrap/scaffolding
  pass); issue #10 (2026-09-15 sizing pass); issue #20 (2026-09-16
  reconciliation pass)
- **Scope**: 1.8 V primary variant only. The 3.3 V I/O-device flavor is named
  but explicitly not opened here — per `CLAUDE.md`'s "1.8 V primary; 3.3 V
  I/O-device flavor only via decision record," opening it requires its own
  `spec/` decision record, never a silent addition alongside this table.

This file is the block's single consolidated target-spec table, following
the twin-row structure `CLAUDE.md` and `README.md` already name for this
program: a two-stage Miller-compensated op-amp specced on its own classic
rows (gain, GBW/PM into a stated `CL`, slew, noise, offset with a statistical
basis, CMRR/PSRR, swing, power), matching the row set the sky130-opamp's
same-topology twin
[`gf180-opamp/spec/target-spec.md`](https://github.com/2AMLogic/gf180-opamp/blob/main/spec/target-spec.md)
uses. Before this file existed, that row set lived only as prose in
`CLAUDE.md`/`README.md`. At the original 2026-09-06 bootstrap pass, nothing
performed circuit design, schematic capture, or simulation, and every
numeric target was either an engineering placeholder proposal `[P]` or
explicitly `[TBD]` pending sky130 device data that did not exist in this
repo yet (`design/`, `sim/`, `layout/`, and `measurements/` all held only
placeholder `README.md` files, verified against `main` @ `491adc3`,
2026-09-06). The 2026-09-15 sizing pass (issue #10) has since committed
device data (`sim/gm-id-characterization/`) and a topology decision
(`DR-001`) and used both to size most §2 rows — but still performs **no
circuit design, schematic capture, or simulation of its own**: `design/`,
`layout/`, and `measurements/` remain placeholder-only, and every `[P]`
value below is a sizing estimate, not a measured result (see §2a).

## How to read this table

**Value tags** — every non-definitional value carries one, following
[`gf180-temp-por/spec/target-spec.md`](https://github.com/2AMLogic/gf180-temp-por/blob/main/spec/target-spec.md)'s
convention (already adopted by this block's twin,
[`gf180-opamp/spec/target-spec.md`](https://github.com/2AMLogic/gf180-opamp/blob/main/spec/target-spec.md)),
so a future reviewer can tell a carried decision from a new proposal at a
glance:

| Tag | Meaning |
|---|---|
| **[DR-n]** | Carried unchanged from a decision record `n`. [`DR-001`](decision-records/DR-001-topology-and-cl.md) (status `submitted for ratification`) is the only one so far, and it tags the `CL` row below. |
| **[P]** | **Proposed by this bootstrap pass, by the 2026-09-15 sizing pass (issue #10), reconciled against the schematic-level device sizing of issue #13 / [`DR-002`](decision-records/DR-002-device-sizing.md) (issue #16), or (six §2 performance rows) reconciled against measured PVT-cornered circuit-level evidence from `sim/opamp-characterization` (issue #17 / PR #19, reconciled into this table by issue #20)** — an engineering placeholder or sizing estimate with no PVT-cornered testbench evidence behind it yet (e.g. carried from this repo's own `README.md`/`CLAUDE.md` framing, a structural convention borrowed from a same-PDK sibling's ratified spec, a §2 performance target sized from the committed gm/ID device sweep under [`DR-001`](decision-records/DR-001-topology-and-cl.md)'s topology — see [§2a](#2a-sizing-basis-for-the-2026-09-15-pass-illustrative-non-binding) — or a later re-estimate from `DR-002`'s drawn device widths, itself still a hand calculation, not a simulated result), **or**, as of issue #20, a value now cited to a measured `sim/` PVT-cornered testbench record instead of (or alongside) a hand estimate. The tag is unchanged in either case, because the *target itself* remains a proposal pending ratification — a measured citation is stronger evidence than a hand estimate, but is not itself a ratification act. Needs an explicit ratification decision before it binds. |
| **[TBD]** | Deliberately unset — no sky130 device data exists yet to propose even a placeholder number, or the committed gm/ID sweep (bare-device DC characterization only) has no basis for this row (e.g. offset/mismatch, CMRR/PSRR small-signal behavior, area — each has a one-line reason at its row, or in [§2a](#2a-sizing-basis-for-the-2026-09-15-pass-illustrative-non-binding)). Filled in once the relevant device/PVT-cornered testbench evidence exists. Tracked collectively under the gap-to-T1 tracker, [#3](https://github.com/2AMLogic/sky130-opamp/issues/3) (item 5, "Full PVT corner simulation vs a ratified spec"), rather than one issue per row. |

**Status** column values: `not started` (no `sim/` evidence exists for this
row at all), or, as of issue #20's reconciliation pass, `measured` (a
`sim/` record's full PVT grid exists and its worst-case value/corner is
cited at the row) — the six rows `sim/opamp-characterization` (issue #17 /
PR #19) measures (open-loop DC gain, GBW, phase margin, slew rate, output
swing, quiescent power) now carry `measured`, as, since issue #66, do the
input common-mode range and CMRR rows (issue #53's benches); every other
row remains `not started`. There is still no `ratifiable` or `conditional` row, unlike the
more mature same-PDK siblings (`sky130-bandgap`, `sky130-ldo`) this table's
shape is borrowed from — `measured` is **not** a synonym for `ratifiable`:
it states only that PVT-cornered testbench evidence now backs the row's
cited number, not that the row is ratified. Which rows are ratified is
recorded separately, by `DR-003` (issue #26) — see §5.

**Binding corner** — the corner at which a row's hard edge is expected to
bind, reasoned from the topology's *generic* behavior (a two-stage
Miller-compensated op-amp on a 1.8 V-core process) since no schematic exists
yet to simulate. This is a **prediction**, not a measurement —
`CLAUDE.md`'s "no claim without a testbench" applies to any future
*pass/fail* verdict on these rows, not to this placeholder prediction of
where the number will eventually bind. A `sim/` record's full PVT grid
supersedes the prediction once it exists.

## 1. Global operating conditions

| Parameter | Value | Notes |
|---|---|---|
| Supply voltage, VDD | **1.8 V ±10% → 1.62–1.98 V** [P] | Primary variant per `CLAUDE.md`'s "1.8 V primary" framing — sky130's 1.8 V core device flavor (`sky130_fd_pr__nfet_01v8` / `pfet_01v8`). This is the **low-voltage member of the three-foundry op-amp twin** (gf180-opamp: 3.3 V primary; sg13g2-opamp: to be confirmed) — headroom-driven divergences from those twins (cascoding choices, swing-row bounds) are expected and will be documented as findings, not hidden, per `CLAUDE.md`. |
| Supply voltage, VDD (I/O-device flavor) | **3.3 V — not opened** [P] | sky130's I/O-tolerant device flavor (`sky130_fd_pr__nfet_g5v0d10v5` / `pfet_g5v0d10v5`, used at 3.3 V per `sky130-ldo`'s [DR-001](https://github.com/2AMLogic/sky130-ldo/blob/main/spec/decision-records/DR-001-pass-device-supply-framing.md) precedent for using this flavor below its full 5.0 V/10.5 V rating). Per `CLAUDE.md`, opening this row requires its own decision record; it is named here only so a future DR has a place to point at, not to imply the row is in scope. [`DR-005`](decision-records/DR-005-io-flavor-not-served.md) records the standing decision that this block does not serve a 3.3 V-rail amplifier position — a superseding DR is the only path to opening the flavor. Never mixed with 1.8 V core-flavor devices in one variant. |
| Operating temperature | **−40…+125 °C** [P] | Matches the fleet-wide convention (`sky130-bandgap`, `sky130-ldo`) for a commercial-grade PDK part. No sky130-specific device data has been checked against this range yet for this topology — proposed by analogy, not measured. |
| Corner grid | **`tt, ff, ss, sf, fs` (sky130 1.8 V-core MOS process corners) — confirmed [P]** | Same *shape* `sky130-bandgap`'s ratified corner set uses, now confirmed specifically for the `_01v8` (1.8 V-core) device flavor against the pinned PDK checkout, rather than assumed by analogy from that 3.3 V-primary sibling — see [`sim/gm-id-characterization/corners/model-files.json`](../sim/gm-id-characterization/corners/model-files.json) and [`corners/README.md`](../sim/gm-id-characterization/corners/README.md) (issue #6), which resolve each corner to its literal `sky130_fd_pr__{nfet,pfet}_01v8__<corner>.*.spice` model file. Still `[P]`, not ratified — this row's binding-corner predictions and pass/fail behavior are decided independently, once a topology exists (see [`porting-plan.md`](porting-plan.md) §4). |
| Load capacitance, CL | **2 pF [DR-001]** | GBW/phase-margin targets are stated "into stated CL" per the twin-row convention. Chosen in [`DR-001`](decision-records/DR-001-topology-and-cl.md) to match `sg13g2-opamp`'s own `CL` decision for cross-PDK comparability across the three-foundry twin set; `gf180-opamp` has no `CL` decision yet to compare against. |

## 2. Performance targets

| Parameter | Target | Stretch | Statistical basis | Binding corner (predicted) | Status |
|---|---|---|---|---|---|
| Open-loop DC gain | **≥ 60 dB [P]** — met at every measured corner of both PVT grids. On the current (DR-007) sizing: worst-case **61.64 dB @ FS / 125 °C**, 1.6 dB of margin (`sim/opamp-characterization` record [`20261001-074923-c317ff9`](../sim/opamp-characterization/records/20261001-074923-c317ff9.md), issue #22's resize reconciliation) — the deliberate cost of DR-007's PMOS-group `L` 0.6 → 0.3 µm trade that closes GBW. On the superseded DR-002 sizing the worst case was 69.72 dB @ SS / 125 °C with 9.7 dB of margin (record [`20260916-032327-edc9f22`](../sim/opamp-characterization/records/20260916-032327-edc9f22.md)); the resize lowers every point by 5.4–8.1 dB, met everywhere on both grids. Target unmet nowhere; margin narrowed — recorded per DR-007 §(b) as the one accepted cost of the resize | ≥ 65 dB [P] | — (deterministic corner-worst-case candidate) | **FS / 125 °C (measured worst-case on the DR-007 sizing)** — moved from SS / 125 °C (the DR-002 sizing's measured worst): the shorter PMOS channel costs gm/gds most where the pfet is already weak (FS) and hot. Full 15-point grid at the cited record | **measured** — `sim/opamp-characterization` record `20261001-074923-c317ff9` (issue #22 / DR-007 resize; prior record `20260916-032327-edc9f22`, issue #17 / PR #19); ratified by `DR-003` (see §5) |
| GBW (into stated CL = 2 pF, per `DR-001`) | **≈ 16 MHz [P]** — self-consistent sizing example (§2a). **Met by the current (DR-007) sizing at every measured corner**: worst-case **17.92 MHz @ SS / 125 °C, 112% of target** (`sim/opamp-characterization` record [`20261001-074923-c317ff9`](../sim/opamp-characterization/records/20261001-074923-c317ff9.md), issue #22's resize reconciliation; grid 17.92–27.07 MHz) — closed from the superseded DR-002 sizing's **8.45 MHz @ SS / 125 °C (≈53% of target)** (record [`20260916-032327-edc9f22`](../sim/opamp-characterization/records/20260916-032327-edc9f22.md)) by DR-007's input-pair gm/ID 10 → 17 at unchanged `I_SS`, with the PMOS group's L 0.6 → 0.3 µm holding phase margin ≥ 60° everywhere at the higher crossover. Per `CLAUDE.md` the target was never lowered; it is now met | — | — | **SS / 125 °C (measured worst-case, both grids)** — unchanged by the resize; GBW still falls with increasing temperature at every corner, SS still the slowest process corner. Full 15-point grid at the cited record | **measured, target met at every corner** — `sim/opamp-characterization` record `20261001-074923-c317ff9` (issue #22 / DR-007 resize; prior record `20260916-032327-edc9f22`, issue #17 / PR #19) |
| Phase margin (at GBW, same CL) | **≥ 60° [P]** — **confirmed on both PVT grids**: on the current (DR-007) sizing, measured worst-case **63.94° @ SF / 27 °C**, ≥ 3.9° of margin at every corner (`sim/opamp-characterization` record [`20261001-074923-c317ff9`](../sim/opamp-characterization/records/20261001-074923-c317ff9.md), issue #22's resize reconciliation); on the superseded DR-002 sizing the worst case was 64.09° at the same corner (record [`20260916-032327-edc9f22`](../sim/opamp-characterization/records/20260916-032327-edc9f22.md)) — the worst corner and margin are essentially unchanged by the resize, which is DR-007's design constraint working: the GBW ×2.12 increase is held against `p2` by the PMOS group's shorter channel (higher `fT6`) and the 2.50 kΩ over-nulled `Rz` | ≥ 45° at the FF/hot corner if 60° is unreachable there — not exercised; target met at every measured corner of both grids | — (deterministic corner-worst-case) | **SF / 27 °C (measured worst-case, both grids)** — SF (slow-NMOS/fast-PMOS), essentially flat across temperature, remains the actual worst process corner ≈1.9° below FF / 125 °C. Full 15-point grid at the cited record | **measured** — `sim/opamp-characterization` record `20261001-074923-c317ff9` (issue #22 / DR-007 resize; prior record `20260916-032327-edc9f22`, issue #17 / PR #19); ratified by `DR-003` (see §5) |
| Slew rate | **≈ 20 V/µs [P]** — self-consistent sizing example (§2a), assumed rise/fall-symmetric (`SR = I_SS/Cc`). **Rise SR is met by the current (DR-007) sizing**: measured worst-case **19.88 V/µs @ SS / −40 °C (99.4% of target)**, grid 19.88–20.89 (`sim/opamp-characterization` record [`20261001-074923-c317ff9`](../sim/opamp-characterization/records/20261001-074923-c317ff9.md), issue #22's resize reconciliation). **Fall SR is partially closed**: measured worst-case **11.03 V/µs @ SS / −40 °C — 55% of target**, up ×6.4 from the superseded DR-002 sizing's **1.73 V/µs (under 9% of target)** at the same corner (record [`20260916-032327-edc9f22`](../sim/opamp-characterization/records/20260916-032327-edc9f22.md)); every grid point improves on both edges. The DR-007 diagnosis (instrumented transient at SS / −40 °C): during the falling edge the input pair's differential overdrive drags the tail node to ~4 mV, starving the first stage — the tail/mirror group's resize (gm/ID 15 → 18) lifts the crawl current, and the residual gap is structural (class-A fixed-bias sink + first-stage starvation), requiring a topology change (DR-001's domain) to close fully. Per `CLAUDE.md` the target is **not** lowered; the honest partial-close statement is this row's current verdict | — | — | **SS / −40 °C for both edges (measured worst-case on the DR-007 sizing)** — rise's worst moves from SS / 125 °C (DR-002 grid) to SS / −40 °C; fall's worst corner is unchanged and the mechanism is now measured, not hypothesized. Full 15-point grid at the cited record | **measured, rise met everywhere; fall partially closed (11.03 V/µs @ SS / −40 °C, 55% of target)** — `sim/opamp-characterization` record `20261001-074923-c317ff9` (issue #22 / DR-007 resize; prior record `20260916-032327-edc9f22`, issue #17 / PR #19) |
| Input-referred noise | **≈ 30 nV/√Hz thermal floor [P], proposed band 100 Hz – 1 MHz [P]** — flicker (1/f) not characterized by the committed gm/ID sweep (§2a) | — | n/a — deterministic device-noise estimate, not yet mismatch/MC-based | TT / 27 °C (thermal-floor estimate is only weakly corner-dependent under this pass's constant-current-bias assumption — see §2a caveat) | not started |
| Input-referred offset | **σ ≤ 0.275 mV (3σ ≤ 0.825 mV) [P]** — the **consumer-derived** number: the tighter end of `sky130-bandgap`'s input-referred amplifier allocation (≈ 0.275–0.369 mV σ, Consumers section), proposed by [`DR-009`](decision-records/DR-009-offset-target.md) (status *proposed*, not ratified) and **kept, not lowered to match the measurement**. **Measured, not met** (gap vs the consumer allocation): the N = 300 mismatch Monte Carlo campaign (issue #85, record [`campaign-20261009-offset-mc300.md`](../sim/offset-capability/records/campaign-20261009-offset-mc300.md) with summary `20261009-154748-campaign-offset-mc300-final-5fbc07.campaign.json`) gives σ from 8.38 mV @ SF / 27 °C to 8.69 mV @ SS / 27 °C across the five corners, 3σ from 25.15 mV @ SF / 27 °C to 26.08 mV @ SS / 27 °C, and |mean| + 3σ up to 26.59 mV @ SS / 27 °C — about 23× to 32× the allocation in σ. Caveats from that record: 27 °C and VDD = 1.8 V only; sweep bracket ±30 mV (extremes at ±27–28 mV); Vos is the open-loop V(inp) − V(inn) at the v(out) = 0.9 V crossing, not a closed-loop offset. The closing lever is not identified (attribution is issue #107). Until DR-009's named ratification act (a separate operator-approved PR flipping DR-009's Status line to `ratified` and removing this note; merging the issue #108 PR is **not** that act) this row stays **OPEN** under DR-003 (§5); the number is a proposal, not a binding target. Earlier `[TBD]` reason (no mismatch MC pass existed) is discharged by the cited record | — | **3σ, mismatch MC N≥300 + process corners [P]** — matches `sky130-bandgap`'s ratified statistical-basis convention; N = 300 per corner now run at TT/SS/FF (+ SF/FS), paired seeds, all 300/300 samples ok; the basis itself stays proposed (DR-009) | SS / 27 °C (widest σ, measured; 27 °C / 1.8 V only — no temperature or VDD grid) | measured; target proposed (DR-009), not ratified; not met |
| CMRR | **≥ 50 dB, DC – 1 kHz [P]** — proposed by [`DR-008`](decision-records/DR-008-cmrr-target.md) (status *proposed*, not ratified), graded as the worst case over the full 15-point grid at **both** recorded common-mode points (0.5·VDD and 0.956 V, the centre of the ICMR target window). Basis: the common-mode AC bench (`Adm − Acm` in one deck) measures a worst case of **55.11 dB @ SS / −40 °C at mid-rail common mode** (0.81 V, which at VDD = 1.62 V lies below the ICMR target window), 5.1 dB of margin; at the target-window centre the worst case is **69.34 dB @ FS / 125 °C** (`sim/opamp-characterization` record [`20261009-103006-566b9a5`](../sim/opamp-characterization/records/20261009-103006-566b9a5.md), issue #53). CMRR is flat to within 0.001 dB from 1 Hz to 10 kHz at every point (the 1 MHz values are not used for grading). Until DR-008's named ratification act (a separate operator-approved PR flipping DR-008's Status line to `ratified` and removing this note; merging the issue #66 PR that introduced DR-008 is **not** that act) this row stays **OPEN** under DR-003 (§5); the number is a proposal, not a binding target. Earlier `[TBD]` reason (no common-mode bench existed; the gm/ID sweep has no basis for it, §2a) is discharged by the cited record | ≥ 60 dB [P] (DR-008) — not met at SS / −40 °C (55.11 dB) and SS / 27 °C (58.40 dB) at mid-rail; met at the other 28 of 30 points | — (deterministic corner-worst-case) | **SS / −40 °C / VDD = 1.62 V, mid-rail common mode (measured worst-case)**; at the window-centre point the worst corner is FS / 125 °C. Full 15-point grid at both common-mode points in the cited record's `-cmrr.csv` | **measured; target proposed (DR-008), not ratified** — `sim/opamp-characterization` record `20261009-103006-566b9a5` (issue #53); spec reconciliation issue #66 |
| PSRR | **[TBD]** — PSRR is a supply-to-output small-signal transfer function (through the compensation network and bias generator); the committed gm/ID sweep has no supply-voltage sweep axis at all (confirmed in `sim/gm-id-characterization/README.md`: "No supply-voltage axis is swept ... there is no 'supply corner' for a two-terminal-bias bare-device sweep"), so there is no device-level basis to size this row from yet (§2a) | — | — (deterministic corner-worst-case) | to be determined | not started |
| Input common-mode range | **≈ 0.888 – 1.024 V (≈ 136 mV window) at the worst-case corner [P]** — sizing estimate from `DR-002` §(f)/§(d), computed from the drawn input-pair and PMOS-mirror `Vov`/`Vth` at that corner. No `[TBD]`-to-`[P]` history for this row: it did not exist before this issue, because no device widths existed to size it from until `DR-002` (issue #13). The window sits *above* mid-rail (0.81 V) rather than spanning it, and is markedly narrower than the twins' topology would suggest — `DR-002` traces this to `DR-001`'s NMOS-input-pair / PMOS-mirror choice meeting sky130's PMOS threshold magnitude (`Vth_p` = 1.1065 V at `ss / −40 °C`), which alone would cap the window near ≈ 0.29 V even at zero PMOS-mirror overdrive. This is left as a recorded finding, not a design decision: `DR-002`'s own "Alternatives considered" names the knob to turn if it binds (biasing the PMOS group at `gm/ID = 12.5 V⁻¹` instead of 10, for ≈ 189 mV of window at ≈ 76 dB gain), but states — and this issue does not override that — that the choice between the current sizing and that alternative belongs against a *simulated* phase margin and common-mode sweep, not another hand calculation. If a future PVT-cornered bench confirms the window does not cover this block's intended input range, reopening `DR-001`'s input-pair polarity requires a **new** decision record superseding `DR-001`, per `DR-001`'s own superseding-record rule — not a silent edit to `DR-001` or to this row. **Measured (issue #53): met at every corner.** The ICMR bench (output held at mid-rail; ICMR = the contiguous common-mode range containing VDD/2 over which local DC CMRR ≥ 40 dB — a CMRR-degradation criterion, not a device-saturation one; see the bench's README caveat) records a **narrowest window of 0.7168 – 1.1686 V (0.452 V) @ SS / −40 °C**, which covers the 0.888 – 1.024 V target at **15 / 15 points**; the binding edges are the highest low edge 0.7388 V @ FS / −40 °C and the lowest high edge 1.1686 V @ SS / −40 °C, every edge input-stage limited (`sim/opamp-characterization` record [`20261009-103006-566b9a5`](../sim/opamp-characterization/records/20261009-103006-566b9a5.md)). The measured window is roughly 3× wider than the ≈ 136 mV hand estimate and extends below mid-rail at every point. The sky130-bandgap consumer's 0.73 V sense point (Consumers section) is **not met at FS / −40 °C** — low edge 0.7388 V, 8.8 mV above 0.73 V — and is covered at the other 14 points; that is a consumer requirement, not this row's target, and neither is relaxed | — | — (deterministic corner-worst-case) | SS / −40 °C / VDD = 1.62 V (the PMOS mirror's threshold magnitude `Vth_p` and the NMOS current-source `Vov` both bind hardest at this corner) — **confirmed for the narrowest window and the high edge (SS / −40 °C, measured)**; the low edge binds at FS / −40 °C instead. Full 15-point grid in the cited record's `-icmr.csv` | **measured, target met at every corner (40 dB criterion)** — `sim/opamp-characterization` record `20261009-103006-566b9a5` (issue #53; spec reconciliation issue #66); ratified by `DR-003` (see §5) |
| Output swing | **≈ 0.072 – 1.464 V (≈ 1.39 Vpp, ≈ 86% of the 1.62 V worst-case-low rail) [P]** — sizing estimate from `DR-002` §(f)'s device-level (drawn-width) `Vov` headroom at the worst-case-low rail (SS / −40 °C / 1.62 V), superseding §2a's earlier ≈ 0.17–1.45 V estimate, computed before any device width existed. **Partially closed by the current (DR-007) sizing**: the unity-buffer DC-swing bench measures **0.254 – 1.203 V (0.948 Vpp, 58.5% of the 1.62 V rail) at that same corner (SS / −40 °C)**, up from **0.328 – 1.184 V (0.855 Vpp, 52.8%)** on the superseded DR-002 sizing — an improvement at **every** one of the 15 grid points (DR-007's wider output devices lower both `Vov`s), but the ≈ 1.39 Vpp DR-002 estimate at that corner remains **unmet** (`sim/opamp-characterization` record [`20261001-074923-c317ff9`](../sim/opamp-characterization/records/20261001-074923-c317ff9.md), issue #22's resize reconciliation; prior record [`20260916-032327-edc9f22`](../sim/opamp-characterization/records/20260916-032327-edc9f22.md)). Per `CLAUDE.md` the target is **not** lowered to match either measurement | — | — | **SS / −40 °C / low VDD (measured worst-case, both grids — confirms this row's own prior prediction)**: swing still widens monotonically with increasing temperature at every process corner. Full 15-point grid at the cited record | **measured, partially closed (0.948 Vpp @ SS / −40 °C vs ≈1.39 Vpp estimate; every grid point improved vs the DR-002 grid)** — `sim/opamp-characterization` record `20261001-074923-c317ff9` (issue #22 / DR-007 resize; prior record `20260916-032327-edc9f22`, issue #17 / PR #19) |
| Quiescent power | **≈ 128.7 µW at the stated binding corner (1.98 V); ≈ 117.0 µW at nominal 1.8 V [P]** — **confirmed on both PVT grids at unchanged bias currents**: on the current (DR-007) sizing, measured **131.92 µW @ FF / 125 °C / 1.98 V (+2.5% vs. the `DR-002` estimate, +0.9% vs. the prior grid's 130.71 µW at the same point)**, with `Iq` 64.24–66.63 µA across the 15-point grid (`sim/opamp-characterization` record [`20261001-074923-c317ff9`](../sim/opamp-characterization/records/20261001-074923-c317ff9.md), issue #22's resize reconciliation); the prior grid measured 130.71 µW @ FF / 125 °C / 116.27 µW @ TT / 27 °C on the DR-002 sizing (record [`20260916-032327-edc9f22`](../sim/opamp-characterization/records/20260916-032327-edc9f22.md)). DR-007 changes device sizes only — `I_Q = 65 µA` (`I_SS = 10 µA + ID2 = 50 µA + 5 µA` reference branch) is exactly DR-002 §(a)'s budget, which is what the row's "≈" estimate encodes | — | — (deterministic corner-worst-case) | **FF / 125 °C / 1.98 V (measured worst-case, both grids — confirms this row's own prior prediction)** — matches `sky130-bandgap`'s ratified Iq binding-corner convention. Full 15-point grid at the cited record | **measured** — `sim/opamp-characterization` record `20261001-074923-c317ff9` (issue #22 / DR-007 resize; prior record `20260916-032327-edc9f22`, issue #17 / PR #19); ratified by `DR-003` (see §5) |
| Area | **[TBD]** — no `layout/` exists yet (holds only a placeholder `README.md`); area has no gm/ID-derived basis at all — it is a post-layout quantity, not a circuit-sizing one, and is not proposed here even as a placeholder | — | n/a (not a PVT line) | n/a | not started |

Every row above now carries either a `[P]` sizing estimate (issue #10,
sized from the committed gm/ID device sweep under `DR-001`'s topology —
see §2a immediately below for the shared assumptions and per-row
derivation), an explicit `[TBD]` with a one-line reason it cannot yet be
filled from that data (PSRR, area; offset was `[TBD]` until issue #108), or — for the six rows
below — a `[P]` value now reconciled against measured PVT-cornered
circuit-level evidence (issue #20, from `sim/opamp-characterization`,
issue #17 / PR #19). CMRR was `[TBD]` on the same grounds until issue #66,
which fills it with a `[P]` target proposed by `DR-008` against issue #53's
measured common-mode AC bench; the input common-mode range row is likewise
reconciled against issue #53's ICMR bench by issue #66.

**Reconciliation summary (issue #20, 2026-09-16), stated plainly per
`CLAUDE.md`'s "no claim without a testbench" and this issue's own
instruction not to fudge or hide a contradiction**: of the six rows
measured, two (**phase margin**, **quiescent power**) **confirm** their
`DR-002` hand estimate at both the predicted binding corner and its
magnitude. The other four **contradict** some part of theirs: **open-loop
DC gain**'s predicted binding corner's *process family* (SS) is confirmed
but its *temperature extreme* is not (worst is 125 °C, not −40 °C — the
`≥ 60 dB` target itself is still met everywhere); **GBW** is contradicted
on both the binding corner's temperature extreme *and* the qualitative
fastest/slowest trend across corners, and is **not met by the current
sizing** at its measured worst case (8.45 MHz, ≈53% of the ≈16 MHz target);
**slew rate** is contradicted on an unstated rise/fall-symmetry
assumption — rise SR stays close to target, but fall SR is **not met by
the current sizing**, and badly (1.73 V/µs measured worst case, under 9%
of the ≈20 V/µs target); **output swing**'s binding corner is confirmed
but its magnitude is **not met by the current sizing** (0.855 Vpp
measured vs. ≈1.39 Vpp estimated at the same corner, 62%). **Per
`CLAUDE.md`, this reconciliation does not lower any target to match a
measurement** — the `≥ 60 dB`, `≈ 16 MHz`, `≈ 20 V/µs`, and `≈ 1.39 Vpp`
figures above are unchanged from the 2026-09-15 sizing pass; where the
current `DR-002` device sizing does not achieve them, the row says so
explicitly rather than silently relaxing the number. Closing the GBW/
slew-rate/output-swing gaps is a device-resizing exercise against this
now-reconciled baseline, and is an explicitly out-of-scope follow-on for
this issue (tracked separately, not by this table edit) — as is a
dedicated bench diagnosing the fall-slew-rate collapse's root cause
(`sim/opamp-characterization/README.md`'s own stated hypothesis: `M7`'s
fixed, non-signal-modulated bias current). This reconciliation also does
**not** itself ratify the table or any individual row — `measured` (see
"How to read this table" above) states only that PVT-cornered evidence now
exists. Ratification is `DR-003`'s separate pass (issue #26), recorded in
§5.

**Resize reconciliation summary (issue #22, 2026-10-01), same plain-spoken
rule**: the `DR-007` device resize was measured by re-running issue #17's
bench unchanged (record
[`20261001-074923-c317ff9`](../sim/opamp-characterization/records/20261001-074923-c317ff9.md),
same PDK pin, same runner) against the resized netlist. **GBW and rise
slew rate are now met at every corner** (17.92 MHz and 19.88 V/µs worst
case vs the ≈16 MHz / ≈20 V/µs targets). **Fall slew rate and output
swing partially close** — 1.73 → 11.03 V/µs (×6.4) and 0.855 → 0.948 Vpp
at their SS / −40 °C worst corners, improving at every grid point, with
the fall-SR mechanism now *measured* (first-stage tail starvation under
differential overdrive, not `M7`'s sink magnitude alone — DR-007's
diagnosis), and the residual gaps honestly stated rather than closed by
target edit. **Phase margin and quiescent power hold** (63.94° worst,
131.92 µW worst, both at their predicted binding corners). **Open-loop DC
gain remains met everywhere but pays for the resize**: worst case
69.72 → 61.64 dB (margin 9.7 → 1.6 dB, worst corner SS/125 → FS/125 °C)
— the recorded cost of `DR-007`'s PMOS channel-length trade, accepted
deliberately and stated here per the same no-fudge rule. No target value
changed in this pass either.

None of the remaining `[TBD]` rows (then offset, CMRR, PSRR, area, and the
separately-estimated input-common-mode-range `[P]` row, as they stood on
2026-10-01) is affected by this reconciliation — the three testbench types `sim/opamp-characterization`
introduces (open-loop AC, unity-buffer slew-rate transient, unity-buffer
DC-swing) do not characterize any of them; each still needs the testbench
type named at its own row. Filling those rows, and closing the four
contradicted rows' gap to target, requires the testbenches named at each
row (tracked in [`porting-plan.md`](porting-plan.md) and the gap-to-T1
tracker, [#3](https://github.com/2AMLogic/sky130-opamp/issues/3)).

**ICMR / CMRR reconciliation summary (issue #66, 2026-10-09), same rule**:
issue #53 added the two benches named at those rows (an ICMR bench with the
output held at mid-rail, and a same-deck `Adm − Acm` common-mode AC bench),
measured on the unchanged DR-007 netlist in record
[`20261009-103006-566b9a5`](../sim/opamp-characterization/records/20261009-103006-566b9a5.md).
**Input common-mode range is met at every corner**: the narrowest window,
0.7168 – 1.1686 V @ SS / −40 °C, covers the ratified 0.888 – 1.024 V target
at 15 / 15 points (40 dB local-CMRR criterion; a CMRR-degradation range,
not a device-saturation one). The consumer sense point 0.73 V is **not
met at FS / −40 °C** (low edge 0.7388 V, 8.8 mV short) — recorded in the
Consumers section, not relaxed. **CMRR is measured**: worst 55.11 dB @
SS / −40 °C at mid-rail common mode, 69.34 dB worst at the target-window
centre (FS / 125 °C). Because the row had no target, `DR-008` *proposes*
one (≥ 50 dB, DC – 1 kHz, `[P]`); ratifying it is a separate operator
step, and the row stays OPEN under DR-003 until then. No ratified target
changed in this pass.

## 2a. Sizing basis for the 2026-09-15 pass (illustrative, non-binding)

**Superseded for six rows, 2026-09-16 (issue #20).** This section's
derivations predate even `DR-002`'s device-level re-estimate (they work
directly from the bare gm/ID CSV, before any device width existed) and are
now further superseded, for the six rows §2's table cites to measured
data, by `sim/opamp-characterization`'s PVT-cornered circuit-level
evidence — see the "Reconciliation summary" immediately above §2a and
each row's own citation. This section is kept as-is below, unedited, as
the historical illustrative derivation trail issue #10's own acceptance
criteria required; it is not itself updated by issue #20.

This section is the citation trail the acceptance criteria for issue #10
require: every `[P]` value in the table above is derived here from a
literal, quoted row of
[`sim/gm-id-characterization/records/20260909-062847-35a9d46-summary.csv`](../sim/gm-id-characterization/records/20260909-062847-35a9d46-summary.csv)
(grep either that file or
[`-full-sweep.csv`](../sim/gm-id-characterization/records/20260909-062847-35a9d46-full-sweep.csv)
directly to reproduce any number below), plus the structural ratios
`DR-001`'s own "Appendix — illustrative (non-binding) first-cut
compensation budget" already names (`Cc ≈ (0.2–0.3) × CL`, `gm2/gm1 ≈ 10`).
**No device width, mirror ratio, or absolute bias current is chosen
anywhere in this repo yet** (`DR-001`'s own "Open items" leaves all three
open) — the bias currents below are this pass's own proposed sizing
example, explicitly flagged as a choice rather than a value read off a
CSV, used to turn `DR-001`'s ratio-only appendix into concrete GBW/slew/
power numbers. A future schematic-level sizing pass may choose different
absolute currents; the ratios (`Cc`, `gm2/gm1`) are the more durable part
of this estimate.

**Shared sizing assumptions (this pass's proposal, not CSV-derived):**

- `Cc = 0.5 pF` — the midpoint of `DR-001`'s own `Cc ≈ (0.2–0.3) × CL`
  range at `CL = 2 pF`, and the exact value `DR-001`'s own worked example
  uses (`(2/0.5) × 2.5 ≈ 10` for the `gm2/gm1` ratio).
- Input-pair tail current `I_SS = 10 µA` (`ID1 = 5 µA` per side), at the
  same `gm/ID = 10 V⁻¹` design point every device in `DR-001` is cited at.
- Output-stage bias current `ID2`, set by `DR-001`'s `gm2/gm1 ≈ 10` ratio
  at the same `gm/ID = 10 V⁻¹` target for the output-stage devices (so
  `ID2/ID1 = gm2/gm1 = 10` when both stages share one `gm/ID` target):
  `ID2 = 50 µA`.
- A 1:1 first-stage mirror ratio (input NMOS drain current = PMOS mirror
  device current) and a matched-current output-stage current-source load
  (`DR-001`'s own framing: "matched-headroom bias branch") — both biased
  at the same `gm/ID = 10 V⁻¹` target as the device they share a node
  with, so the two devices at a shared small-signal node carry equal `gm`
  when their currents are equal (used in the DC-gain parallel-resistance
  calculation below).
- Bias currents are assumed PVT-invariant in this simplified model (no
  bias-generator design exists yet to say otherwise) — flagged as a
  modeling limitation, not a claim about a real bias generator's PSRR/PVT
  behavior.

**Open-loop DC gain.** First-stage output resistance is the parallel
combination of the input NMOS's own `ro` and the PMOS mirror device's
`ro`; because both carry equal current at the same `gm/ID` target (1:1
mirror), their `gm` values are equal, so the stage gain reduces to the
harmonic-mean-style parallel combination of the two devices' `gm/gds`
figures: `A1 = (gm_gds_n1 × gm_gds_p,mirror) / (gm_gds_n1 + gm_gds_p,mirror)`.
The same reduction applies to the second stage (`A2`), between the PMOS
gain device and its matched-current NMOS current-source load. At the
table's stated binding corner (`SS / −40 °C`):
`nfet,ss,0.15,-40.0,10.0,0.11065760695501746,23.055890095214018,53499354550.85566`
(input pair, `gm/gds = 23.056`) and
`pfet,ss,0.3,-40.0,10.0,0.16313970704600889,59.884981649589385,3519118888.054376`
(mirror load, `gm/gds = 59.885`) give `A1 ≈ 16.65`; and
`pfet,ss,1.2,-40.0,10.0,0.17374527049866112,391.3798627647017,279700538.2027164`
(output gain device, `gm/gds = 391.38`) and
`nfet,ss,1.2,-40.0,10.0,0.17338892591692476,147.9923717947348,1199214917.0636318`
(output current-source load, `gm/gds = 147.99`) give `A2 ≈ 107.4` —
`A_v = A1 × A2 ≈ 1788` (`≈ 65.1 dB`). Repeating at `TT / 27 °C`
(`nfet,tt,0.15,27.0,10.0,0.08251096420151932,17.812185903821444,50310997967.09632`;
`pfet,tt,0.3,27.0,10.0,0.14565187191474413,57.8640597462792,3365681803.31053`;
`pfet,tt,1.2,27.0,10.0,0.15633370223321472,394.29946200230614,240374428.32014117`;
`nfet,tt,1.2,27.0,10.0,0.1779772321718718,150.34338894034482,923694282.0334392`)
gives `A_v ≈ 1483` (`≈ 63.4 dB`), and at `FF / 125 °C`
(`nfet,ff,0.15,125.0,10.0,0.07637849840036044,14.890830794752453,48130572647.863014`;
`pfet,ff,0.3,125.0,10.0,0.08012418418989142,51.9412838369931,2379111683.245384`;
`pfet,ff,1.2,125.0,10.0,0.11079070052309993,393.3747331737141,173631100.59244695`;
`nfet,ff,1.2,125.0,10.0,0.196416094071378,153.89886135344202,691484917.1382074`)
gives `A_v ≈ 1280` (`≈ 62.1 dB`). **Finding**: under this simplified
loaded-parallel-resistance model, `FF / 125 °C` (≈ 62.1 dB) trends
slightly lower than the table's stated predicted binding corner
`SS / −40 °C` (≈ 65.1 dB) — the predicted-binding-corner column is left
unchanged here (it is a topology-level prediction, not a `[TBD]` row this
issue fills), but a future corner sweep should confirm which corner
actually binds once a schematic exists. The `Target: ≥ 60 dB` is set
conservatively below all three corner estimates to leave margin for
effects this simplified two-device-parallel model omits entirely
(non-unity mirror ratios, finite tail-current-source loading of the first
stage, layout mismatch).

**GBW, slew rate, and the phase-margin cross-check.** With
`gm1 = (gm/ID) × ID1 = 10 V⁻¹ × 5 µA = 50 µS`:
`GBW ≈ gm1 / (2π·Cc) = 50 µS / (2π × 0.5 pF) ≈ 15.9 MHz`. Slew rate for a
two-stage Miller topology is set by the tail current fully diverting into
`Cc` during a large-signal step: `SR = I_SS / Cc = 10 µA / 0.5 pF = 20 V/µs`.
As a self-consistency check against `DR-001`'s own appendix (which assumed
`p2 / GBW ≈ 2.5` to derive its `gm2/gm1 ≈ 10` ratio): with
`gm2 = 10 × gm1 = 500 µS`, the non-dominant pole
`p2 = gm2 / CL = 500 µS / 2 pF ≈ 2.5 × 10⁸ rad/s ≈ 39.8 MHz`, giving
`p2 / GBW ≈ 39.8 / 15.9 ≈ 2.50` — an exact match to `DR-001`'s own assumed
ratio, i.e. this pass's chosen `Cc`/current values are internally
consistent with the phase-margin budget `DR-001` already named, not an
independent coincidence. Feasibility against device speed: the input
pair's own `fT` at the GBW-binding corner
(`nfet,ss,0.15,-40.0,10.0,...,53499354550.85566` → `fT ≈ 53.5 GHz`) is
~3400x the ~16 MHz GBW target, leaving no plausibility concern at this
level of estimate.

**Quiescent power.** Total quiescent current
`I_Q = I_SS + ID2 = 10 µA + 50 µA = 60 µA`. At the table's stated binding
corner (`FF / 125 °C / 1.98 V`): `P_Q = 60 µA × 1.98 V ≈ 118.8 µW`; at
nominal `1.8 V`: `P_Q = 60 µA × 1.8 V ≈ 108 µW`. This
uses the same `I_SS`/`ID2` sizing choice as the GBW/slew-rate estimate
above (not separately re-derived), under the PVT-invariant-bias-current
simplification stated in "Shared sizing assumptions."

**Input-referred noise (thermal floor only).** For a differential pair
with a 1:1 current-mirror load, matched `gm` between the input device and
the mirror device (per the DC-gain derivation above), the classic
input-referred thermal-noise PSD reduces to
`en² = (16kT / 3gm1) × (1 + gm_mirror/gm1) = 32kT / (3·gm1)`. At
`gm1 = 50 µS`, `T = 300.15 K` (`27 °C`, `k = 1.380649×10⁻²³ J/K`):
`en² ≈ 8.84×10⁻¹⁶ V²/Hz` → `en ≈ 29.7 nV/√Hz`, rounded to `≈ 30 nV/√Hz`.
**Caveat, stated plainly**: this is a thermal-noise-floor estimate only —
the committed gm/ID sweep characterizes DC operating points (`gm/ID`,
`gm/gds`, `fT`), not flicker (`1/f`) noise coefficients, so no `1/f`
corner or total-integrated-noise number is proposed. The `100 Hz – 1 MHz`
band is a proposed measurement band (order-of-magnitude match to the GBW
sizing estimate above), not a value read from any CSV. Corner-to-corner
variation of this estimate is not modeled beyond the `kT` temperature
term, under the same PVT-invariant-bias-current simplification as the
power/GBW estimates.

**Output swing.** At the output stage's candidate devices
(`pfet,ss,1.2,-40.0,10.0,0.17374527049866112,391.3798627647017,279700538.2027164`,
`Vov,p2 ≈ 0.174 V`; `nfet,ss,1.2,-40.0,10.0,0.17338892591692476,147.9923717947348,1199214917.0636318`,
`Vov,n2 ≈ 0.173 V`) at the worst-case-low rail
(`VDD = 1.62 V`, per `target-spec.md` §1): `Vout,min ≈ Vov,n2 ≈ 0.173 V`
and `Vout,max ≈ VDD − Vov,p2 ≈ 1.62 − 0.174 ≈ 1.446 V`, giving a
peak-to-peak swing of `≈ 1.27 V` (`≈ 79%` of the `1.62 V` rail) — this is
a saturation-headroom estimate only (each device needs `Vds`/`Vsd` ≥ its
own `Vov` to stay in saturation), not a full large-signal swing/settling
simulation.

**Rows left `[TBD]`.** Offset, PSRR, and area each had a one-line
reason directly in their table cell (CMRR was also left `[TBD]` by
this pass; issue #66 later filled it from a measured bench, and issue #108
filled offset from the mismatch Monte Carlo campaign, not from this
section); none is a gm/ID-derivable
quantity with the committed sweep's data (bare single-device DC
operating points only — no mismatch coefficients, no supply-sweep axis,
no layout). Per this issue's explicit scope, no new device-characterization
sweep is performed to fill them.

## 3. What this table is not

- **Not ratified.** `spec/decision-records/DR-001-topology-and-cl.md` exists
  ([status `submitted for ratification`](decision-records/DR-001-topology-and-cl.md),
  via the PR that lands this 2026-09-15 sizing pass), but the record's own
  author (a Builder agent) cannot ratify it — this PR is the ratification
  *draft*, per the 2026-08-19 canary spec/DR ratification-via-PR standing
  policy ([2AMLogic/2am#357](https://github.com/2AMLogic/2am/issues/357))
  and the two-key mechanism epic
  ([2AMLogic/2am#372](https://github.com/2AMLogic/2am/issues/372)): a
  non-author EE key and a non-author market key (or, per the standing
  policy, direct operator PR approval where the two-key rollout has not
  yet reached this repo) are what perform the ratification act, not this
  commit. The same applies to every `[P]` sizing estimate this pass adds
  to §2 — proposed on the evidence shown in §2a, not self-ratified.
- **Not a commitment that every `[TBD]` row will end up non-trivial.** Some
  rows (e.g. the corner grid) may turn out to be determined jointly with a
  topology decision rather than independently — `CL` above is now resolved
  via `DR-001`, and most §2 performance rows now carry a `[P]` sizing
  estimate (§2a); PSRR and area remain `[TBD]`, each with a
  stated reason at its row (CMRR carries a `[P]` target proposed by
  `DR-008`, issue #66; offset carries a `[P]` target proposed by
  `DR-009`, issue #108).
- **Not opening the 3.3 V I/O-device-flavor row.** It is named, not scoped
  in.
- **Not a schematic, layout, or simulation pass (2026-09-15).** The
  2026-09-15 sizing pass (issue #10) added no files under `design/`,
  `layout/`, or `measurements/`, and ran no new simulation — every `[P]`
  value it added to §2 was a sizing estimate computed from the
  already-committed gm/ID device sweep and `DR-001`'s structural ratios
  (§2a), not a measured or simulated result. The later 2026-09-16
  reconciliation pass (issue #20) is different in kind: it cites *already-
  committed* measured evidence (`sim/opamp-characterization`, issue #17 /
  PR #19) into six §2 rows, but is itself still a `spec/`-only edit — it
  adds no new `design/`, `layout/`, or `sim/` files of its own, runs no new
  simulation, and changes no device sizing (see next bullet).
- **Not a resizing pass, and not `DR-002`'s ratification (2026-09-16).**
  Issue #20 explicitly does not modify `design/opamp_core.sch`,
  `design/netlist/opamp_core.spice`, or `DR-002` — the four rows its
  reconciliation finds are not met by the current sizing (GBW's binding
  corner and value, slew rate, output-swing magnitude) are reported as
  gaps against the *unchanged* target, not closed. Closing them is a
  future device-resizing issue against this reconciled baseline. Issue #20
  also does not itself ratify the table or promote any row past `measured`
  (see "How to read this table"); ratification is `DR-003`'s separate pass
  (issue #26, §5).

## 4. Sources

- `CLAUDE.md` (this repo) — the twin-row set, the 1.8 V-primary/3.3 V-I/O
  scope rule, and the gm/ID-first ordering.
- [`gf180-opamp/spec/target-spec.md`](https://github.com/2AMLogic/gf180-opamp/blob/main/spec/target-spec.md) — this block's identical-topology, same-bootstrap-issue twin on GF180MCU; the direct structural model for this file (value-tag convention, row set, "not ratified" framing), verified 2026-09-06.
- [`sky130-bandgap` README](https://github.com/2AMLogic/sky130-bandgap#readme) (see its "Target specification" section, ratified per DR-005/issue #1, PSRR row amended by DR-006/issue #123) — ratified target-spec table shape (Target/Stretch columns), the `3σ, mismatch MC N≥300 + process corners` statistical-basis wording, and the Iq binding-corner convention this table borrows. Note this sibling's own ratified Supply row is 3.3 V, not 1.8 V — its device flavor does not transfer directly to this block's 1.8 V-primary scope (see `porting-plan.md` §2).
- [`sky130-ldo/spec/target-spec.md`](https://github.com/2AMLogic/sky130-ldo/blob/main/spec/target-spec.md) — DRAFT-status target-spec precedent on this same PDK (per-row `Src` citation discipline, explicit "nothing here is ratified" banner, ratification gated on a dedicated issue rather than folded into the bootstrap issue) and [DR-001](https://github.com/2AMLogic/sky130-ldo/blob/main/spec/decision-records/DR-001-pass-device-supply-framing.md) for the `pfet_g5v0d10v5`/`nfet_g5v0d10v5` I/O-flavor-at-3.3V precedent cited above.
- [`klayout-tools/docs/design-evidence-tiers.md`](https://github.com/2AMLogic/klayout-tools/blob/main/docs/design-evidence-tiers.md) — the T1 checklist this spec's eventual evidence trail (`sim/`, `layout/`) will need to satisfy, tracked in the gap-to-T1 tracker, [#3](https://github.com/2AMLogic/sky130-opamp/issues/3).
- `sim/gm-id-characterization/records/20260909-062847-35a9d46-{summary,full-sweep}.csv` (issue #6 / PR #7) — the device data every `[P]` value added in the 2026-09-15 sizing pass (issue #10, §2a) is cited from directly.
- `spec/decision-records/DR-001-topology-and-cl.md` (issue #8 / PR #9) — the topology decision and structural compensation ratios (`Cc ≈ (0.2–0.3) × CL`, `gm2/gm1 ≈ 10`) the 2026-09-15 sizing pass builds on.
- [2AMLogic/2am#357](https://github.com/2AMLogic/2am/issues/357) and [2AMLogic/2am#372](https://github.com/2AMLogic/2am/issues/372) — the canary spec/DR ratification-via-PR standing policy and two-key mechanism this pass's DR-001 status promotion follows.
- `spec/decision-records/DR-002-device-sizing.md` (issue #13 / PR #15, status `proposed` — not ratified) — the schematic-level device sizing (`design/opamp_core.sch`) this issue (#16) reconciles the DC-gain, output-swing, and quiescent-power §2 rows against, and the source of the new input-common-mode-range row's numbers and finding.
- `spec/decision-records/DR-003-target-spec-ratification.md` (issue #26) — the 2026-09-21 ratification pass whose per-row dispositions this table's `Status` field and §5 below record; its primary measured input is `sim/opamp-characterization`'s committed record (issue #17 / PR #19).
- [`sim/opamp-characterization/records/20260916-032327-edc9f22.md`](../sim/opamp-characterization/records/20260916-032327-edc9f22.md) / `.json` and [`sim/opamp-characterization/README.md`](../sim/opamp-characterization/README.md) (issue #17 / PR #19) — the PVT-cornered, circuit-level measured evidence (open-loop AC, slew-rate transient, DC-swing testbenches against `design/netlist/opamp_core.spice`) this issue (#20) reconciles into the six `[P]`-tagged §2 performance rows (open-loop DC gain, GBW, phase margin, slew rate, output swing, quiescent power), confirming two and contradicting four against `DR-002`'s hand estimates — and the evidence behind those six rows' `DR-003` dispositions (§5).
- [`sim/opamp-characterization/records/20261009-103006-566b9a5.md`](../sim/opamp-characterization/records/20261009-103006-566b9a5.md) (data `-icmr.csv`, `-cmrr.csv`; issue #53) — the PVT-cornered ICMR and common-mode AC benches issue #66 reconciles into the input-common-mode-range and CMRR rows.
- [`spec/decision-records/DR-009-offset-target.md`](decision-records/DR-009-offset-target.md) (issue #108, status `proposed` — not ratified) — the proposed consumer-derived offset target, kept, with the measured N = 300 Monte Carlo gap from [`sim/offset-capability/records/campaign-20261009-offset-mc300.md`](../sim/offset-capability/records/campaign-20261009-offset-mc300.md) (issue #85).
- [`spec/decision-records/DR-008-cmrr-target.md`](decision-records/DR-008-cmrr-target.md) (issue #66, status `proposed` — not ratified) — the proposed numeric CMRR target and its measured basis.

## 5. Ratification status (2026-09-21 pass — issue #26 / DR-003)

As of [`DR-003`](decision-records/DR-003-target-spec-ratification.md), this
table's rows divide as follows — dispositions below are DR-003's, take
effect when the two-key PR carrying that record merges, and are recorded
per row in the record itself. **No row's numeric value changed in
ratification** — DR-003 disposes each row's *status* only:

- **RATIFIED — measured evidence attached (6 §2 rows)**: open-loop DC gain
  (target met at every grid point — worst 69.72 dB @ SS/125 °C, ≥ 9.7 dB
  margin, stretch bound met everywhere), GBW (**not met** by the current
  sizing — worst 8.45 MHz @ SS/125 °C vs. the unchanged ≈ 16 MHz target),
  phase margin (met everywhere — worst 64.09° @ SF/27 °C), slew rate
  (**not met on the falling edge** — worst 1.73 V/µs @ SS/−40 °C, under
  9% of the unchanged ≈ 20 V/µs target, which DR-003 makes explicitly
  both-edge), output swing (**not met** — worst 0.855 Vpp @ SS/−40 °C vs.
  the unchanged ≈ 1.39 Vpp target; that binding-corner prediction itself
  is confirmed), quiescent power (confirmed — 130.71 µW @ the confirmed
  FF/125 °C/1.98 V binding corner, +1.6% vs. the estimate). Evidence:
  [`sim/opamp-characterization/records/20260916-032327-edc9f22.md`](../sim/opamp-characterization/records/20260916-032327-edc9f22.md)
  — full 5-corner × 3-temperature grid, per-row verdicts in that
  experiment's README.
- **RATIFIED — measured evidence attached since ratification (1 §2 row,
  issue #66)**: input common-mode range (≈ 0.888–1.024 V window at the
  worst-case corner). DR-003 ratified it as target-only, because no
  ICMR-specific bench existed (the dc-swing bench measures closed-loop
  compliance, which its own README states is not an ICMR measurement).
  Issue #53's ICMR bench has since measured it: **met at all 15 grid
  points** — narrowest window 0.7168 – 1.1686 V @ SS / −40 °C, 40 dB
  local-CMRR criterion (record
  [`20261009-103006-566b9a5`](../sim/opamp-characterization/records/20261009-103006-566b9a5.md)).
  The ratified target value is unchanged; only the evidence behind it is
  new.
- **RATIFIED — target only, no measured evidence (1 §2 row)**:
  input-referred noise (≈ 30 nV/√Hz thermal floor, band 100 Hz – 1 MHz —
  no noise testbench is committed anywhere in `sim/`, flicker
  uncharacterized). This binds as a target; **no "met" claim is made or
  implied**. (The noise row's reconciliation belongs to issue #54's
  follow-on and is not touched by issue #66.)
- **RATIFIED — operating conditions (all 5 §1 rows)**: 1.8 V ±10% supply;
  the 3.3 V I/O-flavor row stays named-not-opened; −40…+125 °C; the
  confirmed 5-corner `_01v8` MOS grid; CL = 2 pF (carried from DR-001).
  Grading caveats carried from the committed evidence: VDD is tied to
  process corner in the committed grid (not an independent supply sweep
  per corner), and the R+C (resistor/capacitor process) axis is
  "typical" only — both stated methodology choices in that record's
  README, not ratified claims of coverage.
- **OPEN — explicitly, not silently (4 §2 rows)**: input-referred offset,
  CMRR, PSRR (at DR-003 each needed a bench that did not exist yet —
  mismatch Monte Carlo, common-mode AC, supply AC respectively; the offset
  row's `[P]` *statistical basis* — 3σ, MC N≥300 + process corners —
  stays proposed; the MC pass now exists, see below, but T1 item 6's
  signoff status is unchanged), and area (post-layout; no `layout/`
  exists). PSRR and area carry `[TBD]` with one-line reasons at the row,
  tracked under the gap-to-T1 tracker, [#3](https://github.com/2AMLogic/sky130-opamp/issues/3).
  **CMRR now has its bench** (issue #53; worst 55.11 dB @ SS / −40 °C,
  mid-rail common mode) and a numeric target **proposed** by
  [`DR-008`](decision-records/DR-008-cmrr-target.md) (≥ 50 dB, DC – 1 kHz,
  `[P]`, issue #66). It stays OPEN until DR-008's named ratification act:
  a separate, later operator-approved PR that flips DR-008's Status line to
  `ratified` and removes this OPEN note and the one on the CMRR row (see
  DR-008's Status line). Merging the issue #66 PR that introduced DR-008
  does **not** ratify it, unlike the DR-003/DR-005/DR-007 convention. This
  table does not self-ratify it.
  **Offset now has its mismatch Monte Carlo data** (issue #85: N = 300 per
  corner, σ 8.38–8.69 mV at 27 °C / 1.8 V, open-loop; record
  [`campaign-20261009-offset-mc300.md`](../sim/offset-capability/records/campaign-20261009-offset-mc300.md))
  and a numeric target **proposed** by
  [`DR-009`](decision-records/DR-009-offset-target.md) (σ ≤ 0.275 mV, the
  consumer-derived `sky130-bandgap` allocation, `[P]`, issue #108). The
  measurement does **not** meet it (about 23–32× the allocation); the
  target is kept, not relaxed. It stays OPEN until DR-009's named
  ratification act: a separate, later operator-approved PR that flips
  DR-009's Status line to `ratified` and removes this OPEN note and the one
  on the offset row. Merging the issue #108 PR does **not** ratify it.

The six measured row lines above are deliberately untouched by this pass:
their measured-value *citations* are issue #20's reconciliation, whose
PR (#21) is open and blocked as of this writing — its row-text edits and
this pass's ratification dispositions are complementary (citation axis
vs. binding-status axis), and their diffs are disjoint, so the two PRs
compose in either merge order. Consequently the `[P]` tag's "needs an
explicit ratification decision before it binds" clause is now
**discharged for the 13 ratified rows by DR-003 itself**, while the tag
itself keeps marking each value's *provenance* (a sizing-pass proposal),
not its binding status — which is what this section records. The rows
carry their measured citations at the cell since PR #21 (issue #20)
landed.

## Consumers (2am reuse rule 9 — this block's end of the edge)

[`2am/repos.yml`](https://github.com/2AMLogic/2am/blob/main/repos.yml) records
`consumes: [sky130-opamp]` on two fleet repos (read live 2026-09-22):
**sky130-ldo** (`consumes: [sky130-opamp, sky130-bandgap]`) and
**sky130-bandgap** (`consumes: [sky130-opamp]`). Cross-cutting reuse rule 9
([2AMLogic/2am#899](https://github.com/2AMLogic/2am/issues/899), widened
2026-09-21 to same-PDK sub-blocks) makes that dependency edge a recorded
fact on *both* ends — this section is this repo's end. It names each
consumer, the requirement rows it imposes on an amplifier in its position,
and whether this block's ratified §1/§2 rows meet them. **"Unknown" is a
legitimate row value** (the consumer states no explicit requirement for
that axis); unnamed is the only invalid value.

**Verdict stamp.** Every verdict below was evaluated at this repo's
`8b3ec92` (2026-09-22) against the [DR-003](decision-records/DR-003-target-spec-ratification.md)-ratified rows,
with each consumer read at its own pinned commit. Verdicts **will drift**
when the #22 resize lands and when a consumer edits its tree — the pinned
commits in each row are what make that drift detectable rather than silent.
Re-evaluate on either head moving. Exception: the two **Input range**
cells were refreshed by issue #66 (2026-10-09) against the measured ICMR
record `20261009-103006-566b9a5`; their verdicts are unchanged and the
consumers' pinned commits were not re-read.

Findings about a consumer's own block belong on the **consumer's** tracker,
not here: each consumer's adopt-or-record evaluation of this block is
already filed on its own side — [sky130-ldo#123](https://github.com/2AMLogic/sky130-ldo/issues/123)
and [sky130-bandgap#286](https://github.com/2AMLogic/sky130-bandgap/issues/286).
This section carries links out, not their findings. The machine-parseable
integrator view (top cell, ports, netlist/GDS, area, maturity rung) lives at
a fixed path: [`manifests/integrator.json`](../manifests/integrator.json) —
not in this prose.

### sky130-ldo — pinned @ `a0ff95b` (2026-09-22)

Spec of record: [`spec/target-spec.md`](https://github.com/2AMLogic/sky130-ldo/blob/a0ff95b/spec/target-spec.md)
(RATIFIED per its DR-006/#1). The error amplifier is embedded, not
standalone, so most rows below read Unknown — that is the LDO's spec shape,
not a research gap here.

| Requirement row | Consumer's requirement (source @ `a0ff95b`) | This block's verdict (vs §1/§2 @ `8b3ec92`) |
|---|---|---|
| Port list | **Unknown** — the error amplifier is embedded inside `design/ldo_3v3in_1v8out.sch`; no standalone amplifier port contract exists to compare against. | unknown — nothing to meet yet; this block publishes `vdd vss inn inp out ibias` ([netlist](../design/netlist/opamp_core.spice) @ `8b3ec92`). |
| Rails | Error-amp position spans the 3.3 V input rail (2.97–3.63 V) to ground; the whole amplifier/bias/protection chain runs on 5 V-gate `*_g5v0d10v5` devices (ratified framing A, its [DR-001](https://github.com/2AMLogic/sky130-ldo/blob/a0ff95b/spec/decision-records/DR-001-pass-device-supply-framing.md); schematic header comments @ `a0ff95b`). | **not met** — §1's ratified supply row is 1.8 V ±10% on `_01v8` core devices; the 3.3 V I/O flavor is named-not-opened (§1 row — opening it requires its own decision record). Standing decision recorded in [`DR-005`](decision-records/DR-005-io-flavor-not-served.md): this block does not serve a 3.3 V-rail amplifier position. |
| Input range | **Unknown** — the ratified table states no error-amp input common-mode row; the feedback-divider tap voltage is not fixed there. | unknown — nothing to compare against; for reference this block's ICMR row is a ratified target window (≈ 0.888–1.024 V worst-case), now measured as met at every corner: narrowest window 0.7168–1.1686 V @ SS / −40 °C, 40 dB local-CMRR criterion (record [`20261009-103006-566b9a5`](../sim/opamp-characterization/records/20261009-103006-566b9a5.md), issue #53; cell refreshed by issue #66). |
| Speed (GBW/SR) | **Unknown** — no explicit amp GBW/SR row. Nearest imposing rows are loop-level: Stability (PM ≥ 45°, GM ≥ 10 dB over 0–50 mA and the ratified C_out/ESR window) and Load transient (recover to ±1% in ≤ 20 µs). | unknown — and this block's own GBW row is ratified but **not met** by current sizing (worst 8.45 MHz vs the unchanged ≈ 16 MHz target, DR-003), so any future amp-level comparison moves with the #22 resize. |
| Offset | **Unknown** — no explicit amp-offset row. Nearest accuracy rows: Line regulation < 5 mV/V and Load regulation < 1% (18 mV), counted inside the ±2% output window. | unknown — nothing to compare against (no consumer number). For reference, this block's input-referred offset row is OPEN (§2): measured σ 8.38–8.69 mV (N = 300 mismatch MC, 27 °C / 1.8 V, open-loop; record [`campaign-20261009-offset-mc300.md`](../sim/offset-capability/records/campaign-20261009-offset-mc300.md), issue #85), target proposed by `DR-009`. |
| Noise | **Not imposed** — its Output-noise row reads "not specified — waived unless a consumer states a requirement". | n/a — nothing to meet; this block's noise row is ratified as target-only. |
| Area budget | **Unknown** — its ratified Area row (< 0.1 mm² total core, pass FET included) is a whole-LDO budget; no error-amp share is allocated. | unknown — this block's area row is OPEN (no layout exists). |
| Iq / power | **Explicitly open** — "No number set"; its DR-003 declined to set an Iq figure (the ≈ 24.9 µA @ 50 mA loop-gain-sized draw is a data point, not a target); its own [#121](https://github.com/2AMLogic/sky130-ldo/issues/121) tracks ratifying the row. | unknown — no consumer number to compare; for reference this block's ratified quiescent-power row is I_Q = 65 µA (≈ 117.0 µW @ 1.8 V nominal). |

**Not the same block (recorded once, by name).** sky130-ldo's error
amplifier is a single-stage current-mirror ("symmetric") OTA embedded in
`design/ldo_3v3in_1v8out.sch` — its second gain stage is the LDO's
common-source pass device, and a two-stage Miller standalone second-gain-stage
candidate was explicitly screened and rejected during that repo's own #22
(schematic header comments @ `a0ff95b`). This block **is** a two-stage
Miller-compensated standalone OTA. Not a drop-in; that fact is recorded
here so no reader re-derives it.

### sky130-bandgap — pinned @ `4ac0c24` (2026-09-22)

Spec of record: the ratified target-specification table in its
[README](https://github.com/2AMLogic/sky130-bandgap/blob/4ac0c24/README.md)
(DR-005/#1; PSRR row amended by DR-006/#123). Its amplifier is a named
sub-block with a fixed pin list, so more rows below are citable.

| Requirement row | Consumer's requirement (source @ `4ac0c24`) | This block's verdict (vs §1/§2 @ `8b3ec92`) |
|---|---|---|
| Port list | Fixed pin list `VB VA GDRV TAIL VDD VSS` — `design/error_amp.sch`, instantiated by `bandgap_core.sch` as `XAMP`; TAIL is an external current input (the amp has no internal bias network — its tail comes from the core's MPAMP), and AOUT drives the core's PMOS mirror gate GDRV. | **not met (different contract)** — this block publishes `vdd vss inn inp out ibias`: a self-contained cell whose `ibias` is the on-chip diode-connected reference node (DR-002 §(a)), vs the bandgap amp's external-tail-in / gate-drive-out contract. |
| Rails | Supply 3.3 V ±10% (stretch: 1.8 V-core Banba variant); the amp is all 5 V thick-oxide `*_g5v0d10v5` — "no 1.8 V core devices anywhere" per its [DR-001](https://github.com/2AMLogic/sky130-bandgap/blob/4ac0c24/spec/decision-records/DR-001-supply-flavor-scope.md) scope. | **not met** — same shape as the LDO row: this block's ratified rail is 1.8 V ±10% on `_01v8`; the 3.3 V flavor is named-not-opened. Standing decision recorded in [`DR-005`](decision-records/DR-005-io-flavor-not-served.md). |
| Input range | The amp senses the core's nodes at ≈ 0.73 V (one V_EB, which is what forces its PMOS input pair) — fixed by the core (`design/error_amp.sch` header @ `4ac0c24`). | **not met** — this block's ratified ICMR target window ≈ 0.888–1.024 V (worst-case corner) does not include 0.73 V. The measured range is wider than the target and covers 0.73 V at 14 of 15 grid points, but **misses it at FS / −40 °C** (low edge 0.7388 V, 8.8 mV above 0.73 V; 40 dB local-CMRR criterion, record [`20261009-103006-566b9a5`](../sim/opamp-characterization/records/20261009-103006-566b9a5.md), issue #53; cell refreshed by issue #66). Caveat: the ICMR edge is a CMRR-degradation criterion, not a device-saturation one, and the 0.73 V verdict is criterion-sensitive (at 50 dB the FS / −40 °C low edge rises to 0.8009 V). |
| Speed (GBW/SR) | **Unknown** — no amp GBW/SR row. Nearest imposing rows are loop-level: PSRR > 60 dB DC–1 kHz (frequency-qualified, its DR-006) and Startup < 1 ms. | unknown. |
| Offset | Amp input-referred allocation ≈ 0.275–0.369 mV σ (by temperature) — derived as "what is left after the fixed terms" of the output-accuracy row, via the measured Kuijk offset gain of 9.65 ([`design/error-amp-offset-budget.md` §3](https://github.com/2AMLogic/sky130-bandgap/blob/4ac0c24/design/error-amp-offset-budget.md)); its §10 re-derivation against the ratified ±2% row reads MET with 19–21% margin (N = 300 MC). | **not met (measured gap, target proposed)** — this block's input-referred offset row is OPEN (§2) but now has data: σ 8.38–8.69 mV across the five corners (N = 300 mismatch MC per corner, record [`campaign-20261009-offset-mc300.md`](../sim/offset-capability/records/campaign-20261009-offset-mc300.md), issue #85), about 23× to 32× the ≈ 0.275–0.369 mV σ allocation. [`DR-009`](decision-records/DR-009-offset-target.md) proposes the consumer-derived σ ≤ 0.275 mV as the target and keeps it. Caveats: 27 °C / 1.8 V only, ±30 mV bracket, open-loop Vos definition (not the closed-loop offset the bandgap sees); closing lever not identified (issue #107). |
| Noise | **Not imposed** — its ratified table carries no output-noise row. | n/a. |
| Area budget | Ratified Area < 0.08 mm² whole block, drawn MCC cap included (its DR-007); no amp share is allocated. | unknown — this block's area row is OPEN (no layout exists). |
| Iq / power | Ratified Iq < 50 µA, whole block (README table @ `4ac0c24`). | **not met** — this block's ratified quiescent-power row is I_Q = 65 µA (≈ 117.0 µW @ 1.8 V nominal; 130.71 µW measured worst corner): the amplifier alone exceeds the bandgap's whole-block 50 µA budget before the core is counted — and that comparison is the charitable one, taken at 1.8 V rather than the bandgap's 3.3 V rail, where this block is not characterized at all. |

**Not the same block (recorded once, by name).** sky130-bandgap's error
amplifier is a single-stage current-mirror OTA (`design/error_amp.sch` /
`.sym` @ `4ac0c24`: PMOS input pair, external tail, fixed 6-pin contract) —
not a two-stage Miller standalone op-amp. Recorded here so no reader
re-derives it.
