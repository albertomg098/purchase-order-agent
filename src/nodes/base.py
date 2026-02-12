from abc import ABC, abstractmethod
from src.core.workflow_state import POWorkflowState


class BaseNode(ABC):
    """Base class for all workflow nodes.

    Subclasses must set `name` as a class variable (str) and implement `__call__`.
    """

    name: str  # Class variable, set by each subclass (e.g. name = "classify")

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not getattr(cls, 'name', None) and 'Abstract' not in cls.__name__:
            raise TypeError(f"{cls.__name__} must define a 'name' class variable")

    @abstractmethod
    def __call__(self, state: POWorkflowState) -> dict:
        """Execute node logic. Returns a dict that updates the state."""
        ...
