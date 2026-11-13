"""
Objective function evaluator for opp_aco (OPP v4 + picker speed, no
congestion).

Identical to opp_aco_2's RouteEvaluator, except a batch's execution time
now depends on WHICH picker runs it: the travel+service portion is divided
by that picker's speed (V_p), while setup/picking time stays fixed (same
split as opp_split_stage2_scheduling.zpl's T_exec_pb -- see models/opp_aco/
opp_aco.py header). Batches on the same picker still run sequentially;
batches on different pickers still run in parallel.
"""

from typing import Dict, List, Set

from models.opp_aco.utils import exec_time


class RouteEvaluator:
    """Evaluates the opp_aco objective function (v4 objective, picker-speed-aware)."""

    def __init__(
        self,
        N: Set,
        B: Set,
        P: List[str],
        location_graph,
        batch_assignments: Dict[str, Set[str]],
        W_c: float,
        W_pen: float,
        W_e: float,
        W_t: float,
        C_n: Dict,
        C_v: float,
        A: Dict,
        T_travel: float,
        T_setup: float,
        T_pick: float,
        S: Dict,
        T_due_n: Dict,
        M: float,
        V_p: Dict[str, float],
    ):
        self.N = N
        self.B = B
        self.P = P
        self.location_graph = location_graph
        self.batch_assignments = batch_assignments
        self.W_c = W_c
        self.W_pen = W_pen
        self.W_e = W_e
        self.W_t = W_t
        self.C_n = C_n
        self.C_v = C_v
        self.A = A
        self.T_travel = T_travel
        self.T_setup = T_setup
        self.T_pick = T_pick
        self.S = S if isinstance(S, dict) else {}
        self.T_due_n = T_due_n
        self.M = M
        self.V_p = V_p or {}

    def picker_speed(self, picker: str) -> float:
        """Speed of `picker`; defaults to 1.0 when unset (no-op, matches
        opp_split's migrated-baseline default)."""
        return self.V_p.get(picker, 1.0)

    def evaluate(self, solution) -> float:
        """
        Evaluate objective function:
        W_c * sum(c_b) + W_pen * (W_e * sum(ea_n) + W_t * sum(ta_n))
        """
        batch_times = self.compute_batch_completions(solution)

        earliness_total = 0.0
        tardiness_total = 0.0

        for order in self.N:
            batch = None
            for b in self.B:
                if order in self.batch_assignments[b]:
                    batch = b
                    break

            if batch is None or batch not in batch_times:
                continue

            completion_time = batch_times[batch]
            due_date = self.T_due_n.get(order, float("inf"))

            if completion_time < due_date:
                earliness_total += due_date - completion_time
            else:
                tardiness_total += completion_time - due_date

        recollection_time = sum(batch_times.values()) if batch_times else 0.0
        penalty = self.W_e * earliness_total + self.W_t * tardiness_total

        objective = self.W_c * recollection_time + self.W_pen * penalty

        return objective

    def compute_batch_completions(self, solution) -> Dict[str, float]:
        """
        Compute c_b[b]: the completion time of each batch, given the picker
        it is assigned to (which now also determines its speed) and its
        position within that picker's sequence. Pickers process their
        assigned batches sequentially starting from time zero; different
        pickers work in parallel.
        """
        batch_times: Dict[str, float] = {}

        for picker in self.P:
            cumulative_time = 0.0
            for batch in solution.get_picker_sequence(picker):
                orders = self.batch_assignments.get(batch, set())
                route = solution.get_batch_route(batch)
                exec_time = self._calculate_batch_execution_time(batch, route, orders, picker)
                cumulative_time += exec_time
                batch_times[batch] = cumulative_time

        return batch_times

    def _calculate_batch_execution_time(
        self, batch: str, route: list, orders: Set[str], picker: str
    ) -> float:
        """
        T_exec_pb = T_setup + T_pick * sum(C_n)          [fixed, no speed]
                  + (T_travel * travel_distance + service_time) / V_p[picker]
        """
        return exec_time.T_exec_pb(
            self.location_graph, route, orders, picker,
            self.C_n, self.T_setup, self.T_pick, self.T_travel, self.S, self.V_p,
        )

    def _calculate_route_distance(self, route: list) -> float:
        """Calculate total distance of a route."""
        return exec_time.calculate_route_distance(self.location_graph, route)
