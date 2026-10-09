# Offset sigma attribution record 2026-10-09 (append-only; issue #107)

Measured data only. **Not a limit, not a ratified basis, not a pass/fail claim.**
`spec/target-spec.md` is unchanged; the offset row stays OPEN/TBD. This record
attributes the 8.58 mV (tt) open-loop input-referred offset sigma of
`campaign-20261009-offset-mc300.md` (issue #85) to device groups.

## Setup

- Same bench conventions as #85 (`bench/offset_dc.cir`: committed `opamp_core.spice`, open loop, 5 uA Iref, 2 pF, VDD 1.8 V, 27 C, +/-30 mV bracket, 20 uV step), `corners.process = ["tt_mm"]`, `monte_carlo {n: 100, seed, vary: "mismatch"}`, `KLT_SIM_BACKEND=batch` (AWS Batch Spot fleet), `keep_artifacts: false`. No ngspice was launched on the worker host.
- Seeds are the #85 seeds: chunk k uses 20261085 + k (k = 0..2), global sample g = 100*chunk + `sample_index`. The same g therefore draws the same per-sample mismatch seed here as in the #85 `tt` all-devices run, which is the all-on reference (reused, not re-run).
- N = 300 per MOS group (3 chunks x 100), N = 100 for the passives (1 chunk), N = 4 for the control. A sample is failed, never zero, on the #85 rules (also: echo of n/seed/vary must match the request). 0 samples failed in any group; every `echo_problems` is empty.
- Code: `bin/attribution.py` (`gen`, `run`, `summarize`), benches `bench/attribution/offset_dc_attr_<group>.cir` (generated, checked equal to a regeneration by `tests/test_attribution.py`), `bin/pelgrom_handcalc.py`, derived numbers in `20261009-attribution-summary.json`.

## How a group is isolated (tool gap, stated not hidden)

**`klt sim` has no control that enables mismatch for a subset of instances or device families.** `<corner>_mm` turns the PDK's global mismatch switch on for the whole deck, and `family_mismatch` only reports per family. Per-instance gating is therefore done *outside* the tool: each bench wraps every device that is *not* in the group under test in a bench-level subcircuit (`mmoff_nfet/pfet/res/cap`) that declares a local `.param mc_mm_switch=0` around the unchanged PDK device. The design netlist is not modified; only the model token on each X card differs (checked by test). Validity evidence from this campaign:

- Control `none` (every device wrapped, `tt_mm` library section on): 4/4 samples return exactly +151.0 uV, the mismatch-off systematic baseline of #52, sigma 0.000 mV. Wrappers add no offset and zero all random terms.
- `passives` (Rz, Cc on): 100/100 samples return exactly +151.0 uV, sigma 0.000 mV. This measures, rather than argues, that Rz/Cc mismatch has no DC offset effect (the open item of the #85 record); it resolves the #85 "unverified assumption".
- Additivity: see the RSS check below (Pearson 0.99998 against the independent all-on run).
- Gating loss found while building the wrappers: ngspice dropped the X-line multiplier `m=` through the extra hierarchy level when no un-wrapped device of that model was left, giving a 1-2 mV systematic shift visible only in the control. Wrappers forward `m` and `mult` explicitly.

Tool gap filed per the friction protocol (generic, no design detail): **2AMLogic/klayout-tools#2995** "klt sim monte_carlo: no per-instance / per-family mismatch selection; per-device-group variance attribution needs a hand-written netlist wrapper".

Group list verified against `design/netlist/opamp_core.spice` (10 instances, partitioned with no overlap or omission, checked by test): input pair XM1/XM2, PMOS mirror XM3/XM4, second stage XM6/XM7, tail/bias XM5/XMB1, Rz/Cc XRz/XCc. Note that the "bias" group (XM5 tail, XMB1 diode) shares the XM7 mirror reference: XMB1 and XM7 form the second-stage sink mirror, so the bias group's mismatch enters through the XM7 current, while XM7 (second stage group) carries its own threshold/beta terms. The group boundary is the issue's, kept as stated.

## Result (tt, 27 C, 1.8 V; sigma = sample standard deviation, n-1)

| group (mismatch on) | ok/requested | mean (mV) | sigma (mV) | min / max (mV) | share of group-variance sum |
|---|---|---|---|---|---|
| input pair XM1/XM2 | 300/300 | +0.560 | **3.103** | -8.672 / +8.781 | 13.8 % |
| PMOS mirror XM3/XM4 | 300/300 | +0.109 | **7.740** | -19.965 / +26.967 | 86.2 % |
| second stage XM6/XM7 | 300/300 | +0.149 | **0.052** | -0.060 / +0.296 | 0.0 % |
| tail/bias XM5/XMB1 | 300/300 | +0.153 | **0.037** | +0.028 / +0.264 | 0.0 % |
| Rz/Cc | 100/100 | +0.151 | **0.000** | +0.151 / +0.151 | 0.0 % |
| none (control) | 4/4 | +0.151 | 0.000 | +0.151 / +0.151 | - |
| all devices (#85, tt) | 300/300 | +0.518 | **8.583** | -27.38 / +27.64 | - |

Confidence: the standard error of a sigma from N = 300 is sigma/sqrt(2(N-1)) = 4.1 % (1 sigma), so pair 3.10 +/- 0.13 mV, mirror 7.74 +/- 0.32 mV, all-on 8.58 +/- 0.35 mV. The stage2/bias sigmas are tens of uV, quantised by the 20 uV sweep step (their sigma and shares are resolution-limited, not precise). The mirror tail (-20/+27 mV) is close to the +/-30 mV bracket, as in #85; no sample failed the bracket.

Reading: **the PMOS mirror (1.39 um^2 per device, W/L 4.634/0.3) sets about 86 % of the offset variance and the input pair about 14 %; the second stage, tail/bias and Rz/Cc contribute under 0.1 mV.** This is a measurement of this one design at one operating point.

### RSS vs all-on consistency check

- RSS of the four MOS group sigmas = **8.339 mV** vs the independent all-on run **8.583 mV** (-2.8 %, inside the 4.1 % sampling error of either number).
- Pearson correlation of [sum of per-group Vos minus 3 x baseline] against the same-sample all-on Vos over the 300 common samples: **0.99998**. The per-instance draws are the same under gating and the response is additive to first order.
- Group-variance sum 69.5 mV^2 vs all-on 73.7 mV^2: 94 % explained; the residual 4.1 mV^2 (equivalent 2.0 mV) is the non-additive interaction (and the baseline mean difference), not a separately measured source.

## Pelgrom hand calculation vs measurement

`bin/pelgrom_handcalc.py` (simulator-free for the mismatch statistics: coefficients from the pinned PDK's `*__tt.pm3.spice` expressions and `*__mismatch.corner.spice` slopes; drawn W/L/mult from the netlist; only gm/Id/gds are taken from one nominal `.op`, constants listed in the script). Tolerance **predeclared in the script before the attribution results were read** (committed in `6f18704`, before any group result existed): total within 25 % (4.1 % N=300 sampling error, ~17 % allowance for omitted terms and single-OP gm/Id); a group with predicted sigma >= 0.5 mV within 30 %; a group predicted < 0.5 mV must measure < 0.5 mV.

| group | hand calc (mV) | measured (mV) | rel. diff | tolerance | agree |
|---|---|---|---|---|---|
| input pair | 1.767 | 3.103 | -43 % | 30 % | **no** |
| PMOS mirror | 7.082 | 7.740 | -8.5 % | 30 % | yes |
| second stage | 0.040 | 0.052 | - | < 0.5 mV | yes |
| tail/bias | 0.031 | 0.037 | - | < 0.5 mV | yes |
| Rz/Cc | 0.000 | 0.000 | - | < 0.5 mV | yes |
| **total** | **7.299** | **8.583** | **-15.0 %** | **25 %** | **yes** |

**Statement: the hand calculation agrees with the measured ~8.6 mV total within the predeclared 25 % (it under-predicts by 15 %, and agrees on the mirror dominance and the negligible second stage/bias/passives), but it does NOT agree for the input pair alone (under-predicts by 43 %, outside the predeclared 30 %).** The tolerance was not widened after reading the results.

Unfitted observation on the pair miss, flagged as a hypothesis, not tested here: the hand calculation omits the `voff` mismatch term by design. The nfet `voff` slope in the pinned PDK is 0.007 (about 2x the nfet `vth0` slope 0.003356) while the pfet `voff` slope is 0.0, which is consistent with the pair (nfet) being under-predicted and the mirror (pfet) not. The pair sits at gm/Id ~ 18 (moderate/weak inversion), where `voff` acts. Confirming it needs a further run; none was made.

## Request ledger (append-only; every request kept)

18 requests were submitted (run label `attr`, base seed 20261085; fleet job IDs in each `.summary.json`).

- Used as data (15): none-c0; passives-c0; bias-c0, c1, c2 (`231615-...-66bb3e`); pair-c0, c1, c2; mirror-c0, c1, c2; stage2-c0, c1 (as `...-c1-r4-f7ac35`), c2. Fleet elapsed 70-688 s per request.
- **Batch refusals, `batch_no_capacity`** (verbatim in each `.summary.json` stderr: "batch backend failed: batch-fleet-provision.sh launch failed (exit 1): error: no capacity in any of the 30 pools after 3 attempt(s) ... this is the capacity-refusal case, and it is now visible instead of silent"): `223652-...stage2-c1-28ff0b`, `224337-...stage2-c1-r2-9cedf2`, `225031-...stage2-c1-r3-339731`. The runner waited and resubmitted the identical chunk seed (20261086); `...r4-f7ac35` succeeded. No local fallback was used.
- **Interrupted, no report, no data (request file only; the submitting process was terminated, cause not recorded by the tool):** `211731-offset-attr-pair-c0-6df509` (submitter process gone after ~33 min waiting, no klt report or exit code) and `220127-offset-attr-bias-c2-e84c67` (same). Chunks were re-requested with the identical seeds as `220905-...pair-c0-201946` and `231615-...bias-c2-66bb3e`. Whether the orphan fleet jobs ran is unknown from the repository.
- **Replicate:** `231708-offset-attr-bias-c2-e82290` (a duplicated submission of bias chunk 2, same seed, job `klt-sim-4f89983f5b5e`) returned all 100 per-sample values bit-identical to `...66bb3e`; it is not used in the statistics (summarize keeps the first record per chunk) and serves as a seed-reproducibility check.
- Concurrency: at most 2 concurrent submit streams. The fleet runner reported klt 0.5.0 against client 0.7.0+g (`runner_compatibility: mismatch`, warn only); as in #85 the n/seed/vary echo and sample count were checked for every used chunk (no problems), and the mismatch-off control and the 0.99998 cross-check confirm the seeds took effect. A pre-existing generic report exists at klayout-tools#2851 / #2901.
