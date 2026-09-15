# DR-002: Device sizing — channel widths, lengths, mirror ratios, Rz and Cc

- **Status**: **proposed** — drafted by the Builder agent that captured the
  schematic (issue #13). Deliberately *not* submitted for ratification:
  every number below is an operating point interpolated from the committed
  bare-device gm/ID sweep, and **nothing in this record has been simulated
  as a circuit**. Per `CLAUDE.md`'s "no claim without a testbench", a sizing
  record cannot be ratified ahead of the PVT-cornered AC/DC/transient bench
  that would confirm it; submitting this for ratification now would be
  claiming evidence that does not exist. The 2026-08-19 canary spec/DR
  ratification-via-PR standing policy
  ([2AMLogic/2am#357](https://github.com/2AMLogic/2am/issues/357)) still
  applies when that evidence arrives.
- **Date**: 2026-09-15
- **Decided by**: Loom Builder agent, issue #13
- **Related**: [`DR-001`](DR-001-topology-and-cl.md) (the topology, `CL`, the
  candidate channel lengths this record confirms or revises, and the
  `Rz ≈ 1/gm2` compensation rule), `spec/target-spec.md` §2a (the bias-current
  sizing example this record adopts), #6 / PR #7 (the gm/ID sweep every width
  below is computed from), #10 / PR #12 (§2a), gap-to-T1 tracker #3 (item 1,
  "Design sources")

## Context

`DR-001` fixed the topology (NMOS input pair, non-cascoded simple PMOS
mirror load, Class-A PMOS common-source output stage, Miller compensation
with a nulling resistor `Rz`, `CL = 2 pF`) and named **candidate** channel
lengths — `L = 0.15 µm` input pair, `L = 0.3 µm` tail/mirror, `L = 1.2 µm`
output stage — explicitly as "candidates for a future sizing pass to confirm
or revise, not commitments". `spec/target-spec.md` §2a then proposed bias
*currents* only (`I_SS = 10 µA`, `ID2 = 50 µA`, `Cc = 0.5 pF`, all at a
shared `gm/ID = 10 V⁻¹` design point), flagged there as "this pass's own
proposed sizing example". `DR-001`'s "Open items" recorded what neither
record did: *"Device widths and mirror ratios for every device named above
… device width requires a chosen current density from
`sim/gm-id-characterization/records/*-full-sweep.csv`'s `id_a`/`width_um`
columns, not performed here or in #10"*, and *"`Rz`'s numeric value"*.

This record performs exactly that step, for the schematic captured in
`design/opamp_core.sch` (issue #13). It changes no ratification status of
any other record.

## Method, and what it is not

Every width below is `W = I_D / J`, where `J` is a current density
(`id_a / width_um`) read from
[`sim/gm-id-characterization/records/20260909-062847-35a9d46-full-sweep.csv`](../../sim/gm-id-characterization/records/20260909-062847-35a9d46-full-sweep.csv)
at that device's chosen `gm/ID` operating point, at `tt / 27 °C` (the sizing
corner). Because the sweep steps `Vgs` in 20 mV increments, the exact
`gm/ID` point falls between two rows; both bracketing rows are quoted
literally below, together with the interpolation, so any number here can be
reproduced with `grep` and a calculator.

**The interpolation is the sweep harness's own.** `design/bin/sizing_check.py
validate` re-derives all 465 populated rows of the committed
`-summary.csv` from `-full-sweep.csv` using the interpolation this record
uses, and reproduces every `vov_v`, `gm_gds` and `ft_hz` value in that file
**exactly** (max relative deviation `0.000e+00`). So the widths below are
not sized against a second, differently-interpolated reading of the data.

**What this method is not:**

- The sweep biases every device at `|Vds| = 0.9 V`, `Vsb = 0`, `W = 2.0 µm`
  (`sim/gm-id-characterization/records/20260909-062847-35a9d46.md`). In the
  actual circuit `M1`/`M2`, `M3`/`M4` and `M5` sit at much lower `|Vds|`,
  and the input pair's source is at `V_tail > 0` so it carries body effect
  the sweep does not model (≈ +25 mV on `Vth1` at the tail voltages implied
  below). Every operating point here is therefore a **first-order estimate**,
  not a solved operating point of this circuit.
- No SPICE run of any kind was performed for this record — no `.op`, no AC,
  no transient, no PVT sweep, no Monte Carlo. The gain, bandwidth, headroom,
  noise and power figures below are hand formulas evaluated on swept
  device data.
- Mismatch, offset and flicker noise are not sized here: the committed sweep
  has no Pelgrom/`AVT` coefficients and no `1/f` data (the same reason
  `target-spec.md` leaves the offset row `[TBD]`).

## Decision

### (a) Bias currents and passives: §2a's proposal is adopted unchanged

`I_SS = 10 µA` (`ID1 = 5 µA` per input-pair side), `ID2 = 50 µA`,
`Cc = 0.5 pF`, `CL = 2 pF` [DR-001]. §2a's `gm/ID = 10 V⁻¹` design point is
kept for the **signal-path** devices (input pair, mirror, output gain
device), which is what fixes `gm1 = 50 µS`, `gm2 = 500 µS`, `GBW ≈ 15.9 MHz`,
`SR = 20 V/µs`, `gm2/gm1 = 10`, `p2/GBW = 2.50` and the `≈ 30 nV/√Hz` noise
floor exactly as §2a published them. Nothing in §2a's derivation chain is
re-based by this record.

Two additions §2a did not model:

- **A 5 µA external reference current** into the `ibias` pin, feeding the
  on-chip diode-connected reference `MB1`. §2a's `I_Q = I_SS + ID2 = 60 µA`
  counted the two signal branches only; a self-contained cell needs a
  reference branch. Total `I_Q = 65 µA` (see Consequences).
- **The NMOS current-source devices are biased at `gm/ID = 15 V⁻¹`, not
  10 V⁻¹** — see (d). They are current sources; their `gm` enters none of
  §2a's formulas.

### (b) Channel lengths: three groups, each internally matched

| Devices | Role | `DR-001` candidate | **This record** |
|---|---|---|---|
| `M1`, `M2` | NMOS input pair | 0.15 µm | **1.2 µm** (revised) |
| `M3`, `M4`, `M6` | PMOS mirror + output gain device | 0.3 µm (mirror), 1.2 µm (output) | **0.6 µm, shared** (revised) |
| `MB1`, `M5`, `M7` | NMOS bias reference, tail, output sink | 0.3 µm (tail), 1.2 µm (output sink) | **1.2 µm, shared** (revised/confirmed) |

The governing rule this record adopts, and the reason all three candidate
lengths move: **any two devices whose currents must track each other share a
channel length, so their current ratio is set by device count alone.** The
consequences of not doing so are quantified in "Alternatives considered".

**Input pair — `L = 0.15 µm` is not buildable at this current.** At
`gm/ID = 10 V⁻¹`, `tt / 27 °C`, the width needed to carry `ID1 = 5 µA` is:

| `L` (µm) | `J` at `gm/ID = 10` (µA/µm) | `W = 5 µA / J` | vs. PDK minimum |
|---|---|---|---|
| 0.15 | 23.5158 | **0.2126 µm** | **fails** (< 0.42 µm) |
| 0.3 | 14.2050 | **0.3520 µm** | **fails** (< 0.42 µm) |
| 0.6 | 7.2704 | 0.6877 µm | ok |
| 1.2 | 3.7719 | 1.3256 µm | ok |

The 0.42 µm floor is the PDK's own rule, not this record's judgement:
`$PDK_ROOT/$PDK/libs.tech/xschem/xschemrc`'s `fet_drc` proc rejects any
`[np]fet_01v8` instance with per-finger `W/nf < 0.42` (and `L < 0.15`).
`xschem drc_check` on `design/opamp_core.sch` returns clean; the same check
on a copy with `W = 0.3 µm` returns
`M1 (nfet_01v8): finger width is too small, w / nf = 0.3`.

Of the two remaining lengths, `1.2 µm` is chosen over `0.6 µm` because
sky130's `nfet_01v8` shows reverse short-channel behaviour — `Vth` *falls*
with length (`0.8464 V` at `L = 0.15`, `0.7044 V` at `0.6`, `0.6669 V` at
`1.2`, all `ss / −40 °C`) — and the input pair's `Vgs` sets the bottom of
the input common-mode range, which (d) shows is this block's binding
headroom constraint. `L = 1.2 µm` also gives the highest `gm/gds` (150.3 vs
130.5 at `L = 0.6`, `tt / 27 °C`) and 3.9× the gate area (1.59 µm² vs
0.41 µm²) for matching and flicker noise. The cost is `fT`: `0.92 GHz` at `L = 1.2 µm` versus
`50.3 GHz` at `L = 0.15 µm` — still **58× the 15.9 MHz GBW target**, so
`DR-001` decision (a)'s NMOS-over-PMOS `fT` argument is not spent by this
change (the pfet at the same length reaches only `0.24 GHz`; NMOS remains
the faster input device at every length in the grid).

**PMOS group — mirror and output gain device share `L = 0.6 µm`.** `M6`'s
gate is driven by `d2`, which at balance sits at the `M3` diode voltage, so
`M6` conducts the current its `W/L` and that shared `|Vsg|` imply. Equal
current in `M6` and `M7` at balance — zero systematic offset — is the
Allen–Holberg condition

```
(W6/L6) / (W4/L4) = 2 · (W7/L7) / (W5/L5)
```

which this sizing satisfies **exactly and by construction**: `10 = 2 × 5`
(see (c)). That guarantee only holds if `M6` and `M4` share a length; with
`DR-001`'s literal candidates (`M4` at 0.3 µm, `M6` at 1.2 µm) it collapses
(see "Alternatives considered"). `0.6 µm` is the middle of the swept grid:
it keeps `M6` at 27.45 µm rather than 53.7 µm (`L = 1.2`), while `gm/gds` is
still 151.5 — 2.6× the `L = 0.3 µm` value of 57.9 — and `|Vgs_p|` at
`ss / −40 °C` is 1.2627 V rather than 1.2830 V, worth 20 mV of input
common-mode window.

**NMOS current-source group — reference, tail and output sink share
`L = 1.2 µm`,** so the 1 : 2 : 10 device-count ratios below are exact. This
confirms `DR-001`'s candidate for the output sink and revises the tail from
0.3 µm; the tail's own `gm` and `ro` appear in no §2a formula, and the
longer device raises its output resistance (`gm/gds` 184 vs 71), which helps
CMRR.

### (c) Device table (as drawn in `design/opamp_core.sch`)

All devices are `sky130_fd_pr__nfet_01v8` / `__pfet_01v8` (1.8 V core
flavor only, per `CLAUDE.md`). `m` is a count of identical unit devices —
matching is by device count, never by unequal widths.

| Device | Type | `W` per unit (µm) | `L` (µm) | `m` | `W_total` (µm) | `I_D` | `gm/ID` (tt) | Role |
|---|---|---|---|---|---|---|---|---|
| `M1`, `M2` | nfet_01v8 | 1.325 | 1.2 | 1 | 1.325 | 5 µA | 10.0 | input pair (`M1`→`inn`, `M2`→`inp`) |
| `M3` | pfet_01v8 | 2.745 | 0.6 | 1 | 2.745 | 5 µA | 10.0 | mirror reference (diode) |
| `M4` | pfet_01v8 | 2.745 | 0.6 | 1 | 2.745 | 5 µA | 10.0 | mirror output — **1 : 1 with `M3`** |
| `M6` | pfet_01v8 | 2.745 | 0.6 | 10 | 27.45 | 50 µA | 10.0 | output gain device — **10 : 1 on `M3`/`M4`** |
| `MB1` | nfet_01v8 | 3.835 | 1.2 | 1 | 3.835 | 5 µA | 15.0 | bias reference (diode, `ibias`) |
| `M5` | nfet_01v8 | 3.835 | 1.2 | 2 | 7.670 | 10 µA | 15.0 | tail — **2 : 1 on `MB1`** |
| `M7` | nfet_01v8 | 3.835 | 1.2 | 10 | 38.35 | 50 µA | 15.0 | output sink — **10 : 1 on `MB1`** |
| `Rz` | res_high_po_1p41 | 1.41 (fixed) | 7.585 | 1 | — | — | — | nulling resistor, **2.00 kΩ** |
| `Cc` | cap_mim_m3_1 | 15.62 | 15.62 | 1 | — | — | — | Miller capacitor, **0.4998 pF** |

**Mirror ratios, stated explicitly** (the item `DR-001` left open):

- First-stage mirror `M3 : M4` = **1 : 1** — §2a's assumption, confirmed.
  It is what makes `gm_mirror = gm1` and therefore what makes §2a's
  `en² = 32kT/(3·gm1)` noise reduction valid.
- Output stage `M6 : M7` current matching = **1 : 1** (50 µA against 50 µA)
  — §2a's assumption, confirmed, and now *guaranteed* rather than assumed:
  `M6` is 10 unit devices of the same length and `|Vsg|` as `M4`, and `M7`
  is 10 unit devices of the same length and `Vgs` as `MB1`, with
  `M4`'s current `= I_SS/2 = ` `MB1`'s current by construction.
- Bias mirror `MB1 : M5 : M7` = **1 : 2 : 10**.
- PMOS mirror-to-output-device `M4 : M6` = **1 : 10**.

**The three widths, with their literal source rows.** Reproduce with
`python3 design/bin/sizing_check.py widths`, or by grepping the two
bracketing rows out of the full sweep by line number.

*`M1`/`M2` — nfet, `L = 1.2 µm`, `tt / 27 °C`, `gm/ID = 10 V⁻¹`, 5 µA:*

```
line 951: nfet,tt,1.2,2.0,27.0,0.9,0.78,0.19309581900000006,8.74372999e-06,8.15611431e-05,5.68525867e-07,1.30939535e-14,0.586904181,9.327957655746413,143.46074265781826,991362852.2195708
line 950: nfet,tt,1.2,2.0,27.0,0.9,0.76,0.17309581900000004,7.19275638e-06,7.34882887e-05,4.81683142e-07,1.29689848e-14,0.586904181,10.216985647441044,152.56562310831296,901845794.8974752
```

`Id/W` = `8.74372999e-06 / 2.0 = 4.371865 µA/µm` at `gm/ID = 9.327958`, and
`7.19275638e-06 / 2.0 = 3.596378 µA/µm` at `gm/ID = 10.216986`. Interpolating
to `gm/ID = 10.0` gives **`J = 3.771924 µA/µm`**, so
`W = 5 µA / 3.771924 = 1.3256 µm` → **drawn `W = 1.325 µm` (−0.04 %)**. The
same point in the committed summary file is
`nfet,tt,1.2,27.0,10.0,0.1779772321718718,150.34338894034482,923694282.0334392`
(`Vov = 0.178 V`, `gm/gds = 150.34`, `fT = 0.924 GHz`).

*`M3`/`M4`/`M6` PMOS unit — pfet, `L = 0.6 µm`, `tt / 27 °C`,
`gm/ID = 10 V⁻¹`, 5 µA:*

```
line 6132: pfet,tt,0.6,2.0,27.0,0.9,1.1400000000000001,0.1689999780000001,4.18642598e-06,3.96000524e-05,2.7269117e-07,6.331818e-15,0.971000022,9.459155038016462,145.21941579553163,995376696.891489
line 6133: pfet,tt,0.6,2.0,27.0,0.9,1.12,0.1489999780000001,3.43877474e-06,3.51642386e-05,2.28239503e-07,6.23133145e-15,0.971000022,10.225804613186149,154.06727642585165,898132676.4848673
```

`J = 2.093213` and `1.719387 µA/µm` at `gm/ID = 9.459155` and `10.225805`;
interpolating to 10.0 gives **`J = 1.821959 µA/µm`**, so
`W = 5 / 1.821959 = 2.7443 µm` → **drawn `W = 2.745 µm` (+0.03 %)**, and
`M6` is ten of them (27.45 µm) for `ID2 = 50 µA`. Summary row:
`pfet,tt,0.6,27.0,10.0,0.1548906644491818,151.46127778988793,926774378.148529`.

*`MB1`/`M5`/`M7` NMOS unit — nfet, `L = 1.2 µm`, `tt / 27 °C`,
`gm/ID = 15 V⁻¹`, 5 µA:*

```
line 946: nfet,tt,1.2,2.0,27.0,0.9,0.68,0.09309581900000008,2.66358129e-06,3.96979094e-05,2.15879703e-07,1.23071254e-14,0.586904181,14.903960149081842,183.88903101279513,513370775.55285317
line 945: nfet,tt,1.2,2.0,27.0,0.9,0.66,0.07309581900000006,1.95003252e-06,3.17534264e-05,1.69101582e-07,1.20931504e-14,0.586904181,16.283536850964925,187.77722848269983,417898943.1624605
```

`J = 1.331791` and `0.975016 µA/µm` at `gm/ID = 14.903960` and `16.283537`;
interpolating to 15.0 gives **`J = 1.303192 µA/µm`**, so
`W = 5 / 1.303192 = 3.8367 µm` → **drawn `W = 3.835 µm` (−0.05 %)**, with
`M5` = 2 units (10 µA) and `M7` = 10 units (50 µA). Summary row:
`nfet,tt,1.2,27.0,15.0,0.09170351002889225,184.15970962373447,506724461.11659086`.

### (d) The NMOS current sources are biased at `gm/ID = 15 V⁻¹`, not 10

This is the one place a §2a assumption is revised, and the reason is
headroom. For this topology the input common-mode window at a given supply
is

```
V_icm,max − V_icm,min = VDD − |Vgs,mirror| − Vdsat,M1 − Vdsat,M5
```

and on sky130 `|Vgs|` of the PMOS mirror is dominated by `|Vth_p|`, which at
`ss / −40 °C` is **1.1065 V** for this device — 68 % of the 1.62 V
worst-case-low rail — before any overdrive. Biasing the NMOS current sources
weaker (`gm/ID = 15` instead of 10) cuts their `Vov` from 0.149 V to 0.072 V
at that corner and **more than doubles the worst-corner common-mode window,
from 59 mV to 136 mV**; it also lowers `Vout,min` (set by `M7`'s `Vdsat`)
from 0.149 V to 0.072 V. Nothing in §2a depends on these devices' `gm`.

### (e) `Rz = 2.00 kΩ`, `Cc = 0.4998 pF` — `DR-001` decision (d) confirmed

`Rz = 1/gm2 = 1/500 µS = 2.00 kΩ`, exactly the value `DR-001`'s "Open items"
predicted from §2a's `gm2 = 500 µS`. Realised as one
`sky130_fd_pr__res_high_po_1p41` (the PDK's 1.41 µm-wide high-sheet poly
precision resistor) at `L = 7.585 µm`: that model's own parameters give
`R = rcon + L·rsheet = 254.77 + 230.05 × 7.585 = 1999.7 Ω`.

`Cc = 0.4998 pF` — §2a's `0.5 pF`, i.e. `0.25 × CL`, the midpoint of
`DR-001`'s `Cc ≈ (0.2–0.3) × CL` range. Realised as one
`sky130_fd_pr__cap_mim_m3_1` at `W = L = 15.62 µm`; that model's own area and
perimeter coefficients give
`2 fF/µm² × 15.62² + 0.38 fF/µm × 2 × 15.62 = 499.8 fF`.

With `Rz` fixed at 2.00 kΩ the compensation zero sits at
`1 / (2π·Cc·(1/gm2 − Rz))`: **infinite at `tt / 27 °C`** (exact
cancellation), `−2175 MHz` (left half-plane) at `ss / −40 °C`, and
`+1250 MHz` at `ff / 125 °C`. Even the worst of those — the residual
right-half-plane zero at `ff / 125 °C` — is 89× `GBW`, against the
159 MHz (10× `GBW`) RHP zero plain Miller compensation would have left.
`DR-001` decision (d)'s stated purpose is met at all three corner extremes.

### (f) First-order performance of the sized circuit

Computed from the **drawn** widths, by back-solving each device's operating
point from its fixed current density at each corner
(`python3 design/bin/sizing_check.py corners`). Read these as sizing
estimates, not results.

| Quantity | `tt` / 27 °C / 1.80 V | `ss` / −40 °C / 1.62 V | `ff` / 125 °C / 1.98 V | §2a said |
|---|---|---|---|---|
| Open-loop DC gain | 5116 (**74.2 dB**) | 5673 (**75.1 dB**) | 4348 (**72.8 dB**) | 62.1–65.1 dB |
| `gm1` | 50.0 µS | 56.3 µS | 43.9 µS | 50 µS |
| `gm2` | 500 µS | 540 µS | 444 µS | 500 µS |
| `gm2/gm1` | 10.00 | 9.58 | 10.10 | ≈ 10 |
| GBW | 15.92 MHz | 17.94 MHz | 13.98 MHz | ≈ 15.9 MHz |
| `p2`, `p2/GBW` | 39.8 MHz, 2.50 | 42.9 MHz, 2.39 | 35.3 MHz, 2.52 | 39.8 MHz, 2.50 |
| Slew rate | 20.0 V/µs | 20.0 V/µs | 20.0 V/µs | 20 V/µs |
| Input-referred thermal floor | 29.7 nV/√Hz | 24.4 nV/√Hz | 36.6 nV/√Hz | ≈ 30 nV/√Hz |
| Output swing (saturation-limited) | 0.092–1.645 V | 0.072–1.464 V | 0.130–1.832 V | 0.17–1.45 V |
| **Input common-mode window** | 0.857–1.261 V | **0.888–1.024 V (136 mV)** | 0.836–1.524 V | — (no row) |
| `I_Q` / quiescent power | 65 µA / 117.0 µW | 65 µA / 105.3 µW | 65 µA / **128.7 µW** | 60 µA / 108–119 µW |

The DC-gain estimate uses the same loaded-parallel-resistance model §2a
used, now with this record's actual lengths; the improvement from
62–65 dB to 73–75 dB is entirely the longer input pair and mirror.

## Alternatives considered

- **Keep `DR-001`'s candidate input-pair length `L = 0.15 µm`.** Rejected —
  not buildable. `W = 0.2126 µm` at `ID1 = 5 µA`, `gm/ID = 10 V⁻¹`, versus a
  0.42 µm PDK minimum finger width. Holding `L = 0.15 µm` would force either
  a 2× larger tail current (breaking §2a's `I_SS`, `SR`, `GBW` and power
  numbers) or a much higher `gm/ID` at `W = 0.42 µm` (breaking §2a's
  `gm1 = 50 µS` and therefore its GBW row). Revising `L` is the change that
  costs the published numbers nothing.
- **Input pair at `L = 0.6 µm`** (the shortest length that clears the
  minimum-width floor). Rejected in favour of 1.2 µm: it gives 34 mV more
  input-pair `Vgs` at `ss / −40 °C`, which comes straight off the top of an
  already-136 mV common-mode window, plus lower `gm/gds` and roughly a
  quarter of the gate area for matching. Its only advantage, `fT` of 3.55 GHz vs 0.92 GHz, is
  irrelevant at a 15.9 MHz `GBW`. Worth revisiting if a future spec revision
  raises GBW by an order of magnitude.
- **`DR-001`'s literal candidate pairing: mirror at `L = 0.3 µm`, output
  gain device at `L = 1.2 µm`.** Rejected — it breaks output-stage current
  balance. With `M4` at `L = 0.3 µm` (`W = 1.4466 µm`), `M6` at `L = 1.2 µm`
  would need `W = 166.3 µm` to carry 50 µA at the mirror's `|Vsg|` at
  `tt / 27 °C`; the *same* width delivers only ≈ 39.5 µA at `ff / 125 °C`
  and ≈ 67 µA at `ss / −40 °C`, against an `M7` sink held at 50 µA by a
  same-length NMOS mirror. A −21 % / +34 % imbalance at the output node is a
  large systematic offset that open-loop would drive the output into a rail.
  Matched lengths remove this by construction, at no current cost.
- **All devices at `L = 1.2 µm`** (a single uniform length). Rejected: the
  PMOS mirror's `|Vgs|` grows to 1.2830 V at `ss / −40 °C`, shrinking the
  worst-corner common-mode window from 136 mV to 116 mV, and `M6` grows to
  53.7 µm. The extra DC gain it buys (≈ 81 dB) is not needed against a
  `≥ 60 dB` target.
- **PMOS group at `L = 0.3 µm`.** Rejected: 182 mV of common-mode window
  (46 mV more than chosen) but DC gain falls to 62–65 dB — right at the
  `≥ 60 dB` target with no margin for the effects this first-order model
  omits (finite tail loading, mismatch, layout).
- **PMOS group biased weaker (`gm/ID = 12.5 V⁻¹`) for more headroom.** A
  real candidate: ≈ 189 mV of worst-corner common-mode window and ≈ 76 dB
  gain. Not adopted here because it moves `gm2` to 625 µS, i.e. `Rz` to
  1.6 kΩ and `gm2/gm1` to 12.5, re-basing numbers §2a has already published;
  and because the choice between it and this record's sizing should be made
  against a simulated phase margin and a simulated common-mode range, which
  do not exist yet. **This is the first knob to turn if the AC/PVT bench
  finds the common-mode window binding.**
- **Keeping the NMOS current sources at `gm/ID = 10 V⁻¹`** (a single uniform
  design point, as §2a assumed). Rejected: it costs 77 mV of `Vov` on both
  the tail and the output sink at `ss / −40 °C`, cutting the worst-corner
  common-mode window from 136 mV to 59 mV and raising `Vout,min` from
  0.072 V to 0.149 V, in exchange for nothing §2a's formulas use.
- **No on-chip bias reference (an external gate-voltage `vbias` pin
  instead).** Rejected: it would hold `I_Q` at §2a's 60 µA, but a gate
  voltage does not define a current across PVT — the whole block's bias
  would then be set by an off-chip voltage against on-chip `Vth`. A 5 µA
  current input with a diode-connected reference is the standard interface
  and is what the three-foundry twin `sg13g2-opamp/design/opamp_core.sch`
  uses.
- **A smaller reference current (e.g. 2.5 µA, with 4 : 1 and 20 : 1 mirror
  ratios).** Rejected: it would recover 2.5 µA of `I_Q` at the cost of a
  20 : 1 mirror ratio and a 1.9 µm unit device, trading real matching
  accuracy for a 4 % power figure.
- **`Rz` as a triode-region PMOS instead of a poly resistor.** Not adopted
  here, but explicitly flagged for the compensation bench: a triode device
  biased off the same `|Vsg|` as `M6` makes `Rz` track `1/gm2` over PVT,
  whereas the poly resistor does not (see Consequences). The poly resistor
  is chosen first because it is the literal reading of `DR-001` decision (d),
  it consumes no headroom, and (e) shows the residual zero stays ≥ 89× `GBW`
  across the corner extremes even without tracking.

## Spec lines affected

**None ratified by this record.** It fills `DR-001`'s "Open items" bullets
on device widths, mirror ratios and `Rz`'s numeric value, and `DR-001`'s
"Open items" section is updated to point here. Three `spec/target-spec.md`
§2 rows now have a *better* first-order estimate than §2a's, and one is
*worse*; none of those cells is edited by this record, because they are `[P]`
values whose revision belongs with the PVT bench that can actually measure
them:

- **Open-loop DC gain** — §2a estimated 62.1–65.1 dB; this sizing estimates
  72.8–75.1 dB. The `≥ 60 dB` target is unchanged and still met.
- **Output swing** — §2a estimated 0.17–1.45 V (1.27 Vpp) at the
  worst-case-low rail; this sizing estimates 0.072–1.464 V (1.39 Vpp).
- **Quiescent power** — §2a estimated ≈ 119 µW at the stated binding corner
  (1.98 V); with the 5 µA bias-reference branch this sizing gives
  **128.7 µW**, ≈ 8 % above the published figure. This is a real deviation,
  not a rounding difference (see Consequences).

## Consequences

- **`I_Q` is 65 µA, not 60 µA.** §2a's power row counted only the tail and
  output-stage branches. The reference branch is 5 µA — the smallest this
  record is willing to make it without pushing the bias mirror past 10 : 1.
  The `target-spec.md` quiescent-power row should be reconciled (or the
  reference current re-scoped as external/shared) by whichever issue next
  touches that row with simulated evidence.
- **The input common-mode window is this block's real limiter, and it is
  narrow.** At `ss / −40 °C` and `VDD = 1.62 V` it is ≈ 136 mV wide and sits
  at ≈ 0.89–1.02 V — *above* mid-rail (0.81 V). A unity-gain buffer with its
  input at mid-rail would not bias correctly at that corner. This follows
  directly from `DR-001`'s NMOS-pair-plus-PMOS-mirror choice meeting
  sky130's `|Vth_p| = 1.1065 V` at `ss / −40 °C`: even with the PMOS mirror
  at zero overdrive the window could not exceed ≈ 0.29 V there. This is exactly the
  "headroom-driven divergence from the twins" `CLAUDE.md` asks to be
  recorded as a finding rather than hidden, and `target-spec.md` has **no
  input-common-mode-range row at all** to measure it against. A row should be
  added, and if a common-mode range wider than ≈ 0.2 V at the cold/slow/low
  corner is required, `DR-001`'s input-pair polarity — not this record's
  widths — is what has to be reopened, in a superseding record.
- **Zero systematic offset is now structural, not incidental.** It holds as
  long as the three length groups and the 1 : 2 : 10 and 1 : 10 device counts
  are preserved. Any future edit that changes one device's length without
  changing its group's breaks it silently — that is the main review hazard
  this sizing introduces.
- **`Rz` does not track `gm2` over PVT.** `1/gm2` spans 1854–2255 Ω across
  the corner extremes while the poly resistor has its own ±12.5 %
  process spread and a `+0.514e-3 /°C` temperature coefficient, in the
  opposite direction to `gm2`'s temperature drift. (e) shows the residual
  zero stays far beyond `GBW` anyway, but a triode-`Rz` variant should be on
  the table if the simulated phase margin is tight.
- **Area is dominated by the Miller capacitor.** Drawn gate area totals
  ≈ 82.8 µm² across all eight transistors; `Cc` alone is 244 µm² and `Rz`
  10.7 µm². Any future area target is a `Cc` conversation first.
- **The output-stage devices are large**: `M6` is 10 × 2.745 µm and `M7` is
  10 × 3.835 µm. Both are drawn here as unit-device multiplicities (`m`), so
  the layout pass has an obvious common-centroid structure to build, but
  also 20 unit devices to place.
- **Nothing here is verified.** The next gate is a testbench: DC operating
  point (does every device actually sit in saturation at the `|Vds|` values
  this circuit imposes, rather than the sweep's 0.9 V?), open-loop AC gain
  and phase margin over the PVT grid, slew/settling, and a common-mode sweep
  for the window above.

## Open items

- **Everything in "Consequences" that says "not verified".** No operating
  point, gain, bandwidth, phase margin, slew rate, swing, noise or power
  figure in this record has been simulated. Each is a hand calculation on
  bare-device sweep data taken at `|Vds| = 0.9 V` and `Vsb = 0`.
- **Phase margin** is not computed at all here — only `p2/GBW`, the ratio
  `DR-001`'s appendix uses as a proxy. The `≥ 60°` target is unverified.
- **Input-referred offset and mismatch.** Unchanged from `DR-001`: the
  committed sweep has no `AVT`/Pelgrom data. The input pair's 1.59 µm² gate
  area and the unit-device mirror structure were chosen with matching in
  mind, but no `σ(VOS)` number is claimed.
- **Flicker noise.** Not characterized by the committed sweep; only the
  thermal floor is estimated.
- **Layout parasitics.** `ad`/`as`/`pd`/`ps` in the committed netlist come
  from the PDK symbol's own pre-layout expressions, not from an extraction.
- **An input-common-mode-range row in `spec/target-spec.md`**, and the
  question of whether ≈ 136 mV at `ss / −40 °C` / 1.62 V is acceptable for
  this block's intended use.
- **Reconciling the quiescent-power row** with the 5 µA reference branch.
- **The 3.3 V I/O-device-flavor variant** — still out of scope per
  `CLAUDE.md`.
