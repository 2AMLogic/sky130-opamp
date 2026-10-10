# offset-capability — seeded-mismatch capability probe (issue #52)

**This directory holds the #52 capability probe and, since #85, the offset Monte
Carlo campaign (`records/campaign-20261009-offset-mc300.md`; measured data only,
no limit, no ratification).** The probe text below is the original #52 scope:
**this is a capability probe, not the offset Monte Carlo campaign.** A handful
of samples (n=4 per request) establish whether the pinned PDK's mismatch models
and `klt sim`'s seeded `monte_carlo` path work end to end. They **do not
satisfy T1 item 6**, give no offset distribution, no yield/pass claim and no
offset limit. `spec/target-spec.md` §2's offset row stays OPEN/TBD and its
`3σ, mismatch MC N≥300 + corners` basis stays *proposed*, not ratified. T1
item 6's signoff status and the characterization envelope's MC-evidence status
are unchanged.

Full evidence index: [`records/capability-20261009.md`](records/capability-20261009.md)
(append-only; new findings go in a new dated file).

## Outcome (cold-start summary)

| Capability | Classification |
|---|---|
| Pinned PDK has usable local-mismatch models for the nfet/pfet (and Rz/Cc) used by `opamp_core.spice` | **supported** |
| Mismatch enable mechanism selectable through `klt sim` | **supported** (`corners.process: "tt_mm"`) |
| Independent per-instance randomness | **supported** (device-pair diagnostic, n=8 pair samples) |
| Global process variation distinct from local mismatch | **supported, by construction** (corners `tt/ss/ff/sf/fs` are deterministic; the only AGAUSS draws in the 01v8 MOS/Rz/Cc models are `MC_MM_SWITCH`-gated local terms; no `MC_PR_SWITCH` use found in those models) |
| `klt sim` `monte_carlo` request accepted, client 0.7.0 | **supported** |
| Same request on the batch fleet (runner reports klt 0.5.0) | **supported** (honored; runner/client `mismatch` warning only) |
| Seed -> sample mapping returned | **supported** (`corners[].monte_carlo`) |
| Replay of a seed reproduces results | **supported** (bit-identical at recorded precision, both benches) |
| Different seed changes results | **supported** |
| Mismatch-off control returns the systematic baseline | **supported** |
| Op-amp Vos extraction (DC crossing, failure-safe) | **supported** (tt/27C/1.8 V only) |
| Distribution statistics, N=300 per corner, TT/SS/FF (+SF/FS) | **measured in #85**, see [`records/campaign-20261009-offset-mc300.md`](records/campaign-20261009-offset-mc300.md): sigma 8.4-8.7 mV, 0 failed of 300 at every corner; no yield/pass claim |
| Fleet capacity for a 300-sample campaign | **supported with retry** (3 x 100 chunks per corner completed; one `batch_no_capacity` refusal, retried) |

## Reproduce

```
python3 sim/offset-capability/bin/offset_probe.py run --bench pair   --label seedA --mismatch on  --seed 20261009 --n 4
python3 sim/offset-capability/bin/offset_probe.py run --bench pair   --label seedB --mismatch on  --seed 20261010 --n 4
python3 sim/offset-capability/bin/offset_probe.py run --bench pair   --label seedA-replay --mismatch on --seed 20261009 --n 4
python3 sim/offset-capability/bin/offset_probe.py run --bench pair   --label control-off --mismatch off --seed 20261009 --n 4
# same four with --bench offset
```

The script only builds a `klt sim` request and invokes `klt sim` (backend from
`$KLT_SIM_BACKEND`, `batch` on dispatch hosts); it never runs ngspice itself.
Records are written under `records/` and are never overwritten. `--dry-run`
writes only the request. Unit tests (no simulator):
`python3 -m unittest discover -s tests` (`tests/test_offset_probe.py`).

## Benches

- `bench/pair_diag.cir` — two identical nfet_01v8 and two identical pfet_01v8
  (L=0.5, W=1, `.option scale=1u`) at identical bias; measures drain-current
  difference within each pair (`dn` = nfet pair, `dp` = pfet pair).
- `bench/offset_dc.cir` — the committed op-amp (`design/netlist/opamp_core.spice`)
  open loop, VDD 1.8 V, ideal 5 uA Iref, 2 pF load (PSRR-bench conventions),
  TT/27 C. Vinn = 0.9 V, Vinp = 0.9 V + vd.

Offset definition: **Vos = V(inp) - V(inn) at the first rising crossing of
v(out) = VREF = VDD/2 = 0.9 V**, common mode (V(inn)) = 0.9 V, bracket
vd in [-30 mV, +30 mV], step 20 uV, crossing linearly interpolated by
ngspice `.meas ... when`. A sample is a **failed measurement** (never 0) if
the corner status is not `pass`, any measurement is missing/non-finite, or
v(out) at the bracket ends does not straddle VREF (rail saturation / no
crossing). The extractor does not subtract the systematic baseline.

## Predeclared tolerances (set before evaluating the control)

- Extraction resolution: one sweep step, 20 uV; klt reports `.meas` values to
  ~6 significant digits, so Vos is resolved to ~1 uV at these magnitudes.
- Replay/control repeatability (Vos): <= 2 steps = **40 uV**.
- Pair control: |id1 - id2| with mismatch off <= **1 nA**.
- Randomized pair diagnostic must exceed **10 nA** (nfet pair `dn`) for at least
  one sample per seed and must differ between the two seeds.
- The systematic baseline is not required to be zero.

## Results (tt, 27 C, 1.8 V; n=4 per request; base seeds 20261009 = A, 20261010 = B)

Pair diagnostic, `dn` = Id(XN1)-Id(XN2) at Vgs=0.8 V:

| request | dn (A), samples mc0..mc3 |
|---|---|
| A, tt_mm | +6.57e-7, +1.081e-6, +8.30e-7, -7.52e-7 |
| B, tt_mm | -3.75e-7, +1.35e-7, -5.6e-8, +1.0e-8 |
| A replay | identical to A to every printed digit |
| A seeds, tt (mismatch off) | 0, 0, 0, 0 (exactly; tolerance 1 nA) |

The pfet pair difference `dp` is also nonzero in all 8 randomized samples
(|dp| 6e-10 .. 1.8e-8 A) and exactly 0 with mismatch off.

Op-amp Vos (V), same sample/seed mapping:

| request | mc0 | mc1 | mc2 | mc3 |
|---|---|---|---|---|
| A, tt_mm | +2.954e-3 | +4.097e-3 | -6.532e-3 | +2.524e-3 |
| B, tt_mm | +10.687e-3 | +6.854e-3 | +1.110e-3 | -10.570e-3 |
| A replay | identical to A (max |diff| 0 at printed precision; tol 40 uV) | | | |
| tt, mismatch off (seed A) | +0.151e-3 (all four) | | | |

Systematic baseline Vos(tt, no mismatch) = +151 uV (also +150.6 uV from the
single-unit local run, `ngspice-42` vs fleet `ngspice-46`; difference 0.4 uV,
within tolerance). All of the above pass the predeclared tolerances. Seed A and
seed B yield different values, and the sample spread is millivolt-scale; with
n=4 this is a function check, **not** a sigma estimate (sample sd 4.9 mV and
9.3 mV for A and B shows exactly how unconverged it would be).

## Observed friction

- The first two attempts of one request hit
  `BATCH_MAX_CONCURRENT_INSTANCES=8` ("8 instance(s) already running + 1
  requested exceeds ...") because other sweeps shared the fleet. Retried
  sequentially; failed attempts are kept as records. This is a shared-capacity
  condition, not a verified runner defect, so no upstream issue was filed.
- Fleet runner reports klt 0.5.0 against client 0.7.0+g4cbdfa769875
  (`runner_compatibility: mismatch`); `monte_carlo` was nevertheless executed
  with correct seeds. Request options unknown to 0.5.0 may be silently ignored
  in general (cf. `measurements[].expr`, klayout-tools#2877), so every campaign
  request should keep using `.meas` cards and verify the echo.
- A single-point DC sweep (`start == stop`) and a `.meas ... at=<sweep end>`
  both fail ("out of interval") in ngspice; the probe uses a 3-point sweep and
  measures at stop minus one step. The failure was reported as a measurement
  error by klt (not zero), which exercised the failure path for real
  (`*-pair-localdbg*`, `*-offset-localdbg.*`).

## Outline of the later full campaign (not part of this issue)

Run `bench/offset_dc.cir` through `klt sim` on the batch backend with
`monte_carlo {n, seed, vary: "mismatch"}` over at least TT, SS and FF (ideally
all five corners, plus VDD/temperature per the characterization grid),
recording base seed, N and per-sample seeds, reporting mean and sigma per
corner and the failed-sample count (failures excluded from stats only with
the count shown). **N >= 300 is the currently proposed statistical basis,
pending ratification** in `spec/` with a decision record; the offset limit
itself is likewise unratified. Prerequisites to resolve first: a batch runner
at a klt matching the client, fleet capacity for 3+ sequential requests of 300
samples, and a decision on whether Rz/Cc mismatch (also enabled by `tt_mm`)
belongs in the offset budget.

## Campaign results (#85)

The campaign outlined above was run: `offset_probe.py campaign` (resume with
`--only corner:chunk`, re-aggregate with `summarize`), N=300 per corner
(3 x 100, base seed 20261085) for TT, SS, FF and additionally SF, FS. Result,
seeds, failed counts, interrupted-request ledger and the resolution of the
version-mismatch and Rz/Cc prerequisites are in
[`records/campaign-20261009-offset-mc300.md`](records/campaign-20261009-offset-mc300.md)
and its `*-campaign-offset-mc300-final-*.campaign.json`. These are measured
values only: N>=300 and any offset limit remain unratified, and
`spec/target-spec.md` is unchanged.

## Matched-group sizing feasibility (#144)

Whether enlarging the mirror and input pair can reach the DR-009 *proposed*
σ ≤ 0.275 mV: [`records/campaign-20261010-sizing-feasibility.md`](records/campaign-20261010-sizing-feasibility.md),
disposition in the proposed [`DR-011`](../../spec/decision-records/DR-011-offset-closure-sizing-feasibility.md).
Finding: no (σ 4.25 / 3.22 / 2.34 mV for three bounded candidates, phase
margin fails the ratified row from the first step; ≈ 280–580× matched area
needed). Exploratory N = 100 at tt only; canonical design unchanged.

```
python3 sim/offset-capability/bin/sizing_feasibility.py bounds     # simulator-free area bounds
python3 sim/offset-capability/bin/sizing_feasibility.py gmid       # gm/ID-first, committed sweep
python3 sim/offset-capability/bin/sizing_feasibility.py gen --check # candidates == regeneration, on grid
python3 sim/offset-capability/bin/sizing_feasibility.py op         # ONE local single-corner OP deck
python3 sim/offset-capability/bin/offset_probe.py campaign --label sizing144-m2p1 --base-seed 20261085 \
    --corners tt --n-total 100 --chunk 100 --netlist sim/offset-capability/candidates/opamp_core.m2p1.spice
python3 sim/opamp-characterization/bin/pvt_sweep.py --fleet --backend batch --analyses ac,tran_sr,dc_swing \
    --netlist sim/offset-capability/candidates/opamp_core.m2p1.spice
python3 sim/offset-capability/bin/sizing_feasibility.py summarize --pvt '{"m2p1": "<pvt record id>", ...}'
```

`candidates/` holds generated, non-canonical netlists (not design inputs).
