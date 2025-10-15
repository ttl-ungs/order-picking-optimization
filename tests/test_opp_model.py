import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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

        # ---- Inicialización ----
        model = OPPModel(N, V, H, K, P, B)

        output_handler = OutputHandler()
        model.attach(output_handler)

        # ---- Definición de parámetros ----

        # Pesos
        w1 = 1.0  # Peso del tiempo de cumplimiento
        w2 = 10.0  # Peso de penalizaciones
        gamma = 1.0  # Peso del adelanto
        delta = 5.0  # Peso de la demora

        # Distancias
        M_cost = 99999
        d = {
            (1, 1): M_cost,
            (1, 2): 10.0,
            (1, 3): 12.0,
            (1, 4): M_cost,
            (2, 1): M_cost,
            (2, 2): M_cost,
            (2, 3): 5.0,
            (2, 4): 10.0,
            (3, 1): M_cost,
            (3, 2): 5.0,
            (3, 3): M_cost,
            (3, 4): 10.0,
            (4, 1): M_cost,
            (4, 2): M_cost,
            (4, 3): M_cost,
            (4, 4): M_cost,
        }

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

        dis = {}
        capbatch = {}
        b = {}

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
                d,
                cap_n,
                cap_vehicle,
                a,
                beta_time,
                beta_setup,
                beta_picking,
                due_date,
                M,
                dis,
                capbatch,
                b,
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

    def test_two_orders_two_aisles(self, observer: Observer = None):
        from tests.test_scenarios import two_orders_two_aisles

        V, H, K, P, B, w1, w2, gamma, delta, d, cap_vehicle, cap_n, x = (
            two_orders_two_aisles()
        )
        N = {1, 2}

        N = {1, 2}

        a = {(n, v): 0 for n in N for v in V}

        # Order 1 must visit locations 2, 3, 4
        a[(1, 2)] = 1
        a[(1, 3)] = 1
        a[(1, 4)] = 1

        # Order 2 must visit locations 5, 6, 7
        a[(2, 5)] = 1
        a[(2, 6)] = 1
        a[(2, 7)] = 1

        y = {(1, 1): 1, (1, 2): 0, (2, 1): 0, (2, 2): 1}

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        due_date = {1: 15.0, 2: 15.0}
        dis = {}
        capbatch = {}
        b = {}

        model = OPPModel(N, V, H, K, P, B)
        output_handler = OutputHandler()
        model.attach(output_handler)

        try:
            result = model.solve(
                w1,
                w2,
                gamma,
                delta,
                d,
                cap_vehicle,
                cap_n,
                a,
                beta_time,
                beta_setup,
                beta_picking,
                due_date,
                M,
                dis,
                capbatch,
                b,
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
