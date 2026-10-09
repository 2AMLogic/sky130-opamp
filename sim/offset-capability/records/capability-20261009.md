# Capability record 2026-10-09 (append-only; issue #52)

Not T1 item 6 evidence; no yield/pass claim. See ../README.md for the summary.

## Identity

- Repo SHA at probe time: `3f7fe3cbdf52b1a13ad635a1b70d4e219efb363d` (main; branch feature/issue-52, probe files uncommitted at run time).
- PDK pin (`sim/opamp-characterization/pdk.json`): sky130A, open_pdks `c6d73a35f524070e85faff4a6a9eef49553ebc2b`; installed volare version dir `~/.volare/volare/sky130/versions/c6d73a35...` matches. Pin unchanged.
- `libs.tech/ngspice/sky130.lib.spice` sha256 `17c208a699228f5acb87bf59c09c22a4c4d3937b6766b4957737d34e8e075f64`; the batch response's `environment.models_lib_sha256` is identical, so fleet and local resolved the same library text.
- Client: `klt 0.7.0+g4cbdfa769875`, local ngspice-42. Fleet: `runner_klt_version 0.5.0`, ngspice 46, `runner_compatibility: mismatch` (warn only).

## Model inspection (PDK-relative to `$PDK_ROOT/sky130A/`)

- Library: `libs.tech/ngspice/sky130.lib.spice`. Section `tt` sets `.param mc_mm_switch=0`, `mc_pr_switch=0`; section `tt_mm` sets `mc_mm_switch=1`, `mc_pr_switch=0`. Both then `.include "corners/tt.spice"`, then the `r+c/res_typical__cap_typical{,__lin}.spice` files. (Include order inside the section: switch params, MOS corner file, R+C files, specialized cells.) The same names exist for `ss/ff/sf/fs` and `*_mm`.
- `corners/tt.spice` includes, among others: `libs.ref/sky130_fd_pr/spice/sky130_fd_pr__nfet_01v8__tt.pm3.spice`, `...nfet_01v8__mismatch.corner.spice`, `...pfet_01v8__tt.corner.spice` (which includes `...pfet_01v8__tt.pm3.spice`), `...pfet_01v8__mismatch.corner.spice`. The `__mismatch.corner.spice` files only define `.param ..._slope` Pelgrom-style coefficients (e.g. `nfet_01v8__vth0_slope=3.356e-03`).
- Random-variable expression: in `nfet_01v8__tt.pm3.spice` 540 occurrences and in `pfet_01v8__tt.pm3.spice` 432 occurrences of `MC_MM_SWITCH*AGAUSS(0,1.0,1)*(<slope>/sqrt(l*w*mult))` (e.g. `vth0 = {0.5190093+MC_MM_SWITCH*AGAUSS(0,1.0,1)*(sky130_fd_pr__nfet_01v8__vth0_slope/sqrt(l*w*mult))}`), also toxe, voff, etc. These sit inside subcircuit-expanded model cards, hence are drawn per instance.
- Rz: `sky130_fd_pr__res_high_po_1p41.model.spice` lines 47/49 (`res_match`, `rend`) use `MC_MM_SWITCH*AGAUSS(0,1.0,1)`; Cc: `sky130_fd_pr__cap_mim_m3_1.model.spice` line 25 (`czero`). So `tt_mm` also perturbs Rz and Cc; with `mc_mm_switch=0` all of these terms are exactly zero.
- No `MC_PR_SWITCH` reference in the nfet/pfet 01v8 models or Rz/Cc models found by grep; global process variation is the deterministic corner set, distinct from local mismatch.
- Empirical per-instance independence: identical devices XN1/XN2 and XP1/XP2 at identical bias differ by up to ~1 uA (nfet) under `tt_mm` and by exactly 0.0 under `tt` (same seeds).
- Note: klt's own `family_mismatch` report states `mosfet active: true`; it did not list resistor or capacitor families, so those effects here are from the model-file inspection above, not from klt's report.

## Accepted request (shape; full requests in `*.request.json`)

```
"corners": {"process": ["tt_mm"], "supply_v": {"vdd": [1.8]}, "temperature_c": [27.0]},
"monte_carlo": {"n": 4, "seed": 20261009, "vary": "mismatch"},
"analysis": {"kind": "dc", "args": "Vd -0.03 0.03 2e-05"},
"batch": {"runner_version_check": "warn"}
```

`monte_carlo` is a top-level key; `seed`, `n`, `vary` are echoed in `environment.monte_carlo` (plus `family_mismatch`). Per sample, `corners[].monte_carlo = {sample_index, seed(rndseed), process_seed, mismatch_seed}` and `corner_id` gets `/mc<i>`. klt's generated deck puts `.options seed=<rndseed>` before the `.lib`. Seed A (20261009) maps to rndseeds 1189634286, 328376976, 1668344203, 754629558; seed B (20261010) to 565189081, 493179282, 1473865942, 1841338045. `process_seed` is constant across samples under `vary: mismatch`.

## Command log (host `KLT_SIM_BACKEND=batch`; each = one `klt sim` request via `bin/offset_probe.py`)

| record (prefix 2026-10-09 UTC) | bench | what | outcome | fleet job |
|---|---|---|---|---|
| 102644-pair-localdbg | pair | local single unit, 1-point sweep | error: `.meas ... out of interval` -> reported as error, not value | local |
| 102701-pair-localdbg2 | pair | local, tt_mm, no MC | ok | local |
| 102712-offset-localdbg | offset | local, tt, `.meas at=sweep end` | error (out of interval) | local |
| 102729-offset-localdbg2 | offset | local, tt | Vos +150.6 uV | local |
| 102740-offset-localdbg3 | offset | local, tt_mm, no MC | Vos +3.954 mV | local |
| 102755-pair-seedA | pair | A n=4 | ok | klt-sim-7f4e281c6866 |
| 102923-pair-seedB | pair | B n=4 | ok | klt-sim-2d3e764661f2 |
| 103043-pair-seedA-replay | pair | A n=4 | identical to seedA | klt-sim-a1addbf2cba7 |
| 103206-pair-control-off | pair | tt, A | fleet capacity error (BATCH_MAX_CONCURRENT_INSTANCES=8) | none |
| 103347-pair-control-off-retry | pair | tt, A | dn=dp=0 all four | klt-sim-25ce1d355c4f |
| 103513-offset-seedA | offset | A | ok | klt-sim-e122bb5b0979 |
| 103634-offset-seedB, 103839-offset-seedB-r2 | offset | B | fleet capacity error (twice) | none |
| 104045-offset-seedB-r3 | offset | B | ok | klt-sim-3ca2c0f1edaa |
| 104206-offset-seedA-replay | offset | A | identical to seedA | klt-sim-0124b344371c |
| 104327-offset-control-off | offset | tt, A | Vos +151 uV, all four | klt-sim-356475c7afe7 |

Only the local rows were launched with `--backend local` (single unit each). Each is one invocation; no loops of ngspice, no background jobs.

## Tolerance evaluation (declared in ../README.md before evaluating)

- Replay: pair `dn`, `dp` and offset Vos identical at printed precision; limit 1 nA / 40 uV -> pass.
- Pair control: |dn|,|dp| = 0 <= 1 nA -> pass.
- Offset control: spread 0 uV <= 40 uV; baseline +151 uV (local +150.6 uV) -> pass.
- Seed sensitivity: seed A vs seed B differ on all samples; max |dn| A 1.08 uA, B 0.37 uA > 10 nA -> pass.
- Failure semantics: unit tests (`tests/test_offset_probe.py`) cover missing output, absent measurement, NaN, no crossing/rail saturation, error status and a synthetic known-offset crossing; the real `.meas` out-of-interval errors above were surfaced as errors.

## Upstream filing

None. The only batch failures were fleet concurrency capacity, a shared-resource condition and not a reproducible runner defect. The 0.5.0 runner executed `monte_carlo` correctly, so no tool gap was observed in this probe.
