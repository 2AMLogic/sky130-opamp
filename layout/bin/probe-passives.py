#!/usr/bin/env python3
"""Passive realizability probes for the compensation network (issue #131).

Generates throwaway single-element XRz / XCc *probe cells* with the pinned
klt generators (``res_array`` flavor "high", ``cap_array``) and records, for
each: the generator report, ``klt drc --deck sky130``, ``klt extract``, and
the PDK's own Magic ``drc(full)`` over the flattened stream.

These are PASSIVE PROBES, not full-core layout: no routing, no guard ring,
no LVS against the core netlist, and they are never composed into a cell.
Their only job is to show that a given SPICE ``L``/``W`` can (or cannot) be
drawn by the generator and what the layout-derived length is.

Usage (from the repo root)::

    python3 layout/bin/probe-passives.py                # rebuild + write
    python3 layout/bin/probe-passives.py --check        # rebuild in a tmp dir and compare verdicts

``$KLT_CMD`` selects the klt launcher; by default the pinned build from
``layout/pdk.json`` is run through ``uvx`` (the host ``klt`` is not assumed
to be the pin).  The klt commit and the open_pdks commit are asserted
against ``layout/pdk.json`` before anything is generated.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
from _klt_common import BuildError, write_json  # noqa: E402

PDK_PIN = REPO_ROOT / "layout" / "pdk.json"
OUT_ROOT = REPO_ROOT / "layout" / "passive_probes"
GRID_UM = 0.005  # sky130 manufacturing grid used by this repo (README, DR-010)

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
drc euclidean on
drc style drc(full)
drc check
drc catchup
puts "MAGIC_DRC_TOTAL: [drc listall count total]"
foreach {{msg boxes}} [drc listall why] {{ puts "MAGIC_DRC_WHY: [llength $boxes] :: $msg" }}
quit -noprompt
"""

# id, generator, params, schematic statement it probes
PROBES = [
    {
        "id": "rz_L9p763_prior",
        "role": "XRz prior schematic length (off-grid) -- negative control",
        "generator": "res_array",
        "params": {"length_um": 9.763, "width_um": 1.41, "num": 1, "dummy": 0, "flavor": "high"},
        "spice": {"model": "res_high_po_1p41", "L": 9.763, "W": 1.41},
    },
    {
        "id": "rz_L9p765",
        "role": "XRz candidate: nearest grid-legal length above 9.763",
        "generator": "res_array",
        "params": {"length_um": 9.765, "width_um": 1.41, "num": 1, "dummy": 0, "flavor": "high"},
        "spice": {"model": "res_high_po_1p41", "L": 9.765, "W": 1.41},
    },
    {
        "id": "rz_L9p760",
        "role": "XRz alternative: nearest grid-legal length below 9.763",
        "generator": "res_array",
        "params": {"length_um": 9.76, "width_um": 1.41, "num": 1, "dummy": 0, "flavor": "high"},
        "spice": {"model": "res_high_po_1p41", "L": 9.76, "W": 1.41},
    },
    {
        "id": "cc_15p62",
        "role": "XCc as in the schematic (cap_mim_m3_1 W=L=15.62)",
        "generator": "cap_array",
        "params": {"plate_w_um": 15.62, "plate_h_um": 15.62, "num": 1},
        "spice": {"model": "cap_mim_m3_1", "L": 15.62, "W": 15.62},
    },
]


def klt_cmd() -> list[str]:
    if os.environ.get("KLT_CMD"):
        return shlex.split(os.environ["KLT_CMD"])
    pin = json.loads(PDK_PIN.read_text())
    return ["uvx", "--from", f"klayout-tools @ git+https://github.com/2AMLogic/klayout-tools@{pin['klt_commit']}", "klt"]


def run_klt(klt: list[str], args: list[str], cwd: Path, env: dict, ok: tuple = (0,)) -> dict:
    proc = subprocess.run([*klt, *args, "--format", "json"], cwd=cwd, env=env,
                          capture_output=True, text=True, check=False)
    try:
        resp = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise BuildError(f"klt {' '.join(args)}: no JSON (exit {proc.returncode}):\n{proc.stdout}\n{proc.stderr}") from exc
    if "error" in resp:
        raise BuildError(f"klt {' '.join(args)} failed: {resp['error'].get('message')}")
    if proc.returncode not in ok and proc.returncode not in (0, 2, 3):
        raise BuildError(f"klt {' '.join(args)} exit {proc.returncode}")
    return resp


def check_toolchain(klt: list[str], env: dict) -> dict:
    pin = json.loads(PDK_PIN.read_text())
    ver = run_klt(klt, ["version"], REPO_ROOT, env)
    pdk = run_klt(klt, ["pdk", "find", "--pdk", pin["variant"]], REPO_ROOT, env)
    problems = []
    if ver.get("git_commit") != pin["klt_commit"]:
        problems.append(f"klt {ver.get('git_commit')} != pinned {pin['klt_commit']}")
    if pin["open_pdks_commit"] not in str(pdk.get("version", "")):
        problems.append(f"open_pdks {pdk.get('version')} != pinned {pin['open_pdks_commit']}")
    if problems:
        raise BuildError("toolchain does not match layout/pdk.json: " + "; ".join(problems))
    return {"klt": ver["version"], "pdk": pdk.get("version"), "magic_tech": Path(pdk["assets"]["magic"]) / f"{pin['variant']}.tech"}


def magic_drc(gds: Path, cell: str, tech: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="probe-magic-") as tmp:
        t = Path(tmp)
        (t / "flatten.rb").write_text(FLATTEN_RB)
        subprocess.run(["klayout", "-b", "-rd", f"input={gds}", "-rd", "output=flat.gds", "-r", "flatten.rb"],
                       cwd=t, check=True, capture_output=True, text=True)
        (t / "drc.tcl").write_text(DRC_TCL.format(cell=cell))
        with open(t / "drc.tcl") as script:
            proc = subprocess.run(["magic", "-dnull", "-noconsole", "-rcfile", "/dev/null", "-T", str(tech)],
                                  cwd=t, stdin=script, capture_output=True, text=True, check=False)
    log = proc.stdout + proc.stderr
    types = re.search(r"^MAGIC_TYPES: (.*)$", log, re.MULTILINE)
    total = re.search(r"^MAGIC_DRC_TOTAL: (\d+)", log, re.MULTILINE)
    if not total or not types:
        raise BuildError(f"magic produced no DRC summary:\n{log[-1500:]}")
    why = [{"count": int(m.group(1)), "rule": m.group(2)}
           for m in re.finditer(r"^MAGIC_DRC_WHY: (\d+) :: (.*)$", log, re.MULTILINE)]
    seen = types.group(1).strip("{} ").split()
    return {"drc_style": "drc(full)", "drc_total": int(total.group(1)), "drc_by_rule": why,
            "magic_types_seen": seen,
            "vacuous": not seen}


def off_grid(value_um: float) -> bool:
    n = value_um / GRID_UM
    return abs(n - round(n)) > 1e-6


def build_probe(probe: dict, out: Path, klt: list[str], env: dict, tech: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    cell = probe["id"]
    gen = run_klt(klt, ["gen", probe["generator"], "--pdk", "sky130A", "--params", json.dumps(probe["params"]),
                        "--cell-name", cell, "-o", f"{cell}.gds"], out, env)
    drc = run_klt(klt, ["drc", f"{cell}.gds", "--deck", "sky130"], out, env)
    ext = run_klt(klt, ["extract", f"{cell}.gds", "--deck", "sky130"], out, env)
    # klt extract writes <cell>.spice next to the GDS; keep it, drop nothing.
    for name, payload in (("gen", gen), ("drc", drc), ("extract", ext)):
        for volatile in ("provenance",):
            payload.pop(volatile, None)
        write_json(out / f"{cell}.{name}.json", payload)
    magic = magic_drc(out / f"{cell}.gds", cell, tech)
    write_json(out / f"{cell}.magic.json", magic)
    dev = ext["devices"][0]
    summary = {
        "id": cell,
        "role": probe["role"],
        "kind": "passive probe (not full-core layout)",
        "spice_statement": probe["spice"],
        "spice_L_off_grid": off_grid(probe["spice"]["L"]),
        "generator_bbox_um": gen["bbox_um"],
        "klt_drc": {"status": drc["status"], "violation_count": drc["violation_count"]},
        "magic_drc_full": {"total": magic["drc_total"], "by_rule": magic["drc_by_rule"], "vacuous": magic["vacuous"]},
        "extract_device": {"class": dev["class"], "params": dev["params"]},
    }
    write_json(out / f"{cell}.summary.json", summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="rebuild into a temp dir and compare the verdict fields")
    args = ap.parse_args(argv)
    env = {**os.environ, "PDK": "sky130A"}
    klt = klt_cmd()
    tool = check_toolchain(klt, env)
    tech = tool.pop("magic_tech")
    root = Path(tempfile.mkdtemp(prefix="probe-passives-")) if args.check else OUT_ROOT
    summaries = [build_probe(p, root / p["id"], klt, env, tech) for p in PROBES]
    index = {"schema": "sky130-opamp/passive-probes/1", "tools": tool, "probes": summaries}
    if args.check:
        committed = json.loads((OUT_ROOT / "index.json").read_text())
        if committed != index:
            print("passive probe evidence differs from the committed layout/passive_probes/index.json", file=sys.stderr)
            return 1
        print("passive probes: committed evidence reproduced")
        return 0
    write_json(OUT_ROOT / "index.json", index)
    for s in summaries:
        print(f"{s['id']}: klt drc {s['klt_drc']['status']}, magic drc(full) {s['magic_drc_full']['total']}"
              f"{' (VACUOUS)' if s['magic_drc_full']['vacuous'] else ''}, "
              f"extracted L={s['extract_device']['params'].get('l_um')}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
