"""Simulator-free tests for variants/sink_sizing.py and signal-dependent-sink.spice (issue #79)."""

import re
import unittest

from _paths import EXP, load_module

VAR = EXP / "variants"
ss = load_module("sink_sizing", VAR / "sink_sizing.py")
from _gmid import mos_cards


def series(pairs):
    """(vgs, id_a, gm_id_per_v) triples in the shape load() returns."""
    return [(v, i, {"gm_id_per_v": g}) for v, i, g in pairs]


# J = id_a / SWEEP_W_UM * 1e6 -> 0.05, 0.5, 5.0 uA/um; one blank gm/ID row must be skipped.
SYN = series([(0.4, 1e-7, "25"), (0.45, 5e-8, ""), (0.5, 1e-6, "18"), (0.6, 1e-5, "10")])


class GmidHelpers(unittest.TestCase):
    """Synthetic checks of the shared _gmid helpers sink_sizing re-exports (issue #377)."""

    def test_interp_gmid_linear_in_j(self):
        # Target 14 is the midpoint of the (10 -> 18) bracket, so J is the midpoint
        # of (5.0 -> 0.5) uA/um; the brackets are returned sorted by gm/ID.
        j, lo, hi = ss.interp_gmid(SYN, 14.0)
        self.assertAlmostEqual(j, 2.75, places=12)
        self.assertEqual(lo, (10.0, 5.0))
        self.assertEqual(hi, (18.0, 0.5))

    def test_interp_gmid_at_bracketing_row(self):
        j, lo, hi = ss.interp_gmid(SYN, 18.0)
        self.assertAlmostEqual(j, 0.5, places=12)
        self.assertEqual((lo[0], hi[0]), (10.0, 18.0))

    def test_interp_gmid_outside_sweep(self):
        for target in (5.0, 30.0):
            with self.assertRaises(ValueError):
                ss.interp_gmid(SYN, target)

    def test_legal_grid(self):
        for w in (7.820, 4.635, 2.7800000000000002, 0.605):
            self.assertTrue(ss.legal(w), w)
        for w in (7.819, 4.6341, 1.0001):
            self.assertFalse(ss.legal(w), w)
        for w in (7.819, 15.4937, 10.3702, 0.001, 123.9512):
            self.assertTrue(ss.legal(ss.snap(w)), w)


class SinkSizing(unittest.TestCase):
    def test_widths_match_netlist(self):
        d = mos_cards((VAR / "signal-dependent-sink.spice").read_text())
        jn, *_ = ss.interp_gmid(ss.load("nfet", 1.2)[("tt", 27.0)], 18.0)
        jp, *_ = ss.interp_gmid(ss.load("pfet", 0.3)[("tt", 27.0)], 14.0)
        for name in ("XMA", "XMA2", "XMD", "XMS"):
            self.assertAlmostEqual(d[name].width, ss.snap(5.0 / jn), places=6)
        self.assertAlmostEqual(d["XMP6C"].width, ss.snap(5.0 / jp), places=6)
        self.assertAlmostEqual(d["XMC"].width, ss.snap(0.9 * 5.0 / jp), places=6)

    def test_new_devices_grid_legal_nf1(self):
        base = mos_cards((VAR / "signal-dependent-sink.spice").read_text())
        for name in ("XMP6C", "XMA", "XMA2", "XMC", "XMD", "XMS"):
            self.assertTrue(ss.legal(base[name].width), name)
            self.assertEqual(base[name].nf, 1, name)

    def test_existing_devices_unchanged_vs_tail_clamp_base(self):
        sink = mos_cards((VAR / "signal-dependent-sink.spice").read_text())
        clamp = mos_cards((VAR / "tail-clamp.spice").read_text())
        for name, v in clamp.items():
            if name != "XMCL":
                self.assertEqual(sink[name], v, name)

    def test_ports_in_netlist(self):
        text = (VAR / "signal-dependent-sink.spice").read_text()
        self.assertIsNone(re.search(r"^\.subckt", text, re.M))


if __name__ == "__main__":
    unittest.main()
