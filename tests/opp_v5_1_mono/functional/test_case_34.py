import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from tests.shared_scenarios.functional.two_stage_scenarios_v5 import (
    cold_chain_exact_boundary,
    cold_chain_infeasible_for_every_picker,
    heterogeneous_speed_precise,
)
from tests.opp_v5_1_mono.opp_test_case_v5_1_mono import OPPTestCaseMono


class TestOPPMonoSpeedFormula(OPPTestCaseMono):
    """
    Deeper validation of opp_v5_2_split.1's own capability (heterogeneous picker
    speed), beyond model_20's "which picker gets which batch" check:
    asserts the exact t_exec_pb = tiempo_fijo + R_b_time / V_p formula
    numerically, confirming ONLY the route-time component is divided by
    speed -- setup/picking stays fixed regardless of which picker runs it,
    per opp_model_v5_1_mono.zpl's documented assumption.
    """

    def test_completion_time_matches_the_documented_formula_exactly(self):
        scenario = heterogeneous_speed_precise()
        _, route_times, status, values = self.run_pipeline(scenario)

        self.assertIn(status, ("optimal", "feasible"))
        self.assertAlmostEqual(route_times["B1"], 5.0, places=5)
        self.assertAlmostEqual(route_times["B2"], 14.0, places=5)

        assignments = self.assignments(values, scenario["P"], scenario["B"])
        completions = self.completion_times(values, scenario["P"], scenario["B"])

        # Cost-minimizing assignment: fast picker on the longer route.
        self.assertEqual(assignments, {"B1": "P_slow", "B2": "P_fast"})

        # Exact numbers, not just "smaller than the other assignment would
        # give" -- ties the test directly to the formula in the .zpl.
        tiempo_fijo = 2.0  # B_setup(1.0) + B_picking(1.0) * C_n["O1" or "O2"](1.0)
        self.assertAlmostEqual(
            completions[("P_slow", "B1")], tiempo_fijo + 5.0 / 1.0, places=5
        )
        self.assertAlmostEqual(
            completions[("P_fast", "B2")], tiempo_fijo + 14.0 / 2.0, places=5
        )
        self.assert_no_overlap(values, scenario, route_times)


class TestOPPMonoColdChainEdgeCases(OPPTestCaseMono):
    """
    Deeper validation of opp_v5_2_split.1's other own capability (the cold-chain
    limit), beyond model_21's basic filtering check: the exact `<=`
    boundary, and the genuine infeasible case solved all the way through
    SCIP (not just replicated in Python via eligible_pairs()).
    """

    def test_picker_exactly_at_the_cold_chain_limit_is_still_eligible(self):
        # T_frio_max == t_exec_pb(P_fast, B1) == 9.0 exactly. The cold-chain limit
        # is a `<=` bound (+1e-9), so this must NOT be excluded by an off-by-one
        # at the boundary -- a real risk given the floating-point
        # equality involved (t_exec_pb is itself a derived, not a directly
        # read, parameter).
        scenario = cold_chain_exact_boundary()
        self.assertIn(("P_fast", "B1"), self.eligible_pairs(scenario, {"B1": 14.0}))

        _, route_times, status, values = self.run_pipeline(scenario)
        self.assertIn(status, ("optimal", "feasible"))
        assignments = self.assignments(values, scenario["P"], scenario["B"])
        self.assertEqual(assignments, {"B1": "P_fast"})

    def test_no_eligible_picker_returns_infeasible_gracefully(self):
        # A batch with no eligible (picker, batch) pair under the cold-chain limit
        # must come back as a clean "infeasible" (no values), not as an error.
        # opp_v5_2_split needs a Python-side pre-check for this (ZIMPL rejects the empty
        # sum in its eligibility set at compile time); the monolithic model has
        # no such set, so here SCIP itself has to prove the infeasibility: with
        # u_pb bounded by T_frio_max, assign_exactly_one_picker cannot hold.
        scenario = cold_chain_infeasible_for_every_picker()
        self.assertEqual(self.eligible_pairs(scenario, {"B1": 14.0}), set())

        _, _, status, values = self.run_pipeline(scenario)
        self.assertEqual(status, "infeasible")
        self.assertEqual(values, {})
