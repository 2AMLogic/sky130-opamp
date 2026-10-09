# Prior art — public sky130 op-amp designs (survey and honest comparison)

`CLAUDE.md` asks this repo to cite prior open-PDK op-amp work on sky130,
compare against it honestly, and let the evidence chain be the
differentiator. This document does that. It is **documentation only**: no
row of [`target-spec.md`](target-spec.md) is changed, no new simulation was
run, and no decision record is needed.

- **Survey date**: 2026-10-09. Every source below was fetched on that date at
  the commit shown, and the figures quoted are what was found at that commit.
  If a source reports a number only in a plot, the plot was not read off and
  the figure is listed as "not reported".
- **Scope**: a first pass (issue #76), not an exhaustive survey. Add more
  entries later in the same format.
- **This block's figures** come only from the committed PVT records under
  [`sim/opamp-characterization/`](../sim/opamp-characterization/README.md),
  cited by record id. The current sizing is the DR-007 resize, record
  `20261001-074923-c317ff9`. All of this block's evidence is **pre-layout**
  (schematic netlist, R+C typical, `CL = 2 pF`, `VDD` tied to corner:
  tt/sf/fs 1.80 V, ss 1.62 V, ff 1.98 V, at −40 / 27 / 125 °C).

## 1. Sources surveyed

| # | Source (URL) | Pinned commit (commit date) | Topology as described by the source | Supply | Load used for its figures | Corners / conditions of its figures |
|---|---|---|---|---|---|---|
| S1 | [RTimothyEdwards/sky130_ef_ip__opamp](https://github.com/RTimothyEdwards/sky130_ef_ip__opamp) (Efabless analog-IP example, designer Tim Edwards) | `e3ae288bad8407e96cf14d6169d6bf7c10c5eb7d` (2024-08-23) | "Rail-to-rail driver operational amplifier" (`docs/sky130_ef_ip__opamp.md`). The schematic is in `xschem/` and was not analysed here | 3.3 V typical (`vdd` pin 3.0–3.6 V) | `Rout` 100 MΩ, `Cout` default condition "maximum: 100" fF (`cace/sky130_ef_ip__opamp.yaml`) | CACE sweep, `corner` ss/tt/ff × temperature −40/27/110 °C on the AC and slew rows. Results in `docs/sky130_ef_ip__opamp_rcx.md` are from the **post-layout (rcx) netlist** and list min / typ / max **over that sweep**, not at one named point |
| S2 | [tdextrous/sky130_td_ip__opamp_hp](https://github.com/tdextrous/sky130_td_ip__opamp_hp) ("High-gain operational amplifier IP block … Chipalooza 2024") | `05198f3136350ab9a887ce563b086c287d2ab79b` (2024-04-21) | "Rail-to-rail driver operational amplifier" (`cace/sky130_td_ip__opamp_hp.txt`) | 3.3 V typical | `Rout` 500 kΩ, `Cout` maximum 30 pF | CACE **spec** only, ss/tt/ff × −40/27/85 °C. The repo has spec limits (e.g. Avo min 70 dB, GBW 10–15 MHz) but **no measured results** at the pinned commit |
| S3 | [chennakeshavadasa/Miller-Compensated-Two-stage-OPAMP-using-SKY130PDK](https://github.com/chennakeshavadasa/Miller-Compensated-Two-stage-OPAMP-using-SKY130PDK) | `4de4804d548c45fc3788993bf7306f043a2e9e0c` (2025-06-18) | Two-stage Miller: NMOS differential pair with PMOS mirror, PMOS common-source second stage, `C1` 3 pF Miller cap (README; `Schematics/Two stage Opamp Test bench/2stageopamptry.spice`) | README: "VDD=1.8V". **Caveat**: the committed testbench deck sets `V1 VDD 1.8` **and** `V2 VSS -1.8`, so it may be a ±1.8 V split supply. The README does not say which deck its figures come from | `C2` 10 pF (README "CL: 10pF"; same deck) | No corner or temperature is stated in the README. The committed deck uses `.lib … tt` and has no `.temp` card. Single point, pre-layout |
| S4 | [SkillSurf/ttsky25_se_opamp](https://github.com/SkillSurf/ttsky25_se_opamp) ("Template for Operational Amplifier Design submission for Tiny Tapeout SKY130") | `d296672b3f5de908eb1764ab309abb7cdb67e221` (2025-11-12) | Two-stage single-ended op-amp with Miller capacitor (hand calculation uses `C_miller` = 12 pF), meant as a unity-gain buffer for 1–10 kHz signals | 1.7–1.9 V requirement | 25 pF (requirement table) | Requirement temperature range 20–50 °C. The slew figures are in figure captions with no stated corner. ff/ss PVT results appear as plots only. "Monte-Carlo Simulations yet to be updated" |
| S5 | [idea-fasoc/OpenFASOC](https://github.com/idea-fasoc/OpenFASOC), glayout `opamp_twostage` generator (`openfasoc/generators/glayout/glayout/flow/blocks/composite/opamp/`) | `426c17025c7c01d6e7d4d259fb7f9e7d741cc5c4` (2025-10-22) | Generated two-stage op-amp: diff pair + common-source gain stage, MIM-cap array, plus a separate output stage | 1.8 V (`Vsupply VDD GND 1.8`, `flow/testbench/opamp_tb.sp`) | `cload=0` (CI call in `.github/scripts/test_glayout_ci.py`) | CI regression reference for **one** parameter set: `.lib … tt`, `temp=25`, `noparasitics=False` (extracted), with bias currents **swept by the testbench to maximise** `ugb/(Ibias_cs+Ibias_dp)` subject to PM > 45°. Values in `.github/scripts/expected_sim_outputs/opamp/means.json` |

Also found but not entered as sources: `vyges-ip/sky130-opamp` (pinned
`65f6e2b2dcabe30655f4da17e95c25d288634c02`) says "Two-stage Miller-compensated
op-amp in SKY130 (taped out on Caravel)" but reports no figure of merit in its
README or `rtl/README.md`. Other search hits were left out because their README
gives no numbers (for example `mtfir/sky130-opamp`) or gives them only as plots.
`ridvanumaz/2AC_Folded-Cascode-OTA-with-SKY130-PDK` is one of these: its repo
description quotes 54.27 dB / 66.8 MHz for a 3.3 V folded cascode, but the
README states no load or corner for those numbers.

### 1.1 Figures each source reports (quoted as found)

**S1** (`docs/sky130_ef_ip__opamp_rcx.md`, "netlist source: rcx"; min / typ / max over the CACE sweep):

| Row | Min | Typ | Max |
|---|---|---|---|
| Open-loop voltage gain | 117.218 dB | 123.762 dB | 129.703 dB |
| Gain-bandwidth | 0.000 MHz | 2.368 MHz | 4.408 MHz |
| Phase margin | 155.067° | 157.299° | 180.000° |
| Slew rate, rise | 0.529 V/µs | 9.776 V/µs | 21.751 V/µs |
| Slew rate, fall | 1.116 V/µs | 13.571 V/µs | 25.040 V/µs |
| Idd (enabled, no load) | 91.607 µA | 122.152 µA | 123.705 µA |
| Vol / Voh | — | 0.000 V / 3.300 V | — |
| CMRR @ 100 kHz | −64.420 dB | −51.635 dB | −43.371 dB |
| PSRR @ 100 kHz | −132.436 dB | −71.114 dB | −17.037 dB |
| Equivalent input noise @ 1 kHz / 10 kHz | not reported (target 280 / 100 nV/√Hz, value cells empty) | | |

DRC (Magic and KLayout) and Netgen LVS pass, area 1940.782 µm². The
phase-margin values (155–180°) show a convention different from this block's
`180° + phase_at_gbw`, so the numbers cannot be compared directly.

**S2**: no measured figures at the pinned commit (spec limits only).

**S3** (README "Achieved specifications"): DC gain 60 dB, GBW 10 MHz, phase
margin 80°, power dissipation 41 µW, slew rate "9.06V/sec" (the unit is as
written; probably V/µs, but that is not confirmed), CMRR 71 dB (frequency and
common-mode point not stated). Output swing, PSRR and noise: not reported.

**S4** (README figure captions): slew rate open-loop 9.08 V/µs (positive pulse)
/ 1.3 V/µs (negative pulse); closed-loop 5.80 V/µs (positive) / 1.3 V/µs
(negative). DC gain, GBW and PM appear only as a Bode plot ("for input freq of
10kHz"), so they are not reported here as numbers. Swing, Iq, PSRR, noise:
not reported.

**S5** (`means.json`): `ugb` 33262790.0 (Hz), `dcGain` 66.01914 (dB),
`phaseMargin` 62.0 (°), `power` 0.000546523847 (W, total including the output
stage), `power_twostage` 0.000209923847 (W; the testbench calculates it as
total power minus a fixed `estimated_output_1to1_ref = 336.6u`), `noise`
3.9531001 (unit not stated in the file), `area` 47939.76 (µm² presumably; unit
not stated). Slew, swing, PSRR: not reported. The CI checks a fresh run against
these means ± variance bands, so the values are a regression reference and not
a datasheet.

## 2. Like-for-like comparison

Rules:
- A comparison is only made where load, supply and the corner/temperature
  basis match closely enough. Anything else is **not comparable**, and the
  table says why.
- A source that reports a single typical point is compared with this block's
  **TT / 27 °C** point, not its worst case.
- This block's worst-case value over the 15 points is listed next to it so
  that the weaker rows stay visible.

This block's reference figures (all from record `20261001-074923-c317ff9`
unless another record is named):

| Row | TT / 27 °C / 1.80 V | Worst of 15 PVT points | Target status (`target-spec.md` §2) |
|---|---|---|---|
| Open-loop DC gain (1 Hz) | 65.82 dB | 61.64 dB @ FS / 125 °C | ≥ 60 dB, met everywhere |
| GBW into 2 pF | 22.51 MHz | 17.92 MHz @ SS / 125 °C | ≈ 16 MHz, met everywhere |
| Phase margin into 2 pF | 65.43° | 63.94° @ SF / 27 °C | ≥ 60°, met everywhere |
| Slew rate, rise (unity buffer, 2 pF) | 20.59 V/µs | 19.88 V/µs @ SS / −40 °C | ≈ 20 V/µs, met |
| Slew rate, **fall** (unity buffer, 2 pF) | 14.64 V/µs | **11.03 V/µs @ SS / −40 °C** | ≈ 20 V/µs, **partially closed (about 55 % of target at the worst point)** |
| Output swing (unity-buffer linear range) | 1.431 Vpp (79.5 % of VDD) | **0.948 Vpp (58.5 % of 1.62 V) @ SS / −40 °C** | ≈ 1.39 Vpp estimate, **unmet at the worst corner** |
| Quiescent current / power | 65.74 µA / 118.34 µW | 131.92 µW @ FF / 125 °C / 1.98 V | ≈ 128.7 µW, confirmed |
| PSRR+ (DC–1 kHz window minimum), record `20261009-073254-e06f2fc` | 67.72 dB | 63.57 dB @ FS / 125 °C | no own target (`[TBD]`) |
| PSRR− (DC–1 kHz window minimum), record `20261009-073254-e06f2fc` | 75.17 dB | **54.90 dB @ SS / −40 °C** | no own target (`[TBD]`) |
| CMRR @ 1 kHz, CM = 0.5·VDD, record `20261009-103006-566b9a5` | 71.15 dB | 55.11 dB @ SS / −40 °C | `[TBD]` |
| Input-referred noise @ 1 kHz, record `20261009-073753-e06f2fc` (**single corner only, not PVT evidence**) | 541 nV/√Hz | not measured (the 15-corner noise grid has no record) | no limit in spec |

Comparison per source:

| Source | Row | Source figure (conditions) | This block | Verdict |
|---|---|---|---|---|
| S1 | all AC / slew / Iq / swing rows | 3.3 V rail, ≤ 100 fF and 100 MΩ load, post-layout, min/typ/max over ss/tt/ff × −40/27/110 °C | 1.8 V, 2 pF, schematic, 15-point grid | **not comparable**: different supply class, a load 20× lighter, a different PM convention, and a summary statistic that is not a named point. Qualitatively, S1 leads on **evidence maturity**: it has layout, DRC/LVS and post-layout characterisation over corners, and this block does not have layout yet |
| S1 | swing | Vol 0.000 V / Voh 3.300 V into 100 MΩ (rail-to-rail driver) | 79.5 % of VDD at TT / 27 °C, 58.5 % at worst | **not comparable** (different rail, load and definition). This block's swing is plainly narrower than a rail-to-rail claim, which matches the "unmet" row in `target-spec.md` §2 |
| S2 | — | spec limits only, no results | — | **not comparable**: nothing measured to compare |
| S3 | DC gain | 60 dB, single point, corner and temperature not stated (committed deck: tt, no `.temp`, possibly ±1.8 V) | 65.82 dB (TT / 27 °C) | **partially comparable**: low-frequency gain does not depend on the capacitive load, but the supply is ambiguous. This block reports more gain at its typical point and also has a 15-point worst case (61.64 dB), which the source lacks |
| S3 | GBW, PM | 10 MHz, 80° into 10 pF with 3 pF Cc | 22.51 MHz, 65.43° into 2 pF | **not comparable** (load 5× heavier, different Cc) |
| S3 | slew | "9.06V/sec" (unit as written), 10 pF | 20.59 rise / 14.64 fall V/µs, 2 pF | **not comparable** (different load; unit and edge direction not stated) |
| S3 | power | 41 µW | 118.34 µW (TT / 27 °C) | **not comparable as a figure of merit** (different GBW·CL target and possibly a different supply). Stated anyway: this block draws more quiescent power |
| S3 | CMRR | 71 dB (frequency and CM point not stated) | 71.15 dB @ 1 kHz, CM 0.5·VDD (TT / 27 °C) | **not comparable** (source conditions not stated) |
| S4 | slew, closed loop | 5.80 rise / 1.3 fall V/µs, 25 pF, corner not stated | 20.59 rise / 14.64 fall V/µs, 2 pF, TT / 27 °C | **not comparable in magnitude** (12.5× heavier load, 12 pF Cc). Qualitatively both designs show the same **rise > fall asymmetry**, which fits this block's own diagnosis of a fixed-bias class-A sink and tail starvation (DR-007). This block's fall-slew gap is real and documented, not unique to it |
| S4 | gain / GBW / PM | plot only | — | **not comparable** (no numbers reported) |
| S5 | DC gain | 66.01914 dB at 10 Hz, tt, 25 °C, 1.8 V, extracted, bias optimised by the testbench | 65.82 dB at 1 Hz, TT / 27 °C, 1.80 V, schematic | **approximately comparable** (same supply and corner, 2 °C apart; S5's 10 Hz point is below its own reported `bw_3db` of 7962.968 Hz). The two are essentially at parity. Caveats: S5 is post-layout and its bias was optimised per run, while this block uses a fixed 5 µA reference |
| S5 | UGB, PM | 33.26 MHz, 62.0° at `cload=0` | 22.51 MHz, 65.43° into 2 pF | **not comparable** (unloaded vs 2 pF) |
| S5 | power | 546.5 µW total incl. output stage; 209.9 µW "two-stage" estimate (total minus a fixed 336.6 µW) | 118.34 µW (TT / 27 °C, whole block) | **not comparable** (S5 has an output stage, and its two-stage figure is an estimate, not a measurement) |

### What the comparison shows

- **No surveyed source can be compared like for like on the load-dependent
  rows (GBW, PM, slew).** None reports figures at 1.8 V into 2 pF. Most give
  a single unnamed corner, and one (S1) gives a sweep summary.
- Where comparison is possible (open-loop DC gain at the typical point), this
  block is **at parity** with S5 and above S3's reported 60 dB. That is not a
  performance claim: a 4–6 dB difference in DC gain says nothing about which
  design is better overall.
- **This block is not ahead on headline performance.** Its fall slew rate
  (11.03 V/µs worst) and output swing (0.948 Vpp, 58.5 % worst) do not meet
  their own targets. PSRR− drops to 54.90 dB at SS / −40 °C. The 15-corner
  noise grid is not recorded. There is no layout yet, whereas S1 has full
  post-layout characterisation.

## 3. Position

The differentiator is the **evidence chain**, not headline performance:

- **Every recorded figure has a PVT grid behind it.** All six `[P]` rows were
  measured at 15 points (5 corners × 3 temperatures, corner-paired `VDD`),
  and the worst case is reported next to the typical point. Of the sources
  surveyed, only S1 (CACE, 3 corners × 3 temperatures) reports corner results
  as numbers. S4 shows ff/ss results as plots only.
- **Append-only, citable records.** Each figure traces to a record id with
  its CSV, the rendered decks (`netlist-snapshots/<id>/`), raw ngspice logs,
  the PDK pin (open_pdks `c6d73a35f524070e85faff4a6a9eef49553ebc2b`) and the
  tool versions. Superseded sizings stay on file as baselines instead of being
  overwritten.
- **Contradictions are recorded, not hidden.** Hand estimates that simulation
  contradicted (GBW on the DR-002 sizing, fall slew, swing) are written up as
  findings. No target in `target-spec.md` was relaxed to make a result pass.
- **What this block does not yet have.** It has no layout, DRC/LVS or
  post-layout evidence, which S1 already shows. Until that exists, the
  evidence chain is complete only up to schematic level.

## 4. Method and limits of this survey

- Sources were found by GitHub repository search for "sky130 opamp" on
  2026-10-09 and read through the GitHub API at the pinned commit. Only text
  files (READMEs, CACE YAML/text, SPICE decks, JSON) were quoted. Values that
  appear only in images were not transcribed.
- Popularity, tapeout status and silicon results were not checked. None of
  the quoted figures is a silicon measurement.
- A source's own conditions are reported as its files state them. Where they
  are ambiguous (S3's supply, S1's `Cout` "maximum"), the ambiguity is stated
  here rather than resolved by assumption.
