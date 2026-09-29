"""Write/read a heuristic's solution record (instance + solution) as JSON.

One file per test, written by the test runner when WRITE_SOLUTIONS is set
(tests/infra/execution/runner.py) and read back by verification/ to re-check
the solution against opp_v5_1_mono without re-running the heuristic.

Format (format_version 1), every id (order, batch, picker, vertex) stored as
a string -- ZIMPL reads them as strings anyway (dat_files_builder quotes
every element), and it keeps JSON's string-only object keys from silently
turning an int vertex id into a different key than the same id in a list:

    {
      "format_version": 1,
      "model": "opp_hc_4",
      "test": "<unittest id>",
      "instance": {
        "N": [...], "V": [...], "P": [...], "B": [...],
        "depot": "...", "final": "...",
        "E": [[i, j, D_ij], ...],
        "W_c", "W_pen", "W_e", "W_t",
        "T_travel", "T_setup", "T_pick", "C_v", "M",   (scalars, may be null)
        "C_n": [[n, value], ...], "T_due_n": [[n, value], ...],
        "S_i": [[i, value], ...],
        "A_ni": [[n, i, value], ...],   (non-zero entries only)
        "B_nb": [[n, b, value], ...],     (non-zero entries only)
        "V_p": [[p, speed], ...],       (every picker; missing ones as 1.0,
                                         the models' own default)
        "T_cold": float,            (Infinity when disabled)
        "start_time": float, "Seed": int | null
      },
      "solution": {
        "status", "objective_value",
        "routes": [[b, [stops...]], ...],   (stops strictly between depot and final)
        "picker_sequences": [[p, [b...]], ...],   (execution order per picker)
        "batch_times": [[b, t_exec], ...],
        "batch_completions": [[b, c_b], ...],
        "tardiness": [[n, ta], ...], "earliness": [[n, ea], ...]
      }
    }
"""

import json
import os

FORMAT_VERSION = 1


def _pairs(mapping):
    return [[str(k), v] for k, v in (mapping or {}).items()]


def _nonzero_triples(mapping):
    return [[str(k1), str(k2), v] for (k1, k2), v in (mapping or {}).items() if v]


def _picker_sequences(solution_info, pickers):
    """Execution order per picker. The models fill batch_completions by
    walking each picker's sequence in order, so dict insertion order per
    picker IS the sequence (not re-derived by sorting completion times,
    which would be ambiguous for zero-duration batches)."""
    assignments = solution_info.get("picker_assignments", {})
    sequences = {str(p): [] for p in pickers}
    for batch in solution_info.get("batch_completions", {}):
        sequences.setdefault(str(assignments[batch]), []).append(str(batch))
    return [[p, seq] for p, seq in sequences.items()]


def solution_record_to_dict(record, test_id):
    """Serialize a SolutionRecordDTO (dtos/opp/solution_record_dto.py)."""
    params = record.params
    graph = record.location_graph
    speeds = params.V_p or {}
    info = record.solution_info

    instance = {
        "N": [str(n) for n in record.N],
        "V": [str(v) for v in graph.get_vertices()],
        "P": [str(p) for p in record.P],
        "B": [str(b) for b in record.B],
        "depot": str(graph.get_depot()),
        "final": str(graph.get_final()),
        "E": [[str(i.location_id), str(j.location_id), d] for (i, j), d in graph.distances.items()],
        "W_c": params.W_c,
        "W_pen": params.W_pen,
        "W_e": params.W_e,
        "W_t": params.W_t,
        "T_travel": params.T_travel,
        "T_setup": params.T_setup,
        "T_pick": params.T_pick,
        "C_v": params.C_v,
        "M": params.M,
        "C_n": _pairs(params.C_n if isinstance(params.C_n, dict) else {}),
        "T_due_n": _pairs(params.T_due_n),
        "S_i": _pairs(params.S if isinstance(params.S, dict) else {}),
        "A_ni": _nonzero_triples(params.A),
        "B_nb": _nonzero_triples(params.B_nb),
        "V_p": [[str(p), float(speeds.get(p, 1.0))] for p in record.P],
        "T_cold": float(params.T_cold),
        "start_time": record.start_time,
        "Seed": params.Seed,
    }
    solution = {
        "status": info.get("status"),
        "objective_value": info.get("objective_value"),
        "routes": [[str(b), [str(v) for v in (route or [])]] for b, route in info.get("routes", {}).items()],
        "picker_sequences": _picker_sequences(info, record.P),
        "batch_times": _pairs(info.get("batch_times")),
        "batch_completions": _pairs(info.get("batch_completions")),
        "tardiness": _pairs(info.get("tardiness")),
        "earliness": _pairs(info.get("earliness")),
    }
    return {
        "format_version": FORMAT_VERSION,
        "model": record.model_name,
        "test": test_id,
        "instance": instance,
        "solution": solution,
    }


def _scenario_value(key, value):
    """One entry of a build_dat_files scenario dict, JSON-safe with string ids:
    sets -> sorted lists (tuple members as lists), tuple-keyed dicts ->
    [[k1, k2, value], ...] (zeros dropped for the dense 0/1 incidence
    tables A_ni and B_nb), id-keyed dicts -> [[k, value], ...]."""
    if isinstance(value, (set, frozenset, list, tuple)):
        items = [[str(x) for x in v] if isinstance(v, tuple) else str(v) for v in value]
        return sorted(items, key=str)
    if isinstance(value, dict):
        if value and isinstance(next(iter(value)), tuple):
            drop_zeros = key in ("A_ni", "B_nb", "X_pb")
            return [[*(str(k) for k in ks), v] for ks, v in value.items() if v or not drop_zeros]
        return [[str(k), v] for k, v in value.items()]
    return value


def zimpl_record_to_dict(record, test_id):
    """Serialize a ZimplSolutionRecordDTO (dtos/opp/zimpl_solution_record_dto.py):
    kind "zimpl", the instance as the build_dat_files scenario dict (see
    _scenario_value) and every non-zero variable value; for opp_v5_2_split
    also Stage 1's values (the routes)."""
    def nonzero(values):
        return None if values is None else {k: v for k, v in values.items() if abs(v) > 1e-9}

    scenario = record.scenario or {}
    return {
        "format_version": FORMAT_VERSION,
        "kind": "zimpl",
        "zpl": os.path.basename(record.zpl_path),
        "test": test_id,
        "instance": {key: _scenario_value(key, value) for key, value in scenario.items()},
        "solution": {
            "status": record.status,
            "objective_value": record.objective,
            "values": nonzero(record.values),
            "stage1_values": nonzero(record.stage1_values),
        },
    }


def read_zimpl_record(path):
    """Read a kind "zimpl" JSON: returns the raw dict (instance entries as
    serialized by _scenario_value, solution values keyed by SCIP variable
    name)."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if data.get("kind") != "zimpl":
        raise ValueError(f"{path}: not an exact-model (zimpl) solution record")
    return data


def write_solution_record(record, test_id, path):
    """Write `record` (a heuristic's SolutionRecordDTO or an exact model's
    ZimplSolutionRecordDTO) as JSON at `path` (parent dirs created)."""
    from dtos.opp.zimpl_solution_record_dto import ZimplSolutionRecordDTO

    data = (
        zimpl_record_to_dict(record, test_id)
        if isinstance(record, ZimplSolutionRecordDTO)
        else solution_record_to_dict(record, test_id)
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))


def read_solution_record(path):
    """Read a solution JSON back into plain dicts with tuple keys:
    returns (meta, instance, solution) where instance uses the same shapes
    tests/infra/zimpl/dat_files_builder.build_dat_files expects (E as a set
    of (i, j), D_ij/A_ni/B_nb keyed by tuples, the rest keyed by id)."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if data.get("format_version") != FORMAT_VERSION:
        raise ValueError(f"{path}: unsupported format_version {data.get('format_version')}")
    if data.get("kind") == "zimpl":
        raise ValueError(f"{path}: exact-model solution record, read it with read_zimpl_record")

    raw = data["instance"]
    instance = dict(raw)
    instance["N"] = list(raw["N"])
    instance["V"] = list(raw["V"])
    instance["P"] = list(raw["P"])
    instance["B"] = list(raw["B"])
    instance["E"] = {(i, j) for i, j, _ in raw["E"]}
    instance["D_ij"] = {(i, j): d for i, j, d in raw["E"]}
    instance["C_n"] = dict(raw["C_n"])
    instance["T_due_n"] = dict(raw["T_due_n"])
    instance["S_i"] = dict(raw["S_i"])
    instance["A_ni"] = {(n, i): v for n, i, v in raw["A_ni"]}
    instance["B_nb"] = {(n, b): v for n, b, v in raw["B_nb"]}
    instance["V_p"] = dict(raw["V_p"])

    raw_sol = data["solution"]
    solution = {
        "status": raw_sol["status"],
        "objective_value": raw_sol["objective_value"],
        "routes": {b: list(route) for b, route in raw_sol["routes"]},
        "picker_sequences": {p: list(seq) for p, seq in raw_sol["picker_sequences"]},
        "batch_times": dict(raw_sol["batch_times"]),
        "batch_completions": dict(raw_sol["batch_completions"]),
        "tardiness": dict(raw_sol["tardiness"]),
        "earliness": dict(raw_sol["earliness"]),
    }
    meta = {"model": data["model"], "test": data["test"]}
    return meta, instance, solution
