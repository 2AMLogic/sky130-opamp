"""Helpers shared by the design-tree gate scripts (stdlib-only).

Scripts in this directory run as ``python3 design/bin/<script>.py``, which puts
this directory on ``sys.path[0]``, so ``from _common import ...`` resolves
without a ``sys.path`` shim.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

_LIB = Path(__file__).resolve().parents[2] / "lib"
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))
from spice_text import join_continuations  # noqa: E402

__all__ = ["join_continuations", "sha256_prefixed"]


def sha256_prefixed(path) -> str:
    """Return ``sha256:<hex>`` of the file's bytes (the evidence-JSON form)."""
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()
