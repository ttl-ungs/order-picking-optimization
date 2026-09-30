# Corresponds to test test_case_09.py

import unittest
import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
)

from tests.infra.zimpl.dat_files_builder import build_dat_files
from models.base.opp_location_graph import OPPLocationGraph
from tests.opp_v4.opp_test_case_v4 import OPPTestCaseV4
from tests.opp_v4.config import DAT_DIR, ZPL_PATH
from tests.infra.zimpl.zpl_utils import extract_active_arcs, solve_zpl

from tests.shared_scenarios.common.six_missions_three_pickers_grid_graph_v4 import (
    scenario_six_missions_three_pickers_two_periods_grid_graph,
)

# El modelo ya no evalúa que las órdenes entren en el carro, el test ya no tiene sentido.
class TestOPPModelZIMPL(OPPTestCaseV4):
    """
    Test 9: 12 orders, 6 missions, 3 pickers. Each picker has two missions, and each mission has two orders.
    """

    # def test_twelve_orders_six_missions_three_pickers_one_order_per_vehicle(self):
    #     P, x, opp_location_graph, V, B = (
    #         scenario_six_missions_three_pickers_two_periods_grid_graph()
    #     )
    #     N = {"O1", "O2", "O3", "O4", "O5", "O6", "O7", "O8", "O9", "O10", "O11", "O12"}
    #     a = {(n, v): 0 for n in N for v in V}
    #
    #     a[("O1", "V6")] = 1
    #     a[("O2", "V11")] = 1
    #     a[("O3", "V7")] = 1
    #     a[("O4", "V12")] = 1
    #     a[("O5", "V3")] = 1
    #     a[("O6", "V8")] = 1
    #     a[("O7", "V5")] = 1
    #     a[("O8", "V10")] = 1
    #     a[("O9", "V10")] = 1
    #     a[("O10", "V15")] = 1
    #     a[("O11", "V9")] = 1
    #     a[("O12", "V14")] = 1
    #
    #     y = {(n, b): 0 for n in N for b in B}
    #     y[("O1", "B1")] = 1
    #     y[("O2", "B1")] = 1
    #     y[("O3", "B2")] = 1
    #     y[("O4", "B2")] = 1
    #     y[("O5", "B3")] = 1
    #     y[("O6", "B3")] = 1
    #     y[("O7", "B4")] = 1
    #     y[("O8", "B4")] = 1
    #     y[("O9", "B5")] = 1
    #     y[("O10", "B5")] = 1
    #     y[("O11", "B6")] = 1
    #     y[("O12", "B6")] = 1
    #
    #     w1 = 9.0  # cumplimiento peso alto
    #     w2 = 1.0  # demoras y adelanto peso bajp
    #     gamma = 1.0  # peso del adelanto bajo
    #     delta = 1.0  # peso de demora bajo
    #
    #     beta_time = 0.5
    #     beta_setup = 1.0
    #     beta_picking = 1.0
    #     M = 1000.0
    #
    #     cap_vehicle = 10.0  # One order per vehicle
    #     cap_n = {
    #         "O1": 10.0,
    #         "O2": 10.0,
    #         "O3": 10.0,
    #         "O4": 10.0,
    #         "O5": 10.0,
    #         "O6": 10.0,
    #         "O7": 10.0,
    #         "O8": 10.0,
    #         "O9": 10.0,
    #         "O10": 10.0,
    #         "O11": 10.0,
    #         "O12": 10.0,
    #     }
    #
    #     due_date = {
    #         "O1": 15.0,
    #         "O2": 15.0,
    #         "O3": 15.0,
    #         "O4": 15.0,
    #         "O5": 15.0,
    #         "O6": 15.0,
    #         "O7": 15.0,
    #         "O8": 15.0,
    #         "O9": 15.0,
    #         "O10": 15.0,
    #         "O11": 15.0,
    #         "O12": 15.0,
    #     }
    #     # Adaptación de variables para el formato ZIMPL V4
    #     A_ni = a if "a" in locals() else {}
    #     B_nb = y if "y" in locals() else {}
    #     C_n = cap_n if "cap_n" in locals() else {}
    #     T_due_n = due_date if "due_date" in locals() else {n: 0.0 for n in N}
    #
    #     # Tiempo de servicio por defecto (si V2 no lo tenía explícito)
    #     S_i = {v: 0.0 for v in V}
    #
    #     # Generación de conjunto de Arcos válidos E y distancias D_ij
    #     E = set()
    #     D_ij = {}
    #     for i in opp_location_graph.get_vertices():
    #         for j in opp_location_graph.get_vertices():
    #             if opp_location_graph.has_edge(i, j):
    #                 E.add((i, j))
    #                 D_ij[(i, j)] = opp_location_graph.get_distance(i, j)
    #
    #     scenario_data = {
    #         "N": N,
    #         "V": set(opp_location_graph.get_vertices()),
    #         "P": P,
    #         "B": B,
    #         "E": E,
    #         "depot": opp_location_graph.get_depot(),
    #         "final": opp_location_graph.get_final(),
    #         "W_c": w1,
    #         "W_pen": w2,
    #         "W_e": gamma,
    #         "W_t": delta,
    #         "T_travel": 0.5,
    #         "T_setup": 1.0,
    #         "T_pick": 1.0,
    #         "C_v": cap_vehicle,
    #         "M": 10000.0,
    #         "C_n": C_n,
    #         "T_due_n": T_due_n,
    #         "D_ij": D_ij,
    #         "S_i": S_i,
    #         "A_ni": A_ni,
    #         "B_nb": B_nb,
    #     }
    #
    #     build_dat_files(DAT_DIR, scenario_data)
    #
    #     try:
    #         status, var_values = solve_zpl(
    #             ZPL_PATH,
    #             dat_dir=DAT_DIR,
    #             params={
    #                 "N": len(N),
    #                 "B": len(B),
    #                 "V": len(set(opp_location_graph.get_vertices())),
    #                 "P": len(P),
    #                 "W_c": w1,
    #                 "W_pen": w2,
    #                 "W_e": gamma,
    #                 "W_t": delta,
    #                 "T_travel": 0.5,
    #                 "T_setup": 1.0,
    #                 "T_pick": 1.0,
    #                 "C_v": cap_vehicle,
    #                 "C_n": C_n,
    #                 "T_due_n": T_due_n,
    #                 "D_ij": D_ij,
    #                 "S_i": S_i,
    #                 "A_ni": A_ni,
    #                 "B_nb": B_nb,
    #             },
    #         )
    #
    #         active_arcs = extract_active_arcs(var_values, B)
    #         output_graph = OPPLocationGraph(depot_node="L1", final_node="L4")
    #         for i in opp_location_graph.get_vertices():
    #             if i not in output_graph.get_vertices():
    #                 output_graph.add_vertex(i, "picking")
    #         for b, arcs in active_arcs.items():
    #             for i, j in arcs:
    #                 if not output_graph.has_edge(i, j):
    #                     output_graph.add_edge(i, j, opp_location_graph.get_distance(i, j))
    #
    #         print(output_graph.to_string())
    #     except Exception as e:
    #         self.fail(f"ZPL solve failed: {e}")
    #
    #     self.assertIn(
    #         status,
    #         ("infeasible",),
    #         "El modelo encontró una solución cuando se esperaba que fuera infactible.",
    #     )


if __name__ == "__main__":
    unittest.main()
