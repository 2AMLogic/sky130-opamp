#!/usr/bin/env python3
"""gm/ID characterization sweep -- sky130_fd_pr__{nfet,pfet}_01v8 (issue #6).

The single documented cold-start invocation named in ../README.md:

    python3 sim/gm-id-characterization/bin/sweep.py

Regenerates the full evidence set for this experiment from a clean checkout
(given the pinned PDK in ../pdk.json is installed): renders
../testbench/{nfet,pfet}_gmid.spice.tmpl once per (device, corner, length,
temperature) point, drives ngspice -b on each rendered deck, parses its
`wrdata` output, derives gm/ID, gm/gds and fT vs Vov, and writes a new
timestamped, append-only record under ../records/.

Stdlib only -- no third-party Python dependencies, so the only tools this
script itself requires are python3 and ngspice (plus, to resolve the PDK,
either `volare` on PATH or PDK_ROOT/PDK set by hand -- see --check-env).

    --check-env        report tool/PDK availability and exit (no simulation)
    --devices D,D      subset of {nfet,pfet}          (default: both)
    --corners C,C      subset of {tt,ff,ss,sf,fs}      (default: all five)
    --lengths L,L       channel lengths in um           (default: 0.15,0.3,0.6,1.2)
    --temps T,T         temperatures in degC             (default: -40,27,125)
    --vds V             |Vds| bias point, volts          (default: 0.9)
    --width W           device width, um                 (default: 2.0)
    --vstep V           Vgs/Vsg sweep step, volts         (default: 0.02)
    --gmid-targets ...  gm/ID points (1/V) the summary table reports at
                        (default: 20,15,10,5)
    --keep-work         do not delete the scratch ngspice decks/outputs
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

EXP_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = EXP_DIR.parent.parent
PDK_PIN_FILE = EXP_DIR / "pdk.json"
MODEL_FILES = EXP_DIR / "corners" / "model-files.json"
TESTBENCH_DIR = EXP_DIR / "testbench"
RECORDS_DIR = EXP_DIR / "records"
SNAPSHOT_DIR = EXP_DIR / "netlist-snapshots"

DEVICES = ("nfet", "pfet")
DEFAULT_CORNERS = ("tt", "ff", "ss", "sf", "fs")
DEFAULT_LENGTHS_UM = (0.15, 0.3, 0.6, 1.2)
DEFAULT_TEMPS_C = (-40.0, 27.0, 125.0)
DEFAULT_GMID_TARGETS = (20.0, 15.0, 10.0, 5.0)
VDD = 1.8


class HarnessError(RuntimeError):
    pass


# --------------------------------------------------------------------------
# PDK resolution (same shape as sky130-ldo's sim/bin/corner-run.py resolve_pdk,
# adapted to this experiment's own pdk.json, which points at the per-corner
# ngspice include files rather than the combined library -- see
# ../corners/README.md for why).
# --------------------------------------------------------------------------


def load_json(path: Path) -> dict:
    if not path.exists():
        raise HarnessError(f"missing file: {path}")
    return json.loads(path.read_text())


def volare_path() -> Path | None:
    exe = shutil.which("volare")
    if not exe:
        return None
    try:
        out = subprocess.run(
            [exe, "path"], capture_output=True, text=True, timeout=60, check=True
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return None
    return Path(out) if out else None


class Pdk:
    def __init__(self, pin: dict):
        self.pin = pin
        root_env = os.environ.get("PDK_ROOT", "").strip()
        self.root = Path(root_env).expanduser() if root_env else (
            volare_path() or Path(pin["default_pdk_root"]).expanduser()
        )
        self.variant = os.environ.get("PDK", "").strip() or pin["variant"]
        self.dir = self.root / self.variant
        self.corner_dir = self.dir / pin["ngspice_corner_dir"]
        self.installed_commit = self._installed_commit()

    def _installed_commit(self) -> str:
        parts = self.dir.resolve().parts
        if "versions" in parts:
            idx = parts.index("versions")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        return "unknown"

    @property
    def matches_pin(self) -> bool:
        return self.installed_commit == self.pin["open_pdks_commit"]

    def corner_include(self, corner: str) -> Path:
        return self.corner_dir / f"{corner}.spice"

    def validate(self) -> None:
        if not self.dir.is_dir():
            raise HarnessError(
                f"no PDK at {self.dir}\n"
                f"  install the pinned version with: {self.pin['install_command']}\n"
                f"  (or set PDK_ROOT / PDK to an existing install)"
            )
        for corner in DEFAULT_CORNERS:
            inc = self.corner_include(corner)
            if not inc.is_file():
                raise HarnessError(f"missing corner include: {inc}")


def resolve_pdk() -> Pdk:
    pin = load_json(PDK_PIN_FILE)
    pdk = Pdk(pin)
    pdk.validate()
    return pdk


def first_line(cmd: list[str]) -> str:
    exe = shutil.which(cmd[0])
    if not exe:
        return "not found"
    try:
        proc = subprocess.run([exe, *cmd[1:]], capture_output=True, text=True, timeout=60)
    except (subprocess.SubprocessError, OSError) as exc:  # pragma: no cover
        return f"error: {exc}"
    for line in (proc.stdout + "\n" + proc.stderr).splitlines():
        line = line.strip().lstrip("*").strip()
        if line:
            return line
    return "unknown"


def check_env() -> int:
    status = 0
    for tool, flag in (("ngspice", "-v"), ("volare", "--version")):
        exe = shutil.which(tool)
        if exe:
            print(f"{tool:<8}: OK   {first_line([tool, flag])}")
        else:
            print(f"{tool:<8}: MISSING (not on PATH)")
            if tool == "ngspice":
                status = 1
    try:
        pdk = resolve_pdk()
    except HarnessError as exc:
        print(f"PDK     : MISSING\n{exc}")
        return 1
    note = "matches pdk.json pin" if pdk.matches_pin else "MISMATCH vs pdk.json pin"
    print(f"PDK     : OK   {pdk.dir} (open_pdks {pdk.installed_commit}, {note})")
    for corner in DEFAULT_CORNERS:
        print(f"  corner include: {pdk.corner_include(corner)}")
    return status


# --------------------------------------------------------------------------
# Simulation
# --------------------------------------------------------------------------

# Column layout of the shared `save` list in both templates:
# v(g), gm, gds, id, cgg, vth -- each preceded by its own duplicate x-column
# in ngspice `wrdata` output (see ../testbench/*.tmpl header comments).
VALUE_COLS = {"vg": 1, "gm": 3, "gds": 5, "id": 7, "cgg": 9, "vth": 11}


def render(template_path: Path, subs: dict) -> str:
    text = template_path.read_text()
    for key, val in subs.items():
        text = text.replace("{" + key + "}", str(val))
    if "{" in text and "}" in text:
        remaining = {seg.split("}", 1)[0] for seg in text.split("{")[1:] if "}" in seg}
        if remaining:
            raise HarnessError(f"unsubstituted placeholders in {template_path.name}: {remaining}")
    return text


def run_point(ngspice: str, deck_text: str, workdir: Path, out_path: Path, timeout_s: int = 60):
    deck_path = workdir / "tb.spice"
    deck_path.write_text(deck_text)
    start = time.monotonic()
    try:
        proc = subprocess.run(
            [ngspice, "-b", str(deck_path)],
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        raise HarnessError(f"ngspice timed out after {timeout_s}s") from exc
    elapsed = time.monotonic() - start
    if proc.returncode != 0 or not out_path.is_file():
        raise HarnessError(
            f"ngspice failed (exit {proc.returncode}):\n{proc.stdout}\n{proc.stderr}"
        )
    rows = []
    for line in out_path.read_text().splitlines():
        parts = line.split()
        if not parts:
            continue
        rows.append([float(p) for p in parts])
    return rows, elapsed


def derive_points(device: str, rows: list[list[float]], vdd: float):
    """Yield dicts of derived per-Vgs-point quantities for one ngspice run."""
    for row in rows:
        vg = row[VALUE_COLS["vg"]]
        gm = row[VALUE_COLS["gm"]]
        gds = row[VALUE_COLS["gds"]]
        id_ = row[VALUE_COLS["id"]]
        cgg = row[VALUE_COLS["cgg"]]
        vth = row[VALUE_COLS["vth"]]
        overdrive_bias = vg if device == "nfet" else (vdd - vg)
        vov = overdrive_bias - vth
        id_abs = abs(id_)
        gm_id = (gm / id_abs) if id_abs > 1e-13 else None
        gm_gds = (gm / gds) if gds > 1e-15 else None
        ft = (gm / (2 * math.pi * cgg)) if cgg > 1e-18 else None
        yield {
            "overdrive_bias_v": overdrive_bias,
            "vov_v": vov,
            "id_a": id_,
            "gm_s": gm,
            "gds_s": gds,
            "cgg_f": cgg,
            "vth_v": vth,
            "gm_id_per_v": gm_id,
            "gm_gds": gm_gds,
            "ft_hz": ft,
        }


def interp(x_target: float, xs: list[float], ys: list[float]):
    """Linear interpolation; xs assumed monotonically decreasing (gm/ID vs Vov).
    Returns None if x_target is outside the observed [min(xs), max(xs)] range."""
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if not pairs:
        return None
    pairs.sort(key=lambda p: p[0])  # ascending x
    xs_s, ys_s = zip(*pairs)
    if x_target < xs_s[0] or x_target > xs_s[-1]:
        return None
    for i in range(len(xs_s) - 1):
        x0, x1 = xs_s[i], xs_s[i + 1]
        if x0 <= x_target <= x1:
            if x1 == x0:
                return ys_s[i]
            frac = (x_target - x0) / (x1 - x0)
            return ys_s[i] + frac * (ys_s[i + 1] - ys_s[i])
    return None


def git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10, check=True,
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return "unknown"


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--check-env", action="store_true")
    p.add_argument("--devices", default=",".join(DEVICES))
    p.add_argument("--corners", default=",".join(DEFAULT_CORNERS))
    p.add_argument("--lengths", default=",".join(str(x) for x in DEFAULT_LENGTHS_UM))
    p.add_argument("--temps", default=",".join(str(x) for x in DEFAULT_TEMPS_C))
    p.add_argument("--vds", type=float, default=0.9)
    p.add_argument("--width", type=float, default=2.0)
    p.add_argument("--vstep", type=float, default=0.02)
    p.add_argument("--gmid-targets", default=",".join(str(x) for x in DEFAULT_GMID_TARGETS))
    p.add_argument("--keep-work", action="store_true")
    return p.parse_args(argv)


def run_sweep_matrix(args, devices, corners, lengths, temps, pdk, ngspice, workdir, snapshot_run_dir):
    """Render+run every (device, corner, length, temp) point; return (full_rows, n_runs)."""
    full_rows = []  # one row per (device, corner, length, temp, Vgs point)
    n_runs = 0
    saved_snapshot = {"nfet": False, "pfet": False}
    for device in devices:
        template_path = TESTBENCH_DIR / f"{device}_gmid.spice.tmpl"
        for corner in corners:
            corner_include = pdk.corner_include(corner)
            for length in lengths:
                for temp in temps:
                    out_path = workdir / "sweep_out.txt"
                    subs = {
                        "CORNER_INCLUDE": corner_include,
                        "L": length,
                        "W": args.width,
                        "VDD": VDD,
                        "TEMP": temp,
                        "VSTEP": args.vstep,
                        "OUT_FILE": out_path,
                    }
                    if device == "nfet":
                        subs["VDS"] = args.vds
                    else:
                        subs["VDRAIN"] = VDD - args.vds
                    deck_text = render(template_path, subs)
                    rows, elapsed = run_point(ngspice, deck_text, workdir, out_path)
                    n_runs += 1
                    print(
                        f"[{n_runs:>4}] {device:<4} {corner:<2} L={length:>4}um "
                        f"T={temp:>5}C  {len(rows):>3} pts  {elapsed:.2f}s",
                        file=sys.stderr,
                    )
                    if not saved_snapshot[device] and corner == "tt" and length == lengths[0] and temp == 27.0:
                        (snapshot_run_dir / f"{device}_gmid_tt_L{length}_27C.spice").write_text(deck_text)
                        saved_snapshot[device] = True
                    for pt in derive_points(device, rows, VDD):
                        full_rows.append(
                            {
                                "device": device,
                                "corner": corner,
                                "length_um": length,
                                "width_um": args.width,
                                "temp_c": temp,
                                "vds_v": args.vds,
                                **pt,
                            }
                        )
    return full_rows, n_runs


def main(argv=None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if args.check_env:
        return check_env()

    devices = [d.strip() for d in args.devices.split(",") if d.strip()]
    corners = [c.strip() for c in args.corners.split(",") if c.strip()]
    lengths = [float(x) for x in args.lengths.split(",") if x.strip()]
    temps = [float(x) for x in args.temps.split(",") if x.strip()]
    gmid_targets = [float(x) for x in args.gmid_targets.split(",") if x.strip()]

    pdk = resolve_pdk()
    if not pdk.matches_pin:
        print(
            f"WARNING: installed PDK ({pdk.installed_commit}) does not match "
            f"pdk.json pin ({pdk.pin['open_pdks_commit']}) -- proceeding anyway, "
            f"but the resulting record will not be directly comparable to prior ones.",
            file=sys.stderr,
        )

    ngspice = shutil.which("ngspice")
    if not ngspice:
        print("ERROR: ngspice not found on PATH", file=sys.stderr)
        return 1

    model_files = load_json(MODEL_FILES)
    for corner in corners:
        if corner not in model_files["corners"]:
            print(f"ERROR: corner '{corner}' not in {MODEL_FILES}", file=sys.stderr)
            return 1

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    record_id = f"{ts}-{git_sha()}"
    RECORDS_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_run_dir = SNAPSHOT_DIR / record_id
    snapshot_run_dir.mkdir(parents=True, exist_ok=True)

    t_start = time.monotonic()
    if args.keep_work:
        workdir = Path(tempfile.mkdtemp(prefix="gmid-sweep-"))
        print(f"--keep-work: scratch decks/outputs preserved at {workdir}", file=sys.stderr)
        full_rows, n_runs = run_sweep_matrix(
            args, devices, corners, lengths, temps, pdk, ngspice, workdir, snapshot_run_dir
        )
    else:
        with tempfile.TemporaryDirectory(prefix="gmid-sweep-") as tmp:
            full_rows, n_runs = run_sweep_matrix(
                args, devices, corners, lengths, temps, pdk, ngspice, Path(tmp), snapshot_run_dir
            )
    n_points = len(full_rows)
    elapsed_total = time.monotonic() - t_start
    print(f"Completed {n_runs} ngspice runs, {n_points} data points in {elapsed_total:.1f}s", file=sys.stderr)

    # -- full-sweep CSV (the primary evidence artifact) --
    full_csv_path = RECORDS_DIR / f"{record_id}-full-sweep.csv"
    fieldnames = [
        "device", "corner", "length_um", "width_um", "temp_c", "vds_v",
        "overdrive_bias_v", "vov_v", "id_a", "gm_s", "gds_s", "cgg_f", "vth_v",
        "gm_id_per_v", "gm_gds", "ft_hz",
    ]
    with full_csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(full_rows)

    # -- summary CSV: interpolate gm/gds, fT, Vov at fixed gm/ID targets --
    summary_rows = []
    groups: dict[tuple, list[dict]] = {}
    for row in full_rows:
        key = (row["device"], row["corner"], row["length_um"], row["temp_c"])
        groups.setdefault(key, []).append(row)
    for (device, corner, length, temp), pts in sorted(groups.items()):
        gm_id_list = [p["gm_id_per_v"] for p in pts]
        vov_list = [p["vov_v"] for p in pts]
        gm_gds_list = [p["gm_gds"] for p in pts]
        ft_list = [p["ft_hz"] for p in pts]
        for target in gmid_targets:
            vov_at = interp(target, gm_id_list, vov_list)
            gm_gds_at = interp(target, gm_id_list, gm_gds_list)
            ft_at = interp(target, gm_id_list, ft_list)
            summary_rows.append(
                {
                    "device": device,
                    "corner": corner,
                    "length_um": length,
                    "temp_c": temp,
                    "gm_id_target_per_v": target,
                    "vov_v": vov_at,
                    "gm_gds": gm_gds_at,
                    "ft_hz": ft_at,
                }
            )
    summary_csv_path = RECORDS_DIR / f"{record_id}-summary.csv"
    with summary_csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["device", "corner", "length_um", "temp_c", "gm_id_target_per_v", "vov_v", "gm_gds", "ft_hz"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    # -- JSON record (machine-readable metadata + pointers) --
    record = {
        "record_id": record_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git": {"sha": git_sha()},
        "experiment": {
            "slug": "gm-id-characterization",
            "title": "gm/ID, gm/gds and fT vs overdrive for sky130 1.8V-core MOS devices",
            "claim": (
                "gm/ID-first device characterization ahead of topology/sizing work "
                "(porting-plan.md Section 4). NOT a claim about any circuit's spec "
                "row -- these are bare-device sweeps, not a closed-loop testbench."
            ),
        },
        "matrix": {
            "devices": devices,
            "corners": corners,
            "lengths_um": lengths,
            "temps_c": temps,
            "vds_v": args.vds,
            "width_um": args.width,
            "vgs_step_v": args.vstep,
            "n_runs": n_runs,
            "n_points": n_points,
        },
        "pdk": {
            "variant": pdk.variant,
            "root": str(pdk.root),
            "installed_commit": pdk.installed_commit,
            "pinned_commit": pdk.pin["open_pdks_commit"],
            "matches_pin": pdk.matches_pin,
        },
        "tools": {
            "ngspice": first_line(["ngspice", "-v"]),
            "python": platform.python_version(),
            "platform": f"{platform.system()} {platform.release()} {platform.machine()}",
        },
        "links": {
            "full_sweep_csv": f"sim/gm-id-characterization/records/{record_id}-full-sweep.csv",
            "summary_csv": f"sim/gm-id-characterization/records/{record_id}-summary.csv",
            "record_md": f"sim/gm-id-characterization/records/{record_id}.md",
            "netlist_snapshots": f"sim/gm-id-characterization/netlist-snapshots/{record_id}/",
            "corner_model_files": "sim/gm-id-characterization/corners/model-files.json",
        },
        "elapsed_s": round(elapsed_total, 1),
    }
    json_path = RECORDS_DIR / f"{record_id}.json"
    json_path.write_text(json.dumps(record, indent=2) + "\n")

    # -- Markdown record (human-readable) --
    md_lines = [
        f"# gm/ID characterization record `{record_id}`",
        "",
        f"- Timestamp: {record['timestamp']}",
        f"- Git SHA: {record['git']['sha']}",
        f"- PDK: sky130A, open_pdks `{pdk.installed_commit}`"
        + (" (matches pin)" if pdk.matches_pin else " **MISMATCH vs pdk.json pin**"),
        f"- ngspice: {record['tools']['ngspice']}",
        f"- Devices: {', '.join(devices)}  |  Corners: {', '.join(corners)}  |  "
        f"Lengths (um): {', '.join(str(x) for x in lengths)}  |  Temps (C): {', '.join(str(x) for x in temps)}",
        f"- Bias: |Vds| = {args.vds} V, W = {args.width} um, Vgs/Vsg step = {args.vstep} V, VDD = {VDD} V",
        f"- {n_runs} ngspice runs, {n_points} swept data points, {record['elapsed_s']}s wall time",
        "",
        "Full per-point data: "
        f"[`{record_id}-full-sweep.csv`]({record_id}-full-sweep.csv). "
        "Summary interpolated at fixed gm/ID targets: "
        f"[`{record_id}-summary.csv`]({record_id}-summary.csv).",
        "",
        "## Summary at tt / 27C, minimum length",
        "",
        "| gm/ID (1/V) | Vov (V) | gm/gds | fT (GHz) |",
        "|---|---|---|---|",
    ]
    min_len = min(lengths) if lengths else None
    for row in summary_rows:
        if row["device"] == "nfet" and row["corner"] == "tt" and row["length_um"] == min_len and row["temp_c"] == 27.0:
            ft_ghz = f"{row['ft_hz'] / 1e9:.2f}" if row["ft_hz"] is not None else "n/a"
            vov = f"{row['vov_v']:.3f}" if row["vov_v"] is not None else "n/a"
            gg = f"{row['gm_gds']:.1f}" if row["gm_gds"] is not None else "n/a"
            md_lines.append(f"| {row['gm_id_target_per_v']:.0f} | {vov} | {gg} | {ft_ghz} |")
    md_lines += [
        "",
        "(nfet shown above; see the summary CSV for pfet and every corner/length/temp "
        "combination.)",
        "",
        "See `../README.md` for methodology, the Vov definition, and which "
        "`spec/target-spec.md` rows this study feeds.",
    ]
    md_path = RECORDS_DIR / f"{record_id}.md"
    md_path.write_text("\n".join(md_lines) + "\n")

    print(f"Wrote record {record_id}:")
    print(f"  {full_csv_path.relative_to(REPO_ROOT)}")
    print(f"  {summary_csv_path.relative_to(REPO_ROOT)}")
    print(f"  {json_path.relative_to(REPO_ROOT)}")
    print(f"  {md_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
