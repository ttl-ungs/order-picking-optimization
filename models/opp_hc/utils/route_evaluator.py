"""
Objective function evaluator for opp_hc.

A batch's execution time depends on the picker that runs it: the travel +
service part is divided by the picker's speed (V_p); setup and picking are
not. Batches of the same picker run one after the other; pickers work in
parallel.
"""

from typing import Dict, List, Set


class RouteEvaluator:
    """Evaluates the opp_hc objective function."""

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
        # Batch composition never changes during a run, so the order -> batch
        # lookup is built once.
        self._order_to_batch = {
            order: batch
            for batch, orders in self.batch_assignments.items()
            for order in orders
        }

        # Cache of evaluate_incremental(): _last_* belongs to the last
        # committed solution, _pending_* to the last one scored, which
        # commit() promotes. It assumes the set of batches with orders never
        # changes during a run (only their picker, route and position do).
        self._last_solution = None
        self._last_batch_times: Dict[str, float] = {}
        self._last_earliness_by_batch: Dict[str, float] = {}
        self._last_tardiness_by_batch: Dict[str, float] = {}
        self._last_recollection_time = 0.0
        self._last_earliness_total = 0.0
        self._last_tardiness_total = 0.0
        self._last_objective = 0.0

        self._pending_solution = None
        self._pending_batch_times: Dict[str, float] = {}
        self._pending_earliness_by_batch: Dict[str, float] = {}
        self._pending_tardiness_by_batch: Dict[str, float] = {}
        self._pending_recollection_time = 0.0
        self._pending_earliness_total = 0.0
        self._pending_tardiness_total = 0.0
        self._pending_objective = 0.0

    def picker_speed(self, picker: str) -> float:
        """Speed of `picker` (1.0 when unset)."""
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
            batch = self._order_to_batch.get(order)

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

    def _batch_order_contributions(self, batch: str, completion_time: float):
        """Earliness and tardiness of the orders of one batch (they all share
        its completion time)."""
        earliness = 0.0
        tardiness = 0.0
        for order in self.batch_assignments.get(batch, set()):
            due_date = self.T_due_n.get(order, float("inf"))
            if completion_time < due_date:
                earliness += due_date - completion_time
            else:
                tardiness += completion_time - due_date
        return earliness, tardiness

    def _recompute_picker_suffix(self, picker, new_seq, solution, batch_times, start_idx) -> Set[str]:
        """Recompute the completion times of new_seq[start_idx:] on `picker`,
        given that batch_times is right up to start_idx - 1. Mutates
        batch_times and returns the batches whose value changed."""
        changed = set()
        cumulative = batch_times[new_seq[start_idx - 1]] if start_idx > 0 else 0.0
        for batch in new_seq[start_idx:]:
            orders = self.batch_assignments.get(batch, set())
            route = solution.get_batch_route(batch)
            cumulative += self._calculate_batch_execution_time(batch, route, orders, picker)
            if batch_times.get(batch) != cumulative:
                changed.add(batch)
            batch_times[batch] = cumulative
        return changed

    def _compute_batch_completions_incremental(self, solution):
        """
        Same batch_times as compute_batch_completions(solution), reusing the
        last committed solution's values, plus the set of batches whose
        completion time changed.

        A completion time depends only on the batches that come before on the
        same picker and on their routes. So on each picker everything before
        the first batch whose position or route changed is still valid, and
        only the sequence from there on is recomputed.
        """
        batch_times = dict(self._last_batch_times)
        changed_batches: Set[str] = set()

        for picker in self.P:
            old_seq = self._last_solution.get_picker_sequence(picker)
            new_seq = solution.get_picker_sequence(picker)

            if old_seq == new_seq:
                first_idx = None
                for idx, batch in enumerate(new_seq):
                    if solution.get_batch_route(batch) != self._last_solution.get_batch_route(batch):
                        first_idx = idx
                        break
                if first_idx is None:
                    continue
            else:
                first_idx = 0
                for a, b in zip(old_seq, new_seq):
                    if a != b:
                        break
                    first_idx += 1

            changed_batches |= self._recompute_picker_suffix(picker, new_seq, solution, batch_times, first_idx)

        return batch_times, changed_batches

    def evaluate_incremental(self, solution) -> float:
        """
        Same value as evaluate(solution), computed as a delta from the last
        committed solution: a move changes only a suffix of one or two
        pickers' sequences, so only the orders of those batches are re-priced.

        The committed cache is not touched: solve() calls commit() only when
        it keeps `solution`.
        """
        if self._last_solution is None:
            objective = self.evaluate(solution)
            batch_times = self.compute_batch_completions(solution)
            earliness_by_batch: Dict[str, float] = {}
            tardiness_by_batch: Dict[str, float] = {}
            for batch in batch_times:
                e, t = self._batch_order_contributions(batch, batch_times[batch])
                if e:
                    earliness_by_batch[batch] = e
                if t:
                    tardiness_by_batch[batch] = t

            self._pending_solution = solution
            self._pending_batch_times = batch_times
            self._pending_earliness_by_batch = earliness_by_batch
            self._pending_tardiness_by_batch = tardiness_by_batch
            self._pending_recollection_time = sum(batch_times.values()) if batch_times else 0.0
            self._pending_earliness_total = sum(earliness_by_batch.values())
            self._pending_tardiness_total = sum(tardiness_by_batch.values())
            self._pending_objective = objective
            return objective

        batch_times, changed_batches = self._compute_batch_completions_incremental(solution)

        recollection_time = self._last_recollection_time
        earliness_total = self._last_earliness_total
        tardiness_total = self._last_tardiness_total
        earliness_by_batch = dict(self._last_earliness_by_batch)
        tardiness_by_batch = dict(self._last_tardiness_by_batch)

        for batch in changed_batches:
            recollection_time += batch_times[batch] - self._last_batch_times.get(batch, 0.0)

            earliness_total -= earliness_by_batch.pop(batch, 0.0)
            tardiness_total -= tardiness_by_batch.pop(batch, 0.0)

            new_e, new_t = self._batch_order_contributions(batch, batch_times[batch])
            if new_e:
                earliness_by_batch[batch] = new_e
            if new_t:
                tardiness_by_batch[batch] = new_t
            earliness_total += new_e
            tardiness_total += new_t

        objective = self.W_c * recollection_time + self.W_pen * (
            self.W_e * earliness_total + self.W_t * tardiness_total
        )

        self._pending_solution = solution
        self._pending_batch_times = batch_times
        self._pending_earliness_by_batch = earliness_by_batch
        self._pending_tardiness_by_batch = tardiness_by_batch
        self._pending_recollection_time = recollection_time
        self._pending_earliness_total = earliness_total
        self._pending_tardiness_total = tardiness_total
        self._pending_objective = objective
        return objective

    def commit(self, solution) -> None:
        """Make `solution` the baseline of evaluate_incremental(). Call it
        exactly when solve() accepts `solution`."""
        if self._pending_solution is solution:
            self._last_solution = solution
            self._last_batch_times = self._pending_batch_times
            self._last_earliness_by_batch = self._pending_earliness_by_batch
            self._last_tardiness_by_batch = self._pending_tardiness_by_batch
            self._last_recollection_time = self._pending_recollection_time
            self._last_earliness_total = self._pending_earliness_total
            self._last_tardiness_total = self._pending_tardiness_total
            self._last_objective = self._pending_objective
            return

        # Defensive: `solution` was not the last one scored incrementally.
        self.evaluate_incremental(solution)
        self._last_solution = solution
        self._last_batch_times = self._pending_batch_times
        self._last_earliness_by_batch = self._pending_earliness_by_batch
        self._last_tardiness_by_batch = self._pending_tardiness_by_batch
        self._last_recollection_time = self._pending_recollection_time
        self._last_earliness_total = self._pending_earliness_total
        self._last_tardiness_total = self._pending_tardiness_total
        self._last_objective = self._pending_objective

    def compute_batch_completions(self, solution) -> Dict[str, float]:
        """
        c_b[b]: the completion time of each batch, given its picker (and so
        its speed) and its position in that picker's sequence. Each picker
        runs its batches one after the other from time zero.
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
        setup_time = self.T_setup
        picking_capacity = sum(self.C_n.get(order, 0) for order in orders)
        picking_time = self.T_pick * picking_capacity

        travel_distance = self._calculate_route_distance(route)
        travel_time = self.T_travel * travel_distance
        service_time = sum(self.S.get(loc, 0) for loc in route)

        speed = self.picker_speed(picker)
        return setup_time + picking_time + (travel_time + service_time) / speed

    def _calculate_route_distance(self, route: list) -> float:
        """Calculate total distance of a route."""
        if not route:
            return 0.0

        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()
        total_distance = 0.0

        total_distance += self.location_graph.get_distance(depot, route[0])

        for i in range(len(route) - 1):
            total_distance += self.location_graph.get_distance(route[i], route[i + 1])

        total_distance += self.location_graph.get_distance(route[-1], final)

        return total_distance
