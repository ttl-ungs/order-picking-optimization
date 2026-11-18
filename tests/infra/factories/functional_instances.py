"""
The Split's reference for the comparability registry: every instance its
functional cases solve, with its final status and objective.

tests/shared_scenarios/functional/export_functional_instances.py (needs zimpl
and SCIP) runs opp_split's functional suite and saves, in
functional_instances.json, every scenario as it is written to the .dat files.
experiments/comparison/comparability.py reads it through case_instances() and
applies comparability() to each instance. The heuristics do not read it: they
run the functional cases themselves (tests/infra/cases/heuristic_model_case.py).
"""

import json
import os
from collections import Counter, defaultdict


FIXTURE_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "shared_scenarios", "functional", "functional_instances.json",
))

# The defaults opp_split applies to a scenario without picker speeds or a
# cold-chain limit (tests/infra/zimpl/dat_files_builder.py).
DEFAULT_SPEED = 1.0
DEFAULT_T_COLD = 1_000_000_000.0


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


def with_split_defaults(scenario):
    """Fill V_p / T_cold the way opp_split does when a scenario omits them."""
    scenario = dict(scenario)
    if not scenario.get("V_p"):
        scenario["V_p"] = {p: DEFAULT_SPEED for p in scenario["P"]}
    scenario.setdefault("T_cold", DEFAULT_T_COLD)
    return scenario


def load_fixtures(path=FIXTURE_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# --- instances ------------------------------------------------------------------

def case_instances(entries):
    """(case, test name, entry) for every captured instance.

    The case is the class that defines the Split's test (`Case24ColdChain`, ...) and the test name
    is the Split's own method name, so an instance has the same id as in the exact models. A test
    with several instances inside one case gets a `__1`, `__2` suffix.
    """
    counts = Counter((e["split_case"], e["split_test"]) for e in entries)
    seen = defaultdict(int)
    for entry in entries:
        key = (entry["split_case"], entry["split_test"])
        seen[key] += 1
        suffix = f"__{seen[key]}" if counts[key] > 1 else ""
        yield key[0], key[1] + suffix, entry


# --- comparability ------------------------------------------------------------

def split_waiting_batches(scenario, values, route_times, tolerance=1e-6):
    """
    Batches the Split reports as completed later than their picker could have
    finished them: its c_pb >= T_exec_pb (not ==) lets it delay a batch to
    cut earliness ("voluntary waiting"), which the heuristics do not do. For
    each picker, its batches are taken in completion order; batch b waits if
    c_pb[p, b] exceeds the previous batch's completion (0 for the first)
    plus T_exec_pb[p, b].
    """
    s = with_split_defaults(scenario)
    if s["W_pen"] * s["W_e"] <= 0:
        # Without an earliness weight a later c_pb cannot lower the objective:
        # any slack is the solver's arbitrary pick, not waiting that changes
        # the result.
        return []
    orders = {b: [n for n in s["N"] if s["B_nb"].get((n, b), 0) > 0.5] for b in s["B"]}
    waits = []
    for p in sorted(s["P"]):
        mine = [b for b in s["B"] if values.get(f"x_pb${p}${b}", 0) > 0.5 and orders[b]]
        previous_end = 0.0
        for b in sorted(mine, key=lambda b: values.get(f"c_pb${p}${b}", 0.0)):
            t_exec = (
                s["T_setup"] + s["T_pick"] * sum(s["C_n"][n] for n in orders[b])
                + route_times.get(b, 0.0) / s["V_p"][p]
            )
            completion = values.get(f"c_pb${p}${b}", 0.0)
            if completion - (previous_end + t_exec) > tolerance:
                waits.append(b)
            previous_end = completion
    return sorted(waits)


def comparability(entry):
    """
    (comparable_status, comparable_objective, reason) for one exported
    instance: the rule every comparison uses.

    - timeout: the Split never concluded, nothing to compare;
    - x_pb fixed by the Split: the heuristics cannot take that constraint;
    - infeasible: the outcome is comparable, there is no objective;
    - the Split waits voluntarily in some batch: the outcome is comparable,
      the objective is not (the Split's is lower by design);
    - otherwise (the Split is optimal and does not wait): both are comparable.
    """
    status = entry["split_status"]
    if status == "timeout":
        return False, False, "el Split no terminó (timeout)"
    if entry.get("fixed_assignment"):
        return False, False, "el Split fija la asignación batch-picker (x_pb); las heurísticas no la admiten"
    if status == "infeasible":
        return True, False, "infeasible: no hay objetivo que comparar"
    if entry.get("split_waiting_batches"):
        return True, False, f"el Split usa espera voluntaria en {entry['split_waiting_batches']}"
    if status == "optimal":
        return True, True, ""
    return False, False, f"estado del Split no concluyente ({status})"
