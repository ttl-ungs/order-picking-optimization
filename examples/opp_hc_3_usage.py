"""
Example usage of the OPP Hill Climbing v3 heuristic (congestion-aware).

Same input format as opp_hc_2 (fixed Bn batches + set of pickers P), plus
the new Min_dwell congestion hyperparameter exposed by SolveHC3ModelDTO.
This example forces two pickers through the SAME bottleneck location (L2)
so the congestion wait time is non-zero and visible in the printed output -
same scenario as opp_aco_3's example, for a direct comparison.
"""

from pathlib import Path
import sys

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from models.opp_hc_3 import OPPHillClimbing
from models.opp_hc_3.utils.output_handler import OutputHandler
from dtos.opp.model_dto import ModelDTO
from dtos.hc.solve_hc_3_model_dto import SolveHC3ModelDTO
from models.base.opp_location_graph import OPPLocationGraph


def example_bottleneck_instance():
    """
    Two pickers, two batches, and a warehouse layout with a single
    bottleneck location (L2) both batches must pass through.
    """
    model_dto = ModelDTO()
    model_dto.N = {"O1", "O2", "O3", "O4"}
    model_dto.B = {"B1", "B2"}
    model_dto.P = {"P1", "P2"}

    location_graph = OPPLocationGraph(depot_node="D", final_node="F")
    location_graph.add_vertex("D", "depot")
    location_graph.add_vertex("L1", "picking")
    location_graph.add_vertex("L2", "picking")  # bottleneck
    location_graph.add_vertex("L3", "picking")
    location_graph.add_vertex("F", "final")

    distances = {
        ("D", "L1"): 5, ("D", "L2"): 8, ("D", "L3"): 8,
        ("L1", "L2"): 3, ("L2", "L3"): 3,
        ("L1", "F"): 8, ("L2", "F"): 5, ("L3", "F"): 8,
    }
    for (i, j), dist in distances.items():
        location_graph.add_edge(i, j, dist)
        location_graph.add_edge(j, i, dist)

    model_dto.location_graph = location_graph
    model_dto.start_time = 0.0

    solve_dto = SolveHC3ModelDTO()
    solve_dto.W_full = 1.0
    solve_dto.W_ea_ta = 1.0
    solve_dto.W_ea = 0.1
    solve_dto.W_ta = 0.5

    solve_dto.C_n = {"O1": 3, "O2": 3, "O3": 3, "O4": 3}
    solve_dto.C_v = 10.0

    # Both batches must pass through L2 - a shared bottleneck.
    solve_dto.A = {
        ("O1", "L1"): 1, ("O1", "L2"): 1, ("O1", "L3"): 0,
        ("O2", "L1"): 0, ("O2", "L2"): 1, ("O2", "L3"): 0,
        ("O3", "L1"): 0, ("O3", "L2"): 1, ("O3", "L3"): 1,
        ("O4", "L1"): 0, ("O4", "L2"): 1, ("O4", "L3"): 0,
    }

    solve_dto.B_time = 1.0
    solve_dto.B_setup = 2.0
    solve_dto.B_picking = 0.5
    # L2's high service time makes it a realistic bottleneck.
    solve_dto.S = {"L1": 1.0, "L2": 6.0, "L3": 1.0}

    solve_dto.Dd = {"O1": 60.0, "O2": 60.0, "O3": 60.0, "O4": 60.0}
    solve_dto.M = 1000.0

    solve_dto.Bn = {
        ("O1", "B1"): 1, ("O2", "B1"): 1,
        ("O3", "B2"): 1, ("O4", "B2"): 1,
    }

    solve_dto.Max_it = 300
    solve_dto.Max_imp = 30
    solve_dto.Min_dwell = 1.0

    solver = OPPHillClimbing(model_dto)
    solver.attach(OutputHandler())
    solve_result = solver.solve(solve_dto)

    print(f"\nSolution Status: {solve_result.status}")
    return solve_result


if __name__ == "__main__":
    print("=" * 60)
    print("OPP Hill Climbing v3 Example (congestion-aware)")
    print("=" * 60)
    example_bottleneck_instance()
