"""The klt version pin must be identical in CI and the signoff manifest (issue #127).

Simulator-free: only reads JSON / YAML / Markdown text. To add a copy of the
pin: one line in PIN_LOCATIONS, its file in FILES, its anchor in anchors().
Historical mentions of klt versions in sim/ and layout/ READMEs are run
records, not pins, and are not checked. Shared harness: tests/_pin_sync.py.
"""

import json
import re
import unittest

import _pin_sync

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


class KltPinSyncTests(_pin_sync.PinSyncMixin, unittest.TestCase):
    PIN_RE = VER_RE
    BAD_PIN = "9.9.9"
    FILES = (WORKFLOW, MANIFEST, README)
    PIN_LOCATIONS = {
        "ci signoff.yml pip install": _pip_pin(WORKFLOW),
        "manifest build.version": _build_key("version"),
        "manifest build.package_version": _build_key("package_version"),
        "manifest build.git_tag": _build_key("git_tag", prefix="v"),
        "manifests/README.md pip install": _pip_pin(README),
        "manifests/README.md pin rationale": _readme_moved_to,
    }

    def anchors(self, rel, pin):
        if rel == MANIFEST:
            return ('"version": "' + pin, '"package_version": "' + pin,
                    '"git_tag": "v' + pin)
        if rel == README:
            return ("klayout-tools==" + pin, "pin moved to " + pin)
        return ("klayout-tools==" + pin,)


if __name__ == "__main__":
    unittest.main()
