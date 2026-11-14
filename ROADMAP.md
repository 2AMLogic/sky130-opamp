# Roadmap

A two-stage Miller-compensated op-amp on SkyWater sky130 (1.8 V core devices),
carried up the klayout-tools design-evidence ladder with every claim tied to a
committed record.

Status as of 2026-11-13, `main` @ `96d9fbc`.

[`WORK_PLAN.md`](WORK_PLAN.md) is the generated view of the tracker's labels;
[`manifests/sky130-opamp.signoff.json`](manifests/sky130-opamp.signoff.json)
is the verdict of record and wins over this file where they disagree.

## Where it stands

The committed `klt signoff` record grades **9 of 11 T1 (sim-validated) items
met**, tier `null`. The tracker is #3; its body predates most of this, and
[`manifests/README.md`](manifests/README.md) holds the current per-item account.

| T1 item | Status | Evidence |
|---|---|---|
| 1 Design sources | met | `design/netlist/opamp_core.sources.evidence.json`, regeneration gate in `design-sources.yml` |
| 2 Layout, 3 DRC, 4 LVS, 11 Power delivery | met | `layout/opamp_core/` (`extract.json`, `drc.json`, `lvs.json`, `erc.json`), assembled from four sub-blocks (PR #225, #231) |
| 5 Corner verification vs the ratified spec | **unmet, `check_failed`** | eight `klt sim` envelopes of campaign `20261113-150556-60489db-8101bf` (PR #275) |
| 6 Monte Carlo evidence | **unmet, `no_evidence`** | N = 300 offset campaign exists (`sim/offset-capability/records/campaign-20261009-offset-mc300.md`) but no `klt yield` report |
| 7 Post-layout verification | met | `klt pex` of `opamp_core` (PR #248, attribution split PR #260) |
| 8 Characterization report | met | `sim/opamp-characterization/records/20261009-103006-566b9a5.characterization.json` |
| 9 Testbenches, 10 Repo hygiene | met | attested inventories, `manifests/envelopes/item{9,10}.attest.json` (PR #244) |

What the two unmet items actually rest on:

- **Item 5.** Six of the eight ratified performance rows are graded by the
  tool at every corner. Two fail. **Slew rate is a design miss**: fall edge
  11.04 V/µs against 20 V/µs at SS / −40 °C. **Quiescent power** fails only
  under a zero-tolerance reading of an "≈" row (66.63 µA against 65.0 µA),
  which is a spec question, not a design verdict (#277). Six more rows are
  declared gaps: output swing (not expressible in `klt sim`,
  [klayout-tools#5518](https://github.com/2AMLogic/klayout-tools/issues/5518)),
  noise (#274), and PSRR, area, offset and CMRR, which are `[TBD]`, OPEN or
  only proposed in [`spec/target-spec.md`](spec/target-spec.md).
- **Item 6.** The offset row is OPEN: the target (σ ≤ 0.275 mV, DR-009) is
  proposed, the measurement (σ ≈ 8.4–8.7 mV) does not meet it, and it was
  taken on the DR-007 widths, not the current DR-013 netlist.

Caveat on the met layout items: the PDK's Magic `drc(full)` **fails** on the
assembled core (2 errors, `licon.1c`, inherited from the `opamp_comp`
resistor heads), so the layout is not foundry-DRC-clean. Spec: 13 of 17 rows
ratified (DR-003); DR-008 through DR-014 are `proposed`.

## Now

Startable today, one PR each. Each was filed as an issue just after this
file's snapshot: #281, #282, #283 and #284, in the order below.

1. **Clear the Magic resistor-head DRC failure in `opamp_comp`.** The
   generator gap it was parked on, klayout-tools#3077, is closed upstream.
   Done when: `layout/opamp_comp/magic-signoff/magic.json` reports zero
   `drc(full)` errors on a cell regenerated with a klt revision carrying the
   fix and `compose-cell.py --check` reproduces it; or the cell README names
   the revision tested and what still fails.
2. **Reconcile the PSRR row against the committed benches.** PSRR+ and PSRR−
   records exist (`20261009-073254-e06f2fc`, issue #54) but the spec row
   still reads `[TBD]`, "not started". Done when: the row cites a 15-corner
   PSRR record taken on the current netlist with its worst case and binding
   corner, and a `proposed` decision record states a target, following the
   CMRR precedent (DR-008). Proposing is not ratifying.
3. **Bring the integrator view and status prose up to the assembled core.**
   `manifests/integrator.json` still says no full-core layout exists (`gds`
   and `area_um2` null, evaluated at `8b3ec92`), `README.md` says the
   full-core layout "remains pending", and `layout/README.md` says nothing in
   `manifests/` cites `opamp_core`. Done when: all three match
   `layout/opamp_core/README.md`, the Magic caveat is carried, and
   `python design/bin/integrator_check.py validate` passes.
4. **Record the measured area and refresh the consumer verdicts.** The Area
   row reads "no `layout/` exists yet" and the Consumers tables are evaluated
   at `8b3ec92` (they still quote the pre-resize GBW). DR-004 requires both
   to be updated in the same pass as the integrator view. Done when: the Area
   row carries the measured `opamp_core` extent as a measurement (target
   still OPEN), every verdict cell cites a current record, and
   `python design/bin/spec_figures_check.py validate` passes.

## Next

- **Reassemble `opamp_core` on the corrected compensation block** and
  re-cite items 2, 3, 4, 7 and 11. Done when `layout/opamp_core/magic-signoff/magic.json`
  is clean and `klt signoff` reproduces the committed record. After Now 1.
- **Grade the quiescent-power row.** Done when item 5's `failed_rows` no
  longer lists `quiescent_power`, or the spec row is corrected to "not met".
  Blocked on the decision in #277.
- **Grade the noise row.** Done when the `noise` envelope carries a `limits`
  pair and a `spec_row` tag. Blocked on the decision in #274.
- **Grade output swing in the tool.** Done when a swing envelope with limits
  is cited on item 5. Blocked on klayout-tools#5518.
- **Offset Monte Carlo on the current netlist, as a `klt yield` report**
  cited on item 6. Blocked on a ratified offset target (DR-009) and, for the
  drift conditions, the campaign decision in #196.

## Later

- **Close the fall-slew gap.** DR-012 (proposed) carries the signal-dependent
  sink forward as the only viable output candidate and rules out the tail
  clamp. Question first: is the sink adopted into the canonical schematic,
  and at what cost to swing, power and offset? Adoption means a ratified
  record, a new netlist, a re-run of every item 5 campaign and a new layout.
- **Close the offset gap.** DR-011 (proposed) finds sizing alone
  insufficient; the technique study (PR #195) compares trim, chopping,
  auto-zero and consumer-side correction. Question first: which technique,
  and does paired drift (#196) make foreground trim viable?
- **Ratify the four OPEN rows** (offset, CMRR, PSRR, area) so item 5 can
  reach full row coverage. Question first: each row's target, by decision
  record.

## Blocked and waiting

At the snapshot, every open issue was held on an operator decision or was a
resting tracker: **nothing was dispatchable**. The Now items have since been
filed as #281-#284 and are not listed below.

| Issue | Waiting on |
|---|---|
| #277 | tolerance carried by the "≈" quiescent-power row |
| #274 | which quantity grades the noise row |
| #196 | approval and terms for the B2/B3/B4 offset-drift campaign (plan merged in PR #264) |
| #278 | whether to remove the local ngspice executor from `pvt_sweep.py` |
| #268 | whether DR-014 drops `.gitignore` and `CLAUDE.md` from the item 10 inventory (signoff is green again, the recurrence is not fixed) |
| [klayout-tools#5518](https://github.com/2AMLogic/klayout-tools/issues/5518) | a `klt sim` measurement form for output swing |

## Not planned

- A 3.3 V I/O-device flavor: not served, per
  [DR-005](spec/decision-records/DR-005-io-flavor-not-served.md).
- Hand-drawing the resistor heads in place of generator output, which would
  replace the geometry DR-010 rests on.
