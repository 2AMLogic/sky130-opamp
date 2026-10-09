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
CSV = ("corner,temp_c,vdd_v,gain_dc_db\n"
       "tt,27.0,1.8,66.0\nfs,125.0,1.8,61.6392\nss,-40.0,1.62,68.0\n")
MATRIX = {"record": RID, "csv": "ac", "supply_key": "vdd_v", "points": [
    {"corner": "tt", "temp_c": 27, "vdd_v": 1.8},
    {"corner": "fs", "temp_c": 125, "vdd_v": 1.8},
    {"corner": "ss", "temp_c": -40, "vdd_v": 1.62}]}
MAPPING = {"matrices": {"m": MATRIX}, "figures": [{
    "matrix": "m", "row": "Open-loop DC gain", "record": RID, "csv": "ac", "key": "gain_dc_db", "reduce": "min",
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


class MatrixTests(FixtureTests):
    def csv(self, text):
        (self.tmp / sf.OPAMP_RECORDS / f"{RID}-ac.csv").write_text(text)

    def matrix(self, **kw):
        m = json.loads(json.dumps(MAPPING))
        m["matrices"]["m"].update(kw)
        self.write_map(m)

    def errs(self):
        return [e for e in sf.check(self.tmp) if "matrix" in e]

    def test_removed_non_binding_corner_fails(self):
        self.csv("corner,temp_c,vdd_v,gain_dc_db\nfs,125.0,1.8,61.6392\nss,-40.0,1.62,68.0\n")
        e = self.errs()
        self.assertEqual(len(e), 1)
        self.assertIn("missing expected point tt/27 C/1.8 V", e[0])
        self.assertIn(f"{RID}-ac", e[0])

    def test_duplicate_tuple_fails(self):
        self.csv(CSV + "tt,27.0,1.8,67.0\n")
        self.assertTrue(any("duplicate point tt/27 C/1.8 V in rows [1, 4]" in e for e in self.errs()))

    def test_unexpected_supply_fails(self):
        self.csv(CSV.replace("ss,-40.0,1.62", "ss,-40.0,1.98"))
        e = "\n".join(self.errs())
        self.assertIn("unexpected point ss/-40 C/1.98 V", e)
        self.assertIn("missing expected point ss/-40 C/1.62 V", e)

    def test_nonfinite_metric_fails(self):
        for bad in ("nan", "inf", ""):
            self.csv(CSV.replace("66.0", bad))
            self.assertTrue(any("point tt/27 C/1.8 V has nonfinite" in e for e in self.errs()), bad)

    def test_axes_paired_supply_and_exclusion(self):
        self.matrix(points=None)
        m = json.loads((self.tmp / sf.MAPPING).read_text())
        del m["matrices"]["m"]["points"]
        m["matrices"]["m"].update(
            axes={"corner": ["tt", "fs", "ss"], "temp_c": [-40, 27, 125]},
            supply={"mode": "paired_with_corner", "by_corner": {"tt": 1.8, "fs": 1.8, "ss": 1.62}},
            exclude=[{"corner": "tt", "temp_c": -40}, {"corner": "tt", "temp_c": 125},
                     {"corner": "fs", "temp_c": -40}, {"corner": "fs", "temp_c": 27},
                     {"corner": "ss", "temp_c": 27}, {"corner": "ss", "temp_c": 125}])
        self.write_map(m)
        self.assertEqual(sf.check(self.tmp), [])
        m["matrices"]["m"]["exclude"].append({"corner": "ff", "temp_c": 27})
        self.write_map(m)
        self.assertTrue(any("matches no expected point" in e for e in self.errs()))

    def test_paired_supply_is_not_cartesian(self):
        m = json.loads((self.tmp / sf.MAPPING).read_text())
        del m["matrices"]["m"]["points"]
        m["matrices"]["m"].update(
            axes={"corner": ["tt", "ss"], "temp_c": [27]},
            supply={"mode": "cartesian", "values": [1.62, 1.8]})
        self.write_map(m)
        self.assertTrue(any("missing expected point" in e for e in self.errs()))

    def test_missing_matrix_fails(self):
        m = json.loads((self.tmp / sf.MAPPING).read_text())
        m["figures"][0]["matrix"] = "nope"
        self.write_map(m)
        self.assertTrue(any("no authored matrix 'nope'" in e for e in sf.check(self.tmp)))

    def test_matrix_dataset_mismatch_fails(self):
        self.matrix(csv="other")
        self.assertTrue(any("matrix m csv" in e for e in self.errs()))

    def test_where_filtered_datasets_checked_independently(self):
        rows = ["corner,temp_c,vdd_v,cm_point,gain_dc_db"]
        for cm in ("mid", "window"):
            rows += [f"tt,27.0,1.8,{cm},66.0", f"fs,125.0,1.8,{cm},61.6392", f"ss,-40.0,1.62,{cm},68.0"]
        full = "\n".join(rows) + "\n"
        m = json.loads(json.dumps(MAPPING))
        base = m["matrices"]["m"]
        m["matrices"] = {"mid": dict(base, where={"cm_point": "mid"}),
                         "win": dict(base, where={"cm_point": "window"})}
        f0 = m["figures"][0]
        m["figures"] = [dict(f0, matrix="mid", where={"cm_point": "mid"}),
                        dict(f0, row="Other row", matrix="win", where={"cm_point": "window"})]
        self.write_map(m)
        self.csv(full)
        self.assertEqual(self.errs(), [])
        self.csv(full.replace("tt,27.0,1.8,window,66.0\n", ""))
        e = self.errs()
        self.assertEqual(len(e), 1)
        self.assertIn("matrix win", e[0])

    def test_shared_matrix_reported_once(self):
        m = json.loads(json.dumps(MAPPING))
        m["figures"].append(dict(m["figures"][0], row="Other row", key="gain_dc_db"))
        self.write_map(m)
        self.csv("corner,temp_c,vdd_v,gain_dc_db\nfs,125.0,1.8,61.6392\nss,-40.0,1.62,68.0\n")
        self.assertEqual(len(self.errs()), 1)


class CommittedTests(unittest.TestCase):
    def test_committed_spec_agrees_with_records(self):
        self.assertEqual(sf.check(_paths.REPO), [])


if __name__ == "__main__":
    unittest.main()
