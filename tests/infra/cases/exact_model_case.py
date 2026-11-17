"""Base class of the tests of the exact models (monolithic and Split).

Both exact models write the same variables (x_pb, c_pb, r_b, z_ijb, ...), so
the assertions that read a solution are the same for both and live here. What
changes from one model to the other is where the .dat files are written
(`dat_dir`) and how the model is solved (`solve`, `run_pipeline`): each model's
adapter (OPPTestCaseMono, OPPTestCaseSplit) provides those.
"""

from models.utils.cold_chain_validation import COLD_CHAIN_TOLERANCE
from models.utils.solve_registry import get_last
from tests.infra.cases.opp_test_case import OPPTestCase
from tests.infra.zimpl.zpl_utils import extract_active_arcs


class ExactModelTestCase(OPPTestCase):
    """Solves an instance with an exact model and asserts on its solution."""

    # Directory where the instance's .dat files are written. Set by the adapter.
    dat_dir = None

    def solve(self, params):
        """Solve the instance whose .dat files were just written in `dat_dir`.

        Returns (status, values): the status of the solve and the value of every
        variable, named like in the model (for example "x_pb$P1$B1").
        """
        raise NotImplementedError("Each exact model's adapter implements solve().")

    def run_pipeline(self, scenario):
        """Write the scenario's .dat files and solve it.

        Returns (values, route_times, status, stage_2_values), where
        `route_times` are the r_b of each batch.
        """
        raise NotImplementedError("Each exact model's adapter implements run_pipeline().")

    def extract_route_times(self, values, batches):
        result = {}
        for name, value in values.items():
            if name.lower().startswith("r_b$"):
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
            if name.lower().startswith("c_pb$"):
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
                if any(scenario["A_ni"][(order, location)] * scenario["B_nb"][(order, batch)]
                       for order in scenario["N"])
            }
            visited = {node for arc in arcs for node in arc}
            self.assertTrue(required <= visited, f"{batch} misses {required - visited}")

    def assert_no_overlap(self, values, scenario, route_times):
        assignments = self.assignments(values, scenario["P"], scenario["B"])
        completions = self.completion_times(values, scenario["P"], scenario["B"])
        for batch, picker in assignments.items():
            duration = scenario["T_setup"] + scenario["T_pick"] * sum(
                scenario["C_n"][order] * scenario["B_nb"][(order, batch)] for order in scenario["N"]
            ) + route_times[batch] / scenario["V_p"][picker]
            self.assertGreaterEqual(completions[(picker, batch)] + 1e-5, duration)

        for picker in scenario["P"]:
            intervals = []
            for batch, assigned_picker in assignments.items():
                if assigned_picker == picker:
                    end = completions[(picker, batch)]
                    duration = scenario["T_setup"] + scenario["T_pick"] * sum(
                        scenario["C_n"][order] * scenario["B_nb"][(order, batch)] for order in scenario["N"]
                    ) + route_times[batch] / scenario["V_p"][picker]
                    intervals.append((end - duration, end, batch))
            intervals.sort()
            for (_, end, first), (start, _, second) in zip(intervals, intervals[1:]):
                self.assertGreaterEqual(start + 1e-5, end, f"{first} overlaps {second} on {picker}")

    def assert_workload_balance(self, var_values, P, B, max_difference=1):
        picker_workload = {p: 0 for p in P}
        for key, val in var_values.items():
            if key.lower().startswith("x_pb") and val > 0.5:
                for p in P:
                    if p in key:
                        picker_workload[p] += 1
        workloads = list(picker_workload.values())
        if workloads:
            self.assertLessEqual(max(workloads) - min(workloads), max_difference, "Desbalanceo de carga")

    def assert_no_time_overlap(self, var_values, P, B):
        """Same check as assert_no_overlap, for a solution that exports each task's duration u_pb."""
        x_pb, c_pb, u_pb = {}, {}, {}
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
                elif k.startswith("u_pb"):
                    u_pb[(p, b)] = val
        for p in P:
            tasks = sorted(
                (c_pb.get((p, b), 0) - u_pb.get((p, b), 0), c_pb.get((p, b), 0), b)
                for b in B if x_pb.get((p, b), 0) > 0.5
            )
            for i in range(len(tasks) - 1):
                self.assertGreaterEqual(tasks[i + 1][0], tasks[i][1] - 1e-4, f"Solapamiento temporal en {p}")

    @staticmethod
    def eligible_pairs(scenario, route_times):
        """The (picker, batch) pairs whose execution fits the cold-chain limit, tolerance included."""
        pairs = set()
        for picker in scenario["P"]:
            for batch in scenario["B"]:
                fixed_time = scenario["T_setup"] + scenario["T_pick"] * sum(
                    scenario["C_n"][order] * scenario["B_nb"][(order, batch)]
                    for order in scenario["N"]
                )
                t_exec = fixed_time + route_times[batch] / scenario["V_p"][picker]
                if t_exec <= scenario["T_cold"] + COLD_CHAIN_TOLERANCE:
                    pairs.add((picker, batch))
        return pairs

    @staticmethod
    def objective_value():
        """Objective of the last solve, which carries the whole objective."""
        last = get_last()
        return last.params.get("obj_val") if last is not None else None
