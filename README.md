# sky130-opamp

A two-stage Miller-compensated operational amplifier on SkyWater sky130 on
[SkyWater sky130](https://github.com/google/skywater-pdk), a 130 nm open CMOS PDK — designed by AI agents driving
[klayout-tools](https://github.com/2AMLogic/klayout-tools) and the
open-source xschem + ngspice flow.

**Status: schematic and PVT evidence committed; partial layout started.** The
[gm/ID study](sim/gm-id-characterization/README.md) informs the
[op-amp schematic](design/README.md), whose resized design has
[PVT characterization records](sim/opamp-characterization/README.md).
The [layout flow](layout/README.md) includes the NMOS input pair with
committed DRC and LVS evidence; the full-core layout remains pending.
Performance gaps remain, including falling slew rate; the
[target specification](spec/target-spec.md) is partially ratified.
The 3.3 V I/O flavor is not served
([DR-005](spec/decision-records/DR-005-io-flavor-not-served.md)).

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
rather than ignoring it. The survey and comparison table are in
[`spec/prior-art.md`](spec/prior-art.md).

## Target specification (partially ratified)

Twin row structure at 1.8 V primary. Swing and gain rows will show the
low-headroom trade explicitly; PVT corners on every recorded result.

**Integrator view (machine-parseable, fixed path):**
[`manifests/integrator.json`](manifests/integrator.json) — top cell, port
list, netlist/GDS paths, area, maturity rung. Consumer requirement rows
live in `## Consumers` in [`spec/target-spec.md`](spec/target-spec.md).
The manifest is a snapshot of the current checkout: `python
design/bin/integrator_check.py validate` (run in CI) checks its derived
fields (maturity from the signoff record, top cell and ordered ports from the
netlist, artifact paths) and `refresh` rewrites only those. `consumers`,
`spec_status` and the `evaluated_at` stamp are authored and not compared; the
manifest never embeds its own commit SHA. `gds` stays null until a qualified
full-core layout exists. Non-null artifact paths are resolved against the
repo root and must stay inside it; `gds` must be a regular file, and
`layout/opamp_stage1` (partial) is rejected however it is spelled (`..`
segments, symlinks).

## Tests

Simulator-free checks (stdlib only; no ngspice, xschem or PDK needed, run in
seconds). One runner executes the whole default gate, sequentially, stopping
at the first failure:

```
python design/bin/check_ci.py     # also: npm test / npm run check:ci
```

It runs, in order:

```
python design/bin/sizing_check.py validate   # historical DR-002 interpolation reproducibility only, not current-design sizing
python design/bin/integrator_check.py validate
python design/bin/spec_figures_check.py validate
python sim/lib/dut_identity.py validate
python sim/lib/dut_identity.py current
python -m unittest discover -s tests -v
python -m unittest discover -s layout/bin -p 'test_*.py' -v
python design/bin/test_netlist_check.py CompareUnit -v
python sim/lib/append_only_check.py --base origin/main   # only if origin/main resolves
```

Of these, `sizing_check.py` is a historical DR-002 replay: it checks that
interpolation reproduces the historical sweep summary and says nothing about the
current schematic sizing. The current design is covered by the DUT identity
checks (`dut_identity.py`) and the netlist checks.

If `origin/main` does not resolve the append-only check is skipped with an
explicit message. The runner mirrors `.github/workflows/tests.yml` (the source
of truth); it never runs xschem. The separate xschem + pinned-PDK gate
(`netlist_check.py` regeneration and the `EndToEnd` netlist tests) runs only in
`.github/workflows/design-sources.yml`.

## License

Apache-2.0.
