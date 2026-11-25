# DR-018 — Sampled input noise and the thermal-floor target

- **Status** — Proposed in PR #355. Ratification requires fresh EE and market reviews on the reviewed revision and operator approval to merge. The proposal keeps compliance with the DR-003 thermal-floor target open.
- **Date** — 2026-11-19, revised 2026-11-25 following EE review.
- **Scope** — Input-referred noise on the schematic unity-gain follower with a 2 pF load. The target is approximately 30 nV/√Hz, with a separately reported 100 Hz–1 MHz band. [DR-003](DR-003-target-spec-ratification.md) · [Issue #274](https://github.com/2AMLogic/sky130-opamp/issues/274)

## Decision proposed

Retain the minimum of the nine reported total input-noise densities from 100 kHz through 10 MHz as a diagnostic. Compare that scalar with 30 nV/√Hz inclusively on each paired PVT corner. Keep the thermal-floor row a declared gap in T1 item 5. Issue #274 proposed using the minimum as a proxy for the thermal floor. The source comparison below found that the proxy misses the stated accuracy at ten corners. A passing diagnostic therefore gives no thermal-floor signoff. A missing scalar is a measurement error.

The November fleet envelope records 4 corners within the diagnostic limit, 11 above and 0 errored. The four within it are TT, FF, SF and FS at −40 °C. SS at −40 °C also selects the 10 MHz endpoint and measures 30.49 nV/√Hz. The worst is SS at 1.62 V and 125 °C, 47.25 nV/√Hz. Nominal TT at 1.80 V and 27 °C measures 35.75 nV/√Hz. The envelope preserves the original experiment's row tag. New requests omit that tag, and the signoff manifest excludes the diagnostic envelope. [Fleet envelope](../../manifests/envelopes/20261119-030444-02cc663-b6d61e-noise.klt.json)

## What the window selects

The bench reports four spots per decade. The November calculation takes the minimum of the nine reported spots from 100 kHz through 10 MHz, including both endpoints. The 100 kHz lower edge lies **below every measured crossover** (285–681 kHz, estimated at twice the sampled minimum power density). All 15 minima lie **above** the 1 MHz band edge. Ten select 5.623 MHz and all five cold corners select 10 MHz. Restricting the same calculation to reported spots from 100 Hz through 1 MHz gives 35.69–53.21 nV/√Hz, with zero corners within 30 nV/√Hz. The separately integrated band noise spans 62.49–82.19 µV RMS. DR-003 specifies no integrated RMS limit. [Fleet spectra](../../sim/opamp-characterization/records/20261119-030444-02cc663-b6d61e-noise.csv)

## Thermal contribution at the selected spots

We replayed the November bench with ngspice 47 and its recorded SKY130A open_pdks revision `f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7`. The grid pairs FF with 1.98 V, SS with 1.62 V and TT/SF/FS with 1.80 V at −40, 27 and 125 °C. Enabling the per-source noise summary in squared units gives the modeled output power spectral density of each BSIM4 channel, device resistance, resistor and flicker source. We summed the thermal terms and checked that thermal plus flicker accounts for total output power within one part per million. Multiplying the total input-referred density by the square root of the thermal power fraction refers the thermal component through the same signal gain.

For this proxy check we used a **0.5 dB amplitude-error budget** for each of two effects. This bounds the error of reading a total density as thermal to about 6% (at least 89.1% thermal power), and bounds the change on moving one published frequency step in either direction to the same 6%. This is a measurement-accuracy criterion independent of the 30 nV/√Hz target and its pass count. The upper neighbor of a 10 MHz minimum is 17.78 MHz. That spot is used only to test flatness.

- **Local frequency dependence** met the budget at 15/15 corners. The larger of the two neighbor deviations was 0.17–0.29 dB.
- **Source purity** met the budget at 5/15 corners, all at 125 °C. Flicker supplied 9.06–14.32% of the power at the selected spots. Total density exceeded thermal-only density by 0.41–0.67 dB. All five 10 MHz endpoint minima missed the purity budget (0.53–0.59 dB).
- At SS, −40 °C, the source separation puts the thermal component below 30 nV/√Hz while the total sampled minimum exceeds 30. The distinction changes how one would classify a corner even with an identical numerical limit.

The per-corner CSV reports selected frequency, total and thermal input densities, flicker fraction and both errors. The replay checks each search spot and its upper neighbor against the fleet CSV to its printed precision. The results describe deterministic pre-layout model noise. [Source breakdown](../../sim/opamp-characterization/records/20261125-noise-floor-source-check.csv) · [Replay script](../../sim/opamp-characterization/bin/check_noise_floor.py)

## Fixed-frequency comparisons and remaining decision

At TT, 1.8 V and 27 °C the follower measures **541.18 nV/√Hz at 1 kHz, 199.77 at 10 kHz and 42.42 at 1 MHz**, with 70.11 µV RMS integrated over the band. For scale, TI specifies a typical 7 nV/√Hz at 10 kHz for the 20 MHz OPA320 at 25 °C with a 10 kΩ load. The simulated block is about 29 times higher at that same frequency. The devices and conditions differ, and a packaged-part typical gives no 15-corner guarantee. Neither the quietest high-frequency spot nor the available consumer requirements justify accepting the in-band performance. [TI OPA320 electrical characteristics](https://www.ti.com/lit/ds/symlink/opa320.pdf) · [Target spec and consumers](../target-spec.md)

A future grading proposal needs to identify the physical quantity and frequency conditions a consumer requires, then justify the extraction accuracy. The observed 4/15 diagnostic and the measured in-band results remain available for that decision. Neither a per-spot maximum nor an integrated voltage limit has been adopted.
