def reconstruct_route(output_graph):
    active_edges = []
    for (origin, destination), _ in output_graph.distances.items():
        active_edges.append((origin.location_id, destination.location_id))

    adjacency = {}
    indegree = {vertex: 0 for vertex in output_graph.get_vertices()}
    outdegree = {vertex: 0 for vertex in output_graph.get_vertices()}

    for origin, destination in active_edges:
        if origin in adjacency:
            raise AssertionError(
                f"Branch detected from {origin}: {adjacency[origin]} and {destination}"
            )

        adjacency[origin] = destination
        outdegree[origin] += 1
        indegree[destination] += 1

    depot = output_graph.get_depot()
    final = output_graph.get_final()

    route = [depot]
    visited = {depot}
    current = depot

    while current != final:
        if current not in adjacency:
            raise AssertionError(f"Route is disconnected at {current}")

        next_vertex = adjacency[current]
        if next_vertex in visited:
            raise AssertionError(f"Cycle detected at {next_vertex}")

        route.append(next_vertex)
        visited.add(next_vertex)
        current = next_vertex

    if len(active_edges) != len(route) - 1:
        raise AssertionError("Active edges do not form a single simple path")

    if outdegree.get(depot, 0) != 1:
        raise AssertionError("Depot must have exactly one outgoing arc")

    if indegree.get(final, 0) != 1:
        raise AssertionError("Final node must have exactly one incoming arc")

    for vertex in output_graph.get_vertices():
        if vertex in {depot, final}:
            continue

        if vertex in route:
            if indegree.get(vertex, 0) != 1 or outdegree.get(vertex, 0) != 1:
                raise AssertionError(
                    f"Intermediate vertex {vertex} must have one in and one out"
                )

    return route


def assert_route_covers_orders(testcase, output_graph, orders_by_location):
    route = reconstruct_route(output_graph)

    testcase.assertEqual(route[0], output_graph.get_depot())
    testcase.assertEqual(route[-1], output_graph.get_final())
    testcase.assertEqual(len(route), len(set(route)))

    for location in orders_by_location:
        testcase.assertIn(
            location, route, f"Required location {location} was not visited"
        )

    return route
