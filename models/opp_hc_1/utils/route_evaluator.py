"""
Objective function evaluator for OPP v3 routes (same as exact model).
"""

from typing import Dict, Set


class RouteEvaluator:
    """Evaluates the OPP v3 objective function for a given route solution."""

    def __init__(
        self,
        N: Set,
        B: Set,
        location_graph,
        batch_assignments: Dict[str, Set[str]],
        W_c: float,
        W_pen: float,
        W_e: float,
        W_t: float,
        C_n: Dict,
        C_v: float,
        A: Dict,
        T_travel: float,
        T_setup: float,
        T_pick: float,
        S: Dict,
        T_due_n: Dict,
        M: float,
    ):
        self.N = N
        self.B = B
        self.location_graph = location_graph
        self.batch_assignments = batch_assignments
        self.W_c = W_c
        self.W_pen = W_pen
        self.W_e = W_e
        self.W_t = W_t
        self.C_n = C_n
        self.C_v = C_v
        self.A = A
        self.T_travel = T_travel
        self.T_setup = T_setup
        self.T_pick = T_pick
        self.S = S if isinstance(S, dict) else {}
        self.T_due_n = T_due_n
        self.M = M

    def evaluate(self, solution) -> float:
        """
        Evaluate objective function:
        W_c * sum(c_b) + W_pen * (W_e * sum(ea_n) + W_t * sum(ta_n))
        """
        # Calculate completion time for each batch
        batch_times = {}
        cumulative_time = 0.0

        for batch in sorted(self.B):
            route = solution.get_batch_route(batch)
            orders = self.batch_assignments[batch]

            # Calculate execution time for this batch
            exec_time = self._calculate_batch_execution_time(batch, route, orders)
            cumulative_time += exec_time
            batch_times[batch] = cumulative_time

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

            if batch is None:
                continue

            completion_time = batch_times[batch]
            due_date = self.T_due_n.get(order, float("inf"))

            if completion_time < due_date:
                earliness_total += due_date - completion_time
            else:
                tardiness_total += completion_time - due_date

        # Calculate objective
        recollection_time = sum(batch_times.values()) if batch_times else 0.0
        penalty = self.W_e * earliness_total + self.W_t * tardiness_total

        objective = self.W_c * recollection_time + self.W_pen * penalty

        return objective

    def _calculate_batch_execution_time(self, batch: str, route: list, orders: Set[str]) -> float:
        """
        Calculate execution time for a batch route:
        t_exec = T_setup + T_pick * sum(C_n) + T_travel * travel_distance + service_time
        """
        # Setup time
        setup_time = self.T_setup

        # Picking time: sum of capacities for all orders in batch
        picking_capacity = sum(self.C_n.get(order, 0) for order in orders)
        picking_time = self.T_pick * picking_capacity

        # Travel time from route distance
        travel_distance = self._calculate_route_distance(route)
        travel_time = self.T_travel * travel_distance

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
