"""Simulator-free tests for variants/sink_bias_margin.py and its committed netlists (issue #197)."""

import re
import unittest

from _paths import EXP, load_module

VAR = EXP / "variants"
sbm = load_module("sink_bias_margin", VAR / "sink_bias_margin.py")


def cards(text):
    out = {}
    for line in text.replace("\n+", " ").splitlines():
        if line.startswith("XM"):
            tok = line.split()
            kv = dict(t.split("=") for t in tok if "=" in t)
            out[tok[0]] = (tok[1:6], float(kv["W"]), float(kv["L"]), int(kv["m"]), int(kv["nf"]))
    return out


class BiasMargin(unittest.TestCase):
    def test_committed_files_match_generator(self):
        self.assertEqual(sbm.check(), [])

    def test_only_xmc_width_differs_and_canonical_verbatim(self):
        base = cards(sbm.path("ic090").read_text())
        canon = cards(sbm.CANON.read_text())
        for tag in sbm.FRACTIONS:
            c = cards(sbm.path(tag).read_text())
            for name, v in canon.items():
                self.assertEqual(c[name], v, (tag, name))
            for name in c:
                if name != "XMC":
                    self.assertEqual(c[name], base[name], (tag, name))

    def test_original_matches_signal_dependent_sink_widths(self):
        orig = cards((VAR / "signal-dependent-sink.spice").read_text())
        new = cards(sbm.path(sbm.ORIGINAL).read_text())
        for name in ("XMP6C", "XMA", "XMA2", "XMC", "XMD", "XMS"):
            self.assertAlmostEqual(orig[name][1], new[name][1], places=6)

    def test_margins_ordered_and_grid_legal(self):
        w = [sbm.widths(f)["p_ic"] for f in sbm.FRACTIONS.values()]
        self.assertTrue(w[0] > w[1] > w[2])
        for x in w:
            self.assertTrue(sbm.ss.legal(x))
        self.assertEqual(len(sbm.FRACTIONS), 3)   # reference + at most two margins

    def test_probe_source_is_zero_volt_in_xms_source(self):
        text = sbm.path("ic060").read_text()
        self.assertRegex(text, r"(?m)^XMS out nx xs vss ")
        self.assertRegex(text, r"(?m)^Vxms xs vss 0$")

    def test_static_rows_flag_rail_and_boost(self):
        rep = {"corners": [{"process": "tt", "temperature_c": 27.0, "supply_v": {"vdd": 1.8}, "status": "pass",
                            "measurements": [{"name": "i_vdd_a", "value": -7e-5}, {"name": "i_xms_a", "value": 3e-6},
                                             {"name": "vout_v", "value": 1.75}]},
                           {"process": "ss", "temperature_c": -40.0, "supply_v": {"vdd": 1.62}, "status": "error",
                            "measurements": []}]}
        a, b = sbm.static_rows(rep)
        self.assertTrue(a["ok"] and a["railed"] and a["boost_flag"])
        self.assertFalse(b["ok"])


if __name__ == "__main__":
    unittest.main()
