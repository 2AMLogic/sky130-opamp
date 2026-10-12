# Sink bias-margin study (issue #197)

Status: **partial, no candidate recommended.** Plan: `variants/bias-margin/PLAN.md` (committed before any
fleet request). No topology is adopted, no target revised, no full compliance claimed. Every number below is
regenerated from committed raw records by `variants/sink_bias_report.py`
(outputs: `variants/bias-margin/stage1.out.md`, `stage2-full.out.md`, `stage2-mc.out.txt`,
`provenance.out.md`); record ids are listed in `variants/bias-margin/records.json`. Failed attempts are
retained, not removed.

## Evidence validation and replicate selection

Before a record's rows are used, the report checks it as follows (`provenance.out.md`, tests in
`tests/test_sink_bias_margin.py`):

- **DUT identity.** The record's DUT hash must equal its variant file (canonical records: the canonical
  hash). This covers the static and mismatch records as well as the PVT records. The captured snapshot
  must still hash to that value. Static and mismatch records must also declare the expected `kind` and
  `tag` and hold their declared unit count.
- **Bench and model provenance.** Canonical and variant PVT records share the same PDK commit and RC
  corner, CL, Ibias, supply mode, per-corner VDD, solver settings, klt `models` block and fleet runner
  version. Variant bench bodies are byte-identical to the canonical bodies of the same name. The one
  exception is the two step levels of each ICMR-aware slew body: the method derives them from that DUT's
  own ICMR, so they are masked and checked against the record's own `step_low_v`/`step_high_v`. One
  point differs (SF/125: ic075 ICMR low 0.5841 V vs canonical 0.5842 V, so the step starts at 0.6341 V
  vs 0.6342 V), as the method intends. The static and mismatch probes use one bench body for all three
  variants.
- **Duplicates.** A record listed twice and a measurement key repeated inside one record are rejected.
  The same key in two distinct records is accepted only if every measured column agrees exactly (run
  timing `elapsed_s` excepted). The last-listed record is selected and every source id is kept. A
  conflicting replicate is an error, not a silent choice. On the committed evidence there are 26
  replicated keys, all agreeing: 15 canonical standard-slew points (the canonical ICMR-aware re-run
  re-measured them) and 11 ic075 Stage 1 screen points re-measured by Stage 2. No conflict and no
  within-record duplicate was found. The regenerated tables are byte-identical. Failed-unit errors from
  every record are listed whichever replicate is selected.

## Designs

DR-013-width rebase of the original replica-subtraction sink with the I_C bias leg at fraction f of the
5 uA unit current: `ic090` (original margin, reference), `ic075`, `ic060`; the other cards are
byte-identical to `design/netlist/opamp_core.spice` (`sink_bias_margin.py check`, tests in
`tests/test_sink_bias_margin.py`). The canonical column is the committed canonical fleet records
(DUT `sha256:e954d17d...`); no canonical re-run was spent. The static XMS probe is a zero-volt series source.

## Stage 1 screen (TT/27, SS/-40, FS/125, SF/27, FF/125; paired supplies; batch fleet)

Complete: all three designs, 5 pvt_sweep requests + 1 static (15-unit) request each, 0 failed units.

- Standard fall SR gain over canonical: ic090 +3.98 V/us (TT/27), +1.01 (SS/-40); ic075 +2.24, +0.97;
  ic060 +0.70, +0.76.
- **ic060 stopped** (screening condition 4): TT/27 gain +0.70 < 1.5 V/us. Its evidence is kept.
- **ic075 stopped** (screening condition 1, strict reading): its TT/27 `tran_sr_icmr` fall edge classifies
  `inconclusive` (avg 15.36 V/us, no slew claim), so it is not slew-limited. The `ic090` reference is stopped
  for the same reason. ic075 meets conditions 2-4 (gain >= 61.64 dB, PM >= 62.32 deg at screen points,
  TT/27 fall SR gain +2.24, SS/-40 +0.97) and the static checks (v(out) never within 0.10 V of a rail, max
  static |I(XMS)| 0.0114 uA).
- Power saved by lowering I_C is small: TT/27 Pq 137.3 (ic090) -> 136.2 (ic075) -> 135.1 uW (ic060);
  FF/125 154.9 -> 153.0 -> 151.4 uW. ic075 saves 1.1 uW at TT/27 and 1.9 uW at FF/125 versus the
  original sink and still sits 14.9 to 21.6 uW (mean 18.1) above canonical at the 15 points, because the
  replica leg is fixed (see PLAN.md sizing).
- Unintended static boost (XMS DC current) is negligible for all designs (ic090 max 0.2501 uA at FF/125).
  The overhead is the always-on replica and bias legs, not DC boost.

Under the pre-declared rule, **no candidate survives Stage 1 and nothing should have been expanded**
(`stage1.out.md`, regenerated).

**Plan deviation: Stage 2 ran despite the Stage 1 stop condition.** The screening helper first used for this
study checked missing/failed units, gain, PM, falling-slew gain and static railing. It did not check the
`tran_sr`/`tran_sr_icmr` slew-limited/invalid part of PLAN.md condition 1, so it reported ic075 as a survivor,
and ic075 was expanded on that basis. The helper now enforces the whole of condition 1: missing
`tran_sr_icmr` unit, rise or fall class other than `slew_limited`, and non-finite or non-positive standard
slew. The plan itself is unchanged; only a dated post-run note was appended. The Stage 2 and mismatch results
below are kept as disclosed, off-plan evidence. They are not plan-compliant expansion results and do not
support any viability claim.

## Stage 2 (off-plan, see deviation above): ic075 on the 15-point paired matrix

Records: `20261012-002038-7d10f60-12f3e2` (tran_sr, dc_swing, icmr, tran_sr_icmr, 15/15 each) and
`20261012-015900-5ab2a6b-ca069b` (ac, 15/15).

**Fleet failures.** In the first Stage 2 request the `ac-iq` and `ac` requests were refused by the fleet
(`9 instance(s) already running + 1 requested exceeds BATCH_MAX_CONCURRENT_INSTANCES=8`); they produced no
measurements and are recorded in `12f3e2` errors. Each was resubmitted once (within the plan's cap) as
`ca069b` (the ac and ac-iq requests together), which succeeded. No local fallback was used.

Results (see `stage2-full.out.md`, ic075 vs canonical):

- Gain min 61.64 dB (FS/125), equal to canonical to 0.01 dB; PM min 62.32 deg (FF/125) vs canonical 63.94 deg
  (SF/27): PM >= 60 deg at all 15 points.
- Standard fall SR improves at all 15 points (+0.73 to +4.95 V/us); worst point is SS/-40 C, 11.03 -> 12.00 V/us.
  **No point reaches 20 V/us** (max 19.92 at FF/125); the standard fall-slew target remains unmet.
- Quiescent power: worst 153.2 uW (FF/-40 C) vs canonical worst 131.9 uW and the ~128.7 uW target. Power
  excess over canonical is 14.9 to 21.6 uW per point.
- ICMR-aware fall slew (reported separately from standard): 5 of 15 points classify slew_limited, 10 are
  `inconclusive` (the sink makes the contained step no longer cleanly slew-limited); canonical is
  slew_limited at 15 of 15. The ICMR-aware averages must not be read as closing the standard target.
  SS/-40 C, the ICMR-limited point, stays slew_limited: 13.65 vs canonical 13.95 V/us, i.e. the sink gives no
  output-current benefit there; its standard-step gain (+0.97) is mainly input-range-limited behavior.

## Mismatch probe (predeclared: `sink_bias_margin.py mc`, n=100, mismatch, deterministic seeds)

- TT/27 C (`tt_mm`, 1.8 V; record `20261012-013032-7d10f60-375ebb`, seed 20261198, batch job
  `klt-sim-dfc446ed693a`): 100/100 units ok, 0 railed (v(out) 0.878 to 0.920 V), but **6/100 samples
  have |I(XMS)| > 1 uA** (p95 1.10 uA, max 5.63 uA). This breaches the plan's mismatch limit
  (every sample <= 1 uA). Note the runner/client klt version mismatch warning in the record
  (runner 0.5.0, client 0.7.0); the 100 mismatch samples were returned, so the option was honored.
- FF/125 C (`ff_mm`, 1.98 V): **not obtained.** First attempt (record dir `20261012-013942-7d10f60-579853`)
  was interrupted before any response (killed run; no result recorded). Resubmission
  `20261012-020100-5ab2a6b-f927b8` was refused by the fleet (`8 instance(s) already running + 1 requested exceeds
  BATCH_MAX_CONCURRENT_INSTANCES=8`). The one allowed resubmission is spent; no further retry and no local
  fallback. Hot-corner mismatch robustness is unresolved.

A deterministic seeded sample is sensitivity evidence, not a yield estimate.

## Budget accounting (against PLAN.md caps)

Stage 2 first submissions: 24 pvt_sweep + 2 mc = 26 (cap 26). Resubmissions: ac+ac-iq (2), FF mismatch (1) = 3
(cap 4). Stage 1 as planned. Total within the plan's hard cap. Under a strict reading of condition 1, Stage 2 should
have spent nothing; all 26 Stage 2 first submissions and 3 resubmissions are the off-plan expansion.

## Conclusion and recommendation

Lowering I_C from 0.90 to 0.75 of the unit current keeps gain and PM above 60 and improves standard fall SR
at all 15 paired points, but saves only 1.1 to 1.9 uW against ic090; the sink still costs ~18 uW over canonical
and worst-case power (153.2 uW) is well over the ~128.7 uW target, with fall SR below 20 V/us everywhere.
The TT mismatch probe shows static boost above 1 uA in 6 % of samples, and FF/125 mismatch is unresolved.
**Recommendation: no candidate is recommended for further qualification.** Under a strict reading of the plan,
no candidate passes the Stage 1 screen. The off-plan ic075 expansion fails the mismatch limit at TT/27, leaves
hot-corner mismatch unresolved, and does not recover the power cost. Independent-supply qualification (#110) is not covered.
