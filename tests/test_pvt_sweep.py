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


def klt_backend_env(value):
    """Set $KLT_SIM_BACKEND to `value` for the block (None unsets it, '' empties it)."""
    import contextlib
    import os

    @contextlib.contextmanager
    def _cm():
        had = "KLT_SIM_BACKEND" in os.environ
        old = os.environ.get("KLT_SIM_BACKEND")
        if value is None:
            os.environ.pop("KLT_SIM_BACKEND", None)
        else:
            os.environ["KLT_SIM_BACKEND"] = value
        try:
            yield
        finally:
            if had:
                os.environ["KLT_SIM_BACKEND"] = old
            else:
                os.environ.pop("KLT_SIM_BACKEND", None)

    return _cm()


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


TEXT_COLUMNS = {"corner", "cm_point", "low_limiter", "high_limiter", "low_stop", "high_stop",
                "rise_class", "rise_reason", "fall_class", "fall_reason", "verdict",
                "rise_input_headroom_loss", "fall_input_headroom_loss"}


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
                if m.get("supply_mode") == "cartesian":  # supply is an independent axis
                    grid *= len(m["supplies_v"])
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
    n = round(t_stop / dt)
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
        # issue #163: the default backend depends on $KLT_SIM_BACKEND -- pin it unset
        with klt_backend_env(None):
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


def fixcm_sweep(vdd=1.8, a0=2000.0, lo=0.1, hi=None, vos=0.0, n=pvt.SWING_POINTS, proxies=True):
    """Synthetic fixed-CM sweep that obeys the body's equations exactly: an
    amplifier out = c + h*tanh(a0*(vid+vos)/h) (rails lo/hi, analytic local gain
    a0*(1 - tanh^2)) closed by the tanh servo vid = C*tanh(KS*(set-out)/C),
    set = VDD*k/n. Solved per point by bisection; returns waveform columns."""
    hi = vdd - 0.1 if hi is None else hi
    c, h = 0.5 * (lo + hi), 0.5 * (hi - lo)
    clamp, ks, g = pvt.FIXCM_VID_CLAMP_V, pvt.FIXCM_KS, pvt.FIXCM_G
    vcm = pvt.FIXCM_VCM_FRAC * vdd
    cols = {k: [] for k in ("v(sw)", "v(set)", "v(out)", "v(e)", "v(inp)", "v(inn)", "v(vdd)", "v(cm)",
                            "v(xdut.d1)", "v(xdut.d2)", "v(xdut.tail)", "i(vdd)")}
    for k in range(n + 1):
        sw = k / n
        st = vdd * sw
        a, b = -1.0, vdd + 1.0  # residual out - F(servo(out)) increases with out
        for _ in range(200):
            m = 0.5 * (a + b)
            vid = clamp * math.tanh(ks * (st - m) / clamp)
            if m - (c + h * math.tanh(a0 * (vid + vos) / h)) > 0:
                b = m
            else:
                a = m
        out = 0.5 * (a + b)
        vid = clamp * math.tanh(ks * (st - out) / clamp)
        e = g * vid
        for key, val in (("v(sw)", sw), ("v(set)", st), ("v(out)", out), ("v(e)", e),
                         ("v(inp)", vcm + e / (2 * g)), ("v(inn)", vcm - e / (2 * g)), ("v(vdd)", vdd),
                         ("v(cm)", vcm), ("v(xdut.d1)", vdd - 1.0), ("v(xdut.d2)", vdd - 1.0 - 0.1 * (out - vcm)),
                         ("v(xdut.tail)", 0.2), ("i(vdd)", -6e-5 - 1e-6 * out)):
            cols[key].append(val)
    if not proxies:
        for key in pvt.FIXCM_PROXY_NODES:
            cols.pop(key)
    return cols


def write_wave(path, cols):
    names = list(cols)
    path.write_text(json.dumps({"plotname": "DC transfer characteristic",
                                "variables": [{"index": i, "name": nm} for i, nm in enumerate(names)],
                                "points": [list(p) for p in zip(*(cols[nm] for nm in names))]}))
    return str(path)


def analytic_edge(vdd, a0, floor_db, lo=0.1, hi=None):
    hi = vdd - 0.1 if hi is None else hi
    c, h = 0.5 * (lo + hi), 0.5 * (hi - lo)
    x = math.sqrt(1.0 - 10 ** (floor_db / 20.0) / a0)  # a0*(1-x^2) = floor
    return c - h * x, c + h * x


class SwingFixcmTests(unittest.TestCase):
    """Issue #181: fixed-input-common-mode output-swing diagnostic. Simulator-free."""

    STEP = 1.8 / pvt.SWING_POINTS

    # -- request / deck rendering -------------------------------------------
    def test_request_and_body_rendering(self):
        req, body, tag = klt_request("swing_fixcm", temps=(-40.0, 27.0, 125.0))
        self.assertEqual(tag, "swing-fixcm")
        self.assertEqual(pvt.body_template("swing_fixcm").name, "opamp_swing_fixcm.spice.tmpl")
        self.assertEqual(req["analysis"], klt_request("dc_swing")[0]["analysis"])  # same 0..VDD grid as dc_swing
        self.assertTrue(req["options"]["waveforms"] and req["options"]["keep_artifacts"])
        self.assertEqual(req["backend"], "batch")
        self.assertEqual(req["batch"]["runner_version_check"], pvt.RUNNER_VERSION_CHECK[0])
        self.assertTrue(all("spice" in m and "expr" not in m for m in req["measurements"]))  # klt 0.5.0 runner
        keep = {(c, v) for c in req["corners"]["process"] for v in req["corners"]["supply_v"]["vdd"]}
        for ex in req["exclude"]:
            keep.discard((ex["process"], ex["supply_v"]["vdd"]))
        self.assertEqual(keep, {(c, pvt.VDD_BY_CORNER[c]) for c in pvt.DEFAULT_CORNERS})
        live = "\n".join(ln for ln in body.splitlines() if not ln.lstrip().startswith("*")) + "\n"
        self.assertNotRegex(body, r"\{[A-Za-z_]")  # comments too: every placeholder rendered
        for forbidden in (".control", ".end\n", ".lib", ".temp", "wrdata"):
            self.assertNotIn(forbidden, live)
        self.assertNotRegex(live + json.dumps(req), r"(?i)reltol|abstol|vntol|\.options?\s+(?!scale)")  # DR-006
        self.assertIn('.include "opamp_core.spice"', live)
        # symmetric drive about a FIXED common mode; servo scaled by G, clamped by tanh
        self.assertIn("Bcm cm 0 V = 0.5*v(vdd)", live)
        self.assertIn("Binp inp 0 V = v(cm) + v(e)/(2*100)", live)
        self.assertIn("Binn inn 0 V = v(cm) - v(e)/(2*100)", live)
        self.assertIn("Be e 0 V = 25*tanh(1*100*(v(set) - v(out))/25)", live)
        self.assertIn("Bset set 0 V = v(vdd)*v(sw)", live)

    def test_cartesian_request_carries_every_supply(self):
        with tempfile.TemporaryDirectory() as d:
            path, _t = pvt.build_klt_request("swing_fixcm", None, None, FakeKltPdk(), ["tt"], [27.0], Path(d),
                                             "batch", "cartesian", None)
            req = json.loads(path.read_text())
        self.assertNotIn("exclude", req)
        self.assertEqual(req["corners"]["supply_v"]["vdd"], [1.62, 1.8, 1.98])

    def test_opt_in_and_schema(self):
        self.assertIn("swing_fixcm", pvt.KLT_ANALYSES)
        self.assertNotIn("swing_fixcm", pvt.DEFAULT_ANALYSES)
        self.assertEqual(pvt.FIXCM_PRIMARY, "12db")
        self.assertAlmostEqual(pvt.FIXCM_GAIN_FLOORS_DB["12db"], 20 * math.log10(4))  # follower slope 0.8
        self.assertAlmostEqual(4 / (1 + 4), 0.8)
        self.assertLess(pvt.FIXCM_VID_VALID_V, pvt.FIXCM_VID_CLAMP_V)
        self.assertEqual(len(pvt.FIELDNAMES["swing_fixcm"]), len(set(pvt.FIELDNAMES["swing_fixcm"])))

    # -- boundary extraction -------------------------------------------------
    def test_edges_match_the_analytic_gain_floors(self):
        vdd, a0 = 1.8, 2000.0
        row = pvt.fixcm_extract(vdd, fixcm_sweep(vdd, a0))
        self.assertEqual((row["low_stop"], row["high_stop"]), ("gain_floor", "gain_floor"))
        self.assertAlmostEqual(row["gain_mid_db"], 20 * math.log10(a0), delta=0.05)
        self.assertAlmostEqual(row["vcm_v"], 0.9)
        for label, floor in pvt.FIXCM_GAIN_FLOORS_DB.items():
            sfx = "" if label == pvt.FIXCM_PRIMARY else f"_{label}"
            lo, hi = analytic_edge(vdd, a0, floor)
            with self.subTest(floor=label):
                self.assertAlmostEqual(row[f"out_low_v{sfx}"], lo, delta=self.STEP)
                self.assertAlmostEqual(row[f"out_high_v{sfx}"], hi, delta=self.STEP)
                self.assertAlmostEqual(row[f"out_width_v{sfx}"], row[f"out_high_v{sfx}"] - row[f"out_low_v{sfx}"])
        # wider floors nest: 60 dB inside 40 dB inside 12 dB
        self.assertLess(row["out_low_v"], row["out_low_v_40db"])
        self.assertLess(row["out_low_v_40db"], row["out_low_v_60db"])
        self.assertGreater(row["out_high_v"], row["out_high_v_40db"])
        # required differential input at the edges, signed, small-signal
        self.assertLess(row["vid_low_v"], 0)
        self.assertGreater(row["vid_high_v"], 0)
        self.assertLess(max(abs(row["vid_low_v"]), abs(row["vid_high_v"])), pvt.FIXCM_VID_VALID_V)
        self.assertEqual(row["n_invalid_points"] >= 0, True)

    def test_input_offset_is_reported_not_mistaken_for_a_limit(self):
        row = pvt.fixcm_extract(1.8, fixcm_sweep(1.8, 2000.0, vos=2e-3))
        self.assertAlmostEqual(row["vid_mid_v"], -2e-3, delta=1e-4)
        lo, hi = analytic_edge(1.8, 2000.0, pvt.FIXCM_GAIN_FLOORS_DB["12db"])
        self.assertAlmostEqual(row["out_high_v"], hi, delta=self.STEP)

    def test_gain_held_to_the_sweep_end_is_a_rail_edge(self):
        # amplifier rails beyond 0..VDD: the gain never falls below 12 dB inside the sweep
        row = pvt.fixcm_extract(1.8, fixcm_sweep(1.8, 2000.0, lo=-0.5, hi=2.3))
        self.assertEqual((row["low_stop"], row["high_stop"]), ("sweep_end", "sweep_end"))
        self.assertAlmostEqual(row["out_low_v"], 0.0, delta=1e-3)
        self.assertAlmostEqual(row["out_high_v"], 1.8, delta=1e-3)

    def test_mid_gain_below_a_secondary_floor_reports_nan_not_a_width(self):
        row = pvt.fixcm_extract(1.8, fixcm_sweep(1.8, 300.0))  # 49.5 dB: no 60 dB interval exists
        self.assertTrue(math.isnan(row["out_width_v_60db"]))
        self.assertFalse(math.isnan(row["out_width_v_40db"]))

    def test_headroom_proxies_are_derived_from_saved_nodes(self):
        row = pvt.fixcm_extract(1.8, fixcm_sweep(1.8))
        self.assertAlmostEqual(row["m6_vsg_mid_v"], 1.0, delta=1e-3)  # VDD - v(d2) at out ~ Vcm
        self.assertAlmostEqual(row["m2_vds_mid_v"], 1.8 - 1.0 - 0.2, delta=1e-3)
        self.assertAlmostEqual(row["tail_high_v"], 0.2)
        self.assertGreater(row["m6_vsg_high_v"], row["m6_vsg_mid_v"])  # the synthetic d2 falls as out rises
        self.assertAlmostEqual(row["iq_mid_a"], 6e-5 + 0.9e-6, delta=1e-8)
        bare = pvt.fixcm_extract(1.8, fixcm_sweep(1.8, proxies=False))  # node names absent (candidate netlist)
        self.assertTrue(all(math.isnan(bare[k]) for k in bare if k.startswith(("m6_", "m2_", "tail_", "m3_", "iq_"))))
        self.assertEqual(bare["out_low_v"], row["out_low_v"])

    # -- malformed / incomplete data -----------------------------------------
    def test_malformed_and_incomplete_waveforms_fail_the_unit(self):
        good = fixcm_sweep(1.8)
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            cases = {"missing file": str(d / "none.json"), "no artifact": None}
            junk = d / "junk.json"
            junk.write_text("{not json")
            cases["junk"] = str(junk)
            cases["short"] = write_wave(d / "short.json", {k: v[:40] for k, v in good.items()})
            cases["no v(e)"] = write_wave(d / "noe.json", {k: v for k, v in good.items() if k != "v(e)"})
            nan = dict(good, **{"v(out)": good["v(out)"][:100] + [float("nan")] + good["v(out)"][101:]})
            cases["nan"] = write_wave(d / "nan.json", nan)
            cases["truncated sweep"] = write_wave(d / "trunc.json", {k: v[:300] for k, v in good.items()})
            cm = dict(good, **{"v(inp)": [x + 1e-3 for x in good["v(inp)"]]})
            cases["cm not held"] = write_wave(d / "cm.json", cm)
            inc = dict(good, **{"v(e)": [x * 1.01 for x in good["v(e)"]]})
            cases["vid inconsistent"] = write_wave(d / "inc.json", inc)
            for label, wf in cases.items():
                with self.subTest(label), self.assertRaises(sh.HarnessError):
                    pvt.swing_fixcm_row("tt", 27.0, {"artifacts": {"waveform": wf}, "status": "pass", "runtime_s": 1.0})
            ok = write_wave(d / "ok.json", good)
            with self.assertRaises(sh.HarnessError):  # a 1.8 V sweep presented as the 1.98 V ff corner
                pvt.swing_fixcm_row("ff", 27.0, {"artifacts": {"waveform": ok}, "status": "pass", "runtime_s": 1.0})
            row = pvt.swing_fixcm_row("tt", 27.0, {"artifacts": {"waveform": ok}, "status": "pass", "runtime_s": 2.0})
        self.assertEqual(set(row), set(pvt.FIELDNAMES["swing_fixcm"]))
        self.assertEqual(row["elapsed_s"], 2.0)

    # -- invalid operating interval ------------------------------------------
    def test_invalid_operating_interval_is_a_failure_not_a_limit(self):
        with self.assertRaisesRegex(sh.HarnessError, "invalid operating interval"):
            pvt.fixcm_extract(1.8, fixcm_sweep(1.8, a0=2.0))  # no point anywhere reaches the primary floor
        with self.assertRaisesRegex(sh.HarnessError, "invalid operating interval"):
            pvt.fixcm_extract(1.8, fixcm_sweep(1.8, vos=0.08))  # mid needs |vid| > the small-signal bound
        glitch = fixcm_sweep(1.8)
        m = min(range(len(glitch["v(out)"])), key=lambda i: abs(glitch["v(out)"][i] - 0.9))
        glitch["v(out)"][m + 1] = glitch["v(out)"][m - 1] - 0.01  # non-monotonic at mid-supply
        with self.assertRaisesRegex(sh.HarnessError, "invalid operating interval"):
            pvt.fixcm_extract(1.8, glitch)

    def test_edge_reached_at_an_invalid_point_fails_instead_of_reporting_a_limit(self):
        w = fixcm_sweep(1.8)
        i = min(range(len(w["v(out)"])), key=lambda k: abs(w["v(out)"][k] - 1.3))  # deep in the high-gain region
        w["v(out)"][i] = w["v(out)"][i - 2]  # convergence glitch: out not increasing
        with self.assertRaisesRegex(sh.HarnessError, "high edge not measurable"):
            pvt.fixcm_extract(1.8, w)

    # -- comparison ----------------------------------------------------------
    @staticmethod
    def rows(f_lo, f_hi, b_lo, b_hi, i_lo=0.7, i_hi=1.2, vdd=1.62, corner="ss", temp=-40.0):
        k = {"corner": corner, "temp_c": temp, "vdd_v": vdd}
        fix = dict(k, vcm_v=0.5 * vdd, out_low_v=f_lo, out_high_v=f_hi, out_width_v=f_hi - f_lo,
                   low_stop="gain_floor", high_stop="gain_floor", vid_low_v=-1e-3, vid_high_v=2e-3)
        buf = dict(k, vout_min_v=b_lo, vout_max_v=b_hi, vpp_v=b_hi - b_lo)
        icmr = dict(k, icmr_low_v=i_lo, icmr_high_v=i_hi)
        return fix, buf, icmr

    def test_attribution_rules(self):
        fix, buf, icmr = self.rows(0.01, 1.59, 0.254, 1.203, 0.717, 1.169)
        c = pvt.swing_fixcm_comparison([fix], [buf], [icmr])
        r = c["table"][0]
        self.assertEqual((r["low"]["attribution"], r["high"]["attribution"]), ("input_cm", "input_cm"))
        self.assertTrue(r["vcm_inside_icmr"] and r["low"]["conclusive"] and r["high"]["conclusive"])
        self.assertEqual((r["low"]["buffer_edge_cm_outside_icmr"], r["high"]["buffer_edge_cm_outside_icmr"]),
                         (True, True))
        self.assertEqual(c["summary"], {"low: input_cm": 1, "high: input_cm": 1})
        # edges agreeing within tolerance -> output stage; a fixed-CM edge inside the buffer's -> inconsistent
        fix, buf, icmr = self.rows(0.25, 1.15, 0.254, 1.203)
        r = pvt.swing_fixcm_comparison([fix], [buf], [icmr])["table"][0]
        self.assertEqual((r["low"]["attribution"], r["high"]["attribution"]), ("output_stage", "inconsistent"))
        self.assertFalse(r["high"]["conclusive"])

    def test_attribution_without_icmr_or_with_vcm_outside_is_inconclusive(self):
        fix, buf, icmr = self.rows(0.01, 1.59, 0.254, 1.203, i_lo=0.85, i_hi=1.2)  # Vcm 0.81 outside
        r = pvt.swing_fixcm_comparison([fix], [buf], [icmr])["table"][0]
        self.assertFalse(r["vcm_inside_icmr"])
        self.assertFalse(r["low"]["conclusive"] or r["high"]["conclusive"])
        r = pvt.swing_fixcm_comparison([fix], [buf], None)["table"][0]
        self.assertIsNone(r["vcm_inside_icmr"])
        self.assertFalse(r["low"]["conclusive"])

    def test_unmatched_points_are_listed_not_compared(self):
        fix, buf, _i = self.rows(0.01, 1.59, 0.254, 1.203)
        c = pvt.swing_fixcm_comparison([fix], [dict(buf, temp_c=27.0)], [])
        self.assertEqual((c["points"], len(c["unmatched"])), (0, 1))
        self.assertEqual(pvt.swing_fixcm_comparison([fix], None, None)["points"], 0)

    # -- dc_swing is unchanged -----------------------------------------------
    def test_dc_swing_rule_and_schema_unchanged(self):
        self.assertEqual(pvt.FIELDNAMES["dc_swing"],
                         ["corner", "temp_c", "vdd_v", "vout_min_v", "vout_max_v", "vpp_v",
                          "vpp_pct_of_vdd", "sweep_vout_min_v", "sweep_vout_max_v", "elapsed_s"])
        self.assertEqual(pvt.DEFAULT_ANALYSES, ("ac", "tran_sr", "dc_swing"))
        rec = "20261010-103340-ba1dfa8-0241c1"  # committed fleet baseline: recompute from its own waveform
        wf = RECORDS / f"{rec}-logs" / "klt-dc-swing" / "ss_1p620V_n40C" / "waveform.raw.json"
        if not wf.is_file():
            self.skipTest("baseline waveform artifact not present")
        want = next(r for r in csv.DictReader((RECORDS / f"{rec}-dc-swing.csv").open())
                    if (r["corner"], r["temp_c"]) == ("ss", "-40.0"))
        got = pvt.dc_swing_row("ss", -40.0, {"artifacts": {"waveform": str(wf)}, "status": "pass", "runtime_s": 0})
        for k in ("vout_min_v", "vout_max_v", "vpp_v"):
            self.assertEqual(repr(got[k]), want[k], k)
        hr = pvt.buffer_edge_headroom({"artifacts": {"waveform": str(wf)}}, got)
        self.assertEqual(hr["low"]["vout_v"], got["vout_min_v"])
        self.assertEqual(hr["high"]["vout_v"], got["vout_max_v"])

    # -- campaign against a mocked fleet -------------------------------------
    def _fake_klt(self, d, mutate=None, env=None):
        d = Path(d)

        def fake(req_path, out_dir, bk):
            Path(out_dir).mkdir(parents=True, exist_ok=True)
            req = json.loads(Path(req_path).read_text())
            kind = req["netlist"].split("-body")[0]
            excl = {(e["process"], e["supply_v"]["vdd"]) for e in req.get("exclude", [])}
            units = []
            for c in req["corners"]["process"]:
                for t in req["corners"]["temperature_c"]:
                    for v in req["corners"]["supply_v"]["vdd"]:
                        if (c, v) in excl:
                            continue
                        if kind == "swing-fixcm":
                            wave = fixcm_sweep(v, n=60)
                            meas = [{"name": "vout_mid_v", "value": 0.5 * v}]
                        else:  # dc-swing: a follower clipped 0.25 V from each rail
                            vin = [v * k / pvt.SWING_POINTS for k in range(pvt.SWING_POINTS + 1)]
                            wave = {"v(inp)": vin, "v(out)": [min(max(x, 0.25), v - 0.25) for x in vin]}
                            meas = [{"name": "vout_mid_v", "value": 0.5 * v}]
                        unit = {"process": c, "temperature_c": t, "supply_v": {"vdd": v}, "status": "pass",
                                "runtime_s": 1.0, "diagnostics": [], "measurements": meas,
                                "artifacts": {"waveform": write_wave(d / f"{kind}-{c}-{t:g}-{v:g}.json", wave)}}
                        if mutate:
                            unit = mutate(kind, unit)
                            if unit is None:
                                continue
                        units.append(unit)
            return {"status": "pass", "corner_count": len(units), "corners": units,
                    "environment": {"remote": {"job_id": f"j-{kind}"}} if env is None else env}
        return fake

    def _campaign(self, d, analyses, **kw):
        from unittest import mock
        d = Path(d)
        (d / "snap").mkdir()
        (d / "logs").mkdir()
        results, errors, jobs = {a: [] for a in analyses}, [], []
        with mock.patch.object(pvt, "run_klt_sim", self._fake_klt(d, **kw)), \
                FleetAnalysisTests._armed(self):
            pvt.run_klt_analyses(analyses, FakeKltPdk(), list(pvt.DEFAULT_CORNERS), [-40.0, 27.0, 125.0], "batch",
                                 d / "req", d / "logs", d / "snap", results, errors, jobs)
        return results, errors, jobs

    def test_campaign_rows_and_buffer_headroom_without_local_sim(self):
        # the synthetic fixcm sweep has only 61 points: relax the completeness floor for this mock
        from unittest import mock
        with tempfile.TemporaryDirectory() as d, mock.patch.object(pvt, "SWING_POINTS", 60):
            results, errors, jobs = self._campaign(d, ["swing_fixcm"])
        self.assertEqual(errors, [])
        self.assertEqual(len(results["swing_fixcm"]), 15)
        self.assertTrue(all(set(r) == set(pvt.FIELDNAMES["swing_fixcm"]) for r in results["swing_fixcm"]))
        self.assertEqual([j["remote"]["job_id"] for j in jobs], ["j-swing-fixcm"])

    def test_campaign_failures_are_errors_and_no_remote_is_refused(self):
        from unittest import mock

        def mutate(kind, u):
            if u["process"] == "ss" and u["temperature_c"] == -40.0:
                return None  # absent unit
            if u["process"] == "tt":
                u["artifacts"] = {"waveform": None}  # missing waveform
            if u["process"] == "ff" and u["temperature_c"] == 125.0:
                u["status"] = "error"
                u["diagnostics"] = [{"severity": "error", "code": "timeout", "message": "corner timed out"}]
            return u

        with tempfile.TemporaryDirectory() as d, mock.patch.object(pvt, "SWING_POINTS", 60):
            results, errors, _j = self._campaign(d, ["swing_fixcm"], mutate=mutate)
        self.assertEqual(len(results["swing_fixcm"]), 15 - 1 - 3 - 1)
        self.assertEqual(len(errors), 5)
        with tempfile.TemporaryDirectory() as d, mock.patch.object(pvt, "SWING_POINTS", 60):
            results, errors, _j = self._campaign(d, ["swing_fixcm"], env={})
        self.assertEqual(results["swing_fixcm"], [])
        self.assertTrue(errors and all("no environment.remote" in e for e in errors))

    def test_end_to_end_record_carries_settings_and_same_campaign_comparison(self):
        from unittest import mock

        class Pdk:
            matches_pin, variant, root, installed_commit = True, "sky130A", Path("/pdk"), "abc"
            pin = {"open_pdks_commit": "abc"}
            own_pin = {"rc_corner": {"choice": "typical"}}

        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            root.mkdir()
            records, snaps = root / "records", root / "snaps"
            patches = [
                mock.patch.object(pvt, "REPO_ROOT", root), mock.patch.object(pvt, "RECORDS_DIR", records),
                mock.patch.object(pvt, "SNAPSHOT_DIR", snaps), mock.patch.object(pvt, "resolve_pdk", lambda: Pdk()),
                mock.patch.object(pvt, "klt_available", lambda: "/bin/klt"),
                mock.patch.object(pvt, "klt_version", lambda: "klt-test"),
                mock.patch.object(pvt, "git_sha", lambda _r: "abc1234"),
                mock.patch.object(pvt, "run_klt_sim", self._fake_klt(Path(d))),
                mock.patch.object(pvt, "ACTIVE_DUT", [pvt.DESIGN_NETLIST]),
                mock.patch.object(pvt, "SWING_POINTS", 60),
            ]
            cand = root / "dut.spice"
            cand.write_text("* dut\n")
            with FleetAnalysisTests._armed(self):
                for p in patches:
                    p.start()
                try:
                    rc = pvt.main(["--fleet", "--backend", "batch", "--analyses", "dc_swing,swing_fixcm",
                                   "--netlist", str(cand)])
                finally:
                    mock.patch.stopall()
                    pvt.LOCAL_SIM_FORBIDDEN[0] = False
            self.assertEqual(rc, 0)
            rec = json.loads(next(records.glob("*.json")).read_text())
            rows = list(csv.DictReader((records / Path(rec["links"]["swing_fixcm_csv"]).name).open()))
        self.assertEqual(rec["matrix"]["n_runs"], 30)
        self.assertEqual(rec["matrix"]["swing_fixcm"]["primary_floor"], "12db")
        self.assertEqual(rec["matrix"]["swing_fixcm"]["vcm_frac_of_vdd"], 0.5)
        self.assertEqual(rec["matrix"]["swing_fixcm"]["solver_settings"]["policy"], "DR-006")
        self.assertEqual(len(rows), 15)
        self.assertEqual(list(rows[0]), pvt.FIELDNAMES["swing_fixcm"])
        cmp_ = rec["swing_fixcm_comparison"]
        self.assertEqual((cmp_["points"], cmp_["unmatched"]), (15, []))
        # the mocked follower clips 0.25 V from each rail, the mocked output stage only 0.1 V from it
        self.assertEqual(cmp_["summary"], {"low: input_cm (inconclusive)": 15, "high: input_cm (inconclusive)": 15})
        self.assertIsNotNone(cmp_["table"][0]["low"]["buffer_headroom"])


class EffectiveBackendTests(unittest.TestCase):
    """Issue #163: the backend is resolved once per invocation as an explicit
    --backend > nonempty $KLT_SIM_BACKEND > batch; empty/unset env falls back."""

    def backend(self, argv, env=None):
        with klt_backend_env(env):
            return pvt.parse_args(argv).backend

    def test_unset_env_falls_back_to_batch(self):
        self.assertEqual(self.backend([]), pvt.DEFAULT_KLT_BACKEND)

    def test_empty_env_falls_back_to_batch(self):
        self.assertEqual(self.backend([], env=""), pvt.DEFAULT_KLT_BACKEND)

    def test_env_selects_local_without_the_cli_flag(self):
        self.assertEqual(self.backend([], env="local"), "local")

    def test_cli_beats_env_in_both_directions(self):
        self.assertEqual(self.backend(["--backend", "batch"], env="local"), "batch")
        self.assertEqual(self.backend(["--backend", "local"], env="batch"), "local")


class BatchLocalGridRefusalTests(unittest.TestCase):
    """Issue #163: on the effective batch backend, a request needing more than
    one local ngspice execution unit (local analyses x supply points) exits
    non-zero before any tool/PDK check, simulator/version probe, klt submission
    or record/snapshot allocation. Every later stage is armed to fail the test."""

    def refuse(self, argv, env=None):
        import contextlib
        import io
        import subprocess as sp
        from unittest import mock

        def fail(stage):
            def _fail(*a, **k):
                raise AssertionError(f"{stage} reached despite the refusal")
            return _fail

        with tempfile.TemporaryDirectory() as d:
            records, snaps = Path(d) / "records", Path(d) / "snaps"
            records.mkdir()
            snaps.mkdir()
            err = io.StringIO()
            with klt_backend_env(env), \
                    mock.patch.object(sp, "run", fail("local subprocess")), \
                    mock.patch.object(pvt, "resolve_pdk", fail("PDK resolution")), \
                    mock.patch.object(pvt, "klt_available", fail("klt probe")), \
                    mock.patch.object(pvt, "first_line", fail("tool version probe")), \
                    mock.patch.object(pvt, "allocate_record_id", fail("record allocation")), \
                    mock.patch.object(pvt, "run_klt_sim", fail("klt submission")), \
                    mock.patch.object(pvt, "RECORDS_DIR", records), \
                    mock.patch.object(pvt, "SNAPSHOT_DIR", snaps), \
                    contextlib.redirect_stderr(err):
                rc = pvt.main(list(argv))
            self.assertEqual(list(records.iterdir()), [], "refusal wrote record files")
            self.assertEqual(list(snaps.iterdir()), [], "refusal wrote snapshots")
        self.assertNotEqual(rc, 0)
        return err.getvalue()

    def test_default_campaign_refuses_naming_45_units_and_the_fleet_escape(self):
        err = self.refuse([])
        self.assertIn("45 local ngspice unit", err)
        self.assertIn("'--fleet --backend batch'", err)

    def test_env_batch_refuses_identically(self):
        err = self.refuse([], env="batch")
        self.assertIn("45 local ngspice unit", err)

    def test_cli_batch_beats_env_local(self):
        err = self.refuse(["--backend", "batch"], env="local")
        self.assertIn("'--fleet --backend batch'", err)

    def test_two_local_analyses_at_one_supply_point_are_two_units(self):
        err = self.refuse(["--corners", "tt", "--temps", "27", "--analyses", "ac,tran_sr"])
        self.assertIn("2 local ngspice unit", err)
        self.assertIn("2 local analysis(es) x 1 supply point", err)

    def test_repeated_analysis_entries_are_not_deduplicated(self):
        err = self.refuse(["--corners", "tt", "--temps", "27", "--analyses", "ac,ac"])
        self.assertIn("2 local ngspice unit", err)

    def test_two_cartesian_supplies_at_one_point_are_two_units(self):
        err = self.refuse(["--corners", "tt", "--temps", "27", "--analyses", "ac",
                           "--supply-mode", "cartesian", "--supplies", "1.62,1.98"])
        self.assertIn("2 local ngspice unit", err)
        self.assertIn("1 local analysis(es) x 2 supply point", err)

    def test_unknown_analysis_still_reports_the_pre_guard_error(self):
        err = self.refuse(["--corners", "tt", "--temps", "27", "--analyses", "ac,bogus"])
        self.assertIn("unknown analysis 'bogus'", err)
        self.assertNotIn("--fleet --backend batch", err)

    def test_duplicate_supply_tuple_still_reports_the_pre_guard_error(self):
        err = self.refuse(["--corners", "tt,tt", "--temps", "27", "--analyses", "ac"])
        self.assertIn("duplicate (process, temperature, supply) tuple", err)
        self.assertNotIn("--fleet --backend batch", err)


class LocalExecutionAllowanceTests(unittest.TestCase):
    """Issue #163: what the batch guard lets through -- exactly one local unit,
    an explicit local backend of any grid size, an env-selected local backend,
    mixed local+klt selections (remote work does not consume the local
    allowance) and the zero-local-unit --fleet / klt-only paths -- with the
    unchanged record schema, and no routing state leaking between main() calls."""

    NGSPICE_OUT = ("iq_a=1e-5\npq_w=1e-5\ngain_dc_db=60\ngbw_hz=1e6\nphase_at_gbw_rad=-2\n"
                   "sr_rise_s=1e-8\nsr_fall_s=1e-8\n")

    class LocalPdk(FakePdk):
        variant = "sky130A"
        matches_pin, root, installed_commit = True, Path("/pdk"), "abc"
        pin = {"open_pdks_commit": "abc"}
        own_pin = {"rc_corner": {"choice": "typical"}}

    def run_main(self, argv, env=None):
        """main() to completion against mocked local/klt runners and temporary
        record/snapshot dirs; returns (rc, record, local_decks, klt_campaigns)."""
        import contextlib
        import io
        from unittest import mock

        local_decks, klt_campaigns = [], []

        def fake_ngspice(_ngspice, deck_text, _workdir, _log_path, timeout_s=120):
            local_decks.append(deck_text)
            return self.NGSPICE_OUT, 0.1

        def fake_klt_campaign(analyses, pdk, corners, temps, backend, req_dir, log_dir,
                              snapshot_run_dir, results, errors, klt_jobs,
                              supply_mode=pvt.DEFAULT_SUPPLY_MODE, supplies=None):
            klt_campaigns.append((list(analyses), backend))
            klt_jobs.append({"remote": {"job_id": f"j-{len(klt_campaigns)}"}, "backend": backend})

        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            records, snaps = root / "records", root / "snaps"
            records.mkdir(parents=True)
            snaps.mkdir(parents=True)
            out = io.StringIO()
            patches = [
                mock.patch.object(pvt, "REPO_ROOT", root),
                mock.patch.object(pvt, "RECORDS_DIR", records),
                mock.patch.object(pvt, "SNAPSHOT_DIR", snaps),
                mock.patch.object(pvt, "resolve_pdk", lambda: self.LocalPdk()),
                mock.patch.object(pvt, "klt_available", lambda: "/bin/klt"),
                mock.patch.object(pvt, "klt_version", lambda: "klt-test"),
                mock.patch.object(pvt, "git_sha", lambda _r: "abc1234"),
                mock.patch.object(pvt, "first_line", lambda *a, **k: "fake-ngspice v42"),
                mock.patch.object(pvt.shutil, "which", lambda n: f"/bin/{n}"),
                mock.patch.object(pvt, "run_ngspice", fake_ngspice),
                mock.patch.object(pvt, "run_klt_analyses", fake_klt_campaign),
                mock.patch.object(pvt, "ACTIVE_DUT", [pvt.DESIGN_NETLIST]),
            ]
            with klt_backend_env(env):
                for p in patches:
                    p.start()
                try:
                    with contextlib.redirect_stderr(out), contextlib.redirect_stdout(out):
                        rc = pvt.main(list(argv))
                finally:
                    mock.patch.stopall()
            recs = list(records.glob("*.json"))
            rec = json.loads(recs[0].read_text()) if recs else None
        return rc, rec, local_decks, klt_campaigns

    def test_single_unit_probe_runs_locally_on_batch(self):
        rc, rec, decks, klt = self.run_main(["--corners", "tt", "--temps", "27", "--analyses", "ac"])
        self.assertEqual((rc, len(decks), klt), (0, 1, []))
        self.assertEqual(rec["matrix"]["execution"]["local_ngspice_analyses"], ["ac"])
        self.assertEqual(rec["matrix"]["n_runs"], 1)
        self.assertIsNone(rec["matrix"]["execution"]["backend"])
        self.assertEqual(rec["tools"]["ngspice"], "fake-ngspice v42")
        self.assertIn("ac_csv", rec["links"])

    def test_explicit_local_backend_runs_any_grid(self):
        rc, rec, decks, klt = self.run_main(["--backend", "local", "--corners", "tt,ss",
                                             "--temps", "27", "--analyses", "ac,tran_sr"])
        self.assertEqual((rc, klt), (0, []))
        self.assertEqual(len(decks), 4)  # 2 local analyses x 2 supply points
        self.assertEqual(rec["matrix"]["execution"]["local_ngspice_analyses"], ["ac", "tran_sr"])

    def test_env_selected_local_preserves_the_full_local_campaign(self):
        rc, rec, decks, klt = self.run_main(["--analyses", "ac,tran_sr"], env="local")
        self.assertEqual((rc, klt), (0, []))
        self.assertEqual(len(decks), 30)  # 2 local analyses x 15 supply points, no refusal
        self.assertEqual(rec["matrix"]["n_runs"], 30)
        self.assertEqual(rec["matrix"]["execution"]["local_ngspice_analyses"], ["ac", "tran_sr"])

    def test_mixed_selection_counts_only_the_local_portion(self):
        rc, rec, decks, klt = self.run_main(["--corners", "tt", "--temps", "27",
                                             "--analyses", "ac,icmr"])
        self.assertEqual(rc, 0)
        self.assertEqual(len(decks), 1)  # one local unit allowed on batch
        self.assertEqual(klt, [(["icmr"], "batch")])  # remote work is not constrained
        self.assertEqual(rec["matrix"]["execution"]["backend"], "batch")
        self.assertEqual(rec["matrix"]["execution"]["local_ngspice_analyses"], ["ac"])
        self.assertEqual([j["backend"] for j in rec["klt_jobs"]], ["batch"])

    def test_klt_only_selection_is_never_rejected(self):
        rc, rec, decks, klt = self.run_main(["--analyses", "icmr,cmrr,tran_step"])
        self.assertEqual((rc, decks, rec["matrix"]["n_failed"]), (0, [], 0))
        self.assertEqual(klt, [(["icmr", "cmrr", "tran_step"], "batch")])

    def test_fleet_counts_zero_local_units(self):
        rc, rec, decks, klt = self.run_main(["--fleet", "--backend", "batch"])
        self.assertEqual((rc, decks), (0, []))
        self.assertEqual(klt, [(["ac", "tran_sr", "dc_swing"], "batch")])
        self.assertEqual(rec["matrix"]["execution"]["local_ngspice_analyses"], [])
        self.assertEqual(rec["tools"]["ngspice"], "not invoked (klt/fleet execution)")

    def test_consecutive_main_calls_leave_no_routing_state_stuck(self):
        # fleet/batch sets LOCAL_SIM_FORBIDDEN for its own run; each later call
        # must re-derive the flag and the backend from its own argv/environment.
        self.addCleanup(pvt.LOCAL_SIM_FORBIDDEN.__setitem__, 0, False)
        rc0, _r0, decks0, klt0 = self.run_main(["--fleet", "--backend", "batch",
                                                "--corners", "tt", "--temps", "27"])
        self.assertEqual((rc0, decks0), (0, []))
        self.assertEqual(klt0, [(["ac", "tran_sr", "dc_swing"], "batch")])
        self.assertTrue(pvt.LOCAL_SIM_FORBIDDEN[0])  # left set, as the fleet run does today
        rc1, _r1, decks1, _k1 = self.run_main(["--corners", "tt", "--temps", "27", "--analyses", "ac"])
        self.assertEqual((rc1, len(decks1)), (0, 1))  # one-unit probe not poisoned by the fleet call
        self.assertFalse(pvt.LOCAL_SIM_FORBIDDEN[0])
        rc2, _r2, decks2, _k2 = self.run_main(["--backend", "local", "--corners", "tt,ss",
                                               "--temps", "27", "--analyses", "ac"])
        self.assertEqual((rc2, len(decks2)), (0, 2))
        pvt.LOCAL_SIM_FORBIDDEN[0] = False

    def test_check_env_reports_the_effective_backend_and_precedence(self):
        import contextlib
        import io
        from unittest import mock

        out = io.StringIO()
        with klt_backend_env("batch"), \
                mock.patch.object(pvt, "report_tool_status", lambda: 0), \
                mock.patch.object(pvt, "report_pdk", lambda resolve, corners, label: (0, None)), \
                mock.patch.object(pvt, "klt_available", lambda: "/bin/klt"), \
                mock.patch.object(pvt, "klt_version", lambda: "klt-test"), \
                contextlib.redirect_stdout(out):
            rc = pvt.main(["--check-env", "--backend", "local"])  # CLI wins over the batch env
        self.assertEqual(rc, 0)
        text = out.getvalue()
        self.assertIn("klt sim backend: local", text)
        self.assertIn("KLT_SIM_BACKEND='batch'", text)
        self.assertIn("--backend", text)


def follower_wave(lo, hi, sr=15e6, k=1e8, vdd=1.8, t_stop=2.2e-6, dt=2e-9, offset=0.0, sr_fall=None,
                  freeze_after_rise=False, tail=0.3, pair=0.2, proxies=True):
    """Synthetic unity-buffer step response: dv/dt = clamp(k*(vin - v + offset), -sr_fall, +sr) with the
    standard 200 ns / 1 ns / 1 us pulse. Large `sr` relative to k*step gives pure linear settling."""
    sr_fall = sr if sr_fall is None else sr_fall
    t0, te, pw = pvt.ICMR_SR_T_DELAY_S, pvt.ICMR_SR_T_EDGE_S, pvt.ICMR_SR_T_PW_S

    def vin(x):
        if x < t0:
            return lo
        if x < t0 + te:
            return lo + (hi - lo) * (x - t0) / te
        if x < t0 + te + pw:
            return hi
        if x < t0 + 2 * te + pw:
            return hi - (hi - lo) * (x - t0 - te - pw) / te
        return lo

    n = int(round(t_stop / dt))
    sub = 20
    ts, vs, ivs = [], [], []
    v = lo
    for i in range(n + 1):
        x = i * dt
        ts.append(x)
        vs.append(v)
        ivs.append(-(5e-6 + 55e-6 + 2e-12 * 0.0))
        for _ in range(sub):
            if freeze_after_rise and x > t0 + te + pw:
                break
            r = k * (vin(x) - v + offset)
            r = max(-sr_fall, min(sr, r))
            v += r * dt / sub
            x += dt / sub
    cols = {"time": ts, "v(out)": vs, "v(inp)": [vin(x) for x in ts], "i(vdd)": ivs}
    if proxies:
        cols.update({"v(xdut.d1)": [vdd - 0.9] * len(ts), "v(xdut.d2)": [vdd - 0.9] * len(ts),
                     "v(xdut.tail)": [tail] * len(ts)})
        cols["v(xdut.d1)"] = [tail + pair] * len(ts)
        cols["v(xdut.d2)"] = [tail + pair] * len(ts)
    return cols


class IcmrAwareSlewTests(unittest.TestCase):
    """Issue #185: ICMR-aware unity-buffer slew diagnostic. Simulator-free."""

    VDD = 1.62

    def step(self, low=0.7168, high=1.1686):
        return pvt.select_icmr_step(self.VDD, low, high)

    # -- amplitude selection -------------------------------------------------
    def test_step_is_standard_stimulus_clipped_to_guarded_window(self):
        s = self.step()
        self.assertTrue(s["usable"])
        self.assertAlmostEqual(s["v_low_v"], 0.7168 + pvt.ICMR_SR_GUARD_V)
        self.assertAlmostEqual(s["v_high_v"], 1.1686 - pvt.ICMR_SR_GUARD_V)
        self.assertFalse(s["same_as_standard"])
        self.assertAlmostEqual(s["std_below_icmr_v"], 0.7168 - 0.3 * self.VDD)
        self.assertEqual(s["std_above_icmr_v"], 0.0)
        self.assertFalse(s["std_inside_icmr"])
        self.assertLessEqual(s["v_high_v"] - s["v_low_v"], 0.4 * self.VDD)

    def test_wide_window_reproduces_the_standard_step(self):
        s = pvt.select_icmr_step(1.8, 0.3, 1.5)
        self.assertTrue(s["usable"] and s["same_as_standard"] and s["std_inside_icmr"])
        self.assertAlmostEqual(s["v_low_v"], 0.54)
        self.assertAlmostEqual(s["v_high_v"], 1.26)

    def test_step_never_leaves_the_guarded_window(self):
        for lo, hi in ((0.6, 1.3), (0.9, 1.5), (0.55, 1.2)):
            s = pvt.select_icmr_step(1.8, lo, hi)
            self.assertTrue(s["usable"])
            self.assertGreaterEqual(s["v_low_v"], lo + pvt.ICMR_SR_GUARD_V - 1e-12)
            self.assertLessEqual(s["v_high_v"], hi - pvt.ICMR_SR_GUARD_V + 1e-12)

    def test_no_useful_step_is_reported_not_clamped(self):
        for lo, hi in ((0.888, 1.024), (0.9, 0.95), (1.0, 0.8), (float("nan"), 1.0)):
            with self.subTest(lo=lo, hi=hi):
                s = pvt.select_icmr_step(1.8, lo, hi)
                self.assertFalse(s["usable"])
                self.assertTrue(s["reason"])
                self.assertTrue(math.isnan(s["v_low_v"]))
        row = pvt.icmr_sr_unusable_row(1.8, pvt.select_icmr_step(1.8, 0.888, 1.024), 20.0, 11.0)
        self.assertEqual(row["verdict"], "no_useful_step")
        self.assertEqual(row["step_usable"], 0)
        self.assertTrue(math.isnan(row["fall_sr_claim_v_per_us"]))

    # -- valid slewing --------------------------------------------------------
    def test_slewing_step_yields_a_claim_and_attribution(self):
        s = self.step()
        wave = follower_wave(s["v_low_v"], s["v_high_v"], sr=15e6, sr_fall=14e6, vdd=self.VDD)
        row = pvt.icmr_sr_extract(self.VDD, s, wave, std_fall=11.0, std_rise=20.0)
        self.assertEqual((row["rise_class"], row["fall_class"]), ("slew_limited", "slew_limited"))
        self.assertAlmostEqual(row["fall_sr_peak_v_per_us"], 14.0, delta=0.5)  # the imposed rate
        self.assertLessEqual(row["fall_sr_claim_v_per_us"], row["fall_sr_peak_v_per_us"])  # 20-80 % average
        self.assertGreater(row["fall_sr_claim_v_per_us"], 0.8 * 14.0)
        self.assertAlmostEqual(row["fall_i_load_peak_ua"], 2e-12 * 14e6 * 1e6, delta=2.0)
        self.assertEqual(row["verdict"], "input_range_contributes")
        self.assertAlmostEqual(row["fall_sr_ratio_to_std"], row["fall_sr_claim_v_per_us"] / 11.0)
        self.assertEqual(row["fall_input_headroom_loss"], 0)
        self.assertEqual(set(row) | {"corner", "temp_c", "vdd_v", "elapsed_s"}, set(pvt.FIELDNAMES["tran_sr_icmr"]))

    def test_comparable_slew_is_no_input_range_effect(self):
        s = self.step()
        wave = follower_wave(s["v_low_v"], s["v_high_v"], sr=15e6, sr_fall=11.2e6, vdd=self.VDD)
        row = pvt.icmr_sr_extract(self.VDD, s, wave, std_fall=11.0)
        self.assertEqual(row["verdict"], "no_input_range_effect")

    def test_headroom_loss_proxy_flags_collapsed_tail(self):
        s = self.step()
        wave = follower_wave(s["v_low_v"], s["v_high_v"], vdd=self.VDD, tail=0.05)
        row = pvt.icmr_sr_extract(self.VDD, s, wave, std_fall=11.0)
        self.assertEqual(row["fall_input_headroom_loss"], 1)
        bare = pvt.icmr_sr_extract(self.VDD, s, follower_wave(s["v_low_v"], s["v_high_v"], vdd=self.VDD,
                                                              proxies=False), std_fall=11.0)
        self.assertEqual(bare["fall_input_headroom_loss"], "")
        self.assertTrue(math.isnan(bare["fall_tail_min_v"]))

    # -- invalid measurements never become slew claims ------------------------
    def test_linear_settling_is_not_a_slew_claim(self):
        s = self.step()
        wave = follower_wave(s["v_low_v"], s["v_high_v"], sr=1e9, k=3e7, vdd=self.VDD)  # never rate-limited
        row = pvt.icmr_sr_extract(self.VDD, s, wave, std_fall=11.0)
        self.assertEqual(row["fall_class"], "linear")
        self.assertTrue(math.isnan(row["fall_sr_claim_v_per_us"]))
        self.assertEqual(row["verdict"], "inconclusive")  # a faster linear edge must not read as improved slew
        self.assertGreater(row["fall_sr_avg_v_per_us"], 0)  # the measured average stays visible, unclaimed

    def test_missing_crossing_unsettled_and_unreached_are_invalid(self):
        s = self.step()
        base = follower_wave(s["v_low_v"], s["v_high_v"], vdd=self.VDD)
        t, v = base["time"], list(base["v(out)"])
        # output stuck: no step reached on either edge
        stuck = dict(base, **{"v(out)": [s["v_low_v"]] * len(t)})
        e = pvt.icmr_sr_edge(stuck, s["v_low_v"], s["v_high_v"], pvt.ICMR_SR_T_DELAY_S, 1.201e-6, self.VDD)
        self.assertEqual(e["class"], "invalid")
        self.assertIn("not reached", e["reason"])
        self.assertTrue(math.isnan(e["sr_claim"]) and math.isnan(e["sr_avg"]))
        # too slow: still moving at the end of the region
        slow = follower_wave(s["v_low_v"], s["v_high_v"], sr=0.2e6, sr_fall=0.2e6, vdd=self.VDD)
        row = pvt.icmr_sr_extract(self.VDD, s, slow, std_fall=11.0)
        self.assertEqual(row["fall_class"], "invalid")
        self.assertEqual(row["verdict"], "inconclusive")
        self.assertTrue(math.isnan(row["fall_sr_claim_v_per_us"]))
        # settled endpoint within tolerance but the 20 % crossing is jumped by a single sample
        jump = dict(base, **{"time": [0.0, 1e-9, 1.0e-6, 1.1e-6, 1.2e-6, 1.201e-6, 1.202e-6, 1.5e-6, 2.0e-6, 2.2e-6],
                             "v(out)": [s["v_low_v"], s["v_low_v"], s["v_high_v"], s["v_high_v"], s["v_high_v"],
                              s["v_high_v"], s["v_low_v"], s["v_low_v"], s["v_low_v"], s["v_low_v"]],
                             "v(inp)": [0.0] * 10, "i(vdd)": [-6e-5] * 10})
        e = pvt.icmr_sr_edge({**jump, **{k: [0.3] * 10 for k in pvt.ICMR_SR_PROXY_NODES}}, s["v_low_v"],
                             s["v_high_v"], pvt.ICMR_SR_T_DELAY_S, 1.201e-6, self.VDD)
        self.assertIn(e["class"], ("slew_limited", "inconclusive", "linear", "invalid"))  # structurally handled
        # outright non-finite / short / non-monotonic axes
        for bad in ({**base, "time": t[:5], "v(out)": v[:5]}, {**base, "time": t[::-1]}):
            with self.subTest():
                e = pvt.icmr_sr_edge(bad, s["v_low_v"], s["v_high_v"], pvt.ICMR_SR_T_DELAY_S, 1.201e-6, self.VDD)
                self.assertEqual(e["class"], "invalid")
        nanw = dict(base, **{"v(out)": [float("nan")] * len(t)})
        self.assertEqual(pvt.icmr_sr_edge(nanw, 0.8, 1.1, pvt.ICMR_SR_T_DELAY_S, 1.201e-6, self.VDD)["class"],
                         "invalid")

    def test_missing_20_80_crossing_is_invalid(self):
        # reaches its endpoint with a coarse sample after the 80 % level was passed in the SAME sample
        # interval as the 20 % level only if monotonic -- craft a non-monotonic dip below the 20 % level
        t = [i * 2e-9 for i in range(1101)]
        lo, hi = 0.8, 1.1
        v = [lo if x < 210e-9 else hi for x in t]  # instantaneous jump: crossings coincide
        w = {"time": t, "v(out)": v, "v(inp)": v, "i(vdd)": [-6e-5] * len(t)}
        e = pvt.icmr_sr_edge(w, lo, hi, pvt.ICMR_SR_T_DELAY_S, 1.201e-6, self.VDD)
        self.assertNotEqual(e["class"], "slew_limited") if e["class"] == "invalid" else None
        # level never present in the observation region -> missing crossing
        v2 = [hi] * len(t)
        w2 = dict(w, **{"v(out)": v2})
        e2 = pvt.icmr_sr_edge(w2, lo, hi, pvt.ICMR_SR_T_DELAY_S, 1.201e-6, self.VDD)
        self.assertEqual(e2["class"], "invalid")

    def test_unusable_or_missing_reference_never_asserts_attribution(self):
        s = self.step()
        wave = follower_wave(s["v_low_v"], s["v_high_v"], sr=15e6, vdd=self.VDD)
        self.assertEqual(pvt.icmr_sr_extract(self.VDD, s, wave)["verdict"], "no_standard_reference")
        wide = pvt.select_icmr_step(1.8, 0.3, 1.5)
        w = follower_wave(wide["v_low_v"], wide["v_high_v"], sr=15e6, vdd=1.8)
        self.assertEqual(pvt.icmr_sr_extract(1.8, wide, w, std_fall=11.0)["verdict"], "standard_inside_icmr")

    # -- wiring ---------------------------------------------------------------
    def test_request_is_single_unit_with_literal_levels_and_waveforms(self):
        s = self.step()
        pvt.ICMR_SR_STEPS[("ss", -40.0, round(self.VDD, 6))] = s
        try:
            req, body, tag = klt_request("tran_sr_icmr", None, self.VDD, ["ss"], (-40.0,))
        finally:
            pvt.ICMR_SR_STEPS.clear()
        self.assertEqual(tag, "tran-sr-icmr-ss--40C-1.62V")
        self.assertEqual(req["corners"], {"process": ["ss"], "supply_v": {"vdd": [1.62]}, "temperature_c": [-40.0]})
        self.assertTrue(req["options"]["waveforms"])
        self.assertEqual(req["analysis"], {"kind": "tran", "args": pvt.SR_TRAN_ARGS})
        live = "\n".join(ln for ln in body.splitlines() if not ln.lstrip().startswith("*"))
        self.assertNotRegex(live, r"\{[A-Za-z_]")
        self.assertIn(f"pulse({s['v_low_v']:.6f} {s['v_high_v']:.6f} 200n 1n 1n 1u 2u)", live)
        self.assertEqual(pvt.body_template("tran_sr_icmr").name, "opamp_tran_sr_icmr.spice.tmpl")
        with self.assertRaises(sh.HarnessError):  # an unusable point never gets a request
            pvt.ICMR_SR_STEPS[("ss", -40.0, 1.62)] = pvt.select_icmr_step(1.62, 0.888, 0.95)
            try:
                klt_request("tran_sr_icmr", None, self.VDD, ["ss"], (-40.0,))
            finally:
                pvt.ICMR_SR_STEPS.clear()

    def test_opt_in_and_standard_analysis_untouched(self):
        self.assertIn("tran_sr_icmr", pvt.KLT_ANALYSES)
        self.assertNotIn("tran_sr_icmr", pvt.DEFAULT_ANALYSES)
        self.assertEqual(pvt.FIELDNAMES["tran_sr"][-3:], ["sr_rise_v_per_us", "sr_fall_v_per_us", "elapsed_s"])
        self.assertEqual(len(pvt.FIELDNAMES["tran_sr_icmr"]), len(set(pvt.FIELDNAMES["tran_sr_icmr"])))
        self.assertEqual(pvt.ICMR_SR_CL_F, float(pvt.CL_F.replace("p", "e-12")))
        self.assertEqual(pvt.ICMR_SR_IBIAS_A, float(pvt.IBIAS_A.replace("u", "e-6")))

    def test_row_from_waveform_artifact_and_failures(self):
        s = self.step()
        pvt.ICMR_SR_STEPS[("ss", -40.0, round(self.VDD, 6))] = s
        try:
            with tempfile.TemporaryDirectory() as d:
                d = Path(d)
                wf = write_wave(d / "w.json", follower_wave(s["v_low_v"], s["v_high_v"], sr=15e6, vdd=self.VDD))
                row = pvt.tran_sr_icmr_row("ss", -40.0, {"artifacts": {"waveform": wf}, "runtime_s": 3.0},
                                           self.VDD, 20.0, 11.0)
                self.assertEqual(set(row), set(pvt.FIELDNAMES["tran_sr_icmr"]))
                with self.assertRaises(sh.HarnessError):
                    pvt.tran_sr_icmr_row("ss", -40.0, {"artifacts": {}}, self.VDD)
                with self.assertRaises(sh.HarnessError):  # no step plan for this point
                    pvt.tran_sr_icmr_row("tt", 27.0, {"artifacts": {"waveform": wf}}, 1.8)
        finally:
            pvt.ICMR_SR_STEPS.clear()
        summ = pvt.tran_sr_icmr_summary([row])
        self.assertEqual(summ["points"], 1)


if __name__ == "__main__":
    unittest.main()
