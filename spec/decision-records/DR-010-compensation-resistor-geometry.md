# DR-010: Grid-legal compensation resistor geometry (XRz L = 9.765 um)

- **Status**: proposed
- **Date**: 2026-10-10
- **Decided by**: builder agent (issue #131); not yet ratified by a human

## Context

`design/opamp_core.sch` and `design/netlist/opamp_core.spice` set the Miller
nulling resistor to `sky130_fd_pr__res_high_po_1p41 L=9.763` (W = 1.41 um by the
symbol default, 2.50 kohm per DR-007). `layout/README.md` (build order item 4)
flagged 9.763 um as off the 0.005 um manufacturing grid. #120 and #121 cover
the MOS widths and the PMOS mirror but not XRz/XCc, so this is a separate
prerequisite for full-core layout. Evidence: `layout/passive_probes/` (built by
`layout/bin/probe-passives.py` on the toolchain pinned in `layout/pdk.json`).

## Decision

1. **XRz L = 9.765 um** (W unchanged at 1.41 um). Schematic and regenerated
   netlist are changed together; `design/netlist/opamp_core.pair.json`, the
   item-1 evidence envelope, the manifest and the signoff record carry the new
   pin.
2. **XCc is unchanged** (`cap_mim_m3_1`, W = L = 15.62 um): both dimensions are
   already exact multiples of 0.005 um and the probe is DRC-clean.
3. A simulator-free regression (`design/bin/grid_check.py`,
   `tests/test_grid_check.py`) rejects any off-grid L/W on resistor and
   capacitor instances, including the prior `L=9.763`. Its `mos` class is
   deliberately not enabled; #120 owns the MOS widths and should turn that class
   on in this same mechanism rather than add a second one.

## Alternatives considered

- **L = 9.760 um** -- also grid-legal and DRC-clean, but 0.0276 % below the
  intended value versus 0.0184 % above for 9.765; 9.765 is nearer.
- **Keep 9.763 and let the layout snap** -- the generator draws 9.763 faithfully
  (extracted L = 9.763) and klt DRC then reports 10 on-grid violations
  (`li1/poly/psdm/rpm.ongrid.1`); the layout cannot be clean at the schematic
  value, and schematic != layout otherwise.
- **Change W instead** -- would move R by far more than 5 nm of L and also
  change the area/matching story; no reason to.

## Spec lines affected

None. `spec/target-spec.md` is not edited. The DR-007 "Rz 2.50 kohm" intent is
preserved to within 0.02 %.

## Consequences

Intended vs drawn, tt / 27 C, ngspice model value from the pinned model files
(typical R+C), and the layout-extracted value from `klt extract`:

| XRz L (um) | on 0.005 um grid | model R (ohm) | vs 9.763 intent | klt DRC | Magic drc(full) | extracted L (um) | extracted R (ohm) |
|---|---|---|---|---|---|---|---|
| 9.763 (prior) | no | 2502.276 | 0 | 10 violations | 0 | 9.763 | 2628.85 |
| **9.765** | yes | 2502.736 | **+0.0184 %** | clean | 0 | 9.765 | 2629.31 |
| 9.760 | yes | 2501.586 | -0.0276 % | clean | 0 | 9.760 | 2628.15 |

- Extracted L equals the schematic L exactly for the chosen length. The
  extractor's `r_ohm` is a different convention from the PDK model value (a
  constant ~+5.1 % offset, same 230 ohm/um slope); the L agreement, not the
  absolute ohms, is what ties the layout to the schematic. Reported as tool
  friction (below), not hidden.
- XCc: model C = 498.26 fF; extracted C = 499.84 fF (+0.32 %), area 243.98 um^2,
  klt DRC clean, Magic drc(full) 0. Compatible as is.
- Electrical impact (tt / 27 C, same MOS sizing, snapshot-bound records
  `20261010-102529-ba1dfa8-81edd1` baseline and `20261010-102538-ba1dfa8-fe5399`
  candidate, comparison in
  `sim/opamp-characterization/records/20261010-102538-ba1dfa8-fe5399-rz-grid-comparison.md`):
  gain, Iq and both slew rates unchanged; GBW +0.0004 %; PM +0.002 deg; swing
  +0.026 mV. No regression. Fall SR 14.64 V/us vs the ~20 V/us target is an
  existing gap (#47/#78/#79), unchanged here.
- The probes are single-element passive test cells, not full-core layout: no
  routing, guard ring or core LVS. The klt DRC uses a curated deck and Magic's
  `drc(full)` has no manufacturing-grid rule, so Magic reports 0 even for the
  off-grid 9.763 cell; the grid verdict comes from klt `*.ongrid.1` plus the
  netlist regression.
- Tool friction: filed generically as 2AMLogic/klayout-tools#3049 (extract
  r_ohm convention vs PDK model; no generator blocker was hit).

## Open items

- **The comparison is one corner (tt / 27 C), not the PVT grid.** The `ac`,
  `tran_sr` and `dc_swing` analyses of `pvt_sweep.py` are local ngspice loops
  and cannot be run as a fleet grid (shared-host rule); porting them to `klt
  sim` requests is needed for a full 5 x 3 comparison. With a +0.018 % change
  in R this is not expected to matter, but it is not demonstrated.
- No T1 item is marked met by this record; the probe success does not make the
  layout, LVS or extraction items met.
- Ratification of this record by a human; MOS grid legality (#50/#120), the
  PMOS mirror (#121) and full-core assembly are unchanged.
