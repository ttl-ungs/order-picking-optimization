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
    Compila el .zpl a .lp usando el binario `zimpl` y lo resuelve con SCIP.
    Inyecta automáticamente las variables > 0 en params para los reportes CSV.

    time_limit_seconds: optional SCIP time limit (`limits/time`). Default
    None keeps the previous behaviour (no limit, relies on the external
    test-runner timeout / a process kill to bound wall time). Pass an
    explicit limit when you need SCIP itself to conclude cleanly -- e.g. to
    tell apart "SCIP proved infeasible" from "still searching, ran out of
    time" for a diagnostic run, which an external kill can't distinguish
    (it might kill SCIP moments before it would have concluded infeasible).
    """
    if dat_dir is None:
        dat_dir = os.path.dirname(zpl_path)
    if params is None:
        params = {}

    # The ZIMPL models take B_nb/C_v as fixed parameters, not decision
    # variables, so it has no constraint left to reject a batch that
    # overflows the vehicle or an order assigned to zero/two+ batches --
    # it would just solve happily around garbage input (see
    # models/utils/input_validation.py). Enforce both here, before ever
    # calling zimpl/SCIP, so this input is rejected the same way
    # opp_hc/opp_aco reject it for the same instance.
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

    # Paso 1: compilar .zpl → .lp con zimpl
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

    # Paso 2: resolver el .lp con PySCIPOpt
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

    # A limit-cut solve ("timelimit" etc., only possible when
    # time_limit_seconds was given) may still hold a feasible incumbent:
    # read it too, so a time-budgeted run reports its best solution found
    # instead of nothing (analysis/run_equal_time_study.py). The returned
    # status stays "timelimit" -- callers that require a proven
    # "optimal"/"feasible" answer are unaffected.
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

    # SLA (nivel de servicio): % de ordenes que llegaron a tiempo o antes
    # (tardiness <= 0). Derivado de las variables ta_n$<orden> ya resueltas
    # arriba -- ninguna de las etapas/modelos que no tienen esa variable aporta
    # ta_values, asi que sla_on_time_pct queda ausente para esos, no en 0.
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
    """
    A partir del dict de variables resueltas, extrae los arcos activos:
    z_ijb[i,j,b] == 1  ->  arco (i, j) en lote b.

    Devuelve: dict { b: [(i, j), ...] }
    """
    active = {b: [] for b in B}
    for name, val in var_values.items():
        if name.lower().startswith("z_ijb$") and round(val) == 1:
            parts = name.split("$")
            if len(parts) == 4:
                _, i, j, b = parts
                if b in active:
                    active[b].append((i, j))
    return active
