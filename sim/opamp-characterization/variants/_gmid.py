"""Shared gm/ID sizing and MOS netlist helpers for variants/ scripts.

Candidate scripts use the committed bare-device sweep, DR-007's linear-in-J
interpolation and the sizing grid to generate variants of the canonical netlist.
Reading and emitting their MOS geometry needs only the standard library.
"""
from __future__ import annotations

import csv
import math
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import NamedTuple

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(REPO, "lib"))
from spice_text import join_continuations, strip_eol_comments

CANON = Path(REPO) / "design" / "netlist" / "opamp_core.spice"
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


def canonical_body() -> str:
    """Return the verbatim pin and device lines of the canonical netlist."""
    text = CANON.read_text()
    return text[text.index("*.iopin vdd"):text.index("**.ends")]


def card(name, d, g, s_, b, kind, w, l, mult=1):
    """Emit an xschem-style MOS card with the canonical diffusion geometry."""
    r = 0.29 / w
    return (f"{name} {d} {g} {s_} {b} sky130_fd_pr__{kind}_01v8 L={l:g} W={w:.3f} nf=1 "
            f"ad={w * 0.29:.6g} as={w * 0.29:.6g} pd={2 * (w + 0.29):.6g} ps={2 * (w + 0.29):.6g} nrd={r!r}\n"
            f"+ nrs={r!r} sa=0 sb=0 sd=0 mult={mult} m={mult}\n")


class MosCard(NamedTuple):
    nodes_and_model: list[str]
    width: float
    length: float
    m: int
    nf: int | None


def _whole_number(value: str) -> int:
    """Parse an integer-valued spelling (``2``, ``2.0``); reject truncating ones."""
    number = float(value)
    if not number.is_integer():
        raise ValueError(f"non-integer value: {value}")
    return int(number)


def mos_cards(text: str) -> dict[str, MosCard]:
    """Read connectivity and drawn geometry of the flat netlist's XM devices."""
    cards = {}
    for line in join_continuations(strip_eol_comments(text)):
        if not line.startswith("XM"):
            continue
        tokens = line.split()
        params = dict(t.split("=", 1) for t in tokens[6:] if "=" in t)
        try:
            card_ = MosCard(
                tokens[1:6], float(params["W"]), float(params["L"]),
                _whole_number(params["m"]),
                _whole_number(params["nf"]) if "nf" in params else None)
            if not all(math.isfinite(v) and v > 0 for v in (card_.width, card_.length)):
                raise ValueError("W and L must be finite and positive")
            if card_.m < 1 or (card_.nf is not None and card_.nf < 1):
                raise ValueError("m and nf must be positive")
        except (KeyError, ValueError, OverflowError) as exc:
            raise ValueError(f"cannot parse MOS card: {line[:60]}") from exc
        cards[tokens[0]] = card_
    return cards


def gate_area(path: Path) -> tuple[dict[str, float], float]:
    """Return per-device and total drawn MOS gate area in square micrometres."""
    areas = {name: device.width * device.length * device.m
             for name, device in mos_cards(path.read_text()).items()}
    return areas, sum(areas.values(), 0.0)
