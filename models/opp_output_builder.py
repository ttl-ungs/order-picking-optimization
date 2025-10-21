import pyscipopt
from models.opp_location_graph import OPPLocationGraph


def build_output(
    model: pyscipopt.Model, location_graph: OPPLocationGraph, H: set, z: dict
):
    if z is None or model is None or model.getStatus() != "optimal":
        return None

    output_graph = OPPLocationGraph(
        depot_node=location_graph.get_depot(), final_node=location_graph.get_final()
    )

    for i in location_graph.get_vertices():
        if i not in output_graph.get_vertices():
            output_graph.add_vertex(i, "picking")

    for h in H:
        active_arcs = []
        for i in location_graph.get_vertices():
            for j in location_graph.get_vertices():
                try:
                    val_z = model.getVal(z[i, j, h])
                    if val_z > 0.5 and location_graph.has_edge(i, j):
                        active_arcs.append((i, j))
                        output_graph.add_edge(i, j, location_graph.get_distance(i, j))
                except KeyError:
                    continue

    return output_graph
