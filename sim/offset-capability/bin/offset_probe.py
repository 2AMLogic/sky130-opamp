#!/usr/bin/env python3
"""Seeded-mismatch capability probe for issue #52 (NOT a Monte Carlo campaign).

Builds `klt sim` requests for two small benches, runs them through the actual
backend, and extracts results with explicit failure semantics.

  pair   bench/pair_diag.cir  -- identical-device-pair drain-current differences
  offset bench/offset_dc.cir  -- open-loop input-referred offset (output
                                 crossing VDD/2 on a DC input sweep)

Usage:
  offset_probe.py run --bench pair|offset --label NAME [--mismatch on|off]
                      [--seed N --n N] [--backend NAME] [--dry-run]

`--mismatch on` selects `.lib tt_mm` (mc_mm_switch=1), `off` selects `.lib tt`
(mc_mm_switch=0). Multi-sample requests (`--n` > 1) are submitted through
`klt sim` only; this script never launches ngspice itself and has no loop over
simulator invocations. Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

EXP = Path(__file__).resolve().parent.parent
REPO = EXP.parent.parent
RECORDS = EXP / "records"
sys.path.insert(0, str(REPO / "sim" / "lib"))
from spice_harness import KltSimError, klt_sim  # noqa: E402

VDD = 1.8
VREF = VDD / 2          # output reference for the offset crossing
VCM = 0.9               # inn held here; inp = VCM + vd
SWEEP_LO, SWEEP_HI, SWEEP_STEP = -0.03, 0.03, 20e-6   # vd bracket / resolution (V)
# Predeclared tolerances (see README "Predeclared tolerances").
EXTRACTION_RES_V = SWEEP_STEP          # linear interp between 20 uV points
CONTROL_TOL_V = 2 * EXTRACTION_RES_V   # mismatch-off spread / replay mismatch
PAIR_CONTROL_TOL_A = 1e-9              # |id1-id2| floor with mismatch off
PAIR_MIN_SPREAD_A = 10e-9              # randomized pair diff must exceed this


class ProbeError(RuntimeError):
    pass


def build_request(bench: str, mismatch: bool, mc: dict | None) -> dict:
    cir = {"pair": "../bench/pair_diag.cir", "offset": "../bench/offset_dc.cir"}[bench]
    if bench == "pair":
        analysis = {"kind": "dc", "args": "Vg 0.79 0.81 0.01"}
        meas = [
            {"name": n, "spice": f".meas dc {n} find i({s}) at=0.8", "unit": "A"}
            for n, s in (("idn1", "Vn1"), ("idn2", "Vn2"), ("idp1", "Vp1"), ("idp2", "Vp2"))
        ]
    else:
        analysis = {"kind": "dc", "args": f"Vd {SWEEP_LO} {SWEEP_HI} {SWEEP_STEP:g}"}
        meas = [
            {"name": "vos_inp", "spice": f".meas dc vos_inp find v(inp) when v(out)={VREF} rise=1", "unit": "V"},
            {"name": "out_lo", "spice": f".meas dc out_lo find v(out) at={SWEEP_LO}", "unit": "V"},
            {"name": "out_hi", "spice": f".meas dc out_hi find v(out) at={SWEEP_HI - SWEEP_STEP:.6f}", "unit": "V"},
        ]
    req = {
        "netlist": cir,
        "netlist_source": "schematic",
        "models": {"pdk": "sky130A", "lib": "libs.tech/ngspice/sky130.lib.spice"},
        "corners": {
            "process": ["tt_mm" if mismatch else "tt"],
            "supply_v": {"vdd": [VDD]},
            "temperature_c": [27.0],
        },
        "analysis": analysis,
        "measurements": meas,
        "options": {"timeout_s": 600, "keep_artifacts": True},
        "batch": {"runner_version_check": "warn"},
    }
    if mc:
        req["monte_carlo"] = {"n": mc["n"], "seed": mc["seed"], "vary": "mismatch"}
    return req


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def extract_samples(payload: dict, bench: str) -> list[dict]:
    """Per-corner/sample results. A sample that lacks a finite value for any
    required measurement, or whose output does not bracket VREF, is returned
    with ok=False and a reason -- never as zero offset."""
    if not isinstance(payload, dict) or not isinstance(payload.get("corners"), list):
        raise ProbeError("klt payload has no corners[]")
    need = ("idn1", "idn2", "idp1", "idp2") if bench == "pair" else ("vos_inp", "out_lo", "out_hi")
    out = []
    for c in payload["corners"]:
        vals = {m.get("name"): m.get("value") for m in c.get("measurements", []) if isinstance(m, dict)}
        s = {"corner_id": c.get("corner_id"), "klt_status": c.get("status"),
             "monte_carlo": c.get("monte_carlo"), "ok": True, "reason": None}
        missing = [k for k in need if not _num(vals.get(k))]
        if c.get("status") not in ("pass",):
            s.update(ok=False, reason=f"corner status {c.get('status')!r}")
        elif missing:
            s.update(ok=False, reason=f"missing/non-finite measurement(s): {missing}")
        elif bench == "pair":
            s["dn"] = vals["idn1"] - vals["idn2"]
            s["dp"] = vals["idp1"] - vals["idp2"]
        else:
            lo, hi = vals["out_lo"], vals["out_hi"]
            if not (lo < VREF < hi):
                s.update(ok=False, reason=f"output does not bracket VREF (out_lo={lo}, out_hi={hi})")
            else:
                s["vos_v"] = vals["vos_inp"] - VCM   # Vos = V(inp)-V(inn) at crossing
        out.append(s)
    return out


def run_klt(request_path: Path, outdir: Path, backend: str | None):
    """(cmd, exit code, JSON report or None if klt printed none, stderr)."""
    try:
        return klt_sim(request_path, outdir, backend)
    except KltSimError as exc:
        return exc.cmd, exc.returncode, None, exc.stderr


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cmd", choices=["run"])
    ap.add_argument("--bench", choices=["pair", "offset"], required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--mismatch", choices=["on", "off"], default="on")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--backend")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    mc = {"n": a.n, "seed": a.seed} if a.seed is not None else None
    req = build_request(a.bench, a.mismatch == "on", mc)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    rid = f"{stamp}-{a.bench}-{a.label}"
    RECORDS.mkdir(exist_ok=True)
    req_path = RECORDS / f"{rid}.request.json"
    if req_path.exists():
        raise SystemExit(f"refusing to overwrite append-only record {req_path}")
    req_path.write_text(json.dumps(req, indent=2) + "\n")
    if a.dry_run:
        print(req_path)
        return 0
    outdir = RECORDS / f"{rid}-artifacts"
    cmd, rc, payload, err = run_klt(req_path, outdir, a.backend)
    (RECORDS / f"{rid}.klt.json").write_text(json.dumps(payload, indent=2) + "\n" if payload else "null\n")
    meta = {"record_id": rid, "command": cmd, "exit_code": rc, "stderr": err[-4000:],
            "env_KLT_SIM_BACKEND": os.environ.get("KLT_SIM_BACKEND"),
            "git_sha": subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                                      capture_output=True, text=True).stdout.strip()}
    if payload:
        env = payload.get("environment", {})
        meta["remote"] = env.get("remote")
        meta["monte_carlo_echo"] = env.get("monte_carlo")
        meta["samples"] = extract_samples(payload, a.bench)
    (RECORDS / f"{rid}.summary.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps({k: meta.get(k) for k in ("record_id", "exit_code", "samples")}, indent=2))
    return 0 if payload and all(s["ok"] for s in meta["samples"]) else 1


if __name__ == "__main__":
    sys.exit(main())
