#!/usr/bin/env python3
"""opamp_core PVT-corner characterization sweep (issue #17).

The single documented cold-start invocation named in ../README.md:

    python3 sim/opamp-characterization/bin/pvt_sweep.py

Regenerates the full evidence set for this experiment from a clean checkout
(given the pinned PDK in ../gm-id-characterization/pdk.json is installed):
renders each of ../testbench/opamp_{ac,tran_sr,dc_swing}.spice.tmpl once per
(corner, temperature) point against `design/netlist/opamp_core.spice`, drives
`ngspice -b` on each rendered deck, parses its `.meas`/`print` output (AC,
transient) or `wrdata` sweep output (DC), and writes a new timestamped,
append-only record under ../records/ plus a raw ngspice log per run under
../records/<record_id>-logs/ and a rendered-deck snapshot per run under
../netlist-snapshots/<record_id>/.

Reuses (does not re-resolve or duplicate) the MOS process-corner model-file
resolution already committed at
../../gm-id-characterization/pdk.json and
../../gm-id-characterization/corners/model-files.json, per this issue's
acceptance criteria. Adds its own ../pdk.json only for the R+C ("typical")
corner choice this experiment introduces (Rz/Cc are not swept by the sibling
bare-MOS-device experiment).

Stdlib only -- no third-party Python dependencies, so the only tools this
script itself requires are python3 and ngspice (plus, to resolve the PDK,
either `volare` on PATH or PDK_ROOT/PDK set by hand -- see --check-env).

    --check-env        report tool/PDK availability and exit (no simulation)
    --corners C,C       subset of {tt,ff,ss,sf,fs}      (default: all five)
    --temps T,T          temperatures in degC             (default: -40,27,125)
    --analyses A,A       subset of {ac,tran_sr,dc_swing}  (default: all three)
    --keep-work         do not delete the scratch ngspice decks/outputs
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

EXP_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = EXP_DIR.parent.parent
GMID_DIR = EXP_DIR.parent / "gm-id-characterization"
GMID_PDK_PIN_FILE = GMID_DIR / "pdk.json"
GMID_MODEL_FILES = GMID_DIR / "corners" / "model-files.json"
OWN_PDK_FILE = EXP_DIR / "pdk.json"
TESTBENCH_DIR = EXP_DIR / "testbench"
RECORDS_DIR = EXP_DIR / "records"
SNAPSHOT_DIR = EXP_DIR / "netlist-snapshots"
DESIGN_NETLIST = REPO_ROOT / "design" / "netlist" / "opamp_core.spice"

DEFAULT_CORNERS = ("tt", "ff", "ss", "sf", "fs")
DEFAULT_TEMPS_C = (-40.0, 27.0, 125.0)
DEFAULT_ANALYSES = ("ac", "tran_sr", "dc_swing")

CL_F = "2p"  # DR-001's CL = 2 pF
IBIAS_A = "5u"  # DR-002 (a): 5 uA external reference into `ibias`

# Corner -> VDD mapping. Matches DR-002 Sec (f)'s own pairing (ss -> 1.62V
# worst-case-low, ff -> 1.98V worst-case-high, tt -> 1.80V nominal,
# per spec/target-spec.md Sec 1). sf/fs have no such named pairing in either
# DR-002 or target-spec.md -- nominal VDD is used for both, a stated
# methodology choice (see ../README.md), not a re-derivation of a
# process/supply correlation this repo has not decided.
VDD_BY_CORNER = {"tt": 1.80, "ff": 1.98, "ss": 1.62, "sf": 1.80, "fs": 1.80}


class HarnessError(RuntimeError):
    pass


# --------------------------------------------------------------------------
# PDK resolution -- reuses ../gm-id-characterization's own pdk.json/
# model-files.json for MOS-corner resolution (same class shape as that
# experiment's bin/sweep.py), plus this experiment's own pdk.json for the
# R+C corner include files.
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
    def __init__(self, pin: dict, own_pin: dict):
        self.pin = pin
        self.own_pin = own_pin
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

    def rc_includes(self) -> list[Path]:
        return [self.dir / rel for rel in self.own_pin["rc_corner"]["include_files"]]

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
        for inc in self.rc_includes():
            if not inc.is_file():
                raise HarnessError(f"missing R+C corner include: {inc}")


def resolve_pdk() -> Pdk:
    pin = load_json(GMID_PDK_PIN_FILE)
    own_pin = load_json(OWN_PDK_FILE)
    pdk = Pdk(pin, own_pin)
    pdk.validate()
    return pdk


def first_line(cmd: list[str]) -> str:
    exe = shutil.which(cmd[0])
    if not exe:
        return "not found"
    try:
        proc = subprocess.run([exe, *cmd[1:]], capture_output=True, text=True, timeout=60)
    except (subprocess.SubprocessError, OSError):  # pragma: no cover
        return "error"
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
    if not DESIGN_NETLIST.is_file():
        print(f"netlist : MISSING {DESIGN_NETLIST}")
        return 1
    print(f"netlist : OK   {DESIGN_NETLIST}")
    try:
        pdk = resolve_pdk()
    except HarnessError as exc:
        print(f"PDK     : MISSING\n{exc}")
        return 1
    note = "matches pdk.json pin" if pdk.matches_pin else "MISMATCH vs pdk.json pin"
    print(f"PDK     : OK   {pdk.dir} (open_pdks {pdk.installed_commit}, {note})")
    for corner in DEFAULT_CORNERS:
        print(f"  MOS corner include: {pdk.corner_include(corner)}")
    for inc in pdk.rc_includes():
        print(f"  R+C corner include: {inc}")
    return status


# --------------------------------------------------------------------------
# Rendering + running
# --------------------------------------------------------------------------


def render(template_path: Path, subs: dict) -> str:
    text = template_path.read_text()
    for key, val in subs.items():
        text = text.replace("{" + key + "}", str(val))
    if "{" in text and "}" in text:
        remaining = {seg.split("}", 1)[0] for seg in text.split("{")[1:] if "}" in seg}
        if remaining:
            raise HarnessError(f"unsubstituted placeholders in {template_path.name}: {remaining}")
    return text


MEAS_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([-+0-9.eE]+)")


def parse_meas(stdout: str) -> dict[str, float]:
    """Parse every `name = value ...` line ngspice's .meas/print emit to stdout.

    `.meas ... trig ... targ ...` lines print extra `targ=... trig=...`
    trailer text after the primary value -- match only the leading
    `name = value` token, not the whole line, so those lines still parse.
    """
    out: dict[str, float] = {}
    for line in stdout.splitlines():
        m = MEAS_RE.match(line.strip())
        if m:
            try:
                out[m.group(1)] = float(m.group(2))
            except ValueError:
                continue
    return out


def run_ngspice(ngspice: str, deck_text: str, workdir: Path, log_path: Path, timeout_s: int = 120):
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
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        f"$ ngspice -b {deck_path.name}\n\n--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}\n"
    )
    if proc.returncode != 0:
        raise HarnessError(f"ngspice failed (exit {proc.returncode}) -- see {log_path}")
    return proc.stdout, elapsed


def git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10, check=True,
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return "unknown"


# --------------------------------------------------------------------------
# Per-analysis run + parse
# --------------------------------------------------------------------------


def common_subs(pdk: Pdk, corner: str, temp: float, vdd: float) -> dict:
    rc = pdk.rc_includes()
    return {
        "CORNER_INCLUDE": pdk.corner_include(corner),
        "RC_INCLUDE_BASE": rc[0],
        "RC_INCLUDE_LIN": rc[1],
        "OPAMP_NETLIST": DESIGN_NETLIST,
        "TEMP": temp,
        "VDD": vdd,
        "IBIAS_A": IBIAS_A,
        "CL_F": CL_F,
    }


def run_ac(pdk, ngspice, corner, temp, workdir, log_path):
    vdd = VDD_BY_CORNER[corner]
    vcm = 0.5 * vdd
    subs = common_subs(pdk, corner, temp, vdd)
    subs.update({
        "VCM": vcm,
        "RFB": "1e12",
        "CFB": "1",
        "FSTART": "1",
        "FSTOP": "1g",
        "PTS_PER_DEC": "20",
    })
    deck = render(TESTBENCH_DIR / "opamp_ac.spice.tmpl", subs)
    stdout, elapsed = run_ngspice(ngspice, deck, workdir, log_path)
    meas = parse_meas(stdout)
    for key in ("iq_a", "pq_w", "gain_dc_db", "gbw_hz", "phase_at_gbw_rad"):
        if key not in meas:
            raise HarnessError(f"ac[{corner}/{temp}C]: missing measurement '{key}' -- see {log_path}")
    phase_at_gbw_deg = math.degrees(meas["phase_at_gbw_rad"])
    phase_margin_deg = 180.0 + phase_at_gbw_deg  # gbw phase is negative for a stable 2-pole system
    row = {
        "corner": corner, "temp_c": temp, "vdd_v": vdd, "vcm_v": vcm,
        "iq_a": meas["iq_a"], "pq_w": meas["pq_w"],
        "gain_dc_db": meas["gain_dc_db"], "gbw_hz": meas["gbw_hz"],
        "phase_at_gbw_deg": phase_at_gbw_deg, "phase_margin_deg": phase_margin_deg,
        "elapsed_s": round(elapsed, 2),
    }
    return row, deck


def run_tran_sr(pdk, ngspice, corner, temp, workdir, log_path):
    vdd = VDD_BY_CORNER[corner]
    v_lo = 0.5 * vdd - 0.2 * vdd
    v_hi = 0.5 * vdd + 0.2 * vdd
    span = v_hi - v_lo
    v20 = v_lo + 0.2 * span
    v80 = v_lo + 0.8 * span
    subs = common_subs(pdk, corner, temp, vdd)
    subs.update({
        "V_LOW": v_lo, "V_HIGH": v_hi, "V20": v20, "V80": v80,
        "T_DELAY": "200n", "T_EDGE": "1n", "T_PW": "1u", "T_PER": "2u",
        "T_STEP": "2n", "T_STOP": "2.2u",
    })
    deck = render(TESTBENCH_DIR / "opamp_tran_sr.spice.tmpl", subs)
    stdout, elapsed = run_ngspice(ngspice, deck, workdir, log_path)
    meas = parse_meas(stdout)
    for key in ("sr_rise_s", "sr_fall_s"):
        if key not in meas:
            raise HarnessError(f"tran_sr[{corner}/{temp}C]: missing measurement '{key}' -- see {log_path}")
    sr_rise_v_per_s = 0.6 * span / meas["sr_rise_s"]
    sr_fall_v_per_s = 0.6 * span / meas["sr_fall_s"]
    row = {
        "corner": corner, "temp_c": temp, "vdd_v": vdd,
        "v_low_v": v_lo, "v_high_v": v_hi,
        "sr_rise_v_per_us": sr_rise_v_per_s / 1e6, "sr_fall_v_per_us": sr_fall_v_per_s / 1e6,
        "elapsed_s": round(elapsed, 2),
    }
    return row, deck


def run_dc_swing(pdk, ngspice, corner, temp, workdir, log_path):
    vdd = VDD_BY_CORNER[corner]
    vstep = vdd / 360.0
    out_path = workdir / "dc_out.txt"
    subs = common_subs(pdk, corner, temp, vdd)
    subs.update({"VSTEP": vstep, "OUT_FILE": out_path})
    deck = render(TESTBENCH_DIR / "opamp_dc_swing.spice.tmpl", subs)
    _stdout, elapsed = run_ngspice(ngspice, deck, workdir, log_path)
    if not out_path.is_file():
        raise HarnessError(f"dc_swing[{corner}/{temp}C]: missing sweep output -- see {log_path}")
    vin, vout = [], []
    for line in out_path.read_text().splitlines():
        parts = line.split()
        if not parts:
            continue
        vin.append(float(parts[1]))
        vout.append(float(parts[3]))
    if len(vin) < 3:
        raise HarnessError(f"dc_swing[{corner}/{temp}C]: too few sweep points -- see {log_path}")

    # Find the largest contiguous run around mid-supply where the local
    # slope d(vout)/d(vin) stays within [0.8, 1.2] of unity -- see
    # ../testbench/opamp_dc_swing.spice.tmpl's header for the rationale.
    n = len(vin)
    slopes = [(vout[i + 1] - vout[i]) / (vin[i + 1] - vin[i]) if vin[i + 1] != vin[i] else 0.0
              for i in range(n - 1)]
    center = min(range(n), key=lambda i: abs(vin[i] - 0.5 * vdd))
    lo = center
    while lo > 0 and 0.8 <= slopes[min(lo - 1, len(slopes) - 1)] <= 1.2:
        lo -= 1
    hi = center
    while hi < n - 1 and 0.8 <= slopes[min(hi, len(slopes) - 1)] <= 1.2:
        hi += 1
    vout_min, vout_max = vout[lo], vout[hi]
    row = {
        "corner": corner, "temp_c": temp, "vdd_v": vdd,
        "vout_min_v": vout_min, "vout_max_v": vout_max,
        "vpp_v": vout_max - vout_min,
        "vpp_pct_of_vdd": 100.0 * (vout_max - vout_min) / vdd,
        "sweep_vout_min_v": min(vout), "sweep_vout_max_v": max(vout),
        "elapsed_s": round(elapsed, 2),
    }
    return row, deck


ANALYSES = {"ac": run_ac, "tran_sr": run_tran_sr, "dc_swing": run_dc_swing}
FIELDNAMES = {
    "ac": ["corner", "temp_c", "vdd_v", "vcm_v", "iq_a", "pq_w", "gain_dc_db",
           "gbw_hz", "phase_at_gbw_deg", "phase_margin_deg", "elapsed_s"],
    "tran_sr": ["corner", "temp_c", "vdd_v", "v_low_v", "v_high_v",
                "sr_rise_v_per_us", "sr_fall_v_per_us", "elapsed_s"],
    "dc_swing": ["corner", "temp_c", "vdd_v", "vout_min_v", "vout_max_v", "vpp_v",
                 "vpp_pct_of_vdd", "sweep_vout_min_v", "sweep_vout_max_v", "elapsed_s"],
}


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--check-env", action="store_true")
    p.add_argument("--corners", default=",".join(DEFAULT_CORNERS))
    p.add_argument("--temps", default=",".join(str(t) for t in DEFAULT_TEMPS_C))
    p.add_argument("--analyses", default=",".join(DEFAULT_ANALYSES))
    p.add_argument("--keep-work", action="store_true")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if args.check_env:
        return check_env()

    corners = [c.strip() for c in args.corners.split(",") if c.strip()]
    temps = [float(t) for t in args.temps.split(",") if t.strip()]
    analyses = [a.strip() for a in args.analyses.split(",") if a.strip()]
    for a in analyses:
        if a not in ANALYSES:
            print(f"ERROR: unknown analysis '{a}' (choices: {sorted(ANALYSES)})", file=sys.stderr)
            return 1

    if not DESIGN_NETLIST.is_file():
        print(f"ERROR: missing netlist under test: {DESIGN_NETLIST}", file=sys.stderr)
        return 1

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

    model_files = load_json(GMID_MODEL_FILES)
    for corner in corners:
        if corner not in model_files["corners"]:
            print(f"ERROR: corner '{corner}' not in {GMID_MODEL_FILES}", file=sys.stderr)
            return 1

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    record_id = f"{ts}-{git_sha()}"
    RECORDS_DIR.mkdir(parents=True, exist_ok=True)
    log_dir = RECORDS_DIR / f"{record_id}-logs"
    snapshot_run_dir = SNAPSHOT_DIR / record_id
    snapshot_run_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, list[dict]] = {a: [] for a in analyses}
    errors: list[str] = []
    n_runs = 0
    t_start = time.monotonic()

    def do_matrix(workdir: Path):
        nonlocal n_runs
        for analysis in analyses:
            fn = ANALYSES[analysis]
            for corner in corners:
                for temp in temps:
                    tag = f"{analysis}-{corner}-{temp:g}C"
                    log_path = log_dir / f"{tag}.log"
                    try:
                        row, deck = fn(pdk, ngspice, corner, temp, workdir, log_path)
                        (snapshot_run_dir / f"{tag}.spice").write_text(deck)
                        results[analysis].append(row)
                        n_runs += 1
                        print(f"[{n_runs:>3}] {tag:<24} OK   {row.get('elapsed_s', 0):.1f}s", file=sys.stderr)
                    except HarnessError as exc:
                        n_runs += 1
                        errors.append(f"{tag}: {exc}")
                        print(f"[{n_runs:>3}] {tag:<24} FAIL {exc}", file=sys.stderr)

    if args.keep_work:
        workdir = Path(tempfile.mkdtemp(prefix="opamp-pvt-"))
        print(f"--keep-work: scratch decks/outputs preserved at {workdir}", file=sys.stderr)
        do_matrix(workdir)
    else:
        with tempfile.TemporaryDirectory(prefix="opamp-pvt-") as tmp:
            do_matrix(Path(tmp))

    elapsed_total = time.monotonic() - t_start
    print(f"Completed {n_runs} ngspice runs ({len(errors)} failed) in {elapsed_total:.1f}s", file=sys.stderr)

    written = []
    for analysis, rows in results.items():
        if not rows:
            continue
        csv_path = RECORDS_DIR / f"{record_id}-{analysis.replace('_', '-')}.csv"
        with csv_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES[analysis], lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        written.append(csv_path)

    record = {
        "record_id": record_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git": {"sha": git_sha()},
        "experiment": {
            "slug": "opamp-characterization",
            "title": "opamp_core PVT-corner open-loop AC / slew-rate / output-swing bench",
            "claim": (
                "Op-amp-level (not bare-device) closed-loop/open-loop AC and transient "
                "measurements of design/netlist/opamp_core.spice against DR-002's "
                "schematic-level sizing estimates, over the confirmed 5-corner MOS grid "
                "at -40/27/125 C."
            ),
        },
        "matrix": {
            "corners": corners, "temps_c": temps, "analyses": analyses,
            "vdd_by_corner": VDD_BY_CORNER, "cl_f": CL_F, "ibias_a": IBIAS_A,
            "n_runs": n_runs, "n_failed": len(errors),
        },
        "pdk": {
            "variant": pdk.variant, "root": str(pdk.root),
            "installed_commit": pdk.installed_commit,
            "pinned_commit": pdk.pin["open_pdks_commit"],
            "matches_pin": pdk.matches_pin,
            "rc_corner": pdk.own_pin["rc_corner"]["choice"],
        },
        "tools": {
            "ngspice": first_line(["ngspice", "-v"]),
            "python": platform.python_version(),
            "platform": f"{platform.system()} {platform.release()} {platform.machine()}",
        },
        "links": {
            f"{a}_csv": f"sim/opamp-characterization/records/{record_id}-{a.replace('_', '-')}.csv"
            for a in results if results[a]
        },
        "errors": errors,
        "elapsed_s": round(elapsed_total, 1),
    }
    json_path = RECORDS_DIR / f"{record_id}.json"
    json_path.write_text(json.dumps(record, indent=2) + "\n")

    print(f"Wrote record {record_id}:")
    for p in written:
        print(f"  {p.relative_to(REPO_ROOT)}")
    print(f"  {json_path.relative_to(REPO_ROOT)}")
    print(f"  {log_dir.relative_to(REPO_ROOT)}/ ({n_runs} raw ngspice logs)")
    print(f"  {snapshot_run_dir.relative_to(REPO_ROOT)}/ (rendered deck snapshots)")

    if errors:
        print(f"\n{len(errors)} run(s) FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
