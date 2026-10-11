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
| Open-loop DC gain | superseded sizing: worst-case **61.64 dB @ FS / 125 °C** record `{RID}` |
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
    "at": {"corner": "fs", "temp_c": 125, "supply_v": 1.8}, "printed": ["61.64 dB @ FS / 125 °C"],
    "scope": "historical", "scope_text": "superseded sizing", "historical_reason": "fixture", "legacy_unverified": True,
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
        self.fig(at={"corner": "ss", "temp_c": 125, "supply_v": 1.8})
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


class SupplyBindingTests(unittest.TestCase):
    """Binding supply (issue #172). Fixture: power-like max with two supplies at ff/125."""
    PSPEC = SPEC.replace("| Other row |", f"| Quiescent power | superseded sizing **131.92 µW @ FF / 125 °C / 1.98 V** `{RID}` |\n| Other row |")
    HDR = "corner,temp_c,vdd_v,gain_dc_db,pq_w\n"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        rec = self.tmp / sf.OPAMP_RECORDS
        rec.mkdir(parents=True)
        (rec / f"{RID}.json").write_text("{}")
        (self.tmp / "spec").mkdir()
        (self.tmp / "manifests").mkdir()
        self.write_spec(self.PSPEC)
        self.rows = ["tt,27.0,1.8,66.0,0.00005", "fs,125.0,1.8,61.6392,0.00006",
                     "ss,-40.0,1.62,68.0,0.00004", "ff,125.0,1.98,70.0,0.00013192",
                     "ff,125.0,1.62,70.0,0.00010"]
        self.points = [{"corner": c, "temp_c": t, "vdd_v": v} for c, t, v in
                       [("tt", 27, 1.8), ("fs", 125, 1.8), ("ss", -40, 1.62), ("ff", 125, 1.98), ("ff", 125, 1.62)]]
        self.set_map()

    def set_map(self, at=None, printed=None, **kw):
        m = json.loads(json.dumps(MAPPING))
        m["matrices"]["m"]["points"] = self.points
        f = dict(m["figures"][0], row="Quiescent power", key="pq_w", reduce="max", scale=1e6,
                 expected=131.92, tol=0.005, unit="uW", print_supply=True,
                 at=at or {"corner": "ff", "temp_c": 125, "supply_v": 1.98},
                 printed=printed or ["131.92 µW @ FF / 125 °C / 1.98 V"])
        f.update(kw)
        m["figures"].append(f)
        m["figures"] = m["figures"][1:]
        self.write_map(m)

    def write_spec(self, t):
        (self.tmp / sf.SPEC).write_text(t, encoding="utf-8")

    def write_map(self, m):
        (self.tmp / sf.MAPPING).write_text(json.dumps(m), encoding="utf-8")

    def write_rows(self, rows=None):
        (self.tmp / sf.OPAMP_RECORDS / f"{RID}-ac.csv").write_text(self.HDR + "\n".join(rows or self.rows) + "\n")

    def test_distinguishes_actual_supply_and_passes(self):
        self.write_rows()
        self.assertEqual(sf.check(self.tmp), [])

    def test_row_order_irrelevant(self):
        self.write_rows(self.rows[::-1])
        self.assertEqual(sf.check(self.tmp), [])

    def test_coordinated_edit_to_162_fails_with_both_supplies(self):
        self.write_spec(self.PSPEC.replace("1.98 V", "1.62 V"))
        self.set_map(at={"corner": "ff", "temp_c": 125, "supply_v": 1.62},
                     printed=["131.92 µW @ FF / 125 °C / 1.62 V"])
        self.write_rows()
        errs = [e for e in sf.check(self.tmp) if "binding" in e]
        self.assertEqual(len(errs), 1, errs)
        self.assertIn("1.98", errs[0])
        self.assertIn("1.62", errs[0])

    def test_printed_voltage_must_match_numeric_supply(self):
        self.write_spec(self.PSPEC.replace("1.98 V", "1.62 V"))
        self.set_map(printed=["131.92 µW @ FF / 125 °C / 1.62 V"])
        self.write_rows()
        errs = sf.check(self.tmp)
        self.assertTrue(any("printed supply 1.62 V" in e and "1.98" in e for e in errs), errs)

    def test_print_supply_requires_voltage_rendering(self):
        self.write_spec(self.PSPEC.replace(" / 1.98 V", ""))
        self.set_map(printed=["131.92 µW @ FF / 125 °C"])
        self.write_rows()
        self.assertTrue(any("print_supply" in e for e in sf.check(self.tmp)))

    def test_missing_supply_v_fails(self):
        self.set_map(at={"corner": "ff", "temp_c": 125})
        self.write_rows()
        self.assertTrue(any("at.supply_v" in e for e in sf.check(self.tmp)))

    def test_tie_any_tied_point_attains_extremum(self):
        tie = [r.replace("0.00010", "0.00013192") for r in self.rows]
        for order in (tie, tie[::-1]):
            for sv, txt in ((1.98, "1.98"), (1.62, "1.62")):
                self.write_spec(self.PSPEC.replace("1.98 V", f"{txt} V"))
                self.set_map(at={"corner": "ff", "temp_c": 125, "supply_v": sv},
                             printed=[f"131.92 µW @ FF / 125 °C / {txt} V"])
                self.write_rows(order)
                self.assertEqual(sf.check(self.tmp), [], (sv, order))

    def test_non_extremum_point_with_same_corner_fails(self):
        # ff/125/1.62 is not the max, so it cannot be authored as binding.
        self.write_spec(self.PSPEC.replace("1.98 V", "1.62 V"))
        self.set_map(at={"corner": "ff", "temp_c": 125, "supply_v": 1.62},
                     printed=["131.92 µW @ FF / 125 °C / 1.62 V"])
        self.write_rows()
        self.assertTrue(any("claimed" in e for e in sf.check(self.tmp)))


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


class CampaignFigureTests(unittest.TestCase):
    CJ = "sim/x/records/camp.campaign.json"
    MD = "sim/x/records/camp.md"
    SPEC = ("# spec\n## 2. Targets\n| P | T |\n|---|---|\n"
            "| Input-referred offset | previous DUT: sigma 8.69 mV @ SS / 27 °C camp.md camp.campaign.json |\n## 3. x\n")

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        (self.tmp / "spec").mkdir()
        (self.tmp / "manifests").mkdir()
        (self.tmp / "sim/x/records").mkdir(parents=True)
        (self.tmp / self.MD).write_text("x")
        self.write_json(n_ok_ss=300)
        (self.tmp / sf.SPEC).write_text(self.SPEC, encoding="utf-8")
        fig = {"row": "Input-referred offset", "campaign_json": self.CJ, "record_md": self.MD,
               "corners": ["tt", "ss"], "n_per_corner": 300, "key": "sigma_v", "reduce": "max",
               "scale": 1000.0, "expected": 8.69, "tol": 0.005, "unit": "mV",
               "at": {"corner": "ss", "temp_c": 27}, "printed": ["8.69 mV @ SS / 27 °C"],
               "scope": "historical", "scope_text": "previous DUT", "historical_reason": "fixture",
               "legacy_unverified": True}
        (self.tmp / sf.MAPPING).write_text(json.dumps({"figures": [], "campaign_figures": [fig]}))

    def write_json(self, n_ok_ss):
        def st(sig, n_ok):
            return {"n_requested": 300, "n_ok": n_ok, "n_failed": 300 - n_ok, "sigma_v": sig}
        (self.tmp / self.CJ).write_text(json.dumps(
            {"temp_c": 27.0, "corners": {"tt": st(0.0085, 300), "ss": st(0.0086919, n_ok_ss)}}))

    def test_passes(self):
        self.assertEqual(sf.check(self.tmp), [])

    def test_altered_summary_fails(self):
        (self.tmp / self.CJ).write_text((self.tmp / self.CJ).read_text().replace("0.0086919", "0.0087919"))
        self.assertTrue(any("recomputed" in e for e in sf.check(self.tmp)))

    def test_failed_samples_fail(self):
        self.write_json(n_ok_ss=299)
        self.assertTrue(any("expected 300 ok / 0 failed" in e for e in sf.check(self.tmp)))

    def test_altered_spec_copy_fails(self):
        (self.tmp / sf.SPEC).write_text(self.SPEC.replace("8.69", "8.68"), encoding="utf-8")
        self.assertTrue(any("occurs 0x" in e for e in sf.check(self.tmp)))


class ScopeProvenanceTests(unittest.TestCase):
    """DUT scope and provenance (issue #186). Fixture: a current-design gain
    figure on a record whose dut block names a snapshot equal to the canonical
    netlist."""
    NET = b"* canonical DUT\n.subckt opamp_core\n.ends\n"
    SNAP = "sim/opamp-characterization/netlist-snapshots/" + RID + "/opamp_core.spice"
    CSPEC = SPEC.replace("| Open-loop DC gain | superseded sizing: worst-case",
                         "| Open-loop DC gain | on the current sizing: worst-case")

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        rec = self.tmp / sf.OPAMP_RECORDS
        rec.mkdir(parents=True)
        (rec / f"{RID}-ac.csv").write_text(CSV)
        (self.tmp / "spec").mkdir()
        (self.tmp / "manifests").mkdir()
        (self.tmp / "design/netlist").mkdir(parents=True)
        (self.tmp / "design/netlist/opamp_core.spice").write_bytes(self.NET)
        (self.tmp / self.SNAP).parent.mkdir(parents=True)
        (self.tmp / self.SNAP).write_bytes(self.NET)
        self.write_record(self.NET)
        self.write_spec(self.CSPEC)
        self.fig()

    def write_record(self, data, dut=True):
        import hashlib
        rec = {"record_id": RID}
        if dut:
            rec["dut"] = {"source_path": "design/netlist/opamp_core.spice", "snapshot_path": self.SNAP,
                          "sha256": "sha256:" + hashlib.sha256(data).hexdigest()}
        (self.tmp / sf.OPAMP_RECORDS / f"{RID}.json").write_text(json.dumps(rec))

    def write_spec(self, t):
        (self.tmp / sf.SPEC).write_text(t, encoding="utf-8")

    def fig(self, **kw):
        f = dict(MAPPING["figures"][0], scope="current", scope_text="on the current sizing")
        for k in ("historical_reason", "legacy_unverified"):
            f.pop(k, None)
        f.update(kw)
        self.write_map({"matrices": MAPPING["matrices"], "figures": [f]})

    def write_map(self, m):
        (self.tmp / sf.MAPPING).write_text(json.dumps(m), encoding="utf-8")

    def errs(self):
        return sf.check(self.tmp)

    def test_current_verified_equal_passes(self):
        self.assertEqual(self.errs(), [])

    def test_current_other_dut_fails_despite_correct_numbers(self):
        other = b"* an older DUT\n"
        (self.tmp / self.SNAP).write_bytes(other)
        self.write_record(other)
        errs = self.errs()
        self.assertTrue(any("DUT mismatch" in e for e in errs), errs)
        self.assertFalse(any("recomputed" in e for e in errs), errs)

    def test_current_missing_snapshot_fails(self):
        (self.tmp / self.SNAP).unlink()
        self.assertTrue(any("snapshot missing" in e for e in self.errs()))

    def test_current_corrupt_snapshot_fails(self):
        (self.tmp / self.SNAP).write_bytes(self.NET + b"* edited\n")
        self.assertTrue(any("corrupted" in e for e in self.errs()))

    def test_current_missing_canonical_netlist_fails(self):
        (self.tmp / "design/netlist/opamp_core.spice").unlink()
        self.assertTrue(any("current netlist missing" in e for e in self.errs()))

    def test_current_legacy_record_fails(self):
        self.write_record(self.NET, dut=False)
        self.assertTrue(any("no verified `dut` block" in e for e in self.errs()))

    def test_current_cannot_be_marked_legacy(self):
        self.write_record(self.NET, dut=False)
        self.fig(legacy_unverified=True)
        self.assertTrue(any("no verified `dut` block" in e for e in self.errs()))

    def test_historical_legacy_needs_explicit_flag(self):
        self.write_record(self.NET, dut=False)
        self.write_spec(SPEC)
        self.fig(scope="historical", scope_text="superseded sizing", historical_reason="why")
        self.assertTrue(any("legacy_unverified" in e for e in self.errs()))
        self.fig(scope="historical", scope_text="superseded sizing", historical_reason="why",
                 legacy_unverified=True)
        self.assertEqual(self.errs(), [])

    def test_historical_verified_other_dut_is_allowed_but_integrity_checked(self):
        other = b"* an older DUT\n"
        (self.tmp / self.SNAP).write_bytes(other)
        self.write_record(other)
        self.write_spec(SPEC)
        self.fig(scope="historical", scope_text="superseded sizing", historical_reason="why")
        self.assertEqual(self.errs(), [])
        (self.tmp / self.SNAP).write_bytes(other + b"* edited\n")
        self.assertTrue(any("corrupted" in e for e in self.errs()))

    def test_legacy_flag_on_record_with_dut_fails(self):
        self.write_spec(SPEC)
        self.fig(scope="historical", scope_text="superseded sizing", historical_reason="why",
                 legacy_unverified=True)
        self.assertTrue(any("carries a `dut` block" in e for e in self.errs()))

    def test_historical_needs_reason(self):
        self.write_spec(SPEC)
        self.fig(scope="historical", scope_text="superseded sizing")
        self.assertTrue(any("historical_reason" in e for e in self.errs()))

    def test_missing_or_unknown_scope_fails(self):
        self.fig(scope=None)
        self.assertTrue(any("scope must be one of" in e for e in self.errs()))
        self.fig(scope="recent")
        self.assertTrue(any("scope must be one of" in e for e in self.errs()))

    def test_prose_calls_current_figure_historical_fails(self):
        # JSON says current; the row's prose describes the figure as superseded.
        self.write_spec(self.CSPEC.replace("on the current sizing: worst-case",
                                           "on the current sizing, superseded by none, but historical: worst-case"))
        self.assertTrue(any("describes it as historical" in e for e in self.errs()))

    def test_prose_scope_text_absent_fails(self):
        # JSON says current but the row carries no current-design wording.
        self.write_spec(SPEC)
        self.assertTrue(any("does not occur within" in e for e in self.errs()))

    def test_historical_json_with_current_prose_fails(self):
        self.fig(scope="historical", scope_text="on the current sizing", historical_reason="why")
        self.assertTrue(any("contains no historical word" in e for e in self.errs()))

    def test_current_scope_text_with_historical_word_fails(self):
        self.write_spec(self.CSPEC.replace("on the current sizing", "on the current (superseded) sizing"))
        self.fig(scope_text="on the current (superseded) sizing")
        self.assertTrue(any("must say 'current'" in e for e in self.errs()))

    def test_scope_text_after_figure_does_not_count(self):
        self.write_spec(SPEC.replace("superseded sizing: worst-case **61.64 dB @ FS / 125 °C**",
                                     "worst-case **61.64 dB @ FS / 125 °C** (current sizing)"))
        self.fig(scope_text="current sizing")
        self.assertTrue(any("does not occur within" in e for e in self.errs()))


class CommittedTests(unittest.TestCase):
    def test_committed_spec_agrees_with_records(self):
        self.assertEqual(sf.check(_paths.REPO), [])

    def test_committed_scopes_are_explicit(self):
        m = json.loads((_paths.REPO / sf.MAPPING).read_text(encoding="utf-8"))
        allf = m["figures"] + m["campaign_figures"]
        self.assertTrue(all(f.get("scope") in sf.SCOPES for f in allf))
        # Offset evidence has no canonical campaign: it must stay explicitly historical.
        self.assertTrue(all(f["scope"] == "historical" and f.get("legacy_unverified")
                            for f in m["campaign_figures"]))
        # Deterministic current claims cite the DR-013 canonical records.
        for f in m["figures"]:
            if f["scope"] == "current":
                self.assertIn("04489d4", f["record"])


if __name__ == "__main__":
    unittest.main()
