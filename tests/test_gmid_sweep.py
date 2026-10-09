"""Simulator-free tests for sim/gm-id-characterization/bin/sweep.py (issue #102).

Covers the pure helpers `derive_points` and `interp`. `run_sweep_matrix` is not
covered: it renders decks and drives ngspice, so it cannot run without the
simulator and PDK.
"""
import math
import unittest

import _paths
from _paths import REPO

sw = _paths.load_module("gmid_sweep", REPO / "sim" / "gm-id-characterization" / "bin" / "sweep.py")

VDD = 1.8


def make_row(vg=0.9, gm=1e-3, gds=1e-5, id_=1e-4, cgg=1e-14, vth=0.5):
    vals = {"vg": vg, "gm": gm, "gds": gds, "id": id_, "cgg": cgg, "vth": vth}
    row = [0.0] * (max(sw.VALUE_COLS.values()) + 1)
    for name, v in vals.items():
        row[sw.VALUE_COLS[name]] = v
    return row


def derive(device, **kw):
    return list(sw.derive_points(device, [make_row(**kw)], VDD))[0]


class DerivePoints(unittest.TestCase):
    def test_nfet_overdrive_is_vg(self):
        p = derive("nfet", vg=0.9, vth=0.5)
        self.assertAlmostEqual(p["overdrive_bias_v"], 0.9)
        self.assertAlmostEqual(p["vov_v"], 0.4)

    def test_pfet_overdrive_is_vdd_minus_vg(self):
        p = derive("pfet", vg=0.6, vth=0.5)
        self.assertAlmostEqual(p["overdrive_bias_v"], VDD - 0.6)
        self.assertAlmostEqual(p["vov_v"], VDD - 0.6 - 0.5)

    def test_negative_vov_below_threshold(self):
        self.assertLess(derive("nfet", vg=0.3, vth=0.5)["vov_v"], 0)

    def test_derived_ratios(self):
        p = derive("nfet", gm=2e-3, gds=1e-5, id_=1e-4, cgg=1e-14)
        self.assertAlmostEqual(p["gm_id_per_v"], 20.0)
        self.assertAlmostEqual(p["gm_gds"], 200.0)
        self.assertAlmostEqual(p["ft_hz"], 2e-3 / (2 * math.pi * 1e-14))

    def test_passthrough_fields(self):
        p = derive("nfet", gm=2e-3, gds=1e-5, id_=1e-4, cgg=1e-14, vth=0.45)
        self.assertEqual((p["gm_s"], p["gds_s"], p["id_a"], p["cgg_f"], p["vth_v"]),
                         (2e-3, 1e-5, 1e-4, 1e-14, 0.45))

    def test_negative_pfet_current_uses_abs(self):
        p = derive("pfet", gm=2e-3, id_=-1e-4)
        self.assertAlmostEqual(p["gm_id_per_v"], 20.0)
        self.assertEqual(p["id_a"], -1e-4)

    def test_id_threshold(self):
        self.assertIsNone(derive("nfet", id_=1e-13)["gm_id_per_v"])
        self.assertIsNone(derive("pfet", id_=-1e-13)["gm_id_per_v"])
        self.assertIsNone(derive("nfet", id_=0.0)["gm_id_per_v"])
        self.assertIsNotNone(derive("nfet", id_=1.1e-13)["gm_id_per_v"])
        self.assertIsNotNone(derive("pfet", id_=-1.1e-13)["gm_id_per_v"])

    def test_gds_threshold(self):
        self.assertIsNone(derive("nfet", gds=1e-15)["gm_gds"])
        self.assertIsNone(derive("nfet", gds=0.0)["gm_gds"])
        self.assertIsNotNone(derive("nfet", gds=1.1e-15)["gm_gds"])

    def test_cgg_threshold(self):
        self.assertIsNone(derive("nfet", cgg=1e-18)["ft_hz"])
        self.assertIsNone(derive("nfet", cgg=0.0)["ft_hz"])
        self.assertIsNotNone(derive("nfet", cgg=1.1e-18)["ft_hz"])

    def test_thresholds_are_independent(self):
        p = derive("nfet", id_=0.0)
        self.assertIsNone(p["gm_id_per_v"])
        self.assertIsNotNone(p["gm_gds"])
        self.assertIsNotNone(p["ft_hz"])

    def test_one_point_per_row_in_order(self):
        rows = [make_row(vg=v) for v in (0.1, 0.5, 0.9)]
        pts = list(sw.derive_points("nfet", rows, VDD))
        self.assertEqual([p["overdrive_bias_v"] for p in pts], [0.1, 0.5, 0.9])

    def test_empty_rows(self):
        self.assertEqual(list(sw.derive_points("nfet", [], VDD)), [])


class Interp(unittest.TestCase):
    def test_in_range(self):
        self.assertAlmostEqual(sw.interp(0.5, [0.0, 1.0], [10.0, 20.0]), 15.0)

    def test_exact_knot(self):
        self.assertAlmostEqual(sw.interp(1.0, [0.0, 1.0, 2.0], [0.0, 5.0, 7.0]), 5.0)

    def test_multi_segment(self):
        self.assertAlmostEqual(sw.interp(1.5, [0.0, 1.0, 2.0], [0.0, 10.0, 20.0]), 15.0)
        self.assertAlmostEqual(sw.interp(1.5, [0.0, 1.0, 2.0], [0.0, 10.0, 12.0]), 11.0)

    def test_out_of_range_is_none(self):
        self.assertIsNone(sw.interp(-0.1, [0.0, 1.0], [1.0, 2.0]))
        self.assertIsNone(sw.interp(1.1, [0.0, 1.0], [1.0, 2.0]))

    def test_none_entries_skipped(self):
        xs = [0.0, 0.5, 1.0, None]
        ys = [0.0, None, 10.0, 99.0]
        self.assertAlmostEqual(sw.interp(0.5, xs, ys), 5.0)
        # range is set by surviving points only
        self.assertIsNone(sw.interp(0.5, [0.0, 1.0, None], [None, 1.0, 2.0]))

    def test_empty_is_none(self):
        self.assertIsNone(sw.interp(0.5, [], []))
        self.assertIsNone(sw.interp(0.5, [None], [None]))

    def test_equal_x_segment(self):
        self.assertEqual(sw.interp(1.0, [1.0, 1.0], [3.0, 4.0]), 3.0)
        self.assertAlmostEqual(sw.interp(1.5, [0.0, 1.0, 1.0, 2.0], [0.0, 1.0, 1.0, 3.0]), 2.0)

    def test_unsorted_and_decreasing_input(self):
        self.assertAlmostEqual(sw.interp(0.25, [1.0, 0.0], [20.0, 10.0]), 12.5)
        self.assertAlmostEqual(sw.interp(0.5, [1.0, 0.0, 0.5], [30.0, 10.0, 20.0]), 20.0)
        self.assertAlmostEqual(sw.interp(0.75, [1.0, 0.0, 0.5], [30.0, 10.0, 20.0]), 25.0)


if __name__ == "__main__":
    unittest.main()
