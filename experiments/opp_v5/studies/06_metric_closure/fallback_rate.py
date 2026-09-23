"""How often does the metric closure fall back to the full graph on realistic grids?

The closure is exact only when the expanded route visits no vertex twice; if it
does, the batch is re-solved on the full graph. On a warehouse grid, shortest
paths between locations share corridors, so that may fire almost every time --
which would explain a closure run that never finishes on a 25x25 grid. This
solves each batch on the closure and checks the expansion, without paying for
the fallback re-solve.
"""
import os
import sys
import time

sys.path.insert(0, r"C:\Users\xime-\tesis\linear-picking-routing")
os.environ["OPP_STAGE1_METRIC_CLOSURE"] = "1"

from tests.shared_scenarios.stress.stress_scenarios_v5_designed import designed_stress_scenario
from tests.infra.zimpl.dat_files_builder import build_dat_files
from tests.opp_v5_2_split.config import DAT_DIR, STAGE1_ZPL_PATH
from tests.opp_v5_2_split import stage1_decomposition as s1
from tests.infra.zimpl.zpl_utils import solve_zpl

for lado, ord_lote in ((25, 12), (13, 26), (7, 26)):
    scenario = designed_stress_scenario(6, 3, 6 * ord_lote, lado, lado,
                                        vertical_weight=4, horizontal_weight=5)
    build_dat_files(DAT_DIR, scenario)
    ctx = s1._closure_context(DAT_DIR)
    bn = s1._read_indexed_dat_pairs(os.path.join(DAT_DIR, "Bn.dat"))
    names = ["data_B.dat", "Bn.dat", *s1._CLOSURE_FILES]
    originals = {n: s1._read_file(os.path.join(DAT_DIR, n)) for n in names}

    fallbacks, times, reuse = 0, [], []
    for batch in sorted(scenario["B"]):
        paths = s1._narrow_to_batch(DAT_DIR, batch, bn, ctx)
        t0 = time.time()
        status, values = solve_zpl(STAGE1_ZPL_PATH, dat_dir=DAT_DIR)
        times.append(time.time() - t0)
        expanded = s1._expand_to_real_arcs(values, batch, paths, ctx["depot"], ctx["final"])
        if expanded is None:
            fallbacks += 1
            # how badly: count vertices the walked route visits more than once
            succ = {}
            for k, v in values.items():
                parts = k.split("$")
                if k.lower().startswith("z_ijb$") and round(v) == 1 and len(parts) == 4:
                    succ[parts[1]] = parts[2]
            stops, walked = [ctx["depot"]], [ctx["depot"]]
            while stops[-1] != ctx["final"] and stops[-1] in succ and len(stops) <= len(succ):
                stops.append(succ[stops[-1]])
            for a, b in zip(stops, stops[1:]):
                walked.extend(paths.get((a, b), [a, b])[1:])
            reuse.append(len(walked) - len(set(walked)))
        for n, content in originals.items():
            s1._write_file(os.path.join(DAT_DIR, n), content)

    print(f"{lado}x{lado}, {ord_lote} ord/lote: respaldo en {fallbacks}/6 lotes | "
          f"solve sobre clausura {min(times):.2f}-{max(times):.2f}s | "
          f"vertices repetidos por ruta: {reuse or '-'}")
    sys.stdout.flush()
