# DR-017: Proposed grading band for the quiescent-power "≈" row

- **Status**: **proposed**. Drafted by the Builder agent for issue #277. It
  is not ratified, and **merging the PR that introduces this record does NOT
  ratify it or the band** (same convention as
  [`DR-008`](DR-008-cmrr-target.md), also followed by the slew-rate
  sibling record proposed for issue #289, DR-016 / PR #350). Ratification act: a separate,
  operator-approved PR whose only purpose is flipping this Status line to
  `ratified` (the operator settles the number there), or an operator ruling
  that lands as the same Status-line flip. Until then the row grades as it
  does today — `SPEC_IQ_MAX_A = 65 µA` as a hard `max` in the item-5
  harness, with that harness's own "stated reading, not a design verdict"
  caveat — and nothing in `spec/target-spec.md`, `ROADMAP.md`, or the
  harness changes.
- **Date**: 2026-11-19
- **Decided by**: Loom Builder agent, issue #277 (proposal only)
- **Related**: [`DR-003`](DR-003-target-spec-ratification.md) (ratified the
  row's ≈ figures and explicitly declined to set a tolerance),
  [`DR-002`](DR-002-device-sizing.md) (§(a) 65 µA budget the ≈ estimate
  encodes), DR-016, proposed in PR #350 for issue #289 (the slew-rate
  sibling record under the same operator ruling), issue #277 (this issue),
  #246 / PR #275 (the committed item-5 envelope this record grades),
  [#3](https://github.com/2AMLogic/sky130-opamp/issues/3) (gap-to-T1 item 5,
  which carries the current hard-ceiling grade), #284 (area + Consumers
  refresh — deliberately leaves this row's tolerance to this record),
  #282 / #289 (the other rows' own records)

## Context

Two ratified facts meet without a stated tolerance between them:

1. **The ratified figures.** [`DR-003`](DR-003-target-spec-ratification.md)
   ratified quiescent power as "**≈ 128.7 µW at the 1.98 V binding corner /
   ≈ 117.0 µW at nominal 1.8 V unchanged, with the measured confirmation
   attached**", recorded the historical measured deltas (−0.6%, +1.6%), and
   stated explicitly: "The measured deltas (−0.6%, +1.6%) are recorded here
   as facts; **this record does not convert them into a ratification
   tolerance**." DR-003 also recorded that SS corners run 2–5 µA lower than
   the 65 µA budget — "benign, and in the better direction." The tolerance
   was left open, deliberately.
2. **The operational grade.** T1 item 5 grades `iq_a` against a hard
   65.0 µA maximum (`SPEC_IQ_MAX_A` in
   `sim/opamp-characterization/bin/pvt_sweep.py`). That harness comment
   itself flags the bound as "the ONE place in this block where a `SPEC_*`
   constant is not simply a ratified number copied across … a READING of an
   '≈' row", notes a `fail` on it "means 'fails under the stated reading',
   not a design verdict", and names issue #277 as the reconciliation
   record. Under that reading the committed 15-point item-5 envelope at
   `02cc663` ([`manifests/envelopes/20261113-150556-60489db-8101bf-ac-iq.klt.json`](../../manifests/envelopes/20261113-150556-60489db-8101bf-ac-iq.klt.json),
   issue #246 / PR #275) fails **13 of 15 corners** — nominal TT / 27 °C
   included — spanning **64.2433–66.6284 µA**, worst **66.6284 µA @
   FF / 125 °C / 1.98 V = +2.51%** against the 65.0 µA figure.

Operator ruling (2026-11-18, `/fleet:decide` round 20261118-r16, q152,
recorded on issue #277): each "≈" row gets its own stated tolerance in its
own decision record; the band is two explicit sides (3% default magnitude, a
side may be zero); sides are chosen from **what the row protects** — which
direction of deviation costs a consumer, and which is harmless or better —
**not from which band the committed data happens to clear**; the record
takes the repo's usual ratification path; no ratified figure changes; if a
proposed band leaves the row not met, the same record carries the §2
correction wording.

## Decision

**Proposed band: `+3% / −3%` on the implied 65.0 µA — inclusive limits
63.05–66.95 µA, graded on measured `iq_a` at every corner of the grid,
signed deviation taken against 65.0 µA.** In power terms at the two
ratified supplies (see the mapping below): **124.84–132.56 µW at 1.98 V;
113.49–120.51 µW at 1.80 V.**

Why these sides (chosen from what the row protects, not from the data):

- **Upper side, +3% — the costly direction.** Above the ratified figure,
  every extra µA is idle power a consumer must supply, size for, and burn —
  this is the direction the row exists to bound across PVT ("an integrator
  needs to know how much idle current the block may draw"). The magnitude is
  the ruling's 3% default, with no departure taken: DR-003 ratified an
  explicitly *approximate* figure (it recorded +1.6% and −0.6% measured
  deltas as facts and declined to convert them into a tolerance), so the
  upper side's job is to state the PVT maximum an integrator designs to —
  66.95 µA — not to re-ratify the nominal figure as a hard ceiling. A `+0%`
  side would grade the "≈" figure as an exact 65.000 µA bound, a design
  constraint DR-003 did not write.
- **Lower side, −3% — the benign direction.** DR-003 itself calls lower
  draw benign ("in the better direction"): a consumer loses nothing when a
  corner draws less idle power, so the lower side protects nothing on the
  power axis. It is kept at the 3% default rather than loosened or dropped
  for one reason: the row asserts an *approximate operating point*, not
  merely a ceiling — a draw far below ≈65 µA would falsify the row's own
  description and normally indicates a mis-biased (non-operating) corner,
  which this row should still flag even though no consumer is harmed. A
  `−0%` side is rejected outright because it would grade DR-003's own
  recorded benign deviations (SS running 2–5 µA low) as failures.

Stated plainly per the ruling: the sides above follow from the protection
analysis and the default magnitude only. The measured yield below is the
verdict evidence, applied after the band is chosen — it played no part in
choosing the sides.

**How voltage maps current to power.** The two ratified figures are the
*same current*: 128.7 µW / 1.98 V = 117.0 µW / 1.80 V = **65.0 µA** — the
row's own text notes `I_Q = 65 µA` "is exactly `DR-002` §(a)'s budget,
which is what the row's '≈' estimate encodes". `pq_w` is measured as
`iq_a × VDD` at each corner's supply (that is how the harness computes it),
so one current band converts to a power window at each ratified supply
(124.84–132.56 µW at 1.98 V; 113.49–120.51 µW at 1.80 V). Grading is done
on measured `iq_a` per corner — the supply-independent form, the only
single bound that reproduces *both* ratified power figures exactly. Two
honest caveats: measured current is mildly supply-dependent (at fixed
corner and temperature, `iq_a` rises a few percent across 1.62 → 1.98 V),
so the power windows are the integrator-facing conversion, not a second
graded bound; and at the SS corners' 1.62 V supply *neither* ratified
power figure applies, because DR-003 ratified no figure at 1.62 V —
the concrete case is SS / 125 °C / 1.62 V, which draws 65.1484 µA
= **105.54 µW, below both ratified power figures**, yet fails the current
ceiling as it stands. A current bound supplies the reading a power-figure
comparison cannot at that corner.

### Grade under the proposed band (evidence, applied after the band was chosen)

Full 15-point item-5 envelope
([`20261113-150556-60489db-8101bf-ac-iq.klt.json`](../../manifests/envelopes/20261113-150556-60489db-8101bf-ac-iq.klt.json),
committed at `02cc663`; every value re-derived from the envelope JSON for
this record):

| Corner | `iq_a` (µA) | dev vs 65.0 µA | Current reading (≤ 65.0) | Proposed band (63.05–66.95) |
|---|---|---|---|---|
| SS / 1.62 V / −40 °C | 64.2433 | −1.16% | pass | pass |
| SS / 1.62 V / 27 °C | 64.7358 | −0.41% | pass | pass |
| SS / 1.62 V / 125 °C | 65.1484 | +0.23% | fail | pass |
| FS / 1.80 V / −40 °C | 65.2266 | +0.35% | fail | pass |
| FS / 1.80 V / 27 °C | 65.4613 | +0.71% | fail | pass |
| TT / 1.80 V / −40 °C | 65.5395 | +0.83% | fail | pass |
| FS / 1.80 V / 125 °C | 65.6996 | +1.08% | fail | pass |
| TT / 1.80 V / 27 °C | 65.7449 | +1.15% | fail | pass |
| SF / 1.80 V / −40 °C | 65.8438 | +1.30% | fail | pass |
| TT / 1.80 V / 125 °C | 65.9654 | +1.49% | fail | pass |
| SF / 1.80 V / 27 °C | 66.0214 | +1.57% | fail | pass |
| SF / 1.80 V / 125 °C | 66.2239 | +1.88% | fail | pass |
| FF / 1.98 V / −40 °C | 66.4198 | +2.18% | fail | pass |
| FF / 1.98 V / 27 °C | 66.5069 | +2.32% | fail | pass |
| FF / 1.98 V / 125 °C | 66.6284 | +2.51% | fail | pass |

- **Current reading (reproduced, unrounded envelope values)**: 13/15 fail
  the hard 65.0 µA ceiling; only the two SS cold/cool corners pass; worst
  66.6284 µA (+2.51%) at FF / 125 °C / 1.98 V — the row's ratified
  binding corner.
- **Under the proposed band**: **15/15 pass, 0 fail** — both sides checked:
  the binding corner is FF / 125 °C / 1.98 V at +2.51% (upper side), and
  the lowest-current corner, SS / 1.62 V / −40 °C at −1.16%, sits inside
  the lower limit; the lower side never binds anywhere in the committed
  data. **Row verdict under the band: met** (pending ratification). Because
  the band is met, the miss branch of the ruling does not fire: no §2
  correction wording is triggered, and both ratified power figures stand
  unchanged.
- **Independent 45-point cross-check** (the grid §2 cites, record
  [`20261011-194651-046fe81-86146b`](../../sim/opamp-characterization/records/20261011-194651-046fe81-86146b.json)):
  45/45 points inside 63.05–66.95 µA — worst **66.684 µA (+2.59%,
  132.03 µW) at SF / 125 °C / 1.98 V** (matching the figures §2 already
  cites; on this independent-supply grid the binding process is SF, as the
  §2 binding-corner cell notes), minimum 64.0509 µA (−1.46%). The
  15-point envelope is the item-5 verdict set; this grid checks the
  both-grids claim.

## Alternatives considered

- **`+0% / −3%` (strict ceiling, the status quo reading).** Rejected: it
  grades the "≈" figure as an exact 65.000 µA bound, which makes 13/15
  committed corners — nominal TT / 27 °C included — failures of a
  ratified-and-"confirmed" row; the harness comment already concedes such
  a `fail` is "under the stated reading, not a design verdict". DR-003
  ratified the figure with a recorded *+1.6%* deviation above the
  estimate, so a zero upper side would retroactively turn the ratified
  row into a standing violation by reading, not by measurement. The
  operator may still choose this strictness at ratification if a consumer
  needs it; this record proposes against it.
- **A looser lower side (−10%, or no lower bound).** Rejected: lower draw
  is benign, so the lower side is the non-protective one — but the ruling
  sets 3% as the default magnitude and requires a stated reason to
  depart, and "the benign direction does not need more room than the
  default" is not a reason, it is the absence of one. Dropping the lower
  side entirely would turn "≈" into "≤" and stop flagging a gross
  under-current (a mis-biased corner) that the row's own description
  covers.
- **A tighter upper side (+1% / +2%).** Rejected as a departure from the
  default magnitude with no consumer-imposed reason: no consumer in the
  Consumers section states an idle-power tolerance (sky130-ldo's Iq row is
  "Explicitly open — no number set"; sky130-bandgap's 50 µA whole-block
  row is violated by the ratified 65 µA figure *regardless of any band*),
  so there is no requirement the default fails to honor. #284 owns any
  Consumers-table refresh.
- **One shared band for every "≈" row.** Ruled out by the operator's
  2026-11-18 ruling itself: each row gets its own record. The slew-rate
  sibling is DR-016 (issue #289 / PR #350); this
  record is the quiescent-power sibling and takes DR-017 (see the
  collision note below).
- **Grading on `pq_w` against the two ratified µW figures directly.**
  Rejected on mechanism: a `klt` limits bound is one number across every
  corner of a request, the two ratified figures differ by supply, and the
  SS corners sit at 1.62 V where no figure was ratified at all. The
  current form is the supply-independent one that reproduces both figures
  exactly (the argument the harness comment already makes); `pq_w` stays
  reported alongside, ungraded.
- **Changing the ratified figures toward the measurement.** Rejected
  outright: `CLAUDE.md` ("agents do not relax a ratified spec to make
  results pass") and the ruling ("No ratified figure changes"). Under the
  proposed band no figure needs to change — but if the operator ratifies a
  band the row misses, the correction lands in §2 via this record's
  ratification PR, not by moving the ratified µW figures.

## Spec lines affected

- **This PR adds this record and nothing else.** Per the sibling DR-016's
  convention, the §2 row edit is a ratification to-do, not applied while
  *proposed*:
  - `spec/target-spec.md` §2, **Quiescent power** row, at ratification: the
    Target cell gains the band — the ratified ≈ figures stay verbatim
    (≈ 128.7 µW at 1.98 V; ≈ 117.0 µW at 1.80 V), now graded `+3% / −3%`
    around the implied 65.0 µA (63.05–66.95 µA inclusive) on measured
    `iq_a` — and a pointer to this record; the Status cell notes the
    ratified tolerance alongside `DR-003`. If the operator ratifies a band
    the row misses, the same ratification PR instead carries the §2
    correction wording (measurement and missed requirement identified
    separately), per the ruling.
  - `sim/opamp-characterization/bin/pvt_sweep.py`, at ratification only:
    `SPEC_IQ_MAX_A` becomes 66.95 µA and a new inclusive lower limit
    63.05 µA is added; the comment block's "stated reading" caveat
    resolves. The file's own comment says this: "changing `SPEC_IQ_MAX_A`
    is that ruling's job, not a tuning knob."
  - Tracker [#3](https://github.com/2AMLogic/sky130-opamp/issues/3) item 5
    and `ROADMAP.md`'s "Grade the quiescent-power row" entry: re-graded
    under the ratified band as follow-on work.
- DR-003: stands unchanged. This record does not supersede it — DR-003
  left this tolerance open by design ("does not convert them into a
  ratification tolerance"); on ratification this record discharges that
  open item. No header edit is needed while proposed.
- Nothing under `design/`, `sim/`, `layout/`, `measurements/`, or
  `manifests/` changes: committed evidence is append-only, the envelope is
  cited as committed, and no simulation is re-run.

## Consequences

- **Until ratification, nothing grades differently.** The harness keeps
  `SPEC_IQ_MAX_A = 65 µA` and its caveat; item 5 keeps reporting the
  quiescent-power row failed; the spec row keeps its current text.
- **Once ratified**, item-5 quiescent-power grading becomes the two-sided
  inclusive band; the committed envelope re-grades 15/15 met with no
  re-run (re-grading is a report over committed data); tracker #3 item 5's
  quiescent-power entry and ROADMAP item 5 flip from "fails only under a
  zero-tolerance reading" to met-under-the-ratified-band.
- **Consumers-section verdicts are untouched.** Both consumer comparisons
  read against the ratified 65 µA figure, not a tolerance: sky130-bandgap's
  50 µA whole-block row stays not-met under any band this record could
  propose; sky130-ldo states no number. #284 owns any refresh.
- **Bad consequences, stated:** (1) the band legitimizes up to +3% idle
  draw — after ratification an integrator reading the row must budget
  66.95 µA (132.56 µW at 1.98 V), not 65.0 µA; the operator should weigh
  that against the strict `+0%` alternative. (2) The committed data sits
  inside the proposed band with ≈ 0.4% margin at the top (+2.59% worst on
  the 45-point grid vs. the +3% side). The band was not fitted to that
  data — the sides follow the protection analysis and the default
  magnitude — but the coincidence is stated honestly: a future resize or
  model update pushing the worst case past +3% makes the row unmet again,
  and the closing path is a design fix or an operator-superseding record,
  never a quiet re-fit.
- **Collision note**: DR-015 is proposed in PR #287 (PSRR) and DR-016 in
  PR #350 (slew, the sibling record under this same ruling); this record
  takes **DR-017** to avoid colliding with either. Renumber at merge if a
  collision is found anyway.

## Open items

- **The operator's ratification of the number.** This record proposes
  `+3% / −3%`; the ruling reserves the number to the operator at the
  usual ratification path. A miss under the ratified band is a valid
  outcome and carries its own §2 wording in the ratification PR.
- **Ratification-PR to-dos** (listed above under Spec lines affected):
  §2 row band + pointer; harness upper/lower limits + comment resolution;
  tracker #3 / ROADMAP re-grade.
- **Sibling "≈" rows, each its own record**: slew rate (#289 /
  DR-016, PR #350), PSRR target (#282 / PR
  #287's DR-015), area and Consumers refresh (#284) — all out of scope
  here.
- **Mismatch / Monte-Carlo spread of `iq_a`** is not covered: the row's
  ratified statistical basis is a deterministic corner worst case, and
  this band inherits that basis. Any statistical quiescent-power claim
  needs the mismatch MC pass (tracker item 6 territory) and its own
  record.
