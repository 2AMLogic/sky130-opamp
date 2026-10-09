#!/usr/bin/env python3
"""Independent cross-checks of the PSRR and noise benches (issue #54).

Runs four small single-corner `klt sim` requests (`--backend local`: one
operating point / one corner each, which the host rules allow) and writes
one append-only record `records/<id>-psrr-noise-validation.json`:

  1. DC finite-difference PSRR+ at tt/27C: d(vout)/d(vdd) from two .op solves
     (vdd 1.79 / 1.81 V, input held at a fixed 0.9 V) vs the AC bench's
     low-frequency value -- two different analyses of the same circuit.
  2. Band-limited noise: ss/125C `.noise` swept over exactly 100 Hz-1 MHz,
     whose ngspice-native `inoise_total` is compared with the main bench's
     trapezoid-in-ln(f) `vn_int_band` (post-processed from the full sweep).
  3. Negative control: psrr_vdd.cir with the Cinp shunt removed must read
     ~6 dB of PSRR (the Vcm divider's own ripple dominates) -- proof the
     shunt is load-bearing and the bench would notice a supply-to-input leak.
  4. The AC bench itself at the same tt/27C point (reference for 1).
"""

from __future__ import annotations

import json
import os
import shlex
import math
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

EXP_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = EXP_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "sim" / "lib"))
from spice_harness import git_sha  # noqa: E402

TB = EXP_DIR / "testbench"
MODELS = {"pdk": "sky130A", "lib": "libs.tech/ngspice/sky130.lib.spice"}


def req(netlist, corner, vdd, temp, analysis, meas, digits=10):
    return {
        "netlist": str(netlist), "netlist_source": "schematic", "models": MODELS,
        "corners": {"process": [corner], "supply_v": {"vdd": vdd}, "temperature_c": [temp]},
        "analysis": analysis, "measurements": meas,
        "options": {"timeout_s": 300, "ngspice_init": [f"set numdgt={digits}"]},
    }


def run(tmp: Path, name: str, r: dict) -> dict:
    p = tmp / f"{name}.request.json"
    p.write_text(json.dumps(r, indent=2))
    out = subprocess.run([*shlex.split(os.environ.get("KLT_CMD", "klt")), "sim", str(p), "--backend", "local", "--format", "json"],
                         capture_output=True, text=True)
    d = json.loads(out.stdout)
    vals = [{c["corner_id"]: {m["name"]: m["value"] for m in c["measurements"]}} for c in d["corners"]]
    return {"status": d["status"], "values": vals, "request": r}


def main() -> int:
    ac = {"kind": "ac", "args": "dec 20 0.1 1g"}
    with tempfile.TemporaryDirectory(prefix="opamp-psrr-val-") as t:
        tmp = Path(t)
        no_cinp = tmp / "psrr_vdd_no_cinp.cir"
        src = (TB / "psrr_vdd.cir").read_text()
        assert "Cinp inp 0 1\n" in src
        no_cinp.write_text(src.replace("Cinp inp 0 1\n", "").replace(
            '.include "../../../design/netlist/opamp_core.spice"',
            f'.include "{REPO_ROOT / "design/netlist/opamp_core.spice"}"'))
        # Finite-difference variant: the input must be held at a fixed 0.9 V
        # (the divider would legitimately move Vcm with vdd and read 6 dB).
        fixed = tmp / "psrr_vdd_fixed_vcm.cir"
        fixed_src = no_cinp.read_text().replace("Rdiv1 vdd inp 500k\n", "Vfix inp 0 dc 0.9\n").replace(
            "Rdiv2 inp 0 500k\n", "")
        assert "Vfix" in fixed_src and "Rdiv2" not in fixed_src
        fixed.write_text(fixed_src)
        res = {
            "dc_fd_psrr": run(tmp, "dc_fd", req(
                fixed, "tt", [1.79, 1.81], 27, {"kind": "op", "args": ""},
                [{"name": "vout", "expr": "v(out)", "unit": "V"},
                 {"name": "vinp", "expr": "v(inp)", "unit": "V"}])),
            "ac_reference": run(tmp, "ac_ref", req(
                TB / "psrr_vdd.cir", "tt", [1.8], 27, ac,
                [{"name": "avs_0p1hz_db", "expr": "db(v(out))[0]", "unit": "dB"},
                 {"name": "avs_1khz_db", "expr": "db(v(out))[80]", "unit": "dB"}])),
            "noise_bandlimited": run(tmp, "noise_bl", req(
                TB / "noise.cir", "ss", [1.62], 125,
                {"kind": "noise", "args": "v(out) Vinp dec 100 100 1e6"},
                [{"name": "inoise_total_100hz_1mhz", "expr": "noise2.inoise_total", "unit": "V"}], 8)),
            "noise_full_sweep_same_corner": None,
            "negative_control_no_cinp": run(tmp, "negctl", req(
                no_cinp, "tt", [1.8], 27, ac,
                [{"name": "avs_1khz_db", "expr": "db(v(out))[80]", "unit": "dB"}])),
        }
        # Same corner through the main bench's full-sweep trapezoid.
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import psrr_noise_sweep as m  # noqa: E402
        nreq = m.build_request("noise", ["ss"], [125.0], str(TB / "noise.cir"), False)
        res["noise_full_sweep_same_corner"] = run(tmp, "noise_full", nreq)

    # Derived comparisons
    lo, hi = (next(iter(v.values())) for v in res["dc_fd_psrr"]["values"])
    dvout, dvdd = hi["vout"] - lo["vout"], 1.81 - 1.79
    dc_psrr_db = -20 * math.log10(abs(dvout / dvdd))
    ac_vals = next(iter(res["ac_reference"]["values"][0].values()))
    bl = next(iter(res["noise_bandlimited"]["values"][0].values()))["inoise_total_100hz_1mhz"]
    full = next(iter(res["noise_full_sweep_same_corner"]["values"][0].values()))["vn_int_band"]
    neg = next(iter(res["negative_control_no_cinp"]["values"][0].values()))["avs_1khz_db"]
    summary = {
        "dc_finite_difference_psrr_db": dc_psrr_db,
        "ac_bench_psrr_0p1hz_db": -ac_vals["avs_0p1hz_db"],
        "ac_vs_dc_delta_db": -ac_vals["avs_0p1hz_db"] - dc_psrr_db,
        "noise_native_inoise_total_uv": bl * 1e6,
        "noise_bench_vn_int_band_uv": full * 1e6,
        "noise_integration_rel_error": full / bl - 1.0,
        "negative_control_psrr_1khz_db_without_cinp": -neg,
        "negative_control_ok": -neg < 10.0,
    }
    rid = f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{git_sha(REPO_ROOT)}"
    out = EXP_DIR / "records" / f"{rid}-psrr-noise-validation.json"
    out.write_text(json.dumps({"record_id": rid, "summary": summary, "runs": res}, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    print(f"wrote {out.relative_to(REPO_ROOT)}")
    return 0 if summary["negative_control_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
