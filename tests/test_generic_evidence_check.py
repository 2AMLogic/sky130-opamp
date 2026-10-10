import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import _paths
gec = _paths.load_module("generic_evidence_check",
                         _paths.REPO / "design" / "bin" / "generic_evidence_check.py")

MANIFEST = "manifests/m.json"


def h(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


class Fixture(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.root = Path(self._td.name)

    def write(self, rel, content):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content if isinstance(content, bytes) else content.encode())
        return p

    def envelope(self, rel, artifact, declared, kind="generic", **extra):
        env = {"kind": kind, "provenance": {"input": {}}}
        if artifact is not None:
            env["provenance"]["input"]["path"] = artifact
        if declared is not None:
            env["provenance"]["input"]["content_hash"] = declared
        env.update(extra)
        self.write(rel, json.dumps(env))

    def manifest(self, evidence):
        self.write(MANIFEST, json.dumps({"evidence": evidence}))

    def run_check(self):
        return gec.check_manifest(MANIFEST, self.root)


class CheckTests(Fixture):
    def valid(self):
        self.write("ev/rec.md", "record\n")
        self.envelope("ev/env.json", "rec.md", h(b"record\n"))
        self.manifest({"8": {"file": "ev/env.json", "content_hash": "sha256:x"}})

    def test_valid_passes(self):
        self.valid()
        n, oks, fails = self.run_check()
        self.assertEqual((n, fails), (1, []))
        self.assertEqual(len(oks), 1)

    def test_bare_string_entry(self):
        self.valid()
        self.manifest({"8": "ev/env.json"})
        self.assertEqual(self.run_check()[0], 1)

    def test_altered_artifact_fails_without_touching_hashes(self):
        self.valid()
        env_before = (self.root / "ev/env.json").read_bytes()
        man_before = (self.root / MANIFEST).read_bytes()
        self.write("ev/rec.md", "record\nappended\n")
        n, _, fails = self.run_check()
        self.assertEqual(len(fails), 1)
        self.assertIn("changed under its envelope", fails[0])
        self.assertEqual((self.root / "ev/env.json").read_bytes(), env_before)
        self.assertEqual((self.root / MANIFEST).read_bytes(), man_before)

    def test_envelope_dir_branch(self):
        self.valid()  # artifact next to the envelope
        self.assertEqual(self.run_check()[2], [])

    def test_repo_relative_branch(self):
        self.write("art/rec.md", "x")
        self.envelope("ev/env.json", "art/rec.md", h(b"x"))
        self.manifest({"1": "ev/env.json"})
        n, oks, fails = self.run_check()
        self.assertEqual((n, fails), (1, []))
        self.assertIn("art/rec.md", oks[0])

    def test_envelope_dir_wins_over_repo_relative(self):
        self.write("ev/rec.md", "near")
        self.write("rec.md", "far")
        self.envelope("ev/env.json", "rec.md", h(b"near"))
        self.manifest({"1": "ev/env.json"})
        self.assertEqual(self.run_check()[2], [])
        self.envelope("ev/env.json", "rec.md", h(b"far"))
        self.assertEqual(len(self.run_check()[2]), 1)

    def test_absent_artifact(self):
        self.envelope("ev/env.json", "gone.md", h(b"x"))
        self.manifest({"1": "ev/env.json"})
        fails = self.run_check()[2]
        self.assertEqual(len(fails), 1)
        self.assertIn("resolves to no file", fails[0])

    def test_malformed_json_envelope(self):
        self.write("ev/env.json", "{not json")
        self.manifest({"1": "ev/env.json"})
        self.assertIn("cannot read evidence envelope", self.run_check()[2][0])

    def test_absent_envelope(self):
        self.manifest({"1": "ev/missing.json"})
        self.assertEqual(len(self.run_check()[2]), 1)

    def test_malformed_manifest(self):
        self.write(MANIFEST, "[[")
        self.assertIn("cannot read manifest", self.run_check()[2][0])

    def test_missing_path_or_hash(self):
        self.write("ev/rec.md", "x")
        self.envelope("ev/a.json", None, h(b"x"))
        self.envelope("ev/b.json", "rec.md", None)
        self.manifest({"1": "ev/a.json", "2": "ev/b.json"})
        fails = self.run_check()[2]
        self.assertEqual(len(fails), 2)
        self.assertTrue(all("must declare both" in f for f in fails))

    def test_non_generic_skipped(self):
        self.envelope("ev/env.json", None, None, kind="klt")
        self.manifest({"1": "ev/env.json"})
        self.assertEqual(self.run_check()[:3:2], (0, []))

    def test_command_only_skipped(self):
        self.manifest({"1": {"command": ["klt", "drc"]}})
        self.assertEqual(self.run_check(), (0, [], []))

    def test_failures_aggregate_in_item_order(self):
        self.envelope("ev/a.json", "gone.md", h(b"x"))
        self.write("ev/b.md", "changed")
        self.envelope("ev/b.json", "b.md", h(b"orig"))
        self.manifest({"10": "ev/b.json", "2": "ev/a.json"})
        fails = self.run_check()[2]
        self.assertEqual(len(fails), 2)
        self.assertTrue(fails[0].startswith("item 2:"))
        self.assertTrue(fails[1].startswith("item 10:"))


class CliTests(Fixture):
    def cli(self):
        return subprocess.run(
            [sys.executable, str(_paths.REPO / "design/bin/generic_evidence_check.py"),
             "--manifest", MANIFEST, "--root", str(self.root)],
            capture_output=True, text=True)

    def test_exit_codes(self):
        self.write("ev/rec.md", "r")
        self.envelope("ev/env.json", "rec.md", h(b"r"))
        self.manifest({"1": "ev/env.json"})
        self.assertEqual(self.cli().returncode, 0)
        self.write("ev/rec.md", "r2")
        r = self.cli()
        self.assertEqual(r.returncode, 1)
        self.assertIn("item 1", r.stderr)


class CommittedEvidenceTests(unittest.TestCase):
    def test_committed_generic_evidence_is_fresh(self):
        n, _, fails = gec.check_manifest(gec.DEFAULT_MANIFEST, _paths.REPO)
        self.assertEqual(fails, [])
        self.assertGreaterEqual(n, 1)

    def test_signoff_workflow_calls_checker_without_inline_hashing(self):
        text = (_paths.REPO / ".github/workflows/signoff.yml").read_text()
        self.assertIn("design/bin/generic_evidence_check.py", text)
        self.assertNotIn("hashlib", text)

    def test_local_runner_calls_checker(self):
        ci = _paths.load_module("check_ci_g", _paths.REPO / "design/bin/check_ci.py")
        self.assertTrue(any("generic_evidence_check.py" in " ".join(c)
                            for _, c in ci.default_checks()))


if __name__ == "__main__":
    unittest.main()
