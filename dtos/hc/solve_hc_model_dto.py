from dtos.opp.solve_model_dto import SolveModelDTO

class SolveHCModelDTO(SolveModelDTO):
    def __init__(self):
        super().__init__()
        self._Max_it: int = 500
        self._Max_imp: int = 30
        self._Max_time: float = 30.0

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