"""
سرویس Claude (Anthropic)
پشتیبانی از Claude Sonnet 4, Claude 3.5 Sonnet, Claude 3 Haiku
"""

from typing import Dict, List, Optional, Any, AsyncIterator
import json
from datetime import datetime

from .ai_base import AIServiceBase, Message, AIResponse, AIServiceError
from ..core.models_registry import ModelProvider, get_model
from ..core.config import settings


class ClaudeService(AIServiceBase):
    """سرویس Claude (Anthropic)"""

    provider = ModelProvider.CLAUDE
    BASE_URL = "https://api.anthropic.com/v1"
    API_VERSION = "2023-06-01"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key or settings.CLAUDE_API_KEY)
        if not self.api_key:
            raise AIServiceError("Claude API key not configured", "claude")

    def _build_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": self.API_VERSION,
        }

    def _format_messages(self, messages: List[Message]) -> tuple[Optional[str], List[Dict]]:
        """تبدیل پیام‌ها به فرمت Claude (جدا کردن system)"""
        system_prompt = None
        formatted = []

        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
            else:
                # 🆕 (tool-calling) — اگر محتوای ساختاریافتهٔ خام داریم
                # (assistant tool_use یا user tool_result) مستقیماً استفاده کن
                if getattr(msg, "raw_content", None) is not None:
                    formatted.append({"role": msg.role, "content": msg.raw_content})
                elif msg.images:
                    # پیام با تصویر
                    content = [{"type": "text", "text": msg.content}]
                    for img in msg.images:
                        # تشخیص نوع تصویر از header (PNG: iVBORw0K, JPEG: /9j/)
                        media_type = "image/png" if img.startswith("iVBORw0K") else "image/jpeg"
                        content.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": img,
                            }
                        })
                    formatted.append({"role": msg.role, "content": content})
                else:
                    formatted.append({"role": msg.role, "content": msg.content})

        return system_prompt, formatted

    async def generate(
        self,
        model_id: str,
        messages: List[Message],
        max_tokens: int = 16384,
        temperature: float = 0.7,
        **kwargs
    ) -> AIResponse:
        """تولید پاسخ از مدل Claude"""
        start_time = datetime.now()

        try:
            model = get_model(model_id)
            if not model:
                raise AIServiceError(f"Model {model_id} not found", "claude", model_id)

            system_prompt, formatted_messages = self._format_messages(messages)

            # استفاده از model.id به جای model_id برای حل alias
            payload = {
                "model": model.id,  # استفاده از ID واقعی مدل (نه alias)
                "messages": formatted_messages,
                "max_tokens": min(max_tokens, model.max_tokens),
                "temperature": temperature,
            }

            if system_prompt:
                payload["system"] = system_prompt

            # افزودن پارامترهای اختیاری
            if kwargs.get("top_p"):
                payload["top_p"] = kwargs["top_p"]
            if kwargs.get("stop_sequences"):
                payload["stop_sequences"] = kwargs["stop_sequences"]

            # 🆕 (tool-calling/agent-loop) — افزودن tools و tool_choice
            if kwargs.get("tools"):
                payload["tools"] = kwargs["tools"]
                if kwargs.get("tool_choice"):
                    payload["tool_choice"] = kwargs["tool_choice"]

            response = await self.client.post(
                f"{self.BASE_URL}/messages",
                headers=self._build_headers(),
                json=payload
            )

            if response.status_code != 200:
                self.record_error()
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                except (ValueError, KeyError, TypeError):
                    error_msg = response.text
                raise AIServiceError(error_msg, "claude", model_id, response.status_code)

            data = response.json()
            self.reset_errors()

            latency = int((datetime.now() - start_time).total_seconds() * 1000)

            # استخراج محتوا + بلوک‌های tool_use
            content = ""
            _raw_blocks = data.get("content", []) or []
            _tool_calls = []
            for block in _raw_blocks:
                _bt = block.get("type")
                if _bt == "text":
                    content += block.get("text", "")
                elif _bt == "tool_use":
                    _tool_calls.append({
                        "id": block.get("id", ""),
                        "name": block.get("name", ""),
                        "input": block.get("input", {}) or {},
                    })

            return AIResponse(
                model_id=model_id,
                content=content,
                tokens_used=data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0),
                finish_reason=data.get("stop_reason", ""),
                latency_ms=latency,
                metadata={
                    "input_tokens": data.get("usage", {}).get("input_tokens", 0),
                    "output_tokens": data.get("usage", {}).get("output_tokens", 0),
                },
                tool_calls=_tool_calls or None,
                raw_assistant_content=_raw_blocks if _tool_calls else None,
            )

        except AIServiceError:
            raise
        except Exception as e:
            self.record_error()
            raise AIServiceError(str(e), "claude", model_id)

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
            if not model:
                raise AIServiceError(f"Model {model_id} not found", "claude", model_id)

            system_prompt, formatted_messages = self._format_messages(messages)

            # استفاده از model.id به جای model_id برای حل alias
            payload = {
                "model": model.id,  # استفاده از ID واقعی مدل (نه alias)
                "messages": formatted_messages,
                "max_tokens": min(max_tokens, model.max_tokens),
                "temperature": temperature,
                "stream": True,
            }

            if system_prompt:
                payload["system"] = system_prompt

            async with self.client.stream(
                "POST",
                f"{self.BASE_URL}/messages",
                headers=self._build_headers(),
                json=payload
            ) as response:
                if response.status_code != 200:
                    self.record_error()
                    raise AIServiceError("Stream error", "claude", model_id, response.status_code)

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        try:
                            data = json.loads(data_str)
                            if data.get("type") == "content_block_delta":
                                delta = data.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    yield delta.get("text", "")
                        except json.JSONDecodeError:
                            continue

            self.reset_errors()

        except AIServiceError:
            raise
        except Exception as e:
            self.record_error()
            raise AIServiceError(str(e), "claude", model_id)
