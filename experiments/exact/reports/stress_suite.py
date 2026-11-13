"""The stress suite results of both exact models, paired by test case.

Shared by build_mono_exploration and build_functional_comparison. Each model's
stress CSV is the unified run of its suite (tests 01-19, same numbering and
same instances in both models).
"""
import csv
import os

from experiments.exact.reports.charts import ROOT, es

SPLIT_STRESS = os.path.join(ROOT, "results", "opp_split", "stress",
                            "output_opp_split_stress_tests_parallel.csv")
MONO_STRESS = os.path.join(ROOT, "results", "opp_mono", "stress",
                           "output_opp_mono_stress_tests.csv")

# (short description, lots, grid) per test case, in Spanish for the docs.
SUITE = {
    "01": ("grilla, 30 pickers, 750 órdenes", "30", "100×100"),
    "02": ("grilla, 10 pickers, 100 órdenes", "10", "10×10"),
    "03": ("grilla, 1 picker, 320 órdenes", "40", "7×7"),
    "04": ("realista", "6", "7×7"),
    "05": ("realista", "6", "13×13"),
    "06": ("realista", "6", "14×14"),
    "07": ("realista", "6", "15×15"),
    "08": ("realista", "6", "16×16"),
    "09": ("realista, depósito rectangular", "6", "8×21"),
    "10": ("realista, 4 pickers", "6", "7×7"),
    "11": ("realista, 4 pickers, cadena de frío", "6", "13×13"),
    "12": ("cuadrilla de 4 pickers", "8", "7×7"),
    "13": ("cuadrilla de 5 pickers", "10", "7×7"),
    "14": ("cuadrilla de 6 pickers", "12", "7×7"),
    "15": ("9 pickers para 6 lotes", "6", "10×10"),
    "16": ("12 pickers, una ola", "12", "10×10"),
    "17": ("12 pickers", "15", "10×10"),
    "18": ("12 pickers", "18", "10×10"),
    "19": ("12 pickers, dos lotes cada uno", "24", "10×10"),
}


def _load(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return {r["test"].split(".")[0]: r for r in csv.DictReader(fh)}


def results():
    """[(case, desc, lots, grid, split_status, split_minutes, mono_status)] for tests 01-19."""
    split, mono = _load(SPLIT_STRESS), _load(MONO_STRESS)
    out = []
    for n, (desc, lots, grid) in SUITE.items():
        case = f"test_case_{n}"
        s = split[case]
        minutes = float(s["total_time"]) / 60 if s["status"] == "ok" else None
        out.append((n, desc, lots, grid, s["status"], minutes, mono[case]["status"]))
    return out


STATUS = {"ok": "resuelto", "timeout": "timeout", "no_result": "sin resultado"}


def table_rows():
    """Rows for the Caso / Instancia / Lotes / Grilla / Split / Mono table."""
    rows = []
    for n, desc, lots, grid, s_status, minutes, m_status in results():
        split_cell = f"{es(minutes, 1)} min" if minutes is not None else STATUS[s_status]
        rows.append([n, desc, lots, grid, split_cell, STATUS[m_status]])
    return rows


def stress_table():
    """The suite as a ConTeXt table, one row per test case."""
    header = ["Caso", "Instancia", "Lotes", "Grilla", "Split", "Mono"]
    lines = ["\\blank[medium]", "\\bTABLE[split=yes, align=middle, frame=on]",
             "\\setupTABLE[row][1][background=color, backgroundcolor=darkgray, style=bold]",
             "\\bTR " + " ".join(f"\\bTH {h} \\eTH" for h in header) + " \\eTR"]
    lines += ["\\bTR " + " ".join(f"\\bTD {c} \\eTD" for c in r) + " \\eTR" for r in table_rows()]
    lines += ["\\eTABLE", "\\blank[medium]"]
    return "\n".join(lines)


def counts():
    r = results()
    return {
        "stress_split_ok": str(sum(1 for x in r if x[4] == "ok")),
        "stress_mono_ok": str(sum(1 for x in r if x[6] == "ok")),
        "stress_total": str(len(r)),
        "stress_split_max": es(max(x[5] for x in r if x[5] is not None), 1),
    }
