#!/usr/bin/env python3
"""Emit layout/opamp_out/cell.json (issue #208).

cell.json is the committed source of truth; this script only documents how its
coordinate lists (front-end masks, the klt-draw PMOS array, the routing legs)
were derived from the unit pitch, so a reviewer can regenerate and diff it:

    python3 layout/opamp_out/make-cell-json.py > /tmp/cell.json
    diff /tmp/cell.json layout/opamp_out/cell.json

No device parameter is written here: the LVS reference comes from
design/netlist/opamp_core.spice (layout/bin/stage_reference.py). The drawn
unit sizes (4.635 x 0.3 and 7.82 x 1.2 um) and the unit count (10) are the
netlist's W, L and m.
"""
import json

N = 10                      # units per device (XM6 and XM7: m=10)
R = lambda v: round(v, 3)

# ---- XM7: klt gen mos_array 1 x 10 nfet, W=7.82 L=1.2 (pitch 2.44) --------
NW, NL, NP = 7.82, 1.2, 2.44
n_right = (N - 1) * NP + 2.04            # last diffusion right edge
nx = lambda k: R(0.21 + NP * k)          # S pad centre of column k
nd = lambda k: R(1.83 + NP * k)          # D pad centre
ng = lambda k: R(1.02 + NP * k)          # gate pad centre
NG_Y = 8.43

# ---- XM6: klt draw, pitch 1.54, W=4.635 L=0.3 -----------------------------
PW, PL, PP = 4.635, 0.3, 1.54
PX = 33.0                                # block origin in the cell frame
p_right = (N - 1) * PP + 1.14
PH = PW
pS = lambda k: R(0.21 + PP * k)
pD = lambda k: R(0.93 + PP * k)
pG = lambda k: R(0.57 + PP * k)
PG_Y = R(PH + 0.61)                      # gate port y (mp34: 1.545 + 0.61)
PY = 2.32                                # S/D port y (on the 0.001 grid)


def rect(layer, x0, y0, x1, y1):
    return {"layer": list(layer), "rect_um": [R(x0), R(y0), R(x1), R(y1)]}


# ---------------------------------------------------------------- fe_masks
fe = [rect((93, 44), -0.125, -0.125, n_right + 0.125, NW + 0.125)]
ro = n_right + 1.07                      # ring outer right
top_o = NW + 1.89                        # ring outer top (9.71 for W=7.82)
for r in [(-1.195, -1.195, ro + 0.125, -0.525), (-1.195, top_o - 0.42 - 0.125 , ro + 0.125, top_o + 0.125),
          (-1.195, -0.525, -0.525, top_o - 0.545), (ro - 0.42 - 0.125, -0.525, ro + 0.125, top_o - 0.545)]:
    fe.append(rect((94, 20), *r))
for k in range(N):
    fe.append(rect((95, 20), ng(k) - 0.185, NG_Y - 0.185, ng(k) + 0.185, NG_Y + 0.185))
for k in range(N):
    fe.append(rect((66, 20), 0.42 + NP * k, -0.15, 1.62 + NP * k, 0.0))
for k in range(N):
    fe.append(rect((66, 20), 0.42 + NP * k, NW, 1.62 + NP * k, NW + 0.15))


# ----------------------------------------------------------------- mp6 draw
def mp6():
    s = []
    ports = []
    nlic = 13
    pitch = 0.34
    y0 = 0.195   # centred to within 5 nm, on the 0.005 um grid
    for k in range(N):
        x = PP * k
        s.append(rect((65, 20), x, 0, x + 1.14, PH))
        s.append(rect((67, 20), x, 0, x + 0.42, PH))
        s.append(rect((67, 20), x + 0.72, 0, x + 1.14, PH))
        for j in range(nlic):
            yy = y0 + j * pitch
            s.append(rect((66, 44), x + 0.125, yy, x + 0.295, yy + 0.17))
            s.append(rect((66, 44), x + 0.845, yy, x + 1.015, yy + 0.17))
    for k in range(N):
        x = PP * k
        s.append(rect((66, 20), x + 0.42, -0.15, x + 0.72, PH + 0.15))
        s.append(rect((66, 20), x + 0.36, PH + 0.15, x + 0.78, PH + 0.82))
        s.append(rect((66, 44), x + 0.485, PH + 0.525, x + 0.655, PH + 0.695))
        s.append(rect((67, 20), x + 0.36, PH + 0.4, x + 0.78, PH + 0.82))
        s.append(rect((95, 20), x + 0.385, PH + 0.425, x + 0.755, PH + 0.795))
    # n-tap ring (0.5 um padding, 0.42 um thick), n-well 0.2 um beyond
    xl, xr, yb, yt = -0.92, p_right + 0.92, -0.92, PH + 1.74
    s.insert(0, rect((64, 20), xl - 0.2, yb - 0.2, xr + 0.2, yt + 0.2))
    ring = [(xl, yb, xr, yb + 0.42), (xl, yt - 0.42, xr, yt),
            (xl, yb + 0.42, xl + 0.42, yt - 0.42), (xr - 0.42, yb + 0.42, xr, yt - 0.42)]
    for r in ring:
        s.append(rect((65, 44), *r))
        s.append(rect((67, 20), *r))
    for xx in [1.155 + 0.68 * i for i in range(int((p_right - 1.0) / 0.68) + 1)]:
        s.append(rect((66, 44), xx, yt - 0.295, xx + 0.17, yt - 0.125))
        s.append(rect((66, 44), xx, yb + 0.125, xx + 0.17, yb + 0.295))
    ymid = (yb + yt) / 2
    for yy in [yb + 0.9 + 0.68 * i for i in range(int((yt - yb - 1.6) / 0.68) + 1)]:
        s.append(rect((66, 44), xl + 0.125, yy, xl + 0.295, yy + 0.17))
        s.append(rect((66, 44), xr - 0.295, yy, xr - 0.125, yy + 0.17))
    # implants: psdm over the p-diffusions, nsdm ring over the n-tap ring
    s.append(rect((94, 20), -0.125, -0.125, p_right + 0.125, PH + 0.125))
    for r in [(xl - 0.125, yb - 0.125, xr + 0.125, yb + 0.545), (xl - 0.125, yt - 0.545, xr + 0.125, yt + 0.125),
              (xl - 0.125, yb + 0.545, xl + 0.545, yt - 0.545), (xr - 0.545, yb + 0.545, xr + 0.125, yt - 0.545)]:
        s.append(rect((93, 44), *r))
    lay = {"layer": 67, "datatype": 20}
    def port(name, x, y, w, d):
        ports.append({"name": name, "x_um": R(x), "y_um": R(y), "layer": lay, "width_um": R(w), "direction_deg": d})
    for k in range(N):
        port(f"U{k}_S", pS(k), PY, PH, 180)
        port(f"U{k}_D", pD(k), PY, PH, 0)
        port(f"U{k}_G", pG(k), PG_Y, 0.42, 90)
    xm = p_right / 2
    ym = round(ymid, 2)
    port("TAP_N", xm, yt - 0.21, 0.42, 90)
    port("TAP_S", xm, yb + 0.21, 0.42, 270)
    port("TAP_E", xr - 0.21, ym, 0.42, 0)
    port("TAP_W", xl + 0.21, ym, 0.42, 180)
    return {"id": "mp6", "draw": {"cell_name": "out_pmos_units", "shapes": s, "ports": ports}}, (xm, yb + 0.21, xr - 0.21, ym)


mp6_block, (TAPS_X, TAPS_Y, TAPE_X, TAPE_Y) = mp6()


def stub(pid, cell, layer, west):
    a, b = (0.0, 1.5) if west else (1.5, 0.0)   # west pin: PAD at x=0
    lay = {"layer": layer, "datatype": 20}
    pa = {"name": "PAD", "x_um": 0.0 if west else 1.5, "y_um": 0.21, "layer": lay, "width_um": 0.42,
          "direction_deg": 180 if west else 0}
    pc = {"name": "CONN", "x_um": 1.5 if west else 0.0, "y_um": 0.21, "layer": lay, "width_um": 0.42,
          "direction_deg": 0 if west else 180}
    return {"id": pid, "draw": {"cell_name": cell, "shapes": [rect((layer, 20), 0, 0, 1.5, 0.42)],
                                "ports": [pa, pc]}}


blocks = [
    {"id": "mn", "generator": "mos_array", "cell_name": "out_nmos_units",
     "params": {"w_um": NW, "l_um": NL, "rows": 1, "cols": N, "dummy": 0, "gate_contact": True,
                "add_guard_ring": True, "flavor": "nfet"}},
    {"id": "fe_masks", "draw": {"cell_name": "out_fe_masks", "shapes": fe, "ports": []}},
    mp6_block,
    stub("pin_ibias", "stub_metal2", 68, True),
    stub("pin_vss", "stub_metal2", 68, True),
    stub("pin_out", "stub_metal3", 69, False),
    stub("pin_d2", "stub_metal2", 68, False),
    stub("pin_vdd", "stub_metal2", 68, False),
]

# pin stub origins: CONN centre sits on the routed track
PIN_X_E = R(PX + p_right + 3.0)
origins = {
    "mn": {"x": 0.0, "y": 0.0}, "fe_masks": {"x": 0.0, "y": 0.0}, "mp6": {"x": PX, "y": 0.0},
    "pin_ibias": {"x": -6.0, "y": R(NG_Y + 0.57 - 0.21)},
    "pin_vss": {"x": -6.0, "y": 4.11},
    "pin_out": {"x": PIN_X_E, "y": -2.41},
    "pin_d2": {"x": PIN_X_E, "y": R(PG_Y - 0.21)},
    "pin_vdd": {"x": PIN_X_E, "y": R(TAPE_Y - 0.21)},
}

P = lambda b, p: {"block": b, "port": p}
def leg(a, b, *wp):
    d = {"from_pin": a, "to_pin": b}
    if wp:
        d["waypoints_um"] = [[R(x), R(y)] for x, y in wp]
    return d

# column order west->east of the nmos array = ports sorted by x (U8,U6,...): look up by x
NORDER = [8, 6, 4, 2, 0, 1, 3, 5, 7, 9]   # gen unit index at column k
NU = lambda k, t: P("mn", f"U{NORDER[k]}_{t}")
GBUS_N = NG_Y + 0.57
YV, YO = -1.6, -2.2

ibias_legs = [leg(P("pin_ibias", "CONN"), NU(0, "G"), (ng(0), GBUS_N))]
for k in range(N - 1):
    ibias_legs.append(leg(NU(k, "G"), NU(k + 1, "G"), (ng(k), GBUS_N), (ng(k + 1), GBUS_N)))
vss_n = [leg(P("pin_vss", "CONN"), P("mn", "TAP_W"))]
tapx = 12.0
for k in range(N):
    vss_n.append(leg(NU(k, "S"), P("mn", "TAP_W"), (nx(k), YV), (-0.86, YV)))
out_legs = [leg(P("pin_out", "CONN"), P("mp6", f"U{N-1}_D"), (PX + pD(N - 1), YO))]
for k in range(N - 1):
    out_legs.append(leg(P("mp6", f"U{k+1}_D"), P("mp6", f"U{k}_D"), (PX + pD(k + 1), YO), (PX + pD(k), YO)))
out_legs.append(leg(P("mp6", "U0_D"), NU(N - 1, "D"), (PX + pD(0), YO), (nd(N - 1), YO)))
for k in range(N - 1, 0, -1):
    out_legs.append(leg(NU(k, "D"), NU(k - 1, "D"), (nd(k), YO), (nd(k - 1), YO)))
d2_legs = [leg(P("pin_d2", "CONN"), P("mp6", f"U{N-1}_G"))]
for k in range(N - 1, 0, -1):
    d2_legs.append(leg(P("mp6", f"U{k}_G"), P("mp6", f"U{k-1}_G")))
vdd_legs = [leg(P("pin_vdd", "CONN"), P("mp6", "TAP_E"))]
for k in range(N):
    vdd_legs.append(leg(P("mp6", f"U{k}_S"), P("mp6", "TAP_E"), (PX + pS(k), YV), (PX + TAPE_X, YV)))

conn = [
    {"net": "ibias", "layer_role": "metal2", "pins": [NU(k, "G") for k in range(N)] + [P("pin_ibias", "CONN")], "legs": ibias_legs},
    {"net": "out", "layer_role": "metal3", "pins": [NU(k, "D") for k in range(N)] + [P("mp6", f"U{k}_D") for k in range(N)] + [P("pin_out", "CONN")], "legs": out_legs},
    {"net": "d2", "layer_role": "metal2", "pins": [P("mp6", f"U{k}_G") for k in range(N)] + [P("pin_d2", "CONN")], "legs": d2_legs},
    {"net": "vss", "layer_role": "metal2", "pins": [NU(k, "S") for k in range(N)] + [P("mn", "TAP_W"), P("pin_vss", "CONN")], "legs": vss_n},
    {"net": "vdd", "layer_role": "metal2", "pins": [P("mp6", f"U{k}_S") for k in range(N)] + [P("mp6", "TAP_E"), P("pin_vdd", "CONN")], "legs": vdd_legs},
]

cell = {
    "cell": "opamp_out",
    "_comment": [
        "Cell descriptor for layout/bin/compose-cell.py (issue #208). See layout/opamp_out/README.md.",
        "SCOPE: the canonical output stage of design/netlist/opamp_core.spice:",
        "  XM6 pfet_01v8 W=4.635 L=0.3 m=10 (out d2 vdd vdd)",
        "  XM7 nfet_01v8 W=7.820 L=1.2 m=10 (out ibias vss vss)",
        "Ten drawn units each. Not the full op-amp; no replacement output topology is adopted (DR-012).",
        "Coordinates derive from layout/opamp_out/make-cell-json.py; this file is the source of truth.",
    ],
    "pdk": {"variant": "sky130A", "deck": "sky130"},
    "blocks": blocks,
    "placement": {"strategy": "explicit", "order": [b["id"] for b in blocks], "origins_um": origins},
    "routing": {"layer_role": "metal", "width_um": 0.3},
    "connectivity": conn,
    "pins": [{"net": n, "block": b, "port": "PAD"} for n, b in
             [("ibias", "pin_ibias"), ("vss", "pin_vss"), ("out", "pin_out"), ("d2", "pin_d2"), ("vdd", "pin_vdd")]],
    "lvs": {"reference": "design/netlist/opamp_core.spice", "subckt": "opamp_out",
            "devices": ["XM6", "XM7"], "pins": ["out", "d2", "ibias", "vdd", "vss"],
            "options": {"combine_devices": True}},
    "expect": {"extracted_devices": 2 * N,
               "magic_types": ["nmos", "pmos", "ndiff", "pdiff", "psubdiff", "nsubdiff", "nwell", "poly"]},
}
print(json.dumps(cell, indent=2))
