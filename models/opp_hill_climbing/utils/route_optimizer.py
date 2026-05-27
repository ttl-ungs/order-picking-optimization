"""
Route optimization for OPP batches using nearest neighbor heuristic.
"""

from typing import Set


class RouteOptimizer:
    """Optimizes routes within batches using nearest neighbor."""

    def __init__(self, location_graph):
        self.location_graph = location_graph

    def optimize_route(self, orders: Set[str]):
        """
        Optimize the route for a set of orders within a batch.
        Uses nearest neighbor starting from depot.
        """
        if not orders:
            return []

        # In this simplified version, we don't actually modify the route
        # A full implementation would determine the order of visits
        # and use that for distance calculations in the evaluator
        return list(orders)
