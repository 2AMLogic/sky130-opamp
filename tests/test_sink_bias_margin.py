"""Simulator-free tests for variants/sink_bias_margin.py and its committed netlists (issue #197)."""

import csv
import json
import re
import sys
import unittest
from unittest import mock
from pathlib import Path

from _paths import EXP, load_module

VAR = EXP / "variants"
sbm = load_module("sink_bias_margin", VAR / "sink_bias_margin.py")


def cards(text):
    out = {}
    for line in text.replace("\n+", " ").splitlines():
        if line.startswith("XM"):
            tok = line.split()
            kv = dict(t.split("=") for t in tok if "=" in t)
            out[tok[0]] = (tok[1:6], float(kv["W"]), float(kv["L"]), int(kv["m"]), int(kv["nf"]))
    return out


class BiasMargin(unittest.TestCase):
    def test_committed_files_match_generator(self):
        self.assertEqual(sbm.check(), [])

    def test_only_xmc_width_differs_and_canonical_verbatim(self):
        base = cards(sbm.path("ic090").read_text())
        canon = cards(sbm.CANON.read_text())
        for tag in sbm.FRACTIONS:
            c = cards(sbm.path(tag).read_text())
            for name, v in canon.items():
                self.assertEqual(c[name], v, (tag, name))
            for name in c:
                if name != "XMC":
                    self.assertEqual(c[name], base[name], (tag, name))

    def test_original_matches_signal_dependent_sink_widths(self):
        orig = cards((VAR / "signal-dependent-sink.spice").read_text())
        new = cards(sbm.path(sbm.ORIGINAL).read_text())
        for name in ("XMP6C", "XMA", "XMA2", "XMC", "XMD", "XMS"):
            self.assertAlmostEqual(orig[name][1], new[name][1], places=6)

    def test_margins_ordered_and_grid_legal(self):
        w = [sbm.widths(f)["p_ic"] for f in sbm.FRACTIONS.values()]
        self.assertTrue(w[0] > w[1] > w[2])
        for x in w:
            self.assertTrue(sbm.ss.legal(x))
        self.assertEqual(len(sbm.FRACTIONS), 3)   # reference + at most two margins

    def test_probe_source_is_zero_volt_in_xms_source(self):
        text = sbm.path("ic060").read_text()
        self.assertRegex(text, r"(?m)^XMS out nx xs vss ")
        self.assertRegex(text, r"(?m)^Vxms xs vss 0$")

    def test_static_rows_flag_rail_and_boost(self):
        rep = {"corners": [{"process": "tt", "temperature_c": 27.0, "supply_v": {"vdd": 1.8}, "status": "pass",
                            "measurements": [{"name": "i_vdd_a", "value": -7e-5}, {"name": "i_xms_a", "value": 3e-6},
                                             {"name": "vout_v", "value": 1.75}]},
                           {"process": "ss", "temperature_c": -40.0, "supply_v": {"vdd": 1.62}, "status": "error",
                            "measurements": []}]}
        a, b = sbm.static_rows(rep)
        self.assertTrue(a["ok"] and a["railed"] and a["boost_flag"])
        self.assertFalse(b["ok"])


if __name__ == "__main__":
    unittest.main()


class ReportAndAccountingTests(unittest.TestCase):
    """Simulator-free checks over the committed manifest and plan (issue #197)."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sim/opamp-characterization/variants"))
        import sink_bias_report
        cls.rep = sink_bias_report

    def test_manifest_dut_hashes_match_variants(self):
        m = self.rep.manifest()
        for tag, e in m["variants"].items():
            for rid in e["ids"] + e.get("stage2", []):
                meta = json.loads((self.rep.REC / f"{rid}.json").read_text())
                self.assertEqual(meta["dut"]["sha256"], self.rep.variant_sha(tag), rid)

    def test_screen_stops_every_candidate_under_plan_condition_1(self):
        # Strict reading of PLAN.md condition 1: the TT/27 tran_sr_icmr fall edge of ic075 (and of the
        # ic090 reference) is "inconclusive", so it is stopped; ic060 stops on condition 4.
        m, canon, data = self.rep.get_all()
        tt = self.rep.SCREEN_POINTS["TT/27"]
        self.assertEqual(data["ic075"]["d"]["tran-sr-icmr"][tt]["fall_class"], "inconclusive")
        for tag in ("ic090", "ic075"):
            why = self.rep.screen_verdict(tag, canon, data[tag])
            self.assertIn("tran_sr_icmr fall class inconclusive (not slew_limited) at TT/27", why, tag)
        self.assertTrue(any("fall SR gain 0.70" in r for r in self.rep.screen_verdict("ic060", canon, data["ic060"])))

    def _clean_ic075(self):
        """ic075 Stage-1 data with the TT/27 fall edge forced to slew_limited: then nothing stops it."""
        import copy
        m, canon, data = self.rep.get_all()
        dat = copy.deepcopy(data["ic075"])
        tt = self.rep.SCREEN_POINTS["TT/27"]
        dat["d"]["tran-sr-icmr"][tt]["fall_class"] = "slew_limited"
        self.assertEqual(self.rep.screen_verdict("ic075", canon, dat), [])
        return canon, dat, tt

    def test_screen_stops_on_missing_tran_sr_icmr_unit(self):
        canon, dat, tt = self._clean_ic075()
        del dat["d"]["tran-sr-icmr"][tt]
        self.assertIn("missing tran_sr_icmr unit TT/27", self.rep.screen_verdict("ic075", canon, dat))

    def test_screen_stops_on_non_slew_limited_rise_or_fall(self):
        ss = self.rep.SCREEN_POINTS["SS/-40"]
        for edge in ("rise", "fall"):
            for cls in ("inconclusive", "linear", "invalid", ""):
                canon, dat, tt = self._clean_ic075()
                dat["d"]["tran-sr-icmr"][ss][f"{edge}_class"] = cls
                why = self.rep.screen_verdict("ic075", canon, dat)
                self.assertTrue(any(r.startswith(f"tran_sr_icmr {edge} class") and r.endswith("SS/-40")
                                    for r in why), (edge, cls, why))

    def test_screen_stops_on_invalid_standard_slew(self):
        for col, bad in (("sr_rise_v_per_us", "nan"), ("sr_rise_v_per_us", "-1.0"), ("sr_fall_v_per_us", "nan")):
            canon, dat, tt = self._clean_ic075()
            dat["d"]["tran-sr"][tt][col] = bad
            why = self.rep.screen_verdict("ic075", canon, dat)
            self.assertTrue(any(r.startswith(f"tran_sr {col} invalid") for r in why), (col, bad, why))

    def test_stage2_full_grid_has_15_unique_points_and_keeps_failed_attempt_errors(self):
        m, canon, data = self.rep.get_all(stage2=True)
        d = data["ic075"]
        for sfx in ("ac", "tran-sr", "tran-sr-icmr"):
            self.assertEqual(len(d["d"][sfx]), 15, sfx)
        self.assertTrue(any("BATCH_MAX_CONCURRENT_INSTANCES" in e for e in d["errs"]))

    def test_power_delta_sign_ic075_above_canonical(self):
        m, canon, data = self.rep.get_all(stage2=True)
        for k, r in data["ic075"]["d"]["ac"].items():
            self.assertGreater(float(r["pq_w"]), float(canon["ac"][k]["pq_w"]))

    def test_mismatch_probe_flags_tt_boost_violation(self):
        m = self.rep.manifest()
        rid = m["variants"]["ic075"]["mc"][0]
        rows = list(csv.DictReader(open(self.rep.REC / f"{rid}.csv", newline="")))
        self.assertEqual(len(rows), 100)
        self.assertEqual(sum(1 for r in rows if abs(float(r["i_xms_ua"])) > 1.0), 6)


class EvidenceValidationTests(unittest.TestCase):
    """Static/mismatch DUT identity, bench/model provenance and duplicate-key handling (issue #197)."""

    IC075_S1 = "20261011-224549-15762af-8e3ebb"     # Stage 1 TT/27 record of ic075
    IC075_S2 = "20261012-002038-7d10f60-12f3e2"     # Stage 2 paired-grid record of ic075

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sim/opamp-characterization/variants"))
        import sink_bias_report
        cls.rep = sink_bias_report

    def _manifest_with(self, edit):
        import copy
        m = copy.deepcopy(self.rep.manifest())
        edit(m)
        return mock.patch.object(self.rep, "manifest", return_value=m)

    def _meta_with(self, rid, edit):
        import copy
        real = self.rep.read_meta

        def fake(r):
            meta = real(r)
            if r == rid:
                meta = copy.deepcopy(meta)
                edit(meta)
            return meta
        return mock.patch.object(self.rep, "read_meta", side_effect=fake)

    def _rows_with(self, rid, sfx, edit):
        import copy
        real = self.rep.read

        def fake(r, s=None):
            rows = real(r, s)
            if r == rid and s == sfx:
                rows = edit(copy.deepcopy(rows))
            return rows
        return mock.patch.object(self.rep, "read", side_effect=fake)

    # --- current evidence is accepted -------------------------------------------------------------
    def test_committed_evidence_validates(self):
        self.assertEqual(self.rep.check_provenance(self.rep.manifest()), [])
        m, canon, data = self.rep.get_all(stage2=True)
        self.assertEqual(len(data["ic075"]["static"]), 15)
        for tag, e in m["variants"].items():
            for rid in e.get("static", []) + e.get("mc", []):
                meta = self.rep.read_meta(rid)
                self.assertEqual(meta["dut"]["sha256"], self.rep.variant_sha(tag), rid)

    # --- 1. static / mismatch DUT identity ------------------------------------------------------
    def test_other_variants_static_record_rejected(self):
        def swap(m):
            m["variants"]["ic075"]["static"] = list(m["variants"]["ic090"]["static"])
        with self._manifest_with(swap), self.assertRaises(SystemExit) as cm:
            self.rep.get_all()
        self.assertIn("DUT hash", str(cm.exception))
        self.assertIn(self.rep.manifest()["variants"]["ic090"]["static"][0], str(cm.exception))

    def test_other_variants_mc_record_rejected(self):
        mc = self.rep.manifest()["variants"]["ic075"]["mc"][0]
        with self.assertRaises(SystemExit) as cm:
            self.rep.mc_rows(mc, "ic090")
        self.assertIn("DUT hash", str(cm.exception))

        def give(m):
            m["variants"]["ic090"]["mc"] = [mc]
        with self._manifest_with(give), self.assertRaises(SystemExit):
            self.rep.cmd_mc("ic090")

    def test_static_kind_and_tag_checked(self):
        m = self.rep.manifest()["variants"]["ic075"]
        with self.assertRaises(SystemExit) as cm:      # a mismatch record is not a static probe
            self.rep.static_rows(m["mc"][0], "ic075")
        self.assertIn("kind", str(cm.exception))
        sid = m["static"][0]
        with self._meta_with(sid, lambda d: d.update(tag="ic060")), self.assertRaises(SystemExit) as cm:
            self.rep.static_rows(sid, "ic075")
        self.assertIn("tag", str(cm.exception))

    def test_snapshot_not_matching_declared_hash_rejected(self):
        other = self.rep.read_meta(self.rep.manifest()["variants"]["ic090"]["static"][0])["dut"]["snapshot_path"]
        sid = self.rep.manifest()["variants"]["ic075"]["static"][0]
        for rid, run in ((sid, lambda: self.rep.static_rows(sid, "ic075")),
                         (self.IC075_S1, lambda: self.rep.load([self.IC075_S1], self.rep.variant_sha("ic075")))):
            with self._meta_with(rid, lambda d: d["dut"].update(snapshot_path=other)), \
                    self.assertRaises(SystemExit) as cm:
                run()
            self.assertIn("snapshot not verified", str(cm.exception), rid)

    def test_truncated_static_csv_rejected(self):
        sid = self.rep.manifest()["variants"]["ic075"]["static"][0]
        with self._rows_with(sid, None, lambda rows: rows[:-1]), self.assertRaises(SystemExit) as cm:
            self.rep.static_rows(sid, "ic075")
        self.assertIn("declared units", str(cm.exception))

    # --- 1b. bench / model provenance -----------------------------------------------------------
    def test_variant_pdk_bench_or_solver_drift_rejected(self):
        edits = {"pdk": lambda d: d["pdk"].update(installed_commit="0" * 40),
                 "bench": lambda d: d["matrix"].update(cl_f="5p"),
                 "solver": lambda d: d["matrix"]["execution"]["solver_settings"].update(reltol="1e-4"),
                 "runner_klt": lambda d: d["klt_jobs"][0]["remote"].update(runner_klt_version="0.7.0")}
        for what, edit in edits.items():
            with self._meta_with(self.IC075_S1, edit):
                probs = self.rep.check_provenance(self.rep.manifest())
                self.assertTrue(any(self.IC075_S1 in p for p in probs), (what, probs))
                with self.assertRaises(SystemExit):
                    self.rep.get_all()

    def test_static_probe_runner_drift_rejected(self):
        sid = self.rep.manifest()["variants"]["ic060"]["static"][0]
        with self._meta_with(sid, lambda d: d["remote"].update(runner_klt_version="0.7.0")):
            self.assertTrue(any(sid in p for p in self.rep.check_provenance(self.rep.manifest())))

    def test_variant_bench_body_differing_from_canonical_rejected(self):
        real = self.rep.snapshot_files

        def fake(meta):
            out = real(meta)
            if meta["record_id"] == self.IC075_S1:
                out["ac-body.spice"] = "sha256:" + "0" * 64
            return out
        with mock.patch.object(self.rep, "snapshot_files", side_effect=fake):
            probs = self.rep.check_provenance(self.rep.manifest())
        self.assertTrue(any("ac-body.spice differs from canonical" in p for p in probs), probs)

    def test_icmr_aware_steps_masked_only_and_checked_against_record(self):
        snap = self.rep.SNAP
        name = "tran-sr-icmr-sf-125C-1.8V-body.spice"
        a = (snap / "20261011-201913-046fe81-7c5771" / name).read_text()
        b = (snap / self.IC075_S2 / name).read_text()
        self.assertNotEqual(a, b)   # DUT-derived step low differs (0.6342 vs 0.6341 V)
        self.assertEqual(self.rep.bench_template(a, name)[0], self.rep.bench_template(b, name)[0])
        self.assertEqual(self.rep.bench_template(a, "ac-body.spice"), (a, None))   # no masking elsewhere

        def bump(rows):
            for r in rows:
                if r["corner"] == "sf" and float(r["temp_c"]) == 125.0:
                    r["step_low_v"] = "0.70"
            return rows
        with self._rows_with(self.IC075_S2, "tran-sr-icmr", bump):
            probs = self.rep.check_stimulus(self.IC075_S2, self.rep.read_meta(self.IC075_S2))
        self.assertTrue(any(name in p for p in probs), probs)

    # --- 2. duplicates and replay selection -----------------------------------------------------
    def test_record_listed_twice_rejected(self):
        with self.assertRaises(SystemExit) as cm:
            self.rep.load([self.IC075_S1, self.IC075_S1], self.rep.variant_sha("ic075"))
        self.assertIn("more than once", str(cm.exception))

        def twice(m):
            m["variants"]["ic075"]["static"] *= 2
        with self._manifest_with(twice), self.assertRaises(SystemExit):
            self.rep.get_all()

    def test_duplicate_key_within_one_record_rejected(self):
        for sfx in ("ac", "tran-sr"):
            with self._rows_with(self.IC075_S1, sfx, lambda rows: rows + rows), \
                    self.assertRaises(SystemExit) as cm:
                self.rep.load([self.IC075_S1], self.rep.variant_sha("ic075"))
            self.assertIn("duplicate measurement key", str(cm.exception), sfx)
        sid = self.rep.manifest()["variants"]["ic075"]["static"][0]

        def dup_static(rows):
            rows[1] = dict(rows[0])
            return rows
        with self._rows_with(sid, None, dup_static), self.assertRaises(SystemExit) as cm:
            self.rep.static_rows(sid, "ic075")
        self.assertIn("duplicate measurement key", str(cm.exception))

    def _tt(self, rows, col, value):
        for r in rows:
            if r["corner"] == "tt" and float(r["temp_c"]) == 27.0:
                r[col] = value
        return rows

    def test_conflicting_cross_stage_replicate_rejected(self):
        ids = self.rep.manifest()["variants"]["ic075"]["ids"] + [self.IC075_S2]
        for col, value in (("sr_fall_v_per_us", "17.5"), ("sr_fall_v_per_us", "")):   # differs / failed
            with self._rows_with(self.IC075_S2, "tran-sr", lambda rows: self._tt(rows, col, value)), \
                    self.assertRaises(SystemExit) as cm:
                self.rep.load(ids, self.rep.variant_sha("ic075"))
            msg = str(cm.exception)
            self.assertIn("conflicting duplicate", msg)
            self.assertIn(self.IC075_S1, msg)
            self.assertIn(self.IC075_S2, msg)

    def test_agreeing_replicates_select_last_listed_and_keep_all_sources(self):
        tt = self.rep.SCREEN_POINTS["TT/27"]
        s1 = self.rep.manifest()["variants"]["ic075"]["ids"]
        # elapsed_s is run timing: replicates may differ there and still agree.
        with self._rows_with(self.IC075_S2, "tran-sr", lambda rows: self._tt(rows, "elapsed_s", "999")):
            log = []
            d, errs = self.rep.load(s1 + [self.IC075_S2], self.rep.variant_sha("ic075"), log)
        row = d["tran-sr"][tt]
        self.assertEqual(row["_records"], [self.IC075_S1, self.IC075_S2])
        self.assertEqual(row["elapsed_s"], "999")          # the last-listed record's row is selected
        self.assertIn({"table": "tran-sr", "key": tt, "selected": self.IC075_S2,
                       "replicates": [self.IC075_S1]}, log)
        self.assertTrue(any("BATCH_MAX_CONCURRENT_INSTANCES" in e for e in errs))   # failures retained
        d2, _ = self.rep.load([self.IC075_S2] + s1, self.rep.variant_sha("ic075"))
        self.assertEqual(d2["tran-sr"][tt]["_records"], [self.IC075_S2, self.IC075_S1])

    def test_committed_replicates_are_the_known_overlaps(self):
        m, canon, data = self.rep.get_all(stage2=True)
        self.assertEqual(len(m["_canonical_replicates"]), 15)     # canonical tran-sr re-run
        self.assertEqual(len(data["ic075"]["replicates"]), 11)    # Stage 1 screen points re-measured in Stage 2
        self.assertEqual(data["ic090"]["replicates"], [])
        self.assertEqual(data["ic060"]["replicates"], [])
