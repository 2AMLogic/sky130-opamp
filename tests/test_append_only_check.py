import unittest

import _paths  # noqa: F401  -- sets sys.path for sim/lib
import append_only_check as ao

R = "sim/opamp-characterization/records/x.md"
C = "sim/gm-id-characterization/corners/tt.log"
N = "sim/opamp-characterization/netlist-snapshots/a.cir"


def check(text, allow=None):
    return ao.find_violations(text, allow or {})


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
        ao.parse_allowlist(_paths.REPO.joinpath(ao.DEFAULT_ALLOWLIST).read_text())

    def test_main_stdin_exit_codes(self):
        import io, contextlib
        from unittest import mock
        for text, rc in ((f"A\t{R}\n", 0), (f"M\t{R}\n", 1)):
            with mock.patch("sys.stdin", io.StringIO(text)), \
                 contextlib.redirect_stdout(io.StringIO()), \
                 contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(ao.main(["--stdin", "--allowlist", "/nonexistent"]), rc)


if __name__ == "__main__":
    unittest.main()
