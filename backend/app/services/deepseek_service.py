"""
سرویس DeepSeek
پشتیبانی از DeepSeek Chat, DeepSeek Coder, DeepSeek Reasoner
"""

from typing import Dict, List, Optional, Any, AsyncIterator
import json
from datetime import datetime

from .ai_base import AIServiceBase, Message, AIResponse, AIServiceError
from ..core.models_registry import ModelProvider, get_model
from ..core.config import settings


class DeepSeekService(AIServiceBase):
    """سرویس DeepSeek"""

    provider = ModelProvider.DEEPSEEK
    BASE_URL = "https://api.deepseek.com"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key or settings.DEEPSEEK_API_KEY)
        if not self.api_key:
            raise AIServiceError("DeepSeek API key not configured", "deepseek")

    def _build_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def _format_messages(self, messages: List[Message]) -> List[Dict]:
        """تبدیل پیام‌ها به فرمت DeepSeek (سازگار با OpenAI) شامل tool fields کانونیکال"""
        formatted = []
        for msg in messages:
            # 🆕 (canonical tool fields → OpenAI/DeepSeek format)
            if getattr(msg, "tool_calls", None):
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
                for tr in msg.tool_results:
                    formatted.append({
                        "role": "tool",
                        "tool_call_id": tr.get("tool_use_id", ""),
                        "content": tr.get("content", ""),
                    })
                continue
            formatted.append({"role": msg.role, "content": msg.content})
        return formatted

    @staticmethod
    def _canonical_tools_to_openai(tools: List[Dict]) -> List[Dict]:
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
        """تولید پاسخ از مدل DeepSeek"""
        start_time = datetime.now()

        try:
            model = get_model(model_id)
            if not model:
                raise AIServiceError(f"Model {model_id} not found", "deepseek", model_id)

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

            # 🆕 (tool-calling) — DeepSeek از function calling به سبک OpenAI پشتیبانی
            # می‌کند، به‌جز deepseek-reasoner که (طبق مستندات DeepSeek) tools ندارد.
            if kwargs.get("tools") and "reasoner" not in (model.id or "").lower():
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
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                except (ValueError, KeyError, TypeError):
                    error_msg = response.text
                raise AIServiceError(error_msg, "deepseek", model_id, response.status_code)

            data = response.json()
            self.reset_errors()

            latency = int((datetime.now() - start_time).total_seconds() * 1000)

            # برای DeepSeek Reasoner، reasoning_content جدا از content نگهداری میشه
            # هرگز reasoning رو با content ترکیب نکن — این باعث آلوده شدن خروجی کد میشه
            _msg = data["choices"][0]["message"]
            content = _msg.get("content") or ""
            reasoning = _msg.get("reasoning_content", "")

            # 🆕 (tool-calling) — parse tool_calls از پاسخ به فرمت کانونیکال
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
                content=content,
                tokens_used=data.get("usage", {}).get("total_tokens", 0),
                finish_reason=data["choices"][0].get("finish_reason", ""),
                latency_ms=latency,
                metadata={
                    "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                    "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
                    "has_reasoning": bool(reasoning),
                    "reasoning_content": reasoning if reasoning else None,
                },
                tool_calls=_tool_calls or None,
            )

        except AIServiceError:
            raise
        except Exception as e:
            self.record_error()
            raise AIServiceError(str(e), "deepseek", model_id)

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
                raise AIServiceError(f"Model {model_id} not found", "deepseek", model_id)

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
                    raise AIServiceError("Stream error", "deepseek", model_id, response.status_code)

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
                            # reasoning_content فقط لاگ میشه، yield نمیشه
                            # چون در streaming قابل تفکیک از content نیست
                            # و باعث آلوده شدن خروجی کد میشه
                        except json.JSONDecodeError:
                            continue

            self.reset_errors()

        except AIServiceError:
            raise
        except Exception as e:
            self.record_error()
            raise AIServiceError(str(e), "deepseek", model_id)
