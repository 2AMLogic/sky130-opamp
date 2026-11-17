"""Shared harness for the two pin-sync guards (issue #286).

test_pdk_pin_sync and test_klt_pin_sync guard different pins the same way and
had drifted as copies of one another. Each module keeps what is actually under
test -- its readers, its PIN_LOCATIONS table of every place the pin is copied,
its pin regex and its mutation anchors; this module keeps only the scaffolding
they shared.

Simulator-free: only reads file text.
"""

import shutil
import tempfile
from pathlib import Path

import _paths

REPO = _paths.REPO


def collect(pin_locations, root):
    """Read every copy of the pin under `root`: {location name: pin}."""
    return {name: read(root) for name, read in pin_locations.items()}


class PinSyncMixin:
    """The two pin-sync tests. Mix in alongside unittest.TestCase and set:

    PIN_LOCATIONS  {display name: read(root)} -- one entry per copy of the pin
    FILES          every file holding a copy; cloned for the negative control
    PIN_RE         regex each collected pin must match in full
    BAD_PIN        a well-formed but different pin, substituted to force drift
    anchors()      the substrings to perturb, below
    """

    def anchors(self, rel, pin):
        """Substrings to perturb in `rel`: one per PIN_LOCATIONS entry reading it."""
        raise NotImplementedError

    def _tmp_copy(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        for rel in self.FILES:
            dst = tmp / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(REPO / rel, dst)
        return tmp

    def test_all_copies_equal(self):
        pins = collect(self.PIN_LOCATIONS, REPO)
        self.assertEqual(len(set(pins.values())), 1, f"pin differs: {pins}")
        for name, pin in pins.items():
            self.assertRegex(pin, "^" + self.PIN_RE + "$", name)

    def test_negative_control_each_copy_detected(self):
        """Changing any single live copy in a temp tree must break equality,
        and the anchors must cover every PIN_LOCATIONS entry one-to-one."""
        base = collect(self.PIN_LOCATIONS, REPO)
        pin = next(iter(base.values()))
        perturbed = set()
        for rel in self.FILES:
            for anchor in self.anchors(rel, pin):
                with self.subTest(rel=rel, anchor=anchor):
                    tmp = self._tmp_copy()
                    p = tmp / rel
                    text = p.read_text()
                    self.assertIn(anchor, text)
                    p.write_text(
                        text.replace(anchor, anchor.replace(pin, self.BAD_PIN),
                                     1))
                    after = collect(self.PIN_LOCATIONS, tmp)
                    changed = {name for name, value in after.items()
                               if value != base[name]}
                    self.assertEqual(
                        1, len(changed),
                        f"anchor {anchor!r} in {rel} perturbs {sorted(changed)}"
                        ": expected exactly one location")
                    perturbed |= changed
        uncovered = sorted(set(self.PIN_LOCATIONS) - perturbed)
        self.assertFalse(
            uncovered, f"PIN_LOCATIONS entries no anchor perturbs: {uncovered}")
