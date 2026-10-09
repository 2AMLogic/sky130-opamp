import json
import shutil
import tempfile
import unittest
from pathlib import Path

import _paths

ic = _paths.load_module("integrator_check", _paths.REPO / "design" / "bin" / "integrator_check.py")


class IntegratorCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        for rel in (ic.MANIFEST, ic.SIGNOFF, "design/netlist/opamp_core.spice"):
            dst = self.tmp / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(_paths.REPO / rel, dst)

    def mutate(self, fn):
        p = self.tmp / ic.MANIFEST
        m = json.loads(p.read_text())
        fn(m)
        p.write_text(json.dumps(m))

    def test_committed_manifest_is_consistent(self):
        self.assertEqual(ic.check(_paths.REPO), [])

    def test_no_tier_awarded(self):
        m = json.loads((_paths.REPO / ic.MANIFEST).read_text())
        self.assertIsNone(m["maturity"]["tier"])
        self.assertIsNone(m["gds"])
        self.assertIsNone(m["area_um2"])

    def test_parses_xschem_comment_and_plain_subckt(self):
        self.assertEqual(ic.parse_subckt("**.subckt a x y\n"), ("a", ["x", "y"]))
        self.assertEqual(ic.parse_subckt(".subckt b p q\n"), ("b", ["p", "q"]))

    def test_changed_count(self):
        self.mutate(lambda m: m["maturity"].update(t1_met=0))
        errs = ic.check(self.tmp)
        self.assertEqual(errs, ["maturity.t1_met: expected 2 (from source), actual 0"])

    def test_swapped_ports(self):
        def sw(m):
            p = m["ports"]
            p[0], p[1] = p[1], p[0]
        self.mutate(sw)
        errs = ic.check(self.tmp)
        self.assertEqual(len(errs), 1)
        self.assertTrue(errs[0].startswith("ports: expected ['vdd', 'vss'"))
        self.assertIn("actual ['vss', 'vdd'", errs[0])

    def test_missing_artifact_path(self):
        self.mutate(lambda m: m.update(gds="layout/opamp_core.gds"))
        errs = ic.check(self.tmp)
        self.assertEqual(len(errs), 1)
        self.assertIn("gds: expected existing path", errs[0])
        self.assertIn("layout/opamp_core.gds", errs[0])

    def test_gds_pointing_at_stage1_partial(self):
        d = self.tmp / "layout" / "opamp_stage1"
        d.mkdir(parents=True)
        (d / "x.gds").write_bytes(b"")
        self.mutate(lambda m: m.update(gds="layout/opamp_stage1/x.gds"))
        errs = ic.check(self.tmp)
        self.assertEqual(len(errs), 1)
        self.assertIn("gds: expected full-core GDS outside layout/opamp_stage1/", errs[0])

    def test_refresh_fixes_derived_keeps_authored(self):
        def drift(m):
            m["maturity"]["t1_met"] = 9
            m["ports"].reverse()
            m["consumers"] = [{"repo": "x"}]
        self.mutate(drift)
        ic.refresh(self.tmp)
        self.assertEqual(ic.check(self.tmp), [])
        m = json.loads((self.tmp / ic.MANIFEST).read_text())
        self.assertEqual(m["consumers"], [{"repo": "x"}])
        self.assertIsNone(m["gds"])
        self.assertIn("layout/opamp_stage1", m["gds_note"])


if __name__ == "__main__":
    unittest.main()
