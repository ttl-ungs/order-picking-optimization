import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.opp_location_graph import OPPLocationGraph
from observer.observer import Observer
from utils.output_handler import OutputHandler
from models.opp_model import OPPModel


class TestOPPModel(unittest.TestCase):

    def test_basic_two_orders_capacity_limit(self, observer: Observer = None):
        # ---- Conjuntos ----
        N = {1, 2}  # Órdenes
        V = {1, 2, 3, 4}  # Locaciones: 1=Inicio, 4=Fin, 2,3=Picking
        H = {1, 2}  # Misiones
        K = {1}  # Posiciones por picker
        P = {1, 2}  # Pickers
        B = set()  # Lotes Factibles

        location_graph = OPPLocationGraph(depot_node=1, final_node=4)

        for v in V:
            if v in {2, 3}:
                location_graph.add_vertex(v, "picking")

        location_graph.add_edge(1, 2, 10.0)
        location_graph.add_edge(1, 3, 12.0)
        location_graph.add_edge(2, 3, 5.0)
        location_graph.add_edge(2, 4, 10.0)
        location_graph.add_edge(3, 2, 5.0)
        location_graph.add_edge(3, 4, 10.0)

        # ---- Inicialización ----
        model = OPPModel(N, location_graph, H, K, P, B)

        output_handler = OutputHandler()
        model.attach(output_handler)

        # ---- Definición de parámetros ----

        # Pesos
        w1 = 1.0  # Peso del tiempo de cumplimiento
        w2 = 10.0  # Peso de penalizaciones
        gamma = 1.0  # Peso del adelanto
        delta = 5.0  # Peso de la demora

        # Capacidades
        cap_vehicle = 5.0
        cap_n = {1: 3.0, 2: 3.0}

        # Ubicaciones de picking
        a = {
            (1, 1): 0,
            (1, 2): 1,
            (1, 3): 0,
            (1, 4): 0,
            (2, 1): 0,
            (2, 2): 0,
            (2, 3): 1,
            (2, 4): 0,
        }

        # Tiempos
        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        # Fechas límite
        due_date = {1: 15.0, 2: 15.0}

        # ---- Variables de decisión ----
        # Asignación de pickers
        x = {(p, k, h): 0 for p in P for k in K for h in H}
        x[1, 1, 1] = 1
        x[2, 1, 2] = 1

        # Asignación Orden/Misión
        y = {(n, h): 0 for n in N for h in H}
        y[1, 1] = 1
        y[2, 2] = 1

        # ---- Ejecución del modelo ----
        try:
            result = model.solve(
                w1,
                w2,
                gamma,
                delta,
                cap_n,
                cap_vehicle,
                a,
                beta_time,
                beta_setup,
                beta_picking,
                due_date,
                M,
                x,
                y,
            )
        except Exception as e:
            self.fail(f"La ejecución del modelo falló con la excepción: {e}")

        # ---- Verificación ----
        self.assertTrue(
            result in ("optimal", "feasible", "infeasible", "unbounded"),
            "SCIP no encontró ningún estado de solución.",
        )

    def test_two_orders_two_aisles(self):
        from tests.test_scenarios import two_orders_two_aisles

        V, H, K, P, B, w1, w2, gamma, delta, opp_location_graph, cap_vehicle, x = (
            two_orders_two_aisles()
        )

        N = {"O1", "O2"}
        a = {(n, v): 0 for n in N for v in V}

        # Order 1 must visit locations 2, 3, 4
        a[("O1", "L2")] = 1
        a[("O1", "L3")] = 1
        a[("O1", "L4")] = 1

        # Order 2 must visit locations 5, 6, 7
        a[("O2", "L5")] = 1
        a[("O2", "L6")] = 1
        a[("O2", "L7")] = 1

        y = {("O1", "M1"): 1, ("O1", "M2"): 0, ("O2", "M1"): 0, ("O2", "M2"): 1}
        cap_n = {"O1": 3.0, "O2": 3.0}

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        due_date = {"O1": 15.0, "O2": 15.0}

        model = OPPModel(N, opp_location_graph, H, K, P, B)
        output_handler = OutputHandler()
        model.attach(output_handler)

        try:
            result = model.solve(
                w1,
                w2,
                gamma,
                delta,
                cap_n,
                cap_vehicle,
                a,
                beta_time,
                beta_setup,
                beta_picking,
                due_date,
                M,
                x,
                y,
            )
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertTrue(
            result in ("optimal", "feasible", "infeasible", "unbounded"),
            "The model did not find a solution.",
        )

    def test_two_orders_two_aisles_one_picking_point_per_order(self):
        from tests.test_scenarios import two_orders_two_aisles

        V, H, K, P, B, w1, w2, gamma, delta, opp_location_graph, cap_vehicle, x = (
            two_orders_two_aisles()
        )

        N = {"O1", "O2"}
        a = {(n, v): 0 for n in N for v in V}

        # Order 1 must visit location 3
        a[("O1", "L3")] = 1

        # Order 2 must visit location 5
        a[("O2", "L5")] = 1

        y = {("O1", "M1"): 1, ("O1", "M2"): 0, ("O2", "M1"): 0, ("O2", "M2"): 1}
        cap_n = {"O1": 3.0, "O2": 3.0}

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        due_date = {"O1": 15.0, "O2": 15.0}

        model = OPPModel(N, opp_location_graph, H, K, P, B)
        output_handler = OutputHandler()
        model.attach(output_handler)

        try:
            result = model.solve(
                w1,
                w2,
                gamma,
                delta,
                cap_n,
                cap_vehicle,
                a,
                beta_time,
                beta_setup,
                beta_picking,
                due_date,
                M,
                x,
                y,
            )
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertTrue(
            result in ("optimal", "feasible", "infeasible", "unbounded"),
            "The model did not find a solution.",
        )


if __name__ == "__main__":
    # pyscipopt.SCIP_PARAMSETTING_DEFAULT.set("limits/time", 60)
    unittest.main()
