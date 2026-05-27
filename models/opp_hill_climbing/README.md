# Hill Climbing Heuristic for Order Picking Problem (OPP)

## Overview

This directory contains a **Hill Climbing** heuristic solver for the Order Picking Problem. Hill Climbing is a local search algorithm that iteratively improves a solution by making moves to neighboring solutions that reduce the objective function.

## Algorithm

### Main Loop

1. **Initial Solution**: Generate a greedy initial solution
2. **Neighborhood Generation**: Create a neighbor by moving a random order to a different batch
3. **Evaluation**: Calculate the objective function for both current and neighbor solutions
4. **Acceptance**: Accept the neighbor if it improves the objective (minimization)
5. **Termination**: Stop when:
   - Maximum iterations reached, OR
   - No improvement for N consecutive iterations (convergence to local optimum)

### Objective Function

Minimizes:
```
W_full * Σ(v_b) + W_ea_ta * (W_ea * Σ(ea_n) + W_ta * Σ(ta_n))
```

Where:
- `v_b`: completion time of batch b
- `ea_n`: earliness of order n (finishing before due date)
- `ta_n`: tardiness of order n (finishing after due date)

## Architecture

### Core Components

- **OPPHillClimbing**: Main solver class inheriting from `Model`
- **Solution**: Represents assignment of orders to batches
- **Evaluator**: Calculates objective function
- **RouteOptimizer**: Optimizes routes within batches

### Key Methods

#### `solve(params: SolveModelDTO) -> (status, output)`

Main entry point that runs the hill climbing algorithm.

#### `_generate_initial_solution() -> Solution`

Creates an initial solution using a simple greedy heuristic:
- Sort orders by capacity
- Assign each to the first batch with available capacity

#### `_generate_neighbor(solution: Solution) -> Solution`

Creates a neighbor solution by:
- Selecting a random order
- Moving it to a different random batch
- This ensures local search exploration

## Usage Example

```python
from models.opp_hill_climbing import OPPHillClimbing
from dtos.opp.model_dto import ModelDTO
from dtos.opp.solve_model_dto import SolveModelDTO

# Create DTOs (same as for opp_model_v3)
model_dto = ModelDTO()
# ... populate model_dto ...

solve_dto = SolveModelDTO()
# ... populate solve_dto ...

# Create and solve
solver = OPPHillClimbing(model_dto)
status, solution = solver.solve(solve_dto)
```

## Comparison with Exact Solver

### Pros
- **Fast**: Typically 10-100x faster than exact solver
- **Scalable**: Can handle larger instances
- **Anytime**: Can be stopped at any time with current best solution
- **Simple**: Easy to understand and modify

### Cons
- **Non-optimal**: Returns local optimum, not guaranteed global optimum
- **Variable quality**: Solution quality depends on initial solution and stopping criteria
- **Random**: Results vary between runs

## Parameters

Modify in the code for experimentation:
- `max_iterations`: Maximum iterations (default: 1000)
- `max_no_improvement`: Iterations without improvement before stopping (default: 50)
- Neighborhood generation strategy in `_generate_neighbor()`

## Future Enhancements

1. **Multi-start**: Run multiple times with different initial solutions
2. **Perturbation**: Escape local optima with controlled perturbations (Variable Neighborhood Search)
3. **Tabu List**: Prevent revisiting recently explored solutions
4. **Simulated Annealing**: Accept worse solutions probabilistically to escape local optima
5. **Advanced Neighborhoods**: 2-opt, 3-opt moves within batches
