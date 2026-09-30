"""
Sets:
    N = Órdenes de clientes
    V = Locaciones a visitar
    P = Pickers
    B = Lotes de pedidos factibles

Parameters:
    W_c = Peso del tiempo de cumplimiento
    W_pen = Peso asociado a la suma pesada de las demoras y los adelantos
    W_e = Peso asociado al adelanto total
    W_t = Peso asociado a la demora total
    D_ij = Distancia entre localizaciones de picking i ∈ V y j ∈ V
    C_n = Capacidad requerida para una órden n ∈ N
    C_v = Capacidad del vehículo de picking
    A_ni = 1 si la órder n ∈ N debe visitar la locaclización de picking
            i ∈ V, 0 si no
    T_travel = Tiempo requerido para viajar en una unidad de espacio
    T_setup = Tiempo requerido para planificar cada lote
    T_pick = Tiempo requerido para buscar y recolectar ítems
    T_due_n = Fecha límite para la órden n ∈ N
    M = Entero lo suficientemente grande
    dis_i = Distancia viajada para completar el lote i ∈ B
    capbatch_i = Capacidad requerida para un lote i ∈ B
    B_nb = 1 si el lote b ∈ B contiene a la orden n ∈ N
    X_pb = 1 si el lote b ∈ B es asignado al picker p ∈ P (dato de entrada)

Variables:
    ta_n = tardanza de la orden n ∈ N
    ea_n = adelanto de la orden n ∈ N
    d_b = tiempo de ejecución del lote b ∈ B
    u_pb = tiempo de procesamiento del lote b ∈ B del picker p ∈ P
    c_pb = tiempo de completitud para el lote b ∈ B del picker p ∈ P
    z_ijb = 1 si el arco que conecta las locaciones i ∈ V y j ∈ V están
            incluidos en el lote b ∈ B, 0 si no
    q_ijb = Flujo de carga: locaciones requeridas del lote b ∈ B que
            todavía faltan visitar al recorrer el arco (i, j)
"""

import time

import pyscipopt
from pyscipopt import quicksum
from models.base.model import Model

from dtos.opp.solve_model_dto import SolveModelDTO
from dtos.opp.model_dto import ModelDTO
from models.utils.output_builder import build_output

"""
Version of OPP model without concept of "missions" (H) and "periods" (K)
"""


class OPPModelV2(Model):
    def __init__(self, dto: ModelDTO):
        super().__init__()

        self.N = sorted(dto.N)
        self.location_graph = dto.location_graph
        self.P = sorted(dto.P)
        self.B = sorted(dto.B)
        self.start_time = dto.start_time

    def solve(self, params: SolveModelDTO):
        W_c = params.W_c
        W_pen = params.W_pen
        W_e = params.W_e
        W_t = params.W_t
        C_n = params.C_n
        C_v = params.C_v
        A = params.A
        T_travel = params.T_travel
        T_setup = params.T_setup
        T_pick = params.T_pick
        T_due_n = params.T_due_n
        M = params.M
        X = params.X
        B_nb = params.B_nb
        start_time = self.start_time

        model = pyscipopt.Model("OPP Model Version 2")
        self.model = model

        # ta_n = delay of order n ∈ N
        ta = {n: model.addVar(name=f"ta_{n}", lb=0) for n in self.N}

        # ea_n = advance of order n ∈ N
        ea = {n: model.addVar(name=f"ea_{n}", lb=0) for n in self.N}

        # d_b = execution time of mission b ∈ B
        d = {b: model.addVar(name=f"d_{b}", lb=0) for b in self.B}

        # u_pb = processing time of the batch b ∈ B of picker p ∈ P
        u = {
            (p, b): model.addVar(name=f"u_{p}_{b}", lb=0)
            for p in self.P
            for b in self.B
        }

        # c_pb = completion time of the batch b ∈ B of picker p ∈ P
        c = {
            (p, b): model.addVar(name=f"c_{p}_{b}", lb=0)
            for p in self.P
            for b in self.B
        }

        # z_ijb = 1 if the arc connecting locations i ∈ V and j ∈ V are
        #         included in mission b ∈ B, 0 otherwise
        z = {
            (i, j, b): model.addVar(name=f"z_{i}_{j}_{b}", vtype="B")
            for i in self.location_graph.get_vertices()
            for j in self.location_graph.get_vertices()
            for b in self.B
        }

        # q_ijb = Number of units passing through the arc connecting locations
        #         i ∈ V and j ∈ V in mission b ∈ B
        q = {
            (i, j, b): model.addVar(name=f"q_{i}_{j}_{b}", lb=0)
            for i in self.location_graph.get_vertices()
            for j in self.location_graph.get_vertices()
            for b in self.B
        }

        # Objective function
        model.setObjective(
            self.objective_function(W_c, c, W_pen, ea, W_e, W_t, ta), sense="minimize"
        )

        # Constraints
        depot_node = self.location_graph.get_depot()
        final_node = self.location_graph.get_final()

        # (6)
        for b in self.B:
            model.addCons(
                self.constraint_start_from_depot(z, b),
                name=f"start_from_depot_b{b}",
            )

        # (7)
        for b in self.B:
            model.addCons(
                self.constraint_finish_at_end(z, b),
                name=f"finish_at_end_b{b}",
            )

        # (8)
        for b in self.B:
            model.addCons(
                self.constraint_cant_go_back_to_depot(z, b),
                name=f"cant_go_back_to_depot_b{b}",
            )

        # (9)
        for b in self.B:
            model.addCons(
                self.constraint_cant_move_from_end_node(z, b),
                name=f"cant_move_from_end_node_b{b}",
            )

        # (10)
        for b in self.B:
            for j in self.location_graph.get_vertices():
                if j != depot_node and j != final_node:
                    model.addCons(
                        self.constraint_force_visit_inflow(b, j, z, A, B_nb),
                        name=f"force_visit_inflow_b{b}_j{j}",
                    )

        # (11)
        for b in self.B:
            for j in self.location_graph.get_vertices():
                if j != depot_node and j != final_node:
                    model.addCons(
                        self.constraint_force_visit_outflow(b, j, z, A, B_nb),
                        name=f"force_visit_outflow_b{b}_j{j}",
                    )

        # (12)
        for b in self.B:
            for i in self.location_graph.get_vertices():
                for j in self.location_graph.get_vertices():
                    if i != final_node and j != depot_node:
                        model.addCons(
                            self.constraint_articles_capacity(
                                i, j, b, q, C_v, z
                            ),
                            name=f"articles_capacity_b{b}_i{i}_j{j}",
                        )

        # (13)
        for b in self.B:
            for i in self.location_graph.get_vertices():
                if i != depot_node and i != final_node:
                    model.addCons(
                        self.constraint_route_flow_conservation(z, b, i),
                        name=f"route_flow_conservation_b{b}_i{i}",
                    )

        # (14)
        for b in self.B:
            for i in self.location_graph.get_vertices():
                # depot node does not have an input arc
                if i != depot_node:
                    model.addCons(
                        self.constraint_one_input_arc_per_node(b, i, z),
                        name=f"one_input_arc_per_node_b{b}_i{i}",
                    )

        # (15)
        for b in self.B:
            for i in self.location_graph.get_vertices():
                # final node does not have an output arc
                if i != final_node:
                    model.addCons(
                        self.constraint_one_output_arc_per_node(b, i, z),
                        name=f"one_output_arc_per_node_b{b}_i{i}",
                    )

        # (16)
        # for b in self.B:
        #     for n in self.N:
        #         for i in self.location_graph.get_vertices():
        #             if i != depot_node:
        #                 model.addCons(
        #                     self.constraint_avoid_subtours_cycles(f, i, b, a, y, n),
        #                     name=f"avoid_subtours_cycles_b{b}_n{n}_i{i}",
        #                 )

        # (16) - Gavish-Graves subtour elimination
        for b in self.B:
            model.addCons(
                self.constraint_load_flow_source(b, q, A, B_nb),
                name=f"load_flow_source_b{b}",
            )
            for i in self.location_graph.get_vertices():
                if i != depot_node and i != final_node:
                    model.addCons(
                        self.constraint_load_flow_conservation(i, b, q, A, B_nb),
                        name=f"load_flow_conservation_b{b}_i{i}",
                    )

        # (17)
        for b in self.B:
            for i in self.location_graph.get_vertices():
                if i != depot_node:
                    model.addCons(
                        self.constraint_no_loops(b, i, z),
                        name=f"no_loops_b{b}_i{i}",
                    )

        # (18)
        for b in self.B:
            model.addCons(
                self.constraint_valid_execution_time(
                    b,
                    d,
                    T_travel,
                    T_setup,
                    T_pick,
                    C_n,
                    B_nb,
                    z,
                ),
                name=f"valid_execution_time_b{b}",
            )

        # (19)
        for p in self.P:
            for b in self.B:
                model.addCons(
                    self.constraint_batch_execution_time(p, b, d, M, X, u),
                    name=f"batch_execution_time_p{p}_b{b}",
                )

        # (20)
        for p in self.P:
            for b in self.B:
                model.addCons(
                    self.constraint_processing_time(p, u, c, b),
                    name=f"processing_time_p{p}_b{b}",
                )

        # (21)
        # for p in self.P:
        #     for b in self.B:
        #         if b >= 2:
        #             model.addCons(
        #                 self.constraint_completition_batch_time(u, v, p, b),
        #                 name=f"completition_batch_time_p{p}_b{b}",
        #             )

        # (22)
        for p in self.P:
            for b in self.B:
                for n in self.N:
                    model.addCons(
                        self.constraint_tardiness_definition(
                            c, p, T_due_n, n, M, b, X, B_nb, ta
                        ),
                        name=f"tardiness_definition_p{p}_n{n}_b{b}",
                    )

        # (23)
        for p in self.P:
            for b in self.B:
                for n in self.N:
                    model.addCons(
                        self.constraint_earliness_definition(
                            c, p, T_due_n, n, M, b, X, B_nb, ea
                        ),
                        name=f"earliness_definition_p{p}_n{n}_b{b}",
                    )

        # (24), (25), (26), (27), (28), (29), (30), (31) and (32) are implicit in the definition of the variables

        # Allow only paths between neighbors
        for b in self.B:
            for i in self.location_graph.get_vertices():
                for j in self.location_graph.get_vertices():
                    if not (self.location_graph.has_edge(i, j)):
                        model.addCons(
                            self.constraint_only_valid_edges(i, j, b, z),
                            name=f"only_valid_edges_i{i}_j{j}_b{b}",
                        )

        # Batch loading capacity
        for b in self.B:
            model.addCons(
                self.constraint_batch_capacity(C_n, B_nb, b, self.N, C_v),
                name=f"batch_capacity_b{b}",
            )

        t0 = start_time if start_time is not None else time.time()
        model.optimize()
        elapsed = time.time() - t0

        print(
            f"\nExecution time: {elapsed:.4f}s (solver: {model.getSolvingTime():.4f}s)"
        )

        # Print solution results, for testing purposes
        super().notify(
            model=model,
            N=self.N,
            V=self.location_graph.get_vertices(),
            P=self.P,
            B=self.B,
            ta=ta,
            ea=ea,
            d=d,
            c=c,
            z=z,
            depot_vertex=depot_node,
            final_vertex=final_node,
        )

        output = build_output(model, self.location_graph, self.B, z)
        return model.getStatus(), output

    def objective_function(self, W_c, c, W_pen, ea, W_e, W_t, ta):
        recollection_time = sum(c[p, b] for p in self.P for b in self.B)
        advance_time = sum(ea[n] for n in self.N)
        delay_time = sum(ta[n] for n in self.N)
        penalty = W_e * advance_time + W_t * delay_time

        return W_c * recollection_time + W_pen * penalty

    def constraint_start_from_depot(self, z, b):
        """
        (6): Each mission must start from the depot.
        """
        # The sum of the arcs z(depot, j, b) for all destinations 'j' must be 1.
        return (
            quicksum(
                z[self.location_graph.get_depot(), j, b]
                for j in self.location_graph.get_vertices()
                if j != self.location_graph.get_depot()
            )
            == 1
        )

    def constraint_finish_at_end(self, z, b):
        """
        (7): Each mission must finish at the final node.
        """
        # The sum of the arcs z(i, final_node, b) for all origins 'i' must be 1.
        return (
            quicksum(
                z[i, self.location_graph.get_final(), b]
                for i in self.location_graph.get_vertices()
                if i != self.location_graph.get_final()
            )
            == 1
        )

    def constraint_cant_go_back_to_depot(self, z, b):
        """
        (8): A picker cannot return to the depot after leaving it.
        """
        # The sum of the arcs z(i, depot, b) for all origins 'i' must be 0.
        return (
            quicksum(
                z[i, self.location_graph.get_depot(), b]
                for i in self.location_graph.get_vertices()
                if i != self.location_graph.get_depot()
            )
            == 0
        )

    def constraint_cant_move_from_end_node(self, z, b):
        """
        (9): A picker cannot leave the final node.
        """
        # The sum of the arcs z(final_node, j, b) for all destinations 'j' must be 0.
        return (
            quicksum(
                z[self.location_graph.get_final(), j, b]
                for j in self.location_graph.get_vertices()
                if j != self.location_graph.get_final()
            )
            == 0
        )

    def constraint_force_visit_inflow(self, b, j, z, A, B_nb):
        """
        (10): If any order from batch 'b' must visit location 'j',
        then the sum of arcs entering 'j' must be at least 1.
        """
        inflow = quicksum(
            z[i, j, b] for i in self.location_graph.get_vertices() if i != j
        )

        requirement = min(1, sum(A[n, j] * B_nb[n, b] for n in self.N))

        return inflow >= requirement

    def constraint_force_visit_outflow(self, b, j, z, A, B_nb):
        """
        (11): If any order from batch 'b' must visit location 'j',
        then the sum of arcs leaving 'j' must be at least 1.
        """
        outflow = quicksum(
            z[j, i, b] for i in self.location_graph.get_vertices() if i != j
        )

        requirement = min(1, sum(A[n, j] * B_nb[n, b] for n in self.N))

        return outflow >= requirement

    def constraint_articles_capacity(self, i, j, b, q, C_v, z):
        """
        (12): Articles capacity constraint.
        Ensures that the total capacity of articles of a batch b does
        not exceed the vehicle's capacity.
        """
        return q[i, j, b] - float(C_v) * z[i, j, b] <= 0

    def constraint_route_flow_conservation(self, z, b, i):
        """
        (13): Flow conservation constraint.
        Ensures that the flow of articles is conserved at each location.
        """
        return quicksum(
            z[g, i, b] for g in self.location_graph.get_vertices() if g != i
        ) == quicksum(z[i, j, b] for j in self.location_graph.get_vertices() if j != i)

    def constraint_one_input_arc_per_node(self, b, i, z):
        """
        (14): One input arc per node constraint.
        Ensures that each node i has maximum one incoming arc in the route.
        """
        return (
            quicksum(z[j, i, b] for j in self.location_graph.get_vertices() if j != i)
            <= 1
        )

    def constraint_one_output_arc_per_node(self, b, i, z):
        """
        (15): One output arc per node constraint.
        Ensures that each node i has maximum one outgoing arc in the route.
        """
        return (
            quicksum(z[i, j, b] for j in self.location_graph.get_vertices() if j != i)
            <= 1
        )

    # def constraint_avoid_subtours_cycles(self, f, i, b, a, y, n):
    #     """
    #     (16): Subtour elimination constraint.
    #     Ensures that the route does not contain subtours or cycles.
    #     """
    #     flow_in = quicksum(
    #         f[g, i, b]
    #         for g in self.location_graph.get_vertices()
    #         if g != self.location_graph.get_final()
    #     )
    #     required_flow = a[n, i] * y[n, b]
    #     return flow_in >= required_flow

    def constraint_load_flow_source(self, b, q, A, B_nb):
        """
        (16) Depot sends out exactly required_nodes units.
        """
        # How many required_nodes batch b must visit
        required_nodes = sum(
            min(1, sum(A[n, i] * B_nb[n, b] for n in self.N))
            for i in self.location_graph.get_vertices()
            if i != self.location_graph.get_depot()
            and i != self.location_graph.get_final()
        )
        # How much flow goes from depot_node to any node of batch b
        outflow = quicksum(
            q[self.location_graph.get_depot(), j, b]
            for j in self.location_graph.get_vertices()
            if j != self.location_graph.get_depot()
        )

        # outflow must be exactly required_flow
        return outflow == required_nodes

    def constraint_load_flow_conservation(self, i, b, q, A, B_nb):
        """
        (16) Gavish-Graves balance:
        inflow - outflow = demand at each intermediate node.
        Required nodes consume 1 unit, non-required nodes conserve flow.
        """
        # Inflow to node i (i != final_node)
        inflow = quicksum(
            q[g, i, b]
            for g in self.location_graph.get_vertices()
            if g != self.location_graph.get_final()
        )

        # Outflow of node i (i != depot_node)
        outflow = quicksum(
            q[i, j, b]
            for j in self.location_graph.get_vertices()
            if j != self.location_graph.get_depot()
        )

        # 1 if node i must be visited in batch b, else 0
        demand = min(1, sum(A[n, i] * B_nb[n, b] for n in self.N))

        # If node i must be visited consumes 1 flow unit. Else, consumes 0 flow units.
        return inflow - outflow == demand

    def constraint_no_loops(self, b, i, z):
        """
        (17): No loops constraint.
        Ensures that the route does not contain loops.
        """
        return z[i, i, b] == 0 if i != self.location_graph.get_depot() else None

    def constraint_valid_execution_time(
        self, b, d, T_travel, T_setup, T_pick, C_n, B_nb, z
    ):
        """
        (18): Valid execution time constraint.
        Ensures that the execution time of a mission is correctly calculated
        based on travel time, setup time, and picking time.
        """
        return (
            T_setup
            + T_pick * quicksum(C_n[n] * B_nb[n, b] for n in self.N)
            + T_travel
            * (
                quicksum(
                    self.location_graph.get_distance(i, j) * z[i, j, b]
                    for i in self.location_graph.get_vertices()
                    for j in self.location_graph.get_vertices()
                    if i != self.location_graph.get_final()
                    and j != self.location_graph.get_depot()
                    and self.location_graph.has_edge(i, j)
                )
            )
            <= d[b]
        )

    def constraint_batch_execution_time(self, p, b, d, M, X, u):
        """
        (19): Batch execution time constraint.
        Ensures that the processing time of a batch assigned to a picker is less or
        equal to the execution time of the batch
        assigned to that position.
        """
        return d[b] - M * (1 - X[p, b]) <= u[p, b]

    def constraint_processing_time(self, p, u, c, b):
        """
        (20): Completion time constraint.
        Ensures that the processing time is less or equal to the completion time
        for each batch of a picker.
        """
        return u[p, b] <= c[p, b]

    # def constraint_completition_batch_time(self, u, v, p, b):
    #     """
    #     (21): Completion time of batch constraint.
    #     Ensures that the completion time of a batch assigned to a picker is
    #     correctly calculated based on the processing time of that batch.
    #     """
    #     return u[p, b] + v[p, b - 1] <= v[p, b]

    def constraint_tardiness_definition(self, c, p, T_due_n, n, M, b, X, B_nb, ta):
        """
        (22): Tardiness definition constraint.
        Ensures that the tardiness of an order is correctly calculated
        based on the due date and the completion time of the batch
        to which the order is assigned.
        """
        return c[p, b] - T_due_n[n] - M * (2 - X[p, b] - B_nb[n, b]) <= ta[n]

    def constraint_earliness_definition(self, c, p, T_due_n, n, M, b, X, B_nb, ea):
        """
        (23): Earliness definition constraint.
        Ensures that the earliness of an order is correctly calculated
        based on the due date and the completion time of the batch
        to which the order is assigned.
        """
        return T_due_n[n] - c[p, b] - M * (2 - X[p, b] - B_nb[n, b]) <= ea[n]

    def constraint_batch_capacity(self, C_n, B_nb, b, N, C_v):
        """
        (24): Batch loading capacity constraint.
        Ensures that the total capacity required by orders assigned to a batch
        does not exceed the vehicle's capacity.
        """
        return quicksum(C_n[n] * B_nb[n, b] for n in N) <= C_v

    def constraint_only_valid_edges(self, i, j, b, z):
        """
        (25): Only valid edges constraint.
        Allows only paths between neighbors.
        Ensures that arcs between non-adjacent locations cannot be used.
        """
        return z[i, j, b] == 0
