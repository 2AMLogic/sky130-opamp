#!/usr/bin/env python3
"""Derive a sub-block LVS reference from the design netlist's own device cards.

``design/netlist/opamp_core.spice`` is xschem's export of the whole
``opamp_core`` schematic. Its ``.subckt``/``.ends`` header lines are
commented out (``**.subckt`` / ``**.ends``), every MOS card spills onto a
``+`` continuation line, and the file ends in ``.end``. A layout sub-block
(``layout/opamp_stage1/``) covers only some of those devices, so its LVS
reference is a *selection* of the source cards wrapped in a new subckt:

    .subckt <cell> <pin> <pin> ...
    <selected card, continuation lines joined, otherwise verbatim>
    ...
    .ends <cell>

Nothing else is rewritten: device names, terminal order (d g s b), model
names and every parameter (``L``/``W``/``nf``/``m``/``mult``/``ad``/...) are
copied from the source. No unit rewrite is needed either: the sibling
``compose-cell.py`` this flow is ported from (2AMLogic/sky130-trng@5d44390)
appended ``u`` to bare ``L=``/``W=`` to work around klayout-tools#1492, but
the pinned ``klt`` resolves a bare sky130 literal as micrometres when the
LVS request names ``reference.deck: "sky130"`` (see ``klt lvs`` docs,
"form: subckt-call resolves a bare literal per reference.deck"), so the
cards are passed through unchanged and the reference stays byte-comparable
to the source.

Failure modes are hard errors, never silent: a selected device that is
missing from the source, a selected device that appears more than once, a
duplicate in the selection itself, a card that references a net outside the
declared pin list (this sub-block has no internal-only nets), or a declared
pin that no selected card touches.
"""

from __future__ import annotations

import re
from pathlib import Path


class ReferenceError(ValueError):
    """The requested reference cannot be derived faithfully."""


def logical_lines(text: str) -> list[str]:
    """Join SPICE ``+`` continuation lines onto their parent line.

    Comment lines (``*``) and blank lines are dropped *before* joining, so a
    comment between a card and its continuation does not split it (SPICE
    semantics), and a commented-out ``**.subckt`` header never becomes a
    card. Whitespace inside a card is normalised to single spaces.
    """
    out: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("*"):
            continue
        if line.startswith("+"):
            if not out:
                raise ReferenceError("continuation line before any card")
            out[-1] = f"{out[-1]} {line[1:].strip()}"
            continue
        out.append(line)
    return [" ".join(line.split()) for line in out]


#: Number of terminals per element prefix this flow knows how to select.
#: ``X`` subckt calls to sky130 MOS models carry four (d g s b).
_MOS_MODEL_RE = re.compile(r"^sky130_fd_pr__[np]fet_", re.IGNORECASE)


def card_terminals(card: str) -> tuple[str, list[str], str]:
    """``(name, terminals, model)`` for a MOS subckt-call card."""
    tokens = card.split()
    name = tokens[0]
    if not name.upper().startswith("X"):
        raise ReferenceError(f"{name}: only X subckt-call cards are supported")
    positional = [t for t in tokens[1:] if "=" not in t]
    if len(positional) < 5 or not _MOS_MODEL_RE.match(positional[4]):
        raise ReferenceError(
            f"{name}: not a 4-terminal sky130 MOS card (got {positional!r})"
        )
    return name, positional[:4], positional[4]


def select_cards(text: str, devices: list[str]) -> list[str]:
    """The source cards named by *devices*, in *devices* order."""
    if len({d.upper() for d in devices}) != len(devices):
        raise ReferenceError(f"duplicate device in selection: {devices!r}")
    by_name: dict[str, list[str]] = {}
    for card in logical_lines(text):
        if card.startswith("."):
            continue
        by_name.setdefault(card.split()[0].upper(), []).append(card)
    selected: list[str] = []
    for device in devices:
        found = by_name.get(device.upper(), [])
        if not found:
            raise ReferenceError(f"{device}: not found in source netlist")
        if len(found) > 1:
            raise ReferenceError(
                f"{device}: appears {len(found)} times in source netlist"
            )
        selected.append(found[0])
    return selected


def build_reference(
    text: str, *, cell: str, pins: list[str], devices: list[str]
) -> list[str]:
    """The reference subckt for *cell*, as lines (no trailing newline)."""
    if len(set(pins)) != len(pins):
        raise ReferenceError(f"duplicate pin: {pins!r}")
    cards = select_cards(text, devices)
    used: set[str] = set()
    for card in cards:
        name, terminals, _model = card_terminals(card)
        stray = [t for t in terminals if t not in pins]
        if stray:
            raise ReferenceError(
                f"{name}: terminal net(s) {stray} are not in the pin list "
                f"{pins} (this flow has no internal-only nets)"
            )
        used.update(terminals)
    unused = [p for p in pins if p not in used]
    if unused:
        raise ReferenceError(f"pin(s) {unused} touch no selected device")
    return [f".subckt {cell} {' '.join(pins)}", *cards, f".ends {cell}"]


def write_reference(
    source: Path,
    out_path: Path,
    *,
    source_label: str,
    cell: str,
    pins: list[str],
    devices: list[str],
) -> list[str]:
    """Write the generated reference (with a provenance header) and return it."""
    body = build_reference(source.read_text(), cell=cell, pins=pins, devices=devices)
    lines = [
        f"* LVS reference for {cell} -- GENERATED by layout/bin/stage_reference.py",
        f"* Source: {source_label}, device cards {', '.join(devices)}",
        "* Cards copied verbatim (continuations joined); do not hand-edit.",
        *body,
        ".end",
        "",
    ]
    out_path.write_text("\n".join(lines))
    return body
