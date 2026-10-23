import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import _paths  # noqa: F401  -- sets sys.path for sim/lib
import artifact_store as a

BROKER = "https://broker.example.invalid/x"
SHA = "a" * 64


class Result:
    def __init__(self, rc=0, out="", err=""):
        self.returncode, self.stdout, self.stderr = rc, out, err


def fake_put(calls, rc=0, uri="artifact:k/" + SHA, err=""):
    def run(cmd, **kw):
        calls.append((cmd, kw))
        if "--help" in cmd:
            return Result(rc)
        if rc != 0:
            return Result(rc, "", err)
        mpath = Path(cmd[cmd.index("--manifest") + 1])
        files = cmd[cmd.index("evidence") + 1:]
        entries = [{"sha256": SHA, "size": 1, "kind": "evidence", "uri": uri,
                    "producer": {"tool": "klt", "version": "1", "loom.repo": "o/n", "commit": None},
                    "name": Path(f).name} for f in files]
        mpath.write_text(json.dumps({"schema_version": 1, "entries": entries}))
        return Result(0)
    return run


class PreflightTests(unittest.TestCase):
    def test_unset_broker(self):
        with self.assertRaisesRegex(a.ArtifactError, "unset"):
            a.preflight(env={}, runner=fake_put([]), reachable=lambda b: True)

    def test_klt_without_put(self):
        with self.assertRaisesRegex(a.ArtifactError, "lacks"):
            a.preflight(env={a.BROKER_ENV: BROKER}, runner=fake_put([], rc=2), reachable=lambda b: True)

    def test_missing_klt_binary(self):
        def boom(*_a, **_k):
            raise FileNotFoundError(2, "No such file")
        with self.assertRaises(a.ArtifactError):
            a.preflight(env={a.BROKER_ENV: BROKER}, runner=boom, reachable=lambda b: True)

    def test_unreachable(self):
        with self.assertRaisesRegex(a.ArtifactError, "unreachable"):
            a.preflight(env={a.BROKER_ENV: BROKER}, runner=fake_put([]), reachable=lambda b: False)

    def test_ok_and_broker_not_in_argv(self):
        calls = []
        klt = a.preflight(env={a.BROKER_ENV: BROKER}, runner=fake_put(calls), reachable=lambda b: True)
        self.assertEqual(klt, ["klt"])
        self.assertFalse(any(BROKER in " ".join(c) for c, _ in calls))


class StoreTests(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.addCleanup(self._t.cleanup)
        self.root = Path(self._t.name)
        self.stage = a.stage_dir("b", "r1", self.root / "stage")
        (self.stage / "x.log").write_text("data")
        self.mdir = self.root / "manifests" / "artifacts"
        self.env = {a.BROKER_ENV: BROKER}

    def store(self, runner):
        return a.store("b", "r1", self.stage, ["klt"], env=self.env, runner=runner,
                       repo_root=self.root, manifest_dir=self.mdir)

    def test_success_writes_manifest_and_summary(self):
        m, s = self.store(fake_put([]))
        data = json.loads(m.read_text())
        self.assertTrue(all(e["uri"].startswith("artifact:") for e in data["entries"]))
        self.assertIn(SHA, s.read_text())
        self.assertEqual(sorted(p.name for p in self.mdir.iterdir()),
                         ["b-r1.manifest.json", "b-r1.summary.md"])

    def test_put_failure_writes_nothing_and_keeps_stage(self):
        with self.assertRaises(a.ArtifactError) as cm:
            self.store(fake_put([], rc=1, err=f"refused by {BROKER}"))
        self.assertNotIn(BROKER, str(cm.exception))
        self.assertFalse(self.mdir.exists())
        self.assertTrue((self.stage / "x.log").exists())

    def test_non_artifact_uri_rejected_nothing_written(self):
        with self.assertRaises(a.ArtifactError):
            self.store(fake_put([], uri="https://bucket.s3.amazonaws.com/x"))
        self.assertFalse(self.mdir.exists())

    def test_empty_file_skipped_and_listed(self):
        (self.stage / "empty.log").write_text("")
        calls = []
        _, s = self.store(fake_put(calls))
        put = [c for c, _ in calls if "--manifest" in c][0]
        self.assertFalse(any(p.endswith("empty.log") for p in put))
        self.assertIn("empty.log", s.read_text())

    def test_only_empty_files_is_error(self):
        (self.stage / "x.log").write_text("")
        with self.assertRaises(a.ArtifactError):
            self.store(fake_put([]))

    def test_no_overwrite(self):
        self.store(fake_put([]))
        with self.assertRaises(a.ArtifactError):
            self.store(fake_put([]))

    def test_bad_names(self):
        with self.assertRaises(a.ArtifactError):
            a.stage_dir("../x", "r", self.root)


if __name__ == "__main__":
    unittest.main()
