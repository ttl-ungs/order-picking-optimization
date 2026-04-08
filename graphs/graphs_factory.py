from models.base.opp_location_graph import OPPLocationGraph


class GraphsFactory:
    def get_graph(self, rows, cols, v_weight=4, h_weight=5):
        """
        Build a rows × cols grid graph.

        Vertices are numbered column by column:
            V1  V(rows+1)  V(2*rows+1) ...
            V2  V(rows+2)  ...
            ...
            V(rows) V(2*rows) ...

        Returns:
            OPPLocationGraph with depot=V1 and final=V(rows*cols)
        """
        depot = "V1"
        final = f"V{rows * cols}"

        graph = OPPLocationGraph(depot, final)

        def vid(r, c):
            return f"V{(c - 1) * rows + r}"

        for col in range(1, cols + 1):
            for row in range(1, rows + 1):
                v = vid(row, col)
                if v == depot:
                    graph.add_vertex(v, "depot")
                elif v == final:
                    graph.add_vertex(v, "final")
                else:
                    graph.add_vertex(v, "picking")

        for col in range(1, cols + 1):
            for row in range(1, rows):
                a, b = vid(row, col), vid(row + 1, col)
                graph.add_edge(a, b, v_weight)
                graph.add_edge(b, a, v_weight)

        for row in range(1, rows + 1):
            for col in range(1, cols):
                a, b = vid(row, col), vid(row, col + 1)
                graph.add_edge(a, b, h_weight)
                graph.add_edge(b, a, h_weight)

        return graph, graph.get_vertices()