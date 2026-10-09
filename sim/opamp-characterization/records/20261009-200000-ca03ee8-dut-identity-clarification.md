# Clarification: what the legacy rendered-deck snapshots do and do not establish

- Date: 2026-10-09 (issue #104). Append-only: no earlier record was edited.
- Applies to: [`20261001-074923-c317ff9`](20261001-074923-c317ff9.md),
  [`20261009-103006-566b9a5`](20261009-103006-566b9a5.md) and every other
  record written before the runner captured a DUT snapshot.

## Correction

`20261001-074923-c317ff9.md` states that every rendered deck in
`../netlist-snapshots/20261001-074923-c317ff9/` "embeds the exact netlist it
drove". That is **wrong**. Those decks contain an `.include` of an absolute
path into a working tree (for `ac-tt-27C.spice`, the old issue-22 worktree);
they are pointers to a mutable file, not embedded device definitions. The same
holds for the ICMR/CMRR bodies of `20261009-103006-566b9a5` (issue-53
worktree). Nothing under those snapshot directories establishes which circuit
produced the recorded measurements.

The record's Git SHA does not recover it either: `c317ff9` was a *pre-resize*
commit and the run used the uncommitted DR-007 resize, so the netlist at that
SHA (for example M3 L=0.6/W=2.745) differs from the circuit that was
simulated.

## Status of legacy records

Their DUT identity is **UNVERIFIED**. No hash is back-filled from today's
netlist or from the Git SHA, because either would manufacture provenance the
run did not capture. They remain valid *historical* evidence of what was
reported; they are not mechanically bound to any netlist.

## What is needed for a verified current-design claim

Rerun the campaign with `bin/pvt_sweep.py` at or after the change that adds
the `dut` block (issue #104). The new record then carries
`dut.{source_path,snapshot_path,sha256}`, the immutable copy sits in
`../netlist-snapshots/<record_id>/opamp_core.spice`, and
`python3 sim/lib/dut_identity.py current --require-verified` binds the report
cited for T1 item 8 to the committed netlist. Snapshot integrity says nothing
about spec or T1 compliance.
