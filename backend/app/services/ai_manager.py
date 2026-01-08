"""
مدیر مرکزی سرویس‌های AI
انتخاب هوشمند مدل، مدیریت fallback و load balancing
"""

from typing import Dict, List, Optional, Any, Type
from datetime import datetime
import asyncio
import threading

from .ai_base import AIServiceBase, Message, AIResponse, AIServiceError
from .openai_service import OpenAIService
from .claude_service import ClaudeService
from .gemini_service import GeminiService
from .deepseek_service import DeepSeekService
from ..core.config import settings
from ..core.models_registry import (
    ModelProvider, AIModel, ModelCapability,
    MODEL_REGISTRY, get_model, get_models_by_capability,
    get_enabled_models
)


class AIManager:
    """مدیر مرکزی همه سرویس‌های AI"""

    def __init__(self):
        self._services: Dict[ModelProvider, AIServiceBase] = {}
        self._initialize_services()

    def _initialize_services(self):
        """راه‌اندازی سرویس‌های موجود بر اساس API keys"""
        available = settings.get_available_providers()

        if available.get("openai"):
            try:
                self._services[ModelProvider.OPENAI] = OpenAIService()
            except AIServiceError:
                pass

        if available.get("claude"):
            try:
                self._services[ModelProvider.CLAUDE] = ClaudeService()
            except AIServiceError:
                pass

        if available.get("gemini"):
            try:
                self._services[ModelProvider.GEMINI] = GeminiService()
            except AIServiceError:
                pass

        if available.get("deepseek"):
            try:
                self._services[ModelProvider.DEEPSEEK] = DeepSeekService()
            except AIServiceError:
                pass

    def get_available_providers(self) -> List[str]:
        """لیست provider های فعال"""
        return [p.value for p in self._services.keys()]

    def get_available_models(self) -> List[AIModel]:
        """لیست همه مدل‌های قابل استفاده"""
        available = []
        for model in get_enabled_models():
            if model.provider in self._services:
                if not self._services[model.provider].is_in_error_state():
                    available.append(model)
        return available

    def smart_select_models(
        self,
        prompt: str,
        required_capabilities: Optional[List[ModelCapability]] = None,
        max_models: int = 3,
        prefer_providers: Optional[List[ModelProvider]] = None,
    ) -> List[AIModel]:
        """انتخاب هوشمند مدل‌ها بر اساس نیازها"""
        available = self.get_available_models()

        if not available:
            return []

        # تحلیل پرامپت برای تشخیص قابلیت‌های مورد نیاز
        detected_caps = self._detect_capabilities_from_prompt(prompt)
        all_caps = set(required_capabilities or []) | set(detected_caps)

        # فیلتر بر اساس قابلیت‌ها
        if all_caps:
            filtered = []
            for model in available:
                model_caps = set(model.capabilities)
                if all_caps & model_caps:  # حداقل یک قابلیت مشترک
                    filtered.append(model)
            if filtered:
                available = filtered

        # ترجیح provider خاص
        if prefer_providers:
            preferred = [m for m in available if m.provider in prefer_providers]
            if preferred:
                available = preferred

        # مرتب‌سازی بر اساس اولویت و context window
        available.sort(key=lambda m: (m.priority, -m.context_window))

        # تنوع در provider ها
        selected = []
        used_providers = set()

        for model in available:
            if len(selected) >= max_models:
                break
            # ترجیح تنوع در provider ها
            if model.provider not in used_providers or len(selected) < 2:
                selected.append(model)
                used_providers.add(model.provider)

        return selected

    def _detect_capabilities_from_prompt(self, prompt: str) -> List[ModelCapability]:
        """تشخیص قابلیت‌های مورد نیاز از متن پرامپت"""
        caps = []
        prompt_lower = prompt.lower()

        # کدنویسی
        code_keywords = ['کد', 'برنامه', 'code', 'function', 'debug', 'error', 'bug',
                         'script', 'develop', 'html', 'css', 'javascript', 'python',
                         'backend', 'frontend', 'api']
        if any(kw in prompt_lower for kw in code_keywords):
            caps.append(ModelCapability.CODE)

        # تصویر
        image_keywords = ['تصویر', 'عکس', 'image', 'picture', 'photo', 'visual', 'screenshot']
        if any(kw in prompt_lower for kw in image_keywords):
            caps.append(ModelCapability.VISION)

        # تولید تصویر
        gen_keywords = ['نقاشی', 'بکش', 'رسم', 'طراحی', 'draw', 'paint', 'sketch',
                        'generate image', 'create image', 'تولید تصویر', 'بساز عکس']
        if any(kw in prompt_lower for kw in gen_keywords):
            caps.append(ModelCapability.IMAGE_GENERATION)

        # استدلال
        reason_keywords = ['تحلیل', 'analyze', 'reasoning', 'استدلال', 'منطق', 'چرا']
        if any(kw in prompt_lower for kw in reason_keywords):
            caps.append(ModelCapability.REASONING)

        return caps

    async def generate(
        self,
        model_id: str,
        messages: List[Message],
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> AIResponse:
        """تولید پاسخ از یک مدل خاص"""
        model = get_model(model_id)
        if not model:
            raise AIServiceError(f"Model {model_id} not found", "manager", model_id)

        service = self._services.get(model.provider)
        if not service:
            raise AIServiceError(f"Provider {model.provider} not available", "manager", model_id)

        return await service.generate(model_id, messages, max_tokens, temperature, **kwargs)

    async def generate_with_fallback(
        self,
        model_ids: List[str],
        messages: List[Message],
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> AIResponse:
        """تولید پاسخ با fallback به مدل‌های دیگر در صورت خطا"""
        errors = []

        for model_id in model_ids:
            try:
                return await self.generate(model_id, messages, max_tokens, temperature, **kwargs)
            except AIServiceError as e:
                errors.append(f"{model_id}: {e.message}")
                continue

        raise AIServiceError(
            f"All models failed: {'; '.join(errors)}",
            "manager"
        )

    async def generate_parallel(
        self,
        model_ids: List[str],
        messages: List[Message],
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> List[AIResponse]:
        """تولید پاسخ از چند مدل به صورت موازی"""
        tasks = [
            self.generate(model_id, messages, max_tokens, temperature, **kwargs)
            for model_id in model_ids
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        responses = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                responses.append(AIResponse(
                    model_id=model_ids[i],
                    content="",
                    error=str(result)
                ))
            else:
                responses.append(result)

        return responses

    async def close(self):
        """بستن همه connection ها"""
        for service in self._services.values():
            await service.close()


# Singleton instance with thread-safety
_ai_manager: Optional[AIManager] = None
_ai_manager_lock = threading.Lock()


def get_ai_manager() -> AIManager:
    """دریافت instance مدیر AI (thread-safe)"""
    global _ai_manager
    if _ai_manager is None:
        with _ai_manager_lock:
            # Double-check locking pattern
            if _ai_manager is None:
                _ai_manager = AIManager()
    return _ai_manager


async def reset_ai_manager():
    """ریست کردن AI manager برای بارگذاری مجدد API keys"""
    global _ai_manager
    if _ai_manager is not None:
        try:
            await _ai_manager.close()
        except Exception as e:
            # Log the error but continue with reset
            import logging
            logging.getLogger(__name__).warning(f"Error closing AI manager during reset: {e}")
    _ai_manager = None
    # ایجاد instance جدید
    return get_ai_manager()
