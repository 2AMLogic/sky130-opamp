# Target specification — sky130-opamp

- **Status**: **DRAFT** — engineering input, not yet ratified. One decision
  record exists in this repo,
  [`DR-001-topology-and-cl.md`](decision-records/DR-001-topology-and-cl.md)
  (status `submitted for ratification`, via the PR that lands this pass —
  see below), covering the two-stage topology's input-pair polarity,
  first-stage load, output-stage class, compensation scheme, and the `CL`
  row below; ratification of this table as a whole is a separate, future
  issue.
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
  device sizing, and does **not** ratify the `Status` field above (stays
  `DRAFT`) — see each row below and the note following §2's table.
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
swing, quiescent power) now carry `measured`; every other row remains `not
started`. There is still no `ratifiable` or `conditional` row, unlike the
more mature same-PDK siblings (`sky130-bandgap`, `sky130-ldo`) this table's
shape is borrowed from — `measured` is **not** a synonym for `ratifiable`:
it states only that PVT-cornered testbench evidence now backs the row's
cited number, not that the row (or this table's overall `Status: DRAFT`
above) is ready for a ratification decision.

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
| Open-loop DC gain | **≥ 60 dB [P]** — met at every measured corner, ≥ 9.7 dB of margin. Measured worst-case **69.72 dB @ SS / 125 °C** (`sim/opamp-characterization` record [`20260916-032327-edc9f22`](../sim/opamp-characterization/records/20260916-032327-edc9f22.md), "Results by row" → Open-loop DC gain), vs. `DR-002` §(f)'s ≈ 72.8–75.1 dB sizing estimate across its three named corners (supersedes §2a's earlier ≈ 62–65 dB estimate, computed before any device width existed) — every named `DR-002` point measures 0.5–3.7 dB below its hand estimate (FF / 125 °C is the closest at ≈0.5 dB, SS / −40 °C the furthest at ≈3.6 dB) | ≥ 65 dB [P] | — (deterministic corner-worst-case candidate) | **SS / 125 °C (measured worst-case)** — contradicts this row's own prior prediction of SS / −40 °C: the measured sweep confirms SS as the worst *process* corner as predicted, but finds the worst *temperature* within it is 125 °C, not −40 °C (SS / −40 °C measures 71.43 dB, 1.7 dB better than SS / 125 °C) — gain falls monotonically with increasing temperature at every corner, a direction the hand model did not predict. Full 15-point grid at the cited record | **measured** — `sim/opamp-characterization` record `20260916-032327-edc9f22` (issue #17 / PR #19); not yet ratified |
| GBW (into stated CL = 2 pF, per `DR-001`) | **≈ 16 MHz [P]** — self-consistent sizing example (§2a). **Not met by the current sizing**: measured worst-case **8.45 MHz @ SS / 125 °C, only ≈53% of target** (`sim/opamp-characterization` record [`20260916-032327-edc9f22`](../sim/opamp-characterization/records/20260916-032327-edc9f22.md), "Results by row" → GBW). Even the row's own predicted-binding-corner point, SS / −40 °C, measures **9.56 MHz (≈60% of target, ≈53% of `DR-002` §(f)'s 17.94 MHz hand estimate at that exact point)** — not a rounding-level miss. Per `CLAUDE.md` the target is **not** lowered to match this measurement; see the note following this table | — | — | **SS / 125 °C (measured worst-case)** — contradicts this row's own prior prediction of SS / −40 °C / low VDD: SS is confirmed as the slowest *process* corner as predicted, but GBW falls with *increasing* temperature at every corner (same direction as the gain row) — a qualitative reversal of `DR-002` §(f)'s bare-device model, which had predicted SS / −40 °C to be the *fastest* of its three named points. Full 15-point grid at the cited record | **measured, target not met at the cited corner** — `sim/opamp-characterization` record `20260916-032327-edc9f22` (issue #17 / PR #19); the current `DR-002` sizing does not close this gap — see the note following this table |
| Phase margin (at GBW, same CL) | **≥ 60° [P]** — **confirmed**: measured worst-case **64.09° @ SF / 27 °C**, ≥ 4° of margin at every measured corner (`sim/opamp-characterization` record [`20260916-032327-edc9f22`](../sim/opamp-characterization/records/20260916-032327-edc9f22.md), "Results by row" → Phase margin); `DR-002` never computed phase margin directly (only the `p2/GBW ≈ 2.5` proxy ratio), whose qualitative prediction of a comfortable margin above 60° holds | ≥ 45° at the FF/hot corner if 60° is unreachable there — not exercised; target met at every measured corner | — (deterministic corner-worst-case) | **SF / 27 °C (measured worst-case)** — updates this row's prior prediction of FF / 125 °C: FF / 125 °C measures 65.98°, close to the true worst but not it; SF (slow-NMOS/fast-PMOS), essentially flat across temperature (64.10–64.18°), is the actual worst process corner, ≈1.9° below FF / 125 °C. Full 15-point grid at the cited record | **measured** — `sim/opamp-characterization` record `20260916-032327-edc9f22` (issue #17 / PR #19); not yet ratified |
| Slew rate | **≈ 20 V/µs [P]** — self-consistent sizing example (§2a), assumed rise/fall-symmetric (`SR = I_SS/Cc`), an assumption `DR-002` never stated explicitly but its single-number formula implies. **Rise SR is close to target**: measured worst-case **16.88 V/µs @ SS / 125 °C (≈84% of target)**. **Fall SR is not met by the current sizing, and badly**: measured worst-case **1.73 V/µs @ SS / −40 °C — under 9% of target**, and under 9% of the rise SR at that same point (17.26 V/µs) — `sim/opamp-characterization` record [`20260916-032327-edc9f22`](../sim/opamp-characterization/records/20260916-032327-edc9f22.md), "Results by row" → Slew rate. Per `CLAUDE.md` the target is **not** lowered to match this measurement; see the note following this table | — | — | **SS / 125 °C for rise SR (measured worst-case); SS / −40 °C for fall SR (measured worst-case — matches this row's own prior prediction)** — the qualitative hypothesis (not confirmed by a dedicated bench, out of scope for this reconciliation) is that `M7`'s fixed, non-signal-modulated bias current sets an independent, corner-sensitive ceiling on the falling edge, unlike the rising edge where `M6`'s gate is the signal path. Full 15-point grid at the cited record | **measured, target not met (fall SR) at the cited corner** — `sim/opamp-characterization` record `20260916-032327-edc9f22` (issue #17 / PR #19); the current `DR-002` sizing does not close this gap — see the note following this table |
| Input-referred noise | **≈ 30 nV/√Hz thermal floor [P], proposed band 100 Hz – 1 MHz [P]** — flicker (1/f) not characterized by the committed gm/ID sweep (§2a) | — | n/a — deterministic device-noise estimate, not yet mismatch/MC-based | TT / 27 °C (thermal-floor estimate is only weakly corner-dependent under this pass's constant-current-bias assumption — see §2a caveat) | not started |
| Input-referred offset | **[TBD]** — the committed gm/ID sweep is a bare-device DC characterization (gm/ID, gm/gds, fT only) with no Pelgrom/`AVT` mismatch coefficient extraction; a numeric offset target needs either a dedicated mismatch Monte-Carlo pass or PDK mismatch-model data, neither in scope for this issue (§2a) | — | **3σ, mismatch MC N≥300 + process corners [P]** — matches `sky130-bandgap`'s ratified statistical-basis convention (its output-reference row); sample count not yet re-derived for this topology | to be determined once a topology is drawn — likely SS/FF split-corner pairing on the input differential pair | not started |
| CMRR | **[TBD]** — CMRR is set by the first stage's common-mode-to-differential conversion (tail-current-source and mirror-asymmetry small-signal behavior), which the committed gm/ID sweep's single-device DC operating points do not characterize; needs a common-mode AC testbench, not yet built (§2a) | — | — (deterministic corner-worst-case) | to be determined | not started |
| PSRR | **[TBD]** — PSRR is a supply-to-output small-signal transfer function (through the compensation network and bias generator); the committed gm/ID sweep has no supply-voltage sweep axis at all (confirmed in `sim/gm-id-characterization/README.md`: "No supply-voltage axis is swept ... there is no 'supply corner' for a two-terminal-bias bare-device sweep"), so there is no device-level basis to size this row from yet (§2a) | — | — (deterministic corner-worst-case) | to be determined | not started |
| Input common-mode range | **≈ 0.888 – 1.024 V (≈ 136 mV window) at the worst-case corner [P]** — sizing estimate from `DR-002` §(f)/§(d), computed from the drawn input-pair and PMOS-mirror `Vov`/`Vth` at that corner. No `[TBD]`-to-`[P]` history for this row: it did not exist before this issue, because no device widths existed to size it from until `DR-002` (issue #13). The window sits *above* mid-rail (0.81 V) rather than spanning it, and is markedly narrower than the twins' topology would suggest — `DR-002` traces this to `DR-001`'s NMOS-input-pair / PMOS-mirror choice meeting sky130's PMOS threshold magnitude (`Vth_p` = 1.1065 V at `ss / −40 °C`), which alone would cap the window near ≈ 0.29 V even at zero PMOS-mirror overdrive. This is left as a recorded finding, not a design decision: `DR-002`'s own "Alternatives considered" names the knob to turn if it binds (biasing the PMOS group at `gm/ID = 12.5 V⁻¹` instead of 10, for ≈ 189 mV of window at ≈ 76 dB gain), but states — and this issue does not override that — that the choice between the current sizing and that alternative belongs against a *simulated* phase margin and common-mode sweep, not another hand calculation. If a future PVT-cornered bench confirms the window does not cover this block's intended input range, reopening `DR-001`'s input-pair polarity requires a **new** decision record superseding `DR-001`, per `DR-001`'s own superseding-record rule — not a silent edit to `DR-001` or to this row | — | — (deterministic corner-worst-case) | SS / −40 °C / VDD = 1.62 V (the PMOS mirror's threshold magnitude `Vth_p` and the NMOS current-source `Vov` both bind hardest at this corner) | not started |
| Output swing | **≈ 0.072 – 1.464 V (≈ 1.39 Vpp, ≈ 86% of the 1.62 V worst-case-low rail) [P]** — sizing estimate from `DR-002` §(f)'s device-level (drawn-width) `Vov` headroom at the worst-case-low rail (SS / −40 °C / 1.62 V), superseding §2a's earlier ≈ 0.17–1.45 V estimate, computed before any device width existed. **Not met by the current sizing**: the unity-buffer DC-swing bench measures **0.328 – 1.184 V (0.855 Vpp, 52.8% of the 1.62 V rail) at that same corner (SS / −40 °C)**, only **62% of the `DR-002` estimate's peak-to-peak magnitude** (`sim/opamp-characterization` record [`20260916-032327-edc9f22`](../sim/opamp-characterization/records/20260916-032327-edc9f22.md), "Results by row" → Output swing). Per `CLAUDE.md` the target is **not** lowered to match this measurement; see the note following this table | — | — | **SS / −40 °C / low VDD (measured worst-case — confirms this row's own prior prediction)**: swing widens monotonically with increasing temperature at every process corner, the same direction as the gain/GBW rows, so cold is the binding condition throughout this experiment, not just here — expected to be the row where 1.8 V-primary headroom cost is most visible relative to the 3.3 V/5 V twins. Full 15-point grid at the cited record | **measured, target not met at the cited corner** — `sim/opamp-characterization` record `20260916-032327-edc9f22` (issue #17 / PR #19); the current `DR-002` sizing does not close this gap — see the note following this table |
| Quiescent power | **≈ 128.7 µW at the stated binding corner (1.98 V); ≈ 117.0 µW at nominal 1.8 V [P]** — **confirmed**: measured **130.71 µW @ FF / 125 °C / 1.98 V (+1.6% vs. the `DR-002` estimate)** and **116.27 µW @ TT / 27 °C (nominal, within 0.6%)** (`sim/opamp-characterization` record [`20260916-032327-edc9f22`](../sim/opamp-characterization/records/20260916-032327-edc9f22.md), "Results by row" → Quiescent power) — both the binding corner and the magnitude confirm the `DR-002` §(f)/§(a) hand estimate (`I_Q = 65 µA`: `I_SS = 10 µA + ID2 = 50 µA` signal branches + 5 µA diode-connected on-chip bias-reference branch `MB1`, per `DR-002` §(a)); measured `Iq` ranges 59.67–66.01 µA across the full 15-point grid | — | — (deterministic corner-worst-case) | **FF / 125 °C / 1.98 V (measured worst-case — confirms this row's own prior prediction)** — matches `sky130-bandgap`'s ratified Iq binding-corner convention. Full 15-point grid at the cited record | **measured** — `sim/opamp-characterization` record `20260916-032327-edc9f22` (issue #17 / PR #19); not yet ratified |
| Area | **[TBD]** — no `layout/` exists yet (holds only a placeholder `README.md`); area has no gm/ID-derived basis at all — it is a post-layout quantity, not a circuit-sizing one, and is not proposed here even as a placeholder | — | n/a (not a PVT line) | n/a | not started |

Every row above now carries either a `[P]` sizing estimate (issue #10,
sized from the committed gm/ID device sweep under `DR-001`'s topology —
see §2a immediately below for the shared assumptions and per-row
derivation), an explicit `[TBD]` with a one-line reason it cannot yet be
filled from that data (offset, CMRR, PSRR, area), or — for the six rows
below — a `[P]` value now reconciled against measured PVT-cornered
circuit-level evidence (issue #20, from `sim/opamp-characterization`,
issue #17 / PR #19).

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
**not** ratify this table's `Status: DRAFT` banner (top of file) or any
individual row — `measured` (see "How to read this table" above) states
only that PVT-cornered evidence now exists, not that a row is ready for a
ratification decision.

None of the remaining `[TBD]` rows (offset, CMRR, PSRR, area, and the
separately-estimated input-common-mode-range `[P]` row) is affected by
this reconciliation — the three testbench types `sim/opamp-characterization`
introduces (open-loop AC, unity-buffer slew-rate transient, unity-buffer
DC-swing) do not characterize any of them; each still needs the testbench
type named at its own row. Filling those rows, and closing the four
contradicted rows' gap to target, requires the testbenches named at each
row (tracked in [`porting-plan.md`](porting-plan.md) and the gap-to-T1
tracker, [#3](https://github.com/2AMLogic/sky130-opamp/issues/3)).

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
  also does not ratify this table's `Status: DRAFT` banner or promote any
  row past `measured` (see "How to read this table").

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
- [`sim/opamp-characterization/records/20260916-032327-edc9f22.md`](../sim/opamp-characterization/records/20260916-032327-edc9f22.md) / `.json` and [`sim/opamp-characterization/README.md`](../sim/opamp-characterization/README.md) (issue #17 / PR #19) — the PVT-cornered, circuit-level measured evidence (open-loop AC, slew-rate transient, DC-swing testbenches against `design/netlist/opamp_core.spice`) this issue (#20) reconciles into the six `[P]`-tagged §2 performance rows (open-loop DC gain, GBW, phase margin, slew rate, output swing, quiescent power), confirming two and contradicting four against `DR-002`'s hand estimates.
