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
import math
import os
import shutil
import tempfile
import sys
from pathlib import Path

EXP_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = EXP_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "sim" / "lib"))
import dut_identity  # noqa: E402
from spice_harness import allocate_record_id, git_sha, run_klt_sim, write_new  # noqa: E402

TB = EXP_DIR / "testbench"
RECORDS_DIR = EXP_DIR / "records"
SNAPSHOT_DIR = EXP_DIR / "netlist-snapshots"
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
    d = run_klt_sim(p, tmp / f"{name}-out", "local")
    vals = [{c["corner_id"]: {m["name"]: m["value"] for m in c["measurements"]}} for c in d["corners"]]
    return {"status": d["status"], "values": vals, "request": r}


# ---------------------------------------------------------------------------
# Acceptance criteria (issue #98). The evaluator below is simulator-free.
#
# PSRR_AC_VS_DC_TOL_DB = 0.05 dB. The two analyses see the same circuit, so
# the disagreement is only (a) DC finite-difference resolution: vout is
# printed to ~11 digits (numdgt=10) so a ~8 uV swing carries ~1e-6 relative
# quantization (~1e-5 dB); (b) curvature over the +/-10 mV supply step and
# (c) the AC point at 0.1 Hz rather than true DC; both are well below
# 0.01 dB for this bench (the PSRR bench's own Acl=1 referral error is
# < 0.01 dB). 0.05 dB (0.6 % in amplitude) leaves headroom over those effects
# and ~100x over the committed 0.0004 dB, yet still catches a real
# supply-to-input leak (the no-Cinp control shifts PSRR by ~60 dB).
#
# NOISE_INTEGRATION_TOL_REL = 1e-3. The bench integrates the full sweep
# (dec 100 -> d ln f = 0.023) by trapezoid in ln(f) whose error scales as
# (d ln f)^2/12 ~ 4e-5 of local curvature; the native value is printed to
# 8 digits. The committed error is 1.7e-4; 1e-3 gives ~6x margin and bounds
# the disagreement at 0.1 % (~0.009 dB of rms noise).
#
# NEGATIVE_CONTROL_MAX_DB = 10 dB is the pre-existing criterion (expected ~6 dB).
PSRR_AC_VS_DC_TOL_DB = 0.05
NOISE_INTEGRATION_TOL_REL = 1e-3
NEGATIVE_CONTROL_MAX_DB = 10.0
VDD_STEP_V = (1.79, 1.81)

EXPECTED_CORNERS = {
    "dc_fd_psrr": ["tt/1.790V/27C", "tt/1.810V/27C"],
    "ac_reference": ["tt/1.800V/27C"],
    "noise_bandlimited": ["ss/1.620V/125C"],
    "noise_full_sweep_same_corner": ["ss/1.620V/125C"],
    "negative_control_no_cinp": ["tt/1.800V/27C"],
}
REQUIRED_MEAS = {
    "dc_fd_psrr": ["vout"],
    "ac_reference": ["avs_0p1hz_db"],
    "noise_bandlimited": ["inoise_total_100hz_1mhz"],
    "noise_full_sweep_same_corner": ["vn_int_band"],
    "negative_control_no_cinp": ["avs_1khz_db"],
}


def _finite(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def evaluate(res: dict) -> tuple[dict, list[dict], bool]:
    """Return (summary, criteria, all_passed) for the returned runs `res`.

    Never raises on malformed input: every problem becomes a failed
    criterion. Comparisons whose inputs are invalid are recorded as failed.
    """
    criteria: list[dict] = []

    def add(name, ok, detail, threshold=None, observed=None):
        criteria.append({"name": name, "threshold": threshold, "observed": observed,
                         "verdict": "pass" if ok else "fail", "detail": detail})
        return ok

    # 1. structure: statuses, corners, measurements, finite values
    vals: dict[str, dict[str, dict]] = {}  # run -> corner -> measurements
    for run_name, corners in EXPECTED_CORNERS.items():
        r = res.get(run_name) if isinstance(res, dict) else None
        if not isinstance(r, dict):
            add(f"{run_name}:present", False, "run missing")
            continue
        add(f"{run_name}:status", r.get("status") == "pass",
            f"status={r.get('status')!r}", "pass", r.get("status"))
        by_corner: dict[str, dict] = {}
        for entry in r.get("values") or []:
            if isinstance(entry, dict):
                for cid, meas in entry.items():
                    by_corner[cid] = meas if isinstance(meas, dict) else {}
        vals[run_name] = by_corner
        missing = [c for c in corners if c not in by_corner]
        extra = [c for c in by_corner if c not in corners]
        add(f"{run_name}:corners", not missing and not extra,
            f"expected {corners}, got {sorted(by_corner)}", corners, sorted(by_corner))
        for cid in corners:
            m = by_corner.get(cid, {})
            for name in REQUIRED_MEAS[run_name]:
                val = m.get(name)
                add(f"{run_name}:{cid}:{name}", _finite(val),
                    f"value={val!r} (must be present and finite)", "finite", val)

    def get(run, cid, name):
        val = vals.get(run, {}).get(cid, {}).get(name)
        return val if _finite(val) else None

    summary: dict = {}
    lo_id, hi_id = EXPECTED_CORNERS["dc_fd_psrr"]
    vlo, vhi = get("dc_fd_psrr", lo_id, "vout"), get("dc_fd_psrr", hi_id, "vout")
    ac = get("ac_reference", EXPECTED_CORNERS["ac_reference"][0], "avs_0p1hz_db")
    bl = get("noise_bandlimited", EXPECTED_CORNERS["noise_bandlimited"][0], "inoise_total_100hz_1mhz")
    full = get("noise_full_sweep_same_corner", EXPECTED_CORNERS["noise_full_sweep_same_corner"][0], "vn_int_band")
    neg = get("negative_control_no_cinp", EXPECTED_CORNERS["negative_control_no_cinp"][0], "avs_1khz_db")

    # 2. PSRR AC vs DC finite difference
    dc_db = None
    if vlo is not None and vhi is not None and vhi != vlo:
        dc_db = -20 * math.log10(abs((vhi - vlo) / (VDD_STEP_V[1] - VDD_STEP_V[0])))
        summary["dc_finite_difference_psrr_db"] = dc_db
    else:
        add("psrr_ac_vs_dc", False,
            "DC finite difference undefined (missing vout or zero dvout: log of zero/invalid)")
    if dc_db is not None and ac is not None:
        delta = -ac - dc_db
        summary["ac_bench_psrr_0p1hz_db"] = -ac
        summary["ac_vs_dc_delta_db"] = delta
        add("psrr_ac_vs_dc", abs(delta) <= PSRR_AC_VS_DC_TOL_DB,
            f"|AC - DC| = {abs(delta):.6g} dB, tolerance {PSRR_AC_VS_DC_TOL_DB} dB",
            PSRR_AC_VS_DC_TOL_DB, delta)
    elif dc_db is not None:
        add("psrr_ac_vs_dc", False, "AC reference measurement unavailable")

    # 3. native vs post-processed noise integration
    if bl is not None and full is not None and bl > 0:
        rel = full / bl - 1.0
        summary["noise_native_inoise_total_uv"] = bl * 1e6
        summary["noise_bench_vn_int_band_uv"] = full * 1e6
        summary["noise_integration_rel_error"] = rel
        add("noise_integration", abs(rel) <= NOISE_INTEGRATION_TOL_REL,
            f"|bench/native - 1| = {abs(rel):.3g}, tolerance {NOISE_INTEGRATION_TOL_REL}",
            NOISE_INTEGRATION_TOL_REL, rel)
    else:
        add("noise_integration", False, "noise integration ratio undefined (missing or non-positive native total)")

    # 4. negative control
    if neg is not None:
        summary["negative_control_psrr_1khz_db_without_cinp"] = -neg
        ncok = -neg < NEGATIVE_CONTROL_MAX_DB
        summary["negative_control_ok"] = ncok
        add("negative_control", ncok,
            f"PSRR without Cinp = {-neg:.3f} dB, must be < {NEGATIVE_CONTROL_MAX_DB} dB",
            NEGATIVE_CONTROL_MAX_DB, -neg)
    else:
        summary["negative_control_ok"] = False
        add("negative_control", False, "negative-control measurement unavailable")

    ok = all(c["verdict"] == "pass" for c in criteria)
    summary["all_criteria_passed"] = ok
    return summary, criteria, ok


def main() -> int:
    ac = {"kind": "ac", "args": "dec 20 0.1 1g"}
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import psrr_noise_sweep as m  # noqa: E402
    # Capture the DUT once (issue #151); every run below uses bodies rendered
    # against that copy, retained with their requests in the snapshot dir.
    rid = allocate_record_id(RECORDS_DIR, git_sha(REPO_ROOT), extra_dirs=[SNAPSHOT_DIR])
    snap = SNAPSHOT_DIR / f"{rid}-psrr-noise-validation"
    out = RECORDS_DIR / f"{rid}-psrr-noise-validation.json"
    done = False
    try:
        dut, bodies = m.capture_benches(snap, ["psrr_vdd", "noise"])
        print(f"DUT snapshot: {dut['snapshot_path']} ({dut['sha256']})", file=sys.stderr)
        psrr_body = bodies["psrr_vdd"].read_text()
        assert "Cinp inp 0 1\n" in psrr_body
        no_cinp = snap / "psrr_vdd_no_cinp.spice"
        no_cinp.write_text(psrr_body.replace("Cinp inp 0 1\n", ""))
        # Finite-difference variant: the input must be held at a fixed 0.9 V
        # (the divider would legitimately move Vcm with vdd and read 6 dB).
        fixed = snap / "psrr_vdd_fixed_vcm.spice"
        fixed_src = no_cinp.read_text().replace("Rdiv1 vdd inp 500k\n", "Vfix inp 0 dc 0.9\n").replace(
            "Rdiv2 inp 0 500k\n", "")
        assert "Vfix" in fixed_src and "Rdiv2" not in fixed_src
        fixed.write_text(fixed_src)
        with tempfile.TemporaryDirectory(prefix="opamp-psrr-val-") as t:
            tmp = Path(t)

            def go(name, r):
                snap_r = dict(r)
                snap_r["netlist"] = Path(r["netlist"]).name
                (snap / f"{name}.request.json").write_text(json.dumps(snap_r, indent=2) + "\n")
                res_ = run(tmp, name, r)
                # recorded netlist: relative to records/, pointing into the snapshot
                res_["request"] = dict(r, netlist=os.path.relpath(r["netlist"], RECORDS_DIR))
                return res_

            res = {
                "dc_fd_psrr": go("dc_fd_psrr", req(
                    fixed, "tt", [1.79, 1.81], 27, {"kind": "op", "args": ""},
                    [{"name": "vout", "expr": "v(out)", "unit": "V"},
                     {"name": "vinp", "expr": "v(inp)", "unit": "V"}])),
                "ac_reference": go("ac_reference", req(
                    bodies["psrr_vdd"], "tt", [1.8], 27, ac,
                    [{"name": "avs_0p1hz_db", "expr": "db(v(out))[0]", "unit": "dB"},
                     {"name": "avs_1khz_db", "expr": "db(v(out))[80]", "unit": "dB"}])),
                "noise_bandlimited": go("noise_bandlimited", req(
                    bodies["noise"], "ss", [1.62], 125,
                    {"kind": "noise", "args": "v(out) Vinp dec 100 100 1e6"},
                    [{"name": "inoise_total_100hz_1mhz", "expr": "noise2.inoise_total", "unit": "V"}], 8)),
                "noise_full_sweep_same_corner": None,
                "negative_control_no_cinp": go("negative_control_no_cinp", req(
                    no_cinp, "tt", [1.8], 27, ac,
                    [{"name": "avs_1khz_db", "expr": "db(v(out))[80]", "unit": "dB"}])),
            }
            # Same corner through the main bench's full-sweep trapezoid.
            nreq = m.build_request("noise", ["ss"], [125.0], str(bodies["noise"]), False)
            res["noise_full_sweep_same_corner"] = go("noise_full_sweep_same_corner", nreq)

        summary, criteria, ok = evaluate(res)
        write_new(out, json.dumps(
            {"record_id": rid, "dut": dut, "summary": summary, "criteria": criteria, "passed": ok, "runs": res},
            indent=2) + "\n")
        done = True
    finally:
        if not done:   # no record written -> no orphan snapshot
            shutil.rmtree(snap, ignore_errors=True)
    print(json.dumps(summary, indent=2))
    for c in criteria:
        print(f"[{c['verdict'].upper()}] {c['name']}: {c['detail']}")
    print(f"wrote {out.relative_to(REPO_ROOT)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
