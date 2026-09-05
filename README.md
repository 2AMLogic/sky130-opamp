# sky130-opamp

A two-stage Miller-compensated operational amplifier on SkyWater sky130 on
[SkyWater sky130](https://github.com/google/skywater-pdk), a 130 nm open CMOS PDK — designed by AI agents driving
[klayout-tools](https://github.com/2AMLogic/klayout-tools) and the
open-source xschem + ngspice flow.

**Status: just opened.** Nothing is designed yet. The first work is
the gm/ID device-characterization study at 1.8 V, with the 3.3 V I/O flavor surveyed.

**Built agent-native.** Every specification, decision record, testbench, and
line of documentation here is produced by AI agents working from a ratified
spec and an append-only evidence trail — not human-authored work that agents
merely assisted with. Verification is the product: every claim traces to a
recorded result under PVT corners. Where the agents hit friction with the
open-source tooling — most often
[klayout-tools](https://github.com/2AMLogic/klayout-tools) — that friction is
filed as a public issue against the tool itself, so the fix benefits everyone
using this PDK, not just this repo.

## Why this block, on this PDK

The sky130 leg of the three-foundry op-amp twin (see sg13g2-opamp for the
program rationale). sky130's 1.8 V core devices make this the low-voltage
member of the trio — headroom discipline (cascoding choices, swing rows)
will diverge from the 3.3 V twins, and documenting *why* the same topology
sizes differently at 1.8 V is exactly the comparative evidence the twin
program exists to produce.

sky130's open ecosystem is the deepest of the three; where prior open
op-amp work exists publicly, cite it and position against it honestly
rather than ignoring it.

## Target specification (DRAFT — engineering to ratify)

Twin row structure at 1.8 V primary. Swing and gain rows will show the
low-headroom trade explicitly; PVT corners on every recorded result.

## License

Apache-2.0.
