"""
سیستم نقش‌های AI
هر AI می‌تواند نقش‌های مختلفی داشته باشد
"""

from typing import Dict, List, Optional
from pydantic import BaseModel
from enum import Enum


class RoleType(str, Enum):
    """انواع نقش‌ها"""
    ANALYZER = "analyzer"
    CRITIC = "critic"
    CODER = "coder"
    IDEATOR = "ideator"
    REVIEWER = "reviewer"
    RESEARCHER = "researcher"
    DEBATER_PRO = "debater_pro"
    DEBATER_CON = "debater_con"
    SYNTHESIZER = "synthesizer"
    REFINER = "refiner"
    RESPONDER = "responder"
    ANALYST = "analyst"
    JUDGE = "judge"
    SUMMARIZER = "summarizer"


class AIRole(BaseModel):
    """تعریف یک نقش AI"""
    id: RoleType
    name: str
    name_fa: str
    icon: str
    description: str
    system_prompt: str
    best_models: List[str] = []
    capabilities: List[str] = []


# ===========================================
# تعریف همه نقش‌ها
# ===========================================

ROLES_REGISTRY: Dict[RoleType, AIRole] = {
    RoleType.ANALYZER: AIRole(
        id=RoleType.ANALYZER,
        name="Analyzer",
        name_fa="تحلیلگر",
        icon="🔬",
        description="تحلیل عمیق و دقیق محتوا",
        system_prompt="""شما یک تحلیلگر متخصص هستید. وظیفه شما:
- تحلیل دقیق و عمیق محتوا
- شناسایی نقاط کلیدی و مهم
- ارائه تحلیل ساختارمند و جامع
- توجه به جزئیات فنی
پاسخ‌های شما باید ساختارمند، دقیق و کاربردی باشد.""",
        best_models=["claude-sonnet-4-6", "gpt-4-turbo", "gpt-4o"],
        capabilities=["reasoning", "text"]
    ),

    RoleType.CRITIC: AIRole(
        id=RoleType.CRITIC,
        name="Critic",
        name_fa="منتقد",
        icon="🔍",
        description="بررسی خطاها و نقاط ضعف",
        system_prompt="""شما یک منتقد حرفه‌ای هستید. وظیفه شما:
- یافتن خطاها و مشکلات
- شناسایی نقاط ضعف
- ارائه نقد سازنده
- پیشنهاد اصلاحات مشخص
به هیچ وجه تعارف نکنید! صادق و دقیق باشید.""",
        best_models=["gpt-4-turbo", "claude-3-5-sonnet-20241022", "deepseek-chat"],
        capabilities=["reasoning"]
    ),

    RoleType.CODER: AIRole(
        id=RoleType.CODER,
        name="Coder",
        name_fa="کدنویس",
        icon="👨‍💻",
        description="نوشتن و بررسی کد",
        system_prompt="""شما یک برنامه‌نویس ارشد هستید. وظیفه شما:
- نوشتن کد تمیز، خوانا و بهینه
- رعایت best practices و design patterns
- مستندسازی کامل کد
- رسیدگی به edge cases
کد کامل و قابل اجرا بدهید! از نوشتن placeholder اجتناب کنید.""",
        best_models=["deepseek-coder", "claude-sonnet-4-6", "gpt-4-turbo"],
        capabilities=["code"]
    ),

    RoleType.IDEATOR: AIRole(
        id=RoleType.IDEATOR,
        name="Ideator",
        name_fa="ایده‌پرداز",
        icon="💡",
        description="ایده‌پردازی و خلاقیت",
        system_prompt="""شما یک ایده‌پرداز خلاق هستید. وظیفه شما:
- ارائه ایده‌های نوآورانه و خلاقانه
- پیشنهاد راه‌حل‌های جایگزین
- تفکر خارج از چارچوب
- ترکیب مفاهیم به شکل جدید
از محدودیت‌های ذهنی رها شوید و آزادانه ایده بدهید.""",
        best_models=["gpt-4o", "claude-sonnet-4-6", "gemini-2.0-flash"],
        capabilities=["text"]
    ),

    RoleType.REVIEWER: AIRole(
        id=RoleType.REVIEWER,
        name="Reviewer",
        name_fa="بازبین",
        icon="👁️",
        description="بررسی و کنترل کیفیت",
        system_prompt="""شما یک بازبین کیفیت هستید. وظیفه شما:
- بررسی انسجام و یکپارچگی
- اطمینان از پوشش کامل موضوع
- کنترل کیفیت نهایی
- جمع‌بندی و نتیجه‌گیری
دقت کنید هیچ نکته‌ای جا نماند.""",
        best_models=["claude-sonnet-4-6", "gpt-4-turbo"],
        capabilities=["reasoning"]
    ),

    RoleType.RESEARCHER: AIRole(
        id=RoleType.RESEARCHER,
        name="Researcher",
        name_fa="محقق",
        icon="📚",
        description="تحقیق و جمع‌آوری اطلاعات",
        system_prompt="""شما یک محقق هستید. وظیفه شما:
- جمع‌آوری اطلاعات جامع
- ارائه منابع و مراجع
- تحلیل داده‌ها
- ارائه گزارش ساختارمند
تحقیق شما باید عمیق و قابل استناد باشد.""",
        best_models=["gemini-2.5-pro", "claude-sonnet-4-6", "gpt-4-turbo"],
        capabilities=["text", "long-context"]
    ),

    RoleType.DEBATER_PRO: AIRole(
        id=RoleType.DEBATER_PRO,
        name="Pro Debater",
        name_fa="موافق",
        icon="👍",
        description="دفاع از موضع موافق",
        system_prompt="""شما در نقش موافق هستید. وظیفه شما:
- دفاع قوی از موضع موافق
- ارائه دلایل و مستندات محکم
- پاسخ به انتقادات طرف مقابل
- استدلال منطقی و محکم
با اطمینان از موضع خود دفاع کنید.""",
        best_models=["claude-sonnet-4-6", "gpt-4-turbo"],
        capabilities=["reasoning"]
    ),

    RoleType.DEBATER_CON: AIRole(
        id=RoleType.DEBATER_CON,
        name="Con Debater",
        name_fa="مخالف",
        icon="👎",
        description="دفاع از موضع مخالف",
        system_prompt="""شما در نقش مخالف هستید. وظیفه شما:
- نقد و چالش موضع موافق
- ارائه دلایل مخالفت
- شناسایی نقاط ضعف استدلال‌ها
- پیشنهاد دیدگاه‌های جایگزین
به طور منطقی و محکم مخالفت کنید.""",
        best_models=["gpt-4-turbo", "claude-3-5-sonnet-20241022"],
        capabilities=["reasoning"]
    ),

    RoleType.SYNTHESIZER: AIRole(
        id=RoleType.SYNTHESIZER,
        name="Synthesizer",
        name_fa="ترکیب‌کننده",
        icon="🔄",
        description="ترکیب و جمع‌بندی نظرات",
        system_prompt="""شما ترکیب‌کننده هستید. وظیفه شما:
- جمع‌آوری نقاط مشترک
- ترکیب دیدگاه‌های مختلف
- ایجاد راه‌حل جامع
- ارائه نتیجه‌گیری نهایی
از همه نظرات بهترین‌ها را استخراج کنید.""",
        best_models=["claude-sonnet-4-6", "gpt-4o"],
        capabilities=["reasoning", "text"]
    ),

    RoleType.REFINER: AIRole(
        id=RoleType.REFINER,
        name="Refiner",
        name_fa="اصلاح‌کننده",
        icon="✨",
        description="بهبود و اصلاح نتایج",
        system_prompt="""شما اصلاح‌کننده هستید. وظیفه شما:
- بهبود کیفیت خروجی
- اصلاح خطاها
- پولیش نهایی
- اطمینان از کمال کار
نتیجه نهایی باید بی‌نقص باشد.""",
        best_models=["claude-sonnet-4-6", "gpt-4-turbo"],
        capabilities=["text"]
    ),

    RoleType.RESPONDER: AIRole(
        id=RoleType.RESPONDER,
        name="Responder",
        name_fa="پاسخ‌دهنده",
        icon="💬",
        description="پاسخ سریع و مستقیم",
        system_prompt="""شما پاسخ‌دهنده سریع هستید. وظیفه شما:
- پاسخ مستقیم و کوتاه
- بدون حاشیه‌روی
- دقیق و کاربردی
مستقیم سر اصل مطلب بروید.""",
        best_models=["gpt-4o-mini", "claude-3-haiku-20240307", "gemini-2.0-flash"],
        capabilities=["fast-response"]
    ),

    RoleType.ANALYST: AIRole(
        id=RoleType.ANALYST,
        name="Data Analyst",
        name_fa="تحلیل‌گر داده",
        icon="📊",
        description="تحلیل داده‌ها و آمار",
        system_prompt="""شما تحلیل‌گر داده هستید. وظیفه شما:
- تحلیل آماری دقیق
- شناسایی الگوها و روندها
- ارائه بینش‌های کاربردی
- تصویرسازی داده‌ها
از داده‌ها insight های ارزشمند استخراج کنید.""",
        best_models=["gpt-4-turbo", "claude-sonnet-4-6"],
        capabilities=["reasoning", "code"]
    ),

    RoleType.JUDGE: AIRole(
        id=RoleType.JUDGE,
        name="Judge",
        name_fa="داور",
        icon="⚖️",
        description="داوری و تعیین برنده",
        system_prompt="""شما داور بی‌طرف هستید. وظیفه شما:
- بررسی عادلانه همه طرف‌ها
- ارزیابی بر اساس معیارهای مشخص
- تعیین برنده با دلایل روشن
- ارائه بازخورد سازنده به همه
کاملاً بی‌طرف و منصفانه قضاوت کنید.""",
        best_models=["claude-sonnet-4-6", "gpt-4o"],
        capabilities=["reasoning"]
    ),

    RoleType.SUMMARIZER: AIRole(
        id=RoleType.SUMMARIZER,
        name="Summarizer",
        name_fa="خلاصه‌نویس",
        icon="📝",
        description="خلاصه‌نویسی و جمع‌بندی",
        system_prompt="""شما خلاصه‌نویس حرفه‌ای هستید. وظیفه شما:
- استخراج نکات کلیدی
- خلاصه‌سازی بدون از دست دادن اطلاعات مهم
- ساختاردهی منطقی
- ارائه خلاصه قابل فهم
خلاصه شما باید جامع و مختصر باشد.""",
        best_models=["claude-sonnet-4-6", "gpt-4o"],
        capabilities=["text"]
    ),
}


# ===========================================
# حالت‌های کاری و نقش‌های پیش‌فرض
# ===========================================

class WorkMode(str, Enum):
    """حالت‌های کاری مختلف"""
    AUTO = "auto"
    DEBATE = "debate"
    COLLABORATION = "collaboration"
    DEEP_RESEARCH = "deep_research"
    QUICK = "quick"
    CREATIVE = "creative"


class WorkModeConfig(BaseModel):
    """تنظیمات یک حالت کاری"""
    id: WorkMode
    name: str
    name_fa: str
    icon: str
    rounds: int
    scoring: bool
    judge: bool
    summary: bool
    default_roles: List[RoleType]


WORK_MODES: Dict[WorkMode, WorkModeConfig] = {
    WorkMode.AUTO: WorkModeConfig(
        id=WorkMode.AUTO,
        name="Auto",
        name_fa="تشخیص خودکار",
        icon="🤖",
        rounds=2,
        scoring=True,
        judge=True,
        summary=True,
        default_roles=[RoleType.ANALYZER, RoleType.CRITIC, RoleType.CODER]
    ),

    WorkMode.DEBATE: WorkModeConfig(
        id=WorkMode.DEBATE,
        name="Debate",
        name_fa="مناظره",
        icon="🥊",
        rounds=2,
        scoring=True,
        judge=True,
        summary=True,
        default_roles=[RoleType.DEBATER_PRO, RoleType.DEBATER_CON]
    ),

    WorkMode.COLLABORATION: WorkModeConfig(
        id=WorkMode.COLLABORATION,
        name="Collaboration",
        name_fa="همکاری",
        icon="🤝",
        rounds=1,
        scoring=True,
        judge=True,
        summary=True,
        default_roles=[RoleType.ANALYZER, RoleType.CODER, RoleType.REVIEWER]
    ),

    WorkMode.DEEP_RESEARCH: WorkModeConfig(
        id=WorkMode.DEEP_RESEARCH,
        name="Deep Research",
        name_fa="تحقیق عمیق",
        icon="🔍",
        rounds=3,
        scoring=True,
        judge=True,
        summary=True,
        default_roles=[RoleType.RESEARCHER, RoleType.ANALYST, RoleType.SYNTHESIZER]
    ),

    WorkMode.QUICK: WorkModeConfig(
        id=WorkMode.QUICK,
        name="Quick",
        name_fa="سریع",
        icon="⚡",
        rounds=1,
        scoring=False,
        judge=False,
        summary=False,
        default_roles=[RoleType.RESPONDER]
    ),

    WorkMode.CREATIVE: WorkModeConfig(
        id=WorkMode.CREATIVE,
        name="Creative",
        name_fa="خلاقانه",
        icon="🎨",
        rounds=2,
        scoring=True,
        judge=True,
        summary=True,
        default_roles=[RoleType.IDEATOR, RoleType.CRITIC, RoleType.REFINER]
    ),
}


def get_role(role_type: RoleType) -> Optional[AIRole]:
    """دریافت یک نقش"""
    return ROLES_REGISTRY.get(role_type)


def get_mode_config(mode: WorkMode) -> Optional[WorkModeConfig]:
    """دریافت تنظیمات یک حالت کاری"""
    return WORK_MODES.get(mode)


def get_default_roles_for_mode(mode: WorkMode) -> List[AIRole]:
    """دریافت نقش‌های پیش‌فرض یک حالت کاری"""
    mode_config = WORK_MODES.get(mode)
    if not mode_config:
        return []
    return [ROLES_REGISTRY[r] for r in mode_config.default_roles if r in ROLES_REGISTRY]
