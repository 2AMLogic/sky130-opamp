"""Simulator-free tests for variants/sink_bias_margin.py and its committed netlists (issue #197)."""

import csv
import json
import re
import sys
import unittest
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
