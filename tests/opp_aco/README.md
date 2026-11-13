# OPP Ant Colony Optimization v4 Tests (opp_aco)

Test suite for the ACO heuristic solver `models.opp_aco` - the ACO
counterpart of `models.opp_hc` (itself the Hill Climbing counterpart of
`opp_split`'s two-stage ZIMPL model), built on top of `opp_aco_2`
(multi-picker ACO, no congestion).

## What's different vs. opp_aco_2

Same extension as `opp_hc` over `opp_hc_2` -- a batch's execution time
is no longer a single `d_b` shared by every picker:

```
T_exec_pb[p, b] = fixed_time(b) + route_time(b) / V_p[p]
fixed_time(b)   = T_setup + T_pick * sum(C_n over b's orders)   # speed-independent
route_time(b)   = T_travel * travel_distance + service_time          # scaled by speed
```

- **Picker speed (`V_p`)**: a `{picker: speed}` dict. A picker missing from
  it defaults to speed `1.0` (no-op). Only `_select_picker`'s roulette is
  affected -- the (batch, picker) pheromone table itself is unchanged.
- **Cold chain (`T_cold`)**: a `(picker, batch)` pair is only eligible
  if `T_exec_pb[p, b] <= T_cold`. Since each ant builds a batch's
  route BEFORE picking its picker, `_select_picker`'s candidate pool is
  filtered to that ant's OWN just-built route's eligible pickers (exact,
  not an approximation). A globally infeasible batch (no eligible picker
  under ANY achievable route) makes the instance `"infeasible"` up front,
  short-circuited via `models/opp_split/utils/cold_chain_validation.py::
  batches_without_eligible_picker`, fed a greedy nearest-neighbor
  route-time ESTIMATE (built from the same all-pairs shortest-path table
  `opp_aco_2` already precomputes) since ACO has no single deterministic
  route per batch the way `opp_hc`'s construction does.
- Default `T_cold = +inf` and unset `V_p` disable both extensions (no-op).

**Deliberately no congestion** (unlike `opp_aco_3`): congestion and
picker-speed/cold-chain are orthogonal additions over `opp_aco_2`. This
model does NOT adopt `opp_aco_3`'s incremental `CongestionTracker`
reservation or its multi-pheromone (m-ACO4) architecture, matching how
`opp_hc` leaves `opp_hc_3`'s congestion pricing out.

## Structure

```
tests/opp_aco/
├── opp_aco_test_case.py           # Base assertions (picker assignment, workload, no-overlap, cold chain)
├── functional/
│   ├── test_case_functional_instances.py                  # the functional cases of the thesis, one test per instance (status checked against the Split)
│   ├── test_case_invalid_speed_rejected.py          # case 36c: a non-positive picker speed is refused
│   └── test_case_unreachable_required_location.py   # a required location the graph cannot reach -> infeasible
└── stress/
    ├── stress_test_case.py      # adapter: solves a stress scenario with this model and checks the solution
    └── test_stress_cases.py        # binds the 19 shared stress cases (tests/stress_cases) to that adapter
```

The functional tier runs the instances of the thesis' functional cases
(captured from the Split's own tests, see
`tests/infra/factories/functional_instances.py`) and checks that the heuristic's
status matches the Split's; the objective lands in the results CSV. The
stress suite runs
`opp_split`'s 19 stress scenarios instead, file-for-file and with the
same method names, so `analysis/` joins them against v5 by instance name
(see `docs/specs/comparabilidad_split_heuristicas.md`).

`opp_aco` is registered in `analysis/config.py`'s `MODEL_DIRS` (and
deliberately left OUT of `CONGESTION_AWARE_MODELS`).

Its `single_order_params` fixture (needs a `SolveAcoModelDTO`) lives in
`tests/shared_scenarios/functional/single_order_params_aco.py` -- this model
has no `scenarios/` of its own.

## Running Tests

```bash
python -m tests.run_suite opp_aco functional
WRITE_RESULTS_CSV=1 python -m tests.run_suite opp_aco functional          # to feed analysis/
WRITE_RESULTS_CSV=1 python -m tests.run_suite opp_aco stress
python -m unittest tests.opp_aco.functional.test_case_picker_speed
```
