"""
Example usage of the OPP Ant Colony Optimization v3 heuristic
(congestion-aware, multi-pheromone m-ACO4).

Same input format as opp_aco_2 (fixed Bn batches + set of pickers P), plus
new congestion/multi-pheromone hyperparameters exposed by SolveAco3ModelDTO.
This example purposefully forces two pickers through the SAME bottleneck
location (L2) so the congestion wait time is non-zero and visible in the
printed output.
"""

from pathlib import Path
import sys

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from models.opp_aco_3 import OPPAntColonyOptimization
from models.opp_aco_3.utils.output_handler import OutputHandler
from dtos.opp.model_dto import ModelDTO
from dtos.aco.solve_aco_3_model_dto import SolveAco3ModelDTO
from models.base.opp_location_graph import OPPLocationGraph


def example_bottleneck_instance():
    """
    Two pickers, two batches, and a warehouse layout with a single
    bottleneck location (L2) both batches must pass through - the simplest
    case where the congestion mechanism should introduce a wait time.
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

    solve_dto = SolveAco3ModelDTO()
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
    # L2's high service time makes it a realistic bottleneck: while one
    # picker services it, the other must wait.
    solve_dto.S = {"L1": 1.0, "L2": 6.0, "L3": 1.0}

    solve_dto.Dd = {"O1": 60.0, "O2": 60.0, "O3": 60.0, "O4": 60.0}
    solve_dto.M = 1000.0

    solve_dto.Bn = {
        ("O1", "B1"): 1, ("O2", "B1"): 1,
        ("O3", "B2"): 1, ("O4", "B2"): 1,
    }

    # ACO hyperparameters (defaults already tuned per Lesch et al., 2023)
    solve_dto.A_ants = 15
    solve_dto.Max_it = 40
    solve_dto.Min_dwell = 1.0  # minimum turnaround buffer, even at zero-service nodes
    solve_dto.P_objective_switch = 0.5

    solver = OPPAntColonyOptimization(model_dto)
    solver.attach(OutputHandler())
    solve_result = solver.solve(solve_dto)

    print(f"\nSolution Status: {solve_result.status}")
    return solve_result


if __name__ == "__main__":
    print("=" * 60)
    print("OPP Ant Colony Optimization v3 Example (congestion + m-ACO4)")
    print("=" * 60)
    example_bottleneck_instance()
