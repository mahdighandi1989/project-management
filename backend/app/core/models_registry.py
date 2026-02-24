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
            ModelCapability.LONG_CONTEXT,
            ModelCapability.THINKING
        ],
        max_tokens=65536,
        context_window=1048576,
        strengths=["long-context", "multimodal", "video", "reasoning", "thinking"],
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
            ModelCapability.THINKING
        ],
        max_tokens=65536,
        context_window=1048576,
        strengths=["speed", "cost-effective", "video", "thinking"],
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
            ModelCapability.IMAGE_ANALYSIS
        ],
        max_tokens=8192,
        context_window=1048576,
        strengths=["speed", "cost-effective", "video"],
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
}

# ===========================================
# Alias های سازگاری
# ===========================================
MODEL_ALIASES: Dict[str, str] = {
    "gpt4": "gpt-4o",
    "gpt-4": "gpt-4-turbo",
    "gpt-4-vision": "gpt-4o",
    "claude": "claude-sonnet-4-20250514",
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
