# OPP-HC tests (opp_hc)

Tests of the Hill Climbing heuristic `models.opp_hc`: multi-picker, no congestion, with picker speeds
and a cold-chain limit, the same problem as `opp_split` and `opp_mono`.

## The problem it solves

A batch's execution time depends on the picker that runs it:

```
T_exec_pb[p, b] = fixed_time(b) + route_time(b) / V_p[p]
fixed_time(b)   = T_setup + T_pick * sum(C_n over b's orders)   # speed-independent
route_time(b)   = T_travel * travel_distance + service_time     # scaled by speed
```

- **Picker speed (`V_p`)**: a `{picker: speed}` dict. A picker missing from it defaults to speed `1.0`.
- **Cold chain (`T_cold`)**: a `(picker, batch)` pair is only eligible if `T_exec_pb[p, b] <= T_cold`,
  like `PB_elig` in `opp_split_stage2_scheduling.zpl`. A batch left with no eligible picker makes the
  instance `"infeasible"` up front (`models/opp_split/utils/cold_chain_validation.py::batches_without_eligible_picker`,
  shared with the other models).
- Default `T_cold = +inf` and unset `V_p` disable both.

There is no congestion between pickers, like in the exact models.

## Structure

```
tests/opp_hc/
├── opp_hc_test_case.py                 # base assertions (picker assignment, workload, no-overlap, cold chain)
├── functional/
│   ├── test_case_functional_instances.py   # the functional cases of the thesis, one test per instance (status checked against the Split)
│   └── test_case_invalid_speed_rejected.py # case 36c: a non-positive picker speed is refused
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
python -m tests.run_suite opp_hc functional
WRITE_RESULTS_CSV=1 python -m tests.run_suite opp_hc functional   # to feed analysis/
WRITE_RESULTS_CSV=1 python -m tests.run_suite opp_hc stress
python -m unittest tests.opp_hc.functional.test_case_invalid_speed_rejected
```
