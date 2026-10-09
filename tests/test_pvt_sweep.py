import csv
import json
import re
import tempfile
import unittest
from pathlib import Path

import _paths
from _paths import EXP, RECORDS, REPO, TESTBENCH
import spice_harness as sh

pvt = _paths.load_module("pvt_sweep", EXP / "bin" / "pvt_sweep.py")

TEMPLATES = {
    "ac": "opamp_ac.spice.tmpl",
    "tran_sr": "opamp_tran_sr.spice.tmpl",
    "dc_swing": "opamp_dc_swing.spice.tmpl",
}
PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


class FakePdk:
    """Stands in for OpampPdk: only the path accessors the subs builder uses."""

    def corner_include(self, corner):
        return Path(f"/pdk/corners/{corner}.spice")

    def rc_includes(self):
        return [Path("/pdk/rc/base.spice"), Path("/pdk/rc/lin.spice")]


def ac_subs(vdd=1.8):
    s = pvt.common_subs(FakePdk(), "tt", 27.0, vdd)
    s.update({"VCM": 0.5 * vdd, "RFB": "1e12", "CFB": "1", "FSTART": "1",
              "FSTOP": "1g", "PTS_PER_DEC": "20"})
    return s


class ParseMeasTests(unittest.TestCase):
    def test_parses_plain_and_trailer_lines(self):
        out = pvt.parse_meas(
            "gain_dc_db = 7.2e+01\n"
            "sr_rise_s = 2.5e-08 targ= 1.1e-06 trig= 1.0e-06\n"
            "noise: not a meas line\n"
            "  iq_a=6.4e-05\n"
        )
        self.assertEqual(out["gain_dc_db"], 72.0)
        self.assertEqual(out["sr_rise_s"], 2.5e-08)
        self.assertEqual(out["iq_a"], 6.4e-05)
        self.assertEqual(len(out), 3)

    def test_ignores_non_numeric_values(self):
        self.assertEqual(pvt.parse_meas("x = failed\ny = -.5\n"), {"y": -0.5})


class CommonSubsTests(unittest.TestCase):
    def test_pin_resolution_into_subs(self):
        s = pvt.common_subs(FakePdk(), "ff", 125.0, 1.98)
        self.assertEqual(s["CORNER_INCLUDE"], Path("/pdk/corners/ff.spice"))
        self.assertEqual(s["RC_INCLUDE_BASE"], Path("/pdk/rc/base.spice"))
        self.assertEqual(s["RC_INCLUDE_LIN"], Path("/pdk/rc/lin.spice"))
        self.assertEqual((s["TEMP"], s["VDD"]), (125.0, 1.98))
        self.assertEqual(s["OPAMP_NETLIST"], pvt.DESIGN_NETLIST)

    def test_opamp_pdk_rc_includes_from_own_pin(self):
        own = json.loads((EXP / "pdk.json").read_text())
        pin = json.loads((pvt.GMID_PDK_PIN_FILE).read_text())
        pdk = pvt.OpampPdk(pin, own)
        rels = own["rc_corner"]["include_files"]
        self.assertEqual(pdk.rc_includes(), [pdk.dir / r for r in rels])
        self.assertEqual(len(rels), 2)  # both files are required together

    def test_vdd_table_covers_default_corners(self):
        self.assertEqual(set(pvt.VDD_BY_CORNER), set(pvt.DEFAULT_CORNERS))
        self.assertAlmostEqual(pvt.VDD_BY_CORNER["ff"], 1.1 * 1.8)
        self.assertAlmostEqual(pvt.VDD_BY_CORNER["ss"], 0.9 * 1.8)


class TemplateTests(unittest.TestCase):
    def test_ac_template_renders_with_runner_subs(self):
        text = sh.render(TESTBENCH / TEMPLATES["ac"], ac_subs())
        self.assertNotIn("{", text)
        self.assertIn("/pdk/corners/tt.spice", text)

    def test_every_template_placeholder_is_supplied_by_the_runner(self):
        """Each analysis's runner-side keys must cover its template's placeholders.

        Keys are taken from the runner source (the literal strings passed to
        subs/common_subs), so a renamed placeholder in either place fails.
        """
        src = (EXP / "bin" / "pvt_sweep.py").read_text()
        common = set(pvt.common_subs(FakePdk(), "tt", 27.0, 1.8))
        for analysis, name in TEMPLATES.items():
            fn_src = src.split(f"def run_{analysis}(", 1)[1].split("\ndef ", 1)[0]
            supplied = common | set(re.findall(r'"([A-Z][A-Z0-9_]*)":', fn_src))
            wanted = set(PLACEHOLDER.findall((TESTBENCH / name).read_text()))
            self.assertTrue(wanted, name)
            self.assertLessEqual(wanted, supplied,
                                 f"{name}: unsupplied {sorted(wanted - supplied)}")

    def test_missing_placeholder_fails_render(self):
        subs = ac_subs()
        del subs["CL_F"]
        with self.assertRaises(sh.HarnessError) as cm:
            sh.render(TESTBENCH / TEMPLATES["ac"], subs)
        self.assertIn("CL_F", str(cm.exception))

    def test_scratch_copy_with_broken_placeholder_fails(self):
        """Deliberate break: a misspelled placeholder in a copy is caught."""
        text = (TESTBENCH / TEMPLATES["ac"]).read_text().replace("{VCM}", "{VCMM}")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "broken.tmpl"
            p.write_text(text)
            with self.assertRaises(sh.HarnessError):
                sh.render(p, ac_subs())


class AggregationTests(unittest.TestCase):
    def test_analyses_and_fieldnames_agree(self):
        self.assertEqual(set(pvt.ANALYSES), set(pvt.FIELDNAMES))
        self.assertEqual(set(pvt.ANALYSES), set(pvt.DEFAULT_ANALYSES))

    def test_csv_roundtrip_with_runner_fieldnames(self):
        row = dict.fromkeys(pvt.FIELDNAMES["tran_sr"], 1.0)
        row.update(corner="tt", temp_c=27.0)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.csv"
            with p.open("w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=pvt.FIELDNAMES["tran_sr"], lineterminator="\n")
                w.writeheader()
                w.writerow(row)
            back = list(csv.DictReader(p.read_text().splitlines()))
        self.assertEqual(back[0]["corner"], "tt")
        self.assertEqual(list(back[0]), pvt.FIELDNAMES["tran_sr"])

    def test_extra_row_key_is_rejected_by_writer(self):
        import io
        w = csv.DictWriter(io.StringIO(), fieldnames=pvt.FIELDNAMES["ac"])
        with self.assertRaises(ValueError):
            w.writerow({"bogus": 1})


def pvt_records():
    """Committed PVT-bench records: JSON files carrying a `matrix` block."""
    out = []
    for p in sorted(RECORDS.glob("*.json")):
        try:
            d = json.loads(p.read_text())
        except ValueError:
            continue
        if isinstance(d, dict) and "matrix" in d and "analyses" in d["matrix"] \
                and d.get("experiment", {}).get("slug") == "opamp-characterization" \
                and any(k.endswith("_csv") for k in d.get("links", {})):
            out.append((p, d))
    return out


class CommittedRecordShapeTests(unittest.TestCase):
    TOP = {"record_id", "timestamp", "git", "experiment", "matrix", "pdk",
           "tools", "links", "errors", "elapsed_s"}
    MATRIX = {"corners", "temps_c", "analyses", "vdd_by_corner", "cl_f",
              "ibias_a", "n_runs", "n_failed"}
    PDK = {"variant", "installed_commit", "pinned_commit", "matches_pin", "rc_corner"}

    def test_at_least_one_pvt_record_is_committed(self):
        self.assertTrue(pvt_records())

    def test_json_shape(self):
        for p, d in pvt_records():
            with self.subTest(record=p.name):
                self.assertLessEqual(self.TOP, set(d))
                self.assertLessEqual(self.MATRIX, set(d["matrix"]))
                self.assertLessEqual(self.PDK, set(d["pdk"]))
                self.assertEqual(d["record_id"], p.stem)
                self.assertIn("sha", d["git"])
                self.assertIsInstance(d["errors"], list)
                self.assertEqual(d["matrix"]["n_failed"], len(d["errors"]))
                m = d["matrix"]
                self.assertEqual(
                    m["n_runs"], len(m["corners"]) * len(m["temps_c"]) * len(m["analyses"]))
                for c in m["corners"]:
                    self.assertIn(c, m["vdd_by_corner"])

    def test_links_resolve_and_csv_matches_matrix(self):
        for p, d in pvt_records():
            m = d["matrix"]
            for analysis in m["analyses"]:
                with self.subTest(record=p.name, analysis=analysis):
                    rel = d["links"][f"{analysis}_csv"]
                    path = REPO / rel
                    self.assertTrue(path.is_file(), rel)
                    with path.open(newline="") as f:
                        reader = csv.DictReader(f)
                        self.assertEqual(reader.fieldnames, pvt.FIELDNAMES[analysis])
                        rows = list(reader)
                    self.assertEqual(len(rows), len(m["corners"]) * len(m["temps_c"]) - m["n_failed"])
                    seen = set()
                    for r in rows:
                        for k, v in r.items():
                            float(v) if k != "corner" else None
                        self.assertIn(r["corner"], m["corners"])
                        self.assertIn(float(r["temp_c"]), m["temps_c"])
                        self.assertAlmostEqual(
                            float(r["vdd_v"]), m["vdd_by_corner"][r["corner"]])
                        seen.add((r["corner"], float(r["temp_c"])))
                    self.assertEqual(len(seen), len(rows))  # no duplicate corner/temp

    def test_ac_rows_are_self_consistent(self):
        for p, d in pvt_records():
            if "ac" not in d["matrix"]["analyses"]:
                continue
            for r in csv.DictReader((REPO / d["links"]["ac_csv"]).read_text().splitlines()):
                with self.subTest(record=p.name, corner=r["corner"], t=r["temp_c"]):
                    self.assertAlmostEqual(
                        float(r["phase_margin_deg"]),
                        180.0 + float(r["phase_at_gbw_deg"]), places=6)
                    self.assertAlmostEqual(
                        float(r["vcm_v"]), 0.5 * float(r["vdd_v"]), places=6)


if __name__ == "__main__":
    unittest.main()
