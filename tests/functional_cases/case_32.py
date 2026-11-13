import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tests.infra.zimpl.dat_files_builder import build_dat_files
from tests.infra.cases.exact_model_case import ExactModelTestCase

from tests.shared_scenarios.functional.one_mission_one_picker_grid_graph import (
    scenario_one_mission_one_picker_grid_graph,
)


class Case32(ExactModelTestCase):
    """A single order whose own capacity
    exceeds the vehicle capacity must be infeasible."""

    def test_single_order_exceeds_vehicle(self):
        """Case 32a."""
        P, opp_location_graph, V, B = scenario_one_mission_one_picker_grid_graph(6, 6)

        N = {"O1"}
        a = {(n, v): 0 for n in N for v in V}
        a[("O1", "V2")] = 1
        a[("O1", "V18")] = 1

        y = {(n, b): 0 for n in N for b in B}
        first_b = sorted(B)[0]
        y[("O1", first_b)] = 1

        cap_vehicle = 10.0
        cap_n = {"O1": 25.0}
        due_date = {"O1": 100.0}

        E = set()
        D_ij = {}
        for i in opp_location_graph.get_vertices():
            for j in opp_location_graph.get_vertices():
                if opp_location_graph.has_edge(i, j):
                    E.add((i, j))
                    D_ij[(i, j)] = opp_location_graph.get_distance(i, j)

        scenario_data = {
            "N": N,
            "V": set(opp_location_graph.get_vertices()),
            "P": P,
            "B": B,
            "E": E,
            "depot": opp_location_graph.get_depot(),
            "final": opp_location_graph.get_final(),
            "W_c": 1.0,
            "W_pen": 1.0,
            "W_e": 1.0,
            "W_t": 1.0,
            "T_travel": 0.5,
            "T_setup": 1.0,
            "T_pick": 1.0,
            "C_v": cap_vehicle,
            "M": 1000.0,
            "C_n": cap_n,
            "T_due_n": due_date,
            "D_ij": D_ij,
            "S_i": {v: 0.0 for v in V},
            "A_ni": a,
            "B_nb": y,
        }

        build_dat_files(self.dat_dir, scenario_data)

        status, _ = self.solve(
            params={
                "N": len(N), "B": len(B), "V": len(V), "P": len(P),
                "C_n": cap_n, "B_nb": y, "C_v": cap_vehicle,
            },
        )

        self.assertEqual(status, "infeasible")


if __name__ == "__main__":
    unittest.main()
