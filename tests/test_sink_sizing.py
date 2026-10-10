"""Simulator-free tests for variants/sink_sizing.py and signal-dependent-sink.spice (issue #79)."""

import re
import unittest

from _paths import EXP, load_module

VAR = EXP / "variants"
ss = load_module("sink_sizing", VAR / "sink_sizing.py")


def devices(path):
    text = (VAR / path).read_text().replace("\n+", " ")
    out = {}
    for line in text.splitlines():
        if line.startswith("XM"):
            tok = line.split()
            kv = dict(t.split("=") for t in tok if "=" in t)
            out[tok[0]] = (tok[5], float(kv["W"]), float(kv["L"]), int(kv["m"]), int(kv["nf"]))
    return out


class SinkSizing(unittest.TestCase):
    def test_widths_match_netlist(self):
        d = devices("signal-dependent-sink.spice")
        jn, *_ = ss.interp_gmid(ss.load("nfet", 1.2)[("tt", 27.0)], 18.0)
        jp, *_ = ss.interp_gmid(ss.load("pfet", 0.3)[("tt", 27.0)], 14.0)
        for name in ("XMA", "XMA2", "XMD", "XMS"):
            self.assertAlmostEqual(d[name][1], ss.snap(5.0 / jn), places=6)
        self.assertAlmostEqual(d["XMP6C"][1], ss.snap(5.0 / jp), places=6)
        self.assertAlmostEqual(d["XMC"][1], ss.snap(0.9 * 5.0 / jp), places=6)

    def test_new_devices_grid_legal_nf1(self):
        base = devices("signal-dependent-sink.spice")
        for name in ("XMP6C", "XMA", "XMA2", "XMC", "XMD", "XMS"):
            self.assertTrue(ss.legal(base[name][1]), name)
            self.assertEqual(base[name][4], 1, name)

    def test_existing_devices_unchanged_vs_tail_clamp_base(self):
        sink = devices("signal-dependent-sink.spice")
        clamp = devices("tail-clamp.spice")
        for name, v in clamp.items():
            if name != "XMCL":
                self.assertEqual(sink[name], v, name)

    def test_ports_in_netlist(self):
        text = (VAR / "signal-dependent-sink.spice").read_text()
        self.assertIsNone(re.search(r"^\.subckt", text, re.M))


if __name__ == "__main__":
    unittest.main()
