#!/usr/bin/env python3
"""Second-opinion signoff of a composed cell with the PDK's own Magic/netgen.

``klt drc --deck sky130`` runs a curated rule subset. Its ``coverage`` block
says which rules ran, and it does not include sky130's implant rules or the
poly endcap rule (``poly.8``). This script checks the same committed GDS
against the open_pdks ``sky130A.tech`` full DRC style (``drc(full)``), then
extracts it with Magic and compares it to the cell's generated LVS
reference with netgen and ``sky130A_setup.tcl``. It is evidence beside the
klt chain, not part of it: ``compose-cell.py --check`` does not run it, and
it writes only under ``<cell>/magic-signoff/``.

The GDS is flattened at the *geometry* level first, with KLayout in batch
mode. Magic interprets layers per cell when it reads a hierarchical stream,
so an implant drawn in a sibling cell would never combine with the
diffusion it covers. Magic would then read every n-diffusion as p-diffusion
and report spurious nwell errors. Magic's own ``gds flatglob`` is no
substitute: on these streams it yields an empty top cell, which then
"passes" DRC vacuously. The script therefore also requires that Magic sees
the expected device types before it trusts a zero count.

Usage:
    python3 layout/bin/magic-signoff.py layout/opamp_stage1/cell.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _klt_common import BuildError, run_klt, write_json  # noqa: E402

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
port makeall
drc euclidean on
drc style drc(full)
drc check
drc catchup
puts "MAGIC_DRC_TOTAL: [drc listall count total]"
foreach {{msg boxes}} [drc listall why] {{ puts "MAGIC_DRC_WHY: [llength $boxes] :: $msg" }}
extract all
ext2spice lvs
ext2spice -o {cell}.magic.spice
quit -noprompt
"""


def run(cmd: list[str], cwd: Path) -> str:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise BuildError(
            f"{cmd[0]} exited {proc.returncode}:\n{proc.stdout}\n{proc.stderr}"
        )
    return proc.stdout + proc.stderr


def signoff_clean(summary: dict, netgen_match: bool) -> bool:
    """DRC clean, devices/nets matched AND boundary pins compared equivalent."""
    return (
        summary["drc_total"] == 0
        and netgen_match
        and summary["netgen"]["pins_matched"] is True
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("spec", type=Path)
    parser.add_argument(
        "--expect-types",
        default=None,
        help="comma-separated Magic types that must be present (anti-vacuous "
        "guard); default: the cell.json's expect.magic_types, else "
        "nmos,ndiff,psubdiff,poly",
    )
    args = parser.parse_args(argv)
    spec_path = args.spec.resolve()
    spec = json.loads(spec_path.read_text())
    cell_dir = spec_path.parent
    cell = spec["cell"]
    variant = spec["pdk"]["variant"]
    expect_types = args.expect_types or ",".join(
        spec.get("expect", {}).get("magic_types", ["nmos", "ndiff", "psubdiff", "poly"])
    )

    pdk = run_klt(["pdk", "find", "--pdk", variant], env=dict(os.environ))
    magic_tech = Path(pdk["assets"]["magic"]) / f"{variant}.tech"
    netgen_setup = Path(pdk["assets"]["netgen"]) / f"{variant}_setup.tcl"

    out = cell_dir / "magic-signoff"
    out.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="magic-signoff-") as tmp:
        tmp_dir = Path(tmp)
        (tmp_dir / "flatten.rb").write_text(FLATTEN_RB)
        run(
            [
                "klayout",
                "-b",
                "-rd",
                f"input={cell_dir / f'{cell}.gds'}",
                "-rd",
                "output=flat.gds",
                "-r",
                "flatten.rb",
            ],
            tmp_dir,
        )
        (tmp_dir / "drc.tcl").write_text(DRC_TCL.format(cell=cell))
        with open(tmp_dir / "drc.tcl") as script:
            proc = subprocess.run(
                [
                    "magic",
                    "-dnull",
                    "-noconsole",
                    "-rcfile",
                    "/dev/null",
                    "-T",
                    str(magic_tech),
                ],
                cwd=tmp_dir,
                stdin=script,
                capture_output=True,
                text=True,
                check=False,
            )
        log = proc.stdout + proc.stderr
        types_line = re.search(r"^MAGIC_TYPES: (.*)$", log, re.MULTILINE)
        total = re.search(r"^MAGIC_DRC_TOTAL: (\d+)", log, re.MULTILINE)
        if not types_line or not total:
            raise BuildError(f"magic produced no DRC summary:\n{log[-2000:]}")
        types = types_line.group(1).strip("{} ").split()
        why = [
            {"count": int(m.group(1)), "rule": m.group(2)}
            for m in re.finditer(r"^MAGIC_DRC_WHY: (\d+) :: (.*)$", log, re.MULTILINE)
        ]
        missing = [t for t in expect_types.split(",") if t and t not in types]

        (tmp_dir / "ref.spice").write_text((cell_dir / f"{cell}.ref.spice").read_text())
        netgen_log = run(
            [
                "netgen",
                "-batch",
                "lvs",
                f"{cell}.magic.spice {cell}",
                f"ref.spice {spec['lvs']['subckt']}",
                str(netgen_setup),
                "netgen.out",
            ],
            tmp_dir,
        )
        report = (tmp_dir / "netgen.out").read_text()
        (out / f"{cell}.magic.spice").write_text(
            (tmp_dir / f"{cell}.magic.spice").read_text()
        )
        (out / "netgen.out").write_text(report)
        version = run(["magic", "--version"], tmp_dir).strip()
        netgen_version = re.search(r"Netgen (\S+)", netgen_log)

    netgen_match = (
        "Netlists match uniquely." in report or "Circuits match uniquely." in report
    )
    summary = {
        "schema": "sky130-opamp/magic-signoff/1",
        "gds": f"{cell}.gds",
        "tools": {
            "magic": version,
            "netgen": netgen_version.group(1) if netgen_version else None,
            "pdk": pdk.get("version"),
            "magic_tech": f"{variant}.tech",
            "drc_style": "drc(full)",
            "netgen_setup": netgen_setup.name,
        },
        "magic_types_seen": types,
        "missing_expected_types": missing,
        "drc_total": int(total.group(1)),
        "drc_by_rule": why,
        "netgen": {
            "netlists_match_uniquely": "Netlists match uniquely." in report,
            "pins_matched": "Cell pin lists are equivalent." in report,
            "result_lines": [
                line.strip()
                for line in report.splitlines()
                if "match" in line.lower() and "pin" not in line.lower()
            ][-6:],
        },
    }
    write_json(out / "magic.json", summary)
    print(
        f"magic drc(full): {summary['drc_total']} errors; types seen: {' '.join(types)}; "
        f"netgen: {'match' if netgen_match else 'NO MATCH'}"
    )
    if missing:
        print(
            f"error: expected Magic types missing {missing} -- result would be vacuous",
            file=sys.stderr,
        )
        return 1
    return 0 if signoff_clean(summary, netgen_match) else 3


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
