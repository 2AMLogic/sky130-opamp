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
  omit the device). klt does not need them. The generator gap that made this
  block necessary (klayout-tools#3077) is fixed as of klt `v0.8.0`, which
  draws all three itself -- but that revision is evaluated and NOT adopted
  here, for reasons measured under "Magic DRC blocker" below, so the block
  stays.
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
hand-drawn head, which this directory deliberately does not do because it
would replace the generator output the DR-010 geometry decision rests on).
Until then this block must not be described as foundry-DRC-clean. The
generator-side gap is tracked upstream as klayout-tools#5659; the revision
that closed klayout-tools#3077 was evaluated and rejected, below.

### klt 0.8.0 evaluated and rejected (issue #281, measured 2026-11-14)

klayout-tools#3077 was closed COMPLETED on 2026-10-15 by upstream PR #3344.
**The revision that contains the fix is klt `v0.8.0`**, git
`c572046be644e0407f693f2410f3abb799d68a3a` (`klt version --format json`
reports `is_release: true`, `klayout_version: 0.30.13`); upstream PR #3344's
merge commit `d2513c2be158edfd1d38f056048e5662697373fa` is an ancestor of
that tag and a descendant of `v0.7.0`. It is also the revision
`.github/workflows/signoff.yml` already pins.

**It was regenerated, measured end to end, and NOT adopted.** This directory
stays on klt `0.7.0+g4cbdfa769875` with the `rz_masks` block in place. klt
0.8.0 clears one of the two committed `licon.1c` rules and introduces five
violations of a third, taking Magic `drc(full)` from **2 errors to 7**.

What klt 0.8.0 genuinely fixes: the generator draws RPM 86/20, PSDM 94/20 and
NPC 95/20 itself (one merged 11.045 x 2.600 um shape each over the whole
unit), so `rz_masks` is no longer needed to make the device visible, and
Magic recognises it in the *bare generator output* for the first time.
Measured on a standalone `klt gen res_array` unit, no repo geometry present:

| standalone unit | Magic types seen | `drc(full)` |
|---|---|---|
| klt `0.7.0+g4cbdfa769875` (committed `gen/rz.gds`) | `poly polycont locali` -- **no `ppolyres`** | 0 errors, **vacuously**: Magic sees no resistor |
| klt `0.8.0` | `xpolycontact ppolyres locali` | **6 errors** (`licon.1c + li.5` x1, `rpm.1` x3, `poly.2` x2) |

So the generator's own output is not Magic-DRC-clean once Magic can see the
device. In the composed cell the net effect is:

| `sky130A.tech` rule | klt 0.7.0 | klt 0.8.0 | |
|---|---|---|---|
| `area xpc/li 700000 350` -- "poly resistor contact length < 2.0um (licon.1c)" | 1 box | **0** | cleared |
| `extend xpc/a xhrpoly,uhrpoly 2160` -- "poly contact extends poly resistor by < 2.16um (licon.1c + li.5)" | 2 boxes | 2 boxes | unchanged |
| `cifwidth rpm_generate 1270` -- "Width of RPM/URPM < 1.27um (rpm.1)" | 0 | **5 boxes** | new |
| **total** | **2** | **7** | |

Mechanisms, read off `sky130A.tech` rather than inferred from the verdict:

- **Cleared.** `area xpc/li 700000 350` requires the resistor contact's
  local-metal pad to be at least 0.7 um2 with no dimension under 0.35 um. klt
  0.7.0's pad is 0.420 x 1.410 = 0.5922 um2 and fails; klt 0.8.0's is
  0.390 x 2.200 = 0.858 um2 and passes. The 0.190 x 2.000 um end contacts
  klt 0.8.0's own `drc_hints` note advertises are what make room for it.
- **Unchanged.** `extend xpc/a xhrpoly,uhrpoly 2160` measures the *contact*
  (`xpc`), and wants 2.160 um. Magic's two error boxes are each 1.695 um wide
  and span exactly the 1.410 um body width, i.e. 1.695 um of the required
  extension is absent. klt 0.8.0's 2.200 um figure is the **pad height**, not
  the `xpc` extension this rule measures, so the new head does not touch it.
  Which edges Magic measures here is still not traced through `sky130A.tech`
  in full; what is measured is that the count does not move.
- **New.** `rpm.1` is a `cifwidth` check on `rpm_generate`, which
  `sky130A.tech` *derives* (`bloat-all xhrpoly,uhrpoly xpc; grow 620;
  shrink 420; mask-hints RPM; mask-hints URPM; and-not rpm_block`) -- it is
  not the drawn RPM. The committed `rz_masks` RPM is drawn exactly coincident
  with the poly outline (x 2.005 .. 12.610, y 22.0 .. 23.41 -- the outline
  itself), so the drawn and derived regions agree and the rule stays silent.
  klt 0.8.0's generator-drawn RPM instead overhangs the unit by 0.250 um on
  every side (x -0.250 .. 10.795, y -0.595 .. 2.005 in unit coordinates),
  which leaves steps narrower than the 1.270 um minimum. `klt gen --list`
  exposes no `res_array` parameter controlling the marker margin, so the
  recipe cannot suppress this, and a marker cannot be subtracted in GDS.

Everything *except* Magic passed on klt 0.8.0, so the rejection is the PDK's
Magic rules alone: klt `drc --deck sky130` `clean`/0 violations (on a deck
that grew to a new `content_hash`
`sha256:ba0f97887e3d231aec8b54f1f52f2941ded0228f0234b6759712bcaca0e942e6`),
`klt lvs` `match` 2/2 devices and 4/4 nets, the `XRz:w=d2` negative control
still `mismatch` (12), `compose-cell.py --check` byte-identical, netgen
`Circuits match uniquely.` with `pins_matched: true`, and the POLYRES body
still exactly 9.765 x 1.410 um so DR-010 is unaffected. The regenerated
top-cell GDS SHA-256 would be
`77e6f0358f1139b7b58f007373cb168e577c5e0a901cc3ff430bb8b0b9e018dd` and the
bounding box is unchanged at -6.0 .. 39.5 x 0.0 .. 25.965 um. `rz` x stays
2.005 (the POLYRES left edge moves 2.425 -> 2.395 um, preserving the 5 nm
offset the extraction depends on) and `pin_cz` x stays 20.0 (the cz backbone
centre line moves 16.200 -> 16.180 um, still on the 0.005 um grid; a
full-vertex scan of the regenerated stream found no off-grid coordinate).

**Why it is not adopted.** Adopting it would raise this directory's recorded
foundry-DRC failure from 2 errors to 7 and hand the same regression to
`layout/opamp_core/`, which imports `opamp_comp.gds` by path, for no design
benefit -- the `rz_masks` deletion it enables is cosmetic, because those three
rectangles lie strictly inside klt 0.8.0's generator-drawn markers and the
painted union is identical either way. The remaining gap is filed upstream in
generic terms as **klayout-tools#5659**, with a standalone reproducer that
needs no geometry from this repo: the oversized RPM marker with no parameter
to control it, and the still-unsatisfied `xpc` extension. Adopting the bump is
one command set
(`layout/pdk.json` -> klt 0.8.0 / `c572046be644...` / KLayout 0.30.13, delete
the `rz_masks` block, then the "Regenerate and check" recipe with
`PDK_ROOT=$HOME/.volare` exported) if a later reader weighs the trade
differently.

Note for anyone re-running this on klt 0.8.0 or newer: `klt pdk find` now
resolves `~/.ciel` (open_pdks `f6eeac7d...`) by default and lists `~/.volare`
only as an `ambiguous_sources` entry, so **`PDK_ROOT=$HOME/.volare` must be
exported** or `compose-cell.py` refuses on the open_pdks pin. klt 0.8.0 then
reports `provenance.pdk.compatibility.status: "mismatch"` in every generated
JSON; that is cosmetic and must *not* be "fixed" by moving to the `~/.ciel`
PDK, because `layout/pdk.json`'s `open_pdks_commit` has to equal
`sim/gm-id-characterization/pdk.json`'s.
