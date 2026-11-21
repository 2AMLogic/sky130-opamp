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
- **(b) complementary PMOS pair** — rejected by hand calculation before any
  fleet request: `Vth_n + |Vth_p| = 1.732 V > VDD = 1.62 V` at SS / −40 °C
  leaves a dead zone ≈ [0.49, 0.73] V where neither pair conducts; the
  `dc_swing` metric's contiguous mid-supply run stays NMOS-limited, so the
  binding-corner swing row cannot improve at all, while a second tail (power),
  a doubled offset budget (Pelgrom), GBW/PM spread in the overlap region and a
  DR-001 supersession all pay. It is *not* carried forward even as a proposal.

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

**Negative structural result, with a measured partial improvement that is not
adoptable as-is.** No candidate is carried forward for adoption, and no target
is edited.

1. **The swing row is structurally unclosable at SS / −40 °C / 1.62 V by any
   re-bias of this topology family.** Hand-calculated ceilings from the
   committed gm/ID sweep, stated up front in the plan and confirmed by
   measurement: the NMOS pair's `Vth_n` (0.6669 V at that corner) floors the
   low edge ≥ 0.595 V short of the ratified 0.072 V, and the PMOS mirror's
   `|Vth_p|` (1.0652 V) caps the high edge ≈ 1.230 V, ≥ 0.234 V short of the
   ratified 1.464 V. Closure of this row requires an input-topology change
   (a DR-001-domain decision), not a sizing pass.
2. **`icmr-rebias` measurably moves both rows at their binding corners but
   breaks the phase-margin row**, so it is recorded, not proposed for
   adoption:

| Row (ratified bound) | baseline worst | candidate worst | verdict |
|---|---|---|---|
| Output swing ≈ 1.392 Vpp | 0.897 V @ SF/−40C/1.62V | 0.9879 V @ SF/−40C/1.62V | **partially closes**: better at 17/17 points (+0.04…+0.14 Vpp); binding SS/−40C/1.62V 0.948 → 1.011 Vpp (72.6% of target); does not close |
| Fall slew ≈ 20 V/µs | 9.127 @ FS/−40C/1.62V | 13.06 @ FS/−40C/1.62V | recovers the input-range share at the two −40 °C/1.62 V corners (SS: 11.03 → 13.34, +2.31 = 21% of that corner's gap; FS: 9.13 → 13.06, +3.94 = 48%); **worse at 11/17 points** (≈ −0.3 V/µs); does not close |
| Phase margin ≥ 60° | 63.94° @ SF/27C, 0/17 below | 55.28° @ SF/27C | **BREAKS at 15/17 points** (−7.3…−9.1° everywhere; gm1 +21% without compensation re-tune) |
| Rise slew ≈ 20 V/µs | 19.79 (met, ≥99%) | 19.46 (97.3%) | worse at 17/17; no longer ≥ 99% of target at every point |
| DC gain ≥ 60 dB | 61.64 | 63.59 | better at 17/17, still met |
| GBW ≈ 16 MHz | 17.92 | 19.98 | better at 17/17, still met |
| Quiescent power ≈ 128.7 µW @ 1.98 V | 131.9 µW | 132.1 µW | unchanged currents; +0.1…+0.8 µW (≤ +0.9%) at every point |
| ICMR window 0.888–1.024 V | covered 17/17 | wider at 17/17 (+0.03…+0.13 V); 0.73 V consumer point now covered at 17/17 (baseline missed it at all three FS corners) | improved, not a ratified miss |
| Offset (proposed 0.275 mV σ, DR-009) | 7.30 mV hand-calc 1σ | 4.02 mV hand-calc 1σ | hand calculation only (not simulated here); still ≫ the proposed allocation |

Costs of the move: drawn MOS gate area 153.15 → 206.08 µm² (+34.6%, almost all
in the pair and `XM6`), and the mirror runs sub-|Vth| at TT and hotter corners
(matching/noise at DC unmeasured here).

## Alternatives considered

- **Complementary PMOS pair (b)** — rejected by hand (dead zone at the binding
  corner; see Context). No fleet request spent.
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

- The swing row's remaining gap at SS / −40 °C / 1.62 V (≈ 0.38 Vpp after this
  candidate) is structural for the single-NMOS-pair family; closing it is a
  topology decision under DR-001's superseding-record rule, not another
  sizing pass. This record is the evidence base for that statement.
- The fall-slew row's residual after the input-range share is recovered is
  output-current limited (#185 at 14/15 paired points) — the class-AB study
  (#360) is the live lever there, not further input-stage work.
- Adopting `icmr-rebias` (not sought here) would require: a compensation
  re-tune (`Rz`/`Cc`) to recover the ≥ 60° phase margin lost with gm1 +21%,
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
