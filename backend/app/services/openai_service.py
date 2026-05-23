"""
سرویس OpenAI
پشتیبانی از GPT-4o, GPT-4, GPT-3.5 و DALL-E
"""

from typing import Dict, List, Optional, Any, AsyncIterator
import json
from datetime import datetime

from .ai_base import AIServiceBase, Message, AIResponse, AIServiceError
from ..core.models_registry import ModelProvider, get_model
from ..core.config import settings


class OpenAIService(AIServiceBase):
    """سرویس OpenAI"""

    provider = ModelProvider.OPENAI
    BASE_URL = "https://api.openai.com/v1"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key or settings.OPENAI_API_KEY)
        if not self.api_key:
            raise AIServiceError("OpenAI API key not configured", "openai")

    def _build_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def _format_messages(self, messages: List[Message]) -> List[Dict]:
        """تبدیل پیام‌ها به فرمت OpenAI (شامل tool_calls/tool_results کانونیکال)"""
        formatted = []
        for msg in messages:
            # 🆕 (canonical tool fields → OpenAI format)
            if getattr(msg, "tool_calls", None):
                # assistant turn after tool_use — OpenAI: tool_calls در فیلد جدا
                formatted.append({
                    "role": msg.role,
                    "content": msg.content or None,
                    "tool_calls": [
                        {
                            "id": tc.get("id", ""),
                            "type": "function",
                            "function": {
                                "name": tc.get("name", ""),
                                "arguments": json.dumps(tc.get("input", {}) or {}, ensure_ascii=False),
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                })
                continue
            if getattr(msg, "tool_results", None):
                # user turn with tool results — OpenAI: هر نتیجه یک message جدا
                for tr in msg.tool_results:
                    formatted.append({
                        "role": "tool",
                        "tool_call_id": tr.get("tool_use_id", ""),
                        "content": tr.get("content", ""),
                    })
                continue
            if msg.images:
                # پیام با تصویر (vision)
                content = [{"type": "text", "text": msg.content}]
                for img in msg.images:
                    # تشخیص نوع تصویر از header (PNG: iVBORw0K, JPEG: /9j/)
                    if img.startswith("http"):
                        image_url = img
                    elif img.startswith("iVBORw0K"):
                        image_url = f"data:image/png;base64,{img}"
                    else:
                        image_url = f"data:image/jpeg;base64,{img}"

                    content.append({
                        "type": "image_url",
                        "image_url": {"url": image_url}
                    })
                formatted.append({"role": msg.role, "content": content})
            else:
                formatted.append({"role": msg.role, "content": msg.content})
        return formatted

    @staticmethod
    def _canonical_tools_to_openai(tools: List[Dict]) -> List[Dict]:
        """ترجمهٔ tools از فرمت کانونیکال (Anthropic-style) به فرمت OpenAI."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t.get("name", ""),
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
                },
            }
            for t in (tools or [])
        ]

    @staticmethod
    def _openai_tool_choice(tool_choice: Any) -> Any:
        """ترجمهٔ tool_choice کانونیکال به OpenAI: {type:'auto'}→'auto'، {type:'any'}→'required'."""
        if not tool_choice:
            return None
        if isinstance(tool_choice, str):
            return tool_choice
        if isinstance(tool_choice, dict):
            t = tool_choice.get("type")
            if t == "auto":
                return "auto"
            if t == "any":
                return "required"
            if t == "tool" and tool_choice.get("name"):
                return {"type": "function", "function": {"name": tool_choice["name"]}}
        return None

    async def generate(
        self,
        model_id: str,
        messages: List[Message],
        max_tokens: int = 16384,
        temperature: float = 0.7,
        **kwargs
    ) -> AIResponse:
        """تولید پاسخ از مدل OpenAI"""
        start_time = datetime.now()

        try:
            model = get_model(model_id)
            if not model:
                raise AIServiceError(f"Model {model_id} not found", "openai", model_id)

            # برای DALL-E، از endpoint تولید تصویر استفاده کن
            if model.is_image_generator:
                return await self._generate_image(model_id, messages[-1].content, **kwargs)

            # استفاده از model.id به جای model_id برای حل alias
            payload = {
                "model": model.id,  # استفاده از ID واقعی مدل (نه alias)
                "messages": self._format_messages(messages),
                "max_tokens": min(max_tokens, model.max_tokens),
                "temperature": temperature,
            }

            # افزودن پارامترهای اختیاری
            if kwargs.get("top_p"):
                payload["top_p"] = kwargs["top_p"]
            if kwargs.get("presence_penalty"):
                payload["presence_penalty"] = kwargs["presence_penalty"]
            if kwargs.get("frequency_penalty"):
                payload["frequency_penalty"] = kwargs["frequency_penalty"]

            # 🆕 (tool-calling) — افزودن tools و tool_choice
            if kwargs.get("tools"):
                payload["tools"] = self._canonical_tools_to_openai(kwargs["tools"])
                _tc = self._openai_tool_choice(kwargs.get("tool_choice"))
                if _tc is not None:
                    payload["tool_choice"] = _tc

            response = await self.client.post(
                f"{self.BASE_URL}/chat/completions",
                headers=self._build_headers(),
                json=payload
            )

            if response.status_code != 200:
                self.record_error()
                error_data = response.json()
                raise AIServiceError(
                    error_data.get("error", {}).get("message", "Unknown error"),
                    "openai",
                    model_id,
                    response.status_code
                )

            data = response.json()
            self.reset_errors()

            latency = int((datetime.now() - start_time).total_seconds() * 1000)

            # 🆕 (tool-calling) — parse tool_calls از پاسخ به فرمت کانونیکال
            _msg = data["choices"][0]["message"]
            _content = _msg.get("content") or ""
            _tool_calls = []
            for tc in (_msg.get("tool_calls") or []):
                _fn = tc.get("function", {})
                _args_str = _fn.get("arguments", "")
                try:
                    _input = json.loads(_args_str) if _args_str else {}
                except (json.JSONDecodeError, TypeError):
                    _input = {"__raw_arguments__": _args_str}
                _tool_calls.append({
                    "id": tc.get("id", ""),
                    "name": _fn.get("name", ""),
                    "input": _input,
                })

            return AIResponse(
                model_id=model_id,
                content=_content,
                tokens_used=data.get("usage", {}).get("total_tokens", 0),
                finish_reason=data["choices"][0].get("finish_reason", ""),
                latency_ms=latency,
                metadata={
                    "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                    "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
                },
                tool_calls=_tool_calls or None,
            )

        except AIServiceError:
            raise
        except Exception as e:
            self.record_error()
            raise AIServiceError(str(e), "openai", model_id)

    async def _generate_image(
        self,
        model_id: str,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        n: int = 1,
        **kwargs
    ) -> AIResponse:
        """تولید تصویر با DALL-E"""
        start_time = datetime.now()

        try:
            payload = {
                "model": model_id,
                "prompt": prompt,
                "size": size,
                "quality": quality,
                "n": n,
            }

            response = await self.client.post(
                f"{self.BASE_URL}/images/generations",
                headers=self._build_headers(),
                json=payload
            )

            if response.status_code != 200:
                self.record_error()
                error_data = response.json()
                raise AIServiceError(
                    error_data.get("error", {}).get("message", "Unknown error"),
                    "openai",
                    model_id,
                    response.status_code
                )

            data = response.json()
            self.reset_errors()

            latency = int((datetime.now() - start_time).total_seconds() * 1000)

            # استخراج URL تصاویر
            image_urls = [img["url"] for img in data.get("data", [])]

            return AIResponse(
                model_id=model_id,
                content=json.dumps({"images": image_urls}),
                tokens_used=0,
                finish_reason="success",
                latency_ms=latency,
                metadata={"image_urls": image_urls, "revised_prompt": data.get("data", [{}])[0].get("revised_prompt")}
            )

        except AIServiceError:
            raise
        except Exception as e:
            self.record_error()
            raise AIServiceError(str(e), "openai", model_id)

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
                raise AIServiceError("Streaming not supported for this model", "openai", model_id)

            # استفاده از model.id به جای model_id برای حل alias
            payload = {
                "model": model.id,  # استفاده از ID واقعی مدل (نه alias)
                "messages": self._format_messages(messages),
                "max_tokens": min(max_tokens, model.max_tokens),
                "temperature": temperature,
                "stream": True,
            }

            async with self.client.stream(
                "POST",
                f"{self.BASE_URL}/chat/completions",
                headers=self._build_headers(),
                json=payload
            ) as response:
                if response.status_code != 200:
                    self.record_error()
                    raise AIServiceError("Stream error", "openai", model_id, response.status_code)

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                        except json.JSONDecodeError:
                            continue

            self.reset_errors()

        except AIServiceError:
            raise
        except Exception as e:
            self.record_error()
            raise AIServiceError(str(e), "openai", model_id)
