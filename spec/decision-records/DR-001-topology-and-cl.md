# DR-001: Two-stage topology (input-pair polarity, output stage, cascode) and CL target

- **Status**: proposed (input to a future spec-ratification issue; this
  repo has no ratified spec yet — `spec/target-spec.md` itself is still
  DRAFT, per its own status banner)
- **Date**: 2026-09-09
- **Decided by**: Builder agent, issue #8
- **Related**: #6 / PR #7 (the gm/ID device-characterization study this
  record cites), `spec/target-spec.md` (`CL` row, §1), `spec/porting-plan.md`
  §4 ("Open items and next steps"), gap-to-T1 tracker #3

## Context

`spec/porting-plan.md` §4 named two open items ahead of any sizing work on
this block: the two-stage Miller-compensated topology's input-pair
polarity, first-stage load, output-stage class, and cascode-or-not; and the
load-capacitance (`CL`) target that `spec/target-spec.md`'s GBW/phase-margin
rows are stated "into." Both were explicitly deferred by issue #6 / PR #7
(its own "Out of scope" section), which committed the prerequisite gm/ID
device-characterization data this decision now draws on:
`sim/gm-id-characterization/records/20260909-062847-35a9d46-summary.csv`
(interpolated at fixed gm/ID targets) and
`-full-sweep.csv` (full per-point sweep, including the `vth_v` extraction
used below). Both files are confirmed present on `origin/main` @ `8657ffa`
(2026-09-09).

No same-PDK sibling's amplifier topology transfers wholesale
(`spec/porting-plan.md` §3) — this is genuinely new circuit design for this
block, not a port. Per `CLAUDE.md`, this pass is 1.8 V-core CMOS only; no
3.3 V I/O-flavor variant is opened here. Every device considered below is
therefore `sky130_fd_pr__nfet_01v8` / `sky130_fd_pr__pfet_01v8`.

All figures below are read directly from the two CSVs named above:
`W = 2.0 µm`, `|Vds| = 0.9 V`, `VDD = 1.8 V`, sweep over `L = 0.15 / 0.3 /
0.6 / 1.2 µm`, corners `tt/ff/ss/sf/fs`, temperatures `−40 / 27 / 125 °C`
(per `sim/gm-id-characterization/records/20260909-062847-35a9d46.md`).
Every cited row is a literal `(device, corner, length_um, temp_c,
gm_id_target_per_v, vov_v, gm_gds, ft_hz)` tuple from `-summary.csv`, or a
literal full-precision row from `-full-sweep.csv` for `vth_v` — grep either
file directly to reproduce any number quoted here. The rail assumed
throughout is this block's own 1.8 V ±10% primary (`spec/target-spec.md`
§1): **1.62 V worst-case low, 1.98 V worst-case high**.

## Decision

**(a) Input-pair polarity: NMOS.** At every channel length in the swept
grid, `sky130_fd_pr__nfet_01v8` reaches dramatically higher `fT` than
`sky130_fd_pr__pfet_01v8` at the matched `gm/ID = 10 V⁻¹` bias point
(`tt`, 27 °C):

| L (µm) | nfet fT (GHz) | pfet fT (GHz) | nfet/pfet ratio |
|---|---|---|---|
| 0.15 | 50.31 (`nfet,tt,0.15,27.0,10.0,0.08251096420151932,17.812185903821444,50310997967.09632`) | 8.17 (`pfet,tt,0.15,27.0,10.0,0.14303686150521747,9.249065764929224,8172232995.535432`) | ≈6.2x |
| 0.3 | 13.84 (`nfet,tt,0.3,27.0,10.0,0.1745077297233025,70.63109423010788,13837681973.178862`) | 3.37 (`pfet,tt,0.3,27.0,10.0,0.14565187191474413,57.8640597462792,3365681803.31053`) | ≈4.1x |

Since the input pair's `gm` directly sets both GBW (`GBW ≈ gm1 /
(2π·Cc)`) and input-referred thermal-noise floor for a fixed bias current,
and `gm/ID` is by construction matched across the two rows in each
comparison (both interpolated at `gm/ID = 10 V⁻¹`), the fT advantage is a
real bandwidth/efficiency gain at equal bias efficiency, not an artifact of
unequal `gm/ID`. At the candidate input-pair length (`L = 0.15 µm`, near
the sweep's minimum), NMOS also carries the higher intrinsic gain at this
short length: `gm/gds = 17.81` (nfet, row above) vs. `9.25` (pfet, row
above) — NMOS gives more first-stage gain per device at the same length,
on top of its speed advantage.

**(b) First-stage load: simple mirror, no cascode (single-ended first
stage).** The differential NMOS input pair is loaded by a simple
(non-cascode) PMOS current mirror, converting the first stage to a
single-ended output — the classic two-stage Miller shape, and no CMFB is
needed as a result (only a fully differential first stage would require
one). Cascoding either the input pair or the mirror load is rejected on
headroom: at the sweep's own `vth_v` extraction, the NMOS device at the
input pair's candidate length is already using a large share of the 1.62 V
worst-case rail on `Vgs` alone at the `ss/−40 °C` corner:

`nfet,ss,0.15,2.0,-40.0,0.9,0.0,-0.846406244,3.31808839e-17,1.18245232e-15,4.15274851e-17,8.87114338e-16,0.846406244,,,0.21214078460591812`

(`vth_v = 0.846 V`) — so stacking a second NMOS device in series (a
telescopic cascode) would require `Vgs1 + Vgs2 ≳ 2 × 0.846 V ≈ 1.69 V`
just to keep both devices at threshold, before any `Vov`/`Vds,sat`
headroom is added — already exceeding the 1.62 V rail. The same holds on
the PMOS mirror side at the output-stage device's candidate length (see
(c)):

`pfet,ss,1.2,2.0,-40.0,0.9,1.8,0.6737307000000001,2.73898274e-05,7.57682781e-05,1.23427747e-06,1.38171777e-14,1.1262693,2.7662926455681136,61.386746450131675,872746681.7754251`

(`vth_v = 1.126 V` at `ss/−40 °C`) — a single PMOS device at this length
already consumes the majority of the rail; stacking a second would not fit
at all.

**(c) Second-stage class: Class-A common-source, PMOS gain device.** The
second (output) gain stage is a PMOS common-source transistor (gate driven
from the first stage's single-ended output node, drain = block output),
loaded by an NMOS constant-current sink — the canonical two-stage Miller
shape `CLAUDE.md` names, complementary to the NMOS input pair's PMOS
current-mirror load. PMOS is chosen for the output gain device because
this study's data shows PMOS's intrinsic gain (`gm/gds`) growing far
faster with channel length than NMOS's, at the same `gm/ID = 10 V⁻¹`
target:

| L (µm) | nfet gm/gds | pfet gm/gds | pfet/nfet ratio |
|---|---|---|---|
| 0.15 | 17.81 (row above) | 9.25 (row above) | 0.52x (NMOS ahead, short L) |
| 1.2 | 150.34 (`nfet,tt,1.2,27.0,10.0,0.1779772321718718,150.34338894034482,923694282.0334392`) | 394.30 (`pfet,tt,1.2,27.0,10.0,0.15633370223321472,394.29946200230614,240374428.32014117`) | 2.62x (PMOS ahead, long L) |

confirmed to hold at both corner extremes at `L = 1.2 µm`, `gm/ID = 10
V⁻¹`: `ss/−40 °C` gives `pfet,ss,1.2,-40.0,10.0,0.17374527049866112,391.3798627647017,279700538.2027164`
(`gm/gds = 391.4`) vs. `nfet,ss,1.2,-40.0,10.0,0.17338892591692476,147.9923717947348,1199214917.0636318`
(`gm/gds = 148.0`); `ff/125 °C` gives `pfet,ff,1.2,125.0,10.0,0.11079070052309993,393.3747331737141,173631100.59244695`
(`gm/gds = 393.4`) vs. `nfet,ff,1.2,125.0,10.0,0.196416094071378,153.89886135344202,691484917.1382074`
(`gm/gds = 153.9`) — the ≈2.6x PMOS advantage at long
length holds across the corner grid, not just at `tt/27 °C`. Sizing the
output-stage PMOS gain device at a moderate/long channel (candidate
`L ≈ 1.2 µm`, the sweep's longest point; final length TBD in a future
sizing pass) lets the second stage carry the bulk of total loop gain from
a single non-cascoded device, consistent with the cascode decision in (b).
The output-stage NMOS current-source load can use the same candidate
length for a matched-headroom bias branch:
`nfet,tt,1.2,27.0,10.0,0.1779772321718718,150.34338894034482,923694282.0334392`
(same row cited in the gm/gds table above). The
first-stage tail current source (NMOS) and mirror load (PMOS) are
candidate-sized at an intermediate length (`L = 0.3 µm`) for a moderate
output resistance without paying the full long-channel area cost:
`nfet,tt,0.3,27.0,10.0,0.1745077297233025,70.63109423010788,13837681973.178862`
(tail) and `pfet,tt,0.3,27.0,10.0,0.14565187191474413,57.8640597462792,3365681803.31053`
(mirror load),
confirmed at both corner extremes for the mirror load:
`pfet,ss,0.3,-40.0,10.0,0.16313970704600889,59.884981649589385,3519118888.054376`
and `pfet,ff,0.3,125.0,10.0,0.08012418418989142,51.9412838369931,2379111683.245384`.

**An illustrative (non-binding) two-stage DC-gain estimate** from `gm/gds`
alone — input stage (`nfet`, `L = 0.15 µm`, `tt/27 °C`, `gm/gds = 17.81`)
times output stage (`pfet`, `L = 1.2 µm`, `tt/27 °C`, `gm/gds = 394.30`) —
gives `17.81 × 394.30 ≈ 7023` (≈76.9 dB). At `ss/−40 °C` (input `gm/gds =
23.06` from `nfet,ss,0.15,-40.0,10.0,0.11065760695501746,23.055890095214018,53499354550.85566`,
output `gm/gds = 391.4` from the
row cited above): `23.06 × 391.4 ≈ 9025` (≈79.1 dB). At `ff/125 °C` (input
`gm/gds = 14.89` from `nfet,ff,0.15,125.0,10.0,0.07637849840036044,14.890830794752453,48130572647.863014`,
output `gm/gds = 393.4` from the
row cited above): `14.89 × 393.4 ≈ 5857` (≈75.4 dB). This is a
plausibility check that a non-cascoded architecture can plausibly reach a
canary-block-class DC-gain target across the corner grid — before any
mirror/tail loading is accounted for — not a sizing commitment; actual
DC-gain sizing (with mirror/tail loading, and a specific channel length
for every device) is out of scope here (see "Open items" below).

**(d) Miller compensation: with a nulling resistor in series with Cc.**
Plain Miller compensation (a single capacitor `Cc` between the first- and
second-stage output nodes) introduces a right-half-plane (RHP) zero at
`ωz ≈ gm2 / Cc`, which erodes phase margin — a bigger risk here because the
non-cascoded second stage (decision (b)/(c)) has no cascode device to push
that zero out further, unlike a cascoded topology. Placing a resistor
`Rz` in series with `Cc`, sized to `Rz ≈ 1/gm2` (the standard technique for
this topology), moves the zero to a finite left-half-plane location (or
cancels the non-dominant pole outright when tuned precisely), recovering
phase margin without consuming any rail headroom — a resistor costs no
`Vgs`/`Vds,sat` budget, unlike a cascode device or a source-follower
buffer, both of which were rejected in (b) on exactly that headroom
argument. This choice is therefore consistent with, not independent of,
the non-cascoded decision above: it recovers via a passive element what
the topology deliberately does not spend on stacked active devices.
`Rz`'s exact value depends on `gm2`, which depends on the output-stage
device's bias current — out of scope here (see "Open items"), but the
sizing rule (`Rz ≈ 1/gm2`, or slightly larger to push the zero fully into
the left half-plane and partially cancel the non-dominant pole) is named
now so a future sizing pass has a concrete target.

**Comparison against the twins' own topology choices.** `gf180-opamp` has no
`spec/decision-records/` directory yet (checked directly against that
repo's own tree, 2026-09-09), so there is no topology choice to compare
against there. `sg13g2-opamp` does:
[`sg13g2-opamp/spec/decision-records/0001-topology-and-cl.md`](https://github.com/2AMLogic/sg13g2-opamp/blob/main/spec/decision-records/0001-topology-and-cl.md)
independently reached the *same architecture shape* on a different PDK and
a different (1.2 V) rail — NMOS input pair (its own PSP103 fT data showed
NMOS ≈1.8x faster than PMOS at matched length/overdrive), a PMOS
common-source output stage (chosen for the same reason this record cites:
PMOS's `gm/gds` grows far faster with channel length than NMOS's on that
PDK too), and a non-cascoded topology (rejected for the same headroom
reason: that record's own `Vth` data left little margin on a 1.08 V
worst-case-low rail). This record's independent read of sky130's own gm/ID
data reaches the identical architecture conclusion on a different process
and a different (1.62 V vs. 1.08 V) worst-case rail — the underlying
device-speed/intrinsic-gain trade-off (NMOS faster, PMOS higher `gm/gds` at
long length) recurs across both PDKs, not just this one. `sg13g2-opamp`'s
record does not, however, specify a compensation scheme with the same
level of explicitness this record gives in (d); no comparison is drawn
there beyond noting neither twin repo's compensation choice conflicts with
this one.

**CL target: 2 pF.** No `CL` precedent exists yet in this block's own
three-foundry twin: `gf180-opamp/spec/target-spec.md`'s `Load capacitance,
CL` row is itself still `[TBD]`, and that repo has no
`spec/decision-records/` directory yet (checked directly, no DR to cite).
`sg13g2-opamp` does have a precedent —
[`sg13g2-opamp/spec/decision-records/0001-topology-and-cl.md`](https://github.com/2AMLogic/sg13g2-opamp/blob/main/spec/decision-records/0001-topology-and-cl.md)
chose **`CL = 2 pF`** for the identical topology on a different PDK, with
the same reasoning this record adopts: large enough to be a realistic
stand-in for driving an external test-pad plus probe/ESD parasitic
capacitance (commonly 1–3 pF for a small test-chip bond pad plus
scope-probe loading), yet small enough that GBW/slew-rate targets derived
from it stay meaningful for a canary block's likely bias-current budget.
**This record adopts the same `CL = 2 pF` value** for cross-PDK
comparability across the three-foundry twin set (`CLAUDE.md`: "identical
bench structure to gf180-opamp and sg13g2-opamp"), rather than diverging
on independent judgment where no PDK-specific reason to differ has been
found.

## Alternatives considered

- **PMOS input pair.** Rejected. At matched `gm/ID`, PMOS trails NMOS on
  both `fT` (≈4–6x lower over the swept length range) and `gm/gds` at the
  input pair's likely short-channel length (≈0.52x at `L = 0.15 µm`), so a
  PMOS input pair would either need a larger bias current to match NMOS's
  GBW/gain contribution (worse power efficiency) or accept lower GBW/gain
  at the same current. PMOS's usual input-pair advantages in other
  processes (lower 1/f noise, easier near-rail common-mode range when
  biased from VDD) are not cited here as disqualifying — but this PDK's
  characterization data does not show a compensating `gm/gds` or `fT`
  advantage at the input pair's likely bias point to offset the
  bandwidth/gain cost, so the decision follows `CLAUDE.md`'s "gm/ID first"
  rule on measured device data rather than generic architecture folklore.
- **NMOS output-stage gain device** (paired with the NMOS input pair,
  i.e., an NMOS common-source second stage). Rejected. The data shows the
  *opposite* length-dependent trend this alternative would need: PMOS's
  `gm/gds` grows from `9.25` (`L=0.15`) to `394.30` (`L=1.2`) — a ≈42x
  step — while NMOS's `gm/gds` grows only from `17.81` to `150.34` over the
  same length range — a ≈8.4x step (both at `tt/27 °C`, `gm/ID = 10 V⁻¹`,
  rows cited in Decision (a)/(c)). An NMOS output-stage gain device would
  forfeit the intrinsic-gain headroom PMOS offers at moderate/long length,
  making a non-cascoded design harder to justify without a longer, larger
  device or an explicit cascode.
- **Cascoded (telescopic or folded) two-stage.** Rejected for this record.
  A cascode would recover more DC gain per stage than the non-cascoded
  design's own `gm/gds`-based estimate above, but at the direct cost of
  stacked-device headroom on a rail with only 1.62 V of worst-case low-rail
  margin. The `vth_v` data cited in Decision (b) shows a single candidate
  device at either the input-pair length (`nfet`, `L=0.15 µm`, `vth ≈
  0.85 V` at `ss/−40 °C`) or the output-stage length (`pfet`, `L=1.2 µm`,
  `vth ≈ 1.13 V` at `ss/−40 °C`) already consumes a large fraction of
  1.62 V on `Vgs` alone — stacking a second device of either polarity does
  not fit without either a much shorter/weaker cascode device (undermining
  the reason to cascode in the first place) or exceeding the rail. The
  non-cascoded estimate in Decision (c) already reaches a plausible
  canary-block DC-gain range (≈75–79 dB across corners) without paying
  that headroom cost, so cascode is deferred rather than adopted as a
  first design; nothing in this record forecloses re-opening a cascode
  option in a superseding record if a future sizing pass finds the
  non-cascoded gain estimate does not close once mirror/tail loading and
  mismatch are included.
- **Folded-cascode single-stage (instead of a two-stage Miller topology
  altogether).** Rejected — out of scope by construction: `CLAUDE.md`
  mandates a two-stage Miller-compensated topology for this block; this
  record makes decisions within that mandate (input-pair polarity, load,
  output class, cascode-or-not, compensation scheme), not a decision to
  abandon it.
- **Plain Miller compensation without a nulling resistor.** Rejected as
  the primary choice. It is the simpler circuit (no extra resistor,
  nothing to size beyond `Cc`), but the non-cascoded second stage's RHP
  zero sits closer to the unity-gain crossover than it would in a cascoded
  design, directly threatening the `≥ 60°` phase-margin target
  (`spec/target-spec.md` §2). The nulling resistor is a cheap fix (one
  passive element, no rail-headroom cost) for a problem this record's own
  non-cascoded choice creates, so it is adopted instead of accepting the
  phase-margin risk or reopening the cascode question.
- **CL matched to a specific downstream consumer circuit's input
  capacitance.** Rejected — this is a standalone canary block with no
  named downstream consumer yet (per `README.md`'s framing), so there is
  no concrete consumer capacitance to match. The twin-shared generic
  bench-representative value (2 pF) is used instead, consistent with
  `spec/porting-plan.md` §4's framing of `CL` as independent of any
  specific application context for this block.
- **A larger CL (e.g. 5–10 pF) to stress-test slew rate / output-stage
  drive strength.** Rejected as the primary target — a larger CL is a
  reasonable *stretch* row for a future spec revision once nominal sizing
  exists, but as the primary GBW/phase-margin target it would force this
  canary block's bias currents higher than its role warrants, per
  `CLAUDE.md`'s framing of this block as a canary, not a heavy-load
  driver.
- **A CL diverging from the `sg13g2-opamp` twin's 2 pF** (e.g. an
  independently chosen sky130-specific value). Rejected — no
  sky130-specific reason to diverge was found in this study's device data;
  `CLAUDE.md`'s "identical bench structure to gf180-opamp and sg13g2-opamp"
  favors comparability across the three-foundry twin set whenever no
  PDK-specific constraint forces a different choice, so the twin's value
  is adopted rather than re-derived from scratch.

## Spec lines affected

- `spec/target-spec.md` §1, `Load capacitance, CL` row: filled to
  `2 pF [DR-001]` (was `[TBD]`); the table's intro also gains a one-line
  pointer to this record where it previously stated no decision record
  exists.
- `spec/porting-plan.md` §4: the "Topology decision" and "Load capacitance
  (`CL`) target" bullets are marked done, each pointing at this record —
  mirroring how PR #7 marked the device-characterization and corner-grid
  bullets done in the same section.
- No row in `spec/target-spec.md` §2 (performance targets) is filled or
  relaxed by this record — every `[TBD]` performance row stays `[TBD]`
  until PVT-cornered testbenches exist (gap-to-T1 tracker #3, item 5).

## Consequences

- Every gm/ID-dependent `[TBD]` row in `spec/target-spec.md` §2 (DC gain,
  GBW, slew rate, quiescent power) can now be sized against a concrete
  topology and load, citing
  `sim/gm-id-characterization/records/*.csv` directly per `CLAUDE.md`'s
  "gm/ID first" rule — but no such sizing is performed by this record (see
  "Open items" below).
- The non-cascoded architecture choice means output swing and input
  common-mode range are not further constrained by cascode headroom, but
  the two-stage DC-gain budget now depends on the output-stage PMOS device
  being sized at a moderate-to-long channel length (candidate `L ≈ 1.2 µm`
  class) to realize the `gm/gds` advantage this record cites — a future
  sizing pass that instead sizes that device short (for area or bandwidth
  reasons) would need to re-examine whether the non-cascoded DC-gain
  estimate in this record still closes.
- The nulling-resistor compensation choice adds one component (`Rz`) and
  one sizing equation (`Rz ≈ 1/gm2`) to the eventual schematic, relative to
  plain Miller compensation — a small schematic-capture cost in exchange
  for the phase-margin headroom it buys back from not having a cascode.
- Adopting the `sg13g2-opamp` twin's `CL = 2 pF` value means this block's
  GBW/slew-rate targets, once filled, will be directly comparable to that
  twin's — supporting `CLAUDE.md`'s cross-foundry comparability framing —
  but ties this block's bias-current budget to a load that was chosen for
  a different PDK's canary-block role, not derived independently from any
  sky130-specific application context. If a future sizing pass finds 2 pF
  produces an unrealistic bias-current or area result on this PDK, that
  finding should produce a superseding record, not a silent change.
- This decision is unverified in simulation beyond the device-level gm/ID
  data cited above — no schematic exists yet in this repo (`design/` holds
  only a scaffold `README.md`, verified against `origin/main` @ `8657ffa`,
  2026-09-09). If a future sizing or schematic-level pass finds the
  non-cascoded DC-gain budget does not close (e.g. once mirror/tail-device
  loading and mismatch are included), or finds the nulling-resistor
  compensation cannot hit the phase-margin target at the `CL = 2 pF` load,
  that finding should produce a superseding record, not a silent addition
  of a cascode or a silent `CL` change.

## Open items

This record does **not** perform any actual amplifier sizing — no device
widths, bias currents, or mirror ratios are chosen here; the channel
lengths named above (`L = 0.15 µm` input pair, `L = 0.3 µm` tail/mirror,
`L = 1.2 µm` output stage) are candidates for a future sizing pass to
confirm or revise, not commitments. Specifically left open:

- Device widths, tail current, and mirror ratios for every device named
  above.
- `Cc` and `Rz` numeric values (the appendix-style budget below is
  illustrative, not a sizing commitment).
- Input-referred offset and mismatch budget (statistical basis is named in
  `spec/target-spec.md` §2 but not sized here).
- Whether the `ss/−40 °C` / `ff/125 °C` corner extremes cited above (chosen
  because they bound the swept grid) turn out to also be the binding
  corners once a full schematic exists — `spec/target-spec.md` §2's
  "Binding corner (predicted)" column states these as predictions, not
  measurements, and this record does not change that.
- The 3.3 V I/O-device-flavor variant — explicitly out of scope per
  `CLAUDE.md` ("only via its own decision record").

**Appendix — illustrative (non-binding) first-cut compensation budget.**
For a two-stage Miller-compensated amplifier, `GBW ≈ gm1 / (2π·Cc)` and the
non-dominant pole (uncompensated) sits at `p2 ≈ gm2 / CL`. A common rule of
thumb for `≥ 60°` phase margin under dominant-pole compensation is to keep
`p2 / GBW ≳ 2.2–3`, which — combined with the standard pole-splitting
relation `Cc ≈ (0.2–0.3) × CL` for this topology class — gives, at
`CL = 2 pF`: `Cc` on the order of `0.4–0.6 pF`, and a required `gm2/gm1`
ratio on the order of `(CL/Cc) × (p2/GBW) ≈ (2/0.5) × 2.5 ≈ 10`, i.e. the
output stage's transconductance should be roughly an order of magnitude
larger than the input pair's. This is a structural target expressed as a
ratio (independent of absolute bias current, which is not chosen in this
record), consistent with the output stage being sized at a much longer
channel and, in a future sizing pass, likely a higher bias current than
the input pair. `Rz ≈ 1/gm2` (Decision (d)) then follows once `gm2` is
fixed by that sizing pass. None of these numbers are binding; they exist
only to give a future sizing pass a starting point consistent with this
record's topology choice.

**Next step**: schematic capture in `design/` with xschem, sized from this
DR's operating points.
