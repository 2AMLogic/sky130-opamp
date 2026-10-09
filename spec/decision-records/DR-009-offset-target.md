# DR-009: Proposed input-referred offset target (consumer-derived, gap shown)

- **Status**: **proposed**. Drafted by the Builder agent for issue #108. It
  is not ratified. **Merging the PR that introduces this record (the
  issue #108 spec-reconciliation PR) does NOT ratify DR-009 or the offset
  target.** This follows the [`DR-008`](DR-008-cmrr-target.md) pattern, not
  the "Status-line wart" convention of DR-003/DR-005/DR-007: a merged copy
  of this record that reads `proposed` means proposed.
  **Ratification act:** a separate, later operator-approved PR whose only
  purpose is ratification. That PR flips this Status line to `ratified`
  and, in `spec/target-spec.md`, removes the "OPEN" notes on the
  input-referred offset row and in §5. An operator may instead rule in
  place of such a PR, but the ruling must still land as the same
  Status-line flip. Until that act the offset row stays **OPEN** under
  DR-003 and its value is a `[P]` proposal only. A ratifying operator may
  equally choose a different number or a different basis; this record does
  not pre-empt that choice.
- **Date**: 2026-10-09
- **Decided by**: Loom Builder agent, issue #108 (proposal only)
- **Related**: [`DR-003`](DR-003-target-spec-ratification.md) (left offset
  OPEN because no mismatch Monte Carlo pass existed),
  [`DR-004`](DR-004-consumers-section-and-integrator-view.md) (consumers
  section), [`DR-008`](DR-008-cmrr-target.md) (the pattern followed), issue
  #85 (the campaign), issue #107 (attribution of the measured sigma to
  device groups, open at the time of writing)

## Context

`spec/target-spec.md` §2 carried input-referred offset as `[TBD]` because no
mismatch Monte Carlo pass existed. Issue #85 has since run one: N = 300
samples per corner (3 chunks of 100, paired seeds) at TT, SS, FF and the
extra SF, FS corners, on the committed `opamp_core.spice`. The record is
[`sim/offset-capability/records/campaign-20261009-offset-mc300.md`](../../sim/offset-capability/records/campaign-20261009-offset-mc300.md),
with per-corner statistics in
[`20261009-154748-campaign-offset-mc300-final-5fbc07.campaign.json`](../../sim/offset-capability/records/20261009-154748-campaign-offset-mc300-final-5fbc07.campaign.json).
That record deliberately stops at measured data ("not a limit"). This
record turns it into a spec disposition.

Measured, all 300 / 300 samples ok at every corner, 0 failed (27 °C,
VDD = 1.8 V, open-loop):

| corner | sigma (mV) | 3 sigma (mV) | abs(mean) + 3 sigma (mV) |
|---|---|---|---|
| TT | 8.58 | 25.75 | 26.27 |
| SS | **8.69** | **26.08** | **26.59** |
| FF | 8.39 | 25.16 | 25.69 |
| SF | 8.38 | 25.15 | 25.65 |
| FS | 8.66 | 25.99 | 26.55 |

The one consumer that states an amplifier-offset number is
`sky130-bandgap`: an input-referred allocation of **≈ 0.275–0.369 mV σ** (by
temperature), derived as what is left after the fixed terms of its
output-accuracy row via a measured Kuijk offset gain of 9.65 (see the
Consumers section of `spec/target-spec.md`). `sky130-ldo` states no
amplifier-offset row. Against the bandgap allocation the measured sigma is
too large by a factor of about 23 (8.38 mV vs 0.369 mV) to about 32
(8.69 mV vs 0.275 mV).

## Decision

Proposed `spec/target-spec.md` §2 input-referred offset row:

- **Target: input-referred offset σ ≤ 0.275 mV, i.e. 3σ ≤ 0.825 mV `[P]`.**
  This is the **consumer-derived** number (the tighter end of the
  `sky130-bandgap` allocation range), **kept as the target**. It is **not**
  lowered or rounded to match the measurement.
- **Statistical basis: 3σ, mismatch MC N ≥ 300 + process corners `[P]`**,
  the basis the row already carried. The N = 300 per corner requirement is
  now met by the campaign; the basis itself stays proposed until
  ratification.
- **Status: measured; target proposed (DR-009), not ratified; not met.**
  The measured gap is shown in the row: σ 8.38–8.69 mV, worst 8.69 mV at
  SS / 27 °C, and 3σ 25.15–26.08 mV, against 0.275 mV and 0.825 mV.
- **The closing lever is not identified.** This record names no resize,
  topology change or trim as the fix. Issue #107 is the attribution of the
  sigma to device groups; until it lands, the gap is a finding, not a
  plan. Closing a gap of this size by sizing alone (offset sigma scales
  roughly with 1/sqrt(W·L) for a pair) would need a very large area or a
  different technique such as trim or chopping. That is a design-driving
  decision and needs its own record, not this one.

## Caveats carried from the campaign record

- **27 °C and 1.8 V only.** No temperature or VDD grid. Every figure here
  is a single-temperature, nominal-supply statistic.
- **Bracket ±30 mV.** The extremes (±27–28 mV) sit close to the sweep
  bracket. No sample failed the bracket check, but no tail beyond about
  3σ may be read from this bench without a wider bracket.
- **Open-loop definition of Vos:** V(inp) − V(inn) at the first rising
  v(out) = 0.9 V crossing, with 5 µA ideal Iref and 2 pF. This is not the
  closed-loop offset the bandgap sees; the conversion between the two is
  not established here.
- **Paired seeds.** The same sample index draws the same mismatch seed at
  every corner (Pearson correlation of Vos between corners 0.9989–0.9996),
  so the corner statistics are not independent estimates; the 8.38–8.69 mV
  spread is corner effect on the same draws.
- **Rz / Cc mismatch** is enabled by the `<corner>_mm` sections and its DC
  effect is argued negligible, not measured. The sigma is the inclusive
  reading.
- **Runner/client klt version mismatch** was warn-only and no effect was
  observed on the sampling path (campaign record).

## Alternatives considered

- **Leave the row `[TBD]` until attribution (#107) finishes.** Not chosen.
  The spec would keep claiming that no data exists.
- **Silently adopt 3σ ≈ 26 mV (or σ ≈ 8.7 mV) as the target.** Not chosen.
  That relaxes the spec to fit the result, which `CLAUDE.md` forbids, and
  it would leave the consumer mismatch hidden.
- **Propose a target at the measured value plus margin.** Not chosen, for
  the same reason: a target derived from the measurement it is graded
  against is not independent evidence.
- **Propose no number and record only the gap.** Not chosen. The row needs
  a basis to grade against, and the only consumer-derived one is the
  bandgap's.

## Spec lines affected

- `spec/target-spec.md` §2, **Input-referred offset** row: Target,
  Statistical basis, Binding corner and Status cells. `[TBD]` / `not
  started` becomes `σ ≤ 0.275 mV [P]` / `measured; target proposed
  (DR-009), not ratified; not met`.
- `spec/target-spec.md` §5, OPEN bullet, and the Consumers section's offset
  rows (`sky130-ldo` and `sky130-bandgap`): the "no mismatch MC pass
  exists" statements are replaced by citations of the campaign record,
  labelled as measured and, for the bandgap, as a gap.
- `manifests/spec-section2-figures.json` and
  `design/bin/spec_figures_check.py`: the cited offset figures are
  checked against the committed campaign summary.
- No other row changes. In particular, no ratified target is relaxed.

## Consequences

- Once ratified, the offset row binds and the current sizing does **not**
  meet it, by about 23–32× in sigma. A binding row that is unmet is a
  finding for the gap-to-T1 tracker, not a reason to relax it.
- The consumer comparison for `sky130-bandgap` moves from "unknown" to
  "not met, measured gap", with the caveats above (open-loop definition,
  27 °C only).
- The measured numbers are mechanically guarded: editing a cited offset
  figure in the spec without matching the committed campaign summary makes
  `design/bin/spec_figures_check.py validate` fail.

## Open items

- **Closing lever** (issue #107 and a later decision record).
- **Temperature / VDD coverage** of the offset statistics.
- **Closed-loop vs open-loop offset** conversion for the bandgap use.
- **Ratification** of this record, and therefore of the row, is the
  separate act named in the Status line. Merging the issue #108 PR is not
  that act.
