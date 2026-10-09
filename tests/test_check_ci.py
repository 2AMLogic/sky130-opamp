import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import _paths  # noqa: F401
check_ci = _paths.load_module("check_ci", _paths.REPO / "design" / "bin" / "check_ci.py")


def fake_run(fail_on=None, log=None):
    def run(cmd, cwd=None):
        if log is not None:
            log.append(cmd)
        rc = 3 if fail_on and fail_on in " ".join(cmd) else 0
        return SimpleNamespace(returncode=rc)
    return run


class CheckCiTests(unittest.TestCase):
    def test_inventory_matches_workflow(self):
        text = (_paths.REPO / ".github/workflows/tests.yml").read_text()
        for name, cmd in check_ci.default_checks("python"):
            if "test_netlist_check" in " ".join(cmd):
                continue
            self.assertIn(" ".join(["python"] + cmd[1:]), text, name)

    def test_netlist_selects_compareunit_not_endtoend(self):
        joined = [" ".join(c) for _, c in check_ci.default_checks()]
        netlist = [j for j in joined if "test_netlist_check" in j]
        self.assertEqual(len(netlist), 1)
        self.assertIn("CompareUnit", netlist[0])
        self.assertNotIn("EndToEnd", " ".join(joined))
        self.assertFalse(any("netlist_check.py" in j and "test_" not in j for j in joined))

    def test_failure_stops_later_checks(self):
        log = []
        rc = check_ci.main(resolves=lambda *a: True, run=fake_run("integrator_check", log))
        self.assertNotEqual(rc, 0)
        joined = [" ".join(c) for c in log]
        self.assertTrue(any("integrator_check" in j for j in joined))
        self.assertFalse(any("spec_figures_check" in j or "append_only" in j for j in joined))

    def test_missing_base_skips_append_only(self):
        log = []
        rc = check_ci.main(resolves=lambda *a: False, run=fake_run(log=log))
        self.assertEqual(rc, 0)
        self.assertFalse(any("append_only" in " ".join(c) for c in log))

    def test_existing_base_runs_append_only_and_propagates(self):
        log = []
        self.assertEqual(check_ci.main(resolves=lambda *a: True, run=fake_run(log=log)), 0)
        self.assertIn("append_only", " ".join(log[-1]))
        self.assertEqual(
            check_ci.main(resolves=lambda *a: True, run=fake_run("append_only")), 3)

    def test_ref_resolves(self):
        self.assertFalse(check_ci.ref_resolves("refs/nonexistent/zzz"))
        self.assertTrue(check_ci.ref_resolves("HEAD"))

    def test_stub_xschem_never_invoked(self):
        """Inventory never names xschem; a failing stub on PATH is not touched."""
        with tempfile.TemporaryDirectory() as d:
            marker = Path(d) / "called"
            stub = Path(d) / "xschem"
            stub.write_text(f"#!/bin/sh\ntouch {marker}\nexit 1\n")
            stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
            env = dict(os.environ, PATH=d + os.pathsep + os.environ["PATH"],
                       PDK_ROOT=str(Path(d) / "absent"))
            code = ("import sys; sys.path.insert(0, 'tests'); import _paths; "
                    "m=_paths.load_module('c','design/bin/check_ci.py'); "
                    "import subprocess; "
                    "[subprocess.run(c, cwd='.', env=None) for n,c in m.default_checks() "
                    "if 'test_netlist_check' in ' '.join(c)]")
            r = subprocess.run([sys.executable, "-c", code], cwd=_paths.REPO, env=env)
            self.assertEqual(r.returncode, 0)
            self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
