#!/usr/bin/env python3
"""Unit tests for layout/bin/_klt_common.py (run_klt, write_json).

Run: python3 -m unittest layout/bin/test_klt_common.py
"""

from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _klt_common import BuildError, check_toolchain, run_klt, write_json  # noqa: E402


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

    def test_klt_sequence_is_expanded_into_argv(self):
        _, m = self._run(_proc("{}"), "version", klt=["uvx", "--from", "pkg", "klt"])
        argv = m.call_args.args[0]
        self.assertEqual(argv, ["uvx", "--from", "pkg", "klt", "version", "--format", "json"])

    def test_klt_sequence_appears_in_error_message(self):
        with self.assertRaises(BuildError) as ctx:
            self._run(_proc('{"error": {"message": "boom"}}'), "version", klt=["uvx", "klt"])
        self.assertIn("uvx klt version failed: boom", str(ctx.exception))


CHECK_TOOLCHAIN_PIN = {
    "variant": "sky130A",
    "klt_commit": "4cbdfa7698752b720c0e627163867de1e23475f3",
    "open_pdks_commit": "c6d73a35f524070e85faff4a6a9eef49553ebc2b",
}


class CheckToolchainTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pin_path = Path(self.tmp.name) / "pdk.json"
        self.pin_path.write_text(json.dumps(CHECK_TOOLCHAIN_PIN))
        self.pdk_response = {
            "variant": "sky130A",
            "version": f"open_pdks {CHECK_TOOLCHAIN_PIN['open_pdks_commit']}",
            "assets": {"magic": "/x/libs.tech/magic"},
        }

    def _check(self, ver=None, pdk=None, **kwargs):
        responses = {
            "version": ver if ver is not None else {
                "version": "0.7.0+g4cbdfa769875",
                "git_commit": CHECK_TOOLCHAIN_PIN["klt_commit"],
            },
            "pdk find": pdk if pdk is not None else self.pdk_response,
        }
        calls = []

        def fake_run_klt(args, *, env, cwd=None, klt="klt"):
            calls.append({"argv": list(args), "env": env, "cwd": cwd, "klt": klt})
            return responses[" ".join(args[:2])]

        with mock.patch("_klt_common.run_klt", side_effect=fake_run_klt):
            result = check_toolchain(kwargs.pop("env", {}), pin_path=self.pin_path, **kwargs)
        return result, calls

    def test_matching_pins_return_tools_and_pdk(self):
        (tools, pdk), calls = self._check()
        self.assertEqual(tools, {
            "klt": "0.7.0+g4cbdfa769875",
            "pdk": f"open_pdks {CHECK_TOOLCHAIN_PIN['open_pdks_commit']}",
        })
        self.assertIs(pdk, self.pdk_response)
        self.assertEqual([c["argv"][:2] for c in calls], [["version"], ["pdk", "find"]])

    def test_klt_commit_mismatch_raises_build_error(self):
        ver = {"version": "0.7.0", "git_commit": "deadbeef"}
        with self.assertRaises(BuildError) as cm:
            self._check(ver=ver)
        msg = str(cm.exception)
        self.assertIn("klt git_commit deadbeef != pinned", msg)
        self.assertIn("(see layout/README.md, 'Toolchain')", msg)

    def test_open_pdks_mismatch_raises_build_error(self):
        pdk = {**self.pdk_response, "version": "open_pdks f6eeac7dad08"}
        with self.assertRaises(BuildError) as cm:
            self._check(pdk=pdk)
        self.assertIn("PDK version 'open_pdks f6eeac7dad08' != pinned", str(cm.exception))

    def test_pdk_version_absent_raises_build_error_not_match(self):
        pdk = {k: v for k, v in self.pdk_response.items() if k != "version"}
        with self.assertRaises(BuildError) as cm:
            self._check(pdk=pdk)
        self.assertIn("PDK version None != pinned", str(cm.exception))

    def test_allow_unpinned_warns_on_stderr_and_returns(self):
        ver = {"version": "0.7.0", "git_commit": "deadbeef"}
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            (tools, _pdk), _calls = self._check(ver=ver, allow_unpinned=True)
        self.assertEqual(tools, {"klt": "0.7.0", "pdk": self.pdk_response["version"]})
        self.assertIn("warning: toolchain does not match layout/pdk.json", err.getvalue())
        self.assertIn("klt git_commit deadbeef", err.getvalue())

    def test_missing_version_key_yields_none_not_keyerror(self):
        ver = {"git_commit": CHECK_TOOLCHAIN_PIN["klt_commit"]}
        (tools, _pdk), _calls = self._check(ver=ver)
        self.assertIsNone(tools["klt"])

    def test_custom_klt_sequence_variant_and_cwd_passthrough(self):
        klt = ["uvx", "--from", "pkg", "klt"]
        cwd = Path("/repo")
        _, calls = self._check(variant="sky130B", klt=klt, cwd=cwd)
        self.assertEqual([c["klt"] for c in calls], [klt, klt])
        self.assertEqual([c["cwd"] for c in calls], [cwd, cwd])
        self.assertEqual(calls[1]["argv"], ["pdk", "find", "--pdk", "sky130B"])

    def test_variant_defaults_to_pin_variant(self):
        _, calls = self._check()
        self.assertEqual(calls[1]["argv"], ["pdk", "find", "--pdk", "sky130A"])


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
