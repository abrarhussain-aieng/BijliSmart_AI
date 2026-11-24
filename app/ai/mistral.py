"""Multi-provider LLM router (Groq -> Cerebras -> Gemini) and free local OCR service."""
import io
import json
import logging
import re

import numpy as np
from PIL import Image

from app.core.config import settings
from app.utils.validators import AIServiceError

logger = logging.getLogger(__name__)


class LLMRouterService:
    """Routes chat completions through Groq -> Cerebras -> Gemini and extracts text via RapidOCR."""

    def __init__(self) -> None:
        self._groq_client = None
        self._cerebras_client = None
        self._gemini_client = None
        self._ocr_engine = None

    @property
    def groq_client(self):
        if self._groq_client is None and settings.groq_api_key:
            from groq import Groq
            self._groq_client = Groq(api_key=settings.groq_api_key)
        return self._groq_client

    @property
    def cerebras_client(self):
        if self._cerebras_client is None and settings.cerebras_api_key:
            from cerebras.cloud.sdk import Cerebras
            self._cerebras_client = Cerebras(api_key=settings.cerebras_api_key)
        return self._cerebras_client

    @property
    def gemini_client(self):
        if self._gemini_client is None and settings.gemini_api_key:
            from google import genai
            self._gemini_client = genai.Client(api_key=settings.gemini_api_key)
        return self._gemini_client

    @property
    def ocr_engine(self):
        if self._ocr_engine is None:
            from rapidocr_onnxruntime import RapidOCR
            self._ocr_engine = RapidOCR()
        return self._ocr_engine

    @staticmethod
    def _ensure_json_instruction(messages: list[dict], json_mode: bool) -> list[dict]:
        """Groq and Cerebras require the word 'json' in messages when json_object mode is enabled."""
        if not json_mode:
            return messages
        combined = " ".join(str(m.get("content", "")) for m in messages).lower()
        if "json" in combined:
            return messages
        return [{"role": "system", "content": "Respond with valid JSON."}, *messages]

    @staticmethod
    def _clean_output(text: str) -> str:
        """Remove reasoning blocks if a reasoning model includes <think> tags."""
        cleaned = re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL)
        return cleaned.strip()

    def _call_groq(self, messages: list[dict], *, json_mode: bool, temperature: float) -> str:
        if not self.groq_client:
            raise RuntimeError("GROQ_API_KEY not configured")
        prepared = self._ensure_json_instruction(messages, json_mode)
        kwargs: dict = {
            "model": settings.groq_model,
            "messages": prepared,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = self.groq_client.chat.completions.create(**kwargs)
        return self._clean_output(response.choices[0].message.content or "")

    def _call_cerebras(self, messages: list[dict], *, json_mode: bool, temperature: float) -> str:
        if not self.cerebras_client:
            raise RuntimeError("CEREBRAS_API_KEY not configured")
        prepared = self._ensure_json_instruction(messages, json_mode)
        kwargs: dict = {
            "model": settings.cerebras_model,
            "messages": prepared,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = self.cerebras_client.chat.completions.create(**kwargs)
        return self._clean_output(response.choices[0].message.content or "")

    def _call_gemini(self, messages: list[dict], *, json_mode: bool, temperature: float) -> str:
        if not self.gemini_client:
            raise RuntimeError("GEMINI_API_KEY not configured")
        from google.genai import types

        system_parts: list[str] = []
        contents: list[types.Content] = []

        for msg in messages:
            role = msg.get("role", "user")
            text = str(msg.get("content", ""))
            if role == "system":
                system_parts.append(text)
            else:
                gemini_role = "model" if role == "assistant" else "user"
                contents.append(
                    types.Content(
                        role=gemini_role,
                        parts=[types.Part.from_text(text=text)],
                    )
                )

        config_kwargs: dict = {"temperature": temperature}
        if system_parts:
            config_kwargs["system_instruction"] = "\n\n".join(system_parts)
        if json_mode:
            config_kwargs["response_mime_type"] = "application/json"

        response = self.gemini_client.models.generate_content(
            model=settings.gemini_model,
            contents=contents,
            config=types.GenerateContentConfig(**config_kwargs),
        )
        return self._clean_output(response.text or "")

    def chat(
        self,
        messages: list[dict],
        *,
        json_mode: bool = False,
        temperature: float = 0.2,
    ) -> str:
        """Run a chat completion with automatic fallback: Groq -> Cerebras -> Gemini."""
        providers = [
            ("Groq", self._call_groq),
            ("Cerebras", self._call_cerebras),
            ("Gemini", self._call_gemini),
        ]

        errors: list[str] = []
        for name, caller in providers:
            try:
                result = caller(messages, json_mode=json_mode, temperature=temperature)
                if result:
                    return result
                errors.append(f"{name}: empty response")
            except Exception as exc:
                logger.warning("%s chat failed, falling back to next provider: %s", name, exc)
                errors.append(f"{name}: {exc.__class__.__name__}")

        logger.error("All LLM providers failed: %s", "; ".join(errors))
        raise AIServiceError(
            "All configured AI providers (Groq, Cerebras, Gemini) failed to respond.",
            503,
        )

    def chat_json(
        self,
        messages: list[dict],
        temperature: float = 0.0,
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

    def _ocr_with_rapidocr(self, content: bytes, mime: str) -> str:
        """Extract text locally using RapidOCR + pypdfium2 with row/column layout preservation."""
        images: list[Image.Image] = []

        if mime == "application/pdf":
            import pypdfium2 as pdfium

            pdf = pdfium.PdfDocument(content)
            for page_idx in range(min(len(pdf), 5)):
                bitmap = pdf[page_idx].render(scale=2.0)
                images.append(bitmap.to_pil())
        else:
            images.append(Image.open(io.BytesIO(content)))

        extracted_pages: list[str] = []
        for img in images:
            img_array = np.array(img.convert("RGB"))
            result, _ = self.ocr_engine(img_array)
            if not result:
                continue

            # Sort bounding boxes top-to-bottom (15px row tolerance), then left-to-right
            boxes: list[tuple[float, float, str]] = []
            for item in result:
                if len(item) >= 2 and item[1]:
                    coords, text = item[0], item[1].strip()
                    x_min = min(pt[0] for pt in coords)
                    y_min = min(pt[1] for pt in coords)
                    boxes.append((y_min, x_min, text))

            boxes.sort(key=lambda b: (round(b[0] / 15), b[1]))
            rows: list[list[str]] = []
            last_y: float | None = None
            for y_min, _, text in boxes:
                if last_y is None or abs(y_min - last_y) > 15:
                    rows.append([text])
                    last_y = y_min
                else:
                    rows[-1].append(text)

            extracted_pages.append("\n".join(" | ".join(row) for row in rows))

        return "\n\n".join(extracted_pages).strip()

    def _ocr_with_gemini_vision(self, content: bytes, mime: str) -> str:
        """Gemini Vision backup if local RapidOCR cannot read a blurry/skewed bill."""
        if not self.gemini_client:
            return ""
        from google.genai import types

        response = self.gemini_client.models.generate_content(
            model=settings.gemini_model,
            contents=[
                types.Part.from_bytes(data=content, mime_type=mime),
                (
                    "Extract all text from this electricity bill exactly as printed. "
                    "Include every number, label, tariff slab, and field visible."
                ),
            ],
        )
        return (response.text or "").strip()

    def ocr(self, content: bytes, mime: str) -> str:
        """Extract bill text using free RapidOCR first, with optional Gemini Vision backup."""
        text = ""
        try:
            text = self._ocr_with_rapidocr(content, mime)
        except Exception as exc:
            logger.warning("RapidOCR failed (%s); checking Gemini Vision fallback", exc)

        if len(text.strip()) < 20 and settings.ocr_use_gemini_vision_fallback:
            try:
                logger.info("RapidOCR returned sparse text; trying Gemini Vision fallback")
                vision_text = self._ocr_with_gemini_vision(content, mime)
                if len(vision_text.strip()) > len(text.strip()):
                    text = vision_text
            except Exception as exc:
                logger.warning("Gemini Vision OCR fallback failed: %s", exc)

        if not text:
            raise AIServiceError("Reading the bill failed with the configured OCR engines.")

        return text


# Keep both names so existing imports (`from app.ai.mistral import mistral_service`) keep working
llm_service = LLMRouterService()
mistral_service = llm_service