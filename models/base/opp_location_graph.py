class OPPLocation:
    """
    Simple location class for order picking.
    """

    def __init__(self, location_id, type="picking"):
        self.location_id = location_id
        self.type = type  # or 'depot' or 'final' or 'aisle'

    def __repr__(self):
        return f"OPPLocation({self.location_id})"

    def __eq__(self, other):
        if not isinstance(other, OPPLocation):
            return NotImplemented
        return self.location_id == other.location_id

    def __hash__(self):
        return hash(self.location_id)


class OPPLocationGraph:
    """
    Simple graph class for managing warehouse locations and distances.
    """

    def __init__(self, depot_node=None, final_node=None):
        """
        Initialize empty location graph.

        Args:
            depot_node: Starting location
            final_node: Ending location
        """
        self.distances = {}
        # Mirrors `distances` but keyed by raw (from_id, to_id) tuples instead
        # of OPPLocation pairs, so has_edge/get_distance -- the hottest calls
        # in the search loops -- can look up a distance without allocating a
        # fresh OPPLocation (and hashing it) on every call. `distances` itself
        # is kept as-is: some callers (to_string, _find_paths, __eq__, and
        # tests/infra/cases/route_assertions.py) rely on it being keyed by
        # OPPLocation objects with a `.location_id` attribute.
        self._distance_by_id = {}
        self.depot_node = OPPLocation(depot_node, "depot") if depot_node else None
        self.final_node = OPPLocation(final_node, "final") if final_node else None

        self._vertices_set = (
            {self.depot_node, self.final_node} if depot_node and final_node else set()
        )
        self._vertices_sorted = (
            sorted([depot_node, final_node]) if depot_node and final_node else []
        )
        # Adjacency cache for get_neighbors(), built lazily on first access and
        # invalidated by add_edge. Route-construction hot loops used to do
        # `for n in get_vertices(): if has_edge(current, n)` -- an O(V) scan
        # (re-allocating an OPPLocation + hashing it per candidate) just to
        # find a handful of real neighbors. Profiled at ~82% of opp_aco_2's
        # total runtime on a 100-node stress instance (has_edge: 87M calls).
        # get_neighbors() is O(1) amortized after the first call per graph.
        self._adjacency = None

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
        self._adjacency = None  # invalidate cache

    def get_neighbors(self, vertex):
        """
        Vertex IDs directly reachable from `vertex` (i.e. has_edge(vertex, n)
        is True), without scanning every other vertex. Builds the adjacency
        list once per graph (amortized O(1) per call after that), instead of
        the O(V) `has_edge` scan this replaces in route-construction hot
        loops -- see the comment in __init__ for the profiling that found this.

        Sorted, same as get_vertices(): some callers (e.g. opp_hc_2's BFS
        state-space search) rely on a deterministic exploration order to
        pick a specific route when several equally-short ones exist --
        swapping in insertion order here would silently change which route
        gets returned.
        """
        if self._adjacency is None:
            adjacency = {}
            for from_loc, to_loc in self.distances.keys():
                adjacency.setdefault(from_loc.location_id, []).append(to_loc.location_id)
            for neighbors in adjacency.values():
                neighbors.sort()
            self._adjacency = adjacency
        return self._adjacency.get(vertex, [])

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
        """Public method to get all paths from origin to destination."""
        if (
            origin_vertex not in self.get_vertices()
            or destination_vertex not in self.get_vertices()
        ):
            raise ValueError("Both vertices must be in the graph.")
        return self._find_paths(origin_vertex, destination_vertex)

    def _find_paths(self, origin_vertex, destination_vertex, visited=None):
        """Find all paths from origin to destination using DFS."""
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
