"""
Hill Climbing heuristic for Order Picking Problem (OPP).

Generates an initial solution and improves it iteratively by making
local moves that reduce the objective function.
"""

import time
import random
from typing import Dict, Tuple, Set

from models.base.model import Model
from dtos.opp.solve_model_dto import SolveModelDTO
from dtos.opp.model_dto import ModelDTO
from models.opp_hill_climbing.utils.solution import Solution
from models.opp_hill_climbing.utils.evaluator import Evaluator
from models.opp_hill_climbing.utils.route_optimizer import RouteOptimizer


class OPPHillClimbing(Model):
    def __init__(self, dto: ModelDTO):
        super().__init__()
        self.N = sorted(dto.N)
        self.location_graph = dto.location_graph
        self.B = sorted(dto.B)
        self.T_0 = dto.start_time

    def solve(self, params: SolveModelDTO):
        """
        Solve the OPP using hill climbing heuristic.
        Returns (status, solution_dict).
        """
        start_time = self.T_0 if self.T_0 is not None else time.time()

        evaluator = Evaluator(
            N=self.N,
            B=self.B,
            location_graph=self.location_graph,
            W_full=params.W_full,
            W_ea_ta=params.W_ea_ta,
            W_ea=params.W_ea,
            W_ta=params.W_ta,
            C_n=params.C_n,
            C_v=params.C_v,
            A=params.A,
            B_time=params.B_time,
            B_setup=params.B_setup,
            B_picking=params.B_picking,
            S=params.S,
            Dd=params.Dd,
            M=params.M,
        )

        route_optimizer = RouteOptimizer(self.location_graph)

        # Generate initial solution
        current_solution = self._generate_initial_solution()

        # Optimize routes for current solution
        for batch in current_solution.batch_assignments.values():
            route_optimizer.optimize_route(batch)

        current_cost = evaluator.evaluate(current_solution)
        iteration = 0
        max_iterations = 1000
        no_improvement_count = 0
        max_no_improvement = 50

        improvement_log = [(iteration, current_cost)]

        # Hill climbing main loop
        while iteration < max_iterations and no_improvement_count < max_no_improvement:
            iteration += 1

            # Generate neighbor
            neighbor_solution = self._generate_neighbor(current_solution)

            # Optimize routes for neighbor
            for batch in neighbor_solution.batch_assignments.values():
                route_optimizer.optimize_route(batch)

            neighbor_cost = evaluator.evaluate(neighbor_solution)

            # Accept if better
            if neighbor_cost < current_cost:
                current_solution = neighbor_solution
                current_cost = neighbor_cost
                no_improvement_count = 0
                improvement_log.append((iteration, current_cost))
            else:
                no_improvement_count += 1

        elapsed = time.time() - start_time

        print(f"\nHill Climbing execution time: {elapsed:.4f}s")
        print(f"Final objective value: {current_cost:.4f}")
        print(f"Iterations: {iteration}")
        print(f"Improvements: {len(improvement_log) - 1}")

        # Build output dictionary
        output = self._build_solution_dict(current_solution, current_cost)

        return "optimal", output

    def _generate_initial_solution(self) -> Solution:
        """
        Generate initial solution using a greedy heuristic:
        - Sort orders by capacity
        - Assign each order to the first batch with available capacity
        """
        solution = Solution(self.N, self.B)

        # Sort orders by capacity (descending)
        sorted_orders = sorted(self.N, key=lambda n: -1)

        for order in sorted_orders:
            # Try to assign to a batch
            assigned = False
            for batch in self.B:
                if solution.can_add_order_to_batch(order, batch):
                    solution.assign_order_to_batch(order, batch)
                    assigned = True
                    break

            if not assigned:
                # Assign to first batch if forced (may violate capacity temporarily)
                if self.B:
                    solution.assign_order_to_batch(order, self.B[0])

        return solution

    def _generate_neighbor(self, solution: Solution) -> Solution:
        """
        Generate a neighbor solution by:
        1. Randomly select an order
        2. Move it to a different batch
        """
        neighbor = solution.copy()

        if not self.N:
            return neighbor

        # Select random order
        order = random.choice(list(self.N))

        # Get all batches
        all_batches = set(self.B)

        # Try to move to a different batch
        current_batch = neighbor.get_batch_for_order(order)

        if current_batch is not None:
            # Remove from current batch
            neighbor.remove_order_from_batch(order, current_batch)

        # Try to assign to a random different batch
        available_batches = list(all_batches)
        random.shuffle(available_batches)

        assigned = False
        for batch in available_batches:
            if batch != current_batch and neighbor.can_add_order_to_batch(order, batch):
                neighbor.assign_order_to_batch(order, batch)
                assigned = True
                break

        # If can't assign, put back in original (or any batch)
        if not assigned:
            if current_batch is not None:
                neighbor.assign_order_to_batch(order, current_batch)
            elif self.B:
                neighbor.assign_order_to_batch(order, self.B[0])

        return neighbor

    def _build_solution_dict(self, solution: Solution, cost: float) -> Dict:
        """
        Convert solution to output dictionary format.
        """
        return {
            "assignments": solution.assignments,
            "batch_assignments": solution.batch_assignments,
            "cost": cost,
        }
