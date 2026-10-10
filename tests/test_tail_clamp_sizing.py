"""Simulator-free tests for sim/opamp-characterization/variants/tail_clamp_sizing.py.

Issue #164: the sizing script is the input for the committed tail-clamp
candidate netlists; guard its interpolation helpers and check that the MCL
unit width it computes still matches the width in each committed netlist.
"""

import math
import re
import tempfile
import unittest
from pathlib import Path

from _paths import EXP, load_module

VAR = EXP / "variants"
ts = load_module("tail_clamp_sizing", VAR / "tail_clamp_sizing.py")

HEADER = ("device,corner,length_um,width_um,temp_c,vds_v,overdrive_bias_v,"
          "vov_v,id_a,gm_s,gds_s,cgg_f,vth_v,gm_id_per_v,gm_gds,ft_hz\n")


def row(dev, corner, length, temp, vgs, idv):
    return f"{dev},{corner},{length},2.0,{temp},0.9,{vgs},0,{idv},0,0,0,0,0,0,0\n"


def series(pairs):
    return [(v, i, {}) for v, i in pairs]


# Exactly log-linear: Id = 1e-7 * exp(ln(10) * (v - 0.4) / 0.1) -> decade per 0.1 V
SYN = series([(0.4, 1e-7), (0.5, 1e-6), (0.6, 1e-5)])


def mcl_unit_width_um(rows, vclamp, m):
    """Replicates main() step 1-2 using the module's own helpers/constants."""
    tt = rows[("tt", 27.0)]
    j0 = ts.I_UNIT_A / ts.W_MIRROR_UM * 1e6
    vgs_b, _, _ = ts.vgs_at_density(tt, j0)
    j_cl = ts.density_at_vgs(tt, vgs_b - vclamp)
    w_tot = ts.I_CLAMP_A / (j_cl * 1e-6)
    return ts.snap(w_tot / m)


def netlist_mcl_width(path):
    for line in path.read_text().splitlines():
        if line.startswith("XMCL "):
            return float(re.search(r"\bW=([0-9.]+)", line).group(1))
    raise AssertionError(f"no XMCL line in {path}")


class InterpolationTests(unittest.TestCase):
    def test_round_trip(self):
        for vgs in (0.42, 0.5, 0.55, 0.59):
            j = ts.density_at_vgs(SYN, vgs)
            back, _, _ = ts.vgs_at_density(SYN, j)
            self.assertAlmostEqual(back, vgs, places=9)

    def test_known_value(self):
        # Midpoint of a decade: 3.1623e-7 A per 2 um.
        j = math.sqrt(1e-7 * 1e-6) / ts.SWEEP_W_UM * 1e6
        v, _, _ = ts.vgs_at_density(SYN, j)
        self.assertAlmostEqual(v, 0.45, places=9)

    def test_out_of_sweep(self):
        with self.assertRaises(ValueError):
            ts.vgs_at_density(SYN, 1e-6)  # below range
        with self.assertRaises(ValueError):
            ts.vgs_at_density(SYN, 1e3)  # above range
        with self.assertRaises(ValueError):
            ts.density_at_vgs(SYN, 0.3)
        with self.assertRaises(ValueError):
            ts.density_at_vgs(SYN, 0.7)

    def test_snap_grid(self):
        for w in (7.819, 15.4937, 10.3702, 0.001, 123.9512):
            s = ts.snap(w)
            self.assertLess(abs(s / ts.GRID_UM - round(s / ts.GRID_UM)), 1e-9)
            self.assertLessEqual(abs(s - w), ts.GRID_UM / 2 + 1e-12)
        self.assertAlmostEqual(ts.snap(7.819), 7.820)


class LoadTests(unittest.TestCase):
    def test_filters_and_sorts(self):
        text = HEADER + "".join([
            row("nfet", "tt", 1.2, 27.0, 0.6, 1e-6),
            row("nfet", "tt", 1.2, 27.0, 0.2, 1e-9),
            row("pfet", "tt", 1.2, 27.0, 0.4, 5e-6),   # wrong device
            row("nfet", "tt", 0.5, 27.0, 0.4, 5e-6),   # other length
            row("nfet", "tt", 1.2, 27.0, 0.0, 0.0),    # id <= 0
            row("nfet", "tt", 1.2, 27.0, 0.1, -1e-12),  # id <= 0
            row("nfet", "ss", 1.2, -40.0, 0.4, 1e-7),
        ])
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.csv"
            p.write_text(text)
            old = ts.FULL
            ts.FULL = str(p)
            try:
                rows = ts.load()
            finally:
                ts.FULL = old
        self.assertEqual(set(rows), {("tt", 27.0), ("ss", -40.0)})
        self.assertEqual([v for v, _, _ in rows[("tt", 27.0)]], [0.2, 0.6])
        self.assertEqual(len(rows[("ss", -40.0)]), 1)


class CommittedNetlistTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = ts.load()

    def test_default_matches_tail_clamp_spice(self):
        w = mcl_unit_width_um(self.rows, ts.V_CLAMP_DESIGN, ts.MCL_M)
        self.assertAlmostEqual(w, netlist_mcl_width(VAR / "tail-clamp.spice"), places=6)

    def test_vc050_matches_tail_clamp_vc050_spice(self):
        w = mcl_unit_width_um(self.rows, 0.05, 4)
        self.assertAlmostEqual(w, netlist_mcl_width(VAR / "tail-clamp-vc050.spice"), places=6)


if __name__ == "__main__":
    unittest.main()
