#!/usr/bin/env python3
"""Guard design/netlist/opamp_core.spice against schematic drift (issue #55).

Regenerates the netlist headlessly with xschem from design/opamp_core.sch
(using design/xschemrc) into a scratch directory, then compares it with the
committed netlist. Exits 0 when they agree, 1 on drift, 2 on a tool error.

Normalisation (what is deliberately NOT treated as drift):

* line 1, ``** sch_path: <absolute path>`` -- records the checkout that ran
  xschem and differs on every machine;
* continuation-line wrapping (``+`` lines) -- joined before comparing;
* number formatting (``W=6.030`` vs ``W=6.03``);
* the *derived* geometry parameters ``ad as pd ps nrd nrs``. They come from
  formulas in the PDK's xschem symbols (``expr('int((@nf + 1)/2) * @W ...')``).
  xschem >= 3.4.5 evaluates those while netlisting; older releases (Ubuntu's
  3.4.4) emit the ``expr(...)`` text verbatim. This script evaluates the
  formulas itself (restricted grammar, @W/@nf substituted from the same
  instance) and compares the numbers within a 0.5 % tolerance, so either
  xschem generation compares equal to the committed netlist.

Everything schematic-driven (instance names, nodes, models, L, W, nf, mult,
m, sa/sb/sd, ...) is compared exactly (numerically exact, not textually).

Usage:
    python3 design/bin/netlist_check.py                  # compare (CI mode)
    python3 design/bin/netlist_check.py --write-record   # refresh the pair record

``--write-record`` rewrites design/netlist/opamp_core.pair.json, the
sha256 pin of the (schematic, netlist) pair that the block manifest cites for
T1 item 1. In compare mode the record is also verified against the files on
disk, so editing either file without refreshing the record fails too.

Requires xschem on PATH and a resolvable sky130 PDK (PDK_ROOT / PDK, see
design/xschemrc and sim/gm-id-characterization/pdk.json).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DESIGN = Path(__file__).resolve().parent.parent
DERIVED = {"ad", "as", "pd", "ps", "nrd", "nrs"}
DERIVED_RTOL = 5e-3
EXPR_RE = re.compile(r"""^expr\('(?P<body>.*)'\)$""")
SAFE_BODY_RE = re.compile(r"^[0-9@A-Za-z_ .+\-*/()]*$")


def sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def logical_lines(text: str) -> list[str]:
    """Drop line 1's sch_path comment; join '+' continuations."""
    out: list[str] = []
    for i, line in enumerate(text.splitlines()):
        if i == 0 and line.startswith("** sch_path:"):
            continue
        if line.startswith("+") and out:
            out[-1] += " " + line[1:].strip()
        else:
            out.append(line.rstrip())
    return out


def split_tokens(line: str) -> list[str]:
    # whitespace split that keeps expr('...') (which contains spaces) whole
    return re.findall(r"""(?:expr\('[^']*'\)|\S)+""", line)


def num(s: str) -> float | None:
    try:
        return float(s)
    except ValueError:
        return None


def eval_expr(body: str, params: dict[str, str]) -> float:
    if not SAFE_BODY_RE.match(body):
        raise ValueError(f"unsupported expression: {body!r}")

    def sub(m: re.Match) -> str:
        v = num(params.get(m.group(1).lower(), ""))
        if v is None:
            raise ValueError(f"@{m.group(1)} has no numeric value")
        return repr(v)

    py = re.sub(r"@(\w+)", sub, body)
    if re.search(r"[A-Za-z_]", re.sub(r"\bint\b", "", py)):
        raise ValueError(f"unsupported identifier in {body!r}")
    return float(eval(py, {"__builtins__": {}}, {"int": int}))  # noqa: S307


def parse(lines: list[str]) -> list[tuple[str, list[str], dict[str, str]]]:
    rows = []
    for line in lines:
        toks = split_tokens(line)
        if not toks:
            continue
        kv = {}
        for t in toks:
            if "=" in t and not t.startswith("expr("):
                k, v = t.split("=", 1)
                kv[k.lower()] = v
        rows.append((line, [t for t in toks if "=" not in t], kv))
    return rows


def value(v: str, params: dict[str, str]) -> float | str:
    m = EXPR_RE.match(v)
    if m:
        return eval_expr(m.group("body"), params)
    n = num(v)
    return n if n is not None else v


def compare(fresh_text: str, committed_text: str) -> list[str]:
    problems: list[str] = []
    fresh = parse(logical_lines(fresh_text))
    comm = parse(logical_lines(committed_text))
    if len(fresh) != len(comm):
        problems.append(f"line count differs: regenerated {len(fresh)}, committed {len(comm)}")
    for (fl, fpos, fkv), (cl, cpos, ckv) in zip(fresh, comm):
        if fpos != cpos:
            problems.append(f"differs:\n  regenerated: {fl}\n  committed:   {cl}")
            continue
        if set(fkv) != set(ckv):
            problems.append(
                f"{fpos[0] if fpos else '?'}: parameter set differs "
                f"({sorted(set(fkv) ^ set(ckv))})\n  regenerated: {fl}\n  committed:   {cl}"
            )
            continue
        try:
            for k in fkv:
                fv, cv = value(fkv[k], fkv), value(ckv[k], ckv)
                if isinstance(fv, float) and isinstance(cv, float):
                    if k in DERIVED:
                        ok = abs(fv - cv) <= DERIVED_RTOL * max(abs(fv), abs(cv), 1e-12)
                    else:
                        ok = fv == cv
                else:
                    ok = fv == cv
                if not ok:
                    problems.append(
                        f"{fpos[0] if fpos else '?'}: {k} regenerated={fv} committed={cv}"
                    )
        except ValueError as exc:
            problems.append(f"{fpos[0] if fpos else '?'}: cannot normalise: {exc}")
    return problems


def regenerate(schematic: Path, xschem: str) -> str:
    if shutil.which(xschem) is None:
        raise RuntimeError(f"{xschem!r} not found on PATH")
    rc = DESIGN / "xschemrc"
    with tempfile.TemporaryDirectory(prefix="netlist-check-") as tmp:
        env = dict(os.environ)
        env.setdefault("PDK_ROOT", str(Path.home() / ".volare"))
        env.setdefault("PDK", "sky130A")
        cmd = [xschem, "-n", "-x", "-q", "-r", "--rcfile", str(rc), "-o", tmp, str(schematic)]
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=300)
        out = Path(tmp) / (schematic.stem + ".spice")
        if proc.returncode != 0 or not out.is_file():
            sys.stderr.write(proc.stdout + proc.stderr)
            raise RuntimeError(f"xschem failed (rc={proc.returncode}); no {out.name} produced")
        return out.read_text()


def record_for(schematic: Path, netlist: Path, record: Path) -> dict:
    rel = lambda p: os.path.relpath(p, record.parent)  # noqa: E731
    return {
        "description": (
            "Content pin of the schematic + xschem-generated netlist pair cited "
            "for T1 item 1. Refreshed by design/bin/netlist_check.py --write-record; "
            "verified by the same script in CI."
        ),
        "schematic": {"path": rel(schematic), "content_hash": sha256(schematic)},
        "netlist": {"path": rel(netlist), "content_hash": sha256(netlist)},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--schematic", type=Path, default=DESIGN / "opamp_core.sch")
    ap.add_argument("--netlist", type=Path, default=DESIGN / "netlist" / "opamp_core.spice")
    ap.add_argument("--record", type=Path, default=DESIGN / "netlist" / "opamp_core.pair.json")
    ap.add_argument("--xschem", default="xschem")
    ap.add_argument("--write-record", action="store_true", help="refresh the pair record and exit")
    ap.add_argument("--skip-record", action="store_true", help="do not verify the pair record")
    args = ap.parse_args()

    if args.write_record:
        args.record.write_text(
            json.dumps(record_for(args.schematic, args.netlist, args.record), indent=2) + "\n"
        )
        print(f"wrote {args.record}")
        return 0

    try:
        fresh = regenerate(args.schematic, args.xschem)
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    problems = compare(fresh, args.netlist.read_text())

    if not args.skip_record:
        try:
            pinned = json.loads(args.record.read_text())
            want = record_for(args.schematic, args.netlist, args.record)
            for key in ("schematic", "netlist"):
                if pinned.get(key, {}).get("content_hash") != want[key]["content_hash"]:
                    problems.append(
                        f"{args.record.name}: pinned {key} hash is stale "
                        f"(file is {want[key]['content_hash']}); run "
                        "design/bin/netlist_check.py --write-record and regenerate "
                        "manifests/sky130-opamp.signoff.json"
                    )
        except (OSError, ValueError) as exc:
            problems.append(f"cannot read pair record {args.record}: {exc}")

    if problems:
        print(f"DRIFT: {args.netlist} does not match a fresh xschem netlist of {args.schematic}")
        for p in problems:
            print(" -", p)
        print("Regenerate with the command in design/README.md, commit the netlist, then")
        print("run design/bin/netlist_check.py --write-record and refresh the envelope + signoff record.")
        return 1
    print(f"OK: {args.netlist} matches a fresh xschem netlist of {args.schematic}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
