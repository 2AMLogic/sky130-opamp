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
- **Assembled by**: Loom Builder agent, issue #2 (bootstrap/scaffolding
  pass); issue #10 (2026-09-15 sizing pass)
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
| **[P]** | **Proposed by this bootstrap pass, by the 2026-09-15 sizing pass (issue #10), or reconciled against the schematic-level device sizing of issue #13 / [`DR-002`](decision-records/DR-002-device-sizing.md) (issue #16)** — an engineering placeholder or sizing estimate with no PVT-cornered testbench evidence behind it yet (e.g. carried from this repo's own `README.md`/`CLAUDE.md` framing, a structural convention borrowed from a same-PDK sibling's ratified spec, a §2 performance target sized from the committed gm/ID device sweep under [`DR-001`](decision-records/DR-001-topology-and-cl.md)'s topology — see [§2a](#2a-sizing-basis-for-the-2026-09-15-pass-illustrative-non-binding) — or a later re-estimate from `DR-002`'s drawn device widths, itself still a hand calculation, not a simulated result). Needs an explicit ratification decision before it binds. |
| **[TBD]** | Deliberately unset — no sky130 device data exists yet to propose even a placeholder number, or the committed gm/ID sweep (bare-device DC characterization only) has no basis for this row (e.g. offset/mismatch, CMRR/PSRR small-signal behavior, area — each has a one-line reason at its row, or in [§2a](#2a-sizing-basis-for-the-2026-09-15-pass-illustrative-non-binding)). Filled in once the relevant device/PVT-cornered testbench evidence exists. Tracked collectively under the gap-to-T1 tracker, [#3](https://github.com/2AMLogic/sky130-opamp/issues/3) (item 5, "Full PVT corner simulation vs a ratified spec"), rather than one issue per row. |

**Status** column values: `not started` (no `sim/` evidence exists for this
row at all — true of every row in this pass). There is no `ratifiable` or
`conditional` row yet, unlike the more mature same-PDK siblings
(`sky130-bandgap`, `sky130-ldo`) this table's shape is borrowed from.

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
| Supply voltage, VDD (I/O-device flavor) | **3.3 V — not opened** [P] | sky130's I/O-tolerant device flavor (`sky130_fd_pr__nfet_g5v0d10v5` / `pfet_g5v0d10v5`, used at 3.3 V per `sky130-ldo`'s [DR-001](https://github.com/2AMLogic/sky130-ldo/blob/main/spec/decision-records/DR-001-pass-device-supply-framing.md) precedent for using this flavor below its full 5.0 V/10.5 V rating). Per `CLAUDE.md`, opening this row requires its own decision record; it is named here only so a future DR has a place to point at, not to imply the row is in scope. Never mixed with 1.8 V core-flavor devices in one variant. |
| Operating temperature | **−40…+125 °C** [P] | Matches the fleet-wide convention (`sky130-bandgap`, `sky130-ldo`) for a commercial-grade PDK part. No sky130-specific device data has been checked against this range yet for this topology — proposed by analogy, not measured. |
| Corner grid | **`tt, ff, ss, sf, fs` (sky130 1.8 V-core MOS process corners) — confirmed [P]** | Same *shape* `sky130-bandgap`'s ratified corner set uses, now confirmed specifically for the `_01v8` (1.8 V-core) device flavor against the pinned PDK checkout, rather than assumed by analogy from that 3.3 V-primary sibling — see [`sim/gm-id-characterization/corners/model-files.json`](../sim/gm-id-characterization/corners/model-files.json) and [`corners/README.md`](../sim/gm-id-characterization/corners/README.md) (issue #6), which resolve each corner to its literal `sky130_fd_pr__{nfet,pfet}_01v8__<corner>.*.spice` model file. Still `[P]`, not ratified — this row's binding-corner predictions and pass/fail behavior are decided independently, once a topology exists (see [`porting-plan.md`](porting-plan.md) §4). |
| Load capacitance, CL | **2 pF [DR-001]** | GBW/phase-margin targets are stated "into stated CL" per the twin-row convention. Chosen in [`DR-001`](decision-records/DR-001-topology-and-cl.md) to match `sg13g2-opamp`'s own `CL` decision for cross-PDK comparability across the three-foundry twin set; `gf180-opamp` has no `CL` decision yet to compare against. |

## 2. Performance targets

| Parameter | Target | Stretch | Statistical basis | Binding corner (predicted) | Status |
|---|---|---|---|---|---|
| Open-loop DC gain | **≥ 60 dB [P]** — sizing estimate ≈ 72.8–75.1 dB across the swept corner grid, from `DR-002` §(f)'s device-level (drawn-width) re-estimate (supersedes §2a's earlier ≈ 62–65 dB estimate, computed before any device width existed — see §2a and `DR-002` §(f) for both derivations) | ≥ 65 dB [P] | — (deterministic corner-worst-case candidate) | SS / −40 °C (lowest gm, highest output impedance loss) — `DR-002` §(f) finds FF / 125 °C trends slightly lower in its own device-level model (72.8 dB vs. 75.1 dB at SS), the same pattern §2a already flagged; left unchanged here as a topology-level prediction pending a simulated corner sweep | not started |
| GBW (into stated CL = 2 pF, per `DR-001`) | **≈ 16 MHz [P]** — self-consistent sizing example (§2a) | — | — | SS / −40 °C / low VDD (slowest devices) | not started |
| Phase margin (at GBW, same CL) | **≥ 60° [P]** | ≥ 45° at the FF/hot corner if 60° is unreachable there | — (deterministic corner-worst-case) | FF / 125 °C (fastest devices, most peaking risk) | not started |
| Slew rate | **≈ 20 V/µs [P]** — self-consistent sizing example (§2a) | — | — | SS / −40 °C / low VDD (lowest tail-current headroom) | not started |
| Input-referred noise | **≈ 30 nV/√Hz thermal floor [P], proposed band 100 Hz – 1 MHz [P]** — flicker (1/f) not characterized by the committed gm/ID sweep (§2a) | — | n/a — deterministic device-noise estimate, not yet mismatch/MC-based | TT / 27 °C (thermal-floor estimate is only weakly corner-dependent under this pass's constant-current-bias assumption — see §2a caveat) | not started |
| Input-referred offset | **[TBD]** — the committed gm/ID sweep is a bare-device DC characterization (gm/ID, gm/gds, fT only) with no Pelgrom/`AVT` mismatch coefficient extraction; a numeric offset target needs either a dedicated mismatch Monte-Carlo pass or PDK mismatch-model data, neither in scope for this issue (§2a) | — | **3σ, mismatch MC N≥300 + process corners [P]** — matches `sky130-bandgap`'s ratified statistical-basis convention (its output-reference row); sample count not yet re-derived for this topology | to be determined once a topology is drawn — likely SS/FF split-corner pairing on the input differential pair | not started |
| CMRR | **[TBD]** — CMRR is set by the first stage's common-mode-to-differential conversion (tail-current-source and mirror-asymmetry small-signal behavior), which the committed gm/ID sweep's single-device DC operating points do not characterize; needs a common-mode AC testbench, not yet built (§2a) | — | — (deterministic corner-worst-case) | to be determined | not started |
| PSRR | **[TBD]** — PSRR is a supply-to-output small-signal transfer function (through the compensation network and bias generator); the committed gm/ID sweep has no supply-voltage sweep axis at all (confirmed in `sim/gm-id-characterization/README.md`: "No supply-voltage axis is swept ... there is no 'supply corner' for a two-terminal-bias bare-device sweep"), so there is no device-level basis to size this row from yet (§2a) | — | — (deterministic corner-worst-case) | to be determined | not started |
| Input common-mode range | **≈ 0.888 – 1.024 V (≈ 136 mV window) at the worst-case corner [P]** — sizing estimate from `DR-002` §(f)/§(d), computed from the drawn input-pair and PMOS-mirror `Vov`/`Vth` at that corner. No `[TBD]`-to-`[P]` history for this row: it did not exist before this issue, because no device widths existed to size it from until `DR-002` (issue #13). The window sits *above* mid-rail (0.81 V) rather than spanning it, and is markedly narrower than the twins' topology would suggest — `DR-002` traces this to `DR-001`'s NMOS-input-pair / PMOS-mirror choice meeting sky130's PMOS threshold magnitude (`Vth_p` = 1.1065 V at `ss / −40 °C`), which alone would cap the window near ≈ 0.29 V even at zero PMOS-mirror overdrive. This is left as a recorded finding, not a design decision: `DR-002`'s own "Alternatives considered" names the knob to turn if it binds (biasing the PMOS group at `gm/ID = 12.5 V⁻¹` instead of 10, for ≈ 189 mV of window at ≈ 76 dB gain), but states — and this issue does not override that — that the choice between the current sizing and that alternative belongs against a *simulated* phase margin and common-mode sweep, not another hand calculation. If a future PVT-cornered bench confirms the window does not cover this block's intended input range, reopening `DR-001`'s input-pair polarity requires a **new** decision record superseding `DR-001`, per `DR-001`'s own superseding-record rule — not a silent edit to `DR-001` or to this row | — | — (deterministic corner-worst-case) | SS / −40 °C / VDD = 1.62 V (the PMOS mirror's threshold magnitude `Vth_p` and the NMOS current-source `Vov` both bind hardest at this corner) | not started |
| Output swing | **≈ 0.072 – 1.464 V (≈ 1.39 Vpp, ≈ 86% of the 1.62 V worst-case-low rail) [P]** — sizing estimate from `DR-002` §(f)'s device-level (drawn-width) `Vov` headroom at the worst-case-low rail (SS / −40 °C / 1.62 V), superseding §2a's earlier ≈ 0.17–1.45 V estimate, computed before any device width existed — see §2a and `DR-002` §(f) for both derivations | — | — | low VDD / worst output-stage headroom corner — expected to be the row where 1.8 V-primary headroom cost is most visible relative to the 3.3 V/5 V twins | not started |
| Quiescent power | **≈ 128.7 µW at the stated binding corner (1.98 V); ≈ 117.0 µW at nominal 1.8 V [P]** — sizing estimate from `DR-002` §(f)/§(a): `I_Q = 65 µA`, comprising the two signal branches §2a already counted (`I_SS = 10 µA + ID2 = 50 µA = 60 µA`) plus a 5 µA diode-connected on-chip bias-reference branch (`MB1`) that `DR-002` §(a) commits, needed for a self-contained cell (not treated as off-cell/shared). Supersedes §2a's earlier ≈ 119 µW / `I_Q = 60 µA` estimate, which did not count the reference branch — ≈ 8% above the published figure, a real deviation from headroom, not rounding | — | — (deterministic corner-worst-case) | FF / 125 °C / 1.98 V (leakage + fastest devices) — matches `sky130-bandgap`'s ratified Iq binding-corner convention | not started |
| Area | **[TBD]** — no `layout/` exists yet (holds only a placeholder `README.md`); area has no gm/ID-derived basis at all — it is a post-layout quantity, not a circuit-sizing one, and is not proposed here even as a placeholder | — | n/a (not a PVT line) | n/a | not started |

Every row above now carries either a `[P]` sizing estimate (this pass,
issue #10, sized from the committed gm/ID device sweep under `DR-001`'s
topology — see §2a immediately below for the shared assumptions and
per-row derivation) or an explicit `[TBD]` with a one-line reason it
cannot yet be filled from that data (offset, CMRR, PSRR, area). None of
these `[P]` values is measured or simulated — `CLAUDE.md`'s "no claim
without a testbench" applies to any future *pass/fail* verdict on these
rows, not to this pass's sizing estimates, which are explicitly flagged as
such throughout. Filling the remaining `[TBD]` rows, and confirming any
`[P]` sizing estimate, requires a schematic (`design/`) and PVT-cornered
testbenches (tracked in [`porting-plan.md`](porting-plan.md) and the
gap-to-T1 tracker, [#3](https://github.com/2AMLogic/sky130-opamp/issues/3)).

## 2a. Sizing basis for the 2026-09-15 pass (illustrative, non-binding)

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

**Rows left `[TBD]`.** Offset, CMRR, PSRR, and area each have a one-line
reason directly in their table cell above; none is a gm/ID-derivable
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
  estimate (§2a); offset, CMRR, PSRR, and area remain `[TBD]`, each with a
  stated reason at its row.
- **Not opening the 3.3 V I/O-device-flavor row.** It is named, not scoped
  in.
- **Not a schematic, layout, or simulation pass.** This 2026-09-15 sizing
  pass (issue #10) adds no files under `design/`, `layout/`, or
  `measurements/`, and runs no new simulation — every `[P]` value in §2 is
  a sizing estimate computed from the already-committed gm/ID device sweep
  and `DR-001`'s structural ratios (§2a), not a measured or simulated
  result.

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
- `sim/opamp-characterization/records/20260916-032327-edc9f22.md` (issue #17 / PR #19) — the measured, PVT-cornered circuit-level evidence (full 5-corner × 3-temperature grid) behind six §2 rows' DR-003 dispositions, and — via issue #20's still-open PR #21 — the pending cell-text reconciliation of those six rows.

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
- **RATIFIED — target only, no measured evidence (2 §2 rows)**:
  input-referred noise (≈ 30 nV/√Hz thermal floor, band 100 Hz – 1 MHz —
  no noise testbench is committed anywhere in `sim/`, flicker
  uncharacterized), input common-mode range (≈ 0.888–1.024 V window at
  the worst-case corner — no ICMR-specific bench; the committed dc-swing
  bench measures closed-loop compliance, which its own README states is
  not an ICMR measurement). These bind as targets; **no "met" claim is
  made or implied**.
- **RATIFIED — operating conditions (all 5 §1 rows)**: 1.8 V ±10% supply;
  the 3.3 V I/O-flavor row stays named-not-opened; −40…+125 °C; the
  confirmed 5-corner `_01v8` MOS grid; CL = 2 pF (carried from DR-001).
  Grading caveats carried from the committed evidence: VDD is tied to
  process corner in the committed grid (not an independent supply sweep
  per corner), and the R+C (resistor/capacitor process) axis is
  "typical" only — both stated methodology choices in that record's
  README, not ratified claims of coverage.
- **OPEN — explicitly, not silently (4 §2 rows)**: input-referred offset,
  CMRR, PSRR (each needs a bench that does not exist yet — mismatch
  Monte Carlo, common-mode AC, supply AC respectively; the offset row's
  `[P]` *statistical basis* — 3σ, MC N≥300 + process corners — likewise
  stays proposed until that MC pass exists, and is what gap-to-T1
  tracker item 6 gates), and area (post-layout; no `layout/` exists).
  These rows carry `[TBD]` with one-line reasons at the row, tracked
  under the gap-to-T1 tracker, [#3](https://github.com/2AMLogic/sky130-opamp/issues/3).

The six measured row lines above are deliberately untouched by this pass:
their measured-value *citations* are issue #20's reconciliation, whose
PR (#21) is open and blocked as of this writing — its row-text edits and
this pass's ratification dispositions are complementary (citation axis
vs. binding-status axis), and their diffs are disjoint, so the two PRs
compose in either merge order. Consequently the `[P]` tag's "needs an
explicit ratification decision before it binds" clause is now
**discharged for the 13 ratified rows by DR-003 itself**, while the tag
itself keeps marking each value's *provenance* (a sizing-pass proposal),
not its binding status — which is what this section records. Rows will
carry their measured citations at the cell once PR #21 lands.

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
Re-evaluate on either head moving.

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
| Rails | Error-amp position spans the 3.3 V input rail (2.97–3.63 V) to ground; the whole amplifier/bias/protection chain runs on 5 V-gate `*_g5v0d10v5` devices (ratified framing A, its [DR-001](https://github.com/2AMLogic/sky130-ldo/blob/a0ff95b/spec/decision-records/DR-001-pass-device-supply-framing.md); schematic header comments @ `a0ff95b`). | **not met** — §1's ratified supply row is 1.8 V ±10% on `_01v8` core devices; the 3.3 V I/O flavor is named-not-opened (§1 row — opening it requires its own decision record). |
| Input range | **Unknown** — the ratified table states no error-amp input common-mode row; the feedback-divider tap voltage is not fixed there. | unknown — this block's ICMR row is a ratified target window (≈ 0.888–1.024 V worst-case) with no measured bench. |
| Speed (GBW/SR) | **Unknown** — no explicit amp GBW/SR row. Nearest imposing rows are loop-level: Stability (PM ≥ 45°, GM ≥ 10 dB over 0–50 mA and the ratified C_out/ESR window) and Load transient (recover to ±1% in ≤ 20 µs). | unknown — and this block's own GBW row is ratified but **not met** by current sizing (worst 8.45 MHz vs the unchanged ≈ 16 MHz target, DR-003), so any future amp-level comparison moves with the #22 resize. |
| Offset | **Unknown** — no explicit amp-offset row. Nearest accuracy rows: Line regulation < 5 mV/V and Load regulation < 1% (18 mV), counted inside the ±2% output window. | unknown — this block's input-referred offset row is OPEN (§2; no mismatch MC pass exists). |
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
| Rails | Supply 3.3 V ±10% (stretch: 1.8 V-core Banba variant); the amp is all 5 V thick-oxide `*_g5v0d10v5` — "no 1.8 V core devices anywhere" per its [DR-001](https://github.com/2AMLogic/sky130-bandgap/blob/4ac0c24/spec/decision-records/DR-001-supply-flavor-scope.md) scope. | **not met** — same shape as the LDO row: this block's ratified rail is 1.8 V ±10% on `_01v8`; the 3.3 V flavor is named-not-opened. |
| Input range | The amp senses the core's nodes at ≈ 0.73 V (one V_EB, which is what forces its PMOS input pair) — fixed by the core (`design/error_amp.sch` header @ `4ac0c24`). | **not met** — this block's ratified ICMR target window ≈ 0.888–1.024 V (worst-case corner) does not include 0.73 V. Caveat: DR-003 ratified that window as target-only (no measured ICMR bench exists). |
| Speed (GBW/SR) | **Unknown** — no amp GBW/SR row. Nearest imposing rows are loop-level: PSRR > 60 dB DC–1 kHz (frequency-qualified, its DR-006) and Startup < 1 ms. | unknown. |
| Offset | Amp input-referred allocation ≈ 0.275–0.369 mV σ (by temperature) — derived as "what is left after the fixed terms" of the output-accuracy row, via the measured Kuijk offset gain of 9.65 ([`design/error-amp-offset-budget.md` §3](https://github.com/2AMLogic/sky130-bandgap/blob/4ac0c24/design/error-amp-offset-budget.md)); its §10 re-derivation against the ratified ±2% row reads MET with 19–21% margin (N = 300 MC). | **unknown** — this block's input-referred offset row is OPEN (§2 [TBD]; no mismatch MC pass — gap-to-T1 item 6), so no number exists on this side to compare against ≈ 0.3 mV σ. |
| Noise | **Not imposed** — its ratified table carries no output-noise row. | n/a. |
| Area budget | Ratified Area < 0.08 mm² whole block, drawn MCC cap included (its DR-007); no amp share is allocated. | unknown — this block's area row is OPEN (no layout exists). |
| Iq / power | Ratified Iq < 50 µA, whole block (README table @ `4ac0c24`). | **not met** — this block's ratified quiescent-power row is I_Q = 65 µA (≈ 117.0 µW @ 1.8 V nominal; 130.71 µW measured worst corner): the amplifier alone exceeds the bandgap's whole-block 50 µA budget before the core is counted — and that comparison is the charitable one, taken at 1.8 V rather than the bandgap's 3.3 V rail, where this block is not characterized at all. |

**Not the same block (recorded once, by name).** sky130-bandgap's error
amplifier is a single-stage current-mirror OTA (`design/error_amp.sch` /
`.sym` @ `4ac0c24`: PMOS input pair, external tail, fixed 6-pin contract) —
not a two-stage Miller standalone op-amp. Recorded here so no reader
re-derives it.
