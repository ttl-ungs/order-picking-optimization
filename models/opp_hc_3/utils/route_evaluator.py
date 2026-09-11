"""
Objective function evaluator for opp_hc_3 routes.

Identical formula to opp_hc_2/opp_model_v4 (batches on the same picker run
sequentially, different pickers run in parallel), plus one additive term:
the congestion wait time priced against every other picker's schedule (see
models/utils/congestion.py::simulate_route_congestion). A solution with no
node/edge contention between pickers reduces exactly to opp_hc_2's formula.

Unlike opp_aco_3 (which reserves congestion resources incrementally while
each ant probabilistically builds a route), opp_hc_3 already has a complete,
fixed route per batch by the time evaluate() runs (built once up front by
Dijkstra-nearest-neighbor, then perturbed by 2-opt/reassignment/swap moves)
- so congestion is priced as a full simulation over the current solution,
batch by batch, in "round-robin by picker-queue slot" order (same causal
approximation as opp_aco_3, see its module docstring for the rationale).
Every evaluate() call re-simulates from scratch: a move on one batch can
change the timing every other picker's batches "see" it at.
"""

from typing import Dict, List, Set

from models.utils.congestion import CongestionTracker, simulate_route_congestion


class RouteEvaluator:
    """Evaluates the opp_hc_3 objective function for a given route solution."""

    def __init__(
        self,
        N: Set,
        B: Set,
        P: List[str],
        location_graph,
        batch_assignments: Dict[str, Set[str]],
        W_full: float,
        W_ea_ta: float,
        W_ea: float,
        W_ta: float,
        C_n: Dict,
        C_v: float,
        A: Dict,
        B_time: float,
        B_setup: float,
        B_picking: float,
        S: Dict,
        Dd: Dict,
        M: float,
        Min_dwell: float = 0.0,
    ):
        self.N = N
        self.B = B
        self.P = P
        self.location_graph = location_graph
        self.batch_assignments = batch_assignments
        self.W_full = W_full
        self.W_ea_ta = W_ea_ta
        self.W_ea = W_ea
        self.W_ta = W_ta
        self.C_n = C_n
        self.C_v = C_v
        self.A = A
        self.B_time = B_time
        self.B_setup = B_setup
        self.B_picking = B_picking
        self.S = S if isinstance(S, dict) else {}
        self.Dd = Dd
        self.M = M
        self.Min_dwell = Min_dwell

    def evaluate(self, solution) -> float:
        """
        Evaluate objective function:
        W_full * sum(v_b) + W_ea_ta * (W_ea * sum(ea_n) + W_ta * sum(ta_n))
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
            due_date = self.Dd.get(order, float("inf"))

            if completion_time < due_date:
                earliness_total += due_date - completion_time
            else:
                tardiness_total += completion_time - due_date

        recollection_time = sum(batch_times.values()) if batch_times else 0.0
        penalty = self.W_ea * earliness_total + self.W_ta * tardiness_total

        objective = self.W_full * recollection_time + self.W_ea_ta * penalty

        return objective

    def evaluate_congestion(self, solution) -> float:
        """Total wait time incurred by the current solution (diagnostic-only, not used to accept/reject moves)."""
        return solution.total_congestion_wait()

    def evaluate_congestion_collisions(self, solution) -> int:
        """
        How many times a node/edge reservation had to wait for another
        picker in the current solution (a FREQUENCY metric -- how OFTEN
        two pickers actually collided -- distinct from evaluate_congestion,
        which is the accumulated TIME lost). Diagnostic-only, same as
        evaluate_congestion.
        """
        return solution.get_total_collisions()

    def compute_batch_completions(self, solution) -> Dict[str, float]:
        """
        Compute v_b[b]: the completion time of each batch, given the picker
        it is assigned to and its position within that picker's sequence.
        Pickers process their assigned batches sequentially starting from
        time zero; different pickers work in parallel, but their routes may
        still contend for the same node/edge (congestion), priced here.

        Batches are walked in "round-robin by picker-queue slot" order
        (slot 0 of every picker, then slot 1, ...) so a batch always prices
        its congestion against the reservations already made by batches
        that, given the fixed queues, run at or before its own start time.
        """
        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()

        tracker = CongestionTracker(min_dwell=self.Min_dwell)
        picker_cumulative: Dict[str, float] = {p: 0.0 for p in self.P}
        batch_times: Dict[str, float] = {}

        max_slots = max((len(solution.get_picker_sequence(p)) for p in self.P), default=0)

        for slot in range(max_slots):
            for picker in self.P:
                sequence = solution.get_picker_sequence(picker)
                if slot >= len(sequence):
                    continue

                batch = sequence[slot]
                orders = self.batch_assignments.get(batch, set())
                route = solution.get_batch_route(batch)

                base_exec_time = self._calculate_batch_execution_time(batch, route, orders)

                congestion_wait = 0.0
                if route:
                    full_route = [depot] + route + [final]
                    _, congestion_wait = simulate_route_congestion(
                        self.location_graph,
                        full_route,
                        picker,
                        picker_cumulative[picker],
                        self.B_time,
                        self.S,
                        tracker,
                        depot,
                        final,
                    )

                exec_time = base_exec_time + congestion_wait
                picker_cumulative[picker] += exec_time
                batch_times[batch] = picker_cumulative[picker]
                solution.set_batch_congestion_wait(batch, congestion_wait)

        solution.set_total_collisions(tracker.total_collisions())
        return batch_times

    def _calculate_batch_execution_time(self, batch: str, route: list, orders: Set[str]) -> float:
        """
        Calculate execution time for a batch route, EXCLUDING congestion wait
        (added separately by the caller, since it depends on the other
        pickers' schedules, not just this batch's own route):
        t_exec = B_setup + B_picking * sum(C_n) + B_time * travel_distance + service_time
        """
        setup_time = self.B_setup

        picking_capacity = sum(self.C_n.get(order, 0) for order in orders)
        picking_time = self.B_picking * picking_capacity

        travel_distance = self._calculate_route_distance(route)
        travel_time = self.B_time * travel_distance

        service_time = sum(self.S.get(loc, 0) for loc in route)

        return setup_time + picking_time + travel_time + service_time

    def _calculate_route_distance(self, route: list) -> float:
        """Calculate total distance of a route."""
        if not route:
            return 0.0

        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()
        total_distance = 0.0

        if route:
            total_distance += self.location_graph.get_distance(depot, route[0])

        for i in range(len(route) - 1):
            total_distance += self.location_graph.get_distance(route[i], route[i + 1])

        if route:
            total_distance += self.location_graph.get_distance(route[-1], final)

        return total_distance
