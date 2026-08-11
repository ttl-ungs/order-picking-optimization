"""
Lightweight congestion tracker shared by picker-aware heuristics.

Adapts, to our abstract `OPPLocationGraph` (plain nodes + distances, with no
aisle/sub-aisle/block coordinates), the core idea behind:

    Chen, F., Wang, H., Qi, C., & Xie, Y. (2013). An ant colony optimization
    routing algorithm for two order pickers with congestion consideration.
    Computers & Industrial Engineering, 66(1), 77-85. (Sec. 4.2.1, p.79-80)

That paper computes a "logic travel distance" (physical travel time + the
wait incurred because another picker occupies the same sub-aisle) and keeps
a spatio-temporal tabu list marking, per sub-aisle, the interval during which
it is inaccessible to the other picker. Our graph has no sub-aisle metadata,
so we approximate the same effect by treating every NODE and every EDGE
(undirected: a physical aisle segment, regardless of direction of travel) as
a capacity-1 resource: at most one picker may occupy it at a time. When a
second picker's estimated arrival falls inside another picker's occupancy
window, it must wait until the resource frees up - exactly the "wait time"
component of the paper's logic distance.

Simplification vs. the paper (documented for the thesis write-up): Chen et
al. re-plan step-by-step for exactly two pickers moving concurrently. Here,
routes are built one full batch at a time (see opp_aco_3.py), so resource
reservations are registered in a "round-robin by picker-queue slot" causal
order rather than a true continuous-time simulation of all pickers at once.
This is an approximation, not an exact replication of the paper.
"""

from typing import Dict, List, Tuple, Hashable


class CongestionTracker:
    """
    Tracks capacity-1 occupancy windows for graph resources (nodes and
    undirected edges) and resolves the wait time a picker must incur before
    it may occupy a resource that is already busy with another picker.
    """

    def __init__(self, min_dwell: float = 0.0):
        """
        Args:
            min_dwell: Minimum time a picker "physically occupies" a node
                even when its service time (S_i) is zero - i.e. the
                turnaround/maneuvering buffer. Defaults to 0.0 (no synthetic
                congestion beyond real service/travel times).
        """
        self.min_dwell = min_dwell
        # resource_key -> sorted list of (start, end, owner)
        self._busy: Dict[Hashable, List[Tuple[float, float, str]]] = {}

    @staticmethod
    def node_key(node: str) -> Hashable:
        return ("N", node)

    @staticmethod
    def edge_key(i: str, j: str) -> Hashable:
        """Undirected: traversing i->j occupies the same physical segment as j->i."""
        return ("E", tuple(sorted((i, j))))

    def peek_wait(self, resource: Hashable, requested_start: float, duration: float, owner: str) -> float:
        """Read-only lookahead: wait time `owner` would incur, without reserving."""
        start = requested_start
        for s, e, o in self._busy.get(resource, []):
            if o == owner:
                continue
            if start < e and s < start + duration:
                start = max(start, e)
        return max(0.0, start - requested_start)

    def reserve(self, resource: Hashable, requested_start: float, duration: float, owner: str) -> Tuple[float, float]:
        """
        Reserve `resource` for `owner` for `duration`, starting as close as
        possible to `requested_start`. Pushes the start forward past every
        conflicting interval owned by someone else (cascading delays, as in
        the paper's dynamic recalculation), then registers the interval.

        Returns:
            (actual_start, wait_time) where wait_time = actual_start - requested_start.
        """
        busy = self._busy.setdefault(resource, [])
        start = requested_start
        changed = True
        while changed:
            changed = False
            for s, e, o in busy:
                if o == owner:
                    continue
                if start < e and s < start + duration:
                    start = e
                    changed = True
        busy.append((start, start + duration, owner))
        busy.sort()
        return start, start - requested_start

    def dwell(self, service_time: float) -> float:
        """Node occupancy duration: max of the real service time and the min_dwell floor."""
        return max(self.min_dwell, service_time)
