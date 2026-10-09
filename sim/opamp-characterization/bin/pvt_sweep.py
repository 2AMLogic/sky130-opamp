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

The PDK-resolution and ngspice-harness *code* that applies the same principle
(`HarnessError`, `load_json`, `volare_path`, the `Pdk` base, `first_line`,
`render`, `git_sha`, and the `--check-env` report pair
`report_tool_status`/`report_pdk`) is likewise not duplicated here -- it lives
once in `sim/lib/spice_harness.py` and is imported below (issues #23 and #40).
Only this experiment's own additions stay in this file: the `OpampPdk`
subclass that resolves the R+C corner includes, the per-analysis run/parse
logic, and `check_env()`'s own netlist and R+C-include report lines around the
shared report.

Stdlib only -- no third-party Python dependencies, so the only tools this
script itself requires are python3 and ngspice (plus, to resolve the PDK,
either `volare` on PATH or PDK_ROOT/PDK set by hand -- see --check-env).

    --check-env        report tool/PDK availability and exit (no simulation)
    --corners C,C       subset of {tt,ff,ss,sf,fs}      (default: all five)
    --temps T,T          temperatures in degC             (default: -40,27,125)
    --analyses A,A       subset of {ac,tran_sr,dc_swing,icmr,cmrr}
                         (default: ac,tran_sr,dc_swing -- icmr/cmrr are opt-in)
    --backend NAME       `klt sim` backend for icmr/cmrr (default: batch;
                         `local` for a single-point debug probe)
    --klt-cmd CMD        the klt invocation for icmr/cmrr (default: `klt`, or
                         $KLT_CMD). The batch fleet refuses a client whose
                         `klt --version` differs from the fleet image's
                         (`batch_runner_version_mismatch`); pin a matching one
                         without touching the host tool, e.g.
                         --klt-cmd 'uvx --from klayout-tools==0.5.0 klt'
    --keep-work         do not delete the scratch ngspice decks/outputs

`ac`, `tran_sr` and `dc_swing` are unchanged: this script renders their full
decks and drives `ngspice -b` itself, one subprocess per (corner, temperature)
point. `icmr` and `cmrr` (issue #53) are different by design: their templates
are `klt sim` circuit BODIES, the whole 5x3 grid of each is declared as ONE
`klt sim` request (corner/supply/temperature axes) and submitted with
`klt sim <request> --backend batch`, and the per-corner measurement values in
klt's JSON response are mapped into the same CSV/record scheme. No ngspice loop
is ever run for them. Requires `klt` on PATH.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

EXP_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = EXP_DIR.parent.parent

sys.path.insert(0, str(REPO_ROOT / "sim" / "lib"))
from spice_harness import (  # noqa: E402  -- import follows the sys.path bootstrap above
    HarnessError,
    Pdk,
    first_line,
    git_sha,
    load_json,
    render,
    report_pdk,
    report_tool_status,
)

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
DEFAULT_ANALYSES = ("ac", "tran_sr", "dc_swing")  # icmr/cmrr (issue #53) are opt-in: they go to the klt batch fleet
DEFAULT_KLT_BACKEND = "batch"

CL_F = "2p"  # DR-001's CL = 2 pF
IBIAS_A = "5u"  # DR-002 (a): 5 uA external reference into `ibias`

# Corner -> VDD mapping. Matches DR-002 Sec (f)'s own pairing (ss -> 1.62V
# worst-case-low, ff -> 1.98V worst-case-high, tt -> 1.80V nominal,
# per spec/target-spec.md Sec 1). sf/fs have no such named pairing in either
# DR-002 or target-spec.md -- nominal VDD is used for both, a stated
# methodology choice (see ../README.md), not a re-derivation of a
# process/supply correlation this repo has not decided.
VDD_BY_CORNER = {"tt": 1.80, "ff": 1.98, "ss": 1.62, "sf": 1.80, "fs": 1.80}


# --------------------------------------------------------------------------
# PDK resolution -- the MOS-corner resolution itself lives in
# sim/lib/spice_harness.py and is driven by ../gm-id-characterization's own
# pdk.json/model-files.json; only the R+C corner include files this experiment
# introduces (from its own pdk.json) are resolved here.
# --------------------------------------------------------------------------


class OpampPdk(Pdk):
    """`Pdk` plus the R+C ("typical") corner includes this experiment adds."""

    def __init__(self, pin: dict, own_pin: dict):
        super().__init__(pin)
        self.own_pin = own_pin

    def rc_includes(self) -> list[Path]:
        return [self.dir / rel for rel in self.own_pin["rc_corner"]["include_files"]]

    def validate(self, corners: Iterable[str]) -> None:
        super().validate(corners)
        for inc in self.rc_includes():
            if not inc.is_file():
                raise HarnessError(f"missing R+C corner include: {inc}")


def resolve_pdk() -> OpampPdk:
    pin = load_json(GMID_PDK_PIN_FILE)
    own_pin = load_json(OWN_PDK_FILE)
    pdk = OpampPdk(pin, own_pin)
    pdk.validate(DEFAULT_CORNERS)
    return pdk


def check_env() -> int:
    status = report_tool_status()
    if not DESIGN_NETLIST.is_file():
        print(f"netlist : MISSING {DESIGN_NETLIST}")
        return 1
    print(f"netlist : OK   {DESIGN_NETLIST}")
    pdk_status, pdk = report_pdk(resolve_pdk, DEFAULT_CORNERS, "MOS corner")
    if pdk is not None:
        for inc in pdk.rc_includes():
            print(f"  R+C corner include: {inc}")
    # klt is only required by the icmr/cmrr analyses -- report it, but a
    # missing klt must not fail the legacy ac/tran_sr/dc_swing workflow.
    klt = klt_available()
    if klt:
        print(f"klt     : OK   {' '.join(KLT_CMD)} ({first_line([*KLT_CMD, '--version'])})")
        print(f"  klt sim backend for icmr/cmrr: {DEFAULT_KLT_BACKEND}"
              f" (env KLT_SIM_BACKEND={os.environ.get('KLT_SIM_BACKEND', '<unset>')}; override with --backend)")
    else:
        print("klt     : MISSING (not on PATH) -- needed only for --analyses icmr,cmrr")
    return status | pdk_status


# --------------------------------------------------------------------------
# Running + parsing (deck rendering itself is spice_harness.render)
# --------------------------------------------------------------------------


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


# --------------------------------------------------------------------------
# Per-analysis run + parse
# --------------------------------------------------------------------------


def common_subs(pdk: OpampPdk, corner: str, temp: float, vdd: float) -> dict:
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


# --------------------------------------------------------------------------
# klt-sim analyses (issue #53): ICMR and CMRR.
#
# Unlike the three analyses above these are NOT driven through run_ngspice():
# each is one `klt sim` request that declares the whole corner x supply x
# temperature grid, submitted on the batch backend. The templates are circuit
# bodies (see ../testbench/opamp_{icmr,cmrr}.spice.tmpl); the analysis card,
# `.lib`/`.temp`/`alter vdd` cards and the measurements live in the request.
# --------------------------------------------------------------------------

KLT_ANALYSES = ("icmr", "cmrr")
SKY130_LIB = "libs.tech/ngspice/sky130.lib.spice"  # sections tt/ff/ss/sf/fs

# ICMR bench constants -- fixed before any batch result existed; the README's
# "ICMR bench" section and ../testbench/opamp_icmr.spice.tmpl's header state the
# same criterion: ICMR = contiguous Vcm range around VDD/2, output held at
# mid-rail, over which the local DC CMRR 1/|d vid/d Vcm| stays >= 40 dB.
# One icmr request per corner (3 units each: the temperatures), not per VDD group.
# Observed on the fleet (ngspice-46): the 9-unit tt/sf/fs 1.8 V group request had 7 of
# 9 units sit in gmin/source stepping until the per-corner timeout (twice, with
# different sets of units each time), while the 3-unit 1.62 V / 1.98 V group
# requests and a 1-unit tt/27 C request of the same deck converged in 40-150 s.
ICMR_REQUEST_PER_CORNER = True
ICMR_VSTEP_V = 0.005  # swept-Vcm resolution (edges are interpolated between points)
ICMR_DV_V = 0.01  # Vcm offset between the two amplifier copies (finite-difference step)
ICMR_VSWEEP_START_V = 0.0  # NOT below ground: the fleet's ngspice-46 stalled in source stepping from -0.02 V (README)
ICMR_VSWEEP_OVERSHOOT_V = 0.02  # sweep to VDD + this, same reason on the high side
ICMR_CMRR_FLOORS_DB = {"40db": 40.0, "30db": 30.0, "50db": 50.0}  # primary first; the rest = sensitivity band
ICMR_RLOOP = "100k"  # Rin = Rf of the output-held-at-mid-rail inverting loop
ICMR_RAIL_EPS_V = 0.03  # an edge within this of 0 V / VDD is a rail edge, not an input-stage limit
# Ratified ICMR target window (spec/target-spec.md Sec 2 ICMR row; NOT edited
# or relaxed here) and the sibling-consumer sense point (Sec 5 consumers table).
TARGET_ICMR_V = (0.888, 1.024)
CONSUMER_SENSE_V = 0.73

# CMRR bench: spot frequencies at which Adm and Acm are read (.meas ... at=)
CMRR_SPOTS = (("1hz", "1"), ("10hz", "10"), ("100hz", "100"), ("1khz", "1k"),
              ("10khz", "10k"), ("100khz", "100k"), ("1mhz", "1meg"))
CMRR_SPOT_HEADLINE = "1khz"  # the single "stated spot frequency" quoted in the README
# DC common-mode bias points the CMRR bench is run at: mid-supply (the same
# point opamp_ac uses, so Adm is directly comparable) and the centre of the
# ratified ICMR target window (which sits above mid-rail).
CMRR_CM_POINTS = {
    "mid": ("0.5*v(vdd)", None),
    "window": (f"{0.5 * (TARGET_ICMR_V[0] + TARGET_ICMR_V[1]):g}", 0.5 * (TARGET_ICMR_V[0] + TARGET_ICMR_V[1])),
}
CROSSCHECK_TOL_GAIN_DB = 0.05  # Adm_dc vs committed ac gain_dc_db at the same point
CROSSCHECK_TOL_GBW_FRAC = 0.01  # gbw
CROSSCHECK_TOL_IQ_FRAC = 0.01  # ICMR mid-point supply current vs committed ac iq_a


def icmr_measurements(vdd: float) -> list[dict]:
    """`.meas dc` cards for one VDD group (mid-supply and the sweep's `to`/`from`
    limits are literal numbers in a .meas card, hence one request per VDD; and see
    ICMR_REQUEST_PER_CORNER for why each corner is its own request)."""
    mid = 0.5 * vdd
    ms = [
        {"name": "vout_mid_v", "unit": "V", "spice": f".meas dc vout_mid_v find v(out_1) at={mid:g}"},
        {"name": "vid_mid_v", "unit": "V", "spice": f".meas dc vid_mid_v find v(vid1) at={mid:g}"},
        {"name": "iq_mid_a", "unit": "A", "spice": f".meas dc iq_mid_a find i(vsense) at={mid:g}"},
        {"name": "k_mid", "spice": f".meas dc k_mid find v(k) at={mid:g}"},
    ]
    for label, db in ICMR_CMRR_FLOORS_DB.items():
        level = 10 ** (-db / 20.0)
        ms.append({"name": f"lo_{label}", "unit": "V",
                   "spice": f".meas dc lo_{label} when v(k)={level:g} cross=last to={mid:g}"})
        ms.append({"name": f"hi_{label}", "unit": "V",
                   "spice": f".meas dc hi_{label} when v(k)={level:g} cross=1 from={mid:g}"})
    return ms


def cmrr_measurements() -> list[dict]:
    ms = []
    for label, f in CMRR_SPOTS:
        ms.append({"name": f"adm_{label}_db", "unit": "dB", "spice": f".meas ac adm_{label}_db find vdb(out_d) at={f}"})
        ms.append({"name": f"acm_{label}_db", "unit": "dB", "spice": f".meas ac acm_{label}_db find vdb(out_c) at={f}"})
    ms.append({"name": "gbw_hz", "unit": "Hz", "spice": ".meas ac gbw_hz when vdb(out_d)=0 cross=1"})
    return ms


KLT_MAX_PARALLEL_SUBMITS = 2  # the fleet is shared and capped; do not grab 5 instances at once
CAPACITY_RETRIES = 30
CAPACITY_WAIT_S = 60
RUNNER_VERSION_CHECK = ["warn"]  # set from --batch-runner-check
KLT_TIMEOUT_S = [1200]  # per-corner ngspice timeout in the klt request; set from --timeout-s
KLT_CMD: list[str] = shlex.split(os.environ.get("KLT_CMD", "klt"))


def klt_available() -> str | None:
    return shutil.which(KLT_CMD[0])


def vdd_groups(corners: list[str]) -> dict[float, list[str]]:
    """Corners grouped by their tied VDD (VDD_BY_CORNER)."""
    groups: dict[float, list[str]] = {}
    for c in corners:
        groups.setdefault(VDD_BY_CORNER[c], []).append(c)
    return dict(sorted(groups.items()))


def vdd_pairing(corners: list[str]) -> tuple[list[float], list[dict]]:
    """Per-corner VDD pairing as one request: supply axis = the distinct VDDs,
    `exclude` = every (corner, vdd) combination that is not VDD_BY_CORNER's."""
    vdds = sorted({VDD_BY_CORNER[c] for c in corners})
    exclude = [{"process": c, "supply_v": {"vdd": v}}
               for c in corners for v in vdds if v != VDD_BY_CORNER[c]]
    return vdds, exclude


def build_klt_request(analysis: str, cm_point: str | None, vdd_group: float | None, pdk: OpampPdk,
                      corners: list[str], temps: list[float], req_dir: Path, backend: str) -> tuple[Path, str]:
    """Render the circuit body + write the `klt sim` request JSON into req_dir.

    cmrr: one request for the whole grid (VDD pairing via supply axis + exclude).
    icmr: one request per corner (`.meas ... at=VDD/2` needs a literal mid-supply,
    and the 9-unit tt/sf/fs 1.8 V request stalled on the fleet; see ICMR_REQUEST_PER_CORNER).
    """
    body_subs = {
        "OPAMP_NETLIST": DESIGN_NETLIST, "VDD_NOM": vdd_group or VDD_BY_CORNER["tt"],
        "IBIAS_A": IBIAS_A, "CL_F": CL_F,
    }
    if analysis == "icmr":
        assert vdd_group is not None
        body_subs.update({"RLOOP": ICMR_RLOOP, "DV": ICMR_DV_V, "NS_MID": f"{0.5 * vdd_group:g}"})
        stop = vdd_group + ICMR_VSWEEP_OVERSHOOT_V
        analysis_card = {"kind": "dc", "args": f"Vinp {ICMR_VSWEEP_START_V:g} {stop:g} {ICMR_VSTEP_V:g}"}
        measurements = icmr_measurements(vdd_group)
        vdds, exclude = [vdd_group], []
        tag = f"icmr-{corners[0]}" if len(corners) == 1 else f"icmr-vdd{vdd_group:g}"
    else:
        body_subs.update({"VCM_EXPR": CMRR_CM_POINTS[cm_point][0], "RFB": "1e12", "CFB": "1"})
        analysis_card = {"kind": "ac", "args": "dec 20 1 1g"}
        measurements = cmrr_measurements()
        vdds, exclude = vdd_pairing(corners)
        tag = f"cmrr-{cm_point}"
    body = render(TESTBENCH_DIR / f"opamp_{analysis}.spice.tmpl", body_subs)
    req_dir.mkdir(parents=True, exist_ok=True)
    body_path = req_dir / f"{tag}-body.spice"
    body_path.write_text(body)
    request = {
        "netlist": body_path.name,
        "engine": "ngspice",
        "backend": backend,
        "models": {"pdk": pdk.variant, "lib": SKY130_LIB},
        "corners": {"process": corners, "supply_v": {"vdd": vdds}, "temperature_c": temps},
        **({"exclude": exclude} if exclude else {}),
        "analysis": analysis_card,
        "measurements": measurements,
        "options": {"timeout_s": KLT_TIMEOUT_S[0], "keep_artifacts": True},
    }
    if backend == "batch":
        # The fleet image's klt (0.5.0 when this was written) is older than any
        # client that can submit to it, so the default "enforce" gate refuses
        # every job (batch_runner_version_mismatch, exit 87). "warn" runs the
        # job anyway and records the skew in environment.remote; the requests
        # built here deliberately use only fields klt 0.5.0 understands
        # (measurements[].spice, no `expr`), and the record carries
        # runner_compatibility + a same-grid cross-check against the committed
        # ac record so a silently-ignored option would show up.
        request["batch"] = {"runner_version_check": RUNNER_VERSION_CHECK[0]}
    req_path = req_dir / f"{tag}-request.json"
    req_path.write_text(json.dumps(request, indent=2) + "\n")
    return req_path, tag


def run_klt_sim(req_path: Path, out_dir: Path, backend: str) -> dict:
    """Submit one request; return klt's parsed JSON report (gate on `status`, not exit code)."""
    out_dir = out_dir.resolve()  # klt resolves -o against each corner's own cwd: must be absolute
    out_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [*KLT_CMD, "sim", str(req_path), "-o", str(out_dir), "--backend", backend, "--format", "json"],
        capture_output=True, text=True,
    )
    (out_dir / f"{req_path.stem}.stderr.txt").write_text(proc.stderr)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise HarnessError(
            f"klt sim exit {proc.returncode}: no JSON report on stdout ({proc.stderr.strip()[:500]})"
        ) from exc


def _corner_values(report: dict) -> dict[tuple[str, float], dict]:
    out = {}
    for c in report.get("corners", []):
        vals = {m["name"]: m["value"] for m in c.get("measurements", [])}
        out[(c["process"], float(c["temperature_c"]))] = {
            "values": vals, "status": c.get("status"), "runtime_s": c.get("runtime_s"),
            "diagnostics": c.get("diagnostics", []), "vdd": (c.get("supply_v") or {}).get("vdd"),
        }
    return out


def icmr_row(corner: str, temp: float, info: dict) -> dict:
    v = info["values"]
    vdd = VDD_BY_CORNER[corner]
    need = [f"{p}_{label}" for label in ICMR_CMRR_FLOORS_DB for p in ("lo", "hi")] + [
        "vid_mid_v", "vout_mid_v", "iq_mid_a", "k_mid"]
    missing = [k for k in need if v.get(k) is None]
    if missing:
        raise HarnessError(f"icmr[{corner}/{temp:g}C]: missing measurements {missing} ({info['status']})")
    row = {"corner": corner, "temp_c": temp, "vdd_v": vdd}
    for label in ICMR_CMRR_FLOORS_DB:
        lo, hi = v[f"lo_{label}"], v[f"hi_{label}"]
        sfx = "" if label == "40db" else f"_{label}"
        row[f"icmr_low_v{sfx}"] = round(max(lo, 0.0), 4)
        row[f"icmr_high_v{sfx}"] = round(min(hi, vdd), 4)
        row[f"icmr_width_v{sfx}"] = round(max(0.0, min(hi, vdd) - max(lo, 0.0)), 4)
        if label == "40db":
            tol = 1e-6
            low_rail, high_rail = lo <= ICMR_RAIL_EPS_V, hi >= vdd - ICMR_RAIL_EPS_V
            row["low_limiter"] = "rail_0v" if low_rail else "input_stage"
            row["high_limiter"] = "rail_vdd" if high_rail else "input_stage"
            ok = row["icmr_low_v"] <= TARGET_ICMR_V[0] + tol and row["icmr_high_v"] >= TARGET_ICMR_V[1] - tol
            row["covers_target_window"] = int(ok)
            row["covers_0v73"] = int(row["icmr_low_v"] <= CONSUMER_SENSE_V + tol
                                     and row["icmr_high_v"] >= CONSUMER_SENSE_V - tol)
    row.update({
        "vid_mid_v": v["vid_mid_v"], "cmrr_mid_db": -20.0 * math.log10(max(v["k_mid"], 1e-30)),
        "vout_mid_v": v["vout_mid_v"],
        "iq_mid_a": abs(v["iq_mid_a"]), "elapsed_s": round(info["runtime_s"] or 0.0, 2),
    })
    return row


def cmrr_row(corner: str, temp: float, info: dict, cm_point: str) -> dict:
    v = info["values"]
    vdd = VDD_BY_CORNER[corner]
    need = [f"{p}_{label}_db" for label, _f in CMRR_SPOTS for p in ("adm", "acm")] + ["gbw_hz"]
    missing = [k for k in need if v.get(k) is None]
    if missing:
        raise HarnessError(f"cmrr[{corner}/{temp:g}C/{cm_point}]: missing measurements {missing} ({info['status']})")
    fixed = CMRR_CM_POINTS[cm_point][1]
    row = {"corner": corner, "temp_c": temp, "vdd_v": vdd, "cm_point": cm_point,
           "vcm_v": round(0.5 * vdd if fixed is None else fixed, 4)}
    for label, _f in CMRR_SPOTS:
        row[f"adm_{label}_db"] = v[f"adm_{label}_db"]
        row[f"acm_{label}_db"] = v[f"acm_{label}_db"]
        row[f"cmrr_{label}_db"] = v[f"adm_{label}_db"] - v[f"acm_{label}_db"]
    row["gbw_hz"] = v["gbw_hz"]
    row["elapsed_s"] = round(info["runtime_s"] or 0.0, 2)
    return row


def klt_fieldnames_cmrr() -> list[str]:
    cols = ["corner", "temp_c", "vdd_v", "cm_point", "vcm_v"]
    for label, _f in CMRR_SPOTS:
        cols += [f"adm_{label}_db", f"acm_{label}_db", f"cmrr_{label}_db"]
    return cols + ["gbw_hz", "elapsed_s"]


def latest_ac_csv(before_id: str) -> Path | None:
    """The newest committed -ac.csv older than this record: the cross-check reference."""
    cands = sorted(p for p in RECORDS_DIR.glob("*-ac.csv") if p.name.split("-ac.csv")[0] < before_id)
    return cands[-1] if cands else None


def crosscheck(ref_csv: Path, cmrr_mid_rows: list[dict], icmr_rows: list[dict]) -> dict:
    """Sanity check against the committed open-loop AC record at the same grid points.

    Adm_dc (new CMRR deck instance D) vs gain_dc_db, GBW vs gbw_hz, and the ICMR
    mid-point supply current vs iq_a. Not a substitute for the CMRR/ICMR
    figures themselves -- it shows the new decks reproduce the established AC
    bench's operating point and gain before their numbers are trusted.
    """
    ref = {(r["corner"], float(r["temp_c"])): r for r in csv.DictReader(ref_csv.open())}
    d_gain, d_gbw, d_iq, n = 0.0, 0.0, 0.0, 0
    for r in cmrr_mid_rows:
        a = ref.get((r["corner"], float(r["temp_c"])))
        if a is None:
            continue
        n += 1
        d_gain = max(d_gain, abs(r["adm_1hz_db"] - float(a["gain_dc_db"])))
        d_gbw = max(d_gbw, abs(r["gbw_hz"] / float(a["gbw_hz"]) - 1.0))
    n_iq = 0
    for r in icmr_rows:
        a = ref.get((r["corner"], float(r["temp_c"])))
        if a is None:
            continue
        n_iq += 1
        d_iq = max(d_iq, abs(r["iq_mid_a"] / float(a["iq_a"]) - 1.0))
    return {
        "reference_csv": f"sim/opamp-characterization/records/{ref_csv.name}",
        "cmrr_points_compared": n, "max_abs_adm_dc_minus_gain_dc_db": round(d_gain, 4),
        "max_rel_gbw_error": round(d_gbw, 5), "tolerance_gain_db": CROSSCHECK_TOL_GAIN_DB,
        "tolerance_gbw_frac": CROSSCHECK_TOL_GBW_FRAC,
        "icmr_points_compared": n_iq, "max_rel_iq_error": round(d_iq, 5),
        "tolerance_iq_frac": CROSSCHECK_TOL_IQ_FRAC,
        "ok": bool(n and d_gain <= CROSSCHECK_TOL_GAIN_DB and d_gbw <= CROSSCHECK_TOL_GBW_FRAC
                   and (not n_iq or d_iq <= CROSSCHECK_TOL_IQ_FRAC)),
    }


ANALYSES = {"ac": run_ac, "tran_sr": run_tran_sr, "dc_swing": run_dc_swing}
FIELDNAMES = {
    "ac": ["corner", "temp_c", "vdd_v", "vcm_v", "iq_a", "pq_w", "gain_dc_db",
           "gbw_hz", "phase_at_gbw_deg", "phase_margin_deg", "elapsed_s"],
    "tran_sr": ["corner", "temp_c", "vdd_v", "v_low_v", "v_high_v",
                "sr_rise_v_per_us", "sr_fall_v_per_us", "elapsed_s"],
    "dc_swing": ["corner", "temp_c", "vdd_v", "vout_min_v", "vout_max_v", "vpp_v",
                 "vpp_pct_of_vdd", "sweep_vout_min_v", "sweep_vout_max_v", "elapsed_s"],
    "icmr": ["corner", "temp_c", "vdd_v", "icmr_low_v", "icmr_high_v", "icmr_width_v",
             "low_limiter", "high_limiter", "covers_target_window", "covers_0v73",
             "icmr_low_v_30db", "icmr_high_v_30db", "icmr_width_v_30db",
             "icmr_low_v_50db", "icmr_high_v_50db", "icmr_width_v_50db",
             "vid_mid_v", "cmrr_mid_db", "vout_mid_v", "iq_mid_a", "elapsed_s"],
    "cmrr": klt_fieldnames_cmrr(),
}


def run_klt_analyses(klt_analyses, pdk, corners, temps, backend, req_dir, log_dir, snapshot_run_dir,
                     results, errors, klt_jobs) -> None:
    """Submit one `klt sim` request per (analysis[, CM point]) and fold the
    responses into `results`/`errors`. A failed submit is reported as errors;
    there is deliberately NO fallback to a local ngspice loop."""
    plan = []
    for a in klt_analyses:
        if a == "icmr":
            if ICMR_REQUEST_PER_CORNER:
                plan.extend(("icmr", None, VDD_BY_CORNER[c], [c]) for c in corners)
            else:
                plan.extend(("icmr", None, vdd, cs) for vdd, cs in vdd_groups(corners).items())
        else:
            plan.extend(("cmrr", cp, None, corners) for cp in CMRR_CM_POINTS)
    # Build every request first, then submit them concurrently (the jobs are
    # independent; this process only waits on S3 polls -- the compute is the
    # fleet's, and the fleet enforces its own concurrency/budget caps).
    prepared = []
    for analysis, cm_point, vdd_group, group_corners in plan:
        req_path, tag = build_klt_request(analysis, cm_point, vdd_group, pdk, group_corners, temps, req_dir, backend)
        shutil.copy(req_path, snapshot_run_dir / req_path.name)
        shutil.copy(req_path.with_name(f"{tag}-body.spice"), snapshot_run_dir / f"{tag}-body.spice")
        prepared.append((analysis, cm_point, group_corners, req_path, tag))

    def submit(item):
        _analysis, _cm, _gc, req_path, tag = item
        print(f"klt sim {tag} ({backend}) ...", file=sys.stderr)
        t0 = time.monotonic()
        # The fleet is shared and capped (BATCH_MAX_CONCURRENT_INSTANCES): a
        # submit refused for capacity is retried after a wait (still the fleet,
        # never a local fallback); any other failure is reported at once.
        exc = None
        for attempt in range(CAPACITY_RETRIES + 1):
            try:
                return run_klt_sim(req_path, log_dir / f"klt-{tag}", backend), time.monotonic() - t0, None
            except HarnessError as e:
                exc = e
                if "BATCH_MAX_CONCURRENT_INSTANCES" not in str(e) or attempt == CAPACITY_RETRIES:
                    break
                print(f"klt sim {tag}: fleet at capacity, retry {attempt + 1}/{CAPACITY_RETRIES} in {CAPACITY_WAIT_S}s",
                      file=sys.stderr)
                time.sleep(CAPACITY_WAIT_S)
        return None, time.monotonic() - t0, exc

    with ThreadPoolExecutor(max_workers=max(1, min(len(prepared), KLT_MAX_PARALLEL_SUBMITS))) as pool:
        outcomes = list(pool.map(submit, prepared))

    for (analysis, cm_point, group_corners, req_path, tag), (report, wall, exc) in zip(prepared, outcomes):
        if exc is not None:
            errors.append(f"{tag}: {exc}")
            print(f"{tag}: FAIL {exc}", file=sys.stderr)
            continue
        (log_dir / f"klt-{tag}-response.json").write_text(json.dumps(report, indent=2) + "\n")
        env = report.get("environment", {})
        klt_jobs.append({
            "tag": tag, "backend": backend, "status": report.get("status"),
            "corner_count": report.get("corner_count"), "wall_s": round(wall, 1),
            "remote": env.get("remote"),
            "diagnostic_counts": report.get("diagnostic_counts"),
            "request": f"sim/opamp-characterization/netlist-snapshots/{snapshot_run_dir.name}/{req_path.name}",
            "response": f"sim/opamp-characterization/records/{log_dir.name}/klt-{tag}-response.json",
        })
        if "error" in report:
            errors.append(f"{tag}: klt error: {report['error'].get('message')}")
            continue
        by_point = _corner_values(report)
        for corner in group_corners:
            for temp in temps:
                label = f"{tag}-{corner}-{temp:g}C"
                info = by_point.get((corner, float(temp)))
                if info is None:
                    errors.append(f"{label}: not in the klt response")
                    continue
                bad = [d for d in info["diagnostics"] if d.get("severity") == "error"]
                try:
                    if bad:
                        head = "; ".join(f"{d.get('code')}: {d.get('message')}"[:160] for d in bad[:2])
                        raise HarnessError(f"{head} (+{len(bad) - 2} more)" if len(bad) > 2 else head)
                    row = icmr_row(corner, temp, info) if analysis == "icmr" else cmrr_row(corner, temp, info, cm_point)
                except HarnessError as exc:
                    errors.append(f"{label}: {exc}")
                    print(f"{label:<28} FAIL {exc}", file=sys.stderr)
                    continue
                results[analysis].append(row)

    order = {c: i for i, c in enumerate(corners)}
    for a in klt_analyses:
        results[a].sort(key=lambda r: (r.get("cm_point", ""), order[r["corner"]], r["temp_c"]))


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--check-env", action="store_true")
    p.add_argument("--corners", default=",".join(DEFAULT_CORNERS))
    p.add_argument("--temps", default=",".join(str(t) for t in DEFAULT_TEMPS_C))
    p.add_argument("--analyses", default=",".join(DEFAULT_ANALYSES))
    p.add_argument("--backend", default=DEFAULT_KLT_BACKEND,
                   help="`klt sim` backend for the icmr/cmrr analyses (default: batch; local = single-point probe)")
    p.add_argument("--batch-runner-check", choices=("warn", "enforce"), default="warn",
                   help="klt batch.runner_version_check (default: warn -- the fleet image's klt is older than "
                        "any client that can submit to it; the skew is recorded in the record's klt_jobs)")
    p.add_argument("--klt-cmd", default=None,
                   help="klt invocation for icmr/cmrr (default: $KLT_CMD or `klt`); pin the fleet's version "
                        "with e.g. 'uvx --from klayout-tools==0.5.0 klt'")
    p.add_argument("--timeout-s", type=int, default=1200,
                   help="per-corner ngspice timeout (s) written into the icmr/cmrr klt requests (default 1200; "
                        "healthy points finish in 30-160 s, so a short value makes a stalled point fail fast)")
    p.add_argument("--keep-work", action="store_true")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    RUNNER_VERSION_CHECK[0] = args.batch_runner_check
    KLT_TIMEOUT_S[0] = args.timeout_s
    if args.klt_cmd:
        KLT_CMD[:] = shlex.split(args.klt_cmd)

    if args.check_env:
        return check_env()

    corners = [c.strip() for c in args.corners.split(",") if c.strip()]
    temps = [float(t) for t in args.temps.split(",") if t.strip()]
    analyses = [a.strip() for a in args.analyses.split(",") if a.strip()]
    for a in analyses:
        if a not in ANALYSES and a not in KLT_ANALYSES:
            print(f"ERROR: unknown analysis '{a}' (choices: {sorted([*ANALYSES, *KLT_ANALYSES])})", file=sys.stderr)
            return 1
    klt_analyses = [a for a in analyses if a in KLT_ANALYSES]
    ngspice_analyses = [a for a in analyses if a in ANALYSES]
    if klt_analyses and not klt_available():
        print("ERROR: klt not found on PATH (needed for --analyses icmr,cmrr; see --check-env)", file=sys.stderr)
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
    if ngspice_analyses and not ngspice:
        print("ERROR: ngspice not found on PATH", file=sys.stderr)
        return 1

    model_files = load_json(GMID_MODEL_FILES)
    for corner in corners:
        if corner not in model_files["corners"]:
            print(f"ERROR: corner '{corner}' not in {GMID_MODEL_FILES}", file=sys.stderr)
            return 1

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    record_id = f"{ts}-{git_sha(REPO_ROOT)}"
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
        for analysis in ngspice_analyses:
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

    klt_jobs: list[dict] = []
    klt_crosscheck = None
    if klt_analyses:
        n_klt_errors0 = len(errors)
        with tempfile.TemporaryDirectory(prefix="opamp-klt-") as req_tmp:
            run_klt_analyses(
                klt_analyses, pdk, corners, temps, args.backend, Path(req_tmp),
                log_dir, snapshot_run_dir, results, errors, klt_jobs,
            )
        # attempted units, like the ngspice loop above (failed units count; they are in `errors`)
        n_runs += sum(len(corners) * len(temps) * (len(CMRR_CM_POINTS) if a == "cmrr" else 1) for a in klt_analyses)
        if not len(errors) > n_klt_errors0 and "icmr" in klt_analyses and "cmrr" in klt_analyses:
            ref = latest_ac_csv(record_id)
            if ref is not None:
                mid_rows = [r for r in results["cmrr"] if r["cm_point"] == "mid"]
                klt_crosscheck = crosscheck(ref, mid_rows, results["icmr"])
                print(f"cross-check vs {ref.name}: {json.dumps(klt_crosscheck)}", file=sys.stderr)

    elapsed_total = time.monotonic() - t_start
    print(f"Completed {n_runs} runs ({len(errors)} failed) in {elapsed_total:.1f}s", file=sys.stderr)

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
        "git": {"sha": git_sha(REPO_ROOT)},
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
            **({"klt_backend": args.backend, "icmr_cmrr_floors_db": ICMR_CMRR_FLOORS_DB, "icmr_dv_v": ICMR_DV_V,
                "icmr_vstep_v": ICMR_VSTEP_V, "target_icmr_v": list(TARGET_ICMR_V),
                "consumer_sense_v": CONSUMER_SENSE_V,
                "cmrr_cm_points": {k: v[0] for k, v in CMRR_CM_POINTS.items()}}
               if klt_analyses else {}),
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
            **({"klt": first_line([*KLT_CMD, "--version"]), "klt_cmd": " ".join(KLT_CMD)} if klt_analyses else {}),
        },
        **({"klt_jobs": klt_jobs, "klt_crosscheck": klt_crosscheck} if klt_analyses else {}),
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
    print(f"  {log_dir.relative_to(REPO_ROOT)}/ (raw ngspice logs / klt responses and per-corner artifacts)")
    print(f"  {snapshot_run_dir.relative_to(REPO_ROOT)}/ (rendered deck snapshots)")

    if errors:
        print(f"\n{len(errors)} run(s) FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
