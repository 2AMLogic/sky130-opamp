"""Simulator-free tests for design/bin/_common.py and lib/spice_text.py."""
import hashlib
import tempfile
import unittest
from pathlib import Path

import _paths

_common = _paths.load_module("design_common", _paths.REPO / "design/bin/_common.py")
spice_text = _paths.load_module("spice_text", _paths.REPO / "lib" / "spice_text.py")


class JoinContinuationsTests(unittest.TestCase):
    def test_plain_plus_join(self):
        text = "M1 a b c d x\n+ w=1\n+ l=2\nR1 a b 1k\n"
        self.assertEqual(_common.join_continuations(text),
                         ["M1 a b c d x w=1 l=2", "R1 a b 1k"])

    def test_comment_between_card_and_continuation(self):
        text = "M1 a b c d x\n* note\n+ w=1\n"
        self.assertEqual(_common.join_continuations(text), ["M1 a b c d x w=1"])

    def test_sch_path_and_blank_lines_dropped(self):
        text = "** sch_path: /x.sch\n\nM1 a b c d x\n\n+ w=1\n"
        self.assertEqual(_common.join_continuations(text), ["M1 a b c d x w=1"])

    def test_design_helper_is_the_shared_parse_mode(self):
        text = "M1 a b\n*.note\n\n+ w=1\n+ l=2\nR1 a b 1k\n"
        self.assertEqual(_common.join_continuations(text),
                         spice_text.join_continuations(text))


class JoinModesTests(unittest.TestCase):
    """The two modes of lib/spice_text.py (issue #301)."""

    def test_parse_mode_drops_comments_and_blanks(self):
        text = "M1 a b\n*.note\n\n+ w=1\nR1 a b 1k\n"
        self.assertEqual(spice_text.join_continuations(text),
                         ["M1 a b w=1", "R1 a b 1k"])

    def test_emission_mode_keeps_comments_and_blanks_in_order(self):
        text = "M1 a b\n*.note\n\n+ w=1\nR1 a b 1k\n"
        self.assertEqual(spice_text.join_continuations(text, keep_comments=True),
                         ["M1 a b w=1", "*.note", "", "R1 a b 1k"])

    def test_multiple_continuations_across_comment_and_blank(self):
        text = "M1 a b\n+ c=1\n*.note\n\n+ d=2\n"
        self.assertEqual(spice_text.join_continuations(text), ["M1 a b c=1 d=2"])
        self.assertEqual(spice_text.join_continuations(text, keep_comments=True),
                         ["M1 a b c=1 d=2", "*.note", ""])

    def test_blank_between_card_and_continuation_joins_in_both_modes(self):
        text = "M1 a b\n\n+ w=1\n"
        self.assertEqual(spice_text.join_continuations(text), ["M1 a b w=1"])
        self.assertEqual(spice_text.join_continuations(text, keep_comments=True),
                         ["M1 a b w=1", ""])

    def test_leading_orphan_plus_starts_its_own_line(self):
        text = "+ w=1\nM1 a b\n"
        self.assertEqual(spice_text.join_continuations(text), ["+ w=1", "M1 a b"])
        self.assertEqual(spice_text.join_continuations(text, keep_comments=True),
                         ["+ w=1", "M1 a b"])

    def test_orphan_plus_absorbs_a_following_continuation(self):
        self.assertEqual(spice_text.join_continuations("+ a\n+ b\n"), ["+ a b"])

    def test_emission_mode_rstrips_but_keeps_comment_text_verbatim(self):
        text = "*.iopin tail   \n"
        self.assertEqual(spice_text.join_continuations(text, keep_comments=True),
                         ["*.iopin tail"])


class Sha256PrefixedTests(unittest.TestCase):
    def test_prefix_and_digest(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "f"
            p.write_bytes(b"abc")
            self.assertEqual(_common.sha256_prefixed(p),
                             "sha256:" + hashlib.sha256(b"abc").hexdigest())


if __name__ == "__main__":
    unittest.main()
