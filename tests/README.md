# Tests

This document describes a workflow to design and maintain OPP (v1 and v2) tests consistently.

## Objectives

- Validate feasible routes on representative graphs.
- Verify penalties for tardiness/earliness with controlled scenarios.
- Cover multi picker and multi batch cases.
- Include infeasible cases with clear causes.

## Structure

- tests/shared_scenarios: definition of graphs and base assignments (shared by every model; model-specific ones carry a `_vN` suffix).
- tests/<model>/functional and tests/<model>/stress: test cases per model (`test_case_NN.py`).
- tests/support/: shared test infrastructure (runner, config, `OPPTestCase`, `family_case`, `migrated_case`, `route_assertions`, ZPL helpers).
- tests/run_suite.py: single entry point to run a model's suite.

## Workflow per graph (recommended)

1) Happy path
- Use a minimal set of orders that activates key nodes.
- Validate that the route visits all required locations.
- For a single batch, use `assert_route_covers_orders`.
- For multiple batches, use `assert_batch_routes_cover_locations`.

2) Penalties (tardiness/earliness)
- Reuse the same graph and assignments (N, a, y) for stability.
- Isolate the penalty term:
  - w1 = 0.0, w2 = 1.0
  - gamma = 0.0 (ignore earliness)
  - delta = 1.0
- Tardiness case:
  - due_date very low (e.g. 0.0) to force ta_n > 0.
- Best case:
  - due_date high (e.g. 100.0) to expect ta_n ~= 0.
- Measure the sum with `OPPTestCase.sum_vars_with_prefix(model, "ta_")`.

3) Multi picker / multi batch
- Define x and y so each picker has 1+ batches.
- Validate routes per batch (`assert_batch_routes_cover_locations`).
- Allow shared locations across batches when the case needs it.

4) Infeasible
- Force a specific cause:
  - Duplicate a location within the same batch.
  - Vehicle capacity too low.
  - Disconnected graph for a required location.
- Validate status "infeasible".

### Test Parameter Combinations

Suggested parameter mixes to exercise different behaviors in tests:

- Baseline feasibility: `w1=1`, `w2=1`, `gamma=1`, `delta=1`, moderate `due_date`, and `cap_vehicle` >= sum of `cap_n` per batch.
- Tardiness sensitivity (no `due_date` change): fix `due_date`, set `w1=0`, `w2=1`, `gamma=0`, `delta=1`, and vary `beta_picking` or `cap_n`.
- Earliness sensitivity: fix high `due_date`, set `w1=0`, `w2=1`, `gamma=1`, `delta=0`, and lower `cap_n` or `beta_time`.
- Route/time emphasis: set `w1>0`, `w2=0`, then vary graph weights (`d(i,j)`) or `beta_time`.
- Capacity infeasible: set `cap_vehicle` below the sum of `cap_n` for a batch.
- Assignment stress: use multiple batches per picker and shared locations across batches.
- Disconnected graph: remove a required edge so at least one required node is unreachable.

## Recommended helpers

- `OPPTestCase.normalize_due_dates(orders, override, default)`
- `OPPTestCase.apply_weight_overrides(w1, w2, gamma, delta, ...)`
- `OPPTestCase.sum_vars_with_prefix(model, prefix)`

Using these helpers avoids duplication and makes tests easier to maintain.

## Considerations

Common layouts (per Gemini) are:

| Distribution | Graph Structure | Common Use |
| --- | --- | --- |
| Single block | Simple grid (m x n). | Small warehouses, easy implementation. |
| Multi block | Grids connected by intermediate nodes. | Large distribution centers (Amazon, logistics hubs). |
| Non traditional | Graphs with diagonal edges (Fishbone). | High density warehouses with intensive picking. |

It would be useful to research this further.

## Execution

From the repository root:

python -m unittest tests.opp_v2.functional.test_case_{number}

Or run a whole suite with the timeout/CSV runner:

python -m tests.run_suite opp_v2 functional

Settings (per-test timeouts, whether to write result CSVs) come from a local `.env`; copy `.env.example` to `.env` to change them. `.env` itself is not versioned.
