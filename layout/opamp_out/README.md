# layout/opamp_out: canonical output stage (`XM6` / `XM7`)

Issue #208. This sub-block lays out the canonical output devices of
`design/netlist/opamp_core.spice` as a separately reusable cell:

| Device | Model | Netlist | Units drawn |
|---|---|---|---|
| `XM6` `out d2 vdd vdd` | `sky130_fd_pr__pfet_01v8` | W=4.635 L=0.3, `mult=10 m=10` | 10 x 4.635 x 0.3 um |
| `XM7` `out ibias vss vss` | `sky130_fd_pr__nfet_01v8` | W=7.820 L=1.2, `mult=10 m=10` | 10 x 7.82 x 1.2 um |

Pins: `out d2 ibias vdd vss`. Widths are the grid-legal ones of
[DR-013](../../spec/decision-records/DR-013-grid-legal-mos-widths.md); sizing,
topology and unit counts are unchanged. Multiplicity follows the repo's rule
(`m`, not `m * mult`, see `layout/README.md`): ten units each, not a hundred.

## Scope and limits

A partial cell, not the op-amp layout. It is not joined to `opamp_stage1/`,
`opamp_bias/` or `opamp_comp/`, so T1 item 2 stays `unmet`, no manifest cites
it, and the integrator GDS stays null. Nothing here closes #27 (ERC), the
slew target, or the compensation resistor-head Magic failure
(`opamp_comp/`). It is the canonical output stage as netlisted. DR-012
withholds adoption of the experimental sink (#47) and the #197 bias study
recommends no candidate; a later approved topology change needs its own layout,
and drawing this cell is not a vote for the canonical topology. Parasitics are
not extracted, so nothing here says the matching survives routing.

## Result

| Step | Result | Evidence |
|---|---|---|
| `klt drc --deck sky130` | `clean`, 0 violations; 53 rules checked, 0 skipped, 0 unknown, `nothing_checked: false` | `drc.json` |
| `klt extract` | 20 units (10 nfet W=7.82 L=1.2, 10 pfet W=4.635 L=0.3), 5 nets | `extract.json`, `opamp_out.spice` |
| `klt lvs` (`combine_devices`) | `match`: devices 2/2, nets 5/5, pins 5/5 | `lvs.json` |
| Geometry check (driver) | grouped by terminal nets: `XM6` 10 units, sum 46.35 um; `XM7` 10 units, sum 78.2 um; L exact | `compose-cell.py` exit 0 |
| Magic 8.3.683 `drc(full)`, `sky130A.tech` | **0 errors**; types seen include `nwell nmos pmos ndiff pdiff psubdiff nsubdiff poly`; none of the expected types missing | `magic-signoff/magic.json` |
| netgen 1.5.133, `sky130A_setup.tcl` | `Netlists match uniquely.`, pins `d2 ibias out vdd vss` equivalent | `magic-signoff/netgen.out` |
| Negative control `XM6:g=ibias` (also `XM7:g=d2`) | `status: "mismatch"`, `mismatch_count` 3 (and 1); committed evidence is the first | `negative-control/` |
| `compose-cell.py --check` | rebuild in a temp dir is byte-identical (GDS SHA-256s, reference, verdict fields) | run it |

Top-cell GDS SHA-256:
`cd4f621d3534b63d9eba5b30ba25701c0c0d74d8748a7b6e3ac9f5bcfb4d034a`.
Bounding box -6.0, -2.41 to 52.5, 9.835 um (pin stubs included; the arrays
themselves span x -1.07..25.07 for `XM7` and 31.88..49.12 for `XM6`, n-well included).
Toolchain: klt `0.7.0+g4cbdfa769875` (throwaway venv from the pinned git
commit, not the host klt), KLayout 0.30.12, sky130A open_pdks
`c6d73a35f524070e85faff4a6a9eef49553ebc2b`, Magic 8.3.683, netgen 1.5.133.
No simulator was run; this is a physical-verification result only.

Verdict: all four physical checks pass, the negative control fails as
required and `--check` reproduces. The cell is qualified as a sub-block, not
as the op-amp. Two first-iteration failures happened and are not committed:
the unrouted `vdd` net (the router needed an explicit ring-to-bus leg) and a
set of off-grid licons/ports and a `met1.space.1` hit from tying the ring at
a bus column 0.11 um from a source strap; both were fixed in the recipe.

## Floorplan

Two one-row arrays, side by side, each unit identical and in the same
orientation (source west, drain east, gate pad north):

- **`XM7`, block `mn`** (`klt gen mos_array`, 1 x 10, `nfet`, no dummies):
  pitch 2.44 um, diff 2.04 x 7.82 um, p-tap ring to `vss`.
- **`XM6`, block `mp6`** (`klt draw`, built to the `opamp_stage1` `mp34`
  conventions): pitch 1.54 um, diff 1.14 x 4.635 um (one full-width unit, 13
  licons per pad), n-tap ring to `vdd` with the n-well 0.2 um beyond it, `psdm`
  over the diffusions, `nsdm` ring, `npc` over the gate licons and 0.15 um poly
  endcaps. It is drawn, not generated, for the reason given in
  `opamp_stage1/README.md` (the generator's 0.42 um gate pad vs a 0.3 um
  gate fails Magic `poly.4`).
- **`fe_masks`** adds the `nsdm`/`psdm` ring/`npc`/endcap masks the NMOS
  `mos_array` does not draw (klayout-tools#2934, #2936), as in `opamp_bias/`.

All units of a device share every terminal, so unit order does not matter
electrically; there is no centroid structure to claim beyond identical
adjacent units and a shared ring. No dummies: the edge units are not shielded.

## Routing and pins

| Net | Plane | Path |
|---|---|---|
| `ibias` | met1 | `XM7` gate pads up to a bus at y=9.0, west to the pin |
| `vss` | met1 | `XM7` source straps down to a bus at y=-1.6, west to the ring, ring `TAP_W` to the pin |
| `out` | met2 | all drain straps (both arrays) down to one bus at y=-2.2, east to the pin |
| `d2` | met1 | `XM6` gate pads joined on a bus through the pad row, east to the pin |
| `vdd` | met1 | `XM6` source straps down to a bus at y=-1.6, east to the ring, ring `TAP_E` to the pin |

`ibias`, `vss` pins west; `out`, `d2`, `vdd` east. The ring and sources of a
device are the same net, so source buses and ring merge by design.

## LVS reference

`opamp_out.ref.spice` is generated by `layout/bin/stage_reference.py` from the
`XM6` and `XM7` cards, verbatim, with each `m=10` card expanded to ten
`m=1 mult=1` cards (`klt lvs` cannot take `m` > 1; klayout-tools#3123). No
device parameter is hand-written.

## Reproduce

```
python3 layout/bin/compose-cell.py layout/opamp_out/cell.json            # regenerate in place
python3 layout/bin/compose-cell.py layout/opamp_out/cell.json --check     # byte-exact rebuild check
python3 layout/bin/compose-cell.py layout/opamp_out/cell.json --negative-control XM6:g=ibias
python3 layout/bin/magic-signoff.py layout/opamp_out/cell.json            # Magic DRC + netgen LVS
python3 layout/opamp_out/make-cell-json.py | diff - layout/opamp_out/cell.json
```

`layout/README.md` has the pinned-toolchain venv recipe. `make-cell-json.py`
only documents how `cell.json`'s coordinates follow from the unit pitches;
`cell.json` is the source of truth.

## klt gaps

No new tool gap was needed. The existing ones apply: implant/endcap masks
(2AMLogic/klayout-tools#2934, #2936) and multiplied-device LVS (#3123).

## Files

`cell.json`, `make-cell-json.py`, `gen/`, `compose.request.json`,
`compose.response.json`, `opamp_out.gds`, `drc.json`, `extract.json`,
`opamp_out.spice`, `opamp_out.ref.spice`, `lvs.request.json`, `lvs.json`,
`negative-control/`, `magic-signoff/`.
