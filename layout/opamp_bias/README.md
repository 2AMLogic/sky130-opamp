# layout/opamp_bias: bias and tail mirror (`XMB1` / `XM5`)

Issue #204. This sub-block lays out the canonical NMOS bias/tail mirror from
`design/netlist/opamp_core.spice` as a separately reusable cell:

| Device | Model | Netlist | Units drawn |
|---|---|---|---|
| `XMB1` `ibias ibias vss vss` | `sky130_fd_pr__nfet_01v8` | W=7.820 L=1.2, `m=1` | 1 x 7.82 x 1.2 um |
| `XM5` `tail ibias vss vss` | `sky130_fd_pr__nfet_01v8` | W=7.820 L=1.2, `mult=2 m=2` | 2 x 7.82 x 1.2 um |

The width is the grid-legal one of
[DR-013](../../spec/decision-records/DR-013-grid-legal-mos-widths.md); sizing,
topology and the 1 : 2 ratio are unchanged (unit count only, DR-002/DR-007).

## Scope and limits

This is a partial cell, not the op-amp layout. It is not joined to
`opamp_stage1/`, `opamp_comp/` or the (not yet drawn) output stage, so T1
item 2 stays `unmet`, no manifest cites it, and the integrator GDS stays
null. It does not close #27's full-layout ERC requirement. It does not adopt
any output-stage/sink topology (#47, #197 experiment); it is the canonical
group as netlisted, and a later approved topology change needs its own
layout. Parasitics are not extracted, so nothing here says the matching
survives routing.

## Result

| Step | Result | Evidence |
|---|---|---|
| `klt drc --deck sky130` | `clean`, 0 violations; 49 rules checked, 0 skipped, 0 unknown, `nothing_checked: false` | `drc.json` |
| `klt extract` | 3 units (all nfet, W=7.82 L=1.2), 3 nets | `extract.json`, `opamp_bias.spice` |
| `klt lvs` (`combine_devices`) | `match`: devices 2/2, nets 3/3, pins 3/3 | `lvs.json` |
| Geometry check (driver) | grouped by terminal nets: `XMB1` 1 unit, 7.82 um; `XM5` 2 units, sum 15.64 um; L exactly 1.2 | `compose-cell.py` exit 0 |
| Magic 8.3.683 `drc(full)`, `sky130A.tech` | **0 errors**; types seen `pwell nmos ndiff ndiffc psubdiff psubdiffcont poly polycont locali viali metal1 via1 metal2`; none of `nmos ndiff psubdiff poly` missing | `magic-signoff/magic.json` |
| netgen 1.5.133, `sky130A_setup.tcl` | `Netlists match uniquely.`, pins `ibias tail vss` equivalent | `magic-signoff/netgen.out` |
| Negative control `XM5:g=tail` (also tried `XMB1:g=tail`) | `status: "mismatch"`, `mismatch_count: 8` | `negative-control/` |
| `compose-cell.py --check` | rebuild in a temp dir is byte-identical (GDS SHA-256s, reference, verdict fields) | run it |

Top-cell GDS SHA-256:
`468a3daab5f2a7ae720bb751553323e58a15f4f7c7acee253aeebd910eb26d71`.
Toolchain: klt `0.7.0+g4cbdfa769875` (git `4cbdfa76`, throwaway venv from
`git+https://github.com/2AMLogic/klayout-tools@4cbdfa76`, not the host klt,
which is a different build), KLayout 0.30.12, sky130A open_pdks
`c6d73a35f524070e85faff4a6a9eef49553ebc2b`, Magic 8.3.683, netgen 1.5.133.

Magic is a real second opinion here. The first composition, without the top
poly endcaps, was klt-DRC clean and LVS-matched but Magic reported 24 sites
(`poly.7`, `poly.8`) at the gate tops; klt's curated deck has no poly-endcap
rule. That run is not committed; the fix is the endcap in `fe_masks`.

### What the LVS multiplicity means

`XM5` carries `mult=2 m=2`. In the sky130 model subckt `mult` feeds only the
mismatch formulas and the inner device has no `m`, so the effective count is
`m` = 2 (one-point ngspice check, see `layout/README.md`): `XM5` is two
7.82 um units, giving three units in the group (1 : 2). The older
`W * m * mult` reading (four units) was wrong for `mult = m`; the driver now
uses `m`. `klt lvs` cannot take `m` > 1, so the committed
`opamp_bias.ref.spice` holds `XM5_1`, `XM5_2` with `m=1 mult=1`; `XMB1` and
every other token are verbatim.

## Floorplan and matching

One `klt gen mos_array` block (`mb`: 1 row x 3 columns, `common_centroid`, no
dummies, `gate_contact`, p-tap ring). Coordinates in um, cell frame:

```
              col 0 (diff x 0..2.04)  col 1 (2.44..4.48)  col 2 (4.88..6.92)
 unit         U1 = XM5                U0 = XMB1           U2 = XM5
 S pad x      0.21                    2.65                5.09
 D pad x      1.83                    4.27                6.71
 gate x       0.42..1.62 (L=1.2)      2.86..4.06          5.30..6.50
 diff y 0..7.82, gate pad licon y 8.43, p-tap ring outer -1.07..7.99 x -1.07..9.71
```

- **T B T.** The diode device `XMB1` is the centre unit and the two `XM5`
  units flank it, so both devices share the array-centre x-centroid and the
  same y-centroid (one row). A linear gradient in either direction cancels
  to first order. A B T B row would put the diode at an edge and the tail
  centroid off-centre; with a 1 : 2 ratio T B T is the only symmetric
  three-unit order.
- **Same orientation** for all units (source west, drain east, gate pad
  north), no mirroring.
- **No dummies.** The ring replaces an identical neighbour on the outer
  sides. Common to both devices by symmetry, but the edge units are not
  shielded; a dummy-flanked variant is a possible refinement (it would
  change the area, not the sizing).
- **Ring.** The generator's p-tap ring is the body contact for all units
  (`vss`). `fe_masks` (a `klt draw` overlay in the same frame) adds what the
  sky130 generators do not draw: `nsdm` over the diffusions, a `psdm` ring
  over the tap ring, `npc` over each gate licon and 0.15 um poly endcaps at
  both gate ends (`poly.8` needs 0.13 um). Unlike `opamp_stage1`, the
  generator's own geometry needed no replacement.

## Routing and pins

| Net | Plane | Path |
|---|---|---|
| `vss` | met1 | each source pad down to a bus at y=-1.6, to the ring `TAP_S`; ring `TAP_W` west to the pin |
| `tail` | met2 | outer drains (`XM5`) down to a bus at y=-2.2, east to the pin |
| `ibias` | met1 | centre drain (`XMB1`) up x=4.27 to a gate bus at y=9.0 tying all three gates, west to the pin |

`ibias` and the `vss` stub are on the west edge (x=-6), `tail` on the east
(x=15.5). The ring and the sources are the same net, so the source buses and
the ring merge by design. Routing is not symmetric between the two `XM5`
units' drain/gate paths and `XMB1`'s; only the devices are matched, and
parasitics are not extracted.

## klt gaps (friction protocol)

The sky130 `mos_array` and `klt lvs` hit two gaps, one already filed and one new:

- `mos_array` draws no `nsdm`/`psdm`/`npc` or poly endcap
  (2AMLogic/klayout-tools#2934, #2936): drawn in `fe_masks`.
- `klt lvs` cannot represent a multiplied device (`m` > 1, and `mult` > 1)
  from a `subckt-call` reference: worked around by expanding the reference
  (see above). Filed as 2AMLogic/klayout-tools#3123.

## Reproduce

```
python3 layout/bin/compose-cell.py layout/opamp_bias/cell.json            # regenerate in place
python3 layout/bin/compose-cell.py layout/opamp_bias/cell.json --check    # byte-exact rebuild check
python3 layout/bin/compose-cell.py layout/opamp_bias/cell.json --negative-control XM5:g=tail
python3 layout/bin/magic-signoff.py layout/opamp_bias/cell.json           # Magic DRC + netgen LVS
```

`layout/README.md` has the pinned-toolchain venv recipe.

## Files

`cell.json` (recipe), `gen/` (per-block requests, responses, streams),
`compose.request.json`, `compose.response.json`, `opamp_bias.gds`, `drc.json`,
`extract.json`, `opamp_bias.spice`, `opamp_bias.ref.spice` (generated
reference), `lvs.request.json`, `lvs.json`, `negative-control/`,
`magic-signoff/`.
