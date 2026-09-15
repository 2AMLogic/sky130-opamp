# design/

Schematics (xschem) and netlists for the two-stage Miller-compensated op-amp
core (issue #13).

```
design/
  xschemrc            repo xschem config: resolves the sky130 PDK, adds this
                      repo's own symbol/testbench directories to the library
                      path (ported from the same-PDK sibling
                      sky130-bandgap/sim/xschemrc)
  opamp_core.sch      the op-amp core schematic
  opamp_core.sym      hierarchical-instantiation symbol for the above,
                      generated from the schematic by xschem's own
                      make_sym.awk
  netlist/
    opamp_core.spice  the xschem-generated SPICE netlist (committed --
                      reviewable in git, regenerated on every design change)
  bin/
    sizing_check.py   re-derives every number in DR-002 from the committed
                      gm/ID sweep; no simulation, stdlib only
```

## What's here

- **`opamp_core.sch`** — NMOS input pair (`M1`/`M2`), non-cascoded PMOS
  current-mirror load (`M3`/`M4`), NMOS tail current source (`M5`),
  Class-A PMOS common-source output stage (`M6`) with an NMOS current-sink
  load (`M7`), and nulling-resistor Miller compensation (`Rz` + `Cc`) from
  `d2` to `out` — the topology fixed by
  [`spec/decision-records/DR-001-topology-and-cl.md`](../spec/decision-records/DR-001-topology-and-cl.md).
  One diode-connected NMOS (`MB1`) turns the external `ibias` current into
  the gate bias for `M5` and `M7`. Pins: `vdd`, `vss`, `inn`, `inp`, `out`,
  `ibias`. The schematic's own header comment carries the topology and
  polarity rationale; **it deliberately does not re-derive the sizing.**
- **Sizing rationale lives in
  [`spec/decision-records/DR-002-device-sizing.md`](../spec/decision-records/DR-002-device-sizing.md)**,
  not in this file. A decision record was chosen over a `design/README.md`
  section because this sizing pass *revises* three channel lengths `DR-001`
  named as candidates, and `DR-001` asks for revisions to "produce a
  superseding record, not a silent change". DR-002 carries the per-device
  operating point, the literal `-full-sweep.csv` rows each width is computed
  from, the mirror ratios, `Rz`/`Cc`, the corner table, and the open items.
- **`design/bin/sizing_check.py`** — reproduces all of it:

  ```bash
  python3 design/bin/sizing_check.py validate   # interpolation vs -summary.csv
  python3 design/bin/sizing_check.py widths     # bracketing CSV rows -> W
  python3 design/bin/sizing_check.py corners    # committed W, evaluated tt/ss/ff
  ```

  It reads only `sim/gm-id-characterization/records/*.csv`, needs no PDK and
  no simulator, and runs no simulation.

## Device summary (full derivation in DR-002)

All devices are 1.8 V core flavor (`sky130_fd_pr__nfet_01v8` /
`__pfet_01v8`), per `CLAUDE.md`. `m` is a count of identical unit devices.

| Device | Type | `W` × `L` (µm) | `m` | `I_D` | `gm/ID` (tt/27 °C) |
|---|---|---|---|---|---|
| `M1`, `M2` | nfet_01v8 | 1.325 × 1.2 | 1 | 5 µA | 10 V⁻¹ |
| `M3`, `M4` | pfet_01v8 | 2.745 × 0.6 | 1 | 5 µA | 10 V⁻¹ |
| `M6` | pfet_01v8 | 2.745 × 0.6 | 10 | 50 µA | 10 V⁻¹ |
| `MB1` | nfet_01v8 | 3.835 × 1.2 | 1 | 5 µA | 15 V⁻¹ |
| `M5` | nfet_01v8 | 3.835 × 1.2 | 2 | 10 µA | 15 V⁻¹ |
| `M7` | nfet_01v8 | 3.835 × 1.2 | 10 | 50 µA | 15 V⁻¹ |
| `Rz` | res_high_po_1p41 | 1.41 × 7.585 | 1 | — | 2.00 kΩ |
| `Cc` | cap_mim_m3_1 | 15.62 × 15.62 | 1 | — | 0.4998 pF |

Mirror ratios: `M3`:`M4` = 1:1, `M4`:`M6` = 1:10, `MB1`:`M5`:`M7` = 1:2:10.
Bias currents are `spec/target-spec.md` §2a's proposal unchanged
(`I_SS = 10 µA`, `ID2 = 50 µA`, `Cc = 0.5 pF`), plus a 5 µA reference branch
§2a did not model.

## Running xschem / regenerating the netlist

```bash
export PDK_ROOT="$HOME/.volare"   # parent dir containing sky130A/
export PDK=sky130A
xschem --rcfile design/xschemrc design/opamp_core.sch        # interactive
```

To regenerate the committed netlist headlessly (no X server needed) — the
**one documented command**:

```bash
export PDK_ROOT="$HOME/.volare"
export PDK=sky130A
cd design
xschem -n -x -q -r --rcfile ./xschemrc -o ./netlist ./opamp_core.sch
```

(`-n` netlist, `-x` no X, `-q` quit when done, `-r` regenerate existing —
the same fleet convention `sky130-bandgap` and `sg13g2-opamp` use.) The
netlist lands in `design/netlist/opamp_core.spice` and is committed.

**Expected diff on regeneration**: only line 1, `** sch_path: …`, which
records the absolute path of the schematic in whatever checkout generated it
(a worktree path here). Everything below it is checkout-independent; a diff
anywhere else means the schematic and the committed netlist have actually
diverged.

To regenerate the symbol after adding, removing or reordering a pin:

```bash
cd design && awk -f "$(dirname "$(command -v xschem)")/../share/xschem/make_sym.awk" 150 ./opamp_core.sch
```

`make_sym.awk` orders symbol pins by their **y coordinate** in the
schematic, so the `iopin` instances in `opamp_core.sch` are placed
top-to-bottom in the same order they are declared — that keeps
`opamp_core.sym`'s pin order identical to the schematic's `.subckt`
terminal order (`vdd vss inn inp out ibias`).

A resolvable sky130 PDK install is required (`PDK_ROOT`/`PDK` pointing at a
`sky130A/` open_pdks-shaped directory). This repo does not vendor the PDK;
the pinned version is recorded in
[`sim/gm-id-characterization/pdk.json`](../sim/gm-id-characterization/pdk.json).

## What has been verified in this environment (issue #13)

Done, with the real pinned PDK installed:

- **Netlisting** — `design/netlist/opamp_core.spice` was produced by
  xschem's own netlister with the command above (xschem 3.4.7, sky130A at
  open_pdks `c6d73a35f524070e85faff4a6a9eef49553ebc2b`), with no errors, and
  re-running the netlister produces a byte-identical file. It is **not** a
  hand-written netlist.
- **Symbol** — `opamp_core.sym` was generated from the schematic by xschem's
  own `make_sym.awk`, not hand-written, and its pin order matches the
  schematic's `.subckt` line.
- **Device-dimension DRC** — `xschem drc_check` (which runs the PDK's own
  `fet_drc` proc from `$PDK_ROOT/$PDK/libs.tech/xschem/xschemrc`) returns
  **clean** on this schematic. The check was confirmed non-vacuous: the same
  command on a copy with the input pair narrowed to `W = 0.3 µm` reports
  `M1 (nfet_01v8): finger width is too small, w / nf = 0.3`.
- **Sizing arithmetic** — `python3 design/bin/sizing_check.py validate`
  reproduces all 465 populated rows of the committed gm/ID `-summary.csv`
  from the full sweep, exactly, using the same interpolation DR-002's widths
  are derived with.

**Not done, deliberately** (out of scope for issue #13, and not claimed
anywhere in this directory or in DR-002):

- **No simulation of any kind.** ngspice was never invoked on this netlist —
  no operating point, no AC, no transient, no PVT sweep, no Monte Carlo. The
  netlist is syntactically produced by xschem but has not been shown to
  converge, and no device has been shown to actually sit in saturation at the
  `|Vds|` values this circuit imposes (the gm/ID sweep the sizing comes from
  biased every device at `|Vds| = 0.9 V`, `Vsb = 0`).
- **No layout, no DRC on geometry, no LVS, no extraction.** The `ad`/`as`/
  `pd`/`ps` values in the netlist come from the PDK symbol's pre-layout
  estimation expressions.
