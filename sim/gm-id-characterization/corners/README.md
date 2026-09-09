# Confirmed 1.8V-core MOS corner grid

This directory answers `spec/target-spec.md` Section 1's `[TBD]` "Corner
grid" row and `spec/porting-plan.md` Section 4's "corner-grid confirmation"
open item, by pointer.

`model-files.json` is the confirmed, machine-readable corner-model file
list — verified directly against the pinned PDK checkout named in
`../pdk.json` (open_pdks `c6d73a35f524070e85faff4a6a9eef49553ebc2b`,
`sky130A`), not assumed from `sky130-bandgap`'s 3.3V-primary grid (which
runs a different device flavor at a different supply, per
`porting-plan.md` Section 2).

## The grid

Five standard sky130 process corners, confirmed present in this pinned
checkout for both 1.8V-core device polarities:

| Corner | nfet_01v8 model file | pfet_01v8 model file |
|---|---|---|
| `tt` | `sky130_fd_pr__nfet_01v8__tt.pm3.spice` | `sky130_fd_pr__pfet_01v8__tt.corner.spice` |
| `ff` | `sky130_fd_pr__nfet_01v8__ff.pm3.spice` | `sky130_fd_pr__pfet_01v8__ff.corner.spice` |
| `ss` | `sky130_fd_pr__nfet_01v8__ss.pm3.spice` | `sky130_fd_pr__pfet_01v8__ss.corner.spice` |
| `sf` | `sky130_fd_pr__nfet_01v8__sf.pm3.spice` | `sky130_fd_pr__pfet_01v8__sf.corner.spice` |
| `fs` | `sky130_fd_pr__nfet_01v8__fs.pm3.spice` | `sky130_fd_pr__pfet_01v8__fs.corner.spice` |

This is the same five-corner *shape* `sky130-bandgap`'s ratified spec
uses (`spec/target-spec.md`'s prediction), now confirmed to exist for the
1.8V-core (`_01v8`) device flavor specifically, rather than assumed by
analogy from a 3.3V-primary sibling. Each corner's harness include is
`libs.tech/ngspice/corners/<corner>.spice` — verified by direct `grep` of
that file's own `.include` lines for `nfet_01v8`/`pfet_01v8` (excluding
mismatch and ESD-device includes, which are not this experiment's
concern) rather than assumed from the combined
`libs.tech/combined/sky130.lib.spice`'s `.lib <corner> ... .endl` section
names.

**Why the harness includes `libs.tech/ngspice/corners/<corner>.spice`
directly, not the combined library**: the combined
`libs.tech/combined/sky130.lib.spice` pulls in RF, ESD, high-voltage and
bipolar device families this bare-MOSFET sweep never touches, and parsing
all of it took **~118s per ngspice invocation** in this environment against
one op-point — versus **~1.4s** via the per-corner include actually used by
`bin/sweep.py`. Both resolve to the *same* underlying
`sky130_fd_pr__{nfet,pfet}_01v8__<corner>.*.spice` files (confirmed by
inspecting the combined library's `.lib <corner>` section, which itself
`.include`s `corners/<corner>.spice`) — this is a parse-time optimization,
not a different model source. Filed as a `klayout-tools` friction-protocol
candidate if this parse-time cost turns out to matter for other blocks'
harnesses too; not filed yet since it is an ngspice/PDK-library-structure
observation, not a `klayout-tools` gap.

## Naming convention

Standard SkyWater sky130 corner mnemonic: `tt` = typical-typical, `ff` =
fast-fast, `ss` = slow-slow, `fs` = fast-NMOS/slow-PMOS, `sf` =
slow-NMOS/fast-PMOS. This experiment does not lean on that mnemonic being
correct in either direction for any conclusion — every corner's nfet_01v8
and pfet_01v8 data is measured and reported in `../records/` on its own
terms, not inferred from the corner's name.

## What is not a corner axis here

Process corner (this file) and simulation temperature are orthogonal in
sky130's ngspice deck convention: temperature is a `.temp` analysis
setting, not a separate model file, so it is not enumerated here. This
experiment's PVT grid is process (5, this file) × temperature (3:
`-40C`/`27C`/`125C`, matching `spec/target-spec.md` Section 1's Operating
temperature row) — see `../README.md`.

Supply voltage is **not** a third swept axis for this bare-device study.
`VDS` is the study's own representative fixed bias (see `../README.md` for
the value and rationale), not a node tied to a `VDD` net the way a
full-circuit testbench (e.g. a PSRR or line-regulation bench) would sweep
`VIN`/`VDD` directly — there is no "supply corner" for a two-terminal-bias
device sweep, so this experiment does not manufacture one. Once a topology
is drawn (out of this issue's scope), that circuit's own testbenches will
carry the standard three-point supply axis (`1.62V`/`1.80V`/`1.98V`, per
`spec/target-spec.md` Section 1's Supply row) the way every other block in
the fleet's `sim/` harnesses do.
