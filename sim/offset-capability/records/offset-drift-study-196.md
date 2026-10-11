# Paired offset drift after ideal single-point correction (#196)

Plan (committed before execution, commit dc665c0): [`offset-drift-plan-196.json`](offset-drift-plan-196.json).
Driver: `bin/offset_drift.py` (label `drift196`). Machine-readable result, recomputable from the raw
records with `offset_drift.py report --label drift196`:
`20261011-232842-drift-drift196-ae367c.drift.json`. DUT: the canonical `design/netlist/opamp_core.spice`
(DR-013 widths), `sha256:e954d17d...ce79`, captured once into `dut-drift196/`; every request used that copy.
Backend: `klt sim --backend batch` (fleet), client klt 0.7.0, **runner klt 0.5.0** (`runner_compatibility: mismatch`,
identical on all accepted jobs), ngspice 46, one models-lib hash. No local ngspice was run.

## Verdict (what this does and does not establish)

**One of four conditions was measured. Three could not be run because the fleet was at its instance cap for
all three allowed attempts. This is a partial screen, not the planned four-condition answer.**

| Step | Condition (TT, mismatch seed 20261085) | Result |
|---|---|---|
| B0_ref | 27 C, 1.80 V | accepted (attempt 3 of 3; job `klt-sim-59f75072ec89`), 100/100 samples ok |
| P0_replay | 27 C, 1.80 V, n=1 | accepted (job `klt-sim-d39676a0725a`); replay differs from reference sample 20261085/0 by 0.0 uV |
| B1 | -40 C, 1.62 V | accepted (attempt 1; job `klt-sim-9128edec529b`), 100/100 ok, 100 valid pairs |
| B2 | -40 C, 1.98 V | **NOT MEASURED**: 3 of 3 attempts refused by the fleet (`BATCH_MAX_CONCURRENT_INSTANCES=8`) |
| B3 | 125 C, 1.62 V | **NOT MEASURED**: same, 3 of 3 |
| B4 | 125 C, 1.98 V | **NOT MEASURED**: same, 3 of 3 |

Measured condition B1 (residual = Vos(-40 C, 1.62 V) - Vos(27 C, 1.80 V), joined by sample ID, mV, 95% intervals,
Student t for the mean and chi-square for sigma, assuming i.i.d. approximately normal residuals):

| quantity | value |
|---|---|
| valid pairs / requested / failed (cond, ref) | 100 / 100 / 0, 0 |
| mean residual | -0.069 mV, CI [-0.268, +0.131] |
| sample sigma of residual | **1.006 mV**, CI [0.883, 1.169] |
| max abs residual | 2.472 mV |
| reference sigma (same 100 samples) | 7.560 mV (mean +0.908 mV) |
| sigma screen 0.19 mV | **FAIL_SCREEN** (sigma lower bound 0.883 > 0.19) |

Interpretation, within the stated limits:

- Ideal single-point (constant input-offset) correction **fails the 0.19 mV sigma screen at -40 C / 1.62 V** by a
  factor of about 5 (lower bound 4.6x). This rejects the constant-correction model for that condition under the
  screen; the plan's stop rule says no expansion and "needs re-trim across temperature/supply" for the foreground
  trim ranked first in #147. It does not reject every trim architecture (e.g. temperature-tracked or
  background correction), and says nothing about the three unmeasured conditions, where drift could be larger.
- The mean drift (-0.07 mV, interval spans 0) is small beside the sigma; the screen bounds neither mean nor
  maximum residual and none is claimed.
- The proposed 0.275 mV allocation is untouched; this is not an offset-compliance or consumer-integration claim.
  Trim DAC mismatch, trim-induced operating-point changes, calibration error and noise remain unmeasured.
- Evidence level: exploratory, N=100 at one process corner (TT), one condition measured.

## Pairing evidence (required for any verdict; all held)

1. Echoed per-sample `seed`, `process_seed`, `mismatch_seed` of every B1 sample equal the reference sample with the
   same ID (all 100). klt derives them from (request seed, corner index 0, sample index) so they do not depend on
   temperature or supply (klt 0.7.0 source; runner 0.5.0 behaviour is not assumed, it is checked by the echo).
2. P0 replay (a separate request on a separate job) reproduced reference sample 20261085/0 with equal seeds and a
   0.0 uV difference (tolerance 40 uV).
3. Runner klt version, ngspice version, models-lib hash and bench netlist hash are identical across the accepted jobs.
4. Statistical sanity gate: residual sigma 1.006 mV is 13% of the reference sigma (limit 50%). Independent
   realizations would give about sqrt(2) x 7.56 = 10.7 mV. Corr(Vos_ref, Vos_B1) = 0.9918; the residual's
   regression slope on the reference offset is 0.020, i.e. the residual is mostly NOT a simple scaling of the offset.

Limit: items 1-3 show the seed inputs are held constant; they do not prove the in-simulator device draws are
invariant to temperature and supply. Item 4 is the independent check, and a loose one: a partially decorrelated
realization could hide inside the 13%, which would inflate the measured residual. The result is therefore an upper
-leaning estimate of true drift if pairing is imperfect; it cannot be read as a lower bound on real drift.

## Accounting

Requests recorded: 14 of the maximum 18 (B0_ref 3, P0_replay 1, B1 1, B2 3, B3 3, B4 3 = 14). Unique samples measured:
100 reference + 1 probe + 100 B1 = 201 of the plan's 501. Every attempt is retained:

- B0_ref attempt 1: refused by the fleet cap (no report). Attempt 2: **an orphan request** with no summary record -
  the first launch of the driver was wrapped in a 590 s `timeout` by mistake and killed seconds after submitting
  attempt 2; it has no klt report or job id. It is counted against the cap (the driver counts request files with no
  summary as attempts), so B0_ref had one real attempt left, which succeeded. The driver was then resumed from
  the same DUT snapshot and committed plan (`resume`), with a 300 s wait between retries added.
- B2, B3, B4: each three attempts, each refused with "N instance(s) already running + 1 requested exceeds
  BATCH_MAX_CONCURRENT_INSTANCES=8" (N = 8..12 other jobs from concurrent sweeps). Retry spacing 300 s. Per the plan the
  batches are recorded as FAILED_BATCH and were not retried further; the grid was NOT run locally. No sample is
  zero-filled; the three conditions are NOT_MEASURED.

The drift report's outcome flag reads `VERDICTS_ISSUED` because the pairing evidence held and every step reached
a terminal state; read it with the table above: three of four verdicts are `NOT_MEASURED`.

## Follow-up

Measuring C2-C4 needs a new committed plan (the caps of this plan are spent) and fleet capacity; waiting longer
between attempts or a queueing submit would avoid the same outcome. The tool gaps (no queue/wait on capacity
refusals, runner/client version skew, implicit corner-index-keyed paired draws) are already tracked at
2AMLogic/klayout-tools: #3043, #2869, #2948, #2967, #2929, #2899.
