#!/usr/bin/env python3
"""Simulator-free Pelgrom hand calculation of the open-loop input-referred
offset sigma, per device group (issue #107). Measured data are NOT used here.

Inputs
  * Mismatch coefficients: read from the pinned PDK's model files (the binned
    `*__tt.pm3.spice` expressions `vth0 = {... MC_MM_SWITCH*AGAUSS(0,1,1)*
    (<slope>/sqrt(l*w*mult))}` and `toxe = {...}`, and the `*__mismatch.corner
    .spice` slope values) for the bin that contains each drawn W/L.
  * Drawn W/L/mult: design/netlist/opamp_core.spice (parsed).
  * Nominal operating point (gm, Id, gds): the OP_* constants below, taken from
    ONE nominal ngspice `.op` of the committed netlist (tt, 27 C, 1.8 V,
    Vd = +151 uV = the systematic baseline, so v(out) = 0.9008 V). They are
    the only simulator-derived inputs; the mismatch statistics are not.

Model (first order, each device independent, sigma_VT = s_vt/sqrt(W L mult),
relative beta error from the toxe term sigma_b = s_tox/sqrt(W L mult), since
toxe = toxe0 (1 + AGAUSS s_tox/sqrt(WL mult)) and beta ~ Cox ~ 1/toxe):
  pair   : 2 [ sigma_VT1^2 + (Id/gm1)^2 sigma_b1^2 ]
  mirror : (gm3/gm1)^2 * 2 [ sigma_VT3^2 + (Id/gm3)^2 sigma_b3^2 ]
  stage2 : (1/A1)^2 [ sigma_VT6^2 + (Id/gm6)^2 sigma_b6^2
                      + (Id/gm6)^2 sigma_eps7^2 ],  A1 = gm1/(gds2+gds4),
           sigma_eps7 = relative error of the M7:MB1 mirror ratio
                      = sqrt( (gm7/Id7)^2 (sigma_VT7^2 + sigma_VTB1^2)
                              + sigma_b7^2 + sigma_bB1^2 )   (bias group, see below)
  bias   : the M7:MB1 ratio error above, referred to the input through M6 and
           A1 (it is reported as part of `stage2+bias`; the split is by device
           mismatch source: M6 terms -> stage2, M7/MB1 -> bias). M5 (tail)
           mismatch changes only the tail current, a common-mode quantity to
           first order, so its contribution is taken as 0.
  passives: Rz and Cc carry no DC current, so 0 at DC.
Omitted on purpose (so the calculation is a first-order bound, not a fit): the
`voff` and (pfet) `nfactor` mismatch terms, which act in moderate/weak
inversion (the mirror pfets run at Vsg - |Vth| = ~40 mV), the dependence of
VT on toxe, finite-gain/gds corrections to the pair terms, and the Id/gm
variation across the sample.

Predeclared agreement tolerance (written before the attribution results were
read; judgement, not fitted):
  * total: |calc - measured| / measured <= 25 %. Basis: the sampling error of a
    sigma from N = 300 is 1/sqrt(2 (N-1)) = 4.1 % (1 sigma), so 8.2 % at 2
    sigma; the remaining ~17 % is allowance for the omitted voff/nfactor terms
    and for taking gm/Id from one nominal operating point.
  * per group with predicted sigma >= 0.5 mV: same 25 % ... widened to 30 % for
    a single group (a group sigma is a difference of the total and so loses the
    cancellation of omitted terms).
  * per group with predicted sigma < 0.5 mV: measured sigma < 0.5 mV (absolute).
Usage: pelgrom_handcalc.py [--json]
"""
from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
CORE = REPO / "design" / "netlist" / "opamp_core.spice"
PDK_JSON = REPO / "sim" / "opamp-characterization" / "pdk.json"
SPICE = "libs.ref/sky130_fd_pr/spice"

# Nominal operating point (see module docstring). Device-level totals as ngspice
# reports them for the m-scaled instances; per-side first-stage devices m=1.
OP_SOURCE = ("one local ngspice .op, tt, 27 C, VDD 1.8 V, Iref 5 uA, Vd = +151 uV, "
             "netlist design/netlist/opamp_core.spice at repo commit 0a8d35d")
OP = {
    "id1": 4.715665e-06, "gm1": 8.341725e-05, "gds2": 4.898424e-07,
    "id3": 4.715664e-06, "gm3": 6.682710e-05, "gds4": 1.209336e-06,
    "id6": 5.130935e-05, "gm6": 7.153998e-04,
    "id7": 5.130935e-05, "gm7": 9.405352e-04,
}
AGREE_TOTAL = 0.25
AGREE_GROUP = 0.30
SMALL_GROUP_MV = 0.5


def pdk_root() -> Path:
    if os.environ.get("PDK_ROOT"):
        return Path(os.environ["PDK_ROOT"]) / "sky130A"
    exe = shutil.which("volare")
    if exe:
        out = subprocess.run([exe, "path", "--pdk", "sky130", json.loads(PDK_JSON.read_text())["open_pdks_commit"]],
                             capture_output=True, text=True)
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip()) / "sky130A"
    pin = json.loads(PDK_JSON.read_text())
    return Path(pin["default_pdk_root"]).expanduser() / "sky130A"


def parse_core() -> dict[str, dict]:
    """instance -> {kind, w, l, mult} (um) from the core netlist."""
    lines: list[str] = []
    for ln in CORE.read_text().splitlines():
        if ln.startswith("+") and lines:
            lines[-1] += " " + ln[1:].strip()
        else:
            lines.append(ln)
    out = {}
    for ln in lines:
        if not ln.startswith("X"):
            continue
        t = ln.split()
        kv = {k.lower(): float(v) for k, v in (x.split("=") for x in t if "=" in x and re.match(r"[A-Za-z]+=[-\d.e+]+$", x))}
        kind = "nfet" if "nfet_01v8" in ln else "pfet" if "pfet_01v8" in ln else "other"
        out[t[0]] = {"kind": kind, "w": kv.get("w"), "l": kv.get("l"), "mult": kv.get("mult", 1.0)}
    return out


def bin_slopes(root: Path, kind: str, w_um: float, l_um: float) -> dict:
    """Mismatch slope parameter names/values of the model bin containing W/L."""
    dev = f"sky130_fd_pr__{kind}_01v8"
    pm3 = (root / SPICE / f"{dev}__tt.pm3.spice").read_text()
    corner = (root / SPICE / f"{dev}__mismatch.corner.spice").read_text()
    vals = {m.group(1): float(m.group(2)) for m in re.finditer(r"\.param\s+(\w+)\s*=\s*([-\d.e+]+)", corner)}
    for blk in re.split(r"\n(?=\.model )", pm3):
        m = re.search(r"lmin\s*=\s*([\d.e+-]+)\s+lmax\s*=\s*([\d.e+-]+)\s+wmin\s*=\s*([\d.e+-]+)\s+wmax\s*=\s*([\d.e+-]+)", blk)
        if not m:
            continue
        lmin, lmax, wmin, wmax = map(float, m.groups())
        if lmin <= l_um * 1e-6 < lmax and wmin <= w_um * 1e-6 < wmax:
            names = {}
            for par in ("vth0", "toxe"):
                mm = re.search(par + r"\s*=\s*\{[^{}]*?MC_MM_SWITCH\*AGAUSS\(0,1\.0,1\)\*\([^{}]*?(" + dev + r"__\w+_slope\d*)/sqrt", blk)
                names[par] = mm.group(1)
            return {"bin": blk.split("\n")[0].strip(), "vth0_name": names["vth0"], "s_vt": vals[names["vth0"]],
                    "toxe_name": names["toxe"], "s_tox": vals[names["toxe"]]}
    raise SystemExit(f"no model bin for {kind} W={w_um} L={l_um}")


def device_sigmas(root: Path, geom: dict) -> dict:
    area = geom["w"] * geom["l"] * geom["mult"]
    c = bin_slopes(root, geom["kind"], geom["w"], geom["l"])
    return {**c, "area_um2": area, "sigma_vt_v": c["s_vt"] / math.sqrt(area),
            "sigma_beta_rel": c["s_tox"] / math.sqrt(area)}


def calc(root: Path | None = None, op: dict | None = None) -> dict:
    root = root or pdk_root()
    op = op or OP
    core = parse_core()
    d = {n: device_sigmas(root, core[n]) for n in ("XM1", "XM3", "XM6", "XM7", "XMB1")}
    g = {}
    # input pair (two devices)
    p = d["XM1"]
    g["pair"] = math.sqrt(2 * (p["sigma_vt_v"] ** 2 + (op["id1"] / op["gm1"] * p["sigma_beta_rel"]) ** 2))
    # mirror (two devices), referred through gm3/gm1
    m = d["XM3"]
    g["mirror"] = (op["gm3"] / op["gm1"]) * math.sqrt(
        2 * (m["sigma_vt_v"] ** 2 + (op["id3"] / op["gm3"] * m["sigma_beta_rel"]) ** 2))
    a1 = op["gm1"] / (op["gds2"] + op["gds4"])
    s6 = d["XM6"]
    # M6 own terms (stage2) and M7:MB1 ratio error (bias), both seen at d2 via Id/gm6, then /A1
    stage2_d2 = math.sqrt(s6["sigma_vt_v"] ** 2 + (op["id6"] / op["gm6"] * s6["sigma_beta_rel"]) ** 2)
    n7, nb = d["XM7"], d["XMB1"]
    eps7 = math.sqrt((op["gm7"] / op["id7"]) ** 2 * (n7["sigma_vt_v"] ** 2 + nb["sigma_vt_v"] ** 2)
                     + n7["sigma_beta_rel"] ** 2 + nb["sigma_beta_rel"] ** 2)
    bias_d2 = op["id6"] / op["gm6"] * eps7
    g["stage2"] = stage2_d2 / a1
    g["bias"] = bias_d2 / a1
    g["passives"] = 0.0
    total = math.sqrt(sum(v ** 2 for v in g.values()))
    return {"pdk_root": str(root), "op_source": OP_SOURCE, "op": op, "first_stage_gain_A1": a1,
            "eps7_ratio_sigma_rel": eps7, "devices": d, "group_sigma_v": g, "total_sigma_v": total,
            "tolerance": {"total_rel": AGREE_TOTAL, "group_rel": AGREE_GROUP, "small_group_abs_mv": SMALL_GROUP_MV}}


def agreement(calc_out: dict, measured_total_v: float, measured_group_v: dict) -> dict:
    tol = calc_out["tolerance"]
    res = {"total": {"calc_mv": calc_out["total_sigma_v"] * 1e3, "measured_mv": measured_total_v * 1e3,
                     "rel_diff": (calc_out["total_sigma_v"] - measured_total_v) / measured_total_v}}
    res["total"]["agrees"] = abs(res["total"]["rel_diff"]) <= tol["total_rel"]
    for gname, c in calc_out["group_sigma_v"].items():
        mv = measured_group_v.get(gname)
        if mv is None:
            continue
        if c * 1e3 < tol["small_group_abs_mv"]:
            ok, rel = mv * 1e3 < tol["small_group_abs_mv"], None
        else:
            rel = (c - mv) / mv
            ok = abs(rel) <= tol["group_rel"]
        res[gname] = {"calc_mv": c * 1e3, "measured_mv": mv * 1e3, "rel_diff": rel, "agrees": ok}
    return res


def main() -> int:
    out = calc()
    if "--json" in sys.argv:
        print(json.dumps(out, indent=2))
        return 0
    for n, v in out["devices"].items():
        print(f"{n}: {v['bin']}  W*L*mult={v['area_um2']:.4g} um2  {v['vth0_name']}={v['s_vt']:g}  "
              f"sigma_VT={v['sigma_vt_v']*1e3:.3f} mV  {v['toxe_name']}={v['s_tox']:g}  sigma_beta/beta={v['sigma_beta_rel']*100:.3f} %")
    print(f"A1 = {out['first_stage_gain_A1']:.1f}   eps7 = {out['eps7_ratio_sigma_rel']*100:.3f} %")
    for k, v in out["group_sigma_v"].items():
        print(f"  {k:9s} {v*1e3:7.3f} mV (input-referred, 1 sigma)")
    print(f"  TOTAL     {out['total_sigma_v']*1e3:7.3f} mV")
    return 0


if __name__ == "__main__":
    sys.exit(main())
