# DR-011: Offset closure — matched-group sizing is insufficient; scope a technique study (proposed)

- **Status**: **proposed**. Drafted by the Builder agent for issue #144. It is
  not ratified, and **merging the PR that introduces this record does NOT
  ratify it**, DR-009, or any offset target (the DR-008 / DR-009 pattern: a
  merged copy that reads `proposed` means proposed). Ratification act: a
  separate, operator-approved PR that flips this Status line to `ratified`.
  A ratifying operator may instead pick a different next step.
- **Date**: 2026-10-10
- **Decided by**: Loom Builder agent, issue #144 (proposal only)
- **Related**: [`DR-009`](DR-009-offset-target.md) (proposed σ ≤ 0.275 mV;
  its "closing lever is not identified" open item is what this record
  addresses), [`DR-007`](DR-007-device-resize-gbw-slew-swing.md) (current
  sizing; the PMOS-group L = 0.3 µm phase-margin trade),
  [`DR-005`](DR-005-io-flavor-not-served.md) (3.3 V consumer position not
  served — unchanged by this record), issues #85, #107, #108, #120.

## Context

The N = 300 campaign (#85) measures an open-loop input-referred offset σ of
8.38–8.69 mV. Attribution (#107) puts 86 % of the variance in the PMOS mirror
XM3/XM4 (7.74 mV) and 14 % in the input pair XM1/XM2 (3.10 mV). DR-009
proposes σ ≤ 0.275 mV (the `sky130-bandgap` allocation, kept, not lowered) and
defers the closing lever to a later record. Issue #144 asked whether enlarging
the matched groups can plausibly close it while the ratified rows hold.

Evidence:
[`sim/offset-capability/records/campaign-20261010-sizing-feasibility.md`](../../sim/offset-capability/records/campaign-20261010-sizing-feasibility.md),
with its predeclared plan (committed before any fleet run), a single-corner
OP probe, exploratory Monte Carlo (N = 100, tt / 27 °C / 1.8 V per
candidate, batch fleet) and full 15-point fleet PVT records for three
grid-legal candidates and a grid-only reference.

Measured, against unchanged targets:

| candidate (W and L scaled) | matched gate area vs canonical | σ (mV), N = 100 | σ / 0.275 mV | worst PM (≥ 60°) | worst GBW (≈ 16 MHz) |
|---|---|---|---|---|---|
| canonical (#85, N = 300) | 1× | 8.58 | 31× | 63.9° | 17.9 MHz |
| m2p1: mirror ×2 (pair unchanged) | 1.5× | 4.25 | 15× | **54.1°** | 17.3 MHz |
| m2p2: mirror ×2, pair ×2 | 4.0× | 3.22 | 12× | **49.5°** | 17.5 MHz |
| m4p2: mirror ×4, pair ×2 | 5.9× | 2.34 | 8.5× | **27.1°** | **14.0 MHz** |

- **Mirror-only enlargement leaves the pair**: with the mirror term at
  zero, σ → σ_pair = 3.10 mV (2.85–3.36 mV at ±2 SE), **11.3× the
  allocation**; the pair alone needs ≥ 135× its area (114–158×).
- **Combined area needed**: ≈ **280–580× the canonical matched gate area**
  (≈ 4 800–10 000 µm²: the low end uses the Pelgrom hand-calc split, the
  central/high ends the #107 measured split ±2 SE; anchoring on the
  measured candidates gives ≈ 340–420×), plus XM6 growing in proportion
  (≈ 7 500–14 000 µm², tens of pF at the second-stage input). Estimate —
  the Pelgrom law is verified by the candidates only up to 6× area.
- **Cost already visible at 1.5–6× area**: phase margin fails the ratified
  ≥ 60° row at every candidate (worst SF / 27 °C), GBW falls below target at
  m4p2, rise slew and output swing regress slightly, the mirror Vsg grows by
  up to 107 mV out of the ICMR upper edge (estimate, tt). Gain improves.
- The gm/ID lever on the mirror (higher overdrive) is bounded at ≈ 2.8× and
  is paid in the same ICMR headroom.

## Decision

1. **Record as a quantified finding that matched-group sizing alone cannot
   meet the DR-009 proposed allocation on this topology at 1.8 V**: the
   required area is two to three orders of magnitude beyond the canonical
   sizing, and the measured phase-margin cost begins at the first ×4 mirror
   step.
2. **Propose no sizing candidate.** None of m2p1 / m2p2 / m4p2 is proposed
   for the canonical design; the canonical schematic and netlist are
   unchanged.
3. **Proposed next step: a separately scoped technique study** (a new
   issue, its own plan and record) comparing offset trim, chopping and
   auto-zeroing (or a consumer-side correction) for this block: residual σ
   achievable at N ≥ 300 + corners, area, power, ripple/noise, and impact on
   the ratified rows. Any adoption is its own design-driving decision record.
4. The DR-009 target, its statistical basis and its `proposed` status are
   **not changed**. The 3.3 V consumer position stays unserved (DR-005):
   reducing offset alone would not establish integration readiness.

## Alternatives considered

- **Propose m4p2 (or a larger step) as the next canonical sizing.** Not
  chosen: it remains 8.5× above the allocation and already fails phase
  margin and GBW at the measured corners.
- **Size up further with a compensation re-tune.** Not chosen as a closing
  path: a re-tune can recover some phase margin at GBW/slew cost, but cannot
  remove the ≥ 280× area requirement, which is set by mismatch statistics.
  It may still be a secondary knob inside the technique study.
- **Decouple XM6 from the mirror** (keep L = 0.3 µm, re-derive its W for the
  systematic offset). Not run: it breaks the preserved ratio the study
  bounded itself to, and it addresses only the stability cost, not the
  area requirement.
- **Lower the target or relax a ratified row.** Not permitted
  (`CLAUDE.md`); not done.
- **Run a full N ≥ 300 + corners campaign on the candidates.** Not chosen:
  the exploratory N = 100 already puts every candidate ≥ 7× above the
  target even at the 2-SE lower bound of its σ; a large campaign would add
  cost, not a different decision.

## Spec lines affected

None. `spec/target-spec.md` is unchanged (the offset row stays OPEN under
DR-003 with DR-009's proposed value). This record adds a proposed
disposition of DR-009's "closing lever" open item only.

## Consequences

- The offset gap is now characterised as a technique gap, not a sizing gap,
  with measured evidence; the gap-to-T1 tracker (#3) can cite it.
- The candidate netlists and records stay as evidence; they are not design
  inputs. The 0.005 µm grid snap of the MOS widths (grid0) is measured to be
  electrically invisible, which #120 may cite; this record does not choose
  #120's widths.
- Bad consequence: closing the offset row will need added circuitry (trim
  DAC or chopper switches and their control), which adds area, power and
  verification scope, and may need its own consumer conversation with
  `sky130-bandgap` about closed-loop vs open-loop offset.

## Open items

- The technique study itself (to be filed as a new issue).
- Closed-loop vs open-loop offset conversion for the bandgap use (DR-009).
- Temperature / VDD coverage of offset statistics (DR-009).
- ICMR bench on any future resized candidate (not run here).
- Ratification of this record and of DR-009, each by its own named act.
