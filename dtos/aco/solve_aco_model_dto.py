from dtos import SolveModelDTO


class SolveAcoModelDTO(SolveModelDTO):
    def __init__(self):
        super().__init__()
        self._A = 15
        self._Max_it = 60
        self._Alpha = 1.0       # Importancia de la feromona acumulada
        self._Beta = 2.5        # Importancia de la visibilidad (distancia inversa)
        self._E = 0.15
        self._Q = 100.0

    def A(self) -> float:
        return self._A

    def A(self, value: float):
        self._A = value

    def Max_it(self) -> float:
        return self._Max_it

    def Max_it(self, value: float):
        self._Max_it = value

    def Alpha(self) -> float:
        return self._Alpha

    def Alpha(self, value: float):
        self._Alpha = value

    def Beta(self) -> float:
        return self._Beta

    def Beta(self, value: float):
        self._Beta = value

    def E(self) -> float:
        return self._E

    def E(self, value: float):
        self._E = value

    def Q(self) -> float:
        return self._Q

    def Q(self, value: float):
        self._Q = value