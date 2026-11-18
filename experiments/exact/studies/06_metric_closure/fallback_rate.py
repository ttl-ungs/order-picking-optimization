"""How often does the metric closure fall back to the full graph on realistic grids?

The closure is exact only when the expanded route visits no vertex twice; if it
does, the batch is re-solved on the full graph. On a warehouse grid, shortest
paths between locations share corridors, so that may fire almost every time --
which would explain a closure run that never finishes on a 25x25 grid. This
solves each batch on the closure and checks the expansion, without paying for
the fallback re-solve.

Kept as it was run on 2026-09-23 (translated to English on 2026-09-24, same
logic). It NO LONGER RUNS: it calls closure helpers of
tests/opp_split/stage1_decomposition.py that were removed with the closure on
2026-09-23 (`_closure_context`, `_narrow_to_batch`, `_expand_to_real_arcs`,
`_CLOSURE_FILES`; `_read_indexed_dat_pairs`, `_read_file` and `_write_file`
are still there), and OPP_STAGE1_METRIC_CLOSURE no longer has any effect.

Do not delete it: it is the source of a result the thesis cites. Its printed
output (fallback in 4/6, 6/6 and 5/6 batches on 25x25, 13x13 and 7x7) is
hard-coded in experiments/exact/reports/build_split_exploration.py (figure
"respaldo" of docs/thesis/opp_split_exploration.tex), and the 67-100% of
batches re-solved on the full graph is quoted in the thesis's Appendix 5
(ap5.tex, table tab:anexo_intentos_split, "Clausura métrica" row).
"""
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
os.environ["OPP_STAGE1_METRIC_CLOSURE"] = "1"

from tests.shared_scenarios.stress.stress_scenarios_designed import designed_stress_scenario
from tests.infra.zimpl.dat_files_builder import build_dat_files
from tests.opp_split.config import DAT_DIR, STAGE1_ZPL_PATH
from tests.opp_split import stage1_decomposition as s1
from tests.infra.zimpl.zpl_utils import solve_zpl

for side, orders_per_batch in ((25, 12), (13, 26), (7, 26)):
    scenario = designed_stress_scenario(6, 3, 6 * orders_per_batch, side, side,
                                        vertical_weight=4, horizontal_weight=5)
    build_dat_files(DAT_DIR, scenario)
    ctx = s1._closure_context(DAT_DIR)
    bn = s1._read_indexed_dat_pairs(os.path.join(DAT_DIR, "B_nb.dat"))
    names = ["data_B.dat", "B_nb.dat", *s1._CLOSURE_FILES]
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
            # How badly: count the vertices the walked route visits more than once.
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

    print(f"{side}x{side}, {orders_per_batch} orders/batch: fallback in {fallbacks}/6 batches | "
          f"solve on the closure {min(times):.2f}-{max(times):.2f}s | "
          f"repeated vertices per route: {reuse or '-'}")
    sys.stdout.flush()
