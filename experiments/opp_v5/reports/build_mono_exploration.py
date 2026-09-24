"""Build docs/thesis/opp_v5_1_mono_exploration.tex from studies 04, 05 and 08 to 11.

    python -m experiments.opp_v5.reports.build_mono_exploration

Fills each %%FIG:id%% marker of mono_exploration_template.tex with a MetaPost chart.
Compile the output with `context` from docs/thesis/.
"""
import csv
import glob
import math
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from experiments.opp_v5.reports.charts import Chart, ROOT, STUDIES as S, es, log_ticks
from experiments.opp_v5.reports.stress_suite import counts, stress_table

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mono_exploration_template.tex")
OUT = os.path.join(ROOT, "docs", "thesis", "opp_v5_1_mono_exploration.tex")


def load(pattern):
    path = sorted(glob.glob(os.path.join(S, pattern)))[-1]
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def num(r, k):
    v = r.get(k, "")
    return float(v) if v not in ("", None) else None


def pairs(rows):
    split = {r["label"]: r for r in rows if r["model"] == "split"}
    mono = {r["label"]: r for r in rows if r["model"] == "mono"}
    return split, mono


def build_figures():
    """Every chart of the report, keyed by its %%FIG:id%% marker."""
    f08 = load("08_mono_frontier/frontier_*.csv")
    f09 = load("09_shared_with_split/points_*.csv")
    sp08, mo08 = pairs(f08)
    sp09, mo09 = pairs(f09)

    FIG = {}

    # 1. Frontier map: batches x side, one cell per point.
    BATCHES, SIDES = [1, 2, 3, 4, 6], [3, 4, 5, 6, 7]
    cw, ch = 2.35, 0.9
    out = [f"numeric cw, ch; cw := {cw}cm; ch := {ch}cm;"]
    for i, b in enumerate(BATCHES):
        y = (len(BATCHES) - 1 - i) * ch
        out.append(f'label.lft(textext("\\tfx {b} lote{"s" if b > 1 else ""}"), (-0.1cm,{y + ch / 2:.3f}cm));')
        for j, s in enumerate(SIDES):
            x = j * cw
            r = mo08.get(f"B{b}S{s}")
            box = f"({x + 0.05:.3f}cm,{y + 0.05:.3f}cm)--({x + cw - 0.05:.3f}cm,{y + 0.05:.3f}cm)--({x + cw - 0.05:.3f}cm,{y + ch - 0.05:.3f}cm)--({x + 0.05:.3f}cm,{y + ch - 0.05:.3f}cm)--cycle"
            c = f"({x + cw / 2:.3f}cm,{y + ch / 2:.3f}cm)"
            status = r["status"] if r else "skipped"
            if status == "optimal":
                out.append(f"fill {box} withcolor \\MPcolor{{darkblue}};")
                out.append(f'draw textext("\\tfx {es(num(r, "total_s"))} s") shifted {c} withcolor white;')
            elif status == "timelimit":
                out.append(f"fill {box} withcolor \\MPcolor{{redline}};")
                out.append(f'draw textext("\\tfx brecha {es(num(r, "gap_pct"))}\\%") shifted {c} withcolor white;')
            elif status == "infeasible":
                out.append(f"draw {box} withpen pencircle scaled .8pt withcolor \\MPcolor{{blueline}};")
                out.append(f'draw textext("\\tfx infactible") shifted {c} withcolor \\MPcolor{{blueline}};')
            else:
                out.append(f"draw {box} withpen pencircle scaled .5pt dashed evenly;")
                out.append(f'draw textext("\\tfx no se corrió") shifted {c};')
    for j, s in enumerate(SIDES):
        out.append(f'label.bot(textext("\\tfx {s}×{s}"), ({j * cw + cw / 2:.3f}cm,-0.05cm));')
    FIG["frontera"] = "\\startMPcode\n" + "\n".join(out) + "\n\\stopMPcode"

    # 2. Mono / split time ratio vs side, one line per batch count.
    c = Chart(2.5, 7.5, 0.1, 1000, logy=True, h=6)
    c.axes([(s, f"{s}×{s}") for s in SIDES], [(0.1, "0,1"), (1, "1"), (10, "10"), (100, "100"), (1000, "1.000")],
           "Grilla", "Tiempo de mono / tiempo de split")
    c.hline(1, "igual tiempo", at="right")
    colors = {2: "darkblue", 3: "redline", 4: "blueline"}
    for b, color in colors.items():
        pts, capped = [], []
        for s in SIDES:
            m, sp = mo08.get(f"B{b}S{s}"), sp08.get(f"B{b}S{s}")
            if not m or not sp or m["status"] in ("skipped", "infeasible") or sp["status"] != "optimal":
                continue
            ratio = num(m, "total_s") / num(sp, "total_s")
            pts.append((s, ratio))
            if m["status"] != "optimal":
                capped.append((s, ratio))
        c.line(pts, color)
        for s, ratio in capped:
            c.open_dot(s, ratio, color)
            c.note(s, ratio, "$\\geq$", "rt", dx=0.1)
    c.legend([("darkblue", "2 lotes", "line"), ("redline", "3 lotes", "line"), ("blueline", "4 lotes", "line"),
              ("darkblue", "mono cortado a los 10 min (cota inferior)", "open")])
    FIG["ratio"] = c.code()

    # 3. Incumbent trajectories of the points mono did not close.
    def trajectory(r):
        ref = num(r, "ref_obj")
        pts = []
        for item in (r.get("incumbents") or "").split(";"):
            if ":" in item:
                t, obj = item.split(":")
                pts.append((max(float(t), 1.0), (float(obj) - ref) / ref * 100))
        return pts

    def X(t):
        return math.log10(t)

    c = Chart(0, math.log10(600), 0, 20, h=5.5)
    c.axes([(X(v), lab) for v, lab in ((1, "1"), (10, "10"), (100, "100"), (600, "600"))],
           [(v, f"{v}\\%") for v in (0, 5, 10, 15, 20)], "Segundos (escala logarítmica)", "Mejor solución sobre el óptimo")
    for label, color in (("B3S7", "darkblue"), ("B4S6", "redline"), ("B6S5", "blueline")):
        r = mo08[label]
        pts = trajectory(r)
        steps = []
        for k, (t, v) in enumerate(pts):
            if k:
                steps.append((X(t), pts[k - 1][1]))
            steps.append((X(t), min(v, 20)))
        steps.append((X(num(r, "total_s")), min(pts[-1][1], 20)))
        c.line(steps, color, markers=False)
        for t, v in pts:
            c.dot(X(t), min(v, 20), color)
    c.legend([("darkblue", "3 lotes, 7×7", "line"), ("redline", "4 lotes, 6×6", "line"), ("blueline", "6 lotes, 5×5", "line")], x=6.5)
    FIG["trayectoria"] = c.code()

    # 4. Root bound: split Stage 2 vs mono, same instance.
    c = Chart(30, 100, 30, 100, w=8, h=8)
    c.axes([(v, f"{v}\\%") for v in (30, 50, 70, 90, 100)], [(v, f"{v}\\%") for v in (30, 50, 70, 90, 100)],
           "Cota raíz de split (Etapa 2)", "Cota raíz de mono")
    c.line([(30, 30), (100, 100)], "blueline", dashed=True, markers=False)
    for sp, mo, color in ((sp08, mo08, "darkblue"), (sp09, mo09, "redline")):
        for label, m in mo.items():
            s = sp.get(label)
            if not s or s["status"] != "optimal" or num(s, "root_dual") is None or num(m, "root_dual_ratio_pct") is None:
                continue
            c.dot(num(s, "root_dual") / num(s, "obj") * 100, num(m, "root_dual_ratio_pct"), color)
    for label, dx, pos in (("s01-warehouse-10", 0.1, "rt"), ("s03-tiers-3", 0.1, "rt"), ("s03-tiers-2", 0.1, "rt")):
        s, m = sp09[label], mo09[label]
        c.note(num(s, "root_dual") / num(s, "obj") * 100, num(m, "root_dual_ratio_pct"),
               {"s01-warehouse-10": "10×10", "s03-tiers-3": "3 bandas", "s03-tiers-2": "2 bandas"}[label], pos, dx=dx)
    s, m = sp08["B6S5"], mo08["B6S5"]
    c.note(num(s, "root_dual") / num(s, "obj") * 100, num(m, "root_dual_ratio_pct"), "6 lotes, 5×5", "rt", dx=0.1)
    c.legend([("darkblue", "estudio 08", "dot"), ("redline", "estudio 09", "dot"), ("blueline", "igual cota", "dashed")], x=0.3, top=7.85)
    FIG["raiz"] = c.code()

    # 5. Shared cases: split time vs mono (capped), log.
    SHORT = [("s01-orders-10", "o10"), ("s01-orders-14", "o14"), ("s01-orders-18", "o18"), ("s01-orders-22", "o22"),
             ("s01-orders-26", "o26"), ("s01-pickers-3", "p3"), ("s01-pickers-4", "p4"), ("s01-pickers-5", "p5"),
             ("s01-warehouse-10", "g10"), ("s02-w26-orders-10", "w10"), ("s02-w26-orders-18", "w18"),
             ("s02-w26-orders-26", "w26"), ("s03-spread-26", "vd"), ("s03-tiers-2", "b2"), ("s03-tiers-3", "b3")]
    c = Chart(0, len(SHORT), 1, 1000, logy=True, w=14, h=6)
    c.cat_axes([(i + 0.5, short) for i, (_, short) in enumerate(SHORT)], log_ticks(0, 3), "Tiempo (s)")
    for i, (label, _) in enumerate(SHORT):
        s, m = sp09[label], mo09[label]
        c.bar(i + 0.12, 0.36, 1, num(s, "total_s"), "darkblue")
        c.bar(i + 0.52, 0.36, 1, num(m, "total_s"), "redline", outline=True)
        txt = f"{es(num(m, 'gap_pct'), 0)}\\%" if num(m, "gap_pct") is not None else "s/sol."
        c.note(i + 0.7, num(m, "total_s"), txt, "top", dy=0.02)
    c.legend([("darkblue", "split: óptimo", "box"), ("redline", "mono: cortado a los 300 s (etiqueta: brecha)", "outline")], x=0.2, top=7.0)
    FIG["compartidos"] = c.code()

    # 6. Where mono's bounds end, as a share of the optimum (shared cases).
    c = Chart(0, len(SHORT), 30, 110, w=14, h=6)
    c.cat_axes([(i + 0.5, short) for i, (_, short) in enumerate(SHORT)],
               [(v, f"{v}\\%") for v in (30, 50, 70, 90, 100, 110)], "Proporción del óptimo")
    c.hline(100, "óptimo (split)", at="right")
    for i, (label, _) in enumerate(SHORT):
        m = mo09[label]
        dual = num(m, "dual_ratio_pct")
        best = num(m, "best_gap_to_opt_pct")
        x = i + 0.5
        if best is not None:
            c.line([(x, dual), (x, 100 + best)], "darkblue", markers=False)
            c.dot(x, 100 + best, "redline")
        else:
            c.note(x, dual, "s/sol.", "bot", dy=-0.1)
        c.dot(x, dual, "darkblue")
    c.legend([("darkblue", "cota dual de mono", "dot"), ("redline", "mejor solución de mono", "dot")], x=0.2, top=1.4)
    FIG["cotas"] = c.code()

    # 7. Model size vs time (mono, study 08 + 09).
    c = Chart(2, math.log10(6000), -1, 3, h=5.5)
    def LX(v):
        return math.log10(v)
    c.axes([(LX(v), es(v, 0)) for v in (100, 300, 1000, 3000)],
           [(e, lab) for e, lab in ((-1, "0,1"), (0, "1"), (1, "10"), (2, "100"), (3, "1.000"))],
           "Variables del modelo monolítico (escala log.)", "Tiempo de mono (s, escala log.)")
    for rows in (mo08, mo09):
        for m in rows.values():
            if m["status"] in ("skipped", "infeasible") or num(m, "n_vars") is None:
                continue
            x, y = LX(num(m, "n_vars")), math.log10(max(num(m, "total_s"), 0.1))
            if m["status"] == "optimal":
                c.dot(x, y, "darkblue")
            else:
                c.open_dot(x, y, "redline")
    c.legend([("darkblue", "llegó al óptimo", "dot"), ("redline", "cortado por tiempo", "open")])
    FIG["tamano"] = c.code()


    # ---------------------------------------------------------------- study 10
    f10 = load("10_mono_scale_axes/points_*.csv")
    sp10, mo10 = pairs(f10)


    def both_times(chart, points, xs):
        """Split and mono total time over one axis; open marker where mono was cut off."""
        chart.line([(x, num(sp10[l], "total_s")) for l, x in zip(points, xs)], "darkblue")
        chart.line([(x, num(mo10[l], "total_s")) for l, x in zip(points, xs)], "redline")
        for l, x in zip(points, xs):
            if mo10[l]["status"] != "optimal":
                chart.open_dot(x, num(mo10[l], "total_s"), "redline")
                chart.note(x, num(mo10[l], "total_s"), f"brecha {es(num(mo10[l], 'gap_pct'))}\\%", "lft", dx=-0.1)


    LEG = [("darkblue", "split", "line"), ("redline", "mono", "line")]

    # Orders per batch, weights 4/4 and 2/6.
    c = Chart(8, 52, 1, 1000, logy=True, h=5.5)
    c.axes([(v, str(v)) for v in (10, 20, 30, 40, 50)], log_ticks(0, 3), "Órdenes por lote", "Tiempo (s)")
    orders_pts = ["orders-10", "orders-14", "orders-18", "orders-22", "base", "orders-32", "orders-40", "orders-50"]
    both_times(c, orders_pts, [10, 14, 18, 22, 26, 32, 40, 50])
    w_pts = ["weights26-orders-10", "weights26-orders-26", "weights26-orders-50"]
    c.line([(x, num(sp10[l], "total_s")) for l, x in zip(w_pts, (10, 26, 50))], "darkblue", dashed=True)
    c.line([(x, num(mo10[l], "total_s")) for l, x in zip(w_pts, (10, 26, 50))], "redline", dashed=True)
    c.legend([("darkblue", "split, pesos 4/4", "line"), ("redline", "mono, pesos 4/4", "line"),
              ("darkblue", "split, pesos 2/6", "dashed"), ("redline", "mono, pesos 2/6", "dashed")], x=6.5)
    FIG["m10_ordenes"] = c.code()

    # Grid side.
    c = Chart(2.5, 7.5, 1, 1000, logy=True, h=5)
    c.axes([(s, f"{s}×{s}") for s in (3, 5, 6, 7)], log_ticks(0, 3), "Grilla", "Tiempo (s)")
    both_times(c, ["side-3", "base", "side-6", "side-7"], [3, 5, 6, 7])
    c.legend(LEG)
    FIG["m10_grilla"] = c.code()

    # Batches and pickers, side by side on one axis each.
    c = Chart(1.5, 6.5, 1, 1000, logy=True, h=5)
    c.axes([(b, str(b)) for b in (2, 3, 4, 5, 6)], log_ticks(0, 3), "Lotes (2 pickers, 5×5)", "Tiempo (s)")
    both_times(c, ["batches-2", "batches-3", "base", "batches-5", "batches-6"], [2, 3, 4, 5, 6])
    c.legend(LEG)
    FIG["m10_lotes"] = c.code()

    c = Chart(0.5, 4.5, 1, 1000, logy=True, h=5)
    c.axes([(p, str(p)) for p in (1, 2, 3, 4)], log_ticks(0, 3), "Pickers (4 lotes, 5×5)", "Tiempo (s)")
    both_times(c, ["pickers-1", "base", "pickers-3", "pickers-4"], [1, 2, 3, 4])
    c.legend(LEG)
    FIG["m10_pickers"] = c.code()

    # Speeds: grouped bars by crew size.
    SPEED = [("base", "2P unif."), ("speeds-spread-p2", "2P distintas"), ("pickers-3", "3P unif."),
             ("speeds-tiers2-p3", "3P 2 bandas"), ("speeds-tiers3-p3", "3P 3 bandas"),
             ("pickers-4", "4P unif."), ("speeds-tiers2-p4", "4P 2 bandas")]
    c = Chart(0, len(SPEED), 1, 1000, logy=True, w=13, h=5)
    c.cat_axes([(i + 0.5, short) for i, (_, short) in enumerate(SPEED)], log_ticks(0, 3), "Tiempo (s)")
    for i, (label, _) in enumerate(SPEED):
        c.bar(i + 0.12, 0.36, 1, num(sp10[label], "total_s"), "darkblue")
        c.bar(i + 0.52, 0.36, 1, num(mo10[label], "total_s"), "redline", outline=mo10[label]["status"] != "optimal")
        if mo10[label]["status"] != "optimal":
            c.note(i + 0.7, num(mo10[label], "total_s"), "tope", "top", dy=0.02)
    c.legend([("darkblue", "split", "box"), ("redline", "mono (contorno: no cerró)", "box")], x=0.2, top=4.85)
    FIG["m10_velocidades"] = c.code()

    # <= 1: with and without, both models.
    c = Chart(0, 2, 1, 1000, logy=True, h=5)
    c.cat_axes([(0.5, "5×5"), (1.5, "6×6")], log_ticks(0, 3), "Tiempo (s)")
    for gi, (with_le1, without) in enumerate((("base", "no-le1-base"), ("side-6", "no-le1-side-6"))):
        for k, (label, model, outline) in enumerate(((with_le1, sp10, False), (without, sp10, True),
                                                     (with_le1, mo10, False), (without, mo10, True))):
            color = "darkblue" if model is sp10 else "redline"
            x0 = gi + 0.08 + k * 0.21
            c.bar(x0, 0.19, 1, num(model[label], "total_s"), color, outline)
            c.note(x0 + 0.095, num(model[label], "total_s"), f"{es(num(model[label], 'total_s'), 0)} s", "top", dy=0.02)
    c.legend([("darkblue", "split con $\\leq 1$", "box"), ("darkblue", "split sin $\\leq 1$", "outline"),
              ("redline", "mono con $\\leq 1$", "box"), ("redline", "mono sin $\\leq 1$", "outline")], x=0.2, top=4.85)
    FIG["m10_le1"] = c.code()

    # ---------------------------------------------------------------- study 11
    f11 = load("11_mono_long_cap/points_*.csv")
    sp11, mo11 = pairs(f11)
    m0 = next(r for r in load("05_realistic_calibration/round1_*.csv") if r["label"] == "M0")
    LONG = [("B3S7", "3 lotes, 7×7"), ("B4S6", "4 lotes, 6×6"), ("B6S5", "6 lotes, 5×5"), ("test04", "test 04")]

    # Dual bound as a share of the optimum: at the root, at 10 min (08) and at 40 min (11).
    def dual_at_10(label):
        if label == "test04":  # 10 min not measured; M0 is the same instance at 25 min
            ref = num(sp11["test04"], "obj")
            return num(m0, "obj") / (1 + num(m0, "gap_pct") / 100) / ref * 100
        return num(mo08[label], "dual_ratio_pct")

    c = Chart(0, len(LONG), 0, 100, w=12, h=5.5)
    c.cat_axes([(i + 0.5, lab) for i, (_, lab) in enumerate(LONG)], [(v, f"{v}\\%") for v in (0, 25, 50, 75, 100)],
               "Cota dual / óptimo")
    for i, (label, _) in enumerate(LONG):
        m = mo11[label]
        values = ((num(m, "root_dual_ratio_pct"), "redline", True), (dual_at_10(label), "blueline", False),
                  (num(m, "dual_ratio_pct"), "darkblue", False))
        for k, (v, color, outline) in enumerate(values):
            x0 = i + 0.1 + k * 0.27
            c.bar(x0, 0.25, 0, v, color, outline)
            c.note(x0 + 0.125, v, f"{es(v, 0)}\\%", "top", dy=0.03)
    c.legend([("redline", "nodo raíz", "outline"), ("blueline", "a los 10 min (test 04: a los 25)", "box"),
              ("darkblue", "a los 40 min", "box")], x=0.2, top=7.1)
    FIG["m11_cotas"] = c.code()

    # Incumbent trajectories over the full 40 minutes.
    c = Chart(0, math.log10(2400), 0, 20, h=5.5)
    c.axes([(X(v), lab) for v, lab in ((1, "1"), (10, "10"), (100, "100"), (1000, "1.000"), (2400, "2.400"))],
           [(v, f"{v}\\%") for v in (0, 5, 10, 15, 20)], "Segundos (escala logarítmica)", "Mejor solución sobre el óptimo")
    styles = {"B3S7": ("darkblue", False), "B4S6": ("redline", False), "B6S5": ("blueline", False), "test04": ("darkblue", True)}
    for label, _ in LONG:
        r = mo11[label]
        pts = trajectory(r)
        color, dashed = styles[label]
        steps = []
        for k, (t, v) in enumerate(pts):
            if k:
                steps.append((X(t), min(pts[k - 1][1], 20)))
            steps.append((X(t), min(v, 20)))
        steps.append((X(num(r, "total_s")), min(pts[-1][1], 20)))
        c.line(steps, color, dashed=dashed, markers=False)
    c.legend([("darkblue", "3 lotes, 7×7", "line"), ("redline", "4 lotes, 6×6", "line"),
              ("blueline", "6 lotes, 5×5 (demostró el óptimo a los 32 min)", "line"),
              ("darkblue", "test 04 (6 lotes, 7×7)", "dashed")], x=6.4)
    FIG["m11_trayectoria"] = c.code()

    return FIG


def main():
    text = open(TEMPLATE, encoding="utf-8").read()
    used = set(re.findall(r"%%FIG:(\w+)%%", text))
    figures = build_figures()
    assert used == set(figures), (used ^ set(figures))
    for key, code in figures.items():
        text = text.replace(f"%%FIG:{key}%%", code)
    text = text.replace("%%TABLE:stress%%", stress_table())
    for key, value in counts().items():
        text = text.replace(f"%%NUM:{key}%%", value)
    left = re.findall(r"%%\w+:\w+%%", text)
    assert not left, left
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(f"wrote {OUT} with {len(figures)} charts")


if __name__ == "__main__":
    main()
