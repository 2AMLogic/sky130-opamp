#!/usr/bin/env python3
"""opamp_core PSRR+/PSRR- and input-referred-noise PVT sweep (issue #54).

Cold-start invocation (documented in ../README.md):

    python3 sim/opamp-characterization/bin/psrr_noise_sweep.py

Unlike ../bin/pvt_sweep.py (which drives `ngspice -b` itself, one run at a
time), this runner expresses each bench as a `klt sim` corner-matrix request
and lets `klt sim` pick the backend. On a fleet dispatch host
`$KLT_SIM_BACKEND=batch` sends the 45-corner grids to the Spot batch fleet;
pass `--backend local` for a debug probe on a subset (`--corners ss --temps
125`). This script never hand-parallelises ngspice and never falls back to
a local run if a batch submit fails: it exits non-zero and records nothing.

Three benches (circuit bodies under ../testbench/):

    psrr_vdd   AC 1 on the vdd source, unity-gain buffer  -> PSRR+
    psrr_vss   AC 1 on the vss source, unity-gain buffer  -> PSRR-
    noise      .noise v(out) Vinp, unity-gain buffer      -> input-referred noise

each over the same 5-corner x 3-temperature grid as pvt_sweep.py, with the
same corner->VDD pairing (tt/sf/fs 1.80 V, ss 1.62 V, ff 1.98 V).

Records (append-only; a new timestamped set per run, never overwritten):

    records/<id>-psrr-vdd.csv  records/<id>-psrr-vss.csv  records/<id>-noise.csv
    records/<id>-<bench>.klt.json      the unmodified `klt sim` response
    records/<id>-psrr-noise.json/.md   metadata (backend, remote job ids, pins)
    records/<id>-psrr-noise-logs/      per-corner ngspice log (when returned)
    netlist-snapshots/<id>-psrr-noise/ per-corner generated deck (when returned)

    --check-env       report tool availability and exit
    --dry-run         write the three request files to a scratch dir and exit
    --benches B,B     subset of {psrr_vdd,psrr_vss,noise}
    --corners C,C     subset of {tt,ff,ss,sf,fs}
    --temps T,T       degC (default -40,27,125)
    --backend NAME    forwarded to `klt sim --backend` (default: leave to
                      $KLT_SIM_BACKEND / request / local)
    --label TEXT      free-text label stored in the record (e.g. 'debug probe')
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import platform
import shlex
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

EXP_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = EXP_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "sim" / "lib"))
from spice_harness import git_sha  # noqa: E402

TESTBENCH_DIR = EXP_DIR / "testbench"
RECORDS_DIR = EXP_DIR / "records"
SNAPSHOT_DIR = EXP_DIR / "netlist-snapshots"

DEFAULT_CORNERS = ("tt", "ff", "ss", "sf", "fs")
DEFAULT_TEMPS_C = (-40.0, 27.0, 125.0)
VDD_BY_CORNER = {"tt": 1.80, "ff": 1.98, "ss": 1.62, "sf": 1.80, "fs": 1.80}

# Frequency grid: `dec PPD F0 F1`. Index k <-> f = F0 * 10**(k/PPD).
PPD = 20
F0_HZ = 0.1
F1_HZ = 1e9
N_PTS = int(round(PPD * math.log10(F1_HZ / F0_HZ))) + 1  # 201
CURVE_STEP = 5  # report every 5th index -> 4 points/decade
CURVE_IDX = list(range(0, N_PTS, CURVE_STEP))
# `.meas ... find at=<f>` rejects the very last grid point (rounding puts it a
# hair outside the sweep), so the PSRR curve stops one step short of 1 GHz.
PSRR_CURVE_IDX = [k for k in CURVE_IDX if k < N_PTS - 1]


def idx_of(freq_hz: float) -> int:
    k = round(PPD * math.log10(freq_hz / F0_HZ))
    assert abs(F0_HZ * 10 ** (k / PPD) - freq_hz) < 1e-9 * freq_hz
    return k


def freq_of(k: int) -> float:
    return F0_HZ * 10 ** (k / PPD)


# Consumer-imposed PSRR window (bandgap's PSRR row, DC-1 kHz) and the spec's
# proposed noise band (spec/target-spec.md Sec 2: 100 Hz - 1 MHz).
PSRR_WIN_HI_IDX = idx_of(1e3)
NOISE_LO_IDX = idx_of(1e2)
NOISE_HI_IDX = idx_of(1e6)
FLOOR_LO_IDX = idx_of(1e5)  # white-floor proxy: minimum spot density over
FLOOR_HI_IDX = idx_of(1e7)  # 100 kHz - 10 MHz (below the closed-loop peaking)

BENCHES = {
    "psrr_vdd": {"netlist": "psrr_vdd.cir", "kind": "ac", "tag": "psrr-vdd"},
    "psrr_vss": {"netlist": "psrr_vss.cir", "kind": "ac", "tag": "psrr-vss"},
    "noise": {"netlist": "noise.cir", "kind": "noise", "tag": "noise"},
}


def measurements(bench: str) -> list[dict]:
    m: list[dict] = []
    if bench.startswith("psrr"):
        # Supply-to-output gain in dB, closed-loop unity gain: PSRR = -gain.
        # `.meas` cards (not `expr`) on purpose: they are understood by every
        # klt runner version the batch fleet has shipped (klt 0.5.0 rejects
        # `measurements[].expr` outright -- klayout-tools#2877).
        for k in PSRR_CURVE_IDX:
            m.append({
                "name": f"avs_k{k:03d}",
                "spice": f".meas ac avs_k{k:03d} find vdb(out) at={freq_of(k):.10g}",
                "unit": "dB",
            })
        m.append({
            "name": "avs_win_max",
            "spice": f".meas ac avs_win_max max vdb(out) from={F0_HZ:g} to=1k",
            "unit": "dB",
        })
    else:
        for k in CURVE_IDX:
            m.append({"name": f"en_k{k:03d}", "expr": f"noise1.inoise_spectrum[{k}]", "unit": "V/rtHz"})
        lo, hi = NOISE_LO_IDX, NOISE_HI_IDX
        n = hi - lo + 1
        s = "noise1.inoise_spectrum"
        f = "noise1.frequency"
        # Trapezoid in ln f of S^2 * f (the integrand of the PSD integral on a
        # log grid), cross-checked against ngspice's own inoise_total on a
        # band-limited run (see README).
        integrand_body = f"mean({s}[{lo},{hi}]^2 * mag({f}[{lo},{hi}])) * {n}"
        edge = (
            f"0.5 * {s}[{lo}]^2 * mag({f}[{lo}]) + 0.5 * {s}[{hi}]^2 * mag({f}[{hi}])"
        )
        m.append({
            "name": "vn_int_band",
            "expr": f"sqrt(ln(10) / {PPD} * ({integrand_body} - ({edge})))",
            "unit": "V",
        })
    return m


def build_request(bench: str, corners: list[str], temps: list[float], netlist_rel: str,
                  keep_artifacts: bool, runner_version_check: str | None = None) -> dict:
    spec = BENCHES[bench]
    supplies = sorted({VDD_BY_CORNER[c] for c in corners})
    exclude = []
    for c in corners:
        for v in supplies:
            if v != VDD_BY_CORNER[c]:
                exclude.append({"process": c, "supply_v": {"vdd": v}})
    if spec["kind"] == "ac":
        analysis = {"kind": "ac", "args": f"dec {PPD} {F0_HZ:g} {F1_HZ:g}"}
    else:
        analysis = {"kind": "noise", "args": f"v(out) Vinp dec {PPD} {F0_HZ:g} {F1_HZ:g}"}
    options = {"timeout_s": 600, "keep_artifacts": keep_artifacts}
    if spec["kind"] == "noise":
        options["ngspice_init"] = ["set numdgt=8"]
    req = {
        "netlist": netlist_rel,
        "netlist_source": "schematic",
        "models": {"pdk": "sky130A", "lib": "libs.tech/ngspice/sky130.lib.spice"},
        "corners": {
            "process": corners,
            "supply_v": {"vdd": supplies},
            "temperature_c": temps,
        },
        "exclude": exclude,
        "analysis": analysis,
        "measurements": measurements(bench),
        "options": options,
    }
    if runner_version_check:
        req["batch"] = {"runner_version_check": runner_version_check}
    return req


# `klt` may be overridden (e.g. KLT_CMD='uvx --from klayout-tools==0.5.0 klt') to
# match the batch fleet runner's klt version without touching the host install.
KLT_CMD = shlex.split(os.environ.get("KLT_CMD", "klt"))


def run_klt(request_path: Path, outdir: Path, backend: str | None) -> tuple[int, dict | None, str]:
    cmd = [*KLT_CMD, "sim", str(request_path), "-o", str(outdir), "--format", "json"]
    if backend:
        cmd += ["--backend", backend]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = None
    return proc.returncode, payload, proc.stderr


def num(corner: dict, name: str):
    for m in corner["measurements"]:
        if m["name"] == name:
            return m["value"]
    return None


def log_interp_crossing(freqs: list[float], psd: list[float], level: float) -> float | None:
    """Highest frequency at which psd falls through `level` going up in f
    (log-log interpolation); None if the curve never crosses."""
    for i in range(len(freqs) - 1):
        a, b = psd[i], psd[i + 1]
        if a >= level > b:
            t = (math.log(a) - math.log(level)) / (math.log(a) - math.log(b))
            return 10 ** (math.log10(freqs[i]) + t * (math.log10(freqs[i + 1]) - math.log10(freqs[i])))
    return None


def corner_rows(bench: str, payload: dict) -> tuple[list[dict], list[str]]:
    rows, fields = [], []
    for c in payload["corners"]:
        base = {
            "corner": c["process"], "temp_c": c["temperature_c"],
            "vdd_v": c["supply_v"].get("vdd"), "status": c["status"],
        }
        if bench.startswith("psrr"):
            curve = {k: num(c, f"avs_k{k:03d}") for k in PSRR_CURVE_IDX}
            win = num(c, "avs_win_max")
            row = dict(base)
            row["psrr_dc_0p1hz_db"] = -curve[0] if curve[0] is not None else None
            row["psrr_1khz_db"] = -curve[PSRR_WIN_HI_IDX] if curve[PSRR_WIN_HI_IDX] is not None else None
            row["psrr_window_min_db"] = -win if win is not None else None
            for k in PSRR_CURVE_IDX:
                row[f"psrr_db@{freq_of(k):.4g}Hz"] = -curve[k] if curve[k] is not None else None
        else:
            spot = {k: num(c, f"en_k{k:03d}") for k in CURVE_IDX}
            row = dict(base)
            row["vn_int_100hz_1mhz_uvrms"] = (
                num(c, "vn_int_band") * 1e6 if num(c, "vn_int_band") is not None else None
            )
            floor_pts = [spot[k] for k in CURVE_IDX if FLOOR_LO_IDX <= k <= FLOOR_HI_IDX]
            floor = min(floor_pts) if floor_pts and all(v is not None for v in floor_pts) else None
            row["en_floor_nv_rthz"] = floor * 1e9 if floor is not None else None
            corner_hz = None
            if all(v is not None for v in spot.values()) and floor:
                corner_hz = log_interp_crossing(
                    [freq_of(k) for k in CURVE_IDX], [spot[k] for k in CURVE_IDX], math.sqrt(2.0) * floor
                )
            row["f_1overf_corner_hz"] = corner_hz
            for k in CURVE_IDX:
                row[f"en_nv_rthz@{freq_of(k):.4g}Hz"] = spot[k] * 1e9 if spot[k] is not None else None
        rows.append(row)
        fields = list(row)
    return rows, fields


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    def fmt(v):
        if isinstance(v, float):
            return f"{v:.6g}"
        return "" if v is None else v

    with path.open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(fields)
        for r in rows:
            w.writerow([fmt(r[k]) for k in fields])


def check_env() -> int:
    ok = 0
    for tool in ("klt", "ngspice"):
        p = shutil.which(tool)
        print(f"{tool:8}: {'OK   ' + p if p else 'MISSING'}")
        ok |= 0 if p else 1
    print(f"backend : $KLT_SIM_BACKEND={os.environ.get('KLT_SIM_BACKEND', '(unset -> local)')}")
    print("klt     :", subprocess.run([*KLT_CMD, "--version"], capture_output=True, text=True).stdout.strip())
    return ok


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--check-env", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--benches", default=",".join(BENCHES))
    p.add_argument("--corners", default=",".join(DEFAULT_CORNERS))
    p.add_argument("--temps", default=",".join(f"{t:g}" for t in DEFAULT_TEMPS_C))
    p.add_argument("--backend", default=None)
    p.add_argument("--label", default="")
    p.add_argument("--runner-version-check", choices=("enforce", "warn"), default=None,
                   help="forwarded as batch.runner_version_check (batch backend only)")
    p.add_argument("--allow-errors", action="store_true",
                   help="record a bench even if some corners errored (default: write nothing)")
    args = p.parse_args(argv)

    if args.check_env:
        return check_env()

    benches = [b.strip() for b in args.benches.split(",") if b.strip()]
    corners = [c.strip() for c in args.corners.split(",") if c.strip()]
    temps = [float(t) for t in args.temps.split(",") if t.strip()]
    for b in benches:
        if b not in BENCHES:
            print(f"ERROR: unknown bench '{b}' (choices: {sorted(BENCHES)})", file=sys.stderr)
            return 1
    for c in corners:
        if c not in VDD_BY_CORNER:
            print(f"ERROR: unknown corner '{c}'", file=sys.stderr)
            return 1
    if not shutil.which(KLT_CMD[0]):
        print(f"ERROR: {KLT_CMD[0]} not found on PATH", file=sys.stderr)
        return 1

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    sha = git_sha(REPO_ROOT)
    record_id = f"{ts}-{sha}"

    # Requests live in a scratch dir during the run but reference the committed
    # testbench by relative path; the request JSON itself is committed as the
    # record (records/<id>-<bench>.request.json) with a path relative to there.
    with tempfile.TemporaryDirectory(prefix="opamp-psrr-noise-") as tmp:
        tmpdir = Path(tmp)
        results: dict[str, dict] = {}
        failures: list[str] = []
        prepared: dict[str, tuple[dict, Path, Path]] = {}
        for bench in benches:
            netlist_abs = TESTBENCH_DIR / BENCHES[bench]["netlist"]
            req = build_request(bench, corners, temps, str(netlist_abs), keep_artifacts=True,
                                runner_version_check=args.runner_version_check)
            req_path = tmpdir / f"{bench}.request.json"
            req_path.write_text(json.dumps(req, indent=2) + "\n")
            if args.dry_run:
                print(f"{req_path} ({len(req['measurements'])} measurements)")
                shutil.copy(req_path, Path(tempfile.gettempdir()) / req_path.name)
                continue
            prepared[bench] = (req, req_path, tmpdir / f"out-{bench}")
        if args.dry_run:
            return 0

        # One `klt sim` per bench. They are submitted concurrently only because
        # each is a thin client waiting on its own backend job (the batch fleet
        # does the ngspice work); no ngspice runs on this host unless the
        # backend is `local`, in which case they are run one at a time.
        backend_label = args.backend or os.environ.get("KLT_SIM_BACKEND") or "local"

        def submit(bench):
            req, req_path, outdir = prepared[bench]
            print(f"[{bench}] klt sim ({backend_label}) ...", file=sys.stderr, flush=True)
            return bench, run_klt(req_path, outdir, args.backend)

        workers = 1 if backend_label.startswith("local") else len(prepared)
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            outcomes = list(pool.map(submit, prepared))
        for bench, (rc, payload, err) in outcomes:
            req, _req_path, outdir = prepared[bench]
            if payload is None or "corners" not in payload:
                msg = (payload or {}).get("error", {}).get("message") if payload else err.strip()[-500:]
                failures.append(f"{bench}: klt sim produced no report (exit {rc}): {msg}")
                print(f"[{bench}] FAILED: {msg}", file=sys.stderr)
                continue
            print(f"[{bench}] status={payload['status']} corners={payload['corner_count']} "
                  f"pass={payload['passed']} err={payload['errored']}", file=sys.stderr)
            if payload["errored"] and not args.allow_errors:
                diag = next((d for c in payload["corners"] for d in c["diagnostics"]), {})
                failures.append(f"{bench}: {payload['errored']} errored corner(s), e.g. "
                                f"{diag.get('code')}: {str(diag.get('message'))[:400]}")
                continue
            results[bench] = {"request": req, "payload": payload, "outdir": outdir}
        if failures or not results:
            # Do NOT fall back to a local grid and do not write a partial record.
            print("\nNo record written. Failures:", file=sys.stderr)
            for f in failures:
                print(f"  - {f}", file=sys.stderr)
            return 1

        RECORDS_DIR.mkdir(parents=True, exist_ok=True)
        log_dir = RECORDS_DIR / f"{record_id}-psrr-noise-logs"
        snap_dir = SNAPSHOT_DIR / f"{record_id}-psrr-noise"
        written, meta_benches, any_bad = [], {}, False
        for bench, res in results.items():
            payload, tag = res["payload"], BENCHES[bench]["tag"]
            rows, fields = corner_rows(bench, payload)
            csv_path = RECORDS_DIR / f"{record_id}-{tag}.csv"
            write_csv(csv_path, rows, fields)
            written.append(csv_path)
            req_rec = dict(res["request"])
            req_rec["netlist"] = f"../testbench/{BENCHES[bench]['netlist']}"
            (RECORDS_DIR / f"{record_id}-{tag}.request.json").write_text(json.dumps(req_rec, indent=2) + "\n")
            (RECORDS_DIR / f"{record_id}-{tag}.klt.json").write_text(json.dumps(payload, indent=2) + "\n")
            n_art = 0
            for c in payload["corners"]:
                art = c.get("artifacts") or {}
                cid = c["corner_id"].replace("/", "_")
                for kind, dest_dir, suffix in (("log", log_dir, "log"), ("deck", snap_dir, "spice")):
                    src = art.get(kind)
                    if src and Path(src).is_file():
                        dest_dir.mkdir(parents=True, exist_ok=True)
                        shutil.copy(src, dest_dir / f"{tag}-{cid}.{suffix}")
                        n_art += 1
            remote = (payload.get("environment") or {}).get("remote")
            meta_benches[bench] = {
                "status": payload["status"], "corner_count": payload["corner_count"],
                "passed": payload["passed"], "failed": payload["failed"], "errored": payload["errored"],
                "inconclusive": payload.get("inconclusive"),
                "engine_version": (payload.get("environment") or {}).get("engine_version"),
                "backend_remote": remote,
                "artifacts_copied": n_art,
                "csv": f"sim/opamp-characterization/records/{csv_path.name}",
            }
            any_bad |= payload["status"] not in ("pass", "pass_partial")

        meta = {
            "record_id": record_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "git": {"sha": sha},
            "label": args.label,
            "experiment": {
                "slug": "opamp-characterization/psrr-noise",
                "claim": "Pre-layout (schematic netlist) PSRR+/PSRR- and input-referred noise of "
                         "design/netlist/opamp_core.spice over the 5-corner x 3-temperature grid "
                         "(corner-paired VDD), via klt sim corner requests.",
                "netlist_source": "schematic (pre-layout)",
            },
            "matrix": {"corners": corners, "temps_c": temps, "benches": benches,
                       "vdd_by_corner": {c: VDD_BY_CORNER[c] for c in corners},
                       "grid": {"ppd": PPD, "f0_hz": F0_HZ, "f1_hz": F1_HZ, "curve_step": CURVE_STEP},
                       "psrr_window_hz": [F0_HZ, 1e3], "noise_band_hz": [1e2, 1e6]},
            "backend_arg": args.backend,
            "env_KLT_SIM_BACKEND": os.environ.get("KLT_SIM_BACKEND"),
            "benches": meta_benches,
            "tools": {
                "klt": subprocess.run([*KLT_CMD, "--version"], capture_output=True, text=True).stdout.strip(),
                "python": platform.python_version(),
                "platform": f"{platform.system()} {platform.release()} {platform.machine()}",
            },
        }
        (RECORDS_DIR / f"{record_id}-psrr-noise.json").write_text(json.dumps(meta, indent=2) + "\n")
        print(f"Wrote record {record_id}-psrr-noise:")
        for w in written:
            print(f"  {w.relative_to(REPO_ROOT)}")
        return 1 if any_bad else 0


if __name__ == "__main__":
    sys.exit(main())
