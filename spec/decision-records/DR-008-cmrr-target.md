# DR-008: Proposed CMRR target

- **Status**: **proposed**. Drafted by the Builder agent for issue #66. It
  is not ratified. Under the 2026-08-19 canary spec/DR ratification-via-PR
  standing policy
  ([2AMLogic/2am#357](https://github.com/2AMLogic/2am/issues/357)), the
  ratification act is a separate operator approval of this record. Until
  that approval, `spec/target-spec.md`'s CMRR row stays **OPEN** under
  [`DR-003`](DR-003-target-spec-ratification.md), and its value is a
  `[P]` proposal only.
- **Date**: 2026-10-09
- **Decided by**: Loom Builder agent, issue #66 (proposal only)
- **Related**: [`DR-003`](DR-003-target-spec-ratification.md) (left CMRR
  OPEN because no common-mode bench existed),
  [`DR-007`](DR-007-device-resize-gbw-slew-swing.md) (the sizing that was
  measured), issue #53 (the bench and record), issue #66 (this spec
  reconciliation)

## Context

`spec/target-spec.md` §2 carried CMRR as `[TBD]`. The reason given was
that the gm/ID device sweep cannot characterize common-mode-to-differential
conversion and that no common-mode AC bench existed. DR-003 therefore left
the row OPEN. Issue #53 has since built that bench and run it over the full
5-corner × 3-temperature grid on the committed DR-007 netlist. The result is
[`sim/opamp-characterization/records/20261009-103006-566b9a5`](../../sim/opamp-characterization/records/20261009-103006-566b9a5.md),
with data in `-cmrr.csv`. The bench measures `CMRR(f) = Adm(f) − Acm(f)` from
two amplifier instances in one deck, at two DC common-mode points: 0.5·VDD,
and 0.956 V, the centre of the ratified 0.888–1.024 V ICMR target window. The
record does not grade CMRR because the row has no target. This record
proposes one.

Measured values, read from `20261009-103006-566b9a5-cmrr.csv` (30 points):

| CM point | Worst CMRR (1 Hz and 1 kHz) | Points below 60 dB | Points below 50 dB |
|---|---|---|---|
| 0.5·VDD (mid-rail) | **55.11 dB @ SS / −40 °C** (VDD = 1.62 V, Vcm = 0.81 V) | 2 / 15 (SS / −40 °C 55.11, SS / 27 °C 58.40) | 0 / 15 |
| 0.956 V (target-window centre) | **69.34 dB @ FS / 125 °C** | 0 / 15 | 0 / 15 |

- CMRR is flat over the proposed band. At every point the 1 Hz, 1 kHz and
  10 kHz values agree within 0.001 dB, and 100 kHz is within 0.03 dB. At
  1 MHz the CSV shows changes from 0.90 dB *higher* to 2.39 dB *lower* than
  1 Hz; the largest drop is at SS / 27 °C, window centre. The record's prose
  says "<= 0.4 dB lower at 1 MHz", which its own CSV does not support. That
  is why this record limits the target band to DC – 1 kHz and does not
  rely on the 1 MHz figure.
- The ICMR bench in the same record gives an independent check, because it
  uses a different loop (output held at mid-rail) and a local DC sensitivity.
  Its mid-rail DC CMRR at SS / −40 °C is 54.94 dB, 0.17 dB below the AC
  bench's figure at the same point.
- The same record's 50 dB ICMR sensitivity columns show that local DC CMRR
  is at least 50 dB over the whole 0.888–1.024 V target window at all 15
  points. The highest 50 dB low edge is 0.8009 V and the lowest 50 dB high
  edge is 1.1311 V.
- The worst mid-rail point is at a common-mode voltage *outside* the
  ratified ICMR window. At SS, VDD/2 = 0.81 V, which is below the 0.888 V
  window edge. This is why mid-rail CMRR is weakest there.

## Decision

Proposed `spec/target-spec.md` §2 CMRR row:

- **Target: CMRR ≥ 50 dB, DC – 1 kHz `[P]`.** It is graded as the worst
  case over the full 15-point PVT grid at **both** recorded common-mode
  points (0.5·VDD and the 0.956 V window centre). The spot frequencies are
  1 Hz and 1 kHz, and 1 kHz is the comparison frequency named in the bench
  README. Measured worst case: 55.11 dB (mid-rail, SS / −40 °C), which
  leaves 5.1 dB of margin. At the window centre the worst case is 69.34 dB
  (FS / 125 °C).
- **Stretch: ≥ 60 dB `[P]`.** The current sizing does not meet it at
  mid-rail SS / −40 °C (55.11 dB) or SS / 27 °C (58.40 dB). It is met at
  the other 28 of 30 points, including every window-centre point.
- **Statistical basis: deterministic corner worst case.** This is
  nominal-device CMRR only. Mismatch-driven CMRR, which is usually the
  dominant term in silicon, is not covered. See Open items.

The 50 dB figure is set below the measured worst case rather than at it,
for two reasons. First, the two independent methods disagree by about
0.2 dB at the binding point. Second, the post-layout and mismatch effects
listed below can only lower CMRR. A 50 dB floor is also consistent with the
block's own ICMR definition. ICMR is defined by a 40 dB local-CMRR edge, and
the 50 dB sensitivity band already covers the target window at every point.

## Alternatives considered

- **Leave the row `[TBD]`.** Not chosen. The bench exists and has a full
  grid, so `[TBD]` would understate the evidence that the T1 item 5 grader
  reads.
- **Target at the measured worst case (≈ 55 dB).** Not chosen. It leaves
  essentially no margin (0.11 dB at 55 dB), and the ICMR-bench cross-check
  already reads 0.17 dB lower at the same point.
- **≥ 60 dB as the target.** Not chosen as the target. It is a common
  textbook figure for a two-stage Miller OTA and is kept as the stretch.
  As a target it would be unmet at 2 of 30 points under the current
  sizing. Choosing it would be a design-driving decision (it would need a
  first-stage tail-impedance change), not a reconciliation. It remains
  open to the ratifying operator if a consumer needs it.
- **Grade only at the window centre (≥ 65 dB).** Not chosen. It would hide
  the weaker mid-rail behaviour, and mid-rail is the bias point most users
  assume. Grading at both points is the conservative choice.

## Spec lines affected

- `spec/target-spec.md` §2, **CMRR** row: Target, Stretch, Binding corner
  and Status cells. `[TBD]` / `not started` becomes `≥ 50 dB [P]` /
  `measured; target proposed (DR-008), not ratified`.
- `spec/target-spec.md` §5, OPEN bullet: notes the bench and this proposal.
  CMRR stays OPEN.
- No other row changes. In particular, no ratified target is relaxed.

## Consequences

- Once this record is ratified, the CMRR row binds. The current DR-007
  sizing meets it at every grid point. That claim rests on schematic-level
  simulation only (R+C typical, pre-layout).
- A future resize, or a topology change through a DR superseding DR-001,
  must re-run the issue #53 CMRR bench at both CM points and keep the
  worst case ≥ 50 dB.
- The target is derived from the measurement it is graded against, so
  meeting it is not independent evidence of good design. It records a
  floor that future changes must not cross. A reviewer should read it that
  way.

## Open items

- **Mismatch CMRR is not covered.** Real CMRR is usually limited by
  input-pair and mirror mismatch, which the corner grid does not model. A
  statistical CMRR figure would need the mismatch Monte Carlo pass
  (issue #52 / gap-to-T1 item 6). This record proposes no statistical
  basis for it.
- **Post-layout CMRR** is not measured, because no layout exists.
- **No consumer imposes a CMRR row.** Neither sky130-ldo nor sky130-bandgap
  does (see the Consumers section of `spec/target-spec.md`), so the 50 dB
  figure is not consumer-driven.
- **Ratification** of this record, and therefore of the row, is a separate
  operator step that this record does not perform.
