#!/usr/bin/env python3
"""Unit tests for layout/bin/_klt_common.py (run_klt, write_json).

Run: python3 -m unittest layout/bin/test_klt_common.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _klt_common import BuildError, run_klt, write_json  # noqa: E402


def _proc(stdout: str, returncode: int = 0, stderr: str = ""):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


class RunKltTests(unittest.TestCase):
    def _run(self, proc, *args, **kwargs):
        with mock.patch("_klt_common.subprocess.run", return_value=proc) as m:
            kwargs.setdefault("env", {})
            result = run_klt(list(args) or ["lvs"], **kwargs)
        return result, m

    def test_exit_zero_returns_parsed_dict(self):
        result, _ = self._run(_proc('{"ok": true, "n": 1}'))
        self.assertEqual(result, {"ok": True, "n": 1})

    def test_exit_three_without_error_is_returned(self):
        result, _ = self._run(_proc('{"unrouted": ["a"]}', returncode=3))
        self.assertEqual(result, {"unrouted": ["a"]})

    def test_non_json_stdout_raises_with_exit_and_stderr(self):
        with self.assertRaises(BuildError) as cm:
            self._run(_proc("not json", returncode=2, stderr="boom happened"))
        msg = str(cm.exception)
        self.assertIn("exit 2", msg)
        self.assertIn("boom happened", msg)

    def test_error_object_raises_with_message(self):
        proc = _proc('{"error": {"message": "bad thing"}}', returncode=1)
        with self.assertRaises(BuildError) as cm:
            self._run(proc)
        self.assertIn("bad thing", str(cm.exception))

    def test_argv_format_json_last_and_cwd_env_passthrough(self):
        env = {"A": "1"}
        cwd = Path("/some/dir")
        _, m = self._run(
            _proc("{}"), "gen-compose", "x.json", env=env, cwd=cwd, klt="myklt"
        )
        argv = m.call_args.args[0]
        self.assertEqual(argv[0], "myklt")
        self.assertEqual(argv[-2:], ["--format", "json"])
        self.assertEqual(argv[1:-2], ["gen-compose", "x.json"])
        self.assertIs(m.call_args.kwargs["env"], env)
        self.assertEqual(m.call_args.kwargs["cwd"], cwd)


class WriteJsonTests(unittest.TestCase):
    def test_format_order_and_parent_dirs(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "a" / "b" / "out.json"
            write_json(path, {"z": 1, "a": [1, 2]})
            text = path.read_text()
        self.assertEqual(text, '{\n  "z": 1,\n  "a": [\n    1,\n    2\n  ]\n}\n')
        self.assertEqual(list(json.loads(text)), ["z", "a"])


if __name__ == "__main__":
    unittest.main()
