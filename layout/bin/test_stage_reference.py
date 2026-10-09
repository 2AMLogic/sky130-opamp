#!/usr/bin/env python3
"""Unit tests for layout/bin/stage_reference.py.

Run: python3 -m unittest layout/bin/test_stage_reference.py
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from stage_reference import (  # noqa: E402
    ReferenceError,
    build_reference,
    logical_lines,
    select_cards,
)

REPO_ROOT = HERE.parents[1]
SOURCE = REPO_ROOT / "design" / "netlist" / "opamp_core.spice"

SYNTHETIC = """\
** sch_path: x.sch
**.subckt top a b c
*.iopin a
XA d g s b sky130_fd_pr__nfet_01v8 L=1.2 W=6.03 nf=1
* a comment between card and continuation
+ m=1
XB d2 g s b sky130_fd_pr__pfet_01v8 L=0.3
+ W=4.634
+ m=1
XR n1 n2 b sky130_fd_pr__res_high_po_1p41 L=9.763
**.ends
.end
"""


class LogicalLines(unittest.TestCase):
    def test_joins_continuations_across_comments(self):
        lines = logical_lines(SYNTHETIC)
        self.assertIn("XA d g s b sky130_fd_pr__nfet_01v8 L=1.2 W=6.03 nf=1 m=1", lines)
        self.assertIn("XB d2 g s b sky130_fd_pr__pfet_01v8 L=0.3 W=4.634 m=1", lines)

    def test_commented_headers_are_not_cards(self):
        lines = logical_lines(SYNTHETIC)
        self.assertFalse(any("subckt" in line.lower() for line in lines))
        self.assertFalse(any(line.lower().startswith(".ends") for line in lines))

    def test_orphan_continuation_rejected(self):
        with self.assertRaises(ReferenceError):
            logical_lines("+ W=1\n")


class Selection(unittest.TestCase):
    def test_missing_device_rejected(self):
        with self.assertRaisesRegex(ReferenceError, "not found"):
            select_cards(SYNTHETIC, ["XA", "XZ"])

    def test_duplicate_in_source_rejected(self):
        doubled = SYNTHETIC + "XA d g s b sky130_fd_pr__nfet_01v8 L=1 W=1\n"
        with self.assertRaisesRegex(ReferenceError, "appears 2 times"):
            select_cards(doubled, ["XA"])

    def test_duplicate_in_selection_rejected(self):
        with self.assertRaisesRegex(ReferenceError, "duplicate device"):
            select_cards(SYNTHETIC, ["XA", "xa"])

    def test_non_mos_card_rejected(self):
        with self.assertRaisesRegex(ReferenceError, "not a 4-terminal"):
            build_reference(SYNTHETIC, cell="t", pins=["n1", "n2", "b"], devices=["XR"])

    def test_stray_net_rejected(self):
        with self.assertRaisesRegex(ReferenceError, "not in the pin list"):
            build_reference(SYNTHETIC, cell="t", pins=["d", "g", "s"], devices=["XA"])

    def test_unused_pin_rejected(self):
        with self.assertRaisesRegex(ReferenceError, "touch no selected device"):
            build_reference(
                SYNTHETIC, cell="t", pins=["d", "g", "s", "b", "x"], devices=["XA"]
            )


class CommittedNetlist(unittest.TestCase):
    """The representative input: the committed design netlist itself."""

    def setUp(self):
        self.text = SOURCE.read_text()

    def test_input_pair_reference(self):
        body = build_reference(
            self.text,
            cell="opamp_stage1",
            pins=["inn", "inp", "tail", "d1", "d2", "vss"],
            devices=["XM1", "XM2"],
        )
        self.assertEqual(body[0], ".subckt opamp_stage1 inn inp tail d1 d2 vss")
        self.assertEqual(body[-1], ".ends opamp_stage1")
        self.assertEqual(len(body), 4)
        xm1, xm2 = body[1], body[2]
        self.assertTrue(xm1.startswith("XM1 d1 inn tail vss sky130_fd_pr__nfet_01v8 "))
        self.assertTrue(xm2.startswith("XM2 d2 inp tail vss sky130_fd_pr__nfet_01v8 "))
        for card in (xm1, xm2):
            for param in ("L=1.2", "W=6.03", "nf=1", "m=1", "mult=1"):
                self.assertIn(f" {param}", card)
            # the continuation line's parameters were joined on
            self.assertIn("nrs=0.04809286898839137", card)

    def test_full_first_stage_selection_preserves_terminal_order(self):
        body = build_reference(
            self.text,
            cell="s",
            pins=["inn", "inp", "tail", "d1", "d2", "vdd", "vss"],
            devices=["XM1", "XM2", "XM3", "XM4"],
        )
        self.assertTrue(
            body[3].startswith("XM3 d1 d1 vdd vdd sky130_fd_pr__pfet_01v8 ")
        )
        self.assertTrue(
            body[4].startswith("XM4 d2 d1 vdd vdd sky130_fd_pr__pfet_01v8 ")
        )
        self.assertIn(" W=4.634", body[3])

    def test_cards_match_source_tokens_exactly(self):
        # every token of the selected card is a token of the source card
        source_cards = {c.split()[0]: c for c in logical_lines(self.text)}
        body = build_reference(
            self.text,
            cell="s",
            pins=["inn", "inp", "tail", "d1", "d2", "vss"],
            devices=["XM1", "XM2"],
        )
        for card in body[1:-1]:
            self.assertEqual(card, source_cards[card.split()[0]])


if __name__ == "__main__":
    unittest.main()
