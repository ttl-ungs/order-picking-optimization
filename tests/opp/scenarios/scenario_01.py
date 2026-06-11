from models.base.opp_location_graph import OPPLocationGraph

"""
   Scenario for test 1
"""


def basic_two_orders_capacity_limit():
    V = {"L1", "L2", "L3", "L4"}
    H = {"M1", "M2"}
    K = {1}
    P = {"P1", "P2"}
    B = set()

    location_graph = OPPLocationGraph(depot_node="L1", final_node="L4")

    for i in range(2, 4):
        location_graph.add_vertex(f"L{i}", "picking")

    location_graph.add_edge("L1", "L2", 10)
    location_graph.add_edge("L1", "L3", 12.0)
    location_graph.add_edge("L2", "L3", 5.0)
    location_graph.add_edge("L2", "L4", 10.0)
    location_graph.add_edge("L3", "L2", 5.0)
    location_graph.add_edge("L3", "L4", 10.0)

    w1 = 1.0
    w2 = 10.0
    gamma = 1.0
    delta = 5.0

    cap_vehicle = 5.0

    x = {(p, k, h): 0 for p in P for k in K for h in H}
    x[("P1", 1, "M1")] = 1
    x[("P2", 1, "M2")] = 1

    return V, H, K, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, x
