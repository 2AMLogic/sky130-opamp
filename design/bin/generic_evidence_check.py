#!/usr/bin/env python3
"""Independent freshness gate for generic evidence envelopes (stdlib only).

`klt signoff` grades a generic ("kind": "generic") envelope against the hash
the envelope declares about itself and never re-hashes the artifact that hash
names (klayout-tools#2196, #2403). This checker does that re-hash: for every
manifest evidence entry that cites a generic envelope, resolve the envelope's
provenance.input.path, hash the file and compare with
provenance.input.content_hash.

Malformed input fails rather than passing vacuously: the manifest root must be
an object, 'evidence' must be present and an object ({} passes with 0 checked),
and every entry must be a non-empty path string, {"file": non-empty str[,
"content_hash": str]} or {"command": non-empty list of str} (skipped).

Resolution order (matches klt): relative to the envelope's own directory
first, then repo-relative. Envelopes and artifacts are canonicalised
(realpath) and must stay inside the checkout: external absolute paths, '..'
escapes and symlink escapes are item errors (an escaping envelope-relative
candidate is never silently replaced by the repo-relative one); contained
symlinks and internal '..' segments are accepted. Skipped: {"command": [...]} entries (no file) and
envelopes whose kind is not "generic" (klt computed those hashes itself).

Used by .github/workflows/signoff.yml and design/bin/check_ci.py; the klt
render-and-byte-compare step is separate. Exit 0 = all verified, 1 = any
failure (all item-specific failures are aggregated and reported).

    python3 design/bin/generic_evidence_check.py [--manifest PATH] [--root DIR]
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
DEFAULT_MANIFEST = "manifests/sky130-opamp.json"

REMEDIATION = (
    "Re-hash the artifact, write the new value into BOTH the envelope's "
    "provenance.input.content_hash and the manifest's pinned content_hash, "
    "then regenerate manifests/sky130-opamp.signoff.json in the same PR "
    "(see manifests/README.md)."
)


def _sort_key(kv):
    k = str(kv[0])
    return (0, int(k), k) if k.isdigit() else (1, 0, k)


def sha256_of(path):
    with open(path, "rb") as handle:
        return "sha256:" + hashlib.sha256(handle.read()).hexdigest()


class EvidencePathError(Exception):
    """A cited path is not a usable, checkout-contained evidence file."""


def _contained(root_real, path):
    """True if canonical `path` is root_real or lies beneath it."""
    try:
        return os.path.commonpath([root_real, path]) == root_real
    except ValueError:
        return False


def _canonical(root_real, candidate, what):
    """Return realpath of `candidate`, raising EvidencePathError if it leaves root."""
    try:
        real = os.path.realpath(candidate)
    except (OSError, ValueError, RuntimeError) as exc:
        raise EvidencePathError(f"cannot resolve {what} {candidate!r}: {exc}")
    if not _contained(root_real, real):
        raise EvidencePathError(
            f"{what} {candidate!r} resolves to {real}, outside the repository "
            f"checkout {root_real}; evidence must be committed inside the repo")
    return real


def resolve_envelope(root, envelope_rel):
    """Canonical envelope path, which must stay inside the checkout."""
    root_real = os.path.realpath(root)
    return _canonical(root_real, os.path.join(root, envelope_rel), "evidence envelope")


def resolve_artifact(root, envelope_rel, artifact):
    """Envelope directory first, then repo-relative; None if neither is a file.

    Every candidate is canonicalised (symlinks followed) and must stay inside
    the checkout. A candidate that escapes raises EvidencePathError (never a
    silent fall back to the other lookup branch). Contained symlinks and
    internal '..' segments are fine.
    """
    root_real = os.path.realpath(root)
    envelope_dir = os.path.dirname(envelope_rel)
    for base in (os.path.join(root, envelope_dir), root):
        candidate = os.path.join(base, artifact)
        real = _canonical(root_real, candidate, "provenance.input.path")
        if os.path.isfile(real):
            return real
        if os.path.islink(os.path.normpath(candidate)) and not os.path.exists(real):
            raise EvidencePathError(
                f"provenance.input.path {artifact!r} is a dangling symlink "
                f"({os.path.normpath(candidate)} -> {real})")
    return None


def _type_name(value):
    return "null" if value is None else type(value).__name__


def _classify_entry(entry):
    """Return ("file", path), ("skip", None) or ("error", message)."""
    if isinstance(entry, str):
        if entry:
            return "file", entry
        return "error", "empty file path"
    if isinstance(entry, dict):
        has_file, has_cmd = "file" in entry, "command" in entry
        if has_file and has_cmd:
            return "error", "ambiguous evidence entry (both 'file' and 'command')"
        if has_file:
            path = entry["file"]
            if not isinstance(path, str) or not path:
                return "error", ("'file' must be a non-empty string, "
                                 f"got {_type_name(path)}")
            if "content_hash" in entry and not isinstance(entry["content_hash"], str):
                return "error", ("'content_hash' must be a string, "
                                 f"got {_type_name(entry['content_hash'])}")
            return "file", path
        if has_cmd:
            cmd = entry["command"]
            if (isinstance(cmd, list) and cmd
                    and all(isinstance(c, str) for c in cmd)):
                return "skip", None
            return "error", "'command' must be a non-empty list of strings"
    return "error", (
        f"unrecognized evidence entry of type {_type_name(entry)} (expected "
        'path string, {"file": ...} or {"command": [...]})')


def check_manifest(manifest, root=REPO):
    """Return (checked_count, ok_lines, failures)."""
    root = Path(root)
    mpath = root / manifest
    try:
        with open(mpath) as handle:
            data = json.load(handle)
    except Exception as exc:
        return 0, [], [f"cannot read manifest {manifest}: {exc}"]
    if not isinstance(data, dict):
        return 0, [], [f"manifest {manifest}: root must be a JSON object, "
                       f"got {_type_name(data)}"]
    if "evidence" not in data:
        return 0, [], [f"manifest {manifest}: missing required 'evidence' object"]
    evidence = data["evidence"]
    if not isinstance(evidence, dict):
        return 0, [], [f"manifest {manifest}: 'evidence' must be an object, "
                       f"got {_type_name(evidence)}"]

    checked, oks, failures = 0, [], []
    for item, entry in sorted(evidence.items(), key=_sort_key):
        kind, value = _classify_entry(entry)
        if kind == "skip":
            continue
        if kind == "error":
            failures.append(f"item {item}: {value}")
            continue
        path = value
        try:
            env_real = resolve_envelope(root, path)
            with open(env_real) as handle:
                envelope = json.load(handle)
        except EvidencePathError as exc:
            failures.append(f"item {item}: {path}: {exc}")
            continue
        except Exception as exc:
            failures.append(f"item {item}: cannot read evidence envelope {path}: {exc}")
            continue
        if not isinstance(envelope, dict):
            failures.append(f"item {item}: evidence envelope {path} is not a JSON object")
            continue
        if envelope.get("kind") != "generic":
            continue

        prov = envelope.get("provenance")
        prov = prov.get("input") if isinstance(prov, dict) else None
        prov = prov if isinstance(prov, dict) else {}
        artifact = prov.get("path")
        declared = prov.get("content_hash")
        if not artifact or not declared or not isinstance(artifact, str):
            failures.append(
                f"item {item}: generic envelope {path} must declare both "
                "provenance.input.path and provenance.input.content_hash, so the "
                "artifact it cites can be re-hashed here")
            continue

        try:
            resolved = resolve_artifact(root, path, artifact)
        except EvidencePathError as exc:
            failures.append(f"item {item}: {path}: {exc}")
            continue
        if resolved is None:
            failures.append(
                f"item {item}: {path} names provenance.input.path {artifact!r}, "
                "which resolves to no file")
            continue
        shown = os.path.relpath(resolved, os.path.realpath(root))
        try:
            actual = sha256_of(resolved)
        except OSError as exc:
            failures.append(f"item {item}: cannot read cited artifact {shown}: {exc}")
            continue
        checked += 1
        if actual == declared:
            oks.append(f"item {item}: OK {shown} -> {declared}")
        else:
            failures.append(
                f"item {item}: {shown} hashes to {actual}, but {path} declares "
                f"{declared} -- the cited artifact changed under its envelope")
    return checked, oks, failures


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST,
                    help="block manifest, relative to --root (default: %(default)s)")
    ap.add_argument("--root", default=str(REPO), help="repository root (default: this repo)")
    args = ap.parse_args(argv)

    checked, oks, failures = check_manifest(args.manifest, args.root)
    for line in oks:
        print(line)
    if failures:
        prefix = "::error::" if os.environ.get("GITHUB_ACTIONS") else "ERROR: "
        for failure in failures:
            print(prefix + failure, file=sys.stderr)
        print(REMEDIATION, file=sys.stderr)
        return 1
    print(f"Generic evidence envelopes verified against their cited artifacts: {checked}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
