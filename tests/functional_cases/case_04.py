import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


from tests.infra.zimpl.dat_files_builder import build_dat_files
from models.base.opp_location_graph import OPPLocationGraph
from tests.infra.cases.exact_model_case import ExactModelTestCase
from tests.shared_scenarios.functional.scenario_02 import two_orders_two_aisles
from tests.infra.zimpl.zpl_utils import extract_active_arcs


class Case04(ExactModelTestCase):
    """
    Test 2.2: Medium. 8 vertex, 8 edges, 2 orders, 2 missions.
    Purpose: To test the functionality of the model when we have few vertex assigned to orders.
    """

    def test_two_orders_two_aisles_one_picking_point_per_order(self):
        """Case 4a."""
        V, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, _x = (
            two_orders_two_aisles()
        )

        N = {"O1", "O2"}
        A_ni = {(n, v): 0 for n in N for v in V}

        # Order 1 must visit location 3
        A_ni[("O1", "L3")] = 1

        # Order 2 must visit location 5
        A_ni[("O2", "L5")] = 1

        B_nb = {("O1", "B1"): 1, ("O1", "B2"): 0, ("O2", "B1"): 0, ("O2", "B2"): 1}
        C_n = {"O1": 3.0, "O2": 3.0}
        T_due_n = {"O1": 15.0, "O2": 15.0}

        T_travel = 0.5
        T_setup = 1.0
        T_pick = 1.0
        M = 1000.0

        S_i = {v: 0.0 for v in V}

        E = set()
        D_ij = {}
        for i in location_graph.get_vertices():
            for j in location_graph.get_vertices():
                if location_graph.has_edge(i, j):
                    E.add((i, j))
                    D_ij[(i, j)] = location_graph.get_distance(i, j)

        scenario_data = {
            "N": N,
            "V": set(location_graph.get_vertices()),
            "P": P,
            "B": B,
            "E": E,
            "depot": location_graph.get_depot(),
            "final": location_graph.get_final(),
            "W_c": w1,
            "W_pen": w2,
            "W_e": gamma,
            "W_t": delta,
            "T_travel": T_travel,
            "T_setup": T_setup,
            "T_pick": T_pick,
            "C_v": cap_vehicle,
            "M": M,
            "C_n": C_n,
            "T_due_n": T_due_n,
            "D_ij": D_ij,
            "S_i": S_i,
            "A_ni": A_ni,
            "B_nb": B_nb,
        }

        build_dat_files(self.dat_dir, scenario_data)

        try:
            status, var_values = self.solve(
                params={
                    "N": len(N),
                    "B": len(B),
                    "V": len(set(location_graph.get_vertices())),
                    "P": len(P),
                    "W_c": w1,
                    "W_pen": w2,
                    "W_e": gamma,
                    "W_t": delta,
                    "T_travel": T_travel,
                    "T_setup": T_setup,
                    "T_pick": T_pick,
                    "C_v": cap_vehicle,
                    "C_n": C_n,
                    "T_due_n": T_due_n,
                    "D_ij": D_ij,
                    "S_i": S_i,
                    "A_ni": A_ni,
                    "B_nb": B_nb,
                },
            )
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        expected_graph = OPPLocationGraph(
            depot_node="L1",
            final_node="L8",
        )

        self.assertIn(
            status,
            ("optimal", "feasible", "infeasible", "unbounded"),
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

        self.assertIn(
            status,
            ("optimal", "feasible"),
            "El modelo no encontró una solución.",
        )

        self.assertEqual(output_graph, expected_graph)

        # --- NUEVAS VALIDACIONES INTELIGENTES V4 ---
        if len(P) > 1 and len(B) > 1:
            self.assert_workload_balance(var_values, P, B, max_difference=1)
            
        self.assert_no_time_overlap(var_values, P, B)

if __name__ == "__main__":
    unittest.main()
