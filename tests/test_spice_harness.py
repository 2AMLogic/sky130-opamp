import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _paths  # noqa: F401  -- sets sys.path for spice_harness
import spice_harness as sh

PIN = {
    "variant": "sky130A",
    "open_pdks_commit": "abc123",
    "default_pdk_root": "~/.volare",
    "ngspice_corner_dir": "libs.tech/ngspice/corners",
    "install_command": "volare enable --pdk sky130 abc123",
}


class RenderTests(unittest.TestCase):
    def _tmpl(self, text):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        p = Path(d.name) / "t.spice.tmpl"
        p.write_text(text)
        return p

    def test_substitutes_every_occurrence_and_stringifies(self):
        p = self._tmpl("V1 a 0 {VDD}\nR1 a b {VDD}\n.temp {TEMP}\n")
        out = sh.render(p, {"VDD": 1.8, "TEMP": -40.0})
        self.assertEqual(out, "V1 a 0 1.8\nR1 a b 1.8\n.temp -40.0\n")

    def test_unsubstituted_placeholder_raises_and_names_it(self):
        p = self._tmpl("V1 a 0 {VDD}\nC1 a 0 {CL_F}\n")
        with self.assertRaises(sh.HarnessError) as cm:
            sh.render(p, {"VDD": 1.8})
        self.assertIn("CL_F", str(cm.exception))
        self.assertNotIn("VDD", str(cm.exception))

    def test_extra_subs_are_ignored(self):
        p = self._tmpl("{A}")
        self.assertEqual(sh.render(p, {"A": 1, "B": 2}), "1")

    def test_load_json_missing_file(self):
        with self.assertRaises(sh.HarnessError):
            sh.load_json(Path("/nonexistent/pdk.json"))


class PdkResolutionTests(unittest.TestCase):
    def _root(self, corners=("tt",)):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        root = Path(d.name)
        cdir = root / "sky130A" / PIN["ngspice_corner_dir"]
        cdir.mkdir(parents=True)
        for c in corners:
            (cdir / f"{c}.spice").write_text("* stub\n")
        return root

    def _pdk(self, root, **env):
        e = {"PDK_ROOT": str(root)}
        e.update(env)
        with mock.patch.dict(os.environ, e):
            os.environ.pop("PDK", None) if "PDK" not in env else None
            return sh.Pdk(PIN)

    def test_env_root_and_corner_include_path(self):
        root = self._root()
        pdk = self._pdk(root)
        self.assertEqual(pdk.root, root)
        self.assertEqual(pdk.variant, "sky130A")
        self.assertEqual(pdk.corner_include("ff"),
                         root / "sky130A" / "libs.tech/ngspice/corners/ff.spice")

    def test_pdk_env_overrides_variant(self):
        pdk = self._pdk(self._root(), PDK="sky130B")
        self.assertEqual(pdk.variant, "sky130B")

    def test_validate_ok_and_missing_corner(self):
        pdk = self._pdk(self._root(("tt", "ff")))
        pdk.validate(["tt", "ff"])
        with self.assertRaises(sh.HarnessError) as cm:
            pdk.validate(["tt", "ss"])
        self.assertIn("ss.spice", str(cm.exception))

    def test_validate_missing_pdk_mentions_install_command(self):
        with tempfile.TemporaryDirectory() as d:
            pdk = self._pdk(Path(d))
            with self.assertRaises(sh.HarnessError) as cm:
                pdk.validate(["tt"])
            self.assertIn(PIN["install_command"], str(cm.exception))

    def test_installed_commit_from_versions_path_and_pin_match(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            real = root / "volare" / "versions" / "abc123" / "sky130A"
            real.mkdir(parents=True)
            (root / "sky130A").symlink_to(real)
            pdk = self._pdk(root)
            self.assertEqual(pdk.installed_commit, "abc123")
            self.assertTrue(pdk.matches_pin)
            pdk.pin = dict(PIN, open_pdks_commit="other")
            self.assertFalse(pdk.matches_pin)

    def test_unknown_commit_when_not_under_versions(self):
        pdk = self._pdk(self._root())
        self.assertEqual(pdk.installed_commit, "unknown")
        self.assertFalse(pdk.matches_pin)


if __name__ == "__main__":
    unittest.main()
