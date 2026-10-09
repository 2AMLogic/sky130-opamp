# Offset Monte Carlo campaign record 2026-10-09 (append-only; issue #85)

Measured data only. **Not a limit, not a ratified basis, not a pass/fail claim.**
`spec/target-spec.md` §2's offset row stays OPEN/TBD and its `N>=300` basis
stays *proposed*; T1 item 6's signoff status is unchanged (citing this record
from T1 item 6 is a separate follow-up).

## Setup

- Bench `bench/offset_dc.cir` (committed `opamp_core.spice`, open loop, 5 uA ideal Iref, 2 pF), VDD 1.8 V, 27 C.
- One `klt sim` request per (corner, chunk): `corners.process = ["<corner>_mm"]`, `monte_carlo {n: 100, seed, vary: "mismatch"}`, `KLT_SIM_BACKEND=batch` (AWS Batch Spot fleet). `keep_artifacts: false` (every per-sample value is in the committed `*.klt.json`).
- N = 3 chunks x 100 = **300 per corner**; base seed **20261085**, chunk k seed = 20261085 + k (20261085, 20261086, 20261087), identical at every corner. Per-sample mapping: global sample g = 100*chunk + `monte_carlo.sample_index`; the same g draws the same mismatch seed at every corner (paired across corners).
- Vos = V(inp) - V(inn) at the first rising v(out)=0.9 V crossing; bracket +/-30 mV, 20 uV step. A sample is **failed, never zero**, if status != pass, a measurement is missing/non-finite, the output does not bracket 0.9 V, or the monte_carlo echo does not match the request. Failures would be excluded from mean/sigma with the count shown (sample sigma, n-1 divisor).
- Code: `bin/offset_probe.py campaign` (+ `--only corner:chunk` to resume) and `summarize`; chunk records run at commit `caa31ba` (plus `--only`/capacity-detection edits for the last 4 chunks).

## Result (all 300/300 samples ok at every corner, 0 failed)

| corner | ok | failed | mean (mV) | sigma (mV) | 3 sigma, measured (mV) | abs(mean)+3 sigma (mV) | min / max (mV) |
|---|---|---|---|---|---|---|---|
| tt | 300/300 | 0 | +0.518 | 8.583 | 25.75 | 26.27 | -27.38 / +27.64 |
| ss | 300/300 | 0 | +0.516 | 8.692 | 26.08 | 26.59 | -27.59 / +27.92 |
| ff | 300/300 | 0 | +0.531 | 8.386 | 25.16 | 25.69 | -26.82 / +27.14 |
| sf (extra) | 300/300 | 0 | +0.502 | 8.382 | 25.15 | 25.65 | -26.62 / +26.88 |
| fs (extra) | 300/300 | 0 | +0.556 | 8.664 | 25.99 | 26.55 | -27.60 / +28.10 |

The 3-sigma column is `3 x` the sample standard deviation of each corner, a measured
figure labelled as such. Full per-corner statistics, chunk record IDs and seeds:
`20261009-154748-campaign-offset-mc300-final-5fbc07.campaign.json` (re-derivable with
`offset_probe.py summarize records/*mc300*.summary.json`; checked by `tests/test_offset_probe.py::CampaignRecords`).

Caveats stated, not hidden:

- Extremes (+/-27-28 mV) are close to the +/-30 mV sweep bracket. No sample failed the bracket check so nothing was censored, but a wider bracket is needed before any tail beyond ~3 sigma is read from this bench.
- Sigma is ~8.6 mV and nearly corner-independent: this is the open-loop input-referred offset, dominated by local mismatch (corner shifts are deterministic and small against it). The systematic baseline (tt, mismatch off) is +151 uV (#52); the observed mean ~+0.5 mV is a sample-mean quantity with standard error ~0.5 mV (sigma/sqrt(300)), i.e. not distinguishable from the baseline.
- Pairing check on the committed data: Pearson correlation of Vos(g) between tt and ss/ff/sf/fs is 0.9989..0.9996, confirming the per-sample seed is honored identically at each corner; corner statistics are therefore not independent draws, and sigma differences between corners (8.38..8.69 mV) are corner effects on the same draws, not independent estimates.
- Only 27 C and 1.8 V; no VDD/temperature grid and no CMRR/PSRR interaction.

## Prerequisites from the #52 README, resolved here

1. **Runner/client klt version mismatch.** All 15 successful chunk requests ran on a runner reporting klt 0.5.0 against client `0.7.0+g6440221f9207` (`runner_compatibility: mismatch`, warn only). Effect: none observed on the sampling path. For every chunk the `monte_carlo` echo (n, seed, vary=mismatch), the returned sample count, the `sample_index` set 0..n-1 and the corner process were checked against the request (`echo_problems` empty in every summary; a mismatch would have forced samples to failed), and the cross-corner pairing above independently confirms the seeds took effect. The runner image was not updated; the version mismatch warning and klt's `family_mismatch` note for the capacitor family ("not independently verified") remain.
2. **Rz/Cc mismatch in the budget.** `tt_mm`-family sections enable the mismatch terms of Rz (`res_high_po`) and Cc (`cap_mim_m3_1`) as well as the MOS devices (#52 model inspection). Their DC effect on the offset is argued, not measured: at DC the Miller capacitor carries no current and the series Rz carries no DC current, so they should not move the DC crossing; this was not isolated by a MOS-only or passive-only run (no klt control exists to enable mismatch per device family), so it stays an **unverified** assumption. The recorded sigma is for "all mismatch enabled by `<corner>_mm`", the conservative inclusive reading.

## Request ledger (append-only; every request kept)

- 15 requests supplied the statistics (3 chunks x 5 corners); listed with seeds and job IDs in the `.campaign.json` and each `*.summary.json`.
- `20261009-144723-offset-mc300-sffs-sf-c1-52fdb1`: batch refusal, `batch_no_capacity` (exact error in its `.summary.json` stderr). Retried as `...sf-c1-r2-b16302` (same seed 20261086), which succeeded.
- `20261009-151434-offset-mc300-sffs-fs-c2-0d0756` and `20261009-151558-offset-mc300-ttssff-ss-c2-555353`: **interrupted** (request file only; no klt report or summary; the sweep session that submitted them died at ~15:16Z). They contributed no data. They were not resubmitted blindly: new requests with the identical chunk seed (20261087) and `--only` were submitted by the resuming session as `20261009-152035-offset-mc300-sffs-fs-c2-95fd4e` and `20261009-152035-offset-mc300-ttssff-ss-c2-cc3c4c`, which are the records used.
- Two `*.campaign.json` files (`...152740-campaign-mc300-sffs-ec6ffb`, `...154716-campaign-mc300-ttssff-cbf09b`) are the resume invocations' own end-of-run reports and are **partial by construction** (they only cover the resumed chunks, so they show the other chunks as "requested but not returned"). They are superseded by the `-final-` campaign JSON and must not be read as results.
- Fleet concurrency: two sequential request streams ran side by side (<= 2 concurrent instances); no other submit errors besides the one above.
