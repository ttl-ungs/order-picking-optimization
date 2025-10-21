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
        self.depot_node = OPPLocation(depot_node, "depot") if depot_node else None
        self.final_node = OPPLocation(final_node, "final") if final_node else None

        self.vertices = (
            {self.depot_node, self.final_node} if depot_node and final_node else set()
        )

    def add_vertex(self, vertex, type="picking"):
        """Add a vertex to the graph."""
        if type not in {"picking", "depot", "final"}:
            raise ValueError("Vertex type must be 'picking', 'depot', or 'final'.")

        opp_location = OPPLocation(vertex, type)
        self.vertices.add(opp_location)

    def add_edge(self, from_vertex, to_vertex, distance: float):
        """Add an edge with distance between two vertices."""

        if (
            OPPLocation(from_vertex) not in self.vertices
            or OPPLocation(to_vertex) not in self.vertices
        ):
            raise ValueError("Both vertices must be in the graph.")

        self.distances[(OPPLocation(from_vertex), OPPLocation(to_vertex))] = distance

    def get_distance(self, from_vertex, to_vertex):
        """Get distance between two vertices using location IDs."""
        from_loc = OPPLocation(from_vertex)
        to_loc = OPPLocation(to_vertex)
        return self.distances.get((from_loc, to_loc), float("inf"))

    def has_edge(self, from_vertex, to_vertex):
        """Check if an edge exists between two vertices."""
        from_loc = OPPLocation(from_vertex)
        to_loc = OPPLocation(to_vertex)
        return (from_loc, to_loc) in self.distances

    def get_depot(self):
        """Get the depot (starting) node."""
        return self.depot_node.location_id

    def get_final(self):
        """Get the final (ending) node."""
        return self.final_node.location_id

    def get_vertices(self):
        """Get all vertex IDs in the graph."""
        return {v.location_id for v in self.vertices}

    def __eq__(self, value):
        if not isinstance(value, OPPLocationGraph):
            return NotImplemented

        return (
            self.get_depot() == value.get_depot()
            and self.get_final() == value.get_final()
            and self.get_vertices() == value.get_vertices()
            and self.distances == value.distances
        )
