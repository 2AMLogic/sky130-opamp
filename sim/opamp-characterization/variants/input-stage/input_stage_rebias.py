#!/usr/bin/env python3
"""Input-stage low-headroom re-bias candidate (issue #359).

Simulator-free half of the experiment (the `op` subcommand is the ONE local
single-unit probe the host rules allow; it is not a record).  `sizing` prints
the gm/ID sizing replay, the per-corner overdrive/threshold table and the
hand-calculated ceilings of PLAN.md; `generate` writes the variant DUT
netlist; `check` verifies the file on disk against the generator and the
canonical netlist; `pelgrom` runs the offset hand calculation of
sim/offset-capability/bin/pelgrom_handcalc.py against the variant geometry
and the `op`-measured operating point.

Candidate (a), tag `icmr-rebias`: the input stage is re-biased at UNCHANGED
currents by two grouped width moves, everything else copied verbatim from
design/netlist/opamp_core.spice (DR-013 widths):

  XM1, XM2 (nfet L=1.2)      W 6.030 -> 14.470 um   (gm/ID 17 -> 20 at TT/27C)
  XM3, XM4, XM6 (pfet L=0.3) W 4.635 -> 13.710 um   (gm/ID 14 -> 16 at TT/27C)

Lower Vov on the pair extends the low common-mode edge (the tail-starved
side); lower |Vov| on the PMOS mirror group raises d1/d2 and extends the high
edge (the 15/15 side of issue #181's attribution).  XM3:XM4:XM6 move as ONE
width so the 1:1:10 mirror ratio law of DR-002/DR-007/DR-013 holds and
I(XM6) = 50 uA is preserved by construction; the NMOS bias group
(XMB1:XM5:XM7 = 1:2:10) is deliberately NOT touched (see PLAN.md: Vov(XM5)
at SS/-40C is already ~33 mV, and the group move would drag the output sink
XM7 out of input-stage scope).  Every width is on the 0.005 um manufacturing
grid, nf = 1.

Candidate (b), a complementary PMOS input pair, was dropped at the hand
screen (PLAN.md). At SS/-40C, Vth_n + |Vth_p| = 1.732 V exceeds VDD = 1.62 V.
The estimate leaves an interval without strong-inversion overlap. Continuous
closed-loop swing through that interval would need a circuit measurement.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent.parent
sys.path.insert(0, str(REPO / "sim" / "lib"))
sys.path.insert(0, str(HERE.parent))
from _gmid import (  # noqa: E402
    CANON,
    SWEEP_W_UM,
    canonical_body,
    card,
    interp_gmid,
    legal,
    load,
    snap,
)
from corners import VDD_BY_CORNER  # noqa: E402  (single owner of the ratified table)

OUT_DIR = HERE
VARIANT_TAG = "icmr-rebias"
VARIANT = OUT_DIR / f"{VARIANT_TAG}.spice"

I_UNIT_UA = 5.0                    # first-stage branch unit current (unchanged)
GM_ID_PAIR = 20.0                  # was 17 (DR-007 pair target)
GM_ID_MIRROR = 16.0                # was 14 (DR-007 M3/M4/M6 target)
ICMR_MEASURED_SS_N40 = (0.7168, 1.1686)   # record 20261011-141126-04489d4-b4ac6f
ICMR_MEASURED_FS_N40_LOW = 0.7388         # highest low edge on the 15-point grid
CONSUMER_POINT_V = 0.73                   # sky130-bandgap sense point (FS/-40C miss)

# Nominal operating point of the VARIANT, measured by the ONE local .op probe
# (`op` subcommand; log committed as op-probe.out.txt), same conventions as
# pelgrom_handcalc.OP (tt, 27 C, 1.8 V, Iref 5 uA).  Simulator-derived inputs
# only; the mismatch statistics are not.
OP_SOURCE = ("one local ngspice .op, tt, 27 C, VDD 1.8 V, Iref 5 uA, Vd = +151 uV "
             "(same stimulus convention as pelgrom_handcalc.OP; the variant settles "
             "v(out) = 1.0377 V open-loop there), netlist "
             "variants/input-stage/icmr-rebias.spice -- see op-probe.out.txt")
OP = {
    "id1": 4.761733e-06, "gm1": 1.007474e-04, "gds2": 5.316111e-07,
    "id3": 4.761733e-06, "gm3": 7.552109e-05, "gds4": 1.322983e-06,
    "id6": 5.192905e-05, "gm6": 8.227474e-04,
    "id7": 5.192904e-05, "gm7": 9.489725e-04,
}


# ---------------------------------------------------------------- sizing data
def widths() -> dict:
    n = load("nfet", 1.2)[("tt", 27.0)]
    p = load("pfet", 0.3)[("tt", 27.0)]
    jn, *_ = interp_gmid(n, GM_ID_PAIR)
    jp, *_ = interp_gmid(p, GM_ID_MIRROR)
    return {"pair": snap(I_UNIT_UA / jn), "pair_raw": I_UNIT_UA / jn, "pair_density": jn,
            "mirror": snap(I_UNIT_UA / jp), "mirror_raw": I_UNIT_UA / jp, "mirror_density": jp}


def series(device: str, length: float):
    """(gm/ID, J uA/um, Vov V, Vth V) rows of one (device, L) over all corners."""
    out = defaultdict(list)
    for key, rows in load(device, length).items():
        for _, i, r in rows:
            g = float(r["gm_id_per_v"]) if r["gm_id_per_v"] else None
            if g:
                out[key].append(
                    (g, i / SWEEP_W_UM * 1e6, float(r["vov_v"]), float(r["vth_v"])))
    for k in out:
        out[k].sort()
    return out


def at_J(pts, J):
    """Interpolate (gm/ID, Vov V, Vth V) at current density J (uA/um)."""
    s = sorted(pts, key=lambda t: t[1])
    for a, b in zip(s, s[1:]):
        if a[1] <= J <= b[1] and b[1] > a[1]:
            f = (J - a[1]) / (b[1] - a[1])
            return (a[0] + f * (b[0] - a[0]), a[2] + f * (b[2] - a[2]), a[3] + f * (b[3] - a[3]))
    return None


def sizing_report() -> str:
    w = widths()
    L = []
    A = L.append
    A(f"pair  : gm/ID 17 -> {GM_ID_PAIR:g} at TT/27C: W = {I_UNIT_UA:g} uA / {w['pair_density']:.6f} uA/um"
      f" = {w['pair_raw']:.4f} -> {w['pair']:.3f} um (grid)")
    A(f"mirror: gm/ID 14 -> {GM_ID_MIRROR:g} at TT/27C: W = {I_UNIT_UA:g} uA / {w['mirror_density']:.6f} uA/um"
      f" = {w['mirror_raw']:.4f} -> {w['mirror']:.3f} um (grid; XM6 keeps m=10, ratio 1:1:10)")
    j_pair_cur, j_pair_new = I_UNIT_UA / 6.030, I_UNIT_UA / w["pair"]
    j_mir_cur, j_mir_new = I_UNIT_UA / 4.635, I_UNIT_UA / w["mirror"]
    j_tail = 10.0 / (7.820 * 2)
    nf, pf = series("nfet", 1.2), series("pfet", 0.3)
    A("")
    A("Per-corner first-order table (committed sweep, Vsb = 0, |Vds| = 0.9 V):")
    A("corner      Vth_n   |Vth_p| |  pair Vov cur->new   Vov(M5) | mirror |Vov| cur->new | Vth_n+|Vth_p| vs VDD")
    for c in ("ss", "tt", "ff", "sf", "fs"):
        for t in (-40.0, 27.0, 125.0):
            n, p = nf[(c, t)], pf[(c, t)]
            vn, vp = n[0][3], p[0][3]
            a, b = at_J(n, j_pair_cur), at_J(n, j_pair_new)
            m5 = at_J(n, j_tail)
            q, qn = at_J(p, j_mir_cur), at_J(p, j_mir_new)
            A(f"{c}/{t:g}C   {vn:6.4f}  {vp:6.4f} |  {a[1]*1e3:5.0f} -> {b[1]*1e3:4.0f} mV"
              f"      {m5[1]*1e3:4.0f} mV |     {q[1]*1e3:4.0f} -> {qn[1]*1e3:5.0f} mV     |"
              f" {vn+vp:.3f} vs {VDD_BY_CORNER[c]:g}{'  <== SUM+margin > VDD' if vn+vp+0.06 > VDD_BY_CORNER[c] else ''}")
    # binding-corner edge estimates + ceilings
    n, p = nf[("ss", -40.0)], pf[("ss", -40.0)]
    vn, vp = n[0][3], p[0][3]
    m5 = at_J(n, j_tail)
    vcur, vnew = at_J(n, j_pair_cur), at_J(n, j_pair_new)
    qcur, qnew = at_J(p, j_mir_cur), at_J(p, j_mir_new)
    th2 = ICMR_MEASURED_SS_N40[1] - (1.62 - (vp + qcur[1]))
    A("")
    A("SS/-40C/1.62V input common-mode edges (first order):")
    A(f"  low : cur ~ {m5[1]+vn+vcur[1]:.3f} V, cand ~ {m5[1]+vn+vnew[1]:.3f} V;"
      f" measured ICMR low edge {ICMR_MEASURED_SS_N40[0]:.4f} V")
    A(f"        At zero pair and tail overdrive, estimated Vin_min = Vth_n = {vn:.4f} V.")
    A(f"  high: cur ~ {1.62-(vp+qcur[1])+th2:.3f} V, cand ~ {1.62-(vp+qnew[1])+th2:.3f} V;"
      f" measured ICMR high edge {ICMR_MEASURED_SS_N40[1]:.4f} V (Vth2_eff = {th2:.3f} V implied)")
    A(f"        At zero mirror overdrive, estimated Vin_max = {1.62-vp+th2:.3f} V.")
    A("  See the dc_swing callouts in report.out.md for measured unity-buffer output edges.")
    A("")
    A("FS/-40C consumer point: pair Vov %.0f -> %.0f mV; measured ICMR low edge"
      % (at_J(nf[("fs", -40.0)], j_pair_cur)[1] * 1e3, at_J(nf[("fs", -40.0)], j_pair_new)[1] * 1e3))
    A(f"  {ICMR_MEASURED_FS_N40_LOW:.4f} V -> ~{ICMR_MEASURED_FS_N40_LOW - at_J(nf[('fs', -40.0)], j_pair_cur)[1] + at_J(nf[('fs', -40.0)], j_pair_new)[1]:.3f} V"
      f" vs consumer point {CONSUMER_POINT_V:g} V (currently missed by"
      f" {ICMR_MEASURED_FS_N40_LOW-CONSUMER_POINT_V:.4f} V)")
    A("")
    A("Candidate (b), complementary PMOS pair (hand screen only):")
    A(f"  PMOS strong-inversion upper estimate: VDD - |Vth_p| - |Vov_p| - Vov_tailp"
      f" ~ {1.62-vp-0.03-0.03:.2f} V at SS/-40C/1.62V.")
    A(f"  NMOS strong-inversion lower estimate: Vth_n + Vov_n + Vov_M5 ~ {vn+0.03+0.03:.2f} V.")
    A("  Weak-inversion gain and contiguous unity-buffer swing between these estimates"
      " remain unmeasured. Candidate (b) received no fleet request.")
    return "\n".join(L)


# ------------------------------------------------------------------ netlist
REGENERATED = {
    "XM1": lambda w: card("XM1", "d1", "inn", "tail", "vss", "nfet", w["pair"], 1.2),
    "XM2": lambda w: card("XM2", "d2", "inp", "tail", "vss", "nfet", w["pair"], 1.2),
    "XM3": lambda w: card("XM3", "d1", "d1", "vdd", "vdd", "pfet", w["mirror"], 0.3),
    "XM4": lambda w: card("XM4", "d2", "d1", "vdd", "vdd", "pfet", w["mirror"], 0.3),
    "XM6": lambda w: card("XM6", "out", "d2", "vdd", "vdd", "pfet", w["mirror"], 0.3, 10),
}


def netlist() -> str:
    w = widths()
    head = (
        "** EXPERIMENTAL VARIANT (issue #359) -- NOT the canonical design. Tag icmr-rebias:\n"
        "** input-stage low-headroom re-bias at UNCHANGED currents (candidate (a) of\n"
        "** variants/input-stage/PLAN.md). Base: design/netlist/opamp_core.spice (DR-013\n"
        "** grid-legal widths, sha256:e954d17d...), copied verbatim except FIVE cards:\n"
        "**   XM1, XM2        nfet L=1.2  W 6.030 -> 14.470 um  (gm/ID 17 -> 20 at TT/27C)\n"
        "**   XM3, XM4, XM6   pfet L=0.3  W 4.635 -> 13.710 um  (gm/ID 14 -> 16 at TT/27C)\n"
        "** XM3:XM4:XM6 move as ONE width (mirror ratio 1:1:10 and I(XM6)=50 uA preserved\n"
        "** by construction); the NMOS bias group XMB1:XM5:XM7 (1:2:10) is untouched.\n"
        "** Flat netlist, ports vdd vss inn inp out ibias, as the canonical file. Generator\n"
        "** and checks: variants/input-stage/input_stage_rebias.py (generate / check).\n"
        "** All widths on the 0.005 um grid, nf = 1.\n"
        "**.subckt opamp_core vdd vss inn inp out ibias\n")
    out = []
    for ln in canonical_body().splitlines(keepends=True):
        name = ln.split()[0] if ln.split() else ""
        if name in REGENERATED:
            out.append(REGENERATED[name](w))
        else:
            out.append(ln)
    return head + "".join(out) + "**.ends\n.end\n"


def check() -> list[str]:
    errs = []
    if not VARIANT.is_file():
        return [f"missing {VARIANT}"]
    want = netlist()
    got = VARIANT.read_text()
    if got != want:
        errs.append(f"{VARIANT} does not match the generator (run: generate)")
    canon = CANON.read_text().splitlines()
    var = got.splitlines()
    changed = {ln.split()[0] for ln in var if ln.startswith(("XM1 ", "XM2 ", "XM3 ", "XM4 ", "XM6 "))
               and ln not in canon}
    if changed != {"XM1", "XM2", "XM3", "XM4", "XM6"}:
        errs.append(f"unexpected changed-card set: {sorted(changed)}")
    for card_name in ("XMB1", "XM5", "XM7", "XRz", "XCc"):
        c = [ln for ln in canon if ln.startswith(card_name + " ")]
        v = [ln for ln in var if ln.startswith(card_name + " ")]
        if c != v:
            errs.append(f"{card_name} card differs from canonical")
    w = widths()
    for name, width in (("XM1", w["pair"]), ("XM2", w["pair"]), ("XM3", w["mirror"]),
                        ("XM4", w["mirror"]), ("XM6", w["mirror"])):
        ln = next((l for l in var if l.startswith(name + " ")), "")
        m = re.search(r"W=([\d.]+)", ln)
        if not m or abs(float(m.group(1)) - width) > 1e-9:
            errs.append(f"{name}: W != {width:.3f}")
        if not legal(width):
            errs.append(f"{name}: W={width} off the 0.005 um grid")
    if "sky130_fd_pr__nfet_01v8_lvt" in got or "pfet_01v8_lvt" in got:
        errs.append("variant uses a lower-Vth flavor (out of scope: no committed gm/ID or mismatch data)")
    return errs


# ------------------------------------------------------- one local .op probe
def op_probe() -> int:
    sys.path.insert(0, str(REPO / "sim" / "opamp-characterization" / "bin"))
    import pvt_sweep  # noqa: E402  (resolve_pdk: MOS + R+C corner includes)
    pdk = pvt_sweep.resolve_pdk()
    rc = pdk.rc_includes()
    deck = f"""* ONE local .op probe (issue #359): variant OP for the Pelgrom hand calc. NOT a record.
.option scale=1u
.param mc_mm_switch=0
.param mc_pr_switch=0
.include "{pdk.corner_include('tt')}"
.include "{rc[0]}"
.include "{rc[1]}"
.temp 27

.include "{VARIANT}"

Vdd vdd 0 dc 1.8
Vss vss 0 dc 0
Iref vdd ibias dc 5u
Vinn inn 0 dc 0.8999245
Vinp inp 0 dc 0.9000755
.control
op
print v(out) v(d1) v(d2) v(tail)
print @m.xm1.msky130_fd_pr__nfet_01v8[gm] @m.xm1.msky130_fd_pr__nfet_01v8[gds] @m.xm1.msky130_fd_pr__nfet_01v8[id]
print @m.xm2.msky130_fd_pr__nfet_01v8[gds]
print @m.xm3.msky130_fd_pr__pfet_01v8[gm] @m.xm3.msky130_fd_pr__pfet_01v8[gds] @m.xm3.msky130_fd_pr__pfet_01v8[id]
print @m.xm4.msky130_fd_pr__pfet_01v8[gds]
print @m.xm6.msky130_fd_pr__pfet_01v8[gm] @m.xm6.msky130_fd_pr__pfet_01v8[id]
print @m.xm7.msky130_fd_pr__nfet_01v8[gm] @m.xm7.msky130_fd_pr__nfet_01v8[id]
.endc
.end
"""
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "op.probe.spice"
        p.write_text(deck)
        r = subprocess.run(["ngspice", "-b", str(p)], capture_output=True, text=True, timeout=300)
    print(deck)
    print(r.stdout)
    print(r.stderr, file=sys.stderr)
    return r.returncode


# ------------------------------------------------------------ pelgrom re-run
def pelgrom() -> int:
    spec = importlib.util.spec_from_file_location(
        "pelgrom_handcalc", REPO / "sim" / "offset-capability" / "bin" / "pelgrom_handcalc.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = mod.calc(op=OP, core_path=VARIANT)
    out["op_source"] = OP_SOURCE
    print(f"op source: {OP_SOURCE}")
    for n, v in out["devices"].items():
        print(f"{n}: {v['bin']}  W*L*mult={v['area_um2']:.4g} um2  "
              f"sigma_VT={v['sigma_vt_v']*1e3:.3f} mV  sigma_beta/beta={v['sigma_beta_rel']*100:.3f} %")
    print(f"A1 = {out['first_stage_gain_A1']:.1f}   eps7 = {out['eps7_ratio_sigma_rel']*100:.3f} %")
    for k, v in out["group_sigma_v"].items():
        print(f"  {k:9s} {v*1e3:7.3f} mV (input-referred, 1 sigma)")
    print(f"  TOTAL     {out['total_sigma_v']*1e3:7.3f} mV")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("sizing", "generate", "check", "op", "pelgrom"):
        sub.add_parser(name)
    a = ap.parse_args()
    if a.cmd == "sizing":
        print(sizing_report())
    elif a.cmd == "generate":
        VARIANT.write_text(netlist())
        print(f"wrote {VARIANT}")
    elif a.cmd == "check":
        errs = check()
        for e in errs:
            print(f"ERROR: {e}", file=sys.stderr)
        print("OK" if not errs else f"{len(errs)} error(s)")
        return 1 if errs else 0
    elif a.cmd == "op":
        return op_probe()
    elif a.cmd == "pelgrom":
        return pelgrom()
    return 0


if __name__ == "__main__":
    sys.exit(main())
