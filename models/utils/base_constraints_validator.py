"""
Constraints validator shared by the heuristics: the routing and assignment
constraints of the exact models, checked on a RouteSolution. The numbers in
the comments are those of the constraints in models/opp_mono/opp_mono.zpl.
"""

from typing import Dict, List, Set


class ConstraintsValidator:
    """Validates that a solution satisfies all the constraints of the problem."""

    def __init__(
        self,
        N: Set,
        B: Set,
        location_graph,
        batch_assignments: Dict[str, Set[str]],
        C_n: Dict,
        C_v: float,
        A: Dict,
        P: List[str] = None,
    ):
        self.N = N
        self.B = B
        self.location_graph = location_graph
        self.batch_assignments = batch_assignments
        self.C_n = C_n
        self.C_v = C_v
        self.A = A
        self.P = P or ["P1"]
        self._required_locations_cache: Dict[str, Set] = {}

    def validate_solution(self, solution) -> bool:
        """Validate entire solution against all constraints."""
        for batch in self.B:
            route = solution.get_batch_route(batch)
            if not self._validate_batch_route(batch, route):
                return False
            if not self._validate_batch_picker_assignment(solution, batch):
                return False
        return True

    def _validate_batch_picker_assignment(self, solution, batch: str) -> bool:
        """(14) Every batch with orders is assigned to exactly one picker."""
        if not self.batch_assignments.get(batch):
            return True
        return solution.get_batch_picker(batch) in self.P

    def _validate_batch_route(self, batch: str, route: list) -> bool:
        """Validate one batch's route (the interior stops, without depot and final node)."""
        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()

        # (1) The depot connects to the first stop
        if route and not self.location_graph.has_edge(depot, route[0]):
            return False

        # (2) The last stop connects to the final node
        if route and not self.location_graph.has_edge(route[-1], final):
            return False

        # (3) No return to the depot
        for i in range(1, len(route)):
            if route[i] == depot:
                return False

        # (5), (6) Every required location is visited
        required = self._get_required_locations(batch)
        if not required.issubset(set(route)):
            return False

        # Vehicle capacity (the exact models validate it on the input)
        orders = self.batch_assignments[batch]
        total_capacity = sum(self.C_n.get(order, 0) for order in orders)
        if total_capacity > self.C_v:
            return False

        # (8), (9) No location twice. With it, a list of stops is a simple
        # path, which also gives (4) and the flow conservation (7).
        if len(route) != len(set(route)):
            return False

        # Every arc of the route exists
        if not self._validate_edges(route):
            return False

        return True

    def _get_required_locations(self, batch: str) -> Set:
        """Locations the orders of `batch` must visit. Memoized: the batch
        composition never changes during the life of a validator."""
        cached = self._required_locations_cache.get(batch)
        if cached is not None:
            return cached

        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()
        required = set()
        orders = self.batch_assignments[batch]
        for order in orders:
            for vertex in self.location_graph.get_vertices():
                if vertex != depot and vertex != final:
                    if self.A.get((order, vertex), 0) > 0:
                        required.add(vertex)

        self._required_locations_cache[batch] = required
        return required

    def _validate_edges(self, route: list) -> bool:
        """Validate that all edges in route exist in graph."""
        if not route:
            return True

        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()

        # Check depot -> first
        if not self.location_graph.has_edge(depot, route[0]):
            return False

        # Check edges in route
        for i in range(len(route) - 1):
            if not self.location_graph.has_edge(route[i], route[i+1]):
                return False

        # Check last -> final
        if not self.location_graph.has_edge(route[-1], final):
            return False

        return True
