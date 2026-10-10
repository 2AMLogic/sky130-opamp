#!/usr/bin/env python3
"""Simulator-free manufacturing-grid check for design/netlist/opamp_core.spice (issue #131).

Every drawn dimension (``L``, ``W`` of an instance) must be an exact
multiple of the 0.005 um manufacturing grid, or the layout generators cannot
draw it (klt ``*.ongrid.1`` violations; see layout/passive_probes/).

Device classes are checked independently so each owner can opt in:

* ``passive``: ``res_*`` / ``cap_*`` models (XRz, XCc). Enforced by default;
  this is the mechanism issue #131 adds.
* ``mos``: ``nfet_*`` / ``pfet_*`` models. NOT enforced by default: the MOS
  widths (4.634, 7.819) are off-grid today and are owned by #50/#120. #120
  should switch this on (``--classes passive,mos``) rather than adding a
  second mechanism.

Usage:
    python3 design/bin/grid_check.py [--classes passive,mos] [netlist]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

GRID_UM = 0.005
DEFAULT_NETLIST = Path(__file__).resolve().parent.parent / "netlist" / "opamp_core.spice"
CLASS_RE = {
    "passive": re.compile(r"sky130_fd_pr__(res|cap)_\w+"),
    "mos": re.compile(r"sky130_fd_pr__[np]fet_\w+"),
}
DIMS = ("l", "w")


def on_grid(value: float, grid: float = GRID_UM) -> bool:
    n = value / grid
    return abs(n - round(n)) <= 1e-6


def logical_lines(text: str):
    cur = ""
    for raw in text.splitlines():
        if raw.startswith("+"):
            cur += " " + raw[1:].strip()
            continue
        if cur:
            yield cur
        cur = raw.strip()
    if cur:
        yield cur


def violations(text: str, classes=("passive",)) -> list[str]:
    out = []
    for line in logical_lines(text):
        if not line or line[0] in "*.":
            continue
        tokens = line.split()
        name = tokens[0]
        model = next((t for t in tokens[1:] if t.startswith("sky130_fd_pr__")), None)
        if model is None:
            continue
        kind = next((k for k in classes if CLASS_RE[k].fullmatch(model)), None)
        if kind is None:
            continue
        for tok in tokens:
            key, _, val = tok.partition("=")
            if key.lower() in DIMS and val:
                try:
                    num = float(val)
                except ValueError:
                    out.append(f"{name}: {key}={val} is not a plain number")
                    continue
                if not on_grid(num):
                    out.append(f"{name} ({model}): {key}={val} um is not a multiple of {GRID_UM} um")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("netlist", nargs="?", default=str(DEFAULT_NETLIST))
    ap.add_argument("--classes", default="passive")
    args = ap.parse_args(argv)
    classes = tuple(c for c in args.classes.split(",") if c)
    bad = [c for c in classes if c not in CLASS_RE]
    if bad:
        print(f"unknown class {bad}", file=sys.stderr)
        return 2
    found = violations(Path(args.netlist).read_text(), classes)
    for v in found:
        print(f"OFF-GRID: {v}", file=sys.stderr)
    if found:
        return 1
    print(f"OK: every {'/'.join(classes)} L/W in {args.netlist} is on the {GRID_UM} um grid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
