#!/usr/bin/env python3
"""Unit tests for the tool-free logic in layout/bin/_magic_common.py.

Run: python3 -m unittest layout/bin/test_magic_common.py
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import _magic_common as mc  # noqa: E402

NORMAL_LOG = """\
Magic 8.3 revision 500
MAGIC_TYPES: {nmos ndiff}
MAGIC_DRC_TOTAL: 3
MAGIC_DRC_WHY: 2 :: Poly resistor too short
MAGIC_DRC_WHY: 1 :: Other rule
"""


class ParseMagicLog(unittest.TestCase):
    def test_normal(self):
        r = mc.parse_magic_log(NORMAL_LOG)
        self.assertEqual(r["drc_total"], 3)
        self.assertEqual(r["magic_types_seen"], ["nmos", "ndiff"])
        self.assertEqual(r["drc_by_rule"], [
            {"count": 2, "rule": "Poly resistor too short"},
            {"count": 1, "rule": "Other rule"},
        ])

    def test_empty_types(self):
        r = mc.parse_magic_log("MAGIC_TYPES: \nMAGIC_DRC_TOTAL: 0\n")
        self.assertEqual(r["magic_types_seen"], [])

    def test_missing_summary_raises(self):
        for log in ("Magic crashed\n", "MAGIC_TYPES: {a}\n", "MAGIC_DRC_TOTAL: 0\n"):
            with self.assertRaises(mc.BuildError):
                mc.parse_magic_log(log)


class DrcTemplate(unittest.TestCase):
    def test_plain_has_no_extras(self):
        tcl = mc.DRC_TCL.format(cell="c", pre="", post="")
        self.assertNotIn("port makeall", tcl)
        self.assertNotIn("extract all", tcl)
        self.assertTrue(tcl.endswith("quit -noprompt\n"))

    def test_pre_and_post_placement(self):
        tcl = mc.DRC_TCL.format(cell="c", pre="port makeall\n", post="extract all\n")
        self.assertLess(tcl.index("port makeall"), tcl.index("drc euclidean on"))
        self.assertGreater(tcl.index("extract all"), tcl.index("MAGIC_DRC_WHY"))
        self.assertLess(tcl.index("extract all"), tcl.index("quit -noprompt"))


if __name__ == "__main__":
    unittest.main()
