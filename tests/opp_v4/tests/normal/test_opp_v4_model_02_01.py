import unittest

from models.utils.dat_files_builder import build_dat_files
from models.base.opp_location_graph import OPPLocationGraph
from tests.opp.tests.opp_test_case import OPPTestCase
from tests.opp_v4.config import DAT_DIR, ZPL_PATH
from tests.opp_v4.scenarios.normal.scenario_02 import two_orders_two_aisles
from tests.utils.zpl_utils import extract_active_arcs, solve_zpl


class TestOPPModel(OPPTestCase):
    """
    Test 2.1: Medium. 8 vertex, 8 edges, 2 orders, 2 missions.
    Purpose: To test the functionality of the model when it has to follow a route.
    """

    def test_two_orders_two_aisles(self):
        V, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, _x = (
            two_orders_two_aisles()
        )

        N = {"O1", "O2"}
        A_ni = {(n, v): 0 for n in N for v in V}

        # Order 1 must visit locations 2, 3, 4
        A_ni[("O1", "L2")] = 1
        A_ni[("O1", "L3")] = 1
        A_ni[("O1", "L4")] = 1

        # Order 2 must visit locations 5, 6, 7
        A_ni[("O2", "L5")] = 1
        A_ni[("O2", "L6")] = 1
        A_ni[("O2", "L7")] = 1

        Bn = {("O1", "B1"): 1, ("O1", "B2"): 0, ("O2", "B1"): 0, ("O2", "B2"): 1}
        C_n = {"O1": 3.0, "O2": 3.0}
        Dd = {"O1": 15.0, "O2": 15.0}

        B_time = 0.5
        B_setup = 1.0
        B_picking = 1.0
        M = 1000.0

        S_i = {v: 0.0 for v in V}

        E = set()
        d_ij = {}
        for i in location_graph.get_vertices():
            for j in location_graph.get_vertices():
                if location_graph.has_edge(i, j):
                    E.add((i, j))
                    d_ij[(i, j)] = location_graph.get_distance(i, j)

        scenario_data = {
            "N": N,
            "V": set(location_graph.get_vertices()),
            "P": P,
            "B": B,
            "E": E,
            "depot": location_graph.get_depot(),
            "final": location_graph.get_final(),
            "W_full": w1,
            "W_ea_ta": w2,
            "W_ea": gamma,
            "W_ta": delta,
            "B_time": B_time,
            "B_setup": B_setup,
            "B_picking": B_picking,
            "C_v": cap_vehicle,
            "M": M,
            "C_n": C_n,
            "Dd": Dd,
            "d_ij": d_ij,
            "S_i": S_i,
            "A_ni": A_ni,
            "Bn": Bn,
        }

        build_dat_files(DAT_DIR, scenario_data)

        try:
            status, var_values = solve_zpl(
                ZPL_PATH,
                dat_dir=DAT_DIR,
                params={
                    "N": len(N),
                    "B": len(B),
                    "V": len(set(location_graph.get_vertices())),
                    "P": len(P),
                    "W_full": w1,
                    "W_ea_ta": w2,
                    "W_ea": gamma,
                    "W_ta": delta,
                    "B_time": B_time,
                    "B_setup": B_setup,
                    "B_picking": B_picking,
                    "C_v": cap_vehicle,
                    "C_n": C_n,
                    "Dd": Dd,
                    "d_ij": d_ij,
                    "S_i": S_i,
                    "A_ni": A_ni,
                    "Bn": Bn,
                },
            )
        except Exception as e:
            self.fail(f"ZPL solve failed: {e}")

        expected_graph = OPPLocationGraph(
            depot_node="L1",
            final_node="L8",
        )

        self.assertIn(
            status,
            ("optimal", "feasible"),
            f"The model did not find a solution. Status: {status}",
        )

        assignments = {b: 0 for b in B}
        picker_workload = {p: 0 for p in P}

        for key, val in var_values.items():
            key_lower = key.lower()

            if key_lower.startswith("x_pb") and val > 0.5:
                for b in B:
                    if b in key:
                        assignments[b] += 1
                for p in P:
                    if p in key:
                        picker_workload[p] += 1

        # Cada lote debe tener asignado exactamente un picker
        for b in B:
            self.assertEqual(
                assignments[b],
                1,
                f"Batch {b} does not meet the unique assignment constraint (Assigned to {assignments[b]} pickers).",
            )

        # Deberían paralelizar el trabajo
        for p in P:
            self.assertEqual(
                picker_workload[p],
                1,
                f"The picker {p} was expected to process exactly 1 batch to parallelize the load.",
            )

        for i in location_graph.get_vertices():
            if i not in expected_graph.get_vertices():
                expected_graph.add_vertex(i, "picking")

        expected_graph.add_edge("L1", "L2", location_graph.get_distance("L1", "L2"))
        expected_graph.add_edge("L2", "L3", location_graph.get_distance("L2", "L3"))
        expected_graph.add_edge("L3", "L4", location_graph.get_distance("L3", "L4"))
        expected_graph.add_edge("L4", "L8", location_graph.get_distance("L4", "L8"))

        expected_graph.add_edge("L1", "L5", location_graph.get_distance("L1", "L5"))
        expected_graph.add_edge("L5", "L6", location_graph.get_distance("L5", "L6"))
        expected_graph.add_edge("L6", "L7", location_graph.get_distance("L6", "L7"))
        expected_graph.add_edge("L7", "L8", location_graph.get_distance("L7", "L8"))

        active_arcs = extract_active_arcs(var_values, B)

        output_graph = OPPLocationGraph(depot_node="L1", final_node="L8")
        for i in location_graph.get_vertices():
            if i not in output_graph.get_vertices():
                output_graph.add_vertex(i, "picking")
        for b, arcs in active_arcs.items():
            for i, j in arcs:
                if not output_graph.has_edge(i, j):
                    output_graph.add_edge(i, j, location_graph.get_distance(i, j))

        self.assertEqual(output_graph, expected_graph)


if __name__ == "__main__":
    unittest.main()
