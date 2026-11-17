from abc import ABC, abstractmethod
from observer.observer import Observer


class Model(ABC):
    """Base class of the heuristic solvers: the subject of the Observer
    pattern. A solver computes and calls notify(); its observers (the output
    handlers) print or store the result."""

    def __init__(self):
        self._observers = []

    def attach(self, observer: Observer):
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: Observer):
        self._observers.remove(observer)

    def notify(self, *args, **kwargs):
        for observer in self._observers:
            observer.update(*args, **kwargs)

    @abstractmethod
    def solve(self):
        pass
