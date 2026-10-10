#!/usr/bin/env python3
"""gm/ID sizing replay for the signal-dependent output sink candidate (issue #79).

Simulator-free. Reads only the committed bare-device sweep

    sim/gm-id-characterization/records/20260909-062847-35a9d46-full-sweep.csv

(nfet_01v8, L = 1.2 um, W = 2.0 um, |Vds| = 0.9 V, Vsb = 0) and prints the
design inputs of `signal-dependent-sink.spice`:

  MF2  bias leg of the follower, gate = ibias, mirror of MB1 at ratio ~0.2
  MF1  source follower, gate = d2 (the second-stage drive node), source = g
  MS   boost sink, drain = out, gate = g, source = vss

Topology: when the output must fall, M6 is turned off by d2 rising. d2 is
level-shifted down by one Vgs through MF1 and drives MS. In quiescent (d2 about
0.82 V at tt/27 C, measured by a single-corner local op probe) g sits near
0.2 V and MS is in deep subthreshold, so the quiescent current is about zero and
the M6/M7 balance (and hence the systematic offset) is not disturbed. On a
falling edge d2 rises, g follows at gain < 1, and MS turns on exponentially.
M7 (the fixed 50 uA sink) is untouched.

Sizing rule (gm/ID first): MF2 is the DR-007 mirror unit scaled so it carries
I_F = 1 uA at Vgs(MB1) (current-density ratio kept at 1, so only W is scaled).
MF1 has the same W and L (same current in the follower, so same Vgs; its Vgs
at g ~ 0.2 V is a little larger from body effect, which only lowers the
quiescent g further). MS is sized so that it carries I_BOOST at the gate
voltage G_BOOST, using the density at that Vgs from the sweep.

Usage:
    python3 sim/opamp-characterization/variants/sink_sizing.py [--gboost V --iboost A --m N]
"""
from __future__ import annotations

import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tail_clamp_sizing as tcs  # noqa: E402  (reuse the sweep loader/interpolators)

I_F_A = 1e-6          # follower bias current (0.2 of a 5 uA mirror unit)
G_BOOST_V = 0.80      # MS gate voltage at which MS should carry I_BOOST (tt/27 C)
I_BOOST_A = 100e-6    # boost sink current at G_BOOST (2x the fixed M7 sink)
MS_M = 4              # MS drawn as 4 parallel units
MS_L_UM = 1.2


def main():
    global G_BOOST_V, I_BOOST_A, MS_M
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--gboost", type=float, default=G_BOOST_V)
    ap.add_argument("--iboost", type=float, default=I_BOOST_A)
    ap.add_argument("--m", type=int, default=MS_M)
    a = ap.parse_args()
    G_BOOST_V, I_BOOST_A, MS_M = a.gboost, a.iboost, a.m
    rows = tcs.load()
    tt = rows[("tt", 27.0)]
    j0 = tcs.I_UNIT_A / tcs.W_MIRROR_UM * 1e6
    vgs_b, r0, r1 = tcs.vgs_at_density(tt, j0)
    print(f"1. Bias diode MB1: J0 = {j0:.6f} uA/um, Vgs(MB1) = V(ibias) = {vgs_b:.4f} V "
          f"(gm/ID rows {float(r0['gm_id_per_v']):.6f} / {float(r1['gm_id_per_v']):.6f})")
    w_f_raw = I_F_A / (j0 * 1e-6)
    w_f = tcs.snap(w_f_raw)
    print(f"2. Follower MF1/MF2 (L = {tcs.L_UM}): J = J0 for I_F = {I_F_A * 1e6:.1f} uA -> "
          f"W = {w_f_raw:.4f} um -> drawn {w_f:.3f} um (grid-legal: "
          f"{abs(w_f / tcs.GRID_UM - round(w_f / tcs.GRID_UM)) < 1e-9}); "
          f"actual I_F at J0 = {j0 * w_f:.4f} uA, ratio to MB1 {w_f / tcs.W_MIRROR_UM:.4f}")
    j_b = tcs.density_at_vgs(tt, G_BOOST_V)
    w_tot = I_BOOST_A / (j_b * 1e-6)
    w_unit = tcs.snap(w_tot / MS_M)
    print(f"3. Boost sink MS (L = {MS_L_UM}), tt/27C: Vgs = {G_BOOST_V:.3f} V -> "
          f"J = {j_b:.4f} uA/um -> W_total for {I_BOOST_A * 1e6:.0f} uA = {w_tot:.2f} um "
          f"-> m = {MS_M} x {w_unit:.3f} um (drawn total {w_unit * MS_M:.3f} um; grid-legal: "
          f"{abs(w_unit / tcs.GRID_UM - round(w_unit / tcs.GRID_UM)) < 1e-9})")
    w_d = w_unit * MS_M
    print("\n4. MS current vs gate voltage at the drawn size (Vds = 0.9 V sweep, Vsb = 0), tt/27C:")
    for vg in (0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00):
        try:
            print(f"   Vg = {vg:.2f} V  I = {tcs.density_at_vgs(tt, vg) * w_d:10.4f} uA")
        except ValueError:
            print(f"   Vg = {vg:.2f} V  outside sweep")
    print("\n5. MS current at Vg = V(ibias)-referenced corner spread (I at the Vgs that gives "
          f"{I_BOOST_A * 1e6:.0f} uA at tt/27C, per corner/T):")
    for (c, t) in sorted(rows):
        try:
            print(f"   {c:3s} {t:6.1f}  I = {tcs.density_at_vgs(rows[(c, t)], G_BOOST_V) * w_d:10.3f} uA at Vg = {G_BOOST_V:.2f} V")
        except ValueError:
            print(f"   {c:3s} {t:6.1f}  outside sweep")
    print(f"\n6. Drawn gate area added (W*L, not layout area): MF1+MF2 = {2 * w_f * tcs.L_UM:.3f} um^2, "
          f"MS = {w_d * MS_L_UM:.2f} um^2, total = {2 * w_f * tcs.L_UM + w_d * MS_L_UM:.2f} um^2")


if __name__ == "__main__":
    main()
