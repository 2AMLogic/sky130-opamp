# gm/ID characterization — sky130 1.8 V-core MOS devices

Bare-device gm/ID, gm/gds (intrinsic gain) and fT characterization of
`sky130_fd_pr__nfet_01v8` and `sky130_fd_pr__pfet_01v8`, versus gate
overdrive, over the confirmed 1.8 V-core process-corner grid and a channel
length sweep from minimum length to 8x minimum. Per `CLAUDE.md`'s "gm/ID
first, committed before sizing" and `spec/porting-plan.md` §4's "next
concrete step" — this is the block's first `sim/` evidence and lands ahead
of, and independent of, the topology and `CL` decisions (both explicitly out
of scope here; see "Out of scope" below).

## What was measured

For each device polarity, each of the five confirmed 1.8 V-core process
corners, each of four channel lengths, and each of three temperatures:

- **Devices**: `sky130_fd_pr__nfet_01v8`, `sky130_fd_pr__pfet_01v8`
- **Corners**: `tt`, `ff`, `ss`, `sf`, `fs` — confirmed against the pinned
  PDK checkout in [`corners/model-files.json`](corners/model-files.json)
  and [`corners/README.md`](corners/README.md). This closes
  `spec/porting-plan.md` §4's "corner-grid confirmation" item and answers
  `spec/target-spec.md` §1's `Corner grid` row by pointer (see "Spec rows
  this study feeds" below).
- **Channel lengths**: 0.15, 0.3, 0.6, 1.2 µm (1x/2x/4x/8x minimum length
  for these devices)
- **Temperatures**: −40 °C, 27 °C, 125 °C, matching `spec/target-spec.md`
  §1's Operating temperature row
- **Bias point**: |Vds| = 0.9 V (a representative mid-rail bias for a
  1.8 V-core device, not tied to any particular circuit's operating point —
  see "Why these bias choices" below), W = 2 µm, Vgs/Vsg swept 0 → 1.8 V in
  20 mV steps

This is a **120-point PVT×L matrix** (2 devices × 5 corners × 4 lengths ×
3 temperatures), each point itself a full DC sweep (91 Vgs/Vsg values), for
10,920 total swept data rows.

**Not measured / out of scope**: the topology decision and the `CL` choice
themselves (`spec/porting-plan.md` §4's first two bullets) — this study
produces the device data a sizing pass needs, it does not do the sizing or
pick a topology. No supply-voltage axis is swept (see
[`corners/README.md`](corners/README.md#what-is-not-a-corner-axis-here) —
there is no "supply corner" for a two-terminal-bias bare-device sweep).

## Cold-start invocation

Given the pinned PDK (below) is installed:

```bash
python3 sim/gm-id-characterization/bin/sweep.py
```

Regenerates the full evidence set from a clean checkout: renders
`testbench/{nfet,pfet}_gmid.spice.tmpl` once per (device, corner, length,
temperature) point, drives `ngspice -b` on each rendered deck, and writes a
new timestamped record under `records/` (never overwriting a prior one —
this experiment's evidence is append-only, per `spec/porting-plan.md` §3).
Takes roughly 3–4 minutes on a single core (120 ngspice invocations, ~1.5–2s
each). `python3 sim/gm-id-characterization/bin/sweep.py --check-env` reports
tool/PDK availability without running anything; `--help` lists every
override (subset of devices/corners/lengths/temps, bias point, width, sweep
step, gm/ID targets the summary table reports at).

**PDK pin**: [`pdk.json`](pdk.json) — sky130A, open_pdks commit
`c6d73a35f524070e85faff4a6a9eef49553ebc2b` (same pin as `sky130-ldo` and
`sky130-bandgap`). Install with:

```bash
volare enable --pdk sky130 c6d73a35f524070e85faff4a6a9eef49553ebc2b
```

`sweep.py` resolves the PDK the same way as `sky130-ldo`'s
`sim/bin/corner-run.py` (`PDK_ROOT`/`PDK` env, else `volare path`, else
`pdk.json`'s `default_pdk_root`) and warns (but does not refuse) if the
installed commit does not match the pin.

## Layout of this directory

| Path | Contents |
|---|---|
| `pdk.json` | PDK version pin, resolution rules |
| `spiceinit` | ngspice init settings this experiment's decks assume, for interactive/manual sessions (`sweep.py` does not depend on it — see the file's own header) |
| `corners/model-files.json`, `corners/README.md` | The confirmed 1.8 V-core corner-model file list (this study's answer to the corner-grid-confirmation open item) |
| `testbench/{nfet,pfet}_gmid.spice.tmpl` | The two ngspice deck templates `sweep.py` renders per sweep point |
| `bin/sweep.py` | The sweep runner — the one cold-start command above |
| `netlist-snapshots/<record_id>/` | One representative rendered deck per device per record, for provenance (the `tt` corner, minimum length, 27 °C point) |
| `records/<record_id>-full-sweep.csv` | Every derived quantity at every swept Vgs/Vsg point, for every (device, corner, length, temperature) combination — the primary evidence artifact |
| `records/<record_id>-summary.csv` | The same data collapsed to fixed gm/ID targets (20, 15, 10, 5 1/V) via linear interpolation, for quick sizing-table lookups |
| `records/<record_id>.json` / `.md` | Machine-readable / human-readable record metadata: PDK/tool versions, git SHA, matrix shape, headline table |

## How to read a record

- **Overdrive bias**: for the NFET, this is `Vgs` directly (source and bulk
  grounded). For the PFET, source and bulk are tied to the `VDD` rail (see
  `testbench/pfet_gmid.spice.tmpl`'s header), so the overdrive bias reported
  is `Vsg = VDD − v(g)` — both sweeps run the gate node 0 → VDD, and
  `bin/sweep.py` derives the correct overdrive quantity per device rather
  than assuming the sweep direction implies it.
- **Vov** = overdrive bias − `vth`, where `vth` is ngspice's own
  `@m...[vth]` operating-point output for that instance (reported as a
  positive magnitude for both polarities in this convention) — a
  small-signal-model threshold estimate, not a fitted long-channel `Vt0`.
  Negative `Vov` values in the data are expected and meaningful: they are
  the weak/moderate-inversion region of the same monotonic gm/ID-vs-Vov
  curve, not an error.
- **gm/ID** (1/V) = `gm / |Id|` — decreases monotonically from weak
  inversion (high gm/ID, ~20+ 1/V) to strong inversion (low gm/ID, ~5 1/V
  and below) as `Vov` increases. This is the classical Silveira/Jespers
  gm/ID-methodology sizing axis.
- **gm/gds** = intrinsic voltage gain of the bare device at that bias —
  drops with channel length shortened and with device speed (`ff` corner)
  per standard short-channel behavior.
- **fT** (Hz) = `gm / (2·π·Cgg)` — the device's own unity-current-gain
  frequency estimate from its total gate capacitance, rising with `Vov`
  (opposite direction from gm/ID, as expected).
- The `records/<id>-summary.csv` table's `gm_id_target_per_v` rows are
  **linearly interpolated** against the full sweep's own `(gm/ID, Vov)`
  pairs — `null`/blank if the requested gm/ID target falls outside the
  swept range for that (device, corner, length, temperature) combination
  (this happens at the shortest lengths in the deepest weak-inversion
  target, where the swept Vgs/Vsg range does not reach it).

## Why these bias choices

- **|Vds| = 0.9 V**: half of the 1.8 V `VDD` — a standard representative
  saturation bias for a gm/ID characterization sweep on a core-voltage
  device, used because it is bias-point-neutral with respect to any future
  topology's actual node voltages (which do not exist yet — the topology
  decision is explicitly out of scope, see above). Re-sweeping at a
  topology-specific bias point, once one exists, is a natural follow-up
  once sizing starts.
- **W = 2 µm**: gm/ID, gm/gds and fT are, to first order, width-independent
  normalized quantities (only the absolute `Id`/`gm` scale with `W`, which
  this study does not claim); 2 µm is simply large enough that per-finger
  parasitics are not dominant at the shortest swept length.
- **Lengths 0.15/0.3/0.6/1.2 µm**: 1x/2x/4x/8x minimum length for
  `nfet_01v8`/`pfet_01v8`, a standard log-ish spacing for a gm/ID sizing
  chart (Jespers/Silveira-style), giving a short-channel, two intermediate,
  and a long-channel data point.
- **Temperatures −40/27/125 °C**: matches `spec/target-spec.md` §1's
  Operating temperature row exactly, rather than inventing a different grid
  for this study.

## Spec rows this study feeds

- **`spec/target-spec.md` §1, `Corner grid` row** — directly answered by
  pointer to [`corners/model-files.json`](corners/model-files.json) /
  [`corners/README.md`](corners/README.md); see that row's own text for the
  exact citation.
- **`spec/target-spec.md` §2's performance rows** (Open-loop DC gain, GBW,
  Phase margin, Slew rate, Output swing, Quiescent power) all currently
  `[TBD]` — this study is the device-level input a future sizing pass reads
  gm/ID, gm/gds and fT off of once a topology is chosen; it does not itself
  fill in any of those rows (no schematic exists yet).
- **`spec/porting-plan.md` §4** — closes the "Device characterization" and
  "Corner-grid confirmation" open items; the "Topology decision" and "Load
  capacitance (CL) target" items remain open, to be recorded as a decision
  record once this study's numbers exist (per this issue's explicit
  out-of-scope note).
- **Gap-to-T1 tracker, [#3](https://github.com/2AMLogic/sky130-opamp/issues/3),
  item 9** ("Testbenches shipped") — this study ships this block's first
  committed, cold-start-reproducible testbenches with a pinned PDK
  revision; item 9 covers the full eventual spec-row testbench suite, most
  of which still does not exist (no schematic yet), so this study advances
  but does not close it.

## Out of scope

- The topology decision and the `CL` choice (`spec/porting-plan.md` §4,
  first two bullets) — explicitly out of scope for this issue (#6); to be
  recorded as a decision record once this study's numbers exist.
- Any circuit-level testbench (open-loop gain, GBW/PM, slew, noise, offset,
  CMRR/PSRR, swing, power) — those require a schematic, which does not
  exist yet.
