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

Supported devices: 4-terminal sky130 MOS cards plus the two compensation
passives (``res_high_po_1p41``, three terminals incl. substrate;
``cap_mim_m3_1``, two terminals). Any other model is rejected.

Failure modes are hard errors, never silent: a selected device that is
missing from the source, a selected device that appears more than once, a
duplicate in the selection itself, a card that references a net outside the
declared pin list (unless it is listed in the optional ``internal_nets``
declaration, which never adds ports), a declared pin or internal net that no
selected card touches, or an internal net that duplicates or overlaps a pin.
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


#: ``X`` subckt calls to sky130 MOS models carry four terminals (d g s b).
_MOS_MODEL_RE = re.compile(r"^sky130_fd_pr__[np]fet_", re.IGNORECASE)

#: Passive models this flow can select, keyed by lower-cased model name.
#: Deliberately limited to the two models ``design/netlist/opamp_core.spice``
#: uses for the compensation network (issue #167); any other resistor or
#: capacitor model is a hard error rather than a guessed convention.
#:
#:   terminals       extracted-netlist terminal names, in SPICE card order.
#:                   The resistor's third terminal is its substrate (``w`` in
#:                   the klt extract, ``b`` in the model subckt).
#:   extract_class   the ``class`` ``klt extract`` reports for the device.
#:   default_w_um    resistor width when the card carries no ``W=`` (the
#:                   model's own default; ``_1p41`` is the 1.41 um family).
PASSIVE_MODELS: dict[str, dict] = {
    "sky130_fd_pr__res_high_po_1p41": {
        "kind": "resistor",
        "terminals": ("a", "b", "w"),
        "extract_class": "res_high_po",
        "default_w_um": 1.41,
    },
    "sky130_fd_pr__cap_mim_m3_1": {
        "kind": "capacitor",
        "terminals": ("a", "b"),
        "extract_class": "sky130_fd_pr__model__cap_mim",
    },
}

MOS_TERMINALS = ("d", "g", "s", "b")


def card_params(card: str) -> dict[str, float]:
    """``key=value`` tokens of a card, lower-cased keys, numeric values."""
    params: dict[str, float] = {}
    for token in card.split()[1:]:
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        try:
            params[key.lower()] = float(value)
        except ValueError as exc:
            raise ReferenceError(
                f"{card.split()[0]}: parameter {token!r} is not a plain number"
            ) from exc
    return params


def card_kind(model: str) -> str:
    """``mos``, ``resistor`` or ``capacitor`` for a supported model name."""
    if _MOS_MODEL_RE.match(model):
        return "mos"
    return PASSIVE_MODELS[model.lower()]["kind"]


def terminal_names(model: str) -> tuple[str, ...]:
    """Terminal names of a supported model, in card order."""
    if _MOS_MODEL_RE.match(model):
        return MOS_TERMINALS
    return PASSIVE_MODELS[model.lower()]["terminals"]


def card_terminals(card: str) -> tuple[str, list[str], str]:
    """``(name, terminals, model)`` for a supported subckt-call card.

    Supported: four-terminal sky130 MOS cards and the two passive models in
    :data:`PASSIVE_MODELS` with exactly their terminal count.
    """
    tokens = card.split()
    name = tokens[0]
    if not name.upper().startswith("X"):
        raise ReferenceError(f"{name}: only X subckt-call cards are supported")
    positional = [t for t in tokens[1:] if "=" not in t]
    if len(positional) >= 5 and _MOS_MODEL_RE.match(positional[4]):
        return name, positional[:4], positional[4]
    if positional and positional[-1].lower() in PASSIVE_MODELS:
        model = positional[-1]
        count = len(PASSIVE_MODELS[model.lower()]["terminals"])
        if len(positional) != count + 1:
            raise ReferenceError(
                f"{name}: {model} takes {count} terminals, card has "
                f"{len(positional) - 1} ({positional!r})"
            )
        return name, positional[:count], model
    raise ReferenceError(
        f"{name}: not a 4-terminal sky130 MOS card or a supported passive "
        f"({', '.join(sorted(PASSIVE_MODELS))}) (got {positional!r})"
    )


def passive_geometry(card: str) -> dict:
    """Source geometry the layout must reproduce, for a passive card.

    Resistor: ``{"kind", "l_um", "w_um", "units"}`` -- ``w_um`` is the card's
    ``W=`` or the model default; ``units`` is ``m * mult`` identical parallel
    bodies. Capacitor: ``{"kind", "area_um2", "perimeter_um"}`` summed over
    ``MF * m`` units of ``W x L``. A missing ``L`` (or capacitor ``W``) is a
    hard error: nothing is defaulted silently except the documented
    resistor-width model default.
    """
    name, _terminals, model = card_terminals(card)
    info = PASSIVE_MODELS.get(model.lower())
    if info is None:
        raise ReferenceError(f"{name}: {model} is not a passive model")
    params = card_params(card)
    units = params.get("m", 1.0) * params.get("mult", 1.0) * params.get("mf", 1.0)
    if units <= 0 or abs(units - round(units)) > 1e-9:
        raise ReferenceError(f"{name}: m*mult*mf = {units} is not a positive integer")
    units = int(round(units))
    if "l" not in params:
        raise ReferenceError(f"{name}: {model} card has no L=")
    if info["kind"] == "resistor":
        return {
            "kind": "resistor",
            "l_um": params["l"],
            "w_um": params.get("w", info["default_w_um"]),
            "units": units,
        }
    if "w" not in params:
        raise ReferenceError(f"{name}: {model} card has no W=")
    return {
        "kind": "capacitor",
        "area_um2": params["w"] * params["l"] * units,
        "perimeter_um": 2 * (params["w"] + params["l"]) * units,
    }


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


def effective_multiplicity(card: str) -> int:
    """SPICE-effective parallel copies of a MOS card: the instance ``m``.

    The sky130 ``nfet_01v8``/``pfet_01v8`` subckt uses ``mult`` only inside
    its mismatch (Monte Carlo) formulas; the inner device carries no ``m``
    from it, so the ``X``-instance ``m`` is the only multiplier that scales
    current. Checked with one ngspice operating point on the pinned PDK
    (tt, W=7.82 L=1.2 Vgs=0.8 Vds=0.9): ``m=1 mult=1`` and ``m=1 mult=2``
    both draw 45.99 uA, ``m=2 mult=1`` and ``m=2 mult=2`` both 91.99 uA.
    So a card with ``mult=2 m=2`` is two units, not four.
    """
    name = card.split()[0]
    m = card_params(card).get("m", 1.0)
    if m <= 0 or abs(m - round(m)) > 1e-9:
        raise ReferenceError(f"{name}: m = {m} is not a positive integer")
    return int(round(m))


def expand_multiplicity(card: str) -> list[str]:
    """One card per parallel copy, for ``klt lvs``.

    ``klt lvs`` refuses a ``subckt-call`` card with ``m`` > 1 (it cannot
    represent a multiplied device and asks for one device per drawn gate).
    A MOS card with ``m=N`` therefore becomes ``N`` cards named
    ``<name>_1`` .. ``<name>_N`` identical except for ``m=1 mult=1`` (klt
    rejects ``mult`` > 1 too; it is mismatch-statistics only, and a unit
    device is one copy); every other token is verbatim. Cards with ``m`` absent or 1, and passives, are
    returned unchanged. The verbatim card (with its ``m``) stays the source
    of truth for the extracted-geometry check.
    """
    name, _terminals, model = card_terminals(card)
    if card_kind(model) != "mos":
        return [card]
    count = effective_multiplicity(card)
    if count == 1:
        return [card]
    out = []
    for i in range(1, count + 1):
        tokens = card.split()
        tokens[0] = f"{name}_{i}"
        tokens = [
            f"{t.split('=')[0]}=1" if t.lower().startswith(("m=", "mult=")) else t
            for t in tokens
        ]
        out.append(" ".join(tokens))
    return out


def expand_body(body: list[str]) -> list[str]:
    """``body`` (subckt header, cards, ``.ends``) with every card expanded."""
    out = [body[0]]
    for card in body[1:-1]:
        out.extend(expand_multiplicity(card))
    out.append(body[-1])
    return out


def check_internal_nets(pins: list[str], internal_nets: list[str]) -> None:
    """Validate an ``internal_nets`` declaration against the boundary pins."""
    if not isinstance(internal_nets, list) or not all(
        isinstance(n, str) and n and not n.startswith(".") and len(n.split()) == 1
        for n in internal_nets
    ):
        raise ReferenceError(
            f"internal_nets must be a list of net-name strings, got {internal_nets!r}"
        )
    if len(set(internal_nets)) != len(internal_nets):
        raise ReferenceError(f"duplicate internal net: {internal_nets!r}")
    overlap = [n for n in internal_nets if n in pins]
    if overlap:
        raise ReferenceError(
            f"internal net(s) {overlap} are also boundary pins; an internal net "
            "must not be promoted to a port"
        )


def build_reference(
    text: str,
    *,
    cell: str,
    pins: list[str],
    devices: list[str],
    internal_nets: list[str] | None = None,
) -> list[str]:
    """The reference subckt for *cell*, as lines (no trailing newline).

    *internal_nets* (optional) declares nets that exist only inside the cell.
    They are never subckt ports; a device terminal must be a pin or a declared
    internal net, and every declared internal net must be touched. ``None``
    keeps the strict pins-only behaviour.
    """
    if len(set(pins)) != len(pins):
        raise ReferenceError(f"duplicate pin: {pins!r}")
    internal = [] if internal_nets is None else list(internal_nets)
    if internal_nets is not None:
        check_internal_nets(pins, internal)
    allowed = [*pins, *internal]
    cards = select_cards(text, devices)
    used: set[str] = set()
    for card in cards:
        name, terminals, model = card_terminals(card)
        if card_kind(model) != "mos":
            passive_geometry(card)  # rejects a card without the needed L/W
        stray = [t for t in terminals if t not in allowed]
        if stray:
            hint = (
                "and not declared in internal_nets"
                if internal_nets is not None
                else "(no internal_nets declared; this recipe has no internal-only nets)"
            )
            raise ReferenceError(
                f"{name}: terminal net(s) {stray} are not in the pin list "
                f"{pins} {hint}"
            )
        used.update(terminals)
    unused = [p for p in pins if p not in used]
    if unused:
        raise ReferenceError(f"pin(s) {unused} touch no selected device")
    unused_internal = [n for n in internal if n not in used]
    if unused_internal:
        raise ReferenceError(
            f"internal net(s) {unused_internal} touch no selected device"
        )
    return [f".subckt {cell} {' '.join(pins)}", *cards, f".ends {cell}"]


def write_reference(
    source: Path,
    out_path: Path,
    *,
    source_label: str,
    cell: str,
    pins: list[str],
    devices: list[str],
    internal_nets: list[str] | None = None,
) -> list[str]:
    """Write the generated reference (with a provenance header) and return it."""
    body = build_reference(
        source.read_text(),
        cell=cell,
        pins=pins,
        devices=devices,
        internal_nets=internal_nets,
    )
    expanded = expand_body(body)
    note = (
        [
            "* Exception: a MOS card with m=N is written as N cards <name>_1.._N with",
            "* m=1 mult=1, because klt lvs cannot represent m>1 (see expand_multiplicity).",
        ]
        if len(expanded) != len(body)
        else []
    )
    lines = [
        f"* LVS reference for {cell} -- GENERATED by layout/bin/stage_reference.py",
        f"* Source: {source_label}, device cards {', '.join(devices)}",
        *(
            [f"* Internal nets (not ports): {', '.join(internal_nets)}"]
            if internal_nets
            else []
        ),
        "* Cards copied verbatim (continuations joined); do not hand-edit.",
        *note,
        *expanded,
        ".end",
        "",
    ]
    out_path.write_text("\n".join(lines))
    return body
