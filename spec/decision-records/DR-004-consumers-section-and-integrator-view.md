# DR-004: Consumers section and machine-parseable integrator view (editorial, additive-only)

- **Status**: **proposed** — an editorial record, carried for ratification
  via this PR (Judge review + Champion/operator merge) per the 2026-08-19
  canary spec/DR ratification-via-PR standing policy
  ([2AMLogic/2am#357](https://github.com/2AMLogic/2am/issues/357)); the same
  path DR-003 used. **Nothing here is binding until this PR merges.**
  Status-line wart, stated rather than left to bite (same as DR-003's):
  merging this PR does not rewrite the line above, so a merged copy of this
  record still reads `proposed` — treat it as a drafting artifact of the
  two-key mechanism.
- **Date**: 2026-09-22
- **Decided by**: Builder agent, issue #31 — the drafting party only. The
  ratification act is the approval of the PR carrying this record.
- **Supersedes**: none — fourth decision record in this repo. Does not
  touch DR-001/DR-002/DR-003.
- **Superseded by**: (none while this record stands)
- **Related**: #31 (this issue), #3 (gap-to-T1 tracker), #26 / DR-003 (the
  ratified rows the Consumers verdicts compare against), #22 (the resize
  pass that will drift them), [2AMLogic/2am#899](https://github.com/2AMLogic/2am/issues/899)
  (reuse rule 9 and its 2026-09-21 same-PDK widening),
  [sky130-ldo#123](https://github.com/2AMLogic/sky130-ldo/issues/123) and
  [sky130-bandgap#286](https://github.com/2AMLogic/sky130-bandgap/issues/286)
  (the consumers' own ends of the edge).

## Context

`2am/repos.yml` records `consumes: [sky130-opamp]` on `sky130-ldo` and
`sky130-bandgap` (read live 2026-09-22), and reuse rule 9 makes that edge a
recorded fact on both ends — but nothing in this repo named either consumer:
an integrator evaluating this block as a replacement for its own in-tree
amplifier could not tell from here what those consumers require, what shape
their current blocks are, or what this block delivers as importable
artifacts. Issue #31 is this repo's end of that edge.

## Decision

1. `spec/target-spec.md` gains a `## Consumers` section naming exactly
   `sky130-ldo` (pinned `a0ff95b`) and `sky130-bandgap` (pinned `4ac0c24`),
   with per-consumer requirement rows (port list, rails, input range, speed
   GBW/SR, offset, noise, area budget — plus Iq where the consumer's table
   carries it), each citing its source or reading "Unknown" with a one-line
   reason, each carrying a met / not-met / unknown verdict against the
   DR-003-ratified rows at a stamped commit, and one "not the same block"
   line per consumer describing the in-tree amplifier's shape by name.
2. The integrator view publishes as structured data at a fixed path,
   **`manifests/integrator.json`** — a new sibling file, *not* an extension
   of the graded `manifests/sky130-opamp.json`: top cell, port list,
   netlist path, GDS path, measured area, maturity rung, spec status,
   consumers. Absent values (`gds`, `area_um2`) are explicit `null` plus a
   note, never omitted. `README.md` carries one pointer line to it.

**Additive-only: zero §1/§2 row values change.** The spec edit appends a
section; `git diff` shows no edit to any existing target row, ratified or
open.

## Alternatives considered

- **Extend `manifests/sky130-opamp.json` with the integrator fields** — not
  chosen: that file is the `klt signoff`-graded input whose render CI
  byte-compares against the committed verdict-of-record; `klt signoff`'s
  tolerance for extra top-level keys is unverified (no statement found in
  klayout-tools `docs/cli/signoff.md`, 2026-09-22), and coupling
  integrator-facing data to the graded artifact would make every
  integrator-data edit a signoff event. A sibling file the grader never
  reads avoids both.
- **README prose as the carrier** — not chosen: the issue explicitly
  rejects prose (a full-chip integrator measured what prose costs — a
  floorplan budget wrong by 10× on the first block read). README gets one
  pointer line to the fixed path only.
- **No decision record** — not chosen: `CLAUDE.md` routes spec changes
  through `spec/` with a record, and this edit adds a section to a
  (partially) ratified document; a short editorial record naming the
  additive-only scope is the safe reading of that norm, and cheap.

## Spec lines affected

- **No §1/§2 target row is touched** — zero row-value changes, by design.
- New: `## Consumers` section in `spec/target-spec.md` (appended after §5).
- New file: `manifests/integrator.json`.
- One pointer paragraph added under `README.md`'s "Target specification"
  section.
- `manifests/sky130-opamp.json` and `manifests/sky130-opamp.signoff.json`
  are untouched — the CI signoff byte-compare is unaffected by this PR.

## Consequences

- An integrator can now answer "what does this block deliver, and what do
  its consumers need" from this repo alone: the fixed-path JSON carries the
  import facts, the Consumers section carries the requirement rows and
  verdicts, and each consumer's own adopt-or-record tracker item
  (sky130-ldo#123, sky130-bandgap#286) carries the consumer-side answer.
- The honest verdicts are mostly **not met / unknown today**: both
  consumers' amplifier positions are 3.3 V-rail (this block's ratified
  scope is 1.8 V-primary; the 3.3 V I/O flavor stays named-not-opened), the
  bandgap's ≈ 0.73 V sense nodes sit below this block's ratified ICMR
  window, and this block's offset/CMRR/PSRR/area rows are OPEN. That is the
  correct current answer to the adopt/keep question, not a gap in the
  record.
- Verdicts are commit-stamped on both sides, so they drift detectably: when
  #22's resize lands, or a consumer moves its pinned commit, every
  met/not-met verdict needs re-evaluation — the stamps are what make that
  re-evaluation findable.
- This repo sets the fleet-first pattern for rule 9 (the gf180-opamp twin
  has no Consumers section or integrator view — verified live 2026-09-22),
  so its shape will be copied; wrong or uncited rows here would mislead an
  integrator's adopt/keep decision, which is why every row cites its source
  or reads "Unknown" with a reason.

## Open items

- The 3.3 V I/O-device flavor remains named-not-opened (§1); both
  consumers' rails verdicts can only flip via a future decision record
  opening it — deliberately out of scope here.
- This block's input-referred offset, CMRR, PSRR, and area rows stay OPEN
  (DR-003); the corresponding consumer-verdict rows stay **unknown** until
  those benches exist (gap-to-T1 tracker #3, items 5–6).
- `gds` and `area_um2` in `manifests/integrator.json` stay explicit `null`
  until layout exists; when it does, both the JSON and this record's
  consumers' area rows need updating in the same pass.
- The consumers' own evaluations (their #123 / #286) are theirs to answer;
  this record only guarantees their questions are answerable from here.
