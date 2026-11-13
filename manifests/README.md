# Block manifest and tier-verdict record

This directory holds this block's `klt signoff` input and its committed
output — the machine-readable replacement for a hand-maintained
gap-to-T1 checklist. The gap-to-T1 tracker ([#3](https://github.com/2AMLogic/sky130-opamp/issues/3))
points here as the **verdict of record**; the fleet roll-up
([2AMLogic/2am#956](https://github.com/2AMLogic/2am/issues/956)) consumes
the block manifest, and `block: sky130-opamp` is how this block's row is
identified there.

## Files

- **`sky130-opamp.json`** — the block manifest: this block's identity and
  kind, plus per-T1-item evidence citations for
  [`klt signoff --manifest`](https://github.com/2AMLogic/klayout-tools/blob/main/docs/cli/signoff.md).
  - `kind: analog` is confirmed against the block, not taken from the
    filing issue: a two-stage Miller-compensated operational amplifier,
    no digital or mixed-signal partition (see the tracker's "Block kind"
    section and `design/`).
  - `evidence` holds citations for items 9 and 10 (issue
    [#223](https://github.com/2AMLogic/sky130-opamp/issues/223)), 8 (issue
    [#43](https://github.com/2AMLogic/sky130-opamp/issues/43)), 1 (issue
    [#55](https://github.com/2AMLogic/sky130-opamp/issues/55)), 2, 3, 4, 11
    (issue [#222](https://github.com/2AMLogic/sky130-opamp/issues/222)), 7
    (issue [#247](https://github.com/2AMLogic/sky130-opamp/issues/247)) and 5
    (issue [#246](https://github.com/2AMLogic/sky130-opamp/issues/246); a list
    of citations plus the top-level `spec_rows."5"` row set). Item 6 is the only
    uncited T1 item. Each item's citation — and, for item 6, the reason it stays
    uncited — is recorded per item:
    - **Item 1 (design sources)** cites
      [`design/netlist/opamp_core.sources.evidence.json`](../design/netlist/opamp_core.sources.evidence.json)
      — a generic envelope (`"t1_item": 1`) whose `provenance.input` is
      [`design/netlist/opamp_core.pair.json`](../design/netlist/opamp_core.pair.json),
      a record pinning the sha256 of `design/opamp_core.sch` and
      `design/netlist/opamp_core.spice`. The real gate is
      [`.github/workflows/design-sources.yml`](../.github/workflows/design-sources.yml):
      `design/bin/netlist_check.py` re-runs headless xschem and fails when the
      regenerated netlist differs from the committed one (or the pair record is
      stale), with negative controls in `design/bin/test_netlist_check.py`.
      Under the pinned klt 0.7.0 this generic citation grades item 1 `met`.
      (Historical: klt 0.5.0 rendered a generic item-1 citation
      `wrong_kind`, which is why the pin was first raised to 0.7.0.) Like item 8,
      `klt signoff` never re-hashes the cited input
      ([klayout-tools#2196](https://github.com/2AMLogic/klayout-tools/issues/2196)),
      so `signoff.yml`'s re-hash step plus the design-sources workflow are the
      real freshness gates; a tool-produced envelope for this item is requested
      in [klayout-tools#2844](https://github.com/2AMLogic/klayout-tools/issues/2844).
      To refresh after a design change: regenerate the netlist (design/README.md),
      run `python3 design/bin/netlist_check.py --write-record`, copy the new
      record hash into the envelope's `provenance.input.content_hash` and the
      manifest's item-1 `content_hash`, then regenerate the signoff record.
    - **Item 8 (characterization report)** cites
      [`sim/opamp-characterization/records/20261009-103006-566b9a5.characterization.json`](../sim/opamp-characterization/records/20261009-103006-566b9a5.characterization.json)
      — a **generic evidence envelope** (`"kind": "generic"`,
      [klayout-tools#1152](https://github.com/2AMLogic/klayout-tools/issues/1152))
      wrapping the committed ICMR/CMRR characterization record
      [`20261009-103006-566b9a5.md`](../sim/opamp-characterization/records/20261009-103006-566b9a5.md)
      (issue #53; it carries the six earlier rows forward from record
      `20261001-074923-c317ff9`).
      Generic evidence is currently cited on items 1, 8, 9 and 10,
      and nowhere else. Item 8's checklist text names no `klt` verb, so it
      is reachable with no layout and no `klt sim` port. (Historical, klt
      0.5.0: item 8 was the only item accepting generic evidence; that no
      longer describes the pinned 0.7.0, which grades the item-1 generic
      citation `met`. Re-check the pinned klt's behavior for an item before
      citing generic evidence on it.)
      **Read that envelope's `summary`, not just the `met` row**: `klt
      signoff` grades item 8 on the envelope's `status` alone and cannot
      check coverage, so the coverage disclosure (8 of
      `spec/target-spec.md` §2's 12 rows characterized, 4 uncharacterized
      and named, 2 of the characterized 6 measuring below target at their
      binding corner) lives in that `summary` field and is
      claimant-enforced — the same discipline item 3's DRC-coverage and
      item 4's power-connectivity caveats already carry. The `summary`
      is quoted in `sky130-opamp.signoff.json`'s citation block under
      klt 0.7.0 (`artifact_binding.summary`); the envelope file remains
      the source.
    - **Items 2, 3, 4 and 11 (assembled core layout)** cite the tool-produced
      envelopes of [`layout/opamp_core/`](../layout/opamp_core/README.md)
      (issue [#222](https://github.com/2AMLogic/sky130-opamp/issues/222)), all
      pinned to the stream's `provenance.input.content_hash`
      (`opamp_core.gds`): item 2 cites `extract.json` (`klt extract`), item 3
      `drc.json` (`klt drc`), item 4 `lvs.json` (`klt lvs` against
      `opamp_core.ref.spice`, the whole 10-device netlist), and item 11 the
      compound set `erc.json` + `lvs.json` (`klt erc` on
      [`erc-spec.json`](../layout/opamp_core/erc-spec.json)). Verdicts come
      from `klt signoff`; nothing is hand-marked. What each `met` does and
      does not say:
      - **Item 3 coverage, quoted from `drc.json`'s `coverage`**:
        `layers_in_stream_without_rules` = `66/13, 67/5, 68/5, 69/5, 70/5,
        71/5` (label/pin layers); `rules_skipped` = 52 rules, all
        `no_applicable_geometry` for layers the stream does not draw
        (`areaid_re`, `capm2`, `dnwell`, `hvi`, `hvntm`, `hvtp`, `hvtr`,
        `lvtn`, `met5`, `mf`, `ncm`, `nsm`, `pad`, `pwbm`, `pwde`,
        `pwell_rs`, `tunm`, `uhvi`, `vhvi`, `via4`, `vpp`); `deck_scope` =
        `cap2m, capm, ct, difftap, li, licon, m1, m2, m3, m4, m5, nwell, poly,
        via, via2, via3, via4, x`. The deck holes `layout/README.md` already
        names stand: it has no implant, `npc` or poly-end-cap rules. The
        Magic `drc(full)` run alongside **fails** (2 errors, rule `poly
        contact extends poly resistor by < 2.16um`, inherited from
        `opamp_comp`; `layout/opamp_core/magic-signoff/magic.json`). So item
        3 `met` means klt's curated deck is clean, **not** that the layout is
        foundry-DRC-clean.
      - **Item 4**: `power_connectivity.status` is `unchecked` (the
        `subckt-call` reference carries its own supply pins, so they take
        part in the ordinary compare) and `body_verification.status` is
        `verified` (0 devices needing a check), both as reported in
        `lvs.json`. netgen on the Magic extraction matches circuits but with
        differing pin lists (`magic-signoff/netgen.out`).
      - **Item 11**: `vdd` and `vss` each resolve to one island with zero
        unlabelled conductor on their owned roles (`met1`, `met4`); the
        n-well tap tie (`nwell_tap_vdd`, the dedicated `tap` layer under
        `nsdm`, both wells) is checked with zero `erc.missing_tie`;
        `erc_coverage.skipped` is empty. **The p-substrate tie is not
        graded**: the stream draws no pwell, so it is disclosed
        (`ties_disclosure.undeclared_classes`, `p-substrate`) rather than
        declared; the signoff citation carries it as
        `disclosed_undeclared_tie_classes`. The declaration was
        negative-controlled: pointing the tie at `vss` reports
        `erc.missing_tie`.
    - **Item 7 (post-layout)** cites the `klt pex` report
      [`20261027-pex-opamp_core.pex.json`](../sim/opamp-characterization/records/20261027-pex-opamp_core.pex.json)
      (issue [#247](https://github.com/2AMLogic/sky130-opamp/issues/247)): 150
      `delta[]` rows (10 measurements x 15 PVT points), all `pass`, run with
      `--measure-command` over `sim/opamp-characterization/bin/pex_measure.py`
      (it drives `pvt_sweep.py --fleet --backend batch`; records
      `20261027-011621-653a541-9c077d` schematic leg, `20261027-012720-653a541-83f9a1`
      extracted leg). Rows: DC gain, GBW, phase margin, quiescent power, rise/fall
      slew, output swing (`vpp_v`), ICMR low/high/width. What the `met` does and
      does not say:
      - **`body_bias.status` is `biased`** (0 unbiased devices, 0 unbiased nets), so
        the extracted numbers are comparable to the schematic leg.
      - **`extraction.model` limits** (quoted from the report): quasi-static, one
        frequency-independent R and C per net, lumped star resistance (no
        `--distributed-rc`), vertical-overlap coupling only (no lateral
        coupling: no `--critical-net` was named), no fringe shielding, substrate
        tied through 1e12 ohm. The citation is no evidence about frequency-dependent
        or lateral-coupling effects.
      - **Largest delta per row** (schematic -> extracted): gain +2.24 % (FS/-40 C),
        GBW -3.11 % (SS/-40 C), phase margin +4.11 % (SF/-40 C), Pq +3.68 %
        (SF/-40 C), rise slew +1.05 %, fall slew -9.57 % (SS/-40 C), output swing
        -5.92 % (SS/-40 C), ICMR low -1.21 %, ICMR high -9.05 % and ICMR width
        -17.10 % (SF/-40 C). `met` is the tool's grading that the run completed with
        a biased netlist; it is **not** a claim that every row stays within its spec
        target after extraction. Spec rows are not re-graded or loosened here; the
        extracted ICMR window (0.586 V narrowest) must be read against the target
        window in `spec/target-spec.md`.
      - **Attribution (device-only split).** The rerun
        [`20261030-pex-opamp_core-device-only.pex.json`](../sim/opamp-characterization/records/20261030-pex-opamp_core-device-only.pex.json)
        (`klt pex --device-only-leg`, same layout, same `--measure-command`; 150
        rows, all with `representation_delta_pct` and `parasitic_delta_pct`; records
        `20261030-231341-26b1547-72e42c` schematic, `20261030-233051-26b1547-d56adc`
        extracted, `20261030-234100-26b1547-66bd4e` device-only, all on the batch
        fleet) re-measures the same layout on a third, parasitic-free netlist (same
        fingered devices and AS/AD/PS/PD, no R/C). Its schematic and extracted
        totals reproduce the figures above. `model_mismatch` still stands (35 vs 10
        instances, `res_high_po` vs `res_high_po_1p41`), so the split is: at each
        row's worst-total corner, representation / parasitic (percent, of the total):
        ICMR width -17.10 (SF/-40 C) = -15.80 / -1.55; ICMR high -9.05 (SF/-40 C) =
        -8.47 / -0.64; fall slew -9.57 (SS/-40 C) = -2.41 / -7.34; output swing
        -5.92 (SS/-40 C) = -5.05 / -0.92; GBW -3.11 (SS/-40 C) = -2.31 / -0.82; phase
        margin +4.11 (SF/-40 C) = -0.12 / +4.23; Pq +3.68 (SF/-40 C) = -0.01 / +3.69;
        ICMR low -1.21 (FF/27 C) is representation-dominated
        (-1.43 / +0.22). **Finding:** the ICMR window and output-swing
        deltas are device representation, not R/C; the phase-margin and Pq deltas
        are parasitic; fall slew is mostly parasitic (-7.34 of -9.57) with a
        representation share; gain is representation (+2.22 of +2.24 at FS/-40 C).
        At SF/125 C the ICMR width terms are opposite-signed (+18.35 / -11.17), so the
        attribution is a worst-corner statement. This split does not separate
        fingering from the resistor model, and `--flatten-schematic` was not run.
      - Negative control: `tests/test_pex_measure.py` feeds the wrapper the same
        campaign record on both sides and asserts zero delta on every row, then
        perturbs one side and asserts the delta appears (and that a missing point
        stays an error row, never zero). That covers the measurement path; the
        delta arithmetic is `klt pex`'s own.
    - **Item 5 (corner verification vs a ratified spec)** cites **eight
      `klt sim` envelopes** of one batch-fleet campaign, record
      [`20261113-150556-60489db-8101bf`](../sim/opamp-characterization/records/20261113-150556-60489db-8101bf.json)
      (issue [#246](https://github.com/2AMLogic/sky130-opamp/issues/246)), with
      the item 5 row set declared under the manifest's top-level
      `spec_rows."5"`. `spec/target-spec.md` is **RATIFIED (partial)** (DR-003,
      [#26](https://github.com/2AMLogic/sky130-opamp/issues/26)), so that gate
      has cleared, and item 5's kind restriction to a `sim` envelope is now
      satisfied by the tool's own output rather than by this repo's harness
      records. Historical (measured 2026-10-01 under klt 0.5.0, the pin at that
      time): citing the harness record `20261001-074923-c317ff9.json` on item 5
      rendered `unmet` / **`unrecognized_envelope`** — that record carries no
      `schema_version`, `status` or `provenance`, so it is not a `klt` envelope
      of any kind. What the current citation does and does not say:
      - **The envelopes grade the spec, not just the simulation.** Each
        measurement that corresponds to a ratified row carries that row's
        **unchanged** bound as a klt `limits` pair plus a `spec_row` tag, so the
        envelope itself records per-corner pass/fail and the binding corner
        (`measurements[].worst_case.corner_id`), and `klt signoff` **derives**
        the row coverage from the envelope instead of taking the manifest's
        word: the record's `detail.row_sources` reads `derived` for every
        covered row. Negative control, run against this manifest: adding a row
        to a citation's `rows` that its envelope does not grade puts that row in
        `detail.uncovered_rows` (here on top of the existing `check_failed`
        reason, which a failing citation keeps) — so the coverage really is
        checked against the envelope and not asserted. Every bound is traced to `DR-003`'s per-row
        ratification in the `ITEM5` block of
        [`bin/pvt_sweep.py`](../sim/opamp-characterization/bin/pvt_sweep.py),
        and `tests/test_pvt_sweep.py` asserts each one equals the ratified
        value — the no-relaxation guard `CLAUDE.md` requires.
      - **Item 5 is `unmet` / `check_failed`, and that is the finding, not a
        tooling failure.** `detail.failed_rows` is `["quiescent_power",
        "slew_rate"]`: the design misses two ratified rows at their binding
        corners. Slew rate binds at **SS / −40 °C**, where the 80 %–20 % fall
        transit measures **11.04 V/µs** against the ratified 20 V/µs (the rise
        edge is also under, at 19.88 V/µs — `DR-003` ratified *both* edges
        against that bound and itself called a 19.69 V/µs rise "marginally
        under"). Quiescent power binds at **FF / 125 °C / 1.98 V**, where Iq
        measures **66.63 µA** against the row's 65.0 µA budget (131.92 µW vs the
        ratified ≈ 128.7 µW). No threshold was loosened to make either pass.
      - **Four ratified rows pass at every corner of the 15-point grid**:
        open-loop DC gain (worst **61.64 dB @ FS / 125 °C**, bound ≥ 60 dB), GBW
        (worst **17.92 MHz @ SS / 125 °C**, bound ≈ 16 MHz), phase margin (worst
        **63.91° @ SF / 27 °C**, bound ≥ 60°) and input common-mode range (the
        40 dB window contains the ratified 0.888–1.024 V at all 15 points; the
        binding edge is the lowest high edge, **1.1686 V @ SS / −40 °C**).
      - **Which envelope covers which row.** `…-ac` grades gain, GBW and phase
        margin; `…-ac-iq` grades quiescent power; `…-tran-sr` grades slew rate
        (both edges); and the five `…-icmr-<corner>` envelopes grade the input
        common-mode range. The ICMR bench is one request **per process corner**
        by construction — its `.meas` cards need a literal mid-supply, and a
        9-unit grouped request stalled on the fleet (see that bench's README) —
        so its five envelopes together cover the same 15 points. The campaign's
        `…-dc-swing` envelope is committed but **deliberately not cited**: see
        the output-swing gap below.
      - **Quiescent power is graded as a current, on purpose.** A klt `limits`
        bound is one number across every corner of a request, and the supply
        axis moves with the process corner. The ratified row names two power
        figures — ≈ 128.7 µW at 1.98 V and ≈ 117.0 µW at 1.80 V — which are the
        *same* current (128.7 µW / 1.98 V = 117.0 µW / 1.80 V = 65.0 µA), and
        the row's own text says `I_Q = 65 µA` "is exactly what the row's '≈'
        estimate encodes". Grading Iq is therefore the only single bound that
        reproduces both ratified figures exactly; `pq_w` is reported alongside,
        ungraded, so the envelope still carries the power number.
      - **Six declared gaps keep the item unmet independently of the two
        failures**, each with its reason and issue in `spec_rows."5"` and quoted
        in the record's `detail.declared_gaps`: **output swing** (its ratified
        grading rule is a contiguous-run slope-band reduction over the swept
        waveform, which no `klt sim` measurement form expresses — an
        expressibility gap, not a missing measurement: the row *is* measured on
        the full grid by this campaign's `…-dc-swing` envelope and
        `-dc-swing.csv`. Filed generically as
        [klayout-tools#5518](https://github.com/2AMLogic/klayout-tools/issues/5518)
        under the friction protocol); **input-referred noise** (ratified as a
        target; [#54](https://github.com/2AMLogic/sky130-opamp/issues/54)'s
        bench has landed and its 15-corner envelope is committed, but it carries
        no `limits`/`spec_row` and `DR-003` left the row's graded quantity
        undecided —
        [#274](https://github.com/2AMLogic/sky130-opamp/issues/274));
        **PSRR** and **area** (`[TBD]`, no ratified bound); and
        **input-referred offset** and **CMRR** (targets *proposed* by `DR-009`
        and `DR-008`, not ratified, so there is no ratified bound to grade —
        offset's evidence is a Monte Carlo campaign, which is item 6, not a
        corner envelope).
      - **This campaign reproduces the canonical DR-013 figures.** It ran on the
        batch fleet at `runner_compatibility: match` (klt 0.9.0 both sides, nine
        job ids in the record's `klt_jobs[].remote`), on the same DUT snapshot,
        against the earlier canonical campaigns
        `20261011-140526-04489d4-7e5893` and `20261011-141126-04489d4-b4ac6f`
        (which ran on the fleet's then-ngspice-46): gain, Iq, Pq and all three
        ICMR columns agree **exactly**, and the worst disagreement anywhere is
        **8.5e-4 relative** on the fall slew rate at SS / −40 °C. The record
        also carries a `spec_row_grading` block that cross-checks every klt
        `param=` card against the Python column the harness computes from the
        same response (`klt_vs_python_agrees: true`, worst 2.7e-4 relative —
        the 6-significant-figure print floor), so a silently-ignored request
        option would show up as a disagreement.
    - **Item 6 (Monte Carlo)**: uncited. The offset row now has measured
      mismatch Monte Carlo data (issue #85, N = 300 per corner, sigma about
      8.4-8.7 mV at 27 C / 1.8 V, open-loop; record
      [`campaign-20261009-offset-mc300.md`](../sim/offset-capability/records/campaign-20261009-offset-mc300.md))
      and a numeric target (sigma <= 0.275 mV) **proposed** by
      [DR-009](../spec/decision-records/DR-009-offset-target.md). The row is
      **OPEN**: DR-009 is not ratified, and the measurement does not meet
      the proposed target. Those are `klt sim` and campaign records, not
      the `klt yield` report the item's checklist text names as its
      machine-checkable evidence, so the remaining item-6 gap is an
      evidence-kind one: no `klt yield` report (and no item-6 citation)
      exists. Matching and any other statistical rows are not covered by
      that campaign.
    - **Items 9 and 10 (attested inventories)** cite generic envelopes
      produced by `klt signoff --attest N --inventory
      manifests/inventory/itemN.json` (issue
      [#223](https://github.com/2AMLogic/sky130-opamp/issues/223), design
      in [DR-014](../spec/decision-records/DR-014-t1-attestation-inventories.md)),
      committed as
      [`envelopes/item9.attest.json`](envelopes/item9.attest.json) and
      [`envelopes/item10.attest.json`](envelopes/item10.attest.json).
      Items 9 and 10 have *no* kind restriction at all, so any passing
      envelope would mechanically green them; that is why they are cited
      only on an envelope the tool derived from a versioned inventory (it
      pins the inventory's bytes and every inventoried file's hash and runs
      the declared PDK-free checks), never on a hand-written one. Item 9's
      cold start is the PDK-free harness unit tests; the full ngspice
      sweeps stay documented in each bench README. CI re-runs `klt signoff
      --attest N --inventory ... --check <envelope>` per envelope (exit 3 =
      drift): edit an inventoried file and regenerate the envelope in the
      same PR. The klt pin moved to 0.8.0 because `--attest` first shipped there.
- **`design-evidence-tiers.md`** — the T1-T4 checklist the grader
  parses. Vendored **byte-identical** from
  [`2AMLogic/klayout-tools@31a3e3c`](https://github.com/2AMLogic/klayout-tools/blob/31a3e3c41c08bbd58719e0b99a3b6d19beb9be63/docs/design-evidence-tiers.md)
  `docs/design-evidence-tiers.md` (2026-09-21; upstream is
  [MIT-licensed](https://github.com/2AMLogic/klayout-tools/blob/main/LICENSE)
  — this repo's Apache-2.0 `LICENSE` does not relicense the vendored
  copy). Historical (klt 0.5.0): that
  release bundled a copy that predated checklist item 11 ("Power
  delivery (structural)",
  [klayout-tools#2025](https://github.com/2AMLogic/klayout-tools/issues/2025),
  2026-09-17) — passing `--tiers-doc` at this vendored copy is how the
  report renders the 11-item checklist, including item 11's row. When
  upstream moves, re-vendor the doc and regenerate the record in the
  same PR; the report's `source_doc` field pins which file graded this
  block.
- **`sky130-opamp.signoff.json`** — **the verdict of record**: committed
  output of the regeneration command below. Never hand-edit it.

## Regenerate (cold start)

```console
pip install klayout-tools==0.8.0        # provides the `klt` command
klt signoff --manifest manifests/sky130-opamp.json \
            --tiers-doc manifests/design-evidence-tiers.md \
            --format json > manifests/sky130-opamp.signoff.json
```

`klt signoff --manifest` exits `3` when at least one T1 item is `unmet`
(a valid, clean run — `unmet` with a per-item `reason` is exactly the
honest machine-readable statement of the gap) and `0` when every item is
`met`. Any change that affects the verdict — new evidence, a manifest
edit, a vendored-doc bump, a `klt` version-pin bump — regenerates and
commits the record in the same PR.

## Freshness is CI-enforced

[`.github/workflows/signoff.yml`](../.github/workflows/signoff.yml)
re-runs the regeneration command on every push and byte-compares the
fresh output against the committed record, so a manifest citing an
artifact that has since changed fails the build rather than rotting.

That same workflow carries a second, repo-side step — **"Re-hash every
generic envelope's cited artifact"** — because `klt signoff`'s staleness
gate is *nominal* for a generic citation. The gate compares the
manifest's pinned `content_hash` against the envelope's own
**self-declared** `provenance.input.content_hash`; nothing in any
released `klt` ever re-hashes the artifact that string names. Historical
observation, measured 2026-10-01 under klt 0.5.0 (the pin at that time):
corrupting the manifest's pin flips
item 8 to `unmet` / `stale_evidence`, but **appending a line to the
cited `.md` record leaves item 8 `met`**. The committed pin therefore
proves the manifest and the envelope agree with each other, and nothing
about whether either still describes the record on disk.

Upstream tracked this
([klayout-tools#2196](https://github.com/2AMLogic/klayout-tools/issues/2196),
[#2403](https://github.com/2AMLogic/klayout-tools/issues/2403)) and settled
the contract on purpose: a generic envelope that declares
`provenance.input.path` gets an `input_verified` field, but that field is
**disclosure, never grading**. The committed record shows
`input_verified: true` on both generic citations under the pinned 0.7.0.
Whether a given klt release grades a drifted input as `met` is not
re-measured here; the gate does not rely on it, and has to be ours. The CI
step resolves the envelope's `provenance.input.path` (relative to the
envelope's own directory, matching the upstream resolution order), re-hashes
the file, and fails on any mismatch, missing file, or envelope that omits
either `provenance.input.path` or `provenance.input.content_hash`. Verified
to fail on all three, 2026-10-01 (historical).

The check is the stdlib-only
[`design/bin/generic_evidence_check.py`](../design/bin/generic_evidence_check.py)
(unit-tested in `tests/test_generic_evidence_check.py`). `signoff.yml`
and the local simulator-free runner both call it, so there is a single
implementation. Run it locally, with no `klt` needed:

```console
python3 design/bin/generic_evidence_check.py     # exit 0 = fresh, 1 = drift/malformed
python3 design/bin/check_ci.py                   # default gate; includes the above
```

Evidence must live inside the checkout: envelope and artifact paths are
canonicalised (symlinks followed) and any external absolute path, `..`
traversal or symlink that leaves the repository root is rejected as an
item error, since a fresh checkout would lack that file. When the
envelope-relative candidate escapes, the reference is reported invalid
rather than falling back to the repo-relative lookup. Contained symlinks
and internal `..` segments remain valid; dangling links and unreadable
artifacts are reported per item.

It aggregates every item-specific failure (malformed or unreadable
envelope, missing `provenance.input.path`/`content_hash`, unresolvable
file, hash disagreement). It skips well-formed `{"command": [...]}`
entries (non-empty list of strings) and non-generic envelopes. It also
rejects malformed input instead of passing vacuously: a manifest root
that is not an object, a missing `evidence` key (required; the gate is
only ever run on `manifests/sky130-opamp.json`), a non-object `evidence`
(`null`, `[]`, `""`, `false`, ...), and any entry that is not a non-empty
path string, a `{"file": <non-empty str>[, "content_hash": <str>]}`
object, or a `{"command": [...]}` object (including empty or non-string
`file`/`command`, both keys at once, and non-object entries). An empty
`"evidence": {}` is well-formed and passes with `0` checked. The `klt signoff` render-and-byte-compare step
stays separate. On a hash failure, regenerate in the same PR: re-hash the
artifact (`sha256sum`, prefixed `sha256:`), write it into the envelope's
`provenance.input.content_hash` and the manifest's pinned `content_hash`,
then rerun the `klt signoff` regeneration command above.

## Current verdict

**Not-T1 — T1 items 1, 2, 3, 4, 7, 8, 9, 10 and 11 met (9 of 11)** as of this record. Every item's `reason`
is inside [`sky130-opamp.signoff.json`](sky130-opamp.signoff.json):

- **Item 8 (characterization report) — `met`**, on the generic evidence
  envelope described above (`citation.kind: "generic"`,
  `check_status: "pass"`, with the cited record's `content_hash`
  pinned). `met` here means *an aggregated, current characterization
  report exists and states honestly what it measured* — it is **not** a
  spec-compliance claim (that is item 5) and **not** a statement that
  every spec row is characterized (8 of 12 §2 rows are, and the
  envelope's `summary` names the other 4).
- **Item 1 (design sources) — `met`**, on the generic envelope described
  above; backed by the netlist-drift CI job, not by `klt`.
- **Items 2, 3, 4, 11** — `met` on the `layout/opamp_core/` envelopes
  described above, with the caveats there (Magic `drc(full)` fails; the
  p-substrate tie is disclosed, not graded).
- **Items 9 and 10** — `met` on the `--attest` envelopes described above
  (inventory-derived, re-checked in CI).
- **Item 7 (post-layout) — `met`** on the `klt pex` report described above,
  with the extraction-model limits and the device-only attribution split there.
- **Item 5 (corner verification) — `unmet` / `check_failed`**, cited on eight
  `klt sim` envelopes that grade the ratified rows themselves. The reason is a
  **design** gap, not an evidence one: `detail.failed_rows` names
  `quiescent_power` and `slew_rate`, and six further rows are declared gaps.
  See the per-item rationale above.
- **Item 6 (Monte Carlo) — `unmet` / `no_evidence`**, for the reason recorded
  per item above (no `klt yield` report exists).

Known item-level gates on the path forward (partial layout and measured
offset exist, but neither earns an additional item; nothing here claims
full-core signoff or ratification):

- Item 5 (corner verification vs a ratified spec): the evidence gap is
  closed — the campaign of record
  [`20261113-150556-60489db-8101bf`](../sim/opamp-characterization/records/20261113-150556-60489db-8101bf.json)
  (issue [#246](https://github.com/2AMLogic/sky130-opamp/issues/246)) emits
  `klt sim` envelopes that carry each ratified row's own bound, so six of the
  eight ratified §2 rows are now graded by the tool at every corner. Two gates
  remain, and they are different in kind: **(a)** two graded rows *fail* at
  their binding corners (fall slew 11.04 V/µs vs 20 V/µs at SS / −40 °C, and
  Iq 66.63 µA vs 65.0 µA at FF / 125 °C / 1.98 V) — closing those is a design
  pass, never a threshold edit; **(b)** six rows are declared gaps — output
  swing is an expressibility gap in `klt sim`
  ([klayout-tools#5518](https://github.com/2AMLogic/klayout-tools/issues/5518)),
  noise needs a graded quantity and `limits`
  ([#274](https://github.com/2AMLogic/sky130-opamp/issues/274)), and PSRR,
  area, offset and CMRR stay `[TBD]`, OPEN or proposed in
  `spec/target-spec.md`. See the per-item rationale above.
- Item 6 (Monte Carlo): measured offset data exists against a proposed
  (DR-009), OPEN target, and does not meet it; the remaining gate is a
  `klt yield` report and citation — see the per-item rationale above.
- Item 7 (post-layout): cited on the `klt pex` report above (`met`, `body_bias` biased); the
  attribution split above (device-only leg) stands.
- Items 2, 3, 4 and 11 are cited on the assembled core; the open caveats
  there are the failing Magic `drc(full)` (inherited `opamp_comp` resistor
  head) and the ungraded p-substrate tie.

As evidence lands, the manifest's `evidence` map grows one item at a
time — every citation must pin the `content_hash` of the artifact it
cites. For a `klt`-native envelope that pin is a machine-checked
staleness gate (the hash was computed by `klt` from the artifact at run
time, so a moved input revision renders `unmet` / `stale_evidence`). For
a hand-written generic envelope it is not, which is exactly what the CI
re-hash step above exists to cover.
