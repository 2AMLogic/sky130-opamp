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
  - `evidence` holds **two citations — item 8** (issue
    [#43](https://github.com/2AMLogic/sky130-opamp/issues/43)) **and item 1**
    (issue [#55](https://github.com/2AMLogic/sky130-opamp/issues/55)). Every
    other item stays deliberately uncited, for a reason per item:
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
      Generic evidence is accepted for item 1 only from klt 0.7.0 (0.5.0
      renders `wrong_kind`), which is why the pin moved to 0.7.0. Like item 8,
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
      [`sim/opamp-characterization/records/20261001-074923-c317ff9.characterization.json`](../sim/opamp-characterization/records/20261001-074923-c317ff9.characterization.json)
      — a **generic evidence envelope** (`"kind": "generic"`,
      [klayout-tools#1152](https://github.com/2AMLogic/klayout-tools/issues/1152))
      wrapping the committed PVT characterization record
      [`20261001-074923-c317ff9.md`](../sim/opamp-characterization/records/20261001-074923-c317ff9.md).
      Item 8 is the **only** T1 item the generic kind may satisfy
      (`_ITEMS_ACCEPTING_GENERIC_EVIDENCE == {8}`; a generic citation on
      any other item renders `wrong_kind`), and the only T1 item whose
      checklist text names no `klt` verb — so it is the one item
      reachable with no layout and no `klt sim` port.
      **Read that envelope's `summary`, not just the `met` row**: `klt
      signoff` grades item 8 on the envelope's `status` alone and cannot
      check coverage, so the coverage disclosure (6 of
      `spec/target-spec.md` §2's 12 rows characterized, 6 uncharacterized
      and named, 2 of the characterized 6 measuring below target at their
      binding corner) lives in that `summary` field and is
      claimant-enforced — the same discipline item 3's DRC-coverage and
      item 4's power-connectivity caveats already carry. The `summary`
      is quoted in `sky130-opamp.signoff.json`'s citation block under
      klt 0.7.0 (`artifact_binding.summary`); the envelope file remains
      the source.
    - **Items 3, 4, 7 and 11 (DRC / LVS / post-layout / ERC supply)**:
      no layout exists, so no `klt drc`/`lvs`/`pex`/`erc` envelope exists
      to cite.
    - **Item 5 (corner verification vs a ratified spec)**: `spec/target-spec.md`
      is now **RATIFIED (partial)** (DR-003,
      [#26](https://github.com/2AMLogic/sky130-opamp/issues/26)), so that
      gate has cleared — but item 5 is kind-restricted to a `klt sim`
      envelope (`_ITEM_ALLOWED_KINDS[5]["analog"] == {"sim"}`), and the
      corner sweeps under `sim/opamp-characterization/` are this repo's
      own ngspice harness output. Measured, 2026-10-01 under the pinned
      klt: citing `20261001-074923-c317ff9.json` on item 5 renders
      `unmet` / **`unrecognized_envelope`** (that record carries no
      `schema_version`, `status`, or `provenance` — it is not a `klt`
      envelope of any kind). Closing item 5 needs the PVT bench to emit
      or be re-run through a real `klt sim` envelope; not tracked yet.
    - **Item 6 (Monte Carlo)**: no `klt yield` run exists; the
      statistical spec rows (offset, matching) are `[TBD]`.
    - **Items 2, 9 and 10** have *no* kind restriction at all, so any
      passing envelope would mechanically green them. The grader contract
      is explicit that this is the dishonest-citation failure mode the
      machinery exists to prevent: "The safest default is to leave [items
      2, 9 and 10] uncited (item 1 is cited only because a CI gate re-derives it)." They stay uncited.
- **`design-evidence-tiers.md`** — the T1-T4 checklist the grader
  parses. Vendored **byte-identical** from
  [`2AMLogic/klayout-tools@31a3e3c`](https://github.com/2AMLogic/klayout-tools/blob/31a3e3c41c08bbd58719e0b99a3b6d19beb9be63/docs/design-evidence-tiers.md)
  `docs/design-evidence-tiers.md` (2026-09-21; upstream is
  [MIT-licensed](https://github.com/2AMLogic/klayout-tools/blob/main/LICENSE)
  — this repo's Apache-2.0 `LICENSE` does not relicense the vendored
  copy). The installed release,
  klt 0.5.0, bundles a copy that predates checklist item 11 ("Power
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
pip install klayout-tools==0.7.0        # provides the `klt` command
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
released `klt` ever re-hashes the artifact that string names. Measured
2026-10-01 under the pinned 0.5.0: corrupting the manifest's pin flips
item 8 to `unmet` / `stale_evidence`, but **appending a line to the
cited `.md` record leaves item 8 `met`**. The committed pin therefore
proves the manifest and the envelope agree with each other, and nothing
about whether either still describes the record on disk.

Upstream knows
([klayout-tools#2196](https://github.com/2AMLogic/klayout-tools/issues/2196),
[#2403](https://github.com/2AMLogic/klayout-tools/issues/2403), the
latter's fix on `main` but in no release as of 2026-10-01) and has
settled the contract the other way on purpose: once released, a generic
envelope that declares `provenance.input.path` gets an `input_verified`
field, but that field is **disclosure, never grading** — item 8 still
renders `met` when the input drifted. So no `klt` version will ever fail
the build on this, and the gate has to be ours. The CI step resolves the
envelope's `provenance.input.path` (relative to the envelope's own
directory, matching the upstream resolution order), re-hashes the file,
and fails on any mismatch, missing file, or envelope that omits either
`provenance.input.path` or `provenance.input.content_hash`. Verified to
fail on all three, 2026-10-01. Setting `provenance.input.path` also
means this repo's envelope starts reporting `input_verified: true` for
free whenever the pin moves to a release carrying #2403.

## Current verdict

**Not-T1 — T1 items 1 and 8 met** as of this record. Every item's `reason`
is inside [`sky130-opamp.signoff.json`](sky130-opamp.signoff.json):

- **Item 8 (characterization report) — `met`**, on the generic evidence
  envelope described above (`citation.kind: "generic"`,
  `check_status: "pass"`, with the cited record's `content_hash`
  pinned). `met` here means *an aggregated, current characterization
  report exists and states honestly what it measured* — it is **not** a
  spec-compliance claim (that is item 5) and **not** a statement that
  every spec row is characterized (6 of 12 §2 rows are, and the
  envelope's `summary` names the other 6).
- **Item 1 (design sources) — `met`**, on the generic envelope described
  above; backed by the netlist-drift CI job, not by `klt`.
- **The other 9 T1 items — `unmet` / `no_evidence`**, each for the
  reason recorded per item above.

Known item-level gates on the path forward:

- Item 5 (corner verification vs a ratified spec): the DRAFT-spec gate
  has cleared ([#26](https://github.com/2AMLogic/sky130-opamp/issues/26),
  DR-003), but the item is kind-restricted to a `klt sim` envelope and
  this repo's ngspice harness does not emit one — see the per-item
  rationale above.
- Item 11 (power delivery, structural): the
  [companion item-11 issue](https://github.com/2AMLogic/sky130-opamp/issues/27)
  — ERC supply evidence plus an LVS report whose reference carries the
  supplies; gated on this block having a layout at all.
- Items 3/4/7 (DRC/LVS/post-layout) and 2 (layout): gated on layout
  work that has not started.

As evidence lands, the manifest's `evidence` map grows one item at a
time — every citation must pin the `content_hash` of the artifact it
cites. For a `klt`-native envelope that pin is a machine-checked
staleness gate (the hash was computed by `klt` from the artifact at run
time, so a moved input revision renders `unmet` / `stale_evidence`). For
a hand-written generic envelope it is not, which is exactly what the CI
re-hash step above exists to cover.
