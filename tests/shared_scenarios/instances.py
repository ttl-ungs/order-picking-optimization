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

from tests.shared_scenarios.functional.scenario_01 import basic_two_orders_capacity_limit
from tests.shared_scenarios.functional.three_missions_two_pickers_grid_graph import (
    scenario_three_missions_two_pickers_two_periods_grid_graph,
)
from tests.shared_scenarios.common.six_missions_three_pickers_grid_graph import (
    scenario_six_missions_two_periods_grid_graph,
)


def instance_tiny_two_orders() -> Dict:
    """
    2 orders, 2 batches, 1 implicit picker, 4-node graph. Same instance as
    opp_hc_2's test_case_01.py / opp_v3's test_case_01.py / opp_hc_4's
    test_case_equivalence.py, etc. -- the smallest shared instance in the
    whole suite.
    """
    V, B, w1, w2, gamma, delta, location_graph, cap_vehicle = basic_two_orders_capacity_limit()

    N = {"O1", "O2"}
    A = {(n, v): 0 for n in N for v in V}
    A[("O1", "L2")] = 1
    A[("O2", "L3")] = 1

    B_nb = {("O1", "B1"): 1, ("O1", "B2"): 0, ("O2", "B1"): 0, ("O2", "B2"): 1}

    return {
        "name": "tiny_two_orders",
        "location_graph": location_graph,
        "N": N,
        "B": B,
        "P": {"P1"},
        "A": A,
        "B_nb": B_nb,
        "C_n": {"O1": 3.0, "O2": 3.0},
        "T_due_n": {"O1": 15.0, "O2": 15.0},
        "W_c": w1,
        "W_pen": w2,
        "W_e": gamma,
        "W_t": delta,
        "T_travel": 0.5,
        "T_setup": 1.0,
        "T_pick": 1.0,
        "C_v": cap_vehicle,
        "M": 1000.0,
    }


def instance_small_multi_picker() -> Dict:
    """
    6 orders, 3 batches, 2 pickers, 4x4 grid with transversal aisles. Same
    instance as opp_hc_2's test_case_12.py / opp_v3's test_case_12.py.
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

    B_nb = {(n, b): 0 for n in N for b in B}
    B_nb[("O1", "B1")] = 1
    B_nb[("O2", "B1")] = 1
    B_nb[("O3", "B2")] = 1
    B_nb[("O4", "B2")] = 1
    B_nb[("O5", "B3")] = 1
    B_nb[("O6", "B3")] = 1

    return {
        "name": "small_multi_picker",
        "location_graph": location_graph,
        "N": N,
        "B": B,
        "P": {"P1", "P2"},
        "A": A,
        "B_nb": B_nb,
        "C_n": {n: 10.0 for n in N},
        "T_due_n": {n: 30.0 for n in N},
        "W_c": 9.0,
        "W_pen": 1.0,
        "W_e": 1.0,
        "W_t": 1.0,
        "T_travel": 0.5,
        "T_setup": 1.0,
        "T_pick": 1.0,
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

    B_nb = {(n, b): 0 for n in N for b in B}
    B_nb[("O1", "B1")] = 1
    B_nb[("O2", "B1")] = 1
    B_nb[("O3", "B2")] = 1
    B_nb[("O4", "B2")] = 1
    B_nb[("O5", "B3")] = 1
    B_nb[("O6", "B3")] = 1
    B_nb[("O7", "B4")] = 1
    B_nb[("O8", "B4")] = 1
    B_nb[("O9", "B5")] = 1
    B_nb[("O10", "B5")] = 1
    B_nb[("O11", "B6")] = 1
    B_nb[("O12", "B6")] = 1

    return {
        "name": "medium_multi_picker",
        "location_graph": location_graph,
        "N": N,
        "B": B,
        "P": {"P1", "P2", "P3"},
        "A": A,
        "B_nb": B_nb,
        "C_n": {n: 10.0 for n in N},
        "T_due_n": {n: 15.0 for n in N},
        "W_c": 9.0,
        "W_pen": 1.0,
        "W_e": 1.0,
        "W_t": 1.0,
        "T_travel": 0.5,
        "T_setup": 1.0,
        "T_pick": 1.0,
        "C_v": 20.0,
        "M": 1000.0,
    }


# Order matters for reporting (tiny -> small -> medium), not for correctness.
ALL_INSTANCES: List = [
    instance_tiny_two_orders,
    instance_small_multi_picker,
    instance_medium_multi_picker,
]
