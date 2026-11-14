"""The sky130 PDK pin must be identical in CI, sim and layout configs (issue #81).

Simulator-free: only reads JSON / YAML text. To add a copy of the pin: one
line in PIN_LOCATIONS, its file in FILES, its anchor in anchors(). Shared
harness: tests/_pin_sync.py.
"""

import json
import re
import unittest

import _pin_sync

SHA_RE = r"[0-9a-f]{40}"
WORKFLOW = ".github/workflows/design-sources.yml"
GMID_PDK = "sim/gm-id-characterization/pdk.json"
GMID_MODELS = "sim/gm-id-characterization/corners/model-files.json"
OPAMP_PDK = "sim/opamp-characterization/pdk.json"
LAYOUT_PDK = "layout/pdk.json"
# the configs that repeat the pin in an install_command (one extra copy each)
INSTALL_CMD_FILES = (GMID_PDK, OPAMP_PDK, LAYOUT_PDK)


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
    text = (root / WORKFLOW).read_text()
    m = re.search(r"^\s*PDK_VERSION:\s*(" + SHA_RE + r")\s*$", text, re.M)
    assert m, "PDK_VERSION not found in design-sources.yml"
    return m.group(1)


class PdkPinSyncTests(_pin_sync.PinSyncMixin, unittest.TestCase):
    PIN_RE = SHA_RE
    BAD_PIN = "0" * 40
    FILES = (WORKFLOW, GMID_PDK, OPAMP_PDK, GMID_MODELS, LAYOUT_PDK)
    PIN_LOCATIONS = {
        "ci PDK_VERSION": _workflow_pin,
        "gm-id pdk.json": _json_key(GMID_PDK),
        "gm-id pdk.json install_command": _json_install_cmd(GMID_PDK),
        "opamp pdk.json": _json_key(OPAMP_PDK),
        "opamp pdk.json install_command": _json_install_cmd(OPAMP_PDK),
        "gm-id model-files.json": _json_key(GMID_MODELS),
        "layout pdk.json": _json_key(LAYOUT_PDK),
        "layout pdk.json install_command": _json_install_cmd(LAYOUT_PDK),
    }

    def anchors(self, rel, pin):
        # each anchor carries its key: edit the live value, not a _comment
        if rel == WORKFLOW:
            return ("PDK_VERSION: " + pin,)
        found = ['"open_pdks_commit": "' + pin]
        if rel in INSTALL_CMD_FILES:
            found.append('"install_command": "volare enable --pdk sky130 ' + pin)
        return found


if __name__ == "__main__":
    unittest.main()
