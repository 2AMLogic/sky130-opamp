#!/usr/bin/env python3
"""Unit tests for the tool-free logic in layout/bin/probe-passives.py.

No klt, Magic or PDK is needed: the Magic log parser is fed canned logs and
``main --check`` runs with ``build_probe`` and the toolchain check replaced.

Run: python3 -m unittest layout/bin/test_probe_passives.py
"""

from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
_spec = importlib.util.spec_from_file_location("probe_passives", HERE / "probe-passives.py")
pp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pp)


class OffGrid(unittest.TestCase):
    def test_on_grid(self):
        for v in (9.765, 9.76, 15.62, 1.41, 0.0):
            self.assertFalse(pp.off_grid(v), v)

    def test_one_nm_off_grid(self):
        self.assertTrue(pp.off_grid(9.766))
        self.assertTrue(pp.off_grid(9.764))

    def test_float_noise_values(self):
        self.assertFalse(pp.off_grid(9.76))
        self.assertTrue(pp.off_grid(9.763))


NORMAL_LOG = """\
Magic 8.3 revision 500
MAGIC_TYPES: {rpoly polyres}
MAGIC_DRC_TOTAL: 3
MAGIC_DRC_WHY: 2 :: Poly resistor too short
MAGIC_DRC_WHY: 1 :: Other rule
"""


class MagicLog(unittest.TestCase):
    def test_normal(self):
        r = pp.parse_magic_log(NORMAL_LOG)
        self.assertEqual(r["drc_total"], 3)
        self.assertEqual(r["drc_style"], "drc(full)")
        self.assertEqual(r["magic_types_seen"], ["rpoly", "polyres"])
        self.assertFalse(r["vacuous"])
        self.assertEqual(r["drc_by_rule"], [
            {"count": 2, "rule": "Poly resistor too short"},
            {"count": 1, "rule": "Other rule"},
        ])

    def test_vacuous(self):
        r = pp.parse_magic_log("MAGIC_TYPES: \nMAGIC_DRC_TOTAL: 0\n")
        self.assertEqual(r["magic_types_seen"], [])
        self.assertTrue(r["vacuous"])
        self.assertEqual(r["drc_total"], 0)
        self.assertEqual(r["drc_by_rule"], [])

    def test_missing_summary_raises(self):
        with self.assertRaises(pp.BuildError):
            pp.parse_magic_log("Magic crashed\n")
        with self.assertRaises(pp.BuildError):
            pp.parse_magic_log("MAGIC_TYPES: {a}\n")
        with self.assertRaises(pp.BuildError):
            pp.parse_magic_log("MAGIC_DRC_TOTAL: 0\n")


def _summary(i, verdict="clean"):
    return {"id": f"p{i}", "klt_drc": {"status": verdict, "violation_count": 0}}


class MainCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        out_root = Path(self.tmp.name)
        self.summaries = [_summary(i) for i in range(len(pp.PROBES))]
        self.tools = {"klt": "1", "pdk": "x"}
        self.index = {"schema": "sky130-opamp/passive-probes/1", "tools": self.tools,
                      "probes": self.summaries}
        (out_root / "index.json").write_text(json.dumps(self.index))
        self.out_root = out_root

    def _run(self, built):
        by_id = {p["id"]: s for p, s in zip(pp.PROBES, built)}
        tool = {**self.tools, "magic_tech": Path("/nonexistent.tech")}
        patches = [
            mock.patch.object(pp, "OUT_ROOT", self.out_root),
            mock.patch.object(pp, "klt_cmd", return_value=["klt"]),
            mock.patch.object(pp, "check_toolchain", return_value=tool),
            mock.patch.object(pp, "build_probe",
                              side_effect=lambda probe, *a, **k: by_id[probe["id"]]),
        ]
        err = io.StringIO()
        with contextlib.ExitStack() as st:
            for p in patches:
                st.enter_context(p)
            st.enter_context(contextlib.redirect_stdout(io.StringIO()))
            st.enter_context(contextlib.redirect_stderr(err))
            return pp.main(["--check"]), err.getvalue()

    def test_identical_index_returns_zero(self):
        rc, _ = self._run(copy.deepcopy(self.summaries))
        self.assertEqual(rc, 0)

    def test_changed_verdict_returns_one(self):
        built = copy.deepcopy(self.summaries)
        built[0]["klt_drc"]["status"] = "fail"
        rc, err = self._run(built)
        self.assertEqual(rc, 1)
        self.assertIn("differs", err)


if __name__ == "__main__":
    unittest.main()
