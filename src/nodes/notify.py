from src.nodes.base import BaseNode
from src.services.llm.base import LLMService
from src.services.tools.base import ToolManager
from src.services.prompt_store.base import PromptStore
from src.core.workflow_state import POWorkflowState


class NotifyNode(BaseNode):
    name = "notify"

    def __init__(self, llm: LLMService, tools: ToolManager, prompt_store: PromptStore):
        self.llm = llm
        self.tools = tools
        self.prompt_store = prompt_store

    def __call__(self, state: POWorkflowState) -> dict:
        if state.get("final_status") == "error":
            return {"trajectory": state.get("trajectory", []) + ["notify"]}

        if not state.get("is_valid_po"):
            return {"trajectory": state.get("trajectory", []) + ["notify"]}

        try:
            extracted_data = state.get("extracted_data") or {}
            missing_fields = state.get("missing_fields", [])
            po_id = state.get("po_id", "")
            email_sender = state.get("email_sender", "")

            system_prompt = self.prompt_store.get_and_render("notify", "system")

            if missing_fields:
                missing_desc = ", ".join(missing_fields)
                user_prompt = self.prompt_store.get_and_render("notify", "missing_info", {
                    "order_id": po_id,
                    "missing_fields_description": missing_desc,
                })
                subject = f"Action Required: Missing info for {po_id}"
            else:
                user_prompt = self.prompt_store.get_and_render("notify", "confirmation", {
                    "order_id": po_id,
                    "customer": extracted_data.get("customer", ""),
                    "pickup_location": extracted_data.get("pickup_location", ""),
                    "delivery_location": extracted_data.get("delivery_location", ""),
                    "delivery_datetime": extracted_data.get("delivery_datetime", ""),
                    "driver_name": extracted_data.get("driver_name", ""),
                })
                subject = f"Order Confirmation: {po_id}"

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            email_body = self.llm.generate_text(messages)
            self.tools.send_email(to=email_sender, subject=subject, body=email_body)

            result = {"trajectory": state.get("trajectory", []) + ["notify"]}
            if missing_fields:
                result["missing_info_email_sent"] = True
            else:
                result["confirmation_email_sent"] = True
            return result

        except Exception as e:
            return {
                "final_status": "error",
                "error_message": f"NotifyNode failed: {e}",
                "trajectory": state.get("trajectory", []) + ["notify"],
            }
