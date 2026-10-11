# layout/opamp_comp: Miller compensation network (`XRz` + `XCc`)

This is the routed compensation sub-block of `opamp_core` (issue #167). It
holds `XRz` (`sky130_fd_pr__res_high_po_1p41`, `L=9.765`, model-default
`W=1.41`) in series with `XCc` (`sky130_fd_pr__cap_mim_m3_1`,
`W=L=15.62`), joined at `cz`, exactly as in `design/netlist/opamp_core.spice`:

```
XRz cz d2 vss sky130_fd_pr__res_high_po_1p41 L=9.765 mult=1 m=1
XCc cz out    sky130_fd_pr__cap_mim_m3_1     W=15.62 L=15.62 MF=1 m=1
```

**It is a sub-block, not the op-amp's layout.** Full-core GDS stays
unqualified, T1 item 2 stays `unmet`, and nothing in `manifests/` cites this
directory. No schematic, spec or target changed, so no new PVT campaign was
run.

**Status: klt DRC, extraction, LVS and netgen pass; the PDK's Magic
`drc(full)` does NOT pass.** The Magic DRC failure is a resistor-head
finding, reported below as a blocker for Magic signoff. It is not hidden or
waived.

## Result

| Step | Result | Evidence |
|---|---|---|
| `klt drc --deck sky130` | `status: "clean"`, `violation_count: 0` | `drc.json` |
| `klt extract --deck sky130` | `extracted`: 1 `res_high_po` + 1 `cap_mim`, 4 nets | `extract.json`, `opamp_comp.spice` |
| Passive geometry check (`compose-cell.py`) | resistor `l_um 9.765`, `w_um 1.41`, 1 body; capacitor plate area 243.9844 um2 and perimeter 62.48 um (= `W*L*MF*m`, `2(W+L)`) | `extract.json` |
| `klt lvs` (subckt-call reference, inline extraction) | `status: "match"`: devices 2/2, nets 4/4, pins 4/4; `body_verification: "verified"` | `lvs.json` |
| LVS negative control (`XRz` substrate `vss` -> `d2`, scratch reference) | `status: "mismatch"`, `mismatch_count: 12`; devices 1/2 and nets 1/4 matched | `negative-control/` |
| `compose-cell.py --check` | rebuild is byte-identical (SHA-256 of `opamp_comp.gds` and every `gen/*.gds`, reference text, verdict fields) | run it |
| Magic 8.3.683 `drc(full)`, `sky130A.tech` | **FAIL: 2 rules (3 boxes)**, all on the resistor heads: `licon.1c` "poly resistor contact length < 2.0um" and "poly contact extends poly resistor by < 2.16um". Non-vacuous: types seen include `xpolycontact ppolyres mimcap mimcapcontact metal1-4` | `magic-signoff/magic.json` |
| netgen 1.5.133 + `sky130A_setup.tcl` (Magic extraction vs. the same reference) | `Circuits match uniquely.`, `Netlists match uniquely.`; pins `cz d2 out vss` equivalent. Magic extracts `X1 d2 cz vss sky130_fd_pr__res_high_po_1p41 l=9.765` and `X0 cz out sky130_fd_pr__cap_mim_m3_1 l=15.62 w=15.62` | `magic-signoff/netgen.out`, `magic-signoff/opamp_comp.magic.spice` |

Toolchain: klt `0.7.0+g4cbdfa769875`, KLayout 0.30.12, sky130A open_pdks
`c6d73a35f524070e85faff4a6a9eef49553ebc2b` (`layout/pdk.json`). Bounding box
-6.0 .. 39.5 x 0.0 .. 25.965 um (includes the pin stubs). Top-cell GDS
SHA-256 `0b882615ffe00b5f14e208cfeb43a17f0f7be97f63a5ad40b3b3facb2f6e7b9e`.

## Regenerate and check

Use the pinned klt in a throwaway venv (no host-wide install is touched):

```
uv venv /tmp/klt-4cbdfa7
uv pip install --python /tmp/klt-4cbdfa7/bin/python \
  "klayout-tools @ git+https://github.com/2AMLogic/klayout-tools@4cbdfa7698752b720c0e627163867de1e23475f3"
export PATH=/tmp/klt-4cbdfa7/bin:$PATH
python3 layout/bin/compose-cell.py layout/opamp_comp/cell.json                       # regenerate
python3 layout/bin/compose-cell.py layout/opamp_comp/cell.json --check               # reproduce
python3 layout/bin/compose-cell.py layout/opamp_comp/cell.json --negative-control XRz:w=d2
python3 layout/bin/magic-signoff.py layout/opamp_comp/cell.json                      # exits 3 today (Magic DRC)
```

## Floorplan and conventions

- `cc`: `klt gen cap_array`, one 15.62 x 15.62 top plate. Bottom plate is
  met3 (`out`), top plate is capm/met4 (`cz`).
- `rz`: `klt gen res_array`, `flavor: "high"`, `num: 1`, `dummy: 0`, above the
  capacitor. `R0_A` -> `d2` (li1, west stub), `R0_B` -> `cz` (met4 route down
  to the capacitor's top plate).
- `tap`: `klt gen guard_ring` with `add_well: false`, a p-tap ring beside the
  resistor. With `psdm` over the ring (`tap_masks`) klt's extractor ties the
  resistor body to this ring, which is named `vss`. It is a sibling of `rz`,
  not a guard ring around it: the substrate is a single node and the ring
  only needs to reach it.
- `rz_masks`: RPM 86/20, PSDM 94/20 and NPC 95/20 over the resistor's full
  poly outline. `res_array` draws the first two over the body only and no
  NPC; without them the PDK's Magic does not see a resistor at all (the Magic
  DRC would be "clean" while checking no resistor rule, and extraction would
  omit the device). klt does not need them; see klayout-tools#3077.
- `Rz` x origin is 2.005 um. Magic resolves a 9.765 um body only when its
  edges sit at a 5 nm offset from its 10 nm input scale; at x = 2.000 it
  extracts a generic `res_high_po w=0.705 l=10.47` with both terminals on
  `d2`. `pin_cz` is placed at x = 20.0 so the cz backbone (centred midway
  between the two pins) lands on the 0.005 um grid (klayout-tools#3079).
- Pins: `d2` (li1), `out` (met3), `vss` (li1) and **`cz`** (met4). `cz` is an
  *observation pin*: the LVS flow has no internal-only nets, so the series
  node is exposed. Final integration may drop it by hiding the net.

## What the checks do and do not establish

- `klt lvs` compares topology and the resistor substrate connection
  (`body_verification: verified`). It does **not** compare `R`, `L`, `W` (a
  resistor's geometry parameters are "secondary") or `C` (a placeholder for
  `subckt-call` references). `compose-cell.py` therefore checks them from
  the extract JSON against the source card: resistor `L` and `W` within 1e-6
  um, `W` taken from the card or the `_1p41` model default 1.41, body count =
  `m*mult`; capacitor plate area within a relative 1e-6 and perimeter within
  1e-4 um of `W*L*MF*m` and `2*(W+L)*MF*m`. Resistance and capacitance values
  are the extractor's own and are not compared.
- LVS treats the two capacitor plates as interchangeable: swapping the
  reference to `XCc out cz` still reports `match` (checked manually). That
  `cz` is the top plate and `out` the bottom plate is a floorplan choice
  recorded here, not something LVS enforces.
- The `LVS` input is the GDS (`lvs.layout_input: "gds"`, inline extraction
  with the sky130 deck). The pre-extracted netlist form reads the resistor as
  an undefined subcircuit and fails on topology (klayout-tools#3078).
- `--check` compares GDS bytes, the generated reference and the verdict
  fields. It does not run Magic or netgen; `magic-signoff.py` is a separate
  step and `magic-signoff/` is regenerated by running it.

## Magic DRC blocker

With the markers above Magic recognises the resistor as `xhrpoly`
(`ppolyres`/`xpolycontact`) and applies the precision-resistor rules. The
klt-generated 0.42 um wide poly heads then fail the two `licon.1c` rules
(contact length 2.0 um, extension 2.16 um). The earlier passive probes
(`layout/passive_probes/`, issue #131) reported Magic `drc(full)` clean for
the same generator output, but Magic did not recognise a resistor in those
streams, so that result did not exercise these rules. It is not a
regression: those probe artifacts are preserved unchanged.

This is a generator limitation, not a wiring fault: the klt deck is clean,
the topology matches in both klt and netgen, and the capacitor, routing and
tap pass Magic DRC. Closing the blocker needs a resistor head geometry with
a 2.0 um contact bar and 2.16 um extension (the klt generator, or a
hand-drawn head, which this PR deliberately does not do because it would
replace the generator output the DR-010 geometry decision rests on). It is
reported as klayout-tools#3077. Until then this block must not be described
as foundry-DRC-clean.
