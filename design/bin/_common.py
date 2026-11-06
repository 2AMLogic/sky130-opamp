"""Helpers shared by the design-tree gate scripts (stdlib-only).

Scripts in this directory run as ``python3 design/bin/<script>.py``, which puts
this directory on ``sys.path[0]``, so ``from _common import ...`` resolves
without a ``sys.path`` shim.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_prefixed(path) -> str:
    """Return ``sha256:<hex>`` of the file's bytes (the evidence-JSON form)."""
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def join_continuations(text: str) -> list[str]:
    """Return SPICE logical lines: comments and blanks dropped, ``+`` joined.

    Comment (``*``) and blank lines are dropped *before* joining, so a comment
    between a card and its ``+`` continuation does not swallow the continuation.
    Each line is stripped; a ``+`` line is appended to the previous card with a
    single space. A leading orphan ``+`` (no card to join to) starts its own line.
    """
    out: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("*"):
            continue
        if line.startswith("+") and out:
            out[-1] += " " + line[1:].strip()
        else:
            out.append(line)
    return out
