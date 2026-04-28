from models.base.opp_location_graph import OPPLocationGraph

"""
   Scenario for test 1
"""


def basic_two_orders_capacity_limit():
    V = {"L1", "L2", "L3", "L4"}
    B = {"B1", "B2"}

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

    return V, B, w1, w2, gamma, delta, location_graph, cap_vehicle
