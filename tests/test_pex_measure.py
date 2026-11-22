"""Negative control for the `klt pex --measure-command` wrapper (issue #250).

`klt pex` computes the delta[] rows itself from the two measurement documents
`pex_measure.py` prints. This control feeds the wrapper the same campaign record
on both sides (what `extracted == reference` means for the measurement path) and
checks the delta is exactly zero on every row, then perturbs one side and checks
the delta shows up, and that a missing point stays an error row, never a zero.
No ngspice, no fleet: the campaign is replaced by fixture CSVs.
"""

import contextlib
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _paths
from _paths import EXP

pm = _paths.load_module("pex_measure", EXP / "bin" / "pex_measure.py")
pvt = _paths.load_module("pvt_sweep_for_pex", EXP / "bin" / "pvt_sweep.py")

CORNERS = ["tt", "ss"]
TEMPS = [-40.0, 27.0]
COLUMNS = {
    "ac": ("gain_dc_db", "gbw_hz", "phase_margin_deg", "pq_w"),
    "tran-sr": ("sr_rise_v_per_us", "sr_fall_v_per_us"),
    "dc-swing": ("vpp_v",),
    "icmr": ("icmr_low_v", "icmr_high_v", "icmr_width_v"),
}


def write_record(root: Path, record_id: str, scale: float = 1.0, drop=None):
    """Fixture campaign CSVs; `scale` perturbs one measurement, `drop` blanks one."""
    for suffix, names in COLUMNS.items():
        with (root / f"{record_id}-{suffix}.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["corner", "temp_c", "vdd_v", *names])
            for ci, corner in enumerate(CORNERS):
                for ti, temp in enumerate(TEMPS):
                    row = []
                    for ni, name in enumerate(names):
                        v = 1.0 + ci + 0.1 * ti + 0.01 * ni
                        if name == "icmr_width_v" and corner == "ss" and temp == 27.0:
                            v *= scale
                        row.append("" if (name, corner, temp) == drop else repr(v))
                    w.writerow([corner, temp, pvt.VDD_BY_CORNER[corner], *row])


def measure(root: Path, record_id: str):
    """The document `pex_measure.py` would print for a side that produced `record_id`."""
    with mock.patch.object(pm, "RECORDS_DIR", root):
        return pm.document(pm.read_rows(record_id), CORNERS, TEMPS, pvt.VDD_BY_CORNER)


def delta_rows(ref, ext):
    """klt pex's per-row delta, reduced to what the control needs: (corner, name, pct|None)."""
    rows = []
    for rc, ec in zip(ref["corners"], ext["corners"]):
        assert rc["corner_id"] == ec["corner_id"]
        for rm, em in zip(rc["measurements"], ec["measurements"]):
            assert rm["name"] == em["name"]
            if rm["value"] is None or em["value"] is None:
                rows.append((rc["corner_id"], rm["name"], None))
            else:
                rows.append((rc["corner_id"], rm["name"], 100.0 * (em["value"] - rm["value"]) / rm["value"]))
    return rows


class ReadRowsIdentityTests(unittest.TestCase):
    """Issue #369: read_rows keys rows with sim/lib/point_identity, so the
    silent paths (padded corner, 7th-decimal supply, nonfinite field, duplicate
    point) are gone: malformed rows raise, duplicates raise, and klt pex never
    sees a `value: null` error row for a measurement the campaign produced."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def write_ac(self, record_id: str, rows: list[dict]):
        with (self.root / f"{record_id}-ac.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["corner", "temp_c", "vdd_v", "gain_dc_db", "gbw_hz", "phase_margin_deg", "pq_w"])
            for r in rows:
                w.writerow([r["corner"], r["temp_c"], r["vdd_v"],
                            r.get("gain_dc_db", "65"), "1e6", "60", "1e-4"])

    def rows(self, record_id: str):
        with mock.patch.object(pm, "RECORDS_DIR", self.root):
            return pm.read_rows(record_id)

    def test_padded_corner_and_seventh_decimal_supply_still_match(self):
        self.write_ac("rec", [{"corner": " tt ", "temp_c": "27.0", "vdd_v": "1.8000001"}])
        points = self.rows("rec")
        self.assertIn(("tt", 27.0, 1.8), points)
        with mock.patch.object(pm, "RECORDS_DIR", self.root):
            doc = pm.document(points, ["tt"], [27.0], {"tt": 1.8})
        vals = {m["name"]: m["value"] for m in doc["corners"][0]["measurements"]}
        self.assertEqual(vals["gain_dc_db"], 65.0)
        self.assertEqual({m["status"] for m in doc["corners"][0]["measurements"]
                          if m["name"] in COLUMNS["ac"]}, {"pass"})

    def test_nonfinite_field_or_blank_corner_raises(self):
        for bad in ({"corner": "tt", "temp_c": "nan", "vdd_v": "1.8"},
                    {"corner": "tt", "temp_c": "27", "vdd_v": "inf"},
                    {"corner": "   ", "temp_c": "27", "vdd_v": "1.8"}):
            with self.subTest(bad=bad):
                self.write_ac("rec", [bad])
                with self.assertRaises(ValueError):
                    self.rows("rec")  # was: silently keyed, then value: null on every corner

    def test_duplicate_point_within_one_suffix_csv_raises(self):
        self.write_ac("rec", [{"corner": "tt", "temp_c": "27", "vdd_v": "1.8", "gain_dc_db": "65"},
                              {"corner": "tt", "temp_c": "27.0", "vdd_v": "1.8000001", "gain_dc_db": "70"}])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.rows("rec")  # was: last-row-wins, 70.0 silently overwrote 65.0

    def test_same_point_across_suffix_csvs_is_not_a_duplicate(self):
        self.write_ac("rec", [{"corner": "tt", "temp_c": "27", "vdd_v": "1.8"}])
        with (self.root / "rec-tran-sr.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["corner", "temp_c", "vdd_v", "sr_rise_v_per_us", "sr_fall_v_per_us"])
            w.writerow(["tt", "27", "1.8", "2.0", "1.9"])
        points = self.rows("rec")
        self.assertEqual(points[("tt", 27.0, 1.8)]["gain_dc_db"], 65.0)
        self.assertEqual(points[("tt", 27.0, 1.8)]["sr_rise_v_per_us"], 2.0)


class NegativeControl(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_identical_sides_give_zero_delta_on_every_row(self):
        write_record(self.root, "ref")
        rows = delta_rows(measure(self.root, "ref"), measure(self.root, "ref"))
        self.assertEqual(len(rows), len(CORNERS) * len(TEMPS) * 10)
        self.assertTrue(all(pct == 0.0 for _, _, pct in rows), rows)

    def test_perturbed_extracted_side_is_detected(self):
        write_record(self.root, "ref")
        write_record(self.root, "ext", scale=0.9)
        rows = delta_rows(measure(self.root, "ref"), measure(self.root, "ext"))
        nonzero = [(c, n) for c, n, pct in rows if pct != 0.0]
        self.assertEqual(nonzero, [("ss/1.620V/27C", "icmr_width_v")])
        self.assertAlmostEqual(next(p for c, n, p in rows if n == "icmr_width_v" and c == "ss/1.620V/27C"), -10.0)

    def test_missing_point_is_an_error_row_not_zero(self):
        write_record(self.root, "ref")
        write_record(self.root, "ext", drop=("gbw_hz", "tt", -40.0))
        ext = measure(self.root, "ext")
        bad = [m for c in ext["corners"] for m in c["measurements"] if m["value"] is None]
        self.assertEqual([(m["name"], m["status"]) for m in bad], [("gbw_hz", "error")])
        pcts = {(c, n): p for c, n, p in delta_rows(measure(self.root, "ref"), ext)}
        self.assertIsNone(pcts[("tt/1.800V/-40C", "gbw_hz")])

    def test_cli_prints_the_same_document_for_the_same_netlist(self):
        """End to end through main(): campaign stubbed, same netlist on both sides."""
        write_record(self.root, "ref")
        netlist = self.root / "dut.spice"
        netlist.write_text(".subckt opamp_core a b\nR1 a b 1k\n.ends\n")
        docs = []
        for side in ("schematic", "extracted"):
            out = io.StringIO()
            env = {"KLT_PEX_SIDE": side, "KLT_PEX_ARTIFACTS_DIR": str(self.root)}
            with mock.patch.dict("os.environ", env), \
                    mock.patch.object(pm, "RECORDS_DIR", self.root), \
                    mock.patch.object(pm, "run_campaign", lambda *a: "ref"), \
                    contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(pm.main([str(netlist), f"--corners={','.join(CORNERS)}",
                                          f"--temps={','.join(f'{t:g}' for t in TEMPS)}"]), 0)
            docs.append(json.loads(out.getvalue()))
        self.assertEqual(docs[0], docs[1])
        self.assertTrue(all(pct == 0.0 for _, _, pct in delta_rows(docs[0], docs[1])))


if __name__ == "__main__":
    unittest.main()
