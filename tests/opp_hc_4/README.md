# OPP Hill Climbing v4 Tests (opp_hc_4)

Test suite for the Hill Climbing heuristic solver `models.opp_hc_4` - the
picker-speed / cold-chain equivalent of `opp_v5_2_split` (two-stage ZIMPL model),
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
  `opp_model_v5_2_split_stage2_scheduling.zpl`'s `PB_elig`. A batch left with zero eligible
  pickers makes the instance `"infeasible"`, short-circuited up front via
  `models/opp_v5_2_split/utils/cold_chain_validation.py::batches_without_eligible_picker`
  (reused directly, not re-implemented).
- Default `T_frio_max = +inf` and unset `V_p` make `opp_hc_4` behave
  exactly like `opp_hc_2` (see `test_case_equivalence.py`).

**Deliberately no congestion** (unlike `opp_hc_3`): congestion and
picker-speed/cold-chain are orthogonal additions over `opp_hc_2`, and this
model only combines the latter, matching `opp_v5_2_split` itself (also
congestion-free, see `analysis/config.py`).

## Structure

```
tests/opp_hc_4/
├── opp_hc_4_test_case.py           # Base assertions (picker assignment, workload, no-overlap, cold chain)
├── functional/
│   ├── test_case_equivalence.py    # dedicated: no-op equivalence with hc_2
│   ├── test_case_picker_speed.py   # dedicated: faster picker preferred
│   ├── test_case_cold_chain_infeasible.py  # dedicated: unreachable deadline -> infeasible
│   ├── test_case_cold_chain_eligibility.py # dedicated: forced onto the eligible picker
│   ├── test_case_mixed_eligibility.py      # dedicated: per-batch eligibility, not global
│   └── test_case_NN.py                     # ported 1:1 from opp_hc_2 (V_p unset, T_frio_max=+inf)
└── stress/
    ├── test_case_{01..11}.py  # ported 1:1 from opp_hc_2
    ├── test_case_picker_speed.py   # dedicated: heterogeneous speeds at scale
    └── test_case_cold_chain.py      # dedicated: binding T_frio_max at scale
```

The ported files (both normal and stress) are literal copies of their
`opp_hc_2` counterpart -- same scenario builder, same numeric parameters --
with `V_p` unset and `T_frio_max` left at its default (`+inf`), so they are
pure equivalence checks AND, more importantly, give `analysis/`'s
`quality_gap_table`/cross-model comparisons the same-named, same-shaped
instances it needs to join `opp_hc_4` against `opp_hc_2`/`opp_hc_3`/`opp_v4`
(same pattern `opp_v5_2_split` uses via `tests/infra/factories/migrated_case.py`). The
stress ports were chosen to match `opp_hc_3`'s curated 11-instance stress
subset (see `analysis/README.md`), so `opp_hc_4` lines up with both
`opp_hc_2` (full instance) and `opp_hc_3` (curated subset) at once.

`opp_hc_4` is registered in `analysis/config.py`'s `MODEL_DIRS` (and
deliberately left OUT of `CONGESTION_AWARE_MODELS`).

Its `single_order_params` fixture (needs a `SolveHC4ModelDTO`) lives in
`tests/shared_scenarios/functional/single_order_params_hc4.py`, alongside the
other models' DTO-specific variants -- this model has no `scenarios/` of
its own.

## Running Tests

```bash
python -m tests.run_suite opp_hc_4 functional
WRITE_RESULTS_CSV=1 python -m tests.run_suite opp_hc_4 functional          # to feed analysis/
WRITE_RESULTS_CSV=1 python -m tests.run_suite opp_hc_4 stress
python -m unittest tests.opp_hc_4.functional.test_case_picker_speed
```
