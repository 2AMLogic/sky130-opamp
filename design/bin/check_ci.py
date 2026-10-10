#!/usr/bin/env python3
"""Run the simulator-free CI gate locally (stdlib only).

Mirrors .github/workflows/tests.yml plus the tool-free CompareUnit controls of
design/bin/test_netlist_check.py. The workflows stay the source of truth; this
is a local entrypoint so `npm test` / `npm run check:ci` are not vacuous.

Never runs netlist_check.py regeneration or the EndToEnd cases (they need
xschem and the pinned PDK; see design-sources.yml). Runs sequentially and
stops at the first failure.
"""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
BASE_REF = "origin/main"


def default_checks(py=None):
    py = py or sys.executable
    return [
        ("sizing_check validate", [py, "design/bin/sizing_check.py", "validate"]),
        ("integrator_check validate", [py, "design/bin/integrator_check.py", "validate"]),
        ("spec_figures_check validate", [py, "design/bin/spec_figures_check.py", "validate"]),
        ("dut_identity validate", [py, "sim/lib/dut_identity.py", "validate"]),
        ("dut_identity current", [py, "sim/lib/dut_identity.py", "current"]),
        ("passive grid legality", [py, "design/bin/grid_check.py"]),
        ("generic evidence artifact hashes (signoff.yml)",
         [py, "design/bin/generic_evidence_check.py"]),
        ("unit tests", [py, "-m", "unittest", "discover", "-s", "tests", "-v"]),
        ("layout flow unit tests",
         [py, "-m", "unittest", "discover", "-s", "layout/bin", "-p", "test_*.py", "-v"]),
        ("netlist compare controls (CompareUnit)",
         [py, "design/bin/test_netlist_check.py", "CompareUnit", "-v"]),
    ]


def append_only_check(py=None, local=False):
    """PR form (committed only) by default; local=True adds staged/working-tree."""
    py = py or sys.executable
    cmd = [py, "sim/lib/append_only_check.py", "--base", BASE_REF]
    if local:
        cmd.append("--local")
    return ("append-only evidence", cmd)


def ref_resolves(ref, repo=REPO):
    try:
        r = subprocess.run(["git", "rev-parse", "--verify", "--quiet", ref + "^{commit}"],
                           cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return False
    return r.returncode == 0


def run_checks(checks, repo=REPO, run=subprocess.run):
    """Run checks in order; return (exit_code, failed_name or None)."""
    for name, cmd in checks:
        print(f"==> {name}: {' '.join(cmd[1:])}", flush=True)
        rc = run(cmd, cwd=repo).returncode
        if rc != 0:
            print(f"FAILED: {name} (exit {rc}); later checks not run", file=sys.stderr)
            return (rc or 1), name
    return 0, None


def main(repo=REPO, resolves=ref_resolves, run=subprocess.run):
    checks = default_checks()
    if resolves(BASE_REF, repo):
        checks.append(append_only_check(local=True))
    else:
        print(f"==> append-only evidence: SKIPPED ({BASE_REF} does not resolve; "
              f"run `git fetch origin main` to enable)")
    rc, failed = run_checks(checks, repo, run)
    if rc == 0:
        print("All simulator-free checks passed.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
