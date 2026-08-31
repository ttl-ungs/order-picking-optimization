import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from tests.opp_v5.scenarios.normal.two_stage_scenarios import (
    cold_chain_exact_boundary,
    cold_chain_infeasible_for_every_picker,
    heterogeneous_speed_precise,
)
from tests.opp_v5.tests.opp_test_case_v5 import OPPTestCaseV5
from tests.utils.zpl_utils import solve_zpl
from tests.opp_v5.config import DAT_DIR, STAGE2_ZPL_PATH


class TestOPPV5SpeedFormula(OPPTestCaseV5):
    """
    Deeper validation of opp_v5's own capability (heterogeneous picker
    speed), beyond model_20's "which picker gets which batch" check:
    asserts the exact t_exec_pb = tiempo_fijo + R_b_time / V_p formula
    numerically, confirming ONLY the route-time component is divided by
    speed -- setup/picking stays fixed regardless of which picker runs it,
    per stage2_scheduling.zpl's documented assumption.
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


class TestOPPV5ColdChainEdgeCases(OPPTestCaseV5):
    """
    Deeper validation of opp_v5's other own capability (the cold-chain
    limit), beyond model_21's basic filtering check: the exact `<=`
    boundary, and the genuine infeasible case solved all the way through
    SCIP (not just replicated in Python via eligible_pairs()).
    """

    def test_picker_exactly_at_the_cold_chain_limit_is_still_eligible(self):
        # T_frio_max == t_exec_pb(P_fast, B1) == 9.0 exactly. PB_elig is
        # defined with `<=`, so this must NOT be excluded by an off-by-one
        # at the boundary -- a real risk given the floating-point
        # equality involved (t_exec_pb is itself a derived, not a directly
        # read, parameter).
        scenario = cold_chain_exact_boundary()
        self.assertIn(("P_fast", "B1"), self.eligible_pairs(scenario, {"B1": 14.0}))

        _, route_times, status, values = self.run_pipeline(scenario)
        self.assertIn(status, ("optimal", "feasible"))
        assignments = self.assignments(values, scenario["P"], scenario["B"])
        self.assertEqual(assignments, {"B1": "P_fast"})

    def test_no_eligible_picker_makes_scip_report_infeasible(self):
        # Unlike model_21's test (which only checks the Python-side
        # eligible_pairs() preflight helper never solves stage 2), this
        # actually attempts the SCIP solve with an empty PB_elig for B1
        # and asserts the model itself concludes "infeasible" -- confirms
        # `assign_exactly_one_picker`'s domain restriction to PB_elig
        # produces a real, correctly-detected infeasibility rather than a
        # silently wrong or crashing model when no picker qualifies.
        scenario = cold_chain_infeasible_for_every_picker()
        self.assertEqual(self.eligible_pairs(scenario, {"B1": 14.0}), set())

        # run_pipeline(solve_stage2=False) already writes route_time_b.dat/
        # velocities.dat/frio.dat for us before returning -- no need to
        # rewrite them here, just solve stage 2 directly against them.
        self.run_pipeline(scenario, solve_stage2=False)
        stage2_status, _ = solve_zpl(STAGE2_ZPL_PATH, dat_dir=DAT_DIR)
        self.assertEqual(stage2_status, "infeasible")
