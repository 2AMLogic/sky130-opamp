# Matched-group sizing feasibility for the proposed offset allocation, 2026-10-10 (append-only; issue #144)

Exploratory feasibility study, **not** a design change and **not** a
compliance claim. The canonical design (`design/opamp_core.sch`,
`design/netlist/opamp_core.spice`) is unchanged. `spec/target-spec.md` is
unchanged; DR-009 (σ ≤ 0.275 mV) stays **proposed**. The Monte Carlo here is
**exploratory: N = 100 at tt / 27 °C / 1.8 V per candidate**, not the
`N ≥ 300 + corners` basis DR-009 proposes. The disposition is in
[`DR-011`](../../../spec/decision-records/DR-011-offset-closure-sizing-feasibility.md)
(proposed).

**Finding: matched-group sizing is not a plausible closure path.** No
candidate gets within 8× of the 0.275 mV allocation, the smallest
mirror-only enlargement already fails the ratified phase-margin row, and
reaching the target would need roughly 300–600× the canonical matched gate
area. A separately scoped study of a different technique (trim, chopping or
auto-zero) is the proposed next step.

## Evidence index

| What | Where |
|---|---|
| Predeclared plan: candidate set, seeds, N, retry budget, checks, decision rule. Committed in `f8fb7d7` **before** any fleet submission | [`sizing-feasibility-plan-20261010.json`](sizing-feasibility-plan-20261010.json) |
| Candidate netlists (generated, grid-checked, regeneration-tested) | `../candidates/opamp_core.{grid0,m2p1,m2p2,m4p2}.spice` |
| Single-corner OP probe (one local `ngspice -b`, tt / 27 °C, every netlist in one deck): newly derived gm/ID, sensitivities, Pelgrom predictions, capacitance and headroom estimates | `20261010-135058-sizing144-op-33e160.{json,deck.spice,ngspice.log}` |
| Exploratory MC, one `klt sim` `monte_carlo` request per candidate on the batch fleet, DUT snapshot per campaign | `*-campaign-sizing144-{m2p1,m2p2,m4p2}-*.campaign.json`, `dut-sizing144-*/`, chunk `*.request.json` / `*.klt.json` / `*.summary.json` |
| Fleet PVT (5 corners × 3 temperatures, paired supplies, `ac,tran_sr,dc_swing`), one record per netlist | `../../opamp-characterization/records/20261010-{135147,135603,140018,140536}-f8fb7d7-*` (+ `netlist-snapshots/`) |
| Joined summary, extrapolation and mechanical decision | `20261010-142614-sizing144-summary-a6bd02.json` |
| Code | `../bin/sizing_feasibility.py`; `offset_probe.py campaign --netlist` (new); `pelgrom_handcalc.calc(core_path=…)` (new); tests `tests/test_sizing_feasibility.py`, `tests/test_offset_probe.py` |

Superseded outputs of this study, kept (append-only), not used:
`20261010-135017-sizing144-op-949f7b.*` (identical OP; its derived
`systematic_vos_estimate_v` had the wrong sign, fixed before the second run)
and `20261010-142602-sizing144-summary-f4be03.json` (written before a
lookup bug was fixed: it carries no OP data and no extrapolation).

## 1. Simulator-free bounds (estimates; `sizing_feasibility.py bounds`)

Inputs: the #107 measured group sigmas (pair 3.103 mV, mirror 7.740 mV,
stage 2 + bias 0.064 mV; N = 300, 1 SE = 4.1 %), the canonical matched gate
area (pair 14.47 µm², mirror 2.78 µm², both devices), first-order Pelgrom
area scaling at a fixed operating point.

- **Mirror-only enlargement cannot close the gap.** Driving the mirror term
  to zero leaves σ → σ_pair = **3.10 mV (2.85–3.36 mV at ±2 SE), 11.3× the
  0.275 mV allocation.** The pair alone needs **≥ 135× its area (114–158×)**
  even with a perfect mirror.
- **Area-optimal combined split** (minimise k_p·A_p + k_m·A_m subject to the
  allocation): k_pair ≈ 282, k_mirror ≈ 1604; matched gate area
  **≈ 8 540 µm² (7 200–9 990 µm² at ±2 SE) = ≈ 495× (420–580×)** the
  canonical 17.25 µm². With the hand-calc split instead of the measured one
  (pair under-predicted by 43 %, #107) it is ≈ 4 800 µm² (≈ 280×): the
  model-uncertainty end.
- **Operating-point lever on the mirror** (input-referred mirror term ∝
  gm3/gm1): the mirror sits at gm/ID ≈ 14.2; even gm/ID = 5 (≈ 400 mV
  overdrive) is only a 2.8× reduction, and the mirror Vsg rise comes straight
  out of the ICMR upper edge and the XM6 overdrive. Not a closing lever.
- **Model-bin effect** (the issue's "blind area scaling ignores model
  bins"): the pinned pfet bins at L = 0.3 µm use `vth0_slope1` = 7.356 mV·µm,
  the L ≥ 0.6 µm bins `vth0_slope` = 5.856 mV·µm. Lengthening the mirror
  therefore buys an extra ≈ 1.26× in σ beyond area. Measured below (m2p1),
  it is real and it does not change the conclusion.

## 2. Candidates (bounded before execution: 3 + 1 reference)

Each scales W **and** L of a matched group by the same factor s (W/L,
`mult` and the XM6 : XM3 = 10 : 1 mirror ratio preserved; gate area × s²).
XM6 scales with XM3/XM4 because its Vsg must match XM3's to keep the
first-stage drains balanced (systematic offset). All W/L are on the
0.005 µm grid (`grid_check --classes passive,mos`); the bias group W
7.819 → 7.820 is a placeholder that does not pre-empt #120.

| id | PMOS group XM3/XM4/XM6 W/L (µm) | pair XM1/XM2 W/L (µm) | why |
|---|---|---|---|
| grid0 | 4.635 / 0.3 | 6.03 / 1.2 | reference: canonical, grid snap only |
| m2p1 | 9.27 / 0.6 | 6.03 / 1.2 | mirror-only (area × 4) |
| m2p2 | 9.27 / 0.6 | 12.06 / 2.4 | both × 4 |
| m4p2 | 18.535 / 1.2 | 12.06 / 2.4 | mirror × 16, pair × 4: the area-optimal direction (k_m/k_p ≈ 5.7) |

**gm/ID first** (`sizing_feasibility.py gmid`, committed sweep
`sim/gm-id-characterization/records/20260909-062847-35a9d46`, tt / 27 °C,
at each candidate's current per square, read before any candidate was
simulated): pair 17.18 (unchanged; L = 2.4 µm is outside the swept L, so the
L = 1.2 µm curve is used as a long-channel proxy and flagged), mirror 14.15 →
14.65 (L 0.6) → 14.74 (L 1.2). The OP probe below confirms these within
±0.9 V⁻¹.

## 3. Newly derived operating points and sensitivities (tt / 27 °C, OP probe)

One deterministic single-corner run; the canonical instance in the same deck
reproduces `pelgrom_handcalc.OP` to ≤ 2e-4 relative, so the wrapper is
transparent. Nothing below reuses the baseline OP constants for a resized DUT.

| | canonical | grid0 | m2p1 | m2p2 | m4p2 |
|---|---|---|---|---|---|
| gm/ID XM1 / XM3 (V⁻¹) | 17.69 / 14.17 | 17.69 / 14.17 | 17.68 / 14.72 | 18.04 / 14.70 | 18.04 / 14.75 |
| mirror sensitivity dVos/dVT3 = gm3/gm1 | 0.801 | 0.801 | 0.832 | 0.815 | 0.818 |
| first-stage gain A1 (stage-2 sensitivity 1/A1) | 49.1 | 49.1 | 100.9 | 121.2 | 166.6 |
| Pelgrom hand calc, total (mV) | 7.30 | 7.30 | 3.42 | 3.00 | 1.69 |
| measured-anchored estimate, total (mV) ¹ | 8.34 | 8.34 | 4.46 | 3.50 | 2.21 |
| matched gate area, pair + mirror (µm²) | 17.25 | 17.25 | 25.60 | 69.01 | 102.37 |
| XM6 gate area (µm²) | 13.9 | 13.9 | 55.6 | 55.6 | 222.4 |
| cgg at d1 (XM3+XM4) / at d2 (XM6) (fF) | 13.7 / 69 | 13.7 / 69 | 51 / 258 | 51 / 258 | 202 / 1017 |
| mirror pole estimate gm3/(2π·cgg_d1) (MHz) | 774 | 774 | 216 | 217 | 55 |
| Vsg3 (V) / ICMR upper-edge estimate VDD − Vsg3 + Vth1 (V) | 0.977 / 1.450 | 0.977 / 1.450 | 1.050 / 1.377 | 1.050 / 1.348 | 1.084 / 1.314 |
| systematic Vos estimate (mV) | +0.151 | +0.151 | +0.064 | +0.050 | +0.034 |

¹ #107 measured group sigma × (candidate / canonical) hand-calc ratio per
group, so the 43 % pair under-prediction of the hand calc is not carried
into the candidate prediction.

## 4. Exploratory Monte Carlo (N = 100, tt_mm, 27 °C, 1.8 V)

`offset_probe.py campaign --label sizing144-<id> --base-seed 20261085
--corners tt --n-total 100 --chunk 100 --netlist <candidate>` on the batch
fleet (`KLT_SIM_BACKEND=batch`). Seed 20261085 is chunk 0 of #85 and #107, so
the candidate samples use the same per-sample seeds as the canonical run's
first 100 samples. Every request succeeded on its first attempt (no capacity
refusals, no local fallback); 0 failed samples; the n / seed / vary echo
was checked for every chunk. Sample budget used: 300 of 300.

| id | fleet job | ok / req | mean (mV) | **σ (mV)** | ±2 SE (mV) | min / max (mV) | predicted (anchored) | agrees ±25 % ² | σ / 0.275 mV |
|---|---|---|---|---|---|---|---|---|---|
| m2p1 | `klt-sim-9f66ea133ae0` | 100/100 | +0.66 | **4.25** | 3.64–4.85 | −14.54 / +11.69 | 4.46 | yes (−4.7 %) | 15.4× |
| m2p2 | `klt-sim-1919d6c48366` | 100/100 | +0.03 | **3.22** | 2.77–3.68 | −6.62 / +7.59 | 3.50 | yes (−7.7 %) | 11.7× |
| m4p2 | `klt-sim-bc7863202875` | 100/100 | −0.49 | **2.34** | 2.01–2.67 | −4.73 / +5.61 | 2.21 | yes (+5.9 %) | 8.5× |

² Predeclared in the plan (2 SE at N = 100 is 14 %); not widened.

Same seeds, canonical first 100 samples: σ = 7.56 mV (the full N = 300 is
8.58 mV). Ratios on common seeds: 0.56, 0.43, 0.31. Pearson correlation with
the canonical samples is only 0.37 / 0.26 / 0.22: the per-instance draws do
**not** stay aligned when the geometry (and model bin) changes, so the
seed pairing does not give common-random-number variance reduction here;
each candidate σ stands on its own N = 100.

Implied groups (variance differences, fragile): mirror at L = 0.6 µm (m2p1
minus the #107 pair) ≈ 2.90 mV against 7.74 mV canonical, a 2.67× reduction
for 4× area (area alone: 2×; area × bin slope: 2.51×). Pair at 4× area (m2p2
minus that mirror) ≈ 1.41 mV.

## 5. Deterministic PVT tradeoffs (fleet, 15 points per analysis, 0 failed units)

`pvt_sweep.py --fleet --backend batch --analyses ac,tran_sr,dc_swing
--netlist <netlist>`; 4 batch jobs per netlist, 16 in total, all accepted
on first submission (runner klt 0.5.0 vs client 0.7.0: warn-only, as in
every recent record). Worst case over the 15-point grid; targets are the
unchanged §2 rows.

| metric (target) | canonical `103340` | grid0 `135147` | m2p1 `135603` | m2p2 `140018` | m4p2 `140536` |
|---|---|---|---|---|---|
| open-loop gain (≥ 60 dB) | 61.64 @ fs/125 | 61.64 @ fs/125 | 77.38 @ ss/125 | 78.76 @ fs/125 | 84.28 @ ss/125 |
| GBW (≈ 16 MHz) | 17.92 @ ss/125 | 17.92 @ ss/125 | 17.29 @ ss/125 | 17.46 @ ss/125 | **13.97 @ ss/125 (fail)** |
| phase margin (≥ 60°) | 63.94 @ sf/27 | 63.94 @ sf/27 | **54.11 @ sf/27 (fail)** | **49.49 @ sf/27 (fail)** | **27.12 @ sf/27 (fail)** |
| rise slew (≈ 20 V/µs) | 19.88 @ ss/−40 | 19.88 @ ss/−40 | 19.85 @ ss/−40 | 18.86 @ ss/−40 | 17.39 @ ss/125 |
| fall slew (≈ 20 V/µs, unmet today) | 11.03 @ ss/−40 | 11.03 @ ss/−40 | 12.74 @ ss/−40 | 13.89 @ ss/125 | 12.56 @ ss/125 |
| swing Vpp at ss/−40 (≈ 1.39 V, unmet today) | 0.948 | 0.948 | 0.932 | 0.927 | 0.907 |
| quiescent power, max (≈ 128.7 µW) | 131.92 µW @ ff/125 | 131.92 µW | 131.92 µW | 131.97 µW | 131.97 µW |
| tt / 27 °C: gain, GBW, PM | 65.8 dB, 22.5 MHz, 65.4° | 65.8, 22.5, 65.4° | 79.2, 21.7, 55.5° | 80.7, 22.2, 51.0° | 86.4, 17.5, 28.3° |

grid0 reproduces the canonical record to print precision (largest change:
gain −0.0015 dB, fall slew −0.003 V/µs): the 0.005 µm grid snap of the MOS
widths is electrically invisible (useful to #120, not a sizing decision).

Reading: every resize **raises gain** (longer channels) and **costs phase
margin**; the mirror-only ×4 step (m2p1) already fails the ratified ≥ 60°
row at sf / 27 °C by 5.9°. The loss tracks the capacitance the preserved
ratios add at the two first-stage nodes: XM6's gate load at d2 grows 69 →
258 → 1 017 fF (it scales with the mirror), and the mirror pole falls
774 → 216 → 55 MHz against a 22 MHz crossover. The two are not separated
here (no candidate decouples XM6 from the mirror; that would change the
preserved ratio the issue asks for); an order-of-magnitude doublet estimate
attributes only a few degrees of m2p1's 10° loss to the mirror pole, the
rest to the second-stage pole through Cgs6. Rise slew and swing regress
slightly at every step; fall slew improves (an unrelated, unmet row).

**Headroom (estimate, tt only, no ICMR bench run):** the mirror's Vsg grows
by 73 / 73 / 107 mV (m2p1 / m2p2 / m4p2), and the estimated ICMR upper
edge (VDD − Vsg3 + Vth1, which also moves with the pair's Vth) falls by
73 / 102 / 136 mV. The measured worst-corner upper edge (1.1686 V @ SS / −40 °C, record
`20261009-103006-566b9a5`) has 145 mV of margin over the 1.024 V target;
m4p2's shift would consume most of it. The ICMR bench was not run on the
candidates (outside the predeclared budget).

## 6. Area still needed, anchored on the measured candidates

`extrapolation_from_candidates` in the summary JSON: the m2p1 / m2p2
measurements give per-area coefficients for the long-L mirror and the pair,
fed into the same area-optimal split.

- Central: k_pair ≈ 53, k_mirror ≈ 248 relative to m2p2's geometry;
  matched gate area **≈ 5 830 µm² ≈ 340× canonical**; XM6 (following the
  mirror) ≈ 13 800 µm², d2 gate load ≈ 64 pF. Low end of the ±2 SE band:
  ≈ 7 280 µm² (≈ 420×). High end: not resolvable (the variance difference
  goes non-positive; the N = 100 data cannot bound it from that side).
- Read with section 1: **≈ 280–580× the canonical matched gate area,
  several thousand µm², plus a second-stage device that grows in
  proportion.** m4p2, at 6× the canonical matched area and a 1 pF d2 load,
  is already at 27° phase margin and below the GBW target.

Mechanical application of the predeclared decision rule
(`decision.verdict` in the summary): **`sizing_insufficient`**. No
candidate's σ (upper 2-SE bound 4.85 / 3.68 / 2.67 mV) meets 0.275 mV, and
none keeps phase margin ≥ 60° at all 15 points.

## Limits stated plainly

- N = 100 at one corner, one temperature, one supply: exploratory sampling,
  no `N ≥ 300 + corners` claim, no yield statement.
- The extrapolation is a Pelgrom area law used far outside the simulated
  range; the candidates validate the law up to 6× area only.
- No compensation re-tune was attempted for the candidates (Cc, Rz fixed).
  A re-tune could recover some phase margin at a GBW or slew cost; it cannot
  change the ≥ 280× area requirement, which is set by mismatch statistics,
  not by stability.
- Open-loop offset definition, 5 µA ideal Iref, 2 pF, as in #85 / #107.
