# Paired offset drift after ideal single-point correction (#196)

Plan (committed before execution, commit dc665c0): [`offset-drift-plan-196.json`](offset-drift-plan-196.json).
Driver: `bin/offset_drift.py` (label `drift196`). Machine-readable result, recomputable from the raw
records with `offset_drift.py report --label drift196`:
[`20261011-233532-drift-drift196-1e74b9.drift.json`](20261011-233532-drift-drift196-1e74b9.drift.json)
(outcome `VERDICTS_PARTIAL`, exit code 2). It supersedes the outcome flag of the earlier record
[`20261011-232842-drift-drift196-ae367c.drift.json`](20261011-232842-drift-drift196-ae367c.drift.json),
which read `VERDICTS_ISSUED` although three of four conditions were `NOT_MEASURED`; that record is kept
unchanged (append-only). The new record is a pure recompute from the same raw records (no new
simulation); its statistics, verdicts and pairing evidence are identical to the earlier record's. DUT: the canonical `design/netlist/opamp_core.spice`
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
- **The FAIL_SCREEN depends on the pairing being exact.** The residual is only the drift of one device
  realization if the reference and B1 samples with the same ID are the same realization. If pairing were
  imperfect, part of the measured 1.006 mV would be decorrelation between realizations, not drift, and the
  measured residual would overstate the true drift. The pairing evidence below supports exact pairing (equal
  echoed seeds, exact replay, Corr 0.9918, residual sigma 13% of reference sigma; the sigma lower bound is 4.6x the
  screen), so a spurious fail is unlikely, but this is a condition of the result, not a footnote.

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

- B0_ref attempt 1 (request written 22:24:54): refused by the fleet cap ("10 instance(s) already running + 1
  requested exceeds BATCH_MAX_CONCURRENT_INSTANCES=8"; summary written 22:25:00, no report). Attempt 2: **an orphan
  request**. Its request file was written at 22:25:00, immediately after the refusal (the first driver version had no
  wait between retries), and its artifacts directory is empty: there is no summary, stderr, klt report or job id. The
  driver process therefore ended within seconds of writing that request, before `klt sim` recorded anything; the
  orphan-counting fix (commit 9ae1488) was committed at 22:25:42, under 50 s after the run started. The records do not
  show why the process ended, so **the cause is undetermined**. (An earlier version of this record attributed it to a
  590 s `timeout`; the timestamps rule that out and the claim is withdrawn.) Whether attempt 2 reached the fleet is
  also undetermined; submitted 6 s after a refusal with 10 instances already running, it was most likely refused too.
  It is counted against the cap anyway (the driver counts request files with no summary as attempts), the
  conservative choice, so B0_ref had one attempt left, which was submitted at 22:30:43 and succeeded. The driver was resumed from the
  same DUT snapshot and committed plan (`resume`), with a 300 s wait between retries added.
- B2, B3, B4: each three attempts, each refused with "N instance(s) already running + 1 requested exceeds
  BATCH_MAX_CONCURRENT_INSTANCES=8" (N = 8..12 other jobs from concurrent sweeps). Retry spacing 300 s. Per the plan the
  batches are recorded as FAILED_BATCH and were not retried further; the grid was NOT run locally. No sample is
  zero-filled; the three conditions are NOT_MEASURED.

The drift report's outcome flag reads `VERDICTS_PARTIAL` (exit code 2): the pairing evidence held for the measured
condition and every step reached a terminal state, but three of four conditions are `NOT_MEASURED`. The earlier
record's `VERDICTS_ISSUED` flag overstated this and is superseded (see the top of this record).

## Follow-up

Issue #196 stays open: its acceptance criteria require paired statistics at every declared condition, and this
plan's own stop-expansion rule says the remaining declared conditions still run after a failing condition (the rule
forbids expansion beyond the plan, it does not cancel declared conditions). So the B1 fail does not discharge C2-C4.
Measuring C2-C4 needs a new committed plan (the caps of this plan are spent) and fleet capacity; waiting longer
between attempts or a queueing submit would avoid the same outcome. The tool gaps (no queue/wait on capacity
refusals, runner/client version skew, implicit corner-index-keyed paired draws) are already tracked at
2AMLogic/klayout-tools: #3043, #2869, #2948, #2967, #2929, #2899.
