import os
import subprocess
import time
import pyscipopt
from dtos.opp.solve_result import SolveResult
import models.utils.solve_registry as solve_registry

def solve_zpl(zpl_path, dat_dir=None, params=None):
    """
    Compila el .zpl a .lp usando el binario `zimpl` y lo resuelve con SCIP.
    Inyecta automáticamente las variables > 0 en params para los reportes CSV.
    """
    if dat_dir is None:
        dat_dir = os.path.dirname(zpl_path)

    out_base = os.path.join(dat_dir, "model")
    lp_path = f"{out_base}.lp"

    # Paso 1: compilar .zpl → .lp con zimpl
    result = subprocess.run(
        ["zimpl", "-t", "lp", "-o", out_base, zpl_path],
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

    if params is None:
        params = {}

    params["debug_output"] = debug_string

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
