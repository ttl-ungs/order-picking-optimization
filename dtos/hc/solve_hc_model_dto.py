from dtos.opp.solve_model_dto import SolveModelDTO


class SolveHCModelDTO(SolveModelDTO):
    """
    Parameters of the Hill Climbing heuristic (OPP-HC): the search budget, the
    picker speeds and the cold-chain limit.

    The execution time per (picker, batch) is the one of the exact models:
        T_exec_pb[p, b] = fixed_time(b) + route_time(b) / V_p[p]
    where fixed_time(b) = T_setup + T_pick * sum(C_n over b's orders)
    does NOT depend on picker speed (setup/picking are manual work, not
    walking), and route_time(b) = T_travel * travel_distance + service_time
    is the part scaled by how fast the picker walks/scans.

    There is no congestion between concurrent pickers, like in the exact models.
    """

    def __init__(self):
        super().__init__()
        self._Max_it: int = 500
        self._Max_imp: int = 30
        self._Max_time: float = 30.0
        self._V_p: dict = {}
        self._T_cold: float = float("inf")

    @property
    def Max_it(self) -> int:
        return self._Max_it

    @Max_it.setter
    def Max_it(self, value: int):
        self._Max_it = value

    @property
    def Max_imp(self) -> int:
        return self._Max_imp

    @Max_imp.setter
    def Max_imp(self, value: int):
        self._Max_imp = value

    @property
    def Max_time(self) -> float:
        """Wall-clock time budget (seconds) for the hill climbing main loop."""
        return self._Max_time

    @Max_time.setter
    def Max_time(self, value: float):
        self._Max_time = value

    @property
    def V_p(self) -> dict:
        """dict {picker: speed}. A picker missing from this dict defaults to
        speed 1.0 (see OPP-HC's _picker_speed), which makes the speed a no-op."""
        return self._V_p

    @V_p.setter
    def V_p(self, value: dict):
        self._V_p = value or {}

    @property
    def T_cold(self) -> float:
        """Cold-chain deadline (seconds): the max allowed T_exec_pb[p, b]
        for a (picker, batch) pair to remain eligible for that assignment.
        Default +inf disables the cold chain entirely (every picker is eligible
        for every batch)."""
        return self._T_cold

    @T_cold.setter
    def T_cold(self, value: float):
        self._T_cold = value
