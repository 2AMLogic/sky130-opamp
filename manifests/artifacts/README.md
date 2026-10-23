# Evidence artifact manifests

New sim evidence bytes (raw ngspice logs, klt responses) live in the fleet
artifact store, not in git. This directory holds, per run, a
`<bench>-<run-id>.manifest.json` (schema_version 1; every `uri` is
`artifact:<key>`) and a `<bench>-<run-id>.summary.md` (name, size, sha256 per
object). Both are append-only (`sim/lib/append_only_check.py`).

- Writer: `sim/lib/artifact_store.py`, used by
  `sim/opamp-characterization/bin/pvt_sweep.py` and `psrr_noise_sweep.py`. It
  stages into git-ignored `sim/.work/.stage/`, then `klt artifact put`.
- Fail closed: with `$KLT_ARTIFACT_BROKER` unset, a klt without
  `artifact put` (needs klayout-tools `7e3561f`+), or an unreachable broker, the
  runner exits nonzero before simulating and writes nothing. A put that fails
  after the run writes no manifest and no record and keeps the stage for retry.
  There is no fallback to committing bytes.
- Verify: `klt artifact verify manifests/artifacts/<bench>-<run-id>.manifest.json`;
  fetch one object with `klt artifact get`.
- CI: `sim/lib/check_artifact_manifests.py` validates the schema, accepts only
  `artifact:` URIs, fails if a stored object's bytes are also tracked, and
  rejects bucket URLs and cloud account ARNs anywhere under `manifests/`. Never write the
  broker URL into the repo.
- Zero-byte outputs cannot be stored; the summary lists them.
- Manifest-forward only: evidence committed before this flow stays in
  `sim/*/records/`.
- Other benches (`offset-capability`, `gm-id-characterization`) adopt
  `artifact_store` when next run.
