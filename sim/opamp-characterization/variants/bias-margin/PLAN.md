# Plan: lower-overhead I_C margins for the signal-dependent sink (issue #197)

Committed **before any fleet request** (the only simulation done so far is one local
single-unit syntax probe of the static-current `.meas`, TT/27 C, original bias, not evidence).
Approval scope (issue #197): a bounded experiment; no topology adoption, no target or spec
revision, no full-compliance claim. The canonical design (`design/`) is not touched.

## Designs (immutable DUT identity: each variant netlist is snapshotted per record, sha256 recorded)

| Tag | f = I_C / 5 uA | W(XMC) um | Role |
|---|---|---|---|
| canonical | n/a | n/a | committed fleet records, DUT `sha256:e954d17d...` (not re-run, see below) |
| `ic090` | 0.90 | 4.170 | rebased original sink (reference) |
| `ic075` | 0.75 | 3.475 | margin 1 |
| `ic060` | 0.60 | 2.780 | margin 2 |

Variants are generated from `design/netlist/opamp_core.spice` (DR-013 widths) by
`variants/sink_bias_margin.py generate`; `check` proves the canonical cards are byte-identical,
only XMC differs, and every width is on the 0.005 um grid. The generator's `sizing` output
is the simulator-free selection argument (quiescent margin 10/25/40 %, boost at the falling-edge M6
current 31/23.5/16 uA, saving of 0/1.35/2.7 uW at 1.8 V; lowering I_C can save at most 8.1 uW of
the sink's ~17-19 uW overhead because the replica leg I_6c is fixed). Exactly two margins are screened.
A zero-volt probe source `Vxms` in series with the XMS source (electrically inert) exposes the static
boost current; all three variants carry it.

Canonical reference: the committed fleet records `20261011-140526-04489d4-7e5893` (ac, tran_sr, dc_swing,
45/45) and `20261011-201913-046fe81-7c5771` (icmr, tran_sr, tran_sr_icmr, 15-point paired grid) share the
current canonical DUT hash and the same bench templates (testbench changes since are additive:
`tran_sr_icmr`). They are the canonical column; no canonical re-run is spent.

## Stage 1: screen (fleet, `--fleet --backend batch`, paired supplies, DR-006 solver settings)

Per design (`ic090`, `ic075`, `ic060`), one `pvt_sweep.py --netlist <variant>` invocation per point:

| Point | Why | Analyses | Requests = logical units |
|---|---|---|---|
| TT/27 C, 1.8 V | nominal | ac, tran_sr, icmr, tran_sr_icmr | 5 (ac-iq, ac, tran-sr, icmr, tran-sr-icmr) |
| SS/-40 C, 1.62 V | binding fall slew; ICMR-limited | same | 5 |
| FS/125 C, 1.8 V | binding gain | ac | 2 |
| SF/27 C, 1.8 V | binding phase margin | ac | 2 |
| FF/125 C, 1.98 V | binding quiescent power | ac | 2 |

plus one 15-unit paired-grid `static` request per design (`sink_bias_margin.py static --tag T`; DC
quiescent power, XMS static current, v(out) at the AC bias point). Per design 16 + 1 = 17 requests,
31 units; Stage 1 total **51 requests, 93 logical units**.

## Stage 2: at most one survivor (fleet)

* Full 15-point paired matrix: `pvt_sweep.py --fleet --backend batch --analyses ac,tran_sr,dc_swing,icmr,tran_sr_icmr`
  = 4 + 5 + 15 = **24 requests, 90 units**.
* Mismatch probe: `sink_bias_margin.py mc --tag <survivor> --n 100` at TT/27 C (`tt_mm`, 1.8 V) and FF/125 C
  (`ff_mm`, 1.98 V), distinct seeds = **2 requests, 200 units** (monte_carlo, vary mismatch).

## Caps

* First submissions: Stage 1 <= 51, Stage 2 <= 26; total <= **77** requests.
* Resubmission only of a request that produced no measurements for an infrastructure reason (fleet error,
  timeout, capacity refusal beyond pvt_sweep's built-in capacity wait): <= 1 resubmission per request,
  <= 6 in Stage 1 and <= 4 in Stage 2 (hard total <= 87). A measured outcome (unit fail, non-convergence,
  railed output, low gain) is **never** retried; it is preserved as a result.
* No local grid, ever: if a batch submit fails after the allowed resubmission, the error is recorded in the
  report/PR and the affected claim stays unresolved. No change to host tools.

## Screening conditions (candidates `ic075`, `ic060`; `ic090` is measured identically as the reference)

A candidate is **stopped** (and its evidence kept) on any of:

1. **Fail / rail**: any Stage-1 unit failed or missing for the candidate; or static probe `v(out)` within
   0.10 V of a rail at any of the 15 static points; or a `tran_sr`/`tran_sr_icmr` unit not slew-limited/invalid.
2. **Gain**: `gain_dc_db < 60` at any of the five screen points.
3. **Phase margin**: `phase_margin_deg < 60` at any of the five screen points.
4. **No useful falling-slew improvement**: standard `sr_fall` gain over the canonical record below
   +1.5 V/us at TT/27 C (the original sink gained +3.99 in #79) or below +0.5 V/us at SS/-40 C.

Reported for every design, not a stop condition: standard and ICMR-aware fall slew separately (never merged),
GBW, rise slew, quiescent power per point (saving vs `ic090`, excess over canonical), static XMS boost
current (flag above 1 uA) at 15 points.

**Survivor choice**: among candidates not stopped, the one with the lower measured FF/125 C quiescent power.
If both are stopped, nothing is expanded and the report recommends no candidate. `ic090` is never expanded.

## Recommendation rules

* "Further qualification of candidate X" only if Stage 2 has zero failed/railed units, gain >= 60 dB and
  PM >= 60 deg at all 15 points, fall slew above canonical at all 15, **and** the mismatch probe has all 200
  samples unrailed with |static I(XMS)| <= 1 uA (rule-of-three 95 % bound <= 3 % per point).
* Any mismatch violation or unresolved mismatch probe => no viability recommendation (mismatch limit failed /
  unresolved). Independent-supply qualification (#110) is explicitly out of scope and remains additional work.
* The standard fall-slew target (~20 V/us) is not claimed closed by an ICMR-contained step; saved bias current is
  judged against the existing power target (~128.7 uW) and the canonical 131.9 uW worst case.
