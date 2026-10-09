#!/usr/bin/env python3
"""Fail a PR that edits, deletes or renames committed sim evidence.

CLAUDE.md: "`sim/` results are append-only evidence". Guarded paths:
  sim/*/records/   sim/*/corners/   sim/*/netlist-snapshots/
(README.md prose under sim/*/ is deliberately NOT guarded.)

Only git status `A` (added) is permitted. M, D, T and R*/C* are violations;
for a rename/copy the OLD path is the one checked (the new path is an add).
Escape hatch: sim/append-only-allowlist.txt, one `path | authority` per line
(authority = issue or decision record), so a correction is visible in review.

Usage: append_only_check.py [--base origin/main] [--allowlist FILE]
       git diff --name-status A...B | append_only_check.py --stdin
Stdlib only.
"""

import argparse
import fnmatch
import subprocess
import sys
from pathlib import Path

GUARDED = ("sim/*/records/", "sim/*/corners/", "sim/*/netlist-snapshots/")
DEFAULT_ALLOWLIST = "sim/append-only-allowlist.txt"


def is_guarded(path: str) -> bool:
    return any(fnmatch.fnmatchcase(path, g + "*") for g in GUARDED)


def parse_allowlist(text: str) -> dict:
    """Return {path: authority}. Entries without an authority are rejected."""
    out = {}
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        path, sep, auth = (p.strip() for p in line.partition("|"))
        if not sep or not path or not auth:
            raise ValueError(f"allowlist line {n}: expected 'path | issue-or-DR'")
        out[path] = auth
    return out


def find_violations(name_status: str, allowlist: dict):
    """Return (violations, allowed) as lists of (status, path)."""
    violations, allowed = [], []
    for raw in name_status.splitlines():
        if not raw.strip():
            continue
        fields = raw.split("\t")
        status, paths = fields[0].strip(), fields[1:]
        if not paths:
            continue
        if status[0] in "RC":
            # old path is the pre-existing evidence; new path is just an add
            checked = paths[:1] if status[0] == "R" else []
            if status[0] == "C":
                continue
        else:
            checked = paths
        if status == "A":
            continue
        for p in checked:
            if not is_guarded(p):
                continue
            (allowed if p in allowlist else violations).append((status, p))
    return violations, allowed


def remediation(violations, allowlist_path=DEFAULT_ALLOWLIST) -> str:
    lines = ["append-only evidence violation(s):"]
    lines += [f"  {s}\t{p}" for s, p in violations]
    lines += [
        "",
        "Committed evidence under sim/*/records, corners and netlist-snapshots",
        "is append-only. Remediation:",
        "  - restore the file(s) and add a new record instead (supersede, don't edit); or",
        f"  - if the change is authorised, add a line to {allowlist_path}:",
    ]
    lines += [f"      {p} | <issue-or-DR>" for _, p in violations]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--allowlist", default=DEFAULT_ALLOWLIST)
    ap.add_argument("--stdin", action="store_true", help="read name-status from stdin")
    args = ap.parse_args(argv)

    if args.stdin:
        data = sys.stdin.read()
    else:
        data = subprocess.run(
            ["git", "-c", "core.quotepath=off", "diff", "--name-status", "-M",
             f"{args.base}...HEAD", "--", "sim/"],
            check=True, capture_output=True, text=True).stdout
    al_path = Path(args.allowlist)
    allow = parse_allowlist(al_path.read_text()) if al_path.exists() else {}
    violations, allowed = find_violations(data, allow)
    for s, p in allowed:
        print(f"allowlisted ({allow[p]}): {s}\t{p}")
    if violations:
        print(remediation(violations, args.allowlist), file=sys.stderr)
        return 1
    print("append-only evidence check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
