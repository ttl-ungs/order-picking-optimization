# Hill Climbing Heuristic for OPP V3 - Equivalent with Constraints

## Overview

This directory contains a **Hill Climbing** heuristic solver that solves the **exact same problem as `opp_model_v3.py`**, with the **same constraints**, but using a heuristic approach instead of exact integer linear programming.

### Equivalence Guarantee

**Same Input:**
- Receives all parameters from `SolveModelDTO`
- Fixed batch assignments `Bn` (parameter)

**Same Constraints:**
- (6) Start from depot
- (7) Finish at final node
- (8) Cannot return to depot
- (9) Cannot leave final
- (10), (11) Visit all required locations
- (12) Articles capacity ≤ vehicle capacity
- (13) Flow conservation
- (14), (15) One arc per node
- (17) No loops/cycles
- (25) Only valid edges
- Plus: execution time, earliness/tardiness calculations

**Same Output:**
- Location graph with active arcs
- Compatible with `build_output()` format
- Objective value (same formula)

**Difference:**
- ✅ **Speed**: Heuristic search instead of exact LP solver
- ❌ **Optimality**: Converges to local optimum, not guaranteed global
- ✅ **Feasibility**: All solutions are valid (respect all constraints)

## Algorithm

### Hill Climbing with Constraint Validation

1. **Generate Initial FEASIBLE Solution**
   - For each batch, build route using nearest neighbor
   - Verify all constraints before accepting
   
2. **Main Loop**
   - Generate neighbor via 2-opt (only if maintains feasibility)
   - Evaluate objective
   - Accept if better
   
3. **Termination**
   - Max iterations reached, OR
   - No improvement for N iterations

## Architecture

```
models/opp_hill_climbing/
  ├── opp_hill_climbing.py         # Main solver (equivalent to opp_model_v3)
  ├── utils/
  │   ├── route_solution.py        # Route representation
  │   ├── route_evaluator.py       # Objective function (identical formula)
  │   └── constraints_validator.py # Validates ALL constraints
  ├── (usage example: examples/opp_hc_1_usage.py)
  └── README.md (this file)
```

### Key Components

- **OPPHillClimbingV3**: Main solver
  - `solve(params)`: Same interface as opp_model_v3
  - Validates constraints throughout
  - Returns compatible output

- **ConstraintsValidator**: Ensures feasibility
  - Validates all 13+ constraints
  - Prevents infeasible moves

- **RouteEvaluator**: Objective function
  - Identical formula to exact model
  - Same tardiness/earliness calculation

## Usage

```python
from models.opp_hill_climbing import OPPHillClimbingV3
from dtos.opp.model_dto import ModelDTO
from dtos.opp.solve_model_dto import SolveModelDTO

# Create DTOs (same as opp_model_v3)
model_dto = ModelDTO()
solve_dto = SolveModelDTO()
# ... populate both ...

# Solve with Hill Climbing
solver = OPPHillClimbingV3(model_dto)
status, output_graph = solver.solve(solve_dto)

# Output is identical format to opp_model_v3
```

## Testing

To verify equivalence, copy tests from `opp_v3` test suite:
- Same test fixtures work for both solvers
- Both return compatible output graphs
- Constraint validation should be transparent
- Objective calculations should match exactly

### Example Test Pattern

```python
def test_opp_hc_v3_same_format():
    # Use opp_v3 test setup
    model_dto, solve_dto = create_test_instance()
    
    # Run both solvers
    exact_solver = OPPModelV3(model_dto)
    status_exact, output_exact = exact_solver.solve(solve_dto)
    
    hc_solver = OPPHillClimbingV3(model_dto)
    status_hc, output_hc = hc_solver.solve(solve_dto)
    
    # Both should return compatible graphs
    assert output_exact.get_vertices() == output_hc.get_vertices()
    # Objective values may differ (heuristic), but constraints respected
```

## Performance

| Aspect | Exact | HC V3 |
|--------|-------|-------|
| Optimality | Global optimum | Local optimum |
| Speed | Slow (SCIP) | Fast (heuristic) |
| Constraint validation | Implicit in LP | Explicit checks |
| Feasibility guarantee | Yes (if solver finds solution) | Yes (always) |
| Predictable time | No | Yes |

## Constraints Enforced

All constraints from opp_model_v3 are validated:

1. ✅ Routes start at depot and end at final
2. ✅ Cannot revisit depot or leave final
3. ✅ All required locations visited
4. ✅ Vehicle capacity respected
5. ✅ Only valid edges used
6. ✅ No cycles/repeated locations
7. ✅ Flow conservation (implicit in paths)
8. ✅ Execution times calculated correctly
9. ✅ Earliness/tardiness computed correctly

## Future Enhancements

1. **Better initial solutions**: Savings algorithm, Christofides
2. **Advanced moves**: 3-opt, Or-opt, Lin-Kernighan
3. **Escape mechanisms**: Simulated Annealing, Tabu Search
4. **Multi-start**: Multiple runs with best solution
5. **Parallelization**: Run multiple searches in parallel

