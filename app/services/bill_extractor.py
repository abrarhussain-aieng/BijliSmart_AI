"""Replaceable bill extraction layer: file -> structured JSON."""
from abc import ABC, abstractmethod

from app.ai.mistral import mistral_service
from app.ai.prompts import EXTRACTION_PROMPT
from app.utils.validators import AIServiceError, BillValidationError


class BillExtractor(ABC):
    """Interface so the OCR/vision provider can be swapped without touching the app."""

    @abstractmethod
    def extract(self, content: bytes, mime: str) -> dict:
        """Return raw (unvalidated) bill fields as a dict."""


class MistralBillExtractor(BillExtractor):
    """Mistral OCR for text extraction, then a Mistral chat model for structuring."""

    def extract(self, content: bytes, mime: str) -> dict:
        text = mistral_service.ocr(content, mime)
        if len(text.strip()) < 20:
            raise BillValidationError("Could not read any text from this file. Upload a clearer image or PDF.")
        raw = mistral_service.chat_json(
            [{"role": "system", "content": EXTRACTION_PROMPT}, {"role": "user", "content": text[:12000]}]
        )
        if not isinstance(raw, dict):
            raise AIServiceError("The AI service returned an unexpected bill structure.")
        if raw.get("is_electricity_bill") is False:
            raise BillValidationError("This file does not look like an electricity bill.")
        return raw


def get_bill_extractor() -> BillExtractor:
    """Factory used by the workflow; change the return value to use another provider."""
    return MistralBillExtractor()
