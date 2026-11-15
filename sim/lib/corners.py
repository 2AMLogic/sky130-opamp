#!/usr/bin/env python3
"""The ratified PVT corner / temperature / supply table (issue #288). Stdlib only.

This module is the *single owner* of the three numbers every bench sweeps over.
It exists because the table is ratified-spec data -- DR-002 Sec (f) and
``spec/target-spec.md`` Sec 1 -- and `CLAUDE.md` requires "PVT corners on every
recorded result" with ``sim/`` records append-only. A table typed once per bench
can drift between benches silently: two records both labelled ``ss`` would then
be taken at different supplies, and because records are committed as evidence
before anyone could compare the two tables, that drift is unrecoverable rather
than merely wrong. So the numbers live here, with their citation attached, and
every consumer imports them:

    sys.path.insert(0, str(REPO_ROOT / "sim" / "lib"))
    from corners import DEFAULT_CORNERS, DEFAULT_TEMPS_C, VDD_BY_CORNER

Values are NEVER adjusted here to make a result pass (`CLAUDE.md`: "agents do not
relax the ratified spec"). Changing any of them is a spec change: it goes through
``spec/`` with a decision record first.

The paired/cartesian supply *logic* built on this table (``vdd_pairing``,
``SUPPLY_MODES``, ``vdd_groups``) stays in
``sim/opamp-characterization/bin/pvt_sweep.py`` -- this module owns the table, not
the sweep policy.
"""

# Process corners swept by every bench (DR-002 Sec (f)).
DEFAULT_CORNERS = ("tt", "ff", "ss", "sf", "fs")

# Temperature grid, degrees C (spec/target-spec.md Sec 1).
DEFAULT_TEMPS_C = (-40.0, 27.0, 125.0)

# Corner -> VDD mapping. Matches DR-002 Sec (f)'s own pairing (ss -> 1.62V
# worst-case-low, ff -> 1.98V worst-case-high, tt -> 1.80V nominal,
# per spec/target-spec.md Sec 1). sf/fs have no such named pairing in either
# DR-002 or target-spec.md -- nominal VDD is used for both, a stated
# methodology choice (see sim/opamp-characterization/README.md), not a
# re-derivation of a process/supply correlation this repo has not decided.
VDD_BY_CORNER = {"tt": 1.80, "ff": 1.98, "ss": 1.62, "sf": 1.80, "fs": 1.80}
