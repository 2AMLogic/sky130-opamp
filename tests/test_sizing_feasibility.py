"""Simulator-free tests for sim/offset-capability/bin/sizing_feasibility.py (issue #144)."""
import math
import sys
import unittest

import _paths
from _paths import REPO

sys.path.insert(0, str(REPO / "sim" / "offset-capability" / "bin"))
sys.path.insert(0, str(REPO / "design" / "bin"))
sf = _paths.load_module("sizing_feasibility", REPO / "sim" / "offset-capability" / "bin" / "sizing_feasibility.py")


class Candidates(unittest.TestCase):
    def test_bounded_set(self):
        self.assertEqual(set(sf.CANDIDATES), {"grid0", "m2p1", "m2p2", "m4p2"})
        self.assertEqual(sum(c["mc"] for c in sf.CANDIDATES.values()), 3)

    def test_committed_candidates_equal_regeneration_and_are_on_grid(self):
        self.assertEqual(sf.gen(check_only=True), 0)

    def test_geometry_scales_w_and_l_together_and_keeps_ratios(self):
        core = sf.hc.parse_core()
        for name, cd in sf.CANDIDATES.items():
            geo = sf.candidate_geometry(core, cd)
            for inst, g in geo.items():
                self.assertTrue(sf.grid_check.on_grid(g["w"]) and sf.grid_check.on_grid(g["l"]), (name, inst))
                self.assertEqual(g["mult"], core[inst]["mult"])
                s = cd["pmos_scale"] if inst in sf.PMOS_GROUP else cd["pair_scale"] if inst in sf.PAIR_GROUP else 1
                self.assertAlmostEqual(g["l"], core[inst]["l"] * s, places=6)
                self.assertLess(abs(g["w"] - core[inst]["w"] * s), sf.GRID_UM)
            # mirror / output-device matching is preserved: XM6 = 10 x XM3, same W and L
            self.assertEqual((geo["XM6"]["w"], geo["XM6"]["l"]), (geo["XM3"]["w"], geo["XM3"]["l"]))
            self.assertEqual(geo["XM6"]["mult"], 10 * geo["XM3"]["mult"])
            self.assertEqual(geo["XM1"], geo["XM2"])
            self.assertEqual(geo["XM3"], geo["XM4"])

    def test_candidate_netlist_only_changes_mos_geometry(self):
        canon = sf.hc_logical_lines(sf.CANON.read_text())
        for name in sf.CANDIDATES:
            body = [ln for ln in sf.candidate_netlist(name).splitlines() if not ln.startswith("** CANDIDATE")
                    and not ln.startswith("** Generated") and not ln.startswith("** pmos_scale")
                    and not ln.startswith("** every W/L") and not ln.startswith(f"** {sf.CANDIDATES[name]['why']}")]
            self.assertEqual(len(body), len(canon))
            for a, b in zip(canon, body):
                ta, tb = a.split(), b.split()
                self.assertEqual(len(ta), len(tb))
                for x, y in zip(ta, tb):
                    if x != y:
                        self.assertIn(x.split("=")[0], ("L", "W", "ad", "as", "pd", "ps", "nrd", "nrs"), (name, x, y))


class Bounds(unittest.TestCase):
    def test_area_optimal_closed_form(self):
        r = sf.area_optimal(3.0, 8.0, 14.0, 3.0, 0.3)
        # constraint met with equality, and no other feasible split on a grid has less area
        self.assertAlmostEqual(9.0 / r["k_pair"] + 64.0 / r["k_mirror"], 0.09, places=9)
        for kp in (r["k_pair"] * f for f in (0.8, 0.9, 1.1, 1.25)):
            km = 64.0 / (0.09 - 9.0 / kp)
            self.assertGreater(kp * 14.0 + km * 3.0, r["area_um2"])
        self.assertFalse(sf.area_optimal(1.0, 1.0, 1.0, 1.0, 0.3, rest=0.4)["feasible"])

    def test_mirror_only_floor_is_the_pair(self):
        # bounds() also evaluates the Pelgrom hand calc, which reads the pinned PDK's model files
        if not (sf.hc.pdk_root() / sf.hc.SPICE / "sky130_fd_pr__nfet_01v8__tt.pm3.spice").exists():
            self.skipTest("pinned PDK not installed")
        b = sf.bounds()
        s = b["inputs"]["group_sigma_v"]
        self.assertGreater(b["mirror_only"]["floor_sigma_v"], s["pair"])
        self.assertGreater(b["mirror_only"]["floor_over_target"], 10)
        self.assertGreater(b["pair_area_factor_min"]["k"], (s["pair"] / sf.TARGET_SIGMA_V) ** 2)
        lo, hi = b["area_optimal"]["low_2se"], b["area_optimal"]["high_2se"]
        self.assertLess(lo["area_um2"], b["area_optimal"]["central"]["area_um2"])
        self.assertLess(b["area_optimal"]["central"]["area_um2"], hi["area_um2"])


class OpDeck(unittest.TestCase):
    def test_deck_has_every_dut_once_and_one_op(self):
        duts = {"canonical": sf.CANON, **{n: sf.cand_path(n) for n in sf.CANDIDATES}}
        deck = sf.op_deck(REPO, duts)
        self.assertEqual(deck.count("\nop\n"), 1)
        for n in duts:
            self.assertEqual(deck.count(f".subckt dut_{n} "), 1)
            self.assertIn(f"$&@m.xc_{n}.xm6.msky130_fd_pr__pfet_01v8[cgg]", deck)
        self.assertNotIn(".dc ", deck)
        self.assertNotIn("alter", deck)

    def test_parse_op(self):
        out = sf.parse_op("noise\nOPV a d1 0.82\nOPD a XM1 gm 8.3e-05\nOPD a XM1 id 4.7e-06\n")
        self.assertEqual(out["a"]["nodes"]["d1"], 0.82)
        self.assertEqual(out["a"]["dev"]["XM1"], {"gm": 8.3e-05, "id": 4.7e-06})
        with self.assertRaises(SystemExit):
            sf.parse_op("OPD a XM1 gm nan-ish\n")

    def test_pelgrom_op_takes_this_netlists_values(self):
        dev = {i: {"id": 1e-6 * k, "gm": 1e-5 * k, "gds": 1e-8 * k} for k, i in
               enumerate(("XM1", "XM2", "XM3", "XM4", "XM6", "XM7"), start=1)}
        po = sf.pelgrom_op(dev)
        self.assertTrue(math.isclose(po["gm1"], 1e-5))
        self.assertTrue(math.isclose(po["gds2"], 2e-8))
        self.assertTrue(math.isclose(po["gm3"], 3e-5))
        self.assertTrue(math.isclose(po["id6"], 5e-6))
        self.assertTrue(math.isclose(po["gm7"], 6e-5))


if __name__ == "__main__":
    unittest.main()
