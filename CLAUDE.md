# sky130-opamp — agent instructions

Open-source canary block: a two-stage miller-compensated operational amplifier on skywater sky130,
on SkyWater sky130, a 130 nm open CMOS PDK, designed and verified by AI agents.

- **PDK**: SkyWater sky130 (https://github.com/google/skywater-pdk). Open-source flow: xschem + ngspice for
  design/sim, klayout-tools (`klt`) for layout work.
- **New block; three-foundry twin** — identical bench structure to
  gf180-opamp and sg13g2-opamp; all numbers from sky130 models.
- **1.8 V primary; 3.3 V I/O-device flavor only via decision record.**
  Headroom-driven divergences from the twins are documented as findings,
  not hidden.
- **gm/ID first**, committed before sizing.
- **Prior open-PDK op-amp art exists on sky130** — cite it, compare
  honestly, and let the agent-native evidence chain be the differentiator.
- **Friction protocol (the canary's job)**: every time klayout-tools is
  awkward, missing a capability, or wrong for what you need, file an issue at
  `2AMLogic/klayout-tools` describing the tool gap generically — that tracker
  is scoped to the tool, so keep design-specific detail out of it and
  describe the gap, not the design.
- **Verification is the product**: no claim without a testbench; PVT corners
  on every recorded result; `sim/` results are append-only evidence.
- Spec changes go through `spec/` with a decision record; agents do not
  relax the ratified spec to make results pass.
