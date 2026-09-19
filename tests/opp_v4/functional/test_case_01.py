# Corresponds to test test_case_01.py

import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))


from tests.infra.zimpl.dat_files_builder import build_dat_files
from models.base.opp_location_graph import OPPLocationGraph
from tests.opp_v4.opp_test_case_v4 import OPPTestCaseV4
from tests.opp_v4.config import PROJECT_ROOT, DAT_DIR, ZPL_PATH
from tests.shared_scenarios.functional.scenario_01_v4 import basic_two_orders_capacity_limit
from tests.infra.zimpl.zpl_utils import extract_active_arcs, solve_zpl


class TestOPPModelZIMPL(OPPTestCaseV4):
    """
    Test 1 (ZIMPL): Basic. 4 vertices, 5 edges, 2 orders, 2 batches.
    """

    def test_basic_two_orders_capacity_limit(self):
        V, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, _x = (
            basic_two_orders_capacity_limit()
        )

        N = {"O1", "O2"}

        A_ni = {(n, v): 0 for n in N for v in V}
        A_ni[("O1", "L2")] = 1
        A_ni[("O2", "L3")] = 1

        Bn = {("O1", "B1"): 1, ("O1", "B2"): 0, ("O2", "B1"): 0, ("O2", "B2"): 1}
        C_n = {"O1": 3.0, "O2": 3.0}
        Dd = {"O1": 15.0, "O2": 15.0}

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
            "B_time": 0.5,
            "B_setup": 1.0,
            "B_picking": 1.0,
            "C_v": cap_vehicle,
            "M": 10000.0,
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
                    "B_time": 0.5,
                    "B_setup": 1,
                    "B_picking": 1,
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

        self.assertIn(
            status,
            ("optimal", "feasible"),
            f"The model did not find a solution. Status: {status}",
        )

        # NUEVAS VALIDACIONES
        assignments = {b: 0 for b in B}
        picker_workload = {p: 0 for p in P}

        for key, val in var_values.items():
            key_lower = (
                key.lower()
            )  # Pasamos a minúsculas por cómo ZIMPL exporta a SCIP

            if key_lower.startswith("x_pb") and val > 0.5:
                # Buscamos el lote y el picker dentro del string original (ej: x_pb$P1$B1)
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
        # =========================================================

        # Verificar arcos activos contra el grafo esperado
        expected_graph = OPPLocationGraph(depot_node="L1", final_node="L4")
        for i in location_graph.get_vertices():
            if i not in expected_graph.get_vertices():
                expected_graph.add_vertex(i, "picking")

        expected_graph.add_edge("L1", "L2", location_graph.get_distance("L1", "L2"))
        expected_graph.add_edge("L2", "L4", location_graph.get_distance("L2", "L4"))
        expected_graph.add_edge("L1", "L3", location_graph.get_distance("L1", "L3"))
        expected_graph.add_edge("L3", "L4", location_graph.get_distance("L3", "L4"))

        active_arcs = extract_active_arcs(var_values, B)

        output_graph = OPPLocationGraph(depot_node="L1", final_node="L4")
        for i in location_graph.get_vertices():
            if i not in output_graph.get_vertices():
                output_graph.add_vertex(i, "picking")
        for b, arcs in active_arcs.items():
            for i, j in arcs:
                if not output_graph.has_edge(i, j):
                    output_graph.add_edge(i, j, location_graph.get_distance(i, j))

        self.assertEqual(output_graph, expected_graph)
        # --- NUEVAS VALIDACIONES INTELIGENTES V4 ---
        if len(P) > 1 and len(B) > 1:
            self.assert_workload_balance(var_values, P, B, max_difference=1)
            
        self.assert_no_time_overlap(var_values, P, B)

if __name__ == "__main__":
    unittest.main()
