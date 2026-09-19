import unittest
import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
)

from dtos import ModelDTO
from dtos.aco.solve_aco_model_dto import SolveAcoModelDTO
from models.opp_aco_1.opp_aco_1 import OPPAntColonyOptimization
from models.opp_aco_1.utils.output_handler import OutputHandler
from tests.opp_test_case import OPPTestCase

from tests.shared_scenarios.normal.scenario_02 import two_orders_two_aisles


class TestOrderAssignedMultipleBatches(OPPTestCase):
    """Medium: intentionally assign one order to two batches to exercise model behavior."""

    def test_order_assigned_to_multiple_batches_infeasible(self):
        V, B, w1, w2, gamma, delta, location_graph, cap_vehicle = (
            two_orders_two_aisles()
        )

        N = {"O1", "O2"}
        a = {(n, v): 0 for n in N for v in V}

        a[("O1", "L2")] = 1
        a[("O1", "L3")] = 1
        a[("O2", "L5")] = 1

        # assign O1 to both batches => violates constraint sum_{b} y_{nb} = 1 => infeasible
        y = {(n, b): 0 for n in N for b in B}
        y[("O1", "B1")] = 1
        y[("O1", "B2")] = 1
        y[("O2", "B2")] = 1

        cap_n = {"O1": 3.0, "O2": 3.0}

        params = SolveAcoModelDTO()
        params.W_full = w1
        params.W_ea_ta = w2
        params.W_ea = gamma
        params.W_ta = delta
        params.C_n = cap_n
        params.C_v = cap_vehicle
        params.A = a
        params.B_time = 0.5
        params.B_setup = 1.0
        params.B_picking = 1.0
        params.Dd = {"O1": 50.0, "O2": 50.0}
        params.M = 1000.0
        params.Bn = y

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = location_graph
        model_dto.B = B
        model_dto.start_time = self.start_time
        model = OPPAntColonyOptimization(model_dto)
        model.attach(OutputHandler())

        result, _ = model.solve(params)

        self.assertEqual(result, "infeasible")

    def test_order_assigned_to_single_batch_feasible(self):
        V, B, w1, w2, gamma, delta, location_graph, cap_vehicle = (
            two_orders_two_aisles()
        )

        N = {"O1", "O2"}
        a = {(n, v): 0 for n in N for v in V}

        a[("O1", "L2")] = 1
        a[("O1", "L3")] = 1
        a[("O2", "L5")] = 1

        # assign O1 to one batch, O2 to the other
        y = {(n, b): 0 for n in N for b in B}
        y[("O1", "B1")] = 1
        y[("O2", "B2")] = 1

        cap_n = {"O1": 3.0, "O2": 3.0}

        params = SolveAcoModelDTO()
        params.W_full = w1
        params.W_ea_ta = w2
        params.W_ea = gamma
        params.W_ta = delta
        params.C_n = cap_n
        params.C_v = cap_vehicle
        params.A = a
        params.B_time = 0.5
        params.B_setup = 1.0
        params.B_picking = 1.0
        params.Dd = {"O1": 50.0, "O2": 50.0}
        params.M = 1000.0
        params.Bn = y

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = location_graph
        model_dto.B = B
        model_dto.start_time = self.start_time
        model = OPPAntColonyOptimization(model_dto)
        model.attach(OutputHandler())

        result, _ = model.solve(params)

        self.assertIn(result, ("optimal", "feasible"))


if __name__ == "__main__":
    unittest.main()
