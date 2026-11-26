"""Simulator-free tests: PSRR/noise campaigns bind to one immutable DUT snapshot (#151)."""

import contextlib
import hashlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _paths
from _paths import EXP, REPO
import dut_identity as di

m = _paths.load_module("psrr_noise_sweep", EXP / "bin" / "psrr_noise_sweep.py")

LIVE_ORIG = (REPO / di.CURRENT_NETLIST_REL).read_text()


def sha(path):
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fake_payload(req):
    return {"status": "pass", "corner_count": 1, "passed": 1, "failed": 0, "errored": 0,
            "corners": [{"process": "tt", "temperature_c": 27.0, "supply_v": {"vdd": 1.8},
                         "status": "pass", "measurements": [], "diagnostics": [],
                         "corner_id": "tt/1.800V/27C", "artifacts": {}}],
            "environment": {"engine_version": "fake"}}


class Repo:
    """A temp repo with the live netlist, and the sweep module repointed at it."""

    def __init__(self, test):
        self.tmp = Path(tempfile.mkdtemp(prefix="psrr-id-"))
        test.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.live = self.tmp / di.CURRENT_NETLIST_REL
        self.live.parent.mkdir(parents=True)
        self.live.write_text(LIVE_ORIG)
        self.exp = self.tmp / "sim" / "opamp-characterization"
        self.records = self.exp / "records"
        self.snaps = self.exp / "netlist-snapshots"
        self.records.mkdir(parents=True)
        for name, val in (("REPO_ROOT", self.tmp), ("RECORDS_DIR", self.records),
                          ("SNAPSHOT_DIR", self.snaps), ("DESIGN_NETLIST", self.live)):
            p = mock.patch.object(m, name, val)
            p.start()
            test.addCleanup(p.stop)
        for name, val in (("git_sha", lambda root: "abc1234"), ("klt_version", lambda: "fake")):
            p = mock.patch.object(m, name, val)
            p.start()
            test.addCleanup(p.stop)
        # Issue #240: never reach the real broker or write under the real manifests/ tree.
        stage_root = self.tmp / ".stage"

        def stage_dir(bench, run_id):
            d = stage_root / f"{bench}-{run_id}"
            d.mkdir(parents=True, exist_ok=True)
            return d

        for name, val in (("preflight", lambda: ["klt"]), ("klt_command", lambda: ["klt"]),
                          ("stage_dir", stage_dir),
                          ("store", lambda b, r, s, k: (self.tmp / "manifests" / f"{b}-{r}.manifest.json",
                                                         self.tmp / "x.summary.md"))):
            p = mock.patch.object(m.artifact_store, name, val)
            p.start()
            test.addCleanup(p.stop)
        p = mock.patch.object(m.shutil, "which", lambda t: f"/usr/bin/{t}")
        p.start()
        test.addCleanup(p.stop)

    def campaign(self):
        return self.records.glob("*-psrr-noise.json")


class SubmissionTests(unittest.TestCase):
    def run_sweep(self, repo, fake, extra=()):
        with mock.patch.object(m, "run_klt", fake), contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            return m.main(["--backend", "local", "--corners", "tt", "--temps", "27", *extra])

    def test_live_edit_after_capture_cannot_change_any_submitted_bench(self):
        repo = Repo(self)
        seen = []

        def fake(req_path, outdir, backend):
            if not seen:   # mutate the live design after capture, before/while submitting
                repo.live.write_text(LIVE_ORIG + "\n* edited mid-campaign\n")
            req = json.loads(Path(req_path).read_text())
            body = Path(req["netlist"])
            text = body.read_text()
            self.assertIn('.include "opamp_core.spice"', text)
            self.assertNotIn("design/netlist", text)
            seen.append((body.parent, sha(body.parent / "opamp_core.spice")))
            return 0, fake_payload(req), ""

        self.assertEqual(self.run_sweep(repo, fake), 0)
        self.assertEqual(len(seen), 3)
        meta_path, = repo.campaign()
        meta = json.loads(meta_path.read_text())
        self.assertEqual({h for _, h in seen}, {meta["dut"]["sha256"]})
        self.assertEqual(len({d for d, _ in seen}), 1)
        self.assertEqual(meta["dut"]["sha256"], "sha256:" + hashlib.sha256(LIVE_ORIG.encode()).hexdigest())
        self.assertNotEqual(sha(repo.live), meta["dut"]["sha256"])
        # requests, bodies, DUT retained with no returned deck artifacts
        snap = repo.tmp / meta["dut"]["snapshot_path"]
        for tag in ("psrr-vdd", "psrr-vss", "noise"):
            self.assertTrue((snap.parent / f"{tag}.spice").is_file())
            self.assertTrue((snap.parent / f"{tag}.request.json").is_file())
        self.assertEqual(di.validate_psrr_noise(repo.tmp), 0)  # historical integrity survives the edit

    def test_both_envelope_destinations_omit_only_the_client_path(self):
        repo = Repo(self)
        payload = fake_payload(None)
        payload["environment"]["client_ngspice_binary"] = "/workstation/bin/ngspice"
        expected = {**payload, "environment": {"engine_version": "fake"}}
        for extra, destination in [(["--export-envelopes", "envelopes"], repo.tmp / "envelopes"),
                                   ([], repo.records)]:
            self.assertEqual(self.run_sweep(repo, lambda *args: (0, payload, ""),
                                            ["--benches", "noise", *extra]), 0)
            envelope, = destination.glob("*-noise.klt.json")
            self.assertEqual(json.loads(envelope.read_text()), expected)
            self.assertIn("client_ngspice_binary", payload["environment"])

    def test_failure_writes_no_record_and_no_orphan_snapshot(self):
        repo = Repo(self)
        self.assertEqual(self.run_sweep(repo, lambda *a: (1, None, "boom")), 1)
        self.assertEqual(list(repo.campaign()), [])
        self.assertEqual(list(repo.snaps.glob("*")) if repo.snaps.exists() else [], [])

    def test_export_destination_is_checked_before_submission(self):
        repo = Repo(self)
        destination = repo.tmp / "envelopes.json"
        destination.write_text("existing file")
        submit = mock.Mock()
        rc = self.run_sweep(repo, submit, ["--benches", "noise", "--export-envelopes", destination.name])
        self.assertEqual(rc, 1)
        submit.assert_not_called()
        self.assertEqual(destination.read_text(), "existing file")
        self.assertFalse(list(repo.records.glob("*.json")))
        self.assertFalse(list(repo.snaps.glob("*")))

    def test_late_export_collision_rolls_back_only_this_campaign(self):
        repo = Repo(self)
        destination = repo.tmp / "envelopes"
        destination.mkdir()

        def submit(req_path, outdir, backend):
            # An export target appears after preflight, for the second bench.
            snapshot = Path(json.loads(req_path.read_text())["netlist"]).parent
            rid = snapshot.name.removesuffix("-psrr-noise")
            (destination / f"{rid}-noise.klt.json").write_text("existing envelope")
            return 0, fake_payload(None), ""

        rc = self.run_sweep(repo, submit, ["--benches", "psrr_vdd,noise", "--export-envelopes", "envelopes"])
        self.assertEqual(rc, 1)
        existing, = destination.iterdir()
        self.assertEqual(existing.read_text(), "existing envelope")
        self.assertFalse([p for p in repo.records.iterdir() if p.is_file()])
        self.assertFalse(list(repo.snaps.glob("*")))

    def test_partial_envelope_write_discards_campaign(self):
        repo = Repo(self)
        write_new = m.write_new

        def write(path, text):
            if path.name.endswith("-noise.klt.json"):
                path.write_text(text[:10])
                raise OSError("disk full")
            return write_new(path, text)

        with mock.patch.object(m, "write_new", side_effect=write):
            rc = self.run_sweep(repo, lambda *args: (0, fake_payload(None), ""),
                                ["--benches", "psrr_vdd,noise", "--export-envelopes", "envelopes"])
        self.assertEqual(rc, 1)
        self.assertFalse(list((repo.tmp / "envelopes").iterdir()))
        self.assertFalse([p for p in repo.records.iterdir() if p.is_file()])
        self.assertFalse(list(repo.snaps.glob("*")))

    def test_dry_run_leaves_records_tree_untouched(self):
        repo = Repo(self)
        called = []
        rc = self.run_sweep(repo, lambda *a: called.append(a), ["--dry-run"])
        self.assertEqual((rc, called), (0, []))
        self.assertEqual(list(repo.campaign()), [])
        self.assertFalse(repo.snaps.exists())


class ValidateTests(unittest.TestCase):
    def good(self):
        repo = Repo(self)
        with mock.patch.object(m, "run_klt", lambda p, o, b: (0, fake_payload(None), "")), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(m.main(["--backend", "local", "--corners", "tt", "--temps", "27"]), 0)
        meta_path, = repo.campaign()
        meta = json.loads(meta_path.read_text())
        return repo, meta_path, meta, repo.tmp / meta["dut"]["snapshot_path"]

    def check(self, repo):
        out = {}
        for p in di.psrr_noise_records(repo.tmp):
            out[p.name] = di.psrr_noise_problems(p, repo.tmp)
        (_, problems), = out.values()
        return problems

    def test_intact_verifies(self):
        repo, *_ = self.good()
        self.assertEqual(self.check(repo), [])

    def test_corrupt_and_missing_snapshot_rejected(self):
        repo, _, _, snap = self.good()
        snap.write_text("* tampered\n")
        self.assertTrue(any("corrupted" in p for p in self.check(repo)))
        snap.unlink()
        self.assertTrue(any("missing" in p for p in self.check(repo)))

    def test_body_referencing_live_dut_rejected(self):
        repo, _, _, snap = self.good()
        body = snap.parent / "noise.spice"
        body.write_text(body.read_text().replace('"opamp_core.spice"', '"../../../design/netlist/opamp_core.spice"'))
        self.assertTrue(any("noise.spice" in p and "not the DUT snapshot" in p for p in self.check(repo)))

    def test_missing_rendered_body_or_request_rejected(self):
        repo, _, _, snap = self.good()
        (snap.parent / "psrr-vss.spice").unlink()
        self.assertTrue(any("psrr_vss" in p for p in self.check(repo)))
        (snap.parent / "noise.request.json").unlink()
        self.assertTrue(any("bench noise" in p for p in self.check(repo)))

    def test_legacy_record_unverified_not_inferred(self):
        repo, meta_path, meta, _ = self.good()
        del meta["dut"]
        meta_path.write_text(json.dumps(meta))
        self.assertEqual(di.psrr_noise_problems(meta_path, repo.tmp), (di.UNVERIFIED, []))
        self.assertEqual(di.validate_psrr_noise(repo.tmp), 0)
        self.assertEqual(di.validate_psrr_noise(repo.tmp, require_verified=True), 1)

    def test_validation_record_checks(self):
        repo, _, _, snap = self.good()
        d = snap.parent.parent / "vrid-psrr-noise-validation"
        d.mkdir()
        dut = di.capture_dut(repo.live, d, repo.tmp)
        (d / "noise.spice").write_text('.include "opamp_core.spice"\n')
        (d / "a.request.json").write_text("{}")
        rec = {"record_id": "vrid", "dut": dut,
               "runs": {"a": {"request": {"netlist": "../netlist-snapshots/vrid-psrr-noise-validation/noise.spice"}}}}
        p = repo.records / "vrid-psrr-noise-validation.json"
        p.write_text(json.dumps(rec))
        self.assertEqual(di.psrr_noise_problems(p, repo.tmp), (di.VERIFIED, []))
        rec["runs"]["a"]["request"]["netlist"] = "../testbench/noise.cir"
        p.write_text(json.dumps(rec))
        self.assertTrue(di.psrr_noise_problems(p, repo.tmp)[1])


class CommittedStateTests(unittest.TestCase):
    def test_committed_psrr_noise_records_validate(self):
        self.assertEqual(di.validate_psrr_noise(REPO), 0)


if __name__ == "__main__":
    unittest.main()
