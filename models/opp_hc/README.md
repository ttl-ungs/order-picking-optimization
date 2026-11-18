# OPP-HC

Hill Climbing heuristic for the OPP with picker speeds and a cold-chain limit. No congestion between
pickers, like the exact models.

```python
model = OPPHillClimbing(model_dto)      # ModelDTO: N, B, P, location_graph, start_time
model.attach(OutputHandler())           # optional Observer
status, output_graph = model.solve(params)   # SolveHCModelDTO
```

- **Search.** Stochastic first-improvement hill climbing: each iteration draws one random move and one random neighbor and accepts it only if it lowers the cost. Moves: best 2-opt reversal of a batch's route, reassign a batch to another picker, swap two batches in a picker's sequence.
- **Initial solution.** A portfolio of route constructions (`models/utils/route_construction.py`).
- **Cold chain.** Soft during the search (a large cost penalty), hard on the reported answer: a solution is only returned if every batch is compliant. The only up-front `"infeasible"` is exact: a batch with no eligible picker even with a route time of 0.
- **Budget.** `Max_it`, `Max_imp` and `Max_time` in `SolveHCModelDTO`; `Seed` makes a run reproducible.
- **Execution time.** `T_exec_pb[p, b] = fixed_time(b) + route_time(b) / V_p[p]`, as in the exact models.

| File | What it holds |
| --- | --- |
| `opp_hc.py` | The solver (`OPPHillClimbing`). |
| `utils/route_evaluator.py` | The objective function, speed-aware. |
| `utils/constraints_validator.py` | Hard constraints (base validator) plus the cold-chain checks. |
| `utils/output_handler.py` | Observer that prints the result. |

Parameters: `dtos/hc/solve_hc_model_dto.py`. Tests: `tests/opp_hc/` (functional instances of the thesis' cases,
case 36c and the 19 stress scenarios). Run with `python -m tests.run_suite opp_hc functional`.
