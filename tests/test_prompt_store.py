"""Unit tests for LocalPromptStore."""
from pathlib import Path

import pytest

from src.services.prompt_store.base import PromptStore, PromptTemplate
from src.services.prompt_store.local import LocalPromptStore

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "prompts"


class TestLocalPromptStore:
    def test_loads_prompt_by_category_and_name(self):
        store = LocalPromptStore(FIXTURES_DIR, language="en")
        template = store.get("classify", "system")
        assert template is not None
        assert template.name == "classify.system"
        assert "email classifier" in template.template

    def test_returns_none_for_missing_prompt(self):
        store = LocalPromptStore(FIXTURES_DIR, language="en")
        assert store.get("classify", "nonexistent") is None

    def test_returns_none_for_missing_category(self):
        store = LocalPromptStore(FIXTURES_DIR, language="en")
        assert store.get("nonexistent", "system") is None

    def test_raises_file_not_found_for_missing_directory(self):
        with pytest.raises(FileNotFoundError):
            LocalPromptStore("/nonexistent/path", language="en")

    def test_list_categories(self):
        store = LocalPromptStore(FIXTURES_DIR, language="en")
        categories = store.list_categories()
        assert "classify" in categories
        assert "notify" in categories

    def test_list_prompts(self):
        store = LocalPromptStore(FIXTURES_DIR, language="en")
        prompts = store.list_prompts("classify")
        assert "system" in prompts
        assert "user" in prompts

    def test_list_prompts_missing_category(self):
        store = LocalPromptStore(FIXTURES_DIR, language="en")
        assert store.list_prompts("nonexistent") == []

    def test_render_substitutes_params(self):
        template = PromptTemplate(
            name="test",
            template="Hello {name}, order {order_id}.",
            params=["name", "order_id"],
        )
        result = PromptStore.render(template, {"name": "Juan", "order_id": "PO-001"})
        assert result == "Hello Juan, order PO-001."

    def test_render_raises_for_missing_required_params(self):
        template = PromptTemplate(
            name="test",
            template="Hello {name}, order {order_id}.",
            params=["name", "order_id"],
        )
        with pytest.raises(ValueError, match="Missing required parameters"):
            PromptStore.render(template, {"name": "Juan"})

    def test_get_and_render(self):
        store = LocalPromptStore(FIXTURES_DIR, language="en")
        result = store.get_and_render("classify", "user", {"subject": "PO-001", "body": "Please process"})
        assert "PO-001" in result
        assert "Please process" in result

    def test_get_and_render_raises_for_missing_template(self):
        store = LocalPromptStore(FIXTURES_DIR, language="en")
        with pytest.raises(ValueError, match="not found"):
            store.get_and_render("nonexistent", "system")

    def test_language_fallback(self):
        store = LocalPromptStore(FIXTURES_DIR, language="es", fallback_language="en")
        # "user" only exists in en/classify.yaml, not in es/classify.yaml
        template = store.get("classify", "user")
        assert template is not None
        assert "Analyze this email" in template.template

    def test_language_primary_takes_precedence(self):
        store = LocalPromptStore(FIXTURES_DIR, language="es", fallback_language="en")
        # "system" exists in both es and en — es should win
        template = store.get("classify", "system")
        assert template is not None
        assert "clasificador de emails" in template.template

    def test_caching(self):
        store = LocalPromptStore(FIXTURES_DIR, language="en")
        # First call loads from file
        store.get("classify", "system")
        assert "en/classify" in store._cache
        # Second call uses cache — verify cache key exists
        store.get("classify", "system")
        assert "en/classify" in store._cache

    def test_prompt_template_has_correct_params(self):
        store = LocalPromptStore(FIXTURES_DIR, language="en")
        template = store.get("classify", "user")
        assert template is not None
        assert "subject" in template.params
        assert "body" in template.params
