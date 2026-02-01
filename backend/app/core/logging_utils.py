"""
🔴 سیستم لاگ‌گیری خوانا و استاندارد

این ماژول لاگ‌های خوانا و قابل فهم تولید می‌کند که:
1. فرمت یکسان دارند
2. شامل context و جزئیات کافی هستند
3. قابل جستجو و فیلتر هستند
4. برای debug کردن مفید هستند
"""

import logging
import json
from datetime import datetime
from typing import Any, Dict, Optional
from functools import wraps
import traceback
import time


def get_logger(name: str) -> logging.Logger:
    """دریافت logger با نام مشخص"""
    return logging.getLogger(name)


class StructuredLogger:
    """
    لاگر ساختار یافته برای لاگ‌های خوانا

    فرمت لاگ‌ها:
    [SECTION] [ACTION] message | key1=value1 | key2=value2
    """

    def __init__(self, name: str, section: str = None):
        self.logger = logging.getLogger(name)
        self.section = section or name.split('.')[-1].upper()

    def _format_extras(self, extras: Dict[str, Any]) -> str:
        """فرمت کردن اطلاعات اضافی"""
        if not extras:
            return ""
        parts = []
        for k, v in extras.items():
            if isinstance(v, (dict, list)):
                v = json.dumps(v, ensure_ascii=False)[:100]
            elif v is None:
                v = "null"
            parts.append(f"{k}={v}")
        return " | " + " | ".join(parts) if parts else ""

    def _log(self, level: int, action: str, message: str, **extras):
        """لاگ کردن با فرمت استاندارد"""
        formatted = f"[{self.section}] [{action}] {message}{self._format_extras(extras)}"
        self.logger.log(level, formatted)

    # =====================
    # متدهای اصلی لاگ
    # =====================

    def start(self, action: str, **extras):
        """شروع یک عملیات"""
        self._log(logging.INFO, "START", f"🚀 {action}", **extras)

    def end(self, action: str, **extras):
        """پایان یک عملیات"""
        self._log(logging.INFO, "END", f"✅ {action}", **extras)

    def step(self, step_num: int, description: str, **extras):
        """یک مرحله از عملیات"""
        self._log(logging.INFO, f"STEP-{step_num}", f"➡️ {description}", **extras)

    def progress(self, current: int, total: int, message: str = "", **extras):
        """پیشرفت عملیات"""
        percent = (current / total * 100) if total > 0 else 0
        self._log(logging.INFO, "PROGRESS", f"📊 [{current}/{total}] {percent:.0f}% - {message}", **extras)

    def success(self, message: str, **extras):
        """موفقیت"""
        self._log(logging.INFO, "SUCCESS", f"✅ {message}", **extras)

    def warning(self, message: str, **extras):
        """هشدار"""
        self._log(logging.WARNING, "WARNING", f"⚠️ {message}", **extras)

    def error(self, message: str, exception: Exception = None, **extras):
        """خطا"""
        if exception:
            extras["error_type"] = type(exception).__name__
            extras["error_msg"] = str(exception)[:200]
        self._log(logging.ERROR, "ERROR", f"❌ {message}", **extras)

    def debug(self, message: str, **extras):
        """دیباگ"""
        self._log(logging.DEBUG, "DEBUG", f"🔍 {message}", **extras)

    def info(self, message: str, **extras):
        """اطلاعات عمومی"""
        self._log(logging.INFO, "INFO", f"ℹ️ {message}", **extras)

    def data(self, label: str, data: Any, **extras):
        """لاگ کردن داده"""
        if isinstance(data, (dict, list)):
            preview = json.dumps(data, ensure_ascii=False)[:200]
        else:
            preview = str(data)[:200]
        self._log(logging.INFO, "DATA", f"📦 {label}: {preview}", **extras)

    def ai_call(self, model: str, action: str, **extras):
        """فراخوانی AI"""
        self._log(logging.INFO, "AI", f"🤖 [{model}] {action}", **extras)

    def db_operation(self, operation: str, table: str, **extras):
        """عملیات دیتابیس"""
        self._log(logging.INFO, "DB", f"🗄️ {operation} on {table}", **extras)

    def api_request(self, method: str, path: str, **extras):
        """درخواست API"""
        self._log(logging.INFO, "API", f"🌐 {method} {path}", **extras)

    def file_operation(self, operation: str, path: str, **extras):
        """عملیات فایل"""
        self._log(logging.INFO, "FILE", f"📁 {operation}: {path}", **extras)


def log_operation(section: str = None, action: str = None):
    """
    دکوراتور برای لاگ کردن خودکار عملیات

    Usage:
        @log_operation(section="HEALTH", action="analyze")
        async def analyze_project(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = StructuredLogger(func.__module__, section)
            op_action = action or func.__name__

            start_time = time.time()
            logger.start(op_action, function=func.__name__)

            try:
                result = await func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.end(op_action, elapsed=f"{elapsed:.2f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"{op_action} failed", exception=e, elapsed=f"{elapsed:.2f}s")
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = StructuredLogger(func.__module__, section)
            op_action = action or func.__name__

            start_time = time.time()
            logger.start(op_action, function=func.__name__)

            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.end(op_action, elapsed=f"{elapsed:.2f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"{op_action} failed", exception=e, elapsed=f"{elapsed:.2f}s")
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


# =====================
# لاگرهای از پیش تعریف شده برای بخش‌های مختلف
# =====================

# لاگر برای auto-setup
auto_setup_logger = StructuredLogger("app.services.project_auto_setup", "AUTO-SETUP")

# لاگر برای health analysis
health_logger = StructuredLogger("app.api.routes.project_health", "HEALTH")

# لاگر برای AI manager
ai_logger = StructuredLogger("app.services.ai_manager", "AI")

# لاگر برای فیلدها
field_logger = StructuredLogger("app.api.routes.project_memory", "FIELD")

# لاگر برای GitHub
github_logger = StructuredLogger("app.services.github_service", "GITHUB")

# لاگر برای Chat
chat_logger = StructuredLogger("app.api.routes.chat", "CHAT")

# لاگر برای Settings
settings_logger = StructuredLogger("app.api.routes.settings", "SETTINGS")

# لاگر برای Deploy
deploy_logger = StructuredLogger("app.services.deploy_service", "DEPLOY")
