# OPP Hill Climbing v4 Tests (opp_hc)

Test suite for the Hill Climbing heuristic solver `models.opp_hc` - the
picker-speed / cold-chain equivalent of `opp_split` (two-stage ZIMPL model),
built on top of `opp_hc_2` (multi-picker, no congestion).

## What's different vs. opp_hc_2

A batch's execution time is no longer a single `d_b` shared by every
picker. Instead:

```
T_exec_pb[p, b] = fixed_time(b) + route_time(b) / V_p[p]
fixed_time(b)   = T_setup + T_pick * sum(C_n over b's orders)   # speed-independent
route_time(b)   = T_travel * travel_distance + service_time          # scaled by speed
```

- **Picker speed (`V_p`)**: a `{picker: speed}` dict. A picker missing from
  it defaults to speed `1.0` (no-op).
- **Cold chain (`T_cold`)**: a `(picker, batch)` pair is only eligible
  if `T_exec_pb[p, b] <= T_cold`. This restricts which picker a batch
  can be assigned to (x_pb's domain), mirroring
  `opp_split_stage2_scheduling.zpl`'s `PB_elig`. A batch left with zero eligible
  pickers makes the instance `"infeasible"`, short-circuited up front via
  `models/opp_split/utils/cold_chain_validation.py::batches_without_eligible_picker`
  (reused directly, not re-implemented).
- Default `T_cold = +inf` and unset `V_p` disable both extensions (no-op).

**Deliberately no congestion** (unlike `opp_hc_3`): congestion and
picker-speed/cold-chain are orthogonal additions over `opp_hc_2`, and this
model only combines the latter, matching `opp_split` itself (also
congestion-free, see `analysis/config.py`).

## Structure

```
tests/opp_hc/
├── opp_hc_test_case.py           # Base assertions (picker assignment, workload, no-overlap, cold chain)
├── functional/
│   ├── test_case_functional_instances.py         # the functional cases of the thesis, one test per instance (status checked against the Split)
│   └── test_case_invalid_speed_rejected.py # case 36c: a non-positive picker speed is refused
└── stress/
    ├── stress_test_case.py      # adapter: solves a stress scenario with this model and checks the solution
    └── test_stress_cases.py        # binds the 19 shared stress cases (tests/stress_cases) to that adapter
```

The functional tier runs the instances of the thesis' functional cases
(captured from the Split's own tests, see
`tests/infra/factories/functional_instances.py`) and checks that the heuristic's
status matches the Split's; the objective lands in the results CSV. The
stress suite runs `opp_split`'s 19 stress
scenarios instead, file-for-file and with the same method names, so
`analysis/` joins them against v5 by instance name (see
`docs/specs/comparabilidad_split_heuristicas.md`).

`opp_hc` is registered in `analysis/config.py`'s `MODEL_DIRS` (and
deliberately left OUT of `CONGESTION_AWARE_MODELS`).

Its `single_order_params` fixture (needs a `SolveHCModelDTO`) lives in
`tests/shared_scenarios/functional/single_order_params_hc.py`, alongside the
other models' DTO-specific variants -- this model has no `scenarios/` of
its own.

## Running Tests

```bash
python -m tests.run_suite opp_hc functional
WRITE_RESULTS_CSV=1 python -m tests.run_suite opp_hc functional          # to feed analysis/
WRITE_RESULTS_CSV=1 python -m tests.run_suite opp_hc stress
python -m unittest tests.opp_hc.functional.test_case_picker_speed
```
