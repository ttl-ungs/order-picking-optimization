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
    due_carico_n = Fecha límite para la órden n ∈ N
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
        due_carico: dict,
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
                    if i <= len(self.V) - 1:
                        model.addCons(
                            self.constraint_location_exit(h, n, i, z, a, y),
                            name=f"location_exit_h{h}_n{n}_i{i}",
                        )

        # (12)
        for h in self.H:
            for i in self.V:
                for j in self.V:
                    if i <= len(self.V) - 1 and j > 1:
                        model.addCons(
                            self.constraint_articles_capacity(
                                i, j, h, f, cap_vehicle, z
                            ),
                            name=f"articles_capacity_h{h}_i{i}_j{j}",
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
