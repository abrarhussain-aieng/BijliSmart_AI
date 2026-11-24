"""Multi-provider LLM router (Groq -> Cerebras -> Gemini) and cloud-first OCR service."""
import base64
import io
import json
import logging
import os
import re
import time

import numpy as np
from PIL import Image

from app.core.config import settings
from app.utils.validators import AIServiceError

logger = logging.getLogger(__name__)

GEMINI_VISION_FALLBACK_MODELS = (
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-4-hydrogen",
)
GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"


class LLMRouterService:
    """Routes chat completions through Groq -> Cerebras -> Gemini and extracts bill text."""

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

    @staticmethod
    def _prepare_image_bytes(content: bytes, mime: str) -> tuple[bytes, str]:
        """Downscale raster bill images to 1600px JPEG for fast, low-RAM vision API calls."""
        if mime == "application/pdf":
            return content, mime
        img = Image.open(io.BytesIO(content)).convert("RGB")
        img.thumbnail((1600, 1600))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue(), "image/jpeg"

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
        """Extract bill text via Gemini Vision with retry backoff and active Gemini 3/4 fallback models."""
        if not self.gemini_client:
            return ""
        from google.genai import types

        prompt = (
            "Extract all text from this electricity bill exactly as printed. "
            "Preserve table rows and columns, and include every number, label, "
            "tariff slab, and field visible."
        )

        models_to_try = list(
            dict.fromkeys([settings.gemini_model, *GEMINI_VISION_FALLBACK_MODELS])
        )
        last_exc: Exception | None = None

        for model_name in models_to_try:
            for attempt in range(2):
                try:
                    response = self.gemini_client.models.generate_content(
                        model=model_name,
                        contents=[
                            types.Part.from_bytes(data=content, mime_type=mime),
                            prompt,
                        ],
                    )
                    text = (response.text or "").strip()
                    if text:
                        return text
                except Exception as exc:
                    last_exc = exc
                    err_str = str(exc)
                    is_transient = "503" in err_str or "429" in err_str or "UNAVAILABLE" in err_str
                    logger.warning(
                        "Gemini Vision OCR failed on '%s' (attempt %d): %s",
                        model_name,
                        attempt + 1,
                        exc,
                    )
                    if is_transient and attempt == 0:
                        time.sleep(1.5)
                        continue
                    break

        if last_exc:
            raise last_exc
        return ""

    def _ocr_with_groq_vision(self, content: bytes, mime: str) -> str:
        """Secondary cloud Vision OCR fallback using Groq multimodal model if Gemini is busy."""
        if not self.groq_client or mime == "application/pdf":
            return ""
        b64 = base64.b64encode(content).decode("ascii")
        response = self.groq_client.chat.completions.create(
            model=GROQ_VISION_MODEL,
            temperature=0.0,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Extract all text from this electricity bill exactly as printed. "
                                "Preserve table rows and columns, and include every number, label, "
                                "tariff slab, and field visible."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{b64}"},
                        },
                    ],
                }
            ],
        )
        return (response.choices[0].message.content or "").strip()

    def ocr(self, content: bytes, mime: str) -> str:
        """Cloud-first OCR: Gemini Vision (3.8-flash -> 3.5-flash-lite -> 3.1-flash-lite) -> Groq Vision."""
        prepared_content, prepared_mime = self._prepare_image_bytes(content, mime)

        if self.gemini_client:
            try:
                vision_text = self._ocr_with_gemini_vision(prepared_content, prepared_mime)
                if len(vision_text.strip()) >= 20:
                    return vision_text
            except Exception as exc:
                logger.warning("Gemini Vision chain failed, trying Groq Vision: %s", exc)

        if self.groq_client and prepared_mime != "application/pdf":
            try:
                groq_text = self._ocr_with_groq_vision(prepared_content, prepared_mime)
                if len(groq_text.strip()) >= 20:
                    return groq_text
            except Exception as exc:
                logger.warning("Groq Vision OCR fallback failed: %s", exc)

        if os.getenv("ENABLE_LOCAL_OCR", "false").lower() == "true":
            try:
                text = self._ocr_with_rapidocr(content, mime)
                if text:
                    return text
            except Exception as exc:
                logger.warning("RapidOCR failed: %s", exc)

        raise AIServiceError(
            "Bill OCR service is temporarily busy. Please try again in a few seconds.",
            503,
        )


# Keep both names so existing imports (`from app.ai.mistral import mistral_service`) keep working
llm_service = LLMRouterService()
mistral_service = llm_service