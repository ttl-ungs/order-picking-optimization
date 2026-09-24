import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from models.opp_v5_2_split.utils.cold_chain_validation import COLD_CHAIN_TOLERANCE, invalid_speeds
from models.utils.solve_registry import get_last
from tests.infra.zimpl.dat_files_builder import build_dat_files
from tests.infra.zimpl.zpl_utils import extract_active_arcs, solve_zpl
from tests.opp_v5_1_mono.config import DAT_DIR, ZPL_PATH


class OPPTestCaseMono(unittest.TestCase):
    """Runs the OPP v5.1 monolithic model and exposes the same assertions as OPPTestCaseSplit.

    The helper methods below are the ones opp_v5_2_split's test base defines, so the
    tests ported from opp_v5_2_split keep their assertions untouched. The only
    difference is `run_pipeline`: there is a single solve instead of two
    stages, so the "stage 1 values" it returns are simply the full solution.
    """

    def run_pipeline(self, scenario):
        """Solve the monolithic model; returns (values, route_times, status, values).

        Kept with opp_v5_2_split's `run_pipeline` name and 4-tuple shape so the ported
        test bodies stay identical. `route_times` are the R_b_time values the
        model itself chose (opp_v5_2_split obtains them from its stage 1).
        """
        # V_p[p] is a divisor in the model's t_exec_pb; a speed of 0 divides by
        # zero at ZIMPL compile time and a negative one silently yields a
        # negative duration. Reject before ZIMPL ever sees it (same guard
        # OPPTestCaseSplit.run_pipeline applies).
        bad_speeds = invalid_speeds(scenario["V_p"])
        self.assertFalse(
            bad_speeds,
            f"V_p must be strictly positive for every picker; got non-positive speed for {sorted(bad_speeds)}",
        )

        # build_dat_files also writes velocities.dat and frio.dat from the
        # scenario's V_p / T_frio_max.
        build_dat_files(DAT_DIR, scenario)
        status, values = solve_zpl(ZPL_PATH, dat_dir=DAT_DIR)
        route_times = self.extract_route_times(values, scenario["B"])
        return values, route_times, status, values

    def extract_route_times(self, values, batches):
        result = {}
        for name, value in values.items():
            if name.lower().startswith("r_b_time$"):
                batch = name.split("$")[-1]
                if batch in batches:
                    result[batch] = value
        return result

    def assignments(self, values, pickers, batches):
        result = {}
        for name, value in values.items():
            if not name.lower().startswith("x_pb$") or value <= 0.5:
                continue
            _, picker, batch = name.split("$")
            if picker in pickers and batch in batches:
                result[batch] = picker
        return result

    def completion_times(self, values, pickers, batches):
        result = {}
        for name, value in values.items():
            if name.lower().startswith("v_pb$"):
                _, picker, batch = name.split("$")
                if picker in pickers and batch in batches:
                    result[(picker, batch)] = value
        return result

    def assert_routes_cover_requirements(self, values, scenario):
        arcs_by_batch = extract_active_arcs(values, scenario["B"])
        for batch, arcs in arcs_by_batch.items():
            self.assertTrue(arcs, f"{batch} has no route")
            self.assertEqual(sum(i == scenario["depot"] for i, _ in arcs), 1)
            self.assertEqual(sum(j == scenario["final"] for _, j in arcs), 1)
            required = {
                location for location in scenario["V"]
                if any(scenario["A_ni"][(order, location)] * scenario["Bn"][(order, batch)]
                       for order in scenario["N"])
            }
            visited = {node for arc in arcs for node in arc}
            self.assertTrue(required <= visited, f"{batch} misses {required - visited}")

    def assert_no_overlap(self, values, scenario, route_times):
        assignments = self.assignments(values, scenario["P"], scenario["B"])
        completions = self.completion_times(values, scenario["P"], scenario["B"])
        for batch, picker in assignments.items():
            duration = scenario["B_setup"] + scenario["B_picking"] * sum(
                scenario["C_n"][order] * scenario["Bn"][(order, batch)] for order in scenario["N"]
            ) + route_times[batch] / scenario["V_p"][picker]
            self.assertGreaterEqual(completions[(picker, batch)] + 1e-5, duration)

        for picker in scenario["P"]:
            intervals = []
            for batch, assigned_picker in assignments.items():
                if assigned_picker == picker:
                    end = completions[(picker, batch)]
                    duration = scenario["B_setup"] + scenario["B_picking"] * sum(
                        scenario["C_n"][order] * scenario["Bn"][(order, batch)] for order in scenario["N"]
                    ) + route_times[batch] / scenario["V_p"][picker]
                    intervals.append((end - duration, end, batch))
            intervals.sort()
            for (_, end, first), (start, _, second) in zip(intervals, intervals[1:]):
                self.assertGreaterEqual(start + 1e-5, end, f"{first} overlaps {second} on {picker}")

    @staticmethod
    def eligible_pairs(scenario, route_times):
        """Replicates the (picker, batch) eligibility under the cold-chain limit, tolerance included."""
        pairs = set()
        for picker in scenario["P"]:
            for batch in scenario["B"]:
                fixed_time = scenario["B_setup"] + scenario["B_picking"] * sum(
                    scenario["C_n"][order] * scenario["Bn"][(order, batch)]
                    for order in scenario["N"]
                )
                t_exec = fixed_time + route_times[batch] / scenario["V_p"][picker]
                if t_exec <= scenario["T_frio_max"] + COLD_CHAIN_TOLERANCE:
                    pairs.add((picker, batch))
        return pairs

    @staticmethod
    def objective_value():
        """Objective of the last solve (the model's only one)."""
        last = get_last()
        return last.params.get("obj_val") if last is not None else None
