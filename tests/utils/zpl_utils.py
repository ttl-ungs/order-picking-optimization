import os
import subprocess

import pyscipopt


def solve_zpl(zpl_path, dat_dir=None):
    """
  Compila el .zpl a .lp usando el binario `zimpl` y luego resuelve
  el .lp con PySCIPOpt/SCIP.

  Parameters
  ----------
  zpl_path : str
      Ruta al archivo .zpl.
  dat_dir : str, optional
      Directorio donde estan los .dat que referencia el .zpl.
      Si es None se usa el directorio del propio .zpl.

  Returns
  -------
  status : str
      Estado de SCIP: "optimal", "infeasible", etc.
  var_values : dict
      {nombre_variable: valor}  (vacio si no hay solucion factible).
  """
    if dat_dir is None:
        dat_dir = os.path.dirname(zpl_path)

    lp_path = os.path.join(dat_dir, "model.lp")

    # --- Paso 1: compilar .zpl → .lp con zimpl ----------------------------
    result = subprocess.run(
        ["zimpl", "-t", "lp", "-o", lp_path, zpl_path],
        cwd=dat_dir,          # los .dat se buscan relativos a este directorio
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ZIMPL compilation failed:\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

    # --- Paso 2: resolver el .lp con PySCIPOpt ----------------------------
    model = pyscipopt.Model()
    model.hideOutput()
    model.readProblem(lp_path)   # SCIP lee .lp sin necesitar el plugin ZIMPL
    model.optimize()

    status = model.getStatus()

    var_values = {}
    if status in ("optimal", "feasible"):
        for var in model.getVars():
            var_values[var.name] = model.getVal(var)

    return status, var_values

def extract_active_arcs(var_values, B):
    """
    A partir del dict de variables resueltas, extrae los arcos activos:
    z_ijb[i,j,b] == 1  ->  arco (i, j) en lote b.

    Devuelve: dict { b: [(i, j), ...] }
    """
    active = {b: [] for b in B}
    for name, val in var_values.items():
        if name.startswith("z_ijb#") and round(val) == 1:
            parts = name.split("#")
            if len(parts) == 4:
                _, i, j, b = parts
                if b in active:
                    active[b].append((i, j))
    return active
