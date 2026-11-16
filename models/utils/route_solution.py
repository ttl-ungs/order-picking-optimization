"""
Route-based solution representation shared by the heuristics (Hill Climbing and Ant Colony Optimization).

Represents a solution as a collection of routes for each batch, plus the
assignment of each batch to a picker (x_pb) and the processing order (sequence)
of the batches assigned to each picker. Batches assigned to different pickers
run in parallel; batches assigned to the same picker run one after another,
in sequence order.
"""

from typing import Dict, List, Set, Optional
from copy import deepcopy


class RouteSolution:
    """Represents a solution with explicit routes for each batch and a picker assignment."""

    def __init__(
        self,
        batches: List[str],
        location_graph,
        batch_assignments: Dict[str, Set[str]],
        pickers: Optional[List[str]] = None,
    ):
        """
        Initialize solution.

        Args:
            batches: List of batch IDs
            location_graph: OPPLocationGraph
            batch_assignments: Dict mapping batch -> set of order IDs
            pickers: List of picker IDs (defaults to a single implicit picker)
        """
        self.batches = batches
        self.location_graph = location_graph
        self.batch_assignments = batch_assignments
        self.pickers = pickers if pickers else ["P1"]

        # routes[batch] = list of location IDs in order
        self.routes: Dict[str, List] = {batch: [] for batch in batches}

        # picker_of[batch] = picker assigned to that batch (x_pb == 1)
        self.picker_of: Dict[str, str] = {}

        # sequence[picker] = ordered list of batches processed by that picker
        self.sequence: Dict[str, List[str]] = {p: [] for p in self.pickers}

    def set_batch_route(self, batch: str, route: List):
        """Set the route for a batch."""
        self.routes[batch] = route.copy()

    def get_batch_route(self, batch: str) -> List:
        """Get the route for a batch."""
        return self.routes[batch].copy()

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
        return new_solution

    def to_z_dict(self) -> Dict[tuple, int]:
        """
        Convert routes to z_ijb format (binary dict indicating if arc (i,j) is in batch b).

        Returns:
            Dict[(i, j, batch)] = 1 if arc is used, 0 otherwise
        """
        z = {}

        for batch in self.batches:
            route = self.routes[batch]

            # Initialize all arcs to 0
            for i in self.location_graph.get_vertices():
                for j in self.location_graph.get_vertices():
                    z[(i, j, batch)] = 0

            # Add depot -> first location
            depot = self.location_graph.get_depot()
            final = self.location_graph.get_final()

            if route:
                z[(depot, route[0], batch)] = 1

                # Add edges between locations
                for i in range(len(route) - 1):
                    z[(route[i], route[i+1], batch)] = 1

                # Add last location -> final
                z[(route[-1], final, batch)] = 1

        return z
