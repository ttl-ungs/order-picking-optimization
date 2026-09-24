import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tests.infra.zimpl.dat_files_builder import build_dat_files, write_indexed_dat, write_scalar_dat
from models.opp_v5_2_split.utils.cold_chain_validation import (
    COLD_CHAIN_TOLERANCE, batches_without_eligible_picker, invalid_speeds,
)
from models.utils.solve_registry import get_last
from tests.opp_v5_2_split.config import DAT_DIR, STAGE1_ZPL_PATH, STAGE2_ZPL_PATH
from tests.opp_v5_2_split.stage1_decomposition import solve_stage1_decomposed
from tests.infra.zimpl.zpl_utils import extract_active_arcs, solve_zpl


class OPPTestCaseSplit(unittest.TestCase):
    """Runs both OPP v5 stages and exposes assertions for their contract."""

    def run_pipeline(self, scenario, solve_stage2=True):
        # V_p[p] is a divisor in opp_model_v5_2_split_stage2_scheduling.zpl's t_exec_pb (t_exec_pb
        # = tiempo_fijo[b] + R_b_time[b] / V_p[p]), evaluated eagerly by
        # ZIMPL for every (p, b) pair as soon as the .dat is read -- a speed
        # of exactly 0 divides by zero there (no graceful "infeasible", it's
        # a plain parameter expression, not a constraint); a negative one
        # silently yields a negative t_exec_pb that would look "eligible"
        # for any T_frio_max. Reject before ZIMPL ever sees it (2026-09-10
        # audit finding), same pattern as the stuck_batches short-circuit below.
        # It has to run before build_dat_files too: its M_seq estimate divides
        # by the slowest speed, so a 0 crashed there first (found 2026-09-24).
        bad_speeds = invalid_speeds(scenario["V_p"])
        self.assertFalse(
            bad_speeds,
            f"V_p must be strictly positive for every picker; got non-positive speed for {sorted(bad_speeds)}",
        )

        build_dat_files(DAT_DIR, scenario)
        # Decomposed into one solve per batch instead of one joint solve
        # for every batch (see stage1_decomposition.py's module docstring
        # for the measured speedup) -- STAGE1_ZPL_PATH itself is unchanged.
        stage1_status, stage1_values = solve_stage1_decomposed(DAT_DIR)
        self.assertIn(stage1_status, ("optimal", "feasible"), "Stage 1 did not solve")

        route_times = self.extract_route_times(stage1_values, scenario["B"])
        self.assertEqual(set(route_times), set(scenario["B"]), "Stage 1 did not export every batch time")

        write_indexed_dat(os.path.join(DAT_DIR, "route_time_b.dat"), route_times)
        write_indexed_dat(os.path.join(DAT_DIR, "velocities.dat"), scenario["V_p"])
        write_scalar_dat(os.path.join(DAT_DIR, "frio.dat"), scenario["T_frio_max"])

        if not solve_stage2:
            return stage1_values, route_times, None, None

        # Fix (2026-09-01, code audit): a batch with zero eligible pickers
        # under the cold-chain limit makes opp_model_v5_2_split_stage2_scheduling.zpl's
        # assign_exactly_one_picker sum over an empty PB_elig slice for
        # that batch, which ZIMPL rejects at COMPILE time (RuntimeError).
        # Short-circuit here instead of letting that crash surface
        # (same pattern as opp_v4's input_validation.py pre-checks in solve_zpl).
        stuck_batches = batches_without_eligible_picker(
            scenario["P"], scenario["B"], scenario["N"], scenario["C_n"],
            scenario["Bn"], scenario["B_setup"], scenario["B_picking"],
            route_times, scenario["V_p"], scenario["T_frio_max"],
        )
        if stuck_batches:
            return stage1_values, route_times, "infeasible", {}

        stage2_status, stage2_values = solve_zpl(STAGE2_ZPL_PATH, dat_dir=DAT_DIR)
        return stage1_values, route_times, stage2_status, stage2_values

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
        """Replicates the PB_elig definition before compiling Stage 2, tolerance included."""
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
        """Objective of the last solve: Stage 2, which carries the whole objective."""
        last = get_last()
        return last.params.get("obj_val") if last is not None else None
