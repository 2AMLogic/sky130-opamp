# DR-016: Proposed grading band for the slew-rate "≈ 20 V/µs" row

- **Status**: **proposed**. Drafted by the Builder agent for issue #289. It
  is not ratified, and **merging the PR that introduces this record does NOT
  ratify it or the band** (same convention as
  [`DR-008`](DR-008-cmrr-target.md)). Ratification act: a separate,
  operator-approved PR whose only purpose is flipping this Status line to
  `ratified` (the operator settles the number there), or an operator ruling
  that lands as the same Status-line flip. Until then the slew row is graded
  as it is today (`min: 20.0` in the committed envelope) and nothing in
  `spec/target-spec.md` or `ROADMAP.md` changes.
- **Date**: 2026-11-19
- **Decided by**: Loom Builder agent, issue #289 (proposal only)
- **Related**: [`DR-003`](DR-003-target-spec-ratification.md) (ratified the
  row), [`DR-007`](DR-007-device-resize-gbw-slew-swing.md) (stated the rise
  edge "met"), [`DR-012`](DR-012-output-topology-comparison.md) (fall-edge
  topology), issue #277 (quiescent-power "≈" row, same operator ruling, its
  own record), issues #246 and #280 (envelope and roadmap that surfaced the
  conflict)

## Context

Two ratified records disagree about the same number. DR-003 ratified slew as
"≈ 20 V/µs" and made it explicit that "both the 20%–80% rise and the
80%–20% fall transit … must meet it", with no tolerance stated. DR-007
(ratified, "changes no ratified spec target") then records "rise edge now
**met** (worst 19.88 V/µs @ SS/−40 °C, 99.4 %)". The item-5 envelope
`manifests/envelopes/20261113-150556-60489db-8101bf-tran-sr.klt.json` grades
the same rise number against `limits: {min: 20.0}` and reports `fail`
(margin −0.1227 V/µs); `spec/target-spec.md:180` repeats DR-007's "rise met
everywhere". Nothing ratified states the precision an "≈" row is graded at.

Operator ruling (2026-11-18, `/fleet:decide` round 20261118-r16, q152, issue
#289): each "≈" row gets its own stated tolerance in its own record; the
band is stated as two explicit sides (3 % default magnitude, a side may be
zero); sides are chosen from what the row protects, not from which band the
committed data clears; this record settles the DR-003 / DR-007 precedence by
superseding; the fall edge is a design miss under any band.

Measured values (committed envelope above, worst case, SS / 1.62 V /
−40 °C; shared by the 15-point paired grid):

| Edge | Worst | % of 20 V/µs |
|---|---|---|
| rise | 19.88 V/µs (19.8773) | 99.4 % |
| fall | 11.04 V/µs (11.038) | 55 % |

(The 45-point independent-supply grid, record
`20261011-194651-046fe81-86146b`, has rise 19.79 V/µs and fall 9.13 V/µs
at FS / −40 °C / 1.62 V; rise grid-wide maximum is 20.89 V/µs.)

## Decision

**Proposed band: `+0 % / −3 %` on the ≈ 20 V/µs slew row — a floor of
19.4 V/µs, no ceiling.** Both edges are graded against it at every corner.

Why these sides (what the row protects, independent of the data):

- **Lower side, −3 %.** Slew rate is a minimum: it bounds how fast the
  output can move on a large step. A shortfall lengthens the slew-limited
  part of a large-step settle in proportion (a step of ΔV takes ΔV/SR), so a
  3 % shortfall costs about 3 % on that slew-limited interval. The "≈ 20"
  figure is a self-consistent sizing example (`SR = I_SS/Cc`, §2a), not a
  figure derived from a consumer's step requirement, and no consumer in the
  Consumers section states a slew need — so there is no consumer cost that
  justifies a departure from the 3 % default magnitude in either direction.
- **Upper side, +0 %.** Excess slew does not hurt a consumer of an op-amp
  (it only shortens the slew-limited interval), and an upper bound on a
  minimum would make a *better* amplifier fail. The upper side is therefore
  zero by construction, not a tolerance on overshoot: the row has no
  ceiling.

Grading under the proposed band (floor 19.4 V/µs): **rise passes** (19.88,
+0.48 V/µs margin; 19.79 on the 45-point grid, also passes); **fall fails**
(11.04, 9.13 on the 45-point grid; 8.36 V/µs short of the floor on the
paired grid).

**Precedence (supersession).** On ratification this record supersedes
DR-003's slew clause *only as to the unstated precision*: the grading
follows **DR-007's verdict** — the rise edge is *met* — because under the
`+0 % / −3 %` band DR-003's "both edges must meet it" and DR-007's "rise
met" agree (both edges are still required to meet the row; the rise edge
does, the fall edge does not). DR-003's symmetry requirement and its
ratified-non-compliant fall verdict stand unchanged. Neither record is
edited in place.

**The fall edge is a design miss under any band.** `slew_rate` and item 5
stay **failed**; this record changes the account (rise met, fall missed), not
the verdict. No fall-edge work is decided here (see DR-012).

## Alternatives considered

- **`+0 % / −0 %` (strict 20.0 V/µs).** Rise would fail by 0.12 V/µs
  (0.6 %) for a row whose own "≈" says it is not a hard 20.000; rejected
  because the ratified row already says "≈", and a zero band makes the
  symbol meaningless.
- **`±3 %` (floor 19.4, ceiling 20.6).** Rejected: a ceiling on a minimum
  fails better amplifiers, and rise already measures up to 20.89 V/µs at
  some grid points, so it would fail on excess slew.
- **`+0 % / −1 %` (floor 19.8) or tighter.** Rejected as a departure from
  the 3 % default with no stated consumer reason; picking 1 % would be
  choosing the band from the data (the 45-point rise 19.79 V/µs lies just
  under it), which the ruling forbids.
- **A single shared band for every "≈" row.** Ruled out by the operator;
  quiescent power (#277) is a maximum-type row and gets its own record.

## Spec lines affected

- `spec/target-spec.md` §2 slew-rate row: **no change needed** under the
  proposed band (rise is met, as the row already says; fall is already
  stated as partially closed). On ratification the row's target cell gains
  the band (`≈ 20 V/µs, graded +0 % / −3 %`) and a pointer to this record —
  a to-do on ratification, not applied while *proposed*.
- `ROADMAP.md` item 5: **no correction needed** under the proposed band (it
  already names the fall edge as the design miss). If the operator ratifies
  a band that leaves rise *not met* (e.g. `+0 % / −0 %`), both the
  target-spec row's "rise met everywhere" and ROADMAP item 5 must be
  corrected in the ratification PR.
- DR-003 and DR-007: header "Superseded by" pointer only, added at
  ratification per existing convention; not edited here.

## Consequences

- The committed envelope's `limits.min` is 20.0; it is **not** changed and
  no sim is re-run here (`sim/` is append-only). On ratification a future
  re-grade would set `min: 19.4` for both edges; the rise edge then grades
  `pass`, the fall edge still `fail`, and `slew_rate` remains a failed row.
- Item 5 stays `check_failed`; the closing path is the fall-edge work
  (#22, DR-012), unchanged.
- Bad consequence: a band lower than the DR-003 text weakens the rise
  criterion by 0.6 V/µs; the operator should confirm that trade against
  the strict alternative.
- Collision note: DR-015 is proposed in PR #287; #277's record is a sibling.
  Renumber at merge if a collision is found.

## Open items

- The operator's ratification of the number (this record only proposes
  `+0 % / −3 %`).
- Quiescent-power tolerance (#277) and any other "≈" row: separate records.
- Re-grading the committed envelopes under the ratified band, and the
  target-spec / ROADMAP edits above: follow-on work after ratification.
- Fall-edge design closure: not decided here.
