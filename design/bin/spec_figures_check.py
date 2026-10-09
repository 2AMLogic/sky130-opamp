#!/usr/bin/env python3
"""Check spec/target-spec.md section 2 measured figures against committed records.

Stdlib only, simulator-free, report-only (never rewrites the spec or records).

  spec_figures_check.py validate [--root DIR]   exit 1 on any disagreement

For each row of manifests/spec-section2-figures.json it recomputes the worst
case (min/max of one CSV column over the record's matrix), compares it to the
authored expected value within the printed-precision tolerance, checks the
argmin/argmax corner matches the mapping's `at`, and checks the spec text.

Spec-side checks are scoped to the one section 2 table row whose first cell
starts with the mapping's `row_match` (default: `row`):
  - every `printed` string must occur in that row exactly as many times as it
    is listed (list a string twice if the row prints it twice);
  - every copy of the figure's number in that row must lie inside a matched
    `printed` occurrence, so no stray or hand-edited copy goes unaccounted;
  - the binding corner `at`, rendered as the spec prints it (e.g.
    "SS / \u221240 \u00b0C"), must appear in at least one `printed` string;
  - the record id must be cited in that row;
  - `expected`/`tol` must agree with the number and precision printed in
    `printed[0]`, so the mapping cannot drift from its own text.
Copies of a figure outside the table rows (e.g. a section 2 summary paragraph)
are not covered. It also verifies every record id cited anywhere in section 2
exists under sim/*/records/.

Matrix completeness: every figure names a `matrix` in the mapping's top-level
`matrices` table. A matrix is authored explicitly (never inferred from the CSV)
as either `points` (exact list of {corner, temp_c, <supply_key>}) or `axes`
(`corner` list, `temp_c` list) plus `supply` and optional `exclude`. `supply`
is either {"mode": "paired_with_corner", "by_corner": {corner: volts}}, the
repo's methodology (supply moves with the process corner, not an independent
sweep), or {"mode": "cartesian", "values": [...]}. The expected tuple set is
compared, after the figure's `where` filter, with the unique
(corner, temp_c, supply) tuples of the CSV: missing, duplicate and unexpected
points and nonfinite values of the figure's key are all errors, with dataset
and point diagnostics. Figures that cite the same matrix share one validation.

Campaign figures (offset Monte Carlo, `campaign_figures` in the mapping):
statistics that live in a committed campaign summary JSON rather than a PVT
CSV (sim/offset-capability, issue #85). Each entry names the summary
(`campaign_json`), the per-corner `key` (e.g. sigma_v), a `reduce` (min/max)
over the authored `corners`, a `scale` to the printed unit, and the same
`expected`/`tol`/`at`/`printed`/`row_match` text rules as above. `at` is
the binding corner and, since the campaign ran at one temperature, its
`temp_c` must equal the summary's `temp_c`. Also checked: the summary's
corner set equals the authored `corners`, every corner has n_ok ==
n_requested == `n_per_corner` and n_failed == 0, and the cited
`record_md` file exists and is cited in the row.

Coverage (first increment): gain, GBW, phase margin, rise/fall slew, swing,
quiescent power (record 20261001-074923-c317ff9) plus CMRR at both common-mode
points and ICMR width/edges (record 20261009-103006-566b9a5). Not mapped: the
ICMR low/high edge of the narrowest window (needs a row-select key), the
superseded-sizing figures from record 20260916-032327-edc9f22, and ranges.
"""
import argparse
import csv
import json
import math
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
MAPPING = "manifests/spec-section2-figures.json"
SPEC = "spec/target-spec.md"
RECORDS_GLOB = "sim/*/records"
ID_RE = re.compile(r"\b\d{8}-\d{6}-[0-9a-f]{7}\b")
NUM_RE = re.compile(r"\d+(?:\.\d+)?")
OPAMP_RECORDS = "sim/opamp-characterization/records"


def section2(text):
    m = re.search(r"^## 2\. .*$", text, re.M)
    if not m:
        raise ValueError("no '## 2.' heading in spec")
    n = re.search(r"^## ", text[m.end():], re.M)
    return text[m.end(): m.end() + n.start()] if n else text[m.end():]


def table_rows(spec2, prefix):
    """Section 2 table rows whose first cell starts with `prefix`."""
    out = []
    for line in spec2.splitlines():
        cells = line.split("|")
        if line.startswith("|") and len(cells) > 2 and cells[1].strip().startswith(prefix):
            out.append(line)
    return out


def corner_text(at):
    t = float(at["temp_c"])
    t = f"{t:g}".replace("-", "\u2212")
    return f"{at['corner'].upper()} / {t} \u00b0C"


def occurrences(hay, needle):
    i, out = 0, []
    while needle and (j := hay.find(needle, i)) >= 0:
        out.append((j, j + len(needle)))
        i = j + len(needle)
    return out


def check_text(name, fig, row):
    errs = []
    printed = fig["printed"]
    if not printed:
        return [f"{name}: mapping lists no printed text"]
    m = NUM_RE.search(printed[0])
    if not m:
        return [f"{name}: printed[0] {printed[0]!r} contains no number"]
    num = m.group(0)
    if not math.isclose(float(num), fig["expected"], rel_tol=0, abs_tol=1e-12):
        errs.append(f"{name}: mapping expected {fig['expected']} disagrees with printed {num!r}")
    dec = len(num.split(".")[1]) if "." in num else 0
    if not math.isclose(fig["tol"], 0.5 * 10 ** -dec, rel_tol=1e-9):
        errs.append(f"{name}: mapping tol {fig['tol']} is not half the printed precision of {num!r}")
    spans = []
    for s in sorted(set(printed)):
        occ = occurrences(row, s)
        want = printed.count(s)
        if len(occ) != want:
            errs.append(f"{name}: printed {s!r} occurs {len(occ)}x in its section 2 row, mapping lists {want}x")
        spans += occ
    for n in re.finditer(rf"(?<![\d.]){re.escape(num)}(?!\d)", row):
        if not any(a <= n.start() and n.end() <= b for a, b in spans):
            ctx = row[max(0, n.start() - 30): n.end() + 30]
            errs.append(f"{name}: copy of {num} in its section 2 row not covered by any printed string: ...{ctx}...")
    ct = corner_text(fig["at"])
    if not any(ct in s for s in printed):
        errs.append(f"{name}: binding corner {ct!r} does not appear in any printed string")
    return errs


def record_exists(root, rid):
    for d in Path(root).glob(RECORDS_GLOB):
        if any((d / f"{rid}{ext}").is_file() for ext in (".json", ".md")):
            return True
    return False


def filtered(fig, rows):
    for k, v in fig.get("where", {}).items():
        rows = [r for r in rows if r.get(k) == v]
    return rows


def _num(x):
    return round(float(x), 6)


def _fmt(t):
    return f"{t[0]}/{t[1]:g} C/{t[2]:g} V"


def expected_points(m):
    """Authored expected set of (corner, temp_c, supply) tuples for a matrix."""
    sk = m.get("supply_key", "vdd_v")
    if "points" in m:
        if "axes" in m:
            raise ValueError("matrix gives both points and axes")
        pts = [(p["corner"], _num(p["temp_c"]), _num(p[sk])) for p in m["points"]]
        if len(set(pts)) != len(pts):
            raise ValueError("matrix points contain duplicates")
        return set(pts)
    axes, sup = m["axes"], m["supply"]
    if sup["mode"] == "paired_with_corner":
        by = sup["by_corner"]
        if set(by) != set(axes["corner"]):
            raise ValueError("supply.by_corner keys must equal axes.corner")
        pts = [(c, _num(t), _num(by[c])) for c in axes["corner"] for t in axes["temp_c"]]
    elif sup["mode"] == "cartesian":
        pts = [(c, _num(t), _num(v)) for c in axes["corner"] for t in axes["temp_c"] for v in sup["values"]]
    else:
        raise ValueError(f"unknown supply mode {sup['mode']!r}")
    if len(set(pts)) != len(pts):
        raise ValueError("matrix axes contain repeated values")
    pts = set(pts)
    for ex in m.get("exclude", []):
        hit = {p for p in pts if p[0] == ex["corner"] and p[1] == _num(ex["temp_c"])
               and (sk not in ex or p[2] == _num(ex[sk]))}
        if not hit:
            raise ValueError(f"exclusion {ex} matches no expected point")
        pts -= hit
    return pts


def check_matrix(name, m, rows, keys):
    """Errors for one matrix against its (already filtered) rows."""
    sk = m.get("supply_key", "vdd_v")
    try:
        want = expected_points(m)
    except (KeyError, TypeError, ValueError) as e:
        return [f"matrix {name}: bad matrix definition: {e!r}"]
    errs, seen = [], {}
    for i, r in enumerate(rows, 1):
        try:
            t = (r["corner"], _num(r["temp_c"]), _num(r[sk]))
        except (KeyError, TypeError, ValueError) as e:
            errs.append(f"matrix {name}: row {i} has no usable corner/temp_c/{sk}: {e!r}")
            continue
        seen.setdefault(t, []).append(i)
        for k in keys:
            try:
                ok = math.isfinite(float(r[k]))
            except (KeyError, TypeError, ValueError):
                ok = False
            if not ok:
                errs.append(f"matrix {name}: point {_fmt(t)} has nonfinite or missing {k}: {r.get(k)!r}")
    for t in sorted(want - set(seen)):
        errs.append(f"matrix {name}: missing expected point {_fmt(t)}")
    for t in sorted(set(seen) - want):
        errs.append(f"matrix {name}: unexpected point {_fmt(t)}")
    for t, idx in sorted(seen.items()):
        if len(idx) > 1:
            errs.append(f"matrix {name}: duplicate point {_fmt(t)} in rows {idx}")
    return errs


def worst(fig, rows):
    rows = filtered(fig, rows)
    if not rows:
        raise ValueError("no rows after filter")
    pick = min if fig["reduce"] == "min" else max
    r = pick(rows, key=lambda r: float(r[fig["key"]]))
    return float(r[fig["key"]]) * fig.get("scale", 1.0), r, len(rows)


def check_figure_matrix(name, fig, matrices, allrows, figures, checked):
    mname = fig.get("matrix")
    m = matrices.get(mname)
    if m is None:
        return [f"{name}: no authored matrix {mname!r} in mapping `matrices`"]
    errs = []
    for k in ("record", "csv"):
        if m.get(k) != fig[k]:
            errs.append(f"{name}: matrix {mname} {k} {m.get(k)!r} != figure {k} {fig[k]!r}")
    if m.get("where", {}) != fig.get("where", {}):
        errs.append(f"{name}: matrix {mname} where {m.get('where', {})} != figure where {fig.get('where', {})}")
    if mname in checked:
        return errs
    checked.add(mname)
    keys = sorted({f["key"] for f in figures if f.get("matrix") == mname})
    ds = f"{m.get('record')}-{m.get('csv')}" + (f" where {m['where']}" if m.get("where") else "")
    return errs + [e.replace(f"matrix {mname}:", f"matrix {mname} [{ds}]:", 1)
                   for e in check_matrix(mname, m, filtered(m, allrows), keys)]


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
    matrices = mapping.get("matrices", {})
    checked = set()
    for fig in mapping["figures"]:
        name = fig["row"]
        rows = table_rows(spec2, fig.get("row_match", name))
        if len(rows) != 1:
            errs.append(f"{name}: expected exactly one section 2 table row starting "
                        f"{fig.get('row_match', name)!r}, found {len(rows)}")
        else:
            errs += check_text(name, fig, rows[0])
            if fig["record"] not in rows[0]:
                errs.append(f"{name}: record {fig['record']} is not cited in its section 2 row")
        path = root / OPAMP_RECORDS / f"{fig['record']}-{fig['csv']}.csv"
        if not path.is_file():
            errs.append(f"{name}: record CSV missing: {path.relative_to(root)}")
            continue
        try:
            with path.open(newline="", encoding="utf-8") as f:
                allrows = list(csv.DictReader(f))
            errs += check_figure_matrix(name, fig, matrices, allrows, mapping["figures"], checked)
            val, row, n = worst(fig, allrows)
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
    errs += check_campaign_figures(root, spec2, mapping)
    return errs


def check_campaign_figures(root, spec2, mapping):
    errs = []
    for fig in mapping.get("campaign_figures", []):
        name = fig["row"]
        rows = table_rows(spec2, fig.get("row_match", name))
        if len(rows) != 1:
            errs.append(f"{name}: expected exactly one section 2 table row starting "
                        f"{fig.get('row_match', name)!r}, found {len(rows)}")
        else:
            errs += check_text(name, fig, rows[0])
            for cite in (fig["record_md"], fig["campaign_json"]):
                if Path(cite).name not in rows[0]:
                    errs.append(f"{name}: {Path(cite).name} is not cited in its section 2 row")
        for cite in (fig["record_md"], fig["campaign_json"]):
            if not (root / cite).is_file():
                errs.append(f"{name}: cited campaign file missing: {cite}")
        try:
            data = json.loads((root / fig["campaign_json"]).read_text(encoding="utf-8"))
            cs = data["corners"]
            if set(cs) != set(fig["corners"]):
                errs.append(f"{name}: campaign corners {sorted(cs)} != authored {sorted(fig['corners'])}")
            for c in fig["corners"]:
                st = cs[c]
                n = fig["n_per_corner"]
                if not (st["n_requested"] == st["n_ok"] == n and st["n_failed"] == 0):
                    errs.append(f"{name}: corner {c} has n_ok={st['n_ok']} n_failed={st['n_failed']} "
                                f"of {st['n_requested']}, expected {n} ok / 0 failed")
            if float(data["temp_c"]) != float(fig["at"]["temp_c"]):
                errs.append(f"{name}: campaign temp_c {data['temp_c']} != mapping at.temp_c {fig['at']['temp_c']}")
            vals = {}
            for c in fig["corners"]:
                v = float(cs[c][fig["key"]])
                if not math.isfinite(v):
                    raise ValueError(f"nonfinite {fig['key']} at {c}")
                vals[c] = v * fig.get("scale", 1.0)
        except (OSError, KeyError, TypeError, ValueError) as e:
            errs.append(f"{name}: cannot recompute from {fig.get('campaign_json')}: {e!r}")
            continue
        pick = min if fig["reduce"] == "min" else max
        c = pick(vals, key=vals.get)
        if abs(vals[c] - fig["expected"]) > fig["tol"]:
            errs.append(f"{name}: recomputed {fig['reduce']} {fig['key']} = {vals[c]:.6g} {fig['unit']}, "
                        f"spec states {fig['expected']} (tol {fig['tol']})")
        if c != fig["at"]["corner"]:
            errs.append(f"{name}: binding corner is {c}, mapping says {fig['at']['corner']}")
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
