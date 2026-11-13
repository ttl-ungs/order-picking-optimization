import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tests.infra.zimpl.dat_files_builder import build_dat_files, write_indexed_dat, write_scalar_dat
from models.opp_split.utils.cold_chain_validation import (
    batches_without_eligible_picker, invalid_speeds,
)
from dtos.opp.solve_result import SolveResult
from models.utils.solve_registry import get_last, register as register_solve
from tests.infra.cases.exact_model_case import ExactModelTestCase
from tests.opp_split.config import DAT_DIR, STAGE1_ZPL_PATH, STAGE2_ZPL_PATH
from tests.opp_split.stage1_decomposition import solve_stage1_decomposed
from tests.infra.zimpl.zpl_utils import solve_zpl


def _read_names(path):
    """The names (batches or pickers) listed one per line in a .dat file."""
    with open(path, encoding="utf-8") as f:
        return {line.strip().strip('"') for line in f if line.strip()}


class OPPTestCaseSplit(ExactModelTestCase):
    """Adapter of the Split model: Stage 1 routes each batch, Stage 2 assigns and sequences."""

    dat_dir = DAT_DIR

    def solve(self, params):
        """Solve both stages on the instance whose .dat files a case just wrote.

        The cases that call this write the instance without picker speeds or a
        cold-chain limit, so every picker runs at the reference speed and the
        cold-chain limit is disabled. Returns (status, values), with the values of
        both stages together.
        """
        # Decomposed into one solve per batch instead of one joint solve for
        # every batch (see stage1_decomposition.py's module docstring for the
        # measured speedup) -- STAGE1_ZPL_PATH itself is unchanged. `params`
        # (capacity/duplicate-assignment pre-checks, CSV metadata) isn't
        # threaded into the per-batch solves; it's still applied at the Stage
        # 2 call below with the untouched full scenario, so a genuinely
        # invalid input is still caught -- just there instead of here.
        stage1_status, stage1_values = solve_stage1_decomposed(self.dat_dir)
        if stage1_status not in ("optimal", "feasible"):
            return stage1_status, stage1_values

        batches = _read_names(os.path.join(self.dat_dir, "data_B.dat"))
        pickers = _read_names(os.path.join(self.dat_dir, "data_P.dat"))

        route_times = self.extract_route_times(stage1_values, batches)
        write_indexed_dat(os.path.join(self.dat_dir, "route_time_b.dat"), route_times)
        write_indexed_dat(os.path.join(self.dat_dir, "velocities.dat"), {picker: 1.0 for picker in pickers})
        write_scalar_dat(os.path.join(self.dat_dir, "cold.dat"), 1_000_000_000.0)

        # What assert_no_time_overlap needs to recompute each task's duration.
        self._route_times = route_times
        self._solve_params = params or {}

        stage2_status, stage2_values = solve_zpl(STAGE2_ZPL_PATH, dat_dir=self.dat_dir, params=params)
        # The saved solution (WRITE_SOLUTIONS) needs Stage 1 too: Stage 2 only
        # sees the routes' times, not the routes themselves.
        record = getattr(get_last(), "solution_record", None)
        if record is not None:
            record.add_stage1_values(stage1_values)
        return stage2_status, {**stage1_values, **stage2_values}

    def assert_no_time_overlap(self, var_values, P, B):
        """Check that no picker's batches overlap in time, from the solve() that just ran.

        Stage 2 has no u_pb variable (the duration of each task is the
        parameter T_exec_pb), so the duration is recomputed from the route
        times: fixed_time(b) + route_time(b) / V_p[picker], where V_p is 1.0 for
        every picker in solve().
        """
        route_times = getattr(self, "_route_times", {})
        params = getattr(self, "_solve_params", {})
        T_setup = params.get("T_setup", 0.0)
        T_pick = params.get("T_pick", 0.0)
        C_n = params.get("C_n", {}) or {}
        B_nb = params.get("B_nb", {}) or {}

        def duration(batch):
            orders_in_batch = [n for (n, b), assigned in B_nb.items() if b == batch and assigned]
            fixed_time = T_setup + T_pick * sum(C_n.get(n, 0.0) for n in orders_in_batch)
            return fixed_time + route_times.get(batch, 0.0)

        x_pb, c_pb = {}, {}
        for key, val in var_values.items():
            k = key.lower()
            p_match = [p for p in P if p in key]
            b_match = [b for b in B if b in key]
            if p_match and b_match:
                p, b = p_match[0], b_match[0]
                if k.startswith("x_pb"):
                    x_pb[(p, b)] = val
                elif k.startswith("c_pb"):
                    c_pb[(p, b)] = val

        for p in P:
            tasks = sorted(
                (c_pb.get((p, b), 0) - duration(b), c_pb.get((p, b), 0), b)
                for b in B if x_pb.get((p, b), 0) > 0.5
            )
            for i in range(len(tasks) - 1):
                self.assertGreaterEqual(
                    tasks[i + 1][0], tasks[i][1] - 1e-4, f"Solapamiento temporal en {p}"
                )

    def run_pipeline(self, scenario, solve_stage2=True):
        # V_p[p] is a divisor in opp_split_stage2_scheduling.zpl's T_exec_pb (T_exec_pb
        # = F_b[b] + R_b[b] / V_p[p]), evaluated eagerly by
        # ZIMPL for every (p, b) pair as soon as the .dat is read -- a speed
        # of exactly 0 divides by zero there (no graceful "infeasible", it's
        # a plain parameter expression, not a constraint); a negative one
        # silently yields a negative T_exec_pb that would look "eligible"
        # for any T_cold. Reject before ZIMPL ever sees it (2026-09-10
        # audit finding), same pattern as the stuck_batches short-circuit below.
        # It has to run before build_dat_files too: its M_seq estimate divides
        # by the slowest speed, so a 0 crashed there first (found 2026-09-24).
        bad_speeds = invalid_speeds(scenario["V_p"])
        self.assertFalse(
            bad_speeds,
            f"V_p must be strictly positive for every picker; got non-positive speed for {sorted(bad_speeds)}",
        )

        build_dat_files(self.dat_dir, scenario)
        # Decomposed into one solve per batch instead of one joint solve
        # for every batch (see stage1_decomposition.py's module docstring
        # for the measured speedup) -- STAGE1_ZPL_PATH itself is unchanged.
        stage1_status, stage1_values = solve_stage1_decomposed(self.dat_dir)
        self.assertIn(stage1_status, ("optimal", "feasible"), "Stage 1 did not solve")

        route_times = self.extract_route_times(stage1_values, scenario["B"])
        self.assertEqual(set(route_times), set(scenario["B"]), "Stage 1 did not export every batch time")

        write_indexed_dat(os.path.join(self.dat_dir, "route_time_b.dat"), route_times)
        write_indexed_dat(os.path.join(self.dat_dir, "velocities.dat"), scenario["V_p"])
        write_scalar_dat(os.path.join(self.dat_dir, "cold.dat"), scenario["T_cold"])

        if not solve_stage2:
            return stage1_values, route_times, None, None

        # Fix (2026-09-01, code audit): a batch with zero eligible pickers
        # under the cold-chain limit makes opp_split_stage2_scheduling.zpl's
        # assign_exactly_one_picker sum over an empty PB_elig slice for
        # that batch, which ZIMPL rejects at COMPILE time (RuntimeError).
        # Short-circuit here instead of letting that crash surface
        # (same pattern as input_validation.py's pre-checks in solve_zpl).
        stuck_batches = batches_without_eligible_picker(
            scenario["P"], scenario["B"], scenario["N"], scenario["C_n"],
            scenario["B_nb"], scenario["T_setup"], scenario["T_pick"],
            route_times, scenario["V_p"], scenario["T_cold"],
        )
        if stuck_batches:
            # Register the outcome of the pipeline itself: otherwise the
            # runner's "last solve" is Stage 1's last batch, whose obj_val
            # (a route time) ends up in the CSV as if it were the objective.
            register_solve(SolveResult(
                status="infeasible",
                output={},
                elapsed=0.0,
                params={
                    "obj_val": None,
                    "debug_output": "INFEASIBLE: no eligible picker under the cold chain for "
                    + ", ".join(sorted(stuck_batches)),
                },
            ))
            return stage1_values, route_times, "infeasible", {}

        stage2_status, stage2_values = solve_zpl(STAGE2_ZPL_PATH, dat_dir=self.dat_dir)
        # The saved solution (WRITE_SOLUTIONS) needs Stage 1 too: Stage 2
        # only sees the routes' times, not the routes themselves.
        record = getattr(get_last(), "solution_record", None)
        if record is not None:
            record.add_stage1_values(stage1_values)
        return {**stage1_values, **stage2_values}, route_times, stage2_status, stage2_values
