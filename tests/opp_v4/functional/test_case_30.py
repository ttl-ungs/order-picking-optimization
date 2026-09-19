import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from tests.infra.zimpl.dat_files_builder import build_dat_files
from tests.opp_v4.opp_test_case_v4 import OPPTestCaseV4
from tests.opp_v4.config import DAT_DIR, ZPL_PATH
from tests.infra.zimpl.zpl_utils import solve_zpl

from tests.shared_scenarios.functional.one_mission_one_picker_grid_graph_v4 import (
    scenario_one_mission_one_picker_grid_graph,
)


class TestSingleOrderExceedsVehicleZIMPL(OPPTestCaseV4):
    """Ported from opp_hc_2's test #28: a single order whose own capacity
    exceeds the vehicle capacity must be infeasible."""

    def test_single_order_exceeds_vehicle(self):
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
        d_ij = {}
        for i in opp_location_graph.get_vertices():
            for j in opp_location_graph.get_vertices():
                if opp_location_graph.has_edge(i, j):
                    E.add((i, j))
                    d_ij[(i, j)] = opp_location_graph.get_distance(i, j)

        scenario_data = {
            "N": N,
            "V": set(opp_location_graph.get_vertices()),
            "P": P,
            "B": B,
            "E": E,
            "depot": opp_location_graph.get_depot(),
            "final": opp_location_graph.get_final(),
            "W_full": 1.0,
            "W_ea_ta": 1.0,
            "W_ea": 1.0,
            "W_ta": 1.0,
            "B_time": 0.5,
            "B_setup": 1.0,
            "B_picking": 1.0,
            "C_v": cap_vehicle,
            "M": 1000.0,
            "C_n": cap_n,
            "Dd": due_date,
            "d_ij": d_ij,
            "S_i": {v: 0.0 for v in V},
            "A_ni": a,
            "Bn": y,
        }

        build_dat_files(DAT_DIR, scenario_data)

        status, _ = solve_zpl(
            ZPL_PATH,
            dat_dir=DAT_DIR,
            params={
                "N": len(N), "B": len(B), "V": len(V), "P": len(P),
                "C_n": cap_n, "Bn": y, "C_v": cap_vehicle,
            },
        )

        self.assertEqual(status, "infeasible")


if __name__ == "__main__":
    unittest.main()
