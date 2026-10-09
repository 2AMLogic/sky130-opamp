# sim/

ngspice testbenches and append-only results.

- [`gm-id-characterization/`](gm-id-characterization/README.md) — gm/ID,
  gm/gds and fT vs overdrive for sky130's 1.8 V-core MOS devices
  (`sky130_fd_pr__{nfet,pfet}_01v8`), over the confirmed 1.8 V-core process
  corner grid and a channel-length sweep. This block's first `sim/`
  evidence (issue #6).
- [`opamp-characterization/`](opamp-characterization/README.md) — op-amp
  -level (not bare-device) open-loop AC gain/GBW/phase-margin, slew-rate,
  and output-swing PVT testbenches for `design/netlist/opamp_core.spice`,
  over the same 5-corner grid at 3 temperatures, checked against
  `DR-002`'s hand sizing estimates. This block's first **circuit-level**
  `sim/` evidence (issue #17).
  Issue #54 added PSRR+/PSRR- and input-referred-noise benches, run as
  `klt sim` corner requests (`bin/psrr_noise_sweep.py`); PSRR is recorded over
  the full grid, the noise PVT grid is pending a fleet runner that supports
  `measurements[].expr`.
- [`offset-capability/`](offset-capability/README.md) — bounded capability
  probe (issue #52): does the pinned PDK's mismatch model and the seeded
  `klt sim` `monte_carlo` path (client and batch fleet) work end to end,
  before any offset Monte Carlo campaign. Not T1 item 6 evidence.
- [`lib/spice_harness.py`](lib/spice_harness.py) — the PDK-resolution and
  ngspice-harness helpers both runners above share (pin resolution against a
  committed `pdk.json`, `.spice.tmpl` rendering, tool-version and git-SHA
  stamping). Stdlib only. One copy, imported by every `*/bin/*.py` runner
  rather than pasted into each (issue #23).
