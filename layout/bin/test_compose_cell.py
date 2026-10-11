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


def _res(a, b, w, l=9.765, width=1.41):
    return {
        "class": "res_high_po",
        "nets": {"a": a, "b": b, "w": w},
        "params": {"l_um": l, "w_um": width},
    }


def _cap(a, b, area=15.62 * 15.62, perimeter=4 * 15.62):
    return {
        "class": "sky130_fd_pr__model__cap_mim",
        "nets": {"a": a, "b": b},
        "params": {"area_um2": area, "perimeter_um": perimeter},
    }


class PassiveExtractionCheck(unittest.TestCase):
    BODY = [
        ".subckt opamp_comp d2 out cz vss",
        "XRz cz d2 vss sky130_fd_pr__res_high_po_1p41 L=9.765 mult=1 m=1",
        "XCc cz out sky130_fd_pr__cap_mim_m3_1 W=15.62 L=15.62 MF=1 m=1",
        ".ends opamp_comp",
    ]
    PINS = ["d2", "out", "cz", "vss"]
    NETS = [{"name": n} for n in PINS]

    def run_check(self, devices, nets=None):
        extract = {"devices": devices, "nets": nets or self.NETS}
        return cc.verify_extraction(extract, self.BODY, self.PINS)

    def test_faithful_extraction_is_clean(self):
        # resistor ends and capacitor plates are interchangeable
        self.assertEqual(self.run_check([_res("d2", "cz", "vss"), _cap("out", "cz")]), [])
        self.assertEqual(self.run_check([_res("cz", "d2", "vss"), _cap("cz", "out")]), [])

    def test_backslash_escaped_net_names_are_normalised(self):
        devs = [_res("\\d2", "\\cz", "\\vss"), _cap("\\out", "\\cz")]
        self.assertEqual(self.run_check(devs), [])

    def test_substrate_miswiring_reported(self):
        for wrong in ("d2", "cz", "vsubs"):
            problems = self.run_check([_res("d2", "cz", wrong), _cap("out", "cz")])
            self.assertTrue(any("XRz: no extracted res_high_po" in p for p in problems), problems)
            self.assertTrue(any("match no reference card" in p for p in problems), problems)

    def test_resistor_length_and_width_deviation_reported(self):
        problems = self.run_check([_res("d2", "cz", "vss", l=9.763), _cap("out", "cz")])
        self.assertEqual(len(problems), 1)
        self.assertIn("XRz: extracted L 9.763 != netlist L=9.765", problems[0])
        problems = self.run_check([_res("d2", "cz", "vss", width=1.0), _cap("out", "cz")])
        self.assertIn("XRz: extracted W 1.0 != netlist W=1.41", problems[0])

    def test_resistor_body_count_reported(self):
        devs = [_res("d2", "cz", "vss"), _res("d2", "cz", "vss"), _cap("out", "cz")]
        problems = self.run_check(devs)
        self.assertTrue(any("2 extracted resistor bodies" in p for p in problems), problems)

    def test_capacitor_area_and_perimeter_reported(self):
        problems = self.run_check([_res("d2", "cz", "vss"), _cap("out", "cz", area=240.0)])
        self.assertEqual(len(problems), 1)
        self.assertIn("XCc: extracted plate area 240.0", problems[0])
        problems = self.run_check(
            [_res("d2", "cz", "vss"), _cap("out", "cz", perimeter=70.0)]
        )
        self.assertIn("XCc: extracted plate perimeter 70.0", problems[0])

    def test_capacitor_area_within_rounding_tolerance_passes(self):
        # klt extract rounds area to 1e-4 um^2
        area = 243.9844
        self.assertEqual(
            self.run_check([_res("d2", "cz", "vss"), _cap("out", "cz", area=area, perimeter=62.48)]),
            [],
        )

    def test_open_capacitor_node_reported(self):
        problems = self.run_check([_res("d2", "cz", "vss"), _cap("out", "x")])
        self.assertTrue(any("XCc: no extracted" in p for p in problems), problems)

    def test_missing_device_and_unknown_class_reported(self):
        problems = self.run_check([_res("d2", "cz", "vss")])
        self.assertTrue(any(p.startswith("XCc: no extracted") for p in problems), problems)
        odd = {"class": "pnp", "nets": {"a": "x"}, "params": {}}
        problems = self.run_check([_res("d2", "cz", "vss"), _cap("out", "cz"), odd])
        self.assertEqual(problems, ["extracted device class 'pnp' is unsupported"])

    def test_unnamed_substrate_pin_reported(self):
        problems = self.run_check(
            [_res("d2", "cz", "vss"), _cap("out", "cz")], nets=self.NETS[:-1]
        )
        self.assertEqual(problems, ["pin net(s) ['vss'] not named in the extracted netlist"])

    def test_mos_checks_unchanged_alongside_passives(self):
        body = [
            ".subckt t d g s b o",
            "XM1 d g s b sky130_fd_pr__nfet_01v8 L=1.2 W=6.03 nf=1 mult=1 m=1",
            "XCc d o sky130_fd_pr__cap_mim_m3_1 W=2 L=3 MF=1 m=1",
            ".ends t",
        ]
        devs = [
            _dev("nfet", "s", "g", "d", "b", 6.03, 1.2),
            _cap("o", "d", area=6.0, perimeter=10.0),
        ]
        nets = [{"name": n} for n in "d g s b o".split()]
        self.assertEqual(
            cc.verify_extraction({"devices": devs, "nets": nets}, body, list("dgsbo")), []
        )


class Rewire(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(cc.parse_rewire("XM1:g=inp"), ("XM1", "g", "inp"))

    def test_parse_passive_terminals(self):
        self.assertEqual(cc.parse_rewire("XRz:w=d2"), ("XRz", "w", "d2"))
        self.assertEqual(cc.parse_rewire("XCc:a=vss"), ("XCc", "a", "vss"))

    def test_rewire_card_by_kind(self):
        res = "XRz cz d2 vss sky130_fd_pr__res_high_po_1p41 L=9.765"
        self.assertEqual(
            cc.rewire_card(res, "w", "d2"),
            ("XRz cz d2 d2 sky130_fd_pr__res_high_po_1p41 L=9.765", "vss"),
        )
        self.assertEqual(cc.rewire_card(res, "b", "vss")[1], "d2")
        cap = "XCc cz out sky130_fd_pr__cap_mim_m3_1 W=1 L=1"
        self.assertEqual(cc.rewire_card(cap, "b", "cz")[0], "XCc cz cz sky130_fd_pr__cap_mim_m3_1 W=1 L=1")
        mos = "XM1 d1 inn tail vss sky130_fd_pr__nfet_01v8 L=1.2 W=6.03"
        self.assertEqual(cc.rewire_card(mos, "b", "tail")[1], "vss")
        self.assertEqual(cc.rewire_card(mos, "g", "inp")[1], "inn")

    def test_rewire_card_rejects_wrong_terminal_or_noop(self):
        cap = "XCc cz out sky130_fd_pr__cap_mim_m3_1 W=1 L=1"
        res = "XRz cz d2 vss sky130_fd_pr__res_high_po_1p41 L=9.765"
        with self.assertRaises(cc.BuildError):
            cc.rewire_card(cap, "w", "cz")  # capacitors have no substrate
        with self.assertRaises(cc.BuildError):
            cc.rewire_card(res, "g", "cz")  # resistors have no gate
        with self.assertRaises(cc.BuildError):
            cc.rewire_card(res, "w", "vss")  # already vss

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
