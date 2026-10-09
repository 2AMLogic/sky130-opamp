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
        self.assertEqual(set(pvt.ANALYSES) | set(pvt.KLT_ANALYSES), set(pvt.FIELDNAMES))
        # the legacy ngspice-loop analyses are the default set; icmr/cmrr are opt-in
        self.assertEqual(set(pvt.ANALYSES), set(pvt.DEFAULT_ANALYSES))
        self.assertFalse(set(pvt.KLT_ANALYSES) & set(pvt.DEFAULT_ANALYSES))

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


TEXT_COLUMNS = {"corner", "cm_point", "low_limiter", "high_limiter"}


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
                grid = len(m["corners"]) * len(m["temps_c"])
                # the cmrr bench is run at two CM bias points -> two rows per grid point
                units = sum(2 if a == "cmrr" else 1 for a in m["analyses"])
                if m["n_runs"] != grid * units:
                    # the first icmr/cmrr records (095419, 101813) counted passed units only
                    self.assertEqual(m["n_runs"], grid * units - m["n_failed"])
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
                    per_point = 2 if analysis == "cmrr" else 1
                    full = len(m["corners"]) * len(m["temps_c"]) * per_point
                    self.assertLessEqual(len(rows), full)
                    self.assertGreaterEqual(len(rows), full - m["n_failed"])
                    seen = set()
                    for r in rows:
                        for k, v in r.items():
                            if k not in TEXT_COLUMNS:
                                float(v)
                        self.assertIn(r["corner"], m["corners"])
                        self.assertIn(float(r["temp_c"]), m["temps_c"])
                        self.assertAlmostEqual(
                            float(r["vdd_v"]), m["vdd_by_corner"][r["corner"]])
                        seen.add((r["corner"], float(r["temp_c"]), r.get("cm_point")))
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


class FakeKltPdk(FakePdk):
    variant = "sky130A"


def klt_request(analysis, cm_point=None, vdd=None, corners=None, temps=(27.0,)):
    corners = corners or list(pvt.DEFAULT_CORNERS)
    with tempfile.TemporaryDirectory() as d:
        path, tag = pvt.build_klt_request(
            analysis, cm_point, vdd, FakeKltPdk(), corners, list(temps), Path(d), "batch")
        body = (Path(d) / f"{tag}-body.spice").read_text()
        return json.loads(path.read_text()), body, tag


class KltBenchTests(unittest.TestCase):
    def test_bodies_are_klt_circuit_bodies_with_no_unrendered_placeholders(self):
        for analysis, cm, vdd in (("icmr", None, 1.8), ("cmrr", "mid", None), ("cmrr", "window", None)):
            with self.subTest(analysis=analysis, cm=cm):
                _req, body, _tag = klt_request(analysis, cm, vdd)
                live = "\n".join(ln for ln in body.splitlines() if not ln.lstrip().startswith("*")) + "\n"
                self.assertNotRegex(live, r"\{[A-Za-z_]")
                for forbidden in (".control", ".end\n", ".lib", ".temp"):
                    self.assertNotIn(forbidden, live)

    def test_cmrr_request_pairs_vdd_with_corner_via_exclude(self):
        req, _b, _t = klt_request("cmrr", "mid")
        self.assertEqual(req["analysis"]["kind"], "ac")
        self.assertEqual(req["corners"]["supply_v"]["vdd"], [1.62, 1.8, 1.98])
        keep = {(c, v) for c in req["corners"]["process"] for v in req["corners"]["supply_v"]["vdd"]}
        for ex in req["exclude"]:
            keep.discard((ex["process"], ex["supply_v"]["vdd"]))
        self.assertEqual(keep, {(c, pvt.VDD_BY_CORNER[c]) for c in pvt.DEFAULT_CORNERS})
        self.assertEqual(req["batch"]["runner_version_check"], pvt.RUNNER_VERSION_CHECK[0])

    def test_icmr_request_is_one_per_corner_with_literal_midpoint(self):
        groups = pvt.vdd_groups(list(pvt.DEFAULT_CORNERS))
        self.assertEqual(sorted(groups), [1.62, 1.8, 1.98])
        self.assertEqual(sorted(groups[1.8]), ["fs", "sf", "tt"])
        req, _b, tag = klt_request("icmr", None, 1.62, ["ss"])
        self.assertEqual(tag, "icmr-ss")
        self.assertEqual(req["corners"]["process"], ["ss"])
        self.assertEqual(req["analysis"]["kind"], "dc")
        self.assertNotIn("exclude", req)
        meas = {m["name"]: m["spice"] for m in req["measurements"]}
        self.assertIn("at=0.81", meas["vid_mid_v"])
        # primary 40 dB level is 10**-2; 30/50 dB form the sensitivity band
        self.assertIn("v(k)=0.01 ", meas["lo_40db"] + " ")
        self.assertEqual(set(pvt.ICMR_CMRR_FLOORS_DB), {"40db", "30db", "50db"})

    def test_measurement_names_cover_the_row_builders(self):
        names = {m["name"] for m in pvt.icmr_measurements(1.8)}
        for label in pvt.ICMR_CMRR_FLOORS_DB:
            self.assertLessEqual({f"lo_{label}", f"hi_{label}"}, names)
        cn = {m["name"] for m in pvt.cmrr_measurements()}
        for label, _f in pvt.CMRR_SPOTS:
            self.assertLessEqual({f"adm_{label}_db", f"acm_{label}_db"}, cn)

    def test_target_window_is_the_ratified_one(self):
        self.assertEqual(pvt.TARGET_ICMR_V, (0.888, 1.024))
        self.assertEqual(pvt.CONSUMER_SENSE_V, 0.73)

    def test_cmrr_row_is_adm_minus_acm_from_the_same_response(self):
        vals = {"gbw_hz": 1e7}
        for label, _f in pvt.CMRR_SPOTS:
            vals[f"adm_{label}_db"], vals[f"acm_{label}_db"] = 70.0, -3.0
        row = pvt.cmrr_row("tt", 27.0, {"values": vals, "status": "pass", "runtime_s": 1.0}, "mid")
        self.assertAlmostEqual(row["cmrr_1khz_db"], 73.0)
        self.assertEqual(set(row), set(pvt.FIELDNAMES["cmrr"]))
        self.assertAlmostEqual(row["vcm_v"], 0.9)
        vals.pop("acm_1khz_db")
        with self.assertRaises(sh.HarnessError):
            pvt.cmrr_row("tt", 27.0, {"values": vals, "status": "pass", "runtime_s": 1.0}, "mid")

    def test_icmr_row_flags_rail_vs_input_stage_and_target_coverage(self):
        vals = {"vid_mid_v": 1e-4, "vout_mid_v": 0.9, "iq_mid_a": -6e-5, "k_mid": 1e-3}
        for label in pvt.ICMR_CMRR_FLOORS_DB:
            vals[f"lo_{label}"], vals[f"hi_{label}"] = 0.6, 1.3
        vals["lo_40db"], vals["hi_40db"] = 0.0, 1.5  # rail-limited at 0 V, input-limited at 1.5 V
        row = pvt.icmr_row("tt", 27.0, {"values": vals, "status": "pass", "runtime_s": 1.0})
        self.assertEqual((row["low_limiter"], row["high_limiter"]), ("rail_0v", "input_stage"))
        self.assertEqual((row["covers_target_window"], row["covers_0v73"]), (1, 1))
        self.assertAlmostEqual(row["cmrr_mid_db"], 60.0)
        self.assertEqual(set(row), set(pvt.FIELDNAMES["icmr"]))
        vals["lo_40db"] = 0.95  # misses 0.73 V and the low end of the target window
        row = pvt.icmr_row("tt", 27.0, {"values": vals, "status": "pass", "runtime_s": 1.0})
        self.assertEqual((row["covers_target_window"], row["covers_0v73"]), (0, 0))

    def test_corner_values_maps_report_by_corner_and_temp(self):
        rep = {"corners": [{"process": "ss", "temperature_c": -40, "supply_v": {"vdd": 1.62},
                            "status": "pass", "runtime_s": 2.0,
                            "measurements": [{"name": "a", "value": 1.5}]}]}
        got = pvt._corner_values(rep)
        self.assertEqual(got[("ss", -40.0)]["values"], {"a": 1.5})
        self.assertEqual(got[("ss", -40.0)]["vdd"], 1.62)

    def test_crosscheck_agreement_and_disagreement(self):
        ref = RECORDS / "20261001-074923-c317ff9-ac.csv"
        r = next(csv.DictReader(ref.open()))
        cm = {"corner": r["corner"], "temp_c": float(r["temp_c"]),
              "adm_1hz_db": float(r["gain_dc_db"]), "gbw_hz": float(r["gbw_hz"])}
        ic = {"corner": r["corner"], "temp_c": float(r["temp_c"]), "iq_mid_a": float(r["iq_a"])}
        self.assertTrue(pvt.crosscheck(ref, [cm], [ic])["ok"])
        self.assertFalse(pvt.crosscheck(ref, [dict(cm, adm_1hz_db=cm["adm_1hz_db"] + 1.0)], [ic])["ok"])


if __name__ == "__main__":
    unittest.main()
