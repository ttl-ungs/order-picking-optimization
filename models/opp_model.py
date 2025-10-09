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
    due_date_n = Fecha límite para la órden n ∈ N
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

import pyscipopt
from pyscipopt import quicksum
from models.model import Model

"""
Based on OPP article: A Model for the Joint Optimisation of Order Batching, 
Batch Assignment Sequencing and Picking Routing 
"""


class OPPModel(Model):
    def __init__(self, N: set, V: set, H: set, K: set, P: set, B: set):
        super().__init__()

        self.N = N
        self.V = V
        self.H = H
        self.K = K
        self.P = P
        self.B = B

    def solve(
        self,
        w1: float,
        w2: float,
        gamma: float,
        delta: float,
        d: dict,
        cap_n: dict,
        cap_vehicle: float,
        a: dict,
        beta_time: float,
        beta_setup: float,
        beta_picking: float,
        due_date: dict,
        M: float,
        dis: dict,
        capbatch: dict,
        b: dict,
        x: dict,
        y: dict,
    ):
        model = pyscipopt.Model("OPP Model")

        # ta_n = delay of order n ∈ N
        ta = [model.addVar(f"ta_{n}") for n in self.N]

        # ea_n = advance of order n ∈ N
        ea = [model.addVar(f"ea_{n}") for n in self.N]

        # t_(exec_h) = execution time of mission h ∈ H
        t_exec = [model.addVar(f"t_exec_{h}") for h in self.H]

        # u_pk = processing time of the batch assigned to position k ∈ K
        #        of picker p ∈ P
        u = {(p, k): model.addVar(f"u_{p}_{k}") for p in self.P for k in self.K}

        # v_pk = completion time for the batch assigned to position k ∈ K
        #        of picker p ∈ P
        v = {(p, k): model.addVar(f"v_{p}_{k}") for p in self.P for k in self.K}

        # z_ijh = 1 if the arc connecting locations i ∈ V and j ∈ V are
        #         included in mission h ∈ H, 0 otherwise
        z = {
            (i, j, h): model.addVar(f"z_{i}_{j}_{h}", vtype="B")
            for i in self.V
            for j in self.V
            for h in self.H
        }

        # f_ijh = Number of units passing through the arc connecting locations
        #         i ∈ V and j ∈ V in mission h ∈ H
        f = {
            (i, j, h): model.addVar(f"f_{i}_{j}_{h}")
            for i in self.V
            for j in self.V
            for h in self.H
        }

        # Objective function
        model.setObjective(
            self.objective_function(w1, v, w2, ea, gamma, delta, ta),
            sense=pyscipopt.SCIP_OPTIMIZE_MINIMIZE,
        )

        # Constraints

        final_node = len(self.V) - 1

        # (6)
        for h in self.H:
            model.addCons(
                self.constraint_start_from_depot_rule(z, h),
                name=f"start_from_depot_h{h}",
            )

        # (7)
        for h in self.H:
            model.addCons(
                self.constraint_finish_at_end(z, h),
                name=f"finish_at_end_h{h}",
            )

        # (8)
        model.addCons(
            self.constraint_cant_go_back_to_depot(z),
            name=f"cant_go_back_to_depot_h{h}",
        )

        # (9)
        model.addCons(
            self.constraint_cant_move_from_end_node(z),
            name=f"cant_move_from_end_node_h{h}",
        )

        # (10)
        for h in self.H:
            for n in self.N:
                for j in self.V:
                    if j > 2:
                        model.addCons(
                            self.constraint_location_enter(h, n, j, z, a, y),
                            name=f"location_enter_h{h}_n{n}_j{j}",
                        )

        # (11)
        for h in self.H:
            for n in self.N:
                for i in self.V:
                    if i <= final_node:
                        model.addCons(
                            self.constraint_location_exit(h, n, i, z, a, y),
                            name=f"location_exit_h{h}_n{n}_i{i}",
                        )

        # (12)
        for h in self.H:
            for i in self.V:
                for j in self.V:
                    if i <= final_node and j > 1:
                        model.addCons(
                            self.constraint_articles_capacity(
                                i, j, h, f, cap_vehicle, z
                            ),
                            name=f"articles_capacity_h{h}_i{i}_j{j}",
                        )

        # (13)
        for h in self.H:
            for i in self.V:
                if i >= 2 and i <= final_node:
                    model.addCons(
                        self.constraint_flow_conservation(z, h, i),
                        name=f"flow_conservation_h{h}_i{i}",
                    )

        # (14)
        for h in self.H:
            for i in self.V:
                if i >= 2 and i <= final_node:
                    model.addCons(
                        self.constraint_one_input_arc_per_node(h, i, z),
                        name=f"one_input_arc_per_node_h{h}_i{i}",
                    )

        # (15)
        for h in self.H:
            for n in self.N:
                for j in self.V:
                    if j >= 2:
                        model.addCons(
                            self.constraint_one_output_arc_per_node(h, n, j, z, a, y),
                            name=f"one_output_arc_per_node_h{h}_n{n}_j{j}",
                        )

        # (16)
        for h in self.H:
            for n in self.N:
                for i in self.V:
                    if i >= 2 and i <= final_node:
                        model.addCons(
                            self.constraint_avoid_subtours_cycles(f, i, h, a, y, n),
                            name=f"avoid_subtours_cycles_h{h}_n{n}_i{i}",
                        )

        # (17)
        for h in self.H:
            for i in self.V:
                if i >= 2 and i <= final_node:
                    model.addCons(
                        self.constraint_no_loops(h, i, z), name=f"no_loops_h{h}_i{i}"
                    )

        # (18)
        for h in self.H:
            model.addCons(
                self.constraint_valid_excecution_time(
                    h, t_exec, beta_time, beta_setup, beta_picking, cap_n, y, d, z
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

        # (24)
        for p in self.P:
            for k in self.K:
                for h in self.H:
                    model.addCons(
                        self.constraint_x_binary(p, k, h, x),
                        name=f"x_binary_p{p}_k{k}_h{h}",
                    )

        # (25)
        for h in self.H:
            for n in self.N:
                model.addCons(
                    self.constraint_y_binary(n, h, y),
                    name=f"y_binary_n{n}_h{h}",
                )

    def objective_function(self, w1, v, w2, ea, gamma, delta, ta):
        recolection_time = sum(v[p, k] for p in self.P for k in self.K)
        advance_time = sum(ea[n] for n in self.N)
        delay_time = sum(ta[n] for n in self.N)
        penalty = gamma * advance_time + delta * delay_time

        return w1 * recolection_time + w2 * penalty

    def constraint_start_from_depot(self, z, h):
        """
        (6): Each mission must start from the depot (node 1).
        """
        # We assume the initial depot is node 1.
        # The sum of the arcs z(1, j, h) for all destinations 'j' must be 1.
        return quicksum(z[1, j, h] for j in self.V if j > 1) == 1

    def constraint_finish_at_end(self, z, h):
        """
        (7): Each mission must finish at the end (node 1).
        """
        # We assume the end node is node len(J).
        # The sum of the arcs z(1, len(J) - 1, h) for all origins 'i' must be 1.

        final_node = len(self.V) - 1
        return quicksum(z[1, final_node, h] for i in self.V if i > 1) == 1

    def constraint_cant_go_back_to_depot(self, z):
        """
        (8): A picker cannot return to the depot (node 1) after leaving it.
        """
        # We assume the depot is node 1.
        # The sum of the arcs z(i, 1, h) for all origins 'i' must be 0.
        return quicksum(z[i, 1, h] for i in self.V for h in self.H if i > 1) == 0

    def constraint_cant_move_from_end_node(self, z):
        """
        (9): A picker cannot leave the end node.
        """
        # We assume the end node is node len(J).
        # The sum of the arcs z(len(J), j, h) for all destinations 'j' must be 0.

        final_node = len(self.V) - 1
        return (
            quicksum(
                z[final_node, j, h] for j in self.V for h in self.H if j < final_node
            )
            == 0
        )

    def constraint_location_enter(self, h, n, j, z, a, y):
        """
        (10): Location enter constraint.
        Ensures that if a location is visited in a mission, then the route must
        have a path that enters the location.
        """

        final_node = len(self.V) - 1
        return (z[i, j, h] >= a[n, j] * y[n, h] for i in self.V if i < final_node)

    def constraint_location_exit(self, h, n, i, z, a, y):
        """
        (11): Location exit constraint.
        Ensures that if a location is visited in a mission, then the route must
        have a path that exits the location.
        """
        return (z[j, i, h] >= a[n, j] * y[n, h] for j in self.V if j > 1)

    def constraint_articles_capacity(self, i, j, h, f, cap_vehicle, z):
        """
        (12): Articles capacity constraint.
        Ensures that the total capacity of articles assigned to a mission does
        not exceed the vehicle's capacity.
        """
        return f[i, j, h] <= cap_vehicle * z[i, j, h]

    def constraint_flow_conservation(self, z, h, i):
        """
        (13): Flow conservation constraint.
        Ensures that the flow of articles is conserved at each location.
        """

        final_node = len(self.V) - 1
        return quicksum(z(g, i, h) for g in self.V if g < final_node) == quicksum(
            z(i, j, h) for j in self.V if j > 2
        )

    def constraint_one_input_arc_per_node(self, h, i, z):
        """
        (14): One input arc per node constraint.
        Ensures that each node has maximum one incoming arc in the mission route.
        """
        final_node = len(self.V) - 1
        return quicksum(z[i, j, h] for j in self.V if j < final_node) <= 1

    def constraint_one_output_arc_per_node(self, h, n, j, z, a, y):
        """
        (15): One output arc per node constraint.
        Ensures that each node has maximum one outgoing arc in the mission route.
        """
        final_node = len(self.V) - 1
        return (z[i, j, h] >= a[n, j] * y[n, h] for i in self.V if i < final_node)

    def constraint_avoid_subtours_cycles(self, f, i, h, a, y, n):
        """
        (16): Subtour elimination constraint.
        Ensures that the route does not contain subtours or cycles.
        """
        final_node = len(self.V) - 1
        return (
            quicksum(f[g, i, h] for g in self.V if g < final_node)
            == quicksum(f[i, j, h] for j in self.V if j > 2)
            >= a[n, i] * y[n, h]
        )

    def constraint_no_loops(self, h, i, z):
        """
        (17): No loops constraint.
        Ensures that the route does not contain loops.
        """
        final_node = len(self.V) - 1
        return z[i, i, h] == 0 if i >= 2 and i <= final_node else None

    def constraint_valid_excecution_time(
        self, h, t_exec, beta_time, beta_setup, beta_picking, cap, y, d, z
    ):
        """
        (18): Valid execution time constraint.
        Ensures that the execution time of a mission is correctly calculated
        based on travel time, setup time, and picking time.
        """
        final_node = len(self.V) - 1
        return (
            beta_setup
            + beta_picking * quicksum(cap[n] * y[n, h] for n in self.N)
            + beta_time
            * (
                quicksum(
                    d[i, j] * z[i, j, h]
                    for i in self.V
                    for j in self.V
                    if i < final_node and j > 2
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

    def constraint_completition_batch_time(u, v, p, k):
        """
        (21): Completion time of batch constraint.
        Ensures that the completion time of a batch assigned to a position
        of a picker is correctly calculated based on the processing time
        of that batch.
        """
        return u[p, k] + v[p, k - 1] <= v[p, k]

    def constraint_tardiness_definition(v, p, k, due_date, n, M, h, x, y, ta):
        """
        (22): Tardiness definition constraint.
        Ensures that the tardiness of an order is correctly calculated
        based on the due date and the completion time of the mission
        to which the order is assigned.
        """
        return v[p, k] - due_date[n] - M * (2 - x[p, k, h] - y[n, h]) <= ta[n]

    def constraint_earliness_definition(v, p, k, due_date, n, M, h, x, y, ea):
        """
        (23): Earliness definition constraint.
        Ensures that the earliness of an order is correctly calculated
        based on the due date and the completion time of the mission
        to which the order is assigned.
        """
        return due_date[n] - v[p, k] - M * (2 - x[p, k, h] - y[n, h]) <= ea[n]

    def constraint_x_binary(self, p, k, h, x):
        """
        (24): Binary constraint for x variables.
        Ensures that the variable x is binary (0 or 1).
        """
        return x[p, k, h] in [0, 1]

    def constraint_y_binary(self, n, h, y):
        """
        (25): Binary constraint for y variables.
        Ensures that the variable y is binary (0 or 1).
        """
        return y[n, h] in [0, 1]
