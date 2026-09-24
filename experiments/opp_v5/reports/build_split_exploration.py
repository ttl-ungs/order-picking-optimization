"""Build docs/thesis/opp_v5_2_split_exploration.tex from the exploration CSVs.

    python -m experiments.opp_v5.reports.build_split_exploration

Fills each %%FIG:id%% marker of split_exploration_template.tex with a MetaPost chart
computed from experiments/opp_v5/studies/ and the split stress runs in results/.
Compile the output with `context` from docs/thesis/.
"""
import csv
import glob
import math
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from experiments.opp_v5.reports.charts import Chart, ROOT, STUDIES, es, f, log_ticks, rows

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "split_exploration_template.tex")
OUT = os.path.join(ROOT, "docs", "thesis", "opp_v5_2_split_exploration.tex")


def build_figures():
    """Every chart of the report, keyed by its %%FIG:id%% marker."""
    axes01 = rows("01_axis_sweep/sweep_axes_20260922.csv")
    ext01 = rows("01_axis_sweep/sweep_orders_extended_20260922.csv")
    asym02 = rows("02_grid_weights/asymmetric_weights_20260922_235622.csv")
    size02 = rows("02_grid_weights/warehouse_size_weights26_20260923_001445.csv")
    spread03 = rows("03_picker_speeds/spread_speeds_20260922_235629.csv")
    tiers03 = rows("03_picker_speeds/speed_tiers_20260923_003241.csv")
    kill04 = rows("04_hard_kill_check/kill_check.csv")
    r1 = rows("05_realistic_calibration/round1_20260923_125113.csv")
    r1b = rows("05_realistic_calibration/round1b_20260923_125437.csv")
    solo = rows("05_realistic_calibration/solo_20260923_132704.csv")
    le1 = rows("07_le1_constraint/le1_stage1_20260923_140813.csv")

    orders_pts = [r for r in axes01 if r["phase"] == "1-orders"] + ext01
    orders = [int(r["orders_per_batch"]) for r in orders_pts]
    s1_orders = [f(r, "stage1_s") for r in orders_pts]
    s2_orders = [f(r, "stage2_s") for r in orders_pts]
    nodes_orders = [int(r["bb_nodes"]) for r in orders_pts]
    sla_orders = [f(r, "sla_pct") for r in orders_pts]

    FIG = {}

    # 1. Stage 1 and Stage 2 vs orders per batch
    c = Chart(8, 52, 0, 50)
    c.axes([(v, str(v)) for v in (10, 20, 30, 40, 50)], [(v, str(v)) for v in (0, 10, 20, 30, 40, 50)],
           "Órdenes por lote", "Tiempo (s)")
    c.line(list(zip(orders, s1_orders)), "darkblue")
    c.line(list(zip(orders, s2_orders)), "redline")
    c.legend([("darkblue", "Etapa 1 (ruteo)", "line"), ("redline", "Etapa 2 (asignación y secuencia)", "line")], x=3.2)
    FIG["ordenes_etapas"] = c.code()

    # 2. Stage 2 nodes vs orders per batch, log, SLA annotated
    c = Chart(8, 52, 1e3, 1e6, logy=True)
    c.axes([(v, str(v)) for v in (10, 20, 30, 40, 50)], log_ticks(3, 6, seconds=False),
           "Órdenes por lote", "Nodos B\\&B de la Etapa 2")
    c.line(list(zip(orders, nodes_orders)), "darkblue")
    for x, y, s in zip(orders, nodes_orders, sla_orders):
        c.note(x, y, f"{es(s)}\\%", "urt", dx=0.05, dy=0.08)
    c.legend([("darkblue", "nodos (etiqueta: SLA a tiempo)", "line")], x=5.0)
    FIG["nodos_sla"] = c.code()

    # 3. SLA formula
    c = Chart(8, 52, 50, 100)
    c.axes([(v, str(v)) for v in (10, 20, 30, 40, 50)], [(v, f"{v}\\%") for v in (50, 60, 70, 80, 90, 100)],
           "Órdenes por lote $N_b$", "Órdenes a tiempo")
    curve = [(n, (n + 9) / (2 * n) * 100) for n in range(9, 53)]
    c.line(curve, "blueline", dashed=True, smooth=True, markers=False)
    for x, y in zip(orders, sla_orders):
        c.dot(x, y, "darkblue")
    c.legend([("blueline", "predicho: $(N_b + W_{full})/(2N_b)$, $W_{full}=9$", "dashed"),
              ("darkblue", "medido", "dot")], x=4.0)
    FIG["sla_formula"] = c.code()

    # 4. Stage 2 vs pickers (non-monotone)
    pk_a = [(2, f(orders_pts[4], "stage2_s"))] + [
        (int(r["pickers"]), f(r, "stage2_s")) for r in axes01 if r["phase"] == "3-pickers"]
    pk_b = [(int(r["pickers"]), f(r, "stage2_s")) for r in asym02 if r["axis"] == "pickers"]
    c = Chart(1.5, 6.5, 0, 50)
    c.axes([(v, str(v)) for v in (2, 3, 4, 5, 6)], [(v, str(v)) for v in (0, 10, 20, 30, 40, 50)],
           "Pickers (6 lotes)", "Tiempo de Etapa 2 (s)")
    c.line(pk_a, "darkblue")
    c.line(pk_b, "redline")
    c.legend([("darkblue", "26 órdenes/lote, pesos 4/4", "line"), ("redline", "50 órdenes/lote, pesos 2/6", "line")], x=5.5)
    FIG["pickers"] = c.code()

    # 5. Two paths to the same number of locations per batch
    def mean_locs(r):
        return (f(r, "batch_locations_min") + f(r, "batch_locations_max")) / 2

    path_orders = [(mean_locs(r), f(r, "stage1_s")) for r in orders_pts]
    grid_pts = [orders_pts[4]] + [r for r in axes01 if r["phase"] == "4-warehouse"]
    path_grid = [(mean_locs(r), f(r, "stage1_s")) for r in grid_pts]
    c = Chart(5, 35, 1, 1000, logy=True)
    c.axes([(v, str(v)) for v in (5, 10, 15, 20, 25, 30, 35)], log_ticks(0, 3),
           "Ubicaciones distintas por lote (media)", "Tiempo de Etapa 1 (s)")
    c.line(path_orders, "darkblue")
    c.line(path_grid, "redline")
    for (x, y), r in zip(path_grid, grid_pts):
        c.note(x, y, r["grid"].replace("x", "\\times"), "lft", dx=-0.1)
    c.note(path_orders[-1][0], path_orders[-1][1], "50 órd./lote", "bot", dy=-0.12)
    c.legend([("darkblue", "más órdenes por lote, grilla 7×7", "line"),
              ("redline", "más grilla, 26 órdenes por lote", "line")])
    FIG["dos_caminos"] = c.code()

    # 6. weights: Stage 1 vs orders per batch
    w44 = list(zip(orders, s1_orders))
    w26 = [(int(r["orders_per_batch"]), f(r, "stage1_s")) for r in asym02 if r["axis"] == "orders"]
    c = Chart(8, 52, 0, 50)
    c.axes([(v, str(v)) for v in (10, 20, 30, 40, 50)], [(v, str(v)) for v in (0, 10, 20, 30, 40, 50)],
           "Órdenes por lote (grilla 7×7)", "Tiempo de Etapa 1 (s)")
    c.line(w44, "darkblue")
    c.line(w26, "redline")
    c.legend([("darkblue", "pesos 4/4 (uniformes)", "line"), ("redline", "pesos 2/6 (misma media)", "line")])
    FIG["pesos_ordenes"] = c.code()

    # 7. weights: Stage 1 vs grid side
    side44 = [(7, f(orders_pts[4], "stage1_s"))] + [
        (int(r["grid"].split("x")[0]), f(r, "stage1_s")) for r in axes01 if r["phase"] == "4-warehouse"]
    side26 = [(int(r["grid"].split("x")[0]), f(r, "stage1_s")) for r in size02]
    c = Chart(6, 16, 1, 1000, logy=True)
    c.axes([(v, f"{v}×{v}") for v in (7, 10, 15)], log_ticks(0, 3), "Grilla (26 órdenes/lote)", "Tiempo de Etapa 1 (s)")
    c.line(side44, "darkblue")
    c.line(side26, "redline")
    c.legend([("darkblue", "pesos 4/4", "line"), ("redline", "pesos 2/6", "line")])
    FIG["pesos_grilla"] = c.code()

    # 8. spread speeds vs uniform, Stage 2 vs orders (2 pickers)
    spread = [(int(r["orders_per_batch"]), f(r, "stage2_s")) for r in spread03 if r["axis"] == "orders"]
    c = Chart(8, 52, 0, 50)
    c.axes([(v, str(v)) for v in (10, 20, 30, 40, 50)], [(v, str(v)) for v in (0, 10, 20, 30, 40, 50)],
           "Órdenes por lote (6 lotes, 2 pickers)", "Tiempo de Etapa 2 (s)")
    c.line(list(zip(orders, s2_orders)), "darkblue")
    c.line(spread, "redline")
    c.legend([("darkblue", "velocidades uniformes", "line"), ("redline", "velocidades distintas en [0,7; 1,3]", "line")], x=3.2)
    FIG["velocidades_dispares"] = c.code()

    # 9. speed tiers, grouped bars, log
    order_cfg = ["uniform", "2 tiers", "3 tiers", "all distinct"]
    style = {"uniform": ("darkblue", False), "2 tiers": ("redline", False),
             "3 tiers": ("blueline", False), "all distinct": ("darkblue", True)}
    c = Chart(0, 3, 1, 10000, logy=True, h=6.5)
    c.cat_axes([(0.5, "3 pickers"), (1.5, "4 pickers"), (2.5, "6 pickers")], log_ticks(0, 4), "Tiempo de Etapa 2 (s)")
    c.hline(300, "límite de SCIP: 300 s")
    for gi, pk in enumerate((3, 4, 6)):
        for ci, cfg in enumerate(order_cfg):
            x0 = gi + 0.1 + ci * 0.2
            match = [r for r in tiers03 if int(r["pickers"]) == pk and r["tiers"] == cfg]
            if not match:
                c.note(x0 + 0.1, 1.3, "n/m", "top")
                continue
            r = match[0]
            color, outline = style[cfg]
            c.bar(x0, 0.18, 1, f(r, "stage2_s"), color, outline)
            if f(r, "stage2_s") > 1000:
                c.note(x0 + 0.09, f(r, "stage2_s"), f"{es(f(r, 'stage2_s'), 0)} s", "top", dy=0.02)
            elif r["status"] != "optimal":
                c.note(x0 + 0.09, f(r, "stage2_s"), "tope", "top", dy=0.02)
    c.legend([("darkblue", "uniformes", "box"), ("redline", "2 niveles", "box"),
              ("blueline", "3 niveles", "box"), ("darkblue", "todas distintas", "outline")], x=0.2, top=6.35)
    FIG["niveles"] = c.code()

    # 10. scheduling shapes: final gap after 25 min
    shape = [("6 lotes / 3 pickers", 0.0, "óptimo"),
             ("6 lotes / 4 pickers", f([r for r in r1 if r["label"] == "B1"][0], "gap_pct"), None),
             ("7 lotes / 3 pickers", f([r for r in r1b if r["label"] == "B3"][0], "gap_pct"), None),
             ("8 lotes / 3 pickers", f([r for r in r1 if r["label"] == "B2"][0], "gap_pct"), None)]
    c = Chart(0, 4, 0, 10, h=5)
    c.cat_axes([(i + 0.5, s[0]) for i, s in enumerate(shape)], [(v, f"{v}\\%") for v in (0, 2, 4, 6, 8, 10)],
               "Brecha final")
    for i, (lab, gap, txt) in enumerate(shape):
        if gap > 0:
            c.bar(i + 0.25, 0.5, 0, gap, "redline")
        c.note(i + 0.5, gap, txt or f"{es(gap, 2)}\\%", "top", dy=0.05)
    FIG["formas"] = c.code()

    # 11. stress tests: time by stage (split, realistic profile), from the suite run (6 workers)
    suite_path = os.path.join(ROOT, "results", "opp_v5_2_split", "stress",
                              "output_opp_v5_2_split_stress_tests_parallel.csv")
    with open(suite_path, encoding="utf-8", errors="replace") as fh:
        suite = {r["test"].split(".")[0]: r for r in csv.DictReader(fh)}

    def stage_times(test_case):
        r = suite[test_case]
        return f(r, "total_time"), f(r, "model_time")

    tests = [(label, *stage_times(case)) for label, case in (
        ("7×7", "test_case_04"), ("13×13", "test_case_05"), ("14×14", "test_case_06"),
        ("15×15", "test_case_07"), ("8×21", "test_case_09"))]
    c = Chart(0, 5, 0, 1500, h=6)
    c.cat_axes([(i + 0.5, t[0]) for i, t in enumerate(tests)], [(v, es(v, 0)) for v in (0, 300, 600, 900, 1200, 1500)],
               "Tiempo total (s)")
    for i, (lab, total, s2) in enumerate(tests):
        s1 = total - s2
        c.bar(i + 0.25, 0.5, 0, s1, "darkblue")
        c.bar(i + 0.25, 0.5, s1, total, "redline")
        c.note(i + 0.5, total, f"{es(total / 60, 1)} min", "top", dy=0.03)
    c.legend([("darkblue", "Etapa 1 y preparación", "box"), ("redline", "Etapa 2 (solver)", "box")])
    FIG["etapas_tests"] = c.code()

    # 12. split vs mono on the same instance
    t1 = [r for r in kill04 if r["label"] == "T1"][0]
    t2 = [r for r in kill04 if r["label"] == "T2"][0]
    m0 = [r for r in r1 if r["label"] == "M0"][0]
    r0 = [r for r in r1b if r["label"] == "R0nc"][0]
    c = Chart(0, 2, 1, 10000, logy=True, h=5.5)
    c.cat_axes([(0.5, "5×5, 4 lotes, 2 pickers"), (1.5, "7×7, perfil realista")], log_ticks(0, 4), "Tiempo total (s)")
    pairs = [(0, t1, t2), (1, r0, m0)]
    for gi, sp, mo in pairs:
        c.bar(gi + 0.2, 0.28, 1, f(sp, "total_s"), "darkblue")
        c.note(gi + 0.34, f(sp, "total_s"), "óptimo", "top", dy=0.02)
        c.bar(gi + 0.52, 0.28, 1, f(mo, "total_s"), "darkblue", outline=True)
        gap = f(mo, "gap_pct")
        c.note(gi + 0.66, f(mo, "total_s"), f"brecha {es(gap, 2 if gap < 10 else 1)}\\%", "top", dy=0.02)
    c.legend([("darkblue", "split", "box"), ("darkblue", "mono", "outline")], x=0.2, top=5.35)
    FIG["mono_split"] = c.code()

    # 13. closure fallback rate (diagnostic printed by fallback_rate.py, recorded in meta.md)
    fallback = [("25×25, 12 órd./lote", 4), ("13×13, 26 órd./lote", 6), ("7×7, 26 órd./lote", 5)]
    c = Chart(0, 3, 0, 6, h=5)
    c.cat_axes([(i + 0.5, t[0]) for i, t in enumerate(fallback)], [(v, str(v)) for v in range(7)],
               "Lotes re-resueltos")
    for i, (lab, n) in enumerate(fallback):
        c.bar(i + 0.3, 0.4, 0, n, "redline")
        c.note(i + 0.5, n, f"{es(n / 6 * 100, 0)}\\%", "top", dy=0.05)
    FIG["respaldo"] = c.code()

    # 14. <= 1 constraint: Stage 1 with and without
    def le1_s1(label):
        return f([r for r in le1 if r["label"] == label][0], "stage1_s")

    c = Chart(0, 2, 1, 1000, logy=True, h=5)
    c.cat_axes([(0.5, "7×7, 26 órd./lote"), (1.5, "13×13, 26 órd./lote")], log_ticks(0, 3), "Tiempo de Etapa 1 (s)")
    for gi, (a, b) in enumerate((("L7", "L7r"), ("L13", "L13r"))):
        c.bar(gi + 0.2, 0.28, 1, le1_s1(a), "darkblue")
        c.note(gi + 0.34, le1_s1(a), f"{es(le1_s1(a))} s", "top", dy=0.02)
        c.bar(gi + 0.52, 0.28, 1, le1_s1(b), "darkblue", outline=True)
        c.note(gi + 0.66, le1_s1(b), f"{es(le1_s1(b))} s", "top", dy=0.02)
    c.legend([("darkblue", "con $\\leq 1$", "box"), ("darkblue", "sin $\\leq 1$", "outline")], x=0.2, top=4.85)
    FIG["le1"] = c.code()

    # Study 12's controlled A/B: Stage 1 alone, sequential vs 6 workers, ABBA order.
    ab_path = sorted(glob.glob(os.path.join(STUDIES, "12_stage1_parallel", "points_*.csv")))[-1]
    ab = rows(os.path.relpath(ab_path, STUDIES))

    def ab_mean(side, parallel):
        times = [f(r, "stage1_s") for r in ab
                 if r["label"].startswith(f"S{side}-") and ("workers=6" in r["variant"]) == parallel]
        return sum(times) / len(times)

    # 15. realistic profile: Stage 1 vs grid side -- suite run (6 workers), study 12 (sequential), calibration
    runs = [(side, stage_times(case)[0] - stage_times(case)[1])
            for side, case in ((7, "test_case_04"), (13, "test_case_05"), (14, "test_case_06"), (15, "test_case_07"))]
    seq = [(side, ab_mean(side, False)) for side in (13, 14)]
    cal = [(7, f(solo[0], "stage1_s")), (13, f(solo[1], "stage1_s"))]
    c = Chart(6, 16, 1, 10000, logy=True)
    c.axes([(v, f"{v}×{v}") for v in (7, 10, 13, 14, 15)], log_ticks(0, 4), "Grilla (perfil realista)", "Tiempo de Etapa 1 (s)")
    c.line(runs, "darkblue")
    c.line(seq, "blueline")
    c.line(cal, "redline")
    c.open_dot(15, 1500, "redline")
    c.note(15, 1500, "cortado a 1.500 s", "lft", dx=-0.2, dy=0.35)
    c.legend([("darkblue", "tests de stress, 6 procesos", "line"),
              ("blueline", "estudio 12, en secuencia", "line"),
              ("redline", "calibración en secuencia, de a un punto", "line"),
              ("redline", "calibración cortada sin terminar", "open")])
    FIG["etapa1_realista"] = c.code()

    # 16. Controlled A/B (study 12), each run as a bar.
    c = Chart(0, 2, 0, 450, h=5)
    c.cat_axes([(0.5, "13×13 (test 05)"), (1.5, "14×14 (test 06)")], [(v, str(v)) for v in (0, 100, 200, 300, 400)],
               "Tiempo de la Etapa 1 (s)")
    for gi, side in enumerate((13, 14)):
        runs = [r for r in ab if r["label"].startswith(f"S{side}-")]
        for k, r in enumerate(runs):
            x0 = gi + 0.1 + k * 0.2
            parallel = "workers=6" in r["variant"]
            c.bar(x0, 0.17, 0, f(r, "stage1_s"), "redline" if parallel else "darkblue")
            c.note(x0 + 0.085, f(r, "stage1_s"), f"{es(f(r, 'stage1_s'), 0)}", "top", dy=0.03)
    c.legend([("darkblue", "secuencial", "box"), ("redline", "6 procesos", "box")], x=0.2)
    FIG["paralelo_ab"] = c.code()

    return FIG


def main():
    text = open(TEMPLATE, encoding="utf-8").read()
    used = set(re.findall(r"%%FIG:(\w+)%%", text))
    figures = build_figures()
    missing = used - set(figures)
    unused = set(figures) - used
    assert not missing, missing
    assert not unused, unused
    for key, code in figures.items():
        text = text.replace(f"%%FIG:{key}%%", code)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(f"wrote {OUT} with {len(figures)} charts")


if __name__ == "__main__":
    main()
