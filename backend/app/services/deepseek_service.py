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
        """تبدیل پیام‌ها به فرمت DeepSeek (سازگار با OpenAI)"""
        formatted = []
        for msg in messages:
            formatted.append({"role": msg.role, "content": msg.content})
        return formatted

    async def generate(
        self,
        model_id: str,
        messages: List[Message],
        max_tokens: int = 4096,
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

            # برای DeepSeek Reasoner، ممکن است reasoning_content هم داشته باشیم
            content = data["choices"][0]["message"].get("content", "")
            reasoning = data["choices"][0]["message"].get("reasoning_content", "")

            if reasoning:
                content = f"**استدلال:**\n{reasoning}\n\n**نتیجه:**\n{content}"

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
                }
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
        max_tokens: int = 4096,
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
                            # برای Reasoner
                            if "reasoning_content" in delta:
                                yield delta["reasoning_content"]
                        except json.JSONDecodeError:
                            continue

            self.reset_errors()

        except AIServiceError:
            raise
        except Exception as e:
            self.record_error()
            raise AIServiceError(str(e), "deepseek", model_id)
