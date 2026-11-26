"""Simulator-free tests for variants/input-stage tooling (issue #359).

Checks the committed variant netlist against its generator, the collation
manifest against the committed records, the generated report against the
records, and the collate merge policy (role filtering, replicate agreement,
conflict refusal) on synthetic rows.
"""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from _paths import EXP, load_module

VAR = EXP / "variants"
ISR = load_module("input_stage_rebias", VAR / "input-stage" / "input_stage_rebias.py")
COL = load_module("input_stage_collate", VAR / "input-stage" / "collate.py")
from _gmid import mos_cards


class VariantNetlist(unittest.TestCase):
    def test_committed_file_matches_generator(self):
        self.assertEqual(ISR.check(), [])

    def test_comment_and_blank_before_xm5_continuation_keep_geometry(self):
        text = ISR.CANON.read_text()
        continuation = text.index("\n+", text.index("\nXM5 "))
        annotated = text[:continuation] + "\n*.ipin tail\n" + text[continuation:]
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "annotated.spice"
            path.write_text(annotated)
            areas = COL.gate_area(path)
        self.assertAlmostEqual(areas[0]["XM5"], 7.820 * 1.2 * 2)
        self.assertEqual(areas, COL.gate_area(ISR.CANON))
        self.assertEqual(mos_cards(annotated), mos_cards(text))

    def test_end_of_line_comment_does_not_override_xm5_params(self):
        text = ISR.CANON.read_text()
        cont = text.index("\n+", text.index("\nXM5 "))
        eol = text.index("\n", cont + 1)
        base = COL.gate_area(ISR.CANON)
        for suffix in ("; previous m=1", " $ previous m=1", " // previous m=1"):
            with self.subTest(suffix=suffix):
                with tempfile.TemporaryDirectory() as td:
                    path = Path(td) / "eol.spice"
                    path.write_text(text[:eol] + suffix + text[eol:])
                    areas = COL.gate_area(path)
                self.assertAlmostEqual(areas[0]["XM5"], 7.820 * 1.2 * 2)
                self.assertEqual(areas, base)

    def test_gate_area_accepts_integer_valued_decimal_m_and_nf(self):
        text = ISR.CANON.read_text()
        xm5 = text.index("\nXM5 ")
        base = COL.gate_area(ISR.CANON)
        for old, new in (("m=2", "m=2.0"), ("nf=1", "nf=1.0")):
            with self.subTest(param=old):
                end = text.index("\nXM", xm5 + 1) if "\nXM" in text[xm5 + 1:] else len(text)
                card = text[xm5:end]
                self.assertEqual(card.count(old) >= 1, True, old)
                with tempfile.TemporaryDirectory() as td:
                    path = Path(td) / "decimal.spice"
                    path.write_text(text[:xm5] + card.replace(old, new, 1) + text[end:])
                    self.assertEqual(COL.gate_area(path), base)

    def test_gate_area_rejects_fractional_m_and_nf(self):
        for tail in ("nf=1 m=2.5", "nf=1.5 m=2"):
            with self.subTest(tail=tail):
                with tempfile.TemporaryDirectory() as td:
                    path = Path(td) / "frac.spice"
                    path.write_text("XM5 tail ibias vss vss sky130_fd_pr__nfet_01v8 L=1.2 W=7.820 "
                                    + tail + "\n")
                    with self.assertRaisesRegex(COL.CollateError, "cannot parse MOS card: XM5"):
                        COL.gate_area(path)

    def test_gate_area_rejects_xm5_missing_m(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "truncated.spice"
            path.write_text("XM5 tail ibias vss vss sky130_fd_pr__nfet_01v8 L=1.2 W=7.820 nf=1\n"
                            "+ mult=2\n")
            with self.assertRaisesRegex(COL.CollateError, "cannot parse MOS card: XM5"):
                COL.gate_area(path)

    def test_only_input_stage_cards_differ_canonical_verbatim(self):
        var = mos_cards(ISR.VARIANT.read_text())
        canon = mos_cards(ISR.CANON.read_text())
        self.assertEqual(set(var), set(canon))
        changed = {n for n in var if var[n] != canon[n]}
        self.assertEqual(changed, {"XM1", "XM2", "XM3", "XM4", "XM6"})
        # XRz/XCc verbatim-copy is covered by ISR.check(); they are not MOS cards.

    def test_widths_on_manufacturing_grid(self):
        w = ISR.widths()
        for name in ("pair", "mirror"):
            self.assertTrue(ISR.legal(w[name]), w[name])

    def test_mirror_ratio_law_preserved(self):
        var = mos_cards(ISR.VARIANT.read_text())
        self.assertEqual(var["XM3"].width, var["XM4"].width)
        self.assertEqual(var["XM3"].width, var["XM6"].width)
        self.assertEqual(var["XM6"].m, 10 * var["XM3"].m)
        self.assertEqual(var["XM1"].width, var["XM2"].width)


class SizingReport(unittest.TestCase):
    """The `sizing` replay PLAN.md cites (regression for issue #397: series()
    must load its rows through the shared _gmid loader, keeping the nonzero
    gm/ID filter, density units and tuple sort — the report reads Vth from the
    first tuple of each corner/temperature group)."""

    @classmethod
    def setUpClass(cls):
        cls.report = ISR.sizing_report()

    def test_report_covers_all_fifteen_corner_temperature_groups(self):
        for c in ("ss", "tt", "ff", "sf", "fs"):
            for t in ("-40", "27", "125"):
                self.assertIn(f"\n{c}/{t}C ", self.report)

    def test_ss_40c_estimates_read_vth_from_the_weakest_gm_id_row(self):
        self.assertIn("ss/-40C   0.6669  1.0652 |", self.report)
        self.assertIn(" 1.732 vs 1.62  <== SUM+margin > VDD", self.report)
        self.assertIn("estimated Vin_min = Vth_n = 0.6669 V.", self.report)
        self.assertIn("measured ICMR high edge 1.1686 V (Vth2_eff = 0.676 V implied)",
                      self.report)
        self.assertIn("At zero mirror overdrive, estimated Vin_max = 1.230 V.", self.report)

    def test_fs_40c_consumer_point_estimate(self):
        self.assertIn("FS/-40C consumer point: pair Vov 47 -> 5 mV", self.report)
        self.assertIn("0.7388 V -> ~0.697 V vs consumer point 0.73 V"
                      " (currently missed by 0.0088 V)", self.report)

    def test_tt_27c_grid_snapped_widths_cited_by_the_plan(self):
        self.assertIn("W = 5 uA / 0.345541 uA/um = 14.4701 -> 14.470 um (grid)",
                      self.report)
        self.assertIn("W = 5 uA / 0.364694 uA/um = 13.7101 -> 13.710 um (grid",
                      self.report)


class Collation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((VAR / "input-stage" / "records.json").read_text())

    def test_manifest_records_exist_and_declare_expected_dut(self):
        for group, sha in (("variant", self.manifest["variant"]["sha256"]),
                           ("canonical", self.manifest["canonical"]["sha256"])):
            for e in self.manifest[group]["ids"]["runs"]:
                rec = json.loads((EXP / "records" / f"{e['id']}.json").read_text())
                self.assertEqual(rec["dut"]["sha256"], sha, e["id"])

    def test_variant_records_differ_from_canonical_dut(self):
        self.assertNotEqual(self.manifest["variant"]["sha256"],
                            self.manifest["canonical"]["sha256"])

    def test_report_is_current(self):
        text = COL.build(self.manifest)
        self.assertEqual((VAR / "input-stage" / "report.out.md").read_text(), text)

    def test_report_carries_required_callouts_and_verdicts(self):
        text = (VAR / "input-stage" / "report.out.md").read_text()
        for pt in ("SS/-40C/1.62V", "SF/-40C/1.62V", "FS/-40C/1.62V"):
            self.assertIn(pt, text)
        for section in ("## ICMR window edges", "## Fixed-common-mode swing",
                        "## ICMR-aware vs standard fall slew", "Named callouts",
                        "## Verdict inputs", "## Drawn MOS gate area",
                        "Offset impact"):
            self.assertIn(section, text)

    def test_report_prints_coverage_for_both_duts(self):
        text = COL.build(self.manifest)
        self.assertIn("baseline ICMR covers the target window at 17/17 points "
                      "and 0.73 V at 15/17 points", text)
        self.assertIn("candidate ICMR covers the target window at 17/17 points "
                      "and 0.73 V at 17/17 points", text)
        table = text.split("## ICMR window edges")[1].split("## ")[0]
        misses = [line.split("|")[1].strip() for line in table.splitlines()
                  if line.endswith(" | 0 |")]
        self.assertEqual(misses, ["FS/-40C/1.62V", "FS/-40C/1.8V"])

    def test_named_slew_recovery_and_swing_edges(self):
        callouts = COL.build(self.manifest).split("## Named callouts")[1].split("## ")[0]
        for pt, share in (("SS", "25.8%"), ("SF", "4.2%"), ("FS", "36.2%")):
            self.assertRegex(callouts, rf"\| {pt}/-40C/1\.62V \|[^\n]*\| {share} \|")
        self.assertIn("0.2545–1.2029", callouts)
        self.assertIn("0.2249–1.2355", callouts)

    def test_merge_role_filtering(self):
        rows = [{"corner": "sf", "temp_c": -40.0, "vdd_v": 1.8, "vpp_v": "1.0", "elapsed_s": "1"},
                {"corner": "sf", "temp_c": -40.0, "vdd_v": 1.62, "vpp_v": "0.9", "elapsed_s": "1"}]
        with tempfile.TemporaryDirectory() as td:
            recdir = Path(td)
            (recdir / "r1.json").write_text(json.dumps({"errors": []}))
            for a in COL.ANALYSES:
                want = ["corner", "temp_c", "vdd_v"] + (["vpp_v"] if a == "dc_swing" else [])
                with open(recdir / f"r1-{COL.SUFFIX_BY_ANALYSIS[a]}.csv", "w") as fh:
                    fh.write(",".join(want + ["elapsed_s"]) + "\n")
                    for r in rows:
                        fh.write(",".join(str(r[k]) for k in want + ["elapsed_s"]) + "\n")
            old = COL.REC
            COL.REC = recdir
            try:
                merged, log, failed = COL.merge([("r1", "paired")])
                self.assertIn(("sf", -40.0, 1.8), merged["dc_swing"])
                self.assertNotIn(("sf", -40.0, 1.62), merged["dc_swing"])
                merged, _, _ = COL.merge([("r1", "added")])
                self.assertNotIn(("sf", -40.0, 1.8), merged["dc_swing"])
                self.assertIn(("sf", -40.0, 1.62), merged["dc_swing"])
            finally:
                COL.REC = old

    def test_merge_replicate_agreement_and_conflict(self):
        base = [{"corner": "ss", "temp_c": -40.0, "vdd_v": 1.62, "vpp_v": "1.01", "elapsed_s": "1"}]
        with tempfile.TemporaryDirectory() as td:
            recdir = Path(td)
            for rid, vpp in (("r1", "1.01"), ("r2", "1.01"), ("r3", "1.02")):
                (recdir / f"{rid}.json").write_text(json.dumps({"errors": []}))
                for a in COL.ANALYSES:
                    want = ["corner", "temp_c", "vdd_v"] + (["vpp_v"] if a == "dc_swing" else [])
                    with open(recdir / f"{rid}-{COL.SUFFIX_BY_ANALYSIS[a]}.csv", "w") as fh:
                        fh.write(",".join(want + ["elapsed_s"]) + "\n")
                        fh.write(f"ss,-40.0,1.62,{vpp},2\n" if a == "dc_swing" else "")
            old = COL.REC
            COL.REC = recdir
            try:
                merged, log, _ = COL.merge([("r1", "paired"), ("r2", "paired")])
                self.assertTrue(any("agreeing replicate" in l for l in log))
                self.assertEqual(merged["dc_swing"][("ss", -40.0, 1.62)]["_records"], ["r1", "r2"])
                with self.assertRaises(COL.CollateError):
                    COL.merge([("r1", "paired"), ("r3", "paired")])
            finally:
                COL.REC = old


class ReportFacts(unittest.TestCase):
    """The structural claims of the screen, re-derived from the merged records."""

    @classmethod
    def setUpClass(cls):
        m = json.loads((VAR / "input-stage" / "records.json").read_text())
        cls.cand, _, _ = COL.merge([(e["id"], e["points"]) for e in m["variant"]["ids"]["runs"]])
        cls.base, _, _ = COL.merge([(e["id"], e["points"]) for e in m["canonical"]["ids"]["runs"]])

    def test_binding_corner_swing_improves_but_stays_short_of_target(self):
        k = ("ss", -40.0, 1.62)
        c = float(self.cand["dc_swing"][k]["vpp_v"])
        b = float(self.base["dc_swing"][k]["vpp_v"])
        self.assertGreater(c, b)
        self.assertLess(c, COL.SWING_TGT_VPP)

    def test_icmr_window_wider_at_every_common_point(self):
        common = set(self.cand["icmr"]) & set(self.base["icmr"])
        self.assertGreaterEqual(len(common), 17)
        for k in common:
            self.assertGreater(float(self.cand["icmr"][k]["icmr_width_v"]),
                               float(self.base["icmr"][k]["icmr_width_v"]), k)

    def test_phase_margin_breaks_are_reported_not_hidden(self):
        bad = [k for k in self.cand["ac"] if float(self.cand["ac"][k]["phase_margin_deg"]) < 60.0]
        text = (VAR / "input-stage" / "report.out.md").read_text()
        self.assertIn(f"cand {len(bad)}/{len(self.cand['ac'])} points", text)

    def test_added_tuple_coverage(self):
        for k in (("sf", -40.0, 1.62), ("fs", -40.0, 1.62)):
            for a in ("ac", "tran_sr", "dc_swing", "swing_fixcm", "icmr", "tran_sr_icmr"):
                self.assertIn(k, self.cand[a], (a, k))


if __name__ == "__main__":
    unittest.main()
