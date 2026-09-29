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
        "E": [[i, j, d_ij], ...],
        "W_full", "W_ea_ta", "W_ea", "W_ta",
        "B_time", "B_setup", "B_picking", "C_v", "M",   (scalars, may be null)
        "C_n": [[n, value], ...], "Dd": [[n, value], ...],
        "S_i": [[i, value], ...],
        "A_ni": [[n, i, value], ...],   (non-zero entries only)
        "Bn": [[n, b, value], ...],     (non-zero entries only)
        "V_p": [[p, speed], ...],       (every picker; missing ones as 1.0,
                                         the models' own default)
        "T_frio_max": float,            (Infinity when disabled)
        "start_time": float, "Seed": int | null
      },
      "solution": {
        "status", "objective_value",
        "routes": [[b, [stops...]], ...],   (stops strictly between depot and final)
        "picker_sequences": [[p, [b...]], ...],   (execution order per picker)
        "batch_times": [[b, t_exec], ...],
        "batch_completions": [[b, v_b], ...],
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
        "W_full": params.W_full,
        "W_ea_ta": params.W_ea_ta,
        "W_ea": params.W_ea,
        "W_ta": params.W_ta,
        "B_time": params.B_time,
        "B_setup": params.B_setup,
        "B_picking": params.B_picking,
        "C_v": params.C_v,
        "M": params.M,
        "C_n": _pairs(params.C_n if isinstance(params.C_n, dict) else {}),
        "Dd": _pairs(params.Dd),
        "S_i": _pairs(params.S if isinstance(params.S, dict) else {}),
        "A_ni": _nonzero_triples(params.A),
        "Bn": _nonzero_triples(params.Bn),
        "V_p": [[str(p), float(speeds.get(p, 1.0))] for p in record.P],
        "T_frio_max": float(params.T_frio_max),
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


def write_solution_record(record, test_id, path):
    """Write `record` as JSON at `path` (parent dirs created)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(solution_record_to_dict(record, test_id), f, separators=(",", ":"))


def read_solution_record(path):
    """Read a solution JSON back into plain dicts with tuple keys:
    returns (meta, instance, solution) where instance uses the same shapes
    tests/infra/zimpl/dat_files_builder.build_dat_files expects (E as a set
    of (i, j), d_ij/A_ni/Bn keyed by tuples, the rest keyed by id)."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if data.get("format_version") != FORMAT_VERSION:
        raise ValueError(f"{path}: unsupported format_version {data.get('format_version')}")

    raw = data["instance"]
    instance = dict(raw)
    instance["N"] = list(raw["N"])
    instance["V"] = list(raw["V"])
    instance["P"] = list(raw["P"])
    instance["B"] = list(raw["B"])
    instance["E"] = {(i, j) for i, j, _ in raw["E"]}
    instance["d_ij"] = {(i, j): d for i, j, d in raw["E"]}
    instance["C_n"] = dict(raw["C_n"])
    instance["Dd"] = dict(raw["Dd"])
    instance["S_i"] = dict(raw["S_i"])
    instance["A_ni"] = {(n, i): v for n, i, v in raw["A_ni"]}
    instance["Bn"] = {(n, b): v for n, b, v in raw["Bn"]}
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
