from models.base.opp_location_graph import OPPLocationGraph


def _build_bridge_graph(connect_right=True):
    V = {
        "L1",
        "L2",
        "L3",
        "L4",
        "L5",
        "L6",
        "L7",
        "L8",
        "L9",
        "L10",
        "L11",
        "L12",
    }

    graph = OPPLocationGraph("L1", "L12")
    for i in range(2, 12):
        graph.add_vertex(f"L{i}", "picking")

    graph.add_edge("L1", "L2", 2)
    graph.add_edge("L2", "L1", 2)

    graph.add_edge("L2", "L3", 2)
    graph.add_edge("L3", "L2", 2)

    graph.add_edge("L3", "L4", 2)
    graph.add_edge("L4", "L3", 2)

    graph.add_edge("L4", "L5", 2)
    graph.add_edge("L5", "L4", 2)

    graph.add_edge("L2", "L4", 3)
    graph.add_edge("L4", "L2", 3)

    graph.add_edge("L3", "L5", 3)
    graph.add_edge("L5", "L3", 3)

    graph.add_edge("L5", "L6", 1)
    graph.add_edge("L6", "L5", 1)

    graph.add_edge("L6", "L7", 1)
    graph.add_edge("L7", "L6", 1)

    if connect_right:
        graph.add_edge("L7", "L8", 1)
        graph.add_edge("L8", "L7", 1)

    graph.add_edge("L8", "L9", 2)
    graph.add_edge("L9", "L8", 2)

    graph.add_edge("L9", "L10", 2)
    graph.add_edge("L10", "L9", 2)

    graph.add_edge("L10", "L11", 2)
    graph.add_edge("L11", "L10", 2)

    graph.add_edge("L11", "L12", 2)
    graph.add_edge("L12", "L11", 2)

    graph.add_edge("L8", "L10", 3)
    graph.add_edge("L10", "L8", 3)

    graph.add_edge("L9", "L11", 3)
    graph.add_edge("L11", "L9", 3)

    return V, graph


def bridge_graph_two_pickers_four_batches():
    B = {"B1", "B2", "B3", "B4"}
    V, location_graph = _build_bridge_graph(connect_right=True)

    w1 = 1.0
    w2 = 10.0
    gamma = 1.0
    delta = 5.0

    cap_vehicle = 6.0

    return V, B, w1, w2, gamma, delta, location_graph, cap_vehicle


def bridge_graph_disconnected():
    B = {"B1", "B2", "B3", "B4"}
    V, location_graph = _build_bridge_graph(connect_right=False)

    w1 = 1.0
    w2 = 10.0
    gamma = 1.0
    delta = 5.0

    cap_vehicle = 6.0

    return V, B, w1, w2, gamma, delta, location_graph, cap_vehicle
