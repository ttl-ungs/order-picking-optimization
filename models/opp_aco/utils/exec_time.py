"""
The T_exec_pb formula of opp_aco, in one place for the solver, the evaluator
and the validator:

    T_exec_pb[p, b] = fixed_time(b) + route_time(b) / V_p[p]

fixed_time(b) = T_setup + T_pick * sum(C_n over b's orders) does not depend
on the picker; route_time(b) = T_travel * travel_distance + service_time is
the part the picker's speed divides.

`route` is always the interior-only list RouteSolution stores (without depot
and final node).
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


def fixed_time(orders: Set[str], C_n: Dict, T_setup: float, T_pick: float) -> float:
    """Setup + picking time: the part of T_exec_pb that does not depend on the picker."""
    picking_capacity = sum(C_n.get(o, 0) for o in orders) if isinstance(C_n, dict) else 0
    return T_setup + T_pick * picking_capacity


def route_time(
    location_graph,
    route: List[str],
    T_travel: float,
    S: Dict,
    distance: Optional[float] = None,
) -> float:
    """
    Travel + service time: the part of T_exec_pb the picker's speed divides.
    `distance` may be passed when the caller already has it.
    """
    if not route:
        return 0.0
    if distance is None:
        distance = calculate_route_distance(location_graph, route)
    service_time = sum(S.get(loc, 0) for loc in route) if isinstance(S, dict) else 0
    return T_travel * distance + service_time


def T_exec_pb(
    location_graph,
    route: List[str],
    orders: Set[str],
    picker: str,
    C_n: Dict,
    T_setup: float,
    T_pick: float,
    T_travel: float,
    S: Dict,
    V_p: Dict[str, float],
    distance: Optional[float] = None,
) -> float:
    """T_exec_pb[p, b] = fixed_time(b) + route_time(b) / V_p[p]."""
    speed = (V_p or {}).get(picker, 1.0)
    return (
        fixed_time(orders, C_n, T_setup, T_pick)
        + route_time(location_graph, route, T_travel, S, distance) / speed
    )
