"""Shared path/import bootstrap for the simulator-free unit tests.

The runners are scripts, not a package, so load them by file path. Nothing
here needs ngspice, volare or a PDK.
"""

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EXP = REPO / "sim" / "opamp-characterization"
RECORDS = EXP / "records"
TESTBENCH = EXP / "testbench"

sys.path.insert(0, str(REPO / "sim" / "lib"))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod
