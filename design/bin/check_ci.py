#!/usr/bin/env python3
"""Run the simulator-free CI gate (stdlib only).

Single source of the gate commands: CI's `unit-tests` workflow and local
runs (`python3 design/bin/check_ci.py` here, or `npm test`) both execute
this script, so the command list exists in exactly one place. CI passes
--pr-base origin/<base_ref> on pull_request to add the committed-only
append-only check; locally the same check runs with --local when the base
resolves.

Never runs netlist_check.py regeneration or the EndToEnd cases (they need
xschem and the pinned PDK; see design-sources.yml). Runs sequentially and
stops at the first failure.
"""

import argparse
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
        ("canonical MOS+passive grid legality", [py, "design/bin/grid_check.py"]),
        ("generic evidence artifact hashes (signoff.yml)",
         [py, "design/bin/generic_evidence_check.py"]),
        ("artifact manifests (issue #240)", [py, "sim/lib/check_artifact_manifests.py"]),
        ("unit tests", [py, "-m", "unittest", "discover", "-s", "tests", "-v"]),
        ("layout flow unit tests",
         [py, "-m", "unittest", "discover", "-s", "layout/bin", "-p", "test_*.py", "-v"]),
        ("netlist compare controls (CompareUnit)",
         [py, "design/bin/test_netlist_check.py", "CompareUnit", "-v"]),
    ]


def append_only_check(py=None, local=False, base=BASE_REF):
    """PR form (committed only, --base REF) by default; local=True adds staged/working-tree."""
    py = py or sys.executable
    cmd = [py, "sim/lib/append_only_check.py", "--base", base]
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


def main(repo=REPO, resolves=ref_resolves, run=subprocess.run, pr_base=None):
    """pr_base (from --pr-base) = CI/PR mode: committed-only append-only
    check against that ref, never skipped, no --local. Default = local mode."""
    checks = default_checks()
    if pr_base is not None:
        checks.append(append_only_check(base=pr_base, local=False))
    elif resolves(BASE_REF, repo):
        checks.append(append_only_check(local=True))
    else:
        print(f"==> append-only evidence: SKIPPED ({BASE_REF} does not resolve; "
              f"run `git fetch origin main` to enable)")
    rc, failed = run_checks(checks, repo, run)
    if rc == 0:
        print("All simulator-free checks passed.")
    return rc


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the simulator-free CI gate (the single source of the "
                    "gate commands; CI's unit-tests workflow calls this script).")
    parser.add_argument(
        "--pr-base", metavar="REF",
        help="PR mode: append the committed-only append-only check against REF "
             "(no --local, never skipped); e.g. --pr-base origin/main")
    args = parser.parse_args()
    sys.exit(main(pr_base=args.pr_base))
