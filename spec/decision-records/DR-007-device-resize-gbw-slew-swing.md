# DR-007: Device resize — closing the GBW / fall-slew-rate / output-swing gaps

- **Status**: **proposed** — drafted by the Builder agent (issue #22), and,
  unlike DR-002 at its own drafting, **validated by circuit-level PVT
  simulation**: every number in "Decision" below is the sizing this record
  proposes *and* the sizing the full 5-corner × 3-temperature grid of
  `sim/opamp-characterization/records/20261001-074923-c317ff9` (a re-run of
  issue #17's bench against this resize) actually measured. Per the
  2026-08-19 canary spec/DR ratification-via-PR standing policy
  ([2AMLogic/2am#357](https://github.com/2AMLogic/2am/issues/357)), the
  ratification act is the approval of the PR that carries this record.
- **Date**: 2026-10-01
- **Decided by**: Loom Builder agent, issue #22
- **Supersedes**: [`DR-002`](DR-002-device-sizing.md)'s device sizing
  (widths, the PMOS group's channel length, and `Rz`) — per DR-002's own
  superseding-record convention, DR-002 is **not** edited in place. DR-002's
  *structure* (matched-length groups, count-based mirror ratios, unit-device
  convention) is carried forward unchanged; only the numeric sizing inside
  that structure changes. This record changes **no ratified spec target** —
  per `CLAUDE.md`, the `≈ 16 MHz`, `≈ 20 V/µs`, and `≈ 1.39 Vpp` targets
  stay exactly as DR-003 ratified them.
- **Related**: [`DR-002`](DR-002-device-sizing.md) (the sizing superseded),
  [`DR-003`](DR-003-target-spec-ratification.md) (the un-lowered targets this
  resize is the compliance path for), issue #22 (this resize),
  #17 / PR #19 (the PVT bench), #20 / PR #21 (the reconciliation that
  established the three gaps), #13 (the schematic / DR-002's sizing),
  `sim/opamp-characterization/records/20260916-032327-edc9f22` (the
  pre-resize baseline record this record's measurements are compared
  against, point by point)

## Context

Issue #20's reconciliation (PR #21) established, from measured PVT evidence,
that three of §2's six `[P]` performance rows are **not met** by DR-002's
sizing: GBW (worst 8.45 MHz @ SS/125 °C, ≈53 % of the ≈16 MHz target), fall
slew rate (worst 1.73 V/µs @ SS/−40 °C, under 9 % of the ≈20 V/µs target),
and output swing (0.855 Vpp @ SS/−40 °C, 62 % of DR-002's own ≈1.39 Vpp
estimate at that corner). Issue #22 is the resize pass scoped to close some
or all of those gaps — with an honest partial close as an explicitly
acceptable outcome, and with a measured refutation of the standing
fall-slew-rate hypothesis (README: `M7`'s fixed bias) equally acceptable.

Before resizing, the fall-slew mechanism was **diagnosed directly** with an
instrumented transient run of the committed ss/−40 °C bench deck (the
`.meas` reproduces the record's 1.73 V/µs exactly). During the falling edge
the input pair's differential overdrive (`inn − inp` ≈ 0.65 V) drags the
tail node to **3.6 mV** — `M5` leaves saturation and collapses into deep
triode, the first-stage/mirror current available to pull `d2` up collapses
to a crawl (the `Rz` drop during the crawl is ≈1 mV → ≈0.5 µA through the
Miller path), `M6` never turns off, and the output creeps down through the
M6/M7 current imbalance. So the ceiling is **the tail source's triode-region
current** (`M5`), not `M7`'s sink magnitude itself: the README's qualitative
hypothesis ("the fixed, non-signal-modulated bias") is confirmed in
substance, but the device to resize is the tail/mirror group, and the
mechanism is current *starvation* of the first stage, not an insufficient
`I_D7`. This diagnosis — a measured finding, with node waveforms — is one
of this record's deliverables.

## Decision

### (a) New sizing (gm/ID-first, from the same committed sweep as DR-002)

Every width is interpolated at `tt / 27 °C` from
[`sim/gm-id-characterization/records/20260909-062847-35a9d46-full-sweep.csv`](../../sim/gm-id-characterization/records/20260909-062847-35a9d46-full-sweep.csv)
exactly as DR-002 §(c) did (same interpolation `design/bin/sizing_check.py`
validates). Design points move as follows; **all bias currents, `Cc`, every
mirror ratio, and the unit-device/count conventions are unchanged** from
DR-002:

| Device | Type | `W`/unit (µm) | `L` (µm) | `m` | `gm/ID` design | DR-002 had |
|---|---|---|---|---|---|---|
| `M1`, `M2` | nfet_01v8 | **6.030** | 1.2 | 1 | **17 V⁻¹** | 1.325, gm/ID 10 |
| `M3`, `M4` | pfet_01v8 | **4.634** | **0.3** | 1 | **14 V⁻¹** | 2.745, L 0.6, gm/ID 10 |
| `M6` | pfet_01v8 | **4.634** | **0.3** | 10 | **14 V⁻¹** | 2.745, L 0.6, gm/ID 10 |
| `MB1` | nfet_01v8 | **7.819** | 1.2 | 1 | **18 V⁻¹** | 3.835, gm/ID 15 |
| `M5` | nfet_01v8 | **7.819** | 1.2 | 2 | **18 V⁻¹** | 3.835, gm/ID 15 |
| `M7` | nfet_01v8 | **7.819** | 1.2 | 10 | **18 V⁻¹** | 3.835, gm/ID 15 |
| `Rz` | res_high_po_1p41 | 1.41 (fixed) | **9.763** | 1 | — | L 7.585 (2.00 kΩ) |
| `Cc` | cap_mim_m3_1 | 15.62 | 15.62 | 1 | — | unchanged (0.4998 pF) |

Literal source rows (full sweep, `tt / 27 °C`, `W = 2.0 µm`, `|Vds| = 0.9 V`),
with the same interpolation DR-002 quotes literally:

- **`M1`/`M2` — nfet, `L = 1.2`, gm/ID = 17, 5 µA**: lines 945/944 give
  `gm/ID = 16.283537` at `J = 0.975016 µA/µm` and `gm/ID = 17.662394` at
  `J = 0.694325 µA/µm`; interpolating to 17.0 gives **`J = 0.829167 µA/µm`**
  → `W = 5/0.829167 = 6.0301 µm` → drawn **6.030** (−0.002 %).
- **`M3`/`M4`/`M6` — pfet, `L = 0.3`, gm/ID = 14, 5 µA/unit**: lines
  5867/5868 give `gm/ID = 13.316481` at `J = 1.357395` and
  `gm/ID = 14.116302` at `J = 1.031622`; interpolating to 14.0 gives
  **`J = 1.078993 µA/µm`** → `W = 5/1.078993 = 4.6340 µm` → drawn
  **4.634** (0.0 %).
- **`MB1`/`M5`/`M7` — nfet, `L = 1.2`, gm/ID = 18, 5 µA/unit**: lines
  944/943 give `gm/ID = 17.662394` at `J = 0.694325` and
  `gm/ID = 18.973791` at `J = 0.481260`; interpolating to 18.0 gives
  **`J = 0.639474 µA/µm`** → `W = 5/0.639474 = 7.8189 µm` → drawn
  **7.819** (+0.001 %).
- **`Rz` — 2501 Ω at `L = 9.763 µm`**: `rcon + L·rsheet = 254.77 +
  230.05 × 9.763 = 2501.0 Ω`.

### (b) Why each knob, and what it buys (all measured, full 15-point grid)

- **Input pair gm/ID 10 → 17** raises design `gm1` 50 → 85 µS at the same
  `I_SS = 10 µA` — the GBW lever. GBW is `gm1/(2π·Cc)`; the measured
  worst point moves **8.45 → 17.92 MHz @ SS/125 °C** (112 % of target, was
  53 %). It also widens the input common-mode window (`Vgs1` at ss/−40 °C
  falls ≈ 0.14 V) and improves the input-referred thermal floor
  (∝ 1/√gm1).
- **PMOS group `L` 0.6 → 0.3 µm at gm/ID 10 → 14** is the *phase-margin*
  lever that makes the GBW increase affordable: the shorter channel roughly
  doubles `fT6`, raising the second pole against the now-higher crossover
  (a plain Miller `p2` tracks `gm6`'s transit frequency, not its width —
  widening `M6` alone was screened and found PM-neutral, the width's
  extra `Cgg` cancelling its `gm`). Measured phase margin stays
  ≥ 60° everywhere: worst **63.94° @ SF/27 °C** (baseline worst 64.09° at
  the same corner). The cost is DC gain: gm/gds of the group falls, and the
  gain row's worst point drops **69.72 → 61.64 dB** (corner moves
  SS/125 → FS/125) — still met, but the margin shrinks from 9.7 dB to
  1.6 dB. This is the deliberate trade this record makes.
- **NMOS mirror group gm/ID 15 → 18** is the fall-slew lever the diagnosis
  points at: at the same 5 µA/unit, `M5`'s triode-region conductance (the
  crawl current during tail collapse) roughly doubles. Measured fall SR
  worst **1.73 → 11.03 V/µs @ SS/−40 °C** (×6.4), with *every* grid point
  improving (grid now 11.0–15.3 V/µs). The residual gap is structural —
  see Consequences.
- **`Rz` 2.00 → 2.50 kΩ**: `1/gm2` at the new design point is
  `1/(14 V⁻¹ × 50 µA) = 1.43 kΩ`, but the PVT screen measured the larger
  value better: the over-nulling leaves a benign left-half-plane residual
  zero (≈ 557 MHz at tt, ≈ 25× GBW) worth ≈ 2° of phase margin at the
  crossover, and both values pass ≥ 60° everywhere. 2.50 kΩ is adopted for
  margin; the residual-zero distance stays ≥ 25× GBW at all three corner
  extremes, preserving DR-001 decision (d)'s stated purpose.

### (c) What is deliberately unchanged

Topology (DR-001's domain), `Iref = 5 µA`, `I_SS = 10 µA`, `ID2 = 50 µA`
(`I_Q = 65 µA`), `Cc = 0.4998 pF`, `CL = 2 pF`, the matched-length-group
rule, the `M3 : M4 = 1 : 1`, `MB1 : M5 : M7 = 1 : 2 : 10`, and
`M4 : M6 = 1 : 10` count ratios, and the nfet input pair at `L = 1.2 µm`.
Measured `Iq` across the new grid: 64.24–66.63 µA (was 59.67–66.01).

## Alternatives considered

All of these were actually run (screened at the binding corners ss/−40 °C,
ss/125 °C, sf/27 °C, tt/27 °C — and the survivors at ff/125 °C, fs/−40 °C
too) before the Decision above was fixed; scratch decks and per-variant
results are reproducible from the bench templates exactly as this record's
screens were.

- **Input pair gm/ID = 18** (GBW worst ≈ 18.9 MHz, fall SR ≈ 12.6 @ ss/−40)
  — rejected: measured phase margin at SF/27 °C falls to 60.8°, leaving
  < 1° margin against an unscreened grid point; a PM regression on a
  previously-passing row is disqualifying. gm/ID = 17 keeps 3.9°.
- **Widening `M6` at `L = 0.6` (m = 16/32)** — rejected: measured
  PM-neutral (the `Cgg` growth cancels the `gm2` gain at the second pole),
  while tripling/quadrupling output-device area.
- **`Cc` 0.5 → 0.55 pF** — rejected as primary lever: buys ≈ 2° PM for
  −9 % GBW and −4 % both slew rates; strictly dominated by the `Rz` choice.
- **NMOS group gm/ID = 20** (W = 14.47) — rejected: measured *no* further
  fall-SR improvement at ss/−40 (9.73 vs 9.72 V/µs in that screen) — the
  crawl is no longer tail-limited after gm/ID 18 — at ≈ 2× the area.
- **Scaling all currents ≈ ×1.9** (`I_SS`, `ID2`, `Iref`) — rejected
  without screening: it would roughly double `I_Q`/`Pq` and regress the
  ratified quiescent-power row (≈ 128.7 µW at the binding corner).
- **PMOS group at `L = 0.15 µm`** — rejected: at gm/ID = 14 the unit width
  falls below the PDK's 0.42 µm minimum finger width (DR-002's own floor
  rule), and `gm/gds` would collapse the gain row below margin.
- **PMOS group gm/ID = 12 or 13 at `L = 0.3`** — rejected: measured PM
  2–4° short of the adopted point at the SF binding corner.
- **`Rz` = 1.43 kΩ (the literal `1/gm2` rule at the new design point)** —
  rejected: measured ≈ 2° *worse* PM than 2.50 kΩ at every screened point
  (both pass); margin taken instead.

## Spec lines affected

`spec/target-spec.md` §2 rows reconciled against
[`sim/opamp-characterization/records/20261001-074923-c317ff9`](../../sim/opamp-characterization/records/20261001-074923-c317ff9.md)
(their per-cell citations move from `20260916-032327-edc9f22` to the new
record; **no target value changes**):

- **GBW** — was "measured, target not met"; now **met** (worst 17.92 MHz @
  SS/125 °C, 112 % of ≈16 MHz).
- **Slew rate** — rise edge now **met** (worst 19.88 V/µs @ SS/−40 °C,
  99.4 %); fall edge **partially closed** (worst 11.03 V/µs @ SS/−40 °C,
  55 %; was 8.65 %).
- **Output swing** — **partially closed** (0.948 Vpp @ SS/−40 °C, 58.5 % of
  rail; was 0.855 Vpp / 52.8 %; DR-002's ≈1.39 Vpp estimate remains
  unmet).
- **Open-loop DC gain** — target still met at every point; worst case
  becomes 61.64 dB @ FS/125 °C (was 69.72 @ SS/125), margin 9.7 → 1.6 dB
  (the recorded cost of the PMOS `L` 0.6 → 0.3 trade).
- **Phase margin** — still met everywhere; worst 63.94° @ SF/27 °C (was
  64.09° at the same corner — essentially unchanged).
- **Quiescent power** — still confirmed ≈; worst 131.92 µW @ FF/125 °C
  (was 130.71; +0.9 %, from the slightly flatter mirror at ff, `Iq` 66.63
  vs 66.01 µA at that point).

No `[TBD]` row and no §1 row is touched; the input-common-mode-range `[P]`
row keeps its DR-002-based estimate (no ICM bench exists — the resize
*worsens nothing there by design*: both NMOS `Vov`s fall with gm/ID 15→18).

## Consequences

- **Fall SR remains 55 % of target at the worst corner — honestly open.**
  After the tail-mirror resize the crawl is no longer tail-limited; the
  remaining ceiling is the class-A output stage's single-ended, fixed-bias
  sink (`M7` gate at `ibias`) plus the first stage's starvation during
  large differential overdrive. Closing it fully requires a topology change
  (tail degeneration/clamp, or a class-AB output) — DR-001's domain, not a
  sizing pass. This record deliberately does not attempt it.
- **Gain margin shrank 8 dB** (69.72 → 61.64 dB worst). Still ≥ 60 dB at
  every point, but FS/125 °C now has only 1.6 dB of margin; any future
  change that costs first- or second-stage gain must re-check that corner
  first.
- **Area grows.** Total drawn gate width goes 82.8 µm → ≈ 179 µm of gates
  (`M7` 78.2, `M6` 46.3, `M5` 15.6, pair 2 × 6.03, mirror 2 × 4.63,
  `MB1` 7.82). `Cc` (244 µm²) still dominates the layout area conversation,
  per DR-002's own consequence, but the output devices are now markedly
  wider — the common-centroid structure DR-002 anticipated still applies.
- **Noise improves** (design `gm1` ×1.7 at unchanged current): the §2a
  thermal-floor estimate falls ≈ 30 → ≈ 23 nV/√Hz. The row stays `not
  started` (no noise bench), but the direction is recorded.
- **Zero systematic offset by construction survives**: the group-length and
  unit-count rules DR-002 established still hold exactly (`M6` is 10 units
  of `M3`/`M4`'s device; `M5`/`M7` are 2/10 units of `MB1`'s device). The
  review hazard DR-002 named (changing one device's length without its
  group) is inherited unchanged.
- **`Rz` still does not track `gm2` over PVT** (DR-002's standing caveat);
  with the deliberate over-nulling the residual is a LHP zero ≥ 25× GBW at
  the corner extremes — same order of margin DR-002 documented, opposite
  sign.

## Open items

- **Fall slew rate's structural fix** (tail clamp/degeneration or class-AB
  output) — a topology change requiring a record superseding DR-001, not
  this record. The measured diagnosis above (tail collapse to 3.6 mV, the
  ≈0.5 µA Miller crawl current) is the input any such record should start
  from.
- **Output swing at SS/−40 °C** remains 58.5 % against the ≈86 % estimate;
  the unity-buffer compliance bench conflates input-pair and output-stage
  limits, and an open-loop swing/ICMR bench would separate them.
- **Offset/mismatch, CMRR, PSRR, flicker noise, area** — unchanged `[TBD]`.
- **`Rz` as a triode device tracking `1/gm2`** — still on the table per
  DR-002's own open question; the over-nulled 2.50 kΩ value makes it less
  urgent but does not answer it.
