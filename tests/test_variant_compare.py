"""Simulator-free tests for sim/opamp-characterization/variants/compare.py.

Issue #161: a comparison point is the full (corner, temp_c, vdd_v) tuple.
Fixtures are synthetic CSVs in a temp records dir; no committed evidence is
read or written except the read-only single-supply regression at the end.
"""

import contextlib
import csv
import io
import random
import shutil
import tempfile
import unittest
from pathlib import Path

import _paths

cmp = _paths.load_module("variant_compare", _paths.EXP / "variants" / "compare.py")

HEADERS = {
    "ac": ["corner", "temp_c", "vdd_v", "pq_w", "gain_dc_db", "gbw_hz", "phase_margin_deg"],
    "tran-sr": ["corner", "temp_c", "vdd_v", "sr_rise_v_per_us", "sr_fall_v_per_us"],
    "dc-swing": ["corner", "temp_c", "vdd_v", "vpp_v"],
}


def point(corner, temp, vdd, gain=60.0, gbw=2e7, pm=60.0, pq=1e-4, rise=20.0, fall=12.0, vpp=1.0):
    return {"corner": corner, "temp_c": temp, "vdd_v": vdd, "gain_dc_db": gain, "gbw_hz": gbw,
            "phase_margin_deg": pm, "pq_w": pq, "sr_rise_v_per_us": rise,
            "sr_fall_v_per_us": fall, "vpp_v": vpp}


class _RecordsDir(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="variant-compare-"))
        self.addCleanup(shutil.rmtree, self.dir)

    def write(self, rid, points, raw=None):
        """Write all three analysis CSVs for `rid`; raw[suffix] overrides text."""
        for suf, cols in HEADERS.items():
            path = self.dir / f"{rid}-{suf}.csv"
            if raw and suf in raw:
                path.write_text(raw[suf])
                continue
            with open(path, "w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(cols)
                for p in points:
                    w.writerow([p[c] for c in cols])

    def run_cli(self, *ids):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = cmp.main(["compare.py", *ids], records=str(self.dir))
        return rc, out.getvalue(), err.getvalue()


class MultiSupplyIdentity(_RecordsDir):
    def test_two_supplies_at_same_corner_temp_both_retained(self):
        self.write("c", [point("tt", 27.0, 1.62, gain=61.0), point("tt", 27.0, 1.98, gain=65.0)])
        rows = cmp.load("c", "ac", str(self.dir))
        self.assertEqual(set(rows), {("tt", 27.0, 1.62), ("tt", 27.0, 1.98)})
        self.assertEqual(float(rows[("tt", 27.0, 1.62)]["gain_dc_db"]), 61.0)
        self.assertEqual(float(rows[("tt", 27.0, 1.98)]["gain_dc_db"]), 65.0)

    def test_row_order_independent(self):
        pts = [point(c, t, v, gain=60 + i, vpp=1.0 if c != "ss" else 0.0)
               for i, (c, t, v) in enumerate([("tt", 27.0, 1.62), ("tt", 27.0, 1.98), ("ss", -40.0, 1.62),
                                              ("ss", 125.0, 1.62), ("ff", 125.0, 1.98)])]
        self.write("b", pts)
        self.write("c", pts)
        rc, ref, _ = self.run_cli("c", "b")
        self.assertEqual(rc, 0)
        rng = random.Random(161)
        for _ in range(5):
            shuffled = pts[:]
            rng.shuffle(shuffled)
            self.write("c", shuffled)
            self.write("b", list(reversed(shuffled)))
            rc, out, _ = self.run_cli("c", "b")
            self.assertEqual(rc, 0)
            self.assertEqual(out, ref)
        # vpp ties at both SS points: deterministic label plus explicit tie count
        self.assertIn("0 V @ SS/-40C/1.62V (+1 tied)", ref)

    def test_different_supplies_are_not_compared(self):
        self.write("c", [point("tt", 27.0, 1.62, gain=70.0)])
        self.write("b", [point("tt", 27.0, 1.98, gain=60.0)])
        rc, out, _ = self.run_cli("c", "b")
        self.assertEqual(rc, 0)
        gain = next(l for l in out.splitlines() if l.startswith("| Open-loop DC gain"))
        self.assertIn("0 better, 0 worse, 0 equal, 1 unmatched (baseline only), 1 unmatched (candidate only)", gain)
        delta = next(l for l in out.splitlines() if l.strip().startswith("Open-loop DC gain [dB]:"))
        self.assertIn("tt/27/1.62V:unmatched(candidate-only)", delta)
        self.assertIn("tt/27/1.98V:unmatched(baseline-only)", delta)
        self.assertNotIn("+10", delta)

    def test_deltas_only_at_exact_tuple(self):
        self.write("c", [point("tt", 27.0, 1.62, gain=62.0), point("tt", 27.0, 1.98, gain=66.0)])
        self.write("b", [point("tt", 27.0, 1.62, gain=61.0), point("tt", 27.0, 1.98, gain=67.0)])
        rc, out, _ = self.run_cli("c", "b")
        self.assertEqual(rc, 0)
        delta = next(l for l in out.splitlines() if l.strip().startswith("Open-loop DC gain [dB]:"))
        self.assertIn("tt/27/1.62V:+1", delta)
        self.assertIn("tt/27/1.98V:-1", delta)
        gain = next(l for l in out.splitlines() if l.startswith("| Open-loop DC gain"))
        self.assertIn("1 better, 1 worse, 0 equal |", gain)
        self.assertIn("62 dB @ TT/27C/1.62V", gain)

    def test_named_point_enumerates_every_measured_supply(self):
        self.write("c", [point("tt", 27.0, 1.62, vpp=0.5), point("tt", 27.0, 1.98, vpp=1.5)])
        self.write("b", [point("tt", 27.0, 1.8, vpp=1.4)])
        rc, out, _ = self.run_cli("c", "b")
        self.assertEqual(rc, 0)
        named = [l for l in out.splitlines() if l.strip().startswith("Output swing (Vpp) @ TT/27C")]
        self.assertEqual(len(named), 3, named)
        self.assertIn("TT/27C/1.62V: c=0.5 V | b=missing", named[0])
        self.assertIn("TT/27C/1.8V: c=missing | b=1.4 V", named[1])
        self.assertIn("TT/27C/1.98V: c=1.5 V | b=missing", named[2])
        self.assertIn("Fall slew rate @ SS/-40C: not measured in any record", out)


class Rejection(_RecordsDir):
    def assert_rejected(self, raw_ac, *needles):
        self.write("c", [point("tt", 27.0, 1.8)], raw={"ac": raw_ac})
        self.write("b", [point("tt", 27.0, 1.8)])
        rc, out, err = self.run_cli("c", "b")
        self.assertEqual(rc, 1)
        self.assertEqual(out, "")
        for n in needles:
            self.assertIn(n, err)
        with self.assertRaises(cmp.CompareError):
            cmp.load("c", "ac", str(self.dir))
        return err

    HDR = "corner,temp_c,vdd_v,pq_w,gain_dc_db,gbw_hz,phase_margin_deg\n"

    def test_duplicate_full_tuple(self):
        self.assert_rejected(self.HDR + "tt,27.0,1.8,1e-4,60,2e7,60\ntt,27,1.80,1e-4,61,2e7,60\n",
                             "duplicate point TT/27C/1.8V in rows [1, 2]")

    def test_same_corner_temp_distinct_supply_is_not_duplicate(self):
        self.write("c", [], raw={"ac": self.HDR + "tt,27,1.62,1e-4,60,2e7,60\ntt,27,1.98,1e-4,61,2e7,60\n"})
        self.assertEqual(len(cmp.load("c", "ac", str(self.dir))), 2)

    def test_missing_supply_column(self):
        self.assert_rejected("corner,temp_c,pq_w,gain_dc_db,gbw_hz,phase_margin_deg\ntt,27,1e-4,60,2e7,60\n",
                             "row 1 has no usable corner/temp_c/vdd_v")

    def test_blank_and_nonfinite_identity(self):
        err = self.assert_rejected(self.HDR + "tt,27,,1e-4,60,2e7,60\n,27,1.8,1e-4,60,2e7,60\n"
                                   "tt,nan,1.8,1e-4,60,2e7,60\ntt,27,inf,1e-4,60,2e7,60\n",
                                   "row 1 has", "row 2 has", "row 3 has", "row 4 has")
        self.assertIn("empty corner", err)

    def test_nonfinite_or_missing_metric(self):
        self.assert_rejected(self.HDR + "tt,27,1.8,1e-4,nan,2e7,60\nss,27,1.62,1e-4,60,,60\n"
                             "ff,27,1.98,1e-4,60,2e7,-inf\n",
                             "TT/27C/1.8V has nonfinite or missing gain_dc_db",
                             "SS/27C/1.62V has nonfinite or missing gbw_hz",
                             "FF/27C/1.98V has nonfinite or missing phase_margin_deg")

    def test_missing_record_file(self):
        self.write("b", [point("tt", 27.0, 1.8)])
        rc, out, err = self.run_cli("nope", "b")
        self.assertEqual(rc, 1)
        self.assertIn("cannot read record nope", err)


class SingleSupplyCommittedRecords(unittest.TestCase):
    """Committed single-supply-per-corner records: numbers unchanged, labels gain V."""

    IDS = ("20261010-162948-521c306-f0abf9", "20261010-103340-ba1dfa8-0241c1")

    def setUp(self):
        for rid in self.IDS:
            for suf in HEADERS:
                if not (_paths.RECORDS / f"{rid}-{suf}.csv").exists():
                    self.skipTest(f"committed record {rid}-{suf}.csv not present")

    def test_values_and_labels(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = cmp.main(["compare.py", *self.IDS])
        self.assertEqual(rc, 0)
        text = out.getvalue()
        for s in ("| Open-loop DC gain | 61.73 dB @ FS/125C/1.8V | 61.64 dB @ FS/125C/1.8V | "
                  "15 better, 0 worse, 0 equal |",
                  "| Phase margin | 56.37 deg @ SS/27C/1.62V | 63.94 deg @ SF/27C/1.8V | 0 better, 15 worse, 0 equal |",
                  "| Rise slew rate | 19.96 V/us @ SS/-40C/1.62V | 19.88 V/us @ SS/-40C/1.62V | "
                  "11 better, 4 worse, 0 equal |",
                  "| Quiescent power | 131.9 uW @ FF/125C/1.98V | 131.9 uW @ FF/125C/1.98V | "
                  "14 better, 1 worse, 0 equal |",
                  "Fall slew rate @ TT/27C/1.8V: 20261010-162948-521c306-f0abf9=11.77 V/us | "
                  "20261010-103340-ba1dfa8-0241c1=14.64 V/us",
                  "ss/-40/1.62V:+0.554", "ff/125/1.98V:+0.00099"):
            self.assertIn(s, text)
        self.assertNotIn("unmatched", text)


if __name__ == "__main__":
    unittest.main()
