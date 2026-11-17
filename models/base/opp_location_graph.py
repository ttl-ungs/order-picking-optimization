class OPPLocation:
    """A warehouse location: its id and its type (picking, depot, final or aisle)."""

    def __init__(self, location_id, type="picking"):
        self.location_id = location_id
        self.type = type

    def __repr__(self):
        return f"OPPLocation({self.location_id})"

    def __eq__(self, other):
        if not isinstance(other, OPPLocation):
            return NotImplemented
        return self.location_id == other.location_id

    def __hash__(self):
        return hash(self.location_id)


class OPPLocationGraph:
    """Directed warehouse graph: locations, arcs with distances, a depot and a final node."""

    def __init__(self, depot_node=None, final_node=None):
        """
        Empty graph.

        Args:
            depot_node: id of the location every route starts from
            final_node: id of the location every route ends at
        """
        self.distances = {}
        # `distances` again, keyed by (from_id, to_id). has_edge and
        # get_distance are the hottest calls of the search loops, and this
        # saves them building and hashing an OPPLocation per call.
        self._distance_by_id = {}
        self.depot_node = OPPLocation(depot_node, "depot") if depot_node else None
        self.final_node = OPPLocation(final_node, "final") if final_node else None

        self._vertices_set = (
            {self.depot_node, self.final_node} if depot_node and final_node else set()
        )
        self._vertices_sorted = (
            sorted([depot_node, final_node]) if depot_node and final_node else []
        )
        # Adjacency of get_neighbors(), built on first use and invalidated by
        # add_edge: finding a vertex's neighbors by scanning every vertex with
        # has_edge is O(V) per call and dominated opp_aco's runtime.
        self._adjacency = None
        # (neighbor, distance) pairs per vertex, in get_neighbors() order;
        # same lazy cache.
        self._weighted_adjacency = None

    def add_vertex(self, vertex, type="picking"):
        """Add a vertex to the graph."""
        if type not in {"picking", "depot", "final"}:
            raise ValueError("Vertex type must be 'picking', 'depot', or 'final'.")

        opp_location = OPPLocation(vertex, type)
        if opp_location not in self._vertices_set:
            self._vertices_set.add(opp_location)
            self._vertices_sorted = sorted(v.location_id for v in self._vertices_set)

    def add_edge(self, from_vertex, to_vertex, distance: float):
        """Add an edge with distance between two vertices."""

        if (
            OPPLocation(from_vertex) not in self._vertices_set
            or OPPLocation(to_vertex) not in self._vertices_set
        ):
            raise ValueError("Both vertices must be in the graph.")

        self.distances[(OPPLocation(from_vertex), OPPLocation(to_vertex))] = distance
        self._distance_by_id[(from_vertex, to_vertex)] = distance
        self._adjacency = None
        self._weighted_adjacency = None

    def get_neighbors(self, vertex):
        """
        Ids of the vertices directly reachable from `vertex`, from an
        adjacency list built once per graph.

        Sorted, like get_vertices(): the searches rely on a deterministic
        exploration order to return the same route when several are equally
        short.
        """
        if self._adjacency is None:
            adjacency = {}
            for from_loc, to_loc in self.distances.keys():
                adjacency.setdefault(from_loc.location_id, []).append(to_loc.location_id)
            for neighbors in adjacency.values():
                neighbors.sort()
            self._adjacency = adjacency
        return self._adjacency.get(vertex, [])

    def get_weighted_neighbors(self, vertex):
        """
        [(neighbor, distance), ...] for `vertex`, in get_neighbors() order.
        Saves the shortest-path loops one get_distance() call per edge.
        """
        if self._weighted_adjacency is None:
            self._weighted_adjacency = {
                u: [(v, self._distance_by_id[(u, v)]) for v in self.get_neighbors(u)]
                for u in self._vertices_sorted
            }
        return self._weighted_adjacency.get(vertex, [])

    def get_distance(self, from_vertex, to_vertex):
        """Get distance between two vertices using location IDs."""
        return self._distance_by_id.get((from_vertex, to_vertex), float("inf"))

    def has_edge(self, from_vertex, to_vertex):
        """Check if an edge exists between two vertices."""
        return (from_vertex, to_vertex) in self._distance_by_id

    def get_depot(self):
        """Get the depot (starting) node."""
        return self.depot_node.location_id

    def get_final(self):
        """Get the final (ending) node."""
        return self.final_node.location_id

    def get_vertices(self):
        """Get all vertex IDs in the graph."""
        return self._vertices_sorted

    def getPaths(self, origin_vertex, destination_vertex):
        """All simple paths from origin to destination."""
        if (
            origin_vertex not in self.get_vertices()
            or destination_vertex not in self.get_vertices()
        ):
            raise ValueError("Both vertices must be in the graph.")
        return self._find_paths(origin_vertex, destination_vertex)

    def _find_paths(self, origin_vertex, destination_vertex, visited=None):
        """All simple paths from origin to destination, by depth-first search."""
        if visited is None:
            visited = set()

        visited.add(origin_vertex)

        if origin_vertex == destination_vertex:
            return [[origin_vertex]]

        paths = []
        for (from_v, to_v), _ in self.distances.items():
            if from_v.location_id == origin_vertex and to_v.location_id not in visited:
                sub_paths = self._find_paths(
                    to_v.location_id, destination_vertex, visited
                )
                for sub_path in sub_paths:
                    paths.append([origin_vertex] + sub_path)

        visited.remove(origin_vertex)
        return paths

    def __eq__(self, value):
        if not isinstance(value, OPPLocationGraph):
            return NotImplemented

        return (
            self.get_depot() == value.get_depot()
            and self.get_final() == value.get_final()
            and self.get_vertices() == value.get_vertices()
            and self.distances == value.distances
        )

    def to_string(self):
        """String representation of the graph."""
        edges_str = ", ".join(
            f"{from_v.location_id} -{dist}-> {to_v.location_id}"
            for (from_v, to_v), dist in self.distances.items()
        )

        paths_str = ""
        start = self.get_depot()
        end = self.get_final()
        if start and end:
            all_paths = self._find_paths(start, end)
            paths_str = ", ".join(" -> ".join(path) for path in all_paths)

        return f"""OPPLocationGraph(
                        Depot: {self.get_depot()}, 
                        Final: {self.get_final()}, 
                        Edges: {{{edges_str}}}, 
                        Paths: {{{paths_str}}}
                )"""
