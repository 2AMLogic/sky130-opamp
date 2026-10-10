#!/usr/bin/env python3
"""gm/ID sizing replay for the tail-clamp candidate (issue #78).

Simulator-free. Reads only the committed bare-device sweep

    sim/gm-id-characterization/records/20260909-062847-35a9d46-full-sweep.csv

(nfet_01v8, W = 2.0 um, |Vds| = 0.9 V, Vsb = 0) and prints:

1. the DR-007 mirror-group design point (MB1/M5/M7, L = 1.2 um, gm/ID = 18)
   re-interpolated, so the clamp is sized from the same rows DR-007 cites;
2. the clamp device MCL's current density and width for the chosen design
   clamp level (tt / 27 C), and the grid-legal drawn width;
3. for the drawn MCL width, the implied clamp level at every corner/temperature
   in the sweep (how well the clamp level tracks the bias diode over PVT).

Interpolation: Vgs is linear in ln(Id) between the two bracketing sweep rows
(both sides of the design point are in weak/moderate inversion, where ln(Id)
is close to linear in Vgs). This is a sizing estimate, not a circuit solve:
the sweep has Vsb = 0, while MCL's source sits at the clamp level, so body
effect makes the real clamp level somewhat LOWER than printed here (the
45-unit fleet record is the measurement; this script is only the design input).

Usage:
    python3 sim/opamp-characterization/variants/tail_clamp_sizing.py                      # tail-clamp.spice
    python3 sim/opamp-characterization/variants/tail_clamp_sizing.py --vclamp 0.05 --m 4  # tail-clamp-vc050.spice
"""
from __future__ import annotations

import argparse
import csv
import math
import os
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
FULL = os.path.join(REPO, "sim", "gm-id-characterization", "records",
                    "20260909-062847-35a9d46-full-sweep.csv")

GRID_UM = 0.005
L_UM = 1.2            # same channel length as the MB1/M5/M7 group (tracking)
SWEEP_W_UM = 2.0
I_UNIT_A = 5e-6       # DR-007: 5 uA per mirror unit
W_MIRROR_UM = 7.819   # DR-007 drawn MB1/M5/M7 unit width (inherited, off-grid)
I_CLAMP_A = 10e-6     # MCL must be able to carry the whole tail current (2 units)
V_CLAMP_DESIGN = 0.100  # design clamp level of the tail node at tt / 27 C (V)
MCL_M = 8             # MCL drawn as 8 parallel units (m = 8)


def load():
    rows = defaultdict(list)
    with open(FULL) as fh:
        for r in csv.DictReader(fh):
            if r["device"] != "nfet" or float(r["length_um"]) != L_UM:
                continue
            idv = float(r["id_a"])
            if idv <= 0:
                continue
            rows[(r["corner"], float(r["temp_c"]))].append(
                (float(r["overdrive_bias_v"]), idv, r))
    for k in rows:
        rows[k].sort(key=lambda t: t[0])
    return rows


def vgs_at_density(series, j_ua_per_um):
    """Vgs at which a W=2 um device carries j*W; returns (vgs, lo_row, hi_row)."""
    target = j_ua_per_um * 1e-6 * SWEEP_W_UM
    for (v0, i0, r0), (v1, i1, r1) in zip(series, series[1:]):
        if i0 <= target <= i1:
            f = (math.log(target) - math.log(i0)) / (math.log(i1) - math.log(i0))
            return v0 + f * (v1 - v0), r0, r1
    raise ValueError(f"density {j_ua_per_um} uA/um outside sweep")


def density_at_vgs(series, vgs):
    for (v0, i0, _), (v1, i1, _) in zip(series, series[1:]):
        if v0 <= vgs <= v1:
            f = (vgs - v0) / (v1 - v0)
            return math.exp(math.log(i0) + f * (math.log(i1) - math.log(i0))) / SWEEP_W_UM * 1e6
    raise ValueError(f"Vgs {vgs} outside sweep")


def snap(w):
    return round(w / GRID_UM) * GRID_UM


def main():
    global V_CLAMP_DESIGN, MCL_M
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--vclamp", type=float, default=V_CLAMP_DESIGN,
                    help="design clamp level of V(tail) at tt/27C (V); default %(default)s")
    ap.add_argument("--m", type=int, default=MCL_M, help="MCL unit count; default %(default)s")
    args = ap.parse_args()
    V_CLAMP_DESIGN, MCL_M = args.vclamp, args.m
    rows = load()
    tt = rows[("tt", 27.0)]
    j0 = I_UNIT_A / W_MIRROR_UM * 1e6
    vgs_b, r0, r1 = vgs_at_density(tt, j0)
    print("1. Bias diode MB1 (DR-007 mirror group), tt/27C, L=1.2:")
    print(f"   J0 = 5 uA / {W_MIRROR_UM} um = {j0:.6f} uA/um "
          f"(gm/ID rows: {float(r0['gm_id_per_v']):.6f} @ Vgs {r0['overdrive_bias_v']}, "
          f"{float(r1['gm_id_per_v']):.6f} @ Vgs {r1['overdrive_bias_v']})")
    print(f"   Vgs(MB1) = {vgs_b:.4f} V   (= V(ibias), the clamp gate)")

    vgs_cl = vgs_b - V_CLAMP_DESIGN
    j_cl = density_at_vgs(tt, vgs_cl)
    w_tot = I_CLAMP_A / (j_cl * 1e-6)
    w_unit = snap(w_tot / MCL_M)
    print(f"\n2. Clamp MCL, tt/27C: Vgs = {vgs_b:.4f} - {V_CLAMP_DESIGN:.3f} = {vgs_cl:.4f} V")
    print(f"   J_cl = {j_cl:.6f} uA/um  (density ratio J0/J_cl = {j0 / j_cl:.2f})")
    print(f"   W_total for {I_CLAMP_A * 1e6:.0f} uA = {w_tot:.3f} um -> m = {MCL_M} x {w_unit:.3f} um "
          f"(on 0.005 um grid: {abs(w_unit / GRID_UM - round(w_unit / GRID_UM)) < 1e-9}), "
          f"drawn total {w_unit * MCL_M:.3f} um")
    w_drawn = w_unit * MCL_M

    print("\n3. Implied clamp level V(tail) at which MCL carries 10 uA (Vsb = 0 estimate):")
    print("   corner  T(C)   Vgs(MB1)  Vgs(MCL,10uA)  clamp level")
    for (corner, temp) in sorted(rows):
        s = rows[(corner, temp)]
        vb, _, _ = vgs_at_density(s, j0)
        vc, _, _ = vgs_at_density(s, I_CLAMP_A / w_drawn * 1e6)
        print(f"   {corner:6s} {temp:6.1f}   {vb:.4f}    {vc:.4f}         {vb - vc:+.4f} V")

    print("\n4. Drawn gate area added: MCL "
          f"{MCL_M} x {w_unit:.3f} x {L_UM} = {w_drawn * L_UM:.2f} um^2 "
          "(gate area only; not a layout area)")


if __name__ == "__main__":
    main()
