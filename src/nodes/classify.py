from src.nodes.base import BaseNode
from src.services.llm.base import LLMService
from src.services.prompt_store.base import PromptStore
from src.core.workflow_state import POWorkflowState
from src.core.llm_responses import ClassificationResult


class ClassifyNode(BaseNode):
    name = "classify"

    def __init__(self, llm: LLMService, prompt_store: PromptStore):
        self.llm = llm
        self.prompt_store = prompt_store

    def __call__(self, state: POWorkflowState) -> dict:
        if state.get("final_status") == "error":
            return {"trajectory": state.get("trajectory", []) + ["classify"]}

        try:
            system_prompt = self.prompt_store.get_and_render("classify", "system")
            user_prompt = self.prompt_store.get_and_render("classify", "user", {
                "subject": state.get("email_subject", ""),
                "sender": state.get("email_sender", ""),
                "body": state.get("email_body", ""),
                "has_attachment": str(state.get("has_attachment", False)),
            })

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            result = self.llm.structured_output(messages, ClassificationResult)

            return {
                "is_valid_po": result.is_valid_po,
                "po_id": result.po_id,
                "classification_reason": result.reason,
                "trajectory": state.get("trajectory", []) + ["classify"],
            }
        except Exception as e:
            return {
                "final_status": "error",
                "error_message": f"ClassifyNode failed: {e}",
                "trajectory": state.get("trajectory", []) + ["classify"],
            }
