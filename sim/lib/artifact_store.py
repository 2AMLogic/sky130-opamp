"""Store new sim evidence bytes in the fleet artifact store; git keeps a manifest.

Flow (issue #240, 2AMLogic/2am#5553): a runner stages its raw outputs under the
git-ignored `sim/.work/.stage/<bench>-<run-id>/`, then `store()` hands them to
`klt artifact put --manifest manifests/artifacts/<bench>-<run-id>.manifest.json`
and writes a Markdown summary (name, size, sha256 per object) beside it. Only
the manifest and the summary are committed.

Fail closed, no fallback to committing bytes:
  * `preflight()` runs BEFORE a runner simulates or reserves anything: it needs
    `$KLT_ARTIFACT_BROKER`, a klt that has `artifact put`, and a reachable broker.
  * `store()` puts into a temporary manifest outside the repo and only moves it
    (and the summary) under `manifests/artifacts/` after the put succeeded, so a
    failed put leaves nothing under `manifests/`; the stage is kept for a retry.
The broker URL is never put in argv, files or messages: klt reads it from the
environment, and any text echoed from klt has the value scrubbed.

Zero-byte files cannot be stored (a manifest entry needs size >= 1); they are
skipped and listed in the summary. Stdlib only.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import socket
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STAGE_ROOT = REPO_ROOT / "sim" / ".work" / ".stage"
MANIFEST_DIR = REPO_ROOT / "manifests" / "artifacts"
BROKER_ENV = "KLT_ARTIFACT_BROKER"
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class ArtifactError(RuntimeError):
    pass


def klt_command(env=None) -> list[str]:
    env = os.environ if env is None else env
    return shlex.split(env.get("KLT_CMD") or "klt")


def _scrub(text: str, env) -> str:
    broker = (env.get(BROKER_ENV) or "").strip()
    return text.replace(broker, "<broker>") if broker else text


def _broker_reachable(broker: str, timeout: float = 5.0) -> bool:
    parts = urlsplit(broker)
    if not parts.hostname:
        return False
    port = parts.port or (443 if parts.scheme == "https" else 80)
    try:
        socket.create_connection((parts.hostname, port), timeout).close()
    except OSError:
        return False
    return True


def preflight(env=None, runner=subprocess.run, reachable=_broker_reachable) -> list[str]:
    """Raise ArtifactError unless evidence can be stored; return the klt command."""
    env = os.environ if env is None else env
    broker = (env.get(BROKER_ENV) or "").strip()
    if not broker:
        raise ArtifactError(f"${BROKER_ENV} is unset: cannot store evidence (no fallback to committing bytes)")
    klt = klt_command(env)
    try:
        r = runner([*klt, "artifact", "put", "--help"], capture_output=True, text=True, env=dict(env))
    except OSError as exc:
        raise ArtifactError(f"cannot run {klt[0]}: {exc.strerror or exc}") from None
    if r.returncode != 0:
        raise ArtifactError(f"{' '.join(klt)} lacks `artifact put` (need klayout-tools 7e3561f or later)")
    if not reachable(broker):
        raise ArtifactError("artifact broker is unreachable")
    return klt


def _check_name(label: str, value: str) -> None:
    if not _NAME_RE.match(value):
        raise ArtifactError(f"bad {label} {value!r}")


def stage_dir(bench: str, run_id: str, root: Path | None = None) -> Path:
    """Create and return the git-ignored stage directory for one run."""
    _check_name("bench", bench)
    _check_name("run id", run_id)
    path = (STAGE_ROOT if root is None else root) / f"{bench}-{run_id}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def render_summary(bench: str, run_id: str, entries: list[dict], skipped_empty: list[str]) -> str:
    lines = [
        f"# Evidence artifacts: {bench} {run_id}",
        "",
        f"Manifest: `manifests/artifacts/{bench}-{run_id}.manifest.json`. Bytes live in the fleet "
        "artifact store; fetch or check with `klt artifact get|verify`.",
        "",
        "| name | size (bytes) | sha256 |",
        "| --- | ---: | --- |",
    ]
    for e in sorted(entries, key=lambda e: e.get("name", "")):
        lines.append(f"| `{e.get('name', '')}` | {e['size']} | `{e['sha256']}` |")
    if skipped_empty:
        lines += ["", "Zero-byte outputs (not storable, none stored):", ""]
        lines += [f"- `{n}`" for n in sorted(skipped_empty)]
    return "\n".join(lines) + "\n"


def store(bench: str, run_id: str, stage: Path, klt: list[str], *, env=None, runner=subprocess.run,
          repo_root: Path | None = None, manifest_dir: Path | None = None) -> tuple[Path, Path]:
    """Put every file under `stage`; return (manifest path, summary path).

    Raises ArtifactError, leaving nothing under the manifest directory.
    """
    env = os.environ if env is None else env
    _check_name("bench", bench)
    _check_name("run id", run_id)
    repo_root = REPO_ROOT if repo_root is None else repo_root
    manifest_dir = MANIFEST_DIR if manifest_dir is None else manifest_dir
    files = sorted(p for p in Path(stage).rglob("*") if p.is_file())
    empty = [p for p in files if p.stat().st_size == 0]
    files = [p for p in files if p.stat().st_size > 0]
    if not files:
        raise ArtifactError(f"nothing to store under {stage}")
    final = manifest_dir / f"{bench}-{run_id}.manifest.json"
    summary = manifest_dir / f"{bench}-{run_id}.summary.md"
    for p in (final, summary):
        if p.exists():
            raise ArtifactError(f"refusing to overwrite append-only {p.name}")
    with tempfile.TemporaryDirectory(prefix="artifact-manifest-") as tmp:
        tmp_manifest = Path(tmp) / final.name
        cmd = [*klt, "artifact", "put", "--manifest", str(tmp_manifest), "--kind", "evidence",
               *(str(p) for p in files)]
        try:
            r = runner(cmd, capture_output=True, text=True, env=dict(env), cwd=str(repo_root))
        except OSError as exc:
            raise ArtifactError(f"cannot run {klt[0]}: {exc.strerror or exc}") from None
        if r.returncode != 0:
            tail = _scrub((r.stderr or r.stdout or "").strip()[-400:], env)
            raise ArtifactError(f"`klt artifact put` failed (exit {r.returncode}); stage kept at {stage}: {tail}")
        try:
            manifest_text = tmp_manifest.read_text(encoding="utf-8")
            entries = json.loads(manifest_text)["entries"]
        except (OSError, ValueError, KeyError) as exc:
            raise ArtifactError(f"`klt artifact put` wrote no usable manifest: {exc}") from None
        bad = [e for e in entries if not str(e.get("uri", "")).startswith("artifact:")]
        if bad or len(entries) < len(files):
            raise ArtifactError("manifest has non-artifact: URIs or fewer entries than staged files")
        manifest_dir.mkdir(parents=True, exist_ok=True)
        rel = lambda p: p.relative_to(repo_root).as_posix() if p.is_relative_to(repo_root) else p.name  # noqa: E731
        with open(final, "x", encoding="utf-8") as f:
            f.write(manifest_text)
        with open(summary, "x", encoding="utf-8") as f:
            f.write(render_summary(bench, run_id, entries, [rel(p) for p in empty]))
    return final, summary
