"""
Objective function evaluator for opp_hc (OPP v4 + picker speed, no
congestion).

Identical to opp_hc_2's RouteEvaluator, except a batch's execution time now
depends on WHICH picker runs it: the travel+service portion is divided by
that picker's speed (V_p), while setup/picking time stays fixed (same split
as opp_split_stage2_scheduling.zpl's T_exec_pb -- see models/opp_hc/opp_hc.py
header). Batches on the same picker still run sequentially; batches on
different pickers still run in parallel.
"""

from typing import Dict, List, Set


class RouteEvaluator:
    """Evaluates the opp_hc objective function (v4 objective, picker-speed-aware)."""

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
        # batch_assignments is immutable for the lifetime of this evaluator
        # (only picker/route/sequence change during search, never which
        # orders belong to which batch), so the order->batch lookup evaluate()
        # needs can be built once here instead of an O(N*B) scan per call.
        self._order_to_batch = {
            order: batch
            for batch, orders in self.batch_assignments.items()
            for order in orders
        }

        # Incremental evaluate() cache -- see evaluate_incremental()'s
        # docstring. _last_* reflects the last COMMITTED solution
        # (commit()); _pending_* is the tentative result of the most recent
        # evaluate_incremental() call, promoted to _last_* only if that same
        # solution is what gets committed. Assumes the SET of batches with
        # orders assigned to a picker never changes across the whole run
        # (only WHICH picker, route, and sequence position do) -- true for
        # every move opp_hc.py's solve() loop generates.
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
        """This batch's own contribution to evaluate()'s earliness_total/
        tardiness_total (every order in the batch shares the same
        completion_time)."""
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
        """Recompute cumulative completion times for new_seq[start_idx:]
        under `picker`, given batch_times already holds the correct
        cumulative for new_seq[start_idx - 1] (or starts from 0.0 if
        start_idx == 0) -- see evaluate_incremental()'s docstring for why
        everything strictly before start_idx is guaranteed unaffected.
        Mutates batch_times in place; returns the set of batches whose
        value actually changed."""
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
        Same batch_times dict compute_batch_completions(solution) would
        return, computed by reusing the last COMMITTED solution's cached
        values wherever nothing relevant changed, instead of re-walking
        every picker's whole sequence from position 0. Also returns the set
        of batches whose completion time is actually different from the
        cache, so evaluate_incremental() knows which orders' earliness/
        tardiness need recomputing too.

        For a given picker, `new_seq`'s first `first_idx` entries are
        identical (same batches, same order) to `old_seq`'s -- whether
        `old_seq == new_seq` (only a route changed, found by comparing
        routes directly) or `old_seq != new_seq` (a reassignment/swap
        changed membership or order, found via their common prefix length).
        Either way, completion times up to that shared prefix are provably
        identical to what's already cached (they only depend on which
        batches come before them and those batches' own routes, both
        unchanged), so only _recompute_picker_suffix from that point
        onward is needed -- never the whole sequence, and never a picker
        whose sequence AND every one of its batches' routes are unchanged.
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
        Same value evaluate(solution) would return, computed as a delta
        from the last COMMITTED solution (see commit()) instead of
        recomputing every batch's completion time and every order's
        earliness/tardiness from scratch on every call -- a single 2-opt
        move, picker reassignment, or sequence swap only ever changes a
        bounded suffix of one (or two, for a reassignment) pickers'
        sequences (see _compute_batch_completions_incremental), so only
        the orders belonging to batches in that suffix need their
        earliness/tardiness contribution redone; everything else is reused
        untouched.

        Does NOT mutate the committed cache -- see commit(), which solve()
        calls only once it has decided to keep `solution` as the new
        current_solution (a candidate scored here and then rejected must
        not corrupt the cache the NEXT candidate diffs against).
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
        """Make `solution` the baseline evaluate_incremental() diffs
        against from now on. Call this exactly when solve() accepts
        `solution` as the new current_solution -- never for a candidate
        that ends up rejected."""
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

        # solution wasn't the one most recently scored incrementally
        # (shouldn't happen given how solve() uses this class -- defensive
        # fallback so the cache can't silently go stale/incorrect instead).
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
