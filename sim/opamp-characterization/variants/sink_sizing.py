#!/usr/bin/env python3
"""gm/ID sizing replay for the signal-dependent output sink candidate (issue #79).

Simulator-free. Reads only the committed bare-device sweep

    sim/gm-id-characterization/records/20260909-062847-35a9d46-full-sweep.csv

(W = 2.0 um, |Vds| = 0.9 V, Vsb = 0) and prints the design inputs of
`signal-dependent-sink.spice`, a replica-subtraction class-AB boost sink:

  XMP6C  pfet  gate = d2, drain -> na   1/10 replica of M6: I_6c = I(M6)/10
  XMA    nfet  diode on na              }  1:1 mirror: draws I_6c out of nx
  XMA2   nfet  drain nx, gate na        }
  XMC    pfet  gate = d1, drain -> nx   I_C = 0.9 x the 5 uA M3 mirror unit
  XMD    nfet  diode on nx              }  mirror of (I_C - I_6c), x10
  XMS    nfet  drain = out, gate nx     }  to the output as an extra sink

Sink added = 10 x max(0, I_C - I_6c). At quiescent I(M6) = 50 uA, I_6c = 5 uA
> I_C = 4.5 uA, so nx is pulled to vss and XMS is off (no static current, so
the M6/M7 balance and the systematic offset are undisturbed). When a falling
edge cuts I(M6), I_6c drops below I_C and XMS adds 10 x the deficit. The
replica tracks M6 over PVT, so there is no fixed level shift and no
dependence on the d2 DC level (which spans 0.47-0.82 V across corners).

Sizing rule (gm/ID first, same rows and interpolation as DR-007):
  nfet L = 1.2: the DR-007 mirror unit density J0 = 5 uA / 7.819 um
                = 0.639 uA/um (gm/ID 18); 5 uA at J0 -> 7.819 um -> drawn 7.820
                (grid; +0.013 %, the only deviation from a 1:1 ratio).
  pfet L = 0.3: the DR-007 M3/M4/M6 density, gm/ID 14, J = 1.078993 uA/um;
                5 uA -> 4.634 um -> drawn 4.635 (grid, +0.02 %); 4.5 uA ->
                4.1706 um -> drawn 4.170.

Usage:
    python3 sim/opamp-characterization/variants/sink_sizing.py
"""
from __future__ import annotations

import csv
import math
import os
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
FULL = os.path.join(REPO, "sim", "gm-id-characterization", "records",
                    "20260909-062847-35a9d46-full-sweep.csv")
GRID_UM = 0.005
SWEEP_W_UM = 2.0
I_UNIT_A = 5e-6
MULT_S = 10           # XMS multiplicity (= replica ratio: M6 is 10 units of M3)
IC_FRACTION = 0.9     # I_C as a fraction of the M3 unit current (margin for mirror error)
GM_ID_PFET = 14.0     # DR-007 gm/ID of M3/M4/M6


def load(device, length):
    rows = defaultdict(list)
    with open(FULL) as fh:
        for r in csv.DictReader(fh):
            if r["device"] != device or float(r["length_um"]) != length:
                continue
            i = float(r["id_a"])
            if i > 0:
                rows[(r["corner"], float(r["temp_c"]))].append((float(r["overdrive_bias_v"]), i, r))
    for k in rows:
        rows[k].sort(key=lambda t: t[0])
    return rows


def interp_gmid(series, target):
    """Density (uA/um) at which gm/ID == target, linear in J between bracketing rows
    (the interpolation DR-007 quotes literally, so 7.819 / 4.634 um are reproduced)."""
    pts = [(float(r["gm_id_per_v"]), i / SWEEP_W_UM * 1e6) for _, i, r in series if r["gm_id_per_v"]]
    pts.sort(key=lambda t: t[0])
    for (g0, j0), (g1, j1) in zip(pts, pts[1:]):
        if g0 <= target <= g1 and g1 > g0:
            f = (target - g0) / (g1 - g0)
            return j0 + f * (j1 - j0), (g0, j0), (g1, j1)
    raise ValueError("gm/ID outside sweep")


def snap(w):
    return round(w / GRID_UM) * GRID_UM


def legal(w):
    return abs(w / GRID_UM - round(w / GRID_UM)) < 1e-9


def main():
    n = load("nfet", 1.2)[("tt", 27.0)]
    p = load("pfet", 0.3)[("tt", 27.0)]
    jn, (gn0, jn0), (gn1, jn1) = interp_gmid(n, 18.0)
    jp, (gp0, jp0), (gp1, jp1) = interp_gmid(p, GM_ID_PFET)
    print("1. nfet L=1.2 mirror unit (DR-007, gm/ID 18), tt/27C:")
    print(f"   rows gm/ID {gn0:.6f} @ J {jn0:.6f} and {gn1:.6f} @ J {jn1:.6f} uA/um -> J = {jn:.6f} uA/um")
    w_n = 5.0 / jn
    print(f"   5 uA -> W = {w_n:.4f} um -> drawn {snap(w_n):.3f} um (grid-legal {legal(snap(w_n))}; "
          f"DR-007 unit 7.819 um, ratio {snap(w_n) / 7.819:.5f})")
    print("2. pfet L=0.3 M3/M4/M6 unit (DR-007, gm/ID 14), tt/27C:")
    print(f"   rows gm/ID {gp0:.6f} @ J {jp0:.6f} and {gp1:.6f} @ J {jp1:.6f} uA/um -> J = {jp:.6f} uA/um")
    w_rep = 5.0 / jp
    w_c = IC_FRACTION * 5.0 / jp
    print(f"   XMP6C: 5 uA -> W = {w_rep:.4f} um -> drawn {snap(w_rep):.3f} um (grid-legal {legal(snap(w_rep))}; "
          f"DR-007 unit 4.634 um, ratio {snap(w_rep) / 4.634:.5f})")
    print(f"   XMC:   {IC_FRACTION * 5:.1f} uA -> W = {w_c:.4f} um -> drawn {snap(w_c):.3f} um "
          f"(grid-legal {legal(snap(w_c))}; I_C/I_unit = {snap(w_c) / 4.634:.4f})")
    wn, wr, wc = snap(w_n), snap(w_rep), snap(w_c)
    print("3. Drawn devices (all nf = 1, so finger width = W):")
    area_n = wn * 1.2 * (1 + 1 + 1 + MULT_S)
    area_p = (wr + wc) * 0.3
    print(f"   XMA, XMA2, XMD: nfet {wn:.3f}/1.2 m=1;  XMS: nfet {wn:.3f}/1.2 m={MULT_S};  "
          f"XMP6C: pfet {wr:.3f}/0.3 m=1;  XMC: pfet {wc:.3f}/0.3 m=1")
    print(f"4. Drawn gate area added (W*L, NOT layout area): nfet {area_n:.2f} um^2 + pfet {area_p:.3f} um^2 "
          f"= {area_n + area_p:.2f} um^2  (baseline MOS gate area 153.13 um^2, "
          f"+{(area_n + area_p) / 153.13 * 100:.0f} %)")
    print("5. Quiescent current added (design): replica leg I_6c = I(M6)/10 = 5 uA from vdd "
          "(XMP6C -> XMA); XMC/XMS static current ~ 0 (I_C < I_6c). 5 uA of the 1.8 V rail ~ +9 uW.")
    print("6. Boost law: I_S = 10 x max(0, I_C - I_6c). I_C = 4.5 uA, so I_S = 10 x (4.5 uA - I(M6)/10) "
          "= 45 uA - I(M6) for I(M6) < 45 uA; e.g. I(M6) = 14 uA -> 31 uA extra sink.")
    # Density spread: I_6c replicas track M6 (same L, same Vsg density), so only mirror
    # accuracy limits the quiescent margin. Report the Vds term as a stated caveat.
    print("   Caveat: XMP6C has |Vds| ~ 1.2 V vs M6's ~ 0.9 V; the sweep is at |Vds| = 0.9 V, "
          "so the 10 % I_C margin is a design choice, not a computed tolerance. The fleet record measures it.")


if __name__ == "__main__":
    main()
