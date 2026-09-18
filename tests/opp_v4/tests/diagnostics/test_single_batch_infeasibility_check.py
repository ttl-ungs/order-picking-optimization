"""
Diagnostic, not part of the regular stress battery -- deliberately outside
tests/opp_v4/tests/{normal,stress} so execute_tests.py/execute_stress_tests.py
never pick it up and analysis/ never sees it as just another instance.

Run directly:
    python -m unittest tests.opp_v4.tests.diagnostics.test_single_batch_infeasibility_check

Purpose (2026-08-27): opp_hc_2/opp_aco_2/opp_hc_3/opp_aco_3 all fail to
converge on the "25 orders per batch, 30 batches, 10x10 grid" stress
instance (scenario_custom_setup(30, 750, 10, 10)), and so does
opp_hc_2's fast deterministic path (_generate_feasible_route, Dijkstra
nearest-neighbor) for that instance's first batch (B1, 25 required
locations on a 100-node grid) -- confirmed with 2000 random visitation
orders via the same Dijkstra, all failing (see analysis/README.md's
"Instancias que quedan fuera de alcance..." for the full writeup and the
verification that this order-search method isn't itself buggy).

That's strong circumstantial evidence the underlying MILP is infeasible for
this exact batch (no simple/loop-free route visits all 25 required
locations), not just hard to solve -- but it's evidence from the heuristic
side, not a proof from the exact solver. This test isolates JUST that one
batch (drops the other 29 batches entirely, keeping the same grid, the same
25 orders/required locations, and the same weights/capacities as the real
test_09) and gives SCIP an explicit, generous time limit
(`time_limit_seconds` on solve_zpl) so it can actually conclude instead of
being killed mid-search by an external timeout -- which would lose the
verdict if SCIP was moments from proving infeasibility.

Three possible outcomes, and what each means:
  - status == "infeasible": SCIP proved no solution exists -- confirms the
    hypothesis directly. The full 30-batch instance is infeasible by
    construction, not merely hard.
  - status in ("optimal", "feasible"): SCIP found a route -- the hypothesis
    is WRONG, or at least incomplete. Worth reconciling with the 2000/2000
    Dijkstra failures (e.g. maybe a valid route exists that isn't reachable
    via nearest-neighbor-style construction from any order, which would
    itself be a different, interesting finding about the heuristics'
    construction strategy rather than about instance feasibility).
  - status == "timelimit": inconclusive -- raise the time limit and rerun,
    or accept this as unresolved and keep documenting it as "unproven but
    strongly suspected" infeasibility.
"""

import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
)

from models.utils.dat_files_builder import build_dat_files
from tests.opp_v4.tests.opp_test_case_v4 import OPPTestCaseV4
from tests.opp_v4.config import DAT_DIR, ZPL_PATH
from tests.utils.zpl_utils import solve_zpl
from tests.shared_scenarios.stress.scenario_custom_setup import scenario_custom_setup

# How long to let SCIP search before giving up. 30 min by default -- raise
# this (e.g. to 3600 or more) and rerun if the result comes back "timelimit"
# and you want a more definitive answer.
TIME_LIMIT_SECONDS = 1800


class TestSingleBatchInfeasibilityCheck(OPPTestCaseV4):
    """
    Isolates batch B1 (25 orders/25 required locations, 10x10 grid) from
    opp_hc_2's stress test_09 instance (scenario_custom_setup(30, 750, 10, 10))
    and asks the exact model to solve -- or definitively refute -- just that
    one batch, with SCIP given an explicit time budget to actually conclude.
    """

    def test_single_batch_b1_from_test_09(self):
        # Same scenario call as the real test_09, but we only keep B1's
        # orders and the required-location set they induce -- everything
        # else (grid, distances, depot/final) is identical to the real
        # instance, so this is a genuine sub-problem of it, not a different
        # instance.
        opp_location_graph, V, all_batches, all_orders, y, a = scenario_custom_setup(
            30, 750, 10, 10
        )

        b1_orders = {n for (n, b) in y.keys() if b == "B1" and y[(n, b)] == 1}
        self.assertEqual(len(b1_orders), 25, "Expected exactly 25 orders in B1 (sanity check).")

        N = b1_orders
        B = {"B1"}
        P = {"P1"}

        a_ni = {(n, v): a.get((n, v), 0) for n in N for v in V}
        bn = {(n, "B1"): 1 for n in N}

        cap_n = {n: 10.0 for n in N}
        due_date = {n: 30.0 for n in N}
        cap_vehicle = 250.0  # same as the real test_09 -- 25*10=250, exactly at the boundary

        w1, w2, gamma, delta = 9.0, 1.0, 1.0, 1.0
        beta_time, beta_setup, beta_picking, M = 0.5, 1.0, 1.0, 1000.0

        E = set()
        d_ij = {}
        for i in opp_location_graph.get_vertices():
            for j in opp_location_graph.get_vertices():
                if opp_location_graph.has_edge(i, j):
                    E.add((i, j))
                    d_ij[(i, j)] = opp_location_graph.get_distance(i, j)

        scenario_data = {
            "N": N,
            "V": set(opp_location_graph.get_vertices()),
            "P": P,
            "B": B,
            "E": E,
            "depot": opp_location_graph.get_depot(),
            "final": opp_location_graph.get_final(),
            "W_full": w1,
            "W_ea_ta": w2,
            "W_ea": gamma,
            "W_ta": delta,
            "B_time": beta_time,
            "B_setup": beta_setup,
            "B_picking": beta_picking,
            "C_v": cap_vehicle,
            "M": M,
            "C_n": cap_n,
            "Dd": due_date,
            "d_ij": d_ij,
            "S_i": {v: 0.0 for v in V},
            "A_ni": a_ni,
            "Bn": bn,
        }

        build_dat_files(DAT_DIR, scenario_data)

        print(f"\nSolving with SCIP time limit = {TIME_LIMIT_SECONDS}s "
              f"({TIME_LIMIT_SECONDS / 60:.0f} min)... this may take a while.")

        status, var_values = solve_zpl(
            ZPL_PATH,
            dat_dir=DAT_DIR,
            params={
                "N": len(N), "B": len(B), "V": len(V), "P": len(P),
                "C_n": cap_n, "Bn": bn, "C_v": cap_vehicle,
            },
            time_limit_seconds=TIME_LIMIT_SECONDS,
        )

        print(f"\n{'=' * 60}\nRESULTADO: status = {status!r}\n{'=' * 60}")
        if status == "infeasible":
            print("CONFIRMADO: SCIP probó que este lote (25 ubicaciones "
                  "requeridas, 100 nodos) no tiene ninguna ruta simple posible. "
                  "La instancia de 30 lotes es infeasible por construcción.")
        elif status in ("optimal", "feasible"):
            print("SORPRESA: SCIP SÍ encontró una ruta. La hipótesis de "
                  "infeasibilidad por construcción es incorrecta o incompleta -- "
                  "revisar por qué 2000/2000 intentos de Dijkstra con "
                  "reinicios aleatorios no la encontraron.")
        else:
            print(f"INCONCLUSO (status={status!r}): SCIP no terminó de decidir "
                  f"en {TIME_LIMIT_SECONDS}s. Subí TIME_LIMIT_SECONDS y volvé a "
                  f"correr para un veredicto más definitivo.")

        # Not a pass/fail assertion on purpose -- this test's value is the
        # printed verdict above, not a green checkmark. Only fail on a
        # genuine execution error (ZIMPL/SCIP crash), which solve_zpl already
        # raises as an exception before returning.
        self.assertIn(status, ("infeasible", "optimal", "feasible", "timelimit"))


if __name__ == "__main__":
    unittest.main()
