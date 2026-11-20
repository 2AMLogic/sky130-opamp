# DR-018: Noise-row graded quantity — sampled input-referred floor over 100 kHz – 10 MHz

- **Status**: **proposed** — a recommendation for two-key ratification via
  this PR (Judge review + Champion/operator merge), per the standing
  spec/DR ratification-via-PR policy
  ([2AMLogic/2am#357](https://github.com/2AMLogic/2am/issues/357)), the same
  path [`DR-003`](DR-003-target-spec-ratification.md) used. **Nothing here is
  binding until this PR merges.** Upon merge, the "Decision" below takes
  effect exactly as stated: it is the ratification act for this record, and
  the graded quantity it names becomes the binding reading of the noise row.
  *(Status-line wart, per DR-003's own precedent: merging does not rewrite
  this line, so a merged copy may still read `proposed` — treat that as a
  drafting artifact of the two-key mechanism, not as "still open".)*
- **Date**: 2026-11-19
- **Decided by**: Loom Builder agent, issue #274 (the drafting party only —
  this record does not ratify itself). The graded-quantity selection it
  carries is issue #274's **2026-11-18 decision block** (option "floor",
  auto-selected under `--yolo 70`, confidence 75% — a recorded decision, not
  an operator ruling); this record submits that selection for the
  repository's ordinary DR ratification, per the issue's own Builder scope.
- **Supersedes**: none. Does not change any ratified value: the 30 nV/√Hz
  figure and the 100 Hz – 1 MHz band stay exactly as [`DR-003`](DR-003-target-spec-ratification.md)
  ratified them.
- **Superseded by**: (none)
- **Related**: [`DR-003`](DR-003-target-spec-ratification.md) (ratified the
  noise row *as a target* and left the graded quantity undecided
  explicitly), issue #274 (this record's issue, with the 2026-11-18 decision
  block and the committed-data figures below), #54 (the PSRR/noise benches),
  #246 / PR #275 (the item 5 envelope-export machinery this grading rides),
  #3 (T1 tracker, item 5), #287/#350/#352 (open spec PRs holding DR-015/016/017
  — this record takes the next free number).

## Context

`DR-003` ratified the input-referred-noise row as a target — "≈ 30 nV/√Hz
thermal floor, band 100 Hz – 1 MHz" — and said outright that "grading this
row against the band's integrated-number convention will require the noise
bench". The bench exists since #54, and a committed 15-corner `klt sim`
noise envelope exists
(`sim/opamp-characterization/records/20261030-050623-0fa5c15-950b9f-noise.klt.json`),
but it carries no `limits` and no `spec_row`, so item 5 carries input-referred
noise as a declared gap: DR-003 never fixed **which number is graded**. The
row names a spot thermal floor *and* a band; those are different measurable
quantities and they grade differently.

The committed October record makes the choice consequential — every candidate
reading fails at most or all corners, so the convention decides the recorded
finding (all figures read from that record, 15 corners):

| Quantity (as the bench already computes it) | Range over 15 corners | TT / 27 °C | vs the row's 30 nV/√Hz |
|---|---|---|---|
| White floor: min spot density, 100 kHz – 10 MHz | 28.19 – 47.25 nV/√Hz | 35.75 | ≤ 30 at 4 of 15 corners (tt, ff, sf, fs at −40 °C only) |
| Band-integrated, 100 Hz – 1 MHz | 62.49 – 82.19 µVrms | 70.11 | a flat 30 nV/√Hz over the band integrates to 30.0 µVrms; measured is 2.1 – 2.7× that |
| Spot density at 100 Hz (band low edge) | 1386 – 1704 nV/√Hz | 1500 | ~50× |
| Spot density at 1 MHz (band high edge) | 35.69 – 53.21 nV/√Hz | 42.42 | above 30 at every corner |
| 1/f corner | 285 – 681 kHz | 442 kHz | flicker dominates most of the ratified band |

Issue #274's 2026-11-18 decision block selected the **floor** option. This
record carries that selection into the spec; the expected result is a graded
failing row recorded as a finding — not a met row, and not a threshold edit.

## Decision

**The input-referred-noise row is graded as the minimum input-referred spot
noise density over the bench's reported spot frequencies from 100 kHz through
10 MHz, inclusive — bounded ≤ 30 nV/√Hz at every corner.** Specifically:

- **Quantity**: `min` of the noise bench's **reported** spot densities (the
  4-points-per-decade sample of the `dec 20` grid, indices 120–160 — nine
  spots at 100, 177.8, 316.2, 562.3 kHz, 1, 1.778, 3.162, 5.623, 10 MHz).
  Units V/√Hz. The graded population is the **nine reported spots only**:
  reducing over all 41 underlying sweep samples would silently change the
  population this decision names, and the reported spots are what the
  committed CSV publishes, so the graded number stays recomputable from the
  record alone.
- **Bound**: ≤ 30 nV/√Hz (30e-9 V/√Hz), **inclusive** — a floor exactly at
  the bound passes. This is `DR-003`'s ratified figure, unchanged, attached
  natively as the envelope measurement's `limits.max` with
  `spec_row: "input_referred_noise"`, so the envelope itself records
  per-corner pass/fail and the binding corner, and `klt signoff` derives
  item 5's row coverage from it. A graded measurement with no value (missing
  or invalid data) fails its corner — missing data can never grade a pass.
- **Grid**: the 15-point corner-paired PVT grid (tt/ff/ss/sf/fs ×
  −40/27/125 °C, VDD paired per DR-002 §(f)) — the same grid the noise bench
  already sweeps.
- **The 100 Hz – 1 MHz band still applies to the separate integrated-noise
  result** (`vn_int_band`), which remains an ungraded diagnostic, as do the
  individual spot densities and this reduction's pairwise helper values.

Implementation: `SPEC_NOISE_FLOOR_MAX_V_RTHZ` and
`noise_floor_measurements()` in
`sim/opamp-characterization/bin/psrr_noise_sweep.py`, with the bound-equality
and population tests in `tests/test_psrr_noise_sweep.py` as the
no-relaxation guard. The reduction is expressed natively (ngspice `let`
expressions, pairwise `0.5*(a+b−abs(a−b))` minima over the reported spot
`let`s) — no tool gap needs filing.

## Alternatives considered

- **Band-integrated input-referred noise, 100 Hz – 1 MHz** — the "integrated
  number" `DR-003` mentioned. Rejected as the graded quantity: it measures
  flicker-dominated in-band energy (2.1 – 2.7× the 30.0 µVrms flat-band
  equivalent at every corner), not the thermal floor the row names, and would
  need its own derived bound — a second spec number this record would have to
  invent. It stays the ungraded diagnostic.
- **Spot density at 100 Hz** — the band's low edge, ~50× over at every
  corner: it grades the flicker region, not the floor. Rejected.
- **Spot density at 1 MHz** — above 30 nV/√Hz at all 15 corners: fails
  everywhere by construction and is fragile to grid placement (a
  single-frequency read at one sample of a dec grid). Rejected: the weakest
  defensible statement about a *floor*.
- **Maximum spot over the band, equivalently a per-spot ceiling** — grades
  closed-loop peaking above the floor, the opposite reduction of what the row
  names; also fails warm-only regions far harder than the floor itself.
  Rejected.
- **Minimum over all 41 underlying sweep samples in 100 kHz – 10 MHz** —
  same shape as the chosen quantity but a different population, reading
  marginally below the published curve. Rejected: the graded number must be
  recomputable from the committed CSV's reported spots (see Decision).
- **Leave the row a declared gap** — rejected: DR-003 explicitly deferred
  grading to "the noise bench", the bench exists, the decision block settled
  the quantity, and an ungraded ratified row keeps item 5 partially
  unverifiable for no tooling reason.

## Spec lines affected

- `spec/target-spec.md` §2, **Input-referred noise** row: gains the graded
  quantity (this record) as its grading reference and its measured status.
- `spec/target-spec.md` §2a, the input-referred-noise derivation caveat:
  gains the link to this record for how the row is graded.
- `manifests/sky130-opamp.json` `spec_rows."5"`, `input_referred_noise`:
  declared gap → graded row cited on the noise envelope.

## Consequences

- **The expected result is a recorded finding, not a met row.** On the
  committed October record the sampled floor meets 30 nV/√Hz at 4 of 15
  corners (tt, ff, sf, fs at −40 °C) and fails warm — worst 47.25 nV/√Hz at
  SS / 125 °C / 1.62 V, nominal TT / 27 °C at 35.75 nV/√Hz. A fresh campaign
  on the current DUT establishes the result of record; the October numbers
  are a comparison point only. Neither the bound nor this convention may be
  tuned to change that (CLAUDE.md); closing a failing floor is design work
  (topology/bias), explicitly out of scope here.
- `klt sim`'s noise request gains one graded measurement (`en_floor`) with
  pairwise ungraded helper lets; **neither PSRR request gains any grading**.
- Item 5's declared-gap set shrinks by one (noise becomes a graded,
  currently-failing row); item 5 stays `unmet` while the row fails — that is
  the honest machine-readable statement, per the manifests README's finding
  convention.
- The warm corners' flicker rise is *not* penalized by this reading: the
  window (100 kHz – 10 MHz) sits above the measured 1/f corner (285 – 681
  kHz) at every corner, so the graded quantity is the white floor the row
  always named, not an in-band flicker number.

## Open items

- **Ratification itself** — this record is `proposed`; the two-key merge of
  the PR carrying it is the act that makes the convention binding.
- **A graded integrated-noise convention** (the 100 Hz – 1 MHz number) is
  *not* decided here. `vn_int_band` stays a diagnostic; if a consumer ever
  imposes an integrated requirement, that needs its own record with its own
  derived bound.
- **Closing the failing corners** is design work (bias/topology), not a spec
  change; nothing in this record pre-commits a sizing pass.
