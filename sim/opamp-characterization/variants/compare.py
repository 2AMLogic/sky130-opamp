#!/usr/bin/env python3
"""Per-metric worst case + binding corner: candidate record vs baseline record(s).

Simulator-free; reads only committed CSVs under ../records/. Every number in
README.md's comparison table is printed by this script (no hand transcription).

A measurement point is identified by the full tuple (corner, temp_c, vdd_v);
supply is read from the CSV, never inferred from the corner name. Rows with a
missing or nonfinite identity field, a duplicate full tuple, or a nonfinite
compared metric are rejected (nonzero exit). Per-point deltas are taken only
where candidate and first baseline share the exact full tuple; other points
are reported as unmatched.

Usage:
    python3 sim/opamp-characterization/variants/compare.py CANDIDATE_ID BASELINE_ID [BASELINE_ID ...]
"""
from __future__ import annotations

import csv
import math
import os
import sys

RECORDS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "records")
SUFFIXES = ("ac", "tran-sr", "dc-swing")
SUPPLY_KEY = "vdd_v"

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
# named process/temperature points the issue requires explicitly; every
# measured supply at each is enumerated
NAMED = [("Open-loop DC gain", "fs", 125.0), ("Fall slew rate", "ss", -40.0),
         ("Output swing (Vpp)", "ss", -40.0), ("Phase margin", "fs", 125.0),
         ("Output swing (Vpp)", "tt", 27.0), ("Fall slew rate", "tt", 27.0)]


class CompareError(ValueError):
    """Input records cannot be compared (malformed, duplicate or nonfinite)."""


def _num(x):
    """Finite float rounded like design/bin/spec_figures_check.py's identity."""
    v = float(x)
    if not math.isfinite(v):
        raise ValueError(f"nonfinite value {x!r}")
    return round(v, 6)


def _fmt(k):
    return f"{k[0].upper()}/{k[1]:g}C/{k[2]:g}V"


def _short(k):
    return f"{k[0]}/{k[1]:g}/{k[2]:g}V"


def columns_for(suffix):
    return [m[2] for m in METRICS if m[1] == suffix]


def index_rows(rows, columns, source="<rows>"):
    """Key rows by (corner, temp_c, vdd_v); collect every validation error.

    Follows the full-tuple convention of design/bin/spec_figures_check.py
    check_matrix: unusable identity, nonfinite/missing value and duplicate
    point are all errors. Raises CompareError listing them.
    """
    errs, seen, out = [], {}, {}
    for i, r in enumerate(rows, 1):
        try:
            corner = (r.get("corner") or "").strip()
            if not corner:
                raise ValueError("empty corner")
            k = (corner, _num(r["temp_c"]), _num(r[SUPPLY_KEY]))
        except (KeyError, TypeError, ValueError) as e:
            errs.append(f"{source}: row {i} has no usable corner/temp_c/{SUPPLY_KEY}: {e!r}")
            continue
        seen.setdefault(k, []).append(i)
        for c in columns:
            try:
                ok = math.isfinite(float(r[c]))
            except (KeyError, TypeError, ValueError):
                ok = False
            if not ok:
                errs.append(f"{source}: point {_fmt(k)} has nonfinite or missing {c}: {r.get(c)!r}")
        out[k] = r
    for k, idx in sorted(seen.items()):
        if len(idx) > 1:
            errs.append(f"{source}: duplicate point {_fmt(k)} in rows {idx}")
    if errs:
        raise CompareError("\n".join(errs))
    return out


def load(rid, suffix, records=None):
    path = os.path.join(records or RECORDS, f"{rid}-{suffix}.csv")
    with open(path, newline="") as fh:
        return index_rows(list(csv.DictReader(fh)), columns_for(suffix), source=path)


def load_all(ids, records=None):
    data, errs = {}, []
    for rid in ids:
        data[rid] = {}
        for s in SUFFIXES:
            try:
                data[rid][s] = load(rid, s, records)
            except CompareError as e:
                errs.append(str(e))
            except OSError as e:
                errs.append(f"cannot read record {rid} {s}: {e}")
    if errs:
        raise CompareError("\n".join(errs))
    return data


def worst_point(rows, col, worst):
    """Binding point; sorted keys make ties independent of CSV row order
    (the caller reports how many other points tie)."""
    return worst(sorted(rows), key=lambda k: float(rows[k][col]))


def tally(cand, base, col, worst):
    common = sorted(k for k in cand if k in base)
    better = worse = same = 0
    for k in common:
        c, b = float(cand[k][col]), float(base[k][col])
        if c == b:
            same += 1
        elif (c > b) == (worst is min):
            better += 1
        else:
            worse += 1
    base_only = sum(1 for k in base if k not in cand)
    cand_only = sum(1 for k in cand if k not in base)
    return better, worse, same, base_only, cand_only


def report(ids, data):
    lines = []
    p = lines.append
    for rid in ids:
        n = {s: len(v) for s, v in data[rid].items()}
        p(f"{rid}: points per analysis {n}")
    p("")
    p("| Metric | " + " | ".join(f"`{rid}` worst @ corner" for rid in ids)
      + " | Points improved / worse (cand vs first baseline) |")
    p("|---|" + "---|" * len(ids) + "---|")
    for label, suf, col, scale, worst, unit in METRICS:
        cells = []
        for rid in ids:
            rows = data[rid][suf]
            if not rows:
                cells.append("no points")
                continue
            key = worst_point(rows, col, worst)
            ties = sum(1 for k in rows if k != key and float(rows[k][col]) == float(rows[key][col]))
            cells.append(f"{float(rows[key][col]) * scale:.4g} {unit} @ {_fmt(key)}"
                         + (f" (+{ties} tied)" if ties else ""))
        better, worse, same, base_only, cand_only = tally(data[ids[0]][suf], data[ids[1]][suf], col, worst)
        extra = ""
        if base_only:
            extra += f", {base_only} unmatched (baseline only)"
        if cand_only:
            extra += f", {cand_only} unmatched (candidate only)"
        p(f"| {label} | " + " | ".join(cells) + f" | {better} better, {worse} worse, {same} equal{extra} |")
    p("")
    p("Named points:")
    for label, corner, temp in NAMED:
        suf, col, scale, unit = next((m[1], m[2], m[3], m[5]) for m in METRICS if m[0] == label)
        t = _num(temp)
        supplies = sorted({k[2] for rid in ids for k in data[rid][suf] if k[0] == corner and k[1] == t})
        if not supplies:
            p(f"  {label} @ {corner.upper()}/{temp:g}C: not measured in any record")
            continue
        for v in supplies:
            k = (corner, t, v)
            vals = [f"{float(data[rid][suf][k][col]) * scale:.4g} {unit}" if k in data[rid][suf]
                    else "missing" for rid in ids]
            p(f"  {label} @ {_fmt(k)}: " + " | ".join(f"{rid}={val}" for rid, val in zip(ids, vals)))
    p("")
    p("Full per-point delta (candidate - first baseline; exact corner/temp/supply matches only):")
    for label, suf, col, scale, worst, unit in METRICS:
        cand, base = data[ids[0]][suf], data[ids[1]][suf]
        parts = []
        for k in sorted(set(cand) | set(base)):
            if k in cand and k in base:
                parts.append(f"{_short(k)}:{(float(cand[k][col]) - float(base[k][col])) * scale:+.3g}")
            elif k in base:
                parts.append(f"{_short(k)}:unmatched(baseline-only)")
            else:
                parts.append(f"{_short(k)}:unmatched(candidate-only)")
        p(f"  {label} [{unit}]: " + " ".join(parts))
    return lines


def main(argv, records=None):
    if len(argv) < 3:
        print(__doc__)
        return 2
    ids = argv[1:]
    try:
        data = load_all(ids, records)
    except CompareError as e:
        print(f"compare.py: cannot compare records:\n{e}", file=sys.stderr)
        return 1
    print("\n".join(report(ids, data)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
