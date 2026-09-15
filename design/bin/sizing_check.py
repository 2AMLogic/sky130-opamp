#!/usr/bin/env python3
"""Re-derive every number in spec/decision-records/DR-002-device-sizing.md.

This script performs **no simulation**. It reads the already-committed
bare-device gm/ID sweep

    sim/gm-id-characterization/records/20260909-062847-35a9d46-full-sweep.csv

and does three things:

1.  `validate`  -- proves the interpolation used below is the same one the
    sweep harness itself used, by reproducing every populated row of the
    committed `-summary.csv` from the full sweep.
2.  `widths`    -- prints the two literal full-sweep rows bracketing each
    device's chosen gm/ID design point, the interpolated current density,
    and the channel width that density implies for that device's assigned
    bias current.
3.  `corners`   -- takes the *committed* widths (as drawn in
    design/opamp_core.sch), back-solves each device's operating point at
    tt/27C, ss/-40C and ff/125C from its fixed current density, and prints
    the first-order gain / bandwidth / headroom / noise / power figures
    DR-002 quotes.

Every figure it prints is an operating-point estimate read off a bare-device
DC sweep at |Vds| = 0.9 V and Vsb = 0 -- not an operating-point solve of the
actual circuit, and not an AC or transient simulation. See DR-002 "Open
items" for what that caveat does and does not cover.

Usage:
    python3 design/bin/sizing_check.py [validate|widths|corners|all]
"""

from __future__ import annotations

import csv
import math
import os
import sys
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RECORD = os.path.join(REPO, "sim", "gm-id-characterization", "records",
                      "20260909-062847-35a9d46")
FULL = RECORD + "-full-sweep.csv"
SUMMARY = RECORD + "-summary.csv"

BOLTZMANN = 1.380649e-23  # J/K

# ---------------------------------------------------------------------------
# The committed design point (mirrors design/opamp_core.sch exactly).
# ---------------------------------------------------------------------------
IREF = 5e-6     # external reference current sunk into the ibias pin
ISS = 10e-6     # input-pair tail current   (M5 = 2 x MB1)
ID1 = 5e-6      # per-side input-pair current
ID2 = 50e-6     # output-stage current      (M7 = 10 x MB1, M6 = 10 x M3/M4)
CC = 0.4998e-12  # Cc as drawn: cap_mim_m3_1, W = L = 15.62 um
CL = 2e-12      # DR-001
RZ = 2000.0     # Rz as drawn: res_high_po_1p41, L = 7.585 um

W_IN = 1.325    # M1, M2          nfet_01v8, L = 1.2 um, m = 1
W_P = 2.745     # M3, M4 (m = 1), M6 (m = 10)   pfet_01v8, L = 0.6 um
W_N = 3.835     # MB1 (m = 1), M5 (m = 2), M7 (m = 10)  nfet_01v8, L = 1.2 um

L_IN, L_P, L_N = 1.2, 0.6, 1.2

CORNERS = [("tt", 27.0, 1.80), ("ss", -40.0, 1.62), ("ff", 125.0, 1.98)]


def load():
    rows = list(csv.DictReader(open(FULL)))
    grouped = defaultdict(list)
    for idx, r in enumerate(rows):
        key = (r["device"], r["corner"], float(r["length_um"]), float(r["temp_c"]))
        grouped[key].append((idx + 2, r))  # +2 => 1-based line number in the CSV
    return grouped


GROUPS = load()


def _usable(key):
    return [(ln, r) for ln, r in GROUPS[key]
            if r["gm_id_per_v"] and float(r["id_a"]) > 0]


def interp_at_gmid(dev, corner, length, temp, target):
    """Linear interpolation in gm/ID between the two adjacent sweep points.

    This is the same interpolation the sweep harness used to build
    `-summary.csv`; `validate` below proves it reproduces that file exactly.
    Current density is interpolated log-linearly, because drain current is
    close to exponential in Vgs over one 20 mV sweep step.
    """
    pts = sorted(_usable((dev, corner, length, temp)),
                 key=lambda t: float(t[1]["gm_id_per_v"]))
    for (la, a), (lb, b) in zip(pts, pts[1:]):
        ga, gb = float(a["gm_id_per_v"]), float(b["gm_id_per_v"])
        if ga <= target <= gb and gb > ga:
            f = (target - ga) / (gb - ga)
            ja = float(a["id_a"]) / float(a["width_um"]) * 1e6
            jb = float(b["id_a"]) / float(b["width_um"]) * 1e6
            out = {k: float(a[k]) + f * (float(b[k]) - float(a[k]))
                   for k in ("vov_v", "gm_gds", "ft_hz", "overdrive_bias_v",
                             "vth_v", "cgg_f")}
            out["J"] = math.exp(math.log(ja) + f * (math.log(jb) - math.log(ja)))
            out["cgg_per_um"] = out["cgg_f"] / float(a["width_um"])
            out["bracket"] = ((la, a), (lb, b), ga, gb, f, ja, jb)
            return out
    return None


def interp_at_J(dev, corner, length, temp, j_target):
    """Back-solve the operating point of a device of *fixed* width carrying a
    *fixed* current, i.e. at a fixed current density j_target (uA/um)."""
    pts = sorted(_usable((dev, corner, length, temp)),
                 key=lambda t: float(t[1]["id_a"]))
    for (_, a), (_, b) in zip(pts, pts[1:]):
        ja = float(a["id_a"]) / float(a["width_um"]) * 1e6
        jb = float(b["id_a"]) / float(b["width_um"]) * 1e6
        if ja <= j_target <= jb and jb > ja:
            f = (math.log(j_target) - math.log(ja)) / (math.log(jb) - math.log(ja))
            out = {k: float(a[k]) + f * (float(b[k]) - float(a[k]))
                   for k in ("gm_id_per_v", "vov_v", "gm_gds", "ft_hz",
                             "overdrive_bias_v", "vth_v", "cgg_f")}
            out["cgg_per_um"] = out["cgg_f"] / float(a["width_um"])
            return out
    return None


# ---------------------------------------------------------------------------
def cmd_validate():
    print("== interpolation validation against the committed -summary.csv ==")
    worst = {"vov_v": 0.0, "gm_gds": 0.0, "ft_hz": 0.0}
    compared = skipped = 0
    for s in csv.DictReader(open(SUMMARY)):
        if not s["vov_v"]:
            skipped += 1
            continue
        got = interp_at_gmid(s["device"], s["corner"], float(s["length_um"]),
                             float(s["temp_c"]), float(s["gm_id_target_per_v"]))
        if got is None:
            skipped += 1
            continue
        compared += 1
        for k in worst:
            ref = float(s[k])
            worst[k] = max(worst[k], abs(got[k] - ref) / max(abs(ref), 1e-30))
    print(f"  rows reproduced from -full-sweep.csv : {compared}")
    print(f"  rows skipped (target unreachable)    : {skipped}")
    for k, v in worst.items():
        print(f"  max relative deviation, {k:8s}     : {v:.3e}")
    ok = all(v == 0.0 for v in worst.values())
    print(f"  => {'EXACT match' if ok else 'MISMATCH'}")
    return 0 if ok else 1


DEVICE_POINTS = [
    ("M1/M2 input pair",           "nfet", L_IN, 10.0, ID1, W_IN, 1),
    ("M3/M4/M6 PMOS unit device",  "pfet", L_P,  10.0, ID1, W_P, 1),
    ("MB1/M5/M7 NMOS unit device", "nfet", L_N,  15.0, IREF, W_N, 1),
]


def cmd_widths():
    print("== width derivation at tt/27C (the sizing corner) ==")
    print(f"   source: {os.path.relpath(FULL, REPO)}")
    print("   CSV columns: device,corner,length_um,width_um,temp_c,vds_v,"
          "overdrive_bias_v,vov_v,id_a,gm_s,gds_s,cgg_f,vth_v,gm_id_per_v,"
          "gm_gds,ft_hz")
    for label, dev, length, gmid, current, drawn_w, _ in DEVICE_POINTS:
        r = interp_at_gmid(dev, "tt", length, 27.0, gmid)
        (la, a), (lb, b), ga, gb, f, ja, jb = r["bracket"]
        print(f"\n-- {label}: {dev}_01v8, L = {length} um, gm/ID = {gmid} 1/V,"
              f" Id = {current*1e6:g} uA")
        print(f"   line {la}: {','.join(a[k] for k in a)}")
        print(f"      gm/ID = {ga:.6f} 1/V,  Id/W = {ja:.6f} uA/um")
        print(f"   line {lb}: {','.join(b[k] for k in b)}")
        print(f"      gm/ID = {gb:.6f} 1/V,  Id/W = {jb:.6f} uA/um")
        print(f"   interpolated at gm/ID = {gmid}: Id/W = {r['J']:.6f} uA/um,"
              f" Vov = {r['vov_v']:+.4f} V, gm/gds = {r['gm_gds']:.2f}")
        need = current * 1e6 / r["J"]
        print(f"   required W = {current*1e6:g} uA / {r['J']:.6f} uA/um"
              f" = {need:.4f} um   ->  drawn W = {drawn_w} um"
              f"  ({100*(drawn_w-need)/need:+.2f} %)")
        if drawn_w / 1 < 0.42:
            print("   *** below the PDK minimum finger width of 0.42 um ***")
    return 0


def cmd_corners():
    print("== committed sizing, evaluated across the corner extremes ==")
    j_in, j_p, j_n = ID1 * 1e6 / W_IN, ID1 * 1e6 / W_P, IREF * 1e6 / W_N
    print(f"   fixed current densities: M1/M2 {j_in:.5f}, M3/M4/M6 {j_p:.5f},"
          f" MB1/M5/M7 {j_n:.5f} uA/um")
    for corner, temp, vdd in CORNERS:
        o1 = interp_at_J("nfet", corner, L_IN, temp, j_in)
        op = interp_at_J("pfet", corner, L_P, temp, j_p)
        on = interp_at_J("nfet", corner, L_N, temp, j_n)
        gm1 = o1["gm_id_per_v"] * ID1
        gm34 = op["gm_id_per_v"] * ID1
        gm2 = op["gm_id_per_v"] * ID2
        a1 = 1.0 / (1.0 / o1["gm_gds"]
                    + (op["gm_id_per_v"] / o1["gm_id_per_v"]) / op["gm_gds"])
        a2 = 1.0 / (1.0 / op["gm_gds"]
                    + (on["gm_id_per_v"] / op["gm_id_per_v"]) / on["gm_gds"])
        av = a1 * a2
        gbw = gm1 / (2 * math.pi * CC)
        p2 = gm2 / (2 * math.pi * CL)
        sr = ISS / CC
        en = math.sqrt(16 * BOLTZMANN * (temp + 273.15) / (3 * gm1)
                       * (1 + gm34 / gm1))
        icm_lo = o1["overdrive_bias_v"] + on["vov_v"]
        icm_hi = vdd - op["overdrive_bias_v"] + o1["overdrive_bias_v"] - o1["vov_v"]
        dz = 1.0 / gm2 - RZ
        zero = "infinite" if abs(dz) < 1.0 else f"{1.0/(2*math.pi*CC*dz)/1e6:+.0f} MHz"
        iq = IREF + ISS + ID2
        print(f"\n-- {corner}/{temp:+.0f}C, VDD = {vdd} V")
        print(f"   M1/M2   gm/ID {o1['gm_id_per_v']:6.2f}  Vov {o1['vov_v']:+.4f}"
              f"  Vgs {o1['overdrive_bias_v']:.4f}  gm/gds {o1['gm_gds']:7.2f}"
              f"  fT {o1['ft_hz']/1e9:.3f} GHz  gm1 {gm1*1e6:6.2f} uS")
        print(f"   M3/M4   gm/ID {op['gm_id_per_v']:6.2f}  Vov {op['vov_v']:+.4f}"
              f" |Vgs| {op['overdrive_bias_v']:.4f}  gm/gds {op['gm_gds']:7.2f}"
              f"  |Vth| {op['vth_v']:.4f}")
        print(f"   MB/M5/M7 gm/ID {on['gm_id_per_v']:5.2f}  Vov {on['vov_v']:+.4f}"
              f"  Vgs {on['overdrive_bias_v']:.4f}  gm/gds {on['gm_gds']:7.2f}")
        print(f"   A1 {a1:6.2f}   A2 {a2:6.2f}   Av {av:8.0f}"
              f" = {20*math.log10(av):.1f} dB")
        print(f"   gm2 {gm2*1e6:6.1f} uS  gm2/gm1 {gm2/gm1:5.2f}   1/gm2"
              f" {1/gm2:6.0f} ohm   GBW {gbw/1e6:5.2f} MHz   p2 {p2/1e6:5.1f} MHz"
              f"   p2/GBW {p2/gbw:4.2f}")
        print(f"   Rz = {RZ:.0f} ohm as drawn -> compensation zero {zero}"
              f"   SR {sr/1e6:.1f} V/us")
        print(f"   ICMR [{icm_lo:.3f}, {icm_hi:.3f}] V, width"
              f" {icm_hi-icm_lo:+.3f} V   Vout [{on['vov_v']:.3f},"
              f" {vdd-op['vov_v']:.3f}] V, swing {vdd-op['vov_v']-on['vov_v']:.3f} V")
        print(f"   input-referred thermal floor {en*1e9:.1f} nV/rtHz"
              f"   Iq {iq*1e6:.0f} uA -> {iq*vdd*1e6:.1f} uW")
    return 0


def main(argv):
    what = argv[1] if len(argv) > 1 else "all"
    rc = 0
    if what in ("validate", "all"):
        rc |= cmd_validate()
        print()
    if what in ("widths", "all"):
        rc |= cmd_widths()
        print()
    if what in ("corners", "all"):
        rc |= cmd_corners()
    if what not in ("validate", "widths", "corners", "all"):
        print(__doc__)
        return 2
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
