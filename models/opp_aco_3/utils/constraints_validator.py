"""
Constraints validator for opp_aco_3.

Identical to opp_aco_2's validator: congestion is modeled as an additive
cost (wait time), not a hard constraint, so it never rejects a solution as
infeasible - two pickers queueing for the same node/edge is a scheduling
cost the objective function penalizes, not a physical impossibility the
validator needs to forbid. All ALL-constraints checks below are unchanged
from opp_aco_2 / opp_model_v4.
"""

from typing import Dict, List, Set


class ConstraintsValidator:
    """Validates that a solution satisfies all OPP v4 constraints."""

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
        """(14) Every batch with orders must be assigned to exactly one picker."""
        if not self.batch_assignments.get(batch):
            return True
        return solution.get_batch_picker(batch) in self.P

    def _validate_batch_route(self, batch: str, route: list) -> bool:
        """Validate a single batch route against all constraints."""
        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()

        # (6) Start from depot
        if route and not self.location_graph.has_edge(depot, route[0]):
            return False

        # (7) Finish at final
        if route and not self.location_graph.has_edge(route[-1], final):
            return False

        # (8) Cannot return to depot
        for i in range(1, len(route)):
            if route[i] == depot:
                return False

        # (9) Cannot leave final
        # (implicitly satisfied if route ends at final in path, not traverses it)

        # (10), (11) Force visit required locations
        required = self._get_required_locations(batch)
        if not required.issubset(set(route)):
            return False

        # (12) Articles capacity - sum of C_n for orders in batch
        orders = self.batch_assignments[batch]
        total_capacity = sum(self.C_n.get(order, 0) for order in orders)
        if total_capacity > self.C_v:
            return False

        # (13) Flow conservation - implicitly satisfied in a simple path

        # (14), (15) One input/output arc per node - implicitly satisfied in a path

        # (17) No loops
        if len(route) != len(set(route)):
            return False

        # (25) Only valid edges
        if not self._validate_edges(route):
            return False

        return True

    def _get_required_locations(self, batch: str) -> Set:
        """Get all locations required by orders in batch."""
        required = set()
        orders = self.batch_assignments[batch]
        for order in orders:
            for vertex in self.location_graph.get_vertices():
                if vertex != self.location_graph.get_depot() and vertex != self.location_graph.get_final():
                    if self.A.get((order, vertex), 0) > 0:
                        required.add(vertex)
        return required

    def _validate_edges(self, route: list) -> bool:
        """Validate that all edges in route exist in graph."""
        if not route:
            return True

        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()

        if not self.location_graph.has_edge(depot, route[0]):
            return False

        for i in range(len(route) - 1):
            if not self.location_graph.has_edge(route[i], route[i + 1]):
                return False

        if not self.location_graph.has_edge(route[-1], final):
            return False

        return True
