# layout/opamp_core: assembled op-amp core (issue #220)

`opamp_core` is the four committed sub-block GDS files placed and routed in
one cell through `layout/bin/compose-cell.py`: `opamp_bias` (`XMB1`/`XM5`),
`opamp_stage1` (`XM1`-`XM4`), `opamp_out` (`XM6`/`XM7`) and `opamp_comp`
(`XRz`/`XCc`), imported with `blocks[].cell` (#210). The LVS reference is the
whole of `design/netlist/opamp_core.spice` (all 10 device cards) with pins
`vdd vss inn inp out ibias`; `d1`, `d2`, `tail` and `cz` are
`lvs.internal_nets`.

**Status: klt DRC, extraction and LVS pass; the PDK's Magic `drc(full)` does
NOT pass.** The Magic failure is the `opamp_comp` resistor-head finding
(`opamp_comp/README.md`, "Magic DRC blocker"), inherited unchanged. It was not
fixed here and is not waived: this layout must not be described as
foundry-DRC-clean. No schematic, spec or sizing changed, so no new PVT
campaign was run. Nothing in `manifests/` cites this directory (follow-up).

## Result

| Step | Result | Evidence |
|---|---|---|
| `klt drc --deck sky130` | `status: "clean"`, `violation_count: 0` | `drc.json` |
| `klt extract --deck sky130` | `extracted`: 35 unit devices (10 + 3 + 20 + 2 from the sub-blocks), 10 nets | `extract.json`, `opamp_core.spice` |
| Geometry checks (`compose-cell.py`) | every reference card's `L`, summed `W` (MOS), resistor and capacitor geometry match the extraction | run it |
| `klt lvs` vs the full `opamp_core` reference | `status: "match"`: devices 10/10, nets 10/10; boundary pins `vdd vss inn inp out ibias` | `lvs.json` |
| LVS negative control (`XM6` gate `d2` -> `vss`) | `status: "mismatch"`, `mismatch_count: 10`; nets 6/10, devices 9/10 matched | `negative-control/` |
| `compose-cell.py --check` | rebuild is byte-identical (SHA-256 of `opamp_core.gds`, every `gen/*.gds`, import records, reference, verdicts) | run it |
| Magic 8.3.683 `drc(full)`, `sky130A.tech` | **FAIL: 2 errors**, rule `poly contact extends poly resistor by < 2.16um (licon.1c + li.5)`, the inherited `opamp_comp` finding. The `opamp_comp` run also reported the contact-length rule (1 box); it is absent here. Not investigated. Non-vacuous: types seen include `nmos pmos ppolyres mimcap metal1-4` | `magic-signoff/magic.json` |
| netgen 1.5.133 + `sky130A_setup.tcl` (Magic extraction vs the same reference) | `Circuits match uniquely.`, `Netlists match uniquely.` **but the pin lists differ**: Magic exports the labelled internal nets `d1 d2 tail cz` as ports, the reference has only the six boundary pins. netgen altered the pin lists to match; `pins_matched` is `false`, so `magic-signoff.py` exits 3 on this as well as on DRC | `magic-signoff/netgen.out` |

Toolchain: klt `0.7.0+g4cbdfa769875`, KLayout 0.30.12, sky130A open_pdks
`c6d73a35f524070e85faff4a6a9eef49553ebc2b` (`layout/pdk.json`). Bounding box
-20.0 .. 141.5 x -32.41 .. 25.5 um (includes pin stubs). Top-cell GDS SHA-256
`59f900e1dcbb088a7b9da9aad761685def2208f7139a671db2f0fbe5d46bf25a`.

## Regenerate and check

```
uv venv /tmp/klt-4cbdfa7
uv pip install --python /tmp/klt-4cbdfa7/bin/python \
  "klayout-tools @ git+https://github.com/2AMLogic/klayout-tools@4cbdfa7698752b720c0e627163867de1e23475f3"
export PATH=/tmp/klt-4cbdfa7/bin:$PATH
export PDK_ROOT=$HOME/.volare PDK=sky130A   # the pinned PDK; a host may default to another install
python3 layout/bin/compose-cell.py layout/opamp_core/cell.json                       # regenerate
python3 layout/bin/compose-cell.py layout/opamp_core/cell.json --check               # reproduce
python3 layout/bin/compose-cell.py layout/opamp_core/cell.json --negative-control XM6:g=vss
python3 layout/bin/magic-signoff.py layout/opamp_core/cell.json                      # exits 3 today
```

## Floorplan and conventions

- Placement is explicit: `opamp_bias` at (0, 0), `opamp_stage1` at (40, 0),
  `opamp_out` at (30, -30), `opamp_comp` at (95, -30). Sub-blocks are not
  mirrored or modified.
- Routed here (route layer): `tail` met2, `d2` met3, `ibias` met1, `out` met2,
  `vdd` met1, `vss` met4 trunk, `inn` met3 and `inp` met2. `d1` and `cz` exist
  only inside their sub-blocks and keep their sub-block labels.
- `vss` joins all four sub-blocks. `rel_vss` is an 8 um li1 rectangle
  overlapping the `stage1` vss stub: it moves the vss via stack 8 um clear of
  the `inn` pin stack (0.4 um away at the stub). Without it klt's router
  rejected `inn`/`inp`.
- `inn`/`inp` use `waypoints_um` to leave the crowded west side of `stage1`
  northwards. Pins: `ibias` west, `inn`/`inp` north, `vss`/`vdd`/`out` east.
- The router is a heuristic and has no obstacle avoidance; the clean DRC and
  the LVS match are the checks, not the floorplan.

## What the checks do and do not establish

- `klt lvs` compares topology; `compose-cell.py` additionally checks `L`/`W`
  of every card from the extraction (see `layout/README.md`). Resistance and
  capacitance values are the extractor's own and are not compared, and LVS
  treats the two `XCc` plates as interchangeable (`opamp_comp/README.md`).
- Rail continuity is established by the LVS match (one `vdd` net, one `vss`
  net, 10/10 nets); no parasitic extraction or IR-drop check was run.
- `--check` does not run Magic or netgen; `magic-signoff/` is regenerated by
  running `magic-signoff.py`.
- This is a layout-versus-schematic result only. No post-layout simulation
  was run.
