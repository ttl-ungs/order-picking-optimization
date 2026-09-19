"""
Example usage script for the Ant Colony Optimization (ACO) solver.

This script demonstrates how to construct a basic routing scenario,
initialize the required DTOs, attach the decoupled OutputHandler observer,
and solve the problem instance using the ACO metaheuristic.
"""

import os
import sys

# Dynamic path resolution to ensure the project root is recognized prior to local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from dtos.opp.model_dto import ModelDTO
from dtos.aco.solve_aco_model_dto import SolveAcoModelDTO
from models.base.opp_location_graph import OPPLocationGraph
from models.opp_aco_1.opp_aco_1 import OPPAntColonyOptimization
from models.opp_aco_1.utils.output_handler import OutputHandler


def run_aco_example():
    """Sets up a mock picking scenario and executes the ACO solver."""

    # 1. Initialize the warehouse graph structure
    graph = OPPLocationGraph(depot_node="depot", final_node="final")

    # Add network vertices (depot, picking locations, and final node)
    graph.add_vertex("depot", "depot")
    graph.add_vertex("loc_1", "picking")
    graph.add_vertex("loc_2", "picking")
    graph.add_vertex("final", "final")

    # Define valid edges and physical distances between locations
    graph.add_edge("depot", "loc_1", 10.0)
    graph.add_edge("depot", "loc_2", 15.0)
    graph.add_edge("loc_1", "loc_2", 5.0)
    graph.add_edge("loc_1", "final", 12.0)
    graph.add_edge("loc_2", "final", 8.0)

    # 2. Setup the structural model parameters via ModelDTO
    model_dto = ModelDTO()
    model_dto.N = ["order_1", "order_2"]
    model_dto.B = ["batch_1"]
    model_dto.location_graph = graph
    model_dto.start_time = 0.0

    # 3. Setup runtime execution and heuristic hyperparameters via SolveAcoModelDTO
    solve_dto = SolveAcoModelDTO()

    # Objective function scaling weights (aligned with opp_v3 objective layout)
    solve_dto.W_full = 1.0
    solve_dto.W_ea_ta = 1.0
    solve_dto.W_ea = 0.5
    solve_dto.W_ta = 2.0

    # Vehicle and order capacity configurations
    solve_dto.C_v = 100.0
    solve_dto.C_n = {"order_1": 30.0, "order_2": 40.0}

    # Location visit requirements matrix (A)
    solve_dto.A = {
        ("order_1", "loc_1"): 1,
        ("order_1", "loc_2"): 0,
        ("order_2", "loc_1"): 0,
        ("order_2", "loc_2"): 1,
    }

    # Operational processing time variables
    solve_dto.B_time = 1.0  # Travel time factor per distance unit
    solve_dto.B_setup = 20.0  # Fixed setup time per batch execution
    solve_dto.B_picking = 2.0  # Time coefficient per picked item volume unit
    solve_dto.S = {"loc_1": 5.0, "loc_2": 5.0}  # Fixed service time at nodes

    # Temporal constraints (Due dates and Big-M penalty factor)
    solve_dto.Dd = {"order_1": 60.0, "order_2": 80.0}
    solve_dto.M = 1000.0

    # Structural initial batch assignments matrix (Bn)
    solve_dto.Bn = {
        ("order_1", "batch_1"): 1,
        ("order_2", "batch_1"): 1,
    }

    # Target ACO Metaheuristic Tunable Hyperparameters
    solve_dto.A_ants = 12  # Number of simulated ants per iteration
    solve_dto.Max_it = 40  # Maximum optimization iterations loop limit
    solve_dto.Alpha = 1.0  # Pheromone importance intensity factor (tau)
    solve_dto.Beta = 2.0  # Visibility heuristic desirability factor (eta)
    solve_dto.E = 0.1  # Evaporation coefficient rate (rho)
    solve_dto.Q = 100.0  # Pheromone deposit magnitude constant multiplier

    # 4. Instantiate the Solver and couple the Observer pattern OutputHandler
    model = OPPAntColonyOptimization(model_dto)
    output_handler = OutputHandler()
    model.attach(output_handler)

    # 5. Execute the Ant Colony Optimization routine
    print("Executing Ant Colony Optimization Example Run...")
    solve_result = model.solve(solve_dto)

    print(f"Process terminated with status token: {solve_result.status}")


if __name__ == "__main__":
    run_aco_example()
