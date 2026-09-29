"""
Sets:
    N = Órdenes de clientes
    V = Locaciones a visitar
    H = Misiones que se pueden completar
    K = Períodos por picker en las que recolectan un pedido
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
    X_pkh = 1 si la mision h ∈ H es asignada en la posicion k ∈ K
            del picker p ∈ P, 0 si no
    B_nh = 1 si la orden n ∈ N es asignada a la mision h ∈ H, 0 si no

Variables:
    ta_n = tardanza de la orden n ∈ N
    ea_n = adelanto de la orden n ∈ N
    d_h = tiempo de ejecución de la misión h ∈ H
    u_pk = tiempo de procesamiento del lote asignado a la posición k ∈ K
            del picker p ∈ P
    c_pk = tiempo de completitud para el lote asignado a la posición k ∈ K
            del picker p ∈ P
    z_ijh = 1 si el arco que conecta las locaciones i ∈ V y j ∈ V están
            incluidos en la misión h ∈ H, 0 si no
    q_ijh = Flujo de carga: locaciones requeridas de la misión h ∈ H que
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
Based on OPP article: A Model for the Joint Optimisation of Order Batching, 
Batch Assignment Sequencing and Picking Routing 
"""
class OPPModel(Model):
    def __init__(self, dto: ModelDTO):
        super().__init__()

        self.N = sorted(dto.N)
        self.location_graph = dto.location_graph
        self.H = sorted(dto.H)
        self.K = sorted(dto.K)
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
        X = params.x
        B_nb = params.B_nb
        start_time = self.start_time

        model = pyscipopt.Model("OPP Model")
        self.model = model

        # ta_n = delay of order n ∈ N
        ta = {n: model.addVar(name=f"ta_{n}", lb=0) for n in self.N}

        # ea_n = advance of order n ∈ N
        ea = {n: model.addVar(name=f"ea_{n}", lb=0) for n in self.N}

        # d_h = execution time of mission h ∈ H
        d = {h: model.addVar(name=f"d_{h}", lb=0) for h in self.H}

        # u_pk = processing time of the batch assigned to position k ∈ K
        #        of picker p ∈ P
        u = {
            (p, k): model.addVar(name=f"u_{p}_{k}", lb=0)
            for p in self.P
            for k in self.K
        }

        # c_pk = completion time for the batch assigned to position k ∈ K
        #        of picker p ∈ P
        c = {
            (p, k): model.addVar(name=f"c_{p}_{k}", lb=0)
            for p in self.P
            for k in self.K
        }

        # z_ijh = 1 if the arc connecting locations i ∈ V and j ∈ V are
        #         included in mission h ∈ H, 0 otherwise
        z = {
            (i, j, h): model.addVar(name=f"z_{i}_{j}_{h}", vtype="B")
            for i in self.location_graph.get_vertices()
            for j in self.location_graph.get_vertices()
            for h in self.H
        }

        # q_ijh = Number of units passing through the arc connecting locations
        #         i ∈ V and j ∈ V in mission h ∈ H
        q = {
            (i, j, h): model.addVar(name=f"q_{i}_{j}_{h}", lb=0)
            for i in self.location_graph.get_vertices()
            for j in self.location_graph.get_vertices()
            for h in self.H
        }

        # Objective function
        model.setObjective(
            self.objective_function(W_c, c, W_pen, ea, W_e, W_t, ta), sense="minimize"
        )

        # Constraints
        depot_node = self.location_graph.get_depot()
        final_node = self.location_graph.get_final()

        # (6)
        for h in self.H:
            model.addCons(
                self.constraint_start_from_depot(z, h),
                name=f"start_from_depot_h{h}",
            )

        # (7)
        for h in self.H:
            model.addCons(
                self.constraint_finish_at_end(z, h),
                name=f"finish_at_end_h{h}",
            )

        # (8)
        for h in self.H:
            model.addCons(
                self.constraint_cant_go_back_to_depot(z, h),
                name=f"cant_go_back_to_depot_h{h}",
            )

        # (9)
        for h in self.H:
            model.addCons(
                self.constraint_cant_move_from_end_node(z, h),
                name=f"cant_move_from_end_node_h{h}",
            )

        # (10)
        for h in self.H:
            for j in self.location_graph.get_vertices():
                if j != depot_node and j != final_node:
                    model.addCons(
                        self.constraint_force_visit_inflow(h, j, z, A, B_nb),
                        name=f"force_visit_inflow_h{h}_j{j}",
                    )

        # (11)
        for h in self.H:
            for j in self.location_graph.get_vertices():
                if j != depot_node and j != final_node:
                    model.addCons(
                        self.constraint_force_visit_outflow(h, j, z, A, B_nb),
                        name=f"force_visit_outflow_h{h}_j{j}",
                    )

        # (12)
        for h in self.H:
            for i in self.location_graph.get_vertices():
                for j in self.location_graph.get_vertices():
                    if i != final_node and j != depot_node:
                        model.addCons(
                            self.constraint_articles_capacity(
                                i, j, h, q, C_v, z
                            ),
                            name=f"articles_capacity_h{h}_i{i}_j{j}",
                        )

        # (13)
        for h in self.H:
            for i in self.location_graph.get_vertices():
                if i != depot_node and i != final_node:
                    model.addCons(
                        self.constraint_route_flow_conservation(z, h, i),
                        name=f"route_flow_conservation_h{h}_i{i}",
                    )

        # (14)
        for h in self.H:
            for i in self.location_graph.get_vertices():
                # depot node does not have an input arc
                if i != depot_node:
                    model.addCons(
                        self.constraint_one_input_arc_per_node(h, i, z),
                        name=f"one_input_arc_per_node_h{h}_i{i}",
                    )

        # (15)
        for h in self.H:
            for i in self.location_graph.get_vertices():
                # final node does not have an output arc
                if i != final_node:
                    model.addCons(
                        self.constraint_one_output_arc_per_node(h, i, z),
                        name=f"one_output_arc_per_node_h{h}_i{i}",
                    )

        # (16)
        for h in self.H:
            for n in self.N:
                for i in self.location_graph.get_vertices():
                    if i != depot_node:
                        model.addCons(
                            self.constraint_avoid_subtours_cycles(q, i, h, A, B_nb, n),
                            name=f"avoid_subtours_cycles_h{h}_n{n}_i{i}",
                        )

        # (17)
        for h in self.H:
            for i in self.location_graph.get_vertices():
                if i != depot_node:
                    model.addCons(
                        self.constraint_no_loops(h, i, z),
                        name=f"no_loops_h{h}_i{i}",
                    )

        # (18)
        for h in self.H:
            model.addCons(
                self.constraint_valid_execution_time(
                    h,
                    d,
                    T_travel,
                    T_setup,
                    T_pick,
                    C_n,
                    B_nb,
                    z,
                ),
                name=f"valid_execution_time_h{h}",
            )

        # (19)
        for p in self.P:
            for k in self.K:
                for h in self.H:
                    model.addCons(
                        self.constraint_batch_execution_time(p, k, h, d, M, X, u),
                        name=f"batch_execution_time_p{p}_k{k}_h{h}",
                    )

        # (20)
        for p in self.P:
            model.addCons(
                self.constraint_processing_time(p, u, c),
                name=f"processing_time_p{p}_k1",
            )

        # (21)
        for p in self.P:
            for k in self.K:
                if k >= 2:
                    model.addCons(
                        self.constraint_completition_batch_time(u, c, p, k),
                        name=f"completition_batch_time_p{p}_k{k}",
                    )

        # (22)
        for p in self.P:
            for k in self.K:
                for h in self.H:
                    for n in self.N:
                        model.addCons(
                            self.constraint_tardiness_definition(
                                c, p, k, T_due_n, n, M, h, X, B_nb, ta
                            ),
                            name=f"tardiness_definition_p{p}_k{k}_n{n}_h{h}",
                        )

        # (23)
        for p in self.P:
            for k in self.K:
                for h in self.H:
                    for n in self.N:
                        model.addCons(
                            self.constraint_earliness_definition(
                                c, p, k, T_due_n, n, M, h, X, B_nb, ea
                            ),
                            name=f"earliness_definition_p{p}_k{k}_n{n}_h{h}",
                        )

        # (24), (25), (26), (27), (28), (29), (30), (31) and (32) are implicit in the definition of the variables

        # Extra: Allow only paths between neighbors
        for h in self.H:
            for i in self.location_graph.get_vertices():
                for j in self.location_graph.get_vertices():
                    if not (self.location_graph.has_edge(i, j)):
                        model.addCons(
                            z[i, j, h] == 0, name=f"only_valid_edges_i{i}_j{j}_h{h}"
                        )

        t0 = start_time if start_time is not None else time.time()
        model.optimize()
        elapsed = time.time() - t0

        print(f"\nExecution time: {elapsed:.4f}s (solver: {model.getSolvingTime():.4f}s)")

        # Print solution results, for testing purposes
        super().notify(
            model=model,
            N=self.N,
            V=self.location_graph.get_vertices(),
            H=self.H,
            P=self.P,
            K=self.K,
            ta=ta,
            ea=ea,
            d=d,
            c=c,
            z=z,
            depot_vertex=depot_node,
            final_vertex=final_node,
        )

        output = build_output(model, self.location_graph, self.H, z)
        return model.getStatus(), output

    def objective_function(self, W_c, c, W_pen, ea, W_e, W_t, ta):
        recollection_time = sum(c[p, k] for p in self.P for k in self.K)
        advance_time = sum(ea[n] for n in self.N)
        delay_time = sum(ta[n] for n in self.N)
        penalty = W_e * advance_time + W_t * delay_time

        return W_c * recollection_time + W_pen * penalty

    def constraint_start_from_depot(self, z, h):
        """
        (6): Each mission must start from the depot.
        """
        # The sum of the arcs z(depot, j, h) for all destinations 'j' must be 1.
        return (
            quicksum(
                z[self.location_graph.get_depot(), j, h]
                for j in self.location_graph.get_vertices()
                if j != self.location_graph.get_depot()
            )
            == 1
        )

    def constraint_finish_at_end(self, z, h):
        """
        (7): Each mission must finish at the final node.
        """
        # The sum of the arcs z(i, final_node, h) for all origins 'i' must be 1.
        return (
            quicksum(
                z[i, self.location_graph.get_final(), h]
                for i in self.location_graph.get_vertices()
                if i != self.location_graph.get_final()
            )
            == 1
        )

    def constraint_cant_go_back_to_depot(self, z, h):
        """
        (8): A picker cannot return to the depot after leaving it.
        """
        # The sum of the arcs z(i, depot, h) for all origins 'i' must be 0.
        return (
            quicksum(
                z[i, self.location_graph.get_depot(), h]
                for i in self.location_graph.get_vertices()
                if i != self.location_graph.get_depot()
            )
            == 0
        )

    def constraint_cant_move_from_end_node(self, z, h):
        """
        (9): A picker cannot leave the final node.
        """
        # The sum of the arcs z(final_node, j, h) for all destinations 'j' must be 0.
        return (
            quicksum(
                z[self.location_graph.get_final(), j, h]
                for j in self.location_graph.get_vertices()
                if j != self.location_graph.get_final()
            )
            == 0
        )

    def constraint_force_visit_inflow(self, h, j, z, A, B_nb):
        """
        (10): If mission 'h' must visit location 'j',
        then the sum of arcs entering 'j' must be at least 1.
        """
        inflow = quicksum(
            z[i, j, h] for i in self.location_graph.get_vertices() if i != j
        )

        requirement = quicksum(A[n, j] * B_nb[n, h] for n in self.N)

        return inflow >= requirement

    def constraint_force_visit_outflow(self, h, j, z, A, B_nb):
        """
        (11): If mission 'h' must visit location 'j',
        then the sum of arcs leaving 'j' must be at least 1.
        """
        outflow = quicksum(
            z[j, i, h] for i in self.location_graph.get_vertices() if i != j
        )

        requirement = quicksum(A[n, j] * B_nb[n, h] for n in self.N)

        return outflow >= requirement

    def constraint_articles_capacity(self, i, j, h, q, C_v, z):
        """
        (12): Articles capacity constraint.
        Ensures that the total capacity of articles assigned to a mission does
        not exceed the vehicle's capacity.
        """
        return q[i, j, h] - float(C_v) * z[i, j, h] <= 0

    def constraint_route_flow_conservation(self, z, h, i):
        """
        (13): Flow conservation constraint.
        Ensures that the flow of articles is conserved at each location.
        """
        return quicksum(
            z[g, i, h] for g in self.location_graph.get_vertices() if g != i
        ) == quicksum(z[i, j, h] for j in self.location_graph.get_vertices() if j != i)

    def constraint_one_input_arc_per_node(self, h, i, z):
        """
        (14): One input arc per node constraint.
        Ensures that each node i has maximum one incoming arc in the mission route.
        """
        return (
            quicksum(
                z[j, i, h]
                for j in self.location_graph.get_vertices()
                if j != i
            )
            <= 1
        )

    def constraint_one_output_arc_per_node(self, h, i, z):
        """
        (15): One output arc per node constraint.
        Ensures that each node i has maximum one outgoing arc in the mission route.
        """
        return (
            quicksum(
                z[i, j, h]
                for j in self.location_graph.get_vertices()
                if j != i
            )
            <= 1
        )

    def constraint_avoid_subtours_cycles(self, q, i, h, A, B_nb, n):
        """
        (16): Subtour elimination constraint.
        Ensures that the route does not contain subtours or cycles.
        """
        flow_in = quicksum(
            q[g, i, h]
            for g in self.location_graph.get_vertices()
            if g != self.location_graph.get_final()
        )
        required_flow = A[n, i] * B_nb[n, h]
        return flow_in >= required_flow

    def constraint_no_loops(self, h, i, z):
        """
        (17): No loops constraint.
        Ensures that the route does not contain loops.
        """
        return z[i, i, h] == 0 if i != self.location_graph.get_depot() else None

    def constraint_valid_execution_time(
        self, h, d, T_travel, T_setup, T_pick, C_n, B_nb, z
    ):
        """
        (18): Valid execution time constraint.
        Ensures that the execution time of a mission is correctly calculated
        based on travel time, setup time, and picking time.
        """
        return (
            T_setup
            + T_pick * quicksum(C_n[n] * B_nb[n, h] for n in self.N)
            + T_travel
            * (
                quicksum(
                    self.location_graph.get_distance(i, j) * z[i, j, h]
                    for i in self.location_graph.get_vertices()
                    for j in self.location_graph.get_vertices()
                    if i != self.location_graph.get_final()
                    and j != self.location_graph.get_depot()
                    and self.location_graph.has_edge(i, j)
                )
            )
            <= d[h]
        )

    def constraint_batch_execution_time(self, p, k, h, d, M, X, u):
        """
        (19): Batch execution time constraint.
        Ensures that the processing time of a batch assigned to a position
        of a picker is less or equal to the execution time of the mission
        assigned to that position.
        """
        return d[h] - M * (1 - X[p, k, h]) <= u[p, k]

    def constraint_processing_time(self, p, u, c):
        """
        (20): Completion time constraint.
        Ensures that the processing time is less or equal to the completion time
        for each position of a picker.
        """
        return u[p, 1] <= c[p, 1]

    def constraint_completition_batch_time(self, u, c, p, k):
        """
        (21): Completion time of batch constraint.
        Ensures that the completion time of a batch assigned to a position
        of a picker is correctly calculated based on the processing time
        of that batch.
        """
        return u[p, k] + c[p, k - 1] <= c[p, k]

    def constraint_tardiness_definition(self, c, p, k, T_due_n, n, M, h, X, B_nb, ta):
        """
        (22): Tardiness definition constraint.
        Ensures that the tardiness of an order is correctly calculated
        based on the due date and the completion time of the mission
        to which the order is assigned.
        """
        return c[p, k] - T_due_n[n] - M * (2 - X[p, k, h] - B_nb[n, h]) <= ta[n]

    def constraint_earliness_definition(self, c, p, k, T_due_n, n, M, h, X, B_nb, ea):
        """
        (23): Earliness definition constraint.
        Ensures that the earliness of an order is correctly calculated
        based on the due date and the completion time of the mission
        to which the order is assigned.
        """
        return T_due_n[n] - c[p, k] - M * (2 - X[p, k, h] - B_nb[n, h]) <= ea[n]
