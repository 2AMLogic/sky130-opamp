"""The klt version pin must be identical in CI and the signoff manifest (issue #127).

Simulator-free: only reads JSON / YAML / Markdown text. To add a copy of the
pin, add one line to PIN_LOCATIONS. Historical mentions of klt versions in
sim/ and layout/ READMEs are run records, not pins, and are not checked.
"""

import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

import _paths

REPO = _paths.REPO
VER_RE = r"\d+\.\d+\.\d+"
WORKFLOW = ".github/workflows/signoff.yml"
MANIFEST = "manifests/sky130-opamp.signoff.json"
README = "manifests/README.md"


def _pip_pin(rel):
    def read(root):
        text = (root / rel).read_text()
        m = re.search(r"pip install klayout-tools==(" + VER_RE + r")\b", text)
        assert m, f"klayout-tools pin not found in {rel}"
        return m.group(1)
    return read


def _build_key(key, prefix=""):
    def read(root):
        val = json.loads((root / MANIFEST).read_text())["build"][key]
        assert val.startswith(prefix), f"{MANIFEST}: build.{key} {val!r}"
        return val[len(prefix):]
    return read


def _readme_moved_to(root):
    text = (root / README).read_text()
    m = re.search(r"pin moved to\s+(" + VER_RE + r")\b", text)
    assert m, "'pin moved to X' not found in manifests/README.md"
    return m.group(1)


PIN_LOCATIONS = {
    "ci signoff.yml pip install": _pip_pin(WORKFLOW),
    "manifest build.version": _build_key("version"),
    "manifest build.package_version": _build_key("package_version"),
    "manifest build.git_tag": _build_key("git_tag", prefix="v"),
    "manifests/README.md pip install": _pip_pin(README),
    "manifests/README.md pin rationale": _readme_moved_to,
}

FILES = (WORKFLOW, MANIFEST, README)


def collect(root):
    return {name: read(root) for name, read in PIN_LOCATIONS.items()}


class KltPinSyncTests(unittest.TestCase):
    def test_all_copies_equal(self):
        pins = collect(REPO)
        self.assertEqual(
            len(set(pins.values())), 1, f"klt pin differs across files: {pins}")
        for name, pin in pins.items():
            self.assertRegex(pin, "^" + VER_RE + "$", name)

    def _tmp_copy(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        for rel in FILES:
            dst = tmp / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(REPO / rel, dst)
        return tmp

    def test_negative_control_each_copy_detected(self):
        """Changing any single live copy in a temp tree must break equality."""
        pin = next(iter(collect(REPO).values()))
        bad = "9.9.9"
        edits = {
            WORKFLOW: ("klayout-tools==" + pin,),
            MANIFEST: ('"version": "' + pin, '"package_version": "' + pin,
                       '"git_tag": "v' + pin),
            README: ("klayout-tools==" + pin, "pin moved to " + pin),
        }
        for rel, anchors in edits.items():
            for anchor in anchors:
                with self.subTest(rel=rel, anchor=anchor):
                    tmp = self._tmp_copy()
                    p = tmp / rel
                    text = p.read_text()
                    self.assertIn(anchor, text)
                    p.write_text(
                        text.replace(anchor, anchor.replace(pin, bad), 1))
                    self.assertGreater(len(set(collect(tmp).values())), 1)


if __name__ == "__main__":
    unittest.main()
