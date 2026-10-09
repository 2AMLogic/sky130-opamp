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
| Parameter | Target |
|---|---|
| Open-loop DC gain | worst-case **61.64 dB @ FS / 125 °C** record `{RID}` |
| Other row | 61.64 dB @ FS / 125 °C quoted elsewhere |

Summary: gain fell to 61.64 dB @ FS / 125 °C.
## 3. Other
"""
CSV = "corner,temp_c,gain_dc_db\ntt,27.0,66.0\nfs,125.0,61.6392\nss,-40.0,68.0\n"
MAPPING = {"figures": [{
    "row": "Open-loop DC gain", "record": RID, "csv": "ac", "key": "gain_dc_db", "reduce": "min",
    "expected": 61.64, "tol": 0.005, "unit": "dB",
    "at": {"corner": "fs", "temp_c": 125}, "printed": ["61.64 dB @ FS / 125 °C"],
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
        self.fig(expected=61.74, printed=["61.74 dB @ FS / 125 °C"])
        self.write_spec(SPEC.replace("61.64", "61.74"))
        errs = sf.check(self.tmp)
        self.assertTrue(any("recomputed" in e for e in errs), errs)

    def alter_row(self, old, new):
        row = next(l for l in SPEC.splitlines() if l.startswith("| Open-loop"))
        self.assertIn(old, row)
        self.write_spec(SPEC.replace(row, row.replace(old, new)))

    def test_altered_row_figure_fails_despite_other_copies(self):
        # The Judge's repro: only the row's copy changes; the copy in another
        # row and in the summary paragraph stay correct.
        self.alter_row("61.64 dB", "61.65 dB")
        errs = sf.check(self.tmp)
        self.assertTrue(any("occurs 0x in its section 2 row" in e for e in errs), errs)

    def test_altered_row_corner_text_fails(self):
        self.alter_row("@ FS / 125", "@ SS / 125")
        errs = sf.check(self.tmp)
        self.assertTrue(any("occurs 0x" in e for e in errs), errs)
        self.assertTrue(any("not covered" in e for e in errs), errs)

    def test_unlisted_extra_copy_in_row_fails(self):
        self.alter_row("record", "(grid 61.64–70.0) record")
        errs = sf.check(self.tmp)
        self.assertTrue(any("not covered by any printed string" in e for e in errs), errs)

    def test_repeated_figure_listed_twice_passes_and_one_copy_altered_fails(self):
        self.alter_row("record", "again 61.64 dB @ FS / 125 °C record")
        self.fig(printed=["61.64 dB @ FS / 125 °C"] * 2)
        self.assertEqual(sf.check(self.tmp), [])
        self.alter_row("record", "again 61.65 dB @ FS / 125 °C record")
        errs = sf.check(self.tmp)
        self.assertTrue(any("occurs 1x" in e and "lists 2x" in e for e in errs), errs)

    def test_repeated_figure_listed_once_fails(self):
        self.alter_row("record", "again 61.64 dB @ FS / 125 °C record")
        errs = sf.check(self.tmp)
        self.assertTrue(any("occurs 2x" in e for e in errs), errs)

    def test_corner_missing_from_printed_fails(self):
        self.fig(printed=["61.64 dB"])
        errs = sf.check(self.tmp)
        self.assertTrue(any("binding corner 'FS / 125 °C'" in e for e in errs), errs)

    def test_negative_temp_corner_text(self):
        self.assertEqual(sf.corner_text({"corner": "ss", "temp_c": -40}), "SS / \u221240 °C")

    def test_expected_disagrees_with_printed_fails(self):
        self.fig(expected=61.63)
        errs = sf.check(self.tmp)
        self.assertTrue(any("disagrees with printed" in e for e in errs), errs)

    def test_tol_disagrees_with_printed_precision_fails(self):
        self.fig(tol=0.05)
        errs = sf.check(self.tmp)
        self.assertTrue(any("printed precision" in e for e in errs), errs)

    def test_missing_row_fails(self):
        self.fig(row_match="No such row")
        errs = sf.check(self.tmp)
        self.assertTrue(any("found 0" in e for e in errs), errs)

    def test_record_cited_only_outside_row_fails(self):
        self.alter_row(f"record `{RID}`", "record elsewhere")
        self.write_spec((self.tmp / sf.SPEC).read_text(encoding="utf-8").replace(
            "Summary:", f"Summary (`{RID}`):"))
        errs = sf.check(self.tmp)
        self.assertTrue(any("not cited in its section 2 row" in e for e in errs), errs)

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
