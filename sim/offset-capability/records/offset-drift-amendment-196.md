# Costed continuation plan for B2/B3/B4 (#196) — PROPOSED, planning only

Machine-readable plan: [`offset-drift-plan-196-amendment.json`](offset-drift-plan-196-amendment.json) (2026-11-02, base `dcbe083`).
Original plan, ledger, B0–B4/P0 records and study are unchanged append-only history
([plan](offset-drift-plan-196.json), [study](offset-drift-study-196.md),
[result](20261011-233532-drift-drift196-1e74b9.drift.json)).

**Nothing here is approved or executed.** No simulation, capacity probe, retry reset or spending is authorized by this
document. Accepting the plan does not satisfy #196's four-condition acceptance criteria and does not close it. B1 keeps its
conditional FAIL_SCREEN (sigma 1.006 mV, CI [0.883, 1.169] vs the 0.19 mV screen); B2–B4 stay NOT_MEASURED; the 0.275 mV
allocation stays proposed; no trim architecture is adopted.

## What would be measured

| Step | Condition (TT, mismatch seed 20261085) | Samples | Attempts (max) |
|---|---|---|---|
| PE1 (probe) | −40 °C / 1.62 V, ID `20261085/0` only | 1 | 2 |
| B2 | −40 °C / 1.98 V | 100 | 2 |
| B3 | 125 °C / 1.62 V | 100 | 2 |
| B4 | 125 °C / 1.98 V | 100 | 2 |

300 environmental samples, IDs `20261085/0..99` in every batch. The existing REF batch (27 °C / 1.8 V, job
`klt-sim-59f75072ec89`) is the reference: same DUT snapshot, bench, models library and seed, so **no new reference batch**
is proposed. Residual = Vos(condition, id) − Vos(REF, id), joined by ID.

## Pinned identities (verified against `origin/main` @ `dcbe083`, 2026-11-02)

- DUT `design/netlist/opamp_core.spice` = snapshot `dut-drift196/opamp_core.spice`, `sha256:e954d17d…ce79` (re-derived with `sha256sum` today; equal to the plan's value).
- Bench `dut-drift196/offset_dc.spice` `sha256:0bafe511…c41d`; models lib `sha256:17c208a6…5f64`; ngspice 46; runner klt 0.5.0 (`runner_compatibility: mismatch` with client 0.7.0).
- Hashes of the original plan, study, drift record and the accepted B0/P0/B1 requests and summaries are in the JSON.
- **Client pin**: accepted jobs used client klt 0.7.0. This host has 0.8.1.dev; it must not be changed. Execution would use `uvx --from "klayout-tools==0.7.0" klt …`. PE1 exists partly to confirm that this client/runner/fleet combination still reproduces accepted evidence.

## Pairing-evidence design

Equal seeds and same-condition replay are necessary, not sufficient. Required for each condition: (1) echoed `rndseed`,
`process_seed`, `mismatch_seed` equal REF's for all 100 IDs; (2) PE1 reproduces the accepted B1 sample 0 within 40 µV;
(3) runner/ngspice/models/bench/DUT provenance identical to the accepted jobs; (4) paired-residual sigma < 0.5 × REF sigma
(< 3.78 mV; independent draws would give ≈ 10.7 mV). Limit: (1)–(3) show inputs and environment are held constant;
(4) is the only check on in-simulator draws and is loose (B1 was 13% of REF sigma), so a pass leaves open that part of a
residual is decorrelation, i.e. results are upper-leaning estimates of drift. A device-level realization comparison would be
stronger but no tool exposing per-device draws is established — **an unresolved capability, not a proposed step.**
If any of (1)–(4) fails or cannot be evaluated: CAPABILITY GAP, no drift verdict for that condition, and B1 remains
conditional on pairing.

## Cost

Basis: elapsed seconds in the accepted records only (spot `c7i.4xlarge`/`m7i.4xlarge`, 16 vCPU, concurrency 1).

| Item | Basis | Estimate |
|---|---|---|
| 100-sample batch | B0_ref 822 s, B1 610 s | 610–822 s per executing attempt |
| PE1 (n=1) | P0_replay 43 s | ≈ 45 s per attempt |
| Expected (each step succeeds first time) | 3 × 610–822 + 45 | ≈ 1.9–2.5 ks ≈ 31–42 min instance time |
| Ceiling (every attempt executes to completion) | 6 × 822 + 2 × 45 | ≈ 5.0 ks ≈ 84 min instance time |
| Requests / sample runs | | ≤ 8 requests; ≤ 301 unique, ≤ 602 sample runs incl. retries |

Elapsed time excludes launch, upload and collection overhead (not recorded per attempt) and excludes wait for capacity.
Refused attempts execute nothing but, under this proposal, still consume an attempt.

**Unresolved costs**: (a) dollar cost — records carry no spot price or billing data, so it is not estimated; (b) capacity wait,
which in the original run was ≥ 15 min of spacing per batch with no success; (c) sample runtime may differ at 125 °C
(only −40 °C and 27 °C have been timed); (d) runner/image drift since 2026-10-11.

## Capacity prerequisites and how to verify without submitting

Original failure: 3 × 3 attempts refused with `10..12 instance(s) already running + 1 requested exceeds
BATCH_MAX_CONCURRENT_INSTANCES=8`, caused by concurrent sweeps on a shared fleet. Prerequisite for starting any step: fewer
than 8 instances running at submission time and headroom for 1.

Verification without an unapproved submission: `klt sim --job-status` reads one existing job and reports nothing about fleet
occupancy, and a submit would be the unapproved action. **No read-only occupancy check is established in the tools I inspected;
this is an open item.** Proposed gate G0: the approving operator (or a fleet-side read-only listing they own) confirms
running-instance count < 8 immediately before the decision, and the decision records that observation. The 0.8.1 client
documents `--wait-for-capacity` and `--capacity-retries`; their presence in the pinned 0.7.0 client is not verified, and any
wait must be bounded (proposed ≤ 900 s per attempt) and must still count the refusal as an attempt.

## Finite limits and stop rules

Ceilings: 3 batches, 300 unique environmental samples, 1 probe, ≤ 2 attempts per batch/probe, ≤ 8 requests, ≤ 602 sample
runs, no extra reference/seeds/corners, no sixth batch. Failure accounting is the original plan's: failed samples are listed
with ID and reason, never zero-filled or redrawn; requested/returned/valid-pair/failed counts are reported separately;
< 80 valid pairs is INCONCLUSIVE; a reference failure invalidates that ID everywhere. Stop rules (full list in the JSON):
no step without a later explicit decision naming this plan's hash; PE1 failure or any provenance/DUT hash difference stops the
campaign (CAPABILITY GAP, no re-baselining, no pooling); attempt or request ceiling reached ends submission; a failed submit
is reported, never run locally.

## Decision requested later (not now)

Whether to approve the ceilings above, who confirms G0, and whether to accept the PE1 probe. The old three-attempt allowances
remain exhausted until then.

Tool friction already tracked at `2AMLogic/klayout-tools` (#3043, #2869, #2948, #2967, #2929, #2899). The missing read-only
fleet-occupancy check is not in that list; not filed because I did not confirm it is absent from the docs, only from the
CLI help I read.
