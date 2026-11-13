"""Build docs/thesis/opp_split_vs_heuristics_comparison.tex from the consolidated CSVs.

    python -m experiments.exact.reports.build_heuristics_comparison

Compares opp_split with opp_hc and opp_aco on the instances the three
share (comparable_set): the functional instances of test_functional_cases.py and the 19 stress
scenarios. Reads results/comparability/results_split_vs_heuristics.csv (status,
objective, gap and times per instance and heuristic) and the heuristics'
compliance reports, and fills the %%TABLE:id%%, %%FIG:id%% and %%NUM:id%%
markers of heuristics_comparison_template.tex.
Compile the output with `context` from docs/thesis/.
"""
from experiments.common.load import case_number
import csv
import math
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from experiments.exact.reports.build_functional_comparison import (
    MONO_RUN, SPLIT_RUN, case_ids, label, load, table,
)
from experiments.exact.reports.charts import Chart, ROOT, es
from experiments.exact.reports.comparable_set import HEURISTICS, compliance, registry, results
from experiments.exact.reports.stress_suite import SPLIT_STRESS, SUITE

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "heuristics_comparison_template.tex")
OUT = os.path.join(ROOT, "docs", "thesis", "opp_split_vs_heuristics_comparison.tex")
NAME = {"opp_hc": "OPP-HC", "opp_aco": "ACO-4"}
EXACT = 1e-6  # gap_pct at or below this is the optimum (the registry rounds to 0 below 1e-6 %)


def num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def is_true(value):
    return value == "True"


def pct(value, dec=2):
    return es(value, dec) + " \\%"


def instance_ids():
    """{the Split method: [case id, ...]} from the split run, to label instances like the mono report."""
    split = load(SPLIT_RUN)
    ids = case_ids(set(split) | set(load(MONO_RUN)))
    out = {}
    for key in sorted(split):
        out.setdefault(key[1], []).append((ids[key], label(*key)))
    return out


def instance_label(row, by_method):
    """('20', 'Grilla multiubicación') or ('25f·2', ...) for a test with several instances."""
    cases = by_method[row["split_test"]]
    match = re.search(r"__(\d+)$", row["heuristic_instance"] or "")
    case, text = cases[0]
    if len(cases) > 1 and match:
        case, text = cases[min(int(match.group(1)), len(cases)) - 1]
    elif match:
        case = f"{case}·{match.group(1)}"
    return case, text


def stress_cases():
    """{stress method: case number '01'..'19'} from the split stress CSV."""
    with open(SPLIT_STRESS, encoding="utf-8", errors="replace") as fh:
        return {r["test"].split(".")[-1]: case_number(r["test"]) for r in csv.DictReader(fh)}


def build():
    case_of = stress_cases().__getitem__
    rows = results()
    by_method = instance_ids()
    reg = registry()
    NUM, TABLE, FIG = {}, {}, {}

    def of(tier, heuristic):
        return [r for r in rows if r["tier"] == tier and r["heuristic"] == heuristic]

    # --- Coverage: the same for both heuristics, taken from the registry.
    for tier in ("functional", "stress"):
        tr = [r for r in reg if r["tier"] == tier]
        both = [r for r in tr if is_true(r["comparable_status"]) and is_true(r["comparable_objective"])]
        status_only = [r for r in tr if is_true(r["comparable_status"]) and not is_true(r["comparable_objective"])]
        infeasible = [r for r in status_only if r["split_status"] == "infeasible"]
        NUM[f"{tier}_total"] = str(len(tr))
        NUM[f"{tier}_both"] = str(len(both))
        NUM[f"{tier}_status_only"] = str(len(status_only))
        NUM[f"{tier}_infeasible"] = str(len(infeasible))
        NUM[f"{tier}_wait"] = str(len(status_only) - len(infeasible))
        NUM[f"{tier}_out"] = str(len(tr) - len(both) - len(status_only))
    NUM["status_comparable"] = str(int(NUM["functional_both"]) + int(NUM["functional_status_only"]))
    TABLE["coverage"] = table(["", "Funcional", "Stress"], [
        ["Instancias", NUM["functional_total"], NUM["stress_total"]],
        ["Comparables en estado y objetivo", NUM["functional_both"], NUM["stress_both"]],
        ["Comparables solo en estado", NUM["functional_status_only"], NUM["stress_status_only"]],
        ["\\quad split infactible", NUM["functional_infeasible"], NUM["stress_infeasible"]],
        ["\\quad split usa espera voluntaria", NUM["functional_wait"], NUM["stress_wait"]],
        ["No comparables", NUM["functional_out"], NUM["stress_out"]],
    ])
    out_rows = []
    for r in reg:
        if r["tier"] == "functional" and not is_true(r["comparable_status"]):
            case, text = by_method[r["split_test"]][0]
            reason = r["not_comparable_reason"]
            reason = ("Timeout en split (25 min)" if "timeout" in reason else
                      "Verifica la espera voluntaria, que las heurísticas no modelan" if "espere" in reason else
                      "Rechaza la entrada antes de resolver")
            out_rows.append([case, text, reason])
    TABLE["functional_out"] = table(["Caso", "Test", "Motivo"], sorted(out_rows))

    # --- Compliance of the heuristics' solutions, on the shared instances only.
    shared = {"functional": {(r["case"], r["heuristic_instance"]) for r in reg if r["tier"] == "functional"
                             and r["heuristic_instance"]},
              "stress": {(r["case"], r["heuristic_instance"]) for r in reg if r["tier"] == "stress"}}
    comp_rows, all_compliant = [], True
    for h in HEURISTICS:
        for tier, tier_name in (("functional", "Funcional"), ("stress", "Stress")):
            verdicts = [v for inst, v in compliance(h, tier).items() if inst in shared[tier]]
            counts = {v: verdicts.count(v) for v in ("compliant", "violations", "skipped", "error")}
            all_compliant &= counts["violations"] == 0 and counts["error"] == 0
            comp_rows.append([NAME[h], tier_name, len(verdicts), counts["compliant"], counts["violations"],
                              counts["skipped"]])
    TABLE["compliance"] = table(["Heurística", "Suite", "Instancias", "Cumple", "Viola", "Sin solución"], comp_rows)
    NUM["compliance_violations"] = "ninguna" if all_compliant else "alguna"
    checked = matched = 0
    for h in HEURISTICS:
        for tier in ("functional", "stress"):
            path = os.path.join(ROOT, "results", "compliance", h, tier, f"compliance_output_{h}_{tier}_tests.csv")
            with open(path, encoding="utf-8", errors="replace") as fh:
                for r in csv.DictReader(fh):
                    if tuple(r["test"].split(".")[-2:]) in shared[tier] and r["verdict"] == "compliant":
                        a, b = num(r["heuristic_obj"]), num(r["recomputed_obj"])
                        checked += 1
                        matched += abs(a - b) <= 1e-6 * max(1.0, abs(a))
    NUM["recomputed_checked"], NUM["recomputed_matched"] = str(checked), str(matched)

    # --- Status agreement on the status-comparable instances.
    status_rows = []
    for h in HEURISTICS:
        cells = [NAME[h]]
        for tier in ("functional", "stress"):
            comparable = [r for r in of(tier, h) if is_true(r["comparable_status"])]
            matches = sum(1 for r in comparable if is_true(r["status_matches"]))
            cells.append(f"{matches} / {len(comparable)}")
            NUM[f"status_{tier}_{h}"] = str(matches)
        status_rows.append(cells)
    TABLE["status"] = table(["Heurística", "Funcional", "Stress"], status_rows)

    # --- Objective gap where it is comparable.
    gap_rows = {"functional": [], "stress": []}
    for h in HEURISTICS:
        for tier, tier_name in (("functional", "Funcional"), ("stress", "Stress")):
            gaps = [num(r["gap_pct"]) for r in of(tier, h) if is_true(r["comparable_objective"])]
            optimal = sum(1 for g in gaps if abs(g) <= EXACT)
            gap_rows[tier].append([NAME[h], len(gaps), optimal, pct(statistics.mean(gaps)),
                                   pct(statistics.median(gaps)), pct(max(gaps))])
            NUM[f"optimal_{tier}_{h}"] = str(optimal)
            NUM[f"max_gap_{tier}_{h}"] = es(max(gaps), 2)
            NUM[f"mean_gap_{tier}_{h}"] = es(statistics.mean(gaps), 2)
            NUM[f"better_{tier}_{h}"] = str(sum(1 for g in gaps if g < -EXACT))
    header = ["Heurística", "Instancias", "Óptimo", "Brecha media", "Mediana", "Máxima"]
    TABLE["gap"] = table(header, gap_rows["functional"])
    TABLE["gap_stress"] = table(header, gap_rows["stress"])

    # Instances where split uses voluntary waiting: status comparable, objective not.
    wait = {h: {(r["case"], r["heuristic_instance"]): r for r in of("functional", h) if is_true(r["comparable_status"])
                and not is_true(r["comparable_objective"]) and r["split_status"] == "optimal"} for h in HEURISTICS}
    wait_rows = []
    for inst in sorted(wait[HEURISTICS[0]]):
        r0 = wait[HEURISTICS[0]][inst]
        case, text = instance_label(r0, by_method)
        cells = [case, text, es(num(r0["split_obj"]), 1)]
        for h in HEURISTICS:
            cells.append(es(num(wait[h][inst]["heuristic_obj"]), 1))
        cells.append(r0["not_comparable_reason"].replace("el Split usa espera voluntaria en ", "")
                     .replace("[", "").replace("]", "").replace("'", ""))
        wait_rows.append(cells)
    TABLE["wait"] = table(["Caso", "Test", "Split", "OPP-HC", "ACO-4", "Lotes que esperan"], sorted(wait_rows))
    NUM["wait_count"] = str(len(wait_rows))
    NUM["wait_aco_above"] = str(sum(1 for inst in wait["opp_aco"]
                                    if num(wait["opp_aco"][inst]["heuristic_obj"]) > num(wait["opp_aco"][inst]["split_obj"]) + 1e-6))

    # Functional instances where some heuristic misses the optimum.
    functional = {h: {(r["case"], r["heuristic_instance"]): r for r in of("functional", h)
                      if is_true(r["comparable_objective"])} for h in HEURISTICS}
    missed = sorted({inst for h in HEURISTICS for inst, r in functional[h].items() if num(r["gap_pct"]) > EXACT})
    detail = []
    for inst in missed:
        r0 = functional[HEURISTICS[0]][inst]
        case, text = instance_label(r0, by_method)
        cells = [case, text, es(num(r0["split_obj"]), 1)]
        for h in HEURISTICS:
            r = functional[h][inst]
            cells += [es(num(r["heuristic_obj"]), 1), pct(num(r["gap_pct"]), 1)]
        detail.append(cells)
    TABLE["missed"] = table(["Caso", "Test", "Split", "OPP-HC", "Brecha", "ACO-4", "Brecha"], detail)
    NUM["missed"] = str(len(missed))

    # --- Functional times, where the split time of the instance is known.
    time_rows = []
    timed = {h: [r for r in functional[h].values() if num(r["split_time"]) is not None] for h in HEURISTICS}
    NUM["timed"] = str(len(timed[HEURISTICS[0]]))
    split_t = [num(r["split_time"]) for r in timed[HEURISTICS[0]]]
    time_rows.append(["OPP-Split", es(statistics.median(split_t), 3), es(sum(split_t), 1), "--"])
    for h in HEURISTICS:
        h_t = [num(r["heuristic_time"]) for r in timed[h]]
        speed = statistics.median(num(r["speedup"]) for r in timed[h])
        time_rows.append([NAME[h], es(statistics.median(h_t), 3), es(sum(h_t), 1), es(speed, 1) + "×"])
        NUM[f"functional_speedup_{h}"] = es(speed, 1)
        NUM[f"functional_slower_{h}"] = str(sum(1 for r in timed[h] if num(r["heuristic_time"]) > num(r["split_time"])))
    TABLE["functional_times"] = table(["Modelo", "Mediana (s)", "Suma (s)", "Split / heurística (mediana)"],
                                      time_rows)

    # --- Stress, scenario by scenario.
    stress = {h: {r["split_test"]: r for r in of("stress", h)} for h in HEURISTICS}
    order = sorted(stress[HEURISTICS[0]].values(), key=lambda r: case_of(r["split_test"]))
    stress_rows, ref_speed, noref = [], {h: [] for h in HEURISTICS}, []
    for r0 in order:
        n = case_of(r0["split_test"])
        desc, lots, grid = SUITE[n]
        solved = r0["split_status"] == "optimal"
        cells = [n, lots, grid, es(num(r0["split_time"]), 0) if solved else "timeout"]
        for h in HEURISTICS:
            r = stress[h][r0["split_test"]]
            cells += [es(num(r["heuristic_time"]), 1), pct(num(r["gap_pct"])) if solved else "--"]
            if solved:
                ref_speed[h].append(num(r["speedup"]))
        if not solved:
            hc, aco = (num(stress[h][r0["split_test"]]["heuristic_obj"]) for h in HEURISTICS)
            noref.append((n, hc, aco))
        stress_rows.append(cells)
    TABLE["stress"] = table(["Caso", "Lotes", "Grilla", "Split (s)", "OPP-HC (s)", "Brecha",
                             "ACO-4 (s)", "Brecha"], stress_rows)
    for h in HEURISTICS:
        NUM[f"stress_speedup_{h}"] = es(statistics.median(ref_speed[h]), 1)
        NUM[f"stress_found_{h}"] = str(sum(1 for r in stress[h].values()
                                           if r["split_status"] != "optimal" and is_true(r["heuristic_found_solution"])))
    NUM["stress_noref"] = str(len(noref))
    NUM["noref_aco_better"] = str(sum(1 for _, hc, aco in noref if aco < hc - 1e-9))
    NUM["noref_hc_better"] = str(sum(1 for _, hc, aco in noref if hc < aco - 1e-9))
    TABLE["noref"] = table(["Caso", "OPP-HC", "ACO-4", "ACO-4 contra OPP-HC"], [
        [n, es(hc, 1), es(aco, 1), pct(100 * (aco - hc) / hc)] for n, hc, aco in noref
    ])

    # Chart: time per stress scenario for the three models, log scale.
    c = Chart(0, len(order), 0.3, 5000, logy=True, w=12, h=6.5)
    c.cat_axes([(i + 0.5, case_of(r["split_test"])) for i, r in enumerate(order)],
               [(v, lab) for v, lab in ((1, "1"), (10, "10"), (100, "100"), (1000, "1.000"))],
               "Tiempo total (s, escala log.)")
    c.hline(2400, "tope de 40 min", at="left")
    for i, r0 in enumerate(order):
        solved = r0["split_status"] == "optimal"
        c.bar(i + 0.1, 0.26, 0.3, num(r0["split_time"]), "darkblue", outline=not solved)
        c.bar(i + 0.37, 0.26, 0.3, max(num(stress["opp_hc"][r0["split_test"]]["heuristic_time"]), 0.31), "greenline")
        c.bar(i + 0.64, 0.26, 0.3, max(num(stress["opp_aco"][r0["split_test"]]["heuristic_time"]), 0.31), "redline")
    c.legend([("darkblue", "split", "box"), ("darkblue", "split: timeout", "outline"),
              ("greenline", "OPP-HC", "box"), ("redline", "ACO-4", "box")], x=12.3, top=3.5)
    FIG["stress_times"] = c.code()

    functional_chart(timed, FIG)
    stress_extras(order, stress, case_of, TABLE, FIG, NUM)
    return TABLE, FIG, NUM


LOG_TICKS = [(0.01, "0,01"), (0.1, "0,1"), (1, "1"), (10, "10"), (100, "100"), (1000, "1.000")]
PCT_TICKS = [(v, es(v, 2) + " \\%") for v in (0, 0.05, 0.1, 0.15, 0.2, 0.25)]


def functional_chart(timed, FIG):
    """Split time against each heuristic's time, per functional instance (log-log)."""
    c = Chart(-2, 1, -2, 1, w=8, h=8)
    ticks = [(e, lab) for e, lab in ((-2, "0,01"), (-1, "0,1"), (0, "1"), (1, "10"))]
    c.axes(ticks, ticks, "Split, tiempo total (s, escala log.)", "Heurística, tiempo total (s, escala log.)")
    c.line([(-2, -2), (1, 1)], "blueline", dashed=True, markers=False)
    for h, color in (("opp_hc", "greenline"), ("opp_aco", "redline")):
        for r in timed[h]:
            c.dot(math.log10(num(r["split_time"])), math.log10(max(num(r["heuristic_time"]), 0.01)), color)
    c.legend([("greenline", "OPP-HC", "dot"), ("redline", "ACO-4", "dot"), ("blueline", "igual tiempo", "dashed")],
             x=0.3, top=7.85)
    FIG["functional_scatter"] = c.code()


def raw_stress():
    """{model: {case: row}} of the three models' stress CSVs."""
    paths = {"split": SPLIT_STRESS}
    for h in HEURISTICS:
        paths[h] = os.path.join(ROOT, "results", h, "stress", f"output_{h}_stress_tests.csv")
    out = {}
    for model, path in paths.items():
        with open(path, encoding="utf-8", errors="replace") as fh:
            out[model] = {case_number(r["test"]): r for r in csv.DictReader(fh)}
    return out


def stress_extras(order, stress, case_of, TABLE, FIG, NUM):
    raw = raw_stress()
    cases = [case_of(r["split_test"]) for r in order]
    solved = [n for n, r in zip(cases, order) if r["split_status"] == "optimal"]
    by_case = {h: {case_of(k): r for k, r in stress[h].items()} for h in HEURISTICS}
    split_time = {case_of(r["split_test"]): num(r["split_time"]) for r in order}
    CAP = 2400.0
    COLOR = {"split": "darkblue", "opp_hc": "greenline", "opp_aco": "redline"}

    # Instance size of each scenario, from the heuristics' CSV (same instance in the three models).
    size = {n: {k: int(float(raw["opp_hc"][n][k])) for k in ("N", "B", "P", "V")} for n in cases}
    TABLE["sizes"] = table(["Caso", "Instancia", "Órdenes", "Lotes", "Pickers", "Ubicaciones", "$W^c$"], [
        [n, SUITE[n][0], size[n]["N"], size[n]["B"], size[n]["P"], es(size[n]["V"], 0),
         es(num(raw["opp_hc"][n]["W_c"]), 0)] for n in cases
    ])

    # Scalability: time against batches x locations, the three models.
    c = Chart(math.log10(200), math.log10(400000), 0.3, 5000, logy=True, w=11, h=6.5)
    c.axes([(math.log10(v), lab) for v, lab in ((300, "300"), (1000, "1.000"), (3000, "3.000"),
                                                 (10000, "10.000"), (100000, "100.000"))],
           [(v, lab) for v, lab in LOG_TICKS if v >= 1], "Lotes × ubicaciones (escala log.)",
           "Tiempo total (s, escala log.)")
    c.hline(CAP, "tope de split: 40 min", at="left")
    for n in cases:
        x = math.log10(size[n]["B"] * size[n]["V"])
        if n in solved:
            c.dot(x, split_time[n], COLOR["split"])
        else:
            c.open_dot(x, CAP, COLOR["split"])
        for h in HEURISTICS:
            c.dot(x, max(num(by_case[h][n]["heuristic_time"]), 0.31), COLOR[h])
    c.legend([("darkblue", "split", "dot"), ("darkblue", "split: timeout", "open"),
              ("greenline", "OPP-HC", "dot"), ("redline", "ACO-4", "dot")], x=6.0, top=3.5)
    FIG["stress_scale"] = c.code()

    # Gap per solved scenario, the two heuristics side by side.
    gaps = {h: [num(by_case[h][n]["gap_pct"]) for n in solved] for h in HEURISTICS}
    c = Chart(0, len(solved), 0, 0.25, w=12, h=5.5)
    c.cat_axes([(i + 0.5, n) for i, n in enumerate(solved)], PCT_TICKS, "Brecha contra el óptimo de split")
    for i, n in enumerate(solved):
        for j, h in enumerate(HEURISTICS):
            g = gaps[h][i]
            if g > 1e-9:
                c.bar(i + 0.15 + 0.35 * j, 0.33, 0, g, COLOR[h])
            else:
                c.note(i + 0.31 + 0.35 * j, 0, "0", "top", dy=0.02)
    c.legend([("greenline", "OPP-HC", "box"), ("redline", "ACO-4", "box")], x=0.3, top=5.3)
    FIG["stress_gap"] = c.code()
    NUM["gap_aco_below_hc"] = str(sum(1 for i in range(len(solved))
                                      if gaps["opp_aco"][i] < gaps["opp_hc"][i]))
    NUM["stress_solved"] = str(len(solved))

    # Quality against time: each solved scenario, three models.
    c = Chart(math.log10(0.3), math.log10(3000), -0.01, 0.25, w=11, h=6)
    c.axes([(math.log10(v), lab) for v, lab in LOG_TICKS if 0.3 <= v <= 3000], PCT_TICKS,
           "Tiempo total (s, escala log.)", "Brecha contra el óptimo")
    for n in solved:
        c.dot(math.log10(split_time[n]), 0, COLOR["split"])
        for h in HEURISTICS:
            r = by_case[h][n]
            c.dot(math.log10(max(num(r["heuristic_time"]), 0.31)), num(r["gap_pct"]), COLOR[h])
    c.legend([("darkblue", "split (óptimo)", "dot"), ("greenline", "OPP-HC", "dot"), ("redline", "ACO-4", "dot")],
             x=6.8, top=5.7)
    FIG["tradeoff"] = c.code()

    # Service level (share of orders on time) per scenario.
    def sla(model, n):
        v = num(raw[model][n].get("sla_on_time_pct"))
        return "--" if v is None else es(v, 1) + " \\%"
    TABLE["sla"] = table(["Caso", "Split", "OPP-HC", "ACO-4"], [
        [n, sla("split", n), sla("opp_hc", n), sla("opp_aco", n)] for n in cases
    ])

    # Peak memory per scenario.
    mem = {m: {n: num(raw[m][n]["peak_rss_mb"]) for n in cases} for m in raw}
    c = Chart(0, len(cases), 10, 3000, logy=True, w=12, h=6)
    c.cat_axes([(i + 0.5, n) for i, n in enumerate(cases)],
               [(v, lab) for v, lab in ((10, "10"), (30, "30"), (100, "100"), (300, "300"), (1000, "1.000"))],
               "Memoria pico (MB, escala log.)")
    for i, n in enumerate(cases):
        for j, m in enumerate(("split", "opp_hc", "opp_aco")):
            if mem[m][n] is not None:
                c.bar(i + 0.1 + 0.27 * j, 0.26, 10, mem[m][n], COLOR[m])
    c.legend([("darkblue", "split", "box"), ("greenline", "OPP-HC", "box"), ("redline", "ACO-4", "box")],
             x=12.3, top=3.5)
    FIG["memory"] = c.code()
    for m in HEURISTICS:
        typical = [v for n, v in mem[m].items() if n != "01"]
        NUM[f"mem_median_{m}"] = es(statistics.median(typical), 0)
        NUM[f"mem_01_{m}"] = es(mem[m]["01"], 0)
    split_mem = [v for v in mem["split"].values() if v is not None]
    NUM["mem_split_min"], NUM["mem_split_max"] = es(min(split_mem), 0), es(max(split_mem), 0)
    spikes = [n for n in cases if n != "01" and mem["opp_aco"][n] > 500]
    NUM["mem_aco_spikes"] = ", ".join(spikes)
    NUM["mem_aco_spike_max"] = es(max(mem["opp_aco"][n] for n in spikes), 0)

    # Convergence of the heuristics on the stress scenarios.
    hc, aco = raw["opp_hc"], raw["opp_aco"]
    TABLE["convergence"] = table(["Caso", "OPP-HC: iteraciones", "OPP-HC: mejor en", "ACO-4: iteraciones",
                                  "ACO-4: mejor en", "ACO-4: cortó por tiempo"], [
        [n, hc[n]["iterations_run"], hc[n]["best_found_at_iteration"], aco[n]["iterations_run"],
         aco[n]["best_found_at_iteration"], "sí" if aco[n]["timed_out"] == "True" else "no"] for n in cases
    ])
    NUM["hc_max_it"], NUM["hc_max_imp"] = (str(int(float(hc["04"][k]))) for k in ("Max_it", "Max_imp"))
    NUM["aco_ants"], NUM["aco_max_it"] = (str(int(float(aco["04"][k]))) for k in ("A_ants", "Max_it"))
    # Inside $...$: a bare decimal comma is spaced like a list separator.
    NUM["aco_alpha"], NUM["aco_beta"] = (es(num(aco["04"][k]), 1).replace(",", "{,}") for k in ("Alpha", "Beta"))
    NUM["hc_01_min"] = es(num(hc["01"]["total_time"]) / 60, 0)
    NUM["aco_01_min"] = es(num(aco["01"]["total_time"]) / 60, 0)
    NUM["aco_max_time_min"] = es(num(aco["04"]["Max_time"]) / 60, 0)
    NUM["aco_route_attempts"] = str(int(float(aco["04"]["Max_route_attempts_per_batch"])))
    NUM["hc_best_at_start"] = str(sum(1 for n in cases if n != "01" and hc[n]["best_found_at_iteration"] == "0"))
    NUM["aco_timed_out"] = ", ".join(n for n in cases if aco[n]["timed_out"] == "True")
    NUM["aco_01_iterations"] = aco["01"]["iterations_run"]
    NUM["hc_01_iterations"] = hc["01"]["iterations_run"]


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
    print(NUM)


if __name__ == "__main__":
    main()
