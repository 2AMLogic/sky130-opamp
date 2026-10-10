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

Offset Monte Carlo campaigns (issue #113) use the same snapshot discipline under
sim/offset-capability/records: ``validate`` also checks every offset chunk
summary and campaign report that carries ``dut`` (snapshot intact, request
netlist is the rendered bench in the snapshot, all chunks share one hash);
older records are UNVERIFIED. ``current-offset`` is the separate, explicit
"does a historical offset campaign equal today's netlist" diagnostic.

PSRR/noise campaigns (``*-psrr-noise.json``) and their validation runs
(``*-psrr-noise-validation.json``) use the same discipline (issue #151): the
``dut`` block names a snapshot dir that also holds every rendered bench body
and replayable request; ``validate`` checks the snapshot, that every submitted
request points at a rendered body inside it, and that no body includes the live
DUT. Older records without ``dut`` are UNVERIFIED.

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
OFFSET_RECORDS_REL = "sim/offset-capability/records"
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
        if p.name.endswith((".characterization.json", ".klt.json", ".request.json", "-psrr-noise.json")):
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


def common_dut(named_records: list[tuple[str, dict]], repo_root: Path = REPO_ROOT):
    """Check that records (e.g. the chunks of one offset campaign) share one DUT.

    Returns (state, sha256, problems). state is VERIFIED when every record
    declares an intact snapshot with the same hash, UNVERIFIED when none
    declares ``dut`` (legacy; no problems). Mixed hashes, a mix of declared and
    legacy records, and missing/corrupt snapshots are problems naming the
    offending record. Says nothing about equality to today's design.
    """
    problems: list[str] = []
    hashes: dict[str, list[str]] = {}
    legacy = []
    for name, rec in named_records:
        state, probs = verify_record_dut(rec, repo_root)
        if state == UNVERIFIED:
            legacy.append(name)
            continue
        problems += [f"{name}: {p}" for p in probs]
        sha = (rec.get("dut") or {}).get("sha256")
        if sha:
            hashes.setdefault(sha, []).append(name)
    if legacy and hashes:
        problems.append(f"mixed provenance: {', '.join(legacy)} have no dut block but "
                        f"{', '.join(n for v in hashes.values() for n in v)} do")
    if len(hashes) > 1:
        problems.append("mixed DUT hashes: " + "; ".join(f"{h} <- {', '.join(n)}" for h, n in sorted(hashes.items())))
    if problems:
        return (VERIFIED if hashes else UNVERIFIED), None, problems
    if hashes:
        return VERIFIED, next(iter(hashes)), problems
    return UNVERIFIED, None, problems


def _load(path: Path):
    try:
        d = json.loads(path.read_text())
    except (ValueError, OSError):
        return None
    return d if isinstance(d, dict) else None


def offset_records(repo_root: Path = REPO_ROOT) -> list[tuple[Path, str]]:
    """(path, kind) for offset-runner chunk summaries ('summary') and campaign
    reports ('campaign'). Pair-diagnostic summaries are out of scope."""
    rdir = repo_root / OFFSET_RECORDS_REL
    out = []
    for p in sorted(rdir.glob("*.summary.json")):
        d = _load(p)
        if d is None:
            continue
        bench = d.get("bench")
        if bench is None:
            req = _load(p.with_name(p.name[: -len(".summary.json")] + ".request.json")) or {}
            bench = "offset" if "offset_dc" in str(req.get("netlist", "")) else None
        if bench == "offset":
            out.append((p, "summary"))
    out += [(p, "campaign") for p in sorted(rdir.glob("*.campaign.json"))]
    return out


def offset_problems(path: Path, kind: str, repo_root: Path = REPO_ROOT) -> tuple[str, list[str]]:
    rec = json.loads(path.read_text())
    state, problems = verify_record_dut(rec, repo_root)
    if state == UNVERIFIED:
        return state, []
    if kind == "summary":
        req = _load(path.with_name(path.name[: -len(".summary.json")] + ".request.json")) or {}
        sp = rec["dut"].get("snapshot_path")
        snap = (repo_root / sp).parent.resolve() if sp else None
        net = (path.parent / str(req.get("netlist", ""))).resolve()
        if snap is None or net.parent != snap:
            problems.append(f"submitted request netlist {req.get('netlist')!r} is not the rendered bench in the DUT snapshot")
    else:
        named = []
        for cname, c in sorted((rec.get("corners") or {}).items()):
            for ch in c.get("chunks") or []:
                sp = path.parent / f"{ch['record_id']}.summary.json"
                s = _load(sp)
                if s is None:
                    problems.append(f"{cname} chunk {ch.get('chunk')}: summary {sp.name} missing or unreadable")
                else:
                    named.append((sp.name, s))
        _, sha, probs = common_dut(named, repo_root)
        problems += probs
        if sha and rec["dut"].get("sha256") and sha != rec["dut"]["sha256"]:
            problems.append(f"chunks use {sha} but the campaign declares {rec['dut']['sha256']}")
    return state, problems


def validate_offset(repo_root: Path = REPO_ROOT, require_verified: bool = False) -> int:
    rc = 0
    for p, kind in offset_records(repo_root):
        state, problems = offset_problems(p, kind, repo_root)
        if state == UNVERIFIED:
            print(f"{p.name}: UNVERIFIED legacy offset record (no recorded DUT identity)")
            rc = 1 if require_verified else rc
        elif problems:
            rc = 1
            for pr in problems:
                print(f"{p.name}: FAIL {pr}")
        else:
            print(f"{p.name}: OK offset DUT snapshot verified")
    return rc


def check_current_offset(repo_root: Path = REPO_ROOT) -> int:
    """Explicit current-design check for every verified offset record."""
    rc = 0
    for p, kind in offset_records(repo_root):
        for pr in check_current(json.loads(p.read_text()), repo_root):
            print(f"{p.name}: STALE {pr}")
            rc = 1
    return rc


def psrr_noise_records(repo_root: Path = REPO_ROOT) -> list[Path]:
    """PSRR/noise campaign metadata and validation-run records (issue #151)."""
    rdir = repo_root / RECORDS_REL
    return sorted(p for p in rdir.glob("*.json")
                  if p.name.endswith(("-psrr-noise.json", "-psrr-noise-validation.json")))


def _in_snapshot(rec: dict, netlist: str, base: Path, repo_root: Path) -> str | None:
    """Problem string unless ``netlist`` (relative to ``base``) is an existing
    rendered body in the DUT snapshot directory."""
    snap = (repo_root / rec["dut"]["snapshot_path"]).parent.resolve()
    body = (base / netlist).resolve()
    if body.parent != snap:
        return f"request netlist {netlist!r} is not a rendered bench in the DUT snapshot"
    if not body.is_file():
        return f"rendered bench body {body.name} missing from the DUT snapshot"
    return None


def psrr_noise_problems(path: Path, repo_root: Path = REPO_ROOT) -> tuple[str, list[str]]:
    rec = json.loads(path.read_text())
    state, problems = verify_record_dut(rec, repo_root)
    if state == UNVERIFIED or not (rec["dut"].get("snapshot_path") and rec["dut"].get("sha256")):
        return state, problems
    snap = (repo_root / rec["dut"]["snapshot_path"]).parent
    if "runs" in rec:   # validation record: embedded requests, one rendered body each
        for name, run in sorted((rec.get("runs") or {}).items()):
            net = ((run or {}).get("request") or {}).get("netlist")
            if not net:
                problems.append(f"run {name}: no request netlist recorded")
                continue
            pr = _in_snapshot(rec, net, path.parent, repo_root)
            if pr:
                problems.append(f"run {name}: {pr}")
            if not (snap / f"{name}.request.json").is_file():
                problems.append(f"run {name}: replayable request {name}.request.json missing from the DUT snapshot")
    else:               # campaign: committed request + retained snapshot request + body per bench
        for bname, b in sorted((rec.get("benches") or {}).items()):
            body, snapreq = b.get("rendered_body"), b.get("request_snapshot")
            if not body or not snapreq:
                problems.append(f"bench {bname}: record lacks rendered_body/request_snapshot")
                continue
            for what, rel in (("rendered_body", body), ("request_snapshot", snapreq)):
                f = repo_root / rel
                if f.parent.resolve() != snap.resolve() or not f.is_file():
                    problems.append(f"bench {bname}: {what} {rel} missing or outside the DUT snapshot")
            stem = path.name[: -len("-psrr-noise.json")]
            req = _load(path.with_name(f"{stem}-{Path(snapreq).name}"))
            if req is None:
                problems.append(f"bench {bname}: committed request {stem}-{Path(snapreq).name} missing or unreadable")
            else:
                pr = _in_snapshot(rec, str(req.get("netlist", "")), path.parent, repo_root)
                if pr:
                    problems.append(f"bench {bname}: {pr}")
                elif (path.parent / req["netlist"]).resolve() != (repo_root / body).resolve():
                    problems.append(f"bench {bname}: committed request points at a different body than the record")
    return state, problems


def validate_psrr_noise(repo_root: Path = REPO_ROOT, require_verified: bool = False) -> int:
    rc = 0
    for p in psrr_noise_records(repo_root):
        state, problems = psrr_noise_problems(p, repo_root)
        if state == UNVERIFIED:
            print(f"{p.name}: UNVERIFIED legacy PSRR/noise record (no recorded DUT identity)")
            rc = 1 if require_verified else rc
        elif problems:
            rc = 1
            for pr in problems:
                print(f"{p.name}: FAIL {pr}")
        else:
            print(f"{p.name}: OK PSRR/noise DUT snapshot, bodies and requests verified")
    return rc


def validate_all(repo_root: Path = REPO_ROOT, require_verified: bool = False) -> int:
    rc = validate_offset(repo_root, require_verified)
    rc |= validate_psrr_noise(repo_root, require_verified)
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
    for name in ("validate", "current", "current-offset"):
        p = sub.add_parser(name)
        p.add_argument("--require-verified", action="store_true", help="treat legacy/unverified records as failures")
        p.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    sub.choices["current-offset"].add_argument("--manifest", default=MANIFEST_REL)  # unused; uniform CLI
    sub.choices["current"].add_argument("--manifest", default=MANIFEST_REL)
    sub.choices["current"].add_argument("--item", default="8")
    a = ap.parse_args(argv)
    if a.cmd == "validate":
        return validate_all(a.repo_root, a.require_verified)
    if a.cmd == "current-offset":
        return check_current_offset(a.repo_root)
    return validate_current(a.repo_root, a.repo_root / a.manifest, a.item, a.require_verified)


if __name__ == "__main__":
    sys.exit(main())
