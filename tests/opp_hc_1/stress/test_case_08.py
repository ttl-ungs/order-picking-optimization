import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", ".."))
)

from tests.support.graphs_factory import GraphsFactory
from dtos.opp.model_dto import ModelDTO
from dtos.hc.solve_hc_model_dto import SolveHCModelDTO
from models.opp_hc_1.opp_hc_1 import OPPHillClimbing
from models.opp_hc_1.utils.output_handler import OutputHandler
from tests.support.opp_test_case import OPPTestCase


class TestOPPModel(OPPTestCase):
    """
    Test 8: Shared hot-spot locations across batches. 30 orders, 10 batches. 10x10 grid.
    """

    def test_shared_hotspots(self):
        factory = GraphsFactory()
        opp_location_graph, V = factory.get_graph(10, 10, 4, 4)
        B = {f"B{i}" for i in range(1, 11)}
        N = {f"O{i}" for i in range(1, 31)}

        y = {(o, b): 0 for o in N for b in B}
        sorted_batches = sorted(B)
        for i, o in enumerate(sorted(N)):
            y[(o, sorted_batches[i % len(sorted_batches)])] = 1

        depot = opp_location_graph.get_depot()
        final = opp_location_graph.get_final()
        candidate_locations = [v for v in sorted(V) if v not in {depot, final}]
        hotspots = (
            candidate_locations[:2]
            if len(candidate_locations) >= 2
            else candidate_locations
        )

        a = {(n, v): 0 for n in N for v in V}
        for o in N:
            a[(o, hotspots[0])] = 1
            if len(hotspots) > 1:
                a[(o, hotspots[1])] = 1

        cap_n = {n: 1.0 for n in N}
        due_date = {n: 30.0 for n in N}

        cap_vehicle = 20.0
        w1 = 9.0
        w2 = 1.0
        gamma = 1.0
        delta = 1.0

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        params = SolveHCModelDTO()
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
        model_dto.location_graph = opp_location_graph
        model_dto.B = B
        model_dto.start_time = self.start_time
        model = OPPHillClimbing(model_dto)
        model.attach(OutputHandler())

        try:
            result, _ = model.solve(params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertIn(result, ("optimal", "feasible"))


if __name__ == "__main__":
    unittest.main()
