from src.services.llm.base import LLMService, T


class OpenAILLM(LLMService):
    """OpenAI-compatible LLM service for structured output and text generation."""

    def structured_output(self, messages: list[dict], response_model: type[T]) -> T:
        raise NotImplementedError("OpenAILLM will be implemented in Phase 2")

    def generate_text(self, messages: list[dict]) -> str:
        raise NotImplementedError("OpenAILLM will be implemented in Phase 2")
