# layout/

This directory holds the layout of `opamp_core`, built with klayout-tools
(`klt`), together with its DRC, extraction and LVS evidence. Each laid-out
sub-block lives in its own `layout/<cell>/` directory. That directory holds
the recipe (`cell.json`), every intermediate request/response, the composed
GDS, and the reports that back each claim in the cell's README.

**Status: four sub-blocks. `opamp_out/` (the canonical output stage
`XM6`/`XM7`, ten units each; klt DRC/LVS, Magic `drc(full)` and netgen all
pass, see `opamp_out/README.md`), `opamp_stage1/` (the NMOS input pair
`XM1`/`XM2` and the PMOS mirror `XM3`/`XM4`), `opamp_bias/` (the bias/tail
mirror `XMB1`/`XM5`; klt DRC/LVS, Magic `drc(full)` and netgen all pass, see
`opamp_bias/README.md`) and `opamp_comp/` (the routed `XRz`/`XCc`
compensation network; klt DRC/LVS and netgen pass, Magic `drc(full)` fails on
the resistor heads, see `opamp_comp/README.md`).**
`opamp_core/` (issue #220) assembles the four sub-blocks into the full core:
klt DRC clean, klt LVS match against the whole `opamp_core` netlist, negative
control mismatches, `--check` reproduces it. The PDK's Magic `drc(full)` of
the assembled core **fails**: it inherits the unfixed `opamp_comp` resistor-head
finding (2 errors, `licon.1c`), and netgen's pin lists differ because Magic
exports the internal labelled nets as ports (devices and nets match uniquely);
see `opamp_core/README.md`. It is not foundry-DRC-clean. Nothing in
`manifests/` cites this directory yet (follow-up).

## The flow

`layout/bin/compose-cell.py` is ported from 2AMLogic/sky130-trng
`layout/bin/compose-cell.py` at commit
`5d443907c99bf4eb193092f0cf89f2a6e2a5c80e`. It is the same
`cell.json`-driven recipe the sibling sky130 blocks use. Its docstring
lists what was kept, dropped and added. For one `cell.json` it runs:

```
klt gen <generator> / klt draw   per block       -> gen/<id>.gds, gen/<id>.gen.json|draw.json
klt gen-compose                  place + route   -> compose.request.json, compose.response.json, <cell>.gds
klt drc --deck sky130                            -> drc.json
klt extract --deck sky130                        -> extract.json, <cell>.spice
klt lvs (reference from design/)                 -> <cell>.ref.spice, lvs.request.json, lvs.json
```

After the chain it checks its own result and exits non-zero if any check
fails. The checks are:

- DRC `clean` with 0 violations.
- The extracted devices, grouped by terminal nets, reproduce each reference
  card's `L` exactly and its `W` exactly as a sum of drawn units (MOS). For
  passives: the resistor's `L`/`W`/body count and the MiM capacitor's plate
  area and perimeter, with the resistor substrate part of the grouping key
  (so a substrate miswire is a "no extracted device" failure).
- Every LVS pin is a composed-cell port and a named extracted net.
- LVS `status: "match"`.

Modes:

```
python3 layout/bin/compose-cell.py layout/<cell>/cell.json                  # regenerate in place
python3 layout/bin/compose-cell.py layout/<cell>/cell.json --check          # rebuild in a temp dir, compare
python3 layout/bin/compose-cell.py layout/<cell>/cell.json --negative-control DEV:TERM=NET
python3 layout/bin/magic-signoff.py layout/<cell>/cell.json                 # second-opinion DRC + LVS
```

- `--check` compares **GDS bytes**: the SHA-256 of `<cell>.gds` and of
  every `gen/*.gds`. It also compares the generated reference text and the
  sibling's verdict fields (`drc.json` status/violation count, `extract.json`
  counts, `lvs.json` status/counts, `compose.response.json` cell
  name/bbox). It never writes into the cell directory. Each stream's GDS
  `BGNLIB`/`BGNSTR` timestamps are zeroed as it is written, so the byte
  comparison is not defeated by a writer stamping the time. The pinned klt
  already writes zeros, so today this is a guard, not a rewrite.
- `--negative-control` rebuilds into a temp dir and rewires one terminal of
  one reference card to another boundary net. It then requires LVS to
  report a mismatch. Its evidence goes to `<cell>/negative-control/` only.
- `magic-signoff.py` checks the committed GDS with the PDK's own Magic
  `drc(full)` deck and netgen LVS. This is needed because klt's curated deck
  has no implant, `npc` or poly-endcap rules (see `opamp_stage1/README.md`).

### The LVS reference comes from the design netlist

`design/netlist/opamp_core.spice` exports one flat `opamp_core`, with
commented-out `**.subckt`/`**.ends` headers and `+` continuation lines. A
sub-block covers only some of its devices. `layout/bin/stage_reference.py`
therefore selects the cards named in `cell.json` `lvs.devices` and joins
their continuations. It copies them **verbatim** (terminal order, model,
every parameter) into `.subckt <cell> <lvs.pins>`. No device parameter is
hand-written. One exception, written into the file header when it applies:
`klt lvs` rejects a card with `m` > 1 (or `mult` > 1), so a MOS card with
`m=N` is written as `N` cards `<name>_1`..`<name>_N` with `m=1 mult=1`
(`expand_multiplicity`). The geometry check still uses the verbatim card. It
counts the instance `m` only, not `m * mult`: in the sky130 model subckt
`mult` feeds the mismatch formulas and the inner device has no `m`, so
`mult=2 m=2` (as on `XM5`) is two units. A one-point ngspice check on the
pinned PDK (tt, W=7.82, L=1.2, Vgs=0.8, Vds=0.9) gave 45.99 uA for
`m=1` with `mult` 1 or 2 and 91.99 uA for `m=2` with `mult` 1 or 2. Supported cards are four-terminal sky130 MOS cards and the
two compensation passives (`res_high_po_1p41`, three terminals including
substrate; `cap_mim_m3_1`, two terminals); any other model is rejected. A
missing or duplicated card, a duplicate selection, an unsupported or
wrong-arity card, a passive without `L`/`W`, a terminal net outside the pin list, or a pin no card uses is
a hard error. Bare sky130 geometry literals (`L=1.2`) are read as
micrometres because the request names `reference.deck: "sky130"`
(klayout-tools#1492/#1505). The sibling's `u`-suffix rewrite is therefore
not needed. Unit tests (all `layout/bin/test_*.py`: stage_reference,
compose-cell, magic-signoff; tool-free, run from the repo root of a full
checkout, as in `.github/workflows/tests.yml`):

```
python3 -m unittest discover -s layout/bin -p 'test_*.py' -v
```

### Committed-cell import and internal LVS nets (issue #210)

Prerequisite for the top-level assembly; it promotes no integrator GDS and
makes no maturity claim. Both features are opt-in; recipes without them
behave exactly as before.

`blocks[]` may carry a committed sub-block instead of `draw`/`generator`
(exactly one of the three per block; block ids must be unique):

```json
{"id": "comp", "cell": {"gds": "../opamp_comp/opamp_comp.gds",
                         "cell_name": "opamp_comp",
                         "ports": [{"name": "d2", "net": "d2", "layer": {"layer": 67, "datatype": 20},
                                    "x_um": -6.0, "y_um": 22.705, "width_um": 0.42, "direction_deg": 180}]}}
```

- `gds` is relative to the recipe directory and must stay inside the repo;
  `cell_name` must be defined in the stream; `ports` (the klt
  `gen-compose` `blocks[].cell` port list; copy from the child's
  `compose.response.json`) needs unique names. All of this is validated
  before any tool runs.
- The stream is copied to `gen/<id>.gds` and only the copy is timestamp
  normalised; the source file is never written. `gen/<id>.import.json`
  records source and staged SHA-256, cell name and ports; `--check` diffs it
  (and the staged GDS bytes), so a changed child cannot hide behind stale
  parent artifacts.
- `lvs.internal_nets` (optional list) names reference-only nets. Boundary
  `lvs.pins` remain the only subckt ports. Every device terminal must be a
  pin or a declared internal net; duplicates, overlap with a pin and
  unused declarations are errors. Without the field the strict pins-only
  behaviour is unchanged.

Importing `opamp_comp` carries its recorded resistor-head Magic DRC failure;
composition cannot qualify it. Smoke experiment (pinned klt, single run,
scratch recipe not committed): a one-block composite importing
`opamp_comp.gds` with `lvs.devices = [XRz, XCc]`, `pins = [d2, out, vss]`,
`internal_nets = [cz]` built with klt DRC clean, 2 devices, LVS match 2/2
devices and 4/4 nets, `--check` reproduced it, the source SHA-256 was
unchanged, and appending bytes to the child made `--check` report drift.
Magic signoff was not run on the scratch composite.

### Toolchain

`layout/pdk.json` pins:

- klt `0.7.0+g4cbdfa769875`, git `4cbdfa7698752b720c0e627163867de1e23475f3`,
  with KLayout 0.30.12;
- sky130A open_pdks `c6d73a35f524070e85faff4a6a9eef49553ebc2b`, the same
  commit as `sim/gm-id-characterization/pdk.json`.

`compose-cell.py` refuses to run on a different klt commit or PDK unless
given `--allow-unpinned`. The klt pin is newer than the sibling's
`5edb557f`, the curator's candidate: it is the build this worker fleet
provisions, and the evidence was produced and re-checked on it. To run
exactly the pinned klt without touching any shared install, use a
throwaway venv:

```
uv venv /tmp/klt-4cbdfa7
uv pip install --python /tmp/klt-4cbdfa7/bin/python \
  "klayout-tools @ git+https://github.com/2AMLogic/klayout-tools@4cbdfa7698752b720c0e627163867de1e23475f3"
PATH=/tmp/klt-4cbdfa7/bin:$PATH python3 layout/bin/compose-cell.py layout/opamp_stage1/cell.json --check
```

The PDK is resolved by `klt pdk find` (search root `~/.volare`, installed
with `volare enable --pdk sky130 c6d73a35f524070e85faff4a6a9eef49553ebc2b`).
`magic-signoff.py` additionally needs `magic`, `netgen` and a `klayout`
binary (used only to flatten the GDS) on `PATH`. It reads `sky130A.tech`
and `sky130A_setup.tcl` from the same pinned PDK.

### `cell.json` additions beyond the sibling recipe

- `blocks[].draw`: a block drawn by `klt draw` from shapes in the
  `cell.json`. Pin-promotion stubs and the sky130 front-end mask overlay
  use it. These are regenerated on every run, so `--check` covers them.
  The sibling sky130-temp-por commits hand-drawn stub GDS files instead.
- `blocks[].snap_ports_to_grid_um`: works around
  2AMLogic/klayout-tools#2932. It writes `gen/<id>.snapped.gen.json` with
  port centres moved onto the grid by at most half a step, records every
  move, and keeps the original report.
- `lvs.devices` / `lvs.pins`: the reference selection described above.
  `lvs.options` is passed to `klt lvs` (e.g. `combine_devices` for split
  devices).
- `expect.extracted_devices`: the extracted unit count the cell must
  produce.
- `expect.magic_types`: Magic types `magic-signoff.py` must see (the
  anti-vacuous guard); default is the MOS set `nmos ndiff psubdiff poly`.
- `lvs.layout_input: "gds"`: LVS the GDS with inline extraction instead of
  the pre-extracted netlist. Required for cells with a resistor
  (klayout-tools#3078).
- `--negative-control` terminal letters follow the card: MOS `d/g/s/b`,
  resistor `a/b/w` (`w` = substrate), capacitor `a/b`.

## Plan for the remaining groups

DR-002/DR-007 fix the matching structure: three equal-length groups, with
mirror ratios set by unit count only. Each step below is one sub-block
directory or an extension of one, with the same evidence set.

1. **First stage, PMOS mirror `XM3`/`XM4`: done (#121).** Added to
   `opamp_stage1/` at the grid-legal W=4.635 um of DR-013 as 2 x 3 units of
   1.545 um, with an n-tap ring to `vdd`, `vdd` as the seventh pin, 4/4
   devices, klt and Magic DRC clean, klt and netgen LVS matched. The mirror
   block is drawn with `klt draw`, not `klt gen` (klayout-tools#3115);
   see `opamp_stage1/README.md`.
2. **Bias and tail mirror `XMB1`/`XM5` (1 : 2 units, nfet, L=1.2): done
   (#204).** Separate cell `opamp_bias/` at the grid-legal W=7.820 um of
   DR-013 (the old off-grid-width prerequisite is resolved by DR-013). Three
   equal 7.82 um units in one row, `XM5 | XMB1 | XM5` (T B T), with a p-tap
   ring to `vss`. It is the canonical sub-block as netlisted; whether the
   output topology under evaluation in #47 changes the tail or sink is not
   decided here. klt and Magic DRC clean, klt LVS and netgen matched, negative
   control and `--check` pass. See `opamp_bias/README.md`.
3. **Output stage `XM6` (10 PMOS units, W=4.635 L=0.3) and `XM7` (10 NMOS
   units, W=7.820 L=1.2): done as a sub-block (#208).** Separate cell
   `opamp_out/`, canonical netlist as is (DR-012 withholds adoption of the
   experimental sink; #47 and #197 are closed and recommend no change).
   klt and Magic DRC clean, klt LVS and netgen matched, negative control and
   `--check` pass. Not joined to the other sub-blocks; a future approved
   topology change needs its own layout. See `opamp_out/README.md`.
4. **`Rz` (`res_high_po_1p41`, L=9.765) and `Cc` (`cap_mim_m3_1`, 15.62 x
   15.62).** These use `res_array` (`flavor: "high"`) and `cap_array` (MiM
   on met3/capm). Grid representability was checked first (issue #131,
   [DR-010](../spec/decision-records/DR-010-compensation-resistor-geometry.md)):
   the old L=9.763 is off-grid (klt DRC `*.ongrid.1`, 10 violations), so
   the schematic now uses 9.765; 15.62 x 15.62 is on-grid and DRC-clean.
   Evidence is in [`passive_probes/`](passive_probes/index.json), built by
   `bin/probe-passives.py`. **These are single-element passive probes, not
   full-core layout**: they show the elements can be drawn and what length
   extracts, nothing about routing, guard rings, LVS or placement. The
   routed, LVS-verified network is now [`opamp_comp/`](opamp_comp/README.md)
   (issue #167): klt DRC clean, klt LVS and netgen match, negative control
   fails as required, but the PDK's Magic `drc(full)` reports `licon.1c`
   resistor-head violations (klayout-tools#3077), so it is not foundry-DRC
   clean. Its placement is reusable; final integration may reposition it.
   The probes' Magic "clean" result did not see the resistor
   (`opamp_comp/README.md`, "Magic DRC blocker").
5. **Top-level assembly `opamp_core`: done (#220).** The sub-blocks are
   placed as committed cells (`blocks[].cell`), with supply rails, the six
   `opamp_core` pins and full-cell DRC/LVS against the whole `opamp_core`
   netlist; see `opamp_core/README.md` (Magic signoff still fails on the
   inherited `opamp_comp` finding). Next come item 11
   (#27: ERC/full-layout checks) and parasitic extraction feeding back into
   `sim/`.
