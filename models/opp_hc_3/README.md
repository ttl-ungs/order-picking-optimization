# Hill Climbing v3 — Congestion-Aware

## Overview

`opp_hc_3` solves the **exact same problem as `opp_model_v4.zpl` / `opp_hc_2`**
(same `SolveModelDTO` inputs, same batches, same pickers, same constraints),
adding the Hill Climbing counterpart of `opp_aco_3`'s congestion mechanism:
pricing the wait time incurred when two concurrent pickers' routes physically
contend for the same node or edge — something opp_hc_2 never checks, since it
parallelizes pickers ("different pickers run different batches at the same
time") without verifying whether their routes actually collide.

The addition is **purely additive to the cost function**, not a new hard
constraint: a solution with zero contention (e.g. a single picker, or
pickers that never share a node/edge) reduces exactly to opp_hc_2's
objective value.

## Why this mechanism, and why it's simpler than opp_aco_3's

The underlying physical model is identical to opp_aco_3's — see
`models/opp_aco_3/README.md` for the full literature review (Chen et al.,
2013 on congestion; Lesch et al., 2023 for the shared parametrization
philosophy) and `models/utils/congestion.py` for the shared resource model
(every node and undirected edge is a capacity-1 resource). What differs is
**how** it gets plugged in, because Hill Climbing's architecture is
different from ACO's:

- opp_aco_3's ants build routes **step by step, probabilistically**, so
  congestion needs to be reserved **incrementally, during construction**
  (`CongestionTracker.reserve` interleaved with the roulette-wheel choice),
  and a dedicated pheromone matrix (τ2) biases ants away from contention.
- opp_hc_3 already builds a **complete, fixed route per batch up front**
  (Dijkstra-based nearest neighbor, exactly like opp_hc_2), then perturbs it
  with 2-opt / picker-reassignment / sequence-swap moves. There is nothing
  to bias step-by-step, and no pheromone to update — so congestion is
  simply **priced as a full simulation** every time a solution is evaluated
  (`models/opp_hc_3/utils/route_evaluator.py::compute_batch_completions`,
  using the shared `simulate_route_congestion` helper in
  `models/utils/congestion.py`). Hill Climbing's existing accept-if-better
  rule already rewards congestion-reducing moves once it's part of the cost
  — no separate congestion-avoidance heuristic is needed for a local search.

This makes opp_hc_3 a **smaller, more direct diff** on top of opp_hc_2 than
opp_aco_3 is on top of opp_aco_2: only the evaluator changes; route
construction and all three neighbor moves (2-opt, picker reassignment,
sequence swap) are untouched from opp_hc_2.

### Known simplification

None of the three neighbor moves is congestion-aware by itself — 2-opt
still picks the geometrically shortest reversal, ignoring contention. A move
that shortens a route but increases contention with another picker can
still be **rejected** by the outer accept-if-better check in `solve()`
(since the full evaluate(), congestion included, decides), but the move
*generator* itself never actively searches for a congestion-reducing
reversal. Same causal approximation as opp_aco_3 (round-robin by picker
queue slot, not a true continuous-time joint simulation) applies here too.

## Algorithm

See [`PSEUDOCODE.md`](./PSEUDOCODE.md) for the full algorithm as
line-by-line pseudocode, cross-referenced to the actual method names.

1. **Initial solution** — unchanged from opp_hc_2: Dijkstra-based
   nearest-neighbor routes per batch, batches distributed round-robin
   across pickers (x_pb).
2. **Neighbor generation** — unchanged from opp_hc_2: 2-opt on a random
   batch's route, picker reassignment, or picker-sequence swap.
3. **Evaluation** — `RouteEvaluator.compute_batch_completions` walks every
   picker's queue in **round-robin slot order** (slot 0 of every picker,
   then slot 1, ...), and for each batch's fixed route calls
   `simulate_route_congestion` against a shared `CongestionTracker`. The
   resulting wait is folded into `d_b` and written onto the solution
   (`RouteSolution.set_batch_congestion_wait`) for reporting.
4. **Accept if better** — unchanged from opp_hc_2: accept the neighbor iff
   its full objective (now congestion-inclusive) improves on the current one.

`d_b = T_setup + T_pick·Σcap + T_travel·distance + Σservice_time + congestion_wait`
— a strict superset of opp_hc_2's formula (last term is new).

## Architecture

```
models/opp_hc_3/
  ├── opp_hc_3.py                   # Main solver (route construction/moves unchanged from opp_hc_2)
  ├── utils/
  │   ├── route_solution.py         # Route + picker assignment + per-batch congestion wait
  │   ├── route_evaluator.py        # Objective, with round-robin congestion simulation
  │   ├── constraints_validator.py  # Validates ALL constraints (congestion is a cost, not a hard constraint)
  │   └── output_handler.py
  ├── (usage example: examples/opp_hc_3_usage.py)               # Same two-picker bottleneck example as opp_aco_3, for direct comparison
  └── README.md (this file)

dtos/hc/solve_hc_3_model_dto.py     # SolveHC3ModelDTO: adds Min_dwell on top of SolveHCModelDTO
```

## New hyperparameter (`SolveHC3ModelDTO`, on top of `SolveHCModelDTO`)

| Parameter | Default | Meaning |
|---|---|---|
| `Min_dwell` | 0.0 | Minimum node occupancy/turnaround buffer, even at zero service time |

## Output

`solution_info` adds, on top of opp_hc_2's shape:

- `congestion_objective_value`: total wait time of the returned solution.
- `batch_congestion_wait`: `{batch: wait_time}` per-batch breakdown.

`SolveResult.params` likewise adds `obj_val_congestion` and `Min_dwell`.

Also fixed while porting: opp_hc_2's own `_build_solution_info` used a
formula for `d_b` that diverged from the one `RouteEvaluator` actually
optimizes against (it indexed service time by *order* instead of
*location*, and skipped congestion entirely by construction). opp_hc_3's
`_build_solution_info` now reuses the exact same formula as its
`RouteEvaluator`, so the reported `batch_times`/`batch_completions` are
always consistent with the objective value actually being optimized.

## Testing

`tests/opp_hc_3/`:
- `test_case_01.py`: parity test (single implicit picker, no
  shared resources ⇒ zero congestion) — same fixture as opp_hc_2's model_01.
- `test_case_congestion.py`: two pickers forced through a
  shared bottleneck node — same scenario as opp_aco_3's congestion test (on
  this instance both models converge to the identical objective value,
  68.8, and congestion wait, 3.0 — a useful cross-check between the two
  metaheuristics).
- `test_case_simulate_route_congestion.py`: deterministic unit tests
  for the shared `simulate_route_congestion` helper.

Only a minimal representative test set was written for this first version;
opp_hc_2's full functional/stress test battery (~30+ files) can be ported the
same way as `test_case_01.py` if broader regression coverage is
desired.
