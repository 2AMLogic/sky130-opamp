"""Shared gm/ID sweep loading and 0.005 um grid helpers for variants/ scripts.

Single owner (issue #377) of what tail_clamp_sizing (#78), sink_sizing (#79),
sink_bias_margin (#197) and later candidate scripts share: the committed
bare-device sweep path, the sizing grid constants, the linear-in-J gm/ID
interpolation DR-007 quotes, and the grid snap/legality predicates. Scripts
here run as ``python3 sim/opamp-characterization/variants/<script>.py``
(directory on sys.path) or are loaded by file path from the tests, so every
importer puts this directory on sys.path before ``from _gmid import ...``
(the pattern sink_bias_margin.py already uses).

stdlib only; nothing here needs ngspice, volare or a PDK.
"""
from __future__ import annotations

import csv
import os
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
FULL = os.path.join(REPO, "sim", "gm-id-characterization", "records",
                    "20260909-062847-35a9d46-full-sweep.csv")
GRID_UM = 0.005
SWEEP_W_UM = 2.0
I_UNIT_A = 5e-6       # DR-007: 5 uA per mirror unit
GM_ID_PFET = 14.0     # DR-007 gm/ID of M3/M4/M6


def load(device, length, path=FULL):
    rows = defaultdict(list)
    with open(path) as fh:
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
