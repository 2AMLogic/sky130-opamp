"""Simulator-free tests for the validate_psrr_noise.py acceptance evaluator (#98)."""

import copy
import json
import math
import unittest

import _paths
from _paths import EXP, RECORDS

v = _paths.load_module("validate_psrr_noise", EXP / "bin" / "validate_psrr_noise.py")

RECORD = RECORDS / "20261009-072806-e06f2fc-psrr-noise-validation.json"


def good():
    return copy.deepcopy(json.loads(RECORD.read_text())["runs"])


def failed(criteria):
    return {c["name"] for c in criteria if c["verdict"] == "fail"}


class EvaluateTest(unittest.TestCase):
    def test_committed_record_passes(self):
        summary, criteria, ok = v.evaluate(good())
        self.assertTrue(ok, failed(criteria))
        self.assertIn("psrr_ac_vs_dc", {c["name"] for c in criteria})
        self.assertIn("noise_integration", {c["name"] for c in criteria})
        self.assertLess(abs(summary["ac_vs_dc_delta_db"]), v.PSRR_AC_VS_DC_TOL_DB)

    def test_psrr_disagreement_fails_with_good_negative_control(self):
        r = good()
        r["ac_reference"]["values"][0]["tt/1.800V/27C"]["avs_0p1hz_db"] += 0.5
        s, c, ok = v.evaluate(r)
        self.assertFalse(ok)
        self.assertEqual(failed(c), {"psrr_ac_vs_dc"})
        self.assertTrue(s["negative_control_ok"])

    def test_noise_disagreement_fails_with_good_negative_control(self):
        r = good()
        r["noise_full_sweep_same_corner"]["values"][0]["ss/1.620V/125C"]["vn_int_band"] *= 1.01
        s, c, ok = v.evaluate(r)
        self.assertFalse(ok)
        self.assertEqual(failed(c), {"noise_integration"})
        self.assertTrue(s["negative_control_ok"])

    def test_negative_control_failure_fails(self):
        r = good()
        r["negative_control_no_cinp"]["values"][0]["tt/1.800V/27C"]["avs_1khz_db"] = -40.0
        _, c, ok = v.evaluate(r)
        self.assertFalse(ok)
        self.assertEqual(failed(c), {"negative_control"})

    def test_failed_status(self):
        r = good()
        r["noise_bandlimited"]["status"] = "fail"
        _, c, ok = v.evaluate(r)
        self.assertFalse(ok)
        self.assertIn("noise_bandlimited:status", failed(c))

    def test_missing_corner_and_measurement(self):
        r = good()
        r["dc_fd_psrr"]["values"].pop()
        del r["ac_reference"]["values"][0]["tt/1.800V/27C"]["avs_0p1hz_db"]
        _, c, ok = v.evaluate(r)
        self.assertFalse(ok)
        f = failed(c)
        self.assertIn("dc_fd_psrr:corners", f)
        self.assertIn("ac_reference:tt/1.800V/27C:avs_0p1hz_db", f)
        self.assertIn("psrr_ac_vs_dc", f)

    def test_missing_run(self):
        r = good()
        del r["negative_control_no_cinp"]
        _, c, ok = v.evaluate(r)
        self.assertFalse(ok)
        self.assertIn("negative_control_no_cinp:present", failed(c))
        self.assertIn("negative_control", failed(c))

    def test_nonfinite_values(self):
        for bad in (math.nan, math.inf, None):
            r = good()
            r["noise_bandlimited"]["values"][0]["ss/1.620V/125C"]["inoise_total_100hz_1mhz"] = bad
            _, c, ok = v.evaluate(r)
            self.assertFalse(ok)
            self.assertIn("noise_integration", failed(c))

    def test_invalid_log_and_division_inputs(self):
        r = good()
        r["dc_fd_psrr"]["values"][1]["tt/1.810V/27C"]["vout"] = \
            r["dc_fd_psrr"]["values"][0]["tt/1.790V/27C"]["vout"]
        _, c, ok = v.evaluate(r)  # dvout == 0 -> log10(0)
        self.assertFalse(ok)
        self.assertIn("psrr_ac_vs_dc", failed(c))
        r = good()
        r["noise_bandlimited"]["values"][0]["ss/1.620V/125C"]["inoise_total_100hz_1mhz"] = 0.0
        _, c, ok = v.evaluate(r)  # division by zero
        self.assertFalse(ok)
        self.assertIn("noise_integration", failed(c))

    def test_malformed_input_does_not_raise(self):
        _, c, ok = v.evaluate({})
        self.assertFalse(ok)
        _, c, ok = v.evaluate({"dc_fd_psrr": {"status": "pass", "values": [None, 3]}})
        self.assertFalse(ok)

    def test_criteria_record_threshold_and_observed(self):
        _, c, _ = v.evaluate(good())
        by = {x["name"]: x for x in c}
        self.assertEqual(by["psrr_ac_vs_dc"]["threshold"], v.PSRR_AC_VS_DC_TOL_DB)
        self.assertIsNotNone(by["noise_integration"]["observed"])


if __name__ == "__main__":
    unittest.main()
