"""
⚙️ Dynamic Configuration Service - سیستم تنظیمات پویا
تنظیمات قابل تغییر به صورت خودکار و دستی
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


# =====================================
# مدل‌های تنظیمات
# =====================================

@dataclass
class ModelConfig:
    """تنظیمات یک مدل"""
    model_id: str
    max_tokens: int = 4000
    max_context: int = 128000
    timeout: int = 120
    temperature: float = 0.7
    enabled: bool = True
    priority: int = 1
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0


@dataclass
class ProcessingConfig:
    """تنظیمات پردازش"""
    max_prompt_length: int = 100000
    max_tokens_per_model: int = 4000
    max_tokens_scoring: int = 1500
    max_tokens_judge: int = 2500
    max_tokens_summary: int = 3000
    max_model_time: int = 120
    request_timeout: int = 180
    max_concurrent_requests: int = 5
    auto_retry: bool = True
    retry_count: int = 3
    retry_delay: float = 1.0


@dataclass
class StorageConfig:
    """تنظیمات ذخیره‌سازی"""
    max_upload_size_mb: int = 100
    max_chunk_size_mb: int = 25
    allowed_extensions: List[str] = field(default_factory=lambda: [
        'txt', 'md', 'json', 'csv', 'xml', 'html', 'css', 'js', 'ts',
        'py', 'java', 'cpp', 'go', 'rs', 'pdf', 'doc', 'docx', 'xls', 'xlsx',
        'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'mp3', 'wav', 'mp4', 'webm',
        'zip', 'tar', 'gz'
    ])
    github_enabled: bool = True
    local_storage_path: str = "./storage"


@dataclass
class SystemConfig:
    """تنظیمات کل سیستم"""
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    models: Dict[str, ModelConfig] = field(default_factory=dict)
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    version: int = 1


# =====================================
# پیکربندی پیش‌فرض مدل‌ها
# =====================================

DEFAULT_MODEL_CONFIGS = {
    # Claude
    "claude-sonnet-4-20250514": ModelConfig(
        model_id="claude-sonnet-4-20250514",
        max_tokens=8192,
        max_context=200000,
        timeout=180,
        priority=1,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015
    ),
    "claude-3-5-sonnet-20241022": ModelConfig(
        model_id="claude-3-5-sonnet-20241022",
        max_tokens=8192,
        max_context=200000,
        timeout=180,
        priority=2
    ),
    # OpenAI
    "gpt-4-turbo": ModelConfig(
        model_id="gpt-4-turbo",
        max_tokens=4096,
        max_context=128000,
        timeout=120,
        priority=3,
        cost_per_1k_input=0.01,
        cost_per_1k_output=0.03
    ),
    "gpt-4o": ModelConfig(
        model_id="gpt-4o",
        max_tokens=4096,
        max_context=128000,
        timeout=120,
        priority=2
    ),
    "gpt-4o-mini": ModelConfig(
        model_id="gpt-4o-mini",
        max_tokens=16384,
        max_context=128000,
        timeout=60,
        priority=5
    ),
    # Gemini
    "gemini-2.5-pro": ModelConfig(
        model_id="gemini-2.5-pro",
        max_tokens=8192,
        max_context=1000000,
        timeout=180,
        priority=2
    ),
    "gemini-2.0-flash": ModelConfig(
        model_id="gemini-2.0-flash",
        max_tokens=8192,
        max_context=1000000,
        timeout=60,
        priority=4
    ),
    # DeepSeek
    "deepseek-coder": ModelConfig(
        model_id="deepseek-coder",
        max_tokens=8192,
        max_context=128000,
        timeout=120,
        priority=3
    ),
    "deepseek-chat": ModelConfig(
        model_id="deepseek-chat",
        max_tokens=8192,
        max_context=128000,
        timeout=120,
        priority=4
    ),
}


# =====================================
# سرویس تنظیمات پویا
# =====================================

class DynamicConfigService:
    """
    سرویس مدیریت تنظیمات پویا

    قابلیت‌ها:
    - خواندن/نوشتن تنظیمات از فایل JSON
    - تنظیم خودکار بر اساس توانایی مدل
    - Override دستی
    - تاریخچه تغییرات
    """

    def __init__(self, config_path: str = "./data/config"):
        self.config_path = Path(config_path)
        self.config_path.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_path / "system_config.json"
        self.history_file = self.config_path / "config_history.json"

        self._config: SystemConfig = SystemConfig()
        self._history: List[Dict] = []

        self._load_config()

    def _load_config(self):
        """بارگذاری تنظیمات از فایل"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self._config = SystemConfig(
                    processing=ProcessingConfig(**data.get('processing', {})),
                    storage=StorageConfig(**data.get('storage', {})),
                    models={
                        k: ModelConfig(**v)
                        for k, v in data.get('models', {}).items()
                    },
                    updated_at=data.get('updated_at', datetime.now().isoformat()),
                    version=data.get('version', 1)
                )
            except Exception as e:
                logger.error(f"Error loading config: {e}")
                self._initialize_defaults()
        else:
            self._initialize_defaults()
            self._save_config()

    def _initialize_defaults(self):
        """مقداردهی اولیه با پیش‌فرض‌ها"""
        self._config = SystemConfig(
            processing=ProcessingConfig(),
            storage=StorageConfig(),
            models=DEFAULT_MODEL_CONFIGS.copy()
        )

    def _save_config(self):
        """ذخیره تنظیمات در فایل"""
        try:
            data = {
                'processing': asdict(self._config.processing),
                'storage': asdict(self._config.storage),
                'models': {k: asdict(v) for k, v in self._config.models.items()},
                'updated_at': self._config.updated_at,
                'version': self._config.version
            }

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"Error saving config: {e}")

    def _add_history(self, change_type: str, details: Dict):
        """افزودن به تاریخچه تغییرات"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": change_type,
            "details": details
        }
        self._history.append(entry)

        # نگه داشتن فقط 100 تغییر آخر
        self._history = self._history[-100:]

        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self._history, f, ensure_ascii=False, indent=2)
        except:
            pass

    # =====================================
    # دریافت تنظیمات
    # =====================================

    def get_processing_config(self) -> ProcessingConfig:
        """دریافت تنظیمات پردازش"""
        return self._config.processing

    def get_storage_config(self) -> StorageConfig:
        """دریافت تنظیمات ذخیره‌سازی"""
        return self._config.storage

    def get_model_config(self, model_id: str) -> Optional[ModelConfig]:
        """دریافت تنظیمات یک مدل"""
        return self._config.models.get(model_id)

    def get_all_model_configs(self) -> Dict[str, ModelConfig]:
        """دریافت تنظیمات همه مدل‌ها"""
        return self._config.models

    def get_full_config(self) -> Dict:
        """دریافت کل تنظیمات به صورت dict"""
        return {
            'processing': asdict(self._config.processing),
            'storage': asdict(self._config.storage),
            'models': {k: asdict(v) for k, v in self._config.models.items()},
            'updated_at': self._config.updated_at,
            'version': self._config.version
        }

    # =====================================
    # تغییر تنظیمات
    # =====================================

    def update_processing_config(self, **kwargs) -> ProcessingConfig:
        """بروزرسانی تنظیمات پردازش"""
        old_values = asdict(self._config.processing)

        for key, value in kwargs.items():
            if hasattr(self._config.processing, key):
                setattr(self._config.processing, key, value)

        self._config.updated_at = datetime.now().isoformat()
        self._config.version += 1
        self._save_config()

        self._add_history("processing_update", {
            "old": old_values,
            "new": asdict(self._config.processing),
            "changed_fields": list(kwargs.keys())
        })

        return self._config.processing

    def update_storage_config(self, **kwargs) -> StorageConfig:
        """بروزرسانی تنظیمات ذخیره‌سازی"""
        old_values = asdict(self._config.storage)

        for key, value in kwargs.items():
            if hasattr(self._config.storage, key):
                setattr(self._config.storage, key, value)

        self._config.updated_at = datetime.now().isoformat()
        self._config.version += 1
        self._save_config()

        self._add_history("storage_update", {
            "changed_fields": list(kwargs.keys())
        })

        return self._config.storage

    def update_model_config(self, model_id: str, **kwargs) -> Optional[ModelConfig]:
        """بروزرسانی تنظیمات یک مدل"""
        if model_id not in self._config.models:
            # ایجاد تنظیمات جدید
            self._config.models[model_id] = ModelConfig(model_id=model_id)

        config = self._config.models[model_id]
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)

        self._config.updated_at = datetime.now().isoformat()
        self._config.version += 1
        self._save_config()

        self._add_history("model_update", {
            "model_id": model_id,
            "changed_fields": list(kwargs.keys())
        })

        return config

    # =====================================
    # تنظیم خودکار
    # =====================================

    def auto_adjust_for_task(
        self,
        task_type: str,
        content_length: int = 0,
        file_count: int = 0,
        complexity: str = "medium"
    ) -> Dict[str, Any]:
        """
        تنظیم خودکار پارامترها بر اساس نوع وظیفه

        Args:
            task_type: نوع وظیفه (code_generation, analysis, debate, etc.)
            content_length: طول محتوا
            file_count: تعداد فایل‌ها
            complexity: پیچیدگی (simple, medium, complex)

        Returns:
            پارامترهای توصیه شده
        """
        base_config = self._config.processing

        # تنظیمات پایه بر اساس پیچیدگی
        complexity_multipliers = {
            "simple": 0.5,
            "medium": 1.0,
            "complex": 1.5,
            "very_complex": 2.0
        }
        multiplier = complexity_multipliers.get(complexity, 1.0)

        # تنظیمات بر اساس نوع وظیفه
        task_configs = {
            "code_generation": {
                "max_tokens": int(8000 * multiplier),
                "timeout": int(180 * multiplier),
                "temperature": 0.3
            },
            "analysis": {
                "max_tokens": int(6000 * multiplier),
                "timeout": int(120 * multiplier),
                "temperature": 0.5
            },
            "debate": {
                "max_tokens": int(4000 * multiplier),
                "timeout": int(90 * multiplier),
                "temperature": 0.7
            },
            "creative": {
                "max_tokens": int(4000 * multiplier),
                "timeout": int(90 * multiplier),
                "temperature": 0.9
            },
            "research": {
                "max_tokens": int(8000 * multiplier),
                "timeout": int(180 * multiplier),
                "temperature": 0.4
            },
            "file_analysis": {
                "max_tokens": int(8000 * multiplier),
                "timeout": int(240 * multiplier),
                "temperature": 0.3
            }
        }

        config = task_configs.get(task_type, {
            "max_tokens": int(4000 * multiplier),
            "timeout": 120,
            "temperature": 0.7
        })

        # تنظیم بر اساس طول محتوا
        if content_length > 50000:
            config["timeout"] = int(config["timeout"] * 1.5)
            config["max_tokens"] = min(config["max_tokens"] + 2000, 16000)

        if content_length > 100000:
            config["timeout"] = int(config["timeout"] * 2)
            config["max_tokens"] = min(config["max_tokens"] + 4000, 16000)

        # تنظیم بر اساس تعداد فایل
        if file_count > 3:
            config["timeout"] = int(config["timeout"] * 1.5)

        return config

    def get_recommended_models(
        self,
        task_type: str,
        available_providers: List[str]
    ) -> List[str]:
        """
        دریافت مدل‌های پیشنهادی برای یک وظیفه
        """
        task_model_preferences = {
            "code_generation": [
                "claude-sonnet-4-20250514", "deepseek-coder", "gpt-4-turbo"
            ],
            "analysis": [
                "gemini-2.5-pro", "claude-sonnet-4-20250514", "gpt-4o"
            ],
            "debate": [
                "claude-sonnet-4-20250514", "gpt-4-turbo", "gemini-2.5-pro"
            ],
            "creative": [
                "claude-sonnet-4-20250514", "gpt-4-turbo", "gemini-2.5-pro"
            ],
            "research": [
                "gemini-2.5-pro", "gpt-4-turbo", "claude-sonnet-4-20250514"
            ]
        }

        preferred = task_model_preferences.get(task_type, [])

        # فیلتر بر اساس provider های در دسترس
        available = []
        for model_id in preferred:
            model_config = self._config.models.get(model_id)
            if model_config and model_config.enabled:
                # بررسی provider
                provider = self._get_model_provider(model_id)
                if provider in available_providers:
                    available.append(model_id)

        return available

    def _get_model_provider(self, model_id: str) -> str:
        """تشخیص provider از model_id"""
        if model_id.startswith("claude"):
            return "anthropic"
        elif model_id.startswith("gpt"):
            return "openai"
        elif model_id.startswith("gemini"):
            return "google"
        elif model_id.startswith("deepseek"):
            return "deepseek"
        return "unknown"

    # =====================================
    # تاریخچه
    # =====================================

    def get_history(self, limit: int = 20) -> List[Dict]:
        """دریافت تاریخچه تغییرات"""
        return self._history[-limit:]

    def reset_to_defaults(self):
        """بازگشت به تنظیمات پیش‌فرض"""
        self._initialize_defaults()
        self._config.version += 1
        self._save_config()

        self._add_history("reset", {"message": "Reset to defaults"})


# Singleton
_config_service: Optional[DynamicConfigService] = None


def get_config_service() -> DynamicConfigService:
    global _config_service
    if _config_service is None:
        _config_service = DynamicConfigService()
    return _config_service
