from typing import Dict, Set

class SolveModelDTO:
    """The parameters of the problem: objective weights, capacities, the
    visit matrix (A_ni), the batch composition (B_nb), times, due dates and the
    big-M. The heuristics' DTOs extend it with their own parameters."""

    def __init__(self):
        self._W_c: float = None
        self._W_pen: float = None
        self._W_e: float = None
        self._W_t: float = None
        self._C_n: dict = None
        self._C_v: float = None
        self._A_ni: dict = None
        self._T_travel: float = None
        self._T_setup: float = None
        self._T_pick: float = None
        self._S: dict = None
        self._T_due_n: dict = None
        self._M: float = None
        self._B_nb: dict = None
        self._seed: int = None

    @property
    def W_c(self) -> float:
        return self._W_c

    @W_c.setter
    def W_c(self, value: float):
        self._W_c = value

    @property
    def W_pen(self) -> float:
        return self._W_pen

    @W_pen.setter
    def W_pen(self, value: float):
        self._W_pen = value

    @property
    def W_e(self) -> float:
        return self._W_e

    @W_e.setter
    def W_e(self, value: float):
        self._W_e = value

    @property
    def W_t(self) -> float:
        return self._W_t

    @W_t.setter
    def W_t(self, value: float):
        self._W_t = value

    @property
    def C_n(self) -> dict:
        return self._C_n

    @C_n.setter
    def C_n(self, value: dict):
        self._C_n = value

    @property
    def C_v(self) -> float:
        return self._C_v

    @C_v.setter
    def C_v(self, value: float):
        self._C_v = value

    @property
    def A(self) -> dict:
        return self._A_ni

    @A.setter
    def A(self, value: dict):
        self._A_ni = value

    @property
    def T_travel(self) -> float:
        return self._T_travel

    @T_travel.setter
    def T_travel(self, value: float):
        self._T_travel = value

    @property
    def T_setup(self) -> float:
        return self._T_setup

    @T_setup.setter
    def T_setup(self, value: float):
        self._T_setup = value

    @property
    def T_pick(self) -> float:
        return self._T_pick

    @T_pick.setter
    def T_pick(self, value: float):
        self._T_pick = value

    @property
    def S(self) -> dict:
        return self._S

    @S.setter
    def S(self, value: dict):
        self._S = value

    @property
    def T_due_n(self) -> dict:
        return self._T_due_n

    @T_due_n.setter
    def T_due_n(self, value: dict):
        self._T_due_n = value

    @property
    def M(self) -> float:
        return self._M

    @M.setter
    def M(self, value: float):
        self._M = value

    @property
    def B_nb(self) -> dict:
        return self._B_nb

    @B_nb.setter
    def B_nb(self, value: dict):
        self._B_nb = value

    @property
    def Seed(self) -> int:
        """
        RNG seed of the heuristics (the exact models have no randomness).
        With None, the default, a run uses the global `random` state and
        cannot be reproduced; pass an int to make it reproducible.
        """
        return self._seed

    @Seed.setter
    def Seed(self, value: int):
        self._seed = value


    def is_batch_assignment_valid(self) -> bool:
        """False if some order is assigned to more than one batch."""
        order_batch_count: Dict[str, int] = {}
        for (order, batch), value in self._B_nb.items():
            if value > 0.5:
                order_batch_count[order] = order_batch_count.get(order, 0) + 1
        return all(count <= 1 for count in order_batch_count.values())

    def is_capacity_valid(self) -> bool:
        """False if some batch exceeds the vehicle capacity."""
        batch_assignments = self.extract_batch_assignments()
        for batch, orders in batch_assignments.items():
            total = sum(self._C_n.get(order, 0) for order in orders)
            if total > self._C_v:
                return False
        return True

    def extract_batch_assignments(self) -> Dict[str, Set[str]]:
        """The orders of each batch, from B_nb."""
        unique_batches = {batch for (order, batch) in self._B_nb.keys()}

        batch_assignments = {b: set() for b in unique_batches}
        for (order, batch), value in self._B_nb.items():
            if value > 0.5:
                batch_assignments[batch].add(order)
        return batch_assignments