"""Unit tests for OpenAILLM service (mocked OpenAI client)."""
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from src.services.llm.openai import OpenAILLM


class DummyModel(BaseModel):
    name: str
    value: int


class TestOpenAILLMConstructor:
    def test_accepts_model_param(self):
        with patch("src.services.llm.openai.OpenAI"):
            llm = OpenAILLM(model="gpt-4o")
            assert llm._model == "gpt-4o"

    def test_defaults_to_gpt4o_mini(self):
        with patch("src.services.llm.openai.OpenAI"):
            llm = OpenAILLM()
            assert llm._model == "gpt-4o-mini"

    def test_passes_base_url_and_api_key_to_client(self):
        with patch("src.services.llm.openai.OpenAI") as mock_cls:
            OpenAILLM(model="gpt-4o", base_url="https://custom.api", api_key="sk-test")
            mock_cls.assert_called_once_with(base_url="https://custom.api", api_key="sk-test")


class TestStructuredOutput:
    def test_calls_parse_with_correct_args(self):
        with patch("src.services.llm.openai.OpenAI") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            parsed_result = DummyModel(name="test", value=42)
            mock_client.beta.chat.completions.parse.return_value.choices = [
                MagicMock(message=MagicMock(parsed=parsed_result))
            ]

            llm = OpenAILLM(model="gpt-4o-mini")
            messages = [{"role": "user", "content": "hello"}]
            result = llm.structured_output(messages, DummyModel)

            mock_client.beta.chat.completions.parse.assert_called_once_with(
                model="gpt-4o-mini",
                messages=messages,
                response_format=DummyModel,
            )
            assert result == parsed_result

    def test_raises_value_error_on_none_parsed(self):
        with patch("src.services.llm.openai.OpenAI") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            mock_client.beta.chat.completions.parse.return_value.choices = [
                MagicMock(message=MagicMock(parsed=None))
            ]

            llm = OpenAILLM()
            with pytest.raises(ValueError, match="DummyModel"):
                llm.structured_output([{"role": "user", "content": "hello"}], DummyModel)


class TestGenerateText:
    def test_calls_create_with_correct_args(self):
        with patch("src.services.llm.openai.OpenAI") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            mock_client.chat.completions.create.return_value.choices = [
                MagicMock(message=MagicMock(content="Generated text"))
            ]

            llm = OpenAILLM(model="gpt-4o-mini")
            messages = [{"role": "user", "content": "hello"}]
            result = llm.generate_text(messages)

            mock_client.chat.completions.create.assert_called_once_with(
                model="gpt-4o-mini",
                messages=messages,
            )
            assert result == "Generated text"

    def test_returns_empty_string_on_none_content(self):
        with patch("src.services.llm.openai.OpenAI") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            mock_client.chat.completions.create.return_value.choices = [
                MagicMock(message=MagicMock(content=None))
            ]

            llm = OpenAILLM()
            result = llm.generate_text([{"role": "user", "content": "hello"}])
            assert result == ""
