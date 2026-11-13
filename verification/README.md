# Verification

Checks that the solutions of the heuristics are valid, using OPP-Mono as the single source of truth for the
constraints, and compares the two exact models. Nothing is re-run: everything reads the saved results.

| File | What it does |
| --- | --- |
| `solution_store.py` | Writes/reads a heuristic's solution record (instance + solution) as JSON. The test runner writes one per test when `WRITE_SOLUTIONS=1`, under `results/<model>/<tier>/solutions/<run>/`, linked from the CSV's `solution_file` column. |
| `mono_compliance.py` | Checks one solution against OPP-Mono in three layers: a Python precheck (arcs exist, no revisits, required locations covered, one picker per batch, cold chain, recomputed times and objective, big-M validity); level 1 (routes, assignment and sequence fixed, times free: are the decisions feasible, and what is the best schedule for them); level 2 (completion times fixed too: is the exact reported solution feasible and priced the same). |
| `run_compliance.py` | Checks every saved solution of a results CSV and writes `results/compliance/<model>/<tier>/compliance_<csv name>.csv`. |
| `compare_split_vs_mono.py` | Compares OPP-Split with OPP-Mono test by test (status, objective, and whether routes/assignment/sequence coincide) and writes `results/comparability/compare_split_vs_mono.csv`. |

```bash
python -m verification.run_compliance --model opp_hc --tier functional
python -m verification.compare_split_vs_mono
```

A verdict is `compliant` (prechecks clean, both levels feasible, objective matches), `violations` or `error`
(the check itself could not run). Needs `zimpl` and SCIP.
