from typing import Dict, Set

class SolveModelDTO:
    def __init__(self):
        self._w1: float = None
        self._w2: float = None
        self._gamma: float = None
        self._delta: float = None
        self._cap_n: dict = None
        self._cap_vehicle: float = None
        self._a: dict = None
        self._beta_time: float = None
        self._beta_setup: float = None
        self._beta_picking: float = None
        self._s: dict = None
        self._due_date: dict = None
        self._M: float = None
        self._x: dict = None
        self._y: dict = None
        self._seed: int = None

    @property
    def W_full(self) -> float:
        return self._w1

    @W_full.setter
    def W_full(self, value: float):
        self._w1 = value

    @property
    def W_ea_ta(self) -> float:
        return self._w2

    @W_ea_ta.setter
    def W_ea_ta(self, value: float):
        self._w2 = value

    @property
    def W_ea(self) -> float:
        return self._gamma

    @W_ea.setter
    def W_ea(self, value: float):
        self._gamma = value

    @property
    def W_ta(self) -> float:
        return self._delta

    @W_ta.setter
    def W_ta(self, value: float):
        self._delta = value

    @property
    def C_n(self) -> dict:
        return self._cap_n

    @C_n.setter
    def C_n(self, value: dict):
        self._cap_n = value

    @property
    def C_v(self) -> float:
        return self._cap_vehicle

    @C_v.setter
    def C_v(self, value: float):
        self._cap_vehicle = value

    @property
    def A(self) -> dict:
        return self._a

    @A.setter
    def A(self, value: dict):
        self._a = value

    @property
    def B_time(self) -> float:
        return self._beta_time

    @B_time.setter
    def B_time(self, value: float):
        self._beta_time = value

    @property
    def B_setup(self) -> float:
        return self._beta_setup

    @B_setup.setter
    def B_setup(self, value: float):
        self._beta_setup = value

    @property
    def B_picking(self) -> float:
        return self._beta_picking

    @B_picking.setter
    def B_picking(self, value: float):
        self._beta_picking = value

    @property
    def S(self) -> dict:
        return self._s

    @S.setter
    def S(self, value: dict):
        self._s = value

    @property
    def Dd(self) -> dict:
        return self._due_date

    @Dd.setter
    def Dd(self, value: dict):
        self._due_date = value

    @property
    def M(self) -> float:
        return self._M

    @M.setter
    def M(self, value: float):
        self._M = value

    @property
    def x(self) -> dict:
        return self._x

    @x.setter
    def x(self, value: dict):
        self._x = value

    @property
    def Bn(self) -> dict:
        return self._y

    @Bn.setter
    def Bn(self, value: dict):
        self._y = value

    @property
    def Seed(self) -> int:
        """
        Optional RNG seed for reproducible heuristic runs (opp_hc_2/opp_hc_3/
        opp_aco_2/opp_aco_3 -- opp_v4 is exact, no randomness involved).
        Default None preserves the previous (unseeded, non-reproducible)
        behavior: every solve() call reads/advances the shared global
        `random` module state, so two runs of the same instance with the
        same hyperparameters can produce different search trajectories and
        final objective values with no way to reproduce a specific one.
        Added 2026-08-28 (code audit finding) -- pass an explicit int here
        to make a run's randomness reproducible for debugging or for
        reporting a specific result.
        """
        return self._seed

    @Seed.setter
    def Seed(self, value: int):
        self._seed = value


    def is_batch_assignment_valid(self) -> bool:
        # Return False if any order is assigned to more than one batch
        order_batch_count: Dict[str, int] = {}
        for (order, batch), value in self._y.items():
            if value > 0.5:
                order_batch_count[order] = order_batch_count.get(order, 0) + 1
        return all(count <= 1 for count in order_batch_count.values())

    def is_capacity_valid(self) -> bool:
        # Return False if any batch exceeds the vehicle capacity constraint
        batch_assignments = self.extract_batch_assignments()
        for batch, orders in batch_assignments.items():
            total = sum(self._cap_n.get(order, 0) for order in orders)
            if total > self._cap_vehicle:
                return False
        return True

    def extract_batch_assignments(self) -> Dict[str, Set[str]]:
        # Extract which orders belong to each batch from Bn parameter
        unique_batches = {batch for (order, batch) in self._y.keys()}

        batch_assignments = {b: set() for b in unique_batches}
        for (order, batch), value in self._y.items():
            if value > 0.5:  # Treat as binary
                batch_assignments[batch].add(order)
        return batch_assignments