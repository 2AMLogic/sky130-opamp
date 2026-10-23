import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import _paths  # noqa: F401  -- sets sys.path for sim/lib
import check_artifact_manifests as c

BYTES = b"raw evidence"
import hashlib
SHA = hashlib.sha256(BYTES).hexdigest()


def entry(**kw):
    e = {"sha256": SHA, "size": len(BYTES), "kind": "evidence", "uri": "artifact:k/" + SHA,
         "producer": {"tool": "klt", "version": "1", "loom.repo": "o/n", "commit": None}}
    e.update(kw)
    return e


class CheckTests(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.addCleanup(self._t.cleanup)
        self.root = Path(self._t.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / "manifests" / "artifacts").mkdir(parents=True)

    def manifest(self, entries, name="b-r.manifest.json"):
        (self.root / "manifests" / "artifacts" / name).write_text(
            json.dumps({"schema_version": 1, "entries": entries}))

    def track(self, rel, data=b"x"):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        subprocess.run(["git", "-C", str(self.root), "add", rel], check=True)

    def run_check(self):
        return c.check(self.root)

    def test_good(self):
        self.manifest([entry()])
        self.assertEqual(self.run_check(), [])

    def test_non_artifact_uri(self):
        self.manifest([entry(uri="https://x.example/obj")])
        self.assertTrue(any("artifact:" in f for f in self.run_check()))

    def test_bad_schema(self):
        (self.root / "manifests/artifacts/b-r.manifest.json").write_text("{}")
        self.assertTrue(self.run_check())

    def test_bad_entry_fields(self):
        self.manifest([entry(size=0, sha256="XYZ")])
        self.assertGreaterEqual(len(self.run_check()), 2)

    def test_committed_bytes_also_stored(self):
        self.manifest([entry()])
        self.track("sim/opamp-characterization/records/x-logs/a.log", BYTES)
        self.assertTrue(any("also committed" in f for f in self.run_check()))

    def test_unrelated_bytes_fine(self):
        self.manifest([entry()])
        self.track("sim/other.log", b"different")
        self.assertEqual(self.run_check(), [])

    def test_bucket_string(self):
        self.manifest([entry()])
        self.track("manifests/artifacts/README.md", b"see s3://bucket/key")
        self.assertTrue(any("s3://" in f for f in self.run_check()))

    def test_arn_string(self):
        self.track("manifests/artifacts/n.md", b"arn:aws:iam::1:role/x")
        self.assertTrue(self.run_check())

    def test_repo_is_clean(self):
        self.assertEqual(c.check(Path(__file__).resolve().parent.parent), [])

    def test_readme_does_not_trip_its_own_checker(self):
        repo = Path(__file__).resolve().parent.parent
        text = (repo / "manifests" / "artifacts" / "README.md").read_text(encoding="utf-8")
        self.assertIsNone(c.FORBIDDEN.search(text))

    def test_no_test_fixture_manifests_in_real_tree(self):
        # Tests use placeholder commit abc1234; they must never write into the real manifests/ tree.
        repo = Path(__file__).resolve().parent.parent
        self.assertEqual(sorted((repo / "manifests" / "artifacts").glob("*-abc1234-*")), [])


if __name__ == "__main__":
    unittest.main()
