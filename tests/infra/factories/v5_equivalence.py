"""
v5 -> heuristic equivalence suite: run opp_aco_4 / opp_hc_4 on EXACTLY the
instances opp_v5_2_split's functional tests solve.

Why (2026-09-28 audit): most heuristic functional tests that share a name
with a v5 test wrap opp_aco_2 / opp_hc_2 tests that never set
model_dto.P, so they solve with a single default picker while the v5 test
(migrated from opp_v4, which takes P from the scenario) uses two -- 34 of
the 50 name-matched tests differed in the number of pickers, so their
objectives could not be compared. Instead of copying v5's data by hand
into heuristic tests, the instances are captured from v5's own tests:

1. tests/shared_scenarios/functional/export_v5_equivalence_scenarios.py
   (needs zimpl/SCIP) runs opp_v5_2_split's functional suite, captures
   every scenario dict right when it's written to the .dat files, and v5's
   final status/objective for it, into v5_equivalence_scenarios.json.
2. equivalence_case() builds, for a heuristic, one test per captured
   instance (test_v5eq__<v5 test method>[__<k>]) that solves it through
   tests/infra/factories/v5_scenario_adapter.py -- the same adapter the v5
   stress ports use -- and checks the outcome class (feasible vs
   infeasible) matches v5's. The objective lands in the results CSV via
   the solve registry, joinable with v5's CSV by stripping the prefix.
"""

import inspect
import json
import os
from collections import Counter, defaultdict

from tests.infra.cases.opp_test_case import OPPTestCase
from tests.infra.factories.v5_scenario_adapter import build_model_dto_and_params

FIXTURE_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "shared_scenarios", "functional", "v5_equivalence_scenarios.json",
))

METHOD_PREFIX = "test_v5eq__"

# Same defaults opp_v5_2_split applies to scenarios that predate picker speed
# and cold chain (tests/infra/zimpl/dat_files_builder.py, migrated_case.py).
DEFAULT_SPEED = 1.0
DEFAULT_T_FRIO_MAX = 1_000_000_000.0


# --- JSON encoding: sets and tuple-keyed dicts --------------------------------

def encode(value):
    if isinstance(value, (set, frozenset)):
        return {"__set__": sorted((encode(v) for v in value), key=repr)}
    if isinstance(value, tuple):
        return {"__tuple__": [encode(v) for v in value]}
    if isinstance(value, dict):
        if any(not isinstance(k, str) for k in value):
            return {"__dict_items__": [[encode(k), encode(v)] for k, v in value.items()]}
        return {k: encode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [encode(v) for v in value]
    return value


def decode(value):
    if isinstance(value, dict):
        if set(value) == {"__set__"}:
            return {decode(v) for v in value["__set__"]}
        if set(value) == {"__tuple__"}:
            return tuple(decode(v) for v in value["__tuple__"])
        if set(value) == {"__dict_items__"}:
            return {decode(k): decode(v) for k, v in value["__dict_items__"]}
        return {k: decode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [decode(v) for v in value]
    return value


def with_v5_defaults(scenario):
    """Fill V_p / T_frio_max the way opp_v5_2_split does when a scenario omits them."""
    scenario = dict(scenario)
    if not scenario.get("V_p"):
        scenario["V_p"] = {p: DEFAULT_SPEED for p in scenario["P"]}
    scenario.setdefault("T_frio_max", DEFAULT_T_FRIO_MAX)
    return scenario


def load_fixtures(path=FIXTURE_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# --- heuristic test factory ---------------------------------------------------

def _method_names(entries):
    counts = Counter(e["v5_test"] for e in entries)
    seen = defaultdict(int)
    for entry in entries:
        name = entry["v5_test"]
        seen[name] += 1
        suffix = f"__{seen[name]}" if counts[name] > 1 else ""
        yield METHOD_PREFIX + name + suffix, entry


def _make_test(entry, model_cls, dto_cls, configure_params):
    def test(self):
        if entry.get("fixed_assignment"):
            self.skipTest("v5 fixes the batch->picker assignment (X_pb) here; the heuristics can't take it")
        scenario = with_v5_defaults(decode(entry["scenario"]))
        model_dto, params = build_model_dto_and_params(scenario, dto_cls, seed=1)
        model_dto.start_time = self.start_time
        if configure_params:
            configure_params(params)

        raw = model_cls(model_dto).solve(params)
        status = raw[0] if isinstance(raw, tuple) else raw.status

        expected = entry["v5_status"]
        if expected in ("optimal", "feasible"):
            self.assertIn(status, ("optimal", "feasible"), f"v5 found a solution ({expected}); heuristic: {status}")
        elif expected == "infeasible":
            self.assertEqual(status, "infeasible", "v5 proved this instance infeasible")
        # Any other v5 outcome (timeout, limit) is inconclusive: nothing to compare the status to.

    test.__doc__ = f"Same instance as opp_v5_2_split's {entry['v5_test']} (v5: {entry['v5_status']}, obj {entry['v5_obj']})."
    return test


def equivalence_case(model_cls, dto_cls, configure_params=None, fixture_path=FIXTURE_PATH):
    """
    A TestCase class with one test per instance in the fixture, solved by
    `model_cls` with a `dto_cls` params DTO (seed 1; `configure_params`
    can adjust it, e.g. HC's iteration budget). Named TestV5Equivalence and
    registered in the calling module, so tests/run_suite.py can launch each
    test by its dotted id (same approach as migrated_case / family_case).
    """
    fixtures = load_fixtures(fixture_path)

    class TestV5Equivalence(OPPTestCase):
        pass

    for method_name, entry in _method_names(fixtures["instances"]):
        setattr(TestV5Equivalence, method_name, _make_test(entry, model_cls, dto_cls, configure_params))

    # Without the __qualname__ reset the test id would be
    # "...equivalence_case.<locals>.TestV5Equivalence...", which
    # tests/run_suite.py can't load by name.
    TestV5Equivalence.__qualname__ = "TestV5Equivalence"
    TestV5Equivalence.__module__ = inspect.currentframe().f_back.f_globals["__name__"]
    return TestV5Equivalence


# --- comparability ------------------------------------------------------------

def v5_waiting_batches(scenario, values, route_times, tolerance=1e-6):
    """
    Batches whose completion v5 reports LATER than its picker could have
    finished them: v5's v_pb >= t_exec_pb (not ==) lets it delay a batch to
    cut earliness -- "voluntary waiting", which the heuristics don't model.
    For each picker, its batches (X_pb = 1, with orders) are taken in
    completion order; batch b waits if v_pb[p, b] exceeds the previous
    batch's completion (0 for the first) plus t_exec_pb[p, b] =
    B_setup + B_picking * sum(C_n) + R_b_time[b] / V_p[p].
    """
    s = with_v5_defaults(scenario)
    if s["W_ea_ta"] * s["W_ea"] <= 0:
        # Earliness doesn't count: a later v_pb can't lower the objective,
        # so any slack is just the solver's arbitrary pick within an
        # indifferent range, not waiting that changes the result (e.g.
        # test_longer_single_mission_penalties' second instance, W_full =
        # W_ea = 0: v5 and the heuristics both reach 0).
        return []
    orders = {b: [n for n in s["N"] if s["Bn"].get((n, b), 0) > 0.5] for b in s["B"]}
    waits = []
    for p in sorted(s["P"]):
        mine = [b for b in s["B"] if values.get(f"X_pb${p}${b}", 0) > 0.5 and orders[b]]
        previous_end = 0.0
        for b in sorted(mine, key=lambda b: values.get(f"v_pb${p}${b}", 0.0)):
            t_exec = (
                s["B_setup"] + s["B_picking"] * sum(s["C_n"][n] for n in orders[b])
                + route_times.get(b, 0.0) / s["V_p"][p]
            )
            completion = values.get(f"v_pb${p}${b}", 0.0)
            if completion - (previous_end + t_exec) > tolerance:
                waits.append(b)
            previous_end = completion
    return sorted(waits)


def comparability(entry):
    """
    (comparable_status, comparable_objective, reason) for one exported
    instance -- the single rule every comparison document/plot should use:

    - timeout: v5 never concluded -> nothing to compare;
    - X_pb fixed by v5 -> the heuristics can't take that constraint;
    - infeasible: the outcome is comparable, there's no objective;
    - v5 waits voluntarily in some batch -> outcome comparable, objective
      not (v5's is lower by design, not by a better plan);
    - otherwise (v5 optimal, no waiting) -> both comparable.
    """
    status = entry["v5_status"]
    if status == "timeout":
        return False, False, "v5 no terminó (timeout)"
    if entry.get("fixed_assignment"):
        return False, False, "v5 fija la asignación batch-picker (X_pb); las heurísticas no la admiten"
    if status == "infeasible":
        return True, False, "infeasible: no hay objetivo que comparar"
    if entry.get("v5_waiting_batches"):
        return True, False, f"v5 usa espera voluntaria en {entry['v5_waiting_batches']}"
    if status == "optimal":
        return True, True, ""
    return False, False, f"estado de v5 no concluyente ({status})"
