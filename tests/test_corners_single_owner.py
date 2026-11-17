"""The ratified PVT table has exactly one owner, sim/lib/corners.py (issue #288).

`CLAUDE.md` requires "PVT corners on every recorded result" and keeps `sim/`
records append-only. A bench that re-types the corner / temperature / supply
table can drift from the others silently: two records both labelled `ss` would
then be taken at different supplies, and because records are committed as
evidence before anyone could compare the two tables, that drift is
unrecoverable rather than merely wrong.

So these tests assert the *structural* property, not just today's values: every
bench must resolve the table to the one object `sim/lib/corners.py` defines, and
no file may declare its own copy. Values themselves are ratified
(DR-002 Sec (f), spec/target-spec.md Sec 1) and are checked literally here --
changing one is a spec change and must fail this test until `spec/` ratifies it.
"""

import re
import types
import unittest
from pathlib import Path

import _paths
from _paths import EXP, REPO

import corners

pvt = _paths.load_module("pvt_sweep", EXP / "bin" / "pvt_sweep.py")
psrr = _paths.load_module("psrr_noise_sweep", EXP / "bin" / "psrr_noise_sweep.py")
pex = _paths.load_module("pex_measure", EXP / "bin" / "pex_measure.py")
gmid = _paths.load_module("gmid_sweep", REPO / "sim" / "gm-id-characterization" / "bin" / "sweep.py")

# Files allowed to *declare* the table. Exactly one, by design.
OWNER_REL = "sim/lib/corners.py"

# The ratified corner set. Matching is on the *set*, not the declaration order:
# the copy that escaped #288 (offset_probe.py:86, issue #296) listed the same
# five corners in a different order under a different name.
RATIFIED_CORNERS = set(corners.DEFAULT_CORNERS)

# Declaration-shaped re-typings: any ``*CORNERS`` name, plus the temps/supply
# tables under their owner names. The RHS is matched on the same line (a copy
# spread across several lines can still evade this -- stated limitation).
_TABLE_DECL = re.compile(
    r"^\s*([A-Z_]*CORNERS|DEFAULT_TEMPS_C|VDD_BY_CORNER)\s*=\s*(.+)$", re.MULTILINE)
_CORNER_TOKEN = re.compile(r"""['"]([a-z]{2})['"]""")


def _table_offenders(source: str) -> list[str]:
    """Names in `source` that re-type the ratified table (issue #296).

    Two offender shapes: a temps/supply table under its owner name (always),
    and any ``*CORNERS`` whose quoted elements are the five ratified corners
    *as a set* -- any order. A 3-triple DR-002 replay (sizing_check.py) or a
    per-record expected-corner map (validate_psrr_noise.py) holds fewer
    tokens and is not the table.
    """
    offenders = []
    for m in _TABLE_DECL.finditer(source):
        name, rhs = m.group(1), m.group(2)
        if name in ("DEFAULT_TEMPS_C", "VDD_BY_CORNER"):
            offenders.append(name)
        elif RATIFIED_CORNERS <= set(_CORNER_TOKEN.findall(rhs)):
            offenders.append(name)
    return offenders


def _argparse_defaults(test, module) -> dict:
    """The defaults a runner's parser declares, captured without running it.

    A deliberately-invalid argv makes argparse exit *after* every
    add_argument call has been recorded, so the full parser shape is
    observable with zero side effects (no sweep, no file I/O). The shim
    module is swapped into the *runner's* namespace only -- never into the
    stdlib's: the stdlib's own ``super(ArgumentParser, self)`` calls resolve
    ``ArgumentParser`` through argparse's module globals at runtime, so an
    in-place class swap recurses (observed on CPython 3.12).
    """
    recorded = {}
    real_argparse = module.argparse

    class _Recorder(real_argparse.ArgumentParser):
        def add_argument(self, *names, **kw):
            for n in names:
                if n.startswith("--"):
                    recorded[n] = kw.get("default")
            return super().add_argument(*names, **kw)

        def error(self, message):
            raise SystemExit(2)

    shim = types.ModuleType(real_argparse.__name__)
    shim.__dict__.update(real_argparse.__dict__)
    shim.ArgumentParser = _Recorder
    module.argparse = shim
    try:
        with test.assertRaises(SystemExit):
            module.main(["--no-such-flag-captures-defaults"])
    finally:
        module.argparse = real_argparse
    return recorded


class RatifiedValuesTests(unittest.TestCase):
    """The numbers themselves. A diff here is a spec change, not a refactor."""

    def test_corners_are_the_five_ratified_process_corners(self):
        self.assertEqual(corners.DEFAULT_CORNERS, ("tt", "ff", "ss", "sf", "fs"))

    def test_temperature_grid(self):
        self.assertEqual(corners.DEFAULT_TEMPS_C, (-40.0, 27.0, 125.0))

    def test_vdd_pairing_matches_dr002_sec_f(self):
        self.assertEqual(corners.VDD_BY_CORNER,
                         {"tt": 1.80, "ff": 1.98, "ss": 1.62, "sf": 1.80, "fs": 1.80})

    def test_worst_case_supplies_are_nominal_plus_minus_10_percent(self):
        self.assertAlmostEqual(corners.VDD_BY_CORNER["ff"], 1.1 * 1.8)
        self.assertAlmostEqual(corners.VDD_BY_CORNER["ss"], 0.9 * 1.8)
        self.assertAlmostEqual(corners.VDD_BY_CORNER["tt"], 1.8)

    def test_mixed_speed_corners_take_nominal_vdd_a_stated_methodology_choice(self):
        # Not a derived process/supply correlation: DR-002 and target-spec.md name
        # no pairing for sf/fs. See sim/opamp-characterization/README.md.
        for c in ("sf", "fs"):
            self.assertEqual(corners.VDD_BY_CORNER[c], corners.VDD_BY_CORNER["tt"])

    def test_every_corner_has_a_supply(self):
        self.assertEqual(set(corners.VDD_BY_CORNER), set(corners.DEFAULT_CORNERS))


class SingleOwnerTests(unittest.TestCase):
    """Every bench resolves to the owner's object -- not an equal copy."""

    def test_benches_share_the_corner_tuple_object(self):
        for name, mod in (("pvt_sweep", pvt), ("psrr_noise_sweep", psrr), ("gmid_sweep", gmid)):
            with self.subTest(module=name):
                self.assertIs(mod.DEFAULT_CORNERS, corners.DEFAULT_CORNERS)
                self.assertIs(mod.DEFAULT_TEMPS_C, corners.DEFAULT_TEMPS_C)

    def test_benches_share_the_supply_table_object(self):
        for name, mod in (("pvt_sweep", pvt), ("psrr_noise_sweep", psrr), ("pex_measure", pex)):
            with self.subTest(module=name):
                self.assertIs(mod.VDD_BY_CORNER, corners.VDD_BY_CORNER)

    def test_no_other_file_declares_the_table(self):
        """A re-typed copy is the drift hazard the owner module exists to remove.

        Widened in issue #296: the fixed-name regex #288 used could not see
        offset_probe.py's bare ``CORNERS = (...)`` -- a different name in a
        different element order. Matching is now on the corner *set* (any
        order), so a third copy cannot reappear under yet another name or
        order; a 3-triple replay list or a per-record expected map is not the
        table and stays allowed.

        `tests/` is exempt: asserting the ratified values against a literal is
        this file's own job (RatifiedValuesTests), and a test fixture is never
        what emits a request.
        """
        offenders = []
        for sub in ("sim", "design", "layout"):
            for path in sorted((REPO / sub).glob("**/*.py")):
                rel = path.relative_to(REPO).as_posix()
                if rel == OWNER_REL:
                    continue
                names = _table_offenders(path.read_text())
                if names:
                    offenders.append(f"{rel}: {', '.join(names)}")
        self.assertEqual(offenders, [],
                         f"re-declared the ratified PVT table; import it from {OWNER_REL}")

    def test_guard_flags_the_escaped_offset_probe_shape(self):
        """The bare five-corner tuple, in offset_probe.py's old (unsorted) order."""
        src = 'CORNERS = ("tt", "ss", "ff", "sf", "fs")\n'
        self.assertEqual(_table_offenders(src), ["CORNERS"])

    def test_guard_flags_the_owner_order_under_a_foreign_name_too(self):
        src = 'CORNERS = ("tt", "ff", "ss", "sf", "fs")\n'
        self.assertEqual(_table_offenders(src), ["CORNERS"])

    def test_guard_does_not_flag_sizing_check_replay_triples(self):
        """sizing_check.py's pinned 3-triple DR-002 replay is not the table."""
        src = 'CORNERS = [("tt", 27.0, 1.80), ("ss", -40.0, 1.62), ("ff", 125.0, 1.98)]\n'
        self.assertEqual(_table_offenders(src), [])

    def test_guard_does_not_flag_expected_corner_map(self):
        """validate_psrr_noise.py's per-record expected corner_ids are not the table."""
        src = 'EXPECTED_CORNERS = {"dc_fd_psrr": ["tt/1.790V/27C", "tt/1.810V/27C"]}\n'
        self.assertEqual(_table_offenders(src), [])

    def test_guard_still_flags_temps_and_supply_tables(self):
        self.assertEqual(_table_offenders("DEFAULT_TEMPS_C = (-40.0, 27.0, 125.0)\n"),
                         ["DEFAULT_TEMPS_C"])
        self.assertEqual(_table_offenders('VDD_BY_CORNER = {"tt": 1.80}\n'),
                         ["VDD_BY_CORNER"])

    def test_runner_cli_defaults_parse_back_to_the_owner_table(self):
        """The string shape the declaration guard structurally cannot see (#296).

        Each runner's --corners/--temps argparse default must parse back to
        the owner module's values. Parse-back, not byte equality: --temps
        legitimately renders two ways across the four runners (str(t) gives
        -40.0,27.0,125.0; f"{t:g}" gives -40,27,125) and both are correct; a
        re-typed literal that drifts does not parse back.
        """
        for name, mod in (("pvt_sweep", pvt), ("psrr_noise_sweep", psrr),
                          ("gmid_sweep", gmid), ("pex_measure", pex)):
            with self.subTest(module=name):
                d = _argparse_defaults(self, mod)
                self.assertEqual([c.strip() for c in d["--corners"].split(",") if c.strip()],
                                 list(corners.DEFAULT_CORNERS), "--corners default")
                self.assertEqual([float(t) for t in d["--temps"].split(",") if t.strip()],
                                 list(corners.DEFAULT_TEMPS_C), "--temps default")

    def test_pex_defaults_render_byte_identical_to_the_pre_296_literal(self):
        """Converting pex_measure.py's defaults must not move the emitted string.

        f"{t:g}" is required: str(t) renders -40.0,27.0,125.0 and would change
        what the runner emits by default (issue #296).
        """
        self.assertEqual(",".join(corners.DEFAULT_CORNERS), "tt,ff,ss,sf,fs")
        self.assertEqual(",".join(f"{t:g}" for t in corners.DEFAULT_TEMPS_C), "-40,27,125")
        d = _argparse_defaults(self, pex)
        self.assertEqual(d["--corners"], ",".join(corners.DEFAULT_CORNERS))
        self.assertEqual(d["--temps"], ",".join(f"{t:g}" for t in corners.DEFAULT_TEMPS_C))

    def test_pex_measure_does_not_exec_pvt_sweep_to_borrow_the_table(self):
        """It used to exec all 2699 lines of pvt_sweep.py to read one dict (issue #288)."""
        src = (EXP / "bin" / "pex_measure.py").read_text()
        self.assertFalse("exec_module" in src,
                         "pex_measure.py execs pvt_sweep.py again; import the table instead")


if __name__ == "__main__":
    unittest.main()
