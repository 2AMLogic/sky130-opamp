import unittest
from pathlib import Path

import _paths  # noqa: F401  -- sets sys.path for sim/lib
import append_only_check as ao

R = "sim/opamp-characterization/records/x.md"
C = "sim/gm-id-characterization/corners/tt.log"
N = "sim/opamp-characterization/netlist-snapshots/a.cir"


def z(text):
    """Convert readable tab/newline name-status lines to `-z` format."""
    out = []
    for line in text.splitlines():
        if line:
            out += line.split("\t")
    return "".join(f + "\0" for f in out)


def check(text, allow=None):
    return ao.find_violations(z(text), allow or {})


class AppendOnlyTests(unittest.TestCase):
    def test_add_passes(self):
        v, a = check(f"A\t{R}\nA\t{C}\nA\t{N}\n")
        self.assertEqual((v, a), ([], []))

    def test_modify_fails(self):
        v, _ = check(f"M\t{R}\n")
        self.assertEqual(v, [("M", R)])

    def test_delete_fails(self):
        self.assertEqual(check(f"D\t{C}\n")[0], [("D", C)])

    def test_type_change_fails(self):
        self.assertEqual(check(f"T\t{N}\n")[0], [("T", N)])

    def test_rename_old_path_is_violation(self):
        new = "sim/opamp-characterization/records/y.md"
        v, _ = check(f"R100\t{R}\t{new}\n")
        self.assertEqual(v, [("R100", R)])

    def test_rename_into_guarded_from_outside_passes(self):
        v, _ = check(f"R090\tdocs/x.md\t{R}\n")
        self.assertEqual(v, [])

    def test_unguarded_paths_ignored(self):
        v, _ = check("M\tsim/opamp-characterization/README.md\nM\tsim/lib/spice_harness.py\nD\tdesign/x\n")
        self.assertEqual(v, [])

    def test_allowlisted_passes(self):
        v, a = check(f"M\t{R}\n", {R: "#99"})
        self.assertEqual((v, a), ([], [("M", R)]))

    def test_allowlist_only_covers_listed_path(self):
        v, _ = check(f"M\t{R}\nD\t{C}\n", {R: "#99"})
        self.assertEqual(v, [("D", C)])

    def test_message_has_remediation_and_allowlist(self):
        v, _ = check(f"M\t{R}\n")
        msg = ao.remediation(v)
        self.assertIn(R, msg)
        self.assertIn(ao.DEFAULT_ALLOWLIST, msg)
        self.assertIn("<issue-or-DR>", msg)

    def test_parse_allowlist(self):
        d = ao.parse_allowlist(f"# c\n\n{R} | #12\n")
        self.assertEqual(d, {R: "#12"})
        with self.assertRaises(ValueError):
            ao.parse_allowlist(f"{R}\n")

    def test_committed_allowlist_parses(self):
        ao.parse_allowlist(
            _paths.REPO.joinpath(ao.DEFAULT_ALLOWLIST).read_text(encoding="utf-8"))

    def test_special_char_paths_are_guarded(self):
        # git C-quotes these without -z; with -z they arrive verbatim
        for name in ('t"q.md', "back\\slash.md", "tab\there.md", "new\nline.md"):
            p = f"sim/x/records/{name}"
            v, _ = ao.find_violations(f"D\0{p}\0", {})
            self.assertEqual(v, [("D", p)], name)

    def test_special_char_rename_old_path(self):
        old, new = "sim/x/corners/a\tb\n.log", "sim/x/corners/c.log"
        v, _ = ao.find_violations(f"R100\0{old}\0{new}\0M\0sim/x/records/\"q\0", {})
        self.assertEqual(v, [("R100", old), ("M", 'sim/x/records/"q')])

    def test_copy_consumes_two_paths(self):
        # C record must consume both paths so the next record parses correctly
        v, _ = ao.find_violations(f"C075\0{R}\0sim/x/records/c.md\0D\0{C}\0", {})
        self.assertEqual(v, [("D", C)])

    def test_malformed_input_fails_closed(self):
        for bad in (f"R100\0{R}\0", "M\0", f"\0{R}\0", f"M\t{R}\n"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                ao.find_violations(bad, {})

    def test_main_stdin_exit_codes(self):
        import io, contextlib
        from unittest import mock
        for text, rc in ((z(f"A\t{R}\n"), 0), (z(f"M\t{R}\n"), 1),
                         (f'D\0sim/x/records/t"q.md\0', 1)):
            with mock.patch("sys.stdin", io.StringIO(text)), \
                 contextlib.redirect_stdout(io.StringIO()), \
                 contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(ao.main(["--stdin", "--allowlist", "/nonexistent"]), rc)


class LocalModeGitTests(unittest.TestCase):
    """Real temp git repos: committed base..HEAD plus index/worktree vs HEAD."""

    EV = "sim/blk/records/r.md"
    EV2 = "sim/blk/corners/c.log"

    def setUp(self):
        import os, subprocess, tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = Path(self._tmp.name)
        self._cwd = os.getcwd()
        self.addCleanup(os.chdir, self._cwd)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")
        self.git("config", "commit.gpgsign", "false")
        self.write(self.EV, "evidence\n")
        self.write(self.EV2, "corner data\n")
        self.write("sim/blk/README.md", "prose\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "base")
        self.git("update-ref", "refs/remotes/origin/main", "HEAD")
        os.chdir(self.repo)

    def git(self, *a):
        import subprocess
        subprocess.run(["git", *a], cwd=self.repo, check=True, capture_output=True)

    def write(self, rel, text):
        p = self.repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def run_main(self, *extra, local=True):
        import io, contextlib
        argv = ["--base", "origin/main", "--allowlist", "sim/append-only-allowlist.txt"]
        argv += (["--local"] if local else []) + list(extra)
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            rc = ao.main(argv)
        return rc, err.getvalue()

    def test_clean_passes(self):
        self.assertEqual(self.run_main()[0], 0)

    def test_unstaged_edit_fails_local_only(self):
        self.write(self.EV, "changed\n")
        rc, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn(self.EV, err)
        self.assertEqual(self.run_main(local=False)[0], 0)

    def test_staged_edit_fails(self):
        self.write(self.EV, "changed\n")
        self.git("add", self.EV)
        self.assertEqual(self.run_main()[0], 1)

    def test_unstaged_and_staged_deletion_fail(self):
        (self.repo / self.EV).unlink()
        self.assertEqual(self.run_main()[0], 1)
        self.git("add", "-A")
        self.assertEqual(self.run_main()[0], 1)

    def test_staged_rename_fails(self):
        self.git("mv", self.EV, "sim/blk/records/renamed.md")
        rc, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn(self.EV, err)

    def test_unstaged_rename_fails(self):
        (self.repo / self.EV).rename(self.repo / "sim/blk/records/renamed.md")
        self.assertEqual(self.run_main()[0], 1)

    def test_staged_change_then_unstaged_restoration_still_fails(self):
        self.write(self.EV, "changed\n")
        self.git("add", self.EV)
        self.write(self.EV, "evidence\n")  # worktree now equals HEAD
        rc, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn(self.EV, err)

    def test_staged_deletion_then_restored_in_worktree_fails(self):
        self.git("rm", "-q", "--cached", self.EV)
        self.assertEqual(self.run_main()[0], 1)

    def test_additions_and_prose_pass(self):
        self.write("sim/blk/records/new.md", "new\n")  # untracked
        self.write("sim/blk/corners/new.log", "new\n")
        self.git("add", "sim/blk/corners/new.log")  # staged add
        self.write("sim/blk/README.md", "edited prose\n")
        self.assertEqual(self.run_main()[0], 0)

    def test_allowlisted_path_keeps_behaviour(self):
        self.write("sim/append-only-allowlist.txt", f"{self.EV} | #99\n")
        self.write(self.EV, "changed\n")
        self.assertEqual(self.run_main()[0], 0)
        self.write(self.EV2, "changed\n")  # not allowlisted
        self.assertEqual(self.run_main()[0], 1)

    def test_committed_violation_caught_in_both_modes(self):
        self.write(self.EV, "changed\n")
        self.git("commit", "-qam", "edit evidence")
        self.assertEqual(self.run_main()[0], 1)
        self.assertEqual(self.run_main(local=False)[0], 1)

    def test_pr_mode_ignores_uncommitted(self):
        self.write(self.EV, "changed\n")
        self.git("add", self.EV)
        self.assertEqual(self.run_main(local=False)[0], 0)

    def test_stdin_and_local_exclusive(self):
        with self.assertRaises(SystemExit):
            self.run_main("--stdin")


if __name__ == "__main__":
    unittest.main()
