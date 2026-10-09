#!/usr/bin/env python3
"""Unit tests for the klt-free helpers in layout/bin/compose-cell.py.

Run: python3 -m unittest layout/bin/test_compose_cell.py
(The klt chain itself is exercised by ``compose-cell.py --check``.)
"""

from __future__ import annotations

import importlib.util
import struct
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
_spec = importlib.util.spec_from_file_location("compose_cell", HERE / "compose-cell.py")
cc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cc)


def _record(rectype: int, payload: bytes = b"") -> bytes:
    return struct.pack(">HH", 4 + len(payload), rectype) + payload


def _gds(stamp: int) -> bytes:
    stamps = struct.pack(">12H", *([stamp] * 12))
    return b"".join(
        [
            _record(0x0002, struct.pack(">H", 600)),  # HEADER
            _record(0x0102, stamps),  # BGNLIB
            _record(0x0206, b"LIB\x00"),  # LIBNAME
            _record(0x0502, stamps),  # BGNSTR
            _record(0x0606, b"TOP\x00"),  # STRNAME
            _record(0x0700),  # ENDSTR
            _record(0x0400),  # ENDLIB
        ]
    )


class GdsTimestamps(unittest.TestCase):
    def test_nonzero_stamps_are_zeroed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.gds"
            path.write_bytes(_gds(2026))
            self.assertTrue(cc.normalize_gds_timestamps(path))
            self.assertEqual(path.read_bytes(), _gds(0))

    def test_zero_stamps_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.gds"
            path.write_bytes(_gds(0))
            self.assertFalse(cc.normalize_gds_timestamps(path))
            self.assertEqual(path.read_bytes(), _gds(0))

    def test_malformed_record_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.gds"
            path.write_bytes(struct.pack(">HH", 2, 0x0002))
            with self.assertRaises(cc.BuildError):
                cc.normalize_gds_timestamps(path)


class PortSnapping(unittest.TestCase):
    def test_half_grid_tie_rounds_down(self):
        self.assertEqual(cc._snap(1.5075, 0.005), 1.505)
        self.assertEqual(cc._snap(5.7425, 0.005), 5.74)
        self.assertEqual(cc._snap(0.21, 0.005), 0.21)
        self.assertEqual(cc._snap(-0.71, 0.005), -0.71)

    def test_snap_ports_records_moves_and_keeps_original(self):
        report = {
            "ports": [
                {"name": "A", "x_um": 0.21, "y_um": 1.5075},
                {"name": "B", "x_um": 1.0, "y_um": 2.0},
                {"name": "C"},
            ]
        }
        snapped = cc.snap_ports(report, 0.005)
        self.assertEqual(report["ports"][0]["y_um"], 1.5075)  # input untouched
        self.assertEqual(snapped["ports"][0]["y_um"], 1.505)
        self.assertEqual(
            snapped["_snapped_ports"]["moves"],
            [{"port": "A", "axis": "y_um", "from": 1.5075, "to": 1.505}],
        )


def _dev(cls, d, g, s, b, w, l):
    return {
        "class": cls,
        "nets": {"d": d, "g": g, "s": s, "b": b},
        "params": {"w_um": w, "l_um": l},
    }


class ExtractionCheck(unittest.TestCase):
    BODY = [
        ".subckt t inn inp tail d1 d2 vss",
        "XM1 d1 inn tail vss sky130_fd_pr__nfet_01v8 L=1.2 W=6.03 nf=1 mult=1 m=1",
        "XM2 d2 inp tail vss sky130_fd_pr__nfet_01v8 L=1.2 W=6.03 nf=1 mult=1 m=1",
        ".ends t",
    ]
    PINS = ["inn", "inp", "tail", "d1", "d2", "vss"]
    NETS = [{"name": n} for n in PINS]

    def extract(self, devices):
        return {"devices": devices, "nets": self.NETS}

    def test_split_units_sum_to_card_width(self):
        devs = [
            _dev("nfet", "d1", "inn", "tail", "vss", 3.015, 1.2),
            _dev("nfet", "tail", "inn", "d1", "vss", 3.015, 1.2),  # S/D swapped
            _dev("nfet", "d2", "inp", "tail", "vss", 3.015, 1.2),
            _dev("nfet", "d2", "inp", "tail", "vss", 3.015, 1.2),
        ]
        self.assertEqual(
            cc.verify_extraction(self.extract(devs), self.BODY, self.PINS), []
        )

    def test_width_shortfall_reported(self):
        devs = [
            _dev("nfet", "d1", "inn", "tail", "vss", 3.015, 1.2),
            _dev("nfet", "d2", "inp", "tail", "vss", 6.03, 1.2),
        ]
        problems = cc.verify_extraction(self.extract(devs), self.BODY, self.PINS)
        self.assertEqual(len(problems), 1)
        self.assertIn("XM1: extracted total W 3.015", problems[0])

    def test_wrong_length_and_stray_device_reported(self):
        devs = [
            _dev("nfet", "d1", "inn", "tail", "vss", 6.03, 1.0),
            _dev("nfet", "d2", "inp", "tail", "vss", 6.03, 1.2),
            _dev("nfet", "d2", "inn", "tail", "vss", 1.0, 1.2),
        ]
        problems = cc.verify_extraction(self.extract(devs), self.BODY, self.PINS)
        self.assertTrue(any("XM1: extracted L" in p for p in problems))
        self.assertTrue(any("match no reference card" in p for p in problems))

    def test_unnamed_pin_reported(self):
        devs = [
            _dev("nfet", "d1", "inn", "tail", "vss", 6.03, 1.2),
            _dev("nfet", "d2", "inp", "tail", "vss", 6.03, 1.2),
        ]
        extract = {"devices": devs, "nets": self.NETS[:-1]}
        problems = cc.verify_extraction(extract, self.BODY, self.PINS)
        self.assertEqual(
            problems, ["pin net(s) ['vss'] not named in the extracted netlist"]
        )


class Rewire(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(cc.parse_rewire("XM1:g=inp"), ("XM1", "g", "inp"))

    def test_bad_terminal(self):
        with self.assertRaises(cc.BuildError):
            cc.parse_rewire("XM1:x=inp")


class NegativeControlVerdict(unittest.TestCase):
    def test_genuine_mismatch_passes(self):
        self.assertTrue(
            cc.is_genuine_mismatch(
                {"status": "mismatch", "mismatch_count": 3, "error_count": 3}
            )
        )

    def test_error_unknown_missing_and_match_fail(self):
        for lvs in (
            {"status": "error", "error_count": 1, "mismatch_count": 0},
            {"status": "unknown"},
            {},
            {"status": "match", "mismatch_count": 0},
            {"status": "mismatch", "mismatch_count": 0},
            {"status": "mismatch"},
            {"status": "mismatch", "mismatch_count": 2, "error": "boom"},
        ):
            self.assertFalse(cc.is_genuine_mismatch(lvs), lvs)


if __name__ == "__main__":
    unittest.main()
