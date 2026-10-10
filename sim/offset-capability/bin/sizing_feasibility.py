#!/usr/bin/env python3
"""Matched-group sizing feasibility for the proposed offset allocation (issue #144).

Question: can enlarging the matched device groups (PMOS mirror XM3/XM4 and
input pair XM1/XM2) plausibly bring the open-loop input-referred offset sigma
to the DR-009 *proposed* allocation (sigma <= 0.275 mV) while the ratified
performance rows still hold? DR-009 stays proposed; spec/target-spec.md and
the canonical design (design/opamp_core.sch, design/netlist/opamp_core.spice)
are NOT modified by anything here.

Subcommands (all stdlib; only `op` runs a simulator, once, locally, one corner):

  bounds   simulator-free area bounds from the measured #107 attribution
           (records/20261009-attribution-summary.json): mirror-only floor,
           pair-only area factor, area-optimal combined factors, with the
           sampling (N=300) and model (Pelgrom vs measured) uncertainty bands.
  gmid     gm/ID-first: the inversion level each candidate's matched devices are
           predicted to sit at, read from the COMMITTED bare-device gm/ID sweep
           (sim/gm-id-characterization records) at the candidate's current
           density, before any candidate is simulated.
  gen      write the candidate netlists under ../candidates/ from the canonical
           netlist (geometry scaled per CANDIDATES, every MOS/passive W/L snapped
           to the 0.005 um grid and checked with design/bin/grid_check.py).
  op       ONE local ngspice -b run (tt, 27 C, VDD 1.8 V, unity-gain buffer at
           VCM 0.9 V) holding every candidate and the canonical netlist as
           separate subcircuit instances in the same deck. Single operating
           point, single corner: a debug probe, not a grid. Writes the per-device
           OP and the NEWLY DERIVED sensitivities and Pelgrom predictions for
           each candidate (never the baseline OP constants for a resized DUT).
  summarize  join the exploratory Monte Carlo campaigns and the fleet PVT
           records named in the plan into one append-only summary JSON.

The Monte Carlo and PVT runs themselves are NOT launched by this script: they
are `offset_probe.py campaign --netlist` (klt sim monte_carlo) and
`pvt_sweep.py --fleet --netlist` (klt sim corners) requests on the batch
fleet, listed with their budget in the predeclared plan file
(records/sizing-feasibility-plan-20261010.json).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
REPO = EXP.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "sim" / "lib"))
sys.path.insert(0, str(REPO / "design" / "bin"))
import pelgrom_handcalc as hc  # noqa: E402
import grid_check  # noqa: E402
from spice_harness import allocate_record_id, write_new  # noqa: E402

RECORDS = EXP / "records"
CAND_DIR = EXP / "candidates"
CANON = REPO / "design" / "netlist" / "opamp_core.spice"
ATTR_SUMMARY = RECORDS / "20261009-attribution-summary.json"
GMID_SWEEP = REPO / "sim" / "gm-id-characterization" / "records" / "20260909-062847-35a9d46-full-sweep.csv"
PLAN = RECORDS / "sizing-feasibility-plan-20261010.json"

GRID_UM = 0.005
TARGET_SIGMA_V = 0.275e-3          # DR-009 proposed (not ratified) allocation, kept as is
ALL_ON_TT_SIGMA_V = 8.583e-3       # #85 tt all-devices sigma (campaign-20261009-offset-mc300.md)
N_ATTR = 300                       # #107 samples per MOS group
HANDCALC_TOTAL_V = None            # filled from hc.calc() at run time

# Candidate set (bounded: 3 sizing candidates + 1 grid-only reference). Each
# scales W and L of a matched group by the same factor s (W/L, mult, and the
# XM6:XM3 = 10:1 mirror ratio preserved; gate area x s^2). The PMOS group is
# XM3/XM4 *and* XM6: XM6's Vsg is matched to XM3's to keep the first-stage
# drains balanced (systematic offset), so it scales with the mirror.
# The bias group XM5/XMB1/XM7 W 7.819 is off grid (owned by #120); every
# netlist here uses the nearest grid value 7.820 as a placeholder, which does
# not pre-empt #120's choice.
CANDIDATES = {
    "grid0": {"pmos_scale": 1, "pair_scale": 1, "mc": False,
              "why": "reference: canonical sizing snapped to the 0.005 um grid only "
                     "(4.634->4.635, 7.819->7.820); isolates the grid snap from the resizes"},
    "m2p1": {"pmos_scale": 2, "pair_scale": 1, "mc": True,
             "why": "mirror-only: PMOS group W,L x2 (area x4), pair unchanged; tests the "
                    "mirror-only path and exposes the input-pair floor"},
    "m2p2": {"pmos_scale": 2, "pair_scale": 2, "mc": True,
             "why": "balanced moderate: PMOS group and pair both W,L x2 (area x4 each)"},
    "m4p2": {"pmos_scale": 4, "pair_scale": 2, "mc": True,
             "why": "largest bounded step along the area-optimal direction (mirror area "
                    "factor ~ 5.7x the pair's, see `bounds`): PMOS x4 (area x16), pair x2 (area x4)"},
}
PMOS_GROUP = ("XM3", "XM4", "XM6")
PAIR_GROUP = ("XM1", "XM2")
BIAS_GROUP = ("XM5", "XMB1", "XM7")
DIFF = 0.29   # xschem sky130 diffusion extension (um) used for ad/as/pd/ps/nrd/nrs


def snap(x: float) -> float:
    return round(round(x / GRID_UM) * GRID_UM, 6)


def fmt(x: float) -> str:
    return f"{x:.6g}"


# ------------------------------------------------------------------ bounds --

def _attr() -> dict:
    g = json.loads(ATTR_SUMMARY.read_text())["groups"]
    return {k: g[k]["sigma_v"] for k in ("pair", "mirror", "stage2", "bias")}


def area_optimal(s_pair: float, s_mir: float, a_pair: float, a_mir: float, target: float,
                 rest: float = 0.0) -> dict:
    """Minimise k_p a_p + k_m a_m subject to s_p^2/k_p + s_m^2/k_m + rest^2 <= T^2
    (Pelgrom: group variance scales 1/area at a fixed operating point).
    Lagrange: k_i = s_i sqrt(lambda / a_i), total area = (sum s_i sqrt(a_i))^2 / T_eff^2."""
    t2 = target ** 2 - rest ** 2
    if t2 <= 0:
        return {"feasible": False, "reason": "fixed (non-scaled) terms alone exceed the target"}
    sq = s_pair * math.sqrt(a_pair) + s_mir * math.sqrt(a_mir)
    rl = sq / t2
    kp, km = s_pair * rl / math.sqrt(a_pair), s_mir * rl / math.sqrt(a_mir)
    return {"feasible": True, "k_pair": kp, "k_mirror": km, "area_um2": sq ** 2 / t2,
            "area_baseline_um2": a_pair + a_mir, "area_factor": sq ** 2 / t2 / (a_pair + a_mir)}


def bounds() -> dict:
    s = _attr()
    core = hc.parse_core()
    a_pair = 2 * core["XM1"]["w"] * core["XM1"]["l"] * core["XM1"]["mult"]
    a_mir = 2 * core["XM3"]["w"] * core["XM3"]["l"] * core["XM3"]["mult"]
    rest = math.hypot(s["stage2"], s["bias"])
    se = 1 / math.sqrt(2 * (N_ATTR - 1))     # relative standard error of a sigma, N = 300
    out = {"inputs": {"attribution": str(ATTR_SUMMARY.relative_to(REPO)), "group_sigma_v": s,
                      "target_sigma_v": TARGET_SIGMA_V, "target_status": "DR-009 proposed, not ratified",
                      "matched_gate_area_um2": {"pair_two_devices": a_pair, "mirror_two_devices": a_mir},
                      "sigma_rel_standard_error_N300": se,
                      "tag": "ESTIMATE (first-order Pelgrom area scaling at a fixed operating point)"}}
    # 1. mirror-only: even an infinitely large mirror leaves the pair (and the fixed terms).
    floor = math.sqrt(s["pair"] ** 2 + rest ** 2)
    out["mirror_only"] = {
        "floor_sigma_v": floor, "floor_over_target": floor / TARGET_SIGMA_V,
        "floor_band_2se_v": [floor * (1 - 2 * se), floor * (1 + 2 * se)],
        "statement": "with the mirror term driven to zero, sigma -> sigma_pair; the pair alone is "
                     f"{s['pair'] / TARGET_SIGMA_V:.1f}x the target, so no mirror size meets it"}
    # 2. pair-only area factor with the mirror term removed (lower bound on pair area).
    kp_min = (s["pair"] / math.sqrt(TARGET_SIGMA_V ** 2 - rest ** 2)) ** 2
    out["pair_area_factor_min"] = {
        "k": kp_min, "band_2se": [kp_min * (1 - 2 * se) ** 2, kp_min * (1 + 2 * se) ** 2],
        "note": "pair gate area multiplier needed even if the mirror contributed nothing"}
    # 3. area-optimal split (both groups scaled), central value and 2-SE band.
    cen = area_optimal(s["pair"], s["mirror"], a_pair, a_mir, TARGET_SIGMA_V, rest)
    lo = area_optimal(s["pair"] * (1 - 2 * se), s["mirror"] * (1 - 2 * se), a_pair, a_mir, TARGET_SIGMA_V, rest)
    hi = area_optimal(s["pair"] * (1 + 2 * se), s["mirror"] * (1 + 2 * se), a_pair, a_mir, TARGET_SIGMA_V, rest)
    out["area_optimal"] = {"central": cen, "low_2se": lo, "high_2se": hi,
                           "mirror_to_pair_factor_ratio": cen["k_mirror"] / cen["k_pair"]}
    # 4. model uncertainty: the hand calc under-predicts the pair by 43 % (#107). Using the
    #    hand calc's own pair/mirror instead of the measured split changes the answer by:
    c = hc.calc()
    hp, hm = c["group_sigma_v"]["pair"], c["group_sigma_v"]["mirror"]
    out["area_optimal_handcalc_split"] = area_optimal(hp, hm, a_pair, a_mir, TARGET_SIGMA_V, rest)
    out["area_optimal_handcalc_split"]["note"] = (
        "same optimisation with the Pelgrom hand-calc group sigmas (pair 1.77 mV, mirror 7.08 mV) "
        "instead of the measured ones: the model-uncertainty end of the range")
    # 5. operating-point lever on the mirror: input-referred mirror term ~ (gm3/gm1) sigma_VT3.
    gmid3 = hc.OP["gm3"] / hc.OP["id3"]
    out["mirror_gmid_lever"] = {
        "baseline_gm_over_id_3": gmid3,
        "reduction_if_gmid3_5": gmid3 / 5.0,
        "note": "lowering the mirror gm/ID (higher overdrive) divides the mirror term by "
                "gm/ID3_old/gm/ID3_new at constant area; even gm/ID = 5 (deep strong inversion, "
                f"~{2 / 5.0 * 1e3:.0f} mV overdrive) is a {gmid3 / 5.0:.1f}x reduction, and the mirror's "
                "Vsg rise is taken straight out of the ICMR upper edge (DR-002: 136 mV window at the "
                "worst corner) and the XM6 overdrive"}
    # 6. the reference points for the bounded candidates (measured-anchored scaling).
    out["candidates_area_scaling_estimate"] = {}
    for name, cd in CANDIDATES.items():
        kp, km = cd["pair_scale"] ** 2, cd["pmos_scale"] ** 2
        est = math.sqrt(s["pair"] ** 2 / kp + s["mirror"] ** 2 / km + rest ** 2)
        out["candidates_area_scaling_estimate"][name] = {
            "k_pair": kp, "k_mirror": km, "sigma_v": est, "over_target": est / TARGET_SIGMA_V}
    return out


# -------------------------------------------------------------------- gmid --

def _sweep_rows():
    with GMID_SWEEP.open() as f:
        return list(csv.DictReader(f))


def gmid_at_density(rows, device: str, l_um: float, id_per_sq: float, corner="tt", temp=27.0) -> dict:
    """gm/ID of the committed bare-device sweep (W = 2 um, |Vds| = 0.9 V) at the drain
    current per square `id_per_sq` = Id / (W/L), log-interpolated in Id. If the sweep has
    no row at this L, the nearest swept L <= l_um is used and flagged (long-channel proxy)."""
    ls = sorted({float(r["length_um"]) for r in rows if r["device"] == device})
    use_l = l_um if l_um in ls else max(x for x in ls if x <= l_um)
    sel = [r for r in rows if r["device"] == device and float(r["length_um"]) == use_l
           and r["corner"] == corner and float(r["temp_c"]) == temp and r["gm_id_per_v"]]
    sel.sort(key=lambda r: float(r["id_a"]))
    w_over_l = float(sel[0]["width_um"]) / use_l
    target_id = id_per_sq * w_over_l
    for a, b in zip(sel, sel[1:]):
        ia, ib = float(a["id_a"]), float(b["id_a"])
        if ia <= target_id <= ib and ia > 0:
            t = (math.log(target_id) - math.log(ia)) / (math.log(ib) - math.log(ia))
            ga, gb = float(a["gm_id_per_v"]), float(b["gm_id_per_v"])
            return {"device": device, "l_um_requested": l_um, "l_um_swept": use_l,
                    "proxy": use_l != l_um, "id_per_square_a": id_per_sq,
                    "gm_over_id": ga + t * (gb - ga), "bracket_rows_id_a": [ia, ib]}
    raise SystemExit(f"current density {id_per_sq} outside the swept range for {device} L={use_l}")


def gmid() -> dict:
    rows = _sweep_rows()
    core = hc.parse_core()
    i1, i3 = hc.OP["id1"], hc.OP["id3"]   # branch currents are set by the bias (unchanged)
    out = {"source": str(GMID_SWEEP.relative_to(REPO)), "basis": "tt / 27 C, |Vds| 0.9 V, Vsb 0",
           "note": "scaling W and L by the same factor keeps W/L and Id, hence Id per square; "
                   "a change in gm/ID comes only from L-dependent device physics", "candidates": {}}
    for name, cd in CANDIDATES.items():
        geo = candidate_geometry(core, cd)
        p, m = geo["XM1"], geo["XM3"]
        out["candidates"][name] = {
            "pair": gmid_at_density(rows, "nfet", p["l"], i1 / (p["w"] / p["l"])),
            "mirror": gmid_at_density(rows, "pfet", m["l"], i3 / (m["w"] / m["l"])),
        }
    return out


# --------------------------------------------------------------------- gen --

def candidate_geometry(core: dict, cd: dict) -> dict:
    out = {}
    for inst, g in core.items():
        if g["kind"] not in ("nfet", "pfet"):
            continue
        s = cd["pmos_scale"] if inst in PMOS_GROUP else cd["pair_scale"] if inst in PAIR_GROUP else 1
        out[inst] = {"kind": g["kind"], "w": snap(g["w"] * s), "l": snap(g["l"] * s), "mult": g["mult"]}
    return out


def candidate_netlist(name: str) -> str:
    cd = CANDIDATES[name]
    core = hc.parse_core()
    geo = candidate_geometry(core, cd)
    out = [f"** CANDIDATE netlist '{name}' for the issue #144 sizing-feasibility study -- NOT the canonical design.",
           "** Generated by sim/offset-capability/bin/sizing_feasibility.py gen from design/netlist/opamp_core.spice;",
           f"** {cd['why']}.",
           f"** pmos_scale={cd['pmos_scale']} (XM3/XM4/XM6 W and L), pair_scale={cd['pair_scale']} (XM1/XM2 W and L);",
           "** every W/L snapped to the 0.005 um grid; bias group W 7.819 -> 7.820 placeholder (owned by #120)."]
    for ln in hc_logical_lines(CANON.read_text()):
        toks = ln.split()
        if toks and toks[0] in geo:
            g = geo[toks[0]]
            w, l = g["w"], g["l"]
            rep = {"L": fmt(l), "W": fmt(w), "ad": fmt(w * DIFF), "as": fmt(w * DIFF),
                   "pd": fmt(2 * (w + DIFF)), "ps": fmt(2 * (w + DIFF)),
                   "nrd": fmt(DIFF / w), "nrs": fmt(DIFF / w)}
            toks = [f"{k}={rep[k]}" if "=" in t and (k := t.split("=")[0]) in rep else t for t in toks]
            ln = " ".join(toks)
        out.append(ln)
    return "\n".join(out) + "\n"


def hc_logical_lines(text: str) -> list[str]:
    lines: list[str] = []
    for ln in text.splitlines():
        if ln.startswith("+") and lines:
            lines[-1] += " " + ln[1:].strip()
        else:
            lines.append(ln.rstrip())
    return lines


def cand_path(name: str) -> Path:
    return CAND_DIR / f"opamp_core.{name}.spice"


def gen(check_only: bool = False) -> int:
    CAND_DIR.mkdir(exist_ok=True)
    bad = 0
    for name in CANDIDATES:
        text = candidate_netlist(name)
        v = grid_check.violations(text, classes=("passive", "mos"))
        if v:
            print(f"{name}: OFF GRID {v}", file=sys.stderr)
            bad += 1
        p = cand_path(name)
        if check_only:
            if not p.is_file() or p.read_text() != text:
                print(f"{p.relative_to(REPO)} differs from a regeneration", file=sys.stderr)
                bad += 1
            continue
        if p.exists() and p.read_text() != text:
            raise SystemExit(f"{p} exists with different content; candidates are immutable once run")
        p.write_text(text)
        print(p.relative_to(REPO))
    return 1 if bad else 0


# ---------------------------------------------------------------------- op --

OP_DEVICES = {"XM1": "nfet", "XM2": "nfet", "XM3": "pfet", "XM4": "pfet", "XM6": "pfet", "XM7": "nfet",
              "XMB1": "nfet", "XM5": "nfet"}
OP_PARAMS = ("id", "gm", "gds", "vgs", "vds", "vth", "vdsat", "cgg")
OP_NODES = ("out", "d1", "d2", "tail", "ibias")
VDD, VCM, TEMP = 1.8, 0.9, 27.0


def op_deck(pdk: Path, duts: dict[str, Path]) -> str:
    lines = ["* issue #144: ONE single-corner operating-point probe (tt, 27 C, VDD 1.8 V) of every",
             "* candidate and the canonical netlist, each wrapped as its own subcircuit and biased",
             "* identically (ideal 5 uA Iref, unity-gain buffer, VCM 0.9 V, 2 pF load). Not a grid.",
             ".option scale=1u", ".param mc_mm_switch=0", ".param mc_pr_switch=0",
             f'.include "{pdk}/libs.tech/ngspice/corners/tt.spice"',
             f'.include "{pdk}/libs.tech/ngspice/r+c/res_typical__cap_typical.spice"',
             f'.include "{pdk}/libs.tech/ngspice/r+c/res_typical__cap_typical__lin.spice"',
             f".temp {TEMP:g}", f"Vdd vdd 0 dc {VDD}", "Vss vss 0 dc 0"]
    for n, path in duts.items():
        lines += [f".subckt dut_{n} vdd vss inn inp out ibias", f'.include "{path}"', f".ends dut_{n}",
                  f"Xc_{n} vdd vss out_{n} inp_{n} out_{n} ibias_{n} dut_{n}",
                  f"Iref_{n} vdd ibias_{n} dc 5u", f"Vinp_{n} inp_{n} 0 dc {VCM}", f"Cl_{n} out_{n} 0 2p"]
    lines += [".control", "op"]
    for n in duts:
        for node in OP_NODES:
            lines.append(f"echo OPV {n} {node} $&v(xc_{n}.{node})" if node not in ("out", "ibias")
                         else f"echo OPV {n} {node} $&v({node}_{n})")
        for inst, kind in OP_DEVICES.items():
            dev = f"m.xc_{n}.{inst.lower()}.msky130_fd_pr__{kind}_01v8"
            for prm in OP_PARAMS:
                lines.append(f"echo OPD {n} {inst} {prm} $&@{dev}[{prm}]")
        lines.append(f"echo OPI {n} $&i(vdd)")
    lines += [".endc", ".end"]
    return "\n".join(lines) + "\n"


def parse_op(stdout: str) -> dict:
    out: dict[str, dict] = {}
    for ln in stdout.splitlines():
        t = ln.split()
        if not t or t[0] not in ("OPV", "OPD"):
            continue
        try:
            if t[0] == "OPV":
                out.setdefault(t[1], {"nodes": {}, "dev": {}})["nodes"][t[2]] = float(t[3])
            else:
                out.setdefault(t[1], {"nodes": {}, "dev": {}})["dev"].setdefault(t[2], {})[t[3]] = float(t[4])
        except (IndexError, ValueError):
            raise SystemExit(f"unparseable OP line: {ln!r}")
    return out


def pelgrom_op(dev: dict) -> dict:
    """The OP keys pelgrom_handcalc.calc() consumes, from THIS netlist's own OP."""
    return {"id1": dev["XM1"]["id"], "gm1": dev["XM1"]["gm"], "gds2": dev["XM2"]["gds"],
            "id3": abs(dev["XM3"]["id"]), "gm3": dev["XM3"]["gm"], "gds4": dev["XM4"]["gds"],
            "id6": abs(dev["XM6"]["id"]), "gm6": dev["XM6"]["gm"],
            "id7": dev["XM7"]["id"], "gm7": dev["XM7"]["gm"]}


def derive(name: str, path: Path, opn: dict, root: Path, attr: dict, base_calc: dict) -> dict:
    dev, nodes = opn["dev"], opn["nodes"]
    po = pelgrom_op(dev)
    c = hc.calc(root, op=po, core_path=path)
    g = c["group_sigma_v"]
    bg = base_calc["group_sigma_v"]
    # measured-anchored estimate: #107's measured group sigma x (candidate / baseline) hand-calc ratio.
    anchored = {k: attr[k] * (g[k] / bg[k]) if bg[k] else 0.0 for k in ("pair", "mirror", "stage2", "bias")}
    core = hc.parse_core(path)
    cgg = lambda i: abs(dev[i]["cgg"])  # noqa: E731
    vsg3 = abs(dev["XM3"]["vgs"])
    return {
        "netlist": str(path.relative_to(REPO)),
        "geometry": {i: core[i] for i in ("XM1", "XM3", "XM6", "XM7", "XMB1")},
        "gate_area_um2": {
            "pair_two_devices": 2 * core["XM1"]["w"] * core["XM1"]["l"],
            "mirror_two_devices": 2 * core["XM3"]["w"] * core["XM3"]["l"],
            "xm6_total": core["XM6"]["w"] * core["XM6"]["l"] * core["XM6"]["mult"],
            "all_mos_total": sum(v["w"] * v["l"] * v["mult"] for v in core.values() if v["kind"] in ("nfet", "pfet")),
        },
        "op": {"nodes": nodes, "devices": dev, "i_vdd_a": None},
        "gm_over_id": {"XM1": dev["XM1"]["gm"] / dev["XM1"]["id"], "XM3": dev["XM3"]["gm"] / abs(dev["XM3"]["id"]),
                       "XM6": dev["XM6"]["gm"] / abs(dev["XM6"]["id"]), "XM7": dev["XM7"]["gm"] / dev["XM7"]["id"]},
        "sensitivities": {
            "note": "input-referred Vos per unit threshold shift of one device, from this netlist's own OP",
            "pair_dVos_dVT1": 1.0,
            "mirror_dVos_dVT3": po["gm3"] / po["gm1"],
            "stage2_dVos_dVT6": 1.0 / c["first_stage_gain_A1"],
            "first_stage_gain_A1": c["first_stage_gain_A1"],
        },
        "pelgrom_handcalc_sigma_v": {**g, "total": c["total_sigma_v"]},
        "measured_anchored_estimate_sigma_v": {**anchored,
                                               "total": math.sqrt(sum(v * v for v in anchored.values()))},
        "capacitance_estimate_f": {
            "note": "BSIM4 cgg at the OP (gate total); the mirror node (d1) holds cgg3+cgg4; the "
                    "second-stage input node (d2) holds cgg6 (all 10 fingers) -- estimates, the AC "
                    "fleet bench is the measurement",
            "d1_cgg3_plus_cgg4": cgg("XM3") + cgg("XM4"), "d2_cgg6": cgg("XM6"),
            "input_cgg1": cgg("XM1"),
            "mirror_pole_estimate_hz": dev["XM3"]["gm"] / (2 * math.pi * (cgg("XM3") + cgg("XM4"))),
        },
        "headroom": {
            "vsg3_v": vsg3, "vth3_v": abs(dev["XM3"]["vth"]),
            "vsg6_v": abs(dev["XM6"]["vgs"]), "vdsat6_v": abs(dev["XM6"]["vdsat"]),
            "v_d1_minus_v_d2_v": nodes["d1"] - nodes["d2"],
            "pair_sat_margin_v": dev["XM1"]["vds"] - dev["XM1"]["vdsat"],
            "icmr_upper_edge_estimate_v": VDD - vsg3 + abs(dev["XM1"]["vth"]),
            "note": "ICMR upper edge ~ VDD - Vsg3 + Vth1 (pair enters triode); tt/27 C only",
        },
        # buffer: out = inn, so V(inp) - V(inn) = VCM - V(out) is the systematic input offset
        "systematic_vos_estimate_v": VCM - nodes["out"],
    }


def op(args) -> int:
    root = hc.pdk_root()
    ngspice = shutil.which("ngspice")
    if not ngspice:
        raise SystemExit("ngspice not on PATH")
    duts = {"canonical": CANON, **{n: cand_path(n) for n in CANDIDATES}}
    for n, p in duts.items():
        if not p.is_file():
            raise SystemExit(f"missing netlist {p} (run `gen` first)")
    RECORDS.mkdir(exist_ok=True)
    rid = allocate_record_id(RECORDS, "sizing144-op")
    deck = op_deck(root, duts)
    with tempfile.TemporaryDirectory(prefix="sizing144-op-") as tmp:
        shutil.copy(REPO / "sim" / "gm-id-characterization" / "spiceinit", Path(tmp) / ".spiceinit")
        (Path(tmp) / "op.spice").write_text(deck)
        proc = subprocess.run([ngspice, "-b", "op.spice"], cwd=tmp, capture_output=True, text=True, timeout=300)
    write_new(RECORDS / f"{rid}.deck.spice", deck.replace(str(REPO) + "/", "").replace(str(root), "$PDK_ROOT/sky130A"))
    write_new(RECORDS / f"{rid}.ngspice.log", proc.stdout + "\n--- stderr ---\n" + proc.stderr)
    if proc.returncode != 0:
        raise SystemExit(f"ngspice exit {proc.returncode}; see {rid}.ngspice.log")
    parsed = parse_op(proc.stdout)
    attr = _attr()
    base_calc = hc.calc(root)
    canon_check = {k: (pelgrom_op(parsed["canonical"]["dev"])[k], hc.OP[k]) for k in hc.OP}
    res = {"record_id": rid, "kind": "single-corner operating-point probe (local ngspice -b, one run)",
           "conditions": {"corner": "tt", "temp_c": TEMP, "vdd_v": VDD, "vcm_v": VCM, "iref_a": 5e-6,
                          "bench": "unity-gain buffer, 2 pF"},
           "ngspice": (proc.stdout.split("\n")[0] if proc.stdout else ""),
           "pdk_root": str(root), "dut_sha256": {n: _sha(p) for n, p in duts.items()},
           "canonical_op_vs_pelgrom_constants": canon_check,
           "candidates": {n: derive(n, p, parsed[n], root, attr, base_calc) for n, p in duts.items()}}
    write_new(RECORDS / f"{rid}.json", json.dumps(res, indent=2) + "\n")
    print(rid)
    for n, r in res["candidates"].items():
        a, h = r["measured_anchored_estimate_sigma_v"], r["pelgrom_handcalc_sigma_v"]
        print(f"{n:9s} gm/ID1={r['gm_over_id']['XM1']:5.2f} gm/ID3={r['gm_over_id']['XM3']:5.2f} "
              f"gm3/gm1={r['sensitivities']['mirror_dVos_dVT3']:.3f} A1={r['sensitivities']['first_stage_gain_A1']:.1f} "
              f"hand={h['total'] * 1e3:.3f} mV anchored={a['total'] * 1e3:.3f} mV "
              f"fp_mirror~{r['capacitance_estimate_f']['mirror_pole_estimate_hz'] / 1e6:.0f} MHz "
              f"ICMR+~{r['headroom']['icmr_upper_edge_estimate_v']:.3f} V Vos_sys={r['systematic_vos_estimate_v'] * 1e3:+.3f} mV")
    return 0


def _sha(p: Path) -> str:
    import hashlib
    return "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------- summarize --

PVT_RECORDS = REPO / "sim" / "opamp-characterization" / "records"
# Ratified/proposed §2 rows the candidates are graded against (UNCHANGED targets).
TARGETS = {"gain_dc_db_min": 60.0, "gbw_hz_min": 16e6, "pm_deg_min": 60.0, "sr_v_per_us": 20.0,
           "swing_vpp_ss_m40_target_v": 1.39}


def _csv(path: Path) -> list[dict]:
    with path.open() as f:
        return [{k: (float(v) if k not in ("corner",) else v) for k, v in r.items()} for r in csv.DictReader(f)]


def pvt_metrics(record_id: str) -> dict:
    rec = json.loads((PVT_RECORDS / f"{record_id}.json").read_text())
    ac = _csv(PVT_RECORDS / f"{record_id}-ac.csv")
    sr = _csv(PVT_RECORDS / f"{record_id}-tran-sr.csv")
    sw = _csv(PVT_RECORDS / f"{record_id}-dc-swing.csv")
    worst = lambda rows, k, f=min: f(rows, key=lambda r: r[k])  # noqa: E731
    w = lambda r: f"{r['corner']}/{r['temp_c']:g}C"  # noqa: E731
    out = {"record_id": record_id, "dut_sha256": rec["dut"]["sha256"], "n_failed": rec["matrix"]["n_failed"],
           "n_rows": {"ac": len(ac), "tran_sr": len(sr), "dc_swing": len(sw)},
           "jobs": [(j["tag"], (j.get("remote") or {}).get("job_id")) for j in rec.get("klt_jobs", [])]}
    for key, rows, col, f in (("gain_dc_db_min", ac, "gain_dc_db", min), ("gbw_hz_min", ac, "gbw_hz", min),
                              ("pm_deg_min", ac, "phase_margin_deg", min),
                              ("sr_rise_min", sr, "sr_rise_v_per_us", min), ("sr_fall_min", sr, "sr_fall_v_per_us", min),
                              ("vpp_min", sw, "vpp_v", min), ("pq_w_max", ac, "pq_w", max)):
        if rows:
            r = worst(rows, col, f)
            out[key] = {"value": r[col], "at": w(r)}
    tt = [r for r in ac if r["corner"] == "tt" and r["temp_c"] == 27.0]
    if tt:
        out["tt27"] = {k: tt[0][k] for k in ("gain_dc_db", "gbw_hz", "phase_margin_deg", "pq_w", "iq_a")}
    ssm = [r for r in sw if r["corner"] == "ss" and r["temp_c"] == -40.0]
    if ssm:
        out["swing_ss_m40"] = {k: ssm[0][k] for k in ("vout_min_v", "vout_max_v", "vpp_v")}
    return out


def mc_metrics(label: str) -> dict | None:
    reps = sorted(RECORDS.glob(f"*campaign-{label}-*.campaign.json"))
    if not reps:
        return None
    rep = json.loads(reps[-1].read_text())
    tt = rep["corners"]["tt"]
    se = 1 / math.sqrt(2 * (tt["n_ok"] - 1)) if tt["n_ok"] and tt["n_ok"] > 1 else None
    return {"campaign": reps[-1].name, "dut": rep["dut"], "base_seed": rep["base_seed"], "n_requested": tt["n_requested"],
            "n_ok": tt["n_ok"], "n_failed": tt["n_failed"], "failure_reasons": tt["failure_reasons"],
            "mean_v": tt["mean_v"], "sigma_v": tt["sigma_v"], "min_v": tt["min_v"], "max_v": tt["max_v"],
            "sigma_rel_se": se, "attempts": rep["attempts"],
            "label": "EXPLORATORY (N=100, tt / 27 C / 1.8 V only); not an N>=300 + corners result"}


CANON_TT_C0 = "20261009-143703-offset-mc300-ttssff-tt-c0-b49127"   # #85 tt chunk 0, seed 20261085


def _vos_by_index(summary_json: Path) -> dict[int, float]:
    import offset_probe as op
    meta = json.loads(summary_json.read_text())
    payload = json.loads((summary_json.parent / f"{meta['record_id']}.klt.json").read_text())
    return {s["monte_carlo"]["sample_index"]: s["vos_v"] for s in op.extract_samples(payload, "offset") if s["ok"]}


def paired_vs_canonical(mc: dict) -> dict | None:
    """Same per-sample seeds as #85's tt chunk 0 (base seed 20261085): sigma ratio on the
    common samples and the Pearson correlation (how far the draws stay aligned after resizing)."""
    import attribution
    rid = next((a["record_id"] for a in reversed(mc["attempts"]) if a["got_samples"]), None)
    if rid is None:
        return None
    cand = _vos_by_index(RECORDS / f"{rid}.summary.json")
    base = _vos_by_index(RECORDS / f"{CANON_TT_C0}.summary.json")
    idx = sorted(set(cand) & set(base))
    if len(idx) < 3:
        return None
    sd = lambda v: math.sqrt(math.fsum((x - math.fsum(v) / len(v)) ** 2 for x in v) / (len(v) - 1))  # noqa: E731
    c, b = [cand[i] for i in idx], [base[i] for i in idx]
    return {"canonical_record": CANON_TT_C0, "n_common": len(idx), "sigma_canonical_v": sd(b),
            "sigma_candidate_v": sd(c), "sigma_ratio": sd(c) / sd(b), "pearson": attribution.pearson(c, b)}


def summarize(args) -> int:
    plan = json.loads(PLAN.read_text())
    ops = sorted(RECORDS.glob("*-sizing144-op.json"))
    opr = json.loads(ops[-1].read_text()) if ops else None
    out = {"plan": str(PLAN.relative_to(REPO)), "op_record": opr and opr["record_id"],
           "targets_unchanged": TARGETS, "offset_target_sigma_v": TARGET_SIGMA_V,
           "bounds": bounds(), "candidates": {}}
    for name in ["canonical", *CANDIDATES]:
        entry: dict = {}
        if opr and name in opr["candidates"]:
            c = opr["candidates"][name]
            entry["op"] = {k: c[k] for k in ("gm_over_id", "sensitivities", "pelgrom_handcalc_sigma_v",
                                             "measured_anchored_estimate_sigma_v", "capacitance_estimate_f",
                                             "headroom", "gate_area_um2", "systematic_vos_estimate_v")}
        pv = (args.pvt or {}).get(name)
        if pv:
            entry["pvt"] = pvt_metrics(pv)
        mc = mc_metrics(plan["monte_carlo"]["labels"][name]) if name in plan["monte_carlo"]["labels"] else None
        if mc:
            mc["paired_with_canonical_first_100"] = paired_vs_canonical(mc)
            entry["mc"] = mc
            entry["mc"]["over_target"] = mc["sigma_v"] / TARGET_SIGMA_V if mc["sigma_v"] else None
        out["candidates"][name] = entry
    rid = allocate_record_id(RECORDS, "sizing144-summary")
    write_new(RECORDS / f"{rid}.json", json.dumps(out, indent=2) + "\n")
    print(rid)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("bounds")
    sub.add_parser("gmid")
    g = sub.add_parser("gen")
    g.add_argument("--check", action="store_true", help="verify committed candidates equal a regeneration")
    sub.add_parser("op")
    s = sub.add_parser("summarize")
    s.add_argument("--pvt", type=json.loads, default=None, help='JSON {"name": "pvt record id"} override')
    a = ap.parse_args(argv)
    if a.cmd == "bounds":
        print(json.dumps(bounds(), indent=2))
        return 0
    if a.cmd == "gmid":
        print(json.dumps(gmid(), indent=2))
        return 0
    if a.cmd == "gen":
        return gen(check_only=a.check)
    if a.cmd == "op":
        return op(a)
    return summarize(a)


if __name__ == "__main__":
    sys.exit(main())
