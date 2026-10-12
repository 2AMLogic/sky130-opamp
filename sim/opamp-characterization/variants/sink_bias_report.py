#!/usr/bin/env python3
"""Stage report for the sink bias-margin experiment (issue #197). Simulator-free.

Reads only committed record CSVs. `bias-margin/records.json` lists, per variant tag, the
fleet record ids that carry its measurements (any number of pvt_sweep records, one static
record, optional mc records) plus the canonical reference ids. Every record's DUT hash is
checked against the variant file (or, for the canonical ids, the shared canonical hash).
Points are keyed by the full (corner, temp_c, vdd_v) tuple. Failed/missing units are listed,
never dropped.

    python3 sim/opamp-characterization/variants/sink_bias_report.py screen   # Stage 1 table + verdicts
    python3 sim/opamp-characterization/variants/sink_bias_report.py full TAG # 15-point table for a survivor
    python3 sim/opamp-characterization/variants/sink_bias_report.py mc TAG   # mismatch probe summary
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
REC = REPO / "sim" / "opamp-characterization" / "records"
MANIFEST = HERE / "bias-margin" / "records.json"
sys.path.insert(0, str(REPO / "sim" / "lib"))
import dut_identity  # noqa: E402

SCREEN_POINTS = {  # label -> (corner, temp, vdd), analyses beyond ac
    "TT/27": ("tt", 27.0, 1.8), "SS/-40": ("ss", -40.0, 1.62),
    "FS/125": ("fs", 125.0, 1.8), "SF/27": ("sf", 27.0, 1.8), "FF/125": ("ff", 125.0, 1.98)}
SLEW_POINTS = ("TT/27", "SS/-40")
GAIN_MIN_DB, PM_MIN_DEG = 60.0, 60.0
FALL_GAIN_TT_MIN, FALL_GAIN_SS_MIN = 1.5, 0.5   # V/us over canonical (PLAN.md screening condition 4)
RAIL_V, BOOST_A = 0.10, 1e-6


def key(r):
    return (r["corner"], round(float(r["temp_c"]), 6), round(float(r["vdd_v"]), 6))


def read(rid, suffix):
    p = REC / f"{rid}-{suffix}.csv"
    if not p.exists():
        return []
    with open(p, newline="") as fh:
        return list(csv.DictReader(fh))


def fl(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return math.nan
    return v


def load(ids, expect_sha):
    """Merge rows over record ids; refuse a record whose DUT hash is not the expected one."""
    out = {"ac": {}, "tran-sr": {}, "tran-sr-icmr": {}, "icmr": {}, "dc-swing": {}}
    errs = []
    for rid in ids:
        meta = json.loads((REC / f"{rid}.json").read_text())
        sha = (meta.get("dut") or {}).get("sha256")
        if sha != expect_sha:
            raise SystemExit(f"{rid}: DUT hash {sha} != expected {expect_sha}")
        errs += [f"{rid}: {e}" for e in meta.get("errors", [])]
        for sfx in out:
            for r in read(rid, sfx):
                out[sfx][key(r)] = r
    return out, errs


def static_rows(rid):
    p = REC / f"{rid}.csv"
    with open(p, newline="") as fh:
        return {(r["corner"], round(float(r["temp_c"]), 6), round(float(r["vdd_v"]), 6)): r for r in csv.DictReader(fh)}


def manifest():
    return json.loads(MANIFEST.read_text())


def variant_sha(tag):
    return dut_identity.sha256_file(HERE / "bias-margin" / f"sink-{tag}.spice")


def get_all(stage2=False):
    m = manifest()
    canon, _ = load(m["canonical"]["ids"], m["canonical"]["sha256"])
    data = {}
    for tag, e in m["variants"].items():
        d, errs = load(e["ids"] + (e.get("stage2", []) if stage2 else []), variant_sha(tag))
        stat = {}
        for sid in e.get("static", []):
            stat.update(static_rows(sid))
        data[tag] = {"d": d, "errs": errs, "static": stat}
    return m, canon, data


def val(tbl, k, col):
    r = tbl.get(k)
    return fl(r[col]) if r else math.nan


def f(x, n=2):
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{n}f}"


def screen_verdict(tag, canon, dat):
    reasons = []
    d = dat["d"]
    for lab, k in SCREEN_POINTS.items():
        if k not in d["ac"]:
            reasons.append(f"missing ac unit {lab}")
            continue
        g, pm = val(d["ac"], k, "gain_dc_db"), val(d["ac"], k, "phase_margin_deg")
        if not g >= GAIN_MIN_DB:
            reasons.append(f"gain {f(g)} dB < 60 at {lab}")
        if not pm >= PM_MIN_DEG:
            reasons.append(f"PM {f(pm)} deg < 60 at {lab}")
    for lab in SLEW_POINTS:
        k = SCREEN_POINTS[lab]
        if k not in d["tran-sr"]:
            reasons.append(f"missing tran_sr unit {lab}")
            continue
        gain = val(d["tran-sr"], k, "sr_fall_v_per_us") - val(canon["tran-sr"], k, "sr_fall_v_per_us")
        need = FALL_GAIN_TT_MIN if lab == "TT/27" else FALL_GAIN_SS_MIN
        if not gain >= need:
            reasons.append(f"fall SR gain {f(gain)} V/us < {need} at {lab}")
    s = dat["static"]
    if len(s) < 15:
        reasons.append(f"static probe incomplete ({len(s)}/15 units)")
    for k, r in s.items():
        if r.get("ok") != "True":
            reasons.append(f"static unit failed at {k}")
        elif r.get("railed") == "True":
            reasons.append(f"railed output at {k}")
    reasons += [f"failed unit: {e}" for e in dat["errs"]]
    return reasons


def cmd_screen():
    m, canon, data = get_all()
    print("# Stage 1 screen (generated by sink_bias_report.py; no hand transcription)\n")
    print("| Point | Design | Gain dB | GBW MHz | PM deg | Pq uW | Fall SR std | dFall vs canon | Rise SR | "
          "ICMR-aware fall (class; avg; claim) | I(XMS) static uA |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for lab, k in SCREEN_POINTS.items():
        rows = [("canonical", canon, None)] + [(t, data[t]["d"], data[t]["static"]) for t in data]
        for name, d, st in rows:
            ac, sr, ic = d["ac"].get(k), d["tran-sr"].get(k), d["tran-sr-icmr"].get(k)
            cf = val(canon["tran-sr"], k, "sr_fall_v_per_us")
            fall = val(d["tran-sr"], k, "sr_fall_v_per_us")
            icm = ("n/a" if not ic else f"{ic['fall_class']}; {f(fl(ic['fall_sr_avg_v_per_us']))}; "
                   f"{f(fl(ic['fall_sr_claim_v_per_us']))}")
            xms = "-" if st is None else (f(fl(st[k]["i_xms_ua"]), 4) if k in st and st[k].get("ok") == "True" else "n/a")
            print(f"| {lab} | {name} | {f(val(d['ac'], k, 'gain_dc_db'))} | {f(val(d['ac'], k, 'gbw_hz') / 1e6)} | "
                  f"{f(val(d['ac'], k, 'phase_margin_deg'))} | {f(val(d['ac'], k, 'pq_w') * 1e6, 1)} | "
                  f"{f(fall)} | {f(fall - cf) if name != 'canonical' else '-'} | {f(val(d['tran-sr'], k, 'sr_rise_v_per_us'))} | "
                  f"{icm} | {xms} |")
    print("\n## Static boost current and railing (15 paired points per design; XMS probe, uA)\n")
    for tag in data:
        st = data[tag]["static"]
        vals = [(k, fl(r["i_xms_ua"]), r) for k, r in sorted(st.items()) if r.get("ok") == "True"]
        bad = [k for k, r in st.items() if r.get("ok") != "True"]
        if vals:
            kmax = max(vals, key=lambda t: abs(t[1]))
            print(f"- {tag}: {len(vals)}/{len(st)} units ok; max |I(XMS)| = {abs(kmax[1]):.4f} uA at "
                  f"{kmax[0][0].upper()}/{kmax[0][1]:g}C; flagged > 1 uA: "
                  f"{sum(1 for _, v, _ in vals if abs(v) * 1e-6 > BOOST_A)}; railed: "
                  f"{sum(1 for _, _, r in vals if r['railed'] == 'True')}; failed: {len(bad)}")
        else:
            print(f"- {tag}: no usable static units ({len(st)} rows)")
    print("\n## Power per point: saving vs ic090 and excess over canonical (ac-bench Pq, uW)\n")
    print("| Point | canonical | " + " | ".join(data) + " |")
    print("|---|---|" + "---|" * len(data))
    for lab, k in SCREEN_POINTS.items():
        c = val(canon["ac"], k, "pq_w") * 1e6
        cells = [f(c, 1)] + [f"{f(val(data[t]['d']['ac'], k, 'pq_w') * 1e6, 1)} (+{f(val(data[t]['d']['ac'], k, 'pq_w') * 1e6 - c, 1)})"
                             for t in data]
        print(f"| {lab} | " + " | ".join(cells) + " |")
    print("\n## Screening verdicts (PLAN.md conditions 1-4)\n")
    surv = []
    for tag in data:
        why = screen_verdict(tag, canon, data[tag])
        role = "reference" if tag == m["reference"] else "candidate"
        print(f"- {tag} ({role}): {'STOPPED: ' + '; '.join(why) if why else 'passes all screening conditions'}")
        if not why and role == "candidate":
            surv.append(tag)
    if surv:
        pw = {t: val(data[t]["d"]["ac"], SCREEN_POINTS["FF/125"], "pq_w") for t in surv}
        pick = min(pw, key=pw.get)
        print(f"\nSurvivors: {', '.join(surv)}; expanded (lowest FF/125 Pq): **{pick}**")
    else:
        print("\nSurvivors: none; nothing is expanded.")


def cmd_full(tag):
    m, canon, data = get_all(stage2=True)
    d = data[tag]
    print(f"# 15-point comparison, {tag} vs canonical (generated)\n")
    print("| Point | Gain dB (c / v) | PM deg (c / v) | Pq uW (c / v) | Fall SR (c / v / d) | Rise SR (c / v) | "
          "ICMR-aware fall avg (c / v), class (c / v) | I(XMS) uA |")
    print("|---|---|---|---|---|---|---|---|")
    keys = sorted(set(canon["ac"]) | set(d["d"]["ac"]))
    for k in keys:
        lab = f"{k[0].upper()}/{k[1]:g}C/{k[2]:g}V"
        ci, vi = canon["tran-sr-icmr"].get(k), d["d"]["tran-sr-icmr"].get(k)
        st = d["static"].get(k)
        print(f"| {lab} | {f(val(canon['ac'], k, 'gain_dc_db'))} / {f(val(d['d']['ac'], k, 'gain_dc_db'))} | "
              f"{f(val(canon['ac'], k, 'phase_margin_deg'))} / {f(val(d['d']['ac'], k, 'phase_margin_deg'))} | "
              f"{f(val(canon['ac'], k, 'pq_w') * 1e6, 1)} / {f(val(d['d']['ac'], k, 'pq_w') * 1e6, 1)} | "
              f"{f(val(canon['tran-sr'], k, 'sr_fall_v_per_us'))} / {f(val(d['d']['tran-sr'], k, 'sr_fall_v_per_us'))} / "
              f"{f(val(d['d']['tran-sr'], k, 'sr_fall_v_per_us') - val(canon['tran-sr'], k, 'sr_fall_v_per_us'))} | "
              f"{f(val(canon['tran-sr'], k, 'sr_rise_v_per_us'))} / {f(val(d['d']['tran-sr'], k, 'sr_rise_v_per_us'))} | "
              f"{f(fl(ci['fall_sr_avg_v_per_us'])) if ci else 'n/a'} / {f(fl(vi['fall_sr_avg_v_per_us'])) if vi else 'n/a'}, "
              f"{ci['fall_class'] if ci else 'n/a'} / {vi['fall_class'] if vi else 'n/a'} | "
              f"{f(fl(st['i_xms_ua']), 4) if st and st.get('ok') == 'True' else 'n/a'} |")
    worst = lambda tbl, col, fn: fn((fl(r[col]), k) for k, r in tbl.items() if not math.isnan(fl(r[col])))
    for name, tbl, col, fn in (("gain", "ac", "gain_dc_db", min), ("PM", "ac", "phase_margin_deg", min),
                               ("Pq (uW)", "ac", "pq_w", max), ("fall SR", "tran-sr", "sr_fall_v_per_us", min)):
        sc = 1e6 if col == "pq_w" else 1
        c, v = worst(canon[tbl], col, fn), worst(d["d"][tbl], col, fn)
        print(f"\nWorst {name}: canonical {c[0] * sc:.3f} @ {c[1]}; {tag} {v[0] * sc:.3f} @ {v[1]}")
    print(f"\nUnit errors: {d['errs'] or 'none'}")


def cmd_mc(tag):
    m, *_ = get_all()
    for rid in manifest()["variants"][tag].get("mc", []):
        meta = json.loads((REC / f"{rid}.json").read_text())
        rows = list(csv.DictReader(open(REC / f"{rid}.csv", newline="")))
        ok = [r for r in rows if r["ok"] == "True"]
        x = sorted(abs(fl(r["i_xms_ua"])) for r in ok)
        flagged = sum(1 for v in x if v * 1e-6 > BOOST_A)
        railed = sum(1 for r in ok if r["railed"] == "True")
        n = meta["mc"]["n"]
        print(f"{rid} {meta['mc']['corner']}_mm/{meta['mc']['temp_c']:g}C n={n}: units {len(rows)}, ok {len(ok)}, "
              f"failed {len(rows) - len(ok)}, |I(XMS)|>1uA {flagged}, railed {railed}, "
              f"|I(XMS)| median {x[len(x) // 2]:.4f} p95 {x[int(0.95 * (len(x) - 1))]:.4f} max {x[-1]:.4f} uA")


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else "screen"
    {"screen": cmd_screen, "full": lambda: cmd_full(sys.argv[2]), "mc": lambda: cmd_mc(sys.argv[2])}[c]()
