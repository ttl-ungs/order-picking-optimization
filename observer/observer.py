from abc import ABC, abstractmethod

class Observer(ABC):
    """Receives what a Model notifies. Each heuristic has its own
    (utils/output_handler.py)."""

    @abstractmethod
    def update(self, *args, **kwargs):
        pass
