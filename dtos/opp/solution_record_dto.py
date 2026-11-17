from typing import List

from models.base.opp_location_graph import OPPLocationGraph


class SolutionRecordDTO:
    """
    What is needed to re-check a heuristic's solution outside the run that
    produced it: the instance it solved and the solution (the solution_info
    dict the model hands to its Observer).

    The sets are the ones the model actually used, not those of the input
    ModelDTO: the heuristics fall back to P = ["P1"] when a test leaves P
    unset, and the verifier must use that same picker set.

    Holds references only; it is serialized after the test, and only when the
    runner keeps solutions (WRITE_SOLUTIONS, verification/solution_store.py).
    """

    def __init__(
        self,
        model_name: str,
        N: List[str],
        B: List[str],
        P: List[str],
        location_graph: OPPLocationGraph,
        start_time: float,
        params,
        solution_info: dict,
    ):
        self._model_name = model_name
        self._N = N
        self._B = B
        self._P = P
        self._location_graph = location_graph
        self._start_time = start_time
        self._params = params
        self._solution_info = solution_info

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def N(self) -> List[str]:
        return self._N

    @property
    def B(self) -> List[str]:
        return self._B

    @property
    def P(self) -> List[str]:
        return self._P

    @property
    def location_graph(self) -> OPPLocationGraph:
        return self._location_graph

    @property
    def start_time(self) -> float:
        """T_0: the time every picker's first batch starts at."""
        return self._start_time

    @property
    def params(self):
        """The model's solve DTO (SolveHCModelDTO / SolveAcoModelDTO)."""
        return self._params

    @property
    def solution_info(self) -> dict:
        return self._solution_info
