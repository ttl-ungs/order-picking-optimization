"""Compare opp_split with opp_mono from their saved runs.

Both models solve the same problem (split as two stages, mono as one MIP),
so wherever both finish they must agree on status and objective. This reads
the fixed-name result CSVs and the solution JSONs saved with WRITE_SOLUTIONS
(nothing is re-run) and reports, per test:

  status        both statuses equal?
  objective     both objectives equal (relative tolerance 1e-6)?
  solution      same routes (z_ijb), assignment (x_pb) and per-picker order
                (by c_pb)? Equal objective with a different solution is an
                alternative optimum, not a disagreement.

Functional rows are the cases of the thesis. Stress rows are compared too,
although mono finishes none of them.

--verify-split-stress (opt-in): also check each saved split stress solution
against opp_mono with verification/mono_compliance (split's stages use
mono's constraints, so this only catches an implementation mistake).

Writes results/comparability/compare_split_vs_mono.csv.

Usage:
    python -m verification.compare_split_vs_mono [--verify-split-stress] [--time-limit 300]
"""

import argparse
import csv
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from verification.solution_store import read_zimpl_record

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REL_TOL = 1e-6
csv.field_size_limit(2**31 - 1)

CSVS = {
    ("functional", "opp_split"): "results/opp_split/functional/output_opp_split_functional_tests.csv",
    ("functional", "opp_mono"): "results/opp_mono/functional/output_opp_mono_functional_tests.csv",
    ("stress", "opp_split"): "results/opp_split/stress/output_opp_split_stress_tests_parallel.csv",
    ("stress", "opp_mono"): "results/opp_mono/stress/output_opp_mono_stress_tests.csv",
}
OUT_PATH = os.path.join(PROJECT_ROOT, "results", "comparability", "compare_split_vs_mono.csv")


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _close(a, b):
    return a is not None and b is not None and abs(a - b) <= REL_TOL * max(1.0, abs(a), abs(b))


def _rows(tier, model):
    path = os.path.join(PROJECT_ROOT, CSVS[(tier, model)])
    if not os.path.exists(path):
        return {}
    return {r["test"].split(".")[-1]: r for r in csv.DictReader(open(path, encoding="utf-8"))}


def _group(tier, split_row):
    """The tier of the test: "functional" or "stress"."""
    return tier


def _values(row):
    """All saved variable values of a run (Stage 1 + Stage 2 for split), or None."""
    path = (row.get("solution_file") or "").strip()
    if not path or path.startswith("ERROR"):
        return None
    sol = read_zimpl_record(os.path.join(PROJECT_ROOT, path))["solution"]
    return {**(sol.get("stage1_values") or {}), **(sol.get("values") or {})}


def _stopped_before_stage2(split_row):
    """True when split's saved record is a Stage 1 solve: its pipeline
    returned before solving Stage 2 (an infeasible instance)."""
    path = (split_row.get("solution_file") or "").strip()
    if not path or path.startswith("ERROR"):
        return False
    return "stage1" in read_zimpl_record(os.path.join(PROJECT_ROOT, path)).get("zpl", "")


def _active(values, prefix):
    return {k for k, v in values.items() if k.startswith(prefix) and v > 0.5}


def _sequences(values):
    """picker -> batches in completion order (x_pb = 1, sorted by c_pb)."""
    seq = {}
    for name in _active(values, "x_pb$"):
        _, p, b = name.split("$")
        seq.setdefault(p, []).append((values.get(f"c_pb${p}${b}", 0.0), b))
    return {p: [b for _, b in sorted(items)] for p, items in seq.items()}


def _compare_solutions(split_values, mono_values):
    diffs = []
    if _active(split_values, "z_ijb$") != _active(mono_values, "z_ijb$"):
        diffs.append("routes")
    if _active(split_values, "x_pb$") != _active(mono_values, "x_pb$"):
        diffs.append("assignment")
    elif _sequences(split_values) != _sequences(mono_values):
        diffs.append("order")
    return diffs


def compare(tier):
    split, mono = _rows(tier, "opp_split"), _rows(tier, "opp_mono")
    out = []
    for test in split:
        s, m = split[test], mono.get(test)
        row = {
            "tier": tier, "test": test, "group": _group(tier, s),
            "split_status": s["status"], "mono_status": m["status"] if m else "",
            "split_obj": _num(s["obj_val"]), "mono_obj": _num(m["obj_val"]) if m else None,
            "verdict": "", "detail": "",
        }
        stopped = _stopped_before_stage2(s)
        if stopped:
            # Split's pipeline returns infeasible before Stage 2 (e.g. no
            # picker eligible under the cold chain), so the runner's "last
            # solve" is a Stage 1 batch: its obj_val (a route time) is not
            # an objective of the problem.
            row["split_obj"] = None
        if m is None:
            row["verdict"], row["detail"] = "no_mono_result", "mono has no row for this test"
        elif s["status"] != "ok" or m["status"] != "ok":
            row["verdict"] = "same_status" if s["status"] == m["status"] else "not_both_solved"
            row["detail"] = f"split {s['status']}, mono {m['status']}"
        else:
            so, mo = row["split_obj"], row["mono_obj"]
            if so is None and mo is None:
                row["verdict"] = "both_infeasible"
                row["detail"] = "neither model returned an objective" + (
                    " (split stopped before Stage 2)" if stopped else "")
            elif not _close(so, mo):
                row["verdict"] = "objective_differs"
                row["detail"] = f"split {so}, mono {mo}"
            else:
                sv, mv = _values(s), _values(m)
                if sv is None or mv is None:
                    row["verdict"], row["detail"] = "same_objective", "no saved solution to compare"
                else:
                    diffs = _compare_solutions(sv, mv)
                    row["verdict"] = "same_solution" if not diffs else "alternative_optimum"
                    row["detail"] = "" if not diffs else "differs in " + ", ".join(diffs)
        out.append(row)
    return out


def _split_stress_instance(data):
    """Saved split instance -> the dict shape verification.mono_compliance expects."""
    raw = data["instance"]
    pairs = lambda key: {k: v for k, v in raw.get(key, [])}
    triples = lambda key: {(a, b): v for a, b, v in raw.get(key, [])}
    P = list(raw["P"])
    instance = {k: raw.get(k) for k in ("W_c", "W_pen", "W_e", "W_t", "T_travel", "T_setup", "T_pick",
                                        "C_v", "M", "depot", "final")}
    instance.update(
        N=list(raw["N"]), V=list(raw["V"]), P=P, B=list(raw["B"]),
        E={tuple(e) for e in raw["E"]}, D_ij=triples("D_ij"),
        C_n=pairs("C_n"), T_due_n=pairs("T_due_n"), S_i=pairs("S_i"),
        A_ni=triples("A_ni"), B_nb=triples("B_nb"),
        V_p={p: pairs("V_p").get(p, 1.0) for p in P},
        T_cold=float(raw.get("T_cold", float("inf"))),
        start_time=0.0,
    )
    return instance


def _split_stress_solution(data, instance):
    """Saved split solution -> the heuristic solution shape the verifier reads."""
    sol = data["solution"]
    values = {**(sol.get("stage1_values") or {}), **(sol.get("values") or {})}
    succ = {}
    for name in _active(values, "z_ijb$"):
        _, i, j, b = name.split("$")
        succ.setdefault(b, {})[i] = j
    routes = {}
    for b, nxt in succ.items():
        node, stops = instance["depot"], []
        while node in nxt and len(stops) <= len(nxt):
            node = nxt[node]
            if node != instance["final"]:
                stops.append(node)
        routes[b] = stops
    return {
        "status": sol["status"], "objective_value": sol["objective_value"], "routes": routes,
        "picker_sequences": _sequences(values),
        "batch_times": {},
        "batch_completions": {name.split("$")[1]: v for name, v in values.items() if name.startswith("c_b$")},
        "tardiness": {}, "earliness": {},
    }


def verify_split_stress(time_limit):
    from verification.mono_compliance import check_compliance

    reports = []
    for test, row in _rows("stress", "opp_split").items():
        path = (row.get("solution_file") or "").strip()
        if not path:
            continue
        data = read_zimpl_record(os.path.join(PROJECT_ROOT, path))
        instance = _split_stress_instance(data)
        report = check_compliance({"model": "opp_split", "test": row["test"]}, instance,
                                  _split_stress_solution(data, instance), time_limit)
        print(f"  [{report.verdict}] {test} L1={report.level1_status} L2={report.level2_status}"
              + (f" ({report.error})" if report.error else ""), flush=True)
        reports.append((test, report))
    return reports


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--verify-split-stress", action="store_true",
                        help="Also check each saved split stress solution against opp_mono (opt-in).")
    parser.add_argument("--time-limit", type=float, default=300.0, help="SCIP time limit per solve (s).")
    args = parser.parse_args(argv)

    rows = compare("functional") + compare("stress")
    if args.verify_split_stress:
        print("Verifying split stress solutions against opp_mono:")
        by_test = dict(verify_split_stress(args.time_limit))
        for r in rows:
            if r["tier"] == "stress" and r["test"] in by_test:
                rep = by_test[r["test"]]
                r["detail"] = (r["detail"] + " | " if r["detail"] else "") + f"split vs mono: {rep.verdict}"

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    fields = ["tier", "test", "group", "split_status", "mono_status", "split_obj", "mono_obj", "verdict", "detail"]
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    summary = {}
    for r in rows:
        key = (r["tier"], r["group"])
        summary.setdefault(key, {})
        summary[key][r["verdict"]] = summary[key].get(r["verdict"], 0) + 1
    for (tier, group), counts in sorted(summary.items()):
        print(f"{tier:10} {group:9} " + ", ".join(f"{v}: {c}" for v, c in sorted(counts.items())))
    print(f"✅ {os.path.relpath(OUT_PATH, PROJECT_ROOT)}")
    bad = sum(1 for r in rows if r["verdict"] == "objective_differs")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
