# Observer

`observer.py` defines `Observer`, the abstract receiver of the Observer pattern. A `Model`
(`models/base/model.py`, the base class of the heuristics) keeps the observers given to `attach()` and,
at the end of `solve()`, calls their `update()` through `notify()` with the full `solution_info`.

Observers in the repository:

- `SolutionInfoCapture` in `tests/infra/cases/heuristic_model_case.py` (the heuristics' functional and stress test cases) — keeps the notified `solution_info` so the tests can assert on the assignment, the schedule and the cold chain.
- `OutputHandler` in `models/opp_hc/utils/output_handler.py` and `models/opp_aco/utils/output_handler.py` — prints the full result. Attach it when you want that report (see the models' READMEs). The test runner attaches it to every solver the tests create when `PRINT_RESULTS=1` (see `.env.example`), through `Model.attach_to_new_instances()`, since the tests build their solvers themselves.

The solvers also print on their own, outside the Observer: the reason when they return `"infeasible"`,
and a one-line summary (execution time, iterations, final objective) before notifying.

The exact models run through ZIMPL + SCIP from `tests/infra/zimpl/` and do not use it.
