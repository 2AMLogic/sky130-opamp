"""Shared PDK-resolution and ngspice-harness helpers for this repo's sim runners.

One copy of the logic that every `sim/*/bin/*.py` sweep runner needs before it
can drive ngspice: resolving the installed PDK against a committed `pdk.json`
pin, rendering a `.spice.tmpl` deck, reporting a tool version, and stamping a
record with the repo's git SHA. Extracted from
`sim/gm-id-characterization/bin/sweep.py` and
`sim/opamp-characterization/bin/pvt_sweep.py`, which carried near-identical
copies of all of it (issue #23).

Stdlib only -- the runners that import this promise "python3 + ngspice and
nothing else", and this module must not weaken that.

Import it from a runner by putting `sim/lib` on `sys.path` first, since the
runners are executed as scripts (`python3 sim/<exp>/bin/<runner>.py`) rather
than as a package:

    EXP_DIR = Path(__file__).resolve().parent.parent
    REPO_ROOT = EXP_DIR.parent.parent
    sys.path.insert(0, str(REPO_ROOT / "sim" / "lib"))
    from spice_harness import HarnessError, Pdk, first_line, git_sha, load_json, render

Experiment-specific resolution stays in the runner: `Pdk` here covers only the
MOS process-corner include files that every experiment needs. An experiment
that resolves additional include files (e.g. the op-amp bench's R+C corner)
subclasses `Pdk` and extends `validate()`.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Iterable
from pathlib import Path


class HarnessError(RuntimeError):
    pass


# --------------------------------------------------------------------------
# PDK resolution (same shape as sky130-ldo's sim/bin/corner-run.py resolve_pdk,
# adapted to a per-experiment pdk.json that points at the per-corner ngspice
# include files rather than the combined library -- see
# ../gm-id-characterization/corners/README.md for why).
# --------------------------------------------------------------------------


def load_json(path: Path) -> dict:
    if not path.exists():
        raise HarnessError(f"missing file: {path}")
    return json.loads(path.read_text())


def volare_path() -> Path | None:
    exe = shutil.which("volare")
    if not exe:
        return None
    try:
        out = subprocess.run(
            [exe, "path"], capture_output=True, text=True, timeout=60, check=True
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return None
    return Path(out) if out else None


class Pdk:
    """An installed PDK resolved against a committed `pdk.json` pin.

    Resolution order for the PDK root: `$PDK_ROOT`, then `volare path`, then the
    pin's own `default_pdk_root`. The variant (e.g. `sky130A`) comes from `$PDK`
    if set, else the pin's `variant`.
    """

    def __init__(self, pin: dict):
        self.pin = pin
        root_env = os.environ.get("PDK_ROOT", "").strip()
        self.root = Path(root_env).expanduser() if root_env else (
            volare_path() or Path(pin["default_pdk_root"]).expanduser()
        )
        self.variant = os.environ.get("PDK", "").strip() or pin["variant"]
        self.dir = self.root / self.variant
        self.corner_dir = self.dir / pin["ngspice_corner_dir"]
        self.installed_commit = self._installed_commit()

    def _installed_commit(self) -> str:
        parts = self.dir.resolve().parts
        if "versions" in parts:
            idx = parts.index("versions")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        return "unknown"

    @property
    def matches_pin(self) -> bool:
        return self.installed_commit == self.pin["open_pdks_commit"]

    def corner_include(self, corner: str) -> Path:
        return self.corner_dir / f"{corner}.spice"

    def validate(self, corners: Iterable[str]) -> None:
        if not self.dir.is_dir():
            raise HarnessError(
                f"no PDK at {self.dir}\n"
                f"  install the pinned version with: {self.pin['install_command']}\n"
                f"  (or set PDK_ROOT / PDK to an existing install)"
            )
        for corner in corners:
            inc = self.corner_include(corner)
            if not inc.is_file():
                raise HarnessError(f"missing corner include: {inc}")


# --------------------------------------------------------------------------
# Tooling / rendering / provenance
# --------------------------------------------------------------------------


def first_line(cmd: list[str]) -> str:
    """First non-empty output line of `cmd` -- the tool-version string a record stamps."""
    exe = shutil.which(cmd[0])
    if not exe:
        return "not found"
    try:
        proc = subprocess.run([exe, *cmd[1:]], capture_output=True, text=True, timeout=60)
    except (subprocess.SubprocessError, OSError) as exc:  # pragma: no cover
        return f"error: {exc}"
    for line in (proc.stdout + "\n" + proc.stderr).splitlines():
        line = line.strip().lstrip("*").strip()
        if line:
            return line
    return "unknown"


def render(template_path: Path, subs: dict) -> str:
    """Substitute `{KEY}` placeholders in a deck template; fail on any left over."""
    text = template_path.read_text()
    for key, val in subs.items():
        text = text.replace("{" + key + "}", str(val))
    if "{" in text and "}" in text:
        remaining = {seg.split("}", 1)[0] for seg in text.split("{")[1:] if "}" in seg}
        if remaining:
            raise HarnessError(f"unsubstituted placeholders in {template_path.name}: {remaining}")
    return text


def git_sha(repo_root: Path) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10, check=True,
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return "unknown"
