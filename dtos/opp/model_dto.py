from models.base.opp_location_graph import OPPLocationGraph


class ModelDTO:
    """The structure of an instance: orders (N), batches (B), pickers (P),
    the location graph and the time the pickers start at."""

    def __init__(self):
        self._N: set = None
        self._location_graph: OPPLocationGraph = None
        self._H: set = None
        self._K: set = None
        self._P: set = None
        self._B: set = None
        self._start_time: float = None

    @property
    def N(self) -> set:
        return self._N

    @N.setter
    def N(self, value: set):
        self._N = value

    @property
    def location_graph(self) -> OPPLocationGraph:
        return self._location_graph

    @location_graph.setter
    def location_graph(self, value: OPPLocationGraph):
        self._location_graph = value

    @property
    def H(self) -> set:
        return self._H

    @H.setter
    def H(self, value: set):
        self._H = value

    @property
    def K(self) -> set:
        return self._K

    @K.setter
    def K(self, value: set):
        self._K = value

    @property
    def P(self) -> set:
        return self._P

    @P.setter
    def P(self, value: set):
        self._P = value

    @property
    def B(self) -> set:
        return self._B

    @B.setter
    def B(self, value: set):
        self._B = value

    @property
    def start_time(self) -> float:
        return self._start_time

    @start_time.setter
    def start_time(self, value: float):
        self._start_time = value
