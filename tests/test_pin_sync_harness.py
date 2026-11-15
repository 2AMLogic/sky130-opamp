"""Self-test of the pin-sync harness itself (issue #299).

The negative control in tests/_pin_sync.py must hold its subclasses to a 1:1
correspondence between anchors and PIN_LOCATIONS entries -- the count
assertion it replaced accepted a redundant anchor for an already-covered
location while another location stayed uncovered. Fixtures here are synthetic
PinSyncMixin subclasses on temp files: no repo file, no simulator.
"""

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _pin_sync

FIXTURE_FILE = "fixture.txt"
PIN = "PIN"
BAD_PIN = "BAD"
FIXTURE_TEXT = f"one: {PIN}\ntwo: {PIN}\nthree: {PIN}\n"


def _line_reader(key):
    def read(root):
        for line in (root / FIXTURE_FILE).read_text().splitlines():
            if line.startswith(key + ":"):
                return line.split(":", 1)[1].strip()
        raise AssertionError(f"{key!r} not found in {root / FIXTURE_FILE}")
    return read


def _make_case(locations, anchors):
    """A synthetic PinSyncMixin subclass; not module-level, so unittest
    discovery never runs one against the real tree."""
    def anchors_fn(self, rel, pin):
        return anchors

    return type(
        "FixtureCase", (_pin_sync.PinSyncMixin, unittest.TestCase),
        {"FILES": (FIXTURE_FILE,), "PIN_RE": r"\w+", "BAD_PIN": BAD_PIN,
         "PIN_LOCATIONS": locations, "anchors": anchors_fn})


class TestPinSyncHarnessCorrespondence(unittest.TestCase):
    """The harness must fail anchors that break 1:1 coverage and pass a
    genuine 1:1 subclass."""

    def _run_negative_control(self, case_cls, text=FIXTURE_TEXT):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        (root / FIXTURE_FILE).write_text(text)
        with mock.patch.object(_pin_sync, "REPO", root):
            result = unittest.TestResult()
            case_cls("test_negative_control_each_copy_detected").run(result)
        return result

    def test_redundant_anchor_and_uncovered_location_fails(self):
        # 3 anchors == 3 entries (the old count assertion passes), yet the
        # second "one" anchor is redundant and "two" is never perturbed
        holes = _make_case(
            {"one": _line_reader("one"), "two": _line_reader("two"),
             "three": _line_reader("three")},
            [f"one: {PIN}", f": {PIN}", f"three: {PIN}"])
        result = self._run_negative_control(holes)
        self.assertFalse(
            result.wasSuccessful(),
            "harness accepted a redundant anchor and an uncovered location")

    def test_one_to_one_fixture_passes(self):
        good = _make_case(
            {"one": _line_reader("one"), "two": _line_reader("two"),
             "three": _line_reader("three")},
            [f"one: {PIN}", f"two: {PIN}", f"three: {PIN}"])
        result = self._run_negative_control(good)
        self.assertTrue(result.wasSuccessful(), result.failures + result.errors)

    def test_anchor_perturbing_two_locations_fails_naming_both(self):
        dup = _make_case(
            {"one": _line_reader("one"), "one_dup": _line_reader("one"),
             "two": _line_reader("two")},
            [f"one: {PIN}", f"two: {PIN}"])
        result = self._run_negative_control(dup)
        self.assertFalse(result.wasSuccessful())
        tb = "\n".join(tb for _, tb in result.failures + result.errors)
        self.assertIn(f"one: {PIN}", tb)
        self.assertIn("'one'", tb)
        self.assertIn("'one_dup'", tb)
        self.assertIn("exactly one", tb)

    def test_anchor_perturbing_no_location_fails(self):
        text = FIXTURE_TEXT + f"# {PIN} unused\n"
        dead = _make_case(
            {"one": _line_reader("one"), "two": _line_reader("two"),
             "three": _line_reader("three")},
            [f"one: {PIN}", f"two: {PIN}", f"three: {PIN}", f"# {PIN}"])
        result = self._run_negative_control(dead, text)
        self.assertFalse(result.wasSuccessful())
        tb = "\n".join(tb for _, tb in result.failures + result.errors)
        self.assertIn(f"# {PIN}", tb)
        self.assertIn("exactly one", tb)


if __name__ == "__main__":
    unittest.main()
