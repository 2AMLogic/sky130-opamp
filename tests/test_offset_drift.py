"""Simulator-free tests for sim/offset-capability/bin/offset_drift.py (issue #196)."""
import copy
import json
import math
import random
import tempfile
import unittest
from pathlib import Path

import _paths
import dut_identity
from _paths import REPO

BIN = REPO / "sim" / "offset-capability" / "bin"
op = _paths.load_module("offset_probe", BIN / "offset_probe.py")
od = _paths.load_module("offset_drift", BIN / "offset_drift.py")
PLAN = od.load_plan()
SEED = PLAN["seed_and_sample_mapping"]["monte_carlo"]["seed"]
IDS = [od.sample_id(SEED, i) for i in range(100)]
REF_VOS = {i: random.Random(i).gauss(0.0, 8.6e-3) for i in range(100)}   # volts, ~8.6 mV sigma


# ------------------------------------------------------------ fake backend ---

def rndseed(seed, idx, mutate=False):
    return (seed * 7919 + idx * 104729 + (13 if mutate else 0)) % 2**32


class FakeFleet:
    """Stands in for `klt sim`: builds a klt-shaped report from a request and
    writes the attempt records exactly where the driver reads them."""

    def __init__(self, records, drift_fn=lambda idx, T, V: 0.0, runner="0.7.0"):
        self.records, self.drift_fn, self.runner = Path(records), drift_fn, runner
        self.calls, self.n = [], 0
        self.fail_calls = set()        # 1-based call numbers returning no report
        self.mutators = []             # callables(payload, req) -> payload

    def payload(self, req):
        mc = req["monte_carlo"]
        T = req["corners"]["temperature_c"][0]
        V = req["corners"]["supply_v"]["vdd"][0]
        corners = []
        for i in range(mc["n"]):
            vos = REF_VOS[i] + self.drift_fn(i, T, V)
            corners.append({
                "corner_id": f"tt_mm/{V:.3f}V/{T:g}C/mc{i}", "process": "tt_mm", "supply_v": {"vdd": V},
                "temperature_c": T, "status": "pass",
                "measurements": [{"name": "vos_inp", "value": op.VCM + vos},
                                 {"name": "out_lo", "value": 0.0}, {"name": "out_hi", "value": 1.8}],
                "monte_carlo": {"sample_index": i, "seed": rndseed(mc["seed"], i),
                                "process_seed": 1, "mismatch_seed": rndseed(mc["seed"], i) + 1}})
        return {"status": "pass", "corners": corners,
                "environment": {"monte_carlo": {"n": mc["n"], "seed": mc["seed"], "vary": "mismatch"},
                                "engine": "ngspice", "engine_version": "46", "models_lib_sha256": "m",
                                "netlist_sha256": "n",
                                "remote": {"job_id": f"job{self.n}", "runner_klt_version": self.runner}}}

    def __call__(self, req, label, backend, extra):
        self.n += 1
        self.calls.append((req, extra["drift"]["step"], extra["drift"]["attempt"]))
        rid = f"r{self.n:03d}-{label}"
        payload = None if self.n in self.fail_calls else self.payload(req)
        for m in self.mutators:
            if payload is not None:
                payload = m(payload, req, self.n)
        (self.records / f"{rid}.klt.json").write_text(json.dumps(payload) + "\n")
        meta = {"record_id": rid, "bench": "offset", **extra, "exit_code": 0 if payload else 1,
                "stderr": "" if payload else "BATCH_MAX_CONCURRENT_INSTANCES"}
        (self.records / f"{rid}.summary.json").write_text(json.dumps(meta))


def run_plan(fleet, tmp):
    return od.execute(PLAN, "t", Path(tmp) / "dut-t", {"sha256": PLAN["dut"]["sha256"]}, None,
                      submit=fleet, records=Path(tmp), log=lambda *_: None)


# --------------------------------------------------------------- requests ----

class Requests(unittest.TestCase):
    def test_legacy_defaults_unchanged(self):
        r = op.build_request("offset", True, {"n": 4, "seed": 7})
        self.assertEqual(r["corners"], {"process": ["tt_mm"], "supply_v": {"vdd": [1.8]}, "temperature_c": [27.0]})
        self.assertEqual(op.build_request("offset", True, {"n": 4, "seed": 7}),
                         op.build_request("offset", True, {"n": 4, "seed": 7}, temperature_c=27.0, vdd=op.VDD))

    def test_environment_parameters_only_move_corner(self):
        base = op.build_request("offset", True, {"n": 4, "seed": 7})
        hot = op.build_request("offset", True, {"n": 4, "seed": 7}, temperature_c=125.0, vdd=1.98)
        self.assertEqual(hot["corners"]["temperature_c"], [125.0])
        self.assertEqual(hot["corners"]["supply_v"], {"vdd": [1.98]})
        for k in ("measurements", "analysis", "netlist", "monte_carlo"):
            self.assertEqual(hot[k], base[k])   # same crossing, sweep, bench, seed at every condition

    def test_crossing_and_common_mode_do_not_scale_with_vdd(self):
        r = op.build_request("offset", True, None, vdd=1.62)
        self.assertIn("v(out)=0.9 ", r["measurements"][0]["spice"])

    def test_all_plan_requests_share_dut_bench_and_ids(self):
        reqs = {s["step"]: od.build_step_request(PLAN, s, "dut/offset_dc.spice") for s in PLAN["sequence"]}
        self.assertEqual({r["netlist"] for r in reqs.values()}, {"dut/offset_dc.spice"})
        seeds = {r["monte_carlo"]["seed"] for r in reqs.values()}
        self.assertEqual(seeds, {SEED})
        conds = {(r["corners"]["temperature_c"][0], r["corners"]["supply_v"]["vdd"][0])
                 for n, r in reqs.items() if n.startswith("B")}
        self.assertEqual(conds, {(27.0, 1.8), (-40.0, 1.62), (-40.0, 1.98), (125.0, 1.62), (125.0, 1.98)})
        self.assertEqual(reqs["P0_replay"]["monte_carlo"]["n"], 1)

    def test_plan_budget_is_consistent(self):
        b = PLAN["budget"]
        batches = [s for s in PLAN["sequence"] if s["kind"] == "batch"]
        self.assertEqual(len(batches), b["logical_batches"])
        self.assertEqual(sum(s["n"] for s in batches), b["reference_unique_samples"] + b["environmental_unique_samples"])
        self.assertEqual(b["max_requests"], 3 * b["logical_batches"] + b["max_attempts_probe"])
        self.assertEqual(b["max_attempts_per_logical_batch"], 3)   # initial + two retries
        self.assertEqual(b["max_sample_runs_including_retries"], 3 * 500 + 3)

    def test_plan_dut_is_the_unchanged_canonical_design(self):
        live = dut_identity.sha256_file(REPO / "design" / "netlist" / "opamp_core.spice")
        self.assertEqual(PLAN["dut"]["sha256"], live)


# ------------------------------------------------------------- statistics ----

class Quantiles(unittest.TestCase):
    def test_known_values(self):
        self.assertAlmostEqual(od.t_quantile(0.975, 99), 1.98422, places=4)
        self.assertAlmostEqual(od.t_quantile(0.975, 10), 2.22814, places=4)
        self.assertAlmostEqual(od.chi2_quantile(0.975, 99), 128.422, places=2)
        self.assertAlmostEqual(od.chi2_quantile(0.025, 99), 73.361, places=2)
        self.assertAlmostEqual(od.chi2_quantile(0.5, 2), 2 * math.log(2), places=6)


def ok(v, seed=1):
    return {"ok": True, "vos_v": v, "seed": seed}


class PairedStats(unittest.TestCase):
    def test_known_residuals_sign_units_and_extremes(self):
        ref = {str(i): ok(0.001 * i) for i in range(100)}
        # residual = +0.1 mV constant with a -0.5 mV / +0.4 mV outlier pair
        cond = {i: ok(r["vos_v"] + 1e-4) for i, r in ref.items()}
        cond["3"] = ok(ref["3"]["vos_v"] - 5e-4)
        cond["4"] = ok(ref["4"]["vos_v"] + 4e-4)
        st = od.paired_stats(ref, cond, list(ref))
        vals = [1e-4 * 1e3] * 98 + [-0.5, 0.4]
        mean = sum(vals) / 100
        self.assertEqual(st["n_valid_pairs"], 100)
        self.assertAlmostEqual(st["mean_mv"], mean, places=12)
        self.assertAlmostEqual(st["sigma_mv"], math.sqrt(sum((v - mean) ** 2 for v in vals) / 99), places=12)
        self.assertAlmostEqual(st["max_abs_mv"], 0.5, places=12)
        lo, hi = st["mean_ci_mv"]
        half = od.t_quantile(0.975, 99) * st["sigma_mv"] / 10
        self.assertAlmostEqual(hi - mean, half, places=9)
        self.assertLess(st["sigma_ci_mv"][0], st["sigma_mv"] < st["sigma_ci_mv"][1])

    def test_row_order_is_irrelevant_join_is_by_id(self):
        rng = random.Random(1)
        ref = {str(i): ok(rng.gauss(0, 8e-3)) for i in range(100)}
        cond = {i: ok(r["vos_v"] + rng.gauss(0, 1e-4)) for i, r in ref.items()}
        a = od.paired_stats(ref, cond, list(ref))
        shuffled = dict(reversed(list(cond.items())))
        b = od.paired_stats(dict(reversed(list(ref.items()))), shuffled, list(ref))
        self.assertEqual(a["sigma_mv"], b["sigma_mv"])
        self.assertEqual(a["mean_mv"], b["mean_mv"])
        # independently sorted arrays would give a different (wrong) answer
        sa, sb = sorted(r["vos_v"] for r in ref.values()), sorted(c["vos_v"] for c in cond.values())
        wrong = math.sqrt(sum((x - y) ** 2 for x, y in zip(sa, sb)) / 100) * 1e3
        self.assertNotAlmostEqual(wrong, a["sigma_mv"], places=3)

    def test_verdict_pass_fail_inconclusive(self):
        ids = [str(i) for i in range(100)]
        ref = {i: ok(0.0) for i in ids}

        def with_sigma(s):
            z = random.Random(5)
            vals = [z.gauss(0, 1) for _ in ids]
            m = sum(vals) / 100
            sd = math.sqrt(sum((v - m) ** 2 for v in vals) / 99)
            return {i: ok((v - m) / sd * s * 1e-3) for i, v in zip(ids, vals)}
        self.assertEqual(od.paired_stats(ref, with_sigma(0.10), ids)["verdict"], "PASS_SCREEN")
        self.assertEqual(od.paired_stats(ref, with_sigma(0.30), ids)["verdict"], "FAIL_SCREEN")
        near = od.paired_stats(ref, with_sigma(0.19), ids)
        self.assertEqual(near["verdict"], "INCONCLUSIVE")
        self.assertAlmostEqual(near["sigma_mv"], 0.19, places=9)
        # large mean drift does not change the sigma verdict (mean is reported separately)
        shifted = {i: ok(c["vos_v"] + 1e-3) for i, c in with_sigma(0.10).items()}
        st = od.paired_stats(ref, shifted, ids)
        self.assertEqual(st["verdict"], "PASS_SCREEN")
        self.assertAlmostEqual(st["mean_mv"], 1.0, places=9)

    def test_failures_are_dropped_and_listed_never_zero(self):
        ids = [str(i) for i in range(100)]
        ref = {i: ok(0.0) for i in ids}
        cond = {i: ok(1e-4) for i in ids}
        ref["0"] = {"ok": False, "reason": "unbracketed"}                  # reference failure
        cond["1"] = {"ok": False, "reason": "missing/non-finite"}          # condition failure
        del cond["2"]                                                      # not returned
        cond["3"] = ok(1e-4, seed=2)                                       # seed differs
        st = od.paired_stats(ref, cond, ids)
        self.assertEqual((st["n_requested"], st["n_returned"], st["n_valid_pairs"], st["n_dropped"]),
                         (100, 99, 96, 4))
        self.assertEqual((st["n_failed_reference"], st["n_failed_condition"]), (1, 2))
        self.assertEqual(st["seed_mismatch_ids"], ["3"])
        self.assertAlmostEqual(st["mean_mv"], 0.1, places=12)   # a zero-filled failure would pull this down
        self.assertEqual(set(st["dropped"]), {"0", "1", "2", "3"})

    def test_too_few_pairs_is_inconclusive(self):
        ids = [str(i) for i in range(100)]
        ref = {i: ok(0.0) for i in ids}
        cond = {i: (ok(1e-5 * int(i)) if int(i) < 50 else {"ok": False, "reason": "x"}) for i in ids}
        st = od.paired_stats(ref, cond, ids)
        self.assertEqual(st["verdict"], "INCONCLUSIVE")
        self.assertIn("50 valid pairs", st["verdict_reason"])


# ------------------------------------------------------ response validation --

class ValidateResponse(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.fleet = FakeFleet(self.tmp.name)
        self.step = od.step_table(PLAN)["B1"]
        self.cond = PLAN["conditions"]["C1"]
        self.req = od.build_step_request(PLAN, self.step, "x")

    def check(self, payload):
        return od.validate_response(payload, self.step, self.cond)

    def test_clean_response(self):
        probs, by_id = self.check(self.fleet.payload(self.req))
        self.assertEqual(probs, [])
        self.assertEqual(len(by_id), 100)
        self.assertTrue(all(s["ok"] for s in by_id.values()))

    def test_wrong_condition_echo(self):
        p = self.fleet.payload(self.req)
        p["corners"][5]["temperature_c"] = 27.0
        p["corners"][6]["supply_v"] = {"vdd": 1.8}
        probs, _ = self.check(p)
        self.assertTrue(any("temperature echo" in x for x in probs))
        self.assertTrue(any("vdd echo" in x for x in probs))

    def test_duplicate_and_absent_ids_and_unequal_length(self):
        p = self.fleet.payload(self.req)
        p["corners"][1]["monte_carlo"]["sample_index"] = 0       # duplicate 0, absent 1
        probs, by_id = self.check(p)
        self.assertTrue(any("duplicate sample id" in x for x in probs))
        self.assertTrue(any("sample_index set" in x for x in probs))
        p = self.fleet.payload(self.req)
        p["corners"] = p["corners"][:90]
        probs, _ = self.check(p)
        self.assertTrue(any("90 sample(s) returned, 100 requested" in x for x in probs))

    def test_failed_crossing_and_nonfinite_are_failed_samples(self):
        p = self.fleet.payload(self.req)
        p["corners"][2]["measurements"][2]["value"] = 0.5            # out_hi below 0.9: unbracketed
        p["corners"][3]["measurements"][0]["value"] = float("nan")
        p["corners"][4]["measurements"][0]["value"] = None
        p["corners"][5]["status"] = "error"
        probs, by_id = self.check(p)
        self.assertEqual(probs, [])
        failed = [i for i, s in by_id.items() if not s["ok"]]
        self.assertEqual(sorted(failed), sorted(od.sample_id(SEED, k) for k in (2, 3, 4, 5)))
        self.assertTrue(all("vos_v" not in by_id[i] for i in failed))

    def test_missing_report(self):
        probs, by_id = self.check(None)
        self.assertTrue(probs)
        self.assertEqual(by_id, {})


# ----------------------------------------------------------------- driver ----

class Execute(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_happy_path_pass(self):
        fleet = FakeFleet(self.tmp.name, drift_fn=lambda i, T, V: 5e-5 * math.sin(i) * (T / 100 + (V - 1.8)))
        rep = run_plan(fleet, self.tmp.name)
        self.assertEqual(rep["outcome"], "VERDICTS_ISSUED")
        self.assertEqual([s for _, s, _ in fleet.calls], ["B0_ref", "P0_replay", "B1", "B2", "B3", "B4"])
        self.assertTrue(all(c["stats"]["n_valid_pairs"] == 100 for c in rep["conditions"].values()))
        self.assertTrue(all(v["verdict"] == "PASS_SCREEN" for v in rep["verdicts"].values()))
        self.assertTrue(rep["pairing_evidence"]["items"]["replay_probe"]["ok"])
        self.assertEqual(rep["accounting"]["requests_submitted"], 6)
        # report recomputes identically from the committed records
        again = od.drift_report(PLAN, od.load_ledger("t", Path(self.tmp.name)), Path(self.tmp.name))
        self.assertEqual(json.dumps(rep, sort_keys=True), json.dumps(again, sort_keys=True))

    def test_above_screen_is_failed_but_other_conditions_still_run(self):
        fleet = FakeFleet(self.tmp.name, drift_fn=lambda i, T, V: (1e-3 * math.sin(i) if (T, V) == (125.0, 1.98) else 1e-5 * math.sin(i)))
        rep = run_plan(fleet, self.tmp.name)
        self.assertEqual(rep["outcome"], "VERDICTS_ISSUED")
        self.assertEqual(rep["verdicts"]["B4"]["verdict"], "FAIL_SCREEN")
        self.assertEqual(rep["verdicts"]["B1"]["verdict"], "PASS_SCREEN")
        self.assertEqual(len(fleet.calls), 6)         # no expansion beyond the plan

    def test_retries_keep_ids_stop_at_cap_and_record_failures(self):
        fleet = FakeFleet(self.tmp.name)
        fleet.fail_calls = {3, 4, 5}                 # B1: first three attempts return nothing
        rep = run_plan(fleet, self.tmp.name)
        b1 = [(s, a) for _, s, a in fleet.calls if s == "B1"]
        self.assertEqual(b1, [("B1", 1), ("B1", 2), ("B1", 3)])    # initial + two retries, then stop
        self.assertEqual(rep["step_status"]["B1"], "FAILED_BATCH")
        self.assertEqual(rep["conditions"]["B1"]["verdict"], "NOT_MEASURED")
        self.assertEqual(rep["conditions"]["B2"]["stats"]["n_valid_pairs"], 100)
        reqs = [r for r, s, _ in fleet.calls if s == "B1"]
        self.assertTrue(all(r == reqs[0] for r in reqs))          # same request, same IDs, same seed
        self.assertEqual(len(rep["accounting"]["attempts"]["B1"]), 3)
        self.assertFalse(any(a["accepted"] for a in rep["accounting"]["attempts"]["B1"]))
        self.assertLessEqual(rep["accounting"]["requests_submitted"], PLAN["budget"]["max_requests"])
        # one batch not measured: its absence leaves the rest of the evidence intact
        self.assertEqual(rep["outcome"], "VERDICTS_ISSUED")
        self.assertEqual(rep["verdicts"]["B1"]["verdict"], "NOT_MEASURED")

    def test_retry_then_success_uses_one_accepted_attempt(self):
        fleet = FakeFleet(self.tmp.name)
        fleet.fail_calls = {3}
        rep = run_plan(fleet, self.tmp.name)
        self.assertEqual(rep["conditions"]["B1"]["attempts"], 2)
        self.assertEqual(rep["conditions"]["B1"]["stats"]["n_requested"], 100)   # N not inflated
        self.assertEqual(rep["outcome"], "VERDICTS_ISSUED")

    def test_resume_does_not_resubmit_and_preserves_attempts(self):
        fleet = FakeFleet(self.tmp.name)
        run_plan(fleet, self.tmp.name)
        n = len(fleet.calls)
        fleet2 = FakeFleet(self.tmp.name)
        rep = run_plan(fleet2, self.tmp.name)
        self.assertEqual(fleet2.calls, [])
        self.assertEqual(rep["accounting"]["requests_submitted"], n)

    def test_reference_failure_stops_run(self):
        fleet = FakeFleet(self.tmp.name)
        fleet.fail_calls = {1, 2, 3}
        rep = run_plan(fleet, self.tmp.name)
        self.assertEqual(rep["outcome"], "STOPPED_NO_REFERENCE_OR_PROBE")
        self.assertEqual(len(fleet.calls), 3)
        self.assertIsNone(rep["verdicts"])

    def test_seed_mismatch_is_capability_gap_without_verdict(self):
        fleet = FakeFleet(self.tmp.name)

        def scramble(payload, req, n):
            if req["corners"]["temperature_c"][0] == -40.0 and req["corners"]["supply_v"]["vdd"][0] == 1.62:
                for c in payload["corners"]:
                    c["monte_carlo"]["seed"] += 1            # runner derives different seeds
            return payload
        fleet.mutators.append(scramble)
        rep = run_plan(fleet, self.tmp.name)
        self.assertEqual(rep["outcome"], "CAPABILITY_GAP_NO_VERDICT")
        self.assertIsNone(rep["verdicts"])
        self.assertIn("echoed_seeds_equal", rep["pairing_evidence"]["failed_items"])
        self.assertEqual([s for _, s, _ in fleet.calls], ["B0_ref", "P0_replay", "B1"])   # stopped at once

    def test_replay_probe_mismatch_stops_before_condition_batches(self):
        fleet = FakeFleet(self.tmp.name)

        def perturb(payload, req, n):
            if req["monte_carlo"]["n"] == 1:
                payload["corners"][0]["measurements"][0]["value"] += 1e-3     # 1 mV replay difference
            return payload
        fleet.mutators.append(perturb)
        rep = run_plan(fleet, self.tmp.name)
        self.assertEqual(rep["outcome"], "CAPABILITY_GAP_NO_VERDICT")
        self.assertEqual([s for _, s, _ in fleet.calls], ["B0_ref", "P0_replay"])
        self.assertGreater(abs(rep["pairing_evidence"]["items"]["replay_probe"]["vos_diff_uv"]), 40)

    def test_independent_realizations_trip_statistical_gate(self):
        """Echoed seeds equal, replay fine, but residual sigma ~ sqrt(2) sigma_ref:
        the realizations were NOT held constant."""
        fleet = FakeFleet(self.tmp.name, drift_fn=lambda i, T, V:
                          random.Random((i, T, V).__hash__() if False else i * 31 + int(T) * 7 + int(V * 100)).gauss(0, 8.6e-3)
                          if (T, V) != (27.0, 1.8) else 0.0)
        rep = run_plan(fleet, self.tmp.name)
        self.assertEqual(rep["outcome"], "CAPABILITY_GAP_NO_VERDICT")
        self.assertIn("statistical_sanity_gate", rep["pairing_evidence"]["failed_items"])
        self.assertIsNone(rep["verdicts"])

    def test_runner_version_change_is_capability_gap(self):
        fleet = FakeFleet(self.tmp.name)

        def swap(payload, req, n):
            if n >= 4:
                payload["environment"]["remote"]["runner_klt_version"] = "0.5.0"
            return payload
        fleet.mutators.append(swap)
        rep = run_plan(fleet, self.tmp.name)
        self.assertEqual(rep["outcome"], "CAPABILITY_GAP_NO_VERDICT")
        self.assertIn("provenance_identical", rep["pairing_evidence"]["failed_items"])

    def test_missing_provenance_is_not_a_pass(self):
        fleet = FakeFleet(self.tmp.name)

        def strip(payload, req, n):
            payload["environment"].pop("remote")
            return payload
        fleet.mutators.append(strip)
        rep = run_plan(fleet, self.tmp.name)
        self.assertEqual(rep["outcome"], "CAPABILITY_GAP_NO_VERDICT")

    def test_budget_refuses_over_cap(self):
        plan = copy.deepcopy(PLAN)
        plan["budget"]["max_requests"] = 2
        fleet = FakeFleet(self.tmp.name)
        od.execute(plan, "t", Path(self.tmp.name) / "d", {"sha256": "x"}, None, submit=fleet,
                   records=Path(self.tmp.name), log=lambda *_: None)
        self.assertEqual(len(fleet.calls), 2)


if __name__ == "__main__":
    unittest.main()
