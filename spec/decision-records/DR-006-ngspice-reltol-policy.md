# DR-006: ngspice solver-tolerance convention — keep the default; no `reltol`/`abstol`/`vntol` override in any deck

- **Status**: **proposed** — a status-quo record, carried for ratification
  via this PR (Judge review + Champion/operator merge) per the 2026-08-19
  canary spec/DR ratification-via-PR standing policy
  ([2AMLogic/2am#357](https://github.com/2AMLogic/2am/issues/357)); the same
  path DR-003/DR-004/DR-005 used. **Nothing here is binding until this PR
  merges.** Status-line wart, stated rather than left to bite (same as
  DR-003/DR-004/DR-005's): merging this PR does not rewrite the line above,
  so a merged copy of this record still reads `proposed` — treat it as a
  drafting artifact of the two-key mechanism.
- **Date**: 2026-09-28
- **Decided by**: Builder agent, issue #38 — the drafting party only. The
  ratification act is the approval of the PR carrying this record.
- **Supersedes**: none — sixth decision record in this repo. Touches no
  prior record; it sets no `spec/target-spec.md` row value (see "Spec lines
  affected").
- **Superseded by**: (none while this record stands)
- **Related**: [#38](https://github.com/2AMLogic/sky130-opamp/issues/38)
  (this issue — the cross-repo coordination item this record answers),
  [sg13g2-opamp#68](https://github.com/2AMLogic/sg13g2-opamp/issues/68) and
  its deciding record
  [sg13g2-opamp DR-0005](https://github.com/2AMLogic/sg13g2-opamp/blob/main/spec/decision-records/0005-ngspice-reltol-policy.md)
  (the twin's measured screen and the cross-repo precedent this record
  adopts), [#6](https://github.com/2AMLogic/sky130-opamp/issues/6) /
  [`sim/gm-id-characterization/`](../../sim/gm-id-characterization/README.md)
  (the gm/ID study whose `gds_s` / `gm_gds` columns are the class of column
  the twin's envelope lives in),
  [#17](https://github.com/2AMLogic/sky130-opamp/issues/17) /
  [`sim/opamp-characterization/`](../../sim/opamp-characterization/README.md)
  (the circuit-level PVT harness), and
  [`sim/gm-id-characterization/spiceinit`](../../sim/gm-id-characterization/spiceinit)
  (this repo's only committed ngspice init file).

## Context

`CLAUDE.md`'s three-foundry-twin rule makes bench structure a shared
property of `sky130-opamp`, `gf180-opamp` and `sg13g2-opamp`: results are
supposed to compare across PDKs, so a simulation-methodology choice that
changes what a recorded number *means* is a decision for all three repos,
not one.

`sg13g2-opamp` made that choice first, by measurement. Its DR-0005
(deciding sg13g2-opamp#68) ran all eight of its deterministic benches on a
single host, as committed and with a candidate tolerance injected into
every templated deck, and found: at default tolerance every bench is clean;
at every tightened value it tested, at least one bench loses points (its
input-CMR bench loses 6 of 45 points at `reltol=1e-5` rising monotonically
to 21 at `1e-9`, with DC gmin/source-stepping collapse; its slew-rate bench
loses 39 of 45 at `1e-9` to TRAN timestep collapse) — while no value both
closed its gm/ID cross-host envelope at print precision and kept its fleet
green. Its conclusion: keep the default, and carry the one measured
tolerance-sensitivity (a ~20 % cross-host spread on its finite-difference
`gds`-class columns) as a documented per-bench reading rule rather than
pinning it away. Issue #38 asks this repo to record the same convention.

**What this repo looks like today** (verified on this branch, 2026-09-28):

- `git grep -niE 'reltol|abstol|vntol'` returns **no hits** anywhere in the
  repository outside this record — neither harness pins a solver tolerance.
- The only `.option` lines in any committed deck are `.option scale=1u`
  (both gm/ID templates and all three opamp-characterization templates);
  [`sim/gm-id-characterization/spiceinit`](../../sim/gm-id-characterization/spiceinit)
  sets `ngbehavior`, `skywaterpdk`, `ng_nomodcheck`, `noinit` and `klu`,
  and no tolerance. `sim/opamp-characterization/` has no `spiceinit` at
  all.
- Both committed records
  (`sim/gm-id-characterization/records/20260909-062847-35a9d46.json`,
  `sim/opamp-characterization/records/20260916-032327-edc9f22.json`) were
  produced at ngspice's default tolerance on **one** host — ngspice-46,
  `Darwin 25.6.0 arm64`, sky130A pinned at `c6d73a3`. This repo therefore
  has **no cross-host leg**: it has neither observed the twin's envelope nor
  established its absence.

So the convention is already the de-facto state here. This record converts
it from an accident of "nobody added a line" into a citable decision, which
is the whole point of #38 — a shared non-decision is only shared if all
three repos write it down.

## Decision

1. **The standing convention for this `sim/` tree is ngspice's default
   solver tolerance.** No `.option reltol=` / `.option abstol=` /
   `.option vntol=` line appears in any committed deck, testbench template,
   or `spiceinit` file in this repository, and none is added by this
   record. The existing `.option scale=1u` lines and the
   `sim/gm-id-characterization/spiceinit` settings are unaffected.
2. **Every committed record in `sim/` was, and stays, produced at
   ngspice's default tolerance with no deck-level override.** A future
   record diff is entitled to assume that of every file under any
   `sim/*/records/` directory. A mixed-tolerance comparison — a committed
   record against a tightened re-run, or two records produced under
   different tolerances — is not valid evidence in this tree.
3. **A tolerance-sensitive column is documented, not pinned away.** If this
   repo ever observes a cross-host (or cross-environment) spread on a
   `gds`-class column or any other recorded quantity, the answer is a
   reading rule in that bench's `README.md` — `sg13g2-opamp`'s
   "Cross-host reproducibility envelope" section is the template — saying
   what precision a reader may quote the affected columns to, and how to
   re-derive a converged value in a scratch copy. It is **not** a tolerance
   pin. Nothing is written under this clause today; see "Open items".
4. **Tightening is reversible only through a superseding record that runs
   the screen here.** Any future proposal to pin a tolerance in this repo
   must first run DR-0005's screen *on this repo's own benches* — every
   bench, as committed vs. with the candidate value injected into every
   templated deck, on one host — and clear its gate: **zero** broken
   simulation points at the candidate value across every bench, closure of
   whatever spread motivated the proposal at print precision, and no
   runtime regression. Rescuing a candidate value with convergence aids
   (`gmin` / `itl` stepping knobs) instead of meeting the zero-broken gate
   does not clear it. Citing DR-0005's table is not a substitute for
   running the screen: those numbers are the twin's models, harness and
   host, not this repo's.

## Alternatives considered

- **Pin `reltol=1e-9` (or any tightened value) tree-wide, following the
  twin's starting point.** Not chosen. It has never been measured on this
  PDK, this harness or this repo's benches, and the one repo that *did*
  measure it found it broke two of its eight benches outright. Adopting an
  untested pin would simultaneously risk silently degraded points here and
  make this repo's records incomparable with both twins — the exact
  cross-PDK comparability the three-foundry-twin rule exists to protect.
- **Pin a looser `reltol` (`1e-5` … `1e-7`) as a compromise.** Not chosen.
  Upstream measured that the loose end neither closes the envelope at print
  precision nor keeps the fleet green (`1e-5` still costs its input-CMR
  bench 6 points and ~10x wall time), so the compromise buys nothing
  measured; here it would additionally be adopted with no local measurement
  at all.
- **Pin a tolerance only in the two gm/ID templates (bench-local).** Not
  chosen. The convention has to be uniform for record diffs to stay
  interpretable — a per-bench tolerance map turns every cross-bench
  comparison into a mixed-tolerance join. A reader who needs a converged
  value can re-derive it in a scratch copy without changing what the
  committed evidence means.
- **Record nothing — let the absence of a tolerance line speak for
  itself.** Not chosen. An undocumented status quo is re-derived by every
  future reader and re-litigated by every future tightening proposal, and
  it leaves the twin's coordination item (#38 / sg13g2-opamp#68) unanswered
  on this end. Writing it down costs one file and makes the convention
  citable.
- **Speculatively add a "Cross-host reproducibility envelope" section to
  this repo's bench READMEs now, mirroring the twin's.** Not chosen, and
  explicitly out of scope: no such spread has been observed here (both
  committed records come from the same host), so such a section would
  document a measurement this repo has not made. Clause 3 above says what
  happens *if* one is ever observed.

## Spec lines affected

- **No `spec/target-spec.md` row value or bound changes** — zero row edits,
  by design. This is a simulation-methodology record; it constrains how
  evidence in `sim/` is produced, not what any spec row claims.
- [`spec/target-spec.md`](../target-spec.md) is untouched, as are
  [DR-001](DR-001-topology-and-cl.md) through
  [DR-005](DR-005-io-flavor-not-served.md) (a merged record is superseded,
  never rewritten).
- The files this record *constrains* (none of which is edited by the PR
  carrying it, because the constraint is already satisfied):
  [`sim/gm-id-characterization/testbench/`](../../sim/gm-id-characterization/testbench/)
  (`nfet_gmid.spice.tmpl`, `pfet_gmid.spice.tmpl`),
  [`sim/opamp-characterization/testbench/`](../../sim/opamp-characterization/testbench/)
  (`opamp_ac.spice.tmpl`, `opamp_dc_swing.spice.tmpl`,
  `opamp_tran_sr.spice.tmpl`),
  [`sim/gm-id-characterization/spiceinit`](../../sim/gm-id-characterization/spiceinit),
  and the two runners
  ([`sweep.py`](../../sim/gm-id-characterization/bin/sweep.py),
  [`pvt_sweep.py`](../../sim/opamp-characterization/bin/pvt_sweep.py)),
  neither of which injects a tolerance option into a rendered deck.
- `manifests/` and the CI signoff byte-compare are unaffected — no
  generated artifact changes.

## Consequences

- An integrator or a future agent reading a record in `sim/` gets a
  citable guarantee about how it was produced: ngspice default tolerance,
  no deck-level override, same as both twins. Cross-PDK comparisons of the
  three opamp benches do not have to ask the question.
- The rejection of tightening now has a written gate (Decision 4). A future
  proposal cannot land as a one-line template edit; it has to produce
  numbers on this repo's benches first.
- **This repo adopts the convention on the twin's measurement, not its
  own** — the honest cost of this record. What ngspice-46 does with sky130
  models at a tightened tolerance, on these five templates, is untested
  here. The convergence-collapse numbers quoted in Context are
  `sg13g2-opamp`'s (IHP models, its own harness, its own host) and are
  cited as precedent, not as a local result.
- **The twin's amplification mechanism does not transfer literally.**
  sg13g2-opamp's envelope lives in a `gds` column derived as a central
  difference, where the fractional signal falls to ~`5.8e-04` and amplifies
  anything the convergence test leaves unconstrained by ~1700x. This
  repo's `gds_s` column is the device's internal operating-point parameter
  saved directly by the deck
  (`@m.xm1.msky130_fd_pr__nfet_01v8[gds]`, see
  [`nfet_gmid.spice.tmpl`](../../sim/gm-id-characterization/testbench/nfet_gmid.spice.tmpl)),
  not a difference of nearly-equal solved quantities. So this record claims
  **no** envelope here in either direction: the twin's number is not
  evidence about this repo's columns, and the absence of a local
  observation is not evidence of their insensitivity.
- Nothing is re-run, re-minted, or invalidated: no template is edited, no
  record is regenerated, no spec row moves. The rollout of this decision is
  the decision itself.

## Open items

- **No cross-host reproducibility measurement exists in this repo.** Both
  committed records come from the same Darwin/arm64 host, so there is no
  second leg to diff against. Producing one (a Linux/x86_64 default-
  tolerance gm/ID run, committed as an ordinary append-only record) is the
  prerequisite for ever exercising Decision 3, and is not done here.
- **Whether this repo's `gds_s` / `gm_gds` columns carry any tolerance
  sensitivity at all is unmeasured**, for the mechanism reason above. A
  reader must not infer the twin's ~20 % figure applies here, nor that it
  does not.
- Item 2 of #38 ("if this repo ever observes a cross-host spread …
  document it as a reading rule") is deliberately left future-conditional:
  **no** `sim/*/README.md` gains a "Cross-host reproducibility envelope"
  section by this record. That section is written when — and only when — a
  spread is actually observed on this repo's benches.
- A future ngspice release that changes its own default tolerances would
  change what "the default" means here without any edit to this repo. That
  would warrant re-running DR-0005's screen locally and, if the answer
  moves, a superseding record; nothing in this tree detects it
  automatically.
