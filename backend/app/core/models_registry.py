"""
رجیستری مدل‌های AI
همه مدل‌ها با قابلیت‌ها، تنظیمات و اولویت‌هایشان
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, ConfigDict
from enum import Enum


class ModelProvider(str, Enum):
    """Provider های مختلف AI"""
    OPENAI = "openai"
    CLAUDE = "claude"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"
    OPENROUTER = "openrouter"
    GROQ = "groq"
    PERPLEXITY = "perplexity"  # 🆕 Perplexity AI
    # 🆕 (Cloud Code centralization) — Claude Code OAuth token engine.
    # یک provider مجزا تا در صفحهٔ مدل‌ها به‌عنوان یک ردیف مستقل قابل
    # toggle شود و preferred_for مشخص کند کجاها (auto-runner / single-task /
    # inspector chat / creator engine) از این engine استفاده کنند. خود
    # token از env (`CLAUDE_CODE_OAUTH_TOKEN`) خوانده می‌شود — این entry
    # فقط switchboard کاربر است.
    CLOUD_CODE = "cloud_code"


class ModelCapability(str, Enum):
    """قابلیت‌های مدل‌ها"""
    TEXT = "text"
    CODE = "code"
    REASONING = "reasoning"
    VISION = "vision"
    IMAGE_ANALYSIS = "image-analysis"
    IMAGE_GENERATION = "image-generation"
    FAST_RESPONSE = "fast-response"
    LONG_CONTEXT = "long-context"
    THINKING = "thinking"
    MULTIMODAL = "multimodal"
    # 🆕 (Stage 1 — multimodal extraction) قابلیت‌های پیشرفته‌تر
    # برای انتخاب «بهترین مدل بصری» در زمان استخراج فایل.
    VIDEO_UNDERSTANDING = "video-understanding"    # تحلیل ویدئو (فریم + صدا)
    AUDIO_UNDERSTANDING = "audio-understanding"    # رونویسی/تحلیل صوت
    DOCUMENT_UNDERSTANDING = "document-understanding"  # PDF/DOCX/XLSX/...


class AIModel(BaseModel):
    """تعریف یک مدل AI"""
    id: str
    provider: ModelProvider
    name: str
    endpoint: str
    capabilities: List[ModelCapability]
    max_tokens: int = 16384
    context_window: int = 128000
    strengths: List[str] = []
    weaknesses: List[str] = []
    cost_per_1k_tokens: float = 0.01
    priority: int = 5
    enabled: bool = True
    supports_images: bool = False
    supports_video: bool = False
    is_image_generator: bool = False

    # توجه: use_enum_values=False تا enum ها حفظ بشن برای مقایسه
    model_config = ConfigDict(use_enum_values=False)


# ===========================================
# رجیستری کامل مدل‌ها
# ===========================================

MODEL_REGISTRY: Dict[str, AIModel] = {
    # ===========================================
    # OpenAI Models
    # ===========================================
    "gpt-4o": AIModel(
        id="gpt-4o",
        provider=ModelProvider.OPENAI,
        name="GPT-4o",
        endpoint="https://api.openai.com/v1/chat/completions",
        capabilities=[
            ModelCapability.TEXT,
            ModelCapability.IMAGE_ANALYSIS,
            ModelCapability.VISION,
            ModelCapability.MULTIMODAL,
            ModelCapability.DOCUMENT_UNDERSTANDING,
            ModelCapability.CODE,
            ModelCapability.REASONING
        ],
        max_tokens=16384,
        context_window=128000,
        strengths=["image-analysis", "multimodal", "reasoning"],
        weaknesses=["cost"],
        cost_per_1k_tokens=0.005,
        priority=1,
        supports_images=True
    ),

    "gpt-4o-mini": AIModel(
        id="gpt-4o-mini",
        provider=ModelProvider.OPENAI,
        name="GPT-4o Mini",
        endpoint="https://api.openai.com/v1/chat/completions",
        capabilities=[
            ModelCapability.TEXT,
            ModelCapability.IMAGE_ANALYSIS,
            ModelCapability.FAST_RESPONSE
        ],
        max_tokens=16384,
        context_window=128000,
        strengths=["speed", "cost-effective", "multimodal"],
        weaknesses=["complex-reasoning"],
        cost_per_1k_tokens=0.00015,
        priority=2,
        supports_images=True
    ),

    "gpt-4-turbo": AIModel(
        id="gpt-4-turbo",
        provider=ModelProvider.OPENAI,
        name="GPT-4 Turbo",
        endpoint="https://api.openai.com/v1/chat/completions",
        capabilities=[
            ModelCapability.TEXT,
            ModelCapability.CODE,
            ModelCapability.REASONING,
            ModelCapability.LONG_CONTEXT
        ],
        max_tokens=16384,
        context_window=128000,
        strengths=["reasoning", "code", "complex-tasks"],
        cost_per_1k_tokens=0.01,
        priority=1
    ),

    "gpt-3.5-turbo": AIModel(
        id="gpt-3.5-turbo",
        provider=ModelProvider.OPENAI,
        name="GPT-3.5 Turbo",
        endpoint="https://api.openai.com/v1/chat/completions",
        capabilities=[
            ModelCapability.TEXT,
            ModelCapability.CODE,
            ModelCapability.FAST_RESPONSE
        ],
        max_tokens=16384,
        context_window=16385,
        strengths=["speed", "cost-effective"],
        weaknesses=["complex-reasoning"],
        cost_per_1k_tokens=0.0015,
        priority=3
    ),

    "dall-e-3": AIModel(
        id="dall-e-3",
        provider=ModelProvider.OPENAI,
        name="DALL-E 3",
        endpoint="https://api.openai.com/v1/images/generations",
        capabilities=[ModelCapability.IMAGE_GENERATION],
        max_tokens=0,
        context_window=4000,
        strengths=["creative-images", "artistic", "text-in-images"],
        weaknesses=["only-images", "cost"],
        cost_per_1k_tokens=0,
        priority=1,
        is_image_generator=True
    ),

    # ===========================================
    # Claude Models (Anthropic)
    # ===========================================
    "claude-opus-4-7": AIModel(
        id="claude-opus-4-7",
        provider=ModelProvider.CLAUDE,
        name="Claude Opus 4.7",
        endpoint="https://api.anthropic.com/v1/messages",
        capabilities=[
            ModelCapability.TEXT,
            ModelCapability.CODE,
            ModelCapability.REASONING,
            ModelCapability.VISION,
            ModelCapability.IMAGE_ANALYSIS,
            ModelCapability.MULTIMODAL,
            ModelCapability.LONG_CONTEXT,
        ],
        max_tokens=32000,
        context_window=200000,
        strengths=["reasoning", "code", "agentic", "vision", "most-capable", "latest"],
        weaknesses=["cost"],
        cost_per_1k_tokens=0.015,
        priority=1,
        supports_images=True
    ),

    "claude-sonnet-4-6": AIModel(
        id="claude-sonnet-4-6",
        provider=ModelProvider.CLAUDE,
        name="Claude Sonnet 4.6",
        endpoint="https://api.anthropic.com/v1/messages",
        capabilities=[
            ModelCapability.TEXT,
            ModelCapability.CODE,
            ModelCapability.REASONING,
            ModelCapability.VISION,
            ModelCapability.IMAGE_ANALYSIS,
            ModelCapability.MULTIMODAL,
            ModelCapability.LONG_CONTEXT,
        ],
        max_tokens=64000,
        context_window=200000,
        strengths=["reasoning", "code", "agentic", "vision", "balance", "long-context", "latest"],
        cost_per_1k_tokens=0.003,
        priority=1,
        supports_images=True
    ),

    "claude-haiku-4-5-20251001": AIModel(
        id="claude-haiku-4-5-20251001",
        provider=ModelProvider.CLAUDE,
        name="Claude Haiku 4.5",
        endpoint="https://api.anthropic.com/v1/messages",
        capabilities=[
            ModelCapability.TEXT,
            ModelCapability.CODE,
            ModelCapability.REASONING,
            ModelCapability.VISION,
            ModelCapability.IMAGE_ANALYSIS,
            ModelCapability.FAST_RESPONSE,
        ],
        max_tokens=32000,
        context_window=200000,
        strengths=["speed", "cost-effective", "vision", "code"],
        weaknesses=["complex-reasoning"],
        cost_per_1k_tokens=0.001,
        priority=2,
        supports_images=True
    ),

    "claude-sonnet-4-20250514": AIModel(
        id="claude-sonnet-4-20250514",
        provider=ModelProvider.CLAUDE,
        name="Claude Sonnet 4",
        endpoint="https://api.anthropic.com/v1/messages",
        capabilities=[
            ModelCapability.TEXT,
            ModelCapability.CODE,
            ModelCapability.REASONING,
            ModelCapability.LONG_CONTEXT
        ],
        max_tokens=16384,
        context_window=200000,
        strengths=["reasoning", "long-context", "accuracy", "latest"],
        cost_per_1k_tokens=0.003,
        priority=1
    ),

    "claude-3-5-sonnet-20241022": AIModel(
        id="claude-3-5-sonnet-20241022",
        provider=ModelProvider.CLAUDE,
        name="Claude 3.5 Sonnet",
        endpoint="https://api.anthropic.com/v1/messages",
        capabilities=[
            ModelCapability.TEXT,
            ModelCapability.CODE,
            ModelCapability.REASONING,
            ModelCapability.LONG_CONTEXT
        ],
        max_tokens=8192,
        context_window=200000,
        strengths=["reasoning", "accuracy", "balance"],
        cost_per_1k_tokens=0.003,
        priority=2
    ),

    "claude-3-haiku-20240307": AIModel(
        id="claude-3-haiku-20240307",
        provider=ModelProvider.CLAUDE,
        name="Claude 3 Haiku",
        endpoint="https://api.anthropic.com/v1/messages",
        capabilities=[
            ModelCapability.TEXT,
            ModelCapability.FAST_RESPONSE
        ],
        max_tokens=8192,
        context_window=200000,
        strengths=["speed", "cost-effective"],
        weaknesses=["complex-reasoning"],
        cost_per_1k_tokens=0.00025,
        priority=3
    ),

    # ===========================================
    # DeepSeek Models
    # ===========================================
    "deepseek-chat": AIModel(
        id="deepseek-chat",
        provider=ModelProvider.DEEPSEEK,
        name="DeepSeek Chat",
        endpoint="https://api.deepseek.com/chat/completions",
        capabilities=[
            ModelCapability.TEXT,
            ModelCapability.CODE,
            ModelCapability.REASONING
        ],
        max_tokens=16384,
        context_window=32000,
        strengths=["code", "reasoning", "cost-effective"],
        weaknesses=["multimodal"],
        cost_per_1k_tokens=0.0014,
        priority=2
    ),

    "deepseek-coder": AIModel(
        id="deepseek-coder",
        provider=ModelProvider.DEEPSEEK,
        name="DeepSeek Coder",
        endpoint="https://api.deepseek.com/chat/completions",
        capabilities=[
            ModelCapability.CODE,
            ModelCapability.TEXT
        ],
        max_tokens=16384,
        context_window=16000,
        strengths=["code", "programming"],
        weaknesses=["general-text"],
        cost_per_1k_tokens=0.0014,
        priority=1
    ),

    "deepseek-reasoner": AIModel(
        id="deepseek-reasoner",
        provider=ModelProvider.DEEPSEEK,
        name="DeepSeek Reasoner",
        endpoint="https://api.deepseek.com/chat/completions",
        capabilities=[
            ModelCapability.REASONING,
            ModelCapability.CODE,
            ModelCapability.THINKING
        ],
        max_tokens=16384,
        context_window=64000,
        strengths=["reasoning", "math", "logic", "physics"],
        weaknesses=["speed", "cost"],
        cost_per_1k_tokens=0.0055,
        priority=1
    ),

    # ===========================================
    # Gemini Models (Google)
    # ===========================================
    "gemini-2.5-pro": AIModel(
        id="gemini-2.5-pro",
        provider=ModelProvider.GEMINI,
        name="Gemini 2.5 Pro",
        endpoint="https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent",
        capabilities=[
            ModelCapability.TEXT,
            ModelCapability.CODE,
            ModelCapability.IMAGE_ANALYSIS,
            ModelCapability.VISION,
            ModelCapability.MULTIMODAL,
            ModelCapability.LONG_CONTEXT,
            ModelCapability.THINKING,
            ModelCapability.VIDEO_UNDERSTANDING,
            ModelCapability.AUDIO_UNDERSTANDING,
            ModelCapability.DOCUMENT_UNDERSTANDING,
        ],
        max_tokens=65536,
        context_window=1048576,
        strengths=["long-context", "multimodal", "video", "audio", "reasoning", "thinking"],
        cost_per_1k_tokens=0.00125,
        priority=1,
        supports_images=True,
        supports_video=True
    ),

    "gemini-2.5-flash": AIModel(
        id="gemini-2.5-flash",
        provider=ModelProvider.GEMINI,
        name="Gemini 2.5 Flash",
        endpoint="https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        capabilities=[
            ModelCapability.TEXT,
            ModelCapability.FAST_RESPONSE,
            ModelCapability.IMAGE_ANALYSIS,
            ModelCapability.VISION,
            ModelCapability.MULTIMODAL,
            ModelCapability.LONG_CONTEXT,
            ModelCapability.THINKING,
            ModelCapability.VIDEO_UNDERSTANDING,
            ModelCapability.AUDIO_UNDERSTANDING,
            ModelCapability.DOCUMENT_UNDERSTANDING,
        ],
        max_tokens=65536,
        context_window=1048576,
        strengths=["speed", "cost-effective", "video", "audio", "thinking", "extraction-default"],
        cost_per_1k_tokens=0.00015,
        priority=2,
        supports_images=True,
        supports_video=True
    ),

    "gemini-2.0-flash": AIModel(
        id="gemini-2.0-flash",
        provider=ModelProvider.GEMINI,
        name="Gemini 2.0 Flash",
        endpoint="https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
        capabilities=[
            ModelCapability.TEXT,
            ModelCapability.FAST_RESPONSE,
            ModelCapability.IMAGE_ANALYSIS,
            ModelCapability.VISION,
            ModelCapability.MULTIMODAL,
            ModelCapability.LONG_CONTEXT,
            ModelCapability.VIDEO_UNDERSTANDING,
            ModelCapability.AUDIO_UNDERSTANDING,
            ModelCapability.DOCUMENT_UNDERSTANDING,
        ],
        max_tokens=8192,
        context_window=1048576,
        strengths=["speed", "cost-effective", "video", "audio"],
        cost_per_1k_tokens=0.00001,
        priority=3,
        supports_images=True,
        supports_video=True
    ),

    "imagen-3": AIModel(
        id="imagen-3",
        provider=ModelProvider.GEMINI,
        name="Imagen 3",
        endpoint="https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict",
        capabilities=[ModelCapability.IMAGE_GENERATION],
        max_tokens=0,
        context_window=0,
        strengths=["high-quality-images", "photorealistic"],
        weaknesses=["only-images"],
        cost_per_1k_tokens=0.04,
        priority=2,
        is_image_generator=True
    ),

    # ===========================================
    # Perplexity Models 🆕
    # ===========================================
    "sonar-pro": AIModel(
        id="sonar-pro",
        provider=ModelProvider.PERPLEXITY,
        name="Sonar Pro",
        endpoint="https://api.perplexity.ai/chat/completions",
        capabilities=[
            ModelCapability.TEXT,
            ModelCapability.REASONING,
            ModelCapability.LONG_CONTEXT
        ],
        max_tokens=8192,
        context_window=200000,
        strengths=["search", "research", "up-to-date-info", "citations"],
        weaknesses=["code-generation"],
        cost_per_1k_tokens=0.003,
        priority=1
    ),

    "sonar": AIModel(
        id="sonar",
        provider=ModelProvider.PERPLEXITY,
        name="Sonar",
        endpoint="https://api.perplexity.ai/chat/completions",
        capabilities=[
            ModelCapability.TEXT,
            ModelCapability.FAST_RESPONSE
        ],
        max_tokens=8192,
        context_window=128000,
        strengths=["search", "speed", "cost-effective", "citations"],
        weaknesses=["complex-reasoning"],
        cost_per_1k_tokens=0.001,
        priority=2
    ),

    "sonar-reasoning": AIModel(
        id="sonar-reasoning",
        provider=ModelProvider.PERPLEXITY,
        name="Sonar Reasoning",
        endpoint="https://api.perplexity.ai/chat/completions",
        capabilities=[
            ModelCapability.TEXT,
            ModelCapability.REASONING,
            ModelCapability.THINKING
        ],
        max_tokens=16384,
        context_window=128000,
        strengths=["reasoning", "logic", "research", "citations"],
        cost_per_1k_tokens=0.005,
        priority=1
    ),
    # ===========================================
    # 🆕 (Cloud Code centralization) — Claude Code OAuth engine.
    # یک ردیف "swappable" در صفحهٔ مدل‌ها. وضعیت enabled و preferred_for
    # از ModelSettings DB خوانده می‌شود؛ این entry فقط metadata است.
    # cost_per_1k_tokens=0 چون از اشتراک Claude Code استفاده می‌کند نه
    # API key متری. id="cloud_code" — همان شناسه‌ای که consumer ها از آن
    # برای پرس‌وجوی وضعیت استفاده می‌کنند.
    # ===========================================
    "cloud_code": AIModel(
        id="cloud_code",
        provider=ModelProvider.CLOUD_CODE,
        name="Cloud Code (Claude OAuth)",
        endpoint="https://api.anthropic.com/v1/messages",
        capabilities=[
            ModelCapability.TEXT,
            ModelCapability.CODE,
            ModelCapability.REASONING,
            ModelCapability.LONG_CONTEXT,
            ModelCapability.THINKING,
            # 🆕 (extraction routing) — Claude Sonnet/Opus از طریق
            # OAuth ساپورت می‌کند: تصویر (image content blocks)،
            # PDF (document content blocks). صوت و ویدیو ساپورت ندارد
            # — برای آن‌ها picker خودکار به Gemini fallback می‌کند.
            ModelCapability.VISION,
            ModelCapability.IMAGE_ANALYSIS,
            ModelCapability.DOCUMENT_UNDERSTANDING,
            ModelCapability.MULTIMODAL,
        ],
        max_tokens=32768,
        context_window=200000,
        strengths=[
            "claude_subscription",
            "auto_tier_pick",
            "tool_use",
            "single_source_oauth",
            "vision_via_oauth",
            "pdf_documents_via_oauth",
        ],
        cost_per_1k_tokens=0.0,
        priority=1,
        enabled=True,
        supports_images=True,
    ),
}

# ===========================================
# Alias های سازگاری
# ===========================================
MODEL_ALIASES: Dict[str, str] = {
    "gpt4": "gpt-4o",
    "gpt-4": "gpt-4-turbo",
    "gpt-4-vision": "gpt-4o",
    "claude": "claude-sonnet-4-6",  # 🆕 پیش‌فرض = جدیدترین Sonnet
    "claude-opus": "claude-opus-4-7",
    "claude-sonnet": "claude-sonnet-4-6",
    "claude-haiku": "claude-haiku-4-5-20251001",
    "claude-4": "claude-sonnet-4-20250514",
    "claude-3": "claude-3-5-sonnet-20241022",
    "deepseek": "deepseek-chat",
    "gemini": "gemini-2.0-flash",
    "perplexity": "sonar-pro",  # 🆕
}


def get_model(model_id: str) -> Optional[AIModel]:
    """دریافت مدل با ID یا alias"""
    # اول بررسی alias
    resolved_id = MODEL_ALIASES.get(model_id, model_id)
    return MODEL_REGISTRY.get(resolved_id)


def get_models_by_provider(provider: ModelProvider) -> List[AIModel]:
    """دریافت همه مدل‌های یک provider"""
    return [m for m in MODEL_REGISTRY.values() if m.provider == provider]


def get_models_by_capability(capability: ModelCapability) -> List[AIModel]:
    """دریافت همه مدل‌های با یک قابلیت خاص"""
    return [m for m in MODEL_REGISTRY.values() if capability in m.capabilities]


def get_enabled_models() -> List[AIModel]:
    """دریافت همه مدل‌های فعال"""
    return [m for m in MODEL_REGISTRY.values() if m.enabled]


def get_image_generator_models() -> List[AIModel]:
    """دریافت مدل‌های تولید تصویر"""
    return [m for m in MODEL_REGISTRY.values() if m.is_image_generator]


def get_vision_models() -> List[AIModel]:
    """دریافت مدل‌های با قابلیت تحلیل تصویر"""
    return [m for m in MODEL_REGISTRY.values() if m.supports_images]


# ====================================================================
# 🆕 (Stage 1 — multimodal extraction) — mapping mime → capability
# و انتخاب «بهترین مدل» برای استخراج متن از فایل پیوست تسک.
# ====================================================================

def mime_to_required_capability(mime_type: str) -> ModelCapability:
    """تطبیق mime → قابلیت مدل لازم برای استخراج کامل.

    - تصویر → IMAGE_ANALYSIS
    - ویدئو → VIDEO_UNDERSTANDING
    - صوت → AUDIO_UNDERSTANDING
    - سند (PDF/DOCX/XLSX/...) → DOCUMENT_UNDERSTANDING
    - متن خام → TEXT (هر مدل enabled کفایت می‌کند)
    """
    mt = (mime_type or "").lower().strip()
    if mt.startswith("image/"):
        return ModelCapability.IMAGE_ANALYSIS
    if mt.startswith("video/"):
        return ModelCapability.VIDEO_UNDERSTANDING
    if mt.startswith("audio/"):
        return ModelCapability.AUDIO_UNDERSTANDING
    if mt in (
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/rtf",
    ):
        return ModelCapability.DOCUMENT_UNDERSTANDING
    if mt.startswith("text/"):
        return ModelCapability.TEXT
    # پیش‌فرض ایمن — مدل بصری چندوجهی
    return ModelCapability.MULTIMODAL


# پیش‌فرض extraction — کاربر در gemini-2.5-flash استقرار را تأیید کرد.
# قابل بازنویسی توسط هر caller از طریق `preferred_model_id`.
DEFAULT_EXTRACTION_MODEL_ID: str = "gemini-2.5-flash"


def pick_best_extraction_model(
    mime_type: str,
    *,
    enabled_only: bool = True,
    db_enabled_ids: Optional[List[str]] = None,
    prefer_provider: Optional[ModelProvider] = ModelProvider.GEMINI,
    preferred_model_id: Optional[str] = None,
    require_api_key: bool = True,
) -> Optional[AIModel]:
    """انتخاب بهترین مدل enabled برای استخراج فایلی با mime مشخص.

    منطق ranking:
      0. اگر `preferred_model_id` (یا default Flash) قابلیت لازم را دارد
         و enabled است → همان (داینامیک: کاربر می‌تواند از /models این
         پیش‌فرض را عوض کند).
      1. مدل باید قابلیت لازم (mime_to_required_capability) را داشته باشد.
      2. اگر `db_enabled_ids` داده شده، فقط آن‌ها (فیلتر نهایی روی panel
         «مدیریت مدل‌ها»). اگر None، صرفاً `m.enabled` registry را نگاه کن.
      3. 🛡 (audit fix CRITICAL) `require_api_key=True` (پیش‌فرض): provider
         API key باید واقعاً در env تنظیم باشد. اگر نه، مدل واجد شرایط نیست
         (جلوگیری از fallback silent به مدل غیرvision در ai_manager که
         خروجی غلط «نمی‌توانم تصویر را ببینم» تولید می‌کند).
      4. priority پایین‌تر = بهتر (در registry تعریف شده).
      5. در صورت تساوی، مدل با `prefer_provider` ترجیح داده می‌شود
         (پیش‌فرض Gemini — multimodal native).

    خروجی: AIModel یا None اگر هیچ مدلی نه قابلیت دارد نه enabled است.
    """
    required = mime_to_required_capability(mime_type)

    # 🆕 (Cloud Code centralization — Fix #3) — قبل از همه‌چیز، اگر کاربر
    # در صفحهٔ مدل‌ها `file_extraction` را برای cloud_code تیک زده باشد
    # و این MIME در محدودهٔ ساپورت Claude OAuth باشد (تصویر / PDF /
    # document)، cloud_code را برگردان. هزینه از اشتراک OAuth کم می‌شود،
    # نه از کلید Gemini.
    #
    # برای صوت/ویدیو این شرط false می‌شود (cloud_code آن capability را
    # ندارد در capabilities خود) و picker طبق روال عادی Gemini را
    # برمی‌گرداند — fallback خودکار.
    #
    # 🚨 (Fix #3 audit follow-up — critical) — وقتی caller صراحتاً
    # require_api_key=True پاس می‌دهد، cloud_code را skip کن. این برای
    # مسیر fallback است: وقتی cloud_code call شکست خورد، `_ai_extract_text`
    # دوباره picker را با require_api_key=True صدا می‌زند تا یک مدل
    # *واقعی* (Gemini, OpenAI, ...) برگردد. اگر cloud_code را اینجا هم
    # برگردانیم، fallback همان cloud_code را می‌گیرد و دوباره fail می‌کند
    # — کاربر outage می‌بیند. cloud_code provider در env_map نیست، پس
    # require_api_key=True منطقاً یعنی "از cloud_code نمی‌خواهیم".
    if (
        not require_api_key
        and required in (
            ModelCapability.VISION,
            ModelCapability.IMAGE_ANALYSIS,
            ModelCapability.DOCUMENT_UNDERSTANDING,
            ModelCapability.MULTIMODAL,
        )
    ):
        try:
            from ..services.cloud_code_service import (
                cloud_code_setting_is_enabled_for,
            )
            if cloud_code_setting_is_enabled_for("file_extraction"):
                cc = MODEL_REGISTRY.get("cloud_code")
                if cc is not None and required in cc.capabilities:
                    return cc
        except Exception:
            # silent fallback به منطق legacy — این path هرگز نباید
            # crash کند، فقط priority می‌دهد.
            pass

    # 🛡 (audit fix CRITICAL) — کش provider key availability
    import os as _os
    _key_available: Dict[ModelProvider, bool] = {}
    _provider_env_map = {
        ModelProvider.OPENAI: "OPENAI_API_KEY",
        ModelProvider.CLAUDE: "CLAUDE_API_KEY",
        ModelProvider.GEMINI: "GEMINI_API_KEY",
        ModelProvider.DEEPSEEK: "DEEPSEEK_API_KEY",
        ModelProvider.OPENROUTER: "OPENROUTER_API_KEY",
        ModelProvider.GROQ: "GROQ_API_KEY",
        ModelProvider.PERPLEXITY: "PERPLEXITY_API_KEY",
    }

    def _provider_has_key(prov: ModelProvider) -> bool:
        if prov in _key_available:
            return _key_available[prov]
        env_var = _provider_env_map.get(prov)
        has = bool(_os.environ.get(env_var or "", "").strip()) if env_var else False
        _key_available[prov] = has
        return has

    # 🛡 (audit fix CRITICAL #2) — کش DB enabled status. ai_manager از
    # `ModelSettings.enabled` به‌عنوان منبع اصلی استفاده می‌کند. اگر اینجا
    # هم چک نکنیم، picker یک مدل برمی‌گرداند که ai_manager بعداً به
    # deepseek fallback می‌کند (silent failure).
    _db_enabled_cache: Dict[str, bool] = {}

    def _db_enabled(model_id: str) -> bool:
        if model_id in _db_enabled_cache:
            return _db_enabled_cache[model_id]
        try:
            from ..core.database import SessionLocal
            from ..models.ai_profile import ModelSettings as _MS
            db = SessionLocal()
            try:
                row = db.query(_MS).filter(_MS.model_id == model_id).first()
                if row is not None:
                    val = bool(row.enabled)
                else:
                    # اگر row در DB نیست، registry default (معمولاً True)
                    val = True
            finally:
                db.close()
        except Exception:
            # DB در دسترس نیست — fall back به True (نگذاریم crash کند)
            val = True
        _db_enabled_cache[model_id] = val
        return val

    def _qualifies(m: AIModel) -> bool:
        if enabled_only and not m.enabled:
            return False
        if db_enabled_ids is not None and m.id not in db_enabled_ids:
            return False
        if require_api_key and not _provider_has_key(m.provider):
            return False
        # 🛡 (audit fix CRITICAL #2) — اگر DB گفته disabled، رد کن
        if enabled_only and not _db_enabled(m.id):
            return False
        if required == ModelCapability.TEXT:
            return True
        return required in m.capabilities

    # گام ۰ — اگر preferred_model_id ست شده، آن. وگرنه DB > hard-coded default.
    if preferred_model_id:
        pref_id = preferred_model_id
    else:
        pref_id = None
        # تلاش برای خواندن از DB (silent fail اگر import circular)
        try:
            from ..services.oversight_settings import get_default_extraction_model_id_from_db
            pref_id = get_default_extraction_model_id_from_db()
        except Exception:
            pref_id = None
        if not pref_id:
            pref_id = DEFAULT_EXTRACTION_MODEL_ID
    if pref_id:
        resolved_pref_id = MODEL_ALIASES.get(pref_id, pref_id)
        pref_model = MODEL_REGISTRY.get(resolved_pref_id)
        if pref_model and _qualifies(pref_model):
            return pref_model

    # گام ۱ — fallback به ranking عمومی
    candidates: List[AIModel] = [m for m in MODEL_REGISTRY.values() if _qualifies(m)]
    if not candidates:
        return None

    def _rank(m: AIModel) -> tuple:
        prov_pref = 0 if (prefer_provider and m.provider == prefer_provider) else 1
        return (m.priority, prov_pref, m.cost_per_1k_tokens)

    candidates.sort(key=_rank)
    return candidates[0]


def list_extraction_model_candidates(
    mime_type: str,
    *,
    include_disabled: bool = True,
) -> List[AIModel]:
    """لیست همهٔ مدل‌های توانمند برای این mime (هم enabled هم disabled).
    برای UI «مدل بصری فعال نیست — کدام را فعال کنیم؟».
    """
    required = mime_to_required_capability(mime_type)
    out: List[AIModel] = []
    for m in MODEL_REGISTRY.values():
        if not include_disabled and not m.enabled:
            continue
        if required == ModelCapability.TEXT:
            out.append(m)
            continue
        if required in m.capabilities:
            out.append(m)
    out.sort(key=lambda m: (m.priority, m.cost_per_1k_tokens))
    return out
