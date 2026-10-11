#!/usr/bin/env python3
"""Paired offset-drift screen for ideal single-point correction (issue #196).

Executes the plan committed in records/offset-drift-plan-196.json: one
immutable DUT snapshot, the same 100 mismatch sample IDs measured at a
reference condition (TT, 27 C, 1.8 V) and at -40/125 C x 1.62/1.98 V, and the
per-sample residual Vos(condition) - Vos(reference) joined by sample ID.

  offset_drift.py run    --label NAME [--backend NAME] [--dry-run]
  offset_drift.py resume --label NAME [--backend NAME]
  offset_drift.py report --label NAME          # recompute from committed records

Every request goes through `klt sim` (one at a time, as `monte_carlo`
requests; the batch fleet on dispatch hosts). This script never launches
ngspice. The execution state is the committed attempt ledger (one
`*.summary.json` per attempt, tagged with `drift`), so `resume` and `report`
recompute everything from raw records and nothing is rewritten (append-only).

A drift verdict is issued only when the pairing evidence of the plan holds;
otherwise the result is a CAPABILITY GAP and no drift conclusion is drawn.
Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import offset_probe as op  # noqa: E402
from offset_probe import RECORDS, REPO  # noqa: E402
import dut_identity  # noqa: E402
from spice_harness import allocate_record_id, write_new  # noqa: E402

PLAN_PATH = RECORDS / "offset-drift-plan-196.json"
SAMPLE_REPLAY_TOL_V = op.CONTROL_TOL_V   # 40 uV, plan: pairing_evidence


class DriftError(RuntimeError):
    pass


# ------------------------------------------------------------ statistics ----

def _betacf(a: float, b: float, x: float) -> float:
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 500):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            break
    return h


def betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    front = math.exp(lbeta + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def gammainc(a: float, x: float) -> float:
    """Regularized lower incomplete gamma P(a, x)."""
    if x <= 0.0:
        return 0.0
    if x < a + 1.0:
        term = total = 1.0 / a
        n = a
        for _ in range(2000):
            n += 1.0
            term *= x / n
            total += term
            if abs(term) < abs(total) * 1e-16:
                break
        return total * math.exp(-x + a * math.log(x) - math.lgamma(a))
    tiny = 1e-300
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / b
    h = d
    for i in range(1, 2000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = b + an / c
        c = c if abs(c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            break
    return 1.0 - math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def t_cdf(t: float, dof: float) -> float:
    tail = 0.5 * betainc(dof / 2.0, 0.5, dof / (dof + t * t))
    return 1.0 - tail if t > 0 else tail


def t_quantile(p: float, dof: float) -> float:
    """Quantile of Student t (p in (0.5, 1)) by bisection on the exact cdf."""
    lo, hi = 0.0, 1.0
    while t_cdf(hi, dof) < p:
        hi *= 2.0
        if hi > 1e6:
            raise DriftError("t quantile did not bracket")
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if t_cdf(mid, dof) < p else (lo, mid)
    return 0.5 * (lo + hi)


def chi2_quantile(p: float, dof: float) -> float:
    """Quantile of chi-square by bisection on the exact cdf."""
    lo, hi = 0.0, max(1.0, dof)
    while gammainc(dof / 2.0, hi / 2.0) < p:
        hi *= 2.0
        if hi > 1e9:
            raise DriftError("chi2 quantile did not bracket")
    for _ in range(300):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if gammainc(dof / 2.0, mid / 2.0) < p else (lo, mid)
    return 0.5 * (lo + hi)


def paired_stats(ref: dict, cond: dict, ids: list[str], *, confidence: float = 0.95,
                 min_pairs: int = 80, screen_mv: float = 0.19) -> dict:
    """Paired residual statistics, joined by sample ID.

    `ref` / `cond` map ID -> {"ok": bool, "vos_v": float, "seed": rndseed,
    "reason": str}. Only IDs that are ok in BOTH and carry equal seeds form a
    valid pair; every other requested ID is counted and listed, never zero.
    Units: residual and statistics in mV.
    """
    resid, dropped, seed_mismatch = {}, {}, []
    for i in ids:
        r, c = ref.get(i), cond.get(i)
        if r is None or not r.get("ok"):
            dropped[i] = "reference failed: " + str((r or {}).get("reason") or "not returned")
        elif c is None or not c.get("ok"):
            dropped[i] = "condition failed: " + str((c or {}).get("reason") or "not returned")
        elif r.get("seed") != c.get("seed"):
            dropped[i] = "rndseed differs from reference"
            seed_mismatch.append(i)
        else:
            resid[i] = (c["vos_v"] - r["vos_v"]) * 1e3
    vals = [resid[i] for i in ids if i in resid]
    n = len(vals)
    out = {"n_requested": len(ids), "n_returned": sum(1 for i in ids if i in cond),
           "n_valid_pairs": n, "n_dropped": len(dropped),
           "n_failed_condition": sum(1 for i, w in dropped.items() if w.startswith("condition")),
           "n_failed_reference": sum(1 for i, w in dropped.items() if w.startswith("reference")),
           "dropped": dropped, "seed_mismatch_ids": seed_mismatch,
           "mean_mv": None, "sigma_mv": None, "max_abs_mv": None,
           "mean_ci_mv": None, "sigma_ci_mv": None, "confidence": confidence,
           "sigma_screen_mv": screen_mv, "min_valid_pairs": min_pairs, "verdict": "INCONCLUSIVE",
           "verdict_reason": None}
    if n:
        mean = math.fsum(vals) / n
        out.update(mean_mv=mean, max_abs_mv=max(abs(v) for v in vals))
    if n >= 2:
        sd = math.sqrt(math.fsum((v - mean) ** 2 for v in vals) / (n - 1))
        dof = n - 1
        tq = t_quantile(0.5 + confidence / 2.0, dof)
        half = tq * sd / math.sqrt(n)
        a = (1.0 - confidence) / 2.0
        lo = sd * math.sqrt(dof / chi2_quantile(1.0 - a, dof))
        hi = sd * math.sqrt(dof / chi2_quantile(a, dof))
        out.update(sigma_mv=sd, mean_ci_mv=[mean - half, mean + half], sigma_ci_mv=[lo, hi])
        if n < min_pairs:
            out["verdict_reason"] = f"only {n} valid pairs (< {min_pairs})"
        elif hi < screen_mv:
            out.update(verdict="PASS_SCREEN", verdict_reason=f"sigma upper bound {hi:.4f} < {screen_mv} mV")
        elif lo > screen_mv:
            out.update(verdict="FAIL_SCREEN", verdict_reason=f"sigma lower bound {lo:.4f} > {screen_mv} mV")
        else:
            out["verdict_reason"] = (f"sigma interval [{lo:.4f}, {hi:.4f}] mV contains the "
                                     f"{screen_mv} mV screen")
    else:
        out["verdict_reason"] = f"only {n} valid pairs"
    return out


# ----------------------------------------------------- response handling ----

def load_plan(path: Path = PLAN_PATH) -> dict:
    plan = json.loads(Path(path).read_text())
    for k in ("sequence", "conditions", "budget", "dut", "seed_and_sample_mapping"):
        if k not in plan:
            raise DriftError(f"plan {path} lacks {k!r}")
    return plan


def step_table(plan: dict) -> dict:
    return {s["step"]: s for s in plan["sequence"]}


def sample_id(seed: int, index: int) -> str:
    return f"{seed}/{index}"


def build_step_request(plan: dict, step: dict, netlist: str) -> dict:
    cond = plan["conditions"][step["condition"]]
    mc = {"n": step["n"], "seed": step["seed"]}
    return op.build_request("offset", True, mc, corner="tt", keep_artifacts=False, netlist=netlist,
                            temperature_c=cond["temperature_c"], vdd=cond["vdd_v"])


def validate_response(payload, step: dict, cond: dict) -> tuple[list[str], dict]:
    """(batch-level problems, ID -> sample) for a klt response.

    Problems make the ATTEMPT unaccepted (plan: attempt_acceptance). Within an
    accepted attempt, a failed sample stays a failed sample. Duplicate and
    out-of-range IDs are batch-level problems (no ID is trusted)."""
    probs: list[str] = []
    if not isinstance(payload, dict) or not isinstance(payload.get("corners"), list):
        return ["response has no corners[]"], {}
    mc = {"n": step["n"], "seed": step["seed"]}
    probs += op.check_echo(payload, mc, cond["process"])
    samples = op.extract_samples(payload, "offset")
    by_id: dict[str, dict] = {}
    for c, s in zip(payload["corners"], samples):
        m = c.get("monte_carlo") if isinstance(c.get("monte_carlo"), dict) else {}
        idx = m.get("sample_index")
        if not isinstance(idx, int) or isinstance(idx, bool) or not 0 <= idx < step["n"]:
            probs.append(f"sample with unusable sample_index {idx!r}")
            continue
        sid = sample_id(step["seed"], idx)
        if sid in by_id:
            probs.append(f"duplicate sample id {sid}")
            continue
        T, V = c.get("temperature_c"), (c.get("supply_v") or {}).get("vdd")
        if not (op._num(T) and abs(T - cond["temperature_c"]) < 1e-9):
            probs.append(f"{sid}: temperature echo {T!r} != requested {cond['temperature_c']!r}")
        if not (op._num(V) and abs(V - cond["vdd_v"]) < 1e-9):
            probs.append(f"{sid}: vdd echo {V!r} != requested {cond['vdd_v']!r}")
        rec = {"ok": bool(s["ok"] and op._num(s.get("vos_v"))), "reason": s.get("reason"),
               "seed": m.get("seed"), "process_seed": m.get("process_seed"),
               "mismatch_seed": m.get("mismatch_seed")}
        if rec["ok"]:
            rec["vos_v"] = s["vos_v"]
        elif rec["reason"] is None:
            rec["reason"] = "ok flag without finite vos_v"
        by_id[sid] = rec
    return probs, by_id


def provenance(payload: dict) -> dict:
    env = (payload or {}).get("environment") or {}
    remote = env.get("remote") or {}
    return {"job_id": remote.get("job_id"), "runner_klt_version": remote.get("runner_klt_version"),
            "client_klt_version": remote.get("client_klt_version"),
            "runner_compatibility": remote.get("runner_compatibility"),
            "instance_type": remote.get("instance_type"),
            "engine": env.get("engine"), "engine_version": env.get("engine_version"),
            "models_lib_sha256": env.get("models_lib_sha256"), "netlist_sha256": env.get("netlist_sha256")}


# ------------------------------------------------------------- the ledger ----

def load_ledger(label: str, records: Path | None = None) -> dict[str, list[dict]]:
    """step -> attempt metas (ordered by record id = time), read from committed
    summaries. A request file with NO summary (the run was interrupted while
    the request was in flight) is an orphan attempt: it is counted against the
    caps, as an unaccepted attempt, because it may have reached the backend."""
    records = Path(records) if records else RECORDS
    led: dict[str, list[dict]] = {}
    seen = set()
    for p in sorted(records.glob("*.summary.json")):
        try:
            meta = json.loads(p.read_text())
        except ValueError:
            continue
        d = meta.get("drift") if isinstance(meta, dict) else None
        if isinstance(d, dict) and d.get("label") == label:
            meta["_path"] = str(p)
            seen.add(meta["record_id"])
            led.setdefault(d["step"], []).append(meta)
    pat = re.compile(rf"^(\d{{8}}-\d{{6}}-offset-{re.escape(label)}-(?P<step>[A-Za-z0-9_]+?)(?:-r\d+)?-[0-9a-f]{{6}})\.request\.json$")
    for p in sorted(records.glob("*.request.json")):
        m = pat.match(p.name)
        if m and m.group(1) not in seen and m.group("step") in {"B0_ref", "P0_replay", "B1", "B2", "B3", "B4"}:
            led.setdefault(m.group("step"), []).append(
                {"record_id": m.group(1), "exit_code": None, "orphan": True,
                 "stderr": "orphan request: no summary record (run interrupted while in flight)",
                 "drift": {"label": label, "step": m.group("step"), "attempt": 0}})
    for v in led.values():
        v.sort(key=lambda m: m["record_id"])
        for i, m in enumerate(v, 1):
            m["drift"]["attempt"] = i
    return led


def evaluate_attempt(meta: dict, step: dict, cond: dict, records: Path | None = None) -> dict:
    """Re-read an attempt's raw klt report and judge it. Pure function of the
    committed records, so execution and `report` agree."""
    records = Path(records) if records else RECORDS
    path = records / f"{meta['record_id']}.klt.json"
    payload = None
    if path.is_file():
        try:
            payload = json.loads(path.read_text())
        except ValueError:
            payload = None
    if not isinstance(payload, dict):
        return {"record_id": meta["record_id"], "attempt": meta["drift"]["attempt"], "accepted": False,
                "problems": [f"no usable klt report (exit {meta.get('exit_code')}; "
                             f"{(meta.get('stderr') or '').strip()[-200:]})"], "samples": {}, "provenance": {}}
    probs, by_id = validate_response(payload, step, cond)
    return {"record_id": meta["record_id"], "attempt": meta["drift"]["attempt"], "accepted": not probs,
            "problems": probs, "samples": by_id, "provenance": provenance(payload)}


def resolve_steps(plan: dict, led: dict, records: Path | None = None) -> dict:
    """step -> {"attempts": [evaluated...], "accepted": evaluated|None, "status"}."""
    steps = step_table(plan)
    out = {}
    for name, step in steps.items():
        cond = plan["conditions"][step["condition"]]
        ev = [evaluate_attempt(m, step, cond, records) for m in led.get(name, [])]
        acc = next((e for e in ev if e["accepted"]), None)
        cap = plan["budget"]["max_attempts_probe" if step["kind"] == "probe" else "max_attempts_per_logical_batch"]
        status = ("ACCEPTED" if acc else "FAILED_BATCH" if len(ev) >= cap else
                  "PENDING" if not ev else "RETRYING")
        out[name] = {"attempts": ev, "accepted": acc, "status": status}
    return out


def pairing_evidence(plan: dict, res: dict) -> dict:
    """Evaluate the plan's required pairing evidence. Each item is
    ok=True / False / None (None: not yet evaluable because its steps are
    unresolved). Missing evidence is never an implicit pass."""
    steps = step_table(plan)
    items = {}
    ref = (res.get("B0_ref") or {}).get("accepted")
    probe = (res.get("P0_replay") or {}).get("accepted")
    cond_names = [n for n, s in steps.items() if s["kind"] == "batch" and n != "B0_ref"]
    accepted_conds = [n for n in cond_names if res.get(n, {}).get("accepted")]

    # 1. echoed seeds equal to the reference's, per sample ID
    if not ref:
        items["echoed_seeds_equal"] = {"ok": False if res["B0_ref"]["status"] == "FAILED_BATCH" else None,
                                       "detail": "no accepted reference batch"}
    else:
        seed_bad = {}
        for n in accepted_conds:
            acc = res[n]["accepted"]
            bad = [i for i, s in acc["samples"].items()
                   if i in ref["samples"] and any(s.get(k) != ref["samples"][i].get(k)
                                                  for k in ("seed", "process_seed", "mismatch_seed"))]
            missing = [i for i, s in acc["samples"].items()
                       if s.get("seed") is None or s.get("mismatch_seed") is None]
            if bad or missing:
                seed_bad[n] = {"differing_ids": bad, "ids_without_echoed_seed": missing}
        items["echoed_seeds_equal"] = {"ok": (not seed_bad) if accepted_conds else None,
                                       "checked_conditions": accepted_conds, "detail": seed_bad or None}

    # 2. replay probe reproduces reference sample 0
    rid = sample_id(steps["B0_ref"]["seed"], 0)
    if ref and probe and rid in probe["samples"] and rid in ref["samples"]:
        a_, b_ = ref["samples"][rid], probe["samples"][rid]
        if a_["ok"] and b_["ok"]:
            diff = b_["vos_v"] - a_["vos_v"]
            items["replay_probe"] = {"ok": a_["seed"] == b_["seed"] and abs(diff) <= SAMPLE_REPLAY_TOL_V,
                                     "sample_id": rid, "vos_diff_uv": diff * 1e6,
                                     "tolerance_uv": SAMPLE_REPLAY_TOL_V * 1e6,
                                     "seed_equal": a_["seed"] == b_["seed"]}
        else:
            items["replay_probe"] = {"ok": False, "sample_id": rid,
                                     "detail": "reference or replay sample failed; replay not verifiable"}
    elif res["P0_replay"]["status"] == "FAILED_BATCH" or res["B0_ref"]["status"] == "FAILED_BATCH":
        items["replay_probe"] = {"ok": False, "detail": "reference batch or replay probe failed after the attempt cap"}
    else:
        items["replay_probe"] = {"ok": None, "detail": "reference batch / replay probe not yet accepted"}

    # 3. runner / engine / model provenance identical across accepted attempts
    keys = ("runner_klt_version", "engine_version", "models_lib_sha256", "netlist_sha256")
    used = {n: r["accepted"]["provenance"] for n, r in res.items() if r.get("accepted")}
    spread = {k: sorted({str(p.get(k)) for p in used.values()}) for k in keys}
    unknown = [n for n, p in used.items() if any(p.get(k) is None for k in keys[:3])]
    items["provenance_identical"] = {
        "ok": (all(len(v) == 1 for v in spread.values()) and not unknown) if used else None,
        "values": spread, "steps_missing_provenance": unknown}
    return {"items": items}


def drift_report(plan: dict, led: dict, records: Path | None = None) -> dict:
    """Everything the study record states, as a pure function of the ledger."""
    res = resolve_steps(plan, led, records)
    steps = step_table(plan)
    stat_cfg = plan["statistics"]
    screen = plan["screen"]["sigma_screen_mv"]
    ev = pairing_evidence(plan, res)
    ref = (res["B0_ref"] or {}).get("accepted")
    ids = [sample_id(steps["B0_ref"]["seed"], i) for i in range(steps["B0_ref"]["n"])]
    conds, sanity = {}, {}
    ref_sigma_mv = None
    if ref:
        rv = [s["vos_v"] * 1e3 for s in ref["samples"].values() if s["ok"]]
        if len(rv) >= 2:
            m = math.fsum(rv) / len(rv)
            ref_sigma_mv = math.sqrt(math.fsum((v - m) ** 2 for v in rv) / (len(rv) - 1))
    for name, step in steps.items():
        if step["kind"] != "batch" or name == "B0_ref":
            continue
        acc = res[name]["accepted"]
        entry = {"condition": plan["conditions"][step["condition"]], "step": name,
                 "status": res[name]["status"], "attempts": len(res[name]["attempts"])}
        if ref and acc:
            st = paired_stats(ref["samples"], acc["samples"], ids, confidence=stat_cfg["confidence_level"],
                              min_pairs=stat_cfg["minimum_valid_pairs"], screen_mv=screen)
            entry["stats"] = st
            if ref_sigma_mv is not None and st["sigma_mv"] is not None:
                sanity[name] = {"ok": st["sigma_mv"] < 0.5 * ref_sigma_mv,
                                "residual_sigma_mv": st["sigma_mv"], "reference_sigma_mv": ref_sigma_mv,
                                "limit_mv": 0.5 * ref_sigma_mv}
        else:
            entry["stats"] = None
            entry["verdict"] = "NOT_MEASURED"
        conds[name] = entry
    ev["items"]["statistical_sanity_gate"] = {
        "ok": all(v["ok"] for v in sanity.values()) if sanity else None, "per_condition": sanity or None}
    items = ev["items"]
    ev["failed_items"] = sorted(k for k, v in items.items() if v["ok"] is False)
    ev["unevaluated_items"] = sorted(k for k, v in items.items() if v["ok"] is None)
    steps_done = {n: r["status"] for n, r in res.items()}
    if steps_done["B0_ref"] == "FAILED_BATCH" or steps_done["P0_replay"] == "FAILED_BATCH":
        outcome = "STOPPED_NO_REFERENCE_OR_PROBE"
    elif ev["failed_items"]:
        outcome = "CAPABILITY_GAP_NO_VERDICT"
    elif all(x == "PENDING" for x in steps_done.values()):
        outcome = "NOT_RUN"
    elif any(x in ("PENDING", "RETRYING") for x in steps_done.values()):
        outcome = "INCOMPLETE"
    elif ev["unevaluated_items"]:
        outcome = "CAPABILITY_GAP_NO_VERDICT"
    else:
        outcome = "VERDICTS_ISSUED"
    verdicts = ({n: ({"verdict": c["stats"]["verdict"], "reason": c["stats"]["verdict_reason"]}
                     if c.get("stats") else {"verdict": "NOT_MEASURED"}) for n, c in conds.items()}
                if outcome == "VERDICTS_ISSUED" else None)
    requests = sum(len(r["attempts"]) for r in res.values())
    return {"plan": str(PLAN_PATH.relative_to(REPO)) if PLAN_PATH.is_absolute() else str(PLAN_PATH),
            "outcome": outcome, "step_status": steps_done, "pairing_evidence": ev,
            "reference": {"n_requested": len(ids), "n_ok": sum(1 for s in (ref or {"samples": {}})["samples"].values() if s["ok"]),
                          "sigma_mv": ref_sigma_mv},
            "conditions": conds, "verdicts": verdicts,
            "accounting": {"requests_submitted": requests, "max_requests": plan["budget"]["max_requests"],
                           "attempts": {n: [{"record_id": a["record_id"], "attempt": a["attempt"],
                                             "accepted": a["accepted"], "problems": a["problems"][:5],
                                             "job_id": a["provenance"].get("job_id")}
                                            for a in r["attempts"]] for n, r in res.items()}},
            "provenance": {n: r["accepted"]["provenance"] for n, r in res.items() if r["accepted"]}}


# ------------------------------------------------------------- execution ----

def default_submit(req: dict, label: str, backend: str | None, extra: dict) -> None:
    op.run_one(req, label, backend, mc=req["monte_carlo"], extra=extra)


def budget_ok(plan: dict, led: dict, step: dict) -> tuple[bool, str]:
    total = sum(len(v) for v in led.values())
    cap = plan["budget"]["max_attempts_probe" if step["kind"] == "probe" else "max_attempts_per_logical_batch"]
    if total >= plan["budget"]["max_requests"]:
        return False, f"request budget {plan['budget']['max_requests']} exhausted"
    if len(led.get(step["step"], [])) >= cap:
        return False, f"{step['step']}: {cap} attempts used"
    return True, ""


def execute(plan: dict, label: str, snap_dir: Path, dut: dict, backend: str | None = None,
            submit=default_submit, records: Path | None = None, log=lambda m: print(m, flush=True), retry_wait_s: float = 0) -> dict:
    """Run (or resume) the plan sequentially; return the final report dict.

    Retries only whole requests, same IDs, until accepted or the cap. Stops
    as the plan says: no reference/probe -> end; pairing evidence failed ->
    end before the next condition batch (capability gap, no verdict)."""
    netlist = op.snapshot_netlist(snap_dir)
    steps = step_table(plan)
    for name in [s["step"] for s in plan["sequence"]]:
        step = steps[name]
        while True:
            led = load_ledger(label, records)
            res = resolve_steps(plan, led, records)
            if res[name]["accepted"]:
                break
            ok, why = budget_ok(plan, led, step)
            if not ok:
                log(f"STOP {name}: {why}")
                break
            attempt = len(led.get(name, [])) + 1
            if attempt > 1 and retry_wait_s:
                log(f"{name}: attempt {attempt - 1} not accepted; waiting {retry_wait_s}s before the retry")
                time.sleep(retry_wait_s)
            req = build_step_request(plan, step, netlist)
            extra = {"dut": dut, "drift": {"label": label, "step": name, "attempt": attempt,
                                          "condition": step["condition"], "plan": PLAN_PATH.name}}
            submit(req, f"{label}-{name}" + ("" if attempt == 1 else f"-r{attempt}"), backend, extra)
            led = load_ledger(label, records)
            res = resolve_steps(plan, led, records)
            last = res[name]["attempts"][-1]
            log(json.dumps({"step": name, "attempt": attempt, "accepted": last["accepted"],
                            "problems": last["problems"][:3], "job_id": last["provenance"].get("job_id")}))
            if last["accepted"]:
                break
        rep = drift_report(plan, load_ledger(label, records), records)
        if rep["outcome"] in ("STOPPED_NO_REFERENCE_OR_PROBE", "CAPABILITY_GAP_NO_VERDICT"):
            log(f"STOP after {name}: {rep['outcome']} {rep['pairing_evidence']['failed_items']}")
            break
    return drift_report(plan, load_ledger(label, records), records)


def open_snapshot(plan: dict, label: str, resume: bool) -> tuple[Path, dict]:
    snap_dir = RECORDS / f"dut-{label}"
    if resume:
        meta = snap_dir / op.RENDERED_BENCH
        dut_file = snap_dir / dut_identity.SNAPSHOT_NAME
        if not (meta.is_file() and dut_file.is_file()):
            raise DriftError(f"cannot resume {label!r}: no DUT snapshot at {snap_dir}")
        sha = dut_identity.sha256_file(dut_file)
        dut = {"source_path": plan["dut"]["source_path"],
               "snapshot_path": dut_file.resolve().relative_to(REPO).as_posix(), "sha256": sha}
    else:
        RECORDS.mkdir(exist_ok=True)
        dut = op.capture_offset_dut(snap_dir)
    if dut["sha256"] != plan["dut"]["sha256"]:
        raise DriftError(f"DUT hash {dut['sha256']} != plan {plan['dut']['sha256']}: the live design "
                         "changed since the plan was committed; write a new plan, do not edit this one")
    return snap_dir, dut


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("run", "resume", "report"):
        p = sub.add_parser(name)
        p.add_argument("--label", required=True)
        if name != "report":
            p.add_argument("--backend")
            p.add_argument("--retry-wait-s", type=float, default=300,
                           help="wait before a retry (fleet-capacity refusals are common); default 300")
        if name == "run":
            p.add_argument("--dry-run", action="store_true",
                           help="capture the DUT, write (not submit) the six request files")
        if name == "report":
            p.add_argument("--write", action="store_true", help="write the report as a new *.drift.json record")
    a = ap.parse_args(argv)
    plan = load_plan()
    if a.cmd == "report":
        rep = drift_report(plan, load_ledger(a.label))
    else:
        snap_dir, dut = open_snapshot(plan, a.label, a.cmd == "resume")
        if getattr(a, "dry_run", False):
            for s in plan["sequence"]:
                rid = allocate_record_id(RECORDS, f"offset-{a.label}-{s['step']}")
                write_new(RECORDS / f"{rid}.request.json",
                          json.dumps(build_step_request(plan, s, op.snapshot_netlist(snap_dir)), indent=2) + "\n")
                print(rid)
            return 0
        rep = execute(plan, a.label, snap_dir, dut, a.backend, retry_wait_s=a.retry_wait_s)
        rep = {"label": a.label, "dut": dut, **rep}
        a.write = True
    if a.write:
        rid = allocate_record_id(RECORDS, f"drift-{a.label}")
        write_new(RECORDS / f"{rid}.drift.json", json.dumps(rep, indent=2) + "\n")
        print(f"wrote {rid}.drift.json")
    print(json.dumps({"outcome": rep["outcome"], "verdicts": rep["verdicts"],
                      "failed_pairing_items": rep["pairing_evidence"]["failed_items"]}, indent=2))
    return 0 if rep["outcome"] == "VERDICTS_ISSUED" else 1


if __name__ == "__main__":
    sys.exit(main())
