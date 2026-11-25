"""Shared SPICE logical-line handling for the design, sim and layout trees (issue #301).

One definition of ``+`` continuation semantics, so a comment or blank between
a card and its continuation can never swallow the continuation's parameters
(``mult=`` lives there for every MOS device in the core netlist). Stdlib-only
and repo-rooted so no tree imports another; callers resolve it relative to
their own script location (design/bin/_common.py,
sim/offset-capability/bin/{attribution,pelgrom_handcalc}.py and
layout/bin/stage_reference.py).

Two modes:

* parse (``keep_comments=False``, the design-gate contract since #237):
  comments and blanks are dropped, cards are stripped, and a leading orphan
  ``+`` (no card to join to) starts its own line;
* emission (``keep_comments=True``, the bench/candidate emitters): comments
  and blanks are retained in file order and each continuation folds into its
  owning card, so regenerating a committed bench or candidate is byte-stable
  (operator ruling on #301).
"""

from __future__ import annotations


def join_continuations(text: str, *, keep_comments: bool = False) -> list[str]:
    """Return SPICE logical lines: ``+`` continuations folded onto their card.

    The last *card* is tracked separately from the last emitted line, so a
    full-line ``*`` comment or a blank line never becomes a continuation
    target (SPICE semantics), in either mode.

    ``keep_comments=False`` drops comments and blanks and strips each card.
    ``keep_comments=True`` retains them in order (trailing whitespace
    stripped) and folds each continuation into its owning card with a single
    space; a continuation before any card is emitted as its own line.
    """
    out: list[str] = []
    last_card: int | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("*"):
            if keep_comments:
                out.append(raw.rstrip())
            continue
        if line.startswith("+") and last_card is not None:
            out[last_card] += " " + line[1:].strip()
        else:
            out.append(raw.rstrip() if keep_comments else line)
            last_card = len(out) - 1
    return out
