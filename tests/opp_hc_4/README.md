# OPP Hill Climbing v4 Tests (opp_hc_4)

Test suite for the Hill Climbing heuristic solver `models.opp_hc_4` - the
picker-speed / cold-chain equivalent of `opp_v5` (two-stage ZIMPL model),
built on top of `opp_hc_2` (multi-picker, no congestion).

## What's different vs. opp_hc_2

A batch's execution time is no longer a single `t_exec_b` shared by every
picker. Instead:

```
t_exec_pb[p, b] = fixed_time(b) + route_time(b) / V_p[p]
fixed_time(b)   = B_setup + B_picking * sum(C_n over b's orders)   # speed-independent
route_time(b)   = B_time * travel_distance + service_time          # scaled by speed
```

- **Picker speed (`V_p`)**: a `{picker: speed}` dict. A picker missing from
  it defaults to speed `1.0` (no-op).
- **Cold chain (`T_frio_max`)**: a `(picker, batch)` pair is only eligible
  if `t_exec_pb[p, b] <= T_frio_max`. This restricts which picker a batch
  can be assigned to (X_pb's domain), mirroring
  `stage2_scheduling.zpl`'s `PB_elig`. A batch left with zero eligible
  pickers makes the instance `"infeasible"`, short-circuited up front via
  `models/opp_v5/utils/cold_chain_validation.py::batches_without_eligible_picker`
  (reused directly, not re-implemented).
- Default `T_frio_max = +inf` and unset `V_p` make `opp_hc_4` behave
  exactly like `opp_hc_2` (see `test_opp_hc_4_model_01_equivalence.py`).

**Deliberately no congestion** (unlike `opp_hc_3`): congestion and
picker-speed/cold-chain are orthogonal additions over `opp_hc_2`, and this
model only combines the latter, matching `opp_v5` itself (also
congestion-free, see `analysis/config.py`).

## Structure

```
tests/opp_hc_4/
├── execute_tests.py            # Main test runner (normal suite)
├── execute_stress_tests.py     # Stress suite runner
└── tests/
    ├── opp_hc_4_test_case.py           # Base assertions (picker assignment, no-overlap, cold chain)
    ├── normal/
    │   ├── test_opp_hc_4_model_01_equivalence.py
    │   ├── test_opp_hc_4_model_02_picker_speed.py
    │   ├── test_opp_hc_4_model_03_cold_chain_infeasible.py
    │   └── test_opp_hc_4_model_04_cold_chain_eligibility.py
    └── stress/
```

## Running Tests

```bash
python tests/opp_hc_4/execute_tests.py
python tests/opp_hc_4/execute_stress_tests.py
python -m unittest tests.opp_hc_4.tests.normal.test_opp_hc_4_model_02_picker_speed
```
