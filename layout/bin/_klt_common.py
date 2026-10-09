#!/usr/bin/env python3
"""Shared ``klt``-invocation plumbing for ``layout/bin/`` scripts.

Ported verbatim (contract unchanged, docstrings trimmed to this repo) from
2AMLogic/sky130-trng ``layout/bin/_klt_common.py`` at commit
``5d443907c99bf4eb193092f0cf89f2a6e2a5c80e``.

Contract: shell out to ``klt ... --format json``; a missing/unparsable JSON
response is fatal, an ``error`` object in an otherwise well-formed response
is fatal, and committed JSON is written with one fixed spelling.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


class BuildError(RuntimeError):
    """A step of the chain failed."""


def run_klt(
    args: list[str],
    *,
    env: dict[str, str],
    cwd: Path | None = None,
    klt: str = "klt",
) -> dict:
    """Run ``klt`` with ``--format json`` from *cwd* and parse its response.

    Callers invoke from the artifact's own output directory with *relative*
    paths, so committed responses record repo-relative provenance and no
    absolute home path leaks into the evidence.

    A non-zero exit is not automatically fatal: ``klt gen-compose`` exits 3
    for a partial success (some net unrouted) and ``klt lvs`` exits 3 for a
    clean-run mismatch; callers report those from the response body. A
    response that is not JSON at all is fatal, as is one carrying ``error``.
    """
    proc = subprocess.run(
        [klt, *args, "--format", "json"],
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd,
        check=False,
    )
    try:
        response = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise BuildError(
            f"{klt} {' '.join(args)} produced no JSON response "
            f"(exit {proc.returncode}):\n{proc.stdout}\n{proc.stderr}"
        ) from exc
    if "error" in response:
        raise BuildError(
            f"{klt} {' '.join(args)} failed: {response['error'].get('message')}"
        )
    return response


def write_json(path: Path, payload: dict) -> None:
    """Write *payload* as committed-artifact JSON (2-space, ordered, newline)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")
