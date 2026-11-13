from typing import List

from models.base.opp_location_graph import OPPLocationGraph


class SolutionRecordDTO:
    """
    Everything needed to re-check a heuristic's solution outside the run
    that produced it: the instance it ACTUALLY solved and the solution
    itself (the solution_info dict the model already hands to its Observer).

    The sets are the model's effective ones, not the input ModelDTO's: e.g.
    opp_hc/opp_aco fall back to P = ["P1"] when a test leaves P unset,
    and the verifier must check against that same picker set.

    Holds references only -- nothing is copied or serialized while the model
    is solving, so attaching one to a SolveResult costs nothing measurable.
    Serialization happens after the test finished, and only when the runner
    was asked to keep solutions (WRITE_SOLUTIONS, see
    verification/solution_store.py).
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
