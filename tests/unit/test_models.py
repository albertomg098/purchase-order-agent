"""Unit tests for core models: PurchaseOrder, ExtractionResult, WebhookPayload, LLM responses."""
from datetime import datetime

import pytest
from pydantic import ValidationError

from src.core.purchase_order import PurchaseOrder, ExtractionResult
from src.core.webhook import WebhookPayload
from src.core.llm_responses import ClassificationResult, LLMExtractionResponse, ExtractionData, ExtractionConfidences


# --- PurchaseOrder ---


class TestPurchaseOrder:
    def test_creates_with_valid_data(self):
        po = PurchaseOrder(
            order_id="PO-2025-001",
            customer="Acme Logistics Ltd.",
            pickup_location="Warehouse A, 123 Industrial Rd, Madrid",
            delivery_location="Retail Hub B, 456 Market St, Barcelona",
            delivery_datetime=datetime(2025, 1, 18, 8, 0),
            driver_name="Juan Pérez",
            driver_phone="+34 600 123 456",
        )
        assert po.order_id == "PO-2025-001"
        assert po.customer == "Acme Logistics Ltd."
        assert po.driver_name == "Juan Pérez"

    def test_rejects_missing_required_fields(self):
        with pytest.raises(ValidationError):
            PurchaseOrder(
                order_id="PO-2025-001",
                customer="Acme Logistics Ltd.",
                # missing pickup_location, delivery_location, etc.
            )

    def test_rejects_missing_single_field(self):
        with pytest.raises(ValidationError):
            PurchaseOrder(
                order_id="PO-2025-001",
                customer="Acme Logistics Ltd.",
                pickup_location="Warehouse A",
                delivery_location="Retail Hub B",
                delivery_datetime=datetime(2025, 1, 18, 8, 0),
                driver_name="Juan Pérez",
                # missing driver_phone
            )


# --- ExtractionResult ---


class TestExtractionResult:
    def test_handles_none_data_field(self):
        result = ExtractionResult(data=None)
        assert result.data is None

    def test_default_field_confidences_is_empty_dict(self):
        result = ExtractionResult()
        assert result.field_confidences == {}

    def test_default_raw_ocr_text_is_empty_string(self):
        result = ExtractionResult()
        assert result.raw_ocr_text == ""

    def test_default_warnings_is_empty_list(self):
        result = ExtractionResult()
        assert result.warnings == []

    def test_creates_with_full_data(self):
        po = PurchaseOrder(
            order_id="PO-2025-001",
            customer="Acme",
            pickup_location="A",
            delivery_location="B",
            delivery_datetime=datetime(2025, 1, 18, 8, 0),
            driver_name="Juan",
            driver_phone="+34 600 123 456",
        )
        result = ExtractionResult(
            data=po,
            field_confidences={"order_id": 0.95, "customer": 0.9},
            raw_ocr_text="some ocr text",
            warnings=["low confidence on customer"],
        )
        assert result.data.order_id == "PO-2025-001"
        assert result.field_confidences["order_id"] == 0.95
        assert len(result.warnings) == 1


# --- WebhookPayload ---


class TestWebhookPayload:
    def test_creates_with_minimal_data(self):
        payload = WebhookPayload(
            message_id="msg_001",
            subject="Purchase Order PO-2025-001",
            body="Please find attached the purchase order.",
            sender="orders@acme.com",
            has_attachment=True,
        )
        assert payload.message_id == "msg_001"
        assert payload.has_attachment is True

    def test_default_attachment_ids_is_empty_list(self):
        payload = WebhookPayload(
            message_id="msg_001",
            subject="Test",
            body="Test body",
            sender="test@test.com",
            has_attachment=False,
        )
        assert payload.attachment_ids == []

    def test_default_thread_id_is_none(self):
        payload = WebhookPayload(
            message_id="msg_001",
            subject="Test",
            body="Test body",
            sender="test@test.com",
            has_attachment=False,
        )
        assert payload.thread_id is None

    def test_creates_with_all_fields(self):
        payload = WebhookPayload(
            message_id="msg_001",
            subject="PO-2025-001",
            body="See attached",
            sender="orders@acme.com",
            has_attachment=True,
            attachment_ids=["att_001", "att_002"],
            thread_id="thread_123",
        )
        assert len(payload.attachment_ids) == 2
        assert payload.thread_id == "thread_123"


# --- ClassificationResult ---


class TestClassificationResult:
    def test_creates_valid_po_result(self):
        result = ClassificationResult(
            is_valid_po=True,
            po_id="PO-2025-001",
            reason="Email contains purchase order attachment",
        )
        assert result.is_valid_po is True
        assert result.po_id == "PO-2025-001"
        assert result.reason == "Email contains purchase order attachment"

    def test_creates_non_po_result(self):
        result = ClassificationResult(
            is_valid_po=False,
            reason="Email is a marketing newsletter",
        )
        assert result.is_valid_po is False
        assert result.po_id is None

    def test_po_id_defaults_to_none(self):
        result = ClassificationResult(is_valid_po=False, reason="Not a PO")
        assert result.po_id is None

    def test_requires_is_valid_po_and_reason(self):
        with pytest.raises(ValidationError):
            ClassificationResult()


# --- LLMExtractionResponse ---


class TestLLMExtractionResponse:
    def test_creates_with_full_data(self):
        result = LLMExtractionResponse(
            data=ExtractionData(
                order_id="PO-2025-001",
                customer="Acme Corp",
                pickup_location="Warehouse A",
                delivery_location="Retail Hub B",
                delivery_datetime="2025-01-18T08:00:00",
                driver_name="Juan Pérez",
                driver_phone="+34 600 123 456",
            ),
            field_confidences=ExtractionConfidences(
                order_id=0.95,
                customer=0.90,
                pickup_location=0.85,
                delivery_location=0.80,
                delivery_datetime=0.75,
                driver_name=0.70,
                driver_phone=0.65,
            ),
            warnings=["Low confidence on driver_phone"],
        )
        assert result.data.order_id == "PO-2025-001"
        assert result.field_confidences.order_id == 0.95
        assert len(result.warnings) == 1

    def test_data_allows_none_values(self):
        data = ExtractionData(
            order_id="PO-001", customer=None, pickup_location=None,
            delivery_location=None, delivery_datetime=None,
            driver_name=None, driver_phone=None,
        )
        result = LLMExtractionResponse(
            data=data,
            field_confidences=ExtractionConfidences(
                order_id=0.9, customer=0.1, pickup_location=0.0,
                delivery_location=0.0, delivery_datetime=0.0,
                driver_name=0.0, driver_phone=0.0,
            ),
            warnings=[],
        )
        assert result.data.customer is None

    def test_model_dump_produces_dicts(self):
        data = ExtractionData(
            order_id="PO-001", customer="Acme", pickup_location="A",
            delivery_location="B", delivery_datetime="2025-01-01",
            driver_name="Juan", driver_phone="+34 600",
        )
        dumped = data.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["order_id"] == "PO-001"

    def test_requires_data_and_field_confidences(self):
        with pytest.raises(ValidationError):
            LLMExtractionResponse()
