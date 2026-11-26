# DR-014: T1 items 9 and 10 — commit attestation inventories now, produce envelopes when a klt release has `--attest`

- **Status**: **proposed** — drafted by the Builder agent (issue #221). Ratification is approval of the PR that carries this record. No ratified spec figure is touched.
- **Date**: 2026-10-17
- **Decided by**: Loom Builder agent, issue #221
- **Related**: #221, `manifests/design-evidence-tiers.md` (T1 items 9, 10), klayout-tools#2844

## Context

Items 9 (Testbenches shipped) and 10 (Repo hygiene) of `manifests/sky130-opamp.signoff.json` are `unmet` / `no_evidence`: `manifests/sky130-opamp.json` cites evidence only for items 1 and 8. These items must cite a tool-produced generic envelope from `klt signoff --attest {9,10} --inventory FILE`. That flag is in no released klayout-tools: PyPI latest is 0.7.0 (checked 2026-10-17) and `signoff.yml` pins `==0.7.0`; only a post-0.7.0 dev build has it.

## Decision

1. Commit the two inventories now: `manifests/inventory/item9.json` and `manifests/inventory/item10.json` (`schema_version` 1, `kind` `t1-attestation-inventory`, read from the dev build's `klayout_tools/signoff_attest.py`).
2. **Wait** for a klt release containing #2844 before producing envelopes, citing them, bumping the `signoff.yml` pin or adding `--check` steps. Envelopes are not hand-written and CI is not pinned to a dev build.
3. Phase B (one command per item once released): `uvx --from "klayout-tools==X.Y.Z" klt signoff --attest N --inventory manifests/inventory/itemN.json -o <envelope>`, cite the envelope hashes in `manifests/sky130-opamp.json`, bump the pin (`tests/test_klt_pin_sync.py` must stay green) and the `pins.tools.klayout-tools` value in `item9.json`, add `--check <envelope>` steps to `signoff.yml`, regenerate `manifests/sky130-opamp.signoff.json`.

### Inventory content choices

- Every command is run by `--check` on the `signoff.yml` runner, which has no PDK, no xschem and no ngspice. Only commands that pass there are listed.
- **Item 9 cold start** is `python3 -m unittest discover -s tests -p 'test_*sweep.py'` (the PDK-free harness tests of the three sweep drivers). It does **not** regenerate the 45-run PVT or 120-run gm/ID evidence; those cold starts need the pinned PDK and ngspice and stay documented in `sim/*/README.md`. The item-9 attestation therefore claims "benches are shipped, hashed and pinned, and the harness logic passes", not "measurements were reproduced" — and not "harness bytes are hashed": the `sim/lib/` modules a bench imports stay outside the hash, and only their *logic* is exercised, by the cold start.
- Item 9 pins: PDK `sky130A` at `open_pdks_commit` `c6d73a35f524070e85faff4a6a9eef49553ebc2b` (equal to `sim/gm-id-characterization/pdk.json` and `PDK_VERSION` in `design-sources.yml`), tools `klayout-tools` and `ngspice` 42.
- **Which `sim/lib/` modules enter the inventory** (amended by issue #302): a `sim/lib/` module enters item 9's inventory when it **owns ratified spec data** — a figure, table or identity drawn from `spec/` or a decision record. Behavioural plumbing imported by a bench does **not** enter: its correctness is covered by the item-9 cold start, not by a content hash, and a hash would tax every plumbing edit with an envelope + manifest-pin + signoff re-roll in the same commit. The first entry under this rule is `sim/lib/corners.py`, the single owner of the ratified five-corner list, three-temperature grid and corner→VDD pairing (DR-002 Sec (f)); the cold start already catches a corner-name or VDD edit, but a silent edit to the ratified temperature grid (`DEFAULT_TEMPS_C`) ships green (measured, issue #302: the cold start passes 186/186 with 125.0 → 110.0 while `tests/test_corners_single_owner.py`, which does assert the values, is not matched by the cold-start pattern) — the content hash closes exactly that hole. `sim/lib/point_identity.py` is excluded by this rule today: it owns the ratified `(corner, temp_c, vdd_v)` tuple, but only non-inventoried consumers import it (`sim/opamp-characterization/variants/compare.py`, `sim/opamp-characterization/variants/sink_bias_report.py`, `design/bin/spec_figures_check.py`); it enters the inventory the day an inventoried bench imports it.
- **Item 10 checks** are the simulator-free gates of `tests.yml`. Left out on purpose: `append_only_check.py` (needs a base ref), `netlist_check.py` (needs xschem and the PDK; already item 1's evidence), `generic_evidence_check.py` and `check_ci.py` (they re-hash the envelopes, which would make the attestation depend on itself).

## Alternatives considered

- **Hand-write the envelopes** — rejected: the checklist expects tool-produced evidence for items 1/9/10.
- **Pin CI to a git/dev build of klt** — rejected: unreproducible.
- **Full-sweep cold start** — rejected for the reason above; it cannot run in the signoff job.

## Spec lines affected

None. Evidence packaging only.

## Open items

- Phase B, tracked by the follow-up issue filed with this PR.
- Negative control (Phase A, dev klt, scratch edit of `README.md`): `--check` against a fresh envelope reported `status: drifted` on that file's `content_hash`; to be repeated against the released klt in Phase B.
