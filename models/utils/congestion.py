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
routes are built/priced one full batch at a time (see opp_aco_3.py, which
reserves incrementally as each ant's route is constructed, and opp_hc_3.py,
which prices an already-built route via `simulate_route_congestion` below),
so resource reservations are registered in a "round-robin by picker-queue
slot" causal order rather than a true continuous-time simulation of all
pickers at once. This is an approximation, not an exact replication of the paper.
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

    def snapshot(self) -> Dict[Hashable, List[Tuple[float, float, str]]]:
        """
        Cheap point-in-time copy of all reservations -- lets a
        caller try a reservation sequence and roll it back with `restore()`
        if it turns out to be wasted work, instead of committing every
        `reserve()` call unconditionally.
        """
        return {resource: list(intervals) for resource, intervals in self._busy.items()}

    def restore(self, snapshot: Dict[Hashable, List[Tuple[float, float, str]]]) -> None:
        """Roll back to a previous `snapshot()`, discarding any reservations made since."""
        self._busy = {resource: list(intervals) for resource, intervals in snapshot.items()}


def simulate_route_congestion(
    location_graph,
    full_route: List[str],
    owner: str,
    start_time: float,
    b_time: float,
    S: Dict[str, float],
    tracker: "CongestionTracker",
    depot: str,
    final: str,
) -> Tuple[float, float]:
    """
    Walk an already-built, complete route (depot -> ... -> final) through
    `tracker`, reserving each edge/node resource in causal order, and return
    (end_time, total_wait_incurred).

    Used by opp_hc_3, which builds a full route up front (Dijkstra-based
    nearest neighbor, see opp_hc_2) and only needs to *price* congestion
    against everyone else's already-registered reservations - unlike
    opp_aco_3's ants, which choose the next node step by step and reserve
    incrementally as they go (see opp_aco_3.py::_advance_and_reserve, which
    this function's logic mirrors for a fixed route instead of a
    node-by-node probabilistic choice).
    """
    current = full_route[0]
    current_time = start_time
    total_wait = 0.0

    for next_node in full_route[1:]:
        dist = location_graph.get_distance(current, next_node)
        dist = dist if dist > 0 and dist != float("inf") else 0.0
        travel_time = b_time * dist

        departure, edge_wait = tracker.reserve(
            CongestionTracker.edge_key(current, next_node), current_time, travel_time, owner
        )
        arrival = departure + travel_time
        total_wait += edge_wait

        if next_node in (depot, final):
            current_time = arrival
        else:
            dwell = tracker.dwell(S.get(next_node, 0.0))
            node_start, node_wait = tracker.reserve(
                CongestionTracker.node_key(next_node), arrival, dwell, owner
            )
            current_time = node_start + dwell
            total_wait += node_wait

        current = next_node

    return current_time, total_wait
