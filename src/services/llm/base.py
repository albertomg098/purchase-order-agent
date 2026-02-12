from abc import ABC, abstractmethod
from typing import TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMService(ABC):
    @abstractmethod
    def structured_output(self, messages: list[dict], response_model: type[T]) -> T:
        """Call LLM and parse response into a Pydantic model."""
        ...

    @abstractmethod
    def generate_text(self, messages: list[dict]) -> str:
        """Call LLM and return raw text response."""
        ...
