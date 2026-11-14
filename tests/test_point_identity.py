"""Simulator-free tests for sim/lib/point_identity.py — the single owner of the
(corner, temp_c, vdd_v) measurement-point identity (issue #291).

Two jobs:

* unit-test the owner itself (normalisation, validation, duplicate reporting);
* pin the property the issue is actually about — that the two *validating*
  consumers (`design/bin/spec_figures_check.py`'s `check_matrix`, the CI gate on
  spec/target-spec.md section 2, and
  `sim/opamp-characterization/variants/compare.py`'s `index_rows`) now agree,
  row for row, about whether a record row is well formed. Before this module
  they disagreed on a blank corner, a whitespace-padded corner and a nonfinite
  temp_c; those three inputs are the regression cases below.

No simulator, no PDK, no committed evidence is read or written.
"""

import csv
import unittest
from pathlib import Path

import _paths

pi = _paths.load_module("point_identity", _paths.REPO / "sim" / "lib" / "point_identity.py")
sf = _paths.load_module("spec_figures_check_pi", _paths.REPO / "design" / "bin" / "spec_figures_check.py")
cmp_mod = _paths.load_module("variant_compare_pi", _paths.EXP / "variants" / "compare.py")

CONSUMERS = (
    Path("design/bin/spec_figures_check.py"),
    Path("sim/opamp-characterization/variants/compare.py"),
    Path("sim/opamp-characterization/variants/sink_bias_report.py"),
)


def row(corner="tt", temp_c="27", vdd_v="1.8", **kw):
    return dict({"corner": corner, "temp_c": temp_c, "vdd_v": vdd_v}, **kw)


class NormaliseTests(unittest.TestCase):
    def test_corner_is_stripped(self):
        for raw in (" tt ", "tt\t", "\ntt", "tt"):
            self.assertEqual(pi.norm_corner(raw), "tt")

    def test_blank_or_missing_corner_rejected(self):
        for raw in ("", "   ", "\t", None):
            with self.assertRaises(ValueError):
                pi.norm_corner(raw)

    def test_num_rounds_to_six_decimals(self):
        self.assertEqual(pi.norm_num("1.80"), 1.8)
        self.assertEqual(pi.norm_num(27), 27.0)
        self.assertEqual(pi.norm_num("1.2345674"), 1.234567)

    def test_num_rejects_nonfinite(self):
        for raw in ("nan", "NaN", "inf", "-inf", float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                pi.norm_num(raw)

    def test_num_rejects_junk(self):
        for raw in ("", "abc", None, {}):
            with self.assertRaises((TypeError, ValueError)):
                pi.norm_num(raw)

    def test_point_key_full_tuple(self):
        self.assertEqual(pi.point_key(row(corner=" tt ", temp_c="27.0", vdd_v="1.80")),
                         ("tt", 27.0, 1.8))

    def test_point_key_honours_supply_key(self):
        r = {"corner": "ss", "temp_c": "-40", "vdd_core_v": "1.62"}
        self.assertEqual(pi.point_key(r, "vdd_core_v"), ("ss", -40.0, 1.62))

    def test_point_key_raises_identity_exc(self):
        for bad in (row(corner=""), row(temp_c="nan"), row(vdd_v="inf"),
                    {"corner": "tt", "temp_c": "27"}):
            with self.assertRaises(pi.IDENTITY_EXC):
                pi.point_key(bad)

    def test_supply_is_part_of_the_identity(self):
        """Same corner and temperature at two supplies are two distinct points."""
        a = pi.point_key(row(vdd_v="1.62"))
        b = pi.point_key(row(vdd_v="1.98"))
        self.assertNotEqual(a, b)


class ValidateRowsTests(unittest.TestCase):
    def test_clean_rows_have_no_errors(self):
        v = pi.validate_rows([row(gain="60"), row(corner="ss", temp_c="-40", vdd_v="1.62", gain="68")],
                             ["gain"], "lbl")
        self.assertEqual((v.errors, v.duplicate_errors), ([], []))
        self.assertEqual(sorted(v.index), [("ss", -40.0, 1.62), ("tt", 27.0, 1.8)])

    def test_unusable_identity_is_a_row_error_and_is_not_keyed(self):
        v = pi.validate_rows([row(corner=""), row(temp_c="nan")], ["gain"], "lbl")
        self.assertEqual(len(v.errors), 2)
        for i, e in enumerate(v.errors, 1):
            self.assertIn(f"lbl: row {i} has no usable corner/temp_c/vdd_v", e)
        self.assertEqual(v.index, {})
        self.assertEqual(v.seen, {})

    def test_nonfinite_or_missing_column(self):
        v = pi.validate_rows([row(gain="nan"), row(corner="ss", temp_c="-40", vdd_v="1.62")],
                             ["gain"], "lbl")
        self.assertEqual(len(v.errors), 2)
        self.assertIn("point tt/27/1.8 has nonfinite or missing gain: 'nan'", v.errors[0])
        self.assertIn("has nonfinite or missing gain: None", v.errors[1])

    def test_duplicates_are_reported_separately(self):
        v = pi.validate_rows([row(gain="60"), row(temp_c="27.0", vdd_v="1.80", gain="61")],
                             ["gain"], "lbl")
        self.assertEqual(v.errors, [])
        self.assertEqual(v.duplicate_errors, ["lbl: duplicate point tt/27/1.8 in rows [1, 2]"])

    def test_nonfinite_identity_can_no_longer_defeat_the_duplicate_check(self):
        """A nan key is never equal to itself, so it used to slip past the
        duplicate-point check entirely. It is now a row error instead."""
        v = pi.validate_rows([row(temp_c="nan"), row(temp_c="nan")], ["gain"], "lbl")
        self.assertEqual(v.duplicate_errors, [])
        self.assertEqual(len(v.errors), 2)
        self.assertEqual(v.seen, {})

    def test_label_and_fmt_are_the_callers(self):
        v = pi.validate_rows([row(gain="nan")], ["gain"], "matrix m",
                             fmt=lambda k: f"{k[0]}/{k[1]:g} C/{k[2]:g} V")
        self.assertIn("matrix m: point tt/27 C/1.8 V has nonfinite or missing gain", v.errors[0])


class SingleOwnerTests(unittest.TestCase):
    """The convention has one home: no consumer re-implements it."""

    def test_consumers_import_the_owner(self):
        for rel in CONSUMERS:
            src = (_paths.REPO / rel).read_text()
            self.assertIn("point_identity", src, f"{rel} does not reference the owner")

    def test_no_consumer_reimplements_the_rounding(self):
        """`round(float(x), 6)` on an identity field is the duplicated line this
        issue removed; it must not come back in a consumer."""
        for rel in CONSUMERS:
            src = (_paths.REPO / rel).read_text()
            for ident in ("corner", "temp_c", "vdd_v"):
                self.assertNotIn(f'round(float(r["{ident}"]), 6)', src, str(rel))
            self.assertNotIn("round(float(x), 6)", src, str(rel))

    def test_owner_is_stdlib_only(self):
        src = (_paths.REPO / "sim" / "lib" / "point_identity.py").read_text()
        for banned in ("import numpy", "import pandas", "import yaml", "import requests"):
            self.assertNotIn(banned, src)


class CommittedRecordsTests(unittest.TestCase):
    """Issue #291 step 2, made durable: every committed record CSV must satisfy
    the *union* of what the three copies used to accept.

    This ran as a pre-check before the shared helper was tightened (140 CSVs,
    13095 rows, 0 violations), so no committed evidence was loosened to make the
    stricter rule pass. Keeping it as a test means a future record that would
    split the validators again is a CI failure, not a silent divergence.
    """

    def test_every_committed_record_has_a_usable_point_identity(self):
        paths = sorted(_paths.REPO.glob("sim/*/records/*.csv"))
        self.assertGreater(len(paths), 100, "record corpus not found")
        checked, problems = 0, []
        for path in paths:
            with open(path, newline="") as fh:
                rows = list(csv.DictReader(fh))
            if not rows or not {"corner", "temp_c"} <= set(rows[0]):
                continue
            supply = "vdd_v" if "vdd_v" in rows[0] else None
            for i, r in enumerate(rows, 1):
                checked += 1
                try:
                    pi.norm_corner(r["corner"])
                    pi.norm_num(r["temp_c"])
                    if supply:
                        pi.norm_num(r[supply])
                except pi.IDENTITY_EXC as e:
                    rel = path.relative_to(_paths.REPO)
                    problems.append(f"{rel}: row {i}: {e!r}")
        self.assertEqual(problems, [], "\n".join(problems[:20]))
        self.assertGreater(checked, 1000, "too few rows checked")


class ValidatorAgreementTests(unittest.TestCase):
    """The regression this issue exists for: the CI gate and the comparison
    generator must reach the same verdict on the same row.

    `check_matrix` additionally reports the authored expected set (`want`/`seen`
    arithmetic it still owns), so agreement is asserted on the *row verdict*:
    whether the row is rejected as malformed, and whether it is keyed.
    """

    MATRIX = {"axes": {"corner": ["tt"], "temp_c": [27.0]},
              "supply": {"mode": "cartesian", "values": [1.8]}}
    KEYS = ["gain_dc_db"]

    def gate_errors(self, rows):
        return sf.check_matrix("m", self.MATRIX, rows, self.KEYS)

    def compare_errors(self, rows):
        try:
            cmp_mod.index_rows(rows, self.KEYS, source="t")
            return []
        except cmp_mod.CompareError as e:
            return str(e).splitlines()

    def assertBothRejectRow(self, rows, n, needle):
        gate = self.gate_errors(rows)
        comp = self.compare_errors(rows)
        want = f"row {n} has no usable corner/temp_c/vdd_v"
        self.assertTrue(any(want in e and needle in e for e in gate),
                        f"spec_figures_check did not reject row {n}: {gate}")
        self.assertTrue(any(want in e and needle in e for e in comp),
                        f"compare did not reject row {n}: {comp}")
        # neither validator may describe a malformed row as a legitimate point
        self.assertFalse(any("unexpected point" in e for e in gate), gate)

    def test_blank_corner_rejected_by_both(self):
        self.assertBothRejectRow([row(corner="", gain_dc_db="70")], 1, "empty corner")

    def test_padded_corner_accepted_by_both_and_keyed_the_same(self):
        rows = [row(corner=" tt ", gain_dc_db="70")]
        self.assertEqual(self.gate_errors(rows), [], "padded corner is not an unexpected point")
        self.assertEqual(list(cmp_mod.index_rows(rows, self.KEYS, source="t")), [("tt", 27.0, 1.8)])

    def test_nonfinite_temp_rejected_by_both(self):
        rows = [row(temp_c="nan", gain_dc_db="70"), row(temp_c="nan", gain_dc_db="71")]
        for n in (1, 2):
            self.assertBothRejectRow(rows, n, "nonfinite value")
        gate = self.gate_errors(rows)
        # the authored point really is absent, but it is reported once, not
        # alongside two "unexpected point tt/nan C/1.8 V" lines
        self.assertEqual([e for e in gate if "missing expected point" in e],
                         ["matrix m: missing expected point tt/27 C/1.8 V"])

    def test_clean_row_passes_both(self):
        rows = [row(gain_dc_db="70")]
        self.assertEqual(self.gate_errors(rows), [])
        self.assertEqual(self.compare_errors(rows), [])

    def test_duplicate_point_rejected_by_both(self):
        rows = [row(gain_dc_db="70"), row(temp_c="27.0", vdd_v="1.80", gain_dc_db="71")]
        self.assertTrue(any("duplicate point tt/27 C/1.8 V in rows [1, 2]" in e
                            for e in self.gate_errors(rows)))
        self.assertTrue(any("duplicate point TT/27C/1.8V in rows [1, 2]" in e
                            for e in self.compare_errors(rows)))

    def test_authored_matrix_corner_is_normalised_too(self):
        """A stray-whitespace authored corner must key like the record's, or the
        expected set could never match a well-formed row."""
        m = {"axes": {"corner": [" tt "], "temp_c": [27.0]},
             "supply": {"mode": "cartesian", "values": [1.8]}}
        self.assertEqual(sf.check_matrix("m", m, [row(gain_dc_db="70")], self.KEYS), [])


class SinkBiasReportIdentityTests(unittest.TestCase):
    """The third copy: same key, and now the validation it never had."""

    def setUp(self):
        self.sbr = _paths.load_module(
            "sink_bias_report_pi", _paths.EXP / "variants" / "sink_bias_report.py")

    def test_key_is_the_shared_identity(self):
        self.assertEqual(self.sbr.key(row(corner=" tt ", temp_c="27.0", vdd_v="1.80")),
                         pi.point_key(row(corner="tt")))

    def test_unique_rows_surfaces_a_malformed_row(self):
        for bad, needle in ((row(corner=""), "empty corner"),
                            (row(temp_c="nan"), "nonfinite value")):
            with self.assertRaises(SystemExit) as cm:
                self.sbr.unique_rows([row(), bad], self.sbr.key, "rec-ac")
            msg = str(cm.exception)
            self.assertIn("rec-ac: row 2 has no usable measurement key", msg)
            self.assertIn(needle, msg)

    def test_unique_rows_still_rejects_an_in_record_duplicate(self):
        with self.assertRaises(SystemExit) as cm:
            self.sbr.unique_rows([row(), row(temp_c="27.0")], self.sbr.key, "rec-ac")
        self.assertIn("duplicate measurement key", str(cm.exception))

    def test_unique_rows_accepts_clean_rows(self):
        out = self.sbr.unique_rows([row(), row(corner="ss", temp_c="-40", vdd_v="1.62")],
                                   self.sbr.key, "rec-ac")
        self.assertEqual(sorted(out), [("ss", -40.0, 1.62), ("tt", 27.0, 1.8)])


if __name__ == "__main__":
    unittest.main()
