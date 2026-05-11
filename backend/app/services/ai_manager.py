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
from .perplexity_service import PerplexityService  # 🆕 Perplexity
from ..core.config import settings
from ..core.models_registry import (
    ModelProvider, AIModel, ModelCapability,
    MODEL_REGISTRY, get_model, get_models_by_capability,
    get_enabled_models
)
from ..core.logging_utils import StructuredLogger

# لاگر ساختاریافته
slog = StructuredLogger(__name__, "AI-MANAGER")


class AIManager:
    """مدیر مرکزی همه سرویس‌های AI"""

    def __init__(self):
        self._services: Dict[ModelProvider, AIServiceBase] = {}
        self._init_errors: Dict[str, str] = {}  # برای debug
        self._initialize_services()

    def _initialize_services(self):
        """راه‌اندازی سرویس‌های موجود بر اساس API keys"""
        slog.start("Initializing AI services")

        available = settings.get_available_providers()
        slog.info("Available providers from settings",
            providers=list(available.keys()),
            enabled=[k for k, v in available.items() if v]
        )

        provider_configs = [
            ("openai", ModelProvider.OPENAI, OpenAIService),
            ("claude", ModelProvider.CLAUDE, ClaudeService),
            ("gemini", ModelProvider.GEMINI, GeminiService),
            ("deepseek", ModelProvider.DEEPSEEK, DeepSeekService),
            ("perplexity", ModelProvider.PERPLEXITY, PerplexityService),
        ]

        for name, provider, service_class in provider_configs:
            if available.get(name):
                try:
                    self._services[provider] = service_class()
                    slog.success(f"{name.capitalize()} service initialized")
                except AIServiceError as e:
                    self._init_errors[name] = str(e)
                    slog.warning(f"{name.capitalize()} init failed", error=str(e)[:100])
                except Exception as e:
                    self._init_errors[name] = str(e)
                    slog.error(f"{name.capitalize()} init error", exception=e)

        slog.end("AI services initialization",
            services_count=len(self._services),
            services=list(self._services.keys()),
            errors=list(self._init_errors.keys()) if self._init_errors else None
        )

    def get_available_providers(self) -> List[str]:
        """لیست provider های فعال"""
        return [p.value for p in self._services.keys()]

    def get_available_models(self, task_type: Optional[str] = None) -> List[AIModel]:
        """
        لیست همه مدل‌های قابل استفاده
        با در نظر گرفتن تنظیمات دیتابیس (فعال/غیرفعال)

        Args:
            task_type: نوع کار برای فیلتر مدل‌های مجاز (اختیاری)
        """
        import logging
        logger = logging.getLogger(__name__)

        # 🔴 دریافت تنظیمات از دیتابیس
        db_settings_map = {}
        try:
            from ..core.database import SessionLocal
            from ..models.ai_profile import ModelSettings
            # 🆕 (bugfix) قبلاً `db = next(get_db())` بدون close → session leak
            # حالا با context manager، session تضمیناً close می‌شود
            db = SessionLocal()
            try:
                db_settings = db.query(ModelSettings).all()
                db_settings_map = {s.model_id: s for s in db_settings}
                logger.debug(f"Loaded {len(db_settings_map)} model settings from DB")
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Could not load model settings from DB: {e}")

        available = []
        for model in get_enabled_models():
            # هندل کردن هر دو حالت enum و string
            provider = model.provider
            if isinstance(provider, str):
                # تبدیل string به enum
                try:
                    provider = ModelProvider(provider)
                except ValueError:
                    continue

            if provider in self._services:
                if not self._services[provider].is_in_error_state():
                    # 🔴 چک کردن تنظیمات دیتابیس
                    db_setting = db_settings_map.get(model.id)
                    if db_setting:
                        # اگر در دیتابیس غیرفعال شده، رد شو
                        if not db_setting.enabled:
                            logger.debug(f"Model {model.id} is disabled in settings")
                            continue

                        # اگر task_type مشخص شده، چک کن مجاز هست یا نه
                        if task_type:
                            allowed_tasks = db_setting.allowed_tasks or ["all"]
                            if "all" not in allowed_tasks and task_type not in allowed_tasks:
                                logger.debug(f"Model {model.id} not allowed for task {task_type}")
                                continue

                    available.append(model)

        logger.debug(f"Available models: {[m.id for m in available]}")
        return available

    def smart_select_models(
        self,
        prompt: str,
        required_capabilities: Optional[List[ModelCapability]] = None,
        max_models: int = 3,
        prefer_providers: Optional[List[ModelProvider]] = None,
        task_type: Optional[str] = None,  # 🆕 فیلتر براساس نوع کار
    ) -> List[AIModel]:
        """انتخاب هوشمند مدل‌ها بر اساس نیازها"""
        available = self.get_available_models(task_type=task_type)

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

    def find_fallback_model(self, disabled_model_id: str, task_type: Optional[str] = None, require_vision: bool = False) -> Optional[str]:
        """
        یافتن نزدیک‌ترین مدل فعال به مدل غیرفعال شده

        استراتژی (بهبود یافته):
        1. 🆕 اگر مدل غیرفعال VISION داشت، فقط مدل‌های VISION را انتخاب کن
        2. استفاده از امتیازات واقعی از model_profiler
        3. مدل‌های هم‌provider با قابلیت‌های مشابه
        4. مدل‌های دیگر provider با قابلیت‌های مشابه

        Args:
            disabled_model_id: شناسه مدل غیرفعال
            task_type: نوع کار برای فیلتر اضافی
            require_vision: آیا حتماً باید vision داشته باشد

        Returns:
            شناسه مدل fallback یا None
        """
        slog.info("Finding fallback model",
            disabled_model=disabled_model_id,
            task_type=task_type,
            require_vision=require_vision
        )

        # دریافت اطلاعات مدل غیرفعال
        disabled_model = get_model(disabled_model_id)
        if not disabled_model:
            slog.warning("Cannot find fallback - disabled model not found", model_id=disabled_model_id)
            return None

        # 🆕 بررسی آیا مدل غیرفعال vision داشت
        disabled_has_vision = ModelCapability.VISION in disabled_model.capabilities
        needs_vision = require_vision or disabled_has_vision

        if needs_vision:
            slog.info("Fallback must have VISION capability", original_model=disabled_model_id)

        # دریافت مدل‌های فعال
        available_models = self.get_available_models(task_type=task_type)

        if not available_models:
            slog.warning("No available models for fallback")
            return None

        # 🆕 فیلتر مدل‌های دارای vision اگر نیاز است
        if needs_vision:
            vision_models = [m for m in available_models if ModelCapability.VISION in m.capabilities]
            if vision_models:
                available_models = vision_models
                slog.info(f"Filtered to {len(vision_models)} vision-capable models")
            else:
                slog.warning("No vision-capable models available for fallback, using all models")

        # اگر فقط یک مدل فعال بود، همان را برگردان
        if len(available_models) == 1:
            fallback = available_models[0].id
            slog.info("Only one model available as fallback",
                fallback=fallback,
                disabled=disabled_model_id
            )
            return fallback

        # 🆕 دریافت امتیازات واقعی از model_profiler
        profile_scores = {}
        try:
            from .model_profiler import ModelProfiler
            profiler = ModelProfiler()

            # دریافت پروفایل مدل غیرفعال برای مقایسه
            disabled_profile = profiler.get_profile(disabled_model_id)
            disabled_overall_score = disabled_profile.overall_score if disabled_profile else 50.0

            # دریافت پروفایل همه مدل‌های فعال
            for model in available_models:
                profile = profiler.get_profile(model.id)
                if profile:
                    profile_scores[model.id] = {
                        'overall': profile.overall_score,
                        'accuracy': profile.accuracy_score,
                        'tier': profile.tier,
                        # 🆕 امتیاز براساس task_type خاص
                        'task_score': profile.last_scores_by_task.get(task_type, {}).get('overall', profile.overall_score) if task_type else profile.overall_score
                    }
                else:
                    profile_scores[model.id] = {'overall': 50.0, 'accuracy': 50.0, 'tier': 'C', 'task_score': 50.0}

            slog.debug("Loaded model profiles for fallback", profiles_count=len(profile_scores))

        except Exception as e:
            slog.warning("Could not load model profiles for fallback", error=str(e)[:100])
            disabled_overall_score = 50.0

        # قابلیت‌های مدل غیرفعال
        disabled_caps = set(disabled_model.capabilities)
        disabled_provider = disabled_model.provider

        # امتیازدهی به مدل‌های فعال
        scored_models = []
        for model in available_models:
            score = 0
            model_caps = set(model.capabilities)

            # 🆕 امتیاز اصلی از پروفایل واقعی (تا 40 امتیاز)
            if model.id in profile_scores:
                profile = profile_scores[model.id]
                # امتیاز براساس نزدیکی به مدل غیرفعال + کیفیت خود مدل
                task_score = profile.get('task_score', profile['overall'])

                # 20 امتیاز برای مدل با عملکرد مشابه یا بهتر
                if task_score >= disabled_overall_score * 0.9:
                    score += 20
                elif task_score >= disabled_overall_score * 0.7:
                    score += 15
                else:
                    score += 10

                # 20 امتیاز اضافی براساس tier
                tier_bonus = {'S': 20, 'A': 16, 'B': 12, 'C': 8, 'D': 4, 'F': 0}
                score += tier_bonus.get(profile['tier'], 0)

            # امتیاز برای قابلیت‌های مشترک (هر قابلیت 10 امتیاز)
            common_caps = disabled_caps & model_caps
            score += len(common_caps) * 10

            # امتیاز برای هم‌provider بودن (15 امتیاز)
            if model.provider == disabled_provider:
                score += 15

            # امتیاز برای اولویت مشابه (5 امتیاز اگر اختلاف کمتر از 2)
            if abs(model.priority - disabled_model.priority) <= 2:
                score += 5

            # امتیاز برای context window مشابه یا بیشتر
            if model.context_window >= disabled_model.context_window * 0.8:
                score += 5
            if model.context_window >= disabled_model.context_window:
                score += 5  # امتیاز اضافی برای context بیشتر

            scored_models.append((model.id, score, model.priority, profile_scores.get(model.id, {}).get('tier', 'C')))

        # مرتب‌سازی براساس امتیاز (نزولی) و سپس اولویت (صعودی)
        scored_models.sort(key=lambda x: (-x[1], x[2]))

        if scored_models:
            best_fallback = scored_models[0][0]
            best_score = scored_models[0][1]
            best_tier = scored_models[0][3]
            slog.success("Found smart fallback",
                disabled=disabled_model_id,
                fallback=best_fallback,
                score=best_score,
                tier=best_tier
            )
            return best_fallback

        slog.warning("No suitable fallback found", disabled_model=disabled_model_id)
        return None

    def get_enabled_status(self, model_id: str) -> bool:
        """بررسی فعال بودن مدل در دیتابیس"""
        try:
            from ..core.database import SessionLocal
            from ..models.ai_profile import ModelSettings
            # 🆕 (bugfix) قبلاً `db = next(get_db())` بدون close → session leak
            db = SessionLocal()
            try:
                db_setting = db.query(ModelSettings).filter(ModelSettings.model_id == model_id).first()
                if db_setting:
                    return bool(db_setting.enabled)
                # اگر تنظیمات نداشت، از registry استفاده کن
                model = get_model(model_id)
                return model.enabled if model else False
            finally:
                db.close()
        except Exception as e:
            slog.error("Error checking model enabled status",
                model_id=model_id,
                exception=e
            )
            # 🔴 در صورت خطا، فرض کن غیرفعال است تا fallback کار کند
            return False

    async def generate(
        self,
        model_id: str,
        messages: List[Message],
        max_tokens: int = 16384,
        temperature: float = 0.7,
        task_type: Optional[str] = None,  # 🆕 برای fallback هوشمند
        allow_fallback: bool = True,  # 🆕 اجازه استفاده از fallback
        **kwargs
    ) -> AIResponse:
        """
        تولید پاسخ از یک مدل خاص

        🆕 قابلیت fallback هوشمند:
        - اگر مدل غیرفعال بود، نزدیک‌ترین مدل فعال پیدا می‌شود
        - اگر فقط یک مدل فعال بود، از همان استفاده می‌شود

        Args:
            model_id: شناسه مدل
            messages: لیست پیام‌ها
            max_tokens: حداکثر توکن خروجی
            temperature: دمای تولید
            task_type: نوع کار (برای فیلتر fallback)
            allow_fallback: آیا اجازه fallback داده شود
        """
        original_model_id = model_id
        used_fallback = False

        slog.ai_call(model_id, "generate request",
            messages_count=len(messages),
            max_tokens=max_tokens,
            task_type=task_type
        )

        model = get_model(model_id)
        if not model:
            slog.error("Model not found", model_id=model_id)
            raise AIServiceError(f"Model {model_id} not found", "manager", model_id)

        # 🔴🔴🔴 بررسی فعال بودن مدل - استفاده از متد get_enabled_status
        model_is_enabled = self.get_enabled_status(model_id)

        if not model_is_enabled:
            slog.warning("Model is disabled, looking for fallback", model_id=model_id)

            # 🆕 استفاده از fallback به جای خطا
            if allow_fallback:
                # 🆕 بررسی آیا پیام‌ها تصویر دارند - اگر بله، حتماً مدل vision نیاز است
                has_images = any(msg.images for msg in messages if hasattr(msg, 'images') and msg.images)
                if has_images:
                    slog.info("Messages contain images, requiring vision-capable fallback")

                fallback_model_id = self.find_fallback_model(model_id, task_type=task_type, require_vision=has_images)
                if fallback_model_id:
                    slog.info("Using fallback model",
                        original=model_id,
                        fallback=fallback_model_id
                    )
                    model_id = fallback_model_id
                    model = get_model(model_id)
                    used_fallback = True
                else:
                    # سعی کن اولین مدل فعال را پیدا کنی
                    available = self.get_available_models(task_type=task_type)
                    if available:
                        model_id = available[0].id
                        model = get_model(model_id)
                        used_fallback = True
                        slog.info("Using first available model as fallback", model_id=model_id)
                    else:
                        slog.error("No fallback available", original_model=original_model_id)
                        raise AIServiceError(
                            f"Model {original_model_id} is disabled and no fallback available",
                            "manager", original_model_id
                        )
            else:
                raise AIServiceError(f"Model {model_id} is disabled", "manager", model_id)

        # هندل کردن هر دو حالت enum و string
        provider = model.provider
        if isinstance(provider, str):
            try:
                provider = ModelProvider(provider)
            except ValueError:
                raise AIServiceError(f"Unknown provider: {provider}", "manager", model_id)

        service = self._services.get(provider)
        if not service:
            slog.error("Provider not available", provider=str(provider))
            raise AIServiceError(f"Provider {provider} not available", "manager", model_id)

        # 🔑 بودجه‌بندی هوشمند مرکزی (برای همه مدل‌ها و پروایدرها)
        # ────────────────────────────────────────────────────────
        # مرحله ۱: از ظرفیت واقعی مدل استفاده کن (نه سقف مصنوعی caller)
        _model_max_output = getattr(model, 'max_tokens', 16384) or 16384
        _model_context_window = getattr(model, 'context_window', 128000) or 128000

        # مرحله ۲: تخمین توکن‌های ورودی از روی پیام‌ها
        _estimated_input_tokens = 0
        for msg in messages:
            # متن: هر ۳ کاراکتر ≈ ۱ توکن (ترکیب فارسی/انگلیسی)
            _estimated_input_tokens += len(msg.content or '') // 3
            # تصاویر: هر عکس base64 ≈ 1000-30000 توکن بسته به اندازه
            if hasattr(msg, 'images') and msg.images:
                for img in msg.images:
                    # تخمین محافظه‌کارانه: هر 1KB base64 ≈ 12 توکن
                    _img_tokens = max(1000, len(img) // 80)
                    _estimated_input_tokens += _img_tokens

        # مرحله ۳: محاسبه حداکثر خروجی ایمن
        _safety_margin = max(500, _model_context_window // 100)  # 1% حاشیه ایمنی
        _available_for_output = _model_context_window - _estimated_input_tokens - _safety_margin

        # حداکثر خروجی = حداقل(ظرفیت واقعی مدل, فضای باقیمانده)
        # اگر فضا کافیه → ظرفیت کامل مدل؛ اگر نه → هر چقدر که جا هست
        _smart_max_tokens = min(_model_max_output, max(1024, _available_for_output))

        # اگر caller عدد بزرگتری خواسته ولی بودجه اجازه نمیده → هشدار لاگ
        if max_tokens > _smart_max_tokens:
            slog.info("Smart budget adjusted max_tokens",
                model=model_id,
                requested=max_tokens,
                smart=_smart_max_tokens,
                estimated_input=_estimated_input_tokens,
                context_window=_model_context_window,
                model_max_output=_model_max_output,
            )
        # اگر caller عدد کوچک فرستاده → به حداکثر ایمن ارتقا بده
        max_tokens = _smart_max_tokens

        response = await service.generate(model_id, messages, max_tokens, temperature, **kwargs)

        # 🆕 اضافه کردن اطلاعات fallback به response
        if used_fallback:
            response.fallback_used = True
            response.original_model_id = original_model_id
            slog.info("Response generated using fallback",
                original=original_model_id,
                actual=model_id,
                tokens_used=response.tokens_used
            )
        else:
            slog.success("AI response generated",
                model=model_id,
                tokens_used=response.tokens_used
            )

        return response

    async def generate_with_fallback(
        self,
        model_ids: List[str],
        messages: List[Message],
        max_tokens: int = 16384,
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
        max_tokens: int = 16384,
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
    slog.start("Resetting AI manager")
    if _ai_manager is not None:
        try:
            await _ai_manager.close()
            slog.info("Previous AI manager closed")
        except Exception as e:
            slog.warning("Error closing AI manager during reset", error=str(e)[:100])
    _ai_manager = None
    # ایجاد instance جدید
    new_manager = get_ai_manager()
    slog.end("AI manager reset",
        providers=new_manager.get_available_providers()
    )
    return new_manager


async def load_api_keys_and_reset():
    """
    🔴 تابع متمرکز برای بارگذاری API keys از دیتابیس و ریست کردن AI manager

    این تابع باید در هر جایی که نیاز به بارگذاری کلیدها هست استفاده شود:
    - startup سرور
    - auto-setup پروژه
    - تغییر تنظیمات

    Returns:
        tuple: (ai_manager, keys_loaded, available_providers)
    """
    import os

    slog.start("Loading API keys from database")

    keys_loaded = []

    try:
        from ..core.database import SessionLocal
        from ..models.setting import Setting

        db = SessionLocal()

        # مپ کلیدها: (db_key, env_key)
        key_mapping = [
            ("api_key_openai", "OPENAI_API_KEY"),
            ("api_key_claude", "CLAUDE_API_KEY"),
            ("api_key_gemini", "GEMINI_API_KEY"),
            ("api_key_deepseek", "DEEPSEEK_API_KEY"),
            ("api_key_openrouter", "OPENROUTER_API_KEY"),
            ("api_key_groq", "GROQ_API_KEY"),
            ("api_key_perplexity", "PERPLEXITY_API_KEY"),
        ]

        for db_key, env_key in key_mapping:
            try:
                value = Setting.get_value(db, db_key)
                if value:
                    os.environ[env_key] = value
                    keys_loaded.append(db_key)
                    slog.info(f"Loaded {env_key}", source="database")
            except Exception as e:
                slog.warning(f"Could not load {db_key}", error=str(e)[:50])

        db.close()

    except Exception as e:
        slog.error("Failed to load API keys from database", exception=e)

    # ریست AI manager
    ai_manager = await reset_ai_manager()
    available_providers = ai_manager.get_available_providers()

    slog.end("API keys loaded and AI manager reset",
        keys_loaded=len(keys_loaded),
        providers=available_providers
    )

    return ai_manager, keys_loaded, available_providers
