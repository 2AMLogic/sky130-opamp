"""Simulator-free tests for the record-namespace allocator (issue #75)."""

import sys
import tempfile
import threading
import unittest
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import _paths  # noqa: F401  -- sets sys.path for spice_harness
import spice_harness as sh

FIXED = datetime(2026, 10, 9, 12, 0, 0, tzinfo=timezone.utc)


def _alloc_in_process(args):
    records, = args
    return sh.allocate_record_id(Path(records), "abc1234", now=FIXED)


class AllocTests(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.root = Path(d.name)
        self.records = self.root / "records"
        self.records.mkdir()

    def test_prefix_preserved_and_ids_disjoint_for_same_second_and_revision(self):
        ids = [sh.allocate_record_id(self.records, "abc1234", now=FIXED) for _ in range(50)]
        self.assertEqual(len(set(ids)), 50)
        for i in ids:
            self.assertTrue(i.startswith("20261009-120000-abc1234-"))

    def test_threads_get_exclusive_ownership(self):
        out, lock = [], threading.Lock()

        def work():
            rid = sh.allocate_record_id(self.records, "abc1234", now=FIXED)
            with lock:
                out.append(rid)

        ts = [threading.Thread(target=work) for _ in range(16)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(len(set(out)), 16)

    def test_processes_get_exclusive_ownership(self):
        with ProcessPoolExecutor(max_workers=2) as ex:
            ids = list(ex.map(_alloc_in_process, [(str(self.records),)] * 8))
        self.assertEqual(len(set(ids)), 8)

    def test_forced_token_collision_fails_clearly(self):
        rid = sh.allocate_record_id(self.records, "abc", now=FIXED, token="dead")
        with self.assertRaises(sh.RecordCollisionError):
            sh.allocate_record_id(self.records, "abc", now=FIXED, token="dead")
        self.assertTrue((self.records / ".reservations" / rid).is_dir())

    def test_existing_artifacts_block_reuse_and_are_not_truncated(self):
        # A pre-existing (e.g. committed) record under the same ID, and a snapshot dir.
        legacy = self.records / "20261009-120000-abc-dead.json"
        legacy.write_text("keep")
        snaps = self.root / "snaps"
        (snaps / "20261009-120000-abc-beef").mkdir(parents=True)
        for tok in ("dead", "beef"):
            with self.assertRaises(sh.RecordCollisionError):
                sh.allocate_record_id(self.records, "abc", now=FIXED, token=tok, extra_dirs=[snaps])
        self.assertEqual(legacy.read_text(), "keep")

    def test_historical_id_without_token_is_not_clobbered(self):
        # Historical IDs have no token suffix; a new ID must never equal or nest in one.
        hist = self.records / "20261009-120000-abc.json"
        hist.write_text("old")
        rid = sh.allocate_record_id(self.records, "abc", now=FIXED)
        self.assertNotEqual(rid, "20261009-120000-abc")
        self.assertEqual(hist.read_text(), "old")

    def test_write_new_never_truncates(self):
        p = self.records / "x.json"
        sh.write_new(p, "one")
        with self.assertRaises(sh.RecordCollisionError):
            sh.write_new(p, "two")
        self.assertEqual(p.read_text(), "one")

    def test_make_new_dir_refuses_existing(self):
        d = self.root / "snap"
        sh.make_new_dir(d)
        with self.assertRaises(sh.RecordCollisionError):
            sh.make_new_dir(d)


class ReaderCompatTests(unittest.TestCase):
    def test_latest_ac_csv_orders_new_ids_after_historical(self):
        pvt = _paths.load_module("pvt_sweep_alloc", _paths.EXP / "bin" / "pvt_sweep.py")
        with tempfile.TemporaryDirectory() as d:
            rec = Path(d)
            for n in ("20260916-032327-edc9f22-ac.csv", "20261009-120000-abc1234-a1b2c3-ac.csv"):
                (rec / n).write_text("x")
            old = pvt.RECORDS_DIR
            pvt.RECORDS_DIR = rec
            try:
                got = pvt.latest_ac_csv("20261009-120001-abc1234-ffffff")
                self.assertEqual(got.name, "20261009-120000-abc1234-a1b2c3-ac.csv")
                got = pvt.latest_ac_csv("20261009-120000-abc1234-000000")
                self.assertEqual(got.name, "20260916-032327-edc9f22-ac.csv")
            finally:
                pvt.RECORDS_DIR = old


if __name__ == "__main__":
    unittest.main()
