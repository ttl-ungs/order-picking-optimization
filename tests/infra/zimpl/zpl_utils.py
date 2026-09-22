import os
import subprocess
import time
import pyscipopt
from dtos.opp.solve_result import SolveResult
import models.utils.solve_registry as solve_registry
from models.utils.input_validation import overloaded_batches, orders_without_exactly_one_batch

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

    # opp_model_v4.zpl takes Bn/C_v as fixed parameters, not decision
    # variables, so it has no constraint left to reject a batch that
    # overflows the vehicle or an order assigned to zero/two+ batches --
    # it would just solve happily around garbage input (see
    # models/utils/input_validation.py). Enforce both here, before ever
    # calling zimpl/SCIP, so this input is rejected the same way
    # opp_hc_2/opp_aco_2/opp_hc_3/opp_aco_3 reject it for the same instance.
    bn = params.get("Bn")
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

    if status in ("optimal", "feasible"):
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

    obj_val = model.getObjVal() if status in ("optimal", "feasible") else None

    solve_result = SolveResult(
        status=status,
        output=var_values,
        elapsed=elapsed,
        params={"obj_val": obj_val, **params},
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
