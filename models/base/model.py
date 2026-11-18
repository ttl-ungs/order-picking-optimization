from abc import ABC, abstractmethod
from observer.observer import Observer


class Model(ABC):
    """Base class of the heuristic solvers: the subject of the Observer
    pattern. A solver computes and calls notify(); its observers (the output
    handlers) print or store the result."""

    # Observer factories every new instance of the class starts attached to
    # (see attach_to_new_instances). Empty unless a caller registers one.
    _observers_for_new_instances = ()

    def __init__(self):
        self._observers = [make_observer() for make_observer in type(self)._observers_for_new_instances]

    @classmethod
    def attach_to_new_instances(cls, make_observer):
        """Attach an observer made by `make_observer()` to every instance of
        `cls` created from now on.

        For callers that do not create the solver themselves, such as the
        test runner, whose tests build their own. Registered on `cls` only:
        other Model subclasses are not affected."""
        cls._observers_for_new_instances = (*cls._observers_for_new_instances, make_observer)

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
