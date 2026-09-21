# DR-003: Target-spec table ratification pass 1 — thirteen rows ratified, four left explicitly open

- **Status**: **proposed** — a recommendation for two-key ratification via
  this PR (Judge review + Champion/operator merge), per the 2026-08-19
  canary spec/DR ratification-via-PR standing policy
  ([2AMLogic/2am#357](https://github.com/2AMLogic/2am/issues/357)) — the
  same path `sky130-comparator` used for its
  [`DR-002` ratification pass](https://github.com/2AMLogic/sky130-comparator/blob/main/spec/decision-records/DR-002-target-spec-ratification.md)
  (merged PR #29), which issue #26 names as this record's worked example.
  **Nothing here is binding until this PR merges.** Upon merge, the
  per-row dispositions in "Decision" below take effect exactly as stated —
  this is a **partial** ratification by design: 13 of the table's 17 rows
  (all five §1 operating-condition rows, plus §2's open-loop DC gain, GBW,
  phase margin, slew rate, input-referred noise, input common-mode range,
  output swing, and quiescent power) move DRAFT → RATIFIED; four rows
  (§2's input-referred offset, CMRR, PSRR, and area) stay OPEN,
  explicitly, not silently. No row's numeric value changes.
- **Status-line wart, stated rather than left to bite** (per #26's own
  scope note): merging this PR does **not** rewrite the `Status:` line
  above, so a merged copy of this record still reads `proposed` — the same
  wart `sky130-comparator`'s merged DR-002 carries. A future reader of a
  merged copy should treat the line above as a drafting artifact of the
  two-key mechanism: **once this PR is merged, the dispositions in
  "Decision" below are the ratified state of this table.**
- **Date**: 2026-09-21 (this ratification pass). The measured evidence it
  disposes is record `20260916-032327-edc9f22` (2026-09-16).
- **Decided by**: Builder agent, issue #26 — the drafting party only. Per
  the standing policy, the ratification act is the two-key approval of the
  PR carrying this record, not this record's authorship; this record does
  not ratify itself.
- **Supersedes**: none — third decision record in this repo. Does not
  supersede [`DR-001`](DR-001-topology-and-cl.md) or
  [`DR-002`](DR-002-device-sizing.md); those records' own status lines are
  untouched by this pass (see "Consequences").
- **Superseded by**: (none while this record stands)
- **Related**: #26 (this issue), #3 (gap-to-T1 tracker — its item 5 gate,
  "Full PVT corner simulation vs **a ratified spec**", is what this record
  unblocks partially; the tracker's item 5 row is updated by this pass,
  per #26's scope), #17 / PR #19 (the PVT testbench pass whose record is
  this ratification's primary evidence), #20 / PR #21 (the in-flight
  six-row measured-citation reconciliation — relationship stated in
  "Context" below), #10 / #13 / #16 (the sizing passes that produced the
  `[P]` values being ratified), #22 (the resize pass that would close the
  measured non-compliance recorded below), `spec/README.md` ("Spec changes
  require a decision record" — this is that record for the table's
  ratification status), `CLAUDE.md` (the no-relaxation guardrail this
  record is written under).

## Context

`spec/target-spec.md` has carried **Status: DRAFT** since its 2026-09-06
bootstrap (issue #2). That status is the gate the gap-to-T1 tracker (#3)
names twice: item 5 ("Full PVT corner simulation vs a ratified spec …
**requires the spec table itself to be ratified**") and, through it, items
6/7/8, which grade against the table's rows. Until the table binds, every
verdict against it is provisional by construction — the exact framing #26
files this issue under.

Two things exist now that did not exist at the bootstrap:

1. **Measured, PVT-cornered, circuit-level evidence.** Record
   [`sim/opamp-characterization/records/20260916-032327-edc9f22.md`](../../sim/opamp-characterization/records/20260916-032327-edc9f22.md)
   (issue #17 / PR #19) measures six of the §2 rows — open-loop DC gain,
   GBW, phase margin, slew rate (rise and fall), output swing, quiescent
   power — across the confirmed 5-corner × 3-temperature grid (45 ngspice
   runs, 0 failed, pinned PDK, rendered decks and per-run logs committed).
   Two rows confirm their `DR-002` estimates; four contradict some part of
   theirs — a contradiction reported, not softened, per this repo's
   "verification is the product" rule.
2. **Today's ratification mechanism ruling.** This repo has no
   `ratification/` two-key tree (a fleet-wide gap filed as
   [2AMLogic/product#135](https://github.com/2AMLogic/product/issues/135)),
   so this pass takes the standing policy's PR-based path #2: a Builder
   drafts the decision record as a PR recommending the dispositions, and
   the two-key mechanism evaluates it — Judge review plus
   Champion/operator merge.

**Relationship to #20 / PR #21, stated so nobody re-derives it.** #26's
own body calls #20's reconciliation "the input to this ratification, not
a substitute for it." That reconciliation's *evidence* — the committed
record above — is on `main`; PR #21 (its row-text edit) has been open and
blocked since 2026-09-16 (Doctor-cycle cap exhausted; a one-line residual
text fix awaiting a human). This record therefore cites the **committed
record directly**, which is the actual input; it does not wait on, redo,
or duplicate PR #21's *citation* pass. The two PRs touch disjoint parts of
`spec/target-spec.md` by design (this pass edits the header `Status`
bullet and appends a trailing ratification section; PR #21 edits the six
measured row lines, the `[P]`-tag cell, the Status-column paragraph, and
the note after the table), so they compose and rebase cleanly in either
merge order.

## Decision

Every row of [`spec/target-spec.md`](../target-spec.md) — §1's five
operating-condition rows and §2's twelve performance rows — receives
exactly one disposition below. **No numeric value anywhere changes.** For
rows the committed PVT record measures, the disposition cites the measured
grid; for rows without measured evidence, the disposition either ratifies
the value **as a target** (a binding commitment, explicitly *not* a "met"
claim) or leaves the row explicitly OPEN. Per #26's scope and
`CLAUDE.md`'s guardrail, no target is moved toward a measurement: the
ratified values are the pre-measurement sizing-pass values, verbatim.

### §1 rows — RATIFIED as-is (5 rows)

- **Supply voltage, VDD 1.8 V ±10% → 1.62–1.98 V** — RATIFIED unchanged.
  The 1.8 V primary framing is `CLAUDE.md`'s scope rule, and the committed
  PVT grid already exercises the stated supply points per corner
  (tt/sf/fs at 1.80 V, ss at 1.62 V, ff at 1.98 V, matching `DR-002`
  §(f)'s pairing). Grading caveat, carried honestly: VDD is *tied to*
  process corner in the committed grid, not independently swept at every
  corner (the record's "Does not" list names this).
- **Supply voltage, VDD (I/O-device flavor) 3.3 V — not opened** —
  RATIFIED as a scope statement: the row stays named-not-opened; opening
  it requires its own decision record per `CLAUDE.md`, never a silent
  addition.
- **Operating temperature −40…+125 °C** — RATIFIED unchanged (fleet
  convention, matching sky130-bandgap/sky130-ldo's ratified rows; the
  committed grid's −40 °C and 125 °C extremes are its endpoints).
- **Corner grid `tt, ff, ss, sf, fs` (1.8 V-core MOS)** — RATIFIED
  unchanged, as confirmed for the `_01v8` flavor against the pinned PDK
  checkout (issue #6,
  [`sim/gm-id-characterization/corners/model-files.json`](../../sim/gm-id-characterization/corners/model-files.json))
  and as exercised by the committed circuit-level grid. The R+C
  (resistor/capacitor process) axis is "typical" only in the committed
  evidence — an orthogonal, stated methodology choice (the record's
  `pdk.json` names it), not a ratified claim of R+C spread coverage.
- **Load capacitance, CL = 2 pF [DR-001]** — RATIFIED unchanged, carried
  from `DR-001`: every GBW/phase-margin/slew measurement in the committed
  record is taken into CL = 2 pF per its testbenches. Note: `DR-001`'s own
  status line remains `submitted for ratification` — this record ratifies
  the CL row *as it appears in this table* through this PR's two-key
  review; it does not edit `DR-001`'s line (see Open items).

### §2 rows — measured evidence (6 rows)

- **Open-loop DC gain — RATIFY ≥ 60 dB (stretch ≥ 65 dB) unchanged.**
  Measured across the full 15-point grid: 69.72–74.23 dB; the target is
  met at every point with ≥ 9.7 dB margin, and the stretch bound is also
  met everywhere (worst 69.72 dB > 65 dB). Measured worst point:
  **69.72 dB @ SS/125 °C**. The SS process family is confirmed as the
  binding corner family, but the measured temperature extreme reverses
  the table's SS/−40 °C prediction (71.43 dB measured there, 1.7 dB
  better) — gain falls with *increasing* temperature at every corner, a
  direction the hand estimate did not predict. The measured-vs-`DR-002`
  §(f) deltas at the three named points (tt/27 °C 72.22 vs. 74.2;
  ss/−40 °C 71.43 vs. 75.1; ff/125 °C 72.29 vs. 72.8) are recorded here
  without rounding them into a tolerance claim. **What is explicitly not
  decided here**: pre-layout AC bench only (no layout extraction, no
  Monte Carlo — MC is not applicable to a deterministic row), and the
  binding-corner *cell text* in the table stays for PR #21's in-flight
  reconciliation to update rather than being re-edited here.
- **GBW (into CL = 2 pF) — RATIFY ≈ 16 MHz unchanged, as a target the
  current design does *not* meet.** Measured worst case **8.45 MHz @
  SS/125 °C** (≈ 53% of target); even the row's own predicted binding
  point, SS/−40 °C, measures 9.56 MHz (~53% of `DR-002`'s 17.94 MHz hand
  estimate at that exact point); one grid point (FF/−40 °C, 16.36 MHz)
  reaches the target. Per `CLAUDE.md` the target is **not** lowered to
  match the measurement — this row is ratified as a binding target with
  the measured non-compliance recorded against it, exactly the
  pattern `sky130-comparator`'s DR-002 applied to its Kickback row
  (ratify the bound unchanged; document the design as non-compliant;
  recommend the follow-on design pass as future work). The compliance
  path is the resize pass (#22 — currently `loom:blocked` behind #20 /
  PR #21) or, if a corrected target is ever justified on engineering
  grounds, an explicit superseding decision record — never a silent edit
  or a measurement-matching relaxation.
- **Phase margin (at GBW, same CL) — RATIFY ≥ 60° unchanged.** Measured
  grid 64.09°–73.36°; target met at every point, smallest margin 4.09°
  (SF/27 °C). The stretch clause ("≥ 45° at the FF/hot corner if 60° is
  unreachable there") stands ratified as written and was never exercised —
  the measured FF/125 °C point (65.98°) is above 60° anyway. The measured
  worst corner (SF, essentially flat across temperature) revises the
  table's FF/125 °C prediction — again recorded here, cell-text update
  left to PR #21.
- **Slew rate — RATIFY ≈ 20 V/µs unchanged, with the hand estimate's
  implicit rise/fall symmetry made an explicit part of the ratified
  row: both the 20%–80% rise and the 80%–20% fall transit, per the
  committed bench's measurement convention, must meet it.** Measured:
  rise SR 16.88–19.69 V/µs grid-wide (worst SS/125 °C, ≈ 84% of target);
  fall SR 1.73–15.72 V/µs — the commit's single most actionable finding:
  **fall SR at SS/−40 °C measures 1.73 V/µs — under 9% of the unchanged
  20 V/µs target, and ≈ 10% of the 17.26 V/µs rise SR at that same
  point** (1.7306/17.2561 = 10.0%, per the committed tran-sr CSV) —
  varying ~9× across the grid. The
  design is ratified-non-compliant on the falling edge at cold/slow
  corners (and marginally under on rise at its worst corner). Target not
  lowered; root-cause diagnosis is explicitly out of scope here (the
  record's README carries the qualitative `M7` fixed-sink hypothesis and
  its own "does not diagnose" note); the compliance path is #22 or a
  superseding record, same as GBW.
- **Output swing — RATIFY ≈ 1.39 Vpp (≈ 86% of the 1.62 V worst-case-low
  rail; i.e. ≈ 0.072–1.464 V) unchanged, as a target the current design
  does *not* meet at the worst corner.** Measured: the predicted binding
  corner **is confirmed** (SS/−40 °C is the narrowest swing in the grid)
  but the magnitude is contradicted — **0.855 Vpp (52.8% of rail, window
  0.328–1.184 V) at that exact corner, ≈ 61% of `DR-002`'s 1.392 Vpp
  (1.464 − 0.072) estimate magnitude** (0.8555/1.392 = 61.3%, per the
  committed dc-swing CSV). Target not lowered. Grading definition
  stated for the future bench reader: the committed evidence measures
  this row as the **unity-buffer closed-loop compliance swing** (the
  record's README states plainly that both input-pair common-mode
  compliance and output-stage saturation can bound it — whichever binds
  first), not an open-loop output-stage-only swing; a layout-era or
  application-specific swing bench may legitimately need to separate
  those two mechanisms.
- **Quiescent power — RATIFY ≈ 128.7 µW at the 1.98 V binding corner /
  ≈ 117.0 µW at nominal 1.8 V unchanged, with the measured confirmation
  attached.** Measured: **130.71 µW @ FF/125 °C/1.98 V** — both the
  predicted binding corner and the magnitude confirmed (+1.6% vs. the
  estimate); nominal TT/27 °C measures 116.27 µW (−0.6% vs. the 117.0 µW
  figure); measured Iq ranges 59.67–66.01 µA across the grid, bracketing
  the `DR-002` §(a) 65 µA budget at every corner except SS (which runs
  2–5 µA lower — benign, and in the better direction). The measured
  deltas (−0.6%, +1.6%) are recorded here as facts; this record does not
  convert them into a ratification tolerance.

### §2 rows — target-only ratification (2 rows)

- **Input-referred noise — RATIFY AS TARGET: ≈ 30 nV/√Hz thermal floor,
  band 100 Hz–1 MHz.** No measured evidence exists — no `.noise` testbench
  is committed anywhere in `sim/`, the gm/ID sweep characterizes DC
  operating points only, and flicker (1/f) is entirely uncharacterized on
  this PDK's committed data. Per #26's scope this row is ratified as a
  **target**: the value binds as what the design must meet; **no "met"
  claim is made or implied**, and grading this row against the band's
  integrated-number convention will require the noise bench named in Open
  items.
- **Input common-mode range — RATIFY AS TARGET: ≈ 0.888–1.024 V (≈ 136 mV
  window) at the worst-case corner.** No direct measurement exists: the
  committed dc-swing bench measures closed-loop compliance, and its README
  states explicitly that this is *not* an ICMR measurement (its own
  tt/27 °C linear region, 0.178–1.491 V, is markedly wider than this
  row's estimated window and flags the discrepancy as future-bench
  material). The value binds as the input range the design commits to
  covering; the row's recorded finding (the window sits above mid-rail,
  traced to `DR-001`'s NMOS-input-pair / PMOS-mirror choice meeting
  sky130's PMOS threshold magnitude, with `DR-002`'s `gm/ID = 12.5 V⁻¹`
  alternative knob) carries unchanged, as does the row's own rule that
  reopening `DR-001`'s input-pair polarity requires a **new** decision
  record superseding `DR-001` — never a silent edit.

### §2 rows — left OPEN, explicitly (4 rows)

- **Input-referred offset — OPEN.** `[TBD]`: no numeric bound has ever
  been proposed for this row, so there is no value to ratify — and
  inventing one now would be ratifying a placeholder, which #26 forbids
  ("a partial ratification is legitimate and preferable to a false one").
  The `[P]` *statistical basis* ("3σ, mismatch MC N≥300 + process
  corners", convention carried from sky130-bandgap's ratified table) stays
  **proposed methodology**, not ratified: no mismatch Monte Carlo evidence
  exists (gap-to-T1 tracker item 6). Closing this row needs a mismatch MC
  pass or PDK mismatch-model data, then a follow-on ratification pass.
- **CMRR — OPEN.** `[TBD]`, and no committed bench: CMRR needs a
  common-mode AC testbench, which does not exist yet.
- **PSRR — OPEN.** `[TBD]`, and no committed bench nor any
  supply-voltage-sweep axis anywhere in the committed device data (the
  gm/ID README confirms "no 'supply corner' for a two-terminal-bias
  bare-device sweep"). A supply-AC bench (and, for the real part, a bias
  generator to do the rejecting) is a prerequisite.
- **Area — OPEN.** `[TBD]`, correctly so: area is a post-layout quantity;
  no `layout/` exists (gap-to-T1 items 2–4/7 remain wholly outstanding).

## Alternatives considered

- **Install the fleet `ratification/` two-key tree first and route
  ratification through it** (the 2AMLogic/product#135 fleet-wide ask;
  repo-local equivalent
  [sg13g2-comparator#19](https://github.com/2AMLogic/sg13g2-comparator/issues/19))
  — not chosen: the tree does not exist here today, #26's own body names
  the ratification-via-PR path as the mechanism that "works today with no
  scaffold change", and the standing policy (2AMLogic/2am#357) recognizes
  the PR path as this repo's available two-key act. Installing the tree
  remains open fleet work; nothing here forecloses it.
- **Wait for PR #21 to merge before ratifying anything** — not chosen:
  the *evidence* PR #21 reconciles by citation has been on `main` since
  2026-09-16, and PR #21 itself has been blocked for the same period on a
  residual one-line text fix after its Doctor-cycle cap was exhausted.
  Ratifying from the committed record does not depend on #21's textual
  pass landing first, and this record is shaped (see "Spec lines
  affected") so the two PRs compose in either merge order. The block this
  issue unblocks (T1 item 5) is the block's critical path; serializing
  behind a parked PR would deadlock the two on each other.
- **Full ratification: fill the four `[TBD]` rows with fresh proposals
  and ratify all 17** — not chosen for offset/CMRR/PSRR/area: there is no
  measured evidence behind any proposed number for those rows, so
  ratifying one would be coining spec on speculation — the exact "false
  ratification" #26 prefers an honest OPEN to (the offset row has, as
  yet, not even a value to ratify).
- **Lower the contradicted targets (GBW, fall slew rate, output swing) to
  the measured values** — rejected outright by `CLAUDE.md` ("agents do
  not relax a ratified spec to make results pass") and by this issue's
  own framing; recorded here so the rejection is a documented decision
  rather than an omission. The measured non-compliance is the design's
  problem to fix (#22), not the spec's problem to absorb.

## Spec lines affected

`spec/target-spec.md` only, and there only:

- the header `- **Status**: …` bullet: **DRAFT → RATIFIED (partial)**, with
  the per-row counts and a pointer to this record;
- a new trailing section ("Ratification status") appended after §4
  Sources, carrying the per-row disposition map so a reader of the table
  can tell ratified from open without opening this record;
- **no row line, no Target/Stretch/Statistical-basis/Binding-corner/Status
  cell, and no `[P]`/`[TBD]` tag cell is edited.** That is deliberate:
  PR #21 (open, blocked) already edits the six measured row lines, the
  `[P]`-tag cell, the Status-column paragraph, and the note following the
  table; the two PRs' diffs are disjoint, so they rebase cleanly in either
  order, and no row-text edit made here can drift from #21's in-flight
  wording.

Plus this new file itself, the tracker-comments on #3 (no repo-tree edit),
and nothing under `design/`, `sim/`, `layout/`, or `measurements/`.

## Consequences

- **T1 tracker item 5 unblocks partially, not wholly.** The
  "requires the spec table itself to be ratified" clause of #3 item 5 is
  satisfied for 13 of 17 rows once this PR merges; the checkbox stays
  unchecked (per #3's own acceptance criteria — items 5/6 require the
  table ratified *with real numeric rows* and matching PVT/MC evidence;
  the four OPEN rows carry no numbers, and no Monte Carlo evidence exists
  yet). #3's item 5 row is updated by this pass to say exactly that.
- **Verdicts now bind.** Per-row pass/fail verdicts (Judge review,
  characterization report, design-challenge evidence cites) against the
  13 ratified rows are verdicts against a *binding* spec, not a draft —
  and the guardrail runs the other way now too: with rows ratified, any
  future relaxation requires a superseding decision record, never a quiet
  edit. The measured-non-compliant rows (GBW 8.45 MHz worst vs. 16 MHz;
  fall slew 1.73 V/µs worst vs. 20 V/µs; output swing 0.855 Vpp worst vs.
  1.39 Vpp) are now *binding obligations with recorded standing
  violations* — which is the honest state: the design chain (#22 resize,
  gated on PR #21) has something concrete to close.
- **№ tests or benches change.** Grading continues against identical
  numbers: no testbench, harness, script, or committed record value is
  touched (verified: no code under `sim/` or `design/` asserts on
  `target-spec.md` values — every reference is prose). The committed
  45-run grid grades six of the ratified rows as-is.
- **`DR-001` and `DR-002` status lines unchanged.** `DR-001` remains
  `submitted for ratification` (its CL row, as carried into this table, is
  ratified here via this PR's two-key review; promoting the record's own
  line is fleet convention work not assigned to #26 — see Open items).
  `DR-002` remains `proposed` — and this record gives it no comfort: four
  of its six estimates are now measured-contradicted (some severely), and
  the resize pass (#22) or its superseding successor will render parts of
  it historical.
- **PR #21's rebase gets a one-line rewording, not a conflict**: its
  in-flight text says the table "stays DRAFT" — after this PR merges that
  phrase becomes historical (the ratification *dispositions* are DR-003's,
  which #21 never touches). Whoever unblocks #21 applies that wording fix
  at rebase; no row-content conflict exists (see "Spec lines affected").
- Bug consequence, accepted: a ratified-but-partially-unmeasured table is
  a target table that *some* rows will keep failing against until the
  design passes land; anyone reading "RATIFIED" as *"the amp passes its
  spec"* would be wrong, which is why the header, the trailing section,
  and every per-row disposition here repeat the distinction explicitly.

## Open items

- **Offset / CMRR / PSRR**: the three bench passes that would give those
  rows numbers (mismatch Monte Carlo — which is also gap-to-T1 item 6 —
  common-mode AC, supply-AC), then a follow-on ratification pass for them
  (a DR-004-class record).
- **Noise bench**: thermal + flicker characterization to turn the
  ratified-as-target ≈ 30 nV/√Hz row into a graded one.
- **ICMR-specific bench**: an input-side common-mode sweep to grade the
  ratified target window (and to resolve the compliance-vs-ICMR
  discrepancy the committed record's README already flags).
- **Area**: any time after layout exists (nothing to do until then).
- **The compliance gap itself**: #22 (resize pass, currently
  `loom:blocked` behind #20/PR #21) is the standing vehicle for closing
  GBW / fall-slew / swing; its results then need a fresh PVT record and a
  reconciliation pass, at which point the ratified targets become
  gradeable as met.
- **Aggregate characterization report** (gap-to-T1 item 8) and the
  one-command regeneration (item 11): now have a ratified table to cite.
- **`DR-001`'s own status-line promotion** (fleet convention work; this
  record deliberately does not edit another record's status line).
- **The status-line wart on this record itself**: unchanged by
  construction (see the Status bullets above); if the fleet later
  standardizes a merge-time status flip, this record is a candidate, and
  until then its own text says what it becomes.
- **Full supply × corner × temperature cross** (the committed grid ties
  VDD to corner) and an **R+C-corner spread** axis: both named in the
  committed record's "Does not" list; ratification here neither claims
  them nor removes them from future grading scope.
