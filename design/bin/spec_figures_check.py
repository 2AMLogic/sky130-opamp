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
  - when `at.supply_v` (binding supply, volts) is set, any printed string
    that renders the corner followed by a voltage ("FF / 125 \u00b0C / 1.98 V")
    must print exactly that voltage; `print_supply: true` requires it;
  - the record id must be cited in that row;
  - `expected`/`tol` must agree with the number and precision printed in
    `printed[0]`, so the mapping cannot drift from its own text.
Copies of a figure outside the table rows (e.g. a section 2 summary paragraph)
are not covered. It also verifies every record id cited anywhere in section 2
exists under sim/*/records/.

Binding point: `at` carries the numeric binding supply `supply_v` (required for
matrix figures) and is compared, via the matrix's `supply_key`, with the row
that attains the extremum. Tie policy: all rows equal to the extremum (relative
1e-9) are valid; the authored point must match one of them, independent of CSV
row order. Diagnostics give the measured and claimed corner/temp/supply.

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

DUT scope and provenance (issue #186): every figure and campaign figure
declares `scope`, either "current" or "historical", plus a `scope_text`
phrase that must occur in the cited table row within SCOPE_WINDOW characters
before the first occurrence of `printed[0]`, so a JSON annotation alone cannot
hide a current-design claim in prose:
  - "current": the cited record's `dut` block must verify (snapshot present,
    hash intact, via sim/lib/dut_identity.verify_record_dut) AND equal the
    canonical design/netlist/opamp_core.spice (dut_identity.check_current). A
    numerically correct record for a different DUT, a missing/corrupt snapshot
    or a record with no `dut` block fails. The `scope_text` must say "current"
    and neither it nor the window before the figure may contain a historical
    word (`historical_words`, default HISTORICAL_WORDS).
  - "historical": needs a non-empty `historical_reason`, and its `scope_text`
    must contain a historical word (e.g. "superseded DR-002 sizing",
    "previous DUT"). A record with a `dut` block still has its identity
    verified; a record without one is legacy and the entry must say
    `"legacy_unverified": true` (never inferred from the Git SHA or today's
    netlist). Historical entries claim nothing about the current design.

Coverage (first increment): gain, GBW, phase margin, rise/fall slew, swing,
quiescent power, CMRR at both common-mode points and ICMR width/edges, all as
current-design figures on the DR-013 canonical records, plus the superseded
DR-002 gain and GBW worst cases (legacy record 20260916-032327-edc9f22) as
historical comparisons and the offset Monte Carlo campaign as historical
evidence on the previous DUT. Not mapped: the ICMR low/high edge of the
narrowest window (needs a row-select key), other superseded-sizing figures,
and ranges.
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
ID_RE = re.compile(r"\b\d{8}-\d{6}-[0-9a-f]{7}(?:-[0-9a-f]{6})?\b")
NUM_RE = re.compile(r"\d+(?:\.\d+)?")
OPAMP_RECORDS = "sim/opamp-characterization/records"
SCOPES = ("current", "historical")
SCOPE_WINDOW = 600
HISTORICAL_WORDS = ("superseded", "historical", "previous dut", "prior record", "prior grid", "prior sizing")


def _dut_identity():
    mod = sys.modules.get("dut_identity")
    if mod is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("dut_identity", REPO / "sim" / "lib" / "dut_identity.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules["dut_identity"] = mod
        spec.loader.exec_module(mod)
    return mod


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
    return errs + check_supply_text(name, fig, printed)


def hist_words(mapping):
    return tuple(w.lower() for w in mapping.get("historical_words", HISTORICAL_WORDS))


def check_scope_text(name, fig, row, words):
    """Bind the declared scope to the cited table-row prose."""
    scope, st = fig.get("scope"), fig.get("scope_text")
    if scope not in SCOPES:
        return [f"{name}: scope must be one of {SCOPES}, got {scope!r}"]
    if not isinstance(st, str) or not st.strip():
        return [f"{name}: scope {scope!r} needs a non-empty scope_text that appears in its section 2 row"]
    errs = []
    st_hist = [w for w in words if w in st.lower()]
    if scope == "historical":
        if not str(fig.get("historical_reason", "")).strip():
            errs.append(f"{name}: historical scope needs a non-empty historical_reason")
        if not st_hist:
            errs.append(f"{name}: historical scope_text {st!r} contains no historical word {list(words)}")
    elif st_hist or "current" not in st.lower():
        errs.append(f"{name}: current scope_text {st!r} must say 'current' and contain no historical word")
    pos = row.find(fig["printed"][0]) if fig.get("printed") else -1
    if pos < 0:
        return errs  # check_text already reports the missing printed text
    window = row[max(0, pos - SCOPE_WINDOW): pos]
    if st not in window:
        errs.append(f"{name}: scope_text {st!r} does not occur within {SCOPE_WINDOW} characters before "
                    f"{fig['printed'][0]!r} in its section 2 row")
    elif scope == "current":
        hit = [w for w in words if w in window.lower()]
        if hit:
            errs.append(f"{name}: declared current-design but its section 2 prose describes it as "
                        f"historical (found {hit} before the figure)")
    return errs


def check_provenance(root, name, fig, rec_path):
    """DUT identity of the record behind a figure, per its declared scope."""
    scope = fig.get("scope")
    if scope not in SCOPES:
        return []  # reported by check_scope_text
    root = Path(root)
    try:
        rec = json.loads(rec_path.read_text(encoding="utf-8"))
        if not isinstance(rec, dict):
            raise ValueError("not a JSON object")
    except (OSError, ValueError) as e:
        return [f"{name}: cannot read record {rec_path.name} for DUT identity: {e}"]
    di = _dut_identity()
    try:
        state, problems = di.verify_record_dut(rec, root)
        stale = di.check_current(rec, root) if scope == "current" and state == di.VERIFIED else []
    except (AttributeError, TypeError, OSError) as e:
        return [f"{name}: record {rec_path.name} has an unusable dut block: {e!r}"]
    errs = [f"{name}: {p}" for p in problems + stale]
    legacy = fig.get("legacy_unverified") is True
    if state == di.UNVERIFIED:
        if scope == "current":
            errs.append(f"{name}: declared current-design but {rec_path.name} has no verified `dut` block "
                        f"(legacy record); cite a record for the canonical DUT or mark the figure historical")
        elif not legacy:
            errs.append(f"{name}: {rec_path.name} has no `dut` block; a historical figure on it must set "
                        f"\"legacy_unverified\": true")
    elif legacy:
        errs.append(f"{name}: legacy_unverified is set but {rec_path.name} carries a `dut` block")
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


def worst(fig, rows, supply_key="vdd_v"):
    """(extremum, tied rows, n). Tied rows all attain the extremum (nonfinite
    values are ignored here; the matrix check reports them), sorted by
    (corner, temp_c, supply) so the result never depends on CSV row order."""
    rows = filtered(fig, rows)
    if not rows:
        raise ValueError("no rows after filter")
    fin = []
    for r in rows:
        try:
            v = float(r[fig["key"]])
        except (TypeError, ValueError):
            continue
        if math.isfinite(v):
            fin.append((v, r))
    if not fin:
        raise ValueError(f"no finite {fig['key']} values")
    pick = min if fig["reduce"] == "min" else max
    ext = pick(v for v, _ in fin)
    tied = [r for v, r in fin if math.isclose(v, ext, rel_tol=1e-9, abs_tol=1e-12)]
    try:
        tied.sort(key=lambda r: (r["corner"], float(r["temp_c"]), float(r.get(supply_key) or "nan")))
    except (KeyError, TypeError, ValueError):
        pass
    return ext * fig.get("scale", 1.0), tied, len(rows)


SUPPLY_RE = r"\s*/\s*(\d+(?:\.\d+)?)\s*V\b"


def check_supply_text(name, fig, printed):
    """Validate the numeric binding supply `at.supply_v` against printed text.

    A printed string that renders the binding corner followed by a voltage
    ("FF / 125 \u00b0C / 1.98 V") must print exactly `supply_v`. Figures that
    print no voltage after the corner keep their text unchanged unless the
    mapping sets `print_supply: true`, which requires that rendering.
    """
    sv = fig["at"].get("supply_v")
    if sv is None:
        return []
    errs, ct, found = [], corner_text(fig["at"]), False
    for s in printed:
        for m in re.finditer(re.escape(ct) + SUPPLY_RE, s):
            found = True
            if not math.isclose(float(m.group(1)), float(sv), rel_tol=0, abs_tol=1e-9):
                errs.append(f"{name}: printed supply {m.group(1)} V in {s!r} != mapping at.supply_v {sv} V")
    if fig.get("print_supply") and not found:
        errs.append(f"{name}: print_supply set but no printed string renders '{ct} / {float(sv):g} V'")
    return errs


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
            errs += check_scope_text(name, fig, rows[0], hist_words(mapping))
            if fig["record"] not in rows[0]:
                errs.append(f"{name}: record {fig['record']} is not cited in its section 2 row")
        errs += check_provenance(root, name, fig, root / OPAMP_RECORDS / f"{fig['record']}.json")
        path = root / OPAMP_RECORDS / f"{fig['record']}-{fig['csv']}.csv"
        if not path.is_file():
            errs.append(f"{name}: record CSV missing: {path.relative_to(root)}")
            continue
        try:
            with path.open(newline="", encoding="utf-8") as f:
                allrows = list(csv.DictReader(f))
            errs += check_figure_matrix(name, fig, matrices, allrows, mapping["figures"], checked)
            m = matrices.get(fig.get("matrix"))
            sk = (m or {}).get("supply_key", "vdd_v")
            val, tied, n = worst(fig, allrows, sk)
        except (KeyError, ValueError) as e:
            errs.append(f"{name}: cannot recompute from {path.name}: {e!r}")
            continue
        if abs(val - fig["expected"]) > fig["tol"]:
            errs.append(
                f"{name}: recomputed {fig['reduce']} {fig['key']} = {val:.6g} {fig['unit']}, "
                f"spec states {fig['expected']} (tol {fig['tol']})"
            )
        errs += check_binding(name, fig, tied, sk, m is not None)
    errs += check_campaign_figures(root, spec2, mapping)
    return errs


def check_binding(name, fig, tied, sk, has_matrix):
    """The authored binding point must attain the extremum.

    Tie policy: every row equal to the extremum (relative 1e-9) is a valid
    binding point; the authored `at` passes if it matches any of them, so the
    result is independent of CSV row order. `at.supply_v` is required for
    matrix figures and compared with the row's supply column (`supply_key`).
    """
    at = fig["at"]
    sv = at.get("supply_v")
    if has_matrix and sv is None:
        return [f"{name}: mapping at.supply_v (binding supply, volts) is required for matrix figures"]

    def supply(r):
        try:
            return float(r[sk])
        except (KeyError, TypeError, ValueError):
            return None

    def hit(r):
        s = supply(r)
        return (r["corner"] == at["corner"] and float(r["temp_c"]) == float(at["temp_c"])
                and (sv is None or (s is not None and math.isclose(s, float(sv), rel_tol=0, abs_tol=1e-6))))

    if any(hit(r) for r in tied):
        return []
    meas = ", ".join(f"{r['corner']}/{r['temp_c']} C/{r.get(sk)} V" for r in tied)
    claimed = f"{at['corner']}/{at['temp_c']} C" + (f"/{sv} V" if sv is not None else "")
    return [f"{name}: binding corner is {meas} (measured {sk}), mapping says {claimed} (claimed)"
            + (f"; measured supply {tied[0].get(sk)} V != claimed supply {sv} V"
               if sv is not None and len(tied) == 1 and tied[0]["corner"] == at["corner"]
               and float(tied[0]["temp_c"]) == float(at["temp_c"]) else "")]


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
            errs += check_scope_text(name, fig, rows[0], hist_words(mapping))
            for cite in (fig["record_md"], fig["campaign_json"]):
                if Path(cite).name not in rows[0]:
                    errs.append(f"{name}: {Path(cite).name} is not cited in its section 2 row")
        for cite in (fig["record_md"], fig["campaign_json"]):
            if not (root / cite).is_file():
                errs.append(f"{name}: cited campaign file missing: {cite}")
        if (root / fig["campaign_json"]).is_file():
            errs += check_provenance(root, name, fig, root / fig["campaign_json"])
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
        try:
            m = json.loads((Path(a.root) / MAPPING).read_text(encoding="utf-8"))
            allf = m["figures"] + m.get("campaign_figures", [])
            cur = sum(f["scope"] == "current" for f in allf)
            leg = [f["row"] for f in allf if f.get("legacy_unverified")]
            print(f"NOTE {cur} figure(s) verified against the canonical DUT; "
                  f"{len(allf) - cur} historical, {len(leg)} of them legacy/unverified: {', '.join(leg) or 'none'}")
        except (OSError, ValueError, KeyError):
            pass
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
