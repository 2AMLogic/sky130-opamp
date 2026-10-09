#!/usr/bin/env python3
"""Seeded-mismatch offset probe (#52) and offset Monte Carlo campaign (#85).

Builds `klt sim` requests for two small benches, runs them through the actual
backend, and extracts results with explicit failure semantics.

  pair   bench/pair_diag.cir  -- identical-device-pair drain-current differences
  offset bench/offset_dc.cir  -- open-loop input-referred offset (output
                                 crossing VDD/2 on a DC input sweep)

Usage:
  offset_probe.py run --bench pair|offset --label NAME [--mismatch on|off]
                      [--seed N --n N] [--backend NAME] [--dry-run]
  offset_probe.py campaign --label NAME --base-seed N [--corners tt,ss,ff]
                      [--only corner:chunk,...] [--resume]
                      [--n-total 300 --chunk 100] [--backend NAME] [--dry-run]
  offset_probe.py summarize CHUNK.summary.json ...

`campaign` submits the offset bench once per (corner, chunk) as a seeded
`monte_carlo` `klt sim` request (`<corner>_mm` library section, chunk seed =
base seed + chunk index), sequentially, retrying fleet-capacity failures as
new records, then aggregates per corner (mean, sigma, failed count) with the
same extractor as `run`. `summarize` re-aggregates committed chunk records.

`--mismatch on` selects `.lib tt_mm` (mc_mm_switch=1), `off` selects `.lib tt`
(mc_mm_switch=0). Multi-sample requests (`--n` > 1) are submitted through
`klt sim` only; this script never launches ngspice itself. Its only loop is
`campaign`'s sequential series of `klt sim` requests (one at a time, each
expanded and executed by klt on its backend -- the batch fleet on dispatch
hosts). Campaign requests set `keep_artifacts: false`: every per-sample value
and seed is in the committed klt report, and 1500 per-sample deck/log
directories would bloat the evidence tree. Stdlib only.

DUT identity (issue #113). Every new offset campaign (and standalone full-opamp
`run --bench offset`) captures the design netlist ONCE, via
sim/lib/dut_identity.py, into `records/dut-<label>/` together with a rendered
bench (`offset_dc.spice`) whose include resolves to that copy. Every chunk,
retry and resumed submission uses that rendered bench, so editing the live
netlist mid-campaign cannot change what is simulated. Chunk summaries and the
campaign report carry the `dut` block (snapshot path + SHA-256); `--resume`
re-reads the campaign's original snapshot and seed/chunk plan
(`dut-<label>/campaign.plan.json`) and never recaptures today's design.
`summarize` rejects missing/corrupt snapshots and mixed DUT hashes; records
without a `dut` block are legacy and reported UNVERIFIED. The pair diagnostic
bench is out of scope and unchanged.
"""
from __future__ import annotations

import argparse
import json
import re
import math
import os
import subprocess
import sys
import time
from pathlib import Path

EXP = Path(__file__).resolve().parent.parent
REPO = EXP.parent.parent
RECORDS = EXP / "records"
sys.path.insert(0, str(REPO / "sim" / "lib"))
import dut_identity  # noqa: E402
from spice_harness import (KltSimError, allocate_record_id, klt_sim,  # noqa: E402
                           klt_version, write_new)

DESIGN_NETLIST = REPO / "design" / "netlist" / "opamp_core.spice"
BENCH_TEMPLATE = EXP / "bench" / "offset_dc.cir"
RENDERED_BENCH = "offset_dc.spice"   # in the snapshot dir; ``*.spice`` so dut_identity checks its include
PLAN_NAME = "campaign.plan.json"
_INCLUDE_LINE = re.compile(r'^(\s*\.(?:include|inc)\s+)"?[^"\s]*opamp_core\.spice"?', re.IGNORECASE | re.MULTILINE)

VDD = 1.8
VREF = VDD / 2          # output reference for the offset crossing
VCM = 0.9               # inn held here; inp = VCM + vd
SWEEP_LO, SWEEP_HI, SWEEP_STEP = -0.03, 0.03, 20e-6   # vd bracket / resolution (V)
# Predeclared tolerances (see README "Predeclared tolerances").
EXTRACTION_RES_V = SWEEP_STEP          # linear interp between 20 uV points
CONTROL_TOL_V = 2 * EXTRACTION_RES_V   # mismatch-off spread / replay mismatch
PAIR_CONTROL_TOL_A = 1e-9              # |id1-id2| floor with mismatch off
PAIR_MIN_SPREAD_A = 10e-9              # randomized pair diff must exceed this


class ProbeError(RuntimeError):
    pass


CORNERS = ("tt", "ss", "ff", "sf", "fs")


def render_bench(template_text: str) -> str:
    """The offset bench with its DUT include pointed at the sibling snapshot."""
    out, n = _INCLUDE_LINE.subn(rf'\1"{dut_identity.SNAPSHOT_NAME}"', template_text)
    if n != 1:
        raise ProbeError(f"offset bench template must include the DUT exactly once (found {n})")
    return out


def capture_offset_dut(snap_dir: Path) -> dict:
    """Capture the DUT once into a fresh ``snap_dir`` and render the bench
    against it. Returns the ``dut`` metadata block. Refuses an existing dir."""
    snap_dir = Path(snap_dir)
    try:
        snap_dir.mkdir(parents=True)
    except FileExistsError:
        raise ProbeError(f"DUT snapshot {snap_dir} already exists; use --resume to continue that campaign") from None
    dut = dut_identity.capture_dut(DESIGN_NETLIST, snap_dir, REPO)
    write_new(snap_dir / RENDERED_BENCH, render_bench(BENCH_TEMPLATE.read_text()))
    return dut


def snapshot_netlist(snap_dir: Path) -> str:
    """Request ``netlist`` value (relative to RECORDS) for a captured bench."""
    return os.path.relpath(Path(snap_dir) / RENDERED_BENCH, RECORDS)


def build_request(bench: str, mismatch: bool, mc: dict | None,
                  corner: str = "tt", keep_artifacts: bool = True,
                  netlist: str | None = None) -> dict:
    """`netlist` (offset bench only) overrides the bench path: #113 uses it for the
    per-campaign DUT snapshot, #107 for per-device-group gated variants from
    bin/attribution.py; analysis and measurements are unchanged."""
    cir = {"pair": "../bench/pair_diag.cir", "offset": netlist or "../bench/offset_dc.cir"}[bench]
    if bench == "pair":
        analysis = {"kind": "dc", "args": "Vg 0.79 0.81 0.01"}
        meas = [
            {"name": n, "spice": f".meas dc {n} find i({s}) at=0.8", "unit": "A"}
            for n, s in (("idn1", "Vn1"), ("idn2", "Vn2"), ("idp1", "Vp1"), ("idp2", "Vp2"))
        ]
    else:
        analysis = {"kind": "dc", "args": f"Vd {SWEEP_LO} {SWEEP_HI} {SWEEP_STEP:g}"}
        meas = [
            {"name": "vos_inp", "spice": f".meas dc vos_inp find v(inp) when v(out)={VREF} rise=1", "unit": "V"},
            {"name": "out_lo", "spice": f".meas dc out_lo find v(out) at={SWEEP_LO}", "unit": "V"},
            {"name": "out_hi", "spice": f".meas dc out_hi find v(out) at={SWEEP_HI - SWEEP_STEP:.6f}", "unit": "V"},
        ]
    req = {
        "netlist": cir,
        "netlist_source": "schematic",
        "models": {"pdk": "sky130A", "lib": "libs.tech/ngspice/sky130.lib.spice"},
        "corners": {
            "process": [f"{corner}_mm" if mismatch else corner],
            "supply_v": {"vdd": [VDD]},
            "temperature_c": [27.0],
        },
        "analysis": analysis,
        "measurements": meas,
        "options": {"timeout_s": 600, "keep_artifacts": keep_artifacts},
        "batch": {"runner_version_check": "warn"},
    }
    if mc:
        req["monte_carlo"] = {"n": mc["n"], "seed": mc["seed"], "vary": "mismatch"}
    return req


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def extract_samples(payload: dict, bench: str) -> list[dict]:
    """Per-corner/sample results. A sample that lacks a finite value for any
    required measurement, or whose output does not bracket VREF, is returned
    with ok=False and a reason -- never as zero offset."""
    if not isinstance(payload, dict) or not isinstance(payload.get("corners"), list):
        raise ProbeError("klt payload has no corners[]")
    need = ("idn1", "idn2", "idp1", "idp2") if bench == "pair" else ("vos_inp", "out_lo", "out_hi")
    out = []
    for c in payload["corners"]:
        vals = {m.get("name"): m.get("value") for m in c.get("measurements", []) if isinstance(m, dict)}
        s = {"corner_id": c.get("corner_id"), "klt_status": c.get("status"),
             "monte_carlo": c.get("monte_carlo"), "ok": True, "reason": None}
        missing = [k for k in need if not _num(vals.get(k))]
        if c.get("status") not in ("pass",):
            s.update(ok=False, reason=f"corner status {c.get('status')!r}")
        elif missing:
            s.update(ok=False, reason=f"missing/non-finite measurement(s): {missing}")
        elif bench == "pair":
            s["dn"] = vals["idn1"] - vals["idn2"]
            s["dp"] = vals["idp1"] - vals["idp2"]
        else:
            lo, hi = vals["out_lo"], vals["out_hi"]
            if not (lo < VREF < hi):
                s.update(ok=False, reason=f"output does not bracket VREF (out_lo={lo}, out_hi={hi})")
            else:
                s["vos_v"] = vals["vos_inp"] - VCM   # Vos = V(inp)-V(inn) at crossing
        out.append(s)
    return out


def run_klt(request_path: Path, outdir: Path, backend: str | None):
    """(cmd, exit code, JSON report or None if klt printed none, stderr)."""
    try:
        return klt_sim(request_path, outdir, backend)
    except KltSimError as exc:
        return exc.cmd, exc.returncode, None, exc.stderr


# ---------------------------------------------------------------- campaign --

def check_echo(payload: dict, mc: dict, process: str) -> list[str]:
    """Problems with klt's echo of the monte_carlo request (the fleet runner
    may run an older klt that silently drops unknown options), [] if none."""
    probs = []
    echo = (payload.get("environment") or {}).get("monte_carlo") or {}
    for k in ("n", "seed"):
        if echo.get(k) != mc[k]:
            probs.append(f"monte_carlo.{k} echo {echo.get(k)!r} != requested {mc[k]!r}")
    if echo.get("vary") != "mismatch":
        probs.append(f"monte_carlo.vary echo {echo.get('vary')!r} != 'mismatch'")
    corners = payload.get("corners") or []
    if len(corners) != mc["n"]:
        probs.append(f"{len(corners)} sample(s) returned, {mc['n']} requested")
    idx = sorted(c.get("monte_carlo", {}).get("sample_index", -1) for c in corners
                 if isinstance(c.get("monte_carlo"), dict))
    if idx != list(range(len(corners))):
        probs.append("sample_index set is not 0..n-1")
    if any(c.get("process") not in (None, process) for c in corners):
        probs.append(f"corner process differs from requested {process!r}")
    return probs


def aggregate(samples: list[dict], n_requested: int) -> dict:
    """Per-corner statistics over ok samples only. Failed samples (and samples
    requested but never returned) are counted, never treated as Vos = 0."""
    vals = [s["vos_v"] for s in samples if s.get("ok") and _num(s.get("vos_v"))]
    n_ok = len(vals)
    reasons: dict[str, int] = {}
    for s in samples:
        if not (s.get("ok") and _num(s.get("vos_v"))):
            r = s.get("reason") or "ok flag without finite vos_v"
            reasons[r] = reasons.get(r, 0) + 1
    n_missing = max(0, n_requested - len(samples))
    if n_missing:
        reasons["requested but not returned"] = n_missing
    agg = {"n_requested": n_requested, "n_returned": len(samples), "n_ok": n_ok,
           "n_failed": n_requested - n_ok, "failure_reasons": reasons,
           "mean_v": None, "sigma_v": None, "three_sigma_v": None,
           "mean_abs_plus_3sigma_v": None, "min_v": None, "max_v": None}
    if n_ok:
        mean = math.fsum(vals) / n_ok
        agg.update(mean_v=mean, min_v=min(vals), max_v=max(vals))
    if n_ok >= 2:
        sd = math.sqrt(math.fsum((v - mean) ** 2 for v in vals) / (n_ok - 1))
        agg.update(sigma_v=sd, three_sigma_v=3 * sd, mean_abs_plus_3sigma_v=abs(mean) + 3 * sd)
    return agg


def is_capacity_error(err: str) -> bool:
    """Fleet-capacity refusals (shared instance cap, or no Spot capacity)."""
    return any(t in (err or "") for t in ("BATCH_MAX_CONCURRENT_INSTANCES", "batch_no_capacity"))


def run_one(req: dict, label: str, backend: str | None, bench: str = "offset",
            mc: dict | None = None, extra: dict | None = None) -> dict:
    """Write one request record, run it through klt sim, write the klt report
    and summary records (never overwriting), return the summary dict."""
    RECORDS.mkdir(exist_ok=True)
    # Atomically reserve a unique record namespace (issue #75) before any write.
    rid = allocate_record_id(RECORDS, f"{bench}-{label}")
    req_path = RECORDS / f"{rid}.request.json"
    write_new(req_path, json.dumps(req, indent=2) + "\n")
    outdir = RECORDS / f"{rid}-artifacts"
    cmd, rc, payload, err = run_klt(req_path, outdir, backend)
    write_new(RECORDS / f"{rid}.klt.json", json.dumps(payload, indent=2) + "\n" if payload else "null\n")
    meta = {"record_id": rid, "bench": bench, **(extra or {}), "command": cmd, "exit_code": rc, "stderr": err[-4000:],
            "env_KLT_SIM_BACKEND": os.environ.get("KLT_SIM_BACKEND"),
            "client_klt_version": klt_version(),
            "git_sha": subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                                      capture_output=True, text=True).stdout.strip()}
    if payload and isinstance(payload.get("corners"), list):
        env = payload.get("environment", {})
        meta["remote"] = env.get("remote")
        meta["monte_carlo_echo"] = env.get("monte_carlo")
        samples = extract_samples(payload, bench)
        if mc:
            probs = check_echo(payload, mc, req["corners"]["process"][0])
            meta["echo_problems"] = probs
            if probs:   # unverifiable sampling: count as failed, never as data
                for s in samples:
                    if s["ok"]:
                        s.update(ok=False, reason="monte_carlo echo mismatch")
                        s.pop("vos_v", None)
        meta["samples"] = samples
    elif payload:
        meta["payload_error"] = payload.get("error") or "klt report has no corners[]"
    write_new(RECORDS / f"{rid}.summary.json", json.dumps(meta, indent=2) + "\n")
    return meta


def chunk_plan(corners: list[str], n_total: int, chunk: int, base_seed: int) -> list[dict]:
    """(corner, chunk index, seed, n, global sample offset) for every request.
    Chunk k uses seed base+k at every corner, so sample g = k*chunk + i draws
    the same mismatch seed at each corner (paired across corners)."""
    plan, k, done = [], 0, 0
    sizes = []
    while done < n_total:
        sizes.append(min(chunk, n_total - done))
        done += sizes[-1]
    for c in corners:
        off = 0
        for k, n in enumerate(sizes):
            plan.append({"corner": c, "chunk": k, "seed": base_seed + k, "n": n, "offset": off})
            off += n
    return plan


def corner_report(chunks: list[dict], n_requested: int) -> dict:
    samples = []
    for ch in chunks:
        for s in ch.get("samples") or []:
            s = dict(s)
            s["global_index"] = ch["offset"] + (s.get("monte_carlo") or {}).get("sample_index", 0)
            samples.append(s)
    return aggregate(samples, n_requested)


def open_campaign_dut(a) -> tuple[Path, dict, dict]:
    """(snapshot dir, dut block, plan params) for a fresh or resumed campaign.
    Fresh: capture the live DUT once and persist the plan. Resume: reload the
    ORIGINAL snapshot and plan; never recapture, and reject contradicting args."""
    snap_dir = RECORDS / f"dut-{a.label}"
    if a.resume:
        plan_path = snap_dir / PLAN_NAME
        if not plan_path.is_file():
            raise ProbeError(f"cannot resume {a.label!r}: no DUT snapshot/plan at {plan_path} "
                             "(legacy campaigns have no recorded DUT and cannot be bound retroactively)")
        saved = json.loads(plan_path.read_text())
        _, problems = dut_identity.verify_record_dut(saved, REPO)
        if problems:
            raise ProbeError(f"cannot resume {a.label!r}: " + "; ".join(problems))
        for k in ("base_seed", "corners", "n_total", "chunk"):
            given = getattr(a, k)
            if k == "corners" and given is not None:
                given = [c.strip() for c in given.split(",") if c.strip()]
            if given is not None and given != saved[k]:
                raise ProbeError(f"resume of {a.label!r}: --{k.replace('_', '-')} {given!r} contradicts "
                                 f"the original plan ({saved[k]!r})")
        return snap_dir, saved["dut"], {k: saved[k] for k in ("base_seed", "corners", "n_total", "chunk")}
    if a.base_seed is None:
        raise SystemExit("--base-seed is required for a new campaign")
    params = {"base_seed": a.base_seed,
              "corners": [c.strip() for c in (a.corners or "tt,ss,ff").split(",") if c.strip()],
              "n_total": a.n_total if a.n_total is not None else 300,
              "chunk": a.chunk if a.chunk is not None else 100}
    bad = [c for c in params["corners"] if c not in CORNERS]
    if bad:
        raise SystemExit(f"unknown corner(s) {bad}; choose from {CORNERS}")
    RECORDS.mkdir(exist_ok=True)
    dut = capture_offset_dut(snap_dir)
    write_new(snap_dir / PLAN_NAME, json.dumps({"campaign": a.label, **params, "dut": dut}, indent=2) + "\n")
    return snap_dir, dut, params


def campaign(a) -> int:
    snap_dir, dut, params = open_campaign_dut(a)
    corners = params["corners"]
    plan = chunk_plan(corners, params["n_total"], params["chunk"], params["base_seed"])
    a.n_total, a.chunk, a.base_seed = params["n_total"], params["chunk"], params["base_seed"]
    netlist = snapshot_netlist(snap_dir)
    if a.only:   # resume: run only the listed corner:chunk requests (same seeds)
        want = {(x.split(":")[0], int(x.split(":")[1])) for x in a.only.split(",") if x}
        plan = [p for p in plan if (p["corner"], p["chunk"]) in want]
    results: dict[str, list[dict]] = {c: [] for c in corners}
    log = []
    for p in plan:
        mc = {"n": p["n"], "seed": p["seed"]}
        req = build_request("offset", True, mc, corner=p["corner"], keep_artifacts=False, netlist=netlist)
        label = f"{a.label}-{p['corner']}-c{p['chunk']}"
        if a.dry_run:
            RECORDS.mkdir(exist_ok=True)
            rid = allocate_record_id(RECORDS, f"offset-{label}")
            write_new(RECORDS / f"{rid}.request.json", json.dumps(req, indent=2) + "\n")
            print(rid)
            continue
        for attempt in range(1, a.max_attempts + 1):
            meta = run_one(req, label if attempt == 1 else f"{label}-r{attempt}", a.backend, mc=mc,
                           extra={"campaign": a.label, "dut": dut, "corner": p["corner"], "chunk": p["chunk"],
                                  "chunk_seed": p["seed"], "chunk_n": p["n"],
                                  "global_offset": p["offset"], "attempt": attempt})
            ok_payload = "samples" in meta
            log.append({"record_id": meta["record_id"], "corner": p["corner"], "chunk": p["chunk"],
                        "attempt": attempt, "exit_code": meta["exit_code"], "got_samples": ok_payload,
                        "job_id": (meta.get("remote") or {}).get("job_id")})
            print(json.dumps(log[-1]), flush=True)
            if ok_payload or attempt == a.max_attempts:
                break
            time.sleep(a.retry_wait_s if is_capacity_error(meta.get("stderr", "")) else 30)
        results[p["corner"]].append({**p, "record_id": meta["record_id"], "samples": meta.get("samples")})
    if a.dry_run:
        return 0
    report = {"campaign": a.label, "dut": dut, "base_seed": a.base_seed, "n_total": a.n_total, "chunk": a.chunk,
              "corners": {c: {"chunks": [{k: ch[k] for k in ("chunk", "seed", "n", "offset", "record_id")}
                                         for ch in results[c]],
                              **corner_report(results[c], a.n_total)} for c in corners},
              "attempts": log}
    rid = allocate_record_id(RECORDS, f"campaign-{a.label}")
    write_new(RECORDS / f"{rid}.campaign.json", json.dumps(report, indent=2) + "\n")
    print(json.dumps({c: {k: v for k, v in r.items() if k != "chunks"}
                      for c, r in report["corners"].items()}, indent=2))
    return 0 if all(r["n_failed"] == 0 for r in report["corners"].values()) else 1


def check_chunk_provenance(paths: list[str]) -> tuple[str, str | None]:
    """DUT provenance of the chunk summaries about to be aggregated.
    Returns (state, sha256): VERIFIED with the single common hash, or
    UNVERIFIED (legacy, no ``dut`` anywhere). Raises ProbeError naming the
    offending records on missing/corrupt snapshots or mixed/partial hashes."""
    metas = []
    for path in paths:
        meta = json.loads(Path(path).read_text())
        if "samples" in meta:
            metas.append((Path(path).name, meta))
    state, sha, problems = dut_identity.common_dut(metas, REPO)
    if problems:
        raise ProbeError("DUT provenance check failed: " + "; ".join(problems))
    return state, sha


def summarize(paths: list[str]) -> dict:
    """Re-aggregate committed chunk summaries (one successful attempt per
    (corner, chunk)) from their klt reports via the same extractor. Rejects
    chunks that do not share one intact DUT snapshot."""
    check_chunk_provenance(paths)
    by_corner: dict[str, dict[int, dict]] = {}
    for path in paths:
        meta = json.loads(Path(path).read_text())
        if "samples" not in meta:
            continue
        rid = meta["record_id"]
        payload = json.loads((Path(path).parent / f"{rid}.klt.json").read_text())
        samples = extract_samples(payload, "offset")
        mc = {"n": meta["chunk_n"], "seed": meta["chunk_seed"]}
        probs = check_echo(payload, mc, f"{meta['corner']}_mm")
        if probs:
            for s in samples:
                s.update(ok=False, reason="monte_carlo echo mismatch")
                s.pop("vos_v", None)
        by_corner.setdefault(meta["corner"], {})[meta["chunk"]] = {
            "chunk": meta["chunk"], "seed": meta["chunk_seed"], "n": meta["chunk_n"],
            "offset": meta["global_offset"], "record_id": rid, "samples": samples}
    out = {}
    for c, chunks in by_corner.items():
        ordered = [chunks[k] for k in sorted(chunks)]
        n_req = sum(ch["n"] for ch in ordered)
        out[c] = {"chunks": [{k: ch[k] for k in ("chunk", "seed", "n", "offset", "record_id")} for ch in ordered],
                  **corner_report(ordered, n_req)}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--bench", choices=["pair", "offset"], required=True)
    r.add_argument("--label", required=True)
    r.add_argument("--mismatch", choices=["on", "off"], default="on")
    r.add_argument("--seed", type=int)
    r.add_argument("--n", type=int, default=1)
    r.add_argument("--backend")
    r.add_argument("--dry-run", action="store_true")
    c = sub.add_parser("campaign")
    c.add_argument("--label", required=True)
    c.add_argument("--base-seed", type=int, help="required for a new campaign")
    c.add_argument("--corners", help="default tt,ss,ff")
    c.add_argument("--n-total", type=int, help="default 300")
    c.add_argument("--chunk", type=int, help="default 100")
    c.add_argument("--resume", action="store_true",
                   help="continue campaign --label from its original DUT snapshot and plan")
    c.add_argument("--max-attempts", type=int, default=6)
    c.add_argument("--retry-wait-s", type=int, default=300)
    c.add_argument("--only", help="resume: comma list of corner:chunk to run, e.g. ss:2,ff:0")
    c.add_argument("--backend")
    c.add_argument("--dry-run", action="store_true")
    s = sub.add_parser("summarize")
    s.add_argument("summaries", nargs="+")
    a = ap.parse_args(argv)
    if a.cmd == "campaign":
        return campaign(a)
    if a.cmd == "summarize":
        state, sha = check_chunk_provenance(a.summaries)
        print(json.dumps(summarize(a.summaries), indent=2))
        print(f"DUT: {state.upper()}" + (f" {sha}" if sha else " (legacy chunks; no recorded DUT identity)"),
              file=sys.stderr)
        return 0
    mc = {"n": a.n, "seed": a.seed} if a.seed is not None else None
    dut = None
    netlist = None
    if a.bench == "offset":   # full-opamp offset run: capture a one-off snapshot too
        RECORDS.mkdir(exist_ok=True)
        snap_dir = RECORDS / f"dut-run-{a.label}"
        dut = capture_offset_dut(snap_dir)
        netlist = snapshot_netlist(snap_dir)
    req = build_request(a.bench, a.mismatch == "on", mc, netlist=netlist)
    if a.dry_run:
        RECORDS.mkdir(exist_ok=True)
        rid = allocate_record_id(RECORDS, f"{a.bench}-{a.label}")
        req_path = write_new(RECORDS / f"{rid}.request.json", json.dumps(req, indent=2) + "\n")
        print(req_path)
        return 0
    meta = run_one(req, a.label, a.backend, bench=a.bench, extra={"dut": dut} if dut else None)
    print(json.dumps({k: meta.get(k) for k in ("record_id", "exit_code", "samples")}, indent=2))
    return 0 if meta.get("samples") and all(s["ok"] for s in meta["samples"]) else 1


if __name__ == "__main__":
    sys.exit(main())
