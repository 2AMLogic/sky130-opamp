"""Simulator-free tests for sim/offset-capability/bin/offset_probe.py (issue #52)."""
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


if __name__ == "__main__":
    unittest.main()
