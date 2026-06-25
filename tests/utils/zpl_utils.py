import os
import subprocess
import time

import pyscipopt

from dtos.opp.solve_result import SolveResult
import models.utils.solve_registry as solve_registry


def solve_zpl(zpl_path, dat_dir=None, params=None):
    """
    Compila el .zpl a .lp usando el binario `zimpl` asegurando las extensiones
    para que SCIP mantenga los nombres de las variables intactos.
    """
    if dat_dir is None:
        dat_dir = os.path.dirname(zpl_path)

    lp_path = os.path.join(dat_dir, "model.lp")

    # Paso 1: compilar .zpl → .lp con zimpl
    result = subprocess.run(
        ["zimpl", "-t", "lp", "-o", lp_path, zpl_path],
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
    if status in ("optimal", "feasible"):
        for var in model.getVars():
            var_values[var.name] = model.getVal(var)

    obj_val = model.getObjVal() if status in ("optimal", "feasible") else None

    solve_result = SolveResult(
        status=status,
        output=var_values,
        elapsed=elapsed,
        params={"obj_val": obj_val, **(params or {})},
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
        if name.startswith("z_ijb$") and round(val) == 1:
            parts = name.split("$")
            if len(parts) == 4:
                _, i, j, b = parts
                if b in active:
                    active[b].append((i, j))
    return active
