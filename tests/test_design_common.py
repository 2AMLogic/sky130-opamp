import hashlib
import tempfile
import unittest
from pathlib import Path

import _paths

_common = _paths.load_module("design_common", _paths.REPO / "design/bin/_common.py")


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


class Sha256PrefixedTests(unittest.TestCase):
    def test_prefix_and_digest(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "f"
            p.write_bytes(b"abc")
            self.assertEqual(_common.sha256_prefixed(p),
                             "sha256:" + hashlib.sha256(b"abc").hexdigest())


if __name__ == "__main__":
    unittest.main()
