def assert_correct_path(testcase, output_graph, expected_path):
    paths = output_graph.getPaths(output_graph.get_depot(), output_graph.get_final())
    testcase.assertEqual(
        len(paths), 1, f"Expected exactly one path, but found {len(paths)}: {paths}"
    )
    testcase.assertEqual(
        paths[0], expected_path, f"Expected path {expected_path}, but found {paths[0]}"
    )


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


def _get_var_name(var):
    if hasattr(var, "name"):
        return var.name
    return var.getName()


def get_active_arcs_by_batch(scip_model, batches, threshold=0.5):
    batch_set = set(batches)
    arcs_by_batch = {b: [] for b in batches}

    for var in scip_model.getVars():
        name = _get_var_name(var)
        if not name.startswith("z_"):
            continue

        parts = name.split("_")
        if len(parts) != 4:
            continue

        _, origin, destination, batch = parts
        if batch not in batch_set:
            continue

        if scip_model.getVal(var) > threshold:
            arcs_by_batch[batch].append((origin, destination))

    return arcs_by_batch


def reconstruct_route_from_arcs(arcs, depot, final):
    adjacency = {}
    indegree = {}
    outdegree = {}

    for origin, destination in arcs:
        if origin in adjacency:
            raise AssertionError(
                f"Branch detected from {origin}: {adjacency[origin]} and {destination}"
            )

        adjacency[origin] = destination
        outdegree[origin] = outdegree.get(origin, 0) + 1
        indegree[destination] = indegree.get(destination, 0) + 1

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

    if outdegree.get(depot, 0) != 1:
        raise AssertionError("Depot must have exactly one outgoing arc")

    if indegree.get(final, 0) != 1:
        raise AssertionError("Final node must have exactly one incoming arc")

    for vertex in route[1:-1]:
        if indegree.get(vertex, 0) != 1 or outdegree.get(vertex, 0) != 1:
            raise AssertionError(
                f"Intermediate vertex {vertex} must have one in and one out"
            )

    return route


def assert_batch_routes_cover_locations(
    testcase, scip_model, batches, depot, final, required_by_batch
):
    arcs_by_batch = get_active_arcs_by_batch(scip_model, batches)
    routes_by_batch = {}

    for batch in batches:
        arcs = arcs_by_batch.get(batch, [])
        testcase.assertTrue(arcs, f"Batch {batch} has no active arcs")
        route = reconstruct_route_from_arcs(arcs, depot, final)
        routes_by_batch[batch] = route

        for location in required_by_batch.get(batch, set()):
            testcase.assertIn(
                location,
                route,
                f"Batch {batch} did not visit required location {location}",
            )

    return routes_by_batch
