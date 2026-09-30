# DR-005: 3.3 V I/O-device flavor not served — no 3.3 V-rail amplifier position

- **Status**: **proposed** — a declining record, carried for ratification via
  this PR (Judge review + Champion/operator merge) per the 2026-08-19 canary
  spec/DR ratification-via-PR standing policy
  ([2AMLogic/2am#357](https://github.com/2AMLogic/2am/issues/357)); the same
  path DR-003/DR-004 used. **Nothing here is binding until this PR merges.**
  Status-line wart, stated rather than left to bite (same as DR-003/DR-004's):
  merging this PR does not rewrite the line above, so a merged copy of this
  record still reads `proposed` — treat it as a drafting artifact of the
  two-key mechanism.
- **Date**: 2026-09-23
- **Decided by**: Builder agent, issue #36 — the drafting party only. The
  ratification act is the approval of the PR carrying this record; that is
  where an Option 1 ("open the flavor") vs Option 2 ("decline") ruling
  actually lands. If the ratifying reviewer wants Option 1 instead, this PR
  is declined and #36 is re-scoped into an epic.
- **Supersedes**: none — fifth decision record in this repo. Touches no prior
  record; it answers DR-004's Open-items bullet "the 3.3 V I/O-device flavor
  remains named-not-opened … both consumers' rails verdicts can only flip via
  a future decision record opening it" by recording the standing answer.
- **Superseded by**: (none while this record stands)
- **Related**: [#36](https://github.com/2AMLogic/sky130-opamp/issues/36)
  (this issue — the tracker item this record closes),
  [#31](https://github.com/2AMLogic/sky130-opamp/issues/31) /
  [DR-004](DR-004-consumers-section-and-integrator-view.md) (the Consumers
  section whose Rails verdicts point here),
  [2AMLogic/2am#899](https://github.com/2AMLogic/2am/issues/899) /
  [`REUSE.md`](https://github.com/2AMLogic/2am/blob/main/REUSE.md) rule 9
  step 4 ("a requirement the sibling does not meet gets filed on the
  sibling"),
  [sky130-ldo#123](https://github.com/2AMLogic/sky130-ldo/issues/123) (the
  consumer-side evaluation; its "kept" answer is **pending** on open
  [PR #137](https://github.com/2AMLogic/sky130-ldo/pull/137), branch
  `feature/issue-123`, carrying draft DR-010 — verified open 2026-09-23),
  [sky130-bandgap#286](https://github.com/2AMLogic/sky130-bandgap/issues/286)
  (closed 2026-09-23 via
  [PR #294](https://github.com/2AMLogic/sky130-bandgap/pull/294), whose only
  change is a `reuse.lock.json` entry at status `evaluate` — not `kept`;
  verified live 2026-09-23), and both consumers' own scope records:
  [sky130-ldo DR-001 @ `a0ff95b`](https://github.com/2AMLogic/sky130-ldo/blob/a0ff95b/spec/decision-records/DR-001-pass-device-supply-framing.md)
  and
  [sky130-bandgap DR-001 @ `4ac0c24`](https://github.com/2AMLogic/sky130-bandgap/blob/4ac0c24/spec/decision-records/DR-001-supply-flavor-scope.md)
  (the Consumers-section pinned commits).

## Context

Both same-PDK consumers place their error-amplifier positions across a
3.3 V rail and build the whole amplifier/bias/protection chain on 5 V-gate
`sky130_fd_pr__{n,p}fet_g5v0d10v5` devices — `sky130-ldo` because its pass
gate must swing to VIN (3.63 V worst case, per its ratified DR-001 framing
A), `sky130-bandgap` by its own 3.3 V-only thick-oxide scope (its DR-001).
A 1.8 V-core output stage cannot reach the LDO's pass-gate node at any
sizing. This block's ratified scope (§1, DR-003) is 1.8 V ±10% on `_01v8`
exclusively; §1 names the 3.3 V I/O flavor as **not opened**, and DR-004
already records both consumers' Rails verdicts as **not met** for exactly
this reason — but until now nothing *closed* the question: an integrator had
no decision to cite, and both consumers' own evaluations (ldo pending, see
above; bandgap at `evaluate`) faced an open-ended "might the flavor open?"
on this end. Issue #36 — filed per 2am reuse rule 9 step 4 on this, the
sibling that does not meet the requirement — is the tracker item for that
decision; this record is the answer.

## Decision

1. **This block does not serve a 3.3 V-rail / 5 V-gate amplifier
   position.** The block's charter stays 1.8 V-primary on `_01v8` core
   devices; nothing in the design, bench, or spec grows a `g5v0d10v5`
   path.
2. **The 3.3 V I/O-device flavor stays named-not-opened.** The §1 row
   `Supply voltage, VDD (I/O-device flavor)` keeps its value
   `3.3 V — not opened` and its "opening requires its own decision record"
   framing — this record is the declining decision that row's note now
   points at.
3. **Both consumers keep their in-tree amplifiers by reference to this
   record.** Neither `sky130-ldo` nor `sky130-bandgap` re-derives the
   question; their own ledgers (ldo's evaluation, bandgap's
   `reuse.lock.json`) point here as this repo's standing answer.
4. **A superseding DR is the only path to opening the flavor.** This record
   is written to be superseded: if a consumer's adopt-or-record evaluation
   ever *needs* the 3.3 V flavor, a new record reversing this one — plus the
   characterization work its Alternatives section prices — is the route, not
   an edit to this one.

## Alternatives considered

- **Option 1 — open a 3.3 V / `g5v0d10v5` flavor behind its own decision
  record.** Not chosen, on cost verified against this repo 2026-09-23: the
  5 V-gate family has **never been characterized here** — the gm/ID
  testbench templates hard-code
  `sky130_fd_pr__{n,p}fet_01v8`
  ([`sim/gm-id-characterization/testbench/`](../../sim/gm-id-characterization/testbench/)),
  [`corners/model-files.json`](../../sim/gm-id-characterization/corners/model-files.json)
  resolves only `_01v8` corner model files, and
  [`pvt_sweep.py`](../../sim/opamp-characterization/bin/pvt_sweep.py)
  hard-codes `VDD_BY_CORNER = {tt: 1.80, ff: 1.98, ss: 1.62, sf: 1.80,
  fs: 1.80}`; the only `g5v0d10v5` mention outside `spec/` is none at all
  (`spec/porting-plan.md` names the device menu). On top of a second gm/ID
  sweep (new templates, new corner resolution, new `records/` run),
  [DR-001](DR-001-topology-and-cl.md)'s headroom arguments were made at
  1.62 V worst-case and do not transfer, so a second topology/sizing pass,
  a second netlist and bench VDD map, PVT re-characterization, and a spec
  table with its own ratification pass would all be required. That is an
  epic's worth of work — if ever chosen it should be filed as one
  (`loom:epic` + phases), not built under #36. Neither consumer is blocked
  on it: both keep (ldo, pending PR #137) or are evaluating (bandgap) their
  in-tree amplifiers.
- **Option 2 — record the standing decline (this record).** Chosen: cheap,
  additive-only, reversible (supersede-by-design), and it converts an
  open-ended "might open?" into a citable two-way answer for both
  consumers.
- **No new record — let DR-004's not-met verdicts stand as the answer.**
  Not chosen: DR-004 *records the gap* but deliberately leaves the flavor
  question open (its own Open items say so); without a deciding record,
  each future consumer evaluation re-derives the question from scratch,
  which is exactly the duplication rule 9 step 4 exists to stop.

## Spec lines affected

- **No §1/§2 target row value changes** — zero row-value edits, by design.
- [`spec/target-spec.md`](../target-spec.md) §1, row `Supply voltage, VDD
  (I/O-device flavor)`: the row's **note** gains a pointer to this record;
  the row's value stays `3.3 V — not opened`.
- [`spec/target-spec.md`](../target-spec.md) Consumers section, the two
  **Rails** verdict cells (sky130-ldo, sky130-bandgap): each gains a
  pointer to this record; both verdicts stay **not met**; the `8b3ec92`
  verdict stamps are not re-stamped (this pass re-evaluates nothing).
- `README.md` status paragraph gains a half-line pointer to this record.
- `manifests/sky130-opamp.json` and `manifests/sky130-opamp.signoff.json`
  are untouched — the CI signoff byte-compare is unaffected.
- [DR-004](DR-004-consumers-section-and-integrator-view.md) is **not
  edited** (a merged record is superseded, never rewritten); this record's
  Context/Related cite it instead.

## Consequences

- An integrator reading this repo gets a durable, citable answer to "does
  this block serve a 3.3 V-rail amplifier position?": no, by standing
  decision, revisable only by a superseding DR. Neither consumer's
  evaluation needs to leave an open question on this end of the edge.
- The decline is honest about what it costs a future consumer with a
  genuine 3.3 V-rail need: keep the in-tree amplifier, or fund the
  Option 1 epic. This record does not make that need cheaper — it only
  makes the price legible before anyone commits to paying it.
- Ratification-via-PR is where the Option 1 / Option 2 ruling actually
  lands: a reviewer who believes the flavor should open rejects this PR
  cleanly (the Decision section is deliberately unhedged for exactly that).
- This repo sets the fleet-first pattern for the flavor question: both
  twins carry the same rule shape (`gf180-opamp`: "3.3 V primary; 5 V is a
  stretch row that only a `spec/` decision record can open"), and neither
  twin has a flavor-opening or flavor-declining record yet (verified live
  2026-09-23) — whichever way this lands, the twins will copy the shape.
- The consumers' ledger states are theirs, not ours: ldo's "kept" outcome
  sits in an open PR (#137) and bandgap's lockfile reads `evaluate`; if
  either drifts, the pinned-commit citations above are what makes the
  drift detectable, not silently absorbed.

## Open items

- Deliberately unresolved: any sizing, bench, or characterization work for
  a 3.3 V flavor — none is started or scoped beyond Option 1's cost list
  above. A superseding DR opening the flavor must carry that epic (gm/ID
  sweep over `{n,p}fet_g5v0d10v5`, topology/sizing at 3.3 V-rail
  headroom, netlist + bench VDD map, PVT re-characterization, spec-table
  ratification) as its own tracked phases.
- Post-merge, one comment each on
  [sky130-ldo#123](https://github.com/2AMLogic/sky130-ldo/issues/123) and
  [sky130-bandgap#286](https://github.com/2AMLogic/sky130-bandgap/issues/286)
  links this record, so the consumers' ledgers point here (rule 9 step 4).
- The consumers' own evaluations remain theirs to finish (ldo PR #137
  pending as of 2026-09-23; bandgap `evaluate`); this record only
  guarantees their question is answerable from here.
