#!/usr/bin/env python3
"""Collation of the icmr-rebias screen (issue #359). Simulator-free.

Reads only committed records listed in records.json (variant fleet runs,
canonical DR-013 baselines, the #181 fixed-common-mode attribution record) and
writes report.out.md: provenance validation, the variants/compare.py per-row
worst/binding-corner table over the merged candidate view, the ICMR edge,
swing_fixcm and ICMR-aware slew tables, the named 1.62 V / -40 C callouts the
issue requires, and the per-row verdict inputs against the ratified bounds.

Points are keyed by the full (corner, temp_c, vdd_v) tuple owned by
sim/lib/point_identity.py; every measured column of a key measured in two
records must agree exactly (only elapsed_s may differ) and the record listed
last wins -- the same replicate policy as variants/sink_bias_report.py. A
record cited for the two added tuples contributes only those tuples, so a
cartesian baseline never floods the paired view. Failed units are listed,
never dropped. Any validation failure aborts before a table is printed.

    python3 collate.py            # write report.out.md (and echo it)
    python3 collate.py --check    # exit 1 if report.out.md is not current
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VARIANTS = HERE.parent
REC = VARIANTS.parent / "records"
REPO = VARIANTS.parent.parent.parent
sys.path.insert(0, str(REPO / "sim" / "lib"))
sys.path.insert(0, str(VARIANTS))
import dut_identity  # noqa: E402
from point_identity import point_key  # noqa: E402
import compare  # noqa: E402  (variants/compare.py: METRICS + report tables)

MANIFEST = HERE / "records.json"
REPORT = HERE / "report.out.md"
RUN_COLS = {"elapsed_s"}
ADDED_KEYS = {("sf", -40.0, 1.62), ("fs", -40.0, 1.62)}
NAMED_CALLOUTS = (("ss", -40.0, 1.62), ("sf", -40.0, 1.62), ("fs", -40.0, 1.62))
SWING_TGT_VPP = 1.464 - 0.072          # ratified output-swing window, Vpp
SR_TGT_V_US = 20.0                     # ratified slew-rate row
GAIN_MIN_DB, GBW_TGT_MHZ, PM_MIN_DEG = 60.0, 16.0, 60.0
PQ_TGT_98V_UW, PQ_TGT_18V_UW = 128.7, 117.0
CANON_PELGROM_MV, CANON_PELGROM_SRC = 7.30, (
    "sim/offset-capability/records/campaign-20261010-sizing-feasibility.md (DR-011, canonical column)")

SUFFIX_BY_ANALYSIS = {"ac": "ac", "tran_sr": "tran-sr", "dc_swing": "dc-swing",
                      "swing_fixcm": "swing-fixcm", "icmr": "icmr",
                      "tran_sr_icmr": "tran-sr-icmr"}
ANALYSES = ("ac", "tran_sr", "dc_swing", "swing_fixcm", "icmr", "tran_sr_icmr")


class CollateError(ValueError):
    """Records cannot be collated (provenance, identity or replicate failure)."""


def fmt_pt(k):
    return f"{k[0].upper()}/{k[1]:g}C/{k[2]:g}V"


def load_record(rid: str) -> dict:
    path = REC / f"{rid}.json"
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as e:
        raise CollateError(f"cannot read record {rid}: {e}")


def read_csv(rid: str, suffix: str) -> list[dict]:
    path = REC / f"{rid}-{suffix}.csv"
    if not path.is_file():
        return []
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def key_rows(rows: list[dict], source: str) -> dict:
    out, seen = {}, set()
    for i, r in enumerate(rows, 2):
        try:
            k = point_key(r)
        except (KeyError, TypeError, ValueError) as e:
            raise CollateError(f"{source} row {i}: unusable point identity: {e}")
        if k in seen:
            raise CollateError(f"{source}: duplicate point {fmt_pt(k)}")
        seen.add(k)
        out[k] = r
    return out


def merge(ids: list[tuple[str, str]]) -> tuple[dict, list[str], list[str]]:
    """Merge (rid, role) rows per analysis with the replicate policy.

    role 'added' restricts a record to the two added tuples; role 'paired'
    drops them. Returns (analysis -> key -> row, replicate log, failed units).
    """
    merged: dict[str, dict] = {a: {} for a in ANALYSES}
    log, failed = [], []
    for rid, role in ids:
        rec = load_record(rid)
        failed += [f"{rid}: {e.split(':')[0]}" for e in rec.get("errors", [])]
        for a in ANALYSES:
            rows = key_rows(read_csv(rid, SUFFIX_BY_ANALYSIS[a]), f"{rid} {a}")
            for k, r in rows.items():
                if role == "added" and k not in ADDED_KEYS:
                    continue
                if role == "paired" and k in ADDED_KEYS:
                    continue
                if k in merged[a]:
                    old = merged[a][k]
                    for col in set(old) | set(r):
                        if col in RUN_COLS or col == "_records":
                            continue
                        if old.get(col) != r.get(col):
                            raise CollateError(
                                f"conflicting replicate {a} {fmt_pt(k)} column {col}: "
                                f"{old.get(col)!r} != {r.get(col)!r} "
                                f"(records {old['_records'][-1]} vs {rid})")
                    old["_records"].append(rid)
                    log.append(f"{a} {fmt_pt(k)}: selected {rid} (agreeing replicate "
                               f"of {'/'.join(old['_records'][:-1])})")
                else:
                    r["_records"] = [rid]
                    merged[a][k] = r
    return merged, log, failed


def validate(manifest: dict) -> list[str]:
    lines = []
    var = manifest["variant"]
    live = dut_identity.sha256_file(REPO / var["netlist"])
    if live != var["sha256"]:
        raise CollateError(f"variant netlist on disk hashes to {live}, records.json "
                           f"declares {var['sha256']}")
    canon = manifest["canonical"]
    roles = [("variant", var["sha256"], var["ids"]["runs"])]
    roles.append(("canonical", canon["sha256"], canon["ids"]["runs"]))
    fix = canon["swing_fixcm"]
    roles.append(("swing_fixcm baseline", fix["sha256"], fix["ids"]))
    for role, sha, entries in roles:
        for e in entries:
            rid = e["id"]
            rec = load_record(rid)
            state, problems = dut_identity.verify_record_dut(rec, REPO)
            if problems:
                raise CollateError(f"{rid}: " + "; ".join(problems))
            got = rec["dut"]["sha256"]
            if got != sha:
                raise CollateError(f"{rid}: cited as {role} but its DUT "
                                   f"hash is {got}, expected {sha}")
            lines.append(f"- {rid} ({role}, {e['points']} points): DUT {sha[:16]}… snapshot verified")
    lines.append(f"- variant netlist on disk hashes to the declared {var['sha256'][:16]}…")
    return lines


def pseudo(merged: dict) -> dict:
    return {"ac": merged["ac"], "tran-sr": merged["tran_sr"], "dc-swing": merged["dc_swing"]}


def gate_area(path: Path) -> tuple[dict, float]:
    per, total = {}, 0.0
    text = path.read_text().replace("\n+", " ")
    for ln in text.splitlines():
        if not ln.startswith("XM"):
            continue
        name = ln.split()[0]
        m = re.search(r"L=([\d.]+) W=([\d.]+)", ln)
        mult = re.search(r"\bm=(\d+)", ln)
        if not m or not mult:
            raise CollateError(f"cannot parse MOS card: {ln[:60]}")
        w, l, k = float(m.group(2)), float(m.group(1)), int(mult.group(1))
        per[name] = w * l * k
        total += per[name]
    return per, total


def build(manifest: dict) -> str:
    L: list[str] = []
    A = L.append
    var, canon = manifest["variant"], manifest["canonical"]

    A("# icmr-rebias screen report (issue #359) — generated by collate.py; do not edit")
    A("")
    A("Every number below resolves to a committed record listed in `records.json`")
    A("(append-only); the tables are printed, never hand-transcribed. Simulator-free.")
    A("")
    A("## Provenance validation")
    A("")
    L.extend(validate(manifest))
    A("")
    A("Failed/missing units retained (never dropped):")
    cand_ids = [(e["id"], e["points"]) for e in var["ids"]["runs"]]
    base_ids = [(e["id"], e["points"]) for e in canon["ids"]["runs"]]
    fix_ids = [(e["id"], e["points"]) for e in canon["swing_fixcm"]["ids"]]
    cand, cand_log, cand_failed = merge(cand_ids)
    base, base_log, _ = merge(base_ids)
    fix, _, _ = merge(fix_ids)
    for e in cand_failed:
        A(f"- {e}")
    if not cand_failed:
        A("- none")
    A("")
    A(f"Retry policy applied (records.json `retries`): {manifest['retries']['policy']}")
    for e in manifest["retries"]["infra_failures"]:
        A(f"- infra failure: {e}")
    A("")
    A("Replicate log:")
    for e in cand_log + base_log:
        A(f"- {e}")
    if not (cand_log or base_log):
        A("- none")
    A("")

    A("## Per-row worst case and binding corner (variants/compare.py tables)")
    A("")
    data = {var["tag"]: pseudo(cand), "canonical DR-013": pseudo(base)}
    L.extend(compare.report([var["tag"], "canonical DR-013"], data))
    A("")

    A("## ICMR window edges (candidate vs canonical DR-013 baseline)")
    A("")
    A("| Point | cand low | base low | Δlow | cand high | base high | Δhigh | cand width | base width | Δwidth "
      "| covers 0.888–1.024 (cand) | covers 0.888–1.024 (base) | covers 0.73 V (cand) | covers 0.73 V (base) |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for k in sorted(set(cand["icmr"]) | set(base["icmr"])):
        c, b = cand["icmr"].get(k), base["icmr"].get(k)
        if c and b:
            A(f"| {fmt_pt(k)} | {float(c['icmr_low_v']):.4f} | {float(b['icmr_low_v']):.4f} "
              f"| {float(c['icmr_low_v'])-float(b['icmr_low_v']):+.4f} "
              f"| {float(c['icmr_high_v']):.4f} | {float(b['icmr_high_v']):.4f} "
              f"| {float(c['icmr_high_v'])-float(b['icmr_high_v']):+.4f} "
              f"| {float(c['icmr_width_v']):.4f} | {float(b['icmr_width_v']):.4f} "
              f"| {float(c['icmr_width_v'])-float(b['icmr_width_v']):+.4f} "
              f"| {c['covers_target_window']} | {b['covers_target_window']} "
              f"| {c['covers_0v73']} | {b['covers_0v73']} |")
        else:
            A(f"| {fmt_pt(k)} | " + "unmatched" + " |")
    A("")

    A("## Fixed-common-mode swing (vs the #181 attribution record — DISCLOSED DUT")
    A("mismatch: that baseline measured the pre-DR-013 widths "
      f"{canon['swing_fixcm']['sha256'][:16]}…, not the DR-013 canonical; "
      "DR-013 measured the width move at ≤ 2.6e-5 Vpp swing and ≤ 0.003 V/us "
      "fall SR per point, so the deltas below carry that disclosed slack)")
    A("")
    A("| Point | cand width@12dB | base width@12dB | Δ | cand width@40dB | base width@40dB | Δ40dB | cand stops | base stops |")
    A("|---|---|---|---|---|---|---|---|---|")
    for k in sorted(set(cand["swing_fixcm"]) | set(fix["swing_fixcm"])):
        c, b = cand["swing_fixcm"].get(k), fix["swing_fixcm"].get(k)
        if c and b:
            A(f"| {fmt_pt(k)} | {float(c['out_width_v']):.4f} | {float(b['out_width_v']):.4f} "
              f"| {float(c['out_width_v'])-float(b['out_width_v']):+.4f} "
              f"| {float(c['out_width_v_40db']):.4f} | {float(b['out_width_v_40db']):.4f} "
              f"| {float(c['out_width_v_40db'])-float(b['out_width_v_40db']):+.4f} "
              f"| {c['low_stop']}/{c['high_stop']} | {b['low_stop']}/{b['high_stop']} |")
        else:
            A(f"| {fmt_pt(k)} | unmatched |")
    A("")

    A("## ICMR-aware vs standard fall slew (diagnostic; never merged into the row)")
    A("")
    A("`*` = the standard edge of that point comes from the merged standard-slew")
    A("campaign of the same variant (its own retry campaign carried no `tran_sr`")
    A("unit, so the row's `std_*` columns are `nan` there; never a baseline value).")
    A("")
    A("| Point | std fall V/us | in-window fall V/us | ratio | verdict |")
    A("|---|---|---|---|---|")
    nan_sub = 0
    for k in sorted(cand["tran_sr_icmr"]):
        c = cand["tran_sr_icmr"][k]
        std = c["std_sr_fall_v_per_us"]
        mark = ""
        if float(std) != float(std):  # NaN: retry campaign had no tran_sr unit
            std = cand["tran_sr"][k]["sr_fall_v_per_us"]
            mark = "*"
            nan_sub += 1
        A(f"| {fmt_pt(k)} | {float(std):.3f}{mark} "
          f"| {float(c['fall_sr_claim_v_per_us']):.3f} "
          f"| {float(c['fall_sr_claim_v_per_us'])/float(std):.3f} | {c['verdict']} |")
    A("")

    A("## Named callouts — unity-buffer swing and standard fall SR, 1.62 V / -40 C")
    A("")
    A("| Point | base Vout range (V) | cand Vout range (V) | swing base Vpp | swing cand Vpp | ΔVpp | vs 1.392 Vpp target |")
    A("|---|---|---|---|---|---|---|")
    for k in NAMED_CALLOUTS:
        c, b = cand["dc_swing"].get(k), base["dc_swing"].get(k)
        if not (c and b):
            A(f"| {fmt_pt(k)} | unmatched |")
            continue
        vpp = float(c["vpp_v"])
        base_vpp = float(b["vpp_v"])
        A(f"| {fmt_pt(k)} | {float(b['vout_min_v']):.4f}–{float(b['vout_max_v']):.4f} "
          f"| {float(c['vout_min_v']):.4f}–{float(c['vout_max_v']):.4f} "
          f"| {base_vpp:.4f} | {vpp:.4f} | {vpp-base_vpp:+.4f} | {vpp/SWING_TGT_VPP:.1%} |")
    A("")
    A(f"Fall-slew gap recovered = (candidate − baseline) / ({SR_TGT_V_US:g} V/µs − baseline), "
      "using the standard slew at the same point. A baseline at or above target has no gap.")
    A("")
    A("| Point | std fall base (V/µs) | std fall cand (V/µs) | Δ (V/µs) | gap recovered | in-window fall cand (V/µs) |")
    A("|---|---|---|---|---|---|")
    for k in NAMED_CALLOUTS:
        cs, bs = cand["tran_sr"].get(k), base["tran_sr"].get(k)
        ci = cand["tran_sr_icmr"].get(k)
        if not (cs and bs):
            A(f"| {fmt_pt(k)} | unmatched |")
            continue
        base_sr = float(bs["sr_fall_v_per_us"])
        cand_sr = float(cs["sr_fall_v_per_us"])
        delta = cand_sr - base_sr
        gap = SR_TGT_V_US - base_sr
        recovered = f"{delta/gap:.1%}" if gap > 0 else "—"
        inwin = f"{float(ci['fall_sr_claim_v_per_us']):.3f}" if ci else "—"
        A(f"| {fmt_pt(k)} | {base_sr:.3f} | {cand_sr:.3f} | {delta:+.3f} | {recovered} | {inwin} |")
    A("")

    A("## Verdict inputs against the ratified bounds (all rows, worse included)")
    A("")
    c_ac, b_ac = cand["ac"], base["ac"]

    def worst(rows, col, mode):
        k = mode(sorted(rows), key=lambda x: float(rows[x][col]))
        return float(rows[k][col]), k

    for label, col, scale, unit, mode, bound, desc in (
            ("Open-loop DC gain", "gain_dc_db", 1.0, "dB", min, GAIN_MIN_DB, "≥ 60 dB"),
            ("GBW", "gbw_hz", 1e-6, "MHz", min, GBW_TGT_MHZ, "≈ 16 MHz"),
            ("Phase margin", "phase_margin_deg", 1.0, "deg", min, PM_MIN_DEG, "≥ 60°"),
            ("Rise slew rate", "sr_rise_v_per_us", 1.0, "V/us", min, SR_TGT_V_US, "≈ 20 V/us"),
            ("Fall slew rate", "sr_fall_v_per_us", 1.0, "V/us", min, SR_TGT_V_US, "≈ 20 V/us"),
            ("Output swing (Vpp)", "vpp_v", 1.0, "V", min, SWING_TGT_VPP, "≈ 1.392 Vpp"),
            ("Quiescent power", "pq_w", 1e6, "uW", max, None, "≈ 128.7 uW @ 1.98 V / 117.0 uW @ 1.8 V")):
        src = c_ac if col in next(iter(c_ac.values()), {}) else (
            cand["tran_sr"] if col.startswith("sr_") else cand["dc_swing"])
        bsrc = b_ac if col in next(iter(b_ac.values()), {}) else (
            base["tran_sr"] if col.startswith("sr_") else base["dc_swing"])
        cv, ck = worst(src, col, mode)
        bv, bk = worst(bsrc, col, mode)
        tagv = f", bound {desc}" if bound else ""
        A(f"- **{label}** [{unit}] worst cand {cv*scale:.4g} @ {fmt_pt(ck)} vs base "
          f"{bv*scale:.4g} @ {fmt_pt(bk)}{tagv}")
    pq98c, _ = worst({k: r for k, r in c_ac.items() if k[2] == 1.98}, "pq_w", max)
    pq98b, _ = worst({k: r for k, r in b_ac.items() if k[2] == 1.98}, "pq_w", max)
    pq18c, _ = worst({k: r for k, r in c_ac.items() if k[2] == 1.8}, "pq_w", max)
    pq18b, _ = worst({k: r for k, r in b_ac.items() if k[2] == 1.8}, "pq_w", max)
    A(f"- Quiescent power @ 1.98 V: cand {pq98c*1e6:.4g} uW vs base {pq98b*1e6:.4g} uW "
      f"(estimate {PQ_TGT_98V_UW} uW); @ 1.8 V: cand {pq18c*1e6:.4g} uW vs base "
      f"{pq18b*1e6:.4g} uW (estimate {PQ_TGT_18V_UW} uW)")
    pm_bad = [fmt_pt(k) for k in sorted(c_ac) if float(c_ac[k]["phase_margin_deg"]) < PM_MIN_DEG]
    pm_bad_b = [fmt_pt(k) for k in sorted(b_ac) if float(b_ac[k]["phase_margin_deg"]) < PM_MIN_DEG]
    A(f"- Phase margin below {PM_MIN_DEG:g}°: cand {len(pm_bad)}/{len(c_ac)} points"
      + (f" ({', '.join(pm_bad)})" if pm_bad else "")
      + f"; base {len(pm_bad_b)}/{len(b_ac)}" + (f" ({', '.join(pm_bad_b)})" if pm_bad_b else ""))
    gbw_ratios = [float(c_ac[k]["gbw_hz"]) / float(b_ac[k]["gbw_hz"]) for k in c_ac.keys() & b_ac.keys()]
    if gbw_ratios:
        A(f"- Measured GBW increase at {len(gbw_ratios)} common points ranges from "
          f"{min(gbw_ratios)-1:.1%} to {max(gbw_ratios)-1:.1%}.")
    for name, rows in (("baseline", base["icmr"]), ("candidate", cand["icmr"])):
        window = sum(int(r["covers_target_window"]) for r in rows.values())
        consumer = sum(int(r["covers_0v73"]) for r in rows.values())
        A(f"- {name} ICMR covers the target window at {window}/{len(rows)} points "
          f"and 0.73 V at {consumer}/{len(rows)} points.")
    A("")
    vs, bs_area = gate_area(REPO / var["netlist"]), gate_area(REPO / "design/netlist/opamp_core.spice")
    A("## Drawn MOS gate area (W·L·mult, parsed from the committed netlists)")
    A("")
    A("| Device | canonical µm² | variant µm² |")
    A("|---|---|---|")
    for n in sorted(set(vs[0]) | set(bs_area[0])):
        A(f"| {n} | {bs_area[0].get(n, 0):.3f} | {vs[0].get(n, 0):.3f} |")
    A(f"| **total** | **{bs_area[1]:.3f}** | **{vs[1]:.3f}** "
      f"(**{(vs[1]/bs_area[1]-1)*100:+.1f}%**) |")
    A("")
    A("## Offset impact — Pelgrom HAND calculation (not simulated here)")
    A("")
    A(f"- canonical {CANON_PELGROM_MV:.2f} mV 1σ ({CANON_PELGROM_SRC})")
    A(f"- variant {float(open(HERE/'pelgrom.out.txt').read().split('TOTAL')[1].split()[0]):.2f} mV 1σ "
      "(variants/input-stage/pelgrom.out.txt, `input_stage_rebias.py pelgrom`)")
    A("- both remain far above the proposed 0.275 mV allocation (DR-009, not ratified); "
      "the variant improves the hand-calculated 1σ but does not close that row.")
    A("")
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    try:
        manifest = json.loads(MANIFEST.read_text())
        text = build(manifest)
    except (CollateError, OSError, ValueError, KeyError) as e:
        print(f"collate.py: {e}", file=sys.stderr)
        return 1
    if a.check:
        if REPORT.is_file() and REPORT.read_text() == text:
            print("OK: report.out.md is current")
            return 0
        print("STALE: report.out.md does not match the committed records", file=sys.stderr)
        return 1
    REPORT.write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
