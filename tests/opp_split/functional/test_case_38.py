import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from tests.infra.zimpl.dat_files_builder import build_dat_files
from tests.shared_scenarios.functional.two_stage_scenarios import two_dead_end_aisles
from tests.opp_split.config import DAT_DIR
from tests.opp_split.opp_split_test_case import OPPTestCaseSplit
from tests.opp_split.stage1_decomposition import solve_stage1_decomposed


class TestOPPSplitSimplePathLimit(OPPTestCaseSplit):
    """Documents a limit of the routing formulation, not a business rule.

    one_input_arc_per_node / one_output_arc_per_node (`<= 1`) make every route a
    simple path, so a pick list that forces a walk through the same vertex
    twice has no route -- even though a picker could walk it. Found on
    2026-09-23 on small grids a batch nearly saturates. If the `<= 1` limit is
    ever relaxed, this test's expectation flips to a feasible route.
    """

    def test_route_that_must_revisit_a_vertex_is_infeasible(self):
        """Picking in both dead-end aisles needs D -> H -> L1 -> H -> L2 -> H -> F,
        entering the hub H three times."""
        build_dat_files(DAT_DIR, two_dead_end_aisles())
        status, _ = solve_stage1_decomposed(DAT_DIR)
        self.assertEqual(status, "infeasible")
