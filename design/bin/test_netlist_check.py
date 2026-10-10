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


def _dev(**kv):
    base = dict(ad=1.7487, **{"as": 1.7487}, pd=12.64, ps=12.64, nrd=0.048, nrs=0.048)
    base.update(kv)
    body = " ".join(f"{k}={v!r}" for k, v in base.items())
    return f"XM1 d1 inn tail vss sky130_fd_pr__nfet_01v8 L=1.2 W=6.03 nf=1 {body} mult=1 m=1\n"


class DerivedTolerance(unittest.TestCase):
    def agree(self, key, a, b):
        fwd = nc.compare(_dev(**{key: a}), _dev(**{key: b}))
        rev = nc.compare(_dev(**{key: b}), _dev(**{key: a}))
        self.assertEqual(bool(fwd), bool(rev), "operand order matters")
        return not fwd

    def test_perimeter_rounding_passes(self):
        for k in ("pd", "ps"):
            self.assertTrue(self.agree(k, 9.848, 9.85))
            self.assertTrue(self.agree(k, 16.218, 16.22))
            self.assertTrue(self.agree(k, 12.64, 12.645))

    def test_perimeter_just_outside_fails(self):
        for k in ("pd", "ps"):
            self.assertFalse(self.agree(k, 12.64, 12.66))
            self.assertFalse(self.agree(k, 12.64, 12.69))
            self.assertFalse(self.agree(k, 12.64, 12.6349))
            self.assertFalse(self.agree(k, 12.64, 12.6451))

    def test_other_keys_tight_relative(self):
        for k in ("ad", "as", "nrd", "nrs"):
            v = 1.7487 if k in ("ad", "as") else 0.048
            self.assertTrue(self.agree(k, v, v * (1 + 1e-9)))
            self.assertTrue(self.agree(k, v, v * (1 - 1e-9)))
            for f in (1 + 1e-4, 1 - 1e-4, 1.002, 0.998, 1.0005):
                self.assertFalse(self.agree(k, v, v * f), (k, f))

    def test_relative_bound_edges(self):
        # Just inside / just outside the 1e-6 relative bound, both signs.
        for k in ("ad", "as", "nrd", "nrs"):
            v = 1.7487 if k in ("ad", "as") else 0.048
            for f in (1 + 5e-7, 1 - 5e-7, 1 + 9e-7, 1 - 9e-7):
                self.assertTrue(self.agree(k, v, v * f), (k, f))
            for f in (1 + 1.1e-6, 1 - 1.1e-6, 1 + 2e-6, 1 - 2e-6):
                self.assertFalse(self.agree(k, v, v * f), (k, f))

    def test_perimeter_allowance_not_applied_to_others(self):
        for k in ("ad", "as", "nrd", "nrs"):
            self.assertFalse(self.agree(k, 0.048, 0.052))

    def test_near_zero(self):
        for k in ("ad", "as", "nrd", "nrs"):
            self.assertTrue(self.agree(k, 0.0, 0.0))
            self.assertTrue(self.agree(k, 0.0, 1e-15))
            self.assertFalse(self.agree(k, 0.0, 1e-6))
            self.assertFalse(self.agree(k, 1e-9, 2e-9))
        self.assertTrue(self.agree("pd", 0.0, 0.004))
        self.assertFalse(self.agree("pd", 0.0, 0.006))

    def test_committed_pd_edit_fails_via_netlist(self):
        t = NETLIST.read_text()
        self.assertTrue(nc.compare(t.replace("pd=12.64", "pd=12.66"), t))
        self.assertTrue(nc.compare(t, t.replace("ad=1.7487", "ad=1.752")))


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
