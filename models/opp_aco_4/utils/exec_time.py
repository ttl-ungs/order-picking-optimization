"""
Shared t_exec_pb formula for opp_aco_4:

    t_exec_pb[p, b] = fixed_time(b) + route_time(b) / V_p[p]

where fixed_time(b) = B_setup + B_picking * sum(C_n over b's orders) does
NOT depend on picker speed, and route_time(b) = B_time * travel_distance +
service_time is the part scaled by how fast the picker walks/scans.

Previously computed independently (and verified to compute the exact same
formula) in three places -- opp_aco_4.py (route construction/reporting),
route_evaluator.py (the search's objective function) and
constraints_validator.py (cold-chain eligibility) -- extracted here so a
future formula change only needs one edit instead of three kept in sync by
hand.

`route` throughout is the interior-only format RouteSolution stores
(depot/final excluded); every caller adds them back via location_graph.
"""

from typing import Dict, List, Optional, Set


def calculate_route_distance(location_graph, route: List[str]) -> float:
    """Total travel distance of depot -> route... -> final."""
    if not route:
        return 0.0

    depot = location_graph.get_depot()
    final = location_graph.get_final()

    total = location_graph.get_distance(depot, route[0])
    for i in range(len(route) - 1):
        total += location_graph.get_distance(route[i], route[i + 1])
    total += location_graph.get_distance(route[-1], final)
    return total


def fixed_time(orders: Set[str], C_n: Dict, B_setup: float, B_picking: float) -> float:
    """Setup + picking time -- the part of t_exec_pb that does NOT depend on picker speed."""
    picking_capacity = sum(C_n.get(o, 0) for o in orders) if isinstance(C_n, dict) else 0
    return B_setup + B_picking * picking_capacity


def route_time(
    location_graph,
    route: List[str],
    B_time: float,
    S: Dict,
    distance: Optional[float] = None,
) -> float:
    """
    Travel time (B_time * distance) + service time -- the part of t_exec_pb
    scaled by picker speed. Pass `distance` when the caller already
    computed it, to avoid recomputing it again here (distance doesn't
    depend on picker at all).
    """
    if not route:
        return 0.0
    if distance is None:
        distance = calculate_route_distance(location_graph, route)
    service_time = sum(S.get(loc, 0) for loc in route) if isinstance(S, dict) else 0
    return B_time * distance + service_time


def t_exec_pb(
    location_graph,
    route: List[str],
    orders: Set[str],
    picker: str,
    C_n: Dict,
    B_setup: float,
    B_picking: float,
    B_time: float,
    S: Dict,
    V_p: Dict[str, float],
    distance: Optional[float] = None,
) -> float:
    """t_exec_pb[p, b] = fixed_time(b) + route_time(b) / V_p[p]."""
    speed = (V_p or {}).get(picker, 1.0)
    return (
        fixed_time(orders, C_n, B_setup, B_picking)
        + route_time(location_graph, route, B_time, S, distance) / speed
    )
