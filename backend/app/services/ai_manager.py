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


class AIManager:
    """مدیر مرکزی همه سرویس‌های AI"""

    def __init__(self):
        self._services: Dict[ModelProvider, AIServiceBase] = {}
        self._init_errors: Dict[str, str] = {}  # برای debug
        self._initialize_services()

    def _initialize_services(self):
        """راه‌اندازی سرویس‌های موجود بر اساس API keys"""
        import logging
        logger = logging.getLogger(__name__)

        available = settings.get_available_providers()
        logger.info(f"🔑 Available providers from settings: {available}")

        if available.get("openai"):
            try:
                self._services[ModelProvider.OPENAI] = OpenAIService()
                logger.info("✅ OpenAI service initialized")
            except AIServiceError as e:
                self._init_errors["openai"] = str(e)
                logger.warning(f"⚠️ OpenAI init failed: {e}")
            except Exception as e:
                self._init_errors["openai"] = str(e)
                logger.error(f"❌ OpenAI init error: {e}")

        if available.get("claude"):
            try:
                self._services[ModelProvider.CLAUDE] = ClaudeService()
                logger.info("✅ Claude service initialized")
            except AIServiceError as e:
                self._init_errors["claude"] = str(e)
                logger.warning(f"⚠️ Claude init failed: {e}")
            except Exception as e:
                self._init_errors["claude"] = str(e)
                logger.error(f"❌ Claude init error: {e}")

        if available.get("gemini"):
            try:
                self._services[ModelProvider.GEMINI] = GeminiService()
                logger.info("✅ Gemini service initialized")
            except AIServiceError as e:
                self._init_errors["gemini"] = str(e)
                logger.warning(f"⚠️ Gemini init failed: {e}")
            except Exception as e:
                self._init_errors["gemini"] = str(e)
                logger.error(f"❌ Gemini init error: {e}")

        if available.get("deepseek"):
            try:
                self._services[ModelProvider.DEEPSEEK] = DeepSeekService()
                logger.info("✅ DeepSeek service initialized")
            except AIServiceError as e:
                self._init_errors["deepseek"] = str(e)
                logger.warning(f"⚠️ DeepSeek init failed: {e}")
            except Exception as e:
                self._init_errors["deepseek"] = str(e)
                logger.error(f"❌ DeepSeek init error: {e}")

        if available.get("perplexity"):
            try:
                self._services[ModelProvider.PERPLEXITY] = PerplexityService()
                logger.info("✅ Perplexity service initialized")
            except AIServiceError as e:
                self._init_errors["perplexity"] = str(e)
                logger.warning(f"⚠️ Perplexity init failed: {e}")
            except Exception as e:
                self._init_errors["perplexity"] = str(e)
                logger.error(f"❌ Perplexity init error: {e}")

        logger.info(f"📊 Initialized {len(self._services)} services: {list(self._services.keys())}")
        if self._init_errors:
            logger.warning(f"⚠️ Init errors: {self._init_errors}")

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
            from ..core.database import get_db
            from ..models.ai_profile import ModelSettings
            db = next(get_db())
            db_settings = db.query(ModelSettings).all()
            db_settings_map = {s.model_id: s for s in db_settings}
            logger.debug(f"Loaded {len(db_settings_map)} model settings from DB")
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

    def find_fallback_model(self, disabled_model_id: str, task_type: Optional[str] = None) -> Optional[str]:
        """
        یافتن نزدیک‌ترین مدل فعال به مدل غیرفعال شده

        استراتژی (بهبود یافته):
        1. 🆕 استفاده از امتیازات واقعی از model_profiler
        2. مدل‌های هم‌provider با قابلیت‌های مشابه
        3. مدل‌های دیگر provider با قابلیت‌های مشابه
        4. اگر فقط یک مدل فعال بود، همان را برگردان

        Args:
            disabled_model_id: شناسه مدل غیرفعال
            task_type: نوع کار برای فیلتر اضافی

        Returns:
            شناسه مدل fallback یا None
        """
        import logging
        logger = logging.getLogger(__name__)

        # دریافت اطلاعات مدل غیرفعال
        disabled_model = get_model(disabled_model_id)
        if not disabled_model:
            logger.warning(f"Cannot find fallback - disabled model {disabled_model_id} not found")
            return None

        # دریافت مدل‌های فعال
        available_models = self.get_available_models(task_type=task_type)

        if not available_models:
            logger.warning("No available models for fallback")
            return None

        # اگر فقط یک مدل فعال بود، همان را برگردان
        if len(available_models) == 1:
            fallback = available_models[0].id
            logger.info(f"Only one model available, using {fallback} as fallback for {disabled_model_id}")
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
                    logger.debug(f"Profile for {model.id}: overall={profile.overall_score}, tier={profile.tier}")
                else:
                    profile_scores[model.id] = {'overall': 50.0, 'accuracy': 50.0, 'tier': 'C', 'task_score': 50.0}

            logger.info(f"🔴 Loaded profiles for {len(profile_scores)} models for smart fallback")

        except Exception as e:
            logger.warning(f"Could not load model profiles for fallback: {e}")
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
            logger.info(f"🔴 Found smart fallback for {disabled_model_id}: {best_fallback} (score: {best_score}, tier: {best_tier})")

            # لاگ همه گزینه‌ها برای debug
            logger.debug(f"All fallback options: {[(m[0], m[1], m[3]) for m in scored_models[:5]]}")
            return best_fallback

        return None

    def get_enabled_status(self, model_id: str) -> bool:
        """بررسی فعال بودن مدل در دیتابیس"""
        import logging
        logger = logging.getLogger(__name__)

        try:
            from ..core.database import get_db
            from ..models.ai_profile import ModelSettings
            db = next(get_db())
            db_setting = db.query(ModelSettings).filter(ModelSettings.model_id == model_id).first()
            if db_setting:
                is_enabled = bool(db_setting.enabled)
                logger.info(f"Model {model_id} enabled status from DB: {is_enabled}")
                return is_enabled
            # اگر تنظیمات نداشت، از registry استفاده کن
            model = get_model(model_id)
            is_enabled = model.enabled if model else False
            logger.info(f"Model {model_id} enabled status from registry: {is_enabled}")
            return is_enabled
        except Exception as e:
            logger.error(f"Error checking model {model_id} enabled status: {e}")
            # 🔴 در صورت خطا، فرض کن غیرفعال است تا fallback کار کند
            return False

    async def generate(
        self,
        model_id: str,
        messages: List[Message],
        max_tokens: int = 4096,
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
        import logging
        logger = logging.getLogger(__name__)

        original_model_id = model_id
        used_fallback = False

        model = get_model(model_id)
        if not model:
            raise AIServiceError(f"Model {model_id} not found", "manager", model_id)

        # 🔴🔴🔴 بررسی فعال بودن مدل - استفاده از متد get_enabled_status
        # این متد هم دیتابیس و هم registry را چک می‌کند
        model_is_enabled = self.get_enabled_status(model_id)
        logger.info(f"🔴 Model {model_id} enabled check: {model_is_enabled}")

        if not model_is_enabled:
            logger.warning(f"🔴 Model {model_id} is DISABLED - looking for fallback...")

            # 🆕 استفاده از fallback به جای خطا
            if allow_fallback:
                fallback_model_id = self.find_fallback_model(model_id, task_type=task_type)
                if fallback_model_id:
                    logger.info(f"✅ Using fallback model {fallback_model_id} instead of disabled {model_id}")
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
                        logger.info(f"✅ No specific fallback, using first available: {model_id}")
                    else:
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
            raise AIServiceError(f"Provider {provider} not available", "manager", model_id)

        response = await service.generate(model_id, messages, max_tokens, temperature, **kwargs)

        # 🆕 اضافه کردن اطلاعات fallback به response
        if used_fallback:
            response.fallback_used = True
            response.original_model_id = original_model_id
            logger.info(f"Response generated using fallback: {original_model_id} -> {model_id}")

        return response

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
