# Sink bias-margin study (issue #197)

Status: **partial, no candidate recommended.** Plan: `variants/bias-margin/PLAN.md` (committed before any
fleet request). No topology is adopted, no target revised, no full compliance claimed. Every number below is
regenerated from committed raw records by `variants/sink_bias_report.py`
(outputs: `variants/bias-margin/stage1.out.md`, `stage2-full.out.md`, `stage2-mc.out.txt`); record ids
are listed in `variants/bias-margin/records.json`. Failed attempts are retained, not removed.

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
- ic075 passes all conditions (gain >= 61.64 dB, PM >= 62.32 deg at screen points, static v(out) never within
  0.10 V of a rail, max static |I(XMS)| 0.0114 uA).
- Power saved by lowering I_C is small: TT/27 Pq 137.3 (ic090) -> 136.2 (ic075) -> 135.1 uW (ic060);
  FF/125 154.9 -> 153.0 -> 151.4 uW. ic075 saves 1.1 uW at TT/27 and 1.9 uW at FF/125 versus the
  original sink and still sits 14.9 to 21.6 uW (mean 18.1) above canonical at the 15 points, because the
  replica leg is fixed (see PLAN.md sizing).
- Unintended static boost (XMS DC current) is negligible for all designs (ic090 max 0.2501 uA at FF/125).
  The overhead is the always-on replica and bias legs, not DC boost.

Survivor chosen by the pre-declared rule (lowest FF/125 Pq among non-stopped candidates): **ic075**.

## Stage 2: ic075 on the 15-point paired matrix

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
(cap 4). Stage 1 as planned. Total within the plan's hard cap.

## Conclusion and recommendation

Lowering I_C from 0.90 to 0.75 of the unit current keeps gain and PM above 60 and improves standard fall SR
at all 15 paired points, but saves only 1.1 to 1.9 uW against ic090; the sink still costs ~18 uW over canonical
and worst-case power (153.2 uW) is well over the ~128.7 uW target, with fall SR below 20 V/us everywhere.
The TT mismatch probe shows static boost above 1 uA in 6 % of samples, and FF/125 mismatch is unresolved.
**Recommendation: no candidate is recommended for further qualification** (mismatch limit failed at TT/27;
hot-corner mismatch unresolved; power cost unrecovered). Independent-supply qualification (#110) is not covered.
