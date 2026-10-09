"""Simulator-free tests for sim/offset-capability/bin/offset_probe.py (issues #52, #85)."""
import math
import statistics
import unittest

import _paths
from _paths import REPO

op = _paths.load_module("offset_probe", REPO / "sim" / "offset-capability" / "bin" / "offset_probe.py")


def corner(meas, status="pass", cid="tt_mm/1.800V/27C/mc0"):
    return {"corner_id": cid, "status": status, "monte_carlo": {"sample_index": 0},
            "measurements": [{"name": k, "value": v} for k, v in meas.items()]}


class BuildRequest(unittest.TestCase):
    def test_mismatch_selects_mm_section_and_mc_block(self):
        r = op.build_request("offset", True, {"n": 4, "seed": 7})
        self.assertEqual(r["corners"]["process"], ["tt_mm"])
        self.assertEqual(r["monte_carlo"], {"n": 4, "seed": 7, "vary": "mismatch"})

    def test_control_selects_plain_section(self):
        r = op.build_request("pair", False, {"n": 4, "seed": 7})
        self.assertEqual(r["corners"]["process"], ["tt"])

    def test_no_mc_block_without_seed(self):
        self.assertNotIn("monte_carlo", op.build_request("offset", True, None))

    def test_offset_measurements_declared(self):
        names = [m["name"] for m in op.build_request("offset", True, None)["measurements"]]
        self.assertEqual(names, ["vos_inp", "out_lo", "out_hi"])


class ExtractOffset(unittest.TestCase):
    def test_known_offset_crossing(self):
        p = {"corners": [corner({"vos_inp": op.VCM + 0.0042, "out_lo": 0.0, "out_hi": 1.8})]}
        s = op.extract_samples(p, "offset")[0]
        self.assertTrue(s["ok"])
        self.assertAlmostEqual(s["vos_v"], 0.0042, places=12)

    def test_missing_output_is_failure_not_zero(self):
        p = {"corners": [corner({"vos_inp": None, "out_lo": 0.0, "out_hi": 1.8})]}
        s = op.extract_samples(p, "offset")[0]
        self.assertFalse(s["ok"])
        self.assertNotIn("vos_v", s)

    def test_absent_measurement_is_failure(self):
        s = op.extract_samples({"corners": [corner({"out_lo": 0.0, "out_hi": 1.8})]}, "offset")[0]
        self.assertFalse(s["ok"])

    def test_no_crossing_rail_saturation(self):
        p = {"corners": [corner({"vos_inp": op.VCM, "out_lo": 1.7, "out_hi": 1.8})]}
        s = op.extract_samples(p, "offset")[0]
        self.assertFalse(s["ok"])
        self.assertIn("bracket", s["reason"])

    def test_nonconvergence_status(self):
        p = {"corners": [corner({"vos_inp": op.VCM, "out_lo": 0.0, "out_hi": 1.8}, status="error")]}
        self.assertFalse(op.extract_samples(p, "offset")[0]["ok"])

    def test_nan_rejected(self):
        p = {"corners": [corner({"vos_inp": float("nan"), "out_lo": 0.0, "out_hi": 1.8})]}
        self.assertFalse(op.extract_samples(p, "offset")[0]["ok"])

    def test_rejected_payload(self):
        with self.assertRaises(op.ProbeError):
            op.extract_samples({"error": {"message": "x"}}, "offset")
        with self.assertRaises(op.ProbeError):
            op.extract_samples(None, "offset")


class ExtractPair(unittest.TestCase):
    def test_pair_differences(self):
        p = {"corners": [corner({"idn1": 3e-5, "idn2": 2e-5, "idp1": 1e-5, "idp2": 1.5e-5})]}
        s = op.extract_samples(p, "pair")[0]
        self.assertAlmostEqual(s["dn"], 1e-5)
        self.assertAlmostEqual(s["dp"], -5e-6)

    def test_pair_missing(self):
        p = {"corners": [corner({"idn1": 3e-5, "idn2": 2e-5, "idp1": 1e-5})]}
        self.assertFalse(op.extract_samples(p, "pair")[0]["ok"])


def ok(v):
    return {"ok": True, "reason": None, "vos_v": v}


def bad(reason):
    return {"ok": False, "reason": reason}


class Aggregate(unittest.TestCase):
    def test_mean_sigma_over_ok_samples(self):
        vals = [1e-3, -2e-3, 4e-3, 0.5e-3, -1.5e-3]
        a = op.aggregate([ok(v) for v in vals], 5)
        self.assertEqual((a["n_ok"], a["n_failed"], a["n_returned"]), (5, 0, 5))
        self.assertAlmostEqual(a["mean_v"], statistics.mean(vals), places=15)
        self.assertAlmostEqual(a["sigma_v"], statistics.stdev(vals), places=15)   # n-1 sample sd
        self.assertAlmostEqual(a["three_sigma_v"], 3 * statistics.stdev(vals), places=15)
        self.assertAlmostEqual(a["mean_abs_plus_3sigma_v"],
                               abs(statistics.mean(vals)) + 3 * statistics.stdev(vals), places=15)
        self.assertEqual((a["min_v"], a["max_v"]), (-2e-3, 4e-3))
        self.assertEqual(a["failure_reasons"], {})

    def test_failures_excluded_and_counted_never_zero(self):
        vals = [5e-3, 7e-3, 9e-3]
        samples = [ok(v) for v in vals] + [bad("output does not bracket VREF"),
                                           bad("output does not bracket VREF"),
                                           bad("corner status 'error'")]
        a = op.aggregate(samples, 6)
        self.assertEqual((a["n_ok"], a["n_failed"]), (3, 3))
        # If a failure were counted as Vos = 0 the mean would be 3.5 mV, not 7 mV.
        self.assertAlmostEqual(a["mean_v"], 7e-3, places=15)
        self.assertAlmostEqual(a["sigma_v"], 2e-3, places=15)
        self.assertEqual(a["failure_reasons"], {"output does not bracket VREF": 2,
                                                "corner status 'error'": 1})

    def test_missing_samples_count_as_failed(self):
        a = op.aggregate([ok(1e-3), ok(2e-3)], 100)
        self.assertEqual((a["n_returned"], a["n_ok"], a["n_failed"]), (2, 2, 98))
        self.assertEqual(a["failure_reasons"]["requested but not returned"], 98)

    def test_ok_flag_without_value_is_failure(self):
        a = op.aggregate([ok(1e-3), ok(3e-3), {"ok": True, "vos_v": None}, ok(float("nan"))], 4)
        self.assertEqual((a["n_ok"], a["n_failed"]), (2, 2))
        self.assertAlmostEqual(a["mean_v"], 2e-3)

    def test_all_failed_gives_no_statistics(self):
        a = op.aggregate([bad("x"), bad("x")], 2)
        self.assertEqual(a["n_ok"], 0)
        self.assertIsNone(a["mean_v"])
        self.assertIsNone(a["sigma_v"])

    def test_single_ok_sample_has_no_sigma(self):
        a = op.aggregate([ok(1e-3)], 1)
        self.assertEqual(a["mean_v"], 1e-3)
        self.assertIsNone(a["sigma_v"])

    def test_end_to_end_from_payload(self):
        """Extractor -> aggregate: a rail-saturated and a missing-meas sample
        are excluded, not averaged in as zero."""
        p = {"corners": [
            corner({"vos_inp": op.VCM + 0.004, "out_lo": 0.0, "out_hi": 1.8}),
            corner({"vos_inp": op.VCM + 0.006, "out_lo": 0.0, "out_hi": 1.8}),
            corner({"vos_inp": op.VCM, "out_lo": 1.79, "out_hi": 1.8}),          # saturated
            corner({"vos_inp": None, "out_lo": 0.0, "out_hi": 1.8}),             # no crossing
            corner({"out_lo": 0.0, "out_hi": 1.8}),                              # missing meas
        ]}
        a = op.aggregate(op.extract_samples(p, "offset"), 5)
        self.assertEqual((a["n_ok"], a["n_failed"]), (2, 3))
        self.assertAlmostEqual(a["mean_v"], 0.005, places=12)
        self.assertAlmostEqual(a["sigma_v"], math.sqrt(2e-6), places=12)


def mc_payload(n, seed, process="tt_mm", vary="mismatch", n_returned=None):
    k = n if n_returned is None else n_returned
    return {"environment": {"monte_carlo": {"n": n, "seed": seed, "vary": vary}},
            "corners": [{"corner_id": f"{process}/1.800V/27C/mc{i}", "process": process,
                         "status": "pass", "monte_carlo": {"sample_index": i},
                         "measurements": []} for i in range(k)]}


class Campaign(unittest.TestCase):
    def test_request_per_corner_uses_mm_section_no_artifacts(self):
        r = op.build_request("offset", True, {"n": 100, "seed": 5}, corner="ss", keep_artifacts=False)
        self.assertEqual(r["corners"]["process"], ["ss_mm"])
        self.assertFalse(r["options"]["keep_artifacts"])
        self.assertEqual(r["monte_carlo"], {"n": 100, "seed": 5, "vary": "mismatch"})

    def test_chunk_plan_seeds_and_offsets(self):
        plan = op.chunk_plan(["tt", "ss"], 250, 100, 1000)
        tt = [p for p in plan if p["corner"] == "tt"]
        self.assertEqual([(p["seed"], p["n"], p["offset"]) for p in tt],
                         [(1000, 100, 0), (1001, 100, 100), (1002, 50, 200)])
        self.assertEqual([p["seed"] for p in plan if p["corner"] == "ss"], [1000, 1001, 1002])
        self.assertEqual(sum(p["n"] for p in plan), 500)

    def test_echo_ok(self):
        self.assertEqual(op.check_echo(mc_payload(3, 9), {"n": 3, "seed": 9}, "tt_mm"), [])

    def test_echo_detects_dropped_or_wrong_mc(self):
        mc = {"n": 3, "seed": 9}
        self.assertTrue(op.check_echo(mc_payload(3, 8), mc, "tt_mm"))
        self.assertTrue(op.check_echo(mc_payload(3, 9, vary="all"), mc, "tt_mm"))
        self.assertTrue(op.check_echo(mc_payload(3, 9, n_returned=2), mc, "tt_mm"))
        self.assertTrue(op.check_echo(mc_payload(3, 9, process="tt"), mc, "tt_mm"))
        self.assertTrue(op.check_echo({"corners": []}, mc, "tt_mm"))

    def test_capacity_errors_recognised(self):
        self.assertTrue(op.is_capacity_error("8 instance(s) already running ... BATCH_MAX_CONCURRENT_INSTANCES=8"))
        self.assertTrue(op.is_capacity_error('{"error": {"code": "batch_no_capacity"}}'))
        self.assertFalse(op.is_capacity_error("ngspice: singular matrix"))
        self.assertFalse(op.is_capacity_error(None))

    def test_corner_report_global_index_and_stats(self):
        chunks = [{"offset": 0, "samples": [dict(ok(1e-3), monte_carlo={"sample_index": 0}),
                                            dict(ok(3e-3), monte_carlo={"sample_index": 1})]},
                  {"offset": 2, "samples": None},   # chunk never returned
                  ]
        a = op.corner_report(chunks, 4)
        self.assertEqual((a["n_ok"], a["n_failed"]), (2, 2))
        self.assertAlmostEqual(a["mean_v"], 2e-3)


class CampaignRecords(unittest.TestCase):
    """Committed #85 campaign record is consistent with its chunk summaries."""
    REC = REPO / "sim" / "offset-capability" / "records"

    def setUp(self):
        finals = sorted(self.REC.glob("*campaign-offset-mc300-final-*.campaign.json"))
        if not finals:
            self.skipTest("campaign record not present")
        import json
        self.json = json
        self.final = json.loads(finals[-1].read_text())

    def test_each_corner_has_n300_seeds_and_stats(self):
        for c in ("tt", "ss", "ff"):
            r = self.final["corners"][c]
            self.assertEqual(r["n_requested"], 300)
            self.assertEqual(r["n_ok"] + r["n_failed"], 300)
            self.assertEqual([ch["seed"] for ch in r["chunks"]],
                             [self.final["base_seed"] + k for k in range(3)])
            self.assertEqual([ch["offset"] for ch in r["chunks"]], [0, 100, 200])
            self.assertIsNotNone(r["mean_v"])
            self.assertIsNotNone(r["sigma_v"])

    def test_reaggregation_from_chunk_summaries_matches(self):
        for c, r in self.final["corners"].items():
            paths = [str(self.REC / f"{ch['record_id']}.summary.json") for ch in r["chunks"]]
            again = op.summarize(paths)[c]
            for k in ("n_ok", "n_failed", "mean_v", "sigma_v"):
                self.assertEqual(again[k], r[k], (c, k))

    def test_unused_requests_are_all_listed_and_none_used(self):
        used = {ch["record_id"] for r in self.final["corners"].values() for ch in r["chunks"]}
        listed = {u["record_id"] for u in self.final["requests_not_used_in_statistics"]}
        self.assertFalse(used & listed)
        every = {p.name[:-len(".request.json")] for p in self.REC.glob("*mc300*.request.json")}
        self.assertEqual(every, used | listed)


if __name__ == "__main__":
    unittest.main()
