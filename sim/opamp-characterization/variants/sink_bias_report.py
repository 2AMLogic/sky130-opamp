#!/usr/bin/env python3
"""Stage report for the sink bias-margin experiment (issue #197). Simulator-free.

Reads only committed records. `bias-margin/records.json` lists, per variant tag, the
fleet record ids that carry its measurements (any number of pvt_sweep records, one static
record, optional mc records) plus the canonical reference ids. Points are keyed by the full
(corner, temp_c, vdd_v) tuple. Failed/missing units are listed, never dropped.

Evidence validation (every record, before any of its rows is used):

* DUT identity. The record JSON's DUT hash must equal the variant file (or, for the canonical
  ids, the shared canonical hash). The captured netlist snapshot must still hash to that value
  and saved decks must include only it (`dut_identity.verify_record_dut`). Static and mismatch
  records must also declare the expected `kind` and `tag`, and their CSV must hold `units` rows.
* Bench/model provenance. Every canonical and variant PVT record must share the PDK
  (variant, commit, pin, RC corner), the bench matrix (CL, Ibias, supply mode, per-corner VDD,
  solver settings), the `models` block of every klt request and the fleet runner klt version.
  Every rendered variant bench body must be byte-identical to the canonical body of the same name.
  The one exception is the two step levels of a per-point ICMR-aware slew body: the method derives
  them from that DUT's own ICMR. They are masked for the comparison and must instead equal the
  record's own `step_low_v`/`step_high_v`. Static and mismatch probes share one bench body across
  variants, and their models and runner must match the canonical ones.
* Duplicates and replay selection. A record listed twice, or a measurement key that repeats
  inside one record's CSV, is rejected. The same key in two *distinct* records (for example a
  Stage 2 full grid re-measuring a Stage 1 screen point, or a canonical re-run) is accepted only
  as a replicate: every measured column must agree exactly (only the per-run `elapsed_s` may
  differ). The row from the record listed last is selected. `row["_records"]` keeps every source
  record id, and each overlap is logged with both ids. A conflicting replicate is an error, so
  no silent choice is made. A failed unit (a row missing from a record) is never an overlap, and
  every record's `errors` stay in the unit-error list whichever replicate is selected.

    python3 sim/opamp-characterization/variants/sink_bias_report.py screen   # Stage 1 table + verdicts
    python3 sim/opamp-characterization/variants/sink_bias_report.py full TAG # 15-point table for an expanded design
    python3 sim/opamp-characterization/variants/sink_bias_report.py mc TAG   # mismatch probe summary
    python3 sim/opamp-characterization/variants/sink_bias_report.py provenance # validation + replicate log
"""
from __future__ import annotations

import csv
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
REC = REPO / "sim" / "opamp-characterization" / "records"
SNAP = REPO / "sim" / "opamp-characterization" / "netlist-snapshots"
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
PVT_TABLES = ("ac", "tran-sr", "tran-sr-icmr", "icmr", "dc-swing")
RUN_COLS = {"elapsed_s"}   # per-run timing, not a measurement: may differ between replicates
PDK_FIELDS = ("variant", "installed_commit", "pinned_commit", "matches_pin", "rc_corner")
BENCH_FIELDS = ("cl_f", "ibias_a", "supply_mode", "vdd_by_corner")
ICMR_BODY_RE = re.compile(r"^tran-sr-icmr-([a-z]+)-(-?[0-9.]+)C-([0-9.]+)V-body\.spice$")
PULSE_RE = re.compile(r"pulse\(([-+0-9.eE]+) ([-+0-9.eE]+) ")
LEVELS_RE = re.compile(r"LITERAL levels ([-+0-9.eE]+) and ([-+0-9.eE]+)")


def key(r):
    return (r["corner"], round(float(r["temp_c"]), 6), round(float(r["vdd_v"]), 6))


def read(rid, suffix=None):
    p = REC / (f"{rid}-{suffix}.csv" if suffix else f"{rid}.csv")
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


def read_meta(rid):
    return json.loads((REC / f"{rid}.json").read_text())


def check_dut(rid, meta, expect_sha, kind=None, tag=None):
    """Refuse a record that is not the expected DUT or whose captured snapshot is not intact."""
    sha = (meta.get("dut") or {}).get("sha256")
    if sha != expect_sha:
        raise SystemExit(f"{rid}: DUT hash {sha} != expected {expect_sha}")
    state, problems = dut_identity.verify_record_dut(meta, REPO)
    if state != dut_identity.VERIFIED or problems:
        raise SystemExit(f"{rid}: DUT snapshot not verified ({state}): {'; '.join(problems)}")
    for field, want in (("kind", kind), ("tag", tag)):
        if want is not None and meta.get(field) != want:
            raise SystemExit(f"{rid}: {field} {meta.get(field)!r} != expected {want!r}")


def unique_rows(rows, kfn, where):
    """Key rows; a key that repeats inside one record is an error, never last-row-wins."""
    out = {}
    for r in rows:
        k = kfn(r)
        if k in out:
            raise SystemExit(f"{where}: duplicate measurement key {k} within one record")
        out[k] = r
    return out


def reconcile(tbl, k, row, rid, where, log):
    """Replicate-agreement policy for one key seen in a further, distinct record (see module doc)."""
    row = dict(row, _records=[rid])
    prev = tbl.get(k)
    if prev is not None:
        cols = sorted(c for c in set(prev) | set(row)
                      if not c.startswith("_") and c not in RUN_COLS and prev.get(c) != row.get(c))
        if cols:
            raise SystemExit(f"{where} {k}: conflicting duplicate between {prev['_records']} and {rid} "
                             f"(columns {cols}); no replay selection is made for conflicting evidence")
        row["_records"] = prev["_records"] + [rid]
        log.append({"table": where, "key": k, "selected": rid, "replicates": list(prev["_records"])})
    tbl[k] = row


def no_repeats(ids, where):
    seen = set()
    for rid in ids:
        if rid in seen:
            raise SystemExit(f"{where}: record {rid} listed more than once")
        seen.add(rid)


def load(ids, expect_sha, log=None):
    """Merge rows over record ids under the replicate policy; refuse a record that is not the DUT."""
    log = [] if log is None else log
    no_repeats(ids, "pvt ids")
    out = {sfx: {} for sfx in PVT_TABLES}
    errs = []
    for rid in ids:
        meta = read_meta(rid)
        check_dut(rid, meta, expect_sha)
        errs += [f"{rid}: {e}" for e in meta.get("errors", [])]
        for sfx in out:
            for k, r in unique_rows(read(rid, sfx), key, f"{rid}-{sfx}").items():
                reconcile(out[sfx], k, r, rid, sfx, log)
    return out, errs


def static_rows(rid, tag, kind="sink-static"):
    """Rows of one static (or mismatch) probe record, after DUT/snapshot/kind/tag validation."""
    meta = read_meta(rid)
    check_dut(rid, meta, variant_sha(tag), kind=kind, tag=tag)
    rows = read(rid)
    if len(rows) != meta.get("units"):
        raise SystemExit(f"{rid}: {len(rows)} CSV rows != declared units {meta.get('units')}")
    kfn = (lambda r: key(r) + (r["sample"],)) if kind == "sink-mc" else key
    return unique_rows(rows, kfn, rid), meta


def mc_rows(rid, tag):
    by_key, meta = static_rows(rid, tag, kind="sink-mc")
    return list(by_key.values()), meta


def bench_template(text, name):
    """(template text, step levels). The ICMR-aware slew method derives a body's two step levels from
    the DUT's own ICMR at that point, so they are masked for the cross-DUT comparison and returned for
    `check_stimulus`. Every other body is compared byte for byte."""
    if not ICMR_BODY_RE.match(name):
        return text, None
    levels = {tuple(PULSE_RE.findall(text)), tuple(LEVELS_RE.findall(text))}
    text = LEVELS_RE.sub("LITERAL levels <lo> and <hi>", PULSE_RE.sub("pulse(<lo> <hi> ", text))
    return text, levels


def snapshot_files(meta):
    """{file name: sha256 of the bench template} for the rendered bodies saved next to the DUT snapshot."""
    snap = REPO / Path(meta["dut"]["snapshot_path"]).parent
    return {p.name: dut_identity.sha256_bytes(bench_template(p.read_text(), p.name)[0].encode())
            for p in sorted(snap.glob("*-body.spice"))}


def check_stimulus(rid, meta):
    """The masked ICMR-aware step levels must be exactly the ones the record reports for that point."""
    probs = []
    rows = {key(r): r for r in read(rid, "tran-sr-icmr")}
    snap = REPO / Path(meta["dut"]["snapshot_path"]).parent
    for p in sorted(snap.glob("tran-sr-icmr-*-body.spice")):
        mt = ICMR_BODY_RE.match(p.name)
        _, levels = bench_template(p.read_text(), p.name)
        pulse = levels and next(iter(levels))
        if len(levels) != 1 or len(pulse) != 1:
            probs.append(f"{rid}: {p.name} step levels not stated once and consistently ({sorted(levels)})")
            continue
        r = rows.get((mt[1], round(float(mt[2]), 6), round(float(mt[3]), 6)))
        if r is None:
            continue   # failed unit: no measurement uses this body; the record's errors carry it
        lo, hi = (float(v) for v in pulse[0])
        if abs(lo - fl(r["step_low_v"])) > 5e-7 or abs(hi - fl(r["step_high_v"])) > 5e-7:
            probs.append(f"{rid}: {p.name} steps {lo}..{hi} != record step_low/high "
                         f"{r['step_low_v']}..{r['step_high_v']}")
    return probs


def fingerprint(meta):
    """Comparable bench/model provenance of one record (PVT records also carry pdk and matrix)."""
    snap = REPO / Path(meta["dut"]["snapshot_path"]).parent
    models = sorted({json.dumps(json.loads(p.read_text()).get("models"), sort_keys=True)
                     for p in snap.glob("*-request.json")})
    jobs = meta.get("klt_jobs") or [meta]
    fp = {"models": models,
          "runner_klt": sorted({str((j.get("remote") or {}).get("runner_klt_version")) for j in jobs})}
    if "matrix" in meta:
        mx = meta["matrix"]
        fp["pdk"] = [(meta.get("pdk") or {}).get(f) for f in PDK_FIELDS]
        fp["bench"] = dict({f: mx.get(f) for f in BENCH_FIELDS},
                           solver=(mx.get("execution") or {}).get("solver_settings"))
    return fp


def check_provenance(m):
    """Problems that make the canonical and variant comparisons not like-for-like (empty = ok)."""
    probs = []
    ref, ref_id, canon_bodies = None, None, {}
    for rid in m["canonical"]["ids"]:
        meta = read_meta(rid)
        fp = fingerprint(meta)
        if ref is None:
            ref, ref_id = fp, rid
        elif fp != ref:
            probs.append(f"canonical {rid} provenance {fp} != canonical {ref_id} {ref}")
        probs += check_stimulus(rid, meta)
        for name, h in snapshot_files(meta).items():
            if canon_bodies.setdefault(name, (h, rid))[0] != h:
                probs.append(f"canonical bench {name} differs between {canon_bodies[name][1]} and {rid}")
    probe_body = {}
    for tag, e in m["variants"].items():
        for rid in e["ids"] + e.get("stage2", []):
            meta = read_meta(rid)
            fp = fingerprint(meta)
            for f in fp:
                if fp[f] != ref[f]:
                    probs.append(f"{tag} {rid}: {f} {fp[f]} != canonical {ref[f]}")
            probs += check_stimulus(rid, meta)
            for name, h in snapshot_files(meta).items():
                if name not in canon_bodies:
                    probs.append(f"{tag} {rid}: bench {name} has no canonical counterpart")
                elif canon_bodies[name][0] != h:
                    probs.append(f"{tag} {rid}: bench {name} differs from canonical {canon_bodies[name][1]}")
        for rid in e.get("static", []) + e.get("mc", []):
            meta = read_meta(rid)
            fp = fingerprint(meta)
            for f in ("models", "runner_klt"):
                if fp[f] != ref[f]:
                    probs.append(f"{tag} {rid}: {f} {fp[f]} != canonical {ref[f]}")
            for name, h in snapshot_files(meta).items():
                if probe_body.setdefault("h", (h, rid))[0] != h:
                    probs.append(f"{tag} {rid}: probe bench {name} differs from {probe_body['h'][1]}")
    return probs


def manifest():
    return json.loads(MANIFEST.read_text())


def variant_sha(tag):
    return dut_identity.sha256_file(HERE / "bias-margin" / f"sink-{tag}.spice")


def get_all(stage2=False):
    m = manifest()
    probs = check_provenance(m)
    if probs:
        raise SystemExit("bench/model provenance not comparable:\n  " + "\n  ".join(probs))
    clog = []
    canon, _ = load(m["canonical"]["ids"], m["canonical"]["sha256"], clog)
    data = {}
    for tag, e in m["variants"].items():
        log = []
        d, errs = load(e["ids"] + (e.get("stage2", []) if stage2 else []), variant_sha(tag), log)
        no_repeats(e.get("static", []), f"{tag} static ids")
        stat = {}
        for sid in e.get("static", []):
            for k, r in static_rows(sid, tag)[0].items():
                reconcile(stat, k, r, sid, "static", log)
        data[tag] = {"d": d, "errs": errs, "static": stat, "replicates": log}
    return dict(m, _canonical_replicates=clog), canon, data


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
        # PLAN.md condition 1: a missing Stage-1 slew unit, or a tran_sr / tran_sr_icmr unit that is
        # not slew-limited or is invalid, stops the candidate.
        ic = d["tran-sr-icmr"].get(k)
        if ic is None:
            reasons.append(f"missing tran_sr_icmr unit {lab}")
        else:
            for edge in ("rise", "fall"):
                cls = ic.get(f"{edge}_class") or "n/a"
                if cls != "slew_limited":
                    reasons.append(f"tran_sr_icmr {edge} class {cls} (not slew_limited) at {lab}")
        if k not in d["tran-sr"]:
            reasons.append(f"missing tran_sr unit {lab}")
            continue
        for col in ("sr_rise_v_per_us", "sr_fall_v_per_us"):
            v = val(d["tran-sr"], k, col)
            if not (math.isfinite(v) and v > 0):
                reasons.append(f"tran_sr {col} invalid ({f(v)}) at {lab}")
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
        print("\nSurvivors: none; under PLAN.md nothing is expanded.")
    off_plan = [t for t in data if t not in surv and m["variants"][t].get("stage2")]
    for t in off_plan:
        print(f"\n**Plan deviation:** Stage 2 records exist for {t}, which is STOPPED above. That expansion ran "
              f"despite the Stage 1 stop condition (strict reading of PLAN.md condition 1); it is not "
              f"plan-compliant and is kept as disclosed evidence only.")


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
    ids = m["variants"][tag].get("mc", [])
    no_repeats(ids, f"{tag} mc ids")
    for rid in ids:
        rows, meta = mc_rows(rid, tag)
        ok = [r for r in rows if r["ok"] == "True"]
        x = sorted(abs(fl(r["i_xms_ua"])) for r in ok)
        flagged = sum(1 for v in x if v * 1e-6 > BOOST_A)
        railed = sum(1 for r in ok if r["railed"] == "True")
        n = meta["mc"]["n"]
        print(f"{rid} {meta['mc']['corner']}_mm/{meta['mc']['temp_c']:g}C n={n}: units {len(rows)}, ok {len(ok)}, "
              f"failed {len(rows) - len(ok)}, |I(XMS)|>1uA {flagged}, railed {railed}, "
              f"|I(XMS)| median {x[len(x) // 2]:.4f} p95 {x[int(0.95 * (len(x) - 1))]:.4f} max {x[-1]:.4f} uA")


def cmd_provenance():
    m, canon, data = get_all(stage2=True)
    print("# Evidence validation and replicate selection (generated by sink_bias_report.py)\n")
    print("All DUT hashes, captured snapshots, static/mismatch kind+tag, bench/model provenance and "
          "duplicate-key checks passed (any failure aborts before this line).\n")
    print("Bench comparison: variant bodies equal the canonical bodies of the same name byte for byte, "
          "except the two DUT-derived step levels of each ICMR-aware slew body, which are masked and checked "
          "against the record's own step_low_v/step_high_v.\n")
    print("Replicate policy: a key measured in two distinct records must agree in every measured column "
          "(only `elapsed_s` may differ); the record listed last is selected and all source ids are kept.\n")
    for name, log in [("canonical", m["_canonical_replicates"])] + [(t, data[t]["replicates"]) for t in data]:
        print(f"## {name}: {len(log)} replicated keys\n")
        for o in log:
            k = o["key"]
            print(f"- {o['table']} {k[0].upper()}/{k[1]:g}C/{k[2]:g}V: selected {o['selected']}; "
                  f"agreeing replicate(s) {', '.join(o['replicates'])}")
        if log:
            print()
    for tag in data:
        print(f"Unit errors retained for {tag}: {len(data[tag]['errs'])}")


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else "screen"
    {"screen": cmd_screen, "full": lambda: cmd_full(sys.argv[2]), "mc": lambda: cmd_mc(sys.argv[2]),
     "provenance": cmd_provenance}[c]()
