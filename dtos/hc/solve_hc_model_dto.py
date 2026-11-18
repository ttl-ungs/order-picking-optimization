from dtos.opp.solve_model_dto import SolveModelDTO


class SolveHCModelDTO(SolveModelDTO):
    """
    Parameters of the Hill Climbing heuristic (OPP-HC): the problem's
    parameters (SolveModelDTO) plus the search budget, the picker speeds and
    the cold-chain limit.
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
        """Maximum number of iterations of the main loop."""
        return self._Max_it

    @Max_it.setter
    def Max_it(self, value: int):
        self._Max_it = value

    @property
    def Max_imp(self) -> int:
        """Iterations without improvement after which the search stops."""
        return self._Max_imp

    @Max_imp.setter
    def Max_imp(self, value: int):
        self._Max_imp = value

    @property
    def Max_time(self) -> float:
        """Wall-clock budget (seconds) of the main loop."""
        return self._Max_time

    @Max_time.setter
    def Max_time(self, value: float):
        self._Max_time = value

    @property
    def V_p(self) -> dict:
        """dict {picker: speed}. A picker missing from it has speed 1.0."""
        return self._V_p

    @V_p.setter
    def V_p(self, value: dict):
        self._V_p = value or {}

    @property
    def T_cold(self) -> float:
        """Cold-chain limit: the largest T_exec_pb[p, b] for which the pair
        (picker, batch) is eligible. The default, +inf, disables it."""
        return self._T_cold

    @T_cold.setter
    def T_cold(self, value: float):
        self._T_cold = value
