"""Simulator-free tests for sim/offset-capability/bin/pelgrom_handcalc.py (issue #107)."""
import math
import tempfile
import unittest
from pathlib import Path

import _paths
from _paths import REPO

hc = _paths.load_module("pelgrom_handcalc", REPO / "sim" / "offset-capability" / "bin" / "pelgrom_handcalc.py")

EOL_SUFFIXES = ("; previous mult=1 m=1", " $ previous mult=1 m=1", " // previous mult=1 m=1")


class Core(unittest.TestCase):
    def test_parse_core_geometry(self):
        c = hc.parse_core()
        self.assertEqual((c["XM1"]["kind"], c["XM1"]["w"], c["XM1"]["l"]), ("nfet", 6.03, 1.2))
        self.assertEqual((c["XM3"]["kind"], c["XM3"]["w"], c["XM3"]["l"]), ("pfet", 4.635, 0.3))
        self.assertEqual(c["XM6"]["mult"], 10.0)

    def test_comment_between_card_and_continuation_keeps_geometry(self):
        # issue #301: `mult=` lives on the `+` line; a comment interleaved with
        # it must not make parse_core silently default the multiplier.
        lines = hc.CORE.read_text().splitlines()
        i = next(i for i, ln in enumerate(lines) if ln.startswith("XM5 ")) + 1
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "opamp_core.spice"
            p.write_text("\n".join(lines[:i] + ["*.ipin tail"] + lines[i:]) + "\n")
            c = hc.parse_core(p)
        self.assertEqual(c["XM5"]["mult"], 2.0)
        self.assertEqual(c, hc.parse_core())

    def _parse_core_with_comment(self, line_start: int, suffix: str) -> dict:
        """parse_core() of the canonical netlist with `suffix` ending the line at `line_start`."""
        text = hc.CORE.read_text()
        eol = text.index("\n", line_start)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "opamp_core.spice"
            p.write_text(text[:eol] + suffix + text[eol:])
            return hc.parse_core(p)

    def test_end_of_line_comment_after_continuation_keeps_geometry(self):
        """issue #417: a trailing '; previous mult=1 m=1' on XM7's continuation
        overrode the active multiplier -- the key/value scan keeps the last
        assignment, commented or not -- and shrank its Pelgrom area tenfold."""
        text = hc.CORE.read_text()
        continuation = text.index("\n+", text.index("\nXM7 ")) + 1
        base = hc.parse_core()
        self.assertEqual(base["XM7"]["mult"], 10.0)
        for suffix in EOL_SUFFIXES:
            with self.subTest(suffix=suffix):
                self.assertEqual(self._parse_core_with_comment(continuation, suffix), base)

    def test_end_of_line_comment_on_card_before_continuation_keeps_geometry(self):
        """The comment is dropped per physical line, before the fold: placed on
        the card ahead of a real continuation, it must not cut that
        continuation off with it."""
        card = hc.CORE.read_text().index("\nXM7 ") + 1
        base = hc.parse_core()
        for suffix in EOL_SUFFIXES:
            with self.subTest(suffix=suffix):
                self.assertEqual(self._parse_core_with_comment(card, suffix), base)


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
