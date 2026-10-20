#!/usr/bin/env python3
"""Lower-overhead I_C bias margins for the signal-dependent sink (issue #197).

Simulator-free half of the experiment.  `generate` writes the three variant DUT
netlists, `sizing` prints the gm/ID-consistent widths, the quiescent margin and
the power/boost trade-off, `check` verifies the files on disk against the
generator and the canonical netlist.  The fleet half (`static`, `mc`) lives in
the same file so the request shape is committed with the plan (see
`bias-margin/PLAN.md`; the plan is committed before any fleet request).

Rebase.  Every variant is `design/netlist/opamp_core.spice` (the current
canonical DUT, DR-013 widths) copied verbatim, plus the same six sink devices
as `signal-dependent-sink.spice` and ONE zero-volt probe source `Vxms` in series
with the XMS source (electrically inert; it exposes the static boost current
`I(XMS)` to a `.meas`).  Only the XMC width differs between variants:

    I_C = f * 5 uA,  f in {0.90 (original), 0.75, 0.60}
    W(XMC) = snap_0.005(f * 5 uA / J_pfet(gm/ID 14)),   J from the committed sweep

I_6c is not changed (replica ratio 1/10 of M6), so the added quiescent current
is I_6c + I_C and the boost law is I_S = 10 * max(0, I_C - I(M6)/10).
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
sys.path.insert(0, str(HERE))
import sink_sizing as ss  # noqa: E402

CANON = REPO / "design" / "netlist" / "opamp_core.spice"
OUT_DIR = HERE / "bias-margin"
FRACTIONS = {"ic090": 0.90, "ic075": 0.75, "ic060": 0.60}
ORIGINAL = "ic090"
I_UNIT_UA = 5.0
I_M6_FALL_UA = 14.0    # M6 current during the falling edge (variants/README.md, #79)
VDD_TT = 1.8


def widths(frac: float) -> dict:
    n = ss.load("nfet", 1.2)[("tt", 27.0)]
    p = ss.load("pfet", 0.3)[("tt", 27.0)]
    jn, *_ = ss.interp_gmid(n, 18.0)
    jp, *_ = ss.interp_gmid(p, ss.GM_ID_PFET)
    return {"n_unit": ss.snap(I_UNIT_UA / jn), "p_rep": ss.snap(I_UNIT_UA / jp),
            "p_ic": ss.snap(frac * I_UNIT_UA / jp), "jp": jp}


def card(name, d, g, s_, b, kind, w, l, mult=1):
    """One xschem-style MOS card (diffusion terms by the canonical rule: ad = as = 0.29 W,
    pd = ps = 2 (W + 0.29), nrd = nrs = 0.29 / W)."""
    r = 0.29 / w
    return (f"{name} {d} {g} {s_} {b} sky130_fd_pr__{kind}_01v8 L={l:g} W={w:.3f} nf=1 "
            f"ad={w * 0.29:.6g} as={w * 0.29:.6g} pd={2 * (w + 0.29):.6g} ps={2 * (w + 0.29):.6g} nrd={r!r}\n"
            f"+ nrs={r!r} sa=0 sb=0 sd=0 mult={mult} m={mult}\n")


def canonical_body() -> str:
    """Canonical card lines verbatim, from the first card to just before `**.ends`."""
    text = CANON.read_text()
    start = text.index("*.iopin vdd")
    return text[start:text.index("**.ends")]


def netlist(tag: str) -> str:
    f = FRACTIONS[tag]
    w = widths(f)
    wn, wr, wc = w["n_unit"], w["p_rep"], w["p_ic"]
    head = (
        f"** EXPERIMENTAL VARIANT (issue #197) -- NOT the canonical design. Tag {tag}: I_C = {f:.2f} x 5 uA.\n"
        "** Base: design/netlist/opamp_core.spice (DR-013 grid-legal widths), cards copied verbatim,\n"
        "**       plus the SIX sink devices of variants/signal-dependent-sink.spice (issue #79) and ONE\n"
        "**       zero-volt probe source Vxms (in series with the XMS source; electrically inert, it\n"
        "**       exposes the static boost current I(XMS)). Only XMC's width differs between variants.\n"
        "** Boost law I_S = 10 * max(0, I_C - I(M6)/10); quiescent legs I_6c + I_C are NOT free (+~9.5 uA at f=0.9).\n"
        "** Flat netlist, ports vdd vss inn inp out ibias, as the canonical file. Generator and checks:\n"
        "** variants/sink_bias_margin.py (generate / check). All widths on the 0.005 um grid, nf = 1.\n"
        "**.subckt opamp_core vdd vss inn inp out ibias\n")
    added = (
        card("XMP6C", "na", "d2", "vdd", "vdd", "pfet", wr, 0.3)
        + card("XMA", "na", "na", "vss", "vss", "nfet", wn, 1.2)
        + card("XMA2", "nx", "na", "vss", "vss", "nfet", wn, 1.2)
        + card("XMC", "nx", "d1", "vdd", "vdd", "pfet", wc, 0.3)
        + card("XMD", "nx", "nx", "vss", "vss", "nfet", wn, 1.2)
        + card("XMS", "out", "nx", "xs", "vss", "nfet", wn, 1.2, 10)
        + "Vxms xs vss 0\n")
    return head + canonical_body() + added + "**.ends\n.end\n"


def path(tag: str) -> Path:
    return OUT_DIR / f"sink-{tag}.spice"


def sizing_report() -> str:
    out = []
    w0 = widths(1.0)
    out.append(f"pfet L=0.3 J(gm/ID 14) = {w0['jp']:.6f} uA/um; unit {w0['p_rep']:.3f} um = 5 uA; "
               f"nfet unit {w0['n_unit']:.3f} um")
    out.append(f"{'tag':6} {'f':>5} {'W(XMC)':>7} {'I_C/uA':>7} {'quiesc.margin':>13} {'turn-on I(M6)':>13} "
               f"{'I_S@14uA':>9} {'I_S rel.':>8} {'added Iq':>9} {'dP vs orig @1.8V':>17}")
    ref_boost = None
    for tag, f in FRACTIONS.items():
        wc = widths(f)["p_ic"]
        ic = I_UNIT_UA * wc / widths(1.0)["p_rep"]          # I_C actually drawn (grid-snapped W)
        boost = max(0.0, 10 * ic - I_M6_FALL_UA)
        ref_boost = boost if ref_boost is None else ref_boost
        margin = (I_UNIT_UA - ic) / I_UNIT_UA
        added = I_UNIT_UA + ic
        dp = (added - (I_UNIT_UA + FRACTIONS[ORIGINAL] * I_UNIT_UA)) * VDD_TT
        out.append(f"{tag:6} {f:5.2f} {wc:7.3f} {ic:7.3f} {margin * 100:12.1f}% {10 * ic:11.1f}uA "
                   f"{boost:7.1f}uA {boost / ref_boost:8.2f} {added:7.2f}uA {dp:15.2f}uW")
    out.append("Ceiling: I_6c is fixed by the 1/10 replica, so lowering I_C can save at most "
               f"{FRACTIONS[ORIGINAL] * I_UNIT_UA:.1f} uA = {FRACTIONS[ORIGINAL] * I_UNIT_UA * VDD_TT:.2f} uW at 1.8 V "
               "(the boost vanishes with it); f=0.60 saves 1.5 uA = 2.7 uW.")
    out.append("Selection: f=0.60 is the lowest I_C that keeps >= 50 % of the original boost at the falling-edge "
               "M6 current (14 uA); f=0.75 is the midpoint. Quiescent margin (1 - f) must absorb the XMP6C/XMC "
               "Vds mismatch (about 1.2 V vs ~0.1-1.8 V) and device mismatch: measured, not computed (sweep is at 0.9 V).")
    out.append("Headroom: XMC keeps |Vsg| of the M3 diode (same gm/ID-14 density, L=0.3) at every f -- only W scales, "
               "so it stays saturated while nx < vdd - |Vsg| + |Vtp|; the XMD/XMS gate (nx) is bounded by one nfet "
               "VGS (~0.5-0.7 V) and nx clips to vss when I_6c > I_C.")
    return "\n".join(out)


def cmd_generate(_a):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for tag in FRACTIONS:
        p = path(tag)
        if p.exists():
            print(f"exists, not overwritten (append-only): {p.relative_to(REPO)}")
            continue
        p.write_text(netlist(tag))
        print(f"wrote {p.relative_to(REPO)}")


def cmd_sizing(_a):
    print(sizing_report())


def check() -> list[str]:
    """Problems: file differs from the generator, a canonical card changed, or an off-grid width."""
    import re
    probs = []
    canon_cards = [ln for ln in canonical_body().splitlines()]
    for tag in FRACTIONS:
        p = path(tag)
        if not p.exists() or p.read_text() != netlist(tag):
            probs.append(f"{p.name}: missing or differs from the generator")
            continue
        text = p.read_text()
        if canonical_body() not in text:
            probs.append(f"{p.name}: canonical cards not byte-identical")
        for m in re.finditer(r"^(X\w+) .* W=([0-9.]+) ", text, re.M):
            if not ss.legal(float(m.group(2))):
                probs.append(f"{p.name}: {m.group(1)} W={m.group(2)} off the 0.005 um grid")
    return probs


def cmd_check(_a):
    probs = check()
    print("\n".join(probs) if probs else "ok: variants match the generator, canonical cards verbatim, widths on grid")
    return 1 if probs else 0


# --------------------------------------------------------------------------
# Fleet half: static boost current (one dc request per variant) and the bounded
# mismatch probe (one seeded monte_carlo request per point).  Both are `klt sim`
# requests on the batch backend; there is NO local fallback.
# --------------------------------------------------------------------------
STATIC_MEAS = [
    {"name": "i_vdd_a", "unit": "A", "spice": ".meas dc i_vdd_a find i(vdd) at=0"},
    {"name": "i_xms_a", "unit": "A", "spice": ".meas dc i_xms_a find i(v.xdut.vxms) at=0"},
    {"name": "vout_v", "unit": "V", "spice": ".meas dc vout_v find v(out) at=0"},
]
MC_SEED = 20261197
RAIL_MARGIN_V = 0.10      # |v(out)| closer than this to a rail = railed
STATIC_BOOST_LIMIT_A = 1e-6   # reported as an "unintended DC boost" above this


def _pvt():
    spec = importlib.util.spec_from_file_location("pvt_sweep", REPO / "sim/opamp-characterization/bin/pvt_sweep.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pvt_sweep"] = mod
    spec.loader.exec_module(mod)
    return mod


def build_static_request(pvt, req_dir: Path, tag: str, backend: str, mc: dict | None = None,
                         corner: str = "tt", temp: float = 27.0) -> Path:
    """Same body as the AC bench's `ac-iq` companion (DC servo, Vinp at mid-supply, one dc point
    at Vinp offset 0 = the AC bias point), plus the XMS probe current and v(out).  Grid: all
    5 corners x 3 T paired supplies (15 units) or, with `mc`, one `<corner>_mm` point."""
    pdk = pvt.resolve_pdk()
    req_dir.mkdir(parents=True, exist_ok=True)
    dst = req_dir / pvt.dut_identity.SNAPSHOT_NAME
    if not dst.exists():   # already the captured snapshot when the record dir is the request dir
        shutil.copyfile(pvt.ACTIVE_DUT[0], dst)
    body = pvt.render(pvt.TESTBENCH_DIR / "opamp_ac.klt.spice.tmpl", {
        "OPAMP_NETLIST": pvt.dut_identity.SNAPSHOT_NAME, "VDD_NOM": pvt.VDD_BY_CORNER[corner if mc else "tt"],
        "IBIAS_A": pvt.IBIAS_A, "CL_F": pvt.CL_F, "RFB": pvt.AC_RFB, "CFB": pvt.AC_CFB})
    (req_dir / f"{tag}-body.spice").write_text(body)
    if mc:
        corners, vdds, exclude, temps = [f"{corner}_mm"], [pvt.VDD_BY_CORNER[corner]], [], [temp]
    else:
        corners = list(pvt.DEFAULT_CORNERS)
        temps = list(pvt.DEFAULT_TEMPS_C)
        vdds, exclude = pvt.vdd_pairing(corners)
    req = {
        "netlist": f"{tag}-body.spice", "engine": "ngspice", "backend": backend,
        "models": {"pdk": pdk.variant, "lib": pvt.SKY130_LIB},
        "corners": {"process": corners, "supply_v": {"vdd": vdds}, "temperature_c": temps},
        **({"exclude": exclude} if exclude else {}),
        "analysis": {"kind": "dc", "args": "Vinp 0 1m 1m"},
        "measurements": STATIC_MEAS,
        "options": {"timeout_s": 600, "keep_artifacts": True},
    }
    if backend == "batch":
        req["batch"] = {"runner_version_check": "warn"}
    if mc:
        req["monte_carlo"] = {"n": mc["n"], "seed": mc["seed"], "vary": "mismatch"}
    p = req_dir / f"{tag}-request.json"
    p.write_text(json.dumps(req, indent=2) + "\n")
    return p


def static_rows(report: dict) -> list[dict]:
    rows = []
    for c in report.get("corners", []):
        v = {m["name"]: m.get("value") for m in c.get("measurements", [])}
        vdd = float((c.get("supply_v") or {}).get("vdd", float("nan")))
        ok = c.get("status") in ("pass", "fail") and all(
            isinstance(v.get(k), (int, float)) and math.isfinite(v[k]) for k in ("i_vdd_a", "i_xms_a", "vout_v"))
        row = {"corner": c.get("process"), "temp_c": c.get("temperature_c"), "vdd_v": vdd,
               "sample": (c.get("monte_carlo") or {}).get("sample_index", ""), "status": c.get("status"), "ok": ok}
        if ok:
            row.update(pq_uw=round(-v["i_vdd_a"] * vdd * 1e6, 4), i_xms_ua=round(v["i_xms_a"] * 1e6, 4),
                       vout_v=round(v["vout_v"], 4),
                       railed=bool(v["vout_v"] < RAIL_MARGIN_V or v["vout_v"] > vdd - RAIL_MARGIN_V),
                       boost_flag=bool(abs(v["i_xms_a"]) > STATIC_BOOST_LIMIT_A))
        else:
            row.update(pq_uw="", i_xms_ua="", vout_v="", railed="", boost_flag="")
        rows.append(row)
    return rows


def cmd_fleet(a, mc: bool):
    pvt = _pvt()
    tag = a.tag
    if tag not in FRACTIONS:
        raise SystemExit(f"unknown tag {tag}")
    src = path(tag)
    pr = check()
    if pr:
        raise SystemExit("variant check failed: " + "; ".join(pr))
    rec = pvt.RECORDS_DIR
    rid = pvt.allocate_record_id(rec, pvt.git_sha(REPO), extra_dirs=[pvt.SNAPSHOT_DIR])
    kind = "sink-mc" if mc else "sink-static"
    snap = pvt.SNAPSHOT_DIR / rid
    pvt.make_new_dir(snap)
    dut = pvt.dut_identity.capture_dut(src, snap, REPO)
    pvt.ACTIVE_DUT[0] = REPO / dut["snapshot_path"]
    req = build_static_request(pvt, snap, f"{kind}-{tag}", a.backend,
                               {"n": a.n, "seed": MC_SEED + a.seed_offset} if mc else None, a.corner, a.temp)
    t0 = time.monotonic()
    report = pvt.run_klt_sim(req, rec / f"{rid}-logs" / kind, a.backend)
    wall = time.monotonic() - t0
    env = report.get("environment", {})
    errors = []
    if "error" in report:
        errors.append(f"klt error: {report['error'].get('message')}")
    if a.backend == "batch" and not env.get("remote"):
        errors.append("batch response carries no environment.remote provenance -- refusing")
    (rec / f"{rid}-logs" / f"{kind}-{tag}-response.json").write_text(json.dumps(report, indent=2) + "\n")
    rows = [] if errors else static_rows(report)
    fields = ["corner", "temp_c", "vdd_v", "sample", "status", "ok", "pq_uw", "i_xms_ua", "vout_v", "railed", "boost_flag"]
    if rows:
        with open(rec / f"{rid}-{kind}-{tag}.csv", "x", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
    meta = {"record_id": rid, "kind": kind, "tag": tag, "fraction": FRACTIONS[tag], "dut": dut, "backend": a.backend,
            "mc": ({"n": a.n, "seed": MC_SEED + a.seed_offset, "corner": a.corner, "temp_c": a.temp} if mc else None),
            "klt_status": report.get("status"), "corner_count": report.get("corner_count"),
            "remote": env.get("remote"), "wall_s": round(wall, 1), "errors": errors,
            "units": len(rows), "units_ok": sum(1 for r in rows if r["ok"]),
            "request": f"sim/opamp-characterization/netlist-snapshots/{rid}/{req.name}"}
    (rec / f"{rid}-{kind}-{tag}.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps({k: meta[k] for k in ("record_id", "units", "units_ok", "klt_status", "errors")}))
    return 1 if errors else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for n, fn in (("generate", cmd_generate), ("sizing", cmd_sizing), ("check", cmd_check)):
        sub.add_parser(n).set_defaults(fn=fn)
    for n, mc in (("static", False), ("mc", True)):
        q = sub.add_parser(n)
        q.add_argument("--tag", required=True, choices=sorted(FRACTIONS))
        q.add_argument("--backend", default="batch")
        q.add_argument("--n", type=int, default=100)
        q.add_argument("--seed-offset", type=int, default=0)
        q.add_argument("--corner", default="tt")
        q.add_argument("--temp", type=float, default=27.0)
        q.set_defaults(fn=lambda a, mc=mc: cmd_fleet(a, mc))
    a = ap.parse_args(argv)
    return a.fn(a) or 0


if __name__ == "__main__":
    sys.exit(main())
