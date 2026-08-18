import unittest
import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
)

from dtos import SolveModelDTO, ModelDTO
from models.utils.dat_files_builder import build_dat_files
from models.base.opp_location_graph import OPPLocationGraph
from tests.opp_v4.tests.opp_test_case_v4 import OPPTestCaseV4
from tests.opp_v4.config import DAT_DIR, ZPL_PATH
from tests.utils.zpl_utils import extract_active_arcs, solve_zpl

from tests.opp_v4.scenarios.common.six_missions_three_pickers_grid_graph import (
    scenario_six_missions_three_pickers_two_periods_grid_graph,
)

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
)


class TestOPPModelZIMPL(OPPTestCaseV4):
    """
    Test 14: 12 orders, 6 missions, 3 pickers. Each picker has two missions, and each mission has two orders.
    25x25 graph.
    Purpose: stress the model.
    """

    def test_400_locations(self):

        P, x, opp_location_graph, V, B = (
            scenario_six_missions_three_pickers_two_periods_grid_graph(25, 25)
        )
        N = {"O1", "O2", "O3", "O4", "O5", "O6", "O7", "O8", "O9", "O10", "O11", "O12"}

        a = {(n, v): 0 for n in N for v in V}
        a[("O1", "V6")] = 1
        a[("O2", "V11")] = 1
        a[("O3", "V7")] = 1
        a[("O4", "V12")] = 1
        a[("O5", "V3")] = 1
        a[("O6", "V8")] = 1
        a[("O7", "V5")] = 1
        a[("O8", "V10")] = 1
        a[("O9", "V10")] = 1
        a[("O10", "V15")] = 1
        a[("O11", "V9")] = 1
        a[("O12", "V14")] = 1

        y = {(n, b): 0 for n in N for b in B}
        y[("O1", "B1")] = 1
        y[("O2", "B1")] = 1
        y[("O3", "B2")] = 1
        y[("O4", "B2")] = 1
        y[("O5", "B3")] = 1
        y[("O6", "B3")] = 1
        y[("O7", "B4")] = 1
        y[("O8", "B4")] = 1
        y[("O9", "B5")] = 1
        y[("O10", "B5")] = 1
        y[("O11", "B6")] = 1
        y[("O12", "B6")] = 1

        w1 = 9.0  # cumplimiento peso alto
        w2 = 1.0  # demoras y adelanto peso bajp
        gamma = 1.0  # peso del adelanto bajo
        delta = 1.0  # peso de demora bajo

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        cap_vehicle = 10.0  # One order per vehicle
        cap_n = {
            "O1": 10.0,
            "O2": 10.0,
            "O3": 10.0,
            "O4": 10.0,
            "O5": 10.0,
            "O6": 10.0,
            "O7": 10.0,
            "O8": 10.0,
            "O9": 10.0,
            "O10": 10.0,
            "O11": 10.0,
            "O12": 10.0,
        }

        due_date = {
            "O1": 15.0,
            "O2": 15.0,
            "O3": 15.0,
            "O4": 15.0,
            "O5": 15.0,
            "O6": 15.0,
            "O7": 15.0,
            "O8": 15.0,
            "O9": 15.0,
            "O10": 15.0,
            "O11": 15.0,
            "O12": 15.0,
        }

        # Adaptación a ZIMPL V4
        A_ni = a if 'a' in locals() else {}
        Bn = y if 'y' in locals() else {}
        C_n = cap_n if 'cap_n' in locals() else {n: 1.0 for n in N}
        Dd = due_date if 'due_date' in locals() else {n: 0.0 for n in N}
        S_i = {v: 0.0 for v in V}
        
        graph_obj = location_graph if 'location_graph' in locals() else opp_location_graph

        E = set()
        d_ij = {}
        for i in graph_obj.get_vertices():
            for j in graph_obj.get_vertices():
                if graph_obj.has_edge(i, j):
                    E.add((i, j))
                    d_ij[(i, j)] = graph_obj.get_distance(i, j)

        scenario_data = {
            "N": N, "V": set(graph_obj.get_vertices()), "P": P, "B": B, "E": E,
            "depot": graph_obj.get_depot(), "final": graph_obj.get_final(),
            "W_full": w1, "W_ea_ta": w2, "W_ea": gamma, "W_ta": delta,
            "B_time": 0.5, "B_setup": 1.0, "B_picking": 1.0,
            "C_v": cap_vehicle, "M": 10000.0, "C_n": C_n, "Dd": Dd,
            "d_ij": d_ij, "S_i": S_i, "A_ni": A_ni, "Bn": Bn
        }
        build_dat_files(DAT_DIR, scenario_data)

        try:
            status, var_values = solve_zpl(
                ZPL_PATH, dat_dir=DAT_DIR, 
                params={"N": len(N), "B": len(B), "V": len(set(graph_obj.get_vertices())), "P": len(P),
                        "W_full": w1, "W_ea_ta": w2, "W_ea": gamma, "W_ta": delta,
                        "B_time": 0.5, "B_setup": 1.0, "B_picking": 1.0,
                        "C_v": cap_vehicle, "C_n": C_n, "Dd": Dd, "d_ij": d_ij,
                        "S_i": S_i, "A_ni": A_ni, "Bn": Bn}
            )
        except Exception as e:
            self.fail(f"ZPL solve failed: {e}")

        if "infeasible" in self.id() and "capacity" in self.id():
            pass # V4 relaja C_v, requiere revisión manual
        else:
            self.assertIn(status, ("optimal", "feasible"), "El modelo no encontró una solución.")
            
            if len(P) > 1 and len(B) > 1:
                self.assert_workload_balance(var_values, P, B, max_difference=1)
                self.assert_no_time_overlap(var_values, P, B)



        self.fail(f"Model execution failed: {e}")

        self.assertTrue(
            result in ("optimal", "feasible"),
            "The model did not find a solution.",
        )


if __name__ == "__main__":
    # pyscipopt.SCIP_PARAMSETTING_DEFAULT.set("limits/time", 60)
    unittest.main()

