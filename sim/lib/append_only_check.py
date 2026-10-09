#!/usr/bin/env python3
"""Fail a PR that edits, deletes or renames committed sim evidence.

CLAUDE.md: "`sim/` results are append-only evidence". Guarded paths:
  sim/*/records/   sim/*/corners/   sim/*/netlist-snapshots/
(README.md prose under sim/*/ is deliberately NOT guarded.)

Only git status `A` (added) is permitted. M, D, T and R*/C* are violations;
for a rename/copy the OLD path is the one checked (the new path is an add).
Escape hatch: sim/append-only-allowlist.txt, one `path | authority` per line
(authority = issue or decision record), so a correction is visible in review.

Paths are read from `git diff --name-status -z` (NUL-separated, never
C-quoted), so names containing `"`, backslash, tab or newline are still seen.

Usage: append_only_check.py [--base origin/main] [--allowlist FILE]
       git diff --name-status -z -M A...B | append_only_check.py --stdin
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


def parse_name_status_z(data: str):
    """Parse `git diff --name-status -z` output into [(status, [paths])].

    Each record is STATUS NUL PATH NUL, or STATUS NUL OLD NUL NEW NUL for
    R*/C*. Malformed/truncated input raises ValueError (fail closed).
    """
    fields = data.split("\0")
    if fields and fields[-1] == "":
        fields.pop()
    records, i = [], 0
    while i < len(fields):
        status = fields[i].strip()
        if not status or not status[0].isalpha():
            raise ValueError(f"unexpected name-status field {fields[i]!r}")
        n = 2 if status[0] in "RC" else 1
        paths = fields[i + 1:i + 1 + n]
        if len(paths) != n or any(not p for p in paths):
            raise ValueError(f"truncated name-status record for {status!r}")
        records.append((status, paths))
        i += 1 + n
    return records


def find_violations(name_status_z: str, allowlist: dict):
    """Return (violations, allowed) as lists of (status, path).

    `name_status_z` is `git diff --name-status -z` output.
    """
    violations, allowed = [], []
    for status, paths in parse_name_status_z(name_status_z):
        if status == "A" or status[0] == "C":
            # adds are fine; a copy leaves its source untouched
            continue
        # for a rename the OLD path is the pre-existing evidence; new is an add
        checked = paths[:1] if status[0] == "R" else paths
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
        buf = getattr(sys.stdin, "buffer", None)
        data = (buf.read().decode("utf-8", "surrogateescape")
                if buf is not None else sys.stdin.read())
    else:
        data = subprocess.run(
            ["git", "diff", "--name-status", "-z", "-M",
             f"{args.base}...HEAD", "--", "sim/"],
            check=True, capture_output=True).stdout.decode("utf-8", "surrogateescape")
    al_path = Path(args.allowlist)
    allow = parse_allowlist(al_path.read_text(encoding="utf-8")) if al_path.exists() else {}
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
