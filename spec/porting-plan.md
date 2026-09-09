# Porting plan — what carries over from sky130-bandgap, sky130-ldo, and gf180-opamp

**Status: engineering input, not a ratified decision.** This document is the
required reading for anyone starting design work on this block once
[`target-spec.md`](target-spec.md)'s `[TBD]` rows start getting filled in. It
does not ratify anything itself — no decision record exists yet in this
repo — and it does not perform any circuit design, schematic capture, or
simulation; it only names the nearest mature siblings and what a two-stage
Miller-compensated op-amp on sky130 can and cannot borrow from them.

**This is a same-PDK port for the device menu, and a same-topology port for
the bench structure — but neither sibling is a standalone op-amp.**
`sky130-bandgap` and `sky130-ldo` are both on the identical sky130 PDK this
repo targets, so (unlike a cross-PDK port such as `sg13g2-bandgap`'s from
`gf180-bandgap`/`sky130-bandgap`) no device-menu, model-library, or
voltage-flavor-naming translation work is needed for the *process* itself.
`gf180-opamp`, conversely, is this exact block's own three-foundry twin
(`CLAUDE.md`: "identical bench structure to gf180-opamp and sg13g2-opamp") —
same topology and row set, different PDK. This plan therefore borrows device
menu and error-amplifier design precedent from the two same-PDK siblings, and
borrows structure (bootstrap-issue shape, target-spec table conventions,
gap-to-T1 tracker framing) from `gf180-opamp`, which underwent this identical
bootstrap pass (its own issue #2) first.

## Sources checked

- [`2AMLogic/sky130-bandgap`](https://github.com/2AMLogic/sky130-bandgap) —
  same-PDK, most mature block in the fleet on sky130 (layout-complete,
  DRC-clean, LVS-clean `mismatch_count: 0`, ratified target-spec — see its
  README, verified 2026-09-06). `design/error_amp.sch` + `.sym` are its
  error-amplifier sub-block — this repo's nearest same-PDK amplifier design
  precedent, and the deck/PVT-harness pattern (`sim/*-post-layout/` suites,
  `spec/decision-records/`) is the most mature in the fleet per the curated
  issue body.
- [`2AMLogic/sky130-ldo`](https://github.com/2AMLogic/sky130-ldo) — same-PDK.
  `design/ldo_3v3in_1v8out.sch` embeds a single-stage-OTA error amplifier
  (a current-mirror/"symmetric" OTA driving a common-source pass device with
  Miller-plus-nulling-resistor compensation) — this repo's second same-PDK
  amplifier design precedent, and [`spec/target-spec.md`](https://github.com/2AMLogic/sky130-ldo/blob/main/spec/target-spec.md)
  is the structural model this repo's own `target-spec.md` follows (DRAFT
  status, per-row `Src` citation, ratification gated on a dedicated issue).
  [DR-001](https://github.com/2AMLogic/sky130-ldo/blob/main/spec/decision-records/DR-001-pass-device-supply-framing.md)
  records that sibling's own pass-device-flavor decision — the precedent
  cited for this repo's 3.3 V I/O-flavor row in `target-spec.md`.
- [`2AMLogic/gf180-opamp`](https://github.com/2AMLogic/gf180-opamp) — the
  same block, different PDK (GF180MCU 3.3 V primary vs. this repo's sky130
  1.8 V primary). Its own bootstrap issue (#2) produced the identical
  three-artifact scaffolding this issue produces, and its
  [`spec/target-spec.md`](https://github.com/2AMLogic/gf180-opamp/blob/main/spec/target-spec.md)
  and [`spec/porting-plan.md`](https://github.com/2AMLogic/gf180-opamp/blob/main/spec/porting-plan.md)
  are the direct structural models for this repo's own two spec files —
  same row set, same value-tag convention, same "what carries
  over/changes/does not transfer" section shape (itself borrowed from
  `sg13g2-bandgap/spec/porting-plan.md`'s cross-PDK precedent).
- [`2AMLogic/klayout-tools`, `docs/design-evidence-tiers.md`](https://github.com/2AMLogic/klayout-tools/blob/main/docs/design-evidence-tiers.md) —
  the T1 ("sim-validated") checklist this plan's linked gap-to-T1 tracker
  surveys.

## 1. What carries over unchanged

Same PDK (for the device menu) plus an identical topology-and-row-set twin
(for the bench structure) means most of the *process* and *methodology*
transfer; only the *topology instance* is new (neither same-PDK sibling is a
standalone op-amp, and the twin is on a different PDK).

- **The verification discipline.** PVT-cornered testbenches (per
  `CLAUDE.md`: gain, GBW/PM into stated CL, slew, noise, offset with
  statistical basis, CMRR/PSRR, swing, power, at PVT corners), append-only
  `sim/` records, no claim without a testbench. Identical across every block
  in the fleet regardless of PDK or topology.
- **The friction protocol.** Tool gaps against `klayout-tools` get filed
  generically, design specifics stay out of that tracker. Unchanged by
  topology or PDK.
- **The sky130 device menu itself.** Because this is a same-PDK port (for
  devices), the 1.8 V-core MOS flavors (`nfet_01v8`/`pfet_01v8`) and the
  I/O-tolerant flavors (`nfet_g5v0d10v5`/`pfet_g5v0d10v5`) `sky130-bandgap`
  and `sky130-ldo` already characterize and use are the *same* devices this
  repo would use — no cross-PDK translation table is needed the way
  `sg13g2-bandgap`'s porting plan needed one to map gf180's/sky130's device
  menu onto SG13G2's genuinely different one. Device *numbers* (Vth, gm/ID
  sweeps, resistor sheet resistance) are not yet pulled into this repo — that
  is future device-characterization work — but the *menu* to characterize is
  already known and unchanged from the siblings, modulo the supply-voltage
  caveat in §2 below.
- **The 1.8 V-primary / 3.3 V-I/O-flavor-only-via-DR scope rule.**
  `CLAUDE.md`'s framing is the same shape of rule `gf180-opamp`'s own
  CLAUDE.md applies to its 3.3 V-primary/5 V-stretch split — not a new kind
  of decision this repo has to invent, just the same discipline applied at a
  different voltage.
- **gm/ID-first sizing.** `CLAUDE.md`'s "gm/ID first, committed before
  sizing" is the same practice both same-PDK siblings and the `gf180-opamp`
  twin already follow; nothing about a two-stage op-amp topology changes
  that ordering.
- **The bootstrap scaffolding pattern itself.** `gf180-opamp`'s own issue #2
  produced exactly these three artifacts (draft target-spec, porting plan,
  gap-to-T1 tracker) for the identical topology on a different PDK — this
  issue is a re-run of that same well-worn pattern, not a novel process.
- **The decision-record process itself**, once one is needed. No
  `spec/decision-records/` directory exists in this repo yet (this bootstrap
  pass makes no decisions requiring one). When the first real decision is
  made (e.g. picking a compensation scheme, or opening the 3.3 V I/O-flavor
  row), it should follow one of the two precedented conventions —
  `sky130-bandgap`'s `DR-NNN-<slug>.md` or `sg13g2-bandgap`'s
  `NNNN-<slug>.md` — picked once and kept consistent within this repo; the
  fleet has not converged on one, so neither choice is wrong. `sky130-ldo`
  also uses the `DR-NNN-<slug>.md` shape, which is the more common
  convention among this repo's actual same-PDK siblings.

## 2. What changes, and why

Both same-PDK siblings are a bandgap reference and an LDO — neither is an
amplifier-as-the-whole-block the way this repo is, and `sky130-bandgap`'s own
ratified spec runs at 3.3 V, not this block's 1.8 V-primary scope.

| Aspect | sky130-bandgap / sky130-ldo | sky130-opamp | Why it changes |
|---|---|---|---|
| What is being specced | An error amplifier *inside* a larger loop (bandgap reference loop; LDO regulation loop), specced only indirectly through the host block's own rows (PSRR, line/load regulation, output accuracy) | A standalone two-stage Miller-compensated op-amp, specced directly on its own classic rows (gain, GBW/PM into stated CL, slew, noise, offset, CMRR/PSRR, swing, power) | Neither sibling's spec table has an amplifier-level GBW/PM/slew/CMRR row at all — those rows do not exist to copy, only the host-level rows their amplifier subserves. This repo's row set instead matches its own three-foundry twin, `gf180-opamp`, which already originated this row set from the same `CLAUDE.md` framing on a different PDK. |
| Primary supply voltage | `sky130-bandgap`: 3.3 V ±10% (ratified). `sky130-ldo`: 3.3 V input / 1.8 V regulated output (ratified framing, DR-001) | 1.8 V ±10% primary, per this repo's own `CLAUDE.md` ("1.8 V primary; 3.3 V I/O-device flavor only via decision record") | Neither same-PDK sibling operates its core amplifier stage at this block's target 1.8 V-core rail — `sky130-bandgap`'s error amp and `sky130-ldo`'s OTA are both sized against a 3.3 V (or 3.3 V-input) operating point, using I/O-tolerant devices. This block's 1.8 V-core scope means its headroom budget, device flavor choice, and swing constraints must be re-derived, not copied — this is exactly the "headroom-driven divergence from the twins" `CLAUDE.md` and `README.md` flag as an expected, honestly-documented finding rather than an error. |
| Compensation | Sized against each host loop's own stability requirement (bandgap: a low-bandwidth reference node; LDO: an output pole set by the external cap per `sky130-ldo`'s Miller-plus-nulling-resistor compensation) | Miller compensation between the two gain stages, sized against a stated external `CL` per the twin-row convention — a different compensation topology and a different design freedom (no external LDO output cap or bandgap-loop pole to lean on) | This block's `CL` load-capacitance target (currently `[TBD]` in `target-spec.md`) plays a role analogous to `sky130-ldo`'s external output cap in that sibling's compensation sizing — but it has to be chosen for a general-purpose op-amp with no fixed downstream load, whereas both siblings' compensation targets are fixed by their host circuit's own known load. |
| Amplifier-characterization testbench shape | `sky130-bandgap`'s `design/error-amp-offset-budget.md` and `device-characterization-summary.md` characterize its error amp's offset contribution to the *host* loop's accuracy, not the amplifier's own open-loop gain/GBW/PM/CMRR/PSRR in a standalone test configuration; `sky130-ldo`'s OTA is likewise characterized only through the LDO's own line/load-regulation/PSRR rows | Needs the full classic-row testbench suite `gf180-opamp`'s own porting plan already scoped (open-loop AC sweep for gain/GBW/PM, transient step for slew, noise analysis, CMRR/PSRR AC sweeps, swing sweep, Iq measurement) | Neither same-PDK sibling ships a standalone open-loop-gain / GBW / phase-margin / CMRR / PSRR testbench for its embedded amplifier — those quantities are measured only at the host-block level. `gf180-opamp`'s porting plan already worked out this same gap for the identical topology on a different PDK; this repo inherits that testbench-shape conclusion rather than re-deriving it. |
| Input/output common-mode range | Bounded by each host circuit's own fixed internal nodes (e.g. an LDO error amp's inputs pinned to Vref and the feedback-divider tap) | Must be specified in general, since a standalone op-amp has no fixed host context — this is exactly the "swing" and "CMRR" rows in `target-spec.md` that neither same-PDK sibling's ratified table carries | A standalone amplifier's common-mode/output-swing spec is a first-class deliverable here; for both siblings it was an internal implementation detail of a larger loop, never separately specified or ratified. At a 1.8 V-core rail this row is expected to show the low-headroom trade explicitly, per `README.md`. |

## 3. What does not transfer, and why

- **Either same-PDK sibling's literal amplifier schematic.**
  `sky130-bandgap`'s `error_amp.sch` and `sky130-ldo`'s embedded OTA (inside
  `ldo_3v3in_1v8out.sch`) are each sized for a narrow, fixed internal role
  (correcting a bandgap core's PTAT/CTAT mismatch; driving a pass-FET gate
  inside a 3.3 V-input regulation loop) at a 3.3 V (or 3.3 V-input)
  operating point — neither is a general-purpose, standalone, 1.8 V-core
  two-stage Miller-compensated op-amp meant to drive an arbitrary external
  `CL`. Copying either schematic wholesale would inherit both a different
  supply-voltage headroom budget and sizing decisions made for a different
  design problem.
- **Either same-PDK sibling's host-level spec rows as this block's own
  rows.** `sky130-bandgap`'s PSRR row (measured at the bandgap's
  output-reference node, ratified `> 60 dB DC–1 kHz`) and `sky130-ldo`'s PSRR
  row (measured at the regulated output) are both *system*-level PSRR
  figures dominated by loop gain around the whole reference/regulation loop,
  not an *amplifier*-level PSRR figure measured open-loop or in a standard
  op-amp test configuration. This repo's PSRR row needs its own testbench
  definition, not a copy of either host-level number or test setup.
- **`sky130-bandgap`'s 3.3 V device-flavor choice as this block's default.**
  That sibling's ratified Supply row (3.3 V ±10%) uses sky130's I/O-tolerant
  device flavor as its *primary*, not a stretch — the opposite of this
  block's own 1.8 V-core-primary / 3.3 V-I/O-flavor-only-via-DR scope. The
  device *names* transfer (§1); the *choice of which is primary* does not.
- **`sg13g2-bandgap`'s cross-PDK device-selection decision records** (its
  DR-0001 bipolar-device-selection, DR-0002 supply-voltage-scope). Those
  exist specifically because SG13G2's device menu differs from gf180's/
  sky130's — a question this repo does not face for its device *menu*,
  since both same-PDK siblings are on the identical sky130 process. If this
  repo needs an early decision record, it is more likely to be about
  topology (output-stage class, cascode-vs-not) or the 3.3 V I/O-flavor
  scope, not device selection.
- **Either same-PDK sibling's own numeric mismatch/PVT evidence.** Any
  measured coefficient (`sky130-bandgap`'s box-method TC measurement,
  `sky130-ldo`'s dropout/headroom arithmetic) is specific to that circuit's
  own devices and operating point. Only the *practice* of measuring rather
  than assuming transfers, per `CLAUDE.md`'s "no claim without a testbench"
  — the numbers themselves do not.
- **`gf180-opamp`'s specific numeric target-spec proposals.** Its
  `target-spec.md` is a 3.3 V-primary DRAFT; every `[P]`/`[TBD]` row there
  reflects gf180mcu's device menu and 3.3 V headroom, not sky130's 1.8 V-core
  one. Only the row *set*, value-tag convention, and document *structure*
  transfer from that repo — no numeric value is copied across the PDK
  boundary.

## 4. Open items and next steps

- **Topology decision.** No same-PDK sibling's amplifier schematic transfers
  directly (§3), and this block's twin (`gf180-opamp`) has not yet made its
  own topology decision either (verified against that repo's own
  `porting-plan.md` §4, 2026-09-06) — so the first real design decision this
  repo needs is its own two-stage Miller-compensated topology choice
  (single-ended vs. fully differential first stage, output-stage class,
  cascode-or-not), sized for a 1.8 V-core headroom budget. Not yet made, and
  out of scope for this bootstrap pass.
- **Load capacitance (`CL`) target.** `target-spec.md`'s GBW/PM rows are
  stated "into stated CL" per the twin-row convention, but no CL value has
  been chosen yet — see §2's "Compensation" row above. Choosing one is part
  of the topology decision, not independent of it.
- **Device characterization — done.** `CLAUDE.md`'s "gm/ID first" ordering
  named this as the next concrete step after this bootstrap pass; it is now
  committed as
  [`sim/gm-id-characterization/`](https://github.com/2AMLogic/sky130-opamp/tree/main/sim/gm-id-characterization)
  (issue #6): gm/ID, gm/gds and fT vs overdrive for both `_01v8` polarities,
  over the confirmed corner grid below and a channel-length sweep from
  minimum length to 8x minimum — the same practice `sky130-bandgap` and
  `sky130-ldo` both already followed on this PDK (at their own, different,
  primary supply voltages). This is device-level input for a future sizing
  pass, not a topology choice or a filled-in `target-spec.md` performance
  row (both remain open below).
- **Corner-grid confirmation — done.** `target-spec.md` §1 flagged that
  `sky130-bandgap`'s ratified corner grid runs its devices at 3.3 V, not this
  block's 1.8 V-core primary. The corner *shape* (`tt, ff, ss, fs, sf`) has
  now been confirmed specifically for the `_01v8` (1.8 V-core) flavor
  against the pinned PDK checkout, by
  [`sim/gm-id-characterization/corners/model-files.json`](https://github.com/2AMLogic/sky130-opamp/blob/main/sim/gm-id-characterization/corners/model-files.json)
  (issue #6), which resolves each corner to its literal
  `sky130_fd_pr__{nfet,pfet}_01v8__<corner>.*.spice` model file — not
  assumed by analogy from the 3.3 V-primary sibling.
- **Gap-to-T1 tracker.** [#3](https://github.com/2AMLogic/sky130-opamp/issues/3),
  filed alongside this pass, tracks the block's current distance from the
  klayout-tools T1 ("sim-validated") design-evidence tier — every checklist
  item is currently unmet, since no schematic/layout/sim work has started.
  It is the natural place future passes record progress against items 1–10,
  the same way `gf180-opamp#7` and `sg13g2-bandgap#4` track their own
  repos' gaps. It also carries a review-bar note (one-command
  characterization + README reproducibility) that this bootstrap pass does
  not itself satisfy but names so it is not discovered late.
