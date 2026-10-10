import os
import re
import shlex
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


# Intentional local-only additions vs tests.yml: tool-free CompareUnit controls, and
# the generic-evidence hash gate (its workflow home is signoff.yml; see test_generic_evidence_check).
LOCAL_ONLY = ("test_netlist_check", "generic_evidence_check")


def workflow_commands(text):
    """Return (unconditional, conditional) run commands from a workflow (no YAML dep).

    Each is a list of shlex-split token lists. A step is conditional if it has
    an `if:` line. Handles `run: cmd` and `run: |` block scalars.
    """
    steps, cur = [], None
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^(\s*)- (?:name|uses):", line)
        if m:
            cur = {"indent": len(m.group(1)), "if": False, "cmds": []}
            steps.append(cur)
        elif cur is not None:
            st = line.strip()
            if st.startswith("if:"):
                cur["if"] = True
            elif st.startswith("run:"):
                rest = st[4:].strip()
                if rest in ("|", "|-", ">", ">-"):
                    ind = len(line) - len(line.lstrip())
                    i += 1
                    while i < len(lines) and (not lines[i].strip()
                                              or len(lines[i]) - len(lines[i].lstrip()) > ind):
                        if lines[i].strip():
                            cur["cmds"].append(lines[i].strip())
                        i += 1
                    continue
                cur["cmds"].append(rest)
        i += 1
    uncond = [shlex.split(c) for s in steps if not s["if"] for c in s["cmds"]]
    cond = [shlex.split(c) for s in steps if s["if"] for c in s["cmds"]]
    return uncond, cond


def inventory_problems(workflow_text, checks):
    """Compare workflow and local inventories; return a list of problem strings.

    - every local check (except LOCAL_ONLY) must appear as a workflow command;
    - every unconditional workflow command must be a local check, same order;
    - conditional workflow commands must be exactly the PR-only append-only
      check, which the local runner appends separately (base ref differs).
    """
    uncond, cond = workflow_commands(workflow_text)
    local = [["python"] + c[1:] for _, c in checks
             if not any(t in " ".join(c) for t in LOCAL_ONLY)]
    problems = []
    for cmd in local:
        if cmd not in uncond:
            problems.append("local check not in workflow: " + shlex.join(cmd))
    for cmd in uncond:
        if cmd not in local:
            problems.append("workflow command missing locally: " + shlex.join(cmd))
    if not problems and local != uncond:
        problems.append("local check order differs from workflow")
    ao = check_ci.append_only_check("python")[1]
    if [c[:3] for c in cond] != [ao[:2] + ["--base"]]:
        problems.append("unexpected conditional workflow commands: %r" % (cond,))
    return problems


class CheckCiTests(unittest.TestCase):
    def test_inventory_matches_workflow(self):
        text = (_paths.REPO / ".github/workflows/tests.yml").read_text()
        self.assertEqual(inventory_problems(text, check_ci.default_checks("python")), [])

    def test_grid_check_in_local_gate(self):
        joined = [" ".join(c) for _, c in check_ci.default_checks()]
        self.assertTrue(any(j.endswith("design/bin/grid_check.py") for j in joined))

    def test_workflow_omission_is_detected(self):
        """Negative control: an unconditional workflow command absent locally fails."""
        text = (_paths.REPO / ".github/workflows/tests.yml").read_text()
        text += ("\n      - name: New check\n"
                 "        run: python design/bin/new_check.py\n")
        problems = inventory_problems(text, check_ci.default_checks("python"))
        self.assertTrue(any("new_check.py" in p and "missing locally" in p
                            for p in problems), problems)

    def test_local_omission_of_existing_check_is_detected(self):
        text = (_paths.REPO / ".github/workflows/tests.yml").read_text()
        checks = [c for c in check_ci.default_checks("python") if "grid_check" not in " ".join(c[1])]
        problems = inventory_problems(text, checks)
        self.assertTrue(any("grid_check.py" in p for p in problems), problems)

    def test_grid_failure_stops_later_checks(self):
        log = []
        rc = check_ci.main(resolves=lambda *a: True, run=fake_run("grid_check", log))
        self.assertNotEqual(rc, 0)
        joined = [" ".join(c) for c in log]
        self.assertTrue(any("grid_check" in j for j in joined))
        self.assertFalse(any("unittest" in j or "append_only" in j for j in joined))

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

    def test_local_mode_requested_and_pr_form_unchanged(self):
        log = []
        check_ci.main(resolves=lambda *a: True, run=fake_run(log=log))
        self.assertIn("--local", log[-1])
        self.assertIn("append_only", " ".join(log[-1]))
        self.assertNotIn("--local", check_ci.append_only_check("python")[1])
        self.assertIn("--local", check_ci.append_only_check("python", local=True)[1])

    def test_missing_base_skip_is_explicit(self):
        import contextlib, io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            check_ci.main(resolves=lambda *a: False, run=fake_run())
        self.assertIn("append-only evidence: SKIPPED", buf.getvalue())
        self.assertIn(check_ci.BASE_REF, buf.getvalue())

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
