"""Reusable Mistral service: chat (JSON or text) and vision. Models come from settings."""
import base64
import json
import logging
import re

from app.core.config import settings
from app.utils.validators import AIServiceError

logger = logging.getLogger(__name__)


class MistralService:
    """Thin wrapper around the official mistralai SDK."""

    def __init__(self) -> None:
        self._client = None

    @property
    def client(self):
        if self._client is None:
            if not settings.mistral_api_key:
                raise AIServiceError(
                    "MISTRAL_API_KEY is not configured on the server.", 503
                )
            from mistralai import Mistral
            self._client = Mistral(api_key=settings.mistral_api_key)
        return self._client

    def chat(
        self,
        messages: list[dict],
        *,
        json_mode: bool = False,
        temperature: float = 0.2
    ) -> str:
        """Run a chat completion and return the text."""
        kwargs: dict = {
            "model": settings.mistral_chat_model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            response = self.client.chat.complete(**kwargs)
            content = response.choices[0].message.content
        except AIServiceError:
            raise
        except Exception as exc:
            logger.exception("Mistral chat failed")
            raise AIServiceError(
                f"The AI service request failed ({exc.__class__.__name__})."
            ) from exc
        if isinstance(content, list):
            content = "".join(getattr(part, "text", "") for part in content)
        return (content or "").strip()

    def chat_json(
        self,
        messages: list[dict],
        temperature: float = 0.0
    ) -> dict | list:
        """Chat completion parsed as JSON."""
        text = self.chat(messages, json_mode=True, temperature=temperature)
        text = re.sub(
            r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE
        ).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise AIServiceError(
                "The AI service returned an unreadable response."
            ) from exc

    def ocr(self, content: bytes, mime: str) -> str:
        """Extract bill text using Mistral vision chat."""
        encoded = base64.b64encode(content).decode()

        if mime == "application/pdf":
            content_block = {
                "type": "document_url",
                "document_url": f"data:{mime};base64,{encoded}",
            }
        else:
            content_block = {
                "type": "image_url",
                "image_url": f"data:{mime};base64,{encoded}",
            }

        messages = [
            {
                "role": "user",
                "content": [
                    content_block,
                    {
                        "type": "text",
                        "text": (
                            "Extract all text from this electricity bill exactly "
                            "as printed. Include every number, label and field visible."
                        ),
                    },
                ],
            }
        ]

        try:
            response = self.client.chat.complete(
                model="pixtral-12b-2409",
                messages=messages,
            )
            result = response.choices[0].message.content
            if isinstance(result, list):
                result = "".join(getattr(p, "text", "") for p in result)
            return (result or "").strip()
        except Exception as exc:
            logger.exception("Mistral vision failed")
            raise AIServiceError(
                f"Reading the bill failed ({exc.__class__.__name__})."
            ) from exc


mistral_service = MistralService()