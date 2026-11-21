# DR-015: Proposed PSRR target

- **Status**: **proposed**. Drafted by the Builder agent for issue #282. It
  is not ratified. **Merging the PR that introduces this record (the
  issue #282 spec-reconciliation PR) does NOT ratify DR-015 or the PSRR
  target.** This follows [`DR-008`](DR-008-cmrr-target.md) and
  [`DR-009`](DR-009-offset-target.md) rather than the "Status-line wart"
  convention of [`DR-003`](DR-003-target-spec-ratification.md),
  [`DR-005`](DR-005-io-flavor-not-served.md) and
  [`DR-007`](DR-007-device-resize-gbw-slew-swing.md), under which approving
  the PR that carries a record is its ratification
  ([2AMLogic/2am#357](https://github.com/2AMLogic/2am/issues/357)). The
  issue #282 PR is a spec *reconciliation* plus a *proposal*, not a
  ratification PR. A merged copy of this record that reads `proposed`
  therefore means proposed. It is not a drafting artifact.
  **Ratification act:** a separate, later operator-approved PR whose only
  purpose is ratification. That PR flips this Status line to `ratified`,
  and in `spec/target-spec.md` it removes the "OPEN" note on the PSRR row
  and in §5. An operator may instead rule on it in place of such a PR, but
  that ruling must still land as the same Status-line flip. Until that
  act, `spec/target-spec.md`'s PSRR row stays **OPEN** under DR-003, and
  its value is a `[P]` proposal only.
- **Date**: 2026-11-14
- **Decided by**: Loom Builder agent, issue #282 (proposal only)
- **Related**: [`DR-003`](DR-003-target-spec-ratification.md) (left PSRR
  OPEN because no supply-AC bench existed),
  [`DR-008`](DR-008-cmrr-target.md) (the CMRR precedent this record's form
  and reasoning follow),
  [`DR-013`](DR-013-grid-legal-mos-widths.md) (the sizing that was
  measured), issue #54 (the benches and the first, DUT-unverified record),
  issue #104 (the clarification record that forbids back-filling DUT
  provenance), issue #282 (this spec reconciliation)

## Context

`spec/target-spec.md` §2 carried PSRR as `[TBD]` / "not started". The reason
given was that PSRR is a supply-to-output small-signal transfer function and
that the committed gm/ID device sweep has no supply-voltage axis at all, so
there was no device-level basis to size the row from. DR-003 therefore left
the row OPEN.

Issue #54 has since built the two supply-AC benches
(`sim/opamp-characterization/testbench/psrr_vdd.cir`, `psrr_vss.cir`): an AC
1 V source in series with the respective rail, the amplifier in unity-gain
buffer, PSRR(f) = −gain(f) from that rail to the output. Both run the same
5-corner × 3-temperature grid as the other campaigns, with the same
corner→VDD pairing (tt/sf/fs 1.80 V, ss 1.62 V, ff 1.98 V).

**Why this record cites a new run rather than issue #54's.** Issue #54's
record `20261009-073254-e06f2fc` carries `"dut": null` — it predates the
runner's DUT snapshot capture — and
`sim/opamp-characterization/records/20261009-200000-ca03ee8-dut-identity-clarification.md`
(issue #104) states that such a record is UNVERIFIED and that no hash may be
back-filled onto it, "because either would manufacture provenance the run did
not capture". It also predates `DR-013`'s grid-legal widths (DR-013 is dated
2026-10-11; `e06f2fc` is 2026-10-09), and `design/netlist/opamp_core.spice`
did change between the two commits. So the old record could not bind a claim
to the netlist this spec describes, by inspection and by rule.

Issue #282 therefore re-ran both benches on the batch fleet against the
current netlist. The result is
[`sim/opamp-characterization/records/20261114-032827-96d9fbc-288af8-psrr-noise.json`](../../sim/opamp-characterization/records/20261114-032827-96d9fbc-288af8-psrr-noise.json),
with data in `-psrr-vdd.csv` and `-psrr-vss.csv`. Both benches report
`status: pass`, 15/15 corners, 0 failed (batch jobs `klt-sim-98f59c885da6`
and `klt-sim-cbeb5c357c71`; runner klt 0.9.0, `runner_compatibility: match`;
ngspice 47). Its `dut.sha256` is
`e954d17d085642d1d384694fc3c7799382b6d9ea777b650d60e6125fe918ce79`, equal to
the committed `design/netlist/opamp_core.spice`, so the figures below are
mechanically bound to the current DUT — `design/bin/spec_figures_check.py`
re-derives them from the CSVs on every CI run and reports them among the
figures "verified against the canonical DUT".

Measured worst case of `psrr_window_min_db` (the record's own DC–1 kHz window
minimum; larger is better), 15 points per polarity:

| Polarity | Worst over DC–1 kHz | Binding corner | Points < 60 dB | Points < 55 dB |
|---|---|---|---|---|
| PSRR+ (`psrr_vdd`) | **63.57 dB** | FS / 125 °C (VDD = 1.80 V) | 0 / 15 | 0 / 15 |
| PSRR− (`psrr_vss`) | **54.90 dB** | SS / −40 °C (VDD = 1.62 V) | 2 / 15 (SS / −40 °C 54.90, SS / 27 °C 58.65) | 1 / 15 |

- **Both polarities are flat across the window**, so the window figure *is*
  the DC figure: PSRR− within 0.0001 dB and PSRR+ within 0.07 dB of the
  0.1 Hz value at every one of the 15 points.
- **The two polarities bind at opposite ends of both axes.** PSRR+ is worst
  at FS / 125 °C and PSRR− at SS / −40 °C; the gap between the two worst
  cases is 8.7 dB. Neither polarity is a usable proxy for the other.
- **The DUT-unverified issue-#54 record agrees to within 0.002 dB** at every
  one of the 30 points (max |Δ| 0.0019 dB on `psrr_vdd`, 0.0006 dB on
  `psrr_vss`). The DR-013 width change is grid-legality rounding at the 1 nm
  level (W 4.634 → 4.635 µm, 7.819 → 7.820 µm, Rz L 9.763 → 9.765 µm), so
  the agreement is the expected outcome, not a surprise. It is stated here
  as a cross-check, and because this record's value does not rest on it:
  the re-run is what binds the claim.
- **Outside the window the polarities diverge sharply, and PSRR+ is the one
  that falls.** PSRR+ crosses 60 dB at **14.8–28.0 kHz** at every corner
  (log-interpolated on the 20-points-per-decade grid) and reaches
  **26.05–29.57 dB at 1 MHz**; PSRR− stays above 60 dB out to
  **0.74–3.54 MHz** at 13 of the 15 points — the two exceptions are the two
  SS points that are already below 60 dB at DC. This is why the proposed
  band stops at 1 kHz, and it is a finding for any consumer with ripple
  above the window (see Open items).

## Decision

Proposed `spec/target-spec.md` §2 PSRR row:

- **Target: PSRR ≥ 50 dB, DC – 1 kHz `[P]`.** Graded as the worst case over
  **both** supply polarities across the full 15-point PVT grid — 30 points.
  Measured worst case: 54.90 dB (PSRR−, SS / −40 °C), which leaves 4.9 dB of
  margin. PSRR+'s own worst case is 63.57 dB (FS / 125 °C).
- **Stretch: ≥ 60 dB `[P]`.** Met at all 15 PSRR+ points. Not met on PSRR−
  at SS / −40 °C (54.90 dB) or SS / 27 °C (58.65 dB); met at the other 13,
  so 28 of the 30 points.
- **Statistical basis: deterministic corner worst case.** This is
  nominal-device PSRR only. Mismatch-driven PSRR is not covered. See Open
  items.

**One combined bound, not a PSRR+ / PSRR− split.** The row states a single
figure graded over both polarities, for three reasons.

1. **No consumer imposes a polarity-split row.** The only PSRR row in
   `spec/target-spec.md`'s Consumers section is `sky130-bandgap`'s ratified
   `PSRR > 60 dB DC–1 kHz` (its DR-006), and that is a *whole-loop*
   requirement on the bandgap, which
   `sim/opamp-characterization/README.md` already records as **not an
   allocation to this amplifier**. Deriving a PSRR+ row from it would assert
   an allocation that nobody has made.
2. **A second, + specific number would have no anchor but the measurement
   itself.** At ≥ 60 dB it would carry 3.6 dB of pre-layout margin against
   effects that can only lower PSRR — thinner than the ≈ 5 dB DR-008 judged
   necessary for the same kind of row.
3. **The asymmetry is recorded, not hidden.** The row prints both polarity
   worst cases, both binding corners and the 8.7 dB gap, and the manifest
   binds *both* figures (`manifests/spec-section2-figures.json`,
   `s282-psrr-vdd` / `s282-psrr-vss`), so a future change that degrades
   either polarity trips `spec_figures_check.py` whether or not the combined
   floor is crossed.

The 50 dB figure is set below the measured worst case rather than at it, on
DR-008's reasoning: the bench omits the bias generator's supply path (ideal
`ibias` source) and the netlist is pre-layout, and both omissions can only
lower a real PSRR. 50 dB is also the same floor DR-008 proposes for CMRR, in
the same band, on the same grid, so the two supply/common-mode rejection rows
read alike rather than differing for no recorded reason.

## Alternatives considered

- **Leave the row `[TBD]`.** Not chosen. Both benches exist and have a full
  current-DUT grid, so `[TBD]` would understate the evidence the T1 item 5
  grader reads.
- **Target at the measured worst case (≈ 55 dB).** Not chosen. Rounded to
  55 dB it is in fact **already unmet** — the measured PSRR− worst case is
  54.90 dB, 0.10 dB below it — and set exactly at 54.90 dB it would leave
  zero margin against the two omissions named above. PSRR− is also within
  3.7 dB of 55 dB at a second point (SS / 27 °C, 58.65 dB), so such a floor
  would sit one corner away from binding two points rather than one.
- **Separate PSRR+ ≥ 60 dB and PSRR− ≥ 50 dB.** Not chosen, for the three
  reasons under Decision. It is the alternative a ratifying operator is most
  likely to prefer if a consumer later imposes a supply-rejection figure on
  the amplifier specifically, and both figures are already bound in the
  manifest, so adopting it later needs only a row edit — no new measurement.
- **≥ 60 dB as the combined target.** Not chosen. It would be unmet at 2 of
  30 points under the current sizing, so adopting it would be a
  design-driving decision (it needs a first-stage / tail-impedance change on
  the PSRR− path at SS), not a reconciliation. It is kept as the stretch and
  remains open to the ratifying operator.
- **Extend the band above 1 kHz.** Not chosen. PSRR+ crosses 60 dB at
  14.8–28.0 kHz and decays ≈ 20 dB/decade above that, so any band reaching
  into the tens of kHz would set a materially different number and would
  need its own consumer-driven justification. DC–1 kHz is the band the one consumer PSRR row names and
  the band the record's own `psrr_window_min_db` column computes.
- **Grade PSRR− only (it is the binding polarity).** Not chosen. It would
  leave PSRR+ with no recorded floor at all, which is the polarity the one
  existing consumer requirement is about.

## Spec lines affected

- `spec/target-spec.md` §2, **PSRR** row: Target, Stretch, Binding corner
  and Status cells. `[TBD]` / `not started` becomes
  `PSRR ≥ 50 dB, DC – 1 kHz [P]` /
  `measured; target proposed (DR-015), not ratified`.
- `spec/target-spec.md` §5, OPEN bullet: notes the benches, the current-DUT
  re-run and this proposal. PSRR stays OPEN.
- `manifests/spec-section2-figures.json`: two `scope: "current"` figures and
  their two matrices, so both printed numbers are machine-checked against
  the cited record on every CI run.
- No other row changes. In particular, no ratified target is relaxed, and the
  issue-#54 record is left byte-identical.

## Consequences

- Once this record is ratified, the PSRR row binds. The current DR-013
  sizing meets it at every one of the 30 grid points. That claim rests on
  schematic-level simulation only (R+C typical, pre-layout) with an ideal
  `ibias` source.
- A future resize, or a topology change through a DR superseding DR-001,
  must re-run both issue-#54 benches on the new DUT and keep the worst case
  over both polarities ≥ 50 dB. Because both figures are bound in
  `manifests/spec-section2-figures.json`, a re-run that moves either number
  fails CI until the row is re-authored — the row cannot drift silently.
- The target is derived from the measurement it is graded against, so
  meeting it is not independent evidence of good design. It records a floor
  that future changes must not cross. A reviewer should read it that way.
- This record does **not** change `manifests/integrator.json` or any
  Consumers-section verdict. The bandgap's 60 dB remains a whole-loop
  requirement for the bandgap to evaluate, and that consumer runs the
  amplifier at 3.3 V on thick-oxide devices — a rail this block does not
  serve (`DR-005`), so its verdict for that edge stays "not met (different
  contract)" regardless of these figures.

## Open items

- **Mismatch PSRR is not covered.** The corner grid models no device
  mismatch, and mismatch in the input pair and mirrors couples supply
  movement to the output. A statistical PSRR figure would need the mismatch
  Monte Carlo pass (issue #52 / gap-to-T1 item 6). This record proposes no
  statistical basis for it.
- **Post-layout PSRR is not measured**, because no layout exists. Supply-rail
  IR drop, well/substrate coupling and package or board impedance are all
  absent from these figures and all act to lower them.
- **The bias generator's supply path is not in the bench.** `ibias` is an
  ideal current source, so the real reference's own supply sensitivity is
  excluded. On a block whose `ibias` comes from a resistor-referenced
  generator this term can dominate PSRR in the window.
- **PSRR above the window is uncovered, and PSRR+ is the weak side there.**
  PSRR+ crosses 60 dB at 14.8–28.0 kHz and is down to 26.05–29.57 dB at
  1 MHz. A consumer with switching ripple above ≈ 15 kHz is not covered by
  this row, and the row does not imply it is.
- **No consumer imposes a PSRR row on this amplifier.** `sky130-bandgap`'s
  `PSRR > 60 dB DC–1 kHz` is a loop-level row on the bandgap, not an
  amplifier allocation (see the Consumers section of
  `spec/target-spec.md`), so the 50 dB figure is not consumer-driven. If an
  allocation is ever made, the "separate PSRR+ / PSRR− bounds" alternative
  above becomes the preferred form.
- **Ratification** of this record, and therefore of the row, is the separate
  ratification act named in the Status line: an operator-approved PR that
  flips this Status line to `ratified` and removes the PSRR "OPEN" notes in
  `spec/target-spec.md`. Merging the issue #282 PR is not that act.
