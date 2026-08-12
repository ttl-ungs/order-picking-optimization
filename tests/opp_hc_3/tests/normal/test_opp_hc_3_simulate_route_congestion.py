import unittest

import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
)

from models.base.opp_location_graph import OPPLocationGraph
from models.utils.congestion import CongestionTracker, simulate_route_congestion


class TestSimulateRouteCongestion(unittest.TestCase):
    """
    Deterministic unit tests for simulate_route_congestion (shared by
    opp_hc_3, which prices an already-built, fixed route), independent of
    Hill Climbing's local-search randomness.
    """

    def _build_line_graph(self):
        """D -- L1 -- L2 -- F, all distance 1."""
        g = OPPLocationGraph(depot_node="D", final_node="F")
        g.add_vertex("D", "depot")
        g.add_vertex("L1", "picking")
        g.add_vertex("L2", "picking")
        g.add_vertex("F", "final")
        for i, j in [("D", "L1"), ("L1", "L2"), ("L2", "F")]:
            g.add_edge(i, j, 1.0)
            g.add_edge(j, i, 1.0)
        return g

    def test_no_wait_when_only_one_owner_traverses_the_route(self):
        g = self._build_line_graph()
        tracker = CongestionTracker()
        end_time, wait = simulate_route_congestion(
            g, ["D", "L1", "L2", "F"], "P1", 0.0, 1.0, {"L1": 2.0, "L2": 2.0}, tracker, "D", "F"
        )
        self.assertEqual(wait, 0.0)
        # 3 edges (1.0 each) + 2 node dwells (2.0 each) = 7.0
        self.assertAlmostEqual(end_time, 7.0)

    def test_second_route_waits_for_shared_node(self):
        g = self._build_line_graph()
        tracker = CongestionTracker()
        S = {"L1": 2.0, "L2": 2.0}

        # P1 occupies L2 during [2, 4) (starts at t=0, arrives at L1 at t=1,
        # dwells [1,3), arrives at L2 at t=4... let's just assert P2 is
        # forced to wait, not the exact numbers already covered by
        # CongestionTracker's own unit tests.
        simulate_route_congestion(g, ["D", "L1", "L2", "F"], "P1", 0.0, 1.0, S, tracker, "D", "F")

        _, wait_p2 = simulate_route_congestion(
            g, ["D", "L1", "L2", "F"], "P2", 0.0, 1.0, S, tracker, "D", "F"
        )
        self.assertGreater(wait_p2, 0.0)

    def test_depot_and_final_are_excluded_from_node_contention(self):
        g = self._build_line_graph()
        tracker = CongestionTracker()
        S = {"L1": 0.0, "L2": 0.0}

        # Two pickers both starting/ending at D/F at the same time must NOT
        # wait on the depot/final nodes themselves (only interior nodes and
        # edges are capacity-1 resources).
        simulate_route_congestion(g, ["D", "F"], "P1", 0.0, 1.0, S, tracker, "D", "F")
        _, wait_p2 = simulate_route_congestion(g, ["D", "F"], "P2", 0.0, 1.0, S, tracker, "D", "F")
        self.assertEqual(wait_p2, 0.0)


if __name__ == "__main__":
    unittest.main()
