"""Simulator-free tests for variants/input-stage tooling (issue #359).

Checks the committed variant netlist against its generator, the collation
manifest against the committed records, the generated report against the
records, and the collate merge policy (role filtering, replicate agreement,
conflict refusal) on synthetic rows.
"""

import copy
import json
import unittest
from pathlib import Path

from _paths import EXP, load_module

VAR = EXP / "variants"
ISR = load_module("input_stage_rebias", VAR / "input-stage" / "input_stage_rebias.py")
COL = load_module("input_stage_collate", VAR / "input-stage" / "collate.py")


def cards(text):
    out = {}
    for line in text.replace("\n+", " ").splitlines():
        if line.startswith("XM"):
            tok = line.split()
            kv = dict(t.split("=") for t in tok if "=" in t)
            out[tok[0]] = (tok[1:6], float(kv["W"]), float(kv["L"]), int(kv["m"]), int(kv["nf"]))
    return out


class VariantNetlist(unittest.TestCase):
    def test_committed_file_matches_generator(self):
        self.assertEqual(ISR.check(), [])

    def test_only_input_stage_cards_differ_canonical_verbatim(self):
        var = cards(ISR.VARIANT.read_text())
        canon = cards(ISR.CANON.read_text())
        self.assertEqual(set(var), set(canon))
        changed = {n for n in var if var[n] != canon[n]}
        self.assertEqual(changed, {"XM1", "XM2", "XM3", "XM4", "XM6"})
        # XRz/XCc verbatim-copy is covered by ISR.check(); they are not MOS cards.

    def test_widths_on_manufacturing_grid(self):
        w = ISR.widths()
        for name in ("pair", "mirror"):
            self.assertTrue(ISR.ss.legal(w[name]), w[name])

    def test_mirror_ratio_law_preserved(self):
        var = cards(ISR.VARIANT.read_text())
        self.assertEqual(var["XM3"][1], var["XM4"][1])
        self.assertEqual(var["XM3"][1], var["XM6"][1])
        self.assertEqual(var["XM6"][3], 10 * var["XM3"][3])
        self.assertEqual(var["XM1"][1], var["XM2"][1])


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

    def test_merge_role_filtering(self):
        rows = [{"corner": "sf", "temp_c": -40.0, "vdd_v": 1.8, "vpp_v": "1.0", "elapsed_s": "1"},
                {"corner": "sf", "temp_c": -40.0, "vdd_v": 1.62, "vpp_v": "0.9", "elapsed_s": "1"}]
        import tempfile
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
        import tempfile
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
