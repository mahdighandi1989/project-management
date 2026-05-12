"""
سرویس Gemini (Google)
پشتیبانی از Gemini 2.5 Pro, Gemini 2.5 Flash, Imagen 3
"""

from typing import Dict, List, Optional, Any, AsyncIterator
import json
from datetime import datetime

from .ai_base import AIServiceBase, Message, AIResponse, AIServiceError
from ..core.models_registry import ModelProvider, get_model
from ..core.config import settings


class GeminiService(AIServiceBase):
    """سرویس Gemini (Google)"""

    provider = ModelProvider.GEMINI
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key or settings.GEMINI_API_KEY)
        if not self.api_key:
            raise AIServiceError("Gemini API key not configured", "gemini")

    def _format_messages(self, messages: List[Message]) -> tuple[Optional[str], List[Dict]]:
        """تبدیل پیام‌ها به فرمت Gemini"""
        system_instruction = None
        contents = []

        for msg in messages:
            if msg.role == "system":
                system_instruction = msg.content
            else:
                role = "user" if msg.role == "user" else "model"
                parts = [{"text": msg.content}]

                if msg.images:
                    for img in msg.images:
                        # تشخیص نوع تصویر از header (PNG: iVBORw0K, JPEG: /9j/)
                        mime_type = "image/png" if img.startswith("iVBORw0K") else "image/jpeg"
                        parts.append({
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": img
                            }
                        })

                # 🆕 رسانهٔ inline با MIME صریح (audio/video/PDF/...) — بدون سنیف
                if getattr(msg, "inline_files", None):
                    for entry in msg.inline_files:
                        try:
                            mime_type, b64 = entry[0], entry[1]
                        except Exception:
                            continue
                        if not mime_type or not b64:
                            continue
                        parts.append({
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": b64,
                            }
                        })

                contents.append({"role": role, "parts": parts})

        return system_instruction, contents

    async def generate(
        self,
        model_id: str,
        messages: List[Message],
        max_tokens: int = 16384,
        temperature: float = 0.7,
        **kwargs
    ) -> AIResponse:
        """تولید پاسخ از مدل Gemini"""
        start_time = datetime.now()

        try:
            model = get_model(model_id)
            if not model:
                raise AIServiceError(f"Model {model_id} not found", "gemini", model_id)

            # برای Imagen، از endpoint تولید تصویر استفاده کن
            if model.is_image_generator:
                return await self._generate_image(model_id, messages[-1].content, **kwargs)

            system_instruction, contents = self._format_messages(messages)

            payload = {
                "contents": contents,
                "generationConfig": {
                    "maxOutputTokens": min(max_tokens, model.max_tokens),
                    "temperature": temperature,
                }
            }

            if system_instruction:
                payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

            # افزودن پارامترهای اختیاری
            if kwargs.get("top_p"):
                payload["generationConfig"]["topP"] = kwargs["top_p"]
            if kwargs.get("top_k"):
                payload["generationConfig"]["topK"] = kwargs["top_k"]

            url = f"{self.BASE_URL}/models/{model_id}:generateContent?key={self.api_key}"

            response = await self.client.post(url, json=payload)

            if response.status_code != 200:
                self.record_error()
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                except (ValueError, KeyError, TypeError):
                    error_msg = response.text
                raise AIServiceError(error_msg, "gemini", model_id, response.status_code)

            data = response.json()
            self.reset_errors()

            latency = int((datetime.now() - start_time).total_seconds() * 1000)

            # استخراج محتوا
            content = ""
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                for part in parts:
                    if "text" in part:
                        content += part["text"]

            # محاسبه توکن‌ها
            usage = data.get("usageMetadata", {})
            tokens_used = usage.get("promptTokenCount", 0) + usage.get("candidatesTokenCount", 0)

            return AIResponse(
                model_id=model_id,
                content=content,
                tokens_used=tokens_used,
                finish_reason=candidates[0].get("finishReason", "") if candidates else "",
                latency_ms=latency,
                metadata={
                    "prompt_tokens": usage.get("promptTokenCount", 0),
                    "completion_tokens": usage.get("candidatesTokenCount", 0),
                }
            )

        except AIServiceError:
            raise
        except Exception as e:
            self.record_error()
            raise AIServiceError(str(e), "gemini", model_id)

    async def _generate_image(
        self,
        model_id: str,
        prompt: str,
        **kwargs
    ) -> AIResponse:
        """تولید تصویر با Imagen"""
        start_time = datetime.now()

        try:
            payload = {
                "instances": [{"prompt": prompt}],
                "parameters": {
                    "sampleCount": kwargs.get("n", 1),
                }
            }

            url = f"{self.BASE_URL}/models/{model_id}:predict?key={self.api_key}"

            response = await self.client.post(url, json=payload)

            if response.status_code != 200:
                self.record_error()
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                except (ValueError, KeyError, TypeError):
                    error_msg = response.text
                raise AIServiceError(error_msg, "gemini", model_id, response.status_code)

            data = response.json()
            self.reset_errors()

            latency = int((datetime.now() - start_time).total_seconds() * 1000)

            # استخراج تصاویر
            images = []
            for prediction in data.get("predictions", []):
                if "bytesBase64Encoded" in prediction:
                    images.append(prediction["bytesBase64Encoded"])

            return AIResponse(
                model_id=model_id,
                content=json.dumps({"images": images}),
                tokens_used=0,
                finish_reason="success",
                latency_ms=latency,
                metadata={"image_count": len(images)}
            )

        except AIServiceError:
            raise
        except Exception as e:
            self.record_error()
            raise AIServiceError(str(e), "gemini", model_id)

    async def generate_stream(
        self,
        model_id: str,
        messages: List[Message],
        max_tokens: int = 16384,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncIterator[str]:
        """تولید پاسخ به صورت streaming"""
        try:
            model = get_model(model_id)
            if not model or model.is_image_generator:
                raise AIServiceError("Streaming not supported for this model", "gemini", model_id)

            system_instruction, contents = self._format_messages(messages)

            payload = {
                "contents": contents,
                "generationConfig": {
                    "maxOutputTokens": min(max_tokens, model.max_tokens),
                    "temperature": temperature,
                }
            }

            if system_instruction:
                payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

            url = f"{self.BASE_URL}/models/{model_id}:streamGenerateContent?key={self.api_key}&alt=sse"

            async with self.client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    self.record_error()
                    raise AIServiceError("Stream error", "gemini", model_id, response.status_code)

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        try:
                            data = json.loads(data_str)
                            candidates = data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                for part in parts:
                                    if "text" in part:
                                        yield part["text"]
                        except json.JSONDecodeError:
                            continue

            self.reset_errors()

        except AIServiceError:
            raise
        except Exception as e:
            self.record_error()
            raise AIServiceError(str(e), "gemini", model_id)
