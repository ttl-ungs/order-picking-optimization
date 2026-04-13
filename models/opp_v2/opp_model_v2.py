"""
Sets:
    N = Órdenes de clientes
    V = Locaciones a visitar
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
    y_nb = 1 si el lote b ∈ B contiene a la orden n ∈ N
    x_pb = 1 si el lote b ∈ B es asignado al picker p ∈ P

Variables:
    ta_n = tardanza de la orden n ∈ N
    ea_n = adelanto de la orden n ∈ N
    t_(exec_b) = tiempo de ejecución del lote b ∈ B
    u_pb = tiempo de procesamiento del lote b ∈ B del picker p ∈ P
    v_pb = tiempo de completitud para el lote b ∈ B del picker p ∈ P
    z_ijb = 1 si el arco que conecta las locaciones i ∈ V y j ∈ V están
            incluidos en el lote b ∈ B, 0 si no
    f_ijb = Número de unidades pasando por el arco que conecta las locaciones
            i ∈ V y j ∈ V en el lote b ∈ B
"""

import time

import pyscipopt
from pyscipopt import quicksum
from models.base.model import Model

from dtos.opp.solve_model_dto import SolveModelDTO
from dtos.opp.opp_model_dto import OppModelDTO
from models.utils.output_builder import build_output

"""
Version of OPP model without concept of "missions" (H) and "periods" (K)
"""
class OPPModelV2(Model):
    def __init__(self, dto: OppModelDTO):
        # TODO: Create DTOs without H and K
        super().__init__()

        self.N = sorted(dto.N)
        self.location_graph = dto.location_graph
        self.P = sorted(dto.P)
        self.B = sorted(dto.B)
        self.start_time = dto.start_time

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
        start_time = self.start_time

        model = pyscipopt.Model("OPP Model Version 2")
        self.model = model

        # ta_n = delay of order n ∈ N
        ta = {n: model.addVar(name=f"ta_{n}", lb=0) for n in self.N}

        # ea_n = advance of order n ∈ N
        ea = {n: model.addVar(name=f"ea_{n}", lb=0) for n in self.N}

        # t_(exec_b) = execution time of mission b ∈ B
        t_exec = {b: model.addVar(name=f"t_exec_{b}", lb=0) for b in self.B}

        # u_pb = processing time of the batch b ∈ B of picker p ∈ P
        u = {
            (p, b): model.addVar(name=f"u_{p}_{b}", lb=0)
            for p in self.P
            for b in self.B
        }

        # v_pb = completion time of the batch b ∈ B of picker p ∈ P
        v = {
            (p, b): model.addVar(name=f"v_{p}_{b}", lb=0)
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

        # f_ijb = Number of units passing through the arc connecting locations
        #         i ∈ V and j ∈ V in mission b ∈ B
        f = {
            (i, j, b): model.addVar(name=f"f_{i}_{j}_{b}", lb=0)
            for i in self.location_graph.get_vertices()
            for j in self.location_graph.get_vertices()
            for b in self.B
        }

        # Objective function
        model.setObjective(
            self.objective_function(w1, v, w2, ea, gamma, delta, ta), sense="minimize"
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
                        self.constraint_force_visit_inflow(b, j, z, a, y),
                        name=f"force_visit_inflow_b{b}_j{j}",
                    )

        # (11)
        for b in self.B:
            for j in self.location_graph.get_vertices():
                if j != depot_node and j != final_node:
                    model.addCons(
                        self.constraint_force_visit_outflow(b, j, z, a, y),
                        name=f"force_visit_outflow_b{b}_j{j}",
                    )

        # (12)
        for b in self.B:
            for i in self.location_graph.get_vertices():
                for j in self.location_graph.get_vertices():
                    if i != final_node and j != depot_node:
                        model.addCons(
                            self.constraint_articles_capacity(
                                i, j, b, f, cap_vehicle, z
                            ),
                            name=f"articles_capacity_b{b}_i{i}_j{j}",
                        )

        # (13)
        for b in self.B:
            for i in self.location_graph.get_vertices():
                if i != depot_node and i != final_node:
                    model.addCons(
                        self.constraint_flow_conservation(z, b, i),
                        name=f"flow_conservation_b{b}_i{i}",
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
                self.constraint_f_depot_source(b, f, a, y),
                name=f"f_depot_source_b{b}",
            )
            for i in self.location_graph.get_vertices():
                if i != depot_node and i != final_node:
                    model.addCons(
                        self.constraint_f_flow_conservation(i, b, f, a, y),
                        name=f"f_flow_conservation_b{b}_i{i}",
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
                    t_exec,
                    beta_time,
                    beta_setup,
                    beta_picking,
                    cap_n,
                    y,
                    z,
                ),
                name=f"valid_execution_time_b{b}",
            )

        # (19)
        for p in self.P:
            for b in self.B:
                model.addCons(
                    self.constraint_batch_execution_time(p, b, t_exec, M, x, u),
                    name=f"batch_execution_time_p{p}_b{b}",
                )

        # (20)
        for p in self.P:
            for b in self.B:
                model.addCons(
                    self.constraint_processing_time(p, u, v, b),
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
                            v, p, due_date, n, M, b, x, y, ta
                        ),
                        name=f"tardiness_definition_p{p}_n{n}_b{b}",
                    )

        # (23)
        for p in self.P:
            for b in self.B:
                for n in self.N:
                    model.addCons(
                        self.constraint_earliness_definition(
                            v, p, due_date, n, M, b, x, y, ea
                        ),
                        name=f"earliness_definition_p{p}_n{n}_b{b}",
                    )

        # (24), (25), (26), (27), (28), (29), (30), (31) and (32) are implicit in the definition of the variables

        # Extra: Allow only paths between neighbors
        for b in self.B:
            for i in self.location_graph.get_vertices():
                for j in self.location_graph.get_vertices():
                    if not (self.location_graph.has_edge(i, j)):
                        model.addCons(
                            z[i, j, b] == 0, name=f"only_valid_edges_i{i}_j{j}_b{b}"
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
            P=self.P,
            B=self.B,
            ta=ta,
            ea=ea,
            t_exec=t_exec,
            v=v,
            z=z,
            depot_vertex=depot_node,
            final_vertex=final_node,
        )

        output = build_output(model, self.location_graph, self.B, z)
        return model.getStatus(), output

    def objective_function(self, w1, v, w2, ea, gamma, delta, ta):
        recollection_time = sum(v[p, b] for p in self.P for b in self.B)
        advance_time = sum(ea[n] for n in self.N)
        delay_time = sum(ta[n] for n in self.N)
        penalty = gamma * advance_time + delta * delay_time

        return w1 * recollection_time + w2 * penalty

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

    def constraint_force_visit_inflow(self, b, j, z, a, y):
        """
        (10): If an order from batch 'b' must visit location 'j',
        then the sum of arcs entering 'j' must be at least 1.
        """
        inflow = quicksum(
            z[i, j, b] for i in self.location_graph.get_vertices() if i != j
        )

        requirement = quicksum(a[n, j] * y[n, b] for n in self.N)

        return inflow >= requirement

    def constraint_force_visit_outflow(self, b, j, z, a, y):
        """
        (11): If an order from batch 'b' must visit location 'j',
        then the sum of arcs leaving 'j' must be at least 1.
        """
        outflow = quicksum(
            z[j, i, b] for i in self.location_graph.get_vertices() if i != j
        )

        requirement = quicksum(a[n, j] * y[n, b] for n in self.N)

        return outflow >= requirement

    def constraint_articles_capacity(self, i, j, b, f, cap_vehicle, z):
        """
        (12): Articles capacity constraint.
        Ensures that the total capacity of articles of a batch b does
        not exceed the vehicle's capacity.
        """
        return f[i, j, b] - float(cap_vehicle) * z[i, j, b] <= 0

    def constraint_flow_conservation(self, z, b, i):
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
            quicksum(
                z[j, i, b]
                for j in self.location_graph.get_vertices()
                if j != i
            )
            <= 1
        )

    def constraint_one_output_arc_per_node(self, b, i, z):
        """
        (15): One output arc per node constraint.
        Ensures that each node i has maximum one outgoing arc in the route.
        """
        return (
            quicksum(
                z[i, j, b]
                for j in self.location_graph.get_vertices()
                if j != i
            )
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

    def constraint_f_depot_source(self, b, f, a, y):
        """
        Depot sends out exactly required_nodes units.
        """
        # How many required_nodes batch b must visit
        required_nodes = sum(
            min(1, sum(a[n, i] * y[n, b] for n in self.N))
            for i in self.location_graph.get_vertices()
            if i != self.location_graph.get_depot()
            and i != self.location_graph.get_final()
        )
        # How much flow goes from depot_node to any node of batch b
        outflow = quicksum(
            f[self.location_graph.get_depot(), j, b]
            for j in self.location_graph.get_vertices()
            if j != self.location_graph.get_depot()
        )

        # outflow must be exactly required_flow
        return outflow == required_nodes


    def constraint_f_flow_conservation(self, i, b, f, a, y):
        """
        Gavish-Graves balance:
        inflow - outflow = demand at each intermediate node.
        Required nodes consume 1 unit, non-required nodes conserve flow.
        """
        # Inflow to node i (i != final_node)
        inflow = quicksum(
            f[g, i, b]
            for g in self.location_graph.get_vertices()
            if g != self.location_graph.get_final()
        )

        # Outflow of node i (i != depot_node)
        outflow = quicksum(
            f[i, j, b]
            for j in self.location_graph.get_vertices()
            if j != self.location_graph.get_depot()
        )

        # 1 if node i must be visited in batch b, else 0
        demand = min(1, sum(a[n, i] * y[n, b] for n in self.N))

        # If node i must be visited consumes 1 flow unit. Else, consumes 0 flow units.
        return inflow - outflow == demand

    def constraint_no_loops(self, b, i, z):
        """
        (17): No loops constraint.
        Ensures that the route does not contain loops.
        """
        return z[i, i, b] == 0 if i != self.location_graph.get_depot() else None

    def constraint_valid_execution_time(
        self, b, t_exec, beta_time, beta_setup, beta_picking, cap, y, z
    ):
        """
        (18): Valid execution time constraint.
        Ensures that the execution time of a mission is correctly calculated
        based on travel time, setup time, and picking time.
        """
        return (
            beta_setup
            + beta_picking * quicksum(cap[n] * y[n, b] for n in self.N)
            + beta_time
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
            <= t_exec[b]
        )

    def constraint_batch_execution_time(self, p, b, t_exec, M, x, u):
        """
        (19): Batch execution time constraint.
        Ensures that the processing time of a batch assigned to a picker is less or
        equal to the execution time of the batch
        assigned to that position.
        """
        return t_exec[b] - M * (1 - x[p, b]) <= u[p, b]

    def constraint_processing_time(self, p, u, v, b):
        """
        (20): Completion time constraint.
        Ensures that the processing time is less or equal to the completion time
        for each batch of a picker.
        """
        return u[p, b] <= v[p, b]

    # def constraint_completition_batch_time(self, u, v, p, b):
    #     """
    #     (21): Completion time of batch constraint.
    #     Ensures that the completion time of a batch assigned to a picker is
    #     correctly calculated based on the processing time of that batch.
    #     """
    #     return u[p, b] + v[p, b - 1] <= v[p, b]

    def constraint_tardiness_definition(self, v, p, due_date, n, M, b, x, y, ta):
        """
        (22): Tardiness definition constraint.
        Ensures that the tardiness of an order is correctly calculated
        based on the due date and the completion time of the batch
        to which the order is assigned.
        """
        return v[p, b] - due_date[n] - M * (2 - x[p, b] - y[n, b]) <= ta[n]

    def constraint_earliness_definition(self, v, p, due_date, n, M, b, x, y, ea):
        """
        (23): Earliness definition constraint.
        Ensures that the earliness of an order is correctly calculated
        based on the due date and the completion time of the batch
        to which the order is assigned.
        """
        return due_date[n] - v[p, b] - M * (2 - x[p, b] - y[n, b]) <= ea[n]
