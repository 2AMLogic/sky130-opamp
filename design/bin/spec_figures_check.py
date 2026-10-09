#!/usr/bin/env python3
"""Check spec/target-spec.md section 2 measured figures against committed records.

Stdlib only, simulator-free, report-only (never rewrites the spec or records).

  spec_figures_check.py validate [--root DIR]   exit 1 on any disagreement

For each row of manifests/spec-section2-figures.json it recomputes the worst
case (min/max of one CSV column over the record's matrix), compares it to the
authored expected value within the printed-precision tolerance, checks the
argmin/argmax corner matches the binding corner the spec names, and checks the
printed figure text occurs in section 2. It also verifies every record id cited
anywhere in section 2 exists under sim/*/records/.

Coverage (first increment): gain, GBW, phase margin, rise/fall slew, swing,
quiescent power (record 20261001-074923-c317ff9) plus CMRR at both common-mode
points and ICMR width/edges (record 20261009-103006-566b9a5). Not mapped: the
ICMR low/high edge of the narrowest window (needs a row-select key), the
superseded-sizing figures from record 20260916-032327-edc9f22, and ranges.
"""
import argparse
import csv
import re
import sys
from pathlib import Path
import json

REPO = Path(__file__).resolve().parent.parent.parent
MAPPING = "manifests/spec-section2-figures.json"
SPEC = "spec/target-spec.md"
RECORDS_GLOB = "sim/*/records"
ID_RE = re.compile(r"\b\d{8}-\d{6}-[0-9a-f]{7}\b")
OPAMP_RECORDS = "sim/opamp-characterization/records"


def section2(text):
    m = re.search(r"^## 2\. .*$", text, re.M)
    if not m:
        raise ValueError("no '## 2.' heading in spec")
    n = re.search(r"^## ", text[m.end():], re.M)
    return text[m.end(): m.end() + n.start()] if n else text[m.end():]


def record_exists(root, rid):
    for d in Path(root).glob(RECORDS_GLOB):
        if any((d / f"{rid}{ext}").is_file() for ext in (".json", ".md")):
            return True
    return False


def worst(fig, rows):
    for k, v in fig.get("where", {}).items():
        rows = [r for r in rows if r.get(k) == v]
    if not rows:
        raise ValueError("no rows after filter")
    pick = min if fig["reduce"] == "min" else max
    r = pick(rows, key=lambda r: float(r[fig["key"]]))
    return float(r[fig["key"]]) * fig.get("scale", 1.0), r, len(rows)


def check(root):
    root = Path(root)
    errs = []
    try:
        spec2 = section2((root / SPEC).read_text(encoding="utf-8"))
        mapping = json.loads((root / MAPPING).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return [f"cannot load inputs: {e}"]
    for rid in sorted(set(ID_RE.findall(spec2))):
        if not record_exists(root, rid):
            errs.append(f"section 2 cites record {rid} which does not exist under {RECORDS_GLOB}")
    for fig in mapping["figures"]:
        name = fig["row"]
        for s in fig["printed"]:
            if s not in spec2:
                errs.append(f"{name}: printed figure {s!r} not found in section 2")
        if fig["record"] not in spec2:
            errs.append(f"{name}: record {fig['record']} is not cited in section 2")
        path = root / OPAMP_RECORDS / f"{fig['record']}-{fig['csv']}.csv"
        if not path.is_file():
            errs.append(f"{name}: record CSV missing: {path.relative_to(root)}")
            continue
        try:
            with path.open(newline="", encoding="utf-8") as f:
                val, row, n = worst(fig, list(csv.DictReader(f)))
        except (KeyError, ValueError) as e:
            errs.append(f"{name}: cannot recompute from {path.name}: {e!r}")
            continue
        if abs(val - fig["expected"]) > fig["tol"]:
            errs.append(
                f"{name}: recomputed {fig['reduce']} {fig['key']} = {val:.6g} {fig['unit']}, "
                f"spec states {fig['expected']} (tol {fig['tol']})"
            )
        at = fig["at"]
        if row["corner"] != at["corner"] or float(row["temp_c"]) != float(at["temp_c"]):
            errs.append(
                f"{name}: binding corner is {row['corner']}/{row['temp_c']} C, "
                f"mapping says {at['corner']}/{at['temp_c']} C"
            )
    return errs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("mode", choices=["validate"])
    ap.add_argument("--root", default=str(REPO))
    a = ap.parse_args(argv)
    errs = check(a.root)
    for e in errs:
        print(f"FAIL {SPEC} {e}")
    if not errs:
        print(f"OK {SPEC} section 2 figures agree with committed records")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
