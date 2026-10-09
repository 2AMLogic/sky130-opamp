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

> **Superseded 2026-10-01 (issue #22 / DR-007).** The headline table and
> "Results by row" grids below describe the **DR-002 sizing** this
> experiment first measured; they are kept verbatim as the pre-resize
> baseline. The DR-007 device resize (input pair gm/ID 17, PMOS group
> L=0.3 µm, NMOS mirror group gm/ID 18, Rz 2.50 kΩ) was measured by
> re-running this bench unchanged: see record
> [`records/20261001-074923-c317ff9`](records/20261001-074923-c317ff9.md)
> (GBW and rise SR now met everywhere; fall SR ×6.4; swing +11% at the
> worst corner; the fall-SR mechanism — first-stage tail starvation, not
> `M7`'s sink magnitude — is diagnosed and measured in
> [`DR-007`](../../spec/decision-records/DR-007-device-resize-gbw-slew-swing.md)).
> The fall-SR "Not done" bench below remains open and is now better-specified
> by that diagnosis.

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

### PSRR and noise benches (issue #54)

```bash
python3 sim/opamp-characterization/bin/psrr_noise_sweep.py --check-env
python3 sim/opamp-characterization/bin/psrr_noise_sweep.py          # all three benches, 15 corners each
python3 sim/opamp-characterization/bin/psrr_noise_sweep.py --benches psrr_vdd,psrr_vss --runner-version-check warn
python3 sim/opamp-characterization/bin/psrr_noise_sweep.py --backend local --corners tt --temps 27 --benches noise   # single-corner debug probe only
python3 sim/opamp-characterization/bin/validate_psrr_noise.py       # four single-corner cross-checks (local)
```

Unlike `pvt_sweep.py`, this runner never drives `ngspice` itself: it writes
one `klt sim` corner-matrix request per bench and lets `klt sim` choose the
backend (`$KLT_SIM_BACKEND=batch` on a fleet dispatch host, so the 15-corner
grids run on the Spot batch fleet; the job ids are in the record's
`environment.remote`). It does **not** fall back to a local grid when a batch
submit fails: it exits non-zero and writes nothing. `KLT_CMD` overrides the
`klt` launcher (e.g. `uvx --from klayout-tools==X.Y.Z klt`) without touching
the host install. See "PSRR and input-referred noise" below for the results
and for why the noise grid is **not** yet recorded.

### ICMR and CMRR benches (issue #53)

```bash
python3 sim/opamp-characterization/bin/pvt_sweep.py --check-env --analyses icmr,cmrr   # also reports klt + backend
python3 sim/opamp-characterization/bin/pvt_sweep.py --analyses icmr,cmrr --timeout-s 600  # 15 points each, batch fleet
python3 sim/opamp-characterization/bin/pvt_sweep.py --analyses icmr,cmrr --backend local --corners tt --temps 27   # single-corner debug probe only
```

`icmr` and `cmrr` are **opt-in**: the default analysis set stays
`ac,tran_sr,dc_swing` (so a bare run is unchanged in output and runtime).
Their templates are `klt sim` circuit **bodies** (`testbench/opamp_icmr.spice.tmpl`,
`opamp_cmrr.spice.tmpl`); the runner writes `klt sim` requests (one per corner
for ICMR, because VDD is tied to the corner and `klt` sweeps arrays together by
index; one per CM bias point for CMRR), submits them with `--backend batch`
(default; `$KLT_SIM_BACKEND`) and maps the response into
`records/<id>-{icmr,cmrr}.csv`. It never loops `ngspice` for these points and
does not fall back to a local grid if a batch submit fails. Expected wall-clock
on the fleet: about 11 min for both analyses (record below: 639 s). The three
legacy analyses were not retrofitted and their records and CSV columns are
unchanged. The `.include` of the R+C typical files is satisfied by the
`.lib <sky130.lib.spice> <corner>` section klt appends, which stages correctly
on the batch backend (verified by the passing fleet record).

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
| `bin/pvt_sweep.py` | The sweep runner — the one cold-start command above (and the `icmr,cmrr` `klt sim` path) |
| `testbench/opamp_icmr.spice.tmpl`, `opamp_cmrr.spice.tmpl` | `klt sim` circuit-body benches: input common-mode range (output held at mid-rail) and CMRR (Adm and Acm in one deck) (issue #53) |
| `records/<id>-{icmr,cmrr}.csv` | Per-point ICMR edges / CMRR(f) for the issue #53 benches; `<id>-logs/` holds the klt requests, responses and per-corner decks |
| `testbench/psrr_vdd.cir`, `psrr_vss.cir`, `noise.cir` | Circuit-body benches (no `.control`/`.end`) for `klt sim`: PSRR+ , PSRR-, input-referred noise (issue #54) |
| `bin/psrr_noise_sweep.py` | Writes the three `klt sim` requests, runs them on the configured backend, writes the PSRR/noise records |
| `bin/validate_psrr_noise.py` | Four independent single-corner cross-checks of those benches (DC finite difference, band-limited noise, negative control) |
| `records/<id>-psrr-{vdd,vss}.csv`, `<id>-noise.csv` | One row per (corner, T): window figures plus the full curve at 4 points/decade; `.klt.json` is the unmodified `klt sim` response, `.request.json` the request that produced it |
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

### ICMR bench (`opamp_icmr.spice.tmpl`, issue #53)

Question: over what input common-mode range does the *input stage* work?
The unity-gain follower of the dc-swing bench cannot answer it (output equals
input, so input and output limits are inseparable). This bench instead holds
the output at mid-rail with an inverting unity-gain loop (`Rin = Rf = 100 k`)
whose summing source is forced to `2*Vcm - VDD/2`, while both amplifier inputs
sit at the swept `Vcm` (DC sweep 0..VDD, 5 mV steps). Two copies of the
amplifier at `Vcm` and `Vcm + 10 mV` give the local common-mode sensitivity
`|d vid / d Vcm|` (= 1/local DC CMRR) at every `Vcm` in one sweep.

**Criterion (fixed before any result existed)**: ICMR = contiguous range of
`Vcm` containing `VDD/2` over which local DC CMRR >= **40 dB**; 30 dB and 50 dB
are recorded as a sensitivity band (`*_30db`, `*_50db` columns). The knee is
sharp (tail source / input pair leave saturation), so the edge moves by tens of
mV across that band. 40 dB was chosen as 1 percent input-referred shift per volt of
CM, small against the ~0.14 V target-window scale. `low_limiter`/`high_limiter`
record `input_stage` when the edge is a real crossing and `rail` when the
criterion held to 0 or VDD; the output is held at mid-rail so an output-stage
limit is excluded by construction.

**Caveat, stated**: this is a CMRR-degradation definition, not a
device-saturation one. The fleet runner (klt 0.5.0) has no
`measurements[].expr`, so `@m.x[vdsat]` was not probed and which device leaves
saturation is not recorded. The 40 dB edge is therefore a proxy for
saturation, not a proof of it.

### CMRR bench (`opamp_cmrr.spice.tmpl`, issue #53)

One deck, two instances of the op-amp with the `opamp_ac` DC servo
(`Rfb = 1e12`, `Cfb = 1 F`). Instance D drives AC on `inp` only
(`vdb(out) = Adm`); instance C returns `Cfb` to the AC-driven `inp` node so the
same AC reaches `inn` and `inp` together (`vdb(out) = Acm`). Both share the
corner solve, temperature and tool versions, so `CMRR(f) = Adm(f) - Acm(f)` is
a same-deck quantity. Run at two DC common-mode points: `0.5*VDD` and
`0.956 V` (centre of the 0.888..1.024 V target window). Reported at 1 Hz, 10 Hz,
100 Hz, 1 kHz, 10 kHz, 100 kHz and 1 MHz plus GBW; the spot frequency named for
comparison is 1 kHz.

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

## PSRR and input-referred noise (issue #54)

> **Pre-layout.** Every number in this section is from the schematic netlist
> `design/netlist/opamp_core.spice` (`netlist_source: "schematic"`): no
> routing parasitics, no layout, supply wiring resistance of zero. Nothing
> here is a post-layout or silicon claim.

### Benches

- **PSRR+ / PSRR-** (`testbench/psrr_vdd.cir`, `psrr_vss.cir`): a real
  unity-gain buffer (`inn` tied to `out` through 1 mΩ, as in the slew-rate
  bench), `ac 1` on the `vdd` source (PSRR+) or the `vss` source (PSRR-, `vss`
  held at DC 0 V), signal input AC-grounded. The closed-loop gain is 1 to
  within 1/(1+1/A) < 0.01 dB (open-loop gain is ≥ 61.6 dB at every corner),
  so the supply-to-output gain `vdb(out)` is also the input-referred supply
  gain: **PSRR = −vdb(out)**. The input common mode is `VDD/2` from a divider
  off `vdd` (so `klt sim`'s per-corner `alter vdd=…` moves the bias point
  with the rail); a 1 F shunt (`Cinp`, corner ≈ 3×10⁻⁷ Hz) makes the input
  an AC ground so the divider contributes no supply-to-input path. `ibias` is
  an **ideal** 5 µA current source (AC open): this is the amplifier core's
  supply rejection under an ideal reference, not a bias generator's.
  Sweep `dec 20  0.1 Hz … 1 GHz`.
- **Input-referred noise** (`testbench/noise.cir`): the same buffer,
  `noise v(out) Vinp dec 20 0.1 1g` with `Vinp` the series source at the
  non-inverting input, so `inoise_spectrum` is the amplifier's input-referred
  voltage density. The same `Cinp` shunt removes the divider's own thermal
  noise (a 250 kΩ divider would otherwise add ≈ 64 nV/√Hz at the input).
  1/f comes from the PDK BSIM4 `kf`/`af` flicker model of the pinned open_pdks
  commit; this bench reports what that model produces and makes no claim about
  silicon flicker noise.
- **Grid**: the same 5 MOS corners × (−40, 27, 125 °C) as the rest of this
  experiment, with the same corner-paired `VDD` (tt/sf/fs 1.80 V, ss 1.62 V,
  ff 1.98 V), expressed as one `klt sim` request per bench with a 3-value
  supply axis and `exclude` entries keeping only the 5 paired points × 3
  temperatures = 15 corners. R+C typical (the `tt`/`ss`/… `.lib` section of
  `sky130.lib.spice` pulls in `res_typical__cap_typical{,__lin}` exactly as
  the other benches' explicit includes do). The pairing is a methodology
  choice, as stated under "Methodology" above; the supply axis is not crossed.
- **Bands**: the consumer-imposed PSRR window is **DC–1 kHz** (the
  sky130-bandgap ratified PSRR row, `spec/target-spec.md` "Consumers"); the
  amp has no PSRR row of its own (`[TBD]`, unset), so no pass/fail is graded
  against a local target and the 60 dB consumer figure is stated as the
  *consumer's loop-level requirement*, not an allocation to this amplifier.
  The noise band is the spec row's proposed **100 Hz – 1 MHz** `[P]`; the
  row states no integrated-noise limit, so only the thermal-floor estimate
  (≈ 30 nV/√Hz) is a comparison point, and no 1/f corner or integrated figure
  is in the spec.

### Result: PSRR (full 15-corner grid, batch fleet)

Record `20261009-073254-e06f2fc`
([`psrr-vdd.csv`](records/20261009-073254-e06f2fc-psrr-vdd.csv),
[`psrr-vss.csv`](records/20261009-073254-e06f2fc-psrr-vss.csv)), both benches
`pass` with 15/15 corners, run on the Spot batch fleet
(`psrr_vdd`: job `klt-sim-9ec838f70172`; `psrr_vss`: job
`klt-sim-942a6609c696`; ngspice 46). **Worst PSRR over DC–1 kHz, dB**
(`psrr_window_min_db`; larger is better):

| PSRR+ (vdd) | −40 °C | 27 °C | 125 °C |
|---|---|---|---|
| tt | 67.94 | 67.72 | 66.82 |
| ff | 66.91 | 66.54 | 65.50 |
| ss | 66.19 | 67.05 | 66.85 |
| sf | 69.38 | 69.54 | 69.00 |
| fs | 65.07 | 64.70 | **63.57** |

| PSRR− (vss) | −40 °C | 27 °C | 125 °C |
|---|---|---|---|
| tt | 74.38 | 75.17 | 75.15 |
| ff | 83.69 | 83.64 | 82.88 |
| ss | **54.90** | 58.65 | 61.49 |
| sf | 78.12 | 78.97 | 79.21 |
| fs | 69.05 | 70.08 | 70.07 |

- **PSRR+ is flat across DC–1 kHz** (the window minimum is at 1 kHz, ≤ 0.06 dB
  below the 0.1 Hz value at every corner) and **≥ 60 dB at every corner with
  ≥ 3.5 dB of margin** (worst: FS / 125 °C, 63.57 dB). It crosses 60 dB at
  14.8–28 kHz (FS/125 °C lowest) and decays 20 dB/decade above that to
  ≈ 26–30 dB at 1 MHz, reaching 0 dB near the 20–30 MHz closed-loop
  bandwidth.
- **PSRR− is the weaker side at one corner**: SS / −40 °C reads **54.90 dB
  (< 60 dB)** and SS / 27 °C 58.65 dB; the other 13 points are ≥ 61.4 dB. PSRR−
  is flat from DC to well past 1 kHz, so the DC–1 kHz window figure is the DC
  figure. Whether PSRR− matters depends on a consumer's ground-referencing; the
  only consumer PSRR row in `spec/target-spec.md` (sky130-bandgap, > 60 dB
  DC–1 kHz) is a supply (+) rejection requirement on the bandgap loop.
- **This is not a verdict against the consumer.** The bandgap's 60 dB is a
  whole-loop requirement (amplifier PSRR is one term, with the core's own
  supply path); the amplifier numbers above are inputs to that budget, which
  is the consumer's to evaluate. The bandgap also runs the amp at 3.3 V on
  thick-oxide devices, a rail this block does not serve (`DR-005`), so the
  consumer table's verdict for that edge remains "not met (different
  contract)" regardless of these figures. Consequently
  `manifests/integrator.json` is **unchanged**: no consumer row moved from
  unknown to a measured verdict.
- **Finding, not hidden**: the DC–1 kHz window is flat, but PSRR+ falls
  steeply above ≈ 20 kHz (≈ 26–30 dB at 1 MHz). A consumer with switching
  ripple above the window is not covered by the 60 dB figure.

### Result: noise (bench verified; PVT grid NOT recorded)

**The 15-corner noise grid has no record.** `klt sim`'s only route from a
`.noise` analysis to a number is `measurements[].expr` (ngspice's `.meas`
has no `noise` analysis type). The Spot batch fleet's runner image ran
**klt 0.5.0** on 2026-10-09, which rejects any `measurements[].expr`
(`each request.measurements[] entry requires 'name' and 'spice'`; batch job
`klt-sim-c911be7c7b93`, 15/15 corners `batch_job_failed`; known upstream as
klayout-tools#2877, new gap filed as klayout-tools#2938). Per the host
rule that a failed batch submit is reported and **not** worked around by a
local ngspice grid, the noise grid was not run elsewhere. The bench itself is
unchanged and ready: re-running `psrr_noise_sweep.py --benches noise` on a
fleet image carrying klt ≥ the release that added `expr` produces the 15-corner
record with no edits.

**Re-attempt log (appended 2026-10-09, after the above; earlier text unchanged).**
`psrr_noise_sweep.py --benches noise` was re-run. The first submit was refused
before any job ran (`batch-fleet-provision.sh`: 8 instances already running,
`BATCH_MAX_CONCURRENT_INSTANCES=8`); the second submit ran as batch job
`klt-sim-b1c3b34522bc` and failed 15/15 corners: the runner still reports klt
0.5.0 against client 0.7.0 (`runner_version_check: enforce`, request not run).
No record was written and no local grid was run. The grid remains outstanding
until the fleet runner image carries a klt that supports `measurements[].expr`.

What does exist is evidence that the bench measures the right thing, all
single-corner and run locally (permitted for one corner / one operating point):

| Check | Result |
|---|---|
| Band-limited vs full-sweep integrated noise, SS/125 °C/1.62 V: ngspice-native `inoise_total` over a 100 Hz–1 MHz sweep vs the bench's trapezoid post-processing of the full 0.1 Hz–1 GHz sweep | 82.177 µV vs 82.191 µV rms, **1.7×10⁻⁴ relative** |
| Single-corner probe, **TT / 27 °C / 1.80 V** (record `20261009-073753-e06f2fc`, [`noise.csv`](records/20261009-073753-e06f2fc-noise.csv); *not PVT evidence*) | 100 Hz: 1500 nV/√Hz; 1 kHz: 541; 10 kHz: 200; 100 kHz: 79.7; 1 MHz: 42.4; white floor (min over 100 kHz–10 MHz): **35.8 nV/√Hz** (hand estimate ≈ 30: +19%); 1/f corner (psd = 2× floor²) ≈ 442 kHz; integrated 100 Hz–1 MHz: **70.1 µV rms** |

So on the one probed corner the input-referred noise over the proposed band
is flicker-dominated: the 1/f corner (≈ 440 kHz) lies near the top of the
proposed 100 Hz – 1 MHz band, which `spec/target-spec.md` §2a does not model
(it states a thermal floor only). That is a **spec finding** for the
ratified-target-only noise row, flagged here, not an edit to it. The spec row
does state a band (100 Hz – 1 MHz), so no missing-band finding applies; what
it lacks is any flicker or integrated-noise number to compare against. The
same single-corner data is a preview, not a grid-worst-case claim: other
corners (ss/−40…) are expected to differ and are not measured.

### Validation of the benches (`bin/validate_psrr_noise.py`)

Record [`20261009-072806-e06f2fc-psrr-noise-validation.json`](records/20261009-072806-e06f2fc-psrr-noise-validation.json)
(local, single corner each):

| Check | Result |
|---|---|
| PSRR+ by DC finite difference (`.op` at vdd 1.79 / 1.81 V, input held at a fixed 0.9 V) vs the AC bench at 0.1 Hz, TT / 27 °C / 1.8 V | 67.7590 dB vs 67.7594 dB (**0.0004 dB**) |
| Negative control: the PSRR+ bench with the `Cinp` shunt removed | 6.02 dB (the divider passes half the ripple into the input) — the shunt is load-bearing and the bench does notice a supply-to-input leak |
| Noise integration | see the table above (1.7×10⁻⁴) |

### Limits of this evidence

- Schematic netlist, ideal `ibias`, no layout parasitics or supply
  resistance.
- `VDD` is tied to the process corner, not independently crossed (as for the
  other rows); R+C typical only.
- PSRR is measured with the unity-buffer connection and referred to the input
  assuming Acl = 1 (error < 0.01 dB). PSRR with other closed-loop gains, or
  against a real bias generator, is not measured.
- The fleet runner was klt 0.5.0 and the client 0.7.0
  (`runner_version_check: "warn"`); PSRR requests therefore use `.meas` cards
  only (0.5.0-compatible), and the record's `environment.remote` carries
  `runner_compatibility: "mismatch"`. The local single-corner PSRR probe on
  ngspice 42 reproduced the fleet's ngspice 46 value at SS/125 °C
  (66.9021 dB) to the printed digits.

## ICMR and CMrecords/20261009-103006-566b9a5 (issue #53)

> **Pre-layout**, schematic netlist, R+C typical, `VDD` tied to corner; fleet
> runner klt 0.5.0 vs client 0.7.0 (`runner_compatibility: "mismatch"`, benches
> use `.meas` only). Record:
> [`records/20261009-103006-566b9a5.md`](records/20261009-103006-566b9a5.md) (data `-icmr.csv`, `-cmrr.csv`; batch job ids in the
> record, e.g. `klt-sim-f41e6e881853`; 45 units passed, 0 failed, 0 `batch_*`
> diagnostics, 639 s).

**ICMR (40 dB criterion), 15 points**

| Quantity | Value | Binding corner |
|---|---|---|
| Highest low edge | 0.7388 V | FS / -40 C |
| Lowest high edge | 1.1686 V | SS / -40 C |
| Narrowest window | 0.452 V (0.717 .. 1.169 V) | SS / -40 C |
| Widest window | 1.178 V (0.619 .. 1.797 V) | FF / 125 C |

- **Target window 0.888 .. 1.024 V: met at all 15 points** (the highest
  low edge is 0.739 V against 0.888 V; the lowest high edge 1.169 V against
  1.024 V). The ratified target was not edited.
- **Consumer sense point 0.73 V: not met at FS / -40 C** (low edge 0.7388 V, 8.8 mV
  above 0.73 V, so 0.73 V lies outside the range); covered at the other 14 points. With the 50 dB criterion the low edge
  rises to 0.80 V at the worst point, so the 0.73 V sense point is
  criterion-sensitive. Not relaxed.
- Every edge is input-stage limited; none is rail-limited.

**CMrecords/20261009-103006-566b9a5 (Adm - Acm), 30 points**

| CM point | Worst CMrecords/20261009-103006-566b9a5 @ 1 Hz (= 1 kHz) | Best |
|---|---|---|
| 0.5*VDD | 55.11 dB SS / -40 C | 75.22 dB SF / -40 C |
| 0.956 V | 69.34 dB FS / 125 C | 81.76 dB SS / 27 C |

CMrecords/20261009-103006-566b9a5 is flat from 1 Hz to ~100 kHz and falls <= 0.4 dB by 1 MHz. The spec CMrecords/20261009-103006-566b9a5
row is `[TBD]`, so there is no target to grade against.

**Cross-checks (pass)**: Adm(1 Hz) from the CMrecords/20261009-103006-566b9a5 deck equals `gain_dc_db` in the
committed `20261001-074923-c317ff9-ac.csv` to 0.0000 dB at 15 points (tolerance
0.05 dB; GBW identical); the ICMR bench's mid-point quiescent current agrees with
the committed `iq_a` to 7e-5 relative (tolerance 1 percent), confirming the held-at-mid-rail
loop is at the same operating point as the open-loop servo bench.

Two earlier fleet attempts (`20261009-095419-72db8ef`, `20261009-101813-72db8ef`)
each had 7 failed units (fleet-side non-convergence in the per-supply-group
layout) and are not committed; the per-corner layout with `.nodeset` seeding at
566b9a5 passed 45 / 45.

## What this experiment does not do

- **Does not touch `spec/target-spec.md` or the gap-to-T1 tracker
  (issue #3)** — per this issue's explicit scope, this PR commits raw
  testbenches and results only; reconciling the six rows above against the
  spec table (updating `[P]` estimates, binding-corner columns, or Status
  cells) is a follow-on issue.
- **Does not measure input-referred offset** (still `[TBD]`; mismatch Monte
  Carlo, issue #52) and **does not reconcile the spec**: ICMR and CMRR are now
  measured (see "ICMR and CMRR (issue #53)") and PSRR/noise are benched (issue
  #54), but `spec/target-spec.md` is untouched; reconciling those rows is a
  follow-on issue. The ICMR figure is a CMRR-degradation (40 dB) range, not a
  device-saturation one.
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
