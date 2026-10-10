# layout/

This directory holds the layout of `opamp_core`, built with klayout-tools
(`klt`), together with its DRC, extraction and LVS evidence. Each laid-out
sub-block lives in its own `layout/<cell>/` directory. That directory holds
the recipe (`cell.json`), every intermediate request/response, the composed
GDS, and the reports that back each claim in the cell's README.

**Status: one sub-block, `opamp_stage1/` (the NMOS input pair `XM1`/`XM2`).**
That is not the op-amp's layout. T1 item 2 is `unmet`, and nothing in
`manifests/` cites this directory.

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
  card's `L` exactly and its `W` exactly as a sum of drawn units.
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
hand-written. A missing or duplicated card, a duplicate selection, a
non-MOS card, a terminal net outside the pin list, or a pin no card uses is
a hard error. Bare sky130 geometry literals (`L=1.2`) are read as
micrometres because the request names `reference.deck: "sky130"`
(klayout-tools#1492/#1505). The sibling's `u`-suffix rewrite is therefore
not needed. Unit tests (all `layout/bin/test_*.py`: stage_reference,
compose-cell, magic-signoff; tool-free, run from the repo root of a full
checkout, as in `.github/workflows/tests.yml`):

```
python3 -m unittest discover -s layout/bin -p 'test_*.py' -v
```

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

## Plan for the remaining groups

DR-002/DR-007 fix the matching structure: three equal-length groups, with
mirror ratios set by unit count only. Each step below is one sub-block
directory or an extension of one, with the same evidence set.

1. **First stage, PMOS mirror `XM3`/`XM4`.** Blocked on #50: W=4.634 is
   off the 0.005 um grid, which needs a sizing decision record. Then the
   mirror is added to `opamp_stage1/` as a `diff_pair` with
   `mirror: true, flavor: "pfet"`, with an n-tap ring to `vdd`, `vdd`
   added as the seventh pin, and 4/4 devices.
2. **Bias and tail mirror `XMB1`/`XM5` (1 : 2 units, nfet, L=1.2).** This
   is a three-unit common-centroid row (B T B, or T B T with dummies). Its
   W=7.819 is off-grid too (#50). It also depends on #47, which may change
   the tail topology.
3. **Output stage `XM6` (10 PMOS units of the `XM3`/`XM4` device) and `XM7`
   (10 NMOS units of the `XMB1` device).** These are interdigitated arrays
   sharing the mirror groups' unit devices, each with its own guard ring.
   Their size and topology wait on #47 (slew-rate topology evaluation) and
   #50.
4. **`Rz` (`res_high_po_1p41`, L=9.763) and `Cc` (`cap_mim_m3_1`, 15.62 x
   15.62).** These use `res_array` (`flavor: "high"`) and `cap_array` (MiM
   on met3/capm). Check grid representability of both first: 9.763 is
   off-grid.
5. **Top-level assembly `opamp_core`.** The sub-blocks are placed as
   committed cells (`blocks[].cell`, a sibling feature this port has not
   needed yet), with supply rails, the six `opamp_core` pins and full-cell
   DRC/LVS against the whole `opamp_core` netlist. After that come item 11
   (#27: ERC/full-layout checks) and parasitic extraction feeding back into
   `sim/`.
