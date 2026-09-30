# opamp_core PVT characterization

Op-amp-**level** (not bare-device) ngspice testbenches that measure
`design/netlist/opamp_core.spice`'s open-loop DC gain, GBW, phase margin,
slew rate, output swing, and quiescent power — the six `[P]`-tagged
performance rows in `spec/target-spec.md` §2 — across the confirmed 5-corner
sky130 1.8 V-core process grid (`tt, ff, ss, sf, fs`) at three temperatures
(`-40 °C, 27 °C, 125 °C`). This is this block's first **circuit-level**
`sim/` evidence; the sibling
[`../gm-id-characterization/`](../gm-id-characterization/README.md) is a
bare-device sweep and does not, and never claimed to, measure any of these
six rows.

Per `CLAUDE.md`'s "no claim without a testbench": every `[P]` row in
`target-spec.md` §2 has, until this issue, been a hand sizing estimate from
[`DR-002`](../../spec/decision-records/DR-002-device-sizing.md), which says
so itself in its own "Open items" — *"No operating point, gain, bandwidth,
phase margin, slew rate, swing, noise or power figure in this record has
been simulated."* This experiment is that simulation. **The result is mixed
by design, not by mistake**: two rows measure close to their DR-002 estimate
(quiescent power, phase margin), and four contradict some part of theirs —
either the predicted worst-case corner, the estimated magnitude, or (for
slew rate) an assumption (rise/fall symmetry) the hand estimate did not even
state as an assumption. Every contradiction is reported below; none is
hidden or softened.

## Headline result

| Row | Target | Worst measured (this sweep) | DR-002 `[P]` estimate | Verdict |
|---|---|---|---|---|
| Open-loop DC gain | ≥ 60 dB | **69.72 dB** @ SS/125°C | 72.8–75.1 dB (named corners) | Target met everywhere; **worst-case corner contradicted** (predicted SS/-40°C, actual SS/125°C) |
| GBW (into CL=2pF) | ≈ 16 MHz | **8.45 MHz** @ SS/125°C | 13.98–17.94 MHz (named corners) | **Contradicted** — SS/-40°C itself measures 9.56 MHz, 53% of its 17.94 MHz estimate |
| Phase margin | ≥ 60° | **64.09°** @ SF/27°C | not separately computed (only `p2/GBW` proxy) | Target met everywhere (margin ≥ 4°); predicted binding corner (FF/125°C) close but not the true worst |
| Slew rate | ≈ 20 V/µs | **1.73 V/µs (fall)** @ SS/-40°C | 20 V/µs (assumed symmetric) | **Contradicted** — fall SR at the worst corner is ~9% of the estimate; rise SR alone stays within ~15% |
| Output swing | ≈ 1.39 V (86%) @ SS/-40°C | **0.855 V (52.8%)** @ SS/-40°C | 0.072–1.464 V (≈86%) at SS/-40°C | Worst-case corner **confirmed**; magnitude **contradicted** (62% of estimate) |
| Quiescent power | ≈ 128.7 µW @ FF/125°C | **130.7 µW** @ FF/125°C | 128.7 µW @ FF/125°C | **Confirmed** (+1.6%), including the binding corner |

Full per-row detail, every one of the 45 measured points, and the exact
DR-002 citations each verdict is checked against, are in "Results by row"
below.

## Cold-start invocation

Given the pinned PDK (below) is installed:

```bash
python3 sim/opamp-characterization/bin/pvt_sweep.py
```

Renders `testbench/opamp_{ac,tran_sr,dc_swing}.spice.tmpl` once per
(analysis, corner, temperature) point (3 × 5 × 3 = 45 ngspice runs), drives
`ngspice -b` on each rendered deck, and writes a new timestamped record under
`records/` (never overwriting a prior one — append-only, per `CLAUDE.md`).
Takes roughly 6–8 minutes on a single core (45 ngspice invocations, ~7–15 s
each — this testbench's device count and Rz/Cc subcircuit expansion cost
more per-run than the sibling bare-device sweep's ~1.4 s). Exits non-zero if
any run's `.meas` measurement is missing or ngspice itself errors (see
`bin/pvt_sweep.py`'s per-run `try`/`except`, which still runs every other
point before reporting the aggregate failure — a genuinely useful property
for triage, since one broken point should not hide 44 good ones).

```bash
python3 sim/opamp-characterization/bin/pvt_sweep.py --check-env   # tool/PDK check, no simulation
python3 sim/opamp-characterization/bin/pvt_sweep.py --corners ss --temps -40,125 --analyses ac
```

**PDK pin**: [`pdk.json`](pdk.json) — sky130A, open_pdks commit
`c6d73a35f524070e85faff4a6a9eef49553ebc2b`, the **same pin** as
[`../gm-id-characterization/pdk.json`](../gm-id-characterization/pdk.json)
and confirmed installed and matching in this environment (2026-09-15).
`bin/pvt_sweep.py` resolves the 5-corner MOS grid from that sibling
experiment's own `pdk.json`/`corners/model-files.json` directly (reads them,
does not duplicate or re-derive them, per this issue's acceptance criteria)
and adds only the R+C ("typical") corner choice this experiment introduces
in its own `pdk.json` — see "R+C corner" below. The *code* that performs that
resolution is likewise shared rather than copied: it lives once in
[`../lib/spice_harness.py`](../lib/spice_harness.py), and `bin/pvt_sweep.py`
subclasses its `Pdk` only to add this experiment's R+C includes (issue #23).

```bash
volare enable --pdk sky130 c6d73a35f524070e85faff4a6a9eef49553ebc2b
```

## Layout of this directory

| Path | Contents |
|---|---|
| `pdk.json` | This experiment's own addition to the PDK pin: the R+C ("typical") corner include files, and why both are required together |
| `testbench/opamp_ac.spice.tmpl` | Open-loop AC gain/phase/Iq testbench (DC-servo bias) |
| `testbench/opamp_tran_sr.spice.tmpl` | Unity-gain-buffer large-step slew-rate testbench |
| `testbench/opamp_dc_swing.spice.tmpl` | Unity-gain-buffer DC transfer (output swing) testbench |
| `bin/pvt_sweep.py` | The sweep runner — the one cold-start command above |
| `../lib/spice_harness.py` | Shared (not per-experiment) PDK resolution, deck rendering, tool-version and git-SHA helpers `bin/pvt_sweep.py` imports |
| `netlist-snapshots/<record_id>/` | Every rendered deck for that record (45 files), for provenance |
| `records/<record_id>-{ac,tran-sr,dc-swing}.csv` | Every measured quantity at every (corner, temperature) point — the primary evidence artifacts |
| `records/<record_id>-logs/` | The raw ngspice stdout/stderr for every one of the 45 runs, so a claimed measurement can be spot-checked against the actual simulator output (per this issue's own test plan) |
| `records/<record_id>.json` / `.md` | Machine-readable / human-readable record metadata and headline table |

## Methodology

`design/netlist/opamp_core.spice` is xschem's **flat top-level** netlist for
this block — its `.subckt opamp_core ...`/`.ends` lines are commented out in
the committed file, because `opamp_core.sch` is this repo's top schematic,
not a hierarchical leaf cell (confirmed directly: `grep '^\*\*\.subckt'
design/netlist/opamp_core.spice` matches, i.e. those lines start with `*`,
SPICE's comment character). Every testbench in this experiment therefore
`.include`s that file directly and drives its own node names (`vdd`, `vss`,
`inn`, `inp`, `out`, `ibias`) straight from the testbench, with **no** `X`
subcircuit instantiation wrapper — confirmed necessary and sufficient by
directly running a minimal `.op` deck against the included netlist before
any testbench in this experiment was written.

**Bias**: `ibias` is driven by `Iref vdd ibias dc 5u`, a current source from
`vdd` into the `ibias` node — matching `design/opamp_core.sch`'s header
("5 µA sunk into the block") and [`DR-002`](../../spec/decision-records/DR-002-device-sizing.md)
(a)'s adopted reference-branch current. `MB1`'s diode connection then turns
that current into the gate bias for `M5`/`M7`.

**R+C corner**: sky130's resistor/capacitor process corner is an axis
orthogonal to the 5-corner MOS grid (like temperature is orthogonal to it in
[`../gm-id-characterization/corners/README.md`](../gm-id-characterization/corners/README.md)'s
"What is not a corner axis here"). Every MOS corner in this experiment's 5×3
grid is run at the same **typical** R+C corner
(`libs.tech/ngspice/r+c/res_typical__cap_typical{.spice,__lin.spice}`) — a
stated methodology choice, not a re-derivation of `Rz`/`Cc`'s own process
spread (`DR-002`'s own Consequences section already flags "`Rz` does not
track `gm2` over PVT" as an open question for a future compensation-specific
bench, out of scope here). **Both** R+C include files are required together:
the base file defines the `tol_m3`/`rm3`/`rcvia3`-class parameters
`sky130_fd_pr__res_high_po_1p41`'s model needs, the `__lin` file separately
defines `camimc`/`cpmimc`/`*_var_mult` parameters `sky130_fd_pr__cap_mim_m3_1`'s
model and the resistor's own process-variation terms need — confirmed by
directly running ngspice against `design/netlist/opamp_core.spice` with each
file included alone (both fail with `Undefined parameter` errors on `Rz`/`Cc`'s
own model expressions) and together (converges). See `pdk.json` for the
full note.

**Supply voltage per corner**: `tt/sf/fs` run at nominal `VDD = 1.80 V`;
`ss` at the worst-case-low `1.62 V`; `ff` at the worst-case-high `1.98 V` —
matching [`DR-002`](../../spec/decision-records/DR-002-device-sizing.md)
§(f)'s own pairing. `sf`/`fs` have no such named voltage pairing in either
`DR-002` or `target-spec.md`; nominal `VDD` is used for both, a **stated**
methodology choice, not a claim that mixed-speed corners cannot occur at a
rail extreme too (a future bench could cross the two axes fully — 5 corners
× 3 supply points × 3 temps = 45 points instead of 15 — if that turns out to
matter; not done here to keep this issue's scope to the 5×3 grid its
acceptance criteria name explicitly).

### Open-loop AC bench (`opamp_ac.spice.tmpl`)

**Method, stated as the acceptance criteria require**: a DC operating-point
servo — a very large resistor (`Rfb = 1 TΩ`) from `out` to `inn`, with a
large capacitor (`Cfb = 1 F`) from `inn` to ground — sets the correct
closed-loop DC bias point (corner frequency `1/(2π·Rfb·Cfb) ≈ 1.6×10⁻¹³ Hz`,
many decades below this sweep's 1 Hz start) while presenting an effectively
open circuit at every frequency actually swept, so the AC response from 1 Hz
upward is the amplifier's **true open-loop response**, not a closed-loop
one. This is the standard "DC servo" open-loop AC testbench technique. (A
large-inductor variant of this same idea was tried first and rejected: at
`L = 1×10⁹ H` the measured DC gain came out near 0 dB, i.e. still
closed-loop at 1 Hz — the R+C servo's corner frequency is far easier to place
many decades below the sweep than the inductor's, so it was used instead.)

The AC excitation (`ac 1`) is applied only at `inp` (the non-inverting
input, per `design/opamp_core.sch`'s header), so `vdb(out)`/`vp(out)`
directly report open-loop gain/phase. **ngspice's `vp()` output is in
radians**, confirmed against a trivial R-C low-pass testbench whose
high-frequency phase asymptote lands at exactly `-π/2`; `bin/pvt_sweep.py`
converts to degrees before recording. Phase margin is computed as
`180° + phase_at_gbw_deg` (the phase at the unity-gain crossover is negative
for a stable two-pole system, so this is `180°` minus its magnitude).
Quiescent current/power (`Iq`, `Pq = Iq × VDD`) is read from the same
deck's initial `.op` solve, before the AC sweep — `-i(vdd)`, i.e. the total
current pulled from the supply.

### Slew-rate bench (`opamp_tran_sr.spice.tmpl`)

A genuine unity-gain-buffer connection (`inn` wired to `out` through a
1 mΩ resistor, standing in for a literal wire ngspice's TRAN engine accepts
more readily than a true short in every configuration) — not the AC bench's
DC-servo artifice, since this is a real large-signal closed-loop transient.
`inp` steps between `0.5·VDD ∓ 0.2·VDD` (a step scaled to each corner's own
`VDD`, kept comfortably inside the wide linear input range this experiment's
own DC-swing bench independently confirms — see "Stimulus choices" below)
with a 1 ns edge. `.meas tran` times the 20%-80% (rise) and 80%-20% (fall)
transit of `v(out)` between the step's low and high levels — the textbook
slew-rate convention — and `bin/pvt_sweep.py` converts the measured times to
`V/µs`.

### Output-swing bench (`opamp_dc_swing.spice.tmpl`)

The same real unity-gain-buffer connection, with `inp` DC-swept `0 → VDD`.
While the loop holds (`v(out)` tracks `v(inp)` at unity slope), the
amplifier is in its linear region; wherever the local slope
`d(v(out))/d(v(inp))` falls outside `[0.8, 1.2]`, some device has left
saturation. `bin/pvt_sweep.py` walks outward from the point nearest
mid-supply and reports the largest contiguous unity-slope run's `v(out)`
bounds as the output swing. **Stated limitation, not hidden**: this is a
combined output-swing/closed-loop-compliance measurement (both the input
pair's own valid common-mode range and the output stage's own saturation
headroom can bound it — whichever binds first). It is **not** an independent
measurement of the *open-loop* input-common-mode range `DR-002` separately
estimates in `target-spec.md`'s Input-common-mode-range row — that row is
outside this issue's explicit scope (see the issue body's "Explicitly Out
of Scope": this issue covers the six listed performance rows only). The committed `tt/27°C` point in
`records/*-dc-swing.csv` (`0.178 V`–`1.491 V`, see "Output swing" below)
already shows the real unity-buffer linear region is markedly wider than
`DR-002`'s separately-estimated `≈ 136 mV` input-common-mode window at the
`ss/-40°C` corner — itself a discrepancy worth a future ICM-specific bench,
but out of scope for the six rows this issue measures.

**Stimulus choices**: the slew-rate step (`0.5·VDD ∓ 0.2·VDD`, e.g.
`0.54 V`–`1.26 V` at nominal `1.8 V`) is a large-signal transient stimulus
by design — its purpose is to force full differential-pair current steering,
which necessarily drives the input node outside any narrow small-signal
common-mode range for the duration of the transient. This is standard
practice for a slew-rate measurement (see, e.g., any two-stage-Miller-OTA
slew-rate testbench in the literature) and is not evidence about the
closed-loop small-signal common-mode range, which the dc-swing bench above
addresses on its own terms.

## Results by row

Every row below cites the exact `DR-002`/`target-spec.md` number it checks
against, gives the full 15-point grid, and states plainly whether the
measurement confirms or contradicts the hand estimate — a contradiction is
reported the same way a confirmation is, per `CLAUDE.md` and this issue's
own instruction not to fudge or hide one.

### Open-loop DC gain

Target: `≥ 60 dB` [P]. `DR-002` §(f): 74.2 dB (tt/27°C), 75.1 dB (ss/-40°C),
72.8 dB (ff/125°C) — predicted binding corner in `target-spec.md`: **SS/-40°C**.

| Corner | -40°C | 27°C | 125°C |
|---|---|---|---|
| tt | 73.04 | 72.22 | 71.15 |
| ff | 74.23 | 73.39 | 72.29 |
| ss | 71.43 | 70.73 | **69.72** |
| sf | 71.97 | 71.29 | 70.43 |
| fs | 73.47 | 72.47 | 71.09 |

All 15 points are dB, `.meas ac gain_dc_db find vdb(out) at=1` (the 1 Hz
low-frequency asymptote of the open-loop AC response).

**Verdict**: the `≥ 60 dB` target is met at every corner with ≥ 9.7 dB of
margin. Gain falls monotonically with **increasing temperature at every
process corner** — a clean, consistent trend the hand estimate did not
predict a direction for. The worst measured point is **SS/125°C (69.72 dB)**,
not the predicted SS/-40°C (71.43 dB measured, 1.7 dB better) — **the
predicted binding corner's process family (SS) is confirmed, but its
temperature extreme is contradicted**: SS is worst at hot, not cold. Every
named `DR-002` point measures 1.1–3.7 dB below its hand estimate
(tt/27°C: 72.22 vs. 74.2 measured/estimated; ss/-40°C: 71.43 vs. 75.1;
ff/125°C: 72.29 vs. 72.8), consistent with `DR-002`'s own caveat that its
loaded-parallel-resistance model omits finite tail/mirror loading effects a
real circuit includes.

### GBW (into CL = 2 pF)

Target: `≈ 16 MHz` [P]. `DR-002` §(f): 15.92 MHz (tt/27°C), 17.94 MHz
(ss/-40°C), 13.98 MHz (ff/125°C) — predicted binding corner: **SS/-40°C/low VDD**.

| Corner | -40°C | 27°C | 125°C |
|---|---|---|---|
| tt | 14.78 | 12.69 | 10.85 |
| ff | 16.36 | 13.94 | 11.86 |
| ss | 9.56 | 9.17 | **8.45** |
| sf | 15.62 | 13.41 | 11.49 |
| fs | 13.18 | 11.43 | 9.80 |

All values MHz, `.meas ac gbw_hz when vdb(out)=0 cross=1` (first 0 dB
crossing).

**Verdict**: **contradicted**, and by the largest margin of any row here.
`DR-002` predicted SS/-40°C to have the *highest* GBW of its three named
points (17.94 MHz, faster than even tt/27°C's 15.92 MHz) because its
bare-device gm/ID model shows `gm1` increasing at that corner. The real
circuit shows the opposite: **SS is the slowest corner at every
temperature**, and GBW falls with increasing temperature at every corner
(same direction as the gain row) — so SS/-40°C measures **9.56 MHz, only
53% of its own 17.94 MHz hand estimate**, and the true worst point,
SS/125°C at 8.45 MHz, is 47% of that estimate. `tt/27°C` (12.69 MHz) is
closer to its own estimate (80%) but still measures below it. This is the
clearest case in this sweep of a hand estimate's *qualitative* trend (which
corner is fastest/slowest) being reversed by simulation, not just its
magnitude being off — worth flagging prominently for anyone using `DR-002`'s
GBW numbers for further hand analysis.

### Phase margin (at GBW, same CL)

Target: `≥ 60°` [P]. `DR-002` does not compute phase margin directly (only
the proxy ratio `p2/GBW ≈ 2.5`); predicted binding corner in `target-spec.md`:
**FF/125°C** (fastest devices, most peaking risk).

| Corner | -40°C | 27°C | 125°C |
|---|---|---|---|
| tt | 66.81 | 66.83 | 66.72 |
| ff | 66.15 | 66.20 | 65.98 |
| ss | 73.36 | 71.66 | 70.45 |
| sf | 64.10 | **64.09** | 64.18 |
| fs | 70.09 | 69.92 | 69.59 |

All values degrees, `180° + phase_at_gbw_deg` (see "Methodology" above for
the radians-to-degrees conversion and sign convention).

**Verdict**: the `≥ 60°` target is met at every corner, with the smallest
margin being 4.09° (SF/27°C, 64.09°). The predicted binding corner
(FF/125°C, 65.98° measured) is close to the true worst but not it — **SF**
(slow-NMOS/fast-PMOS), essentially flat across temperature (64.09–64.18°),
is the actual worst process corner, ~1.9° below FF/125°C. Directionally,
`p2/GBW ≈ 2.5` at `tt/27°C` per `DR-002`'s appendix would predict a
comfortable margin, consistent with what is measured (66.83° there) — the
proxy ratio's qualitative prediction (margin comfortably above 60°) holds,
even though the named worst corner does not.

### Slew rate

Target: `≈ 20 V/µs` [P], assumed symmetric (`SR = I_SS/Cc`). Predicted
binding corner: **SS/-40°C/low headroom**.

| Corner | Rise -40°C | Rise 27°C | Rise 125°C | Fall -40°C | Fall 27°C | Fall 125°C |
|---|---|---|---|---|---|---|
| tt | 19.05 | 18.94 | 18.59 | 12.02 | 13.59 | 14.02 |
| ff | 19.69 | 19.65 | 19.46 | 15.69 | 15.72 | 15.52 |
| ss | 17.26 | 17.22 | **16.88** | **1.73** | 4.86 | 9.03 |
| sf | 18.83 | 18.87 | 18.72 | 14.32 | 14.75 | 14.80 |
| fs | 18.90 | 18.70 | 18.17 | 6.53 | 10.98 | 12.58 |

All values V/µs, `0.6·(V_HIGH − V_LOW) / measured 20%-80% (or 80%-20%)
transit time`.

**Verdict**: **contradicted**, on an assumption `DR-002` never stated
explicitly (rise/fall symmetry) but that its single-number `SR = I_SS/Cc`
formula implies. **Rise SR** stays within ~15% of the 20 V/µs estimate at
every corner (worst: SS/125°C, 16.88 V/µs, 84% of estimate) — reasonably
consistent with the hand model, since the first stage's Miller-cap-charging
mechanism the formula describes does drive the rising edge. **Fall SR** is
a different story entirely: it varies **9×** across the grid (1.73–15.72
V/µs) and collapses at cold/slow corners — most severely at **SS/-40°C,
1.73 V/µs — under 9% of the DR-002 estimate (8.65% of the 20 V/µs target),
and ≈ 10% of the rise SR at the same point (17.26 V/µs;
1.7306/17.2561 = 10.0%)**. The mechanism is not fully diagnosed here (out of
scope for this issue — see "Not done" below), but the qualitative picture is
that `M7` (the fixed-current NMOS output-stage sink, gate tied to the
bias-mirror node, not signal-modulated) sets an independent ceiling on how
fast `out` can be pulled down, unlike the rising edge where `M6`'s
gate *is* the signal path and can source well above its quiescent current
when overdriven — and that ceiling is evidently far more corner-sensitive
than `DR-002`'s symmetric `I_SS/Cc` model assumed. **This is the single
most significant, and most actionable, finding in this sweep.**

### Output swing

Target: `≈ 1.39 V (≈86% of 1.62 V)` [P] at the stated corner (`DR-002` §(f):
`0.072–1.464 V` at SS/-40°C/1.62V). Predicted binding corner:
**SS/-40°C/low VDD**.

| Corner | -40°C (Vmin/Vmax/Vpp/%) | 27°C | 125°C |
|---|---|---|---|
| tt | 0.300/1.413/1.113/61.8% | 0.178/1.491/1.313/72.9% | 0.004/1.569/1.565/86.9% |
| ff | 0.270/1.629/1.360/68.7% | 0.146/1.709/1.563/78.9% | 0.002/1.770/1.768/89.3% |
| ss | **0.328/1.184/0.855/52.8%** | 0.194/1.266/1.073/66.2% | 0.018/1.353/1.335/82.4% |
| sf | 0.260/1.309/1.049/58.3% | 0.133/1.386/1.254/69.6% | 0.004/1.490/1.486/82.6% |
| fs | 0.340/1.509/1.169/64.9% | 0.217/1.578/1.361/75.6% | 0.081/1.619/1.539/85.5% |

Units V/V/V/% of that corner's own VDD; `Vmin`/`Vmax` are the unity-buffer
DC transfer curve's linear-region bounds (see "Methodology" above).

**Verdict**: the worst-case **corner is confirmed** — SS/-40°C is indeed the
narrowest swing in the grid, and swing widens monotonically with increasing
temperature at every process corner (same direction as the gain/GBW rows,
consistently — cold is the harder corner throughout this experiment, not
just at this row). The **magnitude is contradicted**: measured `0.855 V`
(52.8% of `1.62 V`) is **62% of `DR-002`'s `1.39 V` (86%) estimate at that
exact corner** — the real circuit's usable output range at the worst
corner is meaningfully narrower than the hand headroom calculation
predicted, consistent with the same "narrower real linear range than
Vov-only headroom suggests" effect noted in "Methodology" above for the
input side.

### Quiescent power

Target: `≈ 128.7 µW` at FF/125°C/1.98V [P] (`≈ 117.0 µW` at nominal
1.8 V). `I_Q = 65 µA` per `DR-002` (a): `I_SS = 10 µA + ID2 = 50 µA` (two
signal branches) `+ 5 µA` (reference branch).

| Corner | Iq (µA) / Pq (µW), -40°C | 27°C | 125°C |
|---|---|---|---|
| tt | 64.29 / 115.72 | 64.60 / 116.27 | 64.87 / 116.76 |
| ff | 65.77 / 130.22 | 65.88 / 130.45 | **66.01 / 130.71** |
| ss | 59.67 / 96.67 | 60.75 / 98.42 | 61.71 / 99.96 |
| sf | 65.04 / 117.07 | 65.26 / 117.46 | 65.47 / 117.85 |
| fs | 62.99 / 113.37 | 63.46 / 114.23 | 63.87 / 114.96 |

**Verdict**: **confirmed**, the cleanest result in this sweep. The worst
measured point, **FF/125°C at 130.71 µW**, matches both the predicted
binding corner *and* the magnitude (`DR-002`: 128.7 µW, measured: 130.71 µW,
**+1.6%**) — well within the precision a first-order hand estimate should be
expected to hit. The nominal point (`tt/27°C`, 116.27 µW) is likewise within
0.6% of `DR-002`'s 117.0 µW nominal estimate. `Iq` ranges 59.67–66.01 µA
across the full grid, bracketing `DR-002`'s 65 µA figure closely at every
corner except SS (which runs consistently ~2–5 µA lower — the slow corner's
lower device currents at a fixed `gm/ID` bias point, expected and benign).

## What this experiment does not do

- **Does not touch `spec/target-spec.md` or the gap-to-T1 tracker
  (issue #3)** — per this issue's explicit scope, this PR commits raw
  testbenches and results only; reconciling the six rows above against the
  spec table (updating `[P]` estimates, binding-corner columns, or Status
  cells) is a follow-on issue.
- **Does not measure input-referred offset, CMRR, PSRR** (still `[TBD]` in
  `target-spec.md`, needing a mismatch Monte Carlo pass, a common-mode AC
  bench, and a supply-AC bench respectively — none of which exist yet), or
  **flicker (1/f) noise**, or **the input-common-mode range** `DR-002`
  separately estimates (a related but distinct measurement from output
  swing — see "Output-swing bench" above). All out of scope per the issue
  body.
- **Does not diagnose the fall-slew-rate collapse's root cause** beyond the
  qualitative hypothesis in "Slew rate" above (a fixed-current, non-signal
  -modulated `M7` sink) — a dedicated bench probing `M7`'s actual bias
  current vs. corner directly (rather than inferring it from the output
  transient) would be needed to confirm that hypothesis, and is a natural
  follow-up issue.
- **Does not cross the corner/temperature grid with a full 3-point supply
  sweep** — `VDD` is tied to process corner per "Supply voltage per corner"
  above, not independently swept at every corner.
- **Does not run layout, DRC, LVS, or post-layout simulation** — gated on
  layout, which does not exist yet (gap-to-T1 tracker items 2–4/7).

## Sources

- `design/netlist/opamp_core.spice`, `design/opamp_core.sch` (issue #13 /
  PR #15) — the netlist under test.
- [`DR-002`](../../spec/decision-records/DR-002-device-sizing.md) (issue #13,
  status `proposed`) — every hand estimate this experiment checks against.
- [`DR-001`](../../spec/decision-records/DR-001-topology-and-cl.md) — `CL = 2 pF`.
- `spec/target-spec.md` §2 — the six `[P]` rows and their predicted binding
  corners this experiment confirms or contradicts.
- [`../gm-id-characterization/pdk.json`](../gm-id-characterization/pdk.json),
  [`../gm-id-characterization/corners/model-files.json`](../gm-id-characterization/corners/model-files.json)
  (issue #6 / PR #7) — the pinned PDK and the confirmed 5-corner MOS
  model-file resolution this experiment reuses directly.
