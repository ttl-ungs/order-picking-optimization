"""
Route-based solution representation for opp_aco_3.

Identical to opp_aco_2's RouteSolution (routes per batch + picker assignment
X_pb + per-picker processing sequence), plus a per-batch congestion wait time
accumulated while the route was built (see CongestionTracker in
models/utils/congestion.py and _build_batch_route_congestion_aware in
opp_aco_3.py). Storing it here - rather than recomputing it inside
RouteEvaluator - keeps the causal, order-dependent congestion simulation in a
single place (route construction), consistent for both the objective
function and the reported solution_info.
"""

from typing import Dict, List, Set, Optional
from copy import deepcopy


class RouteSolution:
    """Represents a solution with explicit routes for each batch, a picker
    assignment, and the congestion wait time incurred while building each
    batch's route."""

    def __init__(
        self,
        batches: List[str],
        location_graph,
        batch_assignments: Dict[str, Set[str]],
        pickers: Optional[List[str]] = None,
    ):
        self.batches = batches
        self.location_graph = location_graph
        self.batch_assignments = batch_assignments
        self.pickers = pickers if pickers else ["P1"]

        # routes[batch] = list of location IDs in order
        self.routes: Dict[str, List] = {batch: [] for batch in batches}

        # picker_of[batch] = picker assigned to that batch (X_pb == 1)
        self.picker_of: Dict[str, str] = {}

        # sequence[picker] = ordered list of batches processed by that picker
        self.sequence: Dict[str, List[str]] = {p: [] for p in self.pickers}

        # congestion_wait[batch] = total wait time (seconds) accumulated by
        # this batch's route while it was being built, due to nodes/edges
        # already occupied by another picker's batch (see CongestionTracker).
        self.congestion_wait: Dict[str, float] = {batch: 0.0 for batch in batches}

        # How many times a reservation had to wait for a busy node/edge
        # while this ant's routes were being built incrementally
        # (CongestionTracker.total_collisions()) -- a FREQUENCY metric,
        # distinct from congestion_wait (accumulated TIME lost).
        self.total_collisions: int = 0

    def set_batch_route(self, batch: str, route: List):
        """Set the route for a batch."""
        self.routes[batch] = route.copy()

    def get_batch_route(self, batch: str) -> List:
        """Get the route for a batch."""
        return self.routes[batch].copy()

    def set_batch_congestion_wait(self, batch: str, wait: float):
        """Record the total congestion wait time incurred while building this batch's route."""
        self.congestion_wait[batch] = wait

    def get_batch_congestion_wait(self, batch: str) -> float:
        """Total congestion wait time (seconds) incurred while building this batch's route."""
        return self.congestion_wait.get(batch, 0.0)

    def total_congestion_wait(self) -> float:
        """Sum of congestion wait time across every batch in the solution."""
        return sum(self.congestion_wait.values())

    def set_total_collisions(self, count: int):
        """Record how many node/edge reservations had to wait while this ant's routes were built."""
        self.total_collisions = count

    def get_total_collisions(self) -> int:
        """How many node/edge reservations had to wait while this ant's routes were built."""
        return self.total_collisions

    def assign_batch_to_picker(self, batch: str, picker: str, position: Optional[int] = None):
        """Assign a batch to a picker, appending it to (or inserting it into) the picker's sequence."""
        previous_picker = self.picker_of.get(batch)
        if previous_picker is not None and previous_picker in self.sequence:
            if batch in self.sequence[previous_picker]:
                self.sequence[previous_picker].remove(batch)

        self.picker_of[batch] = picker
        if picker not in self.sequence:
            self.sequence[picker] = []

        if position is None or position >= len(self.sequence[picker]):
            self.sequence[picker].append(batch)
        else:
            self.sequence[picker].insert(max(position, 0), batch)

    def get_batch_picker(self, batch: str) -> Optional[str]:
        """Get the picker assigned to a batch (None if not assigned)."""
        return self.picker_of.get(batch)

    def get_picker_sequence(self, picker: str) -> List[str]:
        """Get the ordered list of batches assigned to a picker."""
        return list(self.sequence.get(picker, []))

    def set_picker_sequence(self, picker: str, batches: List[str]):
        """Overwrite the processing order of batches for a picker."""
        self.sequence[picker] = list(batches)
        for batch in batches:
            self.picker_of[batch] = picker

    def copy(self) -> "RouteSolution":
        """Create a deep copy of the solution."""
        new_solution = RouteSolution(self.batches, self.location_graph, self.batch_assignments, self.pickers)
        new_solution.routes = deepcopy(self.routes)
        new_solution.picker_of = deepcopy(self.picker_of)
        new_solution.sequence = deepcopy(self.sequence)
        new_solution.congestion_wait = deepcopy(self.congestion_wait)
        new_solution.total_collisions = self.total_collisions
        return new_solution

    def to_z_dict(self) -> Dict[tuple, int]:
        """
        Convert routes to z_ijb format (binary dict indicating if arc (i,j) is in batch b).
        """
        z = {}

        for batch in self.batches:
            route = self.routes[batch]

            for i in self.location_graph.get_vertices():
                for j in self.location_graph.get_vertices():
                    z[(i, j, batch)] = 0

            depot = self.location_graph.get_depot()
            final = self.location_graph.get_final()

            if route:
                z[(depot, route[0], batch)] = 1

                for i in range(len(route) - 1):
                    z[(route[i], route[i + 1], batch)] = 1

                z[(route[-1], final, batch)] = 1

        return z
