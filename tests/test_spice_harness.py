import json
import os
import subprocess
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

    def test_non_object_json_root_raises_typed_error_with_invocation(self):
        sh.KLT_CMD[:] = ["klt"]
        for stdout, tname in (("[]", "list"), ("null", "NoneType"), ("42", "int"),
                              ("true", "bool"), ('"str"', "str")):
            with self.subTest(stdout=stdout):
                with self.assertRaises(sh.KltSimError) as cm:
                    self._run(stdout, stderr="warn: odd\n", rc=3)
                exc = cm.exception
                self.assertIsInstance(exc, sh.HarnessError)
                self.assertEqual((exc.returncode, exc.stderr), (3, "warn: odd\n"))
                self.assertEqual(exc.cmd[:2], ["klt", "sim"])
                self.assertIn(tname, str(exc))
                self.assertIn("exit 3", str(exc))
                self.assertEqual((self.tmp / "out" / "bench.request.stderr.txt").read_text(),
                                 "warn: odd\n")

    def test_non_object_root_rejected_through_run_klt_sim(self):
        proc = mock.Mock(stdout="[]", stderr="", returncode=0)
        with mock.patch.object(sh.subprocess, "run", return_value=proc):
            with self.assertRaises(sh.KltSimError):
                sh.run_klt_sim(self.req, self.tmp / "o")

    def test_dict_reports_accepted_even_on_nonzero_exit(self):
        sh.KLT_CMD[:] = ["klt"]
        res, _cmd = self._run("{}", rc=2)
        self.assertEqual((res.payload, res.returncode), ({}, 2))
        res, _cmd = self._run('{"status": "fail"}', rc=1)
        self.assertEqual(res.payload, {"status": "fail"})

    def test_run_klt_sim_returns_report_dict(self):
        proc = mock.Mock(stdout='{"status": "fail"}', stderr="", returncode=1)
        with mock.patch.object(sh.subprocess, "run", return_value=proc):
            self.assertEqual(sh.run_klt_sim(self.req, self.tmp / "o", "local"), {"status": "fail"})

    def test_klt_version_goes_through_klt_cmd(self):
        sh.KLT_CMD[:] = ["uvx", "--from", "klayout-tools==0.5.0", "klt"]
        with mock.patch.object(sh, "first_line", return_value="klt 0.5.0") as fl:
            self.assertEqual(sh.klt_version(), "klt 0.5.0")
        fl.assert_called_once_with(["uvx", "--from", "klayout-tools==0.5.0", "klt", "--version"])


# --------------------------------------------------------------------------
# batch.capacity_wait_s across the request builders (issue #293)
# --------------------------------------------------------------------------

class _FakeRequestPdk:
    """Stands in for the runners' Pdk/OpampPdk: only what request building touches."""

    variant = "sky130A"

    def corner_include(self, corner):
        return Path(f"/pdk/corners/{corner}.spice")

    def rc_includes(self):
        return [Path("/pdk/rc/base.spice"), Path("/pdk/rc/lin.spice")]


_RUNNERS = {}


def _runner(rel):
    """Load a runner module by repo-relative path (cached; scripts, not a package)."""
    if rel not in _RUNNERS:
        _RUNNERS[rel] = _paths.load_module(rel.replace("/", "_"), _paths.REPO / rel)
    return _RUNNERS[rel]


def _pvt_batch_request():
    pvt = _runner("sim/opamp-characterization/bin/pvt_sweep.py")
    with tempfile.TemporaryDirectory() as d:
        path, _tag = pvt.build_klt_request("ac", None, None, _FakeRequestPdk(), ["tt"], [27.0],
                                           Path(d), "batch")
        return json.loads(path.read_text())


def _psrr_batch_request(backend):
    psrr = _runner("sim/opamp-characterization/bin/psrr_noise_sweep.py")
    return psrr.build_request("noise", ["tt"], [27.0], "bench.spice", True,
                              backend=backend)


def _offset_probe_batch_request():
    op = _runner("sim/offset-capability/bin/offset_probe.py")
    return op.build_request("offset", True, None)


def _sink_bias_request(backend):
    """`variants/sink_bias_margin.py` with a stubbed `pvt.resolve_pdk` (the only
    thing request building touches that needs an installed PDK)."""
    sbm = _runner("sim/opamp-characterization/variants/sink_bias_margin.py")
    pvt = _runner("sim/opamp-characterization/bin/pvt_sweep.py")
    real = pvt.resolve_pdk
    pvt.resolve_pdk = lambda: _FakeRequestPdk()
    try:
        with tempfile.TemporaryDirectory() as d:
            path = sbm.build_static_request(pvt, Path(d), "static", backend)
            return json.loads(path.read_text())
    finally:
        pvt.resolve_pdk = real


def _git_grep(pattern, pathspec):
    """(path, line) pairs from `git grep -nE` over the checkout this test runs in."""
    proc = subprocess.run(["git", "-C", str(_paths.REPO), "grep", "-nE", "-e", pattern, "--", pathspec],
                          capture_output=True, text=True)
    if proc.returncode == 1:
        return []  # no matches
    if proc.returncode != 0:
        raise AssertionError(f"git grep failed ({proc.returncode}): {proc.stderr.strip()}")
    return [(m[0], int(m[1])) for m in
            (line.split(":", 2) for line in proc.stdout.splitlines())]


def _batch_emit_sites():
    """Source paths that build a request's `batch` block -- both the
    `req["batch"] = {...}` assignment shape and the `"batch": {...}` literal
    shape -- derived from the sources, not hand-kept. Python sources under
    `sim/` only; `sim/lib` is excluded: it owns the klt client, not request
    builders. A request builder outside `sim/` would be a new convention; the
    enumeration test below fails until this function grows with it."""
    return {path for path, _line in _git_grep(r'\["batch"\] *=|"batch": *\{', "*.py")
            if path.startswith("sim/") and not path.startswith("sim/lib/")}


class BatchCapacityWaitTests(unittest.TestCase):
    """Every `klt sim` request builder that emits a `batch` block must carry
    `capacity_wait_s == spice_harness.BATCH_CAPACITY_WAIT_S` (issue #293).

    The worker host rule requires `--wait-for-capacity 600` (or the request's
    `batch.capacity_wait_s`) on every batch `klt sim`: the Spot fleet is
    vCPU-budgeted, so a burst of submits is refused with `batch_no_capacity`
    (2am#6872). The builder set is derived from the sources with `git grep`,
    so a request builder added later without the wait fails here instead of
    submitting bare to the fleet. Simulator-free: PDK resolution is stubbed,
    no ngspice, no klt.
    """

    BUILDERS = {
        "sim/opamp-characterization/bin/pvt_sweep.py": _pvt_batch_request,
        "sim/opamp-characterization/bin/psrr_noise_sweep.py":
            lambda: _psrr_batch_request("batch"),
        "sim/offset-capability/bin/offset_probe.py": _offset_probe_batch_request,
        "sim/opamp-characterization/variants/sink_bias_margin.py":
            lambda: _sink_bias_request("batch"),
    }

    def test_builder_enumeration_matches_the_sources(self):
        """Registered builders == the batch-block emitters git grep finds.

        A NEW builder (grep finds it, registry doesn't) fails here -- register
        it and emit the wait in its `batch` block. A builder that stopped
        emitting `batch` (registry has it, grep doesn't) fails too, since that
        changes what reaches the fleet."""
        self.assertEqual(
            _batch_emit_sites(), set(self.BUILDERS),
            "batch-block emitters and the registered request builders disagree; "
            "for a new builder, register it in BatchCapacityWaitTests.BUILDERS "
            "and emit \"capacity_wait_s\": BATCH_CAPACITY_WAIT_S in its `batch` "
            "block (worker host rule 2am#6872, spice_harness.BATCH_CAPACITY_WAIT_S)")

    def test_every_builder_emits_the_shared_wait(self):
        for path, build in sorted(self.BUILDERS.items()):
            with self.subTest(builder=path):
                req = build()
                batch = req.get("batch")
                self.assertIsInstance(batch, dict, path)
                self.assertEqual(batch.get("capacity_wait_s"), sh.BATCH_CAPACITY_WAIT_S, path)

    def test_wait_value_has_a_single_owner(self):
        """`BATCH_CAPACITY_WAIT_S = <literal>` definitions across the repo: the
        shared owner in sim/lib/spice_harness.py, plus pvt_sweep.py's
        grandfathered copy -- migrating that literal is PR #297's, which owns
        pvt_sweep.py; drop it from this set once that lands."""
        owners = {path for path, _line in _git_grep(r"BATCH_CAPACITY_WAIT_S\s*=\s*[0-9]", "*.py")}
        self.assertEqual(owners, {"sim/lib/spice_harness.py",
                                  "sim/opamp-characterization/bin/pvt_sweep.py"})

    def test_sink_bias_margin_local_backend_has_no_batch_block(self):
        """Edge (issue #293): `--backend local` must not grow a `batch` block it
        never had -- the wait goes inside the existing `backend == "batch"`
        branch, not above it."""
        self.assertNotIn("batch", _sink_bias_request("local"))

    def test_psrr_noise_sweep_local_backend_has_no_batch_block(self):
        """Edge (issue #315): same convention for the psrr runner -- the `batch`
        block is gated on the backend, never on `--runner-version-check`, so a
        local debug probe still gets no block."""
        self.assertNotIn("batch", _psrr_batch_request("local"))


if __name__ == "__main__":
    unittest.main()
