"""Generate a probe variant by editing named parameters on DR-013 device cards."""

import argparse
import re
from pathlib import Path


experiment = Path(__file__).resolve().parents[2]
baseline = experiment / "netlist-snapshots/20261011-140526-04489d4-7e5893/opamp_core.spice"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--baseline", type=Path, default=baseline)
parser.add_argument("output", type=Path)
parser.add_argument("edits", nargs="*", metavar="INSTANCE:PARAM=VALUE[:PARAM=VALUE...]")
args = parser.parse_args()

netlist = args.baseline.read_text()
for edit in args.edits:
    instance, *changes = edit.split(":")
    card = re.search(rf"^{re.escape(instance)} [^\n]*(?:\n\+[^\n]*)*", netlist, re.MULTILINE)
    if card is None or not changes:
        parser.error(f"expected a device card and parameter edits for {edit!r}")
    block = card.group()
    for change in changes:
        key, sep, value = change.partition("=")
        if not (key and sep and value):
            parser.error(f"expected PARAM=VALUE in {edit!r}")
        block, count = re.subn(rf"(?<= ){re.escape(key)}=[^\s]+", lambda _: change, block)
        if count != 1:
            parser.error(f"expected one {key} on {instance}, found {count}")
    netlist = netlist[:card.start()] + block + netlist[card.end():]
args.output.write_text(netlist)
