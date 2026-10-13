"""Simulator-free tests for the PSRR/noise runner's pure logic (issue #68).

Covers the frequency<->index map, the log-log noise-corner interpolation, the
`klt sim` request shape per bench and the klt payload -> CSV row folding.
No ngspice, PDK or klt is needed.
"""

import math
import unittest

import _paths
from _paths import EXP

m = _paths.load_module("psrr_noise_sweep_under_test", EXP / "bin" / "psrr_noise_sweep.py")


class FreqIndexTests(unittest.TestCase):
    def test_round_trip_over_whole_grid(self):
        for k in range(m.N_PTS):
            self.assertEqual(m.idx_of(m.freq_of(k)), k)

    def test_grid_endpoints(self):
        self.assertEqual(m.N_PTS, 201)
        self.assertAlmostEqual(m.freq_of(0), m.F0_HZ)
        self.assertAlmostEqual(m.freq_of(m.N_PTS - 1) / m.F1_HZ, 1.0)

    def test_decades_are_ppd_apart(self):
        self.assertEqual(m.idx_of(1e3), m.idx_of(1e2) + m.PPD)
        self.assertEqual(m.NOISE_HI_IDX - m.NOISE_LO_IDX, 4 * m.PPD)

    def test_off_grid_frequency_rejected(self):
        # 0.1 Hz * 10**(1/40) is half a grid step off any index.
        with self.assertRaises(AssertionError):
            m.idx_of(m.F0_HZ * 10 ** (0.5 / m.PPD))

    def test_out_of_range_frequency_not_range_checked(self):
        # On-grid but outside [F0, F1]: idx_of maps it to an index outside
        # [0, N_PTS) rather than raising. Recorded as current behaviour; the
        # callers only pass module constants inside the sweep.
        self.assertEqual(m.idx_of(m.F0_HZ / 10), -m.PPD)
        self.assertEqual(m.idx_of(m.F1_HZ * 10), m.N_PTS - 1 + m.PPD)

    def test_curve_indices_stay_inside_sweep(self):
        self.assertIn(m.N_PTS - 1, m.CURVE_IDX)
        self.assertNotIn(m.N_PTS - 1, m.PSRR_CURVE_IDX)
        self.assertTrue(all(0 <= k < m.N_PTS for k in m.CURVE_IDX))


class LogInterpCrossingTests(unittest.TestCase):
    def test_one_over_f_plus_white_analytic_crossing(self):
        # S^2 = W + K/f; en = sqrt(S^2). en^2 = 2 W at f = K/W.
        white, k = (10e-9) ** 2, (10e-9) ** 2 * 1e3  # corner at 1 kHz
        idx = m.CURVE_IDX
        freqs = [m.freq_of(i) for i in idx]
        en = [math.sqrt(white + k / f) for f in freqs]
        floor = min(en[i] for i, f in enumerate(freqs) if 1e5 <= f <= 1e7)
        self.assertAlmostEqual(floor, math.sqrt(white), delta=1e-3 * floor)
        got = m.log_interp_crossing(freqs, en, math.sqrt(2.0) * floor)
        # 4 pts/decade log-log chord: loose but well under a grid step (1.78x).
        self.assertAlmostEqual(math.log10(got), 3.0, delta=0.05)

    def test_exact_on_a_pure_power_law(self):
        # en = f**-0.5 is a straight line in log-log: interpolation is exact.
        freqs = [1.0, 10.0, 100.0]
        psd = [f ** -0.5 for f in freqs]
        level = 10 ** -0.75  # f = 10**1.5
        self.assertAlmostEqual(m.log_interp_crossing(freqs, psd, level), 10 ** 1.5, places=9)

    def test_crossing_absent_returns_none(self):
        freqs = [1.0, 10.0, 100.0]
        self.assertIsNone(m.log_interp_crossing(freqs, [5.0, 4.0, 3.0], 1.0))  # always above
        self.assertIsNone(m.log_interp_crossing(freqs, [5.0, 4.0, 3.0], 9.0))  # always below
        self.assertIsNone(m.log_interp_crossing(freqs, [1.0, 2.0, 3.0], 1.5))  # rising only
        self.assertIsNone(m.log_interp_crossing([1.0], [1.0], 0.5))            # too short

    def test_flat_psd_returns_none(self):
        self.assertIsNone(m.log_interp_crossing([1.0, 10.0, 100.0], [2.0, 2.0, 2.0], 2.0))

    def test_non_monotonic_returns_first_falling_crossing(self):
        # falls through 2 between f=10 and 100, rises, falls again 1e3..1e4
        freqs = [1.0, 10.0, 100.0, 1e3, 1e4]
        psd = [4.0, 3.0, 1.0, 3.0, 1.0]
        got = m.log_interp_crossing(freqs, psd, 2.0)
        self.assertGreater(got, 10.0)
        self.assertLess(got, 100.0)

    def test_level_equal_to_sample_counts_when_next_is_lower(self):
        self.assertAlmostEqual(m.log_interp_crossing([1.0, 10.0], [2.0, 1.0], 2.0), 1.0)


class MeasurementsTests(unittest.TestCase):
    def test_psrr_measurements_are_meas_cards(self):
        for bench in ("psrr_vdd", "psrr_vss"):
            ms = m.measurements(bench)
            names = [x["name"] for x in ms]
            self.assertEqual(names, [f"avs_k{k:03d}" for k in m.PSRR_CURVE_IDX] + ["avs_win_max"])
            self.assertEqual(len(set(names)), len(names))
            for x in ms:
                self.assertTrue(x["spice"].startswith(".meas ac "))
                self.assertNotIn("expr", x)
                self.assertEqual(x["unit"], "dB")

    def test_psrr_probe_frequencies_inside_sweep(self):
        for x in m.measurements("psrr_vdd")[:-1]:
            f = float(x["spice"].rsplit("at=", 1)[1])
            self.assertGreaterEqual(f, m.F0_HZ * (1 - 1e-9))
            self.assertLess(f, m.F1_HZ)

    def test_noise_measurements_use_expr(self):
        ms = m.measurements("noise")
        self.assertEqual([x["name"] for x in ms],
                         [f"en_k{k:03d}" for k in m.CURVE_IDX] + ["vn_int_band"])
        for x in ms[:-1]:
            self.assertTrue(x["expr"].startswith("noise1.inoise_spectrum["))
        integ = ms[-1]
        self.assertEqual(integ["unit"], "V")
        self.assertIn(f"[{m.NOISE_LO_IDX},{m.NOISE_HI_IDX}]", integ["expr"])


class BuildRequestTests(unittest.TestCase):
    CORNERS = list(m.DEFAULT_CORNERS)
    TEMPS = list(m.DEFAULT_TEMPS_C)

    def req(self, bench, corners=None, temps=None, **kw):
        return m.build_request(bench, corners or self.CORNERS, temps or self.TEMPS,
                               "body.spice", keep_artifacts=True, **kw)

    def test_one_matrix_request_per_bench_no_loop(self):
        for bench in m.BENCHES:
            r = self.req(bench)
            self.assertEqual(r["corners"]["process"], self.CORNERS)
            self.assertEqual(r["corners"]["temperature_c"], self.TEMPS)
            self.assertIsInstance(r["analysis"], dict)  # a single analysis, not a list
            self.assertNotIn("loop", " ".join(str(v) for v in r["analysis"].values()).lower())
            self.assertEqual(r["netlist"], "body.spice")

    def test_literal_vdd_pairing_excludes_cross_products(self):
        r = self.req("psrr_vdd")
        self.assertEqual(r["corners"]["supply_v"]["vdd"], [1.62, 1.8, 1.98])
        keep = set()
        for c in self.CORNERS:
            for v in r["corners"]["supply_v"]["vdd"]:
                if {"process": c, "supply_v": {"vdd": v}} not in r["exclude"]:
                    keep.add((c, v))
        self.assertEqual(keep, {(c, m.VDD_BY_CORNER[c]) for c in self.CORNERS})
        self.assertEqual(len(keep) * len(self.TEMPS), 15)
        for v in r["corners"]["supply_v"]["vdd"]:
            self.assertIsInstance(v, float)  # literal numbers, never a template string

    def test_single_corner_has_single_supply_and_no_exclude(self):
        r = self.req("noise", corners=["ss"], temps=[125.0])
        self.assertEqual(r["corners"]["supply_v"]["vdd"], [1.62])
        self.assertEqual(r["exclude"], [])

    def test_ac_benches(self):
        for bench in ("psrr_vdd", "psrr_vss"):
            r = self.req(bench)
            self.assertEqual(r["analysis"]["kind"], "ac")
            self.assertEqual(r["analysis"]["args"], f"dec {m.PPD} 0.1 1e+09")
            self.assertEqual([x["name"] for x in r["measurements"]],
                             [x["name"] for x in m.measurements(bench)])
            self.assertNotIn("ngspice_init", r["options"])

    def test_noise_bench(self):
        r = self.req("noise")
        self.assertEqual(r["analysis"]["kind"], "noise")
        self.assertTrue(r["analysis"]["args"].startswith("v(out) Vinp dec "))
        self.assertEqual(r["options"]["ngspice_init"], ["set numdgt=8"])
        self.assertIn("vn_int_band", [x["name"] for x in r["measurements"]])

    def test_options_and_version_check(self):
        r = self.req("noise")
        self.assertTrue(r["options"]["keep_artifacts"])
        self.assertNotIn("batch", r)
        r = self.req("noise", runner_version_check="enforce")
        self.assertEqual(r["batch"], {"runner_version_check": "enforce"})

    def test_unknown_bench_and_corner_raise(self):
        with self.assertRaises(KeyError):
            self.req("bogus")
        with self.assertRaises(KeyError):
            self.req("noise", corners=["xx"])


def meas(**kv):
    return [{"name": k, "value": v} for k, v in kv.items()]


def corner(proc, temp, vdd, status, measurements):
    return {"process": proc, "temperature_c": temp, "supply_v": {"vdd": vdd},
            "status": status, "measurements": measurements, "diagnostics": []}


class CornerRowsTests(unittest.TestCase):
    def psrr_meas(self, offset=0.0):
        d = {f"avs_k{k:03d}": -60.0 - offset - k * 0.1 for k in m.PSRR_CURVE_IDX}
        d["avs_win_max"] = -55.0 - offset
        return meas(**d)

    def test_psrr_rows_negate_gain_and_keep_failed_corner(self):
        payload = {"corners": [
            corner("tt", 27.0, 1.8, "pass", self.psrr_meas()),
            corner("ss", 125.0, 1.62, "error", []),  # runner produced nothing
        ]}
        rows, fields = m.corner_rows("psrr_vdd", payload)
        self.assertEqual(len(rows), 2)  # failed corner is not dropped
        ok, bad = rows
        self.assertEqual(ok["status"], "pass")
        self.assertEqual(ok["psrr_dc_0p1hz_db"], 60.0)
        self.assertAlmostEqual(ok["psrr_1khz_db"], 60.0 + m.PSRR_WIN_HI_IDX * 0.1)
        self.assertEqual(ok["psrr_window_min_db"], 55.0)
        self.assertEqual((bad["corner"], bad["temp_c"], bad["vdd_v"]), ("ss", 125.0, 1.62))
        self.assertEqual(bad["status"], "error")
        for f in fields:
            if f.startswith("psrr_"):
                self.assertIsNone(bad[f], f)
        self.assertEqual(list(ok), fields)
        self.assertEqual(list(bad), fields)

    def test_psrr_partial_measurements_become_none_not_zero(self):
        ms = [x for x in self.psrr_meas() if x["name"] != "avs_win_max"]
        rows, _ = m.corner_rows("psrr_vss", {"corners": [corner("tt", 27.0, 1.8, "fail", ms)]})
        self.assertIsNone(rows[0]["psrr_window_min_db"])
        self.assertEqual(rows[0]["psrr_dc_0p1hz_db"], 60.0)
        self.assertEqual(rows[0]["status"], "fail")

    def noise_meas(self, drop=None):
        white, k = (10e-9) ** 2, (10e-9) ** 2 * 1e3
        d = {f"en_k{i:03d}": math.sqrt(white + k / m.freq_of(i)) for i in m.CURVE_IDX}
        d["vn_int_band"] = 2e-6
        if drop:
            d.pop(drop)
        return meas(**d)

    def test_noise_rows_floor_corner_and_units(self):
        rows, fields = m.corner_rows("noise", {"corners": [
            corner("tt", 27.0, 1.8, "pass", self.noise_meas())]})
        r = rows[0]
        self.assertAlmostEqual(r["vn_int_100hz_1mhz_uvrms"], 2.0)
        self.assertAlmostEqual(r["en_floor_nv_rthz"], 10.0, delta=0.05)
        self.assertAlmostEqual(math.log10(r["f_1overf_corner_hz"]), 3.0, delta=0.05)
        self.assertIn("en_nv_rthz@0.1Hz", fields)

    def test_noise_failed_corner_reported_with_none_fields(self):
        payload = {"corners": [
            corner("tt", 27.0, 1.8, "pass", self.noise_meas()),
            corner("ff", -40.0, 1.98, "error", []),
        ]}
        rows, _ = m.corner_rows("noise", payload)
        self.assertEqual([r["status"] for r in rows], ["pass", "error"])
        bad = rows[1]
        for f in ("vn_int_100hz_1mhz_uvrms", "en_floor_nv_rthz", "f_1overf_corner_hz"):
            self.assertIsNone(bad[f])

    def test_noise_missing_spot_point_suppresses_floor_and_corner(self):
        # a missing point inside the floor window must not yield a bogus min
        k = next(i for i in m.CURVE_IDX if m.FLOOR_LO_IDX <= i <= m.FLOOR_HI_IDX)
        rows, _ = m.corner_rows("noise", {"corners": [
            corner("tt", 27.0, 1.8, "pass", self.noise_meas(drop=f"en_k{k:03d}"))]})
        self.assertIsNone(rows[0]["en_floor_nv_rthz"])
        self.assertIsNone(rows[0]["f_1overf_corner_hz"])

    def test_empty_payload(self):
        self.assertEqual(m.corner_rows("noise", {"corners": []}), ([], []))


if __name__ == "__main__":
    unittest.main()
