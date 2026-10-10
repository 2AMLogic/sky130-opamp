# DR-012: Output-topology comparison for the fall-slew gap — tail clamp vs signal-dependent sink (proposed)

- **Status**: **proposed**. Drafted by the Builder agent for issue #79. It is
  not ratified, and merging the PR that carries it does NOT ratify it or
  complete T1 item 5. Ratification is a separate, operator-approved PR that
  flips this Status line. It changes no target, and no ratified record is
  edited.
- **Date**: 2026-10-10
- **Decided by**: Loom Builder agent, issue #79 (proposal only)
- **Related**: [`DR-001`](DR-001-topology-and-cl.md) (class-A output stage,
  part (c)), [`DR-007`](DR-007-device-resize-gbw-slew-swing.md) (baseline; its
  open item "fall slew rate's structural fix"),
  [`DR-006`](DR-006-ngspice-reltol-policy.md) (solver settings used by every
  record cited), issues #47 (parent), #77, #78, #79, #50/#120 (grid-legal
  canonical widths, deliberately not touched here).

## Context

DR-007 left the SS/−40 °C fall slew rate (11.03 V/µs against ≈ 20) as a
structural problem and named two fixes: a tail clamp or a class-AB output.
Issue #78 measured the tail clamp (negative). Issue #79 measures an output-stage
candidate. Both are built from `design/netlist/opamp_core.spice` at `9fb5db6`
(same base; #120 has not landed), run through the 45-unit DR-006 matrix on the
batch fleet, and compared at each metric's binding corner. The canonical design
and `spec/target-spec.md` are unchanged.

Evidence (all 45-unit unless noted; snapshots under
`sim/opamp-characterization/netlist-snapshots/<id>/`):

- DR-007 baseline: [`20261010-103340-ba1dfa8-0241c1`](../../sim/opamp-characterization/records/20261010-103340-ba1dfa8-0241c1.json)
  (identical to `20261001-074923-c317ff9` at every quoted worst value).
- Tail clamp B (`tail-clamp-vc050.spice`): [`20261010-162948-521c306-f0abf9`](../../sim/opamp-characterization/records/20261010-162948-521c306-f0abf9.json), 45/45.
- Tail clamp A (`tail-clamp.spice`): [`20261010-162249-c8da429-a1db50`](../../sim/opamp-characterization/records/20261010-162249-c8da429-a1db50.json), 44 + 1 unit railed (circuit result).
- Signal-dependent sink (`signal-dependent-sink.spice`): [`20261010-234542-1d6c918-7dfe83`](../../sim/opamp-characterization/records/20261010-234542-1d6c918-7dfe83.json), 45/45, 0 failed
  (screen: [`20261010-234414-b96590d-ea93d0`](../../sim/opamp-characterization/records/20261010-234414-b96590d-ea93d0.json)).
- Sizing, mechanism and costs: [`variants/README.md`](../../sim/opamp-characterization/variants/README.md).

## Decision

**Proposed: carry the signal-dependent sink forward as the only viable output
candidate; do not adopt the tail clamp (either strength). Neither candidate
closes T1 item 5, and this record does not ratify the sink for the design.**

Binding corner per metric (worst value, from `compare.py` over the cited records;
"worst" is the minimum except power, the maximum):

| Metric (target) | DR-007 baseline | Tail clamp B | Tail clamp A | Sink |
|---|---|---|---|---|
| DC gain (≥ 60 dB) | 61.64 dB @ FS/125 | 61.73 dB @ FS/125 | 61.93 dB @ FS/125 (SS/−40 unmeasurable) | 62.53 dB @ FS/125 |
| GBW (≈ 16 MHz) | 17.92 MHz @ SS/125 | 18.48 MHz @ FS/125 | 17.96 MHz @ SS/125 | 17.77 MHz @ SS/125 |
| Phase margin (≥ 60°) | 63.94° @ SF/27 | **56.37° @ SS/27** (8 of 15 miss) | **48.31° @ SS/27** (13 of 14 miss) | 61.41° @ FF/125 |
| Rise SR (≈ 20 V/µs) | 19.88 @ SS/−40 | 19.96 @ SS/−40 | 20.23 @ SS/−40 | 19.87 @ SS/−40 |
| **Fall SR (≈ 20 V/µs)** | 11.03 @ SS/−40 | 10.84 @ SS/−40 | 8.22 @ SS/−40 | **12.03 @ SS/−40** |
| Output swing (≈ 1.39 Vpp est.) | 0.9485 @ SS/−40 | 0 (rule) @ SS, all T | 0 (rule) @ SS, all T | 0.9252 @ SS/−40 |
| Quiescent power (≈ 128.7 µW est.) | 131.92 µW @ FF/125 | 131.93 µW @ FF/125 | 131.93 µW @ FF/125 | **154.9 µW @ FF/125** |

Named points:

| Point | Baseline | Tail B | Tail A | Sink |
|---|---|---|---|---|
| FS/125 °C gain | 61.64 dB | 61.73 dB | 61.93 dB | 62.53 dB |
| SS/−40 °C fall SR | 11.03 V/µs | 10.84 | 8.22 | 12.03 |
| SS/−40 °C swing | 0.9485 Vpp | 0 (rule; 0.359 V unanchored) | 0 (rule; 0.318 V unanchored) | 0.9252 Vpp |
| TT/27 °C fall SR | 14.64 V/µs | 11.77 | 8.77 | 18.63 |

Per point against the baseline (15 points): fall SR is worse at 15 (tail B,
A) vs **better at 15, +1.00…+6.44 V/µs (sink)**; phase margin worse at 15 for all
three, but only the sink stays ≥ 60° everywhere (worst 61.41°).

**Target misses (reported, not hidden).** The sink measures fall SR below ≈ 20
V/µs at 12 of 15 points (met at FF/27, FF/125, SF/125 only), so the fall-SR row
remains **not met**; the worst corner is still SS/−40 °C, where the slew bench's
low level lies below the input pair's ICMR low edge (#78), a limit an
output-stage change does not address. Quiescent power is 17 % above the row's
≈ 128.7 µW estimate (the baseline was already +2.5 %), so that row, which held
for the baseline, would be **exceeded**. Phase margin and gain stay met. No
unit failed in any sink record. The tail-clamp misses are target failures (and
one circuit-railed unit in A), not simulation failures.

**Cost of the sink (quantified, not post-layout).**

- Quiescent power: +15.6…+23.0 µW across the grid (+19.0 µW at TT/27 °C, +10.6 µA);
  +17.4 % at the binding corner. Design intent was ≈ 9.5 µA (replica leg 5 µA +
  `I_C` leg 4.5 µA); the measurement matches. The tail clamp costs ≤ 0.7 µW.
- Drawn gate area (ΣW·L of MOS gates, no layout): sink +124.63 µm² (+81 % of the
  baseline's 153.13 µm²), of which `XMS` alone is 93.8 µm². Tail clamp +148.75 µm²
  (A, +97 %) or +49.78 µm² (B, +33 %).
- Added devices: six (sink), one (tail clamp). All new widths on the 0.005 µm
  grid; the six inherited off-grid widths are unchanged and belong to #50/#120.

**Why the sink over the tail clamp, and why not "adopt".** The sink is the only
candidate that moves the fall-SR row in the right direction anywhere, and the
only one that keeps phase margin ≥ 60°. The tail clamp reduces fall SR, swing and
phase margin at every point. Against that, the sink does not meet the target,
and costs power the current estimate does not have room for. Whether to accept
that power, or to trim the `I_C` leg (a follow-on sizing pass), is the
ratifying operator's call and is **not decided here**.

**What ratification would supersede.** If ratified and adopted into the design,
this record would supersede **only DR-001 part (c)**'s "class-A common-source
second stage loaded by an NMOS constant-current sink" for the *sink side*:
the output sink would no longer be a purely fixed `M7`. It would also require
a new sizing/power record revising DR-007's `I_Q = 65 µA` budget and the
quiescent-power row. DR-001's PMOS common-source gain device, Miller `Cc`/`Rz`
structure, input-pair polarity and the `CL = 2 pF` target would remain. This
record does not edit DR-001, DR-007 or any ratified record.

## Alternatives considered

- **Tail clamp** (#78, candidates A/B): rejected on measured evidence; worse fall
  SR, swing and PM at all 15 points, plus a hard low-side floor at SS.
- **Level-shifted follower-driven sink**: screened by local single-corner probes
  only (not a record); it never turned on, because `d2` moves ≈ 0.1 V in a fall
  and sits at a PVT-dependent 0.47–0.82 V. Preserved in `variants/README.md`.
- **Neither**: honest default if the power cost is unacceptable; fall SR stays at
  DR-007's measured values.
- **A full class-AB redesign**: not attempted; the sink is a smaller change that
  already shows the direction.

## Spec lines affected

None changed. Rows that would be re-opened on adoption: fall slew rate (still
partial), quiescent power (≈ 128.7 µW estimate exceeded), and DR-001 part (c)
as above. `spec/target-spec.md` is unchanged by this record.

## Consequences

- If adopted: fall SR improves by 1.0–6.4 V/µs, rises are unchanged (≤ 0.064
  V/µs lower), PM drops 1.6–2.7° (still ≥ 60°), swing is unchanged except at the
  coldest SS/SF points, power +17 %.
- Not measured: offset (the sink was designed to carry ≈ 0 static current, but
  the `I_C`/`I_6c` mismatch margin was only checked at the measured points),
  noise, PSRR, CMRR, ICMR, step response, and Monte Carlo mismatch of the
  replica (the 10 % `I_C` margin is a design choice, not a computed tolerance).
  Those spec rows stay open.
- The new devices contribute only to the sink path; the canonical netlist is
  unchanged.

## Open items

- Ratification decision and, if accepted, the power budget revision.
- Whether the `I_C` leg (4.5 µA) can be dropped or shared to recover ≈ 8 µW.
- The remaining ≈ 8 V/µs gap at SS/−40 °C is an input-range effect (bench low
  level below the pair's ICMR low edge); an output-stage change cannot close it.
- #50/#120: grid-legal canonical widths; re-baseline this comparison if they land
  first.
- Mismatch Monte Carlo of the replica/mirror margin; offset impact.
