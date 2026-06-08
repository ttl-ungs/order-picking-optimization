from dtos.opp.solve_model_dto import SolveModelDTO

class SolveHCModelDTO(SolveModelDTO):
    def __init__(self):
        super().__init__()
        self._Max_it: int = 500
        self._Max_imp: int = 30

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