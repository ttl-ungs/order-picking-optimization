"""
Objective function evaluator for OPP Hill Climbing.
"""

from typing import Dict, Set
from models.opp_hill_climbing.utils.solution import Solution


class Evaluator:
    """Evaluates the objective function for OPP solutions."""

    def __init__(
        self,
        N: Set,
        B: Set,
        location_graph,
        W_full: float,
        W_ea_ta: float,
        W_ea: float,
        W_ta: float,
        C_n: Dict,
        C_v: float,
        A: Dict,
        B_time: float,
        B_setup: float,
        B_picking: float,
        S: Dict,
        Dd: Dict,
        M: float,
    ):
        self.N = N
        self.B = B
        self.location_graph = location_graph
        self.W_full = W_full
        self.W_ea_ta = W_ea_ta
        self.W_ea = W_ea
        self.W_ta = W_ta
        self.C_n = C_n
        self.C_v = C_v
        self.A = A
        self.B_time = B_time
        self.B_setup = B_setup
        self.B_picking = B_picking
        self.S = S if S else {}
        self.Dd = Dd
        self.M = M

    def evaluate(self, solution: Solution) -> float:
        """
        Evaluate the objective function:
        W_full * sum(v_b) + W_ea_ta * (W_ea * sum(ea_n) + W_ta * sum(ta_n))
        """
        # Calculate execution time for each batch
        batch_times = {}
        cumulative_time = 0.0

        for batch in sorted(self.B):
            orders_in_batch = solution.batch_assignments[batch]

            if not orders_in_batch:
                batch_times[batch] = 0.0
                continue

            # Calculate execution time for this batch
            exec_time = self._calculate_batch_execution_time(batch, orders_in_batch)
            cumulative_time += exec_time
            batch_times[batch] = cumulative_time

        # Calculate earliness and tardiness
        earliness_total = 0.0
        tardiness_total = 0.0

        for order in self.N:
            batch = solution.get_batch_for_order(order)
            if batch is None:
                continue

            completion_time = batch_times[batch]
            due_date = self.Dd.get(order, float("inf"))

            if completion_time < due_date:
                earliness_total += due_date - completion_time
            else:
                tardiness_total += completion_time - due_date

        # Calculate objective
        recollection_time = sum(batch_times.values()) if batch_times else 0.0
        penalty = self.W_ea * earliness_total + self.W_ta * tardiness_total

        objective = (
            self.W_full * recollection_time + self.W_ea_ta * penalty
        )

        return objective

    def _calculate_batch_execution_time(self, batch: str, orders: Set[str]) -> float:
        """
        Calculate execution time for a batch:
        t_exec = B_setup + B_picking * sum(C_n[n]) + B_time * travel_distance + service_time
        """
        # Setup time
        setup_time = self.B_setup

        # Picking time
        picking_capacity = sum(self.C_n.get(order, 0) for order in orders)
        picking_time = self.B_picking * picking_capacity

        # Travel time and service time are approximated as a function of batch size
        # In a full solution we'd calculate the actual route distance
        travel_time = self.B_time * self._estimate_travel_distance(batch, orders)
        service_time = self._estimate_service_time(batch, orders)

        return setup_time + picking_time + travel_time + service_time

    def _estimate_travel_distance(self, batch: str, orders: Set[str]) -> float:
        """
        Estimate travel distance for a batch.
        Simplified: proportional to number of locations to visit.
        """
        locations_to_visit = set()

        for order in orders:
            for location in self.location_graph.get_vertices():
                if location != self.location_graph.get_depot():
                    if location != self.location_graph.get_final():
                        # Check if order must visit this location
                        if self.A.get((order, location), 0) > 0:
                            locations_to_visit.add(location)

        # Approximate distance as number of locations (simplified TSP estimate)
        if locations_to_visit:
            return len(locations_to_visit) * 10.0  # arbitrary unit

        return 0.0

    def _estimate_service_time(self, batch: str, orders: Set[str]) -> float:
        """
        Estimate service time for locations in batch.
        """
        service_time = 0.0

        for order in orders:
            for location in self.location_graph.get_vertices():
                if self.A.get((order, location), 0) > 0:
                    service_time += self.S.get(location, 0)

        return service_time
