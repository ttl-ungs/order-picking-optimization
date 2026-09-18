import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
)

from dtos.opp.model_dto import ModelDTO
from dtos.aco.solve_aco_model_dto import SolveAcoModelDTO
from models.opp_aco.opp_aco import OPPAntColonyOptimization
from models.opp_aco.utils.output_handler import OutputHandler
from tests.opp.tests.opp_test_case import OPPTestCase
from tests.shared_scenarios.normal.multigrid_graph import (
    multigrid_5x5_3x3_five_pickers_twelve_batches,
)


class TestOPPModel(OPPTestCase):
    """
    Test 10: Disconnected graph. 6 orders, 12 batches. 5x5 + 3x3 multigrid.
    """

    def test_disconnected_graph(self):
        V, B, w1, w2, gamma, delta, location_graph, cap_vehicle = (
            multigrid_5x5_3x3_five_pickers_twelve_batches(connect=False)
        )

        N = {f"O{i}" for i in range(1, 7)}

        y = {(o, b): 0 for o in N for b in B}
        for o in N:
            y[(o, "B1")] = 1

        depot = location_graph.get_depot()
        final = location_graph.get_final()
        candidate_locations = [
            v for v in sorted(V) if v.startswith("A") and v not in {depot, final}
        ]

        a = {(n, v): 0 for n in N for v in V}
        for i, o in enumerate(sorted(N)):
            a[(o, candidate_locations[i % len(candidate_locations)])] = 1

        cap_n = {n: 2.0 for n in N}
        due_date = {n: 30.0 for n in N}

        cap_vehicle = 20.0

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        params = SolveAcoModelDTO()
        params.W_full = w1
        params.W_ea_ta = w2
        params.W_ea = gamma
        params.W_ta = delta
        params.C_n = cap_n
        params.C_v = cap_vehicle
        params.A = a
        params.B_time = beta_time
        params.B_setup = beta_setup
        params.B_picking = beta_picking
        params.Dd = due_date
        params.M = M
        params.Bn = y

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = location_graph
        model_dto.B = B
        model_dto.start_time = self.start_time
        model = OPPAntColonyOptimization(model_dto)
        model.attach(OutputHandler())

        try:
            result, _ = model.solve(params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertIn(result, ("infeasible", "infeasible_or_unbounded"))


if __name__ == "__main__":
    unittest.main()
