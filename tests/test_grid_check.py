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

    def test_mos_class_is_opt_in(self):
        mos = "XM3 d1 d1 vdd vdd sky130_fd_pr__pfet_01v8 L=0.3 W=4.634 nf=1\n"
        self.assertEqual(gc.violations(mos, ("passive",)), [])
        self.assertEqual(len(gc.violations(mos, ("passive", "mos"))), 1)

    def test_candidate_lengths_on_grid(self):
        for ok in (9.765, 9.76, 15.62):
            self.assertTrue(gc.on_grid(ok), ok)
        self.assertFalse(gc.on_grid(9.763))


if __name__ == "__main__":
    unittest.main()
