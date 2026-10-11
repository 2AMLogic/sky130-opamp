#!/usr/bin/env python3
"""Compose one layout cell from klt primitive generators and verify it.

Ported from 2AMLogic/sky130-trng ``layout/bin/compose-cell.py`` at commit
``5d443907c99bf4eb193092f0cf89f2a6e2a5c80e`` -- the same ``cell.json``-driven
recipe the sibling sky130 blocks use:

    klt gen / klt draw (per block)
      -> klt gen-compose (place + route)
      -> klt drc          (rule sign-off, --deck sky130)
      -> klt extract      (layout-derived netlist)
      -> klt lvs          (extracted vs. a reference derived from design/)

Every step's request/response is written next to the descriptor, so the
committed ``layout/<cell>/`` is the full re-checkable evidence trail.

What was kept, dropped and added relative to the sibling
---------------------------------------------------------

Kept: the single-stage chain, ``run_klt``/``write_json`` (``_klt_common.py``),
relative-path invocation from the output directory, the unrouted-net hard
failure, and ``--check``'s rebuild-into-a-temp-dir shape.

Dropped (not needed by any cell here yet): multi-stage composition,
``blocks[].cell`` sibling-cell placement, dependency/variant reference
rewriting, and the bare-literal ``u`` unit rewrite (klayout-tools#1492 is
fixed in the pinned klt for ``reference.deck: "sky130"``).

Added:

* ``blocks[].draw`` -- a promotion stub drawn by ``klt draw`` from shapes in
  the cell.json (the sibling sky130-temp-por commits hand-drawn
  ``promo_stub.gds`` files; here the stub is regenerated every run so it is
  covered by ``--check`` like every other stream).
* The LVS reference is a *selection* of device cards from the design
  netlist (``layout/bin/stage_reference.py``), not a whole subckt -- the
  design netlist exports one flat ``opamp_core`` and a layout sub-block
  covers only part of it.
* Self-checks after the chain: DRC clean with zero violations, the
  extracted devices grouped by terminal nets reproduce each reference card's
  ``L`` exactly and ``W`` exactly as a sum of the drawn unit widths, every
  declared pin is a composed-cell port and an extracted net name, and LVS
  ``status: "match"``. Any failure is a non-zero exit.
* ``--check`` compares **GDS bytes** (SHA-256 of the cell's own stream and
  every ``gen/*.gds``), the generated reference text, and the
  verdict-bearing JSON fields. The sibling's ``--check`` compared JSON
  fields only.
* GDS volatile metadata: a GDSII stream carries modification/access
  timestamps in its ``BGNLIB``/``BGNSTR`` records. Every stream this script
  produces is passed through :func:`normalize_gds_timestamps`, which zeroes
  those twelve-short date fields in place (and reports whether anything was
  non-zero), so a byte comparison is meaningful regardless of the writer.
* ``--negative-control DEVICE:TERMINAL=NET`` rebuilds into a temp dir,
  rewires one terminal of one reference card to another net, re-runs LVS
  and requires a mismatch. Its evidence goes to ``<cell>/negative-control/``
  only; the passing reference and reports are not touched.
* A toolchain pin check against ``layout/pdk.json`` (klt git commit and the
  resolved open_pdks commit); a mismatch is fatal unless
  ``--allow-unpinned`` is given.

Usage
-----

    python3 layout/bin/compose-cell.py layout/opamp_stage1/cell.json
    python3 layout/bin/compose-cell.py layout/opamp_stage1/cell.json --check
    python3 layout/bin/compose-cell.py layout/opamp_stage1/cell.json \\
        --negative-control XM1:g=inp
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import struct
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _klt_common import BuildError, run_klt, write_json  # noqa: E402
from stage_reference import (  # noqa: E402
    PASSIVE_MODELS,
    ReferenceError,
    card_kind,
    card_terminals,
    passive_geometry,
    terminal_names,
    write_reference,
)

REPO_ROOT = HERE.parents[1]
PDK_PIN = REPO_ROOT / "layout" / "pdk.json"

#: Verdict-bearing fields --check compares, per artifact (sibling's set).
CHECK_FIELDS: dict[str, tuple[str, ...]] = {
    "drc.json": ("status", "violation_count"),
    "extract.json": ("status", "device_count", "net_count", "device_counts"),
    "lvs.json": ("status", "mismatch_count", "error_count", "counts"),
    "compose.response.json": ("cell_name", "bbox_um"),
}

#: GDSII record types whose payload is two 6-short timestamps.
_GDS_BGNLIB = 0x0102
_GDS_BGNSTR = 0x0502


# --------------------------------------------------------------------------
# GDS byte hygiene
# --------------------------------------------------------------------------


def normalize_gds_timestamps(path: Path) -> bool:
    """Zero the BGNLIB/BGNSTR timestamps of a GDSII stream in place.

    Returns True when any timestamp was non-zero (i.e. the file changed).
    """
    data = bytearray(path.read_bytes())
    changed = False
    offset = 0
    while offset + 4 <= len(data):
        length, rectype = struct.unpack_from(">HH", data, offset)
        if length < 4:
            raise BuildError(f"{path}: malformed GDS record at byte {offset}")
        if rectype in (_GDS_BGNLIB, _GDS_BGNSTR):
            payload = slice(offset + 4, offset + length)
            if any(data[payload]):
                data[payload] = bytes(length - 4)
                changed = True
        if rectype == 0x0400:  # ENDLIB
            break
        offset += length
    if changed:
        path.write_bytes(bytes(data))
    return changed


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------
# Toolchain pin
# --------------------------------------------------------------------------


def check_toolchain(env: dict[str, str], variant: str, allow_unpinned: bool) -> dict:
    pin = json.loads(PDK_PIN.read_text())
    version = run_klt(["version"], env=env)
    pdk = run_klt(["pdk", "find", "--pdk", variant], env=env)
    problems = []
    if version.get("git_commit") != pin["klt_commit"]:
        problems.append(
            f"klt git_commit {version.get('git_commit')} != pinned {pin['klt_commit']}"
        )
    if pin["open_pdks_commit"] not in str(pdk.get("version")):
        problems.append(
            f"PDK version {pdk.get('version')!r} != pinned {pin['open_pdks_commit']}"
        )
    if problems:
        message = "toolchain does not match layout/pdk.json: " + "; ".join(problems)
        if not allow_unpinned:
            raise BuildError(message + " (see layout/README.md, 'Toolchain')")
        print(f"warning: {message}", file=sys.stderr)
    return {"klt": version.get("version"), "pdk": pdk.get("version")}


# --------------------------------------------------------------------------
# The chain
# --------------------------------------------------------------------------


def _orientation(block: dict) -> dict:
    orient = block.get("orientation", "none")
    return {"orientation": orient} if orient != "none" else {}


def build_blocks(spec: dict, *, variant: str, env: dict, out_dir: Path) -> list[dict]:
    gen_dir = out_dir / "gen"
    gen_dir.mkdir(parents=True, exist_ok=True)
    blocks_request = []
    for block in spec["blocks"]:
        bid = block["id"]
        if "draw" in block:
            draw = block["draw"]
            write_json(gen_dir / f"{bid}.draw.request.json", {"shapes": draw["shapes"]})
            response = run_klt(
                [
                    "draw",
                    "--params",
                    f"gen/{bid}.draw.request.json",
                    "--cell-name",
                    draw["cell_name"],
                    "-o",
                    f"gen/{bid}.gds",
                ],
                env=env,
                cwd=out_dir,
            )
            normalize_gds_timestamps(gen_dir / f"{bid}.gds")
            write_json(gen_dir / f"{bid}.draw.json", response)
            blocks_request.append(
                {
                    "id": bid,
                    "cell": {
                        "gds_path": f"gen/{bid}.gds",
                        "cell_name": draw["cell_name"],
                        "ports": draw["ports"],
                    },
                    **_orientation(block),
                }
            )
            continue
        response = run_klt(
            [
                "gen",
                block["generator"],
                "--params",
                json.dumps(block["params"]),
                "--pdk",
                variant,
                "--cell-name",
                block["cell_name"],
                "-o",
                f"gen/{bid}.gds",
            ],
            env=env,
            cwd=out_dir,
        )
        normalize_gds_timestamps(gen_dir / f"{bid}.gds")
        write_json(gen_dir / f"{bid}.gen.json", response)
        report = f"gen/{bid}.gen.json"
        grid = block.get("snap_ports_to_grid_um")
        if grid:
            write_json(gen_dir / f"{bid}.snapped.gen.json", snap_ports(response, grid))
            report = f"gen/{bid}.snapped.gen.json"
        blocks_request.append(
            {"id": bid, "generator_report": report, **_orientation(block)}
        )
    return blocks_request


def _snap(value: float, grid: float) -> float:
    """Nearest multiple of *grid*; an exact half-grid tie rounds down."""
    steps = math.floor(value / grid + 0.5 - 1e-9)
    return round(steps * grid, 6)


def snap_ports(report: dict, grid: float) -> dict:
    """A copy of a ``klt gen`` report with every port centre on *grid*.

    Workaround for a klt gap (see layout/README.md, "klt gaps"): ``klt
    gen-compose`` centres each via-drop stack and route backbone on the
    port position the generator reports, and a generator reports the
    *midpoint* of a terminal pad -- which for an odd-multiple-of-grid pad
    (a 3.015 um S/D strip) sits half a grid step off the 0.005 um
    manufacturing grid, so every via cut, landing pad and backbone drawn
    there fails ``*.ongrid.1``. Moving the attach point by at most half a
    grid step keeps it inside the same pad (pads are >= 0.42 um), so the
    connection is unchanged; the original report is kept alongside, and
    every move is recorded in ``_snapped_ports``.
    """
    snapped = json.loads(json.dumps(report))
    moves = []
    for port in snapped.get("ports", []):
        for axis in ("x_um", "y_um"):
            if port.get(axis) is None:
                continue
            new = _snap(port[axis], grid)
            if abs(new - port[axis]) > 1e-9:
                moves.append(
                    {"port": port["name"], "axis": axis, "from": port[axis], "to": new}
                )
                if abs(new - port[axis]) > grid / 2 + 1e-9:
                    raise BuildError(f"snap of {port['name']} moved more than grid/2")
            port[axis] = new
    snapped["_snapped_ports"] = {"grid_um": grid, "moves": moves}
    return snapped


def run_lvs(
    *,
    extract: dict,
    reference_name: str,
    deck: str,
    lvs_spec: dict,
    env: dict,
    out_dir: Path,
    prefix: str = "",
) -> dict:
    # Passives: the pre-extracted ``layout.netlist`` form reads klt's
    # resistor ``X`` card as an undefined subcircuit (the compare then fails
    # on topology and verifies no body connection), so a cell whose
    # reference holds passives names ``lvs.layout_input: "gds"`` and klt
    # extracts inline with the same deck.
    if lvs_spec.get("layout_input", "netlist") == "gds":
        layout = {"file": f"{lvs_spec['cell_gds']}", "deck": deck}
    else:
        layout = {"netlist": Path(extract["netlist_path"]).name}
    request = {
        "layout": layout,
        "reference": {
            "netlist": reference_name,
            "form": "subckt-call",
            "deck": deck,
            "top": lvs_spec["subckt"],
        },
        **({"options": lvs_spec["options"]} if lvs_spec.get("options") else {}),
    }
    write_json(out_dir / f"{prefix}lvs.request.json", request)
    return run_klt(["lvs", f"{prefix}lvs.request.json"], env=env, cwd=out_dir)


def _net(name: str) -> str:
    return name.lstrip("\\")


def _extracted_key(dev: dict) -> tuple | None:
    """Canonical connectivity key of an extracted device (None = unsupported).

    MOS source/drain, resistor ends and capacitor plates are each
    interchangeable, so those terminal pairs are sorted; the resistor's
    substrate net is part of the key, so a miswired substrate never groups
    with its reference card.
    """
    nets = {k: _net(v) for k, v in dev["nets"].items()}
    cls = dev["class"]
    if cls in ("nfet", "pfet"):
        return (cls, *min((nets["d"], nets["s"]), (nets["s"], nets["d"])), nets["g"], nets["b"])
    for info in PASSIVE_MODELS.values():
        if cls == info["extract_class"]:
            ends = tuple(sorted((nets["a"], nets["b"])))
            return (cls, *ends, nets["w"]) if info["kind"] == "resistor" else (cls, *ends)
    return None


def _reference_key(card: str) -> tuple:
    name, terms, model = card_terminals(card)
    if card_kind(model) == "mos":
        d, g, s, b = terms
        cls = "nfet" if "nfet" in model.lower() else "pfet"
        return (cls, *min((d, s), (s, d)), g, b)
    info = PASSIVE_MODELS[model.lower()]
    ends = tuple(sorted(terms[:2]))
    if info["kind"] == "resistor":
        return (info["extract_class"], *ends, terms[2])
    return (info["extract_class"], *ends)


#: Passive geometry tolerances (um / um^2). The klt extract rounds lengths to
#: 1e-6 um and areas to 1e-4 um^2; anything beyond that is a real difference.
LENGTH_TOL_UM = 1e-6
AREA_REL_TOL = 1e-6
PERIMETER_TOL_UM = 1e-4


def _check_mos(card: str, units: list[dict]) -> list[str]:
    name, _terms, _model = card_terminals(card)
    params = {
        k.lower(): v for k, v in (t.split("=", 1) for t in card.split() if "=" in t)
    }
    want_l = float(params["l"])
    want_w = (
        float(params["w"]) * float(params.get("m", 1)) * float(params.get("mult", 1))
    )
    problems = []
    got_l = {round(u["params"]["l_um"], 6) for u in units}
    got_w = round(sum(u["params"]["w_um"] for u in units), 6)
    if got_l != {round(want_l, 6)}:
        problems.append(f"{name}: extracted L {sorted(got_l)} != netlist L={want_l}")
    if got_w != round(want_w, 6):
        problems.append(
            f"{name}: extracted total W {got_w} ({len(units)} units) != "
            f"netlist W={want_w}"
        )
    return problems


def _check_passive(card: str, units: list[dict]) -> list[str]:
    """Resistor: L and W of every body, count = m*mult. Capacitor: summed
    plate area and perimeter. Resistance/capacitance values are not compared
    (klt LVS excludes them as placeholders, and the extractor's R/C come
    from the extraction deck's own sheet data, not the SPICE model)."""
    name, _terms, _model = card_terminals(card)
    want = passive_geometry(card)
    problems = []
    if want["kind"] == "resistor":
        if len(units) != want["units"]:
            problems.append(
                f"{name}: {len(units)} extracted resistor bodies != "
                f"netlist m*mult={want['units']}"
            )
        for u in units:
            if abs(u["params"]["l_um"] - want["l_um"]) > LENGTH_TOL_UM:
                problems.append(
                    f"{name}: extracted L {u['params']['l_um']} != netlist L={want['l_um']}"
                )
            if abs(u["params"]["w_um"] - want["w_um"]) > LENGTH_TOL_UM:
                problems.append(
                    f"{name}: extracted W {u['params']['w_um']} != netlist W={want['w_um']}"
                )
        return problems
    area = sum(u["params"]["area_um2"] for u in units)
    perimeter = sum(u["params"]["perimeter_um"] for u in units)
    if abs(area - want["area_um2"]) > AREA_REL_TOL * want["area_um2"]:
        problems.append(
            f"{name}: extracted plate area {area} um2 != netlist W*L*MF*m="
            f"{want['area_um2']} um2"
        )
    if abs(perimeter - want["perimeter_um"]) > PERIMETER_TOL_UM:
        problems.append(
            f"{name}: extracted plate perimeter {perimeter} um != netlist "
            f"{want['perimeter_um']} um"
        )
    return problems


def verify_extraction(
    extract: dict, reference_body: list[str], pins: list[str]
) -> list[str]:
    """Extracted devices vs. reference cards; returns a list of problems.

    MOS: L exactly and W as the sum of unit widths. Passives: see
    :func:`_check_passive` (resistor L/W/body count, capacitor plate
    area/perimeter). Every device is grouped by terminal nets first, so a
    miswired net (including the resistor substrate) is a "no extracted
    device on nets" problem before any geometry is compared.
    """
    problems: list[str] = []
    groups: dict[tuple, list[dict]] = {}
    for dev in extract.get("devices", []):
        key = _extracted_key(dev)
        if key is None:
            problems.append(f"extracted device class {dev['class']!r} is unsupported")
            continue
        groups.setdefault(key, []).append(dev)
    for card in reference_body[1:-1]:
        name, _terms, model = card_terminals(card)
        key = _reference_key(card)
        units = groups.pop(key, [])
        if not units:
            problems.append(f"{name}: no extracted {key[0]} on nets {key[1:]}")
            continue
        check = _check_mos if card_kind(model) == "mos" else _check_passive
        problems += check(card, units)
    for key, units in groups.items():
        problems.append(f"extracted device(s) on {key} match no reference card")
    names = {_net(str(n.get("name", ""))) for n in extract.get("nets", [])}
    missing = [p for p in pins if p not in names]
    if missing:
        problems.append(f"pin net(s) {missing} not named in the extracted netlist")
    return problems


def compose_cell(
    spec: dict, spec_dir: Path, out_dir: Path, *, allow_unpinned: bool
) -> dict:
    cell = spec["cell"]
    variant = spec["pdk"]["variant"]
    deck = spec["pdk"]["deck"]
    env = {**os.environ, "PDK": variant}
    toolchain = check_toolchain(env, variant, allow_unpinned)

    blocks_request = build_blocks(spec, variant=variant, env=env, out_dir=out_dir)
    request = {
        "pdk": {"variant": variant},
        "blocks": blocks_request,
        "placement": spec["placement"],
        "routing": spec["routing"],
        "connectivity": spec["connectivity"],
        "pins": spec.get("pins", []),
        "options": {"cell_name": cell, "output": f"{cell}.gds"},
    }
    write_json(out_dir / "compose.request.json", request)
    compose = run_klt(["gen-compose", "compose.request.json"], env=env, cwd=out_dir)
    # klt gen-compose records blocks[].cell sources by absolute path (a klt
    # gap, see layout/README.md); rewrite them relative to the output
    # directory so no home/temp path lands in committed evidence.
    prefix = str(out_dir.resolve()) + os.sep
    for entry in compose.get("blocks", []):
        path = entry.get("source_path")
        if isinstance(path, str) and path.startswith(prefix):
            entry["source_path"] = path[len(prefix) :]
    write_json(out_dir / "compose.response.json", compose)
    unrouted = [n["net"] for n in compose.get("nets", []) if not n.get("routed")]
    if unrouted:
        raise BuildError(f"{cell}: nets left unrouted by gen-compose: {unrouted}")
    normalize_gds_timestamps(out_dir / f"{cell}.gds")

    drc = run_klt(["drc", f"{cell}.gds", "--deck", deck], env=env, cwd=out_dir)
    write_json(out_dir / "drc.json", drc)
    extract = run_klt(["extract", f"{cell}.gds", "--deck", deck], env=env, cwd=out_dir)
    write_json(out_dir / "extract.json", extract)

    lvs_spec = spec["lvs"]
    reference_path = out_dir / f"{cell}.ref.spice"
    try:
        reference_body = write_reference(
            REPO_ROOT / lvs_spec["reference"],
            reference_path,
            source_label=lvs_spec["reference"],
            cell=lvs_spec["subckt"],
            pins=lvs_spec["pins"],
            devices=lvs_spec["devices"],
        )
    except ReferenceError as exc:
        raise BuildError(f"reference: {exc}") from exc
    lvs_spec = {**lvs_spec, "cell_gds": f"{cell}.gds"}
    lvs = run_lvs(
        extract=extract,
        reference_name=reference_path.name,
        deck=deck,
        lvs_spec=lvs_spec,
        env=env,
        out_dir=out_dir,
    )
    write_json(out_dir / "lvs.json", lvs)

    problems: list[str] = []
    if drc.get("status") != "clean" or drc.get("violation_count") != 0:
        problems.append(
            f"DRC {drc.get('status')} ({drc.get('violation_count')} violations)"
        )
    if extract.get("status") != "extracted":
        problems.append(f"extract status {extract.get('status')}")
    expected_units = spec.get("expect", {}).get("extracted_devices")
    if expected_units is not None and extract.get("device_count") != expected_units:
        problems.append(
            f"extracted {extract.get('device_count')} devices, expected {expected_units}"
        )
    problems += verify_extraction(extract, reference_body, lvs_spec["pins"])
    ports = {p["name"] for p in compose.get("ports", [])}
    missing_ports = [p for p in lvs_spec["pins"] if p not in ports]
    if missing_ports:
        problems.append(f"pin(s) {missing_ports} not promoted as composed-cell ports")
    if lvs.get("status") != "match":
        problems.append(f"LVS {lvs.get('status')}")

    counts = lvs.get("counts", {})
    return {
        "cell": cell,
        "toolchain": toolchain,
        "drc": f"{drc.get('status')} ({drc.get('violation_count')} violations)",
        "extract": (
            f"{extract.get('status')}: {extract.get('device_count')} devices, "
            f"{extract.get('net_count')} nets"
        ),
        "lvs": (
            f"{lvs.get('status')}: "
            f"{counts.get('devices', {}).get('matched')}/"
            f"{counts.get('devices', {}).get('reference')} devices, "
            f"{counts.get('nets', {}).get('matched')}/"
            f"{counts.get('nets', {}).get('reference')} nets matched"
        ),
        "problems": problems,
        "reference_body": reference_body,
        "extract_json": extract,
        "env": env,
        "deck": deck,
    }


def produced_streams(out_dir: Path, cell: str) -> list[Path]:
    return [out_dir / f"{cell}.gds", *sorted((out_dir / "gen").glob("*.gds"))]


def check_cell(spec: dict, spec_dir: Path, *, allow_unpinned: bool) -> int:
    """Rebuild into a temp dir; diff GDS bytes, reference and verdicts."""
    cell = spec["cell"]
    with tempfile.TemporaryDirectory(prefix="klt-compose-cell-") as tmp:
        tmp_dir = Path(tmp)
        summary = compose_cell(spec, spec_dir, tmp_dir, allow_unpinned=allow_unpinned)
        drift: list[str] = [f"rebuild self-check: {p}" for p in summary["problems"]]
        rebuilt_streams = {
            p.relative_to(tmp_dir) for p in produced_streams(tmp_dir, cell)
        }
        committed_streams = {
            p.relative_to(spec_dir)
            for p in produced_streams(spec_dir, cell)
            if p.exists()
        }
        for rel in sorted(rebuilt_streams | committed_streams):
            committed, rebuilt = spec_dir / rel, tmp_dir / rel
            if not committed.exists():
                drift.append(f"{rel}: missing from {spec_dir}")
            elif not rebuilt.exists():
                drift.append(f"{rel}: committed but not produced by the rebuild")
            elif sha256(committed) != sha256(rebuilt):
                drift.append(
                    f"{rel}: GDS bytes differ (committed sha256 {sha256(committed)[:16]}, "
                    f"rebuilt {sha256(rebuilt)[:16]})"
                )
        ref = f"{cell}.ref.spice"
        if not (spec_dir / ref).exists():
            drift.append(f"{ref}: missing")
        elif (spec_dir / ref).read_text() != (tmp_dir / ref).read_text():
            drift.append(f"{ref}: generated reference differs")
        for name, fields in CHECK_FIELDS.items():
            committed_path = spec_dir / name
            if not committed_path.exists():
                drift.append(f"{name}: missing from {spec_dir}")
                continue
            committed = json.loads(committed_path.read_text())
            rebuilt = json.loads((tmp_dir / name).read_text())
            for field in fields:
                if committed.get(field) != rebuilt.get(field):
                    drift.append(
                        f"{name}.{field}: committed={committed.get(field)!r} "
                        f"rebuilt={rebuilt.get(field)!r}"
                    )
    if drift:
        print(f"DRIFT in {spec_dir}:", file=sys.stderr)
        for entry in drift:
            print(f"  {entry}", file=sys.stderr)
        return 1
    print(
        f"{spec_dir}: rebuild matches committed evidence (GDS bytes, reference, verdicts)"
    )
    return 0


#: Every terminal letter any supported card kind accepts in a rewire.
_REWIRE_TERMINALS = ("d", "g", "s", "b", "a", "w")


def parse_rewire(text: str) -> tuple[str, str, str]:
    try:
        device, rest = text.split(":", 1)
        terminal, net = rest.split("=", 1)
    except ValueError as exc:
        raise BuildError(
            f"--negative-control wants DEVICE:TERMINAL=NET, got {text!r}"
        ) from exc
    if terminal not in _REWIRE_TERMINALS:
        raise BuildError(
            "--negative-control terminal must be one of "
            f"{'/'.join(_REWIRE_TERMINALS)} (MOS d/g/s/b, resistor a/b/w, "
            f"capacitor a/b), got {terminal!r}"
        )
    return device, terminal, net


def is_genuine_mismatch(lvs: dict) -> bool:
    """True only for an LVS that ran cleanly and reported real mismatches."""
    count = lvs.get("mismatch_count")
    return (
        lvs.get("status") == "mismatch"
        and isinstance(count, int)
        and count > 0
        and not lvs.get("error")
    )


def rewire_card(card: str, terminal: str, net: str) -> tuple[str, str]:
    """``(new card, original net)`` with one terminal moved onto *net*.

    Terminal letters are per card kind: MOS d/g/s/b, resistor a/b/w (w =
    substrate), capacitor a/b.
    """
    name, _terms, model = card_terminals(card)
    names = terminal_names(model)
    if terminal not in names:
        raise BuildError(f"{name} has terminals {'/'.join(names)}, not {terminal!r}")
    tokens = card.split()
    index = 1 + names.index(terminal)
    original = tokens[index]
    if original == net:
        raise BuildError(f"{name}.{terminal} is already {net}")
    tokens[index] = net
    return " ".join(tokens), original


def negative_control(
    spec: dict, spec_dir: Path, rewire: str, *, allow_unpinned: bool
) -> int:
    """Rewire one reference terminal in a scratch copy; require an LVS mismatch."""
    device, terminal, net = parse_rewire(rewire)
    cell = spec["cell"]
    lvs_spec = spec["lvs"]
    if net not in lvs_spec["pins"]:
        raise BuildError(f"--negative-control net {net!r} is not a boundary pin")
    evidence = spec_dir / "negative-control"
    with tempfile.TemporaryDirectory(prefix="klt-negctl-") as tmp:
        tmp_dir = Path(tmp)
        summary = compose_cell(spec, spec_dir, tmp_dir, allow_unpinned=allow_unpinned)
        if summary["problems"]:
            raise BuildError(f"positive rebuild is not clean: {summary['problems']}")
        body = list(summary["reference_body"])
        for i, card in enumerate(body[1:-1], start=1):
            if card.split()[0].upper() == device.upper():
                body[i], original = rewire_card(card, terminal, net)
                break
        else:
            raise BuildError(f"{device} is not in the reference")
        scratch_ref = tmp_dir / f"{cell}.negctl.ref.spice"
        scratch_ref.write_text(
            "\n".join(
                [
                    (
                        f"* NEGATIVE CONTROL -- scratch reference for {cell}: "
                        f"{device}.{terminal} rewired {original} -> {net}"
                    ),
                    "* Must NOT match the layout. Not a design artifact.",
                    *body,
                    ".end",
                    "",
                ]
            )
        )
        lvs = run_lvs(
            extract=summary["extract_json"],
            reference_name=scratch_ref.name,
            deck=summary["deck"],
            lvs_spec={**lvs_spec, "cell_gds": f"{cell}.gds"},
            env=summary["env"],
            out_dir=tmp_dir,
            prefix="negctl.",
        )
        evidence.mkdir(exist_ok=True)
        shutil.copy(scratch_ref, evidence / scratch_ref.name)
        shutil.copy(tmp_dir / "negctl.lvs.request.json", evidence / "lvs.request.json")
        write_json(evidence / "lvs.json", lvs)
    status = lvs.get("status")
    print(
        f"negative control {device}.{terminal}: {original} -> {net}: "
        f"lvs status={status} mismatch_count={lvs.get('mismatch_count')}"
    )
    if not is_genuine_mismatch(lvs):
        reason = (
            "MATCHED -- LVS is not discriminating"
            if status == "match"
            else f"did not yield a genuine mismatch (status={status!r})"
        )
        print(f"error: negative control {reason}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("spec", type=Path, help="path to a layout/<cell>/cell.json")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="rebuild into a temp dir and diff GDS bytes, reference and verdicts "
        "against the committed evidence instead of overwriting it",
    )
    mode.add_argument(
        "--negative-control",
        metavar="DEVICE:TERMINAL=NET",
        help="rewire one reference terminal in a scratch copy and require an LVS "
        "mismatch (evidence under <cell>/negative-control/)",
    )
    parser.add_argument(
        "--allow-unpinned",
        action="store_true",
        help="warn instead of failing when klt/PDK differ from layout/pdk.json",
    )
    args = parser.parse_args(argv)

    spec_path = args.spec.resolve()
    spec = json.loads(spec_path.read_text())
    spec_dir = spec_path.parent

    try:
        if args.check:
            return check_cell(spec, spec_dir, allow_unpinned=args.allow_unpinned)
        if args.negative_control:
            return negative_control(
                spec,
                spec_dir,
                args.negative_control,
                allow_unpinned=args.allow_unpinned,
            )
        summary = compose_cell(
            spec, spec_dir, spec_dir, allow_unpinned=args.allow_unpinned
        )
    except BuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"cell:    {summary['cell']}")
    print(f"klt:     {summary['toolchain']['klt']} / {summary['toolchain']['pdk']}")
    print(f"drc:     {summary['drc']}")
    print(f"extract: {summary['extract']}")
    print(f"lvs:     {summary['lvs']}")
    for problem in summary["problems"]:
        print(f"FAIL:    {problem}", file=sys.stderr)
    return 3 if summary["problems"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
