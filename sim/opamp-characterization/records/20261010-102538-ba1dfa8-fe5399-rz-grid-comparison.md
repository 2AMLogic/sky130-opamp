# XRz grid-legal length: baseline vs candidate (issue #131, DR-010)

Append-only comparison of two single-point `pvt_sweep.py` records on the same
MOS sizing; only XRz `L` differs (9.763 -> 9.765 um). Each record cites the DUT
snapshot it ran against (`dut.sha256` in its `.json`).

| Role | Record | DUT netlist sha256 | XRz L |
|---|---|---|---|
| baseline | `20261010-102529-ba1dfa8-81edd1` | `6efc7494e1c27af3623c702a7a55806da59bd2346d3651d9ea23f71ecaf79ace` (= the pre-change `opamp_core.pair.json` netlist pin) | 9.763 |
| candidate | `20261010-102538-ba1dfa8-fe5399` | `feb7cff49291aa308cbe3c07f5ea207f73fdf73110ac24647aacdb4753db9530` (= the post-change pin) | 9.765 |

Conditions (identical): `--corners tt --temps 27 --analyses ac,tran_sr,dc_swing`,
VDD 1.8 V, CL 2 pF, typical R+C corner, pinned PDK. 6 runs, 0 failed, no
measurement missing.

**Scope limit, stated plainly.** This is ONE corner (tt / 27 C), not the
5 x 3 PVT grid. `pvt_sweep.py`'s `ac`, `tran_sr` and `dc_swing` analyses drive
local `ngspice -b` per point (45 per analysis); they are not `klt sim`
requests, so they cannot go to the Spot batch fleet, and hand-launching that
grid on a shared dispatch worker is disallowed. The fleet-capable analyses
(`icmr`, `cmrr`, `tran_step`) do not measure gain/GBW/PM/SR/swing. The full-grid
comparison therefore needs those three analyses ported to `klt sim` requests
(not done here; no fleet submit was attempted, so no submit error exists).
Given the electrical delta below (+0.018 % in R), the one-corner result is
supporting evidence, not a substitute for a grid run.

| Metric (tt / 27 C) | Baseline | Candidate | Delta |
|---|---|---|---|
| DC gain (dB) | 65.8153 | 65.8153 | 0 |
| GBW (MHz) | 22.5140 | 22.5141 | +0.0004 % |
| Phase margin (deg) | 65.4273 | 65.4291 | +0.0017 deg |
| Iq (uA) | 65.7448 | 65.7448 | 0 |
| Slew rise (V/us) | 20.5860 | 20.5860 | 0 |
| Slew fall (V/us) | 14.6440 | 14.6440 | 0 |
| Output min (V) | 0.120036 | 0.120011 | -0.025 mV |
| Output max (V) | 1.530981 | 1.530981 | 0 |
| Swing Vpp (V) | 1.410945 | 1.410971 | +0.026 mV |

No regression: every metric is unchanged or moves by less than the simulator's
own resolution of interest. **Existing target gaps, unchanged and not relaxed:**
fall slew rate is 14.64 V/us at tt/27 against the ~20 V/us target (the known
tail-starvation gap owned by #47/#78/#79, DR-007); this change neither causes
nor affects it. `spec/target-spec.md` is untouched.
