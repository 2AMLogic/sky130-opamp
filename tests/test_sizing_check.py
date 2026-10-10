import contextlib
import io
import unittest

import _paths

sc = _paths.load_module("sizing_check", _paths.REPO / "design" / "bin" / "sizing_check.py")


class SizingCheckTests(unittest.TestCase):
    def test_committed_inputs_exist(self):
        self.assertTrue(__import__("os").path.isfile(sc.FULL), sc.FULL)
        self.assertTrue(__import__("os").path.isfile(sc.SUMMARY), sc.SUMMARY)

    def test_validate_reproduces_committed_summary_exactly(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = sc.cmd_validate()
        out = buf.getvalue()
        self.assertEqual(rc, 0, out)
        self.assertIn("EXACT match", out)

    def test_cli_output_identifies_historical_dr002_replay(self):
        for cmd in (sc.cmd_widths, sc.cmd_corners):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                cmd()
            out = buf.getvalue()
            self.assertIn("DR-002 HISTORICAL REPLAY", out)
            self.assertIn("not the current schematic sizing", out)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            sc.cmd_validate()
        self.assertIn("NOT consistency with the current design", buf.getvalue())

    def test_main_validate_and_unknown_command(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(sc.main(["sizing_check.py", "validate"]), 0)
            self.assertEqual(sc.main(["sizing_check.py", "bogus"]), 2)

    def test_validate_detects_a_perturbed_summary(self):
        import csv, os, tempfile
        with open(sc.SUMMARY) as fh:
            rows = list(csv.DictReader(fh))
        for r in rows:
            if r["vov_v"]:
                r["vov_v"] = str(float(r["vov_v"]) * 1.01)
                break
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "summary.csv")
            with open(p, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
            old, sc.SUMMARY = sc.SUMMARY, p
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(sc.cmd_validate(), 1)
            finally:
                sc.SUMMARY = old

    def test_interpolation_brackets_target_and_none_when_unreachable(self):
        key = next(k for k in sc.GROUPS if len(sc._usable(k)) > 2)
        dev, corner, length, temp = key
        gms = sorted(float(r["gm_id_per_v"]) for _, r in sc._usable(key))
        mid = 0.5 * (gms[0] + gms[-1])
        got = sc.interp_at_gmid(dev, corner, length, temp, mid)
        self.assertIsNotNone(got)
        self.assertGreater(got["J"], 0)
        self.assertIsNone(sc.interp_at_gmid(dev, corner, length, temp, gms[-1] * 10))


if __name__ == "__main__":
    unittest.main()
