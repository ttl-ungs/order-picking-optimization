"""
Objective function evaluator for OPP v4 routes (same as exact model).

Batches assigned to the same picker are executed sequentially (their
completion times accumulate one after another); batches assigned to
different pickers are executed in parallel (each picker's queue starts
from time zero independently). This mirrors v_pb/v_b in the ZPL model:
sum_{p,b} v_pb[p,b] collapses to sum_b v_b[b] since exactly one picker
is assigned per batch.
"""

from typing import Dict, List, Set


class RouteEvaluator:
    """Evaluates the OPP v4 objective function for a given route solution."""

    def __init__(
        self,
        N: Set,
        B: Set,
        P: List[str],
        location_graph,
        batch_assignments: Dict[str, Set[str]],
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
        self.P = P
        self.location_graph = location_graph
        self.batch_assignments = batch_assignments
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
        self.S = S if isinstance(S, dict) else {}
        self.Dd = Dd
        self.M = M

    def evaluate(self, solution) -> float:
        """
        Evaluate objective function:
        W_full * sum(v_b) + W_ea_ta * (W_ea * sum(ea_n) + W_ta * sum(ta_n))
        """
        batch_times = self.compute_batch_completions(solution)

        # Calculate earliness and tardiness for each order
        earliness_total = 0.0
        tardiness_total = 0.0

        for order in self.N:
            # Find which batch this order belongs to
            batch = None
            for b in self.B:
                if order in self.batch_assignments[b]:
                    batch = b
                    break

            if batch is None or batch not in batch_times:
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

        objective = self.W_full * recollection_time + self.W_ea_ta * penalty

        return objective

    def compute_batch_completions(self, solution) -> Dict[str, float]:
        """
        Compute v_b[b]: the completion time of each batch, given the picker
        it is assigned to and its position within that picker's sequence.
        Pickers process their assigned batches sequentially starting from
        time zero; different pickers work in parallel.
        """
        batch_times: Dict[str, float] = {}

        for picker in self.P:
            cumulative_time = 0.0
            for batch in solution.get_picker_sequence(picker):
                orders = self.batch_assignments.get(batch, set())
                route = solution.get_batch_route(batch)
                exec_time = self._calculate_batch_execution_time(batch, route, orders)
                cumulative_time += exec_time
                batch_times[batch] = cumulative_time

        return batch_times

    def _calculate_batch_execution_time(self, batch: str, route: list, orders: Set[str]) -> float:
        """
        Calculate execution time for a batch route:
        t_exec = B_setup + B_picking * sum(C_n) + B_time * travel_distance + service_time
        """
        # Setup time
        setup_time = self.B_setup

        # Picking time: sum of capacities for all orders in batch
        picking_capacity = sum(self.C_n.get(order, 0) for order in orders)
        picking_time = self.B_picking * picking_capacity

        # Travel time from route distance
        travel_distance = self._calculate_route_distance(route)
        travel_time = self.B_time * travel_distance

        # Service time: sum of service times for each location in route
        service_time = sum(self.S.get(loc, 0) for loc in route)

        return setup_time + picking_time + travel_time + service_time

    def _calculate_route_distance(self, route: list) -> float:
        """Calculate total distance of a route."""
        if not route:
            return 0.0

        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()
        total_distance = 0.0

        # Depot to first location
        if route:
            total_distance += self.location_graph.get_distance(depot, route[0])

        # Between locations in route
        for i in range(len(route) - 1):
            total_distance += self.location_graph.get_distance(route[i], route[i+1])

        # Last location to final
        if route:
            total_distance += self.location_graph.get_distance(route[-1], final)

        return total_distance
