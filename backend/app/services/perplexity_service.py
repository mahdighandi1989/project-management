# -*- coding: utf-8 -*-
"""
سرویس Perplexity AI
پشتیبانی از مدل‌های Sonar برای جستجو و تحقیق هوشمند
"""

from typing import Dict, List, Optional, Any, AsyncIterator
import json
from datetime import datetime

from .ai_base import AIServiceBase, Message, AIResponse, AIServiceError
from ..core.models_registry import ModelProvider, get_model
from ..core.config import settings


class PerplexityService(AIServiceBase):
    """سرویس Perplexity AI"""

    provider = ModelProvider.PERPLEXITY
    BASE_URL = "https://api.perplexity.ai"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key or settings.PERPLEXITY_API_KEY)
        if not self.api_key:
            raise AIServiceError("Perplexity API key not configured", "perplexity")

    def _build_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def _format_messages(self, messages: List[Message]) -> List[Dict]:
        """تبدیل پیام‌ها به فرمت Perplexity (سازگار با OpenAI)"""
        formatted = []
        for msg in messages:
            formatted.append({
                "role": msg.role,
                "content": msg.content
            })
        return formatted

    async def generate(
        self,
        model_id: str,
        messages: List[Message],
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> AIResponse:
        """تولید پاسخ از مدل Perplexity"""
        start_time = datetime.now()

        try:
            model = get_model(model_id)
            if not model:
                raise AIServiceError(f"Model {model_id} not found", "perplexity", model_id)

            payload = {
                "model": model_id,
                "messages": self._format_messages(messages),
                "max_tokens": min(max_tokens, model.max_tokens),
                "temperature": temperature,
            }

            # پارامترهای مخصوص Perplexity
            if kwargs.get("return_citations"):
                payload["return_citations"] = True
            if kwargs.get("return_images"):
                payload["return_images"] = True
            if kwargs.get("return_related_questions"):
                payload["return_related_questions"] = True
            if kwargs.get("search_domain_filter"):
                payload["search_domain_filter"] = kwargs["search_domain_filter"]
            if kwargs.get("search_recency_filter"):
                payload["search_recency_filter"] = kwargs["search_recency_filter"]

            # top_p و top_k
            if kwargs.get("top_p"):
                payload["top_p"] = kwargs["top_p"]
            if kwargs.get("top_k"):
                payload["top_k"] = kwargs["top_k"]
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
                error_data = response.json()
                raise AIServiceError(
                    error_data.get("error", {}).get("message", "Unknown error"),
                    "perplexity",
                    model_id,
                    response.status_code
                )

            data = response.json()
            self.reset_errors()

            latency = int((datetime.now() - start_time).total_seconds() * 1000)

            # استخراج citations و related questions اگر موجود باشند
            metadata = {
                "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
            }

            # اضافه کردن citations اگر برگردانده شده
            if "citations" in data:
                metadata["citations"] = data["citations"]
            if "related_questions" in data:
                metadata["related_questions"] = data["related_questions"]
            if "images" in data:
                metadata["images"] = data["images"]

            return AIResponse(
                model_id=model_id,
                content=data["choices"][0]["message"]["content"],
                tokens_used=data.get("usage", {}).get("total_tokens", 0),
                finish_reason=data["choices"][0].get("finish_reason", ""),
                latency_ms=latency,
                metadata=metadata
            )

        except AIServiceError:
            raise
        except Exception as e:
            self.record_error()
            raise AIServiceError(str(e), "perplexity", model_id)

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
                raise AIServiceError(f"Model {model_id} not found", "perplexity", model_id)

            payload = {
                "model": model_id,
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
                    raise AIServiceError("Stream error", "perplexity", model_id, response.status_code)

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
            raise AIServiceError(str(e), "perplexity", model_id)

    async def search(
        self,
        query: str,
        model_id: str = "sonar-pro",
        search_recency: str = "month",
        **kwargs
    ) -> AIResponse:
        """جستجوی هوشمند با Perplexity"""
        messages = [
            Message(role="user", content=query)
        ]

        return await self.generate(
            model_id=model_id,
            messages=messages,
            return_citations=True,
            return_related_questions=True,
            search_recency_filter=search_recency,
            **kwargs
        )
