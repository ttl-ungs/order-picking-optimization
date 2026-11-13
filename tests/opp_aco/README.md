# OPP-ACO tests (opp_aco)

Tests of the Ant Colony Optimization heuristic `models.opp_aco`: multi-picker, no congestion, with
picker speeds and a cold-chain limit, the same problem as `opp_split`, `opp_mono` and `opp_hc`.

## The problem it solves

A batch's execution time depends on the picker that runs it:

```
T_exec_pb[p, b] = fixed_time(b) + route_time(b) / V_p[p]
fixed_time(b)   = T_setup + T_pick * sum(C_n over b's orders)   # speed-independent
route_time(b)   = T_travel * travel_distance + service_time     # scaled by speed
```

- **Picker speed (`V_p`)**: a `{picker: speed}` dict. A picker missing from it defaults to speed `1.0`.
  Only `_select_picker`'s roulette is affected; the (batch, picker) pheromone table is unchanged.
- **Cold chain (`T_cold`)**: a `(picker, batch)` pair is only eligible if `T_exec_pb[p, b] <= T_cold`.
  Each ant builds a batch's route before picking its picker, so the candidate pool of
  `_select_picker` is filtered with that ant's own route. A batch that no route and picker can
  make eligible makes the instance `"infeasible"` up front
  (`models/opp_split/utils/cold_chain_validation.py::batches_without_eligible_picker`).
- Default `T_cold = +inf` and unset `V_p` disable both.

There is no congestion between pickers, like in the exact models.

## Structure

```
tests/opp_aco/
├── opp_aco_test_case.py                # base assertions (picker assignment, workload, no-overlap, cold chain)
├── functional/
│   ├── test_case_functional_instances.py         # the functional cases of the thesis, one test per instance (status checked against the Split)
│   ├── test_case_invalid_speed_rejected.py       # case 36c: a non-positive picker speed is refused
│   └── test_case_unreachable_required_location.py # a required location the graph cannot reach -> infeasible
└── stress/
    ├── stress_test_case.py             # adapter: solves a stress scenario with this model and checks the solution
    └── test_stress_cases.py            # binds the 19 shared stress cases (tests/stress_cases) to that adapter
```

The functional tier runs the instances of the functional cases (captured from OPP-Split's own tests,
see `tests/infra/factories/functional_instances.py`) and checks that the heuristic's status matches
the Split's; the objective lands in the results CSV. The stress tier runs the 19 shared stress
cases with the same method names as the other models, so `analysis/` joins them by instance name (see
`docs/specs/comparabilidad_split_heuristicas.md`).

## Running tests

```bash
python -m tests.run_suite opp_aco functional
WRITE_RESULTS_CSV=1 python -m tests.run_suite opp_aco functional   # to feed analysis/
WRITE_RESULTS_CSV=1 python -m tests.run_suite opp_aco stress
python -m unittest tests.opp_aco.functional.test_case_invalid_speed_rejected
```
