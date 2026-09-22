# Ant Colony Optimization v3 — Congestion-Aware, Multi-Pheromone (m-ACO4)

## Overview

`opp_aco_3` solves the **exact same problem as `opp_model_v4.zpl` / `opp_aco_2`**
(same `SolveModelDTO` inputs, same batches, same pickers, same constraints),
but adds two mechanisms that opp_aco_2 does not model at all, motivated by
the literature review conducted for this thesis:

1. **Congestion between concurrent pickers.** opp_aco_2 parallelizes
   pickers (different pickers run different batches "at the same time") but
   never checks whether their routes actually collide — two pickers could,
   on paper, occupy the exact same aisle location at the exact same instant
   with zero cost. opp_aco_3 prices that as a wait time.
2. **Multi-pheromone (m-ACO4) construction.** opp_aco_2 uses a single edge
   pheromone table biased purely towards short/relevant routes. opp_aco_3
   keeps **two** pheromone matrices — one per objective (time vs.
   congestion) — and lets each ant randomly decide, at every step of route
   construction, which objective guides that step.

Both additions are **purely additive to the cost function**, not new hard
constraints: a solution with zero contention (e.g. a single picker, or
pickers that never share a node/edge) reduces exactly to opp_aco_2's
behaviour and objective value.

## Why these two mechanisms — literature review

Six papers were reviewed. Two are directly about ACO for
order-picking routing, one is a generic multi-objective ACO framework, and
three are about batching/slotting/simulation (not ACO) but confirmed
congestion as an open research gap:

- **Chen, F., Wang, H., Qi, C., & Xie, Y. (2013).** *An ant colony
  optimization routing algorithm for two order pickers with congestion
  consideration.* Computers & Industrial Engineering, 66(1), 77-85.
  Introduces a "logic travel distance" (physical travel time + wait caused
  by another picker occupying the same sub-aisle), a spatio-temporal tabu
  list, dynamic recalculation of costs as pickers move, and a "cataclysm"
  pheromone-reset mechanism against stagnation (Sec. 4.2-4.3).
- **Alaya, I., Solnon, C., & Ghédira, K.** *Ant Colony Optimization for
  Multi-objective Optimization Problems.* Proposes the generic **m-ACO**
  family; **m-ACO₄(1,m)** — one colony, one pheromone matrix per objective,
  objective chosen at random per construction step — is reported as the
  best-performing variant (Sec. 3.2, Table 1, Sec. 6).
- **Lesch, V., Müller, P.B.M., Krämer, M., Hadry, M., Kounev, S., &
  Krupitzer, C. (2023).** *Optimizing storage assignment, order picking, and
  their interaction in mezzanine warehouses.* Applied Intelligence, 53,
  18605-18629. Provides a calibrated ACO3/ACO4 parametrization for a real
  warehouse (α=1.0, β=2.0, ρ=0.02, τ_min=1, τ_max=25, maxIterWoImpr=20,
  maxCataclysms=3 — Table p.18620) and the same cataclysm mechanism
  (Algorithm 2, p.18618), reused here almost verbatim as `SolveAco3ModelDTO` defaults.
- **Coruzzolo, Lolli, Balugani, Magnani & Sellitto.** *Order Picking
  Problem: Joint Optimisation of Batching, Assignment, Sequencing, and
  Routing* (Logistics 2023, 7, 61). Not an ACO paper, but explicitly lists
  **picker congestion/blocking as an open limitation and future work item**
  (p.16) — reinforcing this as a legitimate contribution angle.
- Urzúa, Mendoza & González (2019) and the FP366 slotting paper informed a
  *separate* line of work (ABC/slotting preprocessing) that is **not** part
  of opp_aco_3 — tracked as a possible follow-up model, not implemented here.

### Adaptation, not a literal port

Chen et al.'s congestion model assumes a narrow-aisle layout with explicit
aisle / sub-aisle / block coordinates, and re-plans step-by-step for exactly
two pickers moving concurrently. Our `OPPLocationGraph` is a plain abstract
graph (nodes + distances, arbitrary picker count), so opp_aco_3 adapts the
same *idea* rather than replicating the paper literally:

- Every **node** and every undirected **edge** (a physical aisle segment,
  regardless of travel direction) is treated as a **capacity-1 resource**:
  at most one picker may occupy it at a time. See
  `models/utils/congestion.py::CongestionTracker`.
- Depot and final nodes are excluded from node contention (many pickers
  legitimately start/finish there at once); edges touching them are still
  contended normally.
- Routes are built **one full batch at a time**, not via a true
  continuous-time joint simulation of all pickers. To approximate causality,
  each ant builds batches in **round-robin order across pickers' queue
  slots** (slot 0 of every picker, then slot 1, ...), so a batch always
  "sees" the occupancy already reserved by batches that, given the fixed
  queues, run at or before its own start time. **This is an approximation,
  not an exact replication of Chen et al.'s dynamic recalculation** — stated
  explicitly here for the thesis write-up.

## Algorithm

See [`PSEUDOCODE.md`](./PSEUDOCODE.md) for the full algorithm as
line-by-line pseudocode, cross-referenced to the actual method names.

### 1. Picker assignment (X_pb) — unchanged from opp_aco_2

Each ant assigns every batch with orders to a picker via roulette-wheel
selection over a dedicated `(batch, picker)` pheromone table, combined with
a load-balancing visibility term. This fixes each picker's processing queue
(the order batches will run in).

### 2. Congestion-aware route construction — m-ACO4(1,m)

For every batch, in round-robin slot order across pickers:

- At **each step** of the route (choosing the next location to visit), the
  ant flips a coin (`P_objective_switch`) to decide which pheromone matrix
  guides that step:
  - **τ1 (time):** same visibility as opp_aco_2 — `η = 1/distance` to the
    nearest still-required location.
  - **τ2 (congestion):** `η = 1/(1 + predicted_wait)`, where `predicted_wait`
    is a read-only lookahead (`CongestionTracker.peek_wait`) of how long the
    picker would have to wait for the candidate node/edge, given everything
    reserved so far by earlier batches in this ant's solution.
- Once a candidate is chosen, the move is **committed**: the edge (transit)
  and node (dwell = `max(Min_dwell, service_time)`) resources are reserved
  for real (`CongestionTracker.reserve`), cascading through any pre-existing
  occupancy exactly like the paper's dynamic recalculation. The wait
  actually incurred is accumulated into the batch's `congestion_wait`.
- `t_exec_b = B_setup + B_picking·Σcap + B_time·distance + Σservice_time + congestion_wait`
  — a strict superset of opp_aco_2's formula (last term is new).

### 3. Pheromone update — m-ACO4 deposit rule + MAX-MIN bounds

After every ant builds a (validated) solution, its **time** objective
(`RouteEvaluator.evaluate`, identical formula to opp_aco_2/the exact model)
and **congestion** objective (`RouteEvaluator.evaluate_congestion`, total
wait time) are computed independently. Both pheromone matrices evaporate,
then receive a deposit per ant, per Alaya et al. Sec. 3.2 / Lesch et al.
Eqs. 11-13:

```
Δτ1(edge) = 1 / (1 + time_cost(ant)       - iteration_best_time_cost)        for every edge the ant used
Δτ2(edge) = 1 / (1 + congestion_cost(ant) - iteration_best_congestion_cost)  for every edge the ant used
```

An elitist bonus (Δτ=2.0, i.e. double the maximum per-ant reward) is added
on both matrices for the all-time-best solution (selected by the **time**
objective, so the reported/returned solution stays comparable to
opp_aco_2's single-objective output). Both matrices are then clipped to
`[Tau_min, Tau_max]` (MAX-MIN Ant System bounds).

### 4. Cataclysm (anti-stagnation reset)

If the best-so-far time objective hasn't improved for
`Max_iter_wo_improvement` iterations, both pheromone matrices (and the
picker-assignment pheromone) are reset to their initial value
(`Tau_max`), up to `Max_cataclysms` times (Chen et al., Sec. 4.3; Lesch et
al., Algorithm 2). If stagnation persists after the cataclysm budget is
exhausted, the main loop stops early instead of running to `Max_it`.

## Architecture

```
models/opp_aco_3/
  ├── opp_aco_3.py                  # Main solver
  ├── utils/
  │   ├── route_solution.py         # Route + picker assignment + per-batch congestion wait
  │   ├── route_evaluator.py        # Time objective (tau1) and congestion objective (tau2)
  │   ├── constraints_validator.py  # Validates ALL constraints (congestion is a cost, not a hard constraint)
  │   └── output_handler.py
  ├── example_usage.py               # Two-picker bottleneck example
  └── README.md (this file)

models/utils/congestion.py          # CongestionTracker, shared resource/wait scheduling
dtos/aco/solve_aco_3_model_dto.py   # SolveAco3ModelDTO: congestion + multi-pheromone hyperparameters
```

## New hyperparameters (`SolveAco3ModelDTO`, on top of `SolveAcoModelDTO`)

| Parameter | Default | Source | Meaning |
|---|---|---|---|
| `Alpha` | 1.0 | Lesch et al. (2023) | Pheromone importance (both matrices) |
| `Beta` | 2.0 | Lesch et al. (2023) | Time-visibility importance (τ1 steps) |
| `Beta2` | 2.0 | this thesis | Congestion-visibility importance (τ2 steps) |
| `E` | 0.02 | Lesch et al. (2023) | Evaporation rate (both matrices) |
| `Tau_min` / `Tau_max` | 1.0 / 25.0 | Lesch et al. (2023) | MAX-MIN pheromone bounds |
| `P_objective_switch` | 0.5 | Alaya et al. (m-ACO4) | P(step guided by τ1 instead of τ2) |
| `Min_dwell` | 0.0 | this thesis | Minimum node occupancy/turnaround buffer, even at zero service time |
| `Max_iter_wo_improvement` | 20 | Lesch et al. (2023) | Iterations without improvement before a cataclysm |
| `Max_cataclysms` | 3 | Lesch et al. (2023) | Max pheromone resets before stopping early |

## Output

`solution_info` (notified to observers, e.g. `OutputHandler`) adds two
fields on top of opp_aco_2's shape:

- `congestion_objective_value`: total wait time (τ2) of the returned solution.
- `batch_congestion_wait`: `{batch: wait_time}` per-batch breakdown.

`SolveResult.params` likewise adds `obj_val_congestion` and `Cataclysms_used`.

## Testing

`tests/opp_aco_3/`:
- `test_case_01.py`: parity test (single implicit picker, no
  shared resources ⇒ zero congestion) — same fixture and expected output as
  opp_aco_2's model_01, verifying the new mechanisms are additive.
- `test_case_congestion.py`: two pickers forced through a
  shared bottleneck node — verifies a positive congestion wait is actually
  detected and folded into the objective.
- `test_case_congestion_tracker.py`: deterministic unit tests for
  `CongestionTracker`, independent of ACO's randomness.

Only a minimal representative test set was written for this first version;
`opp_aco_2`'s full normal-test battery (~18 files, reused scenarios under
`tests/shared_scenarios/`) can be ported over the same way as
`test_case_01.py` if broader regression coverage is desired.

## Known simplifications / honest limitations (for the thesis write-up)

1. Congestion resources are inferred from the abstract graph (nodes/edges),
   not from real aisle/sub-aisle geometry — two locations that are not
   graph-adjacent can never contend, even if they are physically close.
2. Route construction is causally approximated (round-robin by queue slot),
   not a true continuous-time joint simulation of every picker.
3. Picker sequencing (which batch runs before which, on a given picker) is
   still fixed by the order batches are enumerated, not optimized — same
   limitation as opp_aco_2.
4. The reported "best" solution is selected by the time objective alone;
   opp_aco_3 does not (yet) report a Pareto front (that would be the
   m-ACO₃-like alternative discussed but not chosen for this iteration).
