"""WorkflowBuilder: wires services and nodes based on AppConfig."""
from src.config import AppConfig
from src.services.ocr.base import OCRService
from src.services.ocr.tesseract import TesseractOCR
from src.services.llm.base import LLMService
from src.services.llm.openai import OpenAILLM
from src.services.tools.base import ToolManager
from src.services.tools.mock import MockToolManager
from src.services.prompt_store.base import PromptStore
from src.services.prompt_store.local import LocalPromptStore
from src.nodes.classify import ClassifyNode
from src.nodes.extract import ExtractNode
from src.nodes.validate import ValidateNode
from src.nodes.track import TrackNode
from src.nodes.notify import NotifyNode
from src.nodes.report import ReportNode
from src.workflow import build_graph


class WorkflowBuilder:
    """Builds the PO workflow graph by wiring services and nodes from config."""

    def __init__(self, config: AppConfig):
        self.config = config

        # Instantiate services
        self._ocr = self._build_ocr()
        self._llm = self._build_llm()
        self._tool_manager = self._build_tool_manager()
        self._prompt_store = self._build_prompt_store()

    @property
    def tool_manager(self) -> ToolManager:
        return self._tool_manager

    @property
    def prompt_store(self) -> PromptStore:
        return self._prompt_store

    def build(self):
        """Build and return a compiled LangGraph workflow."""
        nodes = {
            "classify": ClassifyNode(llm=self._llm, prompt_store=self._prompt_store),
            "extract": ExtractNode(ocr=self._ocr, llm=self._llm, prompt_store=self._prompt_store),
            "validate": ValidateNode(self.config.confidence_threshold),
            "track": TrackNode(tools=self._tool_manager, spreadsheet_id=self.config.spreadsheet_id),
            "notify": NotifyNode(llm=self._llm, tools=self._tool_manager, prompt_store=self._prompt_store),
            "report": ReportNode(),
        }
        return build_graph(nodes)

    def _build_ocr(self) -> OCRService:
        if self.config.ocr_engine == "tesseract":
            return TesseractOCR()
        raise ValueError(f"Unknown OCR engine: {self.config.ocr_engine}")

    def _build_llm(self) -> LLMService:
        if self.config.llm_provider == "openai":
            return OpenAILLM(
                model=self.config.llm_model,
                api_key=self.config.openai_api_key,
                base_url=self.config.llm_base_url,
            )
        raise ValueError(f"Unknown LLM provider: {self.config.llm_provider}")

    def _build_tool_manager(self) -> ToolManager:
        if self.config.tool_manager == "mock":
            return MockToolManager()
        if self.config.tool_manager == "composio":
            raise NotImplementedError("ComposioToolManager is Phase 3")
        raise ValueError(f"Unknown tool manager: {self.config.tool_manager}")

    def _build_prompt_store(self) -> PromptStore:
        if self.config.prompt_store == "local":
            return LocalPromptStore(
                prompts_dir=self.config.prompts_dir,
                language=self.config.prompt_language,
                fallback_language=self.config.prompt_fallback_language,
            )
        raise ValueError(f"Unknown prompt store: {self.config.prompt_store}")
