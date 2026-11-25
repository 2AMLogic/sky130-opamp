# DR-015: Input-stage screen for the common-mode-range-limited rows — icmr-rebias (proposed)

- **Status**: **proposed**. Drafted by the Builder agent for issue #359. It is
  not ratified, and merging the PR that carries it does NOT ratify it or
  complete T1 item 5. Ratification is a separate, operator-approved PR that
  flips this Status line. It changes no target, and no ratified record is
  edited. (Numbering note: the curation comment on #359 said "after DR-018 as
  of `463630d`"; the tree at `95d518f` ends at DR-014, so this record is
  DR-015 — re-derived per the date-stamp re-verification rule.)
- **Date**: 2026-11-21
- **Decided by**: Loom Builder agent, issue #359 (proposal only)
- **Related**: [`DR-001`](DR-001-topology-and-cl.md) (input-pair polarity),
  [`DR-007`](DR-007-device-resize-gbw-slew-swing.md),
  [`DR-011`](DR-011-offset-closure-sizing-feasibility.md) (Pelgrom baseline),
  [`DR-012`](DR-012-output-topology-comparison.md),
  [`DR-013`](DR-013-grid-legal-mos-widths.md) (baseline widths); issues #3
  (T1 tracker, item 5), #181 and #185 (attribution), #78/#79/#197 (earlier
  candidates), #360 (class-AB study, separate limit).

## Context

Two ratified rows are design misses: output swing (0.948 Vpp unity-buffer at
SS / −40 °C / 1.62 V vs ≈ 1.39 Vpp; 45-point worst 0.897 Vpp at SF / −40 °C /
1.62 V) and fall slew rate (11.03 V/µs at SS / −40 °C, 9.13 V/µs at
FS / −40 °C / 1.62 V, vs ≈ 20). The committed attribution (#181: input-CM
limited high side 15/15, low side 11/15; #185: input-range share of fall slew
at the SS / −40 °C corner) makes the input stage the only identified lever for
the swing row. Every prior candidate (#78 tail clamp, #79 sink, #197 sink bias
margins) changed the tail or output stage; the input pair was untouched.

Issue #359 screened input-stage candidates in the #197 shape, plan-first
([`variants/input-stage/PLAN.md`](../../sim/opamp-characterization/variants/input-stage/PLAN.md)),
one fleet-screened candidate:

- **(a) `icmr-rebias`** — low-headroom re-bias at unchanged currents: pair
  `XM1`/`XM2` gm/ID 17 → 20 (W 6.030 → 14.470 µm), PMOS mirror group
  `XM3`:`XM4`:`XM6` 14 → 16 as one width (4.635 → 13.710 µm, ratio 1:1:10 and
  I(XM6) = 50 µA preserved); tail group deliberately untouched.
- **(b) complementary PMOS pair** — screened out before fleet submission.
  At SS / −40 °C, `Vth_n + |Vth_p| = 1.732 V` exceeds the 1.62 V supply.
  The sizing calculation predicts a gap in strong-inversion coverage from
  about 0.49 to 0.73 V. Weak-inversion gain and contiguous unity-buffer
  swing through that interval remain unmeasured. The uncertain benefit,
  extra tail current, additional mismatch sources and DR-001 polarity change
  put this candidate outside the bounded fleet screen.

Evidence: 17-point grid (15 paired + the two 1.62 V / −40 °C tuples the issue
added), DR-006 solver settings, batch fleet, one DUT snapshot
(`sha256:8c1160ee…`); records listed in
[`variants/input-stage/records.json`](../../sim/opamp-characterization/variants/input-stage/records.json)
with the DR-013 canonical baselines (`sha256:e954d17d…`); every table in
[`variants/input-stage/report.out.md`](../../sim/opamp-characterization/variants/input-stage/report.out.md)
is printed by `collate.py`, never hand-transcribed. Two infrastructure-only
retries per the plan's retry rule (fleet returned no report; no measured
outcome retried).

## Decision (proposed)

**Keep the canonical design.** The measured candidate improves swing at all
17 points and misses the phase-margin bound at 15. Candidate (b) has only a
hand screen.

At SS / −40 °C / 1.62 V the unity-buffer DC sweep measures **0.2545–1.2029 V**
for the baseline and **0.2249–1.2355 V** for the candidate. Against the
0.072–1.464 V target, the baseline misses the low edge by 0.182 V. The
candidate still misses it by 0.153 V and the high edge by 0.228 V.

The separate ICMR bench measures 0.7168–1.1686 V for the baseline and
0.6659–1.2257 V for the candidate using the 40 dB local-CMRR criterion.
The pair threshold (0.6669 V) estimates the low input common-mode edge at
zero overdrive. Both unity-buffer sweeps track well below that voltage.
On the high side the mirror headroom calculation gives
`Vin_max ≈ VDD − |Vsg3| + Vth2_eff ≈ 1.230 V` at zero mirror overdrive,
using `|Vth_p| = 1.0652 V`. Its agreement with the candidate's ICMR high
edge and the high-side attribution in #181 explain why this sizing move
falls short at the high end. The sweeps measure the residual swing gap for
this candidate. Its division between input- and output-stage limits under
further design changes remains open.

| Row (ratified bound) | baseline worst | candidate worst | verdict |
|---|---|---|---|
| Output swing ≈ 1.392 Vpp | 0.897 V @ SF/−40C/1.62V | 0.9879 V @ SF/−40C/1.62V | **partially closes**: better at 17/17 points (+0.04…+0.14 Vpp); binding SS/−40C/1.62V 0.948 → 1.011 Vpp (72.6% of target); does not close |
| Fall slew ≈ 20 V/µs | 9.127 @ FS/−40C/1.62V | 13.06 @ FS/−40C/1.62V | At −40 °C / 1.62 V the improvement recovers 25.8% of the baseline shortfall to 20 V/µs at SS (11.03 → 13.34), 4.2% at SF (13.87 → 14.13) and 36.2% at FS (9.13 → 13.06). Worse at 11/17 points overall. |
| Phase margin ≥ 60° | 63.94° @ SF/27C, 0/17 below | 55.28° @ SF/27C | **Below 60° at 15/17 points.** With compensation fixed, measured GBW rises 10.2–21.2% across the grid and phase margin falls 7.3–9.1°. The nominal gm/ID sizing change is 17 → 20 (+17.6%). |
| Rise slew ≈ 20 V/µs | 19.79 (≈99%) | 19.46 (97.3%) | Worse at 17/17 points. |
| DC gain ≥ 60 dB | 61.64 | 63.59 | better at 17/17, still met |
| GBW ≈ 16 MHz | 17.92 | 19.98 | better at 17/17, still met |
| Quiescent power ≈ 128.7 µW @ 1.98 V | 131.9 µW | 132.1 µW | unchanged currents; +0.1…+0.8 µW (≤ +0.9%) at every point |
| ICMR window 0.888–1.024 V | covered 17/17 | covered 17/17, wider at all points (+0.03…+0.13 V) | Coverage of the 0.73 V consumer point rises from 15/17 to 17/17. Both baseline misses were at FS / −40 °C, at 1.62 V and 1.8 V. |
| Offset (proposed 0.275 mV σ, DR-009) | 7.30 mV hand-calc 1σ | 4.02 mV hand-calc 1σ | hand calculation only (not simulated here); still ≫ the proposed allocation |

Costs of the move: drawn MOS gate area 153.15 → 206.08 µm² (+34.6%, almost all
in the pair and `XM6`), and the mirror runs sub-|Vth| at TT and hotter corners
(matching/noise at DC unmeasured here).

## Alternatives considered

- **Complementary PMOS pair (b)** — the hand calculation above justified
  stopping before a fleet run. Its swing and slew remain open.
- **Widening the tail group (`XMB1`:`XM5`:`XM7`)** — rejected in the plan:
  `Vov(XM5)` at SS / −40 °C is already ≈ 33 mV (little headroom left), and the
  1:2:10 group move drags the output sink `XM7` out of input-stage scope.
- **A lower-Vth flavor** — out of scope: no committed gm/ID or mismatch data
  for `*_lvt` devices in this repo's evidence base.

## Spec lines affected

None. No target, tolerance or grading rule is edited; `spec/target-spec.md`,
`design/netlist/opamp_core.spice` and every ratified record are unchanged. If
a future record adopts this candidate (or any successor), the rows it would
move are §1's output swing, fall slew rate, phase margin, rise slew rate and
quiescent power rows, and §2's ICMR row.

## Consequences

- The measured swing gap after re-bias is 0.381 Vpp at SS / −40 °C / 1.62 V.
  A topology change considered to recover more high-side headroom would
  require a superseding record under DR-001.
- Standard fall slew stays below target. The earlier in-window step experiment
  (#185) identified output-current limiting at 14/15 paired baseline points.
  The class-AB study (#360) addresses that limit.
- Adopting `icmr-rebias` (not sought here) would require: a compensation
  re-tune (`Rz`/`Cc`) to recover ≥ 60° phase margin at the increased GBW,
  a new canonical netlist, a re-run of every item-5 campaign, a new layout
  (items 2, 3, 4, 7 and 11 are met on the current core), and no power-budget
  change (currents unchanged; ≈ +0.2% quiescent power from the mirror's
  lower |Vov|).

## Open items

- The compensation re-tune that would accompany adoption (PM recovery under
  the wider pair) is deliberately not screened here; the plan's scope was the
  input stage at unchanged passives.
- Offset impact is hand-calculated only (Pelgrom, one local `.op` probe); a
  mismatch Monte Carlo on any adopted variant is a separate campaign
  (DR-011's domain).
- Whether the ratified swing target itself survives contact with a 1.62 V
  rail on this PDK (≈ 86% of rail) is a spec-level question this record does
  not decide; per the no-relaxation rule the target stands.
