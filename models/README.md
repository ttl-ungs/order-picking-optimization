# Models

The four models of the thesis. All of them solve the same problem: given batches of orders (`B_nb`),
pickers with heterogeneous speeds (`V_p`) and a cold-chain limit (`T_cold`), decide the route of each
batch, which picker runs each batch and in which sequence, minimizing the weighted completion time plus
the earliness and tardiness penalties. Variable and parameter names follow the thesis (`x_pb`, `c_pb`,
`T_exec_pb`, `W_c`, `W_pen`, ...).

| Model | Directory | Kind | README |
| --- | --- | --- | --- |
| OPP-Split | `opp_split/` | Exact, two ZIMPL stages solved with SCIP | [opp_split/README.md](opp_split/README.md) |
| OPP-Mono | `opp_mono/` | Exact, one monolithic ZIMPL MIP solved with SCIP | [opp_mono/README.md](opp_mono/README.md) |
| OPP-HC | `opp_hc/` | Hill Climbing heuristic | [opp_hc/README.md](opp_hc/README.md) |
| OPP-ACO | `opp_aco/` | Ant Colony Optimization heuristic | [opp_aco/README.md](opp_aco/README.md) |

Shared code:

- `base/` — `Model` (abstract solver with the Observer hooks `attach()` / `notify()`) and `OPPLocationGraph` (directed warehouse graph with depot and final node).
- `utils/` — used by the heuristics: `route_construction.py` (self-avoiding routes through the required locations), `route_solution.py`, `base_constraints_validator.py` and `sla.py`; used by every model: `input_validation.py` (capacity and one-batch-per-order checks before solving), `cold_chain_validation.py` (batches without an eligible picker, non-positive speeds, and the cold-chain tolerance) and `solve_registry.py` (the last solve, read by the test runner to record the objective).

The Python side of the exact models is not in this directory: `tests/infra/zimpl/` writes the `.dat`
files into a temporary workspace (a copy of the `.zpl` next to a `dat_files/` directory, see
`tests/<model>/config.py`) and runs ZIMPL + SCIP (`solve_zpl`), and `tests/opp_split/stage1_decomposition.py` solves
Stage 1 one batch at a time.
