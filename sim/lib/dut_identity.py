#!/usr/bin/env python3
"""DUT-netlist identity for PVT campaigns (issue #104). Stdlib only, simulator-free.

A campaign captures the exact DUT bytes once (``capture_dut``), runs every
analysis against that copy, and records its repo-relative path and SHA-256 in
the record JSON under ``"dut"``. This module also validates that metadata:

    python3 sim/lib/dut_identity.py validate [--require-verified]
    python3 sim/lib/dut_identity.py current  [--manifest M] [--item N] [--require-verified]

``validate`` checks every committed PVT record that carries ``dut`` metadata
(snapshot present, hash matches, saved decks include only the snapshot). That
is *historical* evidence: it stays valid after the design moves on. Records
without ``dut`` are legacy and reported UNVERIFIED -- never inferred from the
Git SHA or from today's netlist.

``current`` takes the characterization the block manifest cites for a T1 item
(default 8) and additionally requires its recorded DUT hash to equal the hash
of the *current* ``design/netlist/opamp_core.spice``; a mismatch is reported
as a stale-design diagnostic. Integrity of the report itself stays with the
re-hash step in .github/workflows/signoff.yml. Neither check says anything
about spec/T1 compliance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CURRENT_NETLIST_REL = "design/netlist/opamp_core.spice"
SNAPSHOT_NAME = "opamp_core.spice"
RECORDS_REL = "sim/opamp-characterization/records"
MANIFEST_REL = "manifests/sky130-opamp.json"

VERIFIED = "verified"
UNVERIFIED = "unverified"

_INCLUDE_RE = re.compile(r'^\s*\.(?:include|inc)\s+"?([^"\s]+)"?', re.IGNORECASE | re.MULTILINE)


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def capture_dut(src: Path, snapshot_dir: Path, repo_root: Path = REPO_ROOT) -> dict:
    """Copy the DUT bytes once into ``snapshot_dir`` and return the metadata block.

    The hash is taken from the bytes that were written, so it describes the
    snapshot, not whatever ``src`` holds a moment later.
    """
    data = Path(src).read_bytes()
    dest = Path(snapshot_dir) / SNAPSHOT_NAME
    with open(dest, "xb") as f:
        f.write(data)
    try:
        src_rel = Path(src).resolve().relative_to(repo_root).as_posix()
    except ValueError:
        src_rel = str(src)
    return {
        "source_path": src_rel,
        "snapshot_path": dest.resolve().relative_to(repo_root).as_posix(),
        "sha256": sha256_bytes(data),
    }


def verify_record_dut(record: dict, repo_root: Path = REPO_ROOT) -> tuple[str, list[str]]:
    """Return (state, problems). state is VERIFIED or UNVERIFIED (legacy, no
    ``dut`` block); problems are integrity failures of a declared block."""
    dut = record.get("dut")
    if dut is None:
        return UNVERIFIED, []
    problems: list[str] = []
    snap_rel, declared = dut.get("snapshot_path"), dut.get("sha256")
    if not snap_rel or not declared:
        return VERIFIED, ["dut block must declare snapshot_path and sha256"]
    snap = repo_root / snap_rel
    if not snap.is_file():
        return VERIFIED, [f"DUT snapshot missing: {snap_rel}"]
    actual = sha256_file(snap)
    if actual != declared:
        problems.append(f"DUT snapshot corrupted: {snap_rel} hashes to {actual}, record declares {declared}")
    # Saved decks/bodies must replay against the snapshot, not the live netlist.
    for deck in sorted(snap.parent.glob("*.spice")):
        if deck == snap:
            continue
        for target in _INCLUDE_RE.findall(deck.read_text(errors="replace")):
            if "opamp_core" not in target:
                continue
            if target != SNAPSHOT_NAME and not target.endswith(snap_rel):
                problems.append(f"{deck.name} includes {target!r}, not the DUT snapshot")
    return VERIFIED, problems


def check_current(record: dict, repo_root: Path = REPO_ROOT,
                  netlist_rel: str = CURRENT_NETLIST_REL) -> list[str]:
    """Stale-design diagnostics: recorded DUT hash vs the current netlist."""
    dut = record.get("dut")
    if not dut or not dut.get("sha256"):
        return []
    live = repo_root / netlist_rel
    if not live.is_file():
        return [f"current netlist missing: {netlist_rel}"]
    now = sha256_file(live)
    if now != dut["sha256"]:
        return [f"DUT mismatch (stale design): the record measured {dut['sha256']} but the current "
                f"{netlist_rel} is {now}; rerun the campaign or cite a record for the current design"]
    return []


def pvt_record_paths(repo_root: Path = REPO_ROOT) -> list[Path]:
    out = []
    for p in sorted((repo_root / RECORDS_REL).glob("*.json")):
        if p.name.endswith((".characterization.json", ".klt.json", ".request.json")):
            continue
        try:
            d = json.loads(p.read_text())
        except ValueError:
            continue
        if isinstance(d, dict) and "matrix" in d and "record_id" in d:
            out.append(p)
    return out


def cited_record(manifest: dict, item: str, repo_root: Path = REPO_ROOT) -> Path:
    """The PVT record JSON behind the characterization envelope cited for ``item``."""
    cite = (manifest.get("evidence") or {}).get(str(item))
    if not cite:
        raise ValueError(f"manifest cites no evidence for item {item}")
    name = Path(cite["file"]).name
    if not name.endswith(".characterization.json"):
        raise ValueError(f"item {item} cites {cite['file']}, not a *.characterization.json report")
    return repo_root / Path(cite["file"]).parent / (name[: -len(".characterization.json")] + ".json")


def validate_all(repo_root: Path = REPO_ROOT, require_verified: bool = False) -> int:
    rc = 0
    for p in pvt_record_paths(repo_root):
        state, problems = verify_record_dut(json.loads(p.read_text()), repo_root)
        if state == UNVERIFIED:
            print(f"{p.name}: UNVERIFIED legacy record (no recorded DUT identity)")
            if require_verified:
                rc = 1
        elif problems:
            rc = 1
            for pr in problems:
                print(f"{p.name}: FAIL {pr}")
        else:
            print(f"{p.name}: OK DUT snapshot verified")
    return rc


def validate_current(repo_root: Path, manifest_path: Path, item: str, require_verified: bool = False) -> int:
    manifest = json.loads(manifest_path.read_text())
    rec_path = cited_record(manifest, item, repo_root)
    if not rec_path.is_file():
        print(f"FAIL item {item}: cited record {rec_path.name} not found")
        return 1
    record = json.loads(rec_path.read_text())
    state, problems = verify_record_dut(record, repo_root)
    if state == UNVERIFIED:
        print(f"item {item}: {rec_path.name} is UNVERIFIED -- no recorded DUT identity, so it is NOT "
              "mechanically bound to the current design. Rerun the campaign with the DUT-snapshotting "
              "runner and cite the new record to obtain a verified current-design claim.")
        return 1 if require_verified else 0
    problems += check_current(record, repo_root)
    for pr in problems:
        print(f"item {item}: FAIL {pr}")
    if not problems:
        print(f"item {item}: OK {rec_path.name} DUT snapshot verified and equals the current netlist")
    return 1 if problems else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("validate", "current"):
        p = sub.add_parser(name)
        p.add_argument("--require-verified", action="store_true", help="treat legacy/unverified records as failures")
        p.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    sub.choices["current"].add_argument("--manifest", default=MANIFEST_REL)
    sub.choices["current"].add_argument("--item", default="8")
    a = ap.parse_args(argv)
    if a.cmd == "validate":
        return validate_all(a.repo_root, a.require_verified)
    return validate_current(a.repo_root, a.repo_root / a.manifest, a.item, a.require_verified)


if __name__ == "__main__":
    sys.exit(main())
