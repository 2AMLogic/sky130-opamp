# Target specification — sky130-opamp

- **Status**: **DRAFT** — engineering input, not yet ratified. No decision
  record exists yet in this repo; ratification is a future issue, once
  gm/ID device-characterization data lands under `sim/`.
- **Date**: 2026-09-06
- **Assembled by**: Loom Builder agent, issue #2 (bootstrap/scaffolding pass)
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
`CLAUDE.md`/`README.md`. Nothing in this pass performs circuit design,
schematic capture, or simulation — every numeric target below is either an
engineering placeholder proposal `[P]` or explicitly `[TBD]` pending sky130
device data that does not exist in this repo yet (`design/`, `sim/`,
`layout/`, and `measurements/` all currently hold only placeholder
`README.md` files, verified against `main` @ `491adc3`, 2026-09-06).

## How to read this table

**Value tags** — every non-definitional value carries one, following
[`gf180-temp-por/spec/target-spec.md`](https://github.com/2AMLogic/gf180-temp-por/blob/main/spec/target-spec.md)'s
convention (already adopted by this block's twin,
[`gf180-opamp/spec/target-spec.md`](https://github.com/2AMLogic/gf180-opamp/blob/main/spec/target-spec.md)),
so a future reviewer can tell a carried decision from a new proposal at a
glance:

| Tag | Meaning |
|---|---|
| **[DR-n]** | Carried unchanged from a decision record `n`. None exist yet in this repo — no row currently carries this tag. |
| **[P]** | **Proposed by this bootstrap pass** — an engineering placeholder with no measured sky130 data behind it yet (e.g. carried from this repo's own `README.md`/`CLAUDE.md` framing, or a structural convention borrowed from a same-PDK sibling's ratified spec). Needs an explicit ratification decision before it binds. |
| **[TBD]** | Deliberately unset — no sky130 device data exists yet to propose even a placeholder number. Filled in once gm/ID device characterization (`sim/`) and PVT-cornered testbenches exist. Tracked collectively under the gap-to-T1 tracker, [#3](https://github.com/2AMLogic/sky130-opamp/issues/3) (item 5, "Full PVT corner simulation vs a ratified spec"), rather than one issue per row. |

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
| Load capacitance, CL | **[TBD]** | GBW/phase-margin targets are stated "into stated CL" per the twin-row convention; no CL has been chosen yet since no application/bench context exists for this standalone op-amp characterization. |

## 2. Performance targets

| Parameter | Target | Stretch | Statistical basis | Binding corner (predicted) | Status |
|---|---|---|---|---|---|
| Open-loop DC gain | **[TBD]** | — | — (deterministic corner-worst-case candidate) | SS / −40 °C (lowest gm, highest output impedance loss) | not started |
| GBW (into stated CL, [TBD] above) | **[TBD]** | — | — | SS / −40 °C / low VDD (slowest devices) | not started |
| Phase margin (at GBW, same CL) | **≥ 60° [P]** | ≥ 45° at the FF/hot corner if 60° is unreachable there | — (deterministic corner-worst-case) | FF / 125 °C (fastest devices, most peaking risk) | not started |
| Slew rate | **[TBD]** | — | — | SS / −40 °C / low VDD (lowest tail-current headroom) | not started |
| Input-referred noise | **[TBD]** — band not yet chosen | — | n/a until a band is set | n/a | not started |
| Input-referred offset | **[TBD]** | — | **3σ, mismatch MC N≥300 + process corners [P]** — matches `sky130-bandgap`'s ratified statistical-basis convention (its output-reference row); sample count not yet re-derived for this topology | to be determined once a topology is drawn — likely SS/FF split-corner pairing on the input differential pair | not started |
| CMRR | **[TBD]** | — | — (deterministic corner-worst-case) | to be determined | not started |
| PSRR | **[TBD]** | — | — (deterministic corner-worst-case) | to be determined | not started |
| Output swing | **[TBD]** — expected to show the low-headroom trade explicitly at 1.8 V, per `README.md` | — | — | low VDD / worst output-stage headroom corner — expected to be the row where 1.8 V-primary headroom cost is most visible relative to the 3.3 V/5 V twins | not started |
| Quiescent power | **[TBD]** | — | — (deterministic corner-worst-case) | FF / 125 °C / 1.98 V (leakage + fastest devices) — matches `sky130-bandgap`'s ratified Iq binding-corner convention | not started |
| Area | **[TBD]** | — | n/a (not a PVT line) | n/a | not started |

Every `[TBD]` row above is deliberately left unset rather than guessed, per
`CLAUDE.md`'s "no claim without a testbench" and per this issue's explicit
scope (scaffolding only, no circuit design or simulation). Filling any of
them requires, at minimum, a topology decision (tracked in
[`porting-plan.md`](porting-plan.md)) and a gm/ID device-characterization
pass committed to `sim/`, per `CLAUDE.md`'s "gm/ID first, committed before
sizing."

## 3. What this table is not

- **Not ratified.** No `spec/decision-records/` directory exists yet in this
  repo. Ratification flows through the two-key mechanism described in
  `CLAUDE.md`/`.loom/CLAUDE.md` (an EE key + a market key, both installed by
  the standard tooling) — a future issue's job, once the `[TBD]` rows above
  have real sky130 device data behind them. Per the generalized 2026-08-28
  ruling cited in issue #2's body ("scope-only spec DRs ratified with both
  keys need no per-PR operator statement"), that applies at ratification
  time, not to this DRAFT — this pass ratifies nothing and is not asking any
  key-holder to act on it.
- **Not a commitment that every `[TBD]` row will end up non-trivial.** Some
  rows (e.g. the corner grid, or the load capacitance) may turn out to be
  determined jointly with a topology decision rather than independently.
- **Not opening the 3.3 V I/O-device-flavor row.** It is named, not scoped
  in.

## 4. Sources

- `CLAUDE.md` (this repo) — the twin-row set, the 1.8 V-primary/3.3 V-I/O
  scope rule, and the gm/ID-first ordering.
- [`gf180-opamp/spec/target-spec.md`](https://github.com/2AMLogic/gf180-opamp/blob/main/spec/target-spec.md) — this block's identical-topology, same-bootstrap-issue twin on GF180MCU; the direct structural model for this file (value-tag convention, row set, "not ratified" framing), verified 2026-09-06.
- [`sky130-bandgap` README](https://github.com/2AMLogic/sky130-bandgap#readme) (see its "Target specification" section, ratified per DR-005/issue #1, PSRR row amended by DR-006/issue #123) — ratified target-spec table shape (Target/Stretch columns), the `3σ, mismatch MC N≥300 + process corners` statistical-basis wording, and the Iq binding-corner convention this table borrows. Note this sibling's own ratified Supply row is 3.3 V, not 1.8 V — its device flavor does not transfer directly to this block's 1.8 V-primary scope (see `porting-plan.md` §2).
- [`sky130-ldo/spec/target-spec.md`](https://github.com/2AMLogic/sky130-ldo/blob/main/spec/target-spec.md) — DRAFT-status target-spec precedent on this same PDK (per-row `Src` citation discipline, explicit "nothing here is ratified" banner, ratification gated on a dedicated issue rather than folded into the bootstrap issue) and [DR-001](https://github.com/2AMLogic/sky130-ldo/blob/main/spec/decision-records/DR-001-pass-device-supply-framing.md) for the `pfet_g5v0d10v5`/`nfet_g5v0d10v5` I/O-flavor-at-3.3V precedent cited above.
- [`klayout-tools/docs/design-evidence-tiers.md`](https://github.com/2AMLogic/klayout-tools/blob/main/docs/design-evidence-tiers.md) — the T1 checklist this spec's eventual evidence trail (`sim/`, `layout/`) will need to satisfy, tracked in the gap-to-T1 tracker, [#3](https://github.com/2AMLogic/sky130-opamp/issues/3).
