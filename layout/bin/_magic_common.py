#!/usr/bin/env python3
"""Shared Magic ``drc(full)`` plumbing for ``layout/bin/`` scripts.

``magic-signoff.py`` and ``probe-passives.py`` both flatten a stream with
KLayout, run the PDK's Magic DRC over it and parse the ``MAGIC_*`` marker
lines. That pipeline lives here once so a Magic output-format fix cannot
reach only one of them.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from _klt_common import BuildError

FLATTEN_RB = """\
ly = RBA::Layout.new
ly.read($input)
top = ly.top_cell
top.flatten(true)
ly.cleanup
ly.write($output)
"""

DRC_TCL = """\
gds read flat.gds
load {cell}
select top cell
box values -100000 -100000 100000 100000
select area
puts "MAGIC_TYPES: [lindex [what -list] 0]"
select clear
{pre}drc euclidean on
drc style drc(full)
drc check
drc catchup
puts "MAGIC_DRC_TOTAL: [drc listall count total]"
foreach {{msg boxes}} [drc listall why] {{ puts "MAGIC_DRC_WHY: [llength $boxes] :: $msg" }}
{post}quit -noprompt
"""


def run_checked(cmd: list[str], cwd: Path) -> str:
    """Run *cmd* in *cwd*; return stdout+stderr, raise ``BuildError`` on non-zero."""
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise BuildError(
            f"{cmd[0]} exited {proc.returncode}:\n{proc.stdout}\n{proc.stderr}"
        )
    return proc.stdout + proc.stderr


def flatten_gds(gds: Path, tmp: Path) -> None:
    """Geometry-flatten *gds* into ``<tmp>/flat.gds`` with KLayout batch mode."""
    (tmp / "flatten.rb").write_text(FLATTEN_RB)
    run_checked(
        ["klayout", "-b", "-rd", f"input={gds}", "-rd", "output=flat.gds",
         "-r", "flatten.rb"],
        tmp,
    )


def run_magic(cell: str, tech: Path, tmp: Path, *, pre: str = "", post: str = "") -> str:
    """Run the DRC script on ``<tmp>/flat.gds``; return Magic's stdout+stderr.

    *pre* is Tcl inserted before the DRC commands, *post* after the DRC
    report (each a newline-terminated block). The exit status is not checked:
    callers decide from the parsed markers whether Magic produced a summary.
    """
    (tmp / "drc.tcl").write_text(DRC_TCL.format(cell=cell, pre=pre, post=post))
    with open(tmp / "drc.tcl") as script:
        proc = subprocess.run(
            ["magic", "-dnull", "-noconsole", "-rcfile", "/dev/null", "-T", str(tech)],
            cwd=tmp,
            stdin=script,
            capture_output=True,
            text=True,
            check=False,
        )
    return proc.stdout + proc.stderr


def parse_magic_log(log: str) -> dict:
    """Parse the ``MAGIC_*`` marker lines; raise ``BuildError`` if absent."""
    types = re.search(r"^MAGIC_TYPES: (.*)$", log, re.MULTILINE)
    total = re.search(r"^MAGIC_DRC_TOTAL: (\d+)", log, re.MULTILINE)
    if not total or not types:
        raise BuildError(f"magic produced no DRC summary:\n{log[-2000:]}")
    why = [
        {"count": int(m.group(1)), "rule": m.group(2)}
        for m in re.finditer(r"^MAGIC_DRC_WHY: (\d+) :: (.*)$", log, re.MULTILINE)
    ]
    return {
        "magic_types_seen": types.group(1).strip("{} ").split(),
        "drc_total": int(total.group(1)),
        "drc_by_rule": why,
    }
