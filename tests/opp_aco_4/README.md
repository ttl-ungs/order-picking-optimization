# OPP Ant Colony Optimization v4 Tests (opp_aco_4)

Test suite for the ACO heuristic solver `models.opp_aco_4` - the ACO
counterpart of `models.opp_hc_4` (itself the Hill Climbing counterpart of
`opp_v5_2_split`'s two-stage ZIMPL model), built on top of `opp_aco_2`
(multi-picker ACO, no congestion).

## What's different vs. opp_aco_2

Same extension as `opp_hc_4` over `opp_hc_2` -- a batch's execution time
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
  short-circuited via `models/opp_v5_2_split/utils/cold_chain_validation.py::
  batches_without_eligible_picker`, fed a greedy nearest-neighbor
  route-time ESTIMATE (built from the same all-pairs shortest-path table
  `opp_aco_2` already precomputes) since ACO has no single deterministic
  route per batch the way `opp_hc_4`'s construction does.
- Default `T_cold = +inf` and unset `V_p` make `opp_aco_4` behave
  exactly like `opp_aco_2` (see `test_case_equivalence.py`).

**Deliberately no congestion** (unlike `opp_aco_3`): congestion and
picker-speed/cold-chain are orthogonal additions over `opp_aco_2`. This
model does NOT adopt `opp_aco_3`'s incremental `CongestionTracker`
reservation or its multi-pheromone (m-ACO4) architecture, matching how
`opp_hc_4` leaves `opp_hc_3`'s congestion pricing out.

## Structure

```
tests/opp_aco_4/
├── opp_aco_4_test_case.py           # Base assertions (picker assignment, workload, no-overlap, cold chain)
├── functional/
│   ├── test_case_equivalence.py    # dedicated: no-op equivalence with aco_2
│   ├── test_case_picker_speed.py   # dedicated: faster picker preferred
│   ├── test_case_cold_chain_infeasible.py  # dedicated: unreachable deadline -> infeasible
│   ├── test_case_cold_chain_eligibility.py # dedicated: forced onto the eligible picker
│   ├── test_case_mixed_eligibility.py      # dedicated: per-batch eligibility, not global
│   └── test_case_NN.py                     # ported 1:1 from opp_aco_2 (V_p unset, T_cold=+inf)
└── stress/
    ├── v5_stress_test_case.py      # base: runs a v5 stress scenario through this model
    └── test_case_{01..19}.py       # v5's 19 stress scenarios, same numbering and method names as opp_v5_2_split
```

The ported functional files are literal copies of their `opp_aco_2`
counterpart -- same scenario builder, same numeric parameters -- with `V_p`
unset and `T_cold` left at its default (`+inf`). The stress suite runs
`opp_v5_2_split`'s 19 stress scenarios instead, file-for-file and with the
same method names, so `analysis/` joins them against v5 by instance name
(see `docs/specs/comparabilidad_v5_heuristicas.md`).

`opp_aco_4` is registered in `analysis/config.py`'s `MODEL_DIRS` (and
deliberately left OUT of `CONGESTION_AWARE_MODELS`).

Its `single_order_params` fixture (needs a `SolveAco4ModelDTO`) lives in
`tests/shared_scenarios/functional/single_order_params_aco4.py` -- this model
has no `scenarios/` of its own.

**Note on `tests/opp_aco_4/functional/test_case_12.py`** (ported as-is from `opp_aco_2`):
like its `opp_aco_2` counterpart, it sets no `Seed`, so it is inherently
stochastic -- an unlucky ACO run can occasionally construct a different
(still feasible) route than the one hardcoded in the assertion. This is a
pre-existing characteristic of the ported test, not something introduced
by `opp_aco_4` (confirmed by running `opp_aco_2`'s own copy of the same
test repeatedly).

## Running Tests

```bash
python -m tests.run_suite opp_aco_4 functional
WRITE_RESULTS_CSV=1 python -m tests.run_suite opp_aco_4 functional          # to feed analysis/
WRITE_RESULTS_CSV=1 python -m tests.run_suite opp_aco_4 stress
python -m unittest tests.opp_aco_4.functional.test_case_picker_speed
```
