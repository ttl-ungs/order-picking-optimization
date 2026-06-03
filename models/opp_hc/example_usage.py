"""
Example usage of OPP Hill Climbing V3 heuristic.

This script demonstrates how to use the Hill Climbing solver with the same input
format as the exact solver (opp_model_v3). The key difference:
- Input: Fixed batch assignments (Bn parameter)
- Optimize: Routes within each batch
"""

from pathlib import Path
import sys

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from models.opp_hc import OPPHillClimbing
from dtos.opp.model_dto import ModelDTO
from dtos.opp.solve_model_dto import SolveModelDTO
from models.base.opp_location_graph import OPPLocationGraph


def example_small_instance():
    """
    Example with fixed batch assignments.
    """

    # Create model DTO
    model_dto = ModelDTO()

    # Orders and batches
    model_dto.N = {"O1", "O2", "O3", "O4", "O5"}
    model_dto.B = {"B1", "B2"}

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
    solve_dto = SolveModelDTO()

    # Objective weights
    solve_dto.W_full = 1.0
    solve_dto.W_ea_ta = 1.0
    solve_dto.W_ea = 0.1
    solve_dto.W_ta = 0.5

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
    solve_dto.B_time = 0.5
    solve_dto.B_setup = 5.0
    solve_dto.B_picking = 0.1
    solve_dto.S = {"L1": 2.0, "L2": 3.0, "L3": 1.5}

    # Due dates
    solve_dto.Dd = {
        "O1": 100.0, "O2": 80.0, "O3": 120.0, "O4": 90.0, "O5": 110.0,
    }

    # Big M
    solve_dto.M = 1000.0

    # FIXED batch assignments (Bn parameter)
    # This is the key difference: routes are optimized WITHIN these fixed assignments
    solve_dto.Bn = {
        ("O1", "B1"): 1, ("O2", "B1"): 1, ("O3", "B1"): 0,
        ("O4", "B2"): 1, ("O5", "B2"): 1, ("O3", "B2"): 1,
        # All other combinations are 0 (implicit)
    }

    # Solve
    solver = OPPHillClimbing(model_dto)
    status, output_graph = solver.solve(solve_dto)

    print(f"\nSolution Status: {status}")
    print(f"Output graph vertices: {output_graph.get_vertices()}")
    print(f"Output graph edges: {[(i, j) for i in output_graph.get_vertices() for j in output_graph.get_vertices() if output_graph.has_edge(i, j)]}")

    return output_graph


if __name__ == "__main__":
    print("=" * 60)
    print("OPP Hill Climbing V3 Example")
    print("=" * 60)
    example_small_instance()
