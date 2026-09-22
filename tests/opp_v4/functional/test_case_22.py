# Corresponds to test test_case_19.py

import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", ".."))
)

from tests.opp_v4.opp_test_case_v4 import OPPTestCaseV4
from tests.shared_scenarios.functional.single_order_params_v4 import single_order_params
from tests.infra.zimpl.dat_files_builder import build_dat_files
from tests.opp_v4.config import DAT_DIR, ZPL_PATH
from tests.infra.zimpl.zpl_utils import solve_zpl


class TestOPPModelZIMPL(OPPTestCaseV4):

    def extract_tardiness_earliness(self, var_values, order):
        ta = 0.0
        ea = 0.0
        for key, val in var_values.items():
            # Checking for both standard bracket and ZIMPL '$' output formats
            if f"ta_n[{order}]" in key or f"ta_n${order}" in key:
                ta = val
            if f"ea_n[{order}]" in key or f"ea_n${order}" in key:
                ea = val
        return ta, ea

    def test_earliness_when_batch_finishes_before_due_date(self):
        # Usamos los DTOs antiguos de V2 solo para sacarles los datos limpios
        params, model_dto = single_order_params(
            due_date_value=10000.0, start_time=self.start_time
        )

        # Extracción para ZIMPL
        E, d_ij = set(), {}
        for i in model_dto.location_graph.get_vertices():
            for j in model_dto.location_graph.get_vertices():
                if model_dto.location_graph.has_edge(i, j):
                    E.add((i, j))
                    d_ij[(i, j)] = model_dto.location_graph.get_distance(i, j)

        scenario_data = {
            "N": model_dto.N,
            "V": set(model_dto.location_graph.get_vertices()),
            "P": model_dto.P,
            "B": model_dto.B,
            "E": E,
            "depot": model_dto.location_graph.get_depot(),
            "final": model_dto.location_graph.get_final(),
            "W_full": params.W_full,
            "W_ea_ta": params.W_ea_ta,
            "W_ea": params.W_ea,
            "W_ta": params.W_ta,
            "B_time": params.B_time,
            "B_setup": params.B_setup,
            "B_picking": params.B_picking,
            "C_v": params.C_v,
            "M": params.M,
            "C_n": params.C_n,
            "Dd": params.Dd,
            "d_ij": d_ij,
            "S_i": {v: 0.0 for v in set(model_dto.location_graph.get_vertices())},
            "A_ni": params.A,
            "Bn": params.Bn,
        }

        build_dat_files(DAT_DIR, scenario_data)
        status, var_values = solve_zpl(
            ZPL_PATH,
            dat_dir=DAT_DIR,
            params={
                "N": len(model_dto.N),
                "B": len(model_dto.B),
                "V": len(scenario_data["V"]),
                "P": len(model_dto.P),
                "W_full": params.W_full,
                "W_ea_ta": params.W_ea_ta,
                "W_ea": params.W_ea,
                "W_ta": params.W_ta,
                "B_time": params.B_time,
                "B_setup": params.B_setup,
                "B_picking": params.B_picking,
                "C_v": params.C_v,
                "C_n": params.C_n,
                "Dd": params.Dd,
                "d_ij": d_ij,
                "S_i": {v: 0.0 for v in set(model_dto.location_graph.get_vertices())},
                "A_ni": params.A,
                "Bn": params.Bn
            },
        )

        self.assertIn(status, ("optimal", "feasible"))

        ta, ea = self.extract_tardiness_earliness(var_values, "O1")
        self.assertGreater(ea, 0.0, "Expected positive earliness") #!
        self.assertAlmostEqual(ta, 0.0, places=4, msg="Expected zero tardiness")

    def test_tardiness_when_batch_finishes_after_due_date(self):
        params, model_dto = single_order_params(
            due_date_value=0.0, start_time=self.start_time
        )

        # Extracción para ZIMPL (Misma logica)
        E, d_ij = set(), {}
        for i in model_dto.location_graph.get_vertices():
            for j in model_dto.location_graph.get_vertices():
                if model_dto.location_graph.has_edge(i, j):
                    E.add((i, j))
                    d_ij[(i, j)] = model_dto.location_graph.get_distance(i, j)

        scenario_data = {
            "N": model_dto.N,
            "V": set(model_dto.location_graph.get_vertices()),
            "P": model_dto.P,
            "B": model_dto.B,
            "E": E,
            "depot": model_dto.location_graph.get_depot(),
            "final": model_dto.location_graph.get_final(),
            "W_full": params.W_full,
            "W_ea_ta": params.W_ea_ta,
            "W_ea": params.W_ea,
            "W_ta": params.W_ta,
            "B_time": params.B_time,
            "B_setup": params.B_setup,
            "B_picking": params.B_picking,
            "C_v": params.C_v,
            "M": params.M,
            "C_n": params.C_n,
            "Dd": params.Dd,
            "d_ij": d_ij,
            "S_i": {v: 0.0 for v in set(model_dto.location_graph.get_vertices())},
            "A_ni": params.A,
            "Bn": params.Bn
        }

        build_dat_files(DAT_DIR, scenario_data)
        status, var_values = solve_zpl(
            ZPL_PATH,
            dat_dir=DAT_DIR,
            params={
                "N": len(model_dto.N),
                "B": len(model_dto.B),
                "V": len(scenario_data["V"]),
                "P": len(model_dto.P),
                "W_full": params.W_full,
                "W_ea_ta": params.W_ea_ta,
                "W_ea": params.W_ea,
                "W_ta": params.W_ta,
                "B_time": params.B_time,
                "B_setup": params.B_setup,
                "B_picking": params.B_picking,
                "C_v": params.C_v,
                "C_n": params.C_n,
                "Dd": params.Dd,
                "d_ij": d_ij,
                "S_i": {v: 0.0 for v in set(model_dto.location_graph.get_vertices())},
                "A_ni": params.A,
                "Bn": params.Bn
            },
        )

        self.assertIn(
            status,
            ("optimal", "feasible"),
            "El modelo no encontró una solución.",
        )

        ta, ea = self.extract_tardiness_earliness(var_values, "O1")
        self.assertGreater(ta, 0.0, "Expected positive tardiness")
        self.assertAlmostEqual(ea, 0.0, places=4, msg="Expected zero earliness")


if __name__ == "__main__":
    unittest.main()