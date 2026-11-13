"""Check every solution saved by a test run against opp_mono.

Reads a results CSV written with WRITE_RESULTS_CSV=1 WRITE_SOLUTIONS=1 (its
solution_file column links one JSON per test), checks each solution with
verification.mono_compliance, and writes one row per test to
results/compliance/<model>/<tier>/compliance_<csv name>.csv. Nothing is
re-run: only the saved solutions are checked.

Usage:
    python -m verification.run_compliance --model opp_hc --tier functional
        (latest CSV of that model/tier that has a solution_file column)
    python -m verification.run_compliance results/opp_aco/stress/output_....csv
    ... [--test realistic_crew] [--time-limit 300] [--keep-workdir DIR] [--resume]
"""

import argparse
import csv
import glob
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dtos.verification.compliance_report_dto import ComplianceReportDTO
from verification.mono_compliance import check_compliance
from verification.solution_store import read_solution_record

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
csv.field_size_limit(2**31 - 1)

# Verdicts about the solution itself; "error" means the check didn't run.
FINAL_VERDICTS = ("compliant", "violations", "skipped")


def _has_solutions(csv_path):
    with open(csv_path, newline="", encoding="utf-8") as f:
        return "solution_file" in (next(csv.reader(f), None) or [])


def _latest_csv(model, tier):
    candidates = sorted(glob.glob(os.path.join(PROJECT_ROOT, "results", model, tier, "output_*.csv")))
    with_solutions = [c for c in candidates if _has_solutions(c)]
    if not with_solutions:
        raise SystemExit(
            f"No CSV with a solution_file column under results/{model}/{tier}/ -- "
            "run the suite with WRITE_RESULTS_CSV=1 WRITE_SOLUTIONS=1 first."
        )
    # Filenames end in _YYYYMMDD_HHMMSS: lexicographic order is chronological.
    return with_solutions[-1]


def _output_path(csv_path):
    rel = os.path.relpath(os.path.abspath(csv_path), os.path.join(PROJECT_ROOT, "results"))
    parts = rel.replace(os.sep, "/").split("/")
    model, tier = (parts[0], parts[1]) if len(parts) >= 3 else ("unknown", "unknown")
    name = os.path.splitext(os.path.basename(csv_path))[0]
    return os.path.join(PROJECT_ROOT, "results", "compliance", model, tier, f"compliance_{name}.csv")


def _skipped(row, reason):
    report = ComplianceReportDTO(row["test"], "")
    report.verdict = "skipped"
    report.notes.append(reason)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv", nargs="?", help="Results CSV with a solution_file column.")
    parser.add_argument("--model", help="With --tier: use the latest CSV with solutions of this model.")
    parser.add_argument("--tier", choices=["functional", "stress"])
    parser.add_argument(
        "--test",
        help="Only check tests whose id contains this text (the other rows of an existing report are kept).",
    )
    parser.add_argument("--time-limit", type=float, default=300.0, help="SCIP time limit per solve (s).")
    parser.add_argument("--keep-workdir", help="Keep each test's .dat/.lp files under this directory.")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Keep the rows of an existing compliance CSV for this run and check only the rest "
        "(rows whose check errored are checked again).",
    )
    args = parser.parse_args(argv)

    if args.csv:
        csv_path = args.csv
    elif args.model and args.tier:
        csv_path = _latest_csv(args.model, args.tier)
    else:
        parser.error("give a CSV path, or --model and --tier")

    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if rows and "solution_file" not in rows[0]:
        raise SystemExit(f"{csv_path} has no solution_file column (run with WRITE_SOLUTIONS=1).")

    out_path = _output_path(csv_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fieldnames = list(ComplianceReportDTO("", "").to_csv_row().keys())

    # Rows of an existing compliance CSV that this run keeps as they are:
    #   --test   : every test outside the filter (a filtered run only
    #              replaces the rows it re-checks).
    #   --resume : every row that already has a verdict about the solution;
    #              "error" rows (the check itself failed) are checked again.
    existing = []
    if os.path.exists(out_path):
        with open(out_path, newline="", encoding="utf-8") as f:
            existing = list(csv.DictReader(f))
    selected = [r for r in rows if not args.test or args.test in r["test"]]
    selected_ids = {r["test"] for r in selected}
    kept = [
        r for r in existing
        if (args.test and r["test"] not in selected_ids)
        or (args.resume and r.get("verdict") in FINAL_VERDICTS)
    ]
    done = {r["test"] for r in kept}
    pending = [r for r in selected if r["test"] not in done]

    print(
        f"Checking {len(pending)} test(s) from {os.path.relpath(csv_path, PROJECT_ROOT)} against opp_mono"
        + (f" ({len(kept)} row(s) kept from the existing report)" if kept else ""),
        flush=True,
    )
    counts = {}
    for r in kept:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1

    # Header + already-checked rows first, then one row per test as soon as
    # it's checked (flushed), so a cut run leaves every finished row on disk.
    with open(out_path, "w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=fieldnames)
        writer.writeheader()
        for r in kept:
            writer.writerow({k: r.get(k) for k in fieldnames})
        out.flush()

        for index, row in enumerate(pending, 1):
            print(f"  ({index}/{len(pending)}) {row['test']} ...", flush=True)
            solution_file = (row.get("solution_file") or "").strip()
            if not solution_file:
                report = _skipped(row, f"no saved solution (test status: {row.get('status')})")
            elif solution_file.startswith("ERROR"):
                report = _skipped(row, f"solution was not saved: {solution_file}")
            else:
                meta, instance, solution = read_solution_record(os.path.join(PROJECT_ROOT, solution_file))
                workdir = None
                if args.keep_workdir:
                    workdir = os.path.join(args.keep_workdir, row["test"])
                    os.makedirs(workdir, exist_ok=True)
                report = check_compliance(meta, instance, solution, args.time_limit, workdir)
            writer.writerow(report.to_csv_row())
            out.flush()
            counts[report.verdict] = counts.get(report.verdict, 0) + 1
            time_str = f"{report.check_time:.1f}s" if report.check_time is not None else "-"
            print(
                f"      [{report.verdict}] L1={report.level1_status} L2={report.level2_status} ({time_str})"
                + (f"  {report.error}" if report.error else ""),
                flush=True,
            )

    print("\n" + ", ".join(f"{v}: {c}" for v, c in sorted(counts.items())))
    print(f"✅ Compliance report: {os.path.relpath(out_path, PROJECT_ROOT)}")
    sys.exit(0 if counts.get("violations", 0) == 0 and counts.get("error", 0) == 0 else 1)


if __name__ == "__main__":
    main()
