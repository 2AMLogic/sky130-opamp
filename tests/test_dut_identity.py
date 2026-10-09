"""Simulator-free tests for DUT snapshot capture and identity checks (issue #104)."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import _paths
from _paths import EXP, REPO
import dut_identity as di

pvt = _paths.load_module("pvt_sweep", EXP / "bin" / "pvt_sweep.py")

NETLIST = (REPO / "design" / "netlist" / "opamp_core.spice").read_text()


class FakePdk:
    def corner_include(self, corner):
        return Path(f"/pdk/corners/{corner}.spice")

    def rc_includes(self):
        return [Path("/pdk/rc/base.spice"), Path("/pdk/rc/lin.spice")]


class Campaign:
    """A temp repo with a live netlist, a captured snapshot and a record."""

    def __init__(self, test):
        self.tmp = Path(tempfile.mkdtemp(prefix="dut-id-"))
        test.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.live = self.tmp / "design" / "netlist" / "opamp_core.spice"
        self.live.parent.mkdir(parents=True)
        self.live.write_text(NETLIST)
        self.snap_dir = self.tmp / "sim" / "opamp-characterization" / "netlist-snapshots" / "rid"
        self.snap_dir.mkdir(parents=True)
        self.dut = di.capture_dut(self.live, self.snap_dir, self.tmp)
        self.record = {"record_id": "rid", "matrix": {}, "dut": self.dut}


class CaptureTests(unittest.TestCase):
    def test_capture_records_path_and_hash(self):
        c = Campaign(self)
        self.assertEqual(c.dut["snapshot_path"], "sim/opamp-characterization/netlist-snapshots/rid/opamp_core.spice")
        self.assertEqual(c.dut["source_path"], "design/netlist/opamp_core.spice")
        self.assertEqual(c.dut["sha256"], di.sha256_bytes(NETLIST.encode()))

    def test_live_edit_after_capture_cannot_change_rendered_inputs(self):
        c = Campaign(self)
        old = pvt.ACTIVE_DUT[0]
        pvt.ACTIVE_DUT[0] = c.tmp / c.dut["snapshot_path"]
        try:
            before = pvt.common_subs(FakePdk(), "tt", 27.0, 1.8)
            c.live.write_text(NETLIST.replace("W=", "W=9", 1))  # mutate the live design
            after = pvt.common_subs(FakePdk(), "tt", 27.0, 1.8)
            self.assertEqual(before["OPAMP_NETLIST"], after["OPAMP_NETLIST"])
            self.assertNotEqual(after["OPAMP_NETLIST"], c.live)
            self.assertEqual(di.sha256_file(Path(after["OPAMP_NETLIST"])), c.dut["sha256"])
        finally:
            pvt.ACTIVE_DUT[0] = old

    def test_klt_request_uses_staged_snapshot_copy(self):
        c = Campaign(self)
        old = pvt.ACTIVE_DUT[0]
        pvt.ACTIVE_DUT[0] = c.tmp / c.dut["snapshot_path"]
        try:
            class P:
                variant = "sky130A"
            req, tag = pvt.build_klt_request("tran_step", None, None, P(), ["tt"], [27.0], c.tmp / "req", "local")
            c.live.write_text("* edited live netlist\n")
            body = (req.parent / f"{tag}-body.spice").read_text()
            self.assertIn('.include "opamp_core.spice"', body)
            self.assertEqual(di.sha256_file(req.parent / "opamp_core.spice"), c.dut["sha256"])
        finally:
            pvt.ACTIVE_DUT[0] = old


class VerifyTests(unittest.TestCase):
    def test_intact_snapshot_verifies(self):
        c = Campaign(self)
        self.assertEqual(di.verify_record_dut(c.record, c.tmp), (di.VERIFIED, []))

    def test_missing_snapshot_rejected(self):
        c = Campaign(self)
        (c.tmp / c.dut["snapshot_path"]).unlink()
        state, problems = di.verify_record_dut(c.record, c.tmp)
        self.assertTrue(any("missing" in p for p in problems))

    def test_corrupted_snapshot_rejected(self):
        c = Campaign(self)
        (c.tmp / c.dut["snapshot_path"]).write_text(NETLIST + "* tamper\n")
        _, problems = di.verify_record_dut(c.record, c.tmp)
        self.assertTrue(any("corrupted" in p for p in problems))

    def test_deck_including_live_netlist_rejected(self):
        c = Campaign(self)
        (c.snap_dir / "ac.spice").write_text(f'.include "{c.live}"\n')
        _, problems = di.verify_record_dut(c.record, c.tmp)
        self.assertTrue(any("not the DUT snapshot" in p for p in problems))

    def test_snapshot_relative_and_bare_includes_accepted(self):
        c = Campaign(self)
        (c.snap_dir / "ac.spice").write_text(f'.include "{c.dut["snapshot_path"]}"\n')
        (c.snap_dir / "icmr-body.spice").write_text('.include "opamp_core.spice"\n')
        self.assertEqual(di.verify_record_dut(c.record, c.tmp)[1], [])

    def test_legacy_record_is_unverified_not_inferred(self):
        state, problems = di.verify_record_dut({"record_id": "x", "git": {"sha": "abc"}}, REPO)
        self.assertEqual((state, problems), (di.UNVERIFIED, []))
        self.assertEqual(di.check_current({"record_id": "x"}, REPO), [])


class CurrentDesignTests(unittest.TestCase):
    def test_same_record_is_current_then_historical_after_width_change(self):
        c = Campaign(self)
        self.assertEqual(di.check_current(c.record, c.tmp), [])
        # negative control: change a device width; the record and its hashes stay intact
        before = json.dumps(c.record, sort_keys=True)
        c.live.write_text(NETLIST.replace("W=4.634", "W=4.7", 1) if "W=4.634" in NETLIST else NETLIST + "* W change\n")
        diag = di.check_current(c.record, c.tmp)
        self.assertEqual(len(diag), 1)
        self.assertIn("DUT mismatch", diag[0])
        self.assertIn(c.dut["sha256"], diag[0])
        # ... while the same record is still valid historical evidence
        self.assertEqual(di.verify_record_dut(c.record, c.tmp), (di.VERIFIED, []))
        self.assertEqual(before, json.dumps(c.record, sort_keys=True))

    def _manifest_repo(self, c):
        rec = c.tmp / di.RECORDS_REL
        rec.mkdir(parents=True)
        (rec / "rid.json").write_text(json.dumps(c.record))
        (rec / "rid.characterization.json").write_text("{}")
        (c.tmp / "manifests").mkdir()
        m = c.tmp / di.MANIFEST_REL
        m.write_text(json.dumps({"evidence": {"8": {"file": f"{di.RECORDS_REL}/rid.characterization.json"}}}))
        return m

    def test_cli_current_fails_on_mismatch_and_passes_otherwise(self):
        c = Campaign(self)
        m = self._manifest_repo(c)
        self.assertEqual(di.validate_current(c.tmp, m, "8"), 0)
        c.live.write_text(NETLIST + "* edited\n")
        self.assertEqual(di.validate_current(c.tmp, m, "8"), 1)
        self.assertEqual(di.validate_all(c.tmp), 0)  # historical validation unaffected

    def test_legacy_current_unverified_passes_unless_strict(self):
        c = Campaign(self)
        del c.record["dut"]
        m = self._manifest_repo(c)
        self.assertEqual(di.validate_current(c.tmp, m, "8"), 0)
        self.assertEqual(di.validate_current(c.tmp, m, "8", require_verified=True), 1)


class CommonDutTests(unittest.TestCase):
    """Chunk-set provenance used by the offset campaign runner (issue #113)."""

    def test_same_hash_verified(self):
        c = Campaign(self)
        st, sha, probs = di.common_dut([("a", c.record), ("b", dict(c.record))], c.tmp)
        self.assertEqual((st, sha, probs), (di.VERIFIED, c.dut["sha256"], []))

    def test_mixed_hashes_name_offenders(self):
        c = Campaign(self)
        other = {"dut": dict(c.dut, sha256="sha256:" + "1" * 64)}
        _, _, probs = di.common_dut([("a", c.record), ("b", other)], c.tmp)
        self.assertTrue(any("mixed DUT hashes" in p and "b" in p for p in probs))
        self.assertTrue(any(p.startswith("b: DUT snapshot corrupted") for p in probs))

    def test_missing_snapshot_named(self):
        c = Campaign(self)
        (c.tmp / c.dut["snapshot_path"]).unlink()
        _, _, probs = di.common_dut([("a", c.record)], c.tmp)
        self.assertEqual(probs, [f"a: DUT snapshot missing: {c.dut['snapshot_path']}"])

    def test_legacy_all_unverified_and_partial_rejected(self):
        c = Campaign(self)
        self.assertEqual(di.common_dut([("x", {}), ("y", {})], c.tmp), (di.UNVERIFIED, None, []))
        _, _, probs = di.common_dut([("x", {}), ("a", c.record)], c.tmp)
        self.assertTrue(any("mixed provenance" in p for p in probs))


class CommittedStateTests(unittest.TestCase):
    def test_committed_records_validate(self):
        self.assertEqual(di.validate_all(REPO), 0)

    def test_committed_current_citation_validates(self):
        self.assertEqual(di.validate_current(REPO, REPO / di.MANIFEST_REL, "8"), 0)


if __name__ == "__main__":
    unittest.main()
