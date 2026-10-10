import csv
import json
import math
import re
import tempfile
import unittest
from pathlib import Path

import _paths
from _paths import EXP, RECORDS, REPO, TESTBENCH
import spice_harness as sh
import dut_identity

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
                    cart = m.get("supply_mode") == "cartesian"  # absent in pre-#110 (paired) records
                    n_sup = len(m["supplies_v"]) if cart else 1
                    full = len(m["corners"]) * len(m["temps_c"]) * n_sup * per_point
                    self.assertLessEqual(len(rows), full)
                    self.assertGreaterEqual(len(rows), full - m["n_failed"])
                    seen = set()
                    for r in rows:
                        for k, v in r.items():
                            if k not in TEXT_COLUMNS:
                                float(v)
                        self.assertIn(r["corner"], m["corners"])
                        self.assertIn(float(r["temp_c"]), m["temps_c"])
                        if cart:
                            self.assertIn(float(r["vdd_v"]), m["supplies_v"])
                        else:
                            self.assertAlmostEqual(
                                float(r["vdd_v"]), m["vdd_by_corner"][r["corner"]])
                        seen.add((r["corner"], float(r["temp_c"]), float(r["vdd_v"]), r.get("cm_point")))
                    self.assertEqual(len(seen), len(rows))  # no duplicate corner/temp/supply

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
        rows = list(csv.DictReader(ref.open()))
        r = rows[0]
        reference = {"available": True, "rows": rows, "identity": {"reference": ref.name}}
        cm = {"corner": r["corner"], "temp_c": float(r["temp_c"]), "vdd_v": float(r["vdd_v"]),
              "vcm_v": float(r["vcm_v"]), "adm_1hz_db": float(r["gain_dc_db"]), "gbw_hz": float(r["gbw_hz"])}
        ic = {"corner": r["corner"], "temp_c": float(r["temp_c"]), "vdd_v": float(r["vdd_v"]),
              "iq_mid_a": float(r["iq_a"])}
        self.assertTrue(pvt.crosscheck(reference, [cm], [ic])["ok"])
        self.assertFalse(pvt.crosscheck(reference, [dict(cm, adm_1hz_db=cm["adm_1hz_db"] + 1.0)], [ic])["ok"])


def ac_ref_row(corner="tt", temp=27.0, vdd=1.8, gain=66.0, gbw=2.0e7, iq=6.5e-5, pm=65.0, vcm=None):
    return {"corner": corner, "temp_c": str(temp), "vdd_v": str(vdd), "vcm_v": str(0.5 * vdd if vcm is None else vcm),
            "iq_a": str(iq), "gain_dc_db": str(gain), "gbw_hz": str(gbw), "phase_margin_deg": str(pm)}


def cc_rows(vdd=1.8, gain=66.0, gbw=2.0e7, iq=6.5e-5, corner="tt", temp=27.0):
    cm = {"corner": corner, "temp_c": temp, "vdd_v": vdd, "vcm_v": 0.5 * vdd, "adm_1hz_db": gain, "gbw_hz": gbw}
    ic = {"corner": corner, "temp_c": temp, "vdd_v": vdd, "iq_mid_a": iq}
    return cm, ic


def ref_of(rows):
    return {"available": True, "rows": rows, "identity": {"reference": "x"}}


class ReferenceBindingTests(unittest.TestCase):
    """Issue #143: historical AC is usable only with verified matching DUT identity."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.rdir = self.root / "records"
        self.rdir.mkdir()
        self.addCleanup(self._tmp.cleanup)

    def add(self, rid, dut_bytes=b"* dut A\n", legacy=False, rows=None, corrupt=False):
        (self.rdir / f"{rid}-ac.csv").write_text(
            "corner,temp_c,vdd_v,vcm_v,iq_a,gain_dc_db,gbw_hz,phase_margin_deg\n"
            + "".join(f"{r['corner']},{r['temp_c']},{r['vdd_v']},{r['vcm_v']},{r['iq_a']},"
                      f"{r['gain_dc_db']},{r['gbw_hz']},{r['phase_margin_deg']}\n"
                      for r in (rows or [ac_ref_row()])))
        rec = {"record_id": rid}
        if not legacy:
            snap = self.root / "snap" / rid
            snap.mkdir(parents=True)
            (snap / "opamp_core.spice").write_bytes(dut_bytes)
            declared = dut_identity.sha256_bytes(b"other" if corrupt else dut_bytes)
            rec["dut"] = {"snapshot_path": f"snap/{rid}/opamp_core.spice", "sha256": declared}
        (self.rdir / f"{rid}.json").write_text(json.dumps(rec))

    def select(self, sha=None, before="20261010-000000-zzz-000000"):
        sha = dut_identity.sha256_bytes(b"* dut A\n") if sha is None else sha
        return pvt.select_ac_reference(before, sha, self.root, self.rdir)

    def test_newer_different_dut_cannot_displace_compatible_evidence(self):
        self.add("20261001-000000-aaa-000001")
        self.add("20261005-000000-bbb-000002", dut_bytes=b"* dut B\n")
        got = self.select()
        self.assertTrue(got["available"])
        self.assertEqual(got["identity"]["record_id"], "20261001-000000-aaa-000001")
        self.assertEqual(got["identity"]["dut_sha256"], dut_identity.sha256_bytes(b"* dut A\n"))
        self.assertIn("different DUT", got["skipped_candidates"][0]["reason"])

    def test_legacy_unverified_ac_is_unavailable(self):
        self.add("20261001-000000-aaa-000001", legacy=True)
        got = self.select()
        self.assertFalse(got["available"])
        self.assertIn("no earlier AC record with verified DUT identity", got["unavailable_reasons"][0])
        self.assertIn("legacy", got["skipped_candidates"][0]["reason"])
        cc = pvt.crosscheck(got, [cc_rows()[0]], [cc_rows()[1]])
        self.assertIsNone(cc["ok"])  # neither agreement nor disagreement
        self.assertEqual((cc["cmrr_points_compared"], cc["cmrr_points_unmatched"]), (0, 1))
        self.assertTrue(cc["unavailable_reasons"])

    def test_corrupt_snapshot_is_unavailable_and_later_records_only(self):
        self.add("20261001-000000-aaa-000001", corrupt=True)
        self.add("20261011-000000-ccc-000003")  # not earlier than before_id
        got = self.select()
        self.assertFalse(got["available"])
        self.assertIn("failed verification", got["skipped_candidates"][0]["reason"])

    def test_no_candidates(self):
        self.assertIn("no earlier AC record exists", self.select()["unavailable_reasons"][0])

    def test_current_campaign_preferred_over_matching_history(self):
        self.add("20261001-000000-aaa-000001")
        meta = {"sha256": dut_identity.sha256_bytes(b"* dut A\n")}
        cur = [ac_ref_row(gain=70.0)]
        got = pvt.choose_ac_reference("20261010-000000-zzz-000000", meta, cur, self.root, self.rdir)
        self.assertEqual(got["identity"]["source"], "current_campaign")
        self.assertIs(got["rows"], cur)
        got = pvt.choose_ac_reference("20261010-000000-zzz-000000", meta, None, self.root, self.rdir)
        self.assertEqual(got["identity"]["source"], "historical")

    def test_two_supplies_at_one_corner_do_not_overwrite(self):
        ref = ref_of([ac_ref_row(vdd=1.62, gain=60.0, iq=6.0e-5), ac_ref_row(vdd=1.98, gain=70.0, iq=7.0e-5)])
        a, b = cc_rows(vdd=1.62, gain=60.0, iq=6.0e-5), cc_rows(vdd=1.98, gain=70.0, iq=7.0e-5)
        cc = pvt.crosscheck(ref, [a[0], b[0]], [a[1], b[1]])
        self.assertEqual((cc["cmrr_points_compared"], cc["icmr_points_compared"]), (2, 2))
        self.assertTrue(cc["ok"] and cc["all_points_matched"])
        # a last-write-wins index would pair 1.62 V with the 1.98 V reference and fail
        bad = pvt.crosscheck(ref, [cc_rows(vdd=1.62, gain=70.0)[0]], [])
        self.assertFalse(bad["ok"])

    def test_missing_reference_point_is_diagnosed_not_agreement(self):
        ref = ref_of([ac_ref_row(vdd=1.8)])
        ok_cm, ok_ic = cc_rows(vdd=1.8)
        miss_cm, miss_ic = cc_rows(vdd=1.98)
        cc = pvt.crosscheck(ref, [ok_cm, miss_cm], [ok_ic, miss_ic])
        self.assertEqual((cc["cmrr_points_compared"], cc["cmrr_points_unmatched"]), (1, 1))
        self.assertEqual((cc["icmr_points_compared"], cc["icmr_points_unmatched"]), (1, 1))
        self.assertFalse(cc["all_points_matched"])
        self.assertTrue(cc["ok"])  # the valid pair is kept, not discarded
        self.assertTrue(any("no reference point" in d and "1.98" in d for d in cc["diagnostics"]))
        only_missing = pvt.crosscheck(ref, [miss_cm], [miss_ic])
        self.assertIsNone(only_missing["ok"])

    def test_duplicate_reference_points_are_not_resolved(self):
        ref = ref_of([ac_ref_row(gain=66.0), ac_ref_row(gain=50.0)])
        cm, ic = cc_rows()
        cc = pvt.crosscheck(ref, [cm], [ic])
        self.assertEqual(cc["cmrr_points_compared"], 0)
        self.assertIsNone(cc["ok"])
        self.assertTrue(any("duplicate" in d for d in cc["diagnostics"]))

    def test_common_mode_mismatch_is_unmatched(self):
        ref = ref_of([ac_ref_row(vcm=0.5)])
        cm, ic = cc_rows()
        cc = pvt.crosscheck(ref, [cm], [ic])
        self.assertEqual(cc["cmrr_points_compared"], 0)
        self.assertTrue(any("common-mode mismatch" in d for d in cc["diagnostics"]))

    def test_pm_table_does_not_guess_between_supplies(self):
        ac = [{"corner": "tt", "temp_c": "27", "vdd_v": v, "phase_margin_deg": "60"} for v in ("1.62", "1.98")]
        step = [{"corner": "tt", "temp_c": 27.0, "overshoot_pct": 9.0, "settle_1pct_ns": 1.0}]
        tab = pvt.pm_overshoot_table(ac, step)
        self.assertIsNone(tab[0]["agrees"])
        self.assertEqual(tab[0]["reference_status"], "ambiguous_supply")
        dup = pvt.pm_overshoot_table(ac + [ac[0]], [dict(step[0], vdd_v=1.62)])
        self.assertEqual(dup[0]["reference_status"], "duplicate_reference")
        self.assertEqual(pvt.pm_overshoot_summary(dup)["points_without_ac_reference"], ["tt/27C/1.62V (duplicate_reference)"])


def synthetic_step(vdd=1.8, zeta=0.5, wn=2 * math.pi * 20e6, v_ofs=0.0, t_stop=pvt.STEP_T_STOP_S, dt=0.25e-9,
                   gain=1.0):
    """v(out) of a closed-loop second-order system for the +-20 mV step at
    T_DELAY (instant edge), on a uniform time axis. zeta >= 1 -> overdamped
    (zeta == 1 handled as the critically damped form)."""
    lo = 0.5 * vdd - pvt.STEP_HALF_V + v_ofs
    t, v = [], []
    n = int(round(t_stop / dt))
    for i in range(n + 1):
        ti = i * dt
        x = ti - pvt.STEP_T_DELAY_S
        if x <= 0:
            y = 0.0
        elif zeta < 1:
            wd = wn * math.sqrt(1 - zeta ** 2)
            y = 1 - math.exp(-zeta * wn * x) * (math.cos(wd * x) + zeta / math.sqrt(1 - zeta ** 2) * math.sin(wd * x))
        else:
            y = 1 - math.exp(-wn * x) * (1 + wn * x)
        t.append(ti)
        v.append(lo + gain * pvt.STEP_V * y)
    return t, v


class StepMetricsTests(unittest.TestCase):
    def test_template_renders_with_no_unrendered_placeholders(self):
        req, body, tag = klt_request("tran_step")
        live = "\n".join(ln for ln in body.splitlines() if not ln.lstrip().startswith("*")) + "\n"
        self.assertNotRegex(live, r"\{[A-Za-z_]")
        self.assertEqual(tag, "tran-step")
        self.assertEqual(req["analysis"]["kind"], "tran")
        self.assertEqual(req["corners"]["supply_v"]["vdd"], [1.62, 1.8, 1.98])
        self.assertIn("Rshort inn out", body)
        self.assertEqual({m["name"] for m in req["measurements"]},
                         {"v_init", "v_ofs", "v_final", "v_peak", "t_lo_cross", "t_hi_cross"})

    def test_underdamped_overshoot_matches_analytic(self):
        for zeta in (0.3, 0.5, 0.7):
            with self.subTest(zeta=zeta):
                t, v = synthetic_step(zeta=zeta)
                m = pvt.analyze_waveform(t, v, 1.8)
                want = 100 * math.exp(-math.pi * zeta / math.sqrt(1 - zeta ** 2))
                self.assertAlmostEqual(m["overshoot_pct"], want, delta=0.3)
                self.assertGreater(m["settle_1pct_s"], 0)
                self.assertLess(m["settle_1pct_s"], pvt.STEP_T_STOP_S)

    def test_settling_time_is_the_last_exit_from_the_band(self):
        t, v = synthetic_step(zeta=0.5)
        m = pvt.analyze_waveform(t, v, 1.8)
        centre = 0.5 * 1.8 + pvt.STEP_HALF_V
        last_out = max(ti for ti, x in zip(t, v) if abs(x - centre) > pvt.STEP_TOL_V)
        self.assertAlmostEqual(m["settle_1pct_s"], last_out - pvt.STEP_EDGE_MID_S, delta=1e-9)

    def test_static_offset_is_not_counted_as_overshoot_or_settling_error(self):
        a = pvt.analyze_waveform(*synthetic_step(zeta=0.5), 1.8)
        b = pvt.analyze_waveform(*synthetic_step(zeta=0.5, v_ofs=-0.3e-3), 1.8)
        self.assertAlmostEqual(a["overshoot_pct"], b["overshoot_pct"], delta=0.15)
        self.assertAlmostEqual(a["settle_1pct_s"], b["settle_1pct_s"], delta=2e-9)

    def test_overdamped_has_zero_overshoot_as_a_real_measurement(self):
        m = pvt.analyze_waveform(*synthetic_step(zeta=1.0), 1.8)
        self.assertEqual(m["overshoot_pct"], 0.0)
        self.assertGreater(m["settle_1pct_s"], 0)

    def test_non_settling_runs_fail_rather_than_report_zero(self):
        # undamped ringing never enters the band; a very slow pole is still outside it at the window end
        for kw in ({"zeta": 0.001}, {"zeta": 1.0, "wn": 2 * math.pi * 0.2e6}):
            with self.subTest(**kw):
                with self.assertRaises(sh.HarnessError):
                    pvt.analyze_waveform(*synthetic_step(**kw), 1.8)
        with self.assertRaisesRegex(sh.HarnessError, "non-settling"):  # slow pole: window ends outside the band
            pvt.analyze_waveform(*synthetic_step(zeta=1.0, wn=2 * math.pi * 0.2e6), 1.8)

    def test_failed_measurements_are_errors_not_zeros(self):
        good = {"v_init": 0.88, "v_ofs": 0.0, "v_final": 0.92, "v_peak": 0.9216, "t_lo_cross": 2.1e-7, "t_hi_cross": 2.3e-7}
        self.assertGreater(pvt.step_metrics(good, 1.8)["overshoot_pct"], 0)
        for key in ("v_init", "v_ofs", "v_final", "v_peak", "t_lo_cross"):
            with self.subTest(missing=key):
                with self.assertRaisesRegex(sh.HarnessError, "missing"):
                    pvt.step_metrics({k: v for k, v in good.items() if k != key}, 1.8)
        with self.assertRaisesRegex(sh.HarnessError, "non-finite"):
            pvt.step_metrics(dict(good, v_peak=float("nan")), 1.8)
        with self.assertRaisesRegex(sh.HarnessError, "step not seen"):
            pvt.step_metrics(dict(good, v_final=0.88), 1.8)
        with self.assertRaisesRegex(sh.HarnessError, "inconsistent"):
            pvt.step_metrics({k: v for k, v in good.items() if k != "t_hi_cross"} | {"v_peak": 0.95}, 1.8)
        with self.assertRaisesRegex(sh.HarnessError, "tran_step"):
            pvt.tran_step_row("tt", 27.0, {"values": {}, "status": "error", "runtime_s": 1.0})

    def test_row_matches_fieldnames(self):
        good = {"v_init": 0.88, "v_ofs": 0.0, "v_final": 0.92, "v_peak": 0.9216, "t_lo_cross": 2.1e-7, "t_hi_cross": 2.3e-7}
        row = pvt.tran_step_row("tt", 27.0, {"values": good, "status": "pass", "runtime_s": 2.0})
        self.assertEqual(set(row), set(pvt.FIELDNAMES["tran_step"]))
        self.assertAlmostEqual(row["overshoot_pct"], 4.0, places=6)

    def test_pm_to_overshoot_known_points(self):
        self.assertAlmostEqual(pvt.pm_to_overshoot_pct(65.24), 100 * math.exp(-math.pi * 0.7 / math.sqrt(1 - 0.49)), delta=0.15)
        self.assertAlmostEqual(pvt.pm_to_overshoot_pct(60.0), 8.8, delta=0.3)
        self.assertEqual(pvt.pm_to_overshoot_pct(80.0), 0.0)
        self.assertGreater(pvt.pm_to_overshoot_pct(40.0), pvt.pm_to_overshoot_pct(60.0))

    def test_pm_overshoot_table_flags_disagreement_and_missing_reference(self):
        pm = 60.0
        want = pvt.pm_to_overshoot_pct(pm)
        ac = [{"corner": "tt", "temp_c": "27.0", "phase_margin_deg": str(pm)},
              {"corner": "ss", "temp_c": "27.0", "phase_margin_deg": str(pm)}]
        step = [{"corner": "tt", "temp_c": 27.0, "overshoot_pct": want + 1.0, "settle_1pct_ns": 30.0},
                {"corner": "ss", "temp_c": 27.0, "overshoot_pct": want + 12.0, "settle_1pct_ns": 30.0},
                {"corner": "ff", "temp_c": 27.0, "overshoot_pct": 1.0, "settle_1pct_ns": 30.0}]
        tab = pvt.pm_overshoot_table(ac, step)
        self.assertEqual([r["agrees"] for r in tab], [True, False, None])
        summ = pvt.pm_overshoot_summary(tab)
        self.assertEqual(summ["points_disagreeing"], ["ss/27C"])
        self.assertEqual(summ["points_with_ac_reference"], 2)


class CartesianSupplyTests(unittest.TestCase):
    """Issue #110: opt-in independent-supply mode; paired stays the default."""

    CORNERS = list(pvt.DEFAULT_CORNERS)
    TEMPS = [-40.0, 27.0, 125.0]

    def test_paired_is_default_and_reproduces_historical_tuples(self):
        self.assertEqual(pvt.DEFAULT_SUPPLY_MODE, "paired")
        pts = pvt.supply_points(self.CORNERS, self.TEMPS)
        self.assertEqual(len(pts), 15)
        self.assertEqual({(c, t) for c, t, _ in pts}, {(c, t) for c in self.CORNERS for t in self.TEMPS})
        for c, _t, v in pts:
            self.assertEqual(v, pvt.VDD_BY_CORNER[c])
        self.assertEqual(pvt.parse_args([]).supply_mode, "paired")

    def test_paired_request_exclusions_unchanged(self):
        vdds, ex = pvt.vdd_pairing(self.CORNERS)
        self.assertEqual(vdds, [1.62, 1.8, 1.98])
        self.assertEqual(len(ex), 10)
        self.assertEqual(ex, pvt.vdd_pairing(self.CORNERS, "paired")[1])
        req, _b, tag = klt_request("cmrr", "mid")
        self.assertEqual(tag, "cmrr-mid")
        self.assertEqual(len(req["exclude"]), 10)

    def test_cartesian_emits_45_unique_tuples_per_analysis(self):
        pts = pvt.supply_points(self.CORNERS, self.TEMPS, "cartesian")
        self.assertEqual(len(pts), 45)
        self.assertEqual(len(set(pts)), 45)
        self.assertEqual({v for _c, _t, v in pts}, {1.62, 1.8, 1.98})
        # every process sees both supply extremes at every temperature
        for c in self.CORNERS:
            for t in self.TEMPS:
                self.assertEqual({v for cc, tt, v in pts if (cc, tt) == (c, t)}, {1.62, 1.8, 1.98})

    def test_cartesian_subsets(self):
        pts = pvt.supply_points(["ss", "ff"], [27.0], "cartesian", [1.98, 1.62])
        self.assertEqual(pts, [("ss", 27.0, 1.62), ("ss", 27.0, 1.98), ("ff", 27.0, 1.62), ("ff", 27.0, 1.98)])
        with self.assertRaises(ValueError):
            pvt.supply_values(self.CORNERS, "cartesian", [])
        with self.assertRaises(ValueError):
            pvt.supply_values(self.CORNERS, "bogus")

    def test_artifact_names_unique_per_point(self):
        for mode, n in (("paired", 15), ("cartesian", 45)):
            pts = pvt.supply_points(self.CORNERS, self.TEMPS, mode)
            names = {pvt.point_tag("ac", c, t, v, mode) for c, t, v in pts}
            self.assertEqual(len(names), n, mode)
        self.assertEqual(pvt.point_tag("ac", "tt", 27.0, 1.8, "paired"), "ac-tt-27C")
        self.assertNotEqual(pvt.point_tag("ac", "tt", 27.0, 1.62, "cartesian"),
                            pvt.point_tag("ac", "tt", 27.0, 1.98, "cartesian"))

    def test_cartesian_request_has_all_supplies_and_no_exclusions(self):
        with tempfile.TemporaryDirectory() as d:
            path, tag = pvt.build_klt_request("cmrr", "mid", None, FakeKltPdk(), self.CORNERS, self.TEMPS,
                                              Path(d), "batch", "cartesian", None)
            req = json.loads(path.read_text())
        self.assertEqual(tag, "cmrr-mid")
        self.assertEqual(req["corners"]["supply_v"]["vdd"], [1.62, 1.8, 1.98])
        self.assertNotIn("exclude", req)

    def test_cartesian_icmr_requests_are_per_process_and_supply(self):
        with tempfile.TemporaryDirectory() as d:
            tags = set()
            for v in (1.62, 1.8, 1.98):
                path, tag = pvt.build_klt_request("icmr", None, v, FakeKltPdk(), ["tt"], self.TEMPS,
                                                  Path(d), "batch", "cartesian", None)
                tags.add(tag)
                req = json.loads(path.read_text())
                self.assertEqual(req["corners"]["supply_v"]["vdd"], [v])
                meas = {m["name"]: m["spice"] for m in req["measurements"]}
                self.assertIn(f"at={0.5 * v:g}", meas["vid_mid_v"])
        self.assertEqual(tags, {"icmr-tt-1.62V", "icmr-tt-1.8V", "icmr-tt-1.98V"})

    def test_corner_values_do_not_collide_across_supplies(self):
        rep = {"corners": [
            {"process": "tt", "temperature_c": 27, "supply_v": {"vdd": v}, "status": "pass",
             "runtime_s": 1.0, "measurements": [{"name": "a", "value": v}]} for v in (1.62, 1.8, 1.98)]}
        got = pvt._corner_values(rep, by_supply=True)
        self.assertEqual(len(got), 3)
        self.assertEqual([got[("tt", 27.0, v)]["values"]["a"] for v in (1.62, 1.8, 1.98)], [1.62, 1.8, 1.98])
        self.assertEqual(len(pvt._corner_values(rep)), 1)  # legacy keying would overwrite

    def test_rows_use_actual_point_voltage(self):
        vals = {"gbw_hz": 1e7}
        for label, _f in pvt.CMRR_SPOTS:
            vals[f"adm_{label}_db"], vals[f"acm_{label}_db"] = 70.0, -3.0
        row = pvt.cmrr_row("tt", 27.0, {"values": vals, "status": "pass", "runtime_s": 1.0}, "mid", 1.98)
        self.assertEqual(row["vdd_v"], 1.98)
        self.assertAlmostEqual(row["vcm_v"], 0.99)
        row = pvt.cmrr_row("tt", 27.0, {"values": vals, "status": "pass", "runtime_s": 1.0}, "mid")
        self.assertEqual(row["vdd_v"], 1.8)  # default still the paired voltage

    def test_local_stimuli_use_point_voltage(self):
        captured = []

        def fake_run(ngspice, deck_text, workdir, log_path, timeout_s=120):
            captured.append(deck_text)
            return "iq_a=1e-5\npq_w=1e-5\ngain_dc_db=60\ngbw_hz=1e6\nphase_at_gbw_rad=-2\n" \
                   "sr_rise_s=1e-8\nsr_fall_s=1e-8\n", 0.1

        real = pvt.run_ngspice
        pvt.run_ngspice = fake_run
        try:
            with tempfile.TemporaryDirectory() as d:
                row, deck = pvt.run_ac(FakePdk(), "ngspice", "ss", 27.0, Path(d), Path(d) / "l", vdd=1.98)
                self.assertEqual((row["vdd_v"], row["vcm_v"]), (1.98, 0.99))
                self.assertIn("1.98", deck)
                row, _deck = pvt.run_tran_sr(FakePdk(), "ngspice", "ss", 27.0, Path(d), Path(d) / "l", vdd=1.98)
                self.assertAlmostEqual(row["v_low_v"], 0.3 * 1.98)
                self.assertAlmostEqual(row["v_high_v"], 0.7 * 1.98)
                row, _deck = pvt.run_ac(FakePdk(), "ngspice", "ss", 27.0, Path(d), Path(d) / "l")
                self.assertEqual(row["vdd_v"], 1.62)  # omitted -> paired mapping
        finally:
            pvt.run_ngspice = real

    def test_pm_overshoot_table_distinguishes_supplies(self):
        ac = [{"corner": "tt", "temp_c": "27", "vdd_v": v, "phase_margin_deg": pm}
              for v, pm in (("1.62", "50"), ("1.98", "70"))]
        step = [{"corner": "tt", "temp_c": 27.0, "vdd_v": v,
                 "overshoot_pct": pvt.pm_to_overshoot_pct(pm), "settle_1pct_ns": 1.0}
                for v, pm in ((1.62, 50.0), (1.98, 70.0))]
        tab = pvt.pm_overshoot_table(ac, step)
        self.assertEqual([r["agrees"] for r in tab], [True, True])
        self.assertEqual([r["vdd_v"] for r in tab], [1.62, 1.98])

    def test_cli_defaults_and_flags(self):
        a = pvt.parse_args(["--supply-mode", "cartesian", "--supplies", "1.62,1.98"])
        self.assertEqual((a.supply_mode, a.supplies), ("cartesian", "1.62,1.98"))
        self.assertEqual(pvt.parse_args([]).supplies, "1.62,1.8,1.98")

    def _run_cmrr_campaign(self, mode, drop=None):
        names = ["gbw_hz"] + [f"{p}_{label}_db" for label, _f in pvt.CMRR_SPOTS for p in ("adm", "acm")]

        def fake_klt(req_path, out_dir, backend):
            req = json.loads(Path(req_path).read_text())
            excl = {(e["process"], e["supply_v"]["vdd"]) for e in req.get("exclude", [])}
            units = []
            for c in req["corners"]["process"]:
                for t in req["corners"]["temperature_c"]:
                    for v in req["corners"]["supply_v"]["vdd"]:
                        if (c, v) in excl or (c, t, v) == drop:
                            continue
                        units.append({"process": c, "temperature_c": t, "supply_v": {"vdd": v},
                                      "status": "pass", "runtime_s": 1.0, "diagnostics": [],
                                      "measurements": [{"name": n, "value": 1.0} for n in names]})
            return {"status": "pass", "corner_count": len(units), "corners": units, "environment": {}}

        real = pvt.run_klt_sim
        pvt.run_klt_sim = fake_klt
        results, errors, jobs = {"cmrr": []}, [], []
        try:
            with tempfile.TemporaryDirectory() as d:
                snap, logs = Path(d) / "snap", Path(d) / "logs"
                snap.mkdir()
                logs.mkdir()
                pvt.run_klt_analyses(["cmrr"], FakeKltPdk(), self.CORNERS, self.TEMPS, "batch",
                                     Path(d) / "req", logs, snap, results, errors, jobs, mode, None)
        finally:
            pvt.run_klt_sim = real
        return results["cmrr"], errors

    def test_aggregation_completeness_cartesian(self):
        rows, errors = self._run_cmrr_campaign("cartesian")
        self.assertEqual(errors, [])
        for cm in pvt.CMRR_CM_POINTS:
            keys = [(r["corner"], r["temp_c"], r["vdd_v"]) for r in rows if r["cm_point"] == cm]
            self.assertEqual(len(keys), 45)
            self.assertEqual(set(keys), set(pvt.supply_points(self.CORNERS, self.TEMPS, "cartesian")))

    def test_aggregation_reports_missing_point_explicitly(self):
        rows, errors = self._run_cmrr_campaign("cartesian", drop=("ss", -40.0, 1.62))
        self.assertEqual(len(rows), 2 * 44)
        self.assertEqual(len(errors), 2)
        self.assertTrue(all("ss-" in e and "1.62V" in e and "not in the klt response" in e for e in errors))

    def test_aggregation_paired_unchanged(self):
        rows, errors = self._run_cmrr_campaign("paired")
        self.assertEqual(errors, [])
        self.assertEqual(len(rows) // len(pvt.CMRR_CM_POINTS), 15)
        self.assertTrue(all(r["vdd_v"] == pvt.VDD_BY_CORNER[r["corner"]] for r in rows))


class FleetAnalysisTests(unittest.TestCase):
    """Issue #77: ac / tran_sr / dc_swing as klt (fleet) requests. Simulator-free:
    run_klt_sim is mocked and subprocess.run is armed to fail the test."""

    CORNERS = list(pvt.DEFAULT_CORNERS)
    TEMPS = [-40.0, 27.0, 125.0]
    AC_NAMES = ["gain_dc_db", "gbw_hz", "phase_at_gbw_rad"]

    # -- request construction ------------------------------------------------
    def test_bodies_are_klt_bodies_without_placeholders_or_solver_overrides(self):
        for a in pvt.FLEET_ANALYSES:
            with self.subTest(analysis=a):
                req, body, tag = klt_request(a)
                live = "\n".join(ln for ln in body.splitlines() if not ln.lstrip().startswith("*")) + "\n"
                self.assertNotRegex(live, r"\{[A-Za-z_]")
                for forbidden in (".control", ".end\n", ".lib", ".temp", "wrdata"):
                    self.assertNotIn(forbidden, live)
                # DR-006: no tolerance override in the body or the request
                self.assertNotRegex(live + json.dumps(req), r"(?i)reltol|abstol|vntol|\.options?\s+(?!scale)")
                self.assertIn('.include "opamp_core.spice"', live)
                self.assertEqual(req["backend"], "batch")

    def test_request_shapes(self):
        ac, _b, tag = klt_request("ac")
        self.assertEqual((tag, ac["analysis"]), ("ac", {"kind": "ac", "args": "dec 20 1 1g"}))
        iq, _b, tag = klt_request("ac_iq")
        self.assertEqual((tag, iq["analysis"]["kind"]), ("ac-iq", "dc"))
        self.assertEqual([m["name"] for m in iq["measurements"]], ["i_vdd_a"])
        # klt 0.5.0 runner compatibility: `.meas` cards only, no expr / analysis_steps
        for r in (ac, iq, klt_request("tran_sr")[0], klt_request("dc_swing")[0]):
            self.assertNotIn("analysis_steps", r)
            self.assertTrue(all("spice" in m and "expr" not in m for m in r["measurements"]))
        sr, _b, tag = klt_request("tran_sr")
        self.assertEqual((tag, sr["analysis"]), ("tran-sr", {"kind": "tran", "args": "2n 2.2u"}))
        self.assertEqual({m["name"] for m in sr["measurements"]}, {"t20_rise", "t80_rise", "t80_fall", "t20_fall"})
        dc, body, tag = klt_request("dc_swing")
        self.assertEqual((tag, dc["analysis"]["kind"]), ("dc-swing", "dc"))
        self.assertTrue(dc["options"]["waveforms"])
        self.assertTrue(dc["options"]["keep_artifacts"])
        self.assertNotIn("waveforms", klt_request("tran_sr")[0]["options"])
        self.assertAlmostEqual(float(dc["analysis"]["args"].split()[-1]), 1 / 360, places=10)
        end = float(dc["analysis"]["args"].split()[2])
        self.assertTrue(1.0 < end < 1.0 + 1 / 360)  # reaches the k=360 (VDD) point, adds no 361st

    def test_paired_five_by_three_matrix_and_supply_pairing(self):
        for a in pvt.FLEET_ANALYSES:
            req, _b, _t = klt_request(a, temps=self.TEMPS)
            self.assertEqual(req["corners"]["temperature_c"], self.TEMPS)
            keep = {(c, v) for c in req["corners"]["process"] for v in req["corners"]["supply_v"]["vdd"]}
            for ex in req["exclude"]:
                keep.discard((ex["process"], ex["supply_v"]["vdd"]))
            self.assertEqual(keep, {(c, pvt.VDD_BY_CORNER[c]) for c in self.CORNERS}, a)

    def test_cartesian_request_has_no_exclusions(self):
        for a in pvt.FLEET_ANALYSES:
            with tempfile.TemporaryDirectory() as d:
                path, _tag = pvt.build_klt_request(a, None, None, FakeKltPdk(), self.CORNERS, self.TEMPS,
                                                   Path(d), "batch", "cartesian", None)
                req = json.loads(path.read_text())
            self.assertNotIn("exclude", req)
            self.assertEqual(req["corners"]["supply_v"]["vdd"], [1.62, 1.8, 1.98])

    def test_selected_netlist_is_what_the_request_includes(self):
        with tempfile.TemporaryDirectory() as d:
            cand = Path(d) / "cand.spice"
            cand.write_text("* candidate\nM1 out inp vss vss sky130_fd_pr__nfet_01v8 w=1 l=1\n")
            real = pvt.ACTIVE_DUT[0]
            pvt.ACTIVE_DUT[0] = cand
            try:
                with tempfile.TemporaryDirectory() as r:
                    pvt.build_klt_request("ac", None, None, FakeKltPdk(), ["tt"], [27.0], Path(r), "batch")
                    self.assertEqual((Path(r) / pvt.dut_identity.SNAPSHOT_NAME).read_text(), cand.read_text())
            finally:
                pvt.ACTIVE_DUT[0] = real

    # -- row builders --------------------------------------------------------
    def test_ac_row_matches_local_definitions(self):
        vals = {"gain_dc_db": 90.0, "gbw_hz": 1e7, "phase_at_gbw_rad": math.radians(-110.0)}
        iq = {"values": {"i_vdd_a": -6e-5}, "status": "pass", "runtime_s": 1.0}
        row = pvt.ac_row("tt", 27.0, {"values": vals, "status": "pass", "runtime_s": 3.0}, None, iq)
        self.assertEqual(set(row), set(pvt.FIELDNAMES["ac"]))
        self.assertAlmostEqual(row["phase_margin_deg"], 70.0)
        self.assertAlmostEqual(row["vcm_v"], 0.9)
        self.assertAlmostEqual(row["iq_a"], 6e-5)
        self.assertAlmostEqual(row["pq_w"], 6e-5 * 1.8)
        self.assertAlmostEqual(row["elapsed_s"], 4.0)
        for k in self.AC_NAMES:
            bad = {x: y for x, y in vals.items() if x != k}
            with self.assertRaises(sh.HarnessError):
                pvt.ac_row("tt", 27.0, {"values": bad, "status": "pass", "runtime_s": 1.0}, None, iq)
        with self.assertRaises(sh.HarnessError):  # NaN is not a passing number
            pvt.ac_row("tt", 27.0, {"values": dict(vals, gbw_hz=float("nan")), "status": "pass", "runtime_s": 1.0},
                       None, iq)
        info = {"values": vals, "status": "pass", "runtime_s": 1.0}
        with self.assertRaises(sh.HarnessError):  # no Iq companion unit
            pvt.ac_row("tt", 27.0, info, None, None)
        with self.assertRaises(sh.HarnessError):  # Iq companion without its measurement
            pvt.ac_row("tt", 27.0, info, None, {"values": {}, "status": "pass", "runtime_s": 1.0})

    def test_tran_sr_row_matches_local_definition(self):
        vals = {"t20_rise": 1e-7, "t80_rise": 1.5e-7, "t80_fall": 5e-7, "t20_fall": 5.6e-7}
        row = pvt.tran_sr_row("ff", 27.0, {"values": vals, "status": "pass", "runtime_s": 1.0})
        self.assertEqual(set(row), set(pvt.FIELDNAMES["tran_sr"]))
        span = 0.4 * 1.98
        self.assertAlmostEqual(row["sr_rise_v_per_us"], 0.6 * span / 5e-8 / 1e6)
        self.assertAlmostEqual(row["sr_fall_v_per_us"], 0.6 * span / 6e-8 / 1e6)
        self.assertAlmostEqual(row["v_low_v"], 0.3 * 1.98)
        with self.assertRaises(sh.HarnessError):
            pvt.tran_sr_row("ff", 27.0, {"values": dict(vals, t80_fall=None), "status": "pass", "runtime_s": 1.0})
        with self.assertRaises(sh.HarnessError):  # crossings out of order
            pvt.tran_sr_row("ff", 27.0, {"values": dict(vals, t80_rise=5e-8), "status": "pass", "runtime_s": 1.0})

    @staticmethod
    def follower_sweep(vdd, lo=0.15, hi=0.2):
        n = pvt.SWING_POINTS
        vin = [vdd * k / n for k in range(n + 1)]
        vout = [min(max(v, lo), vdd - hi) for v in vin]
        return vin, vout

    @staticmethod
    def write_waveform(path, vin, vout):
        path.write_text(json.dumps({
            "plotname": "DC transfer characteristic",
            "variables": [{"index": 0, "name": "v(sw)"}, {"index": 1, "name": "v(inp)"}, {"index": 2, "name": "v(out)"}],
            "points": [[a / 1.8, a, b] for a, b in zip(vin, vout)]}))
        return str(path)

    def test_dc_swing_row_from_waveform_equals_shared_rule(self):
        vin, vout = self.follower_sweep(1.8)
        with tempfile.TemporaryDirectory() as d:
            wf = self.write_waveform(Path(d) / "w.json", vin, vout)
            info = {"artifacts": {"waveform": wf}, "status": "pass", "runtime_s": 2.0, "values": {}}
            row = pvt.dc_swing_row("tt", 27.0, info)
        self.assertEqual(set(row), set(pvt.FIELDNAMES["dc_swing"]))
        ref = pvt.swing_row("tt", 27.0, 1.8, vin, vout)
        for k, v in ref.items():
            self.assertEqual(row[k], v)
        self.assertAlmostEqual(row["vout_min_v"], 0.15, delta=1.8 / 360)
        self.assertAlmostEqual(row["vout_max_v"], 1.6, delta=1.8 / 360)

    def test_dc_swing_failures_are_errors(self):
        vin, vout = self.follower_sweep(1.8)
        with tempfile.TemporaryDirectory() as d:
            ok = self.write_waveform(Path(d) / "w.json", vin, vout)
            short = self.write_waveform(Path(d) / "s.json", vin[:20], vout[:20])
            trunc = self.write_waveform(Path(d) / "t.json", vin[:250], vout[:250])
            junk = Path(d) / "j.json"
            junk.write_text("{not json")
            wrong_supply = ok
            for label, wf in (("missing", str(Path(d) / "none.json")), ("none", None), ("short", short),
                              ("junk", str(junk))):
                with self.subTest(label), self.assertRaises(sh.HarnessError):
                    pvt.dc_swing_row("tt", 27.0, {"artifacts": {"waveform": wf}, "status": "pass", "runtime_s": 1.0})
            with self.assertRaises(sh.HarnessError):  # sweep does not reach this corner's VDD
                pvt.dc_swing_row("ff", 27.0, {"artifacts": {"waveform": trunc}, "status": "pass", "runtime_s": 1.0})
            with self.assertRaises(sh.HarnessError):  # 1.8 V sweep presented as the 1.98 V corner
                pvt.dc_swing_row("ff", 27.0, {"artifacts": {"waveform": wrong_supply}, "status": "pass", "runtime_s": 1.0})

    # -- campaigns against mocked responses ---------------------------------
    def _fake_klt(self, d, calls=None, mutate=None, env=None):
        """A run_klt_sim stand-in answering from the request (see _campaign)."""
        d = Path(d)
        calls = [] if calls is None else calls

        def fake_klt(req_path, out_dir, bk):
            Path(out_dir).mkdir(parents=True, exist_ok=True)  # klt creates its outdir
            req = json.loads(Path(req_path).read_text())
            calls.append((req, bk))
            kind = req["netlist"].split("-body")[0]  # ac / ac-iq / tran-sr / dc-swing
            kind = {"ac": "ac", "ac-iq": "ac_iq", "tran-sr": "tran_sr", "dc-swing": "dc_swing"}[kind]
            excl = {(e["process"], e["supply_v"]["vdd"]) for e in req.get("exclude", [])}
            units = []
            for c in req["corners"]["process"]:
                for t in req["corners"]["temperature_c"]:
                    for v in req["corners"]["supply_v"]["vdd"]:
                        if (c, v) in excl:
                            continue
                        unit = {"process": c, "temperature_c": t, "supply_v": {"vdd": v}, "status": "pass",
                                "runtime_s": 1.5, "diagnostics": [], "artifacts": {},
                                "measurements": self._measurements(kind, v)}
                        if kind == "dc_swing":
                            vin, vout = self.follower_sweep(v)
                            unit["artifacts"]["waveform"] = self.write_waveform(
                                d / f"wf-{c}-{t:g}-{v:g}.json", vin, vout)
                        if mutate:
                            unit = mutate(kind, unit)
                            if unit is None:
                                continue
                        units.append(unit)
            return {"status": "pass", "corner_count": len(units), "corners": units,
                    "environment": {"remote": {"provider": "aws-batch-fleet", "job_id": "j"}} if env is None else env}
        return fake_klt

    def _campaign(self, analyses, mode="paired", mutate=None, backend="batch", env=None, tmp=None):
        """Run run_klt_analyses with a mocked fleet. `mutate(analysis, unit)` may edit/return None to drop."""
        d = Path(tmp)
        calls = []
        fake_klt = self._fake_klt(d, calls, mutate, env)
        results, errors, jobs = {a: [] for a in analyses}, [], []
        snap, logs = d / "snap", d / "logs"
        snap.mkdir()
        logs.mkdir()
        real = pvt.run_klt_sim
        pvt.run_klt_sim = fake_klt
        try:
            pvt.run_klt_analyses(analyses, FakeKltPdk(), self.CORNERS, self.TEMPS, backend, d / "req", logs, snap,
                                 results, errors, jobs, mode, None)
        finally:
            pvt.run_klt_sim = real
        return results, errors, jobs, calls

    @staticmethod
    def _measurements(kind, vdd):
        if kind == "ac":
            vals = {"gain_dc_db": 90.0, "gbw_hz": 1e7, "phase_at_gbw_rad": math.radians(-110.0)}
        elif kind == "ac_iq":
            vals = {"i_vdd_a": -6e-5}
        elif kind == "tran_sr":
            vals = {"t20_rise": 1e-7, "t80_rise": 1.5e-7, "t80_fall": 5e-7, "t20_fall": 5.6e-7}
        else:
            vals = {"vout_mid_v": 0.5 * vdd}
        return [{"name": k, "value": v} for k, v in vals.items()]

    def _armed(self):
        """Fail the test if anything tries to start a local simulator subprocess."""
        import subprocess
        from unittest import mock

        def boom(*a, **k):
            raise AssertionError(f"local subprocess invoked: {a[:1]}")
        return mock.patch.object(subprocess, "run", boom)

    def test_paired_campaign_accounts_for_all_45_units_without_local_sim(self):
        with tempfile.TemporaryDirectory() as d, self._armed():
            results, errors, jobs, calls = self._campaign(list(pvt.FLEET_ANALYSES), tmp=d)
        self.assertEqual(errors, [])
        self.assertEqual({a: len(r) for a, r in results.items()}, {a: 15 for a in pvt.FLEET_ANALYSES})
        self.assertEqual(sum(len(r) for r in results.values()), 45)
        self.assertEqual(len(calls), 4)  # ac-iq (Iq companion), ac, tran-sr, dc-swing
        self.assertTrue(all(bk == "batch" for _r, bk in calls))
        for a, rows in results.items():
            self.assertEqual({(r["corner"], r["temp_c"], r["vdd_v"]) for r in rows},
                             set(pvt.supply_points(self.CORNERS, self.TEMPS)), a)
            self.assertTrue(all(set(r) == set(pvt.FIELDNAMES[a]) for r in rows))
        self.assertTrue(all(j["remote"]["job_id"] == "j" for j in jobs))  # remote provenance kept

    def test_cartesian_result_keys_unique_for_several_supplies(self):
        with tempfile.TemporaryDirectory() as d, self._armed():
            results, errors, _j, calls = self._campaign(list(pvt.FLEET_ANALYSES), "cartesian", tmp=d)
        self.assertEqual(errors, [])
        for a, rows in results.items():
            keys = [(r["corner"], r["temp_c"], r["vdd_v"]) for r in rows]
            self.assertEqual(len(keys), 45, a)
            self.assertEqual(len(set(keys)), 45, a)
            self.assertEqual({v for _c, _t, v in keys}, {1.62, 1.8, 1.98})
        # several supplies at the SAME process/temperature stay distinct rows
        tt27 = [r["vdd_v"] for r in results["tran_sr"] if (r["corner"], r["temp_c"]) == ("tt", 27.0)]
        self.assertEqual(sorted(tt27), [1.62, 1.8, 1.98])

    def test_missing_metric_and_missing_unit_are_failures_not_zeros(self):
        def mutate(kind, u):
            if kind == "ac_iq":
                return u
            if (u["process"], u["temperature_c"]) == ("ss", -40.0):
                return None  # unit absent from the response
            if (u["process"], u["temperature_c"]) == ("tt", 27.0):
                u["measurements"] = u["measurements"][:-1]  # partial output
            return u

        with tempfile.TemporaryDirectory() as d, self._armed():
            results, errors, _j, _c = self._campaign(["ac", "tran_sr"], mutate=mutate, tmp=d)
        for a in ("ac", "tran_sr"):
            self.assertEqual(len(results[a]), 13, a)
        self.assertEqual(len(errors), 4)
        self.assertEqual(sum("not in the klt response" in e for e in errors), 2)
        self.assertEqual(sum("missing measurements" in e for e in errors), 2)

    def test_failed_timeout_units_and_missing_waveform_count_as_failures(self):
        def mutate(kind, u):
            if u["process"] == "ff" and u["temperature_c"] == 125.0:
                u["status"] = "error"
                u["diagnostics"] = [{"severity": "error", "code": "timeout", "message": "corner timed out"}]
            if u["process"] == "sf":
                u["artifacts"] = {"waveform": None}
            return u

        with tempfile.TemporaryDirectory() as d, self._armed():
            results, errors, _j, _c = self._campaign(["dc_swing"], mutate=mutate, tmp=d)
        self.assertEqual(len(results["dc_swing"]), 15 - 1 - 3)
        self.assertEqual(len(errors), 4)
        self.assertTrue(any("timeout" in e for e in errors))
        self.assertEqual(sum("missing waveform" in e for e in errors), 3)

    def test_non_ok_status_without_diagnostics_is_a_failure(self):
        def mutate(kind, u):
            if u["process"] == "tt":
                u["status"] = "error"
            return u

        with tempfile.TemporaryDirectory() as d, self._armed():
            results, errors, _j, _c = self._campaign(["tran_sr"], mutate=mutate, tmp=d)
        self.assertEqual(len(results["tran_sr"]), 12)
        self.assertEqual(len(errors), 3)

    def test_batch_response_without_remote_provenance_is_refused(self):
        with tempfile.TemporaryDirectory() as d, self._armed():
            results, errors, _j, _c = self._campaign(["ac"], env={}, tmp=d)
        self.assertEqual(results["ac"], [])
        self.assertEqual(len(errors), 2)  # the ac request and its ac-iq companion
        self.assertTrue(all("no environment.remote" in e for e in errors))

    def test_capacity_refusal_is_retried_then_reported_never_run_locally(self):
        attempts = []

        def refuse(req_path, out_dir, bk):
            attempts.append(bk)
            raise sh.HarnessError("batch backend failed: ... exceeds BATCH_MAX_CONCURRENT_INSTANCES=8")

        saved = (pvt.run_klt_sim, pvt.CAPACITY_RETRIES, pvt.CAPACITY_WAIT_S)
        pvt.run_klt_sim, pvt.CAPACITY_RETRIES, pvt.CAPACITY_WAIT_S = refuse, 2, 0
        try:
            with tempfile.TemporaryDirectory() as d, self._armed():
                dd = Path(d)
                (dd / "snap").mkdir()
                (dd / "logs").mkdir()
                results, errors, jobs = {"ac": []}, [], []
                pvt.run_klt_analyses(["ac"], FakeKltPdk(), self.CORNERS, self.TEMPS, "batch", dd / "req",
                                     dd / "logs", dd / "snap", results, errors, jobs)
        finally:
            pvt.run_klt_sim, pvt.CAPACITY_RETRIES, pvt.CAPACITY_WAIT_S = saved
        self.assertEqual(attempts, ["batch"] * 6)  # ac-iq and ac, 1 try + 2 retries each
        self.assertEqual(results["ac"], [])
        self.assertIn("BATCH_MAX_CONCURRENT_INSTANCES", errors[0])

    def test_local_ngspice_is_forbidden_for_a_batch_fleet_campaign(self):
        pvt.LOCAL_SIM_FORBIDDEN[0] = True
        try:
            with self.assertRaises(sh.HarnessError):
                pvt.run_ngspice("ngspice", "* deck", Path("/nonexistent"), Path("/nonexistent/log"))
        finally:
            pvt.LOCAL_SIM_FORBIDDEN[0] = False

    def test_cli_fleet_and_netlist_flags(self):
        a = pvt.parse_args([])
        self.assertEqual((a.fleet, a.netlist, a.backend), (False, None, "batch"))
        a = pvt.parse_args(["--fleet", "--netlist", "/x/cand.spice"])
        self.assertEqual((a.fleet, a.netlist), (True, "/x/cand.spice"))

    def test_end_to_end_fleet_record_with_selected_netlist(self):
        """main(): --fleet --netlist writes a 45-unit record, snapshots the INPUT netlist, leaves the
        canonical design untouched and never starts a local simulator."""
        import hashlib
        from unittest import mock

        canon = pvt.DESIGN_NETLIST
        canon_hash = hashlib.sha256(canon.read_bytes()).hexdigest()

        class Pdk:
            matches_pin, variant, root, installed_commit = True, "sky130A", Path("/pdk"), "abc"
            pin = {"open_pdks_commit": "abc"}
            own_pin = {"rc_corner": {"choice": "typical"}}

        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            (root / "cand").mkdir(parents=True)
            cand = root / "cand" / "candidate.spice"
            cand.write_text("* candidate netlist, not the canonical design\n")
            records, snaps = root / "records", root / "snaps"
            patches = [
                mock.patch.object(pvt, "REPO_ROOT", root), mock.patch.object(pvt, "RECORDS_DIR", records),
                mock.patch.object(pvt, "SNAPSHOT_DIR", snaps), mock.patch.object(pvt, "resolve_pdk", lambda: Pdk()),
                mock.patch.object(pvt, "klt_available", lambda: "/bin/klt"),
                mock.patch.object(pvt, "klt_version", lambda: "klt-test"), mock.patch.object(pvt, "git_sha", lambda _r: "abc1234"),
                mock.patch.object(pvt, "run_klt_sim", self._fake_klt(Path(d))),
                mock.patch.object(pvt, "first_line", lambda *_a, **_k: self.fail("ngspice version probed")),
                mock.patch.object(pvt, "ACTIVE_DUT", [canon]),
            ]
            (Path(d) / "dummy").mkdir()
            with self._armed():
                for p in patches:
                    p.start()
                try:
                    rc = pvt.main(["--fleet", "--netlist", str(cand), "--backend", "batch"])
                finally:
                    mock.patch.stopall()
                    pvt.LOCAL_SIM_FORBIDDEN[0] = False
            self.assertEqual(rc, 0)
            rec = json.loads(next(records.glob("*.json")).read_text())
            self.assertEqual(rec["matrix"]["n_failed"], 0)
            self.assertEqual(rec["matrix"]["n_runs"], 45)
            self.assertEqual(rec["matrix"]["execution"]["local_ngspice_analyses"], [])
            self.assertEqual(rec["matrix"]["execution"]["solver_settings"]["policy"], "DR-006")
            self.assertEqual(rec["tools"]["ngspice"], "not invoked (klt/fleet execution)")
            self.assertEqual(rec["dut"]["sha256"], "sha256:" + hashlib.sha256(cand.read_bytes()).hexdigest())
            self.assertEqual((root / rec["dut"]["snapshot_path"]).read_bytes(), cand.read_bytes())
            self.assertTrue(all(j["remote"] and j["backend"] == "batch" for j in rec["klt_jobs"]))
            for a in pvt.FLEET_ANALYSES:
                self.assertEqual(len(list(csv.DictReader((records / Path(rec["links"][f"{a}_csv"]).name).open()))), 15)
        self.assertEqual(hashlib.sha256(canon.read_bytes()).hexdigest(), canon_hash)


if __name__ == "__main__":
    unittest.main()
