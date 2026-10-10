# Experimental variants: tail clamp for the fall-slew gap (issue #78)

**Result: negative.** A tail clamp, sized gm/ID-first and measured on the full
45-unit PVT matrix at two clamp strengths, makes **fall slew rate worse at all
15 points**. It also reduces output swing at all 15 points, reduces phase margin
at all 15 points (the ≥ 60° target is now missed at most corners), and makes the
buffer lose regulation at SS when the input is near or below mid-supply. Gain
and GBW improve slightly and quiescent power does not change. This candidate
does not close T1 item 5 and does not move toward closing it. No target was
relaxed. The canonical design (`design/`) and `spec/target-spec.md` are
untouched.

This directory holds experimental netlists only. These files are **not** the
design. `pvt_sweep.py --netlist` characterizes them, and each record snapshots
the exact bytes it measured.

| File | What it is |
|---|---|
| `tail-clamp.spice` | Candidate A: clamp sized for a 0.10 V tail clamp level (MCL = 8 × 15.495 µm / 1.2 µm) |
| `tail-clamp-vc050.spice` | Candidate B: the same circuit, sized for a 0.05 V clamp level (MCL = 4 × 10.370 µm / 1.2 µm) |
| `tail_clamp_sizing.py` | Simulator-free gm/ID sizing replay from the committed sweep (all sizing numbers below) |
| `compare.py` | Simulator-free comparison: worst value and binding corner per metric, the named points, and per-point deltas (all comparison numbers below) |

## Starting point (base-drift guard, #120)

#120 (grid-legal canonical MOS widths) has **not** landed. The variants are
built from `design/netlist/opamp_core.spice` at `9fb5db6`
(`sha256:feb7cff4…`). That is the DR-007 MOS sizing plus DR-010/#131's
grid-legal `XRz` length, 9.765 µm. The DR-007 netlist had 9.763 µm
(`sha256:6efc7494…`). The only edit is one **added** device, `XMCL`. No
existing device, width, length, multiplicity or ratio changed
(`diff design/netlist/opamp_core.spice sim/opamp-characterization/variants/tail-clamp.spice`
shows the header comments and the two `XMCL` lines only). The port order is
unchanged (`vdd vss inn inp out ibias`). The file is a flat body like the
canonical one, so `pvt_sweep.py` wraps it in its own `.subckt`.

Comparison baselines:

- `20261010-103340-ba1dfa8-0241c1`: the DR-007 netlist measured on the same
  fleet route (45/45, issue #77). This is the like-for-like baseline. Every
  "baseline" number below comes from this record.
- `20261001-074923-c317ff9`: the historical DR-007 record. It is identical to
  the record above at every worst-case value quoted here (see `compare.py`
  output; #77 documents the per-point agreement).
- The 2 nm `XRz` difference between the canonical file and DR-007 was measured
  at TT/27 °C in `records/20261010-102538-ba1dfa8-fe5399-rz-grid-comparison.md`.
  Fall slew rate is identical, PM moves +0.002°, swing moves +0.03 mV. That is
  negligible next to every effect reported here. No 45-unit fleet record of
  `feb7cff4…` itself exists.

Inherited off-grid dimensions (#50/#120 own them; deliberately not repaired
here): `XM3`, `XM4` and `XM6` have W = 4.634 µm, and `XMB1`, `XM5` and `XM7`
have W = 7.819 µm. `python3 design/bin/grid_check.py --classes passive,mos <variant>`
lists exactly those six. The new device `XMCL` (15.495 µm and 10.370 µm unit
widths) and both passives are on the 0.005 µm grid.

## Why a tail clamp: the mechanism being targeted

DR-007 diagnosed the SS/−40 °C fall-slew crawl as first-stage starvation. In the
unity-gain buffer, as `out` = `inn` falls toward the step's low level
(0.3·VDD = 0.486 V), the tail node is dragged toward vss. `M5` then drops into
deep triode and the pair current collapses. With it go the `M3`/`M4` mirror
current into `d2` and the Miller current through `Cc`.

Before choosing a circuit, single-corner local debug probes (SS/−40 °C,
`ngspice-42`, the `opamp_tran_sr` stimulus; these are **not** records) put
bounds on what a tail-side fix could buy at the binding corner:

| SS/−40 °C tail, single local probe | Fall SR (V/µs) |
|---|---|
| Canonical `M5` (reproduces the record, 11.03) | 11.02 |
| Ideal 10 µA sink, tail free to go **below** vss (non-physical bound) | 16.0 |
| Ideal sink that keeps 10 µA down to V(tail) ≈ 2 mV | 15.8 |
| … down to ≈ Ut (soft-saturation constant 20 mV) | 15.2 |
| … soft-saturation constant 50 mV | 12.8 |

Two conclusions follow, and the fleet records below do not contradict either:

1. **A tail fix cannot reach ≈ 20 V/µs.** Even a perfect tail stops near
   16 V/µs. At corners where nothing starves (TT/27 °C: 14.64 V/µs), the fall
   edge is set by the class-A sink: `M7`'s fixed 50 µA into CL + Cc plus
   parasitics, I/(2.5 pF) ≤ 20 V/µs. The first stage is not the limit there.
   This is #79's domain.
2. At SS/−40 °C, the step's low level (0.486 V) and its 20 % trigger level
   (0.616 V) are both **below the input pair's measured ICMR low edge** at that
   corner (0.717 V, record `20261009-103006-566b9a5`). The starvation is
   therefore an input-common-mode problem. A tail fix can only help by letting
   the tail current survive at a very small V(tail).

## The candidate circuit

`XMCL`: `nfet_01v8`, L = 1.2 µm (the `MB1`/`M5`/`M7` group length, so the clamp
level tracks the bias diode over PVT). Drain = `d1`, gate = `ibias`,
source = `tail`.

- At quiescent, V(tail) ≈ 0.25–0.35 V. `XMCL` sits far below its operating
  density and is effectively off.
- When the falling-edge overdrive pulls V(tail) toward vss, `XMCL` turns on and
  holds V(tail) near the clamp level. That keeps `M5` saturated (its full
  10 µA).
- The drain goes to `d1`, the side `M1` drives, not to vdd. The rescued tail
  current therefore flows through `M3` → `M4` → `d2` and turns `M6` off, which
  is the direction the falling edge needs. A clamp to vdd would hold `M5`
  saturated but would divert the current out of the first stage. That variant
  was rejected on this argument and not simulated.

### gm/ID sizing (from the committed sweep, `tt / 27 °C`, no simulation)

`python3 sim/opamp-characterization/variants/tail_clamp_sizing.py [--vclamp V --m N]`
reads `sim/gm-id-characterization/records/20260909-062847-35a9d46-full-sweep.csv`
(nfet, L = 1.2, W = 2 µm, |Vds| = 0.9 V, Vsb = 0). Interpolation is Vgs linear
in ln(Id) between the bracketing rows.

- Bias diode `MB1`: J0 = 5 µA / 7.819 µm = 0.639468 µA/µm, bracketed by the
  rows with gm/ID 18.973791 @ Vgs 0.62 V and 17.662394 @ 0.64 V (the same rows
  DR-007 cites). This gives **V(ibias) = Vgs(MB1) = 0.6355 V**.
- The clamp must carry the whole tail current (10 µA) at
  Vgs = V(ibias) − V_clamp.

| | Candidate A (`tail-clamp.spice`) | Candidate B (`tail-clamp-vc050.spice`) |
|---|---|---|
| Design clamp level V_clamp (tt/27 °C) | 0.100 V | 0.050 V |
| Vgs(MCL) at 10 µA | 0.5355 V | 0.5855 V |
| J_cl | 0.080678 µA/µm (J0/J_cl = 7.93) | 0.241134 µA/µm (J0/J_cl = 2.65) |
| W for 10 µA | 123.95 µm | 41.47 µm |
| Drawn | m = 8 × 15.495 µm (123.96 µm) | m = 4 × 10.370 µm (41.48 µm) |
| Implied clamp level over the 15 sweep points (Vsb = 0) | 0.084–0.127 V | 0.042–0.063 V |
| Drawn gate area added (W·L, **not** layout area) | 148.75 µm² (+97 % of the 153.13 µm² MOS gate area) | 49.78 µm² (+33 %) |

The sweep has Vsb = 0, but `XMCL`'s source sits at the clamp level. Body
effect therefore makes the real clamp level somewhat lower than printed. The
records, not this table, are the measurement. Ratios: `MB1 : M5 : M7` stays
1 : 2 : 10 and `M4 : M6` stays 1 : 10, unchanged. `XMCL` is not a mirror member
(its gate is shared with the mirror, but it operates as a common-gate clamp at a
deliberately lower density). Its width ratio to the `MB1` unit is 15.85
(candidate A) or 5.30 (candidate B).

## Records (append-only; all on the Spot batch fleet, `--fleet --backend batch`, DR-006 solver settings)

| Record | Netlist | Scope | Units | Failed |
|---|---|---|---|---|
| `20261010-162029-c8da429-97caac` | A | FS/125 °C `ac` gain screen | 1 | 0 |
| `20261010-162249-c8da429-a1db50` | A | full matrix (ac, tran_sr, dc_swing × 5 corners × 3 T) | 45 | **1** (`ac` SS/−40 °C, see below) |
| `20261010-162822-521c306-258165` | B | FS/125 °C `ac` gain screen | 1 | 0 |
| `20261010-162948-521c306-f0abf9` | B | full matrix | **45** | **0** |

Every record has `tools.ngspice: not invoked` (no local simulator), a DUT
snapshot whose sha256 equals the committed variant file
(`python3 sim/lib/dut_identity.py validate`), the saved requests and bodies
under `netlist-snapshots/<id>/`, and the klt responses plus per-corner raw
artifacts (`corner.cir`, `ngspice.log`, and for `dc-swing` the
`waveform.raw[.json]`) under `records/<id>-logs/`. Remote provenance is in
`klt_jobs[].remote`: job ids `klt-sim-*`, c7i/m6i.4xlarge spot instances. The
fleet runner reports klt 0.5.0 against client 0.7.0 (`runner_compatibility:
mismatch`, accepted with the default `warn`, as in #77's baseline). One submit
reported "fleet at capacity" and succeeded on retry 1/30.

**The failed unit in candidate A's record is a circuit result, not an
infrastructure failure.** At SS/−40 °C the AC bench's operating point (mid-supply
input 0.81 V, DC unity feedback) is **railed**. The measured DC gain is
−83.2 dB, so no 0 dB crossing exists and GBW/PM cannot be measured. The harness
correctly refuses to write a row. A local single-corner op probe of the same
bias shows V(out) = 48 nV, `M1` off (9e-18 A), `XMCL` 4.66 µA into `d1`, and
`M2` 4.03 µA. It was not rerun, because it would reproduce. Candidate B's
record is the complete 45-unit, zero-failure record for the comparison.

## Comparison with the DR-007 baseline

Produced by `python3 sim/opamp-characterization/variants/compare.py <candidate> 20261010-103340-ba1dfa8-0241c1 20261001-074923-c317ff9`.
"Worst" is the minimum, except for power, where it is the maximum.

| Metric (target) | Baseline worst @ binding corner | **B** (`…f0abf9`, 45/45) worst @ corner | A (`…a1db50`, 44 + 1 errored) worst @ corner | B vs baseline, per point |
|---|---|---|---|---|
| Open-loop DC gain (≥ 60 dB) | 61.64 dB @ FS/125 | 61.73 dB @ FS/125 — met | 61.93 dB @ FS/125 (SS/−40 absent: −83 dB, railed) | 15 better (+0.0005…+0.55 dB) |
| GBW (≈ 16 MHz) | 17.92 MHz @ SS/125 | 18.48 MHz @ FS/125 — met | 17.96 MHz @ SS/125 (SS/−40 absent) | 15 better (+0.28…+1.57 MHz) |
| Phase margin (≥ 60°) | 63.94° @ SF/27 | **56.37° @ SS/27 — missed at 8 of 15 points** | **48.31° @ SS/27 — missed at 13 of 14 measured points** | 15 worse (−3.3…−8.9°) |
| Rise SR (≈ 20 V/µs) | 19.88 @ SS/−40 | 19.96 @ SS/−40 | 20.23 @ SS/−40 | 11 better, 4 worse (−0.14…+0.96) |
| **Fall SR (≈ 20 V/µs)** | 11.03 @ SS/−40 | **10.84 @ SS/−40** | **8.22 @ SS/−40** | **15 worse** (−0.20…−2.89) |
| **Output swing** (≈ 1.39 Vpp estimate) | 0.948 Vpp @ SS/−40 | **0 Vpp @ SS (all three T) under the record's rule** | **0 Vpp @ SS (all three T), FS/125** | **15 worse** (−0.56…−1.43 V) |
| Quiescent power (≈ 128.7 µW @ 1.98 V) | 131.92 µW @ FF/125 | 131.93 µW @ FF/125 | 131.93 µW @ FF/125 | ≤ 0.21 µW change at any point |

Named points the issue requires:

| Point | Baseline | B | A |
|---|---|---|---|
| FS/125 °C gain | 61.64 dB | 61.73 dB | 61.93 dB |
| FS/125 °C phase margin | 64.63° | 58.47° (miss) | 51.64° (miss) |
| SS/−40 °C fall SR | 11.03 V/µs | 10.84 V/µs | 8.22 V/µs |
| SS/−40 °C swing | 0.948 Vpp | 0 Vpp (rule); 0.359 V unanchored window | 0 Vpp (rule); 0.318 V unanchored window |
| TT/27 °C fall SR | 14.64 V/µs | 11.77 V/µs | 8.77 V/µs |
| TT/27 °C swing | 1.431 Vpp | 0.723 Vpp | 0.678 Vpp |

Notes on the swing column. The record's `swing_row()` rule grows the
unity-slope window outward **from mid-supply**. At every SS point the
candidate's transfer curve jumps at about 0.79–0.89 V, right at mid-supply
(0.81 V). The window around the mid-supply point is therefore empty and the rule
reports 0 Vpp. That record value stands as written. For information only (not a
record field), the largest unity-slope window *anywhere* in the same committed
SS/−40 °C waveforms is 0.359 V (0.844–1.203 V) for B and 0.318 V for A. Both
are well below the baseline's 0.948 Vpp.

## Why it fails (measured; local single-corner probes are labelled as such)

1. **The clamp is a phantom input.** With its gate at the fixed `ibias` and its
   drain on `M1`'s side, `XMCL` acts like a third input transistor tied to the
   inverting side at a fixed equivalent voltage of roughly V(ibias) +
   n·Ut·ln(W_MCL/W_M1) ≈ 0.8 V. When the real input common mode falls toward
   that level, `XMCL` carries the `d1`-side current, `M1` cannot balance `M2`,
   and the output rails to vss. That sets a new hard low-side floor:
   - the swing lower edge moves from 0.005–0.30 V to 0.77–0.89 V (`dc-swing` CSVs);
   - candidate A rails the AC bench at SS/−40 °C;
   - both candidates rail at the slew step's 0.486 V low level at SS/−40 °C
     (local probes: settled V(out) ≈ 14 nV, against the canonical 0.48–0.50 V).

   So the measured "fall" at SS/−40 °C is partly an unregulated drop to the rail.
2. **Kickback on the shared bias line slows the fall.** `XMCL`'s gate shares
   `ibias` with `M7`'s gate. When V(tail) falls about 0.27 V, the coupling
   through `XMCL`'s gate capacitance pulls V(ibias) down during the edge.
   Local SS/−40 °C probe: −19 mV for A and −12 mV for B, against −5 mV for the
   canonical design. `I_D(M7)` falls from about 50 µA to about 34 µA for A.
   That cuts the class-A sink current, which is what limits fall slew rate at
   every corner. It is consistent with the record's fall SR loss at the
   unstarved corners: −2.1…−2.9 V/µs for B and −4.9…−5.9 V/µs for A. The
   ibias dip was probed only at SS/−40 °C; elsewhere this mechanism is
   inferred, not isolated.
3. **The phase-margin loss is mostly the added capacitance at `d1` and `tail`.**
   Attribution probes at FS/125 °C (local, AC bench bias) on candidate A, whose
   record value is PM 51.64°:
   - zeroing `XMCL`'s junction areas gives 52.65° (≈ 1° from junctions);
   - driving `XMCL`'s gate from an ideal buffer copy of `ibias` gives 55.3°
     (≈ 3.7° from coupling into the shared bias line);
   - the remaining ≈ 8–9° of the 13° loss comes from `XMCL`'s other
     capacitance and conduction at `d1`/`tail` and was not isolated further.

   The DC gain and GBW gains are small and come from the same added conduction
   at the mirror node.

## Costs

- **Quiescent power**: unchanged within 0.21 µW (B) or 0.68 µW (A) at any
  point. The worst point stays 131.93 µW @ FF/125 °C (baseline 131.92 µW). The
  clamp adds no bias branch.
- **Drawn gate area estimate** (ΣW·L of MOS gates, from the netlist): 153.13 µm²
  for the baseline. A adds 148.75 µm² (+97 %) and B adds 49.78 µm² (+33 %).
  Gate width rises from 169.3 µm by 123.96 µm (A) or 41.48 µm (B). This
  excludes `Cc` (244 µm²) and is **not** a post-layout area. No layout was
  done.
- Device/group ratios: unchanged (see above). One device was added.

## What this means for #47 / #79 (not a decision; inputs only)

- A tail clamp at the `ibias` gate cannot be tuned out of this failure. The
  clamp level that protects `M5` (≥ 3–4 Ut) is exactly what creates the
  phantom-input floor. A weaker clamp (B) only moves toward "no clamp".
- The unstarved fall-SR ceiling (≈ 14.6 V/µs at TT, bounded by `M7`'s 50 µA
  into ≈ 2.5 pF) is untouched by any first-stage change. That points the
  remaining gap at the output stage (#79).
- At SS/−40 °C the slew bench's low level sits below the measured input-pair
  ICMR. Any candidate's SS/−40 °C fall number mixes slewing with input-range
  limits, and the per-point records should be read with that in mind. The
  stimulus was deliberately left unchanged so the results stay comparable.

## Process notes (for the audit trail)

- A first full-matrix launch of candidate A was stopped by the operator about
  1 min in: the agent's background-task timeout was too short for the expected
  run time. That stopped the local `klt sim` clients only. The fleet jobs they
  had already submitted were not cancelled from this side, and their results
  were not retrieved. Only empty `-logs/klt-ac{,-iq}/` directories and an
  unwritten snapshot directory existed (no record JSON and no measurement).
  They were deleted before anything was committed. The relaunch is record
  `…a1db50`.
- Local `ngspice-42` was used only for the single-corner debug and attribution
  probes cited above. They are not records and are not committed. Every PVT
  number in the tables comes from the fleet records.

## Reproduce

```bash
python3 sim/opamp-characterization/variants/tail_clamp_sizing.py                      # candidate A sizing
python3 sim/opamp-characterization/variants/tail_clamp_sizing.py --vclamp 0.05 --m 4  # candidate B sizing
python3 sim/opamp-characterization/bin/pvt_sweep.py --fleet --backend batch --corners fs --temps 125 --analyses ac \
    --netlist sim/opamp-characterization/variants/tail-clamp-vc050.spice                 # gain screen
python3 sim/opamp-characterization/bin/pvt_sweep.py --fleet --backend batch --analyses ac,tran_sr,dc_swing \
    --netlist sim/opamp-characterization/variants/tail-clamp-vc050.spice                 # 45 units
python3 sim/opamp-characterization/variants/compare.py 20261010-162948-521c306-f0abf9 \
    20261010-103340-ba1dfa8-0241c1 20261001-074923-c317ff9
```
