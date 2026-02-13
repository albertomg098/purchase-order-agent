from src.nodes.base import BaseNode
from src.services.ocr.base import OCRService
from src.services.llm.base import LLMService
from src.services.prompt_store.base import PromptStore
from src.core.workflow_state import POWorkflowState
from src.core.llm_responses import LLMExtractionResponse


class ExtractNode(BaseNode):
    name = "extract"

    def __init__(self, ocr: OCRService, llm: LLMService, prompt_store: PromptStore):
        self.ocr = ocr
        self.llm = llm
        self.prompt_store = prompt_store

    def __call__(self, state: POWorkflowState) -> dict:
        if state.get("final_status") == "error":
            return {"trajectory": state.get("trajectory", []) + ["extract"]}

        if not state.get("is_valid_po"):
            return {"trajectory": state.get("trajectory", []) + ["extract"]}

        try:
            raw_text = self.ocr.extract_text(state.get("pdf_bytes", b""))

            system_prompt = self.prompt_store.get_and_render("extract", "system")
            user_prompt = self.prompt_store.get_and_render("extract", "user", {
                "ocr_text": raw_text,
            })

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            result = self.llm.structured_output(messages, LLMExtractionResponse)

            return {
                "raw_ocr_text": raw_text,
                "extracted_data": result.data,
                "field_confidences": result.field_confidences,
                "extraction_warnings": result.warnings,
                "trajectory": state.get("trajectory", []) + ["extract"],
            }
        except Exception as e:
            return {
                "final_status": "error",
                "error_message": f"ExtractNode failed: {e}",
                "trajectory": state.get("trajectory", []) + ["extract"],
            }
