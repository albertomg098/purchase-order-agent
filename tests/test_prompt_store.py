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


REAL_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class TestRealPromptTemplates:
    """Validate the actual prompt YAML files in prompts/en/."""

    def test_classify_has_system_and_user(self):
        store = LocalPromptStore(REAL_PROMPTS_DIR, language="en")
        assert store.get("classify", "system") is not None
        assert store.get("classify", "user") is not None

    def test_extract_has_system_and_user(self):
        store = LocalPromptStore(REAL_PROMPTS_DIR, language="en")
        assert store.get("extract", "system") is not None
        assert store.get("extract", "user") is not None

    def test_notify_has_confirmation_missing_info_and_system(self):
        store = LocalPromptStore(REAL_PROMPTS_DIR, language="en")
        assert store.get("notify", "confirmation") is not None
        assert store.get("notify", "missing_info") is not None
        assert store.get("notify", "system") is not None

    def test_classify_user_params(self):
        store = LocalPromptStore(REAL_PROMPTS_DIR, language="en")
        template = store.get("classify", "user")
        assert set(template.params) == {"subject", "sender", "body", "has_attachment"}

    def test_extract_user_params(self):
        store = LocalPromptStore(REAL_PROMPTS_DIR, language="en")
        template = store.get("extract", "user")
        assert template.params == ["ocr_text"]

    def test_notify_confirmation_params(self):
        store = LocalPromptStore(REAL_PROMPTS_DIR, language="en")
        template = store.get("notify", "confirmation")
        expected = {"order_id", "customer", "pickup_location", "delivery_location", "delivery_datetime", "driver_name"}
        assert set(template.params) == expected

    def test_notify_missing_info_params(self):
        store = LocalPromptStore(REAL_PROMPTS_DIR, language="en")
        template = store.get("notify", "missing_info")
        assert set(template.params) == {"order_id", "missing_fields_description"}

    def test_system_prompts_have_no_params(self):
        store = LocalPromptStore(REAL_PROMPTS_DIR, language="en")
        for category in ["classify", "extract", "notify"]:
            template = store.get(category, "system")
            assert template.params == [], f"{category}/system should have no params"
