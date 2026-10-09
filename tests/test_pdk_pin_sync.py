"""The sky130 PDK pin must be identical in CI, sim and layout configs (issue #81).

Simulator-free: only reads JSON / YAML text. To add a copy of the pin, add one
line to PIN_LOCATIONS.
"""

import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

import _paths

REPO = _paths.REPO
SHA_RE = r"[0-9a-f]{40}"


def _json_key(rel, key="open_pdks_commit"):
    def read(root):
        return json.loads((root / rel).read_text())[key]
    return read


def _json_install_cmd(rel):
    def read(root):
        cmd = json.loads((root / rel).read_text())["install_command"]
        m = re.fullmatch(r"volare enable --pdk sky130 (" + SHA_RE + ")", cmd)
        assert m, f"{rel}: unexpected install_command {cmd!r}"
        return m.group(1)
    return read


def _workflow_pin(root):
    text = (root / ".github/workflows/design-sources.yml").read_text()
    m = re.search(r"^\s*PDK_VERSION:\s*(" + SHA_RE + r")\s*$", text, re.M)
    assert m, "PDK_VERSION not found in design-sources.yml"
    return m.group(1)


PIN_LOCATIONS = {
    "ci PDK_VERSION": _workflow_pin,
    "gm-id pdk.json": _json_key("sim/gm-id-characterization/pdk.json"),
    "gm-id pdk.json install_command": _json_install_cmd("sim/gm-id-characterization/pdk.json"),
    "opamp pdk.json": _json_key("sim/opamp-characterization/pdk.json"),
    "opamp pdk.json install_command": _json_install_cmd("sim/opamp-characterization/pdk.json"),
    "gm-id model-files.json": _json_key("sim/gm-id-characterization/corners/model-files.json"),
    "layout pdk.json": _json_key("layout/pdk.json"),
    "layout pdk.json install_command": _json_install_cmd("layout/pdk.json"),
}


def collect(root):
    return {name: read(root) for name, read in PIN_LOCATIONS.items()}


class PdkPinSyncTests(unittest.TestCase):
    def test_all_copies_equal(self):
        pins = collect(REPO)
        self.assertEqual(
            len(set(pins.values())), 1, f"PDK pin differs across configs: {pins}")
        for name, pin in pins.items():
            self.assertRegex(pin, "^" + SHA_RE + "$", name)

    def _tmp_copy(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        for rel in (".github/workflows/design-sources.yml",
                    "sim/gm-id-characterization/pdk.json",
                    "sim/opamp-characterization/pdk.json",
                    "sim/gm-id-characterization/corners/model-files.json",
                    "layout/pdk.json"):
            dst = tmp / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(REPO / rel, dst)
        return tmp

    def test_negative_control_each_copy_detected(self):
        """Changing any single copy in a temp tree must break equality."""
        good = collect(REPO)
        pin = next(iter(good.values()))
        bad = "0" * 40
        files = {
            ".github/workflows/design-sources.yml",
            "sim/gm-id-characterization/pdk.json",
            "sim/opamp-characterization/pdk.json",
            "sim/gm-id-characterization/corners/model-files.json",
            "layout/pdk.json",
        }
        for rel in files:
            with self.subTest(rel=rel):
                tmp = self._tmp_copy()
                p = tmp / rel
                text = p.read_text()
                # change only the live key, not prose mentions of the pin
                if rel.endswith(".yml"):
                    anchor = "PDK_VERSION: " + pin
                else:
                    anchor = '"open_pdks_commit": "' + pin
                self.assertIn(anchor, text)
                p.write_text(text.replace(anchor, anchor.replace(pin, bad), 1))
                self.assertGreater(len(set(collect(tmp).values())), 1)


if __name__ == "__main__":
    unittest.main()
