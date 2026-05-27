"""
Solution representation for OPP Hill Climbing.
"""

from typing import Dict, Set, Optional
from copy import deepcopy


class Solution:
    """Represents an OPP solution as assignment of orders to batches."""

    def __init__(self, orders: Set, batches: Set):
        self.orders = orders
        self.batches = batches

        # assignments[order] = batch
        self.assignments: Dict[str, Optional[str]] = {order: None for order in orders}

        # batch_assignments[batch] = set of orders
        self.batch_assignments: Dict[str, Set] = {batch: set() for batch in batches}

    def assign_order_to_batch(self, order: str, batch: str):
        """Assign an order to a batch."""
        # Remove from previous batch if assigned
        if self.assignments[order] is not None:
            self.batch_assignments[self.assignments[order]].discard(order)

        self.assignments[order] = batch
        self.batch_assignments[batch].add(order)

    def remove_order_from_batch(self, order: str, batch: str):
        """Remove an order from a batch."""
        if self.assignments[order] == batch:
            self.assignments[order] = None
            self.batch_assignments[batch].discard(order)

    def get_batch_for_order(self, order: str) -> Optional[str]:
        """Get the batch assigned to an order."""
        return self.assignments[order]

    def can_add_order_to_batch(self, order: str, batch: str) -> bool:
        """Check if an order can be added to a batch (simple check)."""
        # For now, always allow (capacity checks done in evaluator)
        return True

    def copy(self) -> "Solution":
        """Create a deep copy of the solution."""
        new_solution = Solution(self.orders, self.batches)
        new_solution.assignments = deepcopy(self.assignments)
        new_solution.batch_assignments = deepcopy(self.batch_assignments)
        return new_solution
