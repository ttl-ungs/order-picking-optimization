# Observer

`observer.py` defines `Observer`, the abstract receiver of the Observer pattern. A `Model`
(`models/base/model.py`, the base class of the heuristics) keeps the observers given to `attach()` and
calls their `update()` from `notify()`; the model never prints by itself.

Observers in the repository:

- `models/opp_hc/utils/output_handler.py` and `models/opp_aco/utils/output_handler.py` — print the result.
- `SolutionInfoCapture` in `tests/opp_hc/opp_hc_test_case.py` and `tests/opp_aco/opp_aco_test_case.py` — keeps the notified `solution_info` so the tests can assert on the assignment, the schedule and the cold chain.

The exact models run through ZIMPL + SCIP from `tests/infra/zimpl/` and do not use it.
