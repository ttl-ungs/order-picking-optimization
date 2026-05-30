"""
Route-based solution representation for OPP v3 Hill Climbing.

Represents a solution as a collection of routes for each batch.
"""

from typing import Dict, List, Set
from copy import deepcopy


class RouteSolution:
    """Represents a solution with explicit routes for each batch."""

    def __init__(self, batches: List[str], location_graph, batch_assignments: Dict[str, Set[str]]):
        """
        Initialize solution.

        Args:
            batches: List of batch IDs
            location_graph: OPPLocationGraph
            batch_assignments: Dict mapping batch -> set of order IDs
        """
        self.batches = batches
        self.location_graph = location_graph
        self.batch_assignments = batch_assignments

        # routes[batch] = list of location IDs in order
        self.routes: Dict[str, List] = {batch: [] for batch in batches}

    def set_batch_route(self, batch: str, route: List):
        """Set the route for a batch."""
        self.routes[batch] = route.copy()

    def get_batch_route(self, batch: str) -> List:
        """Get the route for a batch."""
        return self.routes[batch].copy()

    def copy(self) -> "RouteSolution":
        """Create a deep copy of the solution."""
        new_solution = RouteSolution(self.batches, self.location_graph, self.batch_assignments)
        new_solution.routes = deepcopy(self.routes)
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
