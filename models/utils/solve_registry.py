"""The results of the solves of the process, one per instance. Every model
registers the result of each solve and the test runner reads them to write one
CSV row per instance.

A test that solves several instances (the variants of a functional case) marks
where each one starts with begin_instance(); every result registered after it,
until the next mark, belongs to that instance and the last one counts (the
Split registers each Stage 1 batch and then Stage 2). Without marks, the whole
process is one instance and only its last result counts.
"""
import time

from dtos.opp.solve_result import SolveResult

_instances: "list[dict]" = []
_instance_open = False
_instance_started_at: "float | None" = None


def begin_instance() -> None:
    """Start a new instance: the next registered result opens its entry."""
    global _instance_open, _instance_started_at
    _instance_open = False
    _instance_started_at = time.time()


def register(solve_result: SolveResult) -> None:
    global _instance_open
    entry = {"result": solve_result, "started_at": _instance_started_at, "ended_at": time.time()}
    if _instances and _instance_open:
        entry["started_at"] = _instances[-1]["started_at"]
        _instances[-1] = entry
    else:
        _instances.append(entry)
        _instance_open = True


def get_last() -> "SolveResult | None":
    return _instances[-1]["result"] if _instances else None


def get_instances() -> "list[dict]":
    """One entry per instance, in solve order: {"result", "started_at",
    "ended_at"}. `started_at` is None when no begin_instance() marked it."""
    return list(_instances)
