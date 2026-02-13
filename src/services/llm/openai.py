from openai import OpenAI

from src.services.llm.base import LLMService, T


class OpenAILLM(LLMService):
    """OpenAI-compatible LLM service with structured output support."""

    def __init__(self, model: str = "gpt-4o-mini", base_url: str | None = None, api_key: str | None = None):
        self._model = model
        self._client = OpenAI(base_url=base_url, api_key=api_key)

    def structured_output(self, messages: list[dict], response_model: type[T]) -> T:
        completion = self._client.beta.chat.completions.parse(
            model=self._model,
            messages=messages,
            response_format=response_model,
        )
        result = completion.choices[0].message.parsed
        if result is None:
            raise ValueError(f"LLM refused to respond or failed to parse into {response_model.__name__}")
        return result

    def generate_text(self, messages: list[dict]) -> str:
        completion = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
        )
        return completion.choices[0].message.content or ""
