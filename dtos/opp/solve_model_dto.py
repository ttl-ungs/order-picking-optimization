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
        self._due_date: dict = None
        self._M: float = None
        self._x: dict = None
        self._y: dict = None

    @property
    def w1(self) -> float:
        return self._w1

    @w1.setter
    def w1(self, value: float):
        self._w1 = value

    @property
    def w2(self) -> float:
        return self._w2

    @w2.setter
    def w2(self, value: float):
        self._w2 = value

    @property
    def gamma(self) -> float:
        return self._gamma

    @gamma.setter
    def gamma(self, value: float):
        self._gamma = value

    @property
    def delta(self) -> float:
        return self._delta

    @delta.setter
    def delta(self, value: float):
        self._delta = value

    @property
    def cap_n(self) -> dict:
        return self._cap_n

    @cap_n.setter
    def cap_n(self, value: dict):
        self._cap_n = value

    @property
    def cap_vehicle(self) -> float:
        return self._cap_vehicle

    @cap_vehicle.setter
    def cap_vehicle(self, value: float):
        self._cap_vehicle = value

    @property
    def a(self) -> dict:
        return self._a

    @a.setter
    def a(self, value: dict):
        self._a = value

    @property
    def beta_time(self) -> float:
        return self._beta_time

    @beta_time.setter
    def beta_time(self, value: float):
        self._beta_time = value

    @property
    def beta_setup(self) -> float:
        return self._beta_setup

    @beta_setup.setter
    def beta_setup(self, value: float):
        self._beta_setup = value

    @property
    def beta_picking(self) -> float:
        return self._beta_picking

    @beta_picking.setter
    def beta_picking(self, value: float):
        self._beta_picking = value

    @property
    def due_date(self) -> dict:
        return self._due_date

    @due_date.setter
    def due_date(self, value: dict):
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
    def y(self) -> dict:
        return self._y

    @y.setter
    def y(self, value: dict):
        self._y = value

