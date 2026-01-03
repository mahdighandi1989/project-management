"""
کلاس پایه برای همه سرویس‌های AI
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, AsyncIterator
from pydantic import BaseModel
import httpx
import asyncio
from datetime import datetime

from ..core.config import settings
from ..core.models_registry import AIModel, ModelProvider


class Message(BaseModel):
    """پیام در مکالمه"""
    role: str  # system, user, assistant
    content: str
    images: Optional[List[str]] = None  # base64 تصاویر


class AIResponse(BaseModel):
    """پاسخ AI"""
    model_id: str
    content: str
    tokens_used: int = 0
    finish_reason: str = ""
    latency_ms: int = 0
    timestamp: datetime = datetime.now()
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}


class AIServiceBase(ABC):
    """کلاس پایه برای همه سرویس‌های AI"""

    provider: ModelProvider

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT)
        self._error_count = 0
        self._last_error_time: Optional[datetime] = None

    @abstractmethod
    async def generate(
        self,
        model_id: str,
        messages: List[Message],
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> AIResponse:
        """تولید پاسخ از مدل"""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        model_id: str,
        messages: List[Message],
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncIterator[str]:
        """تولید پاسخ به صورت streaming"""
        pass

    async def health_check(self) -> bool:
        """بررسی سلامت سرویس"""
        try:
            # یک درخواست ساده برای تست
            return True
        except Exception:
            return False

    def is_in_error_state(self) -> bool:
        """آیا سرویس در وضعیت خطا است؟"""
        if self._error_count >= 3 and self._last_error_time:
            # اگر 3 خطا در 5 دقیقه گذشته داشتیم
            elapsed = (datetime.now() - self._last_error_time).total_seconds()
            if elapsed < 300:  # 5 دقیقه
                return True
            else:
                # reset کردن بعد از 5 دقیقه
                self._error_count = 0
                self._last_error_time = None
        return False

    def record_error(self):
        """ثبت خطا"""
        self._error_count += 1
        self._last_error_time = datetime.now()

    def reset_errors(self):
        """ریست کردن شمارنده خطا"""
        self._error_count = 0
        self._last_error_time = None

    async def close(self):
        """بستن connection"""
        await self.client.aclose()

    def _build_headers(self) -> Dict[str, str]:
        """ساخت headers پایه"""
        return {
            "Content-Type": "application/json",
        }

    def _estimate_tokens(self, text: str) -> int:
        """تخمین تعداد توکن‌ها"""
        # تخمین ساده: هر 4 کاراکتر ≈ 1 توکن
        return len(text) // 4


class AIServiceError(Exception):
    """خطای سرویس AI"""
    def __init__(self, message: str, provider: str, model_id: str = "", status_code: int = 0):
        self.message = message
        self.provider = provider
        self.model_id = model_id
        self.status_code = status_code
        super().__init__(f"[{provider}] {message}")
