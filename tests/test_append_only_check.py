import unittest

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


if __name__ == "__main__":
    unittest.main()
