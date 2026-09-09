# OPP Ant Colony Optimization v4 Tests (opp_aco_4)

Test suite for the ACO heuristic solver `models.opp_aco_4` - the ACO
counterpart of `models.opp_hc_4` (itself the Hill Climbing counterpart of
`opp_v5`'s two-stage ZIMPL model), built on top of `opp_aco_2`
(multi-picker ACO, no congestion).

## What's different vs. opp_aco_2

Same extension as `opp_hc_4` over `opp_hc_2` -- a batch's execution time
is no longer a single `t_exec_b` shared by every picker:

```
t_exec_pb[p, b] = fixed_time(b) + route_time(b) / V_p[p]
fixed_time(b)   = B_setup + B_picking * sum(C_n over b's orders)   # speed-independent
route_time(b)   = B_time * travel_distance + service_time          # scaled by speed
```

- **Picker speed (`V_p`)**: a `{picker: speed}` dict. A picker missing from
  it defaults to speed `1.0` (no-op). Only `_select_picker`'s roulette is
  affected -- the (batch, picker) pheromone table itself is unchanged.
- **Cold chain (`T_frio_max`)**: a `(picker, batch)` pair is only eligible
  if `t_exec_pb[p, b] <= T_frio_max`. Since each ant builds a batch's
  route BEFORE picking its picker, `_select_picker`'s candidate pool is
  filtered to that ant's OWN just-built route's eligible pickers (exact,
  not an approximation). A globally infeasible batch (no eligible picker
  under ANY achievable route) makes the instance `"infeasible"` up front,
  short-circuited via `models/opp_v5/utils/cold_chain_validation.py::
  batches_without_eligible_picker`, fed a greedy nearest-neighbor
  route-time ESTIMATE (built from the same all-pairs shortest-path table
  `opp_aco_2` already precomputes) since ACO has no single deterministic
  route per batch the way `opp_hc_4`'s construction does.
- Default `T_frio_max = +inf` and unset `V_p` make `opp_aco_4` behave
  exactly like `opp_aco_2` (see `test_opp_aco_4_model_01_equivalence.py`).

**Deliberately no congestion** (unlike `opp_aco_3`): congestion and
picker-speed/cold-chain are orthogonal additions over `opp_aco_2`. This
model does NOT adopt `opp_aco_3`'s incremental `CongestionTracker`
reservation or its multi-pheromone (m-ACO4) architecture, matching how
`opp_hc_4` leaves `opp_hc_3`'s congestion pricing out.

## Structure

```
tests/opp_aco_4/
├── execute_tests.py            # Main test runner (normal suite)
├── execute_stress_tests.py     # Stress suite runner
├── scenarios/normal/            # Fixtures that need a SolveAco4ModelDTO (single_order_params)
└── tests/
    ├── opp_aco_4_test_case.py           # Base assertions (picker assignment, workload, no-overlap, cold chain)
    ├── normal/
    │   ├── test_opp_aco_4_model_01_equivalence.py    # dedicated: no-op equivalence with aco_2
    │   ├── test_opp_aco_4_model_02_picker_speed.py   # dedicated: faster picker preferred
    │   ├── test_opp_aco_4_model_03_cold_chain_infeasible.py  # dedicated: unreachable deadline -> infeasible
    │   ├── test_opp_aco_4_model_04_cold_chain_eligibility.py # dedicated: forced onto the eligible picker
    │   ├── test_opp_aco_4_model_05_mixed_eligibility.py      # dedicated: per-batch eligibility, not global
    │   └── test_opp_aco_4_model_{02,03,...,30}.py            # ported 1:1 from opp_aco_2 (V_p unset, T_frio_max=+inf)
    └── stress/
        ├── test_opp_aco_4_model_{01,...,20}.py       # ported 1:1 from opp_aco_2 (full parity)
        ├── test_opp_aco_4_model_11_picker_speed.py   # dedicated: heterogeneous speeds at scale
        └── test_opp_aco_4_model_12_cold_chain.py      # dedicated: binding T_frio_max at scale
```

The ported files (both normal and stress) are literal copies of their
`opp_aco_2` counterpart -- same scenario builder, same numeric parameters
-- with `V_p` unset and `T_frio_max` left at its default (`+inf`), giving
`analysis/`'s `quality_gap_table`/cross-model comparisons the same-named,
same-shaped instances it needs to join `opp_aco_4` against
`opp_aco_2`/`opp_aco_3`/`opp_v4` (same pattern `opp_v5` and `opp_hc_4`
use). `opp_aco_2` only has 20 stress instances (vs. `opp_hc_2`'s 43), so
all 20 were ported for full parity (`opp_aco_3` also has all 20).

`opp_aco_4` is registered in `analysis/config.py`'s `MODEL_DIRS` (and
deliberately left OUT of `CONGESTION_AWARE_MODELS`).

**Note on `test_opp_aco_4_model_17`** (ported as-is from `opp_aco_2`):
like its `opp_aco_2` counterpart, it sets no `Seed`, so it is inherently
stochastic -- an unlucky ACO run can occasionally construct a different
(still feasible) route than the one hardcoded in the assertion. This is a
pre-existing characteristic of the ported test, not something introduced
by `opp_aco_4` (confirmed by running `opp_aco_2`'s own copy of the same
test repeatedly).

## Running Tests

```bash
python tests/opp_aco_4/execute_tests.py
WRITE_RESULTS_CSV=1 python tests/opp_aco_4/execute_tests.py          # to feed analysis/
WRITE_RESULTS_CSV=1 python tests/opp_aco_4/execute_stress_tests.py
python -m unittest tests.opp_aco_4.tests.normal.test_opp_aco_4_model_02_picker_speed
```
