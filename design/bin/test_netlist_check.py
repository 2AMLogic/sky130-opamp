#!/usr/bin/env python3
"""Negative controls for netlist_check.py (issue #55).

Run: python3 design/bin/test_netlist_check.py

Proves the guard fails when it should: a hand-edited netlist, a schematic
change that was not regenerated, and a stale pair record -- and passes on
the untouched tree. The xschem-backed cases are skipped if xschem is absent.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
DESIGN = HERE.parent
SCRIPT = HERE / "netlist_check.py"
sys.path.insert(0, str(HERE))
import netlist_check as nc  # noqa: E402

NETLIST = DESIGN / "netlist" / "opamp_core.spice"
HAVE_XSCHEM = shutil.which("xschem") is not None


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


class CompareUnit(unittest.TestCase):
    def test_identical_ok(self):
        t = NETLIST.read_text()
        self.assertEqual(nc.compare(t, t), [])

    def test_sch_path_and_format_ignored(self):
        t = NETLIST.read_text()
        u = t.replace("** sch_path: ", "** sch_path: /elsewhere", 1).replace("W=6.03 ", "W=6.030 ")
        self.assertEqual(nc.compare(u, t), [])

    def test_hand_edited_width_fails(self):
        t = NETLIST.read_text()
        self.assertTrue(nc.compare(t.replace("W=6.03 ", "W=6.04 "), t))

    def test_hand_edited_derived_param_fails(self):
        t = NETLIST.read_text()
        self.assertTrue(nc.compare(t.replace("ad=1.7487", "ad=1.9"), t))

    def test_rewired_node_fails(self):
        t = NETLIST.read_text()
        self.assertTrue(nc.compare(t.replace("XM1 d1 inn", "XM1 d1 inp"), t))


@unittest.skipUnless(HAVE_XSCHEM, "xschem not installed")
class EndToEnd(unittest.TestCase):
    def test_clean_tree_passes(self):
        r = run("--skip-record")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_schematic_change_without_regeneration_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            sch = Path(tmp) / "opamp_core.sch"
            text = (DESIGN / "opamp_core.sch").read_text()
            self.assertIn("W=6.03", text)
            sch.write_text(text.replace("W=6.03", "W=6.05", 1))
            r = run("--skip-record", "--schematic", str(sch))
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("DRIFT", r.stdout)

    def test_hand_edited_netlist_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            nl = Path(tmp) / "opamp_core.spice"
            nl.write_text(NETLIST.read_text().replace("L=1.2", "L=1.1", 1))
            r = run("--skip-record", "--netlist", str(nl))
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)

    def test_stale_record_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            rec = Path(tmp) / "pair.json"
            data = json.loads((DESIGN / "netlist" / "opamp_core.pair.json").read_text())
            data["netlist"]["content_hash"] = "sha256:" + "0" * 64
            rec.write_text(json.dumps(data))
            r = run("--record", str(rec))
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("stale", r.stdout)


if __name__ == "__main__":
    unittest.main()
