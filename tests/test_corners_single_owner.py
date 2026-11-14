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

        `tests/` is exempt: asserting the ratified values against a literal is
        this file's own job (RatifiedValuesTests), and a test fixture is never
        what emits a request.
        """
        decl = re.compile(
            r"^\s*(DEFAULT_CORNERS|DEFAULT_TEMPS_C|VDD_BY_CORNER)\s*=\s*[({]", re.MULTILINE)
        offenders = []
        for sub in ("sim", "design", "layout"):
            for path in sorted((REPO / sub).glob("**/*.py")):
                rel = path.relative_to(REPO).as_posix()
                if rel == OWNER_REL:
                    continue
                if decl.search(path.read_text()):
                    offenders.append(rel)
        self.assertEqual(offenders, [],
                         f"re-declared the ratified PVT table; import it from {OWNER_REL}")

    def test_pex_measure_does_not_exec_pvt_sweep_to_borrow_the_table(self):
        """It used to exec all 2699 lines of pvt_sweep.py to read one dict (issue #288)."""
        src = (EXP / "bin" / "pex_measure.py").read_text()
        self.assertFalse("exec_module" in src,
                         "pex_measure.py execs pvt_sweep.py again; import the table instead")


if __name__ == "__main__":
    unittest.main()
