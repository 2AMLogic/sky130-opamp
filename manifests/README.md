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
  - `evidence` is **currently empty, deliberately**: this block has no
    `klt`-produced evidence envelopes yet (no layout → no
    DRC/LVS/extract/pex/erc; the corner sweeps under
    `sim/opamp-characterization/` were produced by this repo's own
    ngspice harness, not by `klt sim`, and are therefore not citable
    here; and `spec/target-spec.md` is still DRAFT, so item 5's
    ratified-spec gate is unmet regardless — ratification is tracked in
    [#26](https://github.com/2AMLogic/sky130-opamp/issues/26)). The
    grader contract is explicit that an all-`unmet` manifest is a
    correct result, and that citing an envelope which does not actually
    support an item just to make a row green is the failure mode this
    machinery exists to prevent ("The safest default is to leave [items
    1, 2, 9 and 10] uncited").
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
pip install klayout-tools==0.5.0        # provides the `klt` command
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

## Current verdict

**Not-T1 — T1 items 0/11 met** as of this record. Every item's `reason`
is inside
[`sky130-opamp.signoff.json`](sky130-opamp.signoff.json) (`no_evidence`
throughout: the manifest cites nothing until real `klt`-native envelopes
exist). Known item-level gates on the path forward:

- Item 5 (corner verification vs a **ratified** spec):
  [#26](https://github.com/2AMLogic/sky130-opamp/issues/26).
- Item 11 (power delivery, structural): the
  [companion item-11 issue](https://github.com/2AMLogic/sky130-opamp/issues/27)
  — ERC supply evidence plus an LVS report whose reference carries the
  supplies; gated on this block having a layout at all.
- Items 3/4/7 (DRC/LVS/post-layout) and 2 (layout): gated on layout
  work that has not started.

As evidence lands, the manifest's `evidence` map grows one item at a
time — every citation must pin the `content_hash` of the artifact it
cites (a pinned citation whose input revision moved renders `unmet` /
`stale_evidence`, the machine-checked staleness gate).
