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
    card_terminals,
    effective_multiplicity,
    expand_body,
    expand_multiplicity,
    logical_lines,
    passive_geometry,
    select_cards,
    terminal_names,
    write_reference,
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

    def test_unsupported_model_rejected(self):
        text = SYNTHETIC + "XU n1 n2 b sky130_fd_pr__res_xhigh_po_1p41 L=9\n"
        with self.assertRaisesRegex(ReferenceError, "not a 4-terminal"):
            build_reference(text, cell="t", pins=["n1", "n2", "b"], devices=["XU"])

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
            self.assertIn("nrs=0.0480928689883914", card)

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
        self.assertIn(" W=4.635", body[3])

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


class Passives(unittest.TestCase):
    """The compensation network's resistor and MiM capacitor (issue #167)."""

    PINS = ["d2", "out", "cz", "vss"]

    def setUp(self):
        self.text = SOURCE.read_text()

    def test_committed_compensation_reference_is_verbatim(self):
        body = build_reference(
            self.text, cell="opamp_comp", pins=self.PINS, devices=["XRz", "XCc"]
        )
        self.assertEqual(body[0], ".subckt opamp_comp d2 out cz vss")
        self.assertEqual(
            body[1],
            "XRz cz d2 vss sky130_fd_pr__res_high_po_1p41 L=9.765 mult=1 m=1",
        )
        self.assertEqual(
            body[2],
            "XCc cz out sky130_fd_pr__cap_mim_m3_1 W=15.62 L=15.62 MF=1 m=1",
        )
        source_cards = {c.split()[0]: c for c in logical_lines(self.text)}
        self.assertEqual(body[1], source_cards["XRz"])
        self.assertEqual(body[2], source_cards["XCc"])

    def test_terminals_and_substrate(self):
        self.assertEqual(
            card_terminals(
                "XRz cz d2 vss sky130_fd_pr__res_high_po_1p41 L=9.765"
            ),
            ("XRz", ["cz", "d2", "vss"], "sky130_fd_pr__res_high_po_1p41"),
        )
        self.assertEqual(terminal_names("sky130_fd_pr__res_high_po_1p41"), ("a", "b", "w"))
        self.assertEqual(terminal_names("sky130_fd_pr__cap_mim_m3_1"), ("a", "b"))
        self.assertEqual(terminal_names("sky130_fd_pr__nfet_01v8"), ("d", "g", "s", "b"))

    def test_resistor_geometry_uses_model_default_width(self):
        geo = passive_geometry("XRz cz d2 vss sky130_fd_pr__res_high_po_1p41 L=9.765 mult=1 m=1")
        self.assertEqual(geo, {"kind": "resistor", "l_um": 9.765, "w_um": 1.41, "units": 1})
        geo = passive_geometry("XR a b s sky130_fd_pr__res_high_po_1p41 L=2 W=1.5 m=2")
        self.assertEqual((geo["w_um"], geo["units"]), (1.5, 2))

    def test_capacitor_geometry_sums_units(self):
        geo = passive_geometry("XCc a b sky130_fd_pr__cap_mim_m3_1 W=15.62 L=15.62 MF=2 m=1")
        self.assertAlmostEqual(geo["area_um2"], 2 * 15.62 * 15.62)
        self.assertAlmostEqual(geo["perimeter_um"], 2 * 4 * 15.62)

    def test_wrong_terminal_count_rejected(self):
        for card in (
            "XRz cz d2 sky130_fd_pr__res_high_po_1p41 L=9.765",  # no substrate
            "XRz cz d2 vss x sky130_fd_pr__res_high_po_1p41 L=9.765",
            "XCc cz sky130_fd_pr__cap_mim_m3_1 W=1 L=1",
            "XCc cz out vss sky130_fd_pr__cap_mim_m3_1 W=1 L=1",
        ):
            with self.assertRaisesRegex(ReferenceError, "takes"):
                card_terminals(card)

    def test_unknown_passive_models_rejected(self):
        for model in (
            "sky130_fd_pr__res_high_po_2p85",
            "sky130_fd_pr__res_generic_po",
            "sky130_fd_pr__cap_mim_m3_2",
            "sky130_fd_pr__cap_var_lvt",
            "totally_unknown",
        ):
            with self.assertRaisesRegex(ReferenceError, "not a 4-terminal"):
                card_terminals(f"XU a b c {model} L=1 W=1")

    def test_non_subckt_element_cards_rejected(self):
        with self.assertRaisesRegex(ReferenceError, "only X subckt-call"):
            card_terminals("R1 a b 1k")

    def test_missing_geometry_rejected(self):
        with self.assertRaisesRegex(ReferenceError, "no L="):
            passive_geometry("XR a b s sky130_fd_pr__res_high_po_1p41 W=1.41")
        with self.assertRaisesRegex(ReferenceError, "no W="):
            passive_geometry("XC a b sky130_fd_pr__cap_mim_m3_1 L=5")
        with self.assertRaisesRegex(ReferenceError, "not a plain number"):
            passive_geometry("XR a b s sky130_fd_pr__res_high_po_1p41 L={len}")
        with self.assertRaisesRegex(ReferenceError, "not a positive integer"):
            passive_geometry("XR a b s sky130_fd_pr__res_high_po_1p41 L=1 m=1.5")

    def test_build_rejects_passive_without_geometry(self):
        text = "XR a b s sky130_fd_pr__res_high_po_1p41 W=1.41\n"
        with self.assertRaisesRegex(ReferenceError, "no L="):
            build_reference(text, cell="t", pins=["a", "b", "s"], devices=["XR"])

    def test_substrate_net_must_be_a_pin(self):
        with self.assertRaisesRegex(ReferenceError, "not in the pin list"):
            build_reference(
                self.text, cell="t", pins=["d2", "out", "cz"], devices=["XRz", "XCc"]
            )

    def test_unused_observation_pin_rejected(self):
        with self.assertRaisesRegex(ReferenceError, "touch no selected device"):
            build_reference(
                self.text, cell="t", pins=[*self.PINS, "x"], devices=["XRz", "XCc"]
            )


class MultiplicityExpansion(unittest.TestCase):
    M2 = (
        "XM5 tail ibias vss vss sky130_fd_pr__nfet_01v8 L=1.2 W=7.820 nf=1 "
        "ad=2.2678 sa=0 mult=2 m=2"
    )
    M1 = M2.replace("XM5", "XMB1").replace("mult=2 m=2", "mult=1 m=1")

    def test_effective_multiplicity_is_m_not_m_times_mult(self):
        self.assertEqual(effective_multiplicity(self.M2), 2)
        self.assertEqual(effective_multiplicity(self.M1), 1)

    def test_non_integer_m_rejected(self):
        with self.assertRaisesRegex(ReferenceError, "not a positive integer"):
            effective_multiplicity(self.M2.replace("m=2", "m=1.5"))

    def test_unit_card_untouched(self):
        self.assertEqual(expand_multiplicity(self.M1), [self.M1])

    def test_m2_becomes_two_unit_cards(self):
        cards = expand_multiplicity(self.M2)
        self.assertEqual(len(cards), 2)
        self.assertEqual([c.split()[0] for c in cards], ["XM5_1", "XM5_2"])
        for card in cards:
            self.assertIn("m=1", card.split())
            self.assertIn("mult=1", card.split())
            self.assertIn("W=7.820", card.split())
            self.assertEqual(card.split()[1:6], self.M2.split()[1:6])

    def test_passive_never_expanded(self):
        card = "XRz cz d2 vss sky130_fd_pr__res_high_po_1p41 L=9.765 mult=1 m=1"
        self.assertEqual(expand_multiplicity(card), [card])

    def test_expand_body_keeps_header_and_footer(self):
        body = [".subckt t ibias tail vss", self.M1, self.M2, ".ends t"]
        out = expand_body(body)
        self.assertEqual(out[0], body[0])
        self.assertEqual(out[-1], body[-1])
        self.assertEqual(len(out), 5)

    def test_canonical_bias_group_is_three_units(self):
        body = build_reference(
            SOURCE.read_text(),
            cell="t",
            pins=["ibias", "tail", "vss"],
            devices=["XMB1", "XM5"],
        )
        units = sum(effective_multiplicity(c) for c in body[1:-1])
        self.assertEqual(units, 3)
        self.assertEqual(len(expand_body(body)) - 2, 3)


INTERNAL = """\
XA n1 g1 vss vss sky130_fd_pr__nfet_01v8 L=1 W=2 m=1
XB out g2 n1 vss sky130_fd_pr__nfet_01v8 L=1 W=2 m=1
"""


class InternalNets(unittest.TestCase):
    def build(self, **kw):
        base = dict(
            cell="c", pins=["out", "g1", "g2", "vss"], devices=["XA", "XB"]
        )
        base.update(kw)
        return build_reference(INTERNAL, **base)

    def test_internal_net_is_not_a_port(self):
        body = self.build(internal_nets=["n1"])
        self.assertEqual(body[0], ".subckt c out g1 g2 vss")
        self.assertIn("n1", body[1])

    def test_undeclared_internal_net_still_fails(self):
        with self.assertRaisesRegex(ReferenceError, "n1"):
            self.build()
        with self.assertRaisesRegex(ReferenceError, "n1"):
            self.build(internal_nets=[])
        with self.assertRaisesRegex(ReferenceError, "not declared in internal_nets"):
            self.build(internal_nets=["other"])

    def test_invalid_declarations(self):
        for bad in (["n1", "n1"], ["vss", "n1"], "n1", ["n 1"], [""], [3]):
            with self.subTest(bad=bad), self.assertRaises(ReferenceError):
                self.build(internal_nets=bad)

    def test_unused_declaration_rejected(self):
        with self.assertRaisesRegex(ReferenceError, "touch no selected"):
            self.build(internal_nets=["n1", "spare"])

    def test_promotion_to_boundary_pin_rejected(self):
        with self.assertRaisesRegex(ReferenceError, "promoted to a port"):
            self.build(pins=["out", "g1", "g2", "vss", "n1"], internal_nets=["n1"])

    def test_write_reference_notes_internal_nets(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            src, out = Path(tmp) / "s.spice", Path(tmp) / "o.spice"
            src.write_text(INTERNAL)
            write_reference(
                src, out, source_label="s", cell="c",
                pins=["out", "g1", "g2", "vss"], devices=["XA", "XB"],
                internal_nets=["n1"],
            )
            text = out.read_text()
            self.assertIn("Internal nets (not ports): n1", text)
            self.assertIn(".subckt c out g1 g2 vss", text)


if __name__ == "__main__":
    unittest.main()
