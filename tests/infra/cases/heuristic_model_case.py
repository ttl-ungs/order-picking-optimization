"""Base of the heuristics' adapters (OPP-HC, OPP-ACO) for the shared cases.

The functional cases of tests/functional_cases are written against
ExactModelTestCase: they write the instance with build_dat_files() and call
solve(), or hand a scenario to run_pipeline(), and then read the solution as
the variables of the exact models (x_pb, c_pb, u_pb, c_b, r_b, z_ijb, ta_n,
ea_n). An adapter of this class solves that same instance with a heuristic and
returns its solution under those names, so the cases run unchanged on the
heuristics: the scenario and the assertions are the same, only the model is
not.
"""

import atexit
import shutil
import tempfile

from models.utils.cold_chain_validation import invalid_speeds
from observer.observer import Observer
from tests.infra.cases.exact_model_case import ExactModelTestCase
from tests.infra.factories.scenario_adapter import build_model_dto_and_params
from tests.infra.zimpl.dat_files_builder import DEFAULT_T_COLD, last_scenario

# The cases write their .dat files here before calling solve(). The heuristics
# do not read them: solve() takes the scenario build_dat_files() just wrote.
_DAT_DIR = tempfile.mkdtemp(prefix="opp_heuristic_dat_")
atexit.register(shutil.rmtree, _DAT_DIR, True)


class SolutionInfoCapture(Observer):
    """Keeps the solution_info a heuristic notifies at the end of solve()."""

    def __init__(self):
        self.solution_info = {}

    def update(self, solution_info: dict, **kwargs):
        self.solution_info = solution_info


class HeuristicModelTestCase(ExactModelTestCase):
    """Solves the instance of a shared case with a heuristic. Each heuristic's
    adapter sets the solver class and its parameters DTO."""

    model_cls = None
    dto_cls = None
    dat_dir = _DAT_DIR
    waits_voluntarily = False

    def solve(self, params=None):
        """Solve the instance whose .dat files the case just wrote.

        Returns (status, values) like the exact models. The speeds and the
        cold-chain limit are the ones the .dat files carry: the scenario's, or
        V_p = 1.0 and a limit that never binds when it defines none.
        """
        scenario = last_scenario()
        self.assertIsNotNone(scenario, "the case did not write its instance with build_dat_files()")
        scenario = dict(scenario)
        scenario["V_p"] = scenario.get("V_p") or {picker: 1.0 for picker in scenario["P"]}
        scenario.setdefault("T_cold", DEFAULT_T_COLD)
        return self._solve_scenario(scenario)

    def run_pipeline(self, scenario):
        """Solve the scenario; returns (values, route_times, status, values),
        the shape of the exact models' run_pipeline. `route_times` are the r_b
        of the heuristic's routes."""
        # The same pre-check as the exact models' adapters, so that case 36c
        # asserts the same thing on every model.
        bad_speeds = invalid_speeds(scenario["V_p"])
        self.assertFalse(
            bad_speeds,
            f"V_p must be strictly positive for every picker; got non-positive speed for {sorted(bad_speeds)}",
        )
        status, values = self._solve_scenario(scenario)
        route_times = self.extract_route_times(values, scenario["B"])
        return values, route_times, status, values

    def _solve_scenario(self, scenario):
        model_dto, params = build_model_dto_and_params(scenario, self.dto_cls)
        model_dto.start_time = self.start_time
        model = self.model_cls(model_dto)
        capture = SolutionInfoCapture()
        model.attach(capture)
        status, _ = model.solve(params)
        if status not in ("optimal", "feasible"):
            return status, {}
        return status, self._as_model_variables(scenario, capture.solution_info)

    @staticmethod
    def _as_model_variables(scenario, solution_info):
        """The heuristic's solution as the exact models' variables, named like
        solve_zpl() names them ("x_pb$P1$B1")."""
        assignment = solution_info["picker_assignments"]
        completions = solution_info["batch_completions"]
        durations = solution_info["batch_times"]
        values = {}

        for batch in scenario["B"]:
            picker_of_batch = assignment.get(batch)
            for picker in scenario["P"]:
                assigned = picker == picker_of_batch
                values[f"x_pb${picker}${batch}"] = 1.0 if assigned else 0.0
                values[f"c_pb${picker}${batch}"] = completions[batch] if assigned else 0.0
                values[f"u_pb${picker}${batch}"] = durations[batch] if assigned else 0.0
            values[f"c_b${batch}"] = completions.get(batch, 0.0)

            # r_b is the part of T_exec_pb the picker's speed divides:
            # T_exec_pb = fixed time + r_b / V_p.
            fixed_time = scenario["T_setup"] + scenario["T_pick"] * sum(
                scenario["C_n"][order] * scenario["B_nb"].get((order, batch), 0) for order in scenario["N"]
            )
            route_time = 0.0
            if picker_of_batch is not None:
                route_time = (durations[batch] - fixed_time) * scenario["V_p"][picker_of_batch]
            values[f"r_b${batch}"] = route_time

            route = solution_info["routes"].get(batch) or []
            if route:
                path = [scenario["depot"], *route, scenario["final"]]
                for i, j in zip(path, path[1:]):
                    values[f"z_ijb${i}${j}${batch}"] = 1.0

        for order in scenario["N"]:
            values[f"ta_n${order}"] = solution_info["tardiness"].get(order, 0.0)
            values[f"ea_n${order}"] = solution_info["earliness"].get(order, 0.0)
        return values
