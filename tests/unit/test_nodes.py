"""Unit tests for BaseNode ABC and all node stubs."""
import pytest

from src.nodes.base import BaseNode
from src.nodes.classify import ClassifyNode
from src.nodes.extract import ExtractNode
from src.nodes.validate import ValidateNode
from src.nodes.track import TrackNode
from src.nodes.notify import NotifyNode
from src.nodes.report import ReportNode

from src.services.llm.base import LLMService
from src.services.ocr.base import OCRService
from src.services.tools.base import ToolManager
from src.services.prompt_store.base import PromptStore


# --- Fake services for constructor tests ---

class FakeLLM(LLMService):
    def structured_output(self, messages, response_model):
        pass

    def generate_text(self, messages):
        return ""


class FakeOCR(OCRService):
    def extract_text(self, pdf_bytes):
        return ""


class FakeToolManager(ToolManager):
    def send_email(self, to, subject, body, thread_id=None):
        return {"status": "ok"}

    def append_sheet_row(self, spreadsheet_id, values):
        return {"status": "ok"}

    def get_email_attachment(self, message_id, attachment_id):
        return b""


class FakePromptStore(PromptStore):
    @property
    def language(self):
        return "en"

    @property
    def fallback_language(self):
        return "en"

    def get(self, category, name):
        return None

    def list_categories(self):
        return []

    def list_prompts(self, category):
        return []


# --- BaseNode ABC ---

class TestBaseNode:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            BaseNode()

    def test_subclass_without_name_raises_type_error(self):
        with pytest.raises(TypeError, match="must define a 'name' class variable"):
            class BadNode(BaseNode):
                def __call__(self, state):
                    return {}


# --- Node stubs ---

class TestClassifyNode:
    def test_has_correct_name(self):
        assert ClassifyNode.name == "classify"

    def test_accepts_constructor_args(self):
        node = ClassifyNode(llm=FakeLLM(), prompt_store=FakePromptStore())
        assert node.llm is not None
        assert node.prompt_store is not None

    def test_call_raises_not_implemented(self):
        node = ClassifyNode(llm=FakeLLM(), prompt_store=FakePromptStore())
        with pytest.raises(NotImplementedError):
            node({})


class TestExtractNode:
    def test_has_correct_name(self):
        assert ExtractNode.name == "extract"

    def test_accepts_constructor_args(self):
        node = ExtractNode(ocr=FakeOCR(), llm=FakeLLM(), prompt_store=FakePromptStore())
        assert node.ocr is not None
        assert node.llm is not None
        assert node.prompt_store is not None

    def test_call_raises_not_implemented(self):
        node = ExtractNode(ocr=FakeOCR(), llm=FakeLLM(), prompt_store=FakePromptStore())
        with pytest.raises(NotImplementedError):
            node({})


class TestValidateNode:
    def test_has_correct_name(self):
        assert ValidateNode.name == "validate"

    def test_accepts_no_args(self):
        node = ValidateNode()
        assert node is not None

    def test_call_raises_not_implemented(self):
        node = ValidateNode()
        with pytest.raises(NotImplementedError):
            node({})


class TestTrackNode:
    def test_has_correct_name(self):
        assert TrackNode.name == "track"

    def test_accepts_constructor_args(self):
        node = TrackNode(tools=FakeToolManager(), spreadsheet_id="sheet_123")
        assert node.tools is not None
        assert node.spreadsheet_id == "sheet_123"

    def test_call_raises_not_implemented(self):
        node = TrackNode(tools=FakeToolManager(), spreadsheet_id="sheet_123")
        with pytest.raises(NotImplementedError):
            node({})


class TestNotifyNode:
    def test_has_correct_name(self):
        assert NotifyNode.name == "notify"

    def test_accepts_constructor_args(self):
        node = NotifyNode(llm=FakeLLM(), tools=FakeToolManager(), prompt_store=FakePromptStore())
        assert node.llm is not None
        assert node.tools is not None
        assert node.prompt_store is not None

    def test_call_raises_not_implemented(self):
        node = NotifyNode(llm=FakeLLM(), tools=FakeToolManager(), prompt_store=FakePromptStore())
        with pytest.raises(NotImplementedError):
            node({})


class TestReportNode:
    def test_has_correct_name(self):
        assert ReportNode.name == "report"

    def test_accepts_no_args(self):
        node = ReportNode()
        assert node is not None

    def test_call_raises_not_implemented(self):
        node = ReportNode()
        with pytest.raises(NotImplementedError):
            node({})
