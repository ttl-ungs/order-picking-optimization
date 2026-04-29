from models.base.opp_location_graph import OPPLocationGraph


def longer_single_mission_route():
    V = {"L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9"}
    B = {"B1"}

    opp_location_graph = OPPLocationGraph("L1", "L9")

    for i in range(2, 9):
        opp_location_graph.add_vertex(f"L{i}", "picking")

    opp_location_graph.add_edge("L1", "L2", 2)
    opp_location_graph.add_edge("L2", "L1", 2)

    opp_location_graph.add_edge("L2", "L3", 2)
    opp_location_graph.add_edge("L3", "L2", 2)

    opp_location_graph.add_edge("L3", "L4", 2)
    opp_location_graph.add_edge("L4", "L3", 2)

    opp_location_graph.add_edge("L4", "L5", 2)
    opp_location_graph.add_edge("L5", "L4", 2)

    opp_location_graph.add_edge("L5", "L6", 2)
    opp_location_graph.add_edge("L6", "L5", 2)

    opp_location_graph.add_edge("L6", "L7", 2)
    opp_location_graph.add_edge("L7", "L6", 2)

    opp_location_graph.add_edge("L7", "L9", 2)
    opp_location_graph.add_edge("L9", "L7", 2)

    opp_location_graph.add_edge("L2", "L4", 5)
    opp_location_graph.add_edge("L4", "L2", 5)

    opp_location_graph.add_edge("L3", "L5", 5)
    opp_location_graph.add_edge("L5", "L3", 5)

    opp_location_graph.add_edge("L4", "L6", 5)
    opp_location_graph.add_edge("L6", "L4", 5)

    opp_location_graph.add_edge("L5", "L7", 5)
    opp_location_graph.add_edge("L7", "L5", 5)

    opp_location_graph.add_edge("L8", "L9", 5)
    opp_location_graph.add_edge("L9", "L8", 5)

    w1 = 1.0
    w2 = 10.0
    gamma = 1.0
    delta = 5.0
    cap_vehicle = 12.0

    return V, B, w1, w2, gamma, delta, opp_location_graph, cap_vehicle
