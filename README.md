# Linear Picking Routing

Implementation of the thesis on the order picking problem (OPP) in a warehouse: jointly deciding how
batches of customer orders are assigned to pickers, in which sequence each picker runs them, and
which route each batch follows through the warehouse graph, so that the weighted completion time
plus the earliness and tardiness penalties is minimized. Pickers have heterogeneous speeds and a
cold-chain limit bounds how long a batch may take.

The formulation follows *A Model for the Joint Optimisation of Order Batching, Batch Assignment
Sequencing and Picking Routing*.

## The four models

| Model | Directory | What it is |
| --- | --- | --- |
| OPP-Split | `models/opp_split/` | Exact, two stages in ZIMPL + SCIP: Stage 1 routes each batch, Stage 2 assigns and sequences. The reference of the comparisons. |
| OPP-Mono | `models/opp_mono/` | Exact, the same problem as one monolithic MIP in ZIMPL + SCIP. |
| OPP-HC | `models/opp_hc/` | Hill Climbing heuristic (Python). |
| OPP-ACO | `models/opp_aco/` | Ant Colony Optimization heuristic (Python). |

All four solve the same cases: the 38 functional cases (37 in `tests/functional_cases/` plus case 38,
which each exact model holds as a test of its own) and the 19 stress scenarios of the thesis.
The exact models are checked against the exact optimum (objective and routes); the heuristics are
checked on the status, and their solutions are verified against OPP-Mono (`verification/`).

## Repository layout

- `models/` — the four models, plus `base/` (abstract `Model`, location graph) and `utils/` (code shared by the heuristics and the pre-solve validations).
- `dtos/` — parameter containers (`ModelDTO`, `SolveModelDTO`, `SolveHCModelDTO`, `SolveAcoModelDTO`, solve results and solution records).
- `observer/` — the Observer pattern: the heuristics notify; each heuristic's `utils/output_handler.py` prints.
- `tests/` — `functional_cases/` and `stress_cases/` hold each case once; each `tests/<model>/` binds a model to them (`bind_cases`) and holds the tests of its own; `shared_scenarios/` has the graphs and scenarios; `infra/` has the runner and helpers; `run_suite.py` is the entry point.
- `results/` — CSVs of the runs: `results/<model>/<functional|stress>/`, studies of a model (`ablation`, `pheromone`, `seeds`, `budget`), `compliance/`, `comparability/` and `equal_time/`.
- `verification/` — checks saved heuristic solutions against OPP-Mono and compares OPP-Split with OPP-Mono.
- `experiments/` — everything that is not a test and reads or produces `results/`, split by who it is for: `common/` (all models: which result files count), `comparison/` (models against each other), `exact/` (OPP-Split and OPP-Mono) and `heuristics/` (OPP-HC, OPP-ACO). See [experiments/README.md](experiments/README.md).
- `scripts/` — repository checks (`check_repo`, `run_all`, `make_stress_smoke`).
- `docs/` — specs, the style guide and the generated reports; `conventions.md` — the binding conventions.

## Documentation

| Where | What |
| --- | --- |
| [models/README.md](models/README.md) | The four models and the code they share; one README per model. |
| [dtos/README.md](dtos/README.md) | The parameter and result containers. |
| [tests/README.md](tests/README.md) | How the cases are shared and how to run them. |
| [results/README.md](results/README.md) | Layout of the result files. |
| [experiments/README.md](experiments/README.md) | Which experiments exist, for which models, and how they work. |
| [verification/README.md](verification/README.md) | Checking the heuristics' solutions against OPP-Mono. |
| [scripts/README.md](scripts/README.md) | Repository checks and CI. |
| [observer/README.md](observer/README.md) | The Observer pattern and who uses it. |
| [docs/README.md](docs/README.md) | The specs, the style guide and the generated reports. |
| [docs/specs/comparabilidad_split_heuristicas.md](docs/specs/comparabilidad_split_heuristicas.md) | Which results of the exact models and the heuristics can be compared. |
| [conventions.md](conventions.md) | The binding conventions. |

## Requirements

Python 3.12+ and `pip install -r requirements.txt` (PySCIPOpt, python-dotenv, pandas).
The exact models also need the `zimpl` binary on the `PATH` (conda-forge package `zimpl`).
Local settings (per-test timeouts, whether to write result CSVs and solutions, whether the heuristics print their full result) come from a `.env`;
copy `.env.example` to change them.

## Running the tests

From the repository root:

```bash
python -m tests.run_suite opp_hc functional
python -m tests.run_suite opp_split stress --id 04
python -m scripts.check_repo
python -m scripts.run_all --collect-only --profile full --tier all
```

`run_suite` runs every test in its own process with a timeout and, with `WRITE_RESULTS_CSV=1`, writes
`results/<model>/<tier>/`. `--id NN` selects one case. See `scripts/README.md` and `tests/README.md`.

## Authors

- Lucia Soria
- Ximena Ebertz
