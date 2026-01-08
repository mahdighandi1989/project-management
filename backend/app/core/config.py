"""
تنظیمات مرکزی سیستم
همه چیز از environment variables یا فایل config خوانده می‌شود
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Optional, Dict, List, Union
import os
import json


class Settings(BaseSettings):
    """تنظیمات اصلی سیستم - همه چیز داینامیک و قابل تغییر"""

    # ===========================================
    # اطلاعات پایه
    # ===========================================
    APP_NAME: str = "AI Debate & Project Management System"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = Field(default=False, description="حالت Debug")
    ENVIRONMENT: str = Field(default="development", description="محیط اجرا")

    # ===========================================
    # API Keys - همه از محیط خوانده می‌شود
    # ===========================================
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="کلید OpenAI")
    CLAUDE_API_KEY: Optional[str] = Field(default=None, description="کلید Anthropic Claude")
    GEMINI_API_KEY: Optional[str] = Field(default=None, description="کلید Google Gemini")
    DEEPSEEK_API_KEY: Optional[str] = Field(default=None, description="کلید DeepSeek")
    OPENROUTER_API_KEY: Optional[str] = Field(default=None, description="کلید OpenRouter")
    GROQ_API_KEY: Optional[str] = Field(default=None, description="کلید Groq")

    # ===========================================
    # تنظیمات سرور
    # ===========================================
    HOST: str = Field(default="0.0.0.0", description="آدرس سرور")
    PORT: int = Field(default=8000, description="پورت سرور")
    WORKERS: int = Field(default=4, description="تعداد worker ها")

    # ===========================================
    # تنظیمات دیتابیس
    # ===========================================
    DATABASE_URL: str = Field(
        default="sqlite:///./data/app.db",
        description="آدرس دیتابیس"
    )

    # ===========================================
    # تنظیمات پردازش AI
    # ===========================================
    MAX_TOKENS_PER_MODEL: int = Field(default=4000, description="حداکثر توکن برای هر مدل")
    MAX_TOKENS_FOR_SCORING: int = Field(default=1000, description="حداکثر توکن برای امتیازدهی")
    MAX_TOKENS_FOR_JUDGE: int = Field(default=2000, description="حداکثر توکن برای داوری")
    MAX_TOKENS_FOR_SUMMARY: int = Field(default=2500, description="حداکثر توکن برای خلاصه")
    MAX_PROMPT_LENGTH: int = Field(default=100000, description="حداکثر طول پرامپت")

    # تنظیمات timeout
    REQUEST_TIMEOUT: int = Field(default=120, description="timeout درخواست (ثانیه)")
    MAX_MODEL_TIME: int = Field(default=60, description="حداکثر زمان برای هر مدل")

    # ===========================================
    # تنظیمات CORS - به صورت string برای سازگاری با env
    # ===========================================
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:8000,*",
        description="آدرس‌های مجاز CORS (با کاما جدا شده)"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """تبدیل CORS_ORIGINS به لیست"""
        if not self.CORS_ORIGINS:
            return ["*"]
        # اگر JSON array باشه
        if self.CORS_ORIGINS.startswith("["):
            try:
                return json.loads(self.CORS_ORIGINS)
            except:
                pass
        # اگر با کاما جدا شده باشه
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    # ===========================================
    # تنظیمات ذخیره‌سازی
    # ===========================================
    UPLOAD_DIR: str = Field(default="./uploads", description="پوشه آپلود فایل‌ها")
    MAX_UPLOAD_SIZE: int = Field(default=500 * 1024 * 1024, description="حداکثر سایز آپلود (500MB)")

    # ===========================================
    # تنظیمات JWT
    # ===========================================
    SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        description="کلید رمزنگاری JWT"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24, description="مدت اعتبار توکن")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def get_available_providers(self) -> Dict[str, bool]:
        """لیست provider های فعال با API key - مستقیم از environment میخونه"""
        return {
            "openai": bool(os.environ.get("OPENAI_API_KEY")),
            "claude": bool(os.environ.get("CLAUDE_API_KEY")),
            "gemini": bool(os.environ.get("GEMINI_API_KEY")),
            "deepseek": bool(os.environ.get("DEEPSEEK_API_KEY")),
            "openrouter": bool(os.environ.get("OPENROUTER_API_KEY")),
            "groq": bool(os.environ.get("GROQ_API_KEY")),
        }

    def get_api_key(self, provider: str) -> Optional[str]:
        """دریافت API key یک provider - مستقیم از environment میخونه"""
        keys = {
            "openai": os.environ.get("OPENAI_API_KEY"),
            "claude": os.environ.get("CLAUDE_API_KEY"),
            "gemini": os.environ.get("GEMINI_API_KEY"),
            "deepseek": os.environ.get("DEEPSEEK_API_KEY"),
            "openrouter": os.environ.get("OPENROUTER_API_KEY"),
            "groq": os.environ.get("GROQ_API_KEY"),
        }
        return keys.get(provider)


def get_settings() -> Settings:
    """تنظیمات - بدون cache برای خواندن fresh از environment"""
    return Settings()


# Instance سراسری - یک بار در startup ساخته میشه
settings = Settings()
