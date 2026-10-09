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


class KltSimTests(unittest.TestCase):
    """The shared `klt sim` client, with subprocess.run stubbed (no klt needed)."""

    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.tmp = Path(d.name)
        self.req = self.tmp / "bench.request.json"
        self.req.write_text("{}")
        saved = list(sh.KLT_CMD)
        self.addCleanup(lambda: sh.KLT_CMD.__setitem__(slice(None), saved))

    def _run(self, stdout, stderr="warn: skew\n", rc=0, outdir=None, backend=None):
        proc = mock.Mock(stdout=stdout, stderr=stderr, returncode=rc)
        with mock.patch.object(sh.subprocess, "run", return_value=proc) as run:
            cwd = os.getcwd()
            os.chdir(self.tmp)  # so a relative outdir resolves under tmp
            try:
                result = sh.klt_sim(self.req, outdir or Path("out"), backend)
            finally:
                os.chdir(cwd)
        return result, run.call_args.args[0]

    def test_command_absolute_outdir_and_stderr_file(self):
        sh.KLT_CMD[:] = ["uvx", "--from", "klayout-tools==0.5.0", "klt"]  # as pvt_sweep --klt-cmd does
        res, cmd = self._run('{"status": "pass", "corners": []}', rc=1, backend="batch")
        out = (self.tmp / "out").resolve()
        self.assertEqual(cmd, ["uvx", "--from", "klayout-tools==0.5.0", "klt", "sim", str(self.req),
                               "-o", str(out), "--backend", "batch", "--format", "json"])
        self.assertTrue(Path(cmd[cmd.index("-o") + 1]).is_absolute())
        self.assertEqual((out / "bench.request.stderr.txt").read_text(), "warn: skew\n")
        self.assertEqual(res.payload, {"status": "pass", "corners": []})
        self.assertEqual((res.returncode, res.stderr), (1, "warn: skew\n"))
        cmd_, rc, payload, err = res  # offset_probe's (cmd, rc, payload, stderr) shape
        self.assertEqual(cmd_, cmd)

    def test_no_backend_flag_when_unset(self):
        sh.KLT_CMD[:] = ["klt"]
        _res, cmd = self._run("{}")
        self.assertNotIn("--backend", cmd)
        self.assertEqual(cmd[-2:], ["--format", "json"])

    def test_non_json_stdout_raises_typed_error_with_invocation(self):
        sh.KLT_CMD[:] = ["klt"]
        with self.assertRaises(sh.KltSimError) as cm:
            self._run("Traceback ...", stderr="boom: BATCH_MAX_CONCURRENT_INSTANCES", rc=2)
        exc = cm.exception
        self.assertIsInstance(exc, sh.HarnessError)  # pvt_sweep's retry loop catches HarnessError
        self.assertEqual((exc.returncode, exc.stderr), (2, "boom: BATCH_MAX_CONCURRENT_INSTANCES"))
        self.assertIn("BATCH_MAX_CONCURRENT_INSTANCES", str(exc))
        self.assertEqual(exc.cmd[:2], ["klt", "sim"])

    def test_run_klt_sim_returns_report_dict(self):
        proc = mock.Mock(stdout='{"status": "fail"}', stderr="", returncode=1)
        with mock.patch.object(sh.subprocess, "run", return_value=proc):
            self.assertEqual(sh.run_klt_sim(self.req, self.tmp / "o", "local"), {"status": "fail"})

    def test_klt_version_goes_through_klt_cmd(self):
        sh.KLT_CMD[:] = ["uvx", "--from", "klayout-tools==0.5.0", "klt"]
        with mock.patch.object(sh, "first_line", return_value="klt 0.5.0") as fl:
            self.assertEqual(sh.klt_version(), "klt 0.5.0")
        fl.assert_called_once_with(["uvx", "--from", "klayout-tools==0.5.0", "klt", "--version"])


if __name__ == "__main__":
    unittest.main()
