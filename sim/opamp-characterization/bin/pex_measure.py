#!/usr/bin/env python3
"""`klt pex --measure-command` wrapper over the opamp_core PVT benches (issue #247).

`klt pex` runs this command twice -- once on the schematic netlist
(`$KLT_PEX_SIDE=schematic`), once on the netlist it extracted from the layout
(`$KLT_PEX_SIDE=extracted`) -- with the netlist path as the final argument, and
computes every `delta[]` row itself from the two measurement documents printed on
stdout. Phase margin, slew rate and the ICMR window are not single-`.meas`-card
rows, so the testbench mode of `klt pex` cannot express them; this wrapper drives
the existing campaign instead:

    python3 sim/opamp-characterization/bin/pvt_sweep.py \
        --netlist <dut> --fleet --backend batch --analyses ac,tran_sr,dc_swing,icmr

(every unit goes to the Spot batch fleet; no local ngspice grid is ever run) and
maps that campaign's CSV rows into `{"corners": [{"corner_id", "measurements"}]}`.
Each side therefore leaves its own append-only record under ../records/.

The extracted netlist is a `.SUBCKT opamp_core ibias inn inp out vdd vss ...`
with a `.GLOBAL vsubs` card; the benches `.include` the DUT *inside* their own
`.subckt opamp_dut vdd vss inn inp out ibias`, where neither card may appear.
`flatten_dut` therefore drops those cards (the ports are matched by name, so the
extracted header's port order is irrelevant); the substrate node `vsubs` becomes a
local node of the bench subckt, still tied to ground by the netlist's own
`Rvsubs_dctie` card. Nothing else in the netlist is touched.

Measurement names (one per ratified spec row): gain_dc_db, gbw_hz,
phase_margin_deg, sr_rise_v_per_us, sr_fall_v_per_us, vpp_v (output swing),
pq_w (quiescent power), icmr_low_v, icmr_high_v, icmr_width_v. A grid point the
campaign did not return is emitted with `value: null` (an `error` delta row),
never a zero.

Usage (what `klt pex` calls; `--selftest` and `--flatten-only` are for review):

    pex_measure.py [--corners C,..] [--temps T,..] <netlist>
    pex_measure.py --flatten-only <extracted.spice>      # print the adapted DUT
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

EXP_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = EXP_DIR.parent.parent
PVT_SWEEP = EXP_DIR / "bin" / "pvt_sweep.py"
RECORDS_DIR = EXP_DIR / "records"

ANALYSES = "ac,tran_sr,dc_swing,icmr"

# analysis CSV suffix -> measurement columns exported as spec rows
MEASURES = {
    "ac": ("gain_dc_db", "gbw_hz", "phase_margin_deg", "pq_w"),
    "tran-sr": ("sr_rise_v_per_us", "sr_fall_v_per_us"),
    "dc-swing": ("vpp_v",),
    "icmr": ("icmr_low_v", "icmr_high_v", "icmr_width_v"),
}


def flatten_dut(text: str) -> str:
    """Drop the `.SUBCKT`/`.ENDS`/`.GLOBAL` cards so the body can be `.include`d
    inside the bench's own subckt. Netlists without them pass through unchanged."""
    out: list[str] = []
    skipping = False
    for line in text.splitlines():
        if skipping and line.startswith("+"):
            continue
        skipping = False
        card = line.split(None, 1)[0].lower() if line.strip() else ""
        if card in (".subckt", ".global"):
            skipping = True
            continue
        if card == ".ends":
            continue
        out.append(line)
    return "\n".join(out) + "\n"


def corner_id(corner: str, vdd: float, temp: float) -> str:
    return f"{corner}/{vdd:.3f}V/{temp:g}C"


def num(raw: str):
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def read_rows(record_id: str) -> dict[tuple[str, float, float], dict[str, float | None]]:
    """{(corner, temp_c, vdd_v): {measurement: value}} from the record's CSVs."""
    points: dict[tuple[str, float, float], dict[str, float | None]] = {}
    for suffix, names in MEASURES.items():
        path = RECORDS_DIR / f"{record_id}-{suffix}.csv"
        if not path.is_file():
            continue
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                key = (row["corner"], float(row["temp_c"]), float(row["vdd_v"]))
                slot = points.setdefault(key, {})
                for name in names:
                    slot[name] = num(row.get(name))
    return points


def document(points, corners: list[str], temps: list[float], vdd_by_corner: dict[str, float]) -> dict:
    names = [n for ns in MEASURES.values() for n in ns]
    docs = []
    for corner in corners:
        for temp in temps:
            vdd = vdd_by_corner[corner]
            slot = points.get((corner, temp, vdd), {})
            docs.append({
                "corner_id": corner_id(corner, vdd, temp),
                "measurements": [
                    {"name": n, "value": slot.get(n),
                     "status": "pass" if slot.get(n) is not None else "error"}
                    for n in names
                ],
            })
    return {"corners": docs}


def run_campaign(dut: Path, corners: list[str], temps: list[float]) -> str:
    cmd = [sys.executable, "-I", str(PVT_SWEEP), "--netlist", str(dut), "--fleet", "--backend", "batch",
           "--analyses", ANALYSES, f"--corners={','.join(corners)}", f"--temps={','.join(f'{t:g}' for t in temps)}"]
    # stdout belongs to the measurement document; the campaign's chatter goes to stderr
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=sys.stderr, text=True, cwd=REPO_ROOT)
    sys.stderr.write(proc.stdout)
    m = re.search(r"^Wrote record (\S+):", proc.stdout, re.M)
    if not m:
        raise SystemExit(f"pex_measure: pvt_sweep.py wrote no record (exit {proc.returncode}); no measurements to report")
    if proc.returncode:
        print(f"pex_measure: campaign {m.group(1)} had failed points; they are reported as null rows", file=sys.stderr)
    return m.group(1)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("netlist", type=Path)
    p.add_argument("--corners", default="tt,ff,ss,sf,fs")
    p.add_argument("--temps", default="-40,27,125")
    p.add_argument("--flatten-only", action="store_true", help="print the adapted DUT netlist and exit")
    args = p.parse_args(argv)

    text = args.netlist.read_text()
    if args.flatten_only:
        sys.stdout.write(flatten_dut(text))
        return 0

    corners = [c for c in args.corners.split(",") if c]
    temps = [float(t) for t in args.temps.split(",") if t]
    side = os.environ.get("KLT_PEX_SIDE", "schematic")
    art = Path(os.environ.get("KLT_PEX_ARTIFACTS_DIR") or "/tmp") / f"pex-measure-{side}"
    art.mkdir(parents=True, exist_ok=True)
    dut = art / "dut.spice"
    dut.write_text(flatten_dut(text))

    sys.path.insert(0, str(EXP_DIR / "bin"))
    import importlib.util
    spec = importlib.util.spec_from_file_location("pvt_sweep", PVT_SWEEP)
    pvt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pvt)

    record_id = run_campaign(dut, corners, temps)
    print(f"pex_measure: side={side} record={record_id}", file=sys.stderr)
    doc = document(read_rows(record_id), corners, temps, pvt.VDD_BY_CORNER)
    doc["record_id"] = record_id
    json.dump(doc, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
