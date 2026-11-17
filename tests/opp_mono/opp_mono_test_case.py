import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from models.utils.cold_chain_validation import invalid_speeds
from tests.infra.cases.exact_model_case import ExactModelTestCase
from tests.infra.zimpl.dat_files_builder import build_dat_files
from tests.infra.zimpl.zpl_utils import solve_zpl
from tests.opp_mono.config import DAT_DIR, ZPL_PATH


class OPPTestCaseMono(ExactModelTestCase):
    """Adapter of the monolithic model: solves routing, assignment and sequencing in a single model."""

    dat_dir = DAT_DIR

    def solve(self, params):
        return solve_zpl(ZPL_PATH, dat_dir=self.dat_dir, params=params)

    def run_pipeline(self, scenario):
        """Solve the monolithic model; returns (values, route_times, status, values).

        There is a single solve, so the values of "the first stage" and of "the
        second stage" are the whole solution; the 4-tuple keeps the shape of
        OPPTestCaseSplit.run_pipeline so the same case runs on both models.
        `route_times` are the r_b values the model itself chose.
        """
        # V_p[p] is a divisor in the model's T_exec_pb; a speed of 0 divides by
        # zero at ZIMPL compile time and a negative one silently yields a
        # negative duration. Reject before ZIMPL ever sees it (same guard
        # OPPTestCaseSplit.run_pipeline applies).
        bad_speeds = invalid_speeds(scenario["V_p"])
        self.assertFalse(
            bad_speeds,
            f"V_p must be strictly positive for every picker; got non-positive speed for {sorted(bad_speeds)}",
        )

        # build_dat_files also writes velocities.dat and cold.dat from the
        # scenario's V_p / T_cold.
        build_dat_files(self.dat_dir, scenario)
        status, values = solve_zpl(ZPL_PATH, dat_dir=self.dat_dir)
        route_times = self.extract_route_times(values, scenario["B"])
        return values, route_times, status, values
