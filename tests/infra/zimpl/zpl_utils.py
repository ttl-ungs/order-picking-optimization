import os
import subprocess
import time
import pyscipopt
from dtos.opp.solve_result import SolveResult
from dtos.opp.zimpl_solution_record_dto import ZimplSolutionRecordDTO
from tests.infra.zimpl.dat_files_builder import last_scenario
import models.utils.solve_registry as solve_registry
from models.utils.input_validation import overloaded_batches, orders_without_exactly_one_batch

# SCIP statuses meaning "stopped on a limit, not concluded".
_LIMIT_STATUSES = ("timelimit", "gaplimit", "sollimit", "nodelimit", "totalnodelimit", "stallnodelimit", "memlimit", "userinterrupt")


def solve_zpl(zpl_path, dat_dir=None, params=None, time_limit_seconds=None):
    """
    Compile the .zpl to .lp with the `zimpl` binary and solve it with SCIP.
    The values of the variables that are > 0 are added to `params`, for the
    results CSV.

    time_limit_seconds: optional SCIP time limit (`limits/time`). Without it
    only the test runner's timeout bounds the run; pass it when SCIP itself
    must conclude, e.g. to tell "proved infeasible" from "ran out of time".
    """
    if dat_dir is None:
        dat_dir = os.path.dirname(zpl_path)
    if params is None:
        params = {}

    # The ZIMPL models take B_nb and C_v as parameters, so no constraint
    # rejects an overloaded batch or an order in zero or several batches
    # (models/utils/input_validation.py). Reject them here, like the
    # heuristics do.
    bn = params.get("B_nb")
    invalid_reasons = []

    overloaded = overloaded_batches(params.get("C_n"), bn, params.get("C_v"))
    if overloaded:
        invalid_reasons.append(
            "batch(es) exceed vehicle capacity (C_v): " + ", ".join(sorted(overloaded))
        )

    N_inferred = {n for (n, _b) in bn.keys()} if bn else set()
    misassigned = orders_without_exactly_one_batch(bn, N_inferred)
    if misassigned:
        invalid_reasons.append(
            "order(s) not assigned to exactly one batch: " + ", ".join(sorted(misassigned))
        )

    if invalid_reasons:
        params["debug_output"] = "INFEASIBLE: " + "; ".join(invalid_reasons)
        solve_result = SolveResult(
            status="infeasible",
            output={},
            elapsed=0.0,
            params={"obj_val": None, **params},
        )
        solve_registry.register(solve_result)
        return "infeasible", {}

    out_base = os.path.join(dat_dir, "model")
    lp_path = f"{out_base}.lp"

    # Step 1: compile the .zpl to .lp with zimpl
    result = subprocess.run(
        ["zimpl", "-t", "lp", "-l", "8192", "-o", out_base, zpl_path],
        cwd=dat_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ZIMPL compilation failed:\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

    # Step 2: solve the .lp with PySCIPOpt
    model = pyscipopt.Model()
    model.hideOutput()
    if time_limit_seconds is not None:
        model.setParam("limits/time", time_limit_seconds)
    model.readProblem(lp_path)

    t0 = time.time()
    model.optimize()
    elapsed = time.time() - t0

    status = model.getStatus()
    var_values = {}
    debug_string = ""

    # A solve cut by a limit (only with time_limit_seconds) may hold a feasible
    # incumbent: read it too, so that a time-budgeted run
    # (experiments/comparison/run_equal_time_study.py) reports its best
    # solution. The status stays "timelimit".
    has_incumbent = status in ("optimal", "feasible") or (
        status in _LIMIT_STATUSES and model.getNSols() > 0
    )
    if status in _LIMIT_STATUSES or time_limit_seconds is not None:
        params["dual_bound"] = model.getDualbound()
        params["mip_gap"] = model.getGap() if has_incumbent else None

    if has_incumbent:
        debug_list = []
        for var in model.getVars():
            val = model.getVal(var)
            var_values[var.name] = val
            if val > 0.01:
                debug_list.append(f"{var.name}: {val}")
        debug_string = " | ".join(debug_list)

    elif status == "infeasible":
        debug_string = "INFEASIBLE"

    params["debug_output"] = debug_string

    # Service level: % of orders on time or early (tardiness <= 0), from the
    # ta_n values. A solve without that variable (Stage 1) reports no
    # sla_on_time_pct rather than 0.
    ta_values = [val for name, val in var_values.items() if name.lower().startswith("ta_n$")]
    if ta_values:
        params["sla_on_time_pct"] = sum(1 for t in ta_values if t <= 1e-6) / len(ta_values) * 100

    obj_val = model.getObjVal() if has_incumbent else None

    solve_result = SolveResult(
        status=status,
        output=var_values,
        elapsed=elapsed,
        params={"obj_val": obj_val, **params},
        # Instance + solution for verification/ (written only with
        # WRITE_SOLUTIONS); references only, nothing is copied here.
        solution_record=ZimplSolutionRecordDTO(
            zpl_path=zpl_path, scenario=last_scenario(), status=status, objective=obj_val, values=var_values,
        ),
    )
    solve_registry.register(solve_result)

    return status, var_values

def extract_active_arcs(var_values, B):
    """Active arcs of a solution: {b: [(i, j), ...]} for every z_ijb[i,j,b] == 1."""
    active = {b: [] for b in B}
    for name, val in var_values.items():
        if name.lower().startswith("z_ijb$") and round(val) == 1:
            parts = name.split("$")
            if len(parts) == 4:
                _, i, j, b = parts
                if b in active:
                    active[b].append((i, j))
    return active
