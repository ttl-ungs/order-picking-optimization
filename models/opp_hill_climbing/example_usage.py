"""
Example usage of OPP Hill Climbing heuristic.

This script demonstrates how to use the hill climbing solver
with the same input format as the exact solver (opp_model_v3).
"""

from pathlib import Path
import sys

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from models.opp_hill_climbing import OPPHillClimbing
from dtos.opp.model_dto import ModelDTO
from dtos.opp.solve_model_dto import SolveModelDTO
from models.base.opp_location_graph import OPPLocationGraph


def example_small_instance():
    """
    Example with a small instance.
    Creates model DTO and solve DTO, then runs the hill climbing solver.
    """

    # Create model DTO
    model_dto = ModelDTO()

    # Example: 5 orders, 3 batches
    model_dto.N = {"O1", "O2", "O3", "O4", "O5"}
    model_dto.B = {"B1", "B2", "B3"}

    # Create location graph
    location_graph = OPPLocationGraph(depot_node="D", final_node="F")

    # Add vertices (depot, picking locations, final)
    location_graph.add_vertex("D", "depot")
    location_graph.add_vertex("L1", "picking")
    location_graph.add_vertex("L2", "picking")
    location_graph.add_vertex("L3", "picking")
    location_graph.add_vertex("F", "final")

    # Add edges (distances)
    for i in ["D", "L1", "L2", "L3"]:
        for j in ["D", "L1", "L2", "L3", "F"]:
            if i != j:
                # Example distances
                distance = 10.0
                location_graph.add_edge(i, j, distance)

    model_dto.location_graph = location_graph
    model_dto.start_time = 0.0

    # Create solve DTO
    solve_dto = SolveModelDTO()

    # Objective weights
    solve_dto.W_full = 1.0  # Weight for completion time
    solve_dto.W_ea_ta = 1.0  # Weight for earliness/tardiness penalties
    solve_dto.W_ea = 0.1  # Weight for earliness
    solve_dto.W_ta = 0.5  # Weight for tardiness (usually higher)

    # Capacity
    solve_dto.C_n = {"O1": 5, "O2": 3, "O3": 4, "O4": 2, "O5": 6}
    solve_dto.C_v = 20.0  # Vehicle capacity

    # Assignment matrix: A[order, location] = 1 if order must visit location
    solve_dto.A = {
        ("O1", "L1"): 1, ("O1", "L2"): 0, ("O1", "L3"): 0,
        ("O2", "L1"): 0, ("O2", "L2"): 1, ("O2", "L3"): 0,
        ("O3", "L1"): 1, ("O3", "L2"): 1, ("O3", "L3"): 0,
        ("O4", "L1"): 0, ("O4", "L2"): 0, ("O4", "L3"): 1,
        ("O5", "L1"): 1, ("O5", "L2"): 0, ("O5", "L3"): 1,
    }

    # Time parameters
    solve_dto.B_time = 0.5  # Travel time per unit distance
    solve_dto.B_setup = 5.0  # Setup time per batch
    solve_dto.B_picking = 0.1  # Time per unit capacity
    solve_dto.S = {"L1": 2.0, "L2": 3.0, "L3": 1.5}  # Service times

    # Due dates for each order
    solve_dto.Dd = {
        "O1": 100.0,
        "O2": 80.0,
        "O3": 120.0,
        "O4": 90.0,
        "O5": 110.0,
    }

    # Big M for linearization
    solve_dto.M = 1000.0

    # Create solver and solve
    solver = OPPHillClimbing(model_dto)
    status, solution = solver.solve(solve_dto)

    print(f"\nSolution Status: {status}")
    print(f"Solution: {solution}")

    return solution


if __name__ == "__main__":
    print("=" * 60)
    print("OPP Hill Climbing Example")
    print("=" * 60)
    example_small_instance()
