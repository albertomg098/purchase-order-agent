import yaml
from pathlib import Path
from typing import Optional
from src.services.prompt_store.base import PromptStore, PromptTemplate


class LocalPromptStore(PromptStore):
    """Loads prompts from local YAML files organized by language.

    Directory structure:
        prompts/
        ├── en/
        │   ├── classify.yaml      # category: "classify"
        │   ├── extract.yaml       # category: "extract"
        │   └── notify.yaml        # category: "notify"
        └── es/
            └── ...

    YAML format per file (each key is a prompt name within the category):
        system:
            template: |
                You are an email classifier...
            description: System prompt for email classification
            params: []
        user:
            template: |
                Analyze this email:
                Subject: {subject}
                Body: {body}
            description: User prompt template
            params:
                - subject
                - body
    """

    def __init__(self, prompts_dir: str | Path, language: str = "en", fallback_language: str = "en"):
        self._base_dir = Path(prompts_dir)
        self._language = language
        self._fallback_language = fallback_language
        self._cache: dict[str, dict] = {}

        if not self._base_dir.exists():
            raise FileNotFoundError(f"Prompts directory not found: {self._base_dir}")

    @property
    def language(self) -> str:
        return self._language

    @property
    def fallback_language(self) -> str:
        return self._fallback_language

    def get(self, category: str, name: str) -> Optional[PromptTemplate]:
        # Try current language first, then fallback
        for lang in [self._language, self._fallback_language]:
            data = self._load_category(category, lang)
            if data and name in data:
                entry = data[name]
                return PromptTemplate(
                    name=f"{category}.{name}",
                    template=entry["template"],
                    description=entry.get("description", ""),
                    params=entry.get("params", []),
                )
        return None

    def list_categories(self) -> list[str]:
        categories = set()
        for lang in [self._language, self._fallback_language]:
            lang_dir = self._base_dir / lang
            if lang_dir.exists():
                for path in lang_dir.glob("*.yaml"):
                    categories.add(path.stem)
        return sorted(categories)

    def list_prompts(self, category: str) -> list[str]:
        for lang in [self._language, self._fallback_language]:
            data = self._load_category(category, lang)
            if data:
                return list(data.keys())
        return []

    def _load_category(self, category: str, lang: str) -> Optional[dict]:
        cache_key = f"{lang}/{category}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        path = self._base_dir / lang / f"{category}.yaml"
        if not path.exists():
            return None

        with open(path) as f:
            data = yaml.safe_load(f)

        self._cache[cache_key] = data
        return data
