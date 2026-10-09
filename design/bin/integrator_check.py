#!/usr/bin/env python3
"""Validate / refresh manifests/integrator.json against its cited sources.

Stdlib only, simulator-free.

  integrator_check.py validate [--root DIR]   exit 1 on any disagreement
  integrator_check.py refresh  [--root DIR]   rewrite derived fields only

Derived fields (rewritten by refresh, compared by validate):
  maturity.tier / t1_met / t1_total   <- manifests/sky130-opamp.signoff.json
  top_cell, ports (ordered)           <- design/netlist/opamp_core.spice
Authored fields (never touched): consumers, spec_status, evaluated_at, notes.
Validate also checks that every non-null artifact path exists and that `gds`
never points into layout/opamp_stage1 (a partial layout, not the full core).

Snapshot semantics: the manifest describes the current checkout. It does not
embed its own resulting commit SHA; `evaluated_at` is a disclosed historical
stamp and is not compared.
"""
import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
MANIFEST = "manifests/integrator.json"
SIGNOFF = "manifests/sky130-opamp.signoff.json"
PARTIAL_DIR = "layout/opamp_stage1"
GDS_NOTE = (
    "no full-core layout exists yet; a partial stage-1 layout (input pair only) "
    "is in layout/opamp_stage1 and is not the full-core deliverable"
)

_SUBCKT = re.compile(r"^\s*(?:\*\*)?\.subckt\s+(\S+)\s*(.*)$", re.IGNORECASE)


def parse_subckt(text, top=None):
    """Return (name, ports) of the first .subckt (or **.subckt) line, or of
    the one named `top` if given."""
    for line in text.splitlines():
        m = _SUBCKT.match(line)
        if not m:
            continue
        toks = [t for t in m.group(2).split() if "=" not in t]
        if top is None or m.group(1) == top:
            return m.group(1), toks
    return None, []


def _load(root, rel):
    return json.loads((Path(root) / rel).read_text(encoding="utf-8"))


def derive(root):
    so = _load(root, SIGNOFF)
    man = _load(root, MANIFEST)
    net = (Path(root) / man.get("netlist", "design/netlist/opamp_core.spice")).read_text()
    name, ports = parse_subckt(net, man.get("top_cell"))
    return {
        "top_cell": name,
        "ports": ports,
        "maturity.tier": so.get("tier"),
        "maturity.t1_met": so.get("t1_met_count"),
        "maturity.t1_total": so.get("t1_item_count"),
    }


def _get(man, dotted):
    cur = man
    for k in dotted.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def check(root):
    """Return a list of diagnostic strings (empty == consistent)."""
    root = Path(root)
    man = _load(root, MANIFEST)
    errs = []
    for field, expected in derive(root).items():
        actual = _get(man, field)
        if actual != expected:
            errs.append(f"{field}: expected {expected!r} (from source), actual {actual!r}")
    for field in ("netlist", "gds", "maturity.source"):
        p = _get(man, field)
        if p is not None and not (root / p).exists():
            errs.append(f"{field}: expected existing path, actual {p!r} (missing)")
    gds = man.get("gds")
    if gds is not None:
        norm = Path(gds).as_posix().lstrip("./")
        if norm == PARTIAL_DIR or norm.startswith(PARTIAL_DIR + "/"):
            errs.append(
                f"gds: expected full-core GDS outside {PARTIAL_DIR}/ (partial layout), actual {gds!r}"
            )
    return errs


def refresh(root):
    root = Path(root)
    path = root / MANIFEST
    man = json.loads(path.read_text())
    d = derive(root)
    man["top_cell"] = d["top_cell"]
    man["ports"] = d["ports"]
    man["maturity"]["tier"] = d["maturity.tier"]
    man["maturity"]["t1_met"] = d["maturity.t1_met"]
    man["maturity"]["t1_total"] = d["maturity.t1_total"]
    if man.get("gds") is None:
        man["gds_note"] = GDS_NOTE
    out = json.dumps(man, indent=2, ensure_ascii=False)
    # keep the ports list on one line (matches the authored layout)
    out = re.sub(
        r'"ports": \[([^\]]*)\]',
        lambda m: '"ports": [' + ", ".join(t.strip() for t in m.group(1).split(",")) + "]",
        out,
    )
    path.write_text(out + "\n", encoding="utf-8")
    return man


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("mode", choices=["validate", "refresh"])
    ap.add_argument("--root", default=str(REPO))
    a = ap.parse_args(argv)
    if a.mode == "refresh":
        refresh(a.root)
        print(f"refreshed {MANIFEST}")
        return 0
    errs = check(a.root)
    for e in errs:
        print(f"FAIL {MANIFEST} {e}")
    if not errs:
        print(f"OK {MANIFEST} agrees with cited sources")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
