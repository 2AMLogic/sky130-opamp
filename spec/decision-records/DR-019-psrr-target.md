# DR-019: Proposed DC power-supply rejection target

- **Status**: **proposed**. The PSRR row stays OPEN under DR-003. Merging PR #287 does not ratify this proposal. Ratification requires separate operator approval recorded by changing this status to `ratified` and adopting the target in §2 and §5 of the spec.
- **Date**: 2026-11-14, revised 2026-11-26 following the [operator ruling on PR #287](https://github.com/2AMLogic/sky130-opamp/pull/287#issuecomment-7177870533).
- **Decided by**: Proposal for operator review, issue #282. Earlier versions of PR #287 called this record DR-015. That number now identifies the input-stage study.

## Context

Issue #54 introduced separate supply-AC benches for VDD and VSS. Its October
record predates the DR-013 sizing and lacks a DUT hash. Issue #282 repeated
both benches on the canonical netlist. Each drives one rail of a unity-gain
buffer, holds the input at AC ground and measures supply feedthrough. The
paired grid covers TT, FF, SS, SF and FS at −40, 27 and 125 °C, with 1.62 V
at SS, 1.98 V at FF and 1.80 V elsewhere. Both runs completed at all 15
points. [DUT-bound campaign record](../../sim/opamp-characterization/records/20261114-032827-96d9fbc-288af8-psrr-noise.json)

## Decision

Propose **DC PSRR ≥ 70 dB on each rail at every point of the paired grid**.
TI's LMV951 is a 1.8 V op-amp comparator identified in the market review.
Its 1.8 V electrical table specifies a 70 dB minimum at 25 °C and a 67 dB
minimum at the temperature extremes for a positive-supply sweep from 1 V to
1.8 V with the input common mode fixed at 0.5 V. We adopt the room-temperature
minimum as a design goal for both supply pins across our grid. The extension
to VSS and to all corners is our engineering choice. [TI LMV951 datasheet, §6.6, p. 5](https://www.ti.com/lit/ds/symlink/lmv951.pdf)

Use the 0.1 Hz shelf (`psrr_dc_0p1hz_db`) as the bench's DC proxy.
The separate `psrr_window_min_db` metric reports the lowest rejection
from 0.1 Hz through 1 kHz. The proposal places no floor on that AC window.

| Rail | Binding corner | DC proxy | Gap to 70 dB DC | DC points below 70 dB | DC–1 kHz minimum |
|---|---|---:|---:|---:|---:|
| [PSRR+](../../sim/opamp-characterization/records/20261114-032827-96d9fbc-288af8-psrr-vdd.csv) | FS / 125 °C / 1.80 V | 63.5971 dB | 6.40 dB | 15/15 | 63.57 dB |
| [PSRR−](../../sim/opamp-characterization/records/20261114-032827-96d9fbc-288af8-psrr-vss.csv) | SS / −40 °C / 1.62 V | 54.9009 dB | 15.10 dB | 4/15 | 54.90 dB |

## Alternatives considered

- The previous 50 dB floor and 60 dB stretch over DC–1 kHz were chosen from this design's measurements. Neither value has an independent ripple allocation for the amplifier.
- A band-wide goal, or different limits for the two rails, would need a frequency- and rail-specific basis. The bandgap's 60 dB DC–1 kHz requirement applies to its complete loop at 3.3 V. Its allocation to this amplifier is unknown. [Consumer requirements in the target spec](../target-spec.md#consumers-2am-reuse-rule-9--this-blocks-end-of-the-edge)

## Spec lines affected

The §2 PSRR row records both measured window minima and their binding corners.
The target and stretch stay unset. Section 5 lists PSRR as OPEN under DR-003.
The figure manifest binds both window minima to the DR-013 DUT and its CSVs.

## Consequences

The current sizing misses the proposed DC goal on both rails. The design
follow-up tracks the two shortfalls and calls for rerunning both benches on
a candidate while checking the ratified rows for regressions. [Design issue #396](https://github.com/2AMLogic/sky130-opamp/issues/396)

## Open items

The supply-AC benches use an ideal `ibias` current source. The pre-layout
schematic excludes bias-generator supply coupling, extracted parasitics, rail
IR drop, and package and board impedances. The grid also excludes mismatch.
Rejection with those effects included requires further characterization.
