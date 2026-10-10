#!/usr/bin/env python3
"""Per-metric worst case + binding corner: candidate record vs baseline record(s).

Simulator-free; reads only committed CSVs under ../records/. Every number in
README.md's comparison table is printed by this script (no hand transcription).

Usage:
    python3 sim/opamp-characterization/variants/compare.py CANDIDATE_ID BASELINE_ID [BASELINE_ID ...]
"""
from __future__ import annotations

import csv
import os
import sys

RECORDS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "records")

# (label, csv suffix, column, scale, worst = min|max, unit)
METRICS = [
    ("Open-loop DC gain", "ac", "gain_dc_db", 1.0, min, "dB"),
    ("GBW", "ac", "gbw_hz", 1e-6, min, "MHz"),
    ("Phase margin", "ac", "phase_margin_deg", 1.0, min, "deg"),
    ("Rise slew rate", "tran-sr", "sr_rise_v_per_us", 1.0, min, "V/us"),
    ("Fall slew rate", "tran-sr", "sr_fall_v_per_us", 1.0, min, "V/us"),
    ("Output swing (Vpp)", "dc-swing", "vpp_v", 1.0, min, "V"),
    ("Quiescent power", "ac", "pq_w", 1e6, max, "uW"),
]
# named points the issue requires explicitly
NAMED = [("Open-loop DC gain", "fs", 125.0), ("Fall slew rate", "ss", -40.0),
         ("Output swing (Vpp)", "ss", -40.0), ("Phase margin", "fs", 125.0),
         ("Output swing (Vpp)", "tt", 27.0), ("Fall slew rate", "tt", 27.0)]


def load(rid, suffix):
    path = os.path.join(RECORDS, f"{rid}-{suffix}.csv")
    with open(path) as fh:
        return {(r["corner"], float(r["temp_c"])): r for r in csv.DictReader(fh)}


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    ids = argv[1:]
    data = {rid: {s: load(rid, s) for s in ("ac", "tran-sr", "dc-swing")} for rid in ids}
    for rid in ids:
        n = {s: len(v) for s, v in data[rid].items()}
        print(f"{rid}: points per analysis {n}")
    print()
    print("| Metric | " + " | ".join(f"`{rid}` worst @ corner" for rid in ids) + " | Points improved / worse (cand vs first baseline) |")
    print("|---|" + "---|" * len(ids) + "---|")
    for label, suf, col, scale, worst, unit in METRICS:
        cells = []
        for rid in ids:
            rows = data[rid][suf]
            key = worst(rows, key=lambda k: float(rows[k][col]))
            cells.append(f"{float(rows[key][col]) * scale:.4g} {unit} @ {key[0].upper()}/{key[1]:g}C")
        cand, base = data[ids[0]][suf], data[ids[1]][suf]
        common = [k for k in cand if k in base]
        better = sum(1 for k in common if (float(cand[k][col]) > float(base[k][col])) == (worst is min)
                     and float(cand[k][col]) != float(base[k][col]))
        same = sum(1 for k in common if float(cand[k][col]) == float(base[k][col]))
        absent = len(base) - len(common)
        print(f"| {label} | " + " | ".join(cells) + f" | {better} better, {len(common) - better - same} worse, "
              f"{same} equal" + (f", {absent} absent from candidate (errored unit)" if absent else "") + " |")
    print()
    print("Named points:")
    for label, corner, temp in NAMED:
        suf, col, scale, unit = next((m[1], m[2], m[3], m[5]) for m in METRICS if m[0] == label)
        vals = [f"{float(data[rid][suf][(corner, temp)][col]) * scale:.4g}" if (corner, temp) in data[rid][suf]
                else "ABSENT(errored unit)" for rid in ids]
        print(f"  {label} @ {corner.upper()}/{temp:g}C: " + " | ".join(f"{rid}={v} {unit}" for rid, v in zip(ids, vals)))
    print()
    print("Full per-point delta (candidate - first baseline):")
    for label, suf, col, scale, worst, unit in METRICS:
        cand, base = data[ids[0]][suf], data[ids[1]][suf]
        parts = [f"{k[0]}/{k[1]:g}:{(float(cand[k][col]) - float(base[k][col])) * scale:+.3g}" if k in cand
                 else f"{k[0]}/{k[1]:g}:ABSENT" for k in sorted(base)]
        print(f"  {label} [{unit}]: " + " ".join(parts))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
