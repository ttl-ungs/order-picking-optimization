"""
Plain problem instances (physical data only -- graph, orders, batches,
pickers, weights -- no model-specific DTO yet). See adapters.py for how a
dict from here becomes a ready-to-solve (params, model_dto) pair for a
specific model family.

Each mirrors an existing, already-validated test's instance 1:1, reusing
that test's own scenario builder instead of
inventing a new one.
"""

from typing import Dict, List

from tests.shared_scenarios.normal.scenario_01 import basic_two_orders_capacity_limit
from tests.shared_scenarios.normal.three_missions_two_pickers_grid_graph import (
    scenario_three_missions_two_pickers_two_periods_grid_graph,
)
from tests.shared_scenarios.common.six_missions_three_pickers_grid_graph import (
    scenario_six_missions_two_periods_grid_graph,
)


def instance_tiny_two_orders() -> Dict:
    """
    2 orders, 2 batches, 1 implicit picker, 4-node graph. Same instance as
    test_opp_hc_2_model_01.py / test_opp_v3_model_1.py / test_opp_hc_4_
    model_01_equivalence.py, etc. -- the smallest shared instance in the
    whole suite.
    """
    V, B, w1, w2, gamma, delta, location_graph, cap_vehicle = basic_two_orders_capacity_limit()

    N = {"O1", "O2"}
    A = {(n, v): 0 for n in N for v in V}
    A[("O1", "L2")] = 1
    A[("O2", "L3")] = 1

    Bn = {("O1", "B1"): 1, ("O1", "B2"): 0, ("O2", "B1"): 0, ("O2", "B2"): 1}

    return {
        "name": "tiny_two_orders",
        "location_graph": location_graph,
        "N": N,
        "B": B,
        "P": {"P1"},
        "A": A,
        "Bn": Bn,
        "C_n": {"O1": 3.0, "O2": 3.0},
        "Dd": {"O1": 15.0, "O2": 15.0},
        "W_full": w1,
        "W_ea_ta": w2,
        "W_ea": gamma,
        "W_ta": delta,
        "B_time": 0.5,
        "B_setup": 1.0,
        "B_picking": 1.0,
        "C_v": cap_vehicle,
        "M": 1000.0,
    }


def instance_small_multi_picker() -> Dict:
    """
    6 orders, 3 batches, 2 pickers, 4x4 grid with transversal aisles. Same
    instance as test_opp_hc_2_model_16.py / test_opp_v3_model_16.py.
    """
    location_graph, V, B = scenario_three_missions_two_pickers_two_periods_grid_graph(4, 4)

    N = {"O1", "O2", "O3", "O4", "O5", "O6"}
    A = {(n, v): 0 for n in N for v in V}
    A[("O1", "V2")] = 1
    A[("O1", "V6")] = 1
    A[("O2", "V2")] = 1
    A[("O2", "V7")] = 1
    A[("O3", "V5")] = 1
    A[("O3", "V9")] = 1
    A[("O4", "V6")] = 1
    A[("O4", "V14")] = 1
    A[("O5", "V4")] = 1
    A[("O5", "V8")] = 1
    A[("O6", "V11")] = 1
    A[("O6", "V14")] = 1

    Bn = {(n, b): 0 for n in N for b in B}
    Bn[("O1", "B1")] = 1
    Bn[("O2", "B1")] = 1
    Bn[("O3", "B2")] = 1
    Bn[("O4", "B2")] = 1
    Bn[("O5", "B3")] = 1
    Bn[("O6", "B3")] = 1

    return {
        "name": "small_multi_picker",
        "location_graph": location_graph,
        "N": N,
        "B": B,
        "P": {"P1", "P2"},
        "A": A,
        "Bn": Bn,
        "C_n": {n: 10.0 for n in N},
        "Dd": {n: 30.0 for n in N},
        "W_full": 9.0,
        "W_ea_ta": 1.0,
        "W_ea": 1.0,
        "W_ta": 1.0,
        "B_time": 0.5,
        "B_setup": 1.0,
        "B_picking": 1.0,
        "C_v": 25.0,
        "M": 1000.0,
    }


def instance_medium_multi_picker() -> Dict:
    """
    12 orders, 6 batches, 3 pickers, 10x10 grid. Same instance as stress
    test #01 across every heuristic model's suite (hc_2/3/4, aco_2/3/4) --
    already the de facto canonical "medium" instance for cross-model
    comparison, just reused here instead of a new one.
    """
    location_graph, V, B = scenario_six_missions_two_periods_grid_graph(10, 10)

    N = {f"O{i}" for i in range(1, 13)}
    A = {(n, v): 0 for n in N for v in V}
    A[("O1", "V6")] = 1
    A[("O2", "V11")] = 1
    A[("O3", "V7")] = 1
    A[("O4", "V12")] = 1
    A[("O5", "V3")] = 1
    A[("O6", "V8")] = 1
    A[("O7", "V5")] = 1
    A[("O8", "V10")] = 1
    A[("O9", "V10")] = 1
    A[("O10", "V15")] = 1
    A[("O11", "V9")] = 1
    A[("O12", "V14")] = 1

    Bn = {(n, b): 0 for n in N for b in B}
    Bn[("O1", "B1")] = 1
    Bn[("O2", "B1")] = 1
    Bn[("O3", "B2")] = 1
    Bn[("O4", "B2")] = 1
    Bn[("O5", "B3")] = 1
    Bn[("O6", "B3")] = 1
    Bn[("O7", "B4")] = 1
    Bn[("O8", "B4")] = 1
    Bn[("O9", "B5")] = 1
    Bn[("O10", "B5")] = 1
    Bn[("O11", "B6")] = 1
    Bn[("O12", "B6")] = 1

    return {
        "name": "medium_multi_picker",
        "location_graph": location_graph,
        "N": N,
        "B": B,
        "P": {"P1", "P2", "P3"},
        "A": A,
        "Bn": Bn,
        "C_n": {n: 10.0 for n in N},
        "Dd": {n: 15.0 for n in N},
        "W_full": 9.0,
        "W_ea_ta": 1.0,
        "W_ea": 1.0,
        "W_ta": 1.0,
        "B_time": 0.5,
        "B_setup": 1.0,
        "B_picking": 1.0,
        "C_v": 20.0,
        "M": 1000.0,
    }


# Order matters for reporting (tiny -> small -> medium), not for correctness.
ALL_INSTANCES: List = [
    instance_tiny_two_orders,
    instance_small_multi_picker,
    instance_medium_multi_picker,
]
