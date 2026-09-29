"""Build docs/thesis/opp_v5_1_mono_vs_opp_v5_2_split_comparison.tex from the functional
and stress runs.

    python -m experiments.opp_v5.reports.build_functional_comparison

Pairs every functional test the two models share (same test_case number and
method) and keeps the comparable ones: the tests whose instances split, hc_4 and
aco_4 all solve or all declare infeasible (comparable_set, the same base as the
heuristics report). Solved pairs carry the verdict of
results/comparability/compare_v5_split_vs_mono.csv (same solution or an
alternative optimum). Fills the %%TABLE:id%%, %%FIG:id%% and %%NUM:id%% markers
of functional_comparison_template.tex.
Compile the output with `context` from docs/thesis/.
"""
import csv
import math
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from experiments.opp_v5.reports.charts import Chart, ROOT, STUDIES, es
from experiments.opp_v5.reports.comparable_set import functional_methods, split_vs_mono_verdicts
from experiments.opp_v5.reports.stress_suite import counts as stress_counts, stress_table

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "functional_comparison_template.tex")
OUT = os.path.join(ROOT, "docs", "thesis", "opp_v5_1_mono_vs_opp_v5_2_split_comparison.tex")
SPLIT_RUN = "results/opp_v5_2_split/functional/output_opp_v5_2_split_functional_tests.csv"
MONO_RUN = "results/opp_v5_1_mono/functional/output_opp_v5_1_mono_functional_tests.csv"

# (test_case, fragment of the method name, short Spanish label for the tables)
LABELS = [
    ("01", "", "Capacidad básica"), ("02", "", "Dos pasillos"), ("03", "", "Dos pasillos (variante)"),
    ("04", "", "Un punto por orden"), ("05", "", "Un pasillo"),
    ("06", "every_route", "Todas las rutas llegan a tiempo"), ("06", "shorter", "Ruta corta si la larga atrasa"),
    ("07", "", "Ubicaciones repetidas"), ("08", "", "Ubicaciones repetidas 2"),
    ("09", "", "Dos ubicaciones"), ("10", "", "Dos misiones"), ("11", "", "Cuatro órdenes"),
    ("13", "", "Dos períodos, grilla"), ("14", "", "Un período, grilla"),
    ("15", "", "Tres órdenes, un picker"), ("16", "", "Seis órdenes, dos pickers"),
    ("17", "", "Ruta ramificada"), ("18", "", "Ruta con desvío"),
    ("19", "duplicate", "Ruta extendida, ubicación dup."), ("19", "penalties", "Ruta extendida, penalizaciones"),
    ("19", "route", "Ruta extendida"), ("20", "", "Grilla multiubicación"), ("21", "", "Puente desconectado"),
    ("22", "earliness", "Adelanto"), ("22", "tardiness", "Atraso"),
    ("23", "longer_route", "Ruta larga al picker rápido"), ("23", "exported", "Rutas exportadas"),
    ("24", "cold_chain", "Frío excluye al picker lento"), ("24", "preflight", "Chequeo previo de frío"),
    ("25", "batch_infeasible", "Grilla: tamaño infactible"), ("25", "duplicate", "Grilla: ubicación dup."),
    ("25", "multi_location", "Grilla multiubicación"), ("25", "bigger_than_cart", "Grilla: orden mayor al carro"),
    ("25", "penalties_due_date", "Grilla: penalización por fecha"),
    ("25", "equal_to_cart", "Grilla: orden igual al carro"), ("25", "shared", "Grilla: ubic. compartidas"),
    ("26", "disconnected", "Puente desconectado"), ("26", "earliness", "Puente: adelanto"),
    ("26", "shared", "Puente: ubic. compartidas"), ("26", "tardiness", "Puente: atraso"),
    ("27", "", "Pesos distintos"), ("28", "", "Fechas ajustadas y holgadas"),
    ("29", "", "Lote vacío permitido"), ("30", "infeasible", "Capacidades fraccionarias (infact.)"),
    ("30", "feasible", "Capacidades fraccionarias"),
    ("31", "multiple", "Orden en varios lotes"), ("31", "single", "Orden en un lote"),
    ("32", "", "Orden excede el vehículo"),
    ("33", "mixed", "Servicio mixto"), ("33", "one", "Servicio unitario"), ("33", "zero", "Servicio cero"),
    ("34", "no_eligible", "Ningún picker elegible"), ("34", "exactly", "Frío justo en el límite"),
    ("34", "formula", "Fórmula de velocidad"),
    ("35", "each_batch", "Frío por lote, no por turno"), ("35", "tolerance", "Tolerancia de frío"),
    ("35", "fixed_time", "La parte fija cuenta para el frío"),
    ("36", "twice", "Rápido 2×: reparte los lotes"), ("36", "four_times", "Rápido 4×: hace los dos"),
    ("36", "non_positive", "Velocidad no positiva"), ("36", "tardiness", "Atraso con velocidad 0,5"),
    ("37", "delayed_while", "Demora a propósito"), ("37", "not_delayed", "Sin demora"),
    ("38", "", "Pasillos sin salida ($\\leq 1$)"),
]


def label(num, method):
    for n, fragment, text in LABELS:
        if n == num and fragment in method:
            return text
    return method


def load(path):
    csv.field_size_limit(10**9)
    with open(os.path.join(ROOT, path), encoding="utf-8", errors="replace") as fh:
        rows = {}
        for r in csv.DictReader(fh):
            num, _, method = r["test"].split(".")
            rows[(num.replace("test_case_", ""), method)] = r
        return rows


def num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def case_ids(keys):
    """'19a', '19b'... for test cases with several methods, in method order."""
    ids, by_case = {}, {}
    for key in sorted(keys):
        by_case.setdefault(key[0], []).append(key)
    for case, members in by_case.items():
        for i, key in enumerate(members):
            ids[key] = case + ("abcdefgh"[i] if len(members) > 1 else "")
    return ids


def table(header, rows, width="fit"):
    lines = ["\\blank[medium]", f"\\bTABLE[split=yes, align=middle, frame=on, width={width}]",
             "\\setupTABLE[row][1][background=color, backgroundcolor=darkgray, style=bold]",
             "\\bTR " + " ".join(f"\\bTH {h} \\eTH" for h in header) + " \\eTR"]
    for r in rows:
        lines.append("\\bTR " + " ".join(f"\\bTD {c} \\eTD" for c in r) + " \\eTR")
    lines += ["\\eTABLE", "\\blank[medium]"]
    return "\n".join(lines)


def build():
    split, mono = load(SPLIT_RUN), load(MONO_RUN)
    shared = sorted(set(split) & set(mono))
    ids = case_ids(set(split) | set(mono))

    comparable = functional_methods()
    verdicts = split_vs_mono_verdicts()
    # A method can appear in several test cases (02 and 03); compare_v5 keeps one row per
    # method name, so the cases that share it share its verdict.
    verdict = {}
    for key in shared:
        rows = verdicts[("functional", key[1])]
        verdict[key] = rows.pop(0) if len(rows) > 1 else rows[0]

    feasible, infeasible, excluded_keys = [], [], []
    for key in shared:
        if not comparable[key[1]][0]:
            excluded_keys.append(key)
        elif verdict[key][0] in ("same_solution", "alternative_optimum"):
            feasible.append(key)
        elif verdict[key][0] == "both_infeasible":
            infeasible.append(key)
        else:
            raise ValueError((key, verdict[key]))
    split_only = sorted(set(split) - set(mono))
    alternative = [k for k in feasible if verdict[k][0] == "alternative_optimum"]
    alt_routes = [k for k in alternative if "routes" in verdict[k][1]]
    alt_assign = [k for k in alternative if "assignment" in verdict[k][1]]

    t_m = [num(mono[k]["total_time"]) for k in feasible]
    t_s = [num(split[k]["total_time"]) for k in feasible]
    m_m = [num(mono[k]["model_time"]) for k in feasible]
    m_s = [num(split[k]["model_time"]) for k in feasible]
    ratios = {k: num(mono[k]["total_time"]) / num(split[k]["total_time"]) for k in feasible}
    diffs = {k: abs(num(mono[k]["obj_val"]) - num(split[k]["obj_val"])) for k in feasible}
    faster_mono = [k for k in feasible if ratios[k] < 1]
    top = max(ratios, key=ratios.get)
    mantissa, exponent = f"{max(diffs.values()):.2e}".split("e")
    max_diff = f"{mantissa.replace('.', '{,}')} \\times 10^{{{int(exponent)}}}"

    NUM = {
        "pairs": str(len(shared)), "split_tests": str(len(split)), "mono_tests": str(len(mono)),
        "comparable": str(len(feasible) + len(infeasible)),
        "excluded": str(len(excluded_keys) + len(split_only)),
        "same_solution": str(len(feasible) - len(alternative)), "alternative": str(len(alternative)),
        "alt_routes": str(len(alt_routes)), "alt_assign": str(len(alt_assign)),
        "feasible": str(len(feasible)), "infeasible": str(len(infeasible)),
        "max_diff": max_diff,
        "diff_cases": ", ".join(sorted({ids[k] for k, d in diffs.items() if d > 1e-9})),
        "same_obj": str(sum(1 for d in diffs.values() if d <= 1e-4)),
        "sum_ratio": es(sum(t_m) / sum(t_s), 1), "median_mono": es(statistics.median(t_m), 3),
        "median_split": es(statistics.median(t_s), 3), "mono_faster": str(len(faster_mono)),
        "mono_faster_min": es(min(ratios[k] for k in faster_mono), 2),
        "mono_faster_max": es(max(ratios[k] for k in faster_mono), 2),
        "top_ratio": es(ratios[top], 1), "top_case": ids[top],
        "model_sum_ratio": es(sum(m_m) / sum(m_s), 0),
        "model_median_ratio": es(statistics.median(m_m) / statistics.median(m_s), 1),
    }

    def stat_row(name, f_m, f_s, ratio=True, dec=3):
        return [name, es(f_m, dec), es(f_s, dec), (es(f_m / f_s, 2) + "×") if ratio else "--"]

    TABLE = {}
    TABLE["coverage"] = table(["Métrica", "Pares"], [
        ["Tests en los dos modelos", len(shared)],
        ["Comparables", len(feasible) + len(infeasible)],
        ["\\quad resueltos en los dos", len(feasible)],
        ["\\quad infactibles en los dos", len(infeasible)],
        ["Fuera de la comparación", len(excluded_keys) + len(split_only)],
    ])
    TABLE["times"] = table(["Métrica", "Mono (s)", "Split (s)", "Mono / split"], [
        stat_row("\\type{total_time} suma", sum(t_m), sum(t_s), dec=1),
        stat_row("\\type{total_time} promedio", statistics.mean(t_m), statistics.mean(t_s)),
        stat_row("\\type{total_time} mediana", statistics.median(t_m), statistics.median(t_s)),
        stat_row("\\type{total_time} desvío", statistics.stdev(t_m), statistics.stdev(t_s), ratio=False),
        stat_row("\\type{total_time} mínimo", min(t_m), min(t_s)),
        stat_row("\\type{total_time} máximo", max(t_m), max(t_s)),
        stat_row("\\type{model_time} suma", sum(m_m), sum(m_s), dec=2),
        stat_row("\\type{model_time} mediana", statistics.median(m_m), statistics.median(m_s)),
    ])
    SOLUTION = {"": "igual", "routes": "otras rutas", "assignment": "otra asignación",
                "routes, assignment": "otras rutas y asignación"}
    TABLE["detail"] = table(["Caso", "Test", "Mono (s)", "Split (s)", "Mono / split", "Objetivo", "Solución de mono"], [
        [ids[k], label(*k), es(num(mono[k]["total_time"]), 3), es(num(split[k]["total_time"]), 3),
         es(ratios[k], 2) + "×", es(num(split[k]["obj_val"]), 1),
         SOLUTION[verdict[k][1].replace("differs in ", "")]] for k in feasible
    ])
    TABLE["infeasible"] = table(["Caso", "Test", "Mono (s)", "Split (s)", "Mono / split"], [
        [ids[k], label(*k), es(num(mono[k]["total_time"]), 3), es(num(split[k]["total_time"]), 3),
         es(num(mono[k]["total_time"]) / num(split[k]["total_time"]), 2) + "×"] for k in infeasible
    ])
    def reason(key):
        text = comparable[key[1]][1]
        if "timeout" in text:
            return "Timeout en split (25 min): sin referencia"
        if "espere" in text:
            return "Verifica la espera voluntaria, que las heurísticas no modelan"
        if "no llega al solver" in text:
            return "Rechaza la entrada antes de resolver"
        return text

    excluded = [[ids[k], label(*k), reason(k)] for k in excluded_keys]
    excluded += [[ids[k], label(*k), "Resuelve solo la Etapa 1; mono no tiene etapas"] for k in split_only]
    TABLE["excluded"] = table(["Caso", "Test", "Motivo"], sorted(excluded))

    FIG = {}
    # Scatter of total_time, log-log, with the y = x diagonal.
    lo, hi = -1, 2
    c = Chart(lo, hi, lo, hi, w=8, h=8)
    ticks = [(e, lab) for e, lab in ((-1, "0,1"), (0, "1"), (1, "10"), (2, "100"))]
    c.axes(ticks, ticks, "Split, tiempo total (s, escala log.)", "Mono, tiempo total (s, escala log.)")
    c.line([(lo, lo), (hi, hi)], "blueline", dashed=True, markers=False)
    for k in feasible:
        c.dot(math.log10(num(split[k]["total_time"])), math.log10(num(mono[k]["total_time"])), "darkblue")
    c.legend([("darkblue", "par resuelto", "dot"), ("blueline", "igual tiempo", "dashed")], x=0.3, top=7.85)
    FIG["scatter"] = c.code()

    # Ratio per pair, sorted, log scale.
    order = sorted(feasible, key=ratios.get)
    c = Chart(0, len(order), 0.4, 50, logy=True, w=14, h=6)
    c.cat_axes([], [(0.5, "0,5"), (1, "1"), (2, "2"), (5, "5"), (10, "10"), (50, "50")], "Mono / split (tiempo total)")
    c.hline(1, "igual", at="right")
    for i, k in enumerate(order):
        r = ratios[k]
        lo_v, hi_v = (1, r) if r >= 1 else (r, 1)
        c.bar(i + 0.15, 0.7, lo_v, hi_v, "darkblue" if r >= 1 else "redline")
        if r >= 10:
            c.note(i + 0.5, r, ids[k], "top", dy=0.03)
    c.legend([("darkblue", "split más rápido", "box"), ("redline", "mono más rápido", "box")], x=0.3, top=5.85)
    FIG["ratio"] = c.code()

    # Solver time vs instance size (batches x locations), where the CSV records it.
    sized = [k for k in feasible if num(split[k].get("B")) and num(split[k].get("V"))]
    c = Chart(0, math.log10(200), -4, 2, h=6)
    c.axes([(math.log10(v), str(v)) for v in (1, 2, 5, 10, 20, 50, 100, 200)],
           [(e, lab) for e, lab in ((-4, "$10^{-4}$"), (-3, "$10^{-3}$"), (-2, "0,01"), (-1, "0,1"),
                                    (0, "1"), (1, "10"), (2, "100"))],
           "Lotes × ubicaciones (escala log.)", "Tiempo del solver (s, escala log.)")
    for k in sized:
        size = math.log10(num(split[k]["B"]) * num(split[k]["V"]))
        for model, color in ((mono, "redline"), (split, "darkblue")):
            c.dot(size, math.log10(max(num(model[k]["model_time"]), 1e-4)), color)
    c.legend([("redline", "mono", "dot"), ("darkblue", "split (Etapa 2)", "dot")], x=0.3)
    FIG["size"] = c.code()
    NUM["sized"] = str(len(sized))

    TABLE["stress"] = stress_table()
    NUM.update(stress_counts())
    scale(TABLE, FIG, NUM)
    return TABLE, FIG, NUM


def study(pattern):
    """{(label, model): row} of the latest CSV of a pair study (split and mono on one instance)."""
    import glob
    path = sorted(glob.glob(os.path.join(STUDIES, pattern)))[-1]
    with open(path, encoding="utf-8") as fh:
        return {(r["label"], r["model"]): r for r in csv.DictReader(fh)}


def scale(TABLE, FIG, NUM):
    """Studies 08 and 11: the realistic profile on growing grids, solved by both models."""
    f08 = study("08_mono_frontier/frontier_*.csv")
    cap = float(f08[("B2S3", "mono")]["hard_cap_s"])
    SIDES = [3, 4, 5, 6, 7]
    LINES = [(2, "darkblue"), (3, "redline"), (4, "blueline"), (6, "greenline")]
    panels, ratios, capped = [], {}, []
    for model in ("split", "mono"):
        c = Chart(2.6, 7.4, 0.1, 20000, logy=True, w=6.4, h=6.5)
        c.axes([(s, f"{s}×{s}") for s in SIDES],
               [(v, lab) for v, lab in ((0.1, "0,1"), (1, "1"), (10, "10"), (100, "100"), (1000, "1.000"))],
               "Grilla", "Tiempo hasta el óptimo (s, escala log.)")
        c.hline(cap, "tope: 10 min", at="right" if model == "split" else "left")
        for b, color in LINES:
            pts = []
            for side in SIDES:
                r = f08.get((f"B{b}S{side}", model))
                if not r or r["status"] in ("skipped", "infeasible") or r["status"].endswith("infeasible"):
                    continue
                t = float(r["total_s"])
                if r["status"] == "optimal":
                    pts.append((side, t))
                    if model == "mono" and f08[(f"B{b}S{side}", "split")]["status"] == "optimal":
                        ratios[(b, side)] = t / float(f08[(f"B{b}S{side}", "split")]["total_s"])
                else:
                    pts.append((side, cap))
                    capped.append((b, side))
            c.line(pts, color, markers=False)
            for side, t in pts:
                if model == "mono" and (b, side) in capped:
                    c.open_dot(side, t, color)
                else:
                    c.dot(side, t, color)
        if model == "split":
            c.legend([(color, f"{b} lotes", "line") for b, color in LINES], x=0.3, top=6.4)
        else:
            c.legend([("darkblue", "no termina (cortado al tope)", "open")], x=0.3, top=6.4)
        panels.append(c.code())
    FIG["scale_split"], FIG["scale_mono"] = panels
    NUM["scale_cap_min"] = es(cap / 60, 0)
    NUM["scale_capped"] = ", ".join(f"{b} lotes en {side}×{side}" for b, side in capped)
    worst = max(ratios, key=ratios.get)
    NUM["scale_max_ratio"] = es(ratios[worst], 0)
    NUM["scale_max_case"] = f"{worst[0]} lotes en {worst[1]}×{worst[1]}"
    # Where mono hit the cap its ratio is only a lower bound: cap / split time.
    bound = {(b, side): cap / float(f08[(f"B{b}S{side}", "split")]["total_s"]) for b, side in capped}
    top = max(bound, key=bound.get)
    NUM["scale_bound_ratio"] = es(bound[top], 0)
    NUM["scale_bound_case"] = f"{top[0]} lotes en {top[1]}×{top[1]}"
    # Model size: mono's MIP against split's Stage 2 (what the study records for split).
    size_rows = []
    for b in (3, 4):
        for side in (3, 5, 6, 7):
            m, sp = f08.get((f"B{b}S{side}", "mono")), f08.get((f"B{b}S{side}", "split"))
            if not m or not sp or not m["n_vars"] or not sp["n_vars"]:
                continue
            size_rows.append([f"{b} lotes, {side}×{side}", es(float(m["n_vars"]), 0), es(float(m["n_conss"]), 0),
                              es(float(sp["n_vars"]), 0), es(float(sp["n_conss"]), 0)])
    TABLE["model_size"] = table(["Instancia", "Mono: variables", "Mono: restricciones",
                                 "Split Etapa 2: variables", "Split Etapa 2: restricciones"], size_rows)
    NUM["scale_bound_split"] = es(float(f08[(f"B{top[0]}S{top[1]}", "split")]["total_s"]), 1)

    # Study 11: the points mono did not close, and stress test 04, with a 40-minute cap.
    f11 = study("11_mono_long_cap/points_*.csv")
    rows = []
    for lab, text in (("B3S7", "3 lotes, 7×7"), ("B4S6", "4 lotes, 6×6"), ("B6S5", "6 lotes, 5×5"),
                      ("test04", "stress 04: 6 lotes, 7×7")):
        sp, mo = f11[(lab, "split")], f11[(lab, "mono")]
        closed = mo["status"] == "optimal"
        rows.append([text, es(float(sp["total_s"]), 1), es(float(mo["total_s"]) / 60, 1) + " min",
                     "sí" if closed else "no",
                     es(float(mo["best_gap_to_opt_pct"]), 2) + " \\%",
                     "--" if closed else es(float(mo["gap_pct"]), 1) + " \\%"])
    TABLE["long_cap"] = table(["Instancia", "Split (s)", "Mono", "¿Mono prueba el óptimo?",
                               "Mono: distancia al óptimo", "Mono: gap que reporta"], rows)
    t04 = f11[("test04", "mono")]
    NUM["t04_best"] = es(float(t04["best_gap_to_opt_pct"]), 2)
    NUM["t04_gap"] = es(float(t04["gap_pct"]), 1)
    NUM["t04_split"] = es(float(f11[("test04", "split")]["total_s"]), 0)


def main():
    TABLE, FIG, NUM = build()
    with open(TEMPLATE, encoding="utf-8") as fh:
        text = fh.read()
    for kind, values in (("TABLE", TABLE), ("FIG", FIG), ("NUM", NUM)):
        used = set(re.findall(rf"%%{kind}:(\w+)%%", text))
        missing = used - set(values)
        assert not missing, (kind, missing)
        for key, value in values.items():
            text = text.replace(f"%%{kind}:{key}%%", str(value))
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(f"wrote {OUT}")
    print({k: v for k, v in NUM.items()})


if __name__ == "__main__":
    main()
