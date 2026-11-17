# OPP-ACO

Ant Colony Optimization heuristic for the OPP with picker speeds and a cold-chain limit. No congestion
between pickers, like the exact models.

```python
model = OPPAntColonyOptimization(model_dto)   # ModelDTO: N, B, P, location_graph, start_time
model.attach(OutputHandler())                 # optional Observer
status, output_graph = model.solve(params)    # SolveAcoModelDTO
```

- **Construction.** Each ant builds, batch by batch, a route with pick-to-pick probabilistic construction (pheromone and visibility, after Chen et al. 2013) and then picks the batch's picker with a roulette over the eligible pickers. Routes never revisit a vertex. Each picker's sequence is then ordered by the earliest due date among each batch's orders.
- **Pheromone.** Two tables: route edges and (batch, picker) pairs. MAX-MIN style bounds, evaporation `E` (called `rho` in the pheromone study), deposit `Q`.
- **Local search.** Route local search (2-opt and segment re-routing) on every ant, elite-route polishing, and a first-improvement local search on the schedule of the best solution, with the routes fixed (move a batch into another picker's sequence, swap two batches within a sequence, exchange two batches between pickers) (`COMPONENT_FLAGS` in `experiments/heuristics/aco/aco_study_common.py` switches each component off for the ablation study).
- **Cold chain.** Soft during the search (a large objective penalty), hard on the reported answer. The roulette only considers the pickers that make the ant's own route eligible. The only up-front `"infeasible"` is exact: a batch with no eligible picker even with a route time of 0.
- **Budget.** `A_ants`, `Max_it`, `Max_time`, and `Seed` for reproducibility (`SolveAcoModelDTO`).
- **Execution time.** `T_exec_pb[p, b] = fixed_time(b) + route_time(b) / V_p[p]`, as in the exact models.

| File | What it holds |
| --- | --- |
| `opp_aco.py` | The solver (`OPPAntColonyOptimization`). |
| `utils/route_evaluator.py` | The objective function, speed-aware. |
| `utils/constraints_validator.py` | Hard constraints (base validator) plus the cold-chain checks. |
| `utils/exec_time.py` | `T_exec_pb` for a route and a picker. |
| `utils/output_handler.py` | Observer that prints the result. |

Parameters: `dtos/aco/solve_aco_model_dto.py`. Tests: `tests/opp_aco/` (functional instances of the thesis' cases,
case 36c (`test_case_invalid_speed_rejected.py`), the unreachable-location test and the 19 stress scenarios). Run with
`python -m tests.run_suite opp_aco functional`.
