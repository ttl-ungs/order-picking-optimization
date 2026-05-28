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
        self._s: dict = None
        self._due_date: dict = None
        self._M: float = None
        self._x: dict = None
        self._y: dict = None

    @property
    def W_full(self) -> float:
        return self._w1

    @W_full.setter
    def W_full(self, value: float):
        self._w1 = value

    @property
    def W_ea_ta(self) -> float:
        return self._w2

    @W_ea_ta.setter
    def W_ea_ta(self, value: float):
        self._w2 = value

    @property
    def W_ea(self) -> float:
        return self._gamma

    @W_ea.setter
    def W_ea(self, value: float):
        self._gamma = value

    @property
    def W_ta(self) -> float:
        return self._delta

    @W_ta.setter
    def W_ta(self, value: float):
        self._delta = value

    @property
    def C_n(self) -> dict:
        return self._cap_n

    @C_n.setter
    def C_n(self, value: dict):
        self._cap_n = value

    @property
    def C_v(self) -> float:
        return self._cap_vehicle

    @C_v.setter
    def C_v(self, value: float):
        self._cap_vehicle = value

    @property
    def A(self) -> dict:
        return self._a

    @A.setter
    def A(self, value: dict):
        self._a = value

    @property
    def B_time(self) -> float:
        return self._beta_time

    @B_time.setter
    def B_time(self, value: float):
        self._beta_time = value

    @property
    def B_setup(self) -> float:
        return self._beta_setup

    @B_setup.setter
    def B_setup(self, value: float):
        self._beta_setup = value

    @property
    def B_picking(self) -> float:
        return self._beta_picking

    @B_picking.setter
    def B_picking(self, value: float):
        self._beta_picking = value

    @property
    def S(self) -> dict:
        return self._s

    @S.setter
    def S(self, value: dict):
        self._s = value

    @property
    def Dd(self) -> dict:
        return self._due_date

    @Dd.setter
    def Dd(self, value: dict):
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
    def Bn(self) -> dict:
        return self._y

    @Bn.setter
    def Bn(self, value: dict):
        self._y = value
