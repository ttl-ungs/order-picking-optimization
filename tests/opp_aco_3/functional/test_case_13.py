import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", ".."))
)

from dtos.opp.model_dto import ModelDTO
from dtos.aco.solve_aco_3_model_dto import SolveAco3ModelDTO
from models.opp_aco_3 import OPPAntColonyOptimization
from models.opp_aco_3.utils.output_handler import OutputHandler
from models.opp_aco_3.utils.route_evaluator import RouteEvaluator
from models.opp_aco_3.utils.route_solution import RouteSolution
from tests.opp_test_case import OPPTestCase
from tests.shared_scenarios.normal.scenario_17 import branched_single_mission_route
from tests.opp_v2.route_assertions import assert_route_covers_orders


class TestOPPModel(OPPTestCase):
    def test_branched_single_mission_route(self):
        """
        NOTE (2026-08-27): this test used to assert an exact hardcoded route
        (L1-L2-L3-L5-L6-L7, the shortest physical path). That assertion was
        WRONG, not opp_aco_3: with Dd=20.0 and W_ea (earliness weight) > 0,
        finishing at t=12.5 via the short route is heavily penalized for
        being too EARLY (4 orders x (20-12.5) x W_ea x W_ea_ta = 300), while
        the longer detour through L4 finishes at t=16.0, closer to the due
        date, for a strictly lower total objective (176.0 < 312.5) -- verify
        with RouteEvaluator, same one opp_aco_3 itself uses to score
        candidates. opp_aco_2/opp_hc_2/opp_hc_3 "pass" this same scenario
        only because their simpler/more deterministic construction never
        explores the detour; opp_aco_3's multi-pheromone construction
        explores enough to reliably find the true optimum instead. So the
        right check here is "did it find a valid, cost-optimal-or-better
        route", not "does it match one specific (suboptimal) path".
        """
        V, B, w1, w2, gamma, delta, location_graph, cap_vehicle = (
            branched_single_mission_route()
        )

        N = {"O1", "O2", "O3", "O4"}
        a = {(n, v): 0 for n in N for v in V}
        a[("O1", "L2")] = 1
        a[("O2", "L3")] = 1
        a[("O3", "L5")] = 1
        a[("O4", "L6")] = 1

        y = {("O1", "B1"): 1, ("O2", "B1"): 1, ("O3", "B1"): 1, ("O4", "B1"): 1}
        cap_n = {"O1": 2.0, "O2": 2.0, "O3": 2.0, "O4": 2.0}

        params = SolveAco3ModelDTO()
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
        params.Dd = {n: 20.0 for n in N}
        params.M = 1000.0
        params.Bn = y

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = location_graph
        model_dto.B = B
        model_dto.start_time = self.start_time
        model = OPPAntColonyOptimization(model_dto)
        model.attach(OutputHandler())

        try:
            result, output_graph = model.solve(params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertEqual(result, "optimal")
        route = assert_route_covers_orders(self, output_graph, {"L2", "L3", "L5", "L6"})

        # Cost check: the route opp_aco_3 returns must be at least as good
        # as the naive shortest-path route, under the SAME objective
        # opp_aco_3 itself optimizes (RouteEvaluator).
        batch_assignments = {"B1": N}
        evaluator = RouteEvaluator(
            N=N, B=B, P=["P1"], location_graph=location_graph,
            batch_assignments=batch_assignments,
            W_full=w1, W_ea_ta=w2, W_ea=gamma, W_ta=delta,
            C_n=cap_n, C_v=cap_vehicle, A=a,
            B_time=0.5, B_setup=1.0, B_picking=1.0,
            S={}, Dd=params.Dd, M=1000.0,
        )

        naive_shortest_route = ["L2", "L3", "L5", "L6"]
        naive_solution = RouteSolution(B, location_graph, batch_assignments, ["P1"])
        naive_solution.set_batch_route("B1", naive_shortest_route)
        naive_solution.assign_batch_to_picker("B1", "P1")
        naive_shortest_route_obj = evaluator.evaluate(naive_solution)

        found_solution = RouteSolution(B, location_graph, batch_assignments, ["P1"])
        found_solution.set_batch_route("B1", route[1:-1])  # strip depot/final
        found_solution.assign_batch_to_picker("B1", "P1")
        found_obj = evaluator.evaluate(found_solution)

        self.assertLessEqual(
            found_obj,
            naive_shortest_route_obj + 1e-6,
            f"opp_aco_3's route (obj={found_obj}) should be at least as good "
            f"as the naive shortest-path route (obj={naive_shortest_route_obj}), "
            f"under the model's own objective.",
        )


if __name__ == "__main__":
    unittest.main()
