import json
import shutil
import tempfile
import unittest
from pathlib import Path

import _paths

sf = _paths.load_module("spec_figures_check", _paths.REPO / "design" / "bin" / "spec_figures_check.py")

RID = "20261001-000000-abcdef1"
SPEC = f"""# spec
## 1. Global
cites 20200101-000000-0000000 outside section 2
## 2. Performance targets
Gain worst-case **61.64 dB @ FS / 125 °C** record `{RID}`.
## 3. Other
"""
CSV = "corner,temp_c,gain_dc_db\ntt,27.0,66.0\nfs,125.0,61.6392\nss,-40.0,68.0\n"
MAPPING = {"figures": [{
    "row": "gain", "record": RID, "csv": "ac", "key": "gain_dc_db", "reduce": "min",
    "expected": 61.64, "tol": 0.005, "unit": "dB",
    "at": {"corner": "fs", "temp_c": 125}, "printed": ["61.64 dB"],
}]}


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        rec = self.tmp / sf.OPAMP_RECORDS
        rec.mkdir(parents=True)
        (rec / f"{RID}-ac.csv").write_text(CSV)
        (rec / f"{RID}.json").write_text("{}")
        (self.tmp / "spec").mkdir()
        (self.tmp / "manifests").mkdir()
        self.write_spec(SPEC)
        self.write_map(MAPPING)

    def write_spec(self, s):
        (self.tmp / sf.SPEC).write_text(s, encoding="utf-8")

    def write_map(self, m):
        (self.tmp / sf.MAPPING).write_text(json.dumps(m), encoding="utf-8")

    def fig(self, **kw):
        m = json.loads(json.dumps(MAPPING))
        m["figures"][0].update(kw)
        self.write_map(m)

    def test_fixture_passes(self):
        self.assertEqual(sf.check(self.tmp), [])

    def test_altered_mapped_figure_fails(self):
        self.fig(expected=61.74)
        errs = sf.check(self.tmp)
        self.assertTrue(any("recomputed" in e for e in errs), errs)

    def test_altered_spec_text_fails(self):
        self.write_spec(SPEC.replace("61.64 dB", "61.46 dB"))
        errs = sf.check(self.tmp)
        self.assertTrue(any("not found in section 2" in e for e in errs), errs)

    def test_altered_record_data_fails(self):
        p = self.tmp / sf.OPAMP_RECORDS / f"{RID}-ac.csv"
        p.write_text(CSV.replace("61.6392", "60.1000"))
        self.assertTrue(any("recomputed" in e for e in sf.check(self.tmp)))

    def test_wrong_binding_corner_fails(self):
        self.fig(at={"corner": "ss", "temp_c": 125})
        self.assertTrue(any("binding corner" in e for e in sf.check(self.tmp)))

    def test_cited_record_id_missing_fails(self):
        self.write_spec(SPEC.replace(RID, "20261001-000000-abcdef2"))
        errs = sf.check(self.tmp)
        self.assertTrue(any("does not exist" in e for e in errs), errs)

    def test_id_outside_section2_ignored(self):
        self.assertEqual(sf.check(self.tmp), [])

    def test_unknown_key_fails(self):
        self.fig(key="nope")
        self.assertTrue(any("cannot recompute" in e for e in sf.check(self.tmp)))


class CommittedTests(unittest.TestCase):
    def test_committed_spec_agrees_with_records(self):
        self.assertEqual(sf.check(_paths.REPO), [])


if __name__ == "__main__":
    unittest.main()
