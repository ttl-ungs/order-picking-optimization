# Ant Colony Optimization Heuristic for OPP V4 - Equivalent with Constraints

## Overview

This directory contains an **Ant Colony Optimization (ACO)** heuristic solver that solves the **exact same problem as `opp_model_v4.zpl`**, with the **same constraints**, but using a metaheuristic approach instead of exact integer linear programming.

The key feature added on top of `opp_aco_1` (v3): orders are grouped into batches
and **batches are assigned to different pickers (X_pb)** so that the work can
be **parallelized** — batches on different pickers execute at the same time,
while batches on the same picker are sequenced one after another.

### Equivalence Guarantee

**Same Input:**
- Receives all parameters from `SolveModelDTO` (plus ACO hyperparameters via `SolveAcoModelDTO`)
- Fixed batch assignments `B_nb` (parameter)
- Set of pickers `P` (via `ModelDTO.P`); when omitted, falls back to a single
  implicit picker, matching the old non-parallel behaviour

**Same Constraints:**
- (6) Start from depot
- (7) Finish at final node
- (8) Cannot return to depot
- (9) Cannot leave final
- (10), (11) Visit all required locations
- (12) Articles capacity ≤ vehicle capacity
- (13) Flow conservation
- (14), (15) One arc per node
- (14) Every batch with orders assigned to exactly one picker (X_pb)
- (17) No loops/cycles
- (25) Only valid edges
- Plus: execution time, earliness/tardiness calculations

**Same Output:**
- Location graph with active arcs
- Compatible with `build_output()` format
- Objective value (same formula)

**Difference:**
- ✅ **Speed**: Heuristic search instead of exact LP solver
- ❌ **Optimality**: Converges to a good (not necessarily global) solution
- ✅ **Feasibility**: All solutions are valid (respect all constraints)

## Algorithm

### Ant Colony Optimization with Constraint Validation

Each ant constructs a complete solution made of two decisions per batch,
guided by two independent pheromone tables:

1. **Route construction** (edge pheromone table): probabilistic roulette-wheel
   selection of the next location to visit, combining pheromone intensity
   with a distance-based visibility term, same as `opp_aco_1`.
2. **Picker assignment** (batch/picker pheromone table, `X_pb`): probabilistic
   roulette-wheel selection of which picker executes the batch, combining
   the `(batch, picker)` pheromone with a load-balancing visibility term that
   favors currently less-loaded pickers.

After every ant has built a solution:
- Feasible solutions are evaluated (batches on the same picker accumulate
  completion time sequentially; different pickers run in parallel from time
  zero).
- The iteration-best and all-time-best solutions are tracked.
- Both pheromone tables evaporate and receive a deposit proportional to
  `Q / cost` for every feasible ant, plus an elitist boost for the
  all-time-best solution.

### Termination

- Fixed number of iterations (`Max_it`), each running `A_ants` ants.

## Architecture

```
models/opp_aco_2/
  ├── opp_aco_2.py              # Main solver (equivalent to opp_model_v4)
  ├── utils/
  │   ├── route_solution.py        # Route + picker assignment representation
  │   ├── route_evaluator.py       # Objective function (identical formula)
  │   └── constraints_validator.py # Validates ALL constraints
  ├── (usage example: examples/opp_aco_2_usage.py)
  └── README.md (this file)
```

### Key Components

- **OPPAntColonyOptimization**: Main solver
  - `solve(params)`: Same interface as `opp_model_v3`/`opp_aco_1`
  - Validates constraints throughout
  - Returns compatible output

- **RouteSolution**: Represents a solution as routes per batch, plus the
  picker assigned to each batch (`X_pb`) and each picker's processing
  sequence.

- **ConstraintsValidator**: Ensures feasibility
  - Validates all constraints, including the picker assignment constraint

- **RouteEvaluator**: Objective function
  - Identical formula to the exact model
  - Computes per-picker parallel completion times

## Usage

```python
from models.opp_aco_2 import OPPAntColonyOptimization
from dtos.opp.model_dto import ModelDTO
from dtos.aco.solve_aco_model_dto import SolveAcoModelDTO

# Create DTOs
model_dto = ModelDTO()
model_dto.P = {"P1", "P2"}
solve_dto = SolveAcoModelDTO()
# ... populate both ...

# Solve with ACO
solver = OPPAntColonyOptimization(model_dto)
solve_result = solver.solve(solve_dto)

# Output is identical format to opp_model_v3 / opp_aco_1
```

## Constraints Enforced

All constraints from `opp_model_v3` are validated, plus the picker assignment
constraint from `opp_model_v4`:

1. ✅ Routes start at depot and end at final
2. ✅ Cannot revisit depot or leave final
3. ✅ All required locations visited
4. ✅ Vehicle capacity respected
5. ✅ Only valid edges used
6. ✅ No cycles/repeated locations
7. ✅ Flow conservation (implicit in paths)
8. ✅ Every batch with orders assigned to exactly one picker
9. ✅ Execution times calculated correctly
10. ✅ Earliness/tardiness computed correctly
