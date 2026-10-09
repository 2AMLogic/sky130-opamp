"""Simulator-free tests for sim/offset-capability/bin/attribution.py (issue #107)."""
import unittest

import _paths
from _paths import REPO

at = _paths.load_module("attribution", REPO / "sim" / "offset-capability" / "bin" / "attribution.py")
CORE = at.CORE.read_text()


class Benches(unittest.TestCase):
    def test_committed_benches_equal_regenerated(self):
        for g in at.GROUPS:
            self.assertEqual(at.bench_path(g).read_text(), at.bench_text(g), g)

    def test_group_instances_exist_and_partition_the_core(self):
        inst = at.instances(CORE)
        listed = [i for g, (on, _n) in at.GROUPS.items() if g != "none" for i in on]
        self.assertEqual(sorted(listed), sorted(inst))      # every device in exactly one group

    def test_only_group_devices_keep_pdk_model(self):
        for g, (on, _n) in at.GROUPS.items():
            cards = {ln.split()[0]: ln for ln in at.logical_lines(at.gated_netlist(CORE, on))
                     if ln.startswith("X")}
            for name, ln in cards.items():
                wrapped = any(t.startswith("mmoff_") for t in ln.split())
                self.assertEqual(wrapped, name not in on, (g, name))

    def test_wrapped_cards_differ_from_core_only_in_model_token(self):
        orig = {ln.split()[0]: ln.split() for ln in at.logical_lines(CORE) if ln.startswith("X")}
        for ln in at.logical_lines(at.gated_netlist(CORE, ())):
            if ln.startswith("X"):
                t = ln.split()
                o = orig[t[0]]
                self.assertEqual(len(t), len(o))
                diff = [(a, b) for a, b in zip(o, t) if a != b]
                self.assertEqual(len(diff), 1)
                self.assertEqual(at.MODEL_WRAP[diff[0][0]], diff[0][1])

    def test_wrappers_pass_m_and_mult_and_zero_the_switch(self):
        lines = at.WRAPPERS.splitlines()
        self.assertEqual(lines.count(".param mc_mm_switch=0"), 4)
        inner = [ln for ln in lines if ln.startswith("XX")]
        self.assertEqual(len(inner), 4)
        for ln in inner:
            self.assertIn("m={m}", ln)
        for ln in inner[:2]:
            self.assertIn("mult={mult}", ln)

    def test_bench_keeps_offset_bench_sources(self):
        base = at.BASE_BENCH.read_text().split(".include")[1].split("\n", 1)[1]
        for g in at.GROUPS:
            self.assertTrue(at.bench_text(g).endswith(base))

    def test_unknown_instance_rejected(self):
        with self.assertRaises(SystemExit):
            at.gated_netlist(CORE, ("XNOPE",))


class Plan(unittest.TestCase):
    def test_seeds_match_campaign_scheme(self):
        p = at.plan(["pair", "passives"], 20261085)
        self.assertEqual([(x["group"], x["chunk"], x["seed"], x["n"], x["offset"]) for x in p],
                         [("pair", 0, 20261085, 100, 0), ("pair", 1, 20261086, 100, 100),
                          ("pair", 2, 20261087, 100, 200), ("passives", 0, 20261085, 100, 0)])

    def test_request_points_at_group_bench_and_mm_section(self):
        r = at.request_for("mirror", {"n": 100, "seed": 5})
        self.assertEqual(r["netlist"], "../bench/attribution/offset_dc_attr_mirror.cir")
        self.assertEqual(r["corners"]["process"], ["tt_mm"])
        self.assertEqual(r["monte_carlo"]["vary"], "mismatch")


if __name__ == "__main__":
    unittest.main()
