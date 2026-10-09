"""Simulator-free tests for sim/offset-capability/bin/pelgrom_handcalc.py (issue #107)."""
import math
import unittest

import _paths
from _paths import REPO

hc = _paths.load_module("pelgrom_handcalc", REPO / "sim" / "offset-capability" / "bin" / "pelgrom_handcalc.py")


class Core(unittest.TestCase):
    def test_parse_core_geometry(self):
        c = hc.parse_core()
        self.assertEqual((c["XM1"]["kind"], c["XM1"]["w"], c["XM1"]["l"]), ("nfet", 6.03, 1.2))
        self.assertEqual((c["XM3"]["kind"], c["XM3"]["w"], c["XM3"]["l"]), ("pfet", 4.634, 0.3))
        self.assertEqual(c["XM6"]["mult"], 10.0)


class Calc(unittest.TestCase):
    def setUp(self):
        root = hc.pdk_root()
        if not (root / hc.SPICE / "sky130_fd_pr__nfet_01v8__tt.pm3.spice").exists():
            self.skipTest("pinned PDK not installed")
        self.out = hc.calc(root)

    def test_pair_is_sqrt2_pelgrom(self):
        d = self.out["devices"]["XM1"]
        self.assertAlmostEqual(d["sigma_vt_v"], 3.356e-3 / math.sqrt(6.03 * 1.2), places=9)
        vt_only = math.sqrt(2) * d["sigma_vt_v"]
        self.assertGreaterEqual(self.out["group_sigma_v"]["pair"], vt_only)
        self.assertLess(self.out["group_sigma_v"]["pair"], 1.05 * vt_only)

    def test_mirror_uses_pfet_bin_slope1(self):
        d = self.out["devices"]["XM3"]
        self.assertEqual(d["vth0_name"], "sky130_fd_pr__pfet_01v8__vth0_slope1")
        self.assertAlmostEqual(d["s_vt"], 7.356e-3)

    def test_mirror_dominates_and_passives_zero(self):
        g = self.out["group_sigma_v"]
        self.assertGreater(g["mirror"], g["pair"])
        self.assertEqual(g["passives"], 0.0)
        self.assertAlmostEqual(self.out["total_sigma_v"], math.sqrt(sum(v * v for v in g.values())))

    def test_agreement_logic(self):
        r = hc.agreement(self.out, self.out["total_sigma_v"] * 1.2, {"pair": 1.7e-3, "stage2": 0.9e-3})
        self.assertTrue(r["total"]["agrees"])
        self.assertFalse(r["stage2"]["agrees"])   # small group: absolute 0.5 mV cap
        r = hc.agreement(self.out, self.out["total_sigma_v"] * 1.4, {})
        self.assertFalse(r["total"]["agrees"])


if __name__ == "__main__":
    unittest.main()
