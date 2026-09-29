"""
Example usage of the OPP Ant Colony Optimization V4 heuristic (picker-parallel).

This script demonstrates how to use the ACO solver with the same input
format as the exact solver (opp_model_v4). The key differences vs. opp_aco_1 (v3):
- Input: Fixed batch assignments (B_nb parameter) + a set of pickers (P)
- Optimize: Routes within each batch (probabilistic ACO construction) AND the
  assignment/sequencing of batches to pickers (X_pb), so batches on different
  pickers run in parallel
"""

from pathlib import Path
import sys

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from models.opp_aco_2 import OPPAntColonyOptimization
from models.opp_aco_2.utils.output_handler import OutputHandler
from dtos.opp.model_dto import ModelDTO
from dtos.aco.solve_aco_model_dto import SolveAcoModelDTO
from models.base.opp_location_graph import OPPLocationGraph


def example_small_instance():
    """
    Example with fixed batch assignments and two pickers working in parallel.
    """

    # Create model DTO
    model_dto = ModelDTO()

    # Orders, batches and pickers
    model_dto.N = {"O1", "O2", "O3", "O4", "O5"}
    model_dto.B = {"B1", "B2"}
    model_dto.P = {"P1", "P2"}

    # Create location graph
    location_graph = OPPLocationGraph(depot_node="D", final_node="F")

    # Add vertices
    location_graph.add_vertex("D", "depot")
    location_graph.add_vertex("L1", "picking")
    location_graph.add_vertex("L2", "picking")
    location_graph.add_vertex("L3", "picking")
    location_graph.add_vertex("F", "final")

    # Add edges
    distances = {
        ("D", "L1"): 10,
        ("D", "L2"): 15,
        ("D", "L3"): 20,
        ("L1", "L2"): 5,
        ("L1", "L3"): 12,
        ("L2", "L3"): 8,
        ("L1", "F"): 10,
        ("L2", "F"): 12,
        ("L3", "F"): 15,
    }

    for (i, j), dist in distances.items():
        location_graph.add_edge(i, j, dist)
        location_graph.add_edge(j, i, dist)  # Undirected

    model_dto.location_graph = location_graph
    model_dto.start_time = 0.0

    # Create solve DTO
    solve_dto = SolveAcoModelDTO()

    # Objective weights
    solve_dto.W_c = 1.0
    solve_dto.W_pen = 1.0
    solve_dto.W_e = 0.1
    solve_dto.W_t = 0.5

    # Capacity
    solve_dto.C_n = {"O1": 5, "O2": 3, "O3": 4, "O4": 2, "O5": 6}
    solve_dto.C_v = 20.0

    # Assignment matrix: which orders need which locations
    solve_dto.A = {
        ("O1", "L1"): 1, ("O1", "L2"): 0, ("O1", "L3"): 0,
        ("O2", "L1"): 0, ("O2", "L2"): 1, ("O2", "L3"): 0,
        ("O3", "L1"): 1, ("O3", "L2"): 1, ("O3", "L3"): 0,
        ("O4", "L1"): 0, ("O4", "L2"): 0, ("O4", "L3"): 1,
        ("O5", "L1"): 1, ("O5", "L2"): 0, ("O5", "L3"): 1,
    }

    # Time parameters
    solve_dto.T_travel = 0.5
    solve_dto.T_setup = 5.0
    solve_dto.T_pick = 0.1
    solve_dto.S = {"L1": 2.0, "L2": 3.0, "L3": 1.5}

    # Due dates
    solve_dto.T_due_n = {
        "O1": 100.0, "O2": 80.0, "O3": 120.0, "O4": 90.0, "O5": 110.0,
    }

    # Big M
    solve_dto.M = 1000.0

    # FIXED batch assignments (B_nb parameter)
    solve_dto.B_nb = {
        ("O1", "B1"): 1, ("O2", "B1"): 1, ("O3", "B1"): 0,
        ("O4", "B2"): 1, ("O5", "B2"): 1, ("O3", "B2"): 1,
        # All other combinations are 0 (implicit)
    }

    # ACO metaheuristic hyperparameters
    solve_dto.A_ants = 12
    solve_dto.Max_it = 40
    solve_dto.Alpha = 1.0
    solve_dto.Beta = 2.0
    solve_dto.E = 0.1
    solve_dto.Q = 100.0

    # Solve
    solver = OPPAntColonyOptimization(model_dto)
    solver.attach(OutputHandler())
    solve_result = solver.solve(solve_dto)

    print(f"\nSolution Status: {solve_result.status}")

    return solve_result


if __name__ == "__main__":
    print("=" * 60)
    print("OPP Ant Colony Optimization V4 Example")
    print("=" * 60)
    example_small_instance()
