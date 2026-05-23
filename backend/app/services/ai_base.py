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
    images: Optional[List[str]] = None  # base64 تصاویر (PNG/JPEG)
    # 🆕 رسانهٔ inline با MIME صریح: لیست (mime, base64).
    # برای فایل‌های غیر-تصویری مانند audio/*, video/*, application/pdf, ...
    # که نمی‌توان MIME را از prefix base64 حدس زد. اگر provider از این
    # رسانه پشتیبانی نمی‌کند، باید AIServiceError بدهد (بدون سنیف غلط).
    inline_files: Optional[List[tuple]] = None  # List[Tuple[mime: str, b64: str]]
    # 🆕 (tool-calling/agent-loop) — محتوای ساختاریافتهٔ خام برای پیام‌هایی که
    # نمی‌توان با یک str نمایش داد: پیام assistant که tool_use دارد (echo برگشتی)
    # و پیام user که tool_result دارد. اگر set شود، provider باید آن را
    # مستقیماً به‌عنوان content blocks استفاده کند (نه msg.content).
    # ⚠️ (legacy/Claude-specific): این فرمت Anthropic block است؛ برای کار
    # provider-agnostic از tool_calls/tool_results کانونیکال زیر استفاده کنید.
    raw_content: Optional[Any] = None  # List[Dict] — Anthropic content blocks
    # 🆕 (canonical, provider-agnostic) — برای echo برگرداندن assistant turn که
    # tool_use داشت. هر provider این را به فرمت native خود ترجمه می‌کند.
    # هر آیتم: {"id": str, "name": str, "input": dict}
    tool_calls: Optional[List[Dict[str, Any]]] = None
    # 🆕 (canonical, provider-agnostic) — برای پیام user که نتیجهٔ ابزارها را
    # برمی‌گرداند. هر آیتم: {"tool_use_id": str, "name": str, "content": str, "is_error": bool}
    # توجه: name برای Gemini لازم است (Gemini با نام match می‌کند نه id).
    tool_results: Optional[List[Dict[str, Any]]] = None


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
    # 🆕 اطلاعات fallback
    fallback_used: bool = False  # آیا از fallback استفاده شده
    original_model_id: Optional[str] = None  # مدل اصلی که غیرفعال بود
    # 🆕 (tool-calling/agent-loop) — بلوک‌های tool_use که مدل درخواست کرده.
    # هر مورد: {"id": str, "name": str, "input": dict}. وقتی finish_reason
    # == "tool_use" پر می‌شود.
    tool_calls: Optional[List[Dict[str, Any]]] = None
    # محتوای کامل assistant (آرایهٔ content blocks) برای echo برگشتی در حلقه
    raw_assistant_content: Optional[List[Dict[str, Any]]] = None


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
        max_tokens: int = 16384,
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
        max_tokens: int = 16384,
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
