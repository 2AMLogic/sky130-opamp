#!/usr/bin/env python3
"""CI check for committed evidence manifests under manifests/artifacts/.

Fails when a `*.manifest.json` there:
  * is not `{schema_version: 1, entries: [...]}` with well-formed entries
    (sha256 = 64 lowercase hex, size >= 1, kind, producer, uri);
  * has a `uri` that is not `artifact:<key>` (storage URLs are never accepted);
  * names an object whose bytes (same sha256) are also tracked by git;
and fails if any file under manifests/ contains `s3://` or `arn:aws:`.

Usage: check_artifact_manifests.py [--root DIR]    (stdlib only)
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

MANIFEST_GLOB = "manifests/artifacts/*.manifest.json"
FORBIDDEN = re.compile(r"s3://|arn:aws:")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED = ("sha256", "size", "kind", "producer", "uri")
OPTIONAL = ("name", "media_type")


def entry_problems(entry) -> list:
    if not isinstance(entry, dict):
        return ["entry is not an object"]
    out = [f"missing {f}" for f in REQUIRED if f not in entry]
    out += [f"unknown field {f}" for f in sorted(set(entry) - set(REQUIRED) - set(OPTIONAL))]
    sha = entry.get("sha256")
    if not isinstance(sha, str) or not SHA_RE.match(sha):
        out.append("sha256 must be 64 lowercase hex digits")
    size = entry.get("size")
    if not isinstance(size, int) or isinstance(size, bool) or size < 1:
        out.append("size must be a positive integer")
    if not isinstance(entry.get("kind"), str):
        out.append("kind must be a string")
    if not isinstance(entry.get("producer"), dict):
        out.append("producer must be an object")
    uri = entry.get("uri")
    if not isinstance(uri, str) or not uri.startswith("artifact:") or len(uri) == len("artifact:"):
        out.append("uri must be artifact:<key>")
    return out


def manifest_problems(text: str) -> tuple:
    """Return (problems, set of sha256 named by the manifest)."""
    try:
        data = json.loads(text)
    except ValueError as exc:
        return [f"not valid JSON: {exc}"], set()
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("entries"), list):
        return ["must be {schema_version: 1, entries: [...]}"], set()
    problems, shas = [], set()
    for i, e in enumerate(data["entries"]):
        problems += [f"entry {i}: {p}" for p in entry_problems(e)]
        if isinstance(e, dict) and isinstance(e.get("sha256"), str):
            shas.add(e["sha256"])
    return problems, shas


def tracked_files(root: Path) -> list:
    out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], check=True, capture_output=True).stdout
    return [p for p in out.decode("utf-8", "surrogateescape").split("\0") if p]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check(root: Path, tracked=None) -> list:
    root = Path(root)
    tracked = tracked_files(root) if tracked is None else tracked
    failures, stored = [], {}
    for rel in sorted(root.glob(MANIFEST_GLOB)):
        name = rel.relative_to(root).as_posix()
        problems, shas = manifest_problems(rel.read_text(encoding="utf-8"))
        failures += [f"{name}: {p}" for p in problems]
        for s in shas:
            stored.setdefault(s, name)
    for rel in tracked:
        p = root / rel
        if rel.startswith("manifests/") and p.is_file():
            if FORBIDDEN.search(p.read_text(encoding="utf-8", errors="replace")):
                failures.append(f"{rel}: names a storage bucket / cloud account (s3:// or arn:aws:)")
        if stored and p.is_file() and not p.is_symlink() and p.stat().st_size > 0:
            s = sha256_of(p)
            if s in stored and not rel.startswith("manifests/"):
                failures.append(f"{rel}: bytes are stored (sha256 {s[:12]}.. in {stored[s]}) but also committed")
    return failures


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".")
    args = ap.parse_args(argv)
    failures = check(Path(args.root))
    if failures:
        print("artifact manifest check FAILED:", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        return 1
    print("artifact manifest check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
