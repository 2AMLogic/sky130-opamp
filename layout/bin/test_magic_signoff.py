#!/usr/bin/env python3
"""Unit tests for the tool-free verdict logic in layout/bin/magic-signoff.py.

Run: python3 -m unittest layout/bin/test_magic_signoff.py
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
_spec = importlib.util.spec_from_file_location("magic_signoff", HERE / "magic-signoff.py")
ms = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ms)


def _summary(drc=0, pins=True):
    return {"drc_total": drc, "netgen": {"pins_matched": pins}}


class SignoffVerdict(unittest.TestCase):
    def test_clean_passes(self):
        self.assertTrue(ms.signoff_clean(_summary(), True))

    def test_pin_mismatch_with_matching_topology_fails(self):
        self.assertFalse(ms.signoff_clean(_summary(pins=False), True))

    def test_drc_or_netlist_failure_fails(self):
        self.assertFalse(ms.signoff_clean(_summary(drc=1), True))
        self.assertFalse(ms.signoff_clean(_summary(), False))


if __name__ == "__main__":
    unittest.main()
