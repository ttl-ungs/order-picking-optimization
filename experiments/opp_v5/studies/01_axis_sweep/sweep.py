"""Walk one axis at a time from stress 09's shape until each one hurts.

Exploration, not tests: it finds the edges so that only three or four landmark
scenarios have to become test files. Order of axes follows the warehouse's own
logic -- how much a picker carries, then how many batches, then how many
pickers, then how big the warehouse is.

Every row is flushed to CSV as it is measured, so a kill loses nothing but the
point in flight. It also records the real per-batch route times, which is what
the due dates need to be placed against: stress 09 put them on an ESTIMATE and
came out at 96.67% on time, nearly as degenerate as the 0% it replaced.
"""
import csv
import os
import subprocess
import sys
import time

sys.path.insert(0, r"C:\Users\xime-\tesis\linear-picking-routing")

import pyscipopt

from tests.shared_scenarios.stress.stress_scenarios_v5_designed import designed_stress_scenario
from tests.infra.zimpl.dat_files_builder import (
    build_dat_files, write_indexed_dat, write_scalar_dat,
)
from tests.opp_v5_2_split.config import DAT_DIR, STAGE2_ZPL_PATH
from tests.opp_v5_2_split.stage1_decomposition import solve_stage1_decomposed

os.environ["OPP_STAGE1_METRIC_CLOSURE"] = "1"

CAP = 300  # 5 minutes per solve
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sweep_results.csv")
FIELDS = [
    "fase", "lotes", "pickers", "ord_lote", "grilla", "nodos",
    "ubic_lote_min", "ubic_lote_max", "etapa1_s", "etapa2_s", "status",
    "obj", "nodos_bb", "sla_pct", "ruta_min", "ruta_max", "fin_estimado",
]


def measure(batches, pickers, orders_per_batch, side, fase):
    orders = batches * orders_per_batch
    scenario = designed_stress_scenario(batches, pickers, orders, side, side)
    build_dat_files(DAT_DIR, scenario)

    t0 = time.time()
    status, values = solve_stage1_decomposed(DAT_DIR)
    stage1 = time.time() - t0

    row = {
        "fase": fase, "lotes": batches, "pickers": pickers,
        "ord_lote": orders_per_batch, "grilla": f"{side}x{side}",
        "nodos": len(scenario["V"]), "etapa1_s": round(stage1, 2),
    }
    per_batch = [
        len({v for v in scenario["V"]
             if any(scenario["A_ni"][(n, v)] * scenario["Bn"][(n, b)] for n in scenario["N"])})
        for b in sorted(scenario["B"])
    ]
    row["ubic_lote_min"], row["ubic_lote_max"] = min(per_batch), max(per_batch)

    if status not in ("optimal", "feasible"):
        row["status"] = f"etapa1:{status}"
        return row, scenario, None

    routes = {
        k.split("$")[-1]: v for k, v in values.items()
        if k.lower().startswith("r_b_time$")
    }
    row["ruta_min"], row["ruta_max"] = round(min(routes.values()), 1), round(max(routes.values()), 1)
    fixed = scenario["B_setup"] + scenario["B_picking"] * orders_per_batch * scenario["C_n"][
        next(iter(scenario["N"]))
    ]
    depth = -(-batches // pickers)
    durations = sorted((fixed + r for r in routes.values()), reverse=True)
    row["fin_estimado"] = round(sum(durations[:depth]), 1)

    if stage1 > CAP:
        row["status"] = "etapa1_lenta"
        return row, scenario, routes

    write_indexed_dat(os.path.join(DAT_DIR, "route_time_b.dat"), routes)
    write_indexed_dat(os.path.join(DAT_DIR, "velocities.dat"), scenario["V_p"])
    write_scalar_dat(os.path.join(DAT_DIR, "frio.dat"), scenario["T_frio_max"])

    base = os.path.join(DAT_DIR, "sweep_stage2")
    subprocess.run(
        ["zimpl", "-t", "lp", "-l", "8192", "-o", base, STAGE2_ZPL_PATH],
        cwd=DAT_DIR, capture_output=True, text=True, check=True,
    )
    model = pyscipopt.Model()
    model.hideOutput()
    model.readProblem(f"{base}.lp")
    model.setParam("limits/time", CAP)
    t0 = time.time()
    model.optimize()
    row["etapa2_s"] = round(time.time() - t0, 2)
    row["status"] = model.getStatus()
    row["nodos_bb"] = model.getNNodes()
    if model.getStatus() in ("optimal", "feasible"):
        row["obj"] = round(model.getObjVal(), 2)
        finished = [model.getVal(v) for v in model.getVars() if v.name.lower().startswith("ta_n$")]
        if finished:
            row["sla_pct"] = round(sum(1 for t in finished if t <= 1e-6) / len(finished) * 100, 1)
    return row, scenario, routes


def run():
    fresh = not os.path.exists(OUT)
    with open(OUT, "a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if fresh:
            writer.writeheader()
            handle.flush()

        def record(row):
            writer.writerow(row)
            handle.flush()
            print(f"  {row['fase']:<10} {row['lotes']:>2}L/{row['pickers']}P "
                  f"{row['ord_lote']:>3}o/L {row['grilla']:>7} | "
                  f"e1 {row.get('etapa1_s','-'):>7} e2 {row.get('etapa2_s','-'):>7} | "
                  f"{row['status']:<12} sla={row.get('sla_pct','-')}")
            sys.stdout.flush()

        # Fase 1 -- cuanto carga cada lote. 7x7 solo tiene 47 ubicaciones
        # pickeables, asi que pasadas ~25 ordenes por lote las ubicaciones
        # distintas dejan de crecer y solo sube el tiempo de picking.
        best_orders = 10
        for orders_per_batch in (10, 14, 18, 22, 26):
            row, _s, _r = measure(6, 2, orders_per_batch, 7, "1-ordenes")
            record(row)
            if row["status"] != "optimal":
                break
            best_orders = orders_per_batch

        # Fase 2 -- cuantos lotes, con la carga por lote ya fijada.
        best_batches = 6
        for batches in (8, 10, 12, 14):
            row, _s, _r = measure(batches, 2, best_orders, 7, "2-lotes")
            record(row)
            if row["status"] != "optimal":
                break
            best_batches = batches

        # Fase 3 -- cuantos pickers, con lotes y carga fijados.
        for pickers in (3, 4, 5):
            row, _s, _r = measure(best_batches, pickers, best_orders, 7, "3-pickers")
            record(row)
            if row["status"] != "optimal":
                break

        # Fase 4 -- tamano del deposito. Con la clausura metrica esto deberia
        # salir casi gratis: reduce cada lote a un TSP sobre sus ubicaciones.
        for side in (10, 15, 20):
            row, _s, _r = measure(best_batches, 2, best_orders, side, "4-deposito")
            record(row)
            if row["status"] != "optimal":
                break

    print(f"\nresultados en {OUT}")


if __name__ == "__main__":
    run()
