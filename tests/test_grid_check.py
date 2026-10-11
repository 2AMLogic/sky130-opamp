import unittest

import _paths

gc = _paths.load_module("grid_check", _paths.REPO / "design" / "bin" / "grid_check.py")
NETLIST = _paths.REPO / "design" / "netlist" / "opamp_core.spice"
PRIOR_RZ = "XRz cz d2 vss sky130_fd_pr__res_high_po_1p41 L=9.763 mult=1 m=1\n"


class PassiveGridTests(unittest.TestCase):
    def test_committed_netlist_passives_on_grid(self):
        self.assertEqual(gc.violations(NETLIST.read_text(), ("passive",)), [])

    def test_prior_illegal_resistor_length_is_rejected(self):
        found = gc.violations(PRIOR_RZ, ("passive",))
        self.assertEqual(len(found), 1, found)
        self.assertIn("XRz", found[0])
        self.assertIn("L=9.763", found[0])

    def test_committed_resistor_is_not_the_prior_length(self):
        self.assertNotIn("L=9.763 ", NETLIST.read_text())

    def test_continuation_lines_and_both_dims_checked(self):
        text = "XCc cz out sky130_fd_pr__cap_mim_m3_1\n+ W=15.62 L=15.623 MF=1 m=1\n"
        found = gc.violations(text, ("passive",))
        self.assertEqual(len(found), 1, found)
        self.assertIn("L=15.623", found[0])

    def test_mos_class_is_default_and_opt_out(self):
        mos = "XM3 d1 d1 vdd vdd sky130_fd_pr__pfet_01v8 L=0.3 W=4.634 nf=1\n"
        self.assertEqual(gc.violations(mos, ("passive",)), [])
        self.assertEqual(len(gc.violations(mos, ("passive", "mos"))), 1)

    def test_committed_mos_widths_on_grid(self):
        self.assertEqual(gc.violations(NETLIST.read_text(), ("passive", "mos")), [])

    def test_prior_dr007_widths_are_rejected(self):
        for w in ("4.634", "7.819"):
            card = f"XM sky130_fd_pr__nfet_01v8 L=1.2 W={w} nf=1\n"
            self.assertEqual(len(gc.violations(card, ("mos",))), 1, w)
        self.assertNotIn("W=4.634", NETLIST.read_text())
        self.assertNotIn("W=7.819", NETLIST.read_text())

    def test_default_cli_checks_mos(self):
        import tempfile, pathlib
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d) / "n.spice"
            f.write_text("XM3 a b c d sky130_fd_pr__pfet_01v8 L=0.3 W=4.634 nf=1\n")
            self.assertEqual(gc.main([str(f)]), 1)

    def test_group_widths_and_multiplicities_preserved(self):
        import re
        text = NETLIST.read_text().replace("\n+", "")
        def card(n):
            m = re.search(rf"^{n} .*$", text, re.M).group(0)
            return {k.lower(): v for k, v in (t.split("=") for t in m.split() if "=" in t)}
        for n in ("XM3", "XM4", "XM6"):
            self.assertEqual(float(card(n)["w"]), 4.635, n)
        for n in ("XMB1", "XM5", "XM7"):
            self.assertEqual(float(card(n)["w"]), 7.82, n)
        self.assertEqual([int(card(n)["m"]) for n in ("XM3", "XM4", "XM6")], [1, 1, 10])
        self.assertEqual([int(card(n)["m"]) for n in ("XMB1", "XM5", "XM7")], [1, 2, 10])

    def test_per_finger_width_checked(self):
        bad = "XM sky130_fd_pr__nfet_01v8 L=1 W=4.64 nf=3\n"   # 1.54667 per finger
        ok = "XM sky130_fd_pr__nfet_01v8 L=1 W=4.65 nf=3\n"    # 1.55 per finger
        self.assertEqual(len(gc.violations(bad, ("mos",))), 1)
        self.assertEqual(gc.violations(ok, ("mos",)), [])

    def test_candidate_lengths_on_grid(self):
        for ok in (9.765, 9.76, 15.62):
            self.assertTrue(gc.on_grid(ok), ok)
        self.assertFalse(gc.on_grid(9.763))


class MalformedGeometryTests(unittest.TestCase):
    @staticmethod
    def mos(extra, name="XM"):
        return f"{name} d g s b sky130_fd_pr__nfet_01v8 L=1 W=4.65 {extra}\n"

    def test_invalid_explicit_nf_rejected_with_instance_name(self):
        for nf in ("0", "-1", "2.5", "abc", "nan", "inf", "-inf", ""):
            found = gc.violations(self.mos(f"nf={nf}", "XBAD"), ("mos",))
            self.assertTrue(found, nf)
            self.assertTrue(all("XBAD" in f for f in found), (nf, found))
            self.assertTrue(any("nf=" in f for f in found), (nf, found))

    def test_valid_nf_forms(self):
        for extra in ("", "nf=1", "nf=3", "nf=3.0"):
            self.assertEqual(gc.violations(self.mos(extra), ("mos",)), [], extra)

    def test_nf_2_0_still_checks_per_finger(self):
        bad = "XM d g s b sky130_fd_pr__nfet_01v8 L=1 W=4.635 nf=2.0\n"  # 2.3175/finger
        self.assertEqual(len(gc.violations(bad, ("mos",))), 1)

    def test_invalid_dimensions_rejected(self):
        for dim in ("L", "W"):
            for v in ("0", "-0.5", "nan", "inf", "-inf"):
                text = self.mos(f"{dim}={v}", "XD")
                found = gc.violations(text, ("mos",))
                self.assertTrue(found, (dim, v))
                self.assertTrue(all("XD" in f for f in found), found)

    def test_passive_dimensions_validated_too(self):
        found = gc.violations("XR a b sky130_fd_pr__res_high_po_1p41 L=nan\n", ("passive",))
        self.assertEqual(len(found), 1, found)

    def test_ordinary_off_grid_unchanged(self):
        found = gc.violations("XM d g s b sky130_fd_pr__nfet_01v8 L=1 W=4.634 nf=1\n", ("mos",))
        self.assertEqual(len(found), 1)
        self.assertIn("not a multiple", found[0])

    def test_multiple_invalid_instances_aggregate(self):
        text = (self.mos("nf=0", "XA") + self.mos("nf=1.5", "XB")
                + "XC d g s b sky130_fd_pr__pfet_01v8 L=0 W=4.65\n"
                + "XD d g s b sky130_fd_pr__pfet_01v8 L=1 W=nan\n" + self.mos("nf=2", "XOK"))
        found = gc.violations(text, ("passive", "mos"))
        for n in ("XA", "XB", "XC", "XD"):
            self.assertTrue(any(f.startswith(n) for f in found), (n, found))
        self.assertFalse(any(f.startswith("XOK") for f in found), found)

    def test_cli_fails_on_malformed_and_passes_canonical(self):
        import contextlib, io, pathlib, tempfile
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d) / "n.spice"
            f.write_text(self.mos("nf=0", "XA") + self.mos("nf=nan", "XB"))
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(gc.main([str(f)]), 1)
            self.assertIn("XA", err.getvalue())
            self.assertIn("XB", err.getvalue())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(gc.main([str(NETLIST)]), 0)


if __name__ == "__main__":
    unittest.main()
