from abc import ABC, abstractmethod
from typing import Any, Optional
from pydantic import BaseModel, Field


class PromptTemplate(BaseModel):
    """A single prompt template with its metadata."""
    name: str
    template: str
    description: str = ""
    params: list[str] = Field(default_factory=list)


class PromptStore(ABC):
    """Abstract interface for prompt template storage.

    Templates are organized by category (derived from filename) and prompt name.
    For example, a file `classify.yaml` with a `system` prompt would be accessed
    as `get("classify", "system")`.

    Multi-language support:
    - Templates are organized by language in subfolders (e.g., prompts/en/, prompts/es/)
    - The `language` property returns the current language code
    - The `fallback_language` property returns the fallback language code
    - When a template is not found in the current language, it falls back to the fallback language
    """

    @property
    @abstractmethod
    def language(self) -> str:
        """Current language code (ISO 639-1, e.g., 'en', 'es')."""
        ...

    @property
    @abstractmethod
    def fallback_language(self) -> str:
        """Fallback language code when translation is missing."""
        ...

    @abstractmethod
    def get(self, category: str, name: str) -> Optional[PromptTemplate]:
        """Get a prompt template by category and name.

        Args:
            category: Category identifier (typically the YAML filename without extension)
            name: Template identifier within the category (e.g., 'system', 'user')

        Returns:
            PromptTemplate if found, None otherwise
        """
        ...

    @abstractmethod
    def list_categories(self) -> list[str]:
        """List all available categories."""
        ...

    @abstractmethod
    def list_prompts(self, category: str) -> list[str]:
        """List all available prompt names within a category."""
        ...

    @staticmethod
    def render(template: PromptTemplate, params: dict[str, Any]) -> str:
        """Render a template with the given parameters.

        Validates that all required parameters are provided before rendering.

        Args:
            template: The prompt template to render
            params: Dictionary of parameter values

        Returns:
            Rendered template string

        Raises:
            ValueError: If required parameters are missing
        """
        missing = [p for p in template.params if p not in params]
        if missing:
            raise ValueError(
                f"Missing required parameters for template '{template.name}': {missing}"
            )
        return template.template.format(**params)

    def get_and_render(
        self, category: str, name: str, params: Optional[dict[str, Any]] = None
    ) -> str:
        """Get a template and render it in one call.

        Args:
            category: Category identifier
            name: Template identifier within the category
            params: Dictionary of parameter values (defaults to empty dict)

        Returns:
            Rendered template string

        Raises:
            ValueError: If template not found or required parameters missing
        """
        template = self.get(category, name)
        if template is None:
            raise ValueError(f"Prompt template '{category}/{name}' not found")
        return self.render(template, params or {})
