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
        pass
