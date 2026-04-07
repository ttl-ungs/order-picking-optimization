"""
Sets:
    N = Órdenes de clientes
    V = Locaciones a visitar
    H = Misiones que se pueden completar
    K = Períodos por picker en las que recolectan un pedido
    P = Pickers
    B = Lotes de pedidos factibles

Parameters:
    w_1 = Peso del tiempo de cumplimiento
    w_2 = Peso asociado a la suma pesada de las demoras y los adelantos
    γ = Peso asociado al adelanto total
    δ = Peso asociado a la demora total
    d_(i,j) = Distancia entre localizaciones de picking i ∈ V y j ∈ V
    cap_n = Capacidad requerida para una órden n ∈ N
    cap_vehicle = Capacidad del vehículo de picking
    a_ni = 1 si la órder n ∈ N debe visitar la locaclización de picking
            i ∈ V, 0 si no
    β^time = Tiempo requerido para viajar en una unidad de espacio
    β^setup = Tiempo requerido para planificar cada lote
    β^picking = Tiempo requerido para buscar y recolectar ítems
    due_date = Fecha límite para la órden n ∈ N
    M = Entero lo suficientemente grande
    dis_i = Distancia viajada para completar el lote i ∈ B
    capbatch_i = Capacidad requerida para un lote i ∈ B
    b_ni = 1 si el lote i ∈ B contiene la órden n ∈ N, 0 si no
    x_pkh = 1 si la mision h ∈ H es asignada en la posicion k ∈ K
            del picker p ∈ P, 0 si no
    y_nh = 1 si la orden n ∈ N es asignada a la mision h ∈ H, 0 si no

Variables:
    ta_n = tardanza de la orden n ∈ N
    ea_n = adelanto de la orden n ∈ N
    t_(exec_n) = tiempo de ejecución de la misión h ∈ H
    u_pk = tiempo de procesamiento del lote asignado a la posición k ∈ K
            del picker p ∈ P
    v_pk = tiempo de completitud para el lote asignado a la posición k ∈ K
            del picker p ∈ P
    z_ijh = 1 si el arco que conecta las locaciones i ∈ V y j ∈ V están
            incluidos en la misión h ∈ H, 0 si no
    f_ijh = Número de unidades pasando por el arco que conecta las locaciones
            i ∈ V y j ∈ V en la misión h ∈ H
"""

import time

import pyscipopt
from pyscipopt import quicksum
from models.base.model import Model

from models.opp.utils.opp_output_builder import build_output
from dtos.opp.solve_model_dto import SolveModelDTO
from dtos.opp.opp_model_dto import OppModelDTO

"""
Based on OPP article: A Model for the Joint Optimisation of Order Batching, 
Batch Assignment Sequencing and Picking Routing 
"""


class OPPModel(Model):
    def __init__(self, dto: OppModelDTO):
        super().__init__()

        self.N = sorted(dto.N)
        self.location_graph = dto.location_graph
        self.H = sorted(dto.H)
        self.K = sorted(dto.K)
        self.P = sorted(dto.P)
        self.B = sorted(dto.B)

    def solve(self, params: SolveModelDTO):
        w1 = params.w1
        w2 = params.w2
        gamma = params.gamma
        delta = params.delta
        cap_n = params.cap_n
        cap_vehicle = params.cap_vehicle
        a = params.a
        beta_time = params.beta_time
        beta_setup = params.beta_setup
        beta_picking = params.beta_picking
        due_date = params.due_date
        M = params.M
        x = params.x
        y = params.y
        start_time = params.start_time

        model = pyscipopt.Model("OPP Model")
        self.model = model

        # ta_n = delay of order n ∈ N
        ta = {n: model.addVar(name=f"ta_{n}", lb=0) for n in self.N}

        # ea_n = advance of order n ∈ N
        ea = {n: model.addVar(name=f"ea_{n}", lb=0) for n in self.N}

        # t_(exec_h) = execution time of mission h ∈ H
        t_exec = {h: model.addVar(name=f"t_exec_{h}", lb=0) for h in self.H}

        # u_pk = processing time of the batch assigned to position k ∈ K
        #        of picker p ∈ P
        u = {
            (p, k): model.addVar(name=f"u_{p}_{k}", lb=0)
            for p in self.P
            for k in self.K
        }

        # v_pk = completion time for the batch assigned to position k ∈ K
        #        of picker p ∈ P
        v = {
            (p, k): model.addVar(name=f"v_{p}_{k}", lb=0)
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

        # f_ijh = Number of units passing through the arc connecting locations
        #         i ∈ V and j ∈ V in mission h ∈ H
        f = {
            (i, j, h): model.addVar(name=f"f_{i}_{j}_{h}", lb=0)
            for i in self.location_graph.get_vertices()
            for j in self.location_graph.get_vertices()
            for h in self.H
        }

        # Objective function
        model.setObjective(
            self.objective_function(w1, v, w2, ea, gamma, delta, ta), sense="minimize"
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
                        self.constraint_force_visit_inflow(h, j, z, a, y),
                        name=f"force_visit_inflow_h{h}_j{j}",
                    )

        # (11)
        for h in self.H:
            for j in self.location_graph.get_vertices():
                if j != depot_node and j != final_node:
                    model.addCons(
                        self.constraint_force_visit_outflow(h, j, z, a, y),
                        name=f"force_visit_outflow_h{h}_j{j}",
                    )

        # (12)
        for h in self.H:
            for i in self.location_graph.get_vertices():
                for j in self.location_graph.get_vertices():
                    if i != final_node and j != depot_node:
                        model.addCons(
                            self.constraint_articles_capacity(
                                i, j, h, f, cap_vehicle, z
                            ),
                            name=f"articles_capacity_h{h}_i{i}_j{j}",
                        )

        # (13)
        for h in self.H:
            for i in self.location_graph.get_vertices():
                if i != depot_node and i != final_node:
                    model.addCons(
                        self.constraint_flow_conservation(z, h, i),
                        name=f"flow_conservation_h{h}_i{i}",
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
                            self.constraint_avoid_subtours_cycles(f, i, h, a, y, n),
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
                    t_exec,
                    beta_time,
                    beta_setup,
                    beta_picking,
                    cap_n,
                    y,
                    z,
                ),
                name=f"valid_execution_time_h{h}",
            )

        # (19)
        for p in self.P:
            for k in self.K:
                for h in self.H:
                    model.addCons(
                        self.constraint_batch_execution_time(p, k, h, t_exec, M, x, u),
                        name=f"batch_execution_time_p{p}_k{k}_h{h}",
                    )

        # (20)
        for p in self.P:
            model.addCons(
                self.constraint_processing_time(p, u, v),
                name=f"processing_time_p{p}_k1",
            )

        # (21)
        for p in self.P:
            for k in self.K:
                if k >= 2:
                    model.addCons(
                        self.constraint_completition_batch_time(u, v, p, k),
                        name=f"completition_batch_time_p{p}_k{k}",
                    )

        # (22)
        for p in self.P:
            for k in self.K:
                for h in self.H:
                    for n in self.N:
                        model.addCons(
                            self.constraint_tardiness_definition(
                                v, p, k, due_date, n, M, h, x, y, ta
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
                                v, p, k, due_date, n, M, h, x, y, ea
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
            t_exec=t_exec,
            v=v,
            z=z,
            depot_vertex=depot_node,
            final_vertex=final_node,
        )

        output = build_output(model, self.location_graph, self.H, z)
        return model.getStatus(), output

    def objective_function(self, w1, v, w2, ea, gamma, delta, ta):
        recollection_time = sum(v[p, k] for p in self.P for k in self.K)
        advance_time = sum(ea[n] for n in self.N)
        delay_time = sum(ta[n] for n in self.N)
        penalty = gamma * advance_time + delta * delay_time

        return w1 * recollection_time + w2 * penalty

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

    def constraint_force_visit_inflow(self, h, j, z, a, y):
        """
        (10): If mission 'h' must visit location 'j',
        then the sum of arcs entering 'j' must be at least 1.
        """
        inflow = quicksum(
            z[i, j, h] for i in self.location_graph.get_vertices() if i != j
        )

        requirement = quicksum(a[n, j] * y[n, h] for n in self.N)

        return inflow >= requirement

    def constraint_force_visit_outflow(self, h, j, z, a, y):
        """
        (11): If mission 'h' must visit location 'j',
        then the sum of arcs leaving 'j' must be at least 1.
        """
        outflow = quicksum(
            z[j, i, h] for i in self.location_graph.get_vertices() if i != j
        )

        requirement = quicksum(a[n, j] * y[n, h] for n in self.N)

        return outflow >= requirement

    def constraint_articles_capacity(self, i, j, h, f, cap_vehicle, z):
        """
        (12): Articles capacity constraint.
        Ensures that the total capacity of articles assigned to a mission does
        not exceed the vehicle's capacity.
        """
        return f[i, j, h] - float(cap_vehicle) * z[i, j, h] <= 0

    def constraint_flow_conservation(self, z, h, i):
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

    def constraint_avoid_subtours_cycles(self, f, i, h, a, y, n):
        """
        (16): Subtour elimination constraint.
        Ensures that the route does not contain subtours or cycles.
        """
        flow_in = quicksum(
            f[g, i, h]
            for g in self.location_graph.get_vertices()
            if g != self.location_graph.get_final()
        )
        required_flow = a[n, i] * y[n, h]
        return flow_in >= required_flow

    def constraint_no_loops(self, h, i, z):
        """
        (17): No loops constraint.
        Ensures that the route does not contain loops.
        """
        return z[i, i, h] == 0 if i != self.location_graph.get_depot() else None

    def constraint_valid_execution_time(
        self, h, t_exec, beta_time, beta_setup, beta_picking, cap, y, z
    ):
        """
        (18): Valid execution time constraint.
        Ensures that the execution time of a mission is correctly calculated
        based on travel time, setup time, and picking time.
        """
        return (
            beta_setup
            + beta_picking * quicksum(cap[n] * y[n, h] for n in self.N)
            + beta_time
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
            <= t_exec[h]
        )

    def constraint_batch_execution_time(self, p, k, h, t_exec, M, x, u):
        """
        (19): Batch execution time constraint.
        Ensures that the processing time of a batch assigned to a position
        of a picker is less or equal to the execution time of the mission
        assigned to that position.
        """
        return t_exec[h] - M * (1 - x[p, k, h]) <= u[p, k]

    def constraint_processing_time(self, p, u, v):
        """
        (20): Completion time constraint.
        Ensures that the processing time is less or equal to the completion time
        for each position of a picker.
        """
        return u[p, 1] <= v[p, 1]

    def constraint_completition_batch_time(self, u, v, p, k):
        """
        (21): Completion time of batch constraint.
        Ensures that the completion time of a batch assigned to a position
        of a picker is correctly calculated based on the processing time
        of that batch.
        """
        return u[p, k] + v[p, k - 1] <= v[p, k]

    def constraint_tardiness_definition(self, v, p, k, due_date, n, M, h, x, y, ta):
        """
        (22): Tardiness definition constraint.
        Ensures that the tardiness of an order is correctly calculated
        based on the due date and the completion time of the mission
        to which the order is assigned.
        """
        return v[p, k] - due_date[n] - M * (2 - x[p, k, h] - y[n, h]) <= ta[n]

    def constraint_earliness_definition(self, v, p, k, due_date, n, M, h, x, y, ea):
        """
        (23): Earliness definition constraint.
        Ensures that the earliness of an order is correctly calculated
        based on the due date and the completion time of the mission
        to which the order is assigned.
        """
        return due_date[n] - v[p, k] - M * (2 - x[p, k, h] - y[n, h]) <= ea[n]
