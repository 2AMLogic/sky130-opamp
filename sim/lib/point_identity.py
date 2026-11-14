#!/usr/bin/env python3
"""Single owner of this repo's PVT measurement-point identity (issue #291).

A measurement point is identified by the full tuple `(corner, temp_c, <supply>)`,
with the supply read from the record, never inferred from the corner name. This
module owns that tuple's *normalisation* and the *row validation* built on it, so
the CI gate on the ratified spec and the report generators cannot drift apart
about whether a committed row is well formed.

Normalisation (`point_key`):
  * `corner` is stripped and must be non-blank — `" tt "` keys as `"tt"`, `""`
    is an error rather than a corner literally named "".
  * `temp_c` and the supply must parse as *finite* floats and are rounded to 6
    decimals, so `nan`/`inf` are errors rather than keys that compare unequal to
    themselves.

Validation (`validate_rows`): unusable identity, a nonfinite/missing measured
column, and a duplicate point are each an error. Duplicates come back in their
own list so a caller can order them against its own extra checks.

Deliberately NOT owned here:
  * the authored expected-point set arithmetic of
    `design/bin/spec_figures_check.py` (`want - seen` / `seen - want`), which is
    specific to that mapping's `matrices` table;
  * point *rendering*. Callers print the same tuple differently
    (`tt/27 C/1.8 V` vs `TT/27C/1.8V`); pass your own `fmt`.

Before this module existed the convention had three copies, two of which
validated and already disagreed: a blank or whitespace-padded corner and a
nonfinite `temp_c` were rejected by
`sim/opamp-characterization/variants/compare.py` but silently keyed by
`design/bin/spec_figures_check.py` (where a `nan` key, never equal to itself,
also defeated that file's own duplicate-point check). Stdlib only.
"""

from __future__ import annotations

import math
from typing import NamedTuple

SUPPLY_KEY = "vdd_v"
NDIGITS = 6

#: Exceptions a caller must catch around `point_key` / `norm_*`. A malformed row
#: raises one of these; callers turn them into their own error reporting.
IDENTITY_EXC = (KeyError, TypeError, ValueError)


def norm_corner(x):
    """Canonical corner name: stripped, non-blank. Raises ValueError otherwise."""
    if x is None:
        raise ValueError("missing corner")
    c = str(x).strip()
    if not c:
        raise ValueError("empty corner")
    return c


def norm_num(x):
    """Finite float rounded to the identity's 6 decimals.

    Raises ValueError on a nonfinite value (`nan`, `inf`) so it can never reach a
    key, and propagates TypeError/ValueError from `float()` for junk.
    """
    v = float(x)
    if not math.isfinite(v):
        raise ValueError(f"nonfinite value {x!r}")
    return round(v, NDIGITS)


def point_key(row, supply_key=SUPPLY_KEY):
    """`(corner, temp_c, supply)` identity of one record row.

    Raises one of `IDENTITY_EXC` when the row cannot be keyed.
    """
    return (norm_corner(row["corner"]), norm_num(row["temp_c"]), norm_num(row[supply_key]))


def format_point(k):
    """Neutral rendering, for callers without a house style of their own."""
    return f"{k[0]}/{k[1]:g}/{k[2]:g}"


class RowIndex(NamedTuple):
    """Result of `validate_rows`.

    index:      point key -> row (last row wins; `duplicate_errors` reports it)
    seen:       point key -> 1-based row numbers carrying it
    errors:     unusable-identity and nonfinite/missing-column errors, in row order
    duplicate_errors: duplicate-point errors, separate so a caller can order them
                against its own checks
    """

    index: dict
    seen: dict
    errors: list
    duplicate_errors: list


def validate_rows(rows, columns, label, supply_key=SUPPLY_KEY, fmt=format_point):
    """Key `rows` by point identity and collect every validation error.

    `columns` are the measured columns that must be finite at each point.
    `label` prefixes every message (a record path, or `f"matrix {name}"`).
    Returns a `RowIndex`; raises nothing — the caller decides what an error means.
    """
    index, seen, errors, dup_errors = {}, {}, [], []
    for i, r in enumerate(rows, 1):
        try:
            k = point_key(r, supply_key)
        except IDENTITY_EXC as e:
            errors.append(f"{label}: row {i} has no usable corner/temp_c/{supply_key}: {e!r}")
            continue
        seen.setdefault(k, []).append(i)
        for c in columns:
            try:
                ok = math.isfinite(float(r[c]))
            except (KeyError, TypeError, ValueError):
                ok = False
            if not ok:
                errors.append(f"{label}: point {fmt(k)} has nonfinite or missing {c}: {r.get(c)!r}")
        index[k] = r
    for k, idx in sorted(seen.items()):
        if len(idx) > 1:
            dup_errors.append(f"{label}: duplicate point {fmt(k)} in rows {idx}")
    return RowIndex(index, seen, errors, dup_errors)
