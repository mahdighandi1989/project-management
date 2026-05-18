"""سرویس مرکزی نوتیفیکیشن — نسخه ۲.

ویژگی‌ها:
- ۱۲+ نوع event مستقل (verify_done/partial/not_done/regressed، scan_*،
  idea_created، pr_created، …)
- per-event sound: برای هر event مشخص می‌شود با صدا (notification) یا silent
- هشتگ خودکار: #event #priority #project برای جستجوی راحت
- Inline keyboard: زیر هر پیام دکمه‌های لینک به پنل
- prefs در notification_prefs.json (runtime-mutable)
- credentials از environment (silent skip اگر نباشد)
- webhook handler برای /start /menu /status commands ربات
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import smtplib
import ssl
from abc import ABC, abstractmethod
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def _resolve_storage_dir() -> Path:
    candidates = [
        os.environ.get("NOTIFICATION_STORAGE", "").strip(),
        os.environ.get("OVERSIGHT_STORAGE", "").strip(),
        "./storage/notifications",
        "/tmp/notifications",
    ]
    for c in candidates:
        if not c:
            continue
        try:
            p = Path(c)
            p.mkdir(parents=True, exist_ok=True)
            test = p / ".write_test"
            test.write_text("ok", encoding="utf-8")
            test.unlink(missing_ok=True)
            return p
        except Exception:
            continue
    return Path("/tmp")


_STORAGE = _resolve_storage_dir()
_PREFS_FILE = _STORAGE / "notification_prefs.json"
# 🆕 (Index Hub) state پیام index pin شده — message_id ذخیره می‌شود تا edit شود
_INDEX_STATE_FILE = _STORAGE / "telegram_index_state.json"


def _read_index_state() -> Dict[str, Any]:
    try:
        if _INDEX_STATE_FILE.exists():
            with open(_INDEX_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f) or {}
    except Exception as e:
        logger.warning(f"index state read failed: {e}")
    return {}


def _write_index_state(state: Dict[str, Any]) -> None:
    try:
        tmp = _INDEX_STATE_FILE.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        tmp.replace(_INDEX_STATE_FILE)
    except Exception as e:
        logger.warning(f"index state write failed: {e}")


# 🆕 (Persistent Reply Keyboard) منوی ثابت زیر input box
# Telegram دو نوع keyboard دارد:
#   - inline (زیر یک پیام مشخص) — برای flow های مرحله‌ای استفاده می‌کنیم
#   - reply (زیر input، در همه پیام‌ها) — منوی ثابت برای دسترسی سریع
# این persistent است: یک‌بار با /start یا /menu ست می‌شود و تا remove نشود می‌ماند.
PERSISTENT_REPLY_KEYBOARD: Dict[str, Any] = {
    "keyboard": [
        [{"text": "📋 ایندکس"}, {"text": "🆕 تسک جدید"}],
        [{"text": "🔔 یادآوری جدید"}, {"text": "📚 شناسنامه"}],
        [{"text": "🚀 پروژه جدید"}, {"text": "💰 مصرف AI"}],
        [{"text": "📊 وضعیت"}, {"text": "📋 منو"}],
    ],
    "resize_keyboard": True,
    "is_persistent": True,
    "input_field_placeholder": "/menu یا روی دکمه‌های زیر کلیک کن",
}

# نقشهٔ alias های متنی → command واقعی
# وقتی کاربر روی دکمهٔ reply keyboard کلیک می‌کند، متن دکمه ارسال می‌شود
TEXT_ALIASES: Dict[str, str] = {
    "📋 ایندکس": "/index",
    "🆕 تسک جدید": "/new_task",
    "🔔 یادآوری جدید": "/reminder",
    "📚 شناسنامه": "/codex",
    "🚀 پروژه جدید": "/new_project",
    "📊 وضعیت": "/status",
    "📋 منو": "/menu",
    "💰 مصرف AI": "/usage",
    "❌ بستن منو": "/hide_menu",
}


# ---------------------------------------------------------------------------
# Event registry — منبع واحد برای تعریف هر event
# ---------------------------------------------------------------------------

EVENT_REGISTRY: Dict[str, Dict[str, Any]] = {
    # Verify events
    "verify_done": {
        "label": "✅ Verify موفق",
        "help": "وقتی verify status = done باشد",
        "default_enabled": True,
        "default_sound": True,
        "icon": "✅",
    },
    "verify_partial": {
        "label": "🟡 Verify partial",
        "help": "وقتی بخشی از معیارها برآورده شده",
        "default_enabled": True,
        "default_sound": False,
        "icon": "🟡",
    },
    "verify_not_done": {
        "label": "❌ Verify not_done",
        "help": "وقتی هیچ تغییر معناداری انجام نشده",
        "default_enabled": True,
        "default_sound": False,
        "icon": "❌",
    },
    "verify_regressed": {
        "label": "🔴 Verify regressed",
        "help": "وقتی تغییرات وضعیت را بدتر کرده‌اند (بحرانی)",
        "default_enabled": True,
        "default_sound": True,
        "icon": "🔴",
    },
    "verify_clarification": {
        "label": "🟠 نیاز به توضیح",
        "help": "verify نتیجهٔ مبهم گرفت — کاربر باید بررسی کند",
        "default_enabled": True,
        "default_sound": False,
        "icon": "🟠",
    },
    # Scan events
    "scan_started": {
        "label": "🚀 شروع Deep Scan",
        "help": "وقتی Deep Scan آغاز می‌شود",
        "default_enabled": False,
        "default_sound": False,
        "icon": "🚀",
    },
    "scan_done": {
        "label": "🔬 پایان Deep Scan",
        "help": "وقتی Deep Scan کامل شد (با تعداد یافته‌ها/تسک‌ها)",
        "default_enabled": True,
        "default_sound": False,
        "icon": "🔬",
    },
    "scan_critical_found": {
        "label": "🚨 یافتهٔ critical در scan",
        "help": "اگر در scan یک یا چند مورد critical پیدا شد",
        "default_enabled": True,
        "default_sound": True,
        "icon": "🚨",
    },
    "scan_failed": {
        "label": "💥 خطا در scan",
        "help": "اگر scan با error متوقف شد",
        "default_enabled": True,
        "default_sound": True,
        "icon": "💥",
    },
    # Task lifecycle
    "task_created": {
        "label": "📌 تسک جدید (auto)",
        "help": "وقتی scan تسک جدید می‌سازد — معمولاً پر سر و صدا",
        "default_enabled": False,
        "default_sound": False,
        "icon": "📌",
    },
    "idea_created": {
        "label": "💡 ایده ثبت شد",
        "help": "وقتی کاربر ایده جدید ثبت می‌کند و پرامپت ساخته می‌شود",
        "default_enabled": True,
        "default_sound": False,
        "icon": "💡",
    },
    # 🔔 Reminder events
    "reminder_due": {
        "label": "🔔 یادآوری موعد رسیده",
        "help": "وقتی یک یادآوری به زمان موعدش می‌رسد و باید به کاربر اطلاع داده شود",
        "default_enabled": True,
        "default_sound": True,  # با صدا — کاربر باید بفهمد
        "icon": "🔔",
    },
    "reminder_snoozed": {
        "label": "⏰ یادآوری به تعویق افتاد",
        "help": "وقتی کاربر یادآوری را snooze می‌کند",
        "default_enabled": True,
        "default_sound": False,
        "icon": "⏰",
    },
    "reminder_done": {
        "label": "✅ یادآوری انجام شد",
        "help": "وقتی یادآوری توسط کاربر done/archived می‌شود",
        "default_enabled": True,
        "default_sound": False,
        "icon": "✅",
    },
    # 🆕 (Stage 10 audit fix #3) — eventهای اختصاصی برای فعال/غیرفعال موقت مدل
    "model_temp_activated": {
        "label": "🔓 مدل موقتاً فعال شد",
        "help": "وقتی مدل بصری برای extraction یک فایل پیوست موقتاً فعال می‌شود",
        "default_enabled": True,
        "default_sound": True,  # مهم — کاربر باید بداند مدل فعال شده
        "icon": "🔓",
    },
    "model_temp_reverted": {
        "label": "🔒 مدل به حالت قبل برگشت",
        "help": "وقتی فعال‌سازی موقت مدل پس از اتمام کار، خودکار revert می‌شود",
        "default_enabled": True,
        "default_sound": False,
        "icon": "🔒",
    },
    "pr_created": {
        "label": "🔀 PR ساخته شد",
        "help": "وقتی Inspector یک PR از تسک می‌سازد",
        "default_enabled": True,
        "default_sound": True,
        "icon": "🔀",
    },
    # System
    "manual_test": {
        "label": "🧪 تست دستی",
        "help": "برای دکمهٔ «تست ارسال»",
        "default_enabled": True,
        "default_sound": True,
        "icon": "🧪",
    },
    # 🆕 (Daily Report)
    "daily_report": {
        "label": "📊 گزارش روزانهٔ پروژه‌ها",
        "help": "گزارش دوره‌ای جامع از وضعیت همهٔ پروژه‌ها (پیش‌فرض روزی یک‌بار صبح)",
        "default_enabled": True,
        "default_sound": False,
        "icon": "📊",
    },
    # 🆕 (Creator) رویدادهای ساخت پروژه
    "project_created": {
        "label": "🚀 پروژهٔ جدید ساخته شد",
        "help": "وقتی یک پروژه از طریق creator (وب یا ربات) ساخته و push می‌شود",
        "default_enabled": True,
        "default_sound": True,
        "icon": "🚀",
    },
    "project_auto_watched": {
        "label": "👁 پروژه خودکار تحت نظارت قرار گرفت",
        "help": "وقتی یک پروژهٔ جدید به‌صورت خودکار به watched اضافه می‌شود",
        "default_enabled": True,
        "default_sound": False,
        "icon": "👁",
    },
    "creator_failed": {
        "label": "💥 خطا در ساخت پروژه",
        "help": "اگر create_project یا push_to_github fail شد",
        "default_enabled": True,
        "default_sound": True,
        "icon": "💥",
    },
    # 🆕 (Smart Task Lifecycle) رویدادهای چرخهٔ تسک
    "task_duplicate_detected": {
        "label": "🔍 تسک مشابه پیدا شد",
        "help": "هنگام ایجاد دستی تسک، یک یا چند تسک مشابه قبلی یافت شد",
        "default_enabled": True,
        "default_sound": False,
        "icon": "🔍",
    },
    "task_merged": {
        "label": "🔀 ادغام تسک انجام شد",
        "help": "وقتی یک تسک کاندید با تسک موجود ادغام می‌شود",
        "default_enabled": True,
        "default_sound": True,
        "icon": "🔀",
    },
    "prompt_regenerated": {
        "label": "🔄 پرامپت بازتولید شد",
        "help": "پس از regenerate خودکار یا دستی یک پرامپت ناقص",
        "default_enabled": True,
        "default_sound": True,
        "icon": "🔄",
    },
    # 🆕 (Inspector → Oversight Bridge) تسک‌های آمده از بازرس ویژه
    "task_from_inspector": {
        "label": "📥 تسک از بازرس ویژه",
        "help": "وقتی کاربر از بازرس ویژه (در /projects) درخواست را به مرکز نظارت ارسال می‌کند",
        "default_enabled": True,
        "default_sound": True,
        "icon": "📥",
    },
    # 🆕 (Phase 3) — backfill events
    "backfill_ac_needed": {
        "label": "🔬 backfill AC نیاز است",
        "help": "وقتی Phase 3 detection نشان دهد AC هایی هستند که از قابلیت‌های action loop / vision_pair / expected_api_calls استفاده نمی‌کنند",
        "default_enabled": True,
        "default_sound": True,
        "icon": "🔬",
    },
    "backfill_ac_completed": {
        "label": "✅ backfill AC تمام شد",
        "help": "نتیجه پایان backfill (force یا عادی) — خلاصه تعداد enrich شده، خطاها، توزیع method ها",
        "default_enabled": True,
        "default_sound": True,
        "icon": "✅",
    },
    # 🆕 (AI Balance Monitor — Tile 3)
    "ai_balance_low": {
        "label": "💰 موجودی AI کم",
        "help": "موجودی DeepSeek (API) یا budget دستی پایین‌تر از آستانه",
        "default_enabled": True,
        "default_sound": True,
        "icon": "💰",
    },
}


def _build_default_prefs() -> Dict[str, Any]:
    return {
        "events": {k: v["default_enabled"] for k, v in EVENT_REGISTRY.items()},
        "sound": {k: v["default_sound"] for k, v in EVENT_REGISTRY.items()},
        "channels": {
            "telegram": {"enabled": True},
            "email": {"enabled": True},
        },
        "min_priority": "low",
        "include_hashtags": True,
        "include_inline_buttons": True,
        "app_base_url": "",  # مثل https://ai-creator-frontend.onrender.com
        # 🆕 (Daily Report) تنظیمات گزارش دوره‌ای
        "daily_report": {
            "enabled": True,
            "hour_of_day": 8,
            "timezone": "Asia/Tehran",
            "include_recommendations": True,
            "include_top_findings": True,
            "include_creator_section": True,
            "max_projects_in_report": 20,
            "last_sent_at": None,
            "last_sent_status": None,
        },
    }


def _read_prefs() -> Dict[str, Any]:
    defaults = _build_default_prefs()
    try:
        if _PREFS_FILE.exists():
            with open(_PREFS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
                if isinstance(v, dict) and k in defaults and isinstance(defaults[k], dict):
                    defaults[k].update(v)
                else:
                    defaults[k] = v
            # event/sound dicts: اگر event جدیدی اضافه شده، default را پر کن
            for ev, meta in EVENT_REGISTRY.items():
                if ev not in defaults["events"]:
                    defaults["events"][ev] = meta["default_enabled"]
                if ev not in defaults["sound"]:
                    defaults["sound"][ev] = meta["default_sound"]
    except Exception as e:
        logger.warning(f"notification: read prefs failed: {e}")
    return defaults


def _write_prefs(prefs: Dict[str, Any]) -> None:
    try:
        tmp = _PREFS_FILE.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2)
        tmp.replace(_PREFS_FILE)
    except Exception as e:
        logger.warning(f"notification: write prefs failed: {e}")


# ---------------------------------------------------------------------------
# Hashtags & Inline keyboard helpers
# ---------------------------------------------------------------------------

def _sanitize_tag(s: str) -> str:
    """تبدیل رشته به hashtag valid (فقط letters/digits/underscore)."""
    out = []
    for ch in s:
        if ch.isalnum() or ch == "_":
            out.append(ch)
        elif ch in ("/", "-", " ", ".", ":"):
            out.append("_")
    return "".join(out).strip("_")


def build_hashtags(
    event: str, *, project_name: Optional[str] = None, priority: Optional[str] = None,
    extra: Optional[List[str]] = None,
) -> str:
    tags: List[str] = [f"#{_sanitize_tag(event)}"]
    if priority:
        tags.append(f"#{_sanitize_tag(priority)}")
    if project_name:
        tags.append(f"#{_sanitize_tag(project_name)}")
    for e in (extra or []):
        if e:
            tags.append(f"#{_sanitize_tag(e)}")
    return " ".join(tags)


def build_inline_keyboard(
    app_base_url: str, event: str, *,
    watched_id: Optional[str] = None,
    extra_buttons: Optional[List[Dict[str, str]]] = None,
) -> Optional[Dict[str, Any]]:
    """ساخت inline_keyboard برای Telegram. اگر app_base_url خالی باشد None برمی‌گردد."""
    base = (app_base_url or "").rstrip("/")
    if not base:
        return None
    rows: List[List[Dict[str, str]]] = []
    # ردیف اول — context-aware بر اساس event
    primary: List[Dict[str, str]] = []
    if event.startswith("verify_") or event in ("task_created", "task_failed"):
        primary.append({"text": "📋 تسک‌ها", "url": f"{base}/oversight?tab=tasks"})
        primary.append({"text": "📊 گزارش‌ها", "url": f"{base}/oversight?tab=reports"})
    elif event.startswith("scan_"):
        primary.append({"text": "👁 پروژه‌ها", "url": f"{base}/oversight?tab=watched"})
        primary.append({"text": "📋 تسک‌های جدید", "url": f"{base}/oversight?tab=tasks"})
    elif event == "idea_created":
        primary.append({"text": "💡 ایده‌ها", "url": f"{base}/oversight?tab=ideas"})
        primary.append({"text": "📋 تسک‌ها", "url": f"{base}/oversight?tab=tasks"})
    elif event == "pr_created":
        primary.append({"text": "📋 تسک‌ها", "url": f"{base}/oversight?tab=tasks"})
    else:
        primary.append({"text": "👁 پنل نظارت", "url": f"{base}/oversight"})
    if primary:
        rows.append(primary)
    # extra_buttons (مثلاً URL مستقیم به PR)
    if extra_buttons:
        rows.append(extra_buttons)
    # ردیف آخر همیشه: open app
    rows.append([{"text": "🏠 باز کردن پنل", "url": f"{base}/oversight"}])
    return {"inline_keyboard": rows}


# ---------------------------------------------------------------------------
# Channels
# ---------------------------------------------------------------------------

class NotificationChannel(ABC):
    name: str = "abstract"

    @abstractmethod
    async def send(
        self, message: str, *, subject: Optional[str] = None,
        silent: bool = False, reply_markup: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        ...


class TelegramChannel(NotificationChannel):
    name = "telegram"

    def __init__(self, bot_token: Optional[str], chat_id: Optional[str]):
        self.bot_token = (bot_token or "").strip()
        self.chat_id = (chat_id or "").strip()

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    async def send(
        self, message: str, *, subject: Optional[str] = None,
        silent: bool = False, reply_markup: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self.is_configured():
            return {"ok": False, "channel": self.name, "error": "TELEGRAM_BOT_TOKEN/CHAT_ID خالی است"}
        text = f"*{subject}*\n\n{message}" if subject else message
        if len(text) > 4000:
            text = text[:3990] + "\n…[truncated]"
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload: Dict[str, Any] = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
            "disable_notification": bool(silent),
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as r:
                    if r.status != 200:
                        body = await r.text()
                        # اگر Markdown parse fail شد، یک بار retry بدون parse_mode
                        if "can't parse" in body.lower():
                            payload.pop("parse_mode", None)
                            async with session.post(url, json=payload) as r2:
                                if r2.status == 200:
                                    return {"ok": True, "channel": self.name, "silent": silent}
                                return {"ok": False, "channel": self.name, "error": f"HTTP {r2.status}"}
                        return {"ok": False, "channel": self.name, "error": f"HTTP {r.status}: {body[:300]}"}
                    return {"ok": True, "channel": self.name, "silent": silent}
        except Exception as e:
            return {"ok": False, "channel": self.name, "error": str(e)[:300]}

    async def send_document(
        self, file_bytes: bytes, filename: str, *,
        caption: Optional[str] = None, silent: bool = False,
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """ارسال فایل (مثل .md, .json) به Telegram.

        کاربرد: نمایش Codex کامل که بیش از 4000 کاراکتر است.
        """
        if not self.is_configured():
            return {"ok": False, "channel": self.name, "error": "TELEGRAM_BOT_TOKEN/CHAT_ID خالی است"}
        url = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"
        data = aiohttp.FormData()
        data.add_field("chat_id", str(self.chat_id))
        if caption:
            # caption تا 1024 char محدودیت دارد
            cap = caption[:1020] + ("…" if len(caption) > 1020 else "")
            data.add_field("caption", cap)
            data.add_field("parse_mode", "Markdown")
        if silent:
            data.add_field("disable_notification", "true")
        if reply_markup:
            data.add_field("reply_markup", json.dumps(reply_markup))
        # تشخیص content_type از پسوند filename — برای PDF/HTML/JSON/MD
        fname_low = filename.lower()
        if fname_low.endswith(".pdf"):
            ctype = "application/pdf"
        elif fname_low.endswith(".html") or fname_low.endswith(".htm"):
            ctype = "text/html"
        elif fname_low.endswith(".json"):
            ctype = "application/json"
        elif fname_low.endswith(".txt"):
            ctype = "text/plain"
        else:
            ctype = "text/markdown"
        data.add_field(
            "document", file_bytes,
            filename=filename, content_type=ctype,
        )
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, data=data) as r:
                    if r.status != 200:
                        body = await r.text()
                        # اگر Markdown parse fail شد، یک بار retry بدون parse_mode
                        if caption and "can't parse" in body.lower():
                            retry = aiohttp.FormData()
                            retry.add_field("chat_id", str(self.chat_id))
                            retry.add_field("caption", caption[:1020])
                            if silent:
                                retry.add_field("disable_notification", "true")
                            if reply_markup:
                                retry.add_field("reply_markup", json.dumps(reply_markup))
                            retry.add_field(
                                "document", file_bytes,
                                filename=filename, content_type=ctype,
                            )
                            async with session.post(url, data=retry) as r2:
                                if r2.status == 200:
                                    return {"ok": True, "channel": self.name, "filename": filename}
                                body2 = await r2.text()
                                return {"ok": False, "channel": self.name, "error": f"HTTP {r2.status}: {body2[:300]}"}
                        return {"ok": False, "channel": self.name, "error": f"HTTP {r.status}: {body[:300]}"}
                    return {"ok": True, "channel": self.name, "filename": filename}
        except Exception as e:
            return {"ok": False, "channel": self.name, "error": str(e)[:300]}

    async def send_photo(
        self, photo_path: str, *,
        caption: Optional[str] = None, silent: bool = True,
    ) -> Dict[str, Any]:
        """ارسال یک عکس (PNG/JPG) به Telegram. مسیر absolute روی دیسک می‌گیرد.

        کاربرد: ضمیمه‌ی screenshot های auto-verify در کنار گزارش متنی.
        """
        if not self.is_configured():
            return {"ok": False, "channel": self.name, "error": "TELEGRAM_BOT_TOKEN/CHAT_ID خالی است"}
        try:
            with open(photo_path, "rb") as f:
                photo_bytes = f.read()
        except Exception as e:
            return {"ok": False, "channel": self.name, "error": f"read photo failed: {e}"}
        url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
        data = aiohttp.FormData()
        data.add_field("chat_id", str(self.chat_id))
        if caption:
            cap = caption[:1020] + ("…" if len(caption) > 1020 else "")
            data.add_field("caption", cap)
        if silent:
            data.add_field("disable_notification", "true")
        # نوع content_type بر اساس پسوند
        fname = photo_path.rsplit("/", 1)[-1]
        ctype = "image/jpeg" if fname.lower().endswith((".jpg", ".jpeg")) else "image/png"
        data.add_field("photo", photo_bytes, filename=fname, content_type=ctype)
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, data=data) as r:
                    if r.status != 200:
                        body = await r.text()
                        return {"ok": False, "channel": self.name,
                                "error": f"HTTP {r.status}: {body[:300]}"}
                    return {"ok": True, "channel": self.name, "filename": fname}
        except Exception as e:
            return {"ok": False, "channel": self.name, "error": str(e)[:300]}

    async def send_media_group_photos(
        self,
        photo_paths: List[str],
        captions: Optional[List[str]] = None,
        *,
        silent: bool = True,
    ) -> Dict[str, Any]:
        """ارسال تا ۱۰ photo به‌عنوان یک media_group (یک پیام «آلبوم»).

        Telegram محدودیت: ۱۰ media در هر group، caption نهایی ۱۰۲۴ char.
        اگر تعداد بیشتر از ۱۰ باشد، فقط ۱۰ تای اول ارسال می‌شود.

        خروجی: {ok, channel, count, error?}
        """
        if not self.is_configured():
            return {"ok": False, "channel": self.name,
                    "error": "TELEGRAM_BOT_TOKEN/CHAT_ID خالی است"}
        if not photo_paths:
            return {"ok": False, "channel": self.name, "error": "no photos"}

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMediaGroup"
        data = aiohttp.FormData()
        data.add_field("chat_id", str(self.chat_id))
        if silent:
            data.add_field("disable_notification", "true")

        # بارگذاری فایل‌ها و ساخت آرایه media
        media_array: List[Dict[str, Any]] = []
        successful_paths: List[str] = []
        for i, p in enumerate(photo_paths[:10]):
            try:
                with open(p, "rb") as f:
                    photo_bytes = f.read()
            except Exception:
                continue
            attach_name = f"photo_{i}"
            fname = p.rsplit("/", 1)[-1]
            ctype = "image/jpeg" if fname.lower().endswith((".jpg", ".jpeg")) else "image/png"
            media_item: Dict[str, Any] = {
                "type": "photo",
                "media": f"attach://{attach_name}",
            }
            if captions and i < len(captions) and captions[i]:
                # caption max 1024 char در Telegram
                cap = captions[i][:1020]
                media_item["caption"] = cap
            media_array.append(media_item)
            data.add_field(
                attach_name, photo_bytes,
                filename=fname, content_type=ctype,
            )
            successful_paths.append(p)

        if not media_array:
            return {"ok": False, "channel": self.name,
                    "error": "no readable photos"}

        data.add_field("media", json.dumps(media_array))
        try:
            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, data=data) as r:
                    if r.status != 200:
                        body = await r.text()
                        return {"ok": False, "channel": self.name,
                                "error": f"HTTP {r.status}: {body[:300]}",
                                "count": len(media_array)}
                    return {"ok": True, "channel": self.name,
                            "count": len(media_array),
                            "paths": successful_paths}
        except Exception as e:
            return {"ok": False, "channel": self.name,
                    "error": str(e)[:300]}

    # 🆕 (Compose Stage 2) — کمک‌کننده‌ها برای download کردن media از Telegram
    async def get_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        """تماس با Bot API getFile → file_path و file_size می‌گیریم.

        خروجی None اگر file_id نامعتبر است یا فایل بزرگ‌تر از 20MB.
        """
        if not self.bot_token:
            return None
        url = f"https://api.telegram.org/bot{self.bot_token}/getFile"
        try:
            timeout = aiohttp.ClientTimeout(total=20)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json={"file_id": file_id}) as r:
                    body = await r.json()
                    if not body.get("ok"):
                        return None
                    return body.get("result") or None
        except Exception as e:
            logger.warning(f"telegram getFile failed: {e}")
            return None

    async def download_file(self, file_path: str) -> Optional[bytes]:
        """download فایل از Telegram CDN.

        ⚠ محدودیت Bot API: حداکثر 20MB. برای بزرگ‌تر None.
        """
        if not self.bot_token or not file_path:
            return None
        url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"
        try:
            timeout = aiohttp.ClientTimeout(total=120)  # برای فایل ۲۰MB
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as r:
                    if r.status != 200:
                        return None
                    return await r.read()
        except Exception as e:
            logger.warning(f"telegram downloadFile failed: {e}")
            return None

    async def edit_message_text(
        self, chat_id: Any, message_id: int, text: str, *,
        reply_markup: Optional[Dict[str, Any]] = None,
        parse_mode: Optional[str] = "Markdown",
    ) -> Dict[str, Any]:
        """ویرایش پیام موجود (برای status updateهای idempotent در compose)."""
        if not self.is_configured():
            return {"ok": False, "error": "not configured"}
        if len(text) > 4000:
            text = text[:3990] + "\n…[truncated]"
        url = f"https://api.telegram.org/bot{self.bot_token}/editMessageText"
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "disable_web_page_preview": True,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as r:
                    body = await r.json()
                    if not body.get("ok"):
                        err = (body.get("description") or "").lower()
                        # "message is not modified" → no-op، OK
                        if "not modified" in err:
                            return {"ok": True, "no_change": True}
                        # markdown parse fail → retry بدون parse_mode
                        if "can't parse" in err and parse_mode:
                            return await self.edit_message_text(
                                chat_id, message_id, text,
                                reply_markup=reply_markup, parse_mode=None,
                            )
                        return {"ok": False, "error": body.get("description")}
                    return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)[:300]}

    async def send_with_reply_keyboard(
        self, message: str, keyboard_rows: List[List[str]], *,
        silent: bool = False, parse_mode: Optional[str] = "Markdown",
    ) -> Dict[str, Any]:
        """ارسال پیام با ReplyKeyboard دائم پایین صفحه (دکمه‌های بزرگ).

        keyboard_rows: [['متن دکمه ۱', 'متن دکمه ۲'], ['متن دکمه ۳']]
        """
        if not self.is_configured():
            return {"ok": False, "error": "not configured"}
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload: Dict[str, Any] = {
            "chat_id": self.chat_id,
            "text": message,
            "disable_web_page_preview": True,
            "disable_notification": bool(silent),
            "reply_markup": {
                "keyboard": [[{"text": btn} for btn in row] for row in keyboard_rows],
                "resize_keyboard": True,
                "one_time_keyboard": False,
                "is_persistent": True,
            },
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as r:
                    if r.status != 200:
                        body = await r.text()
                        if "can't parse" in body.lower() and parse_mode:
                            payload.pop("parse_mode", None)
                            async with session.post(url, json=payload) as r2:
                                if r2.status == 200:
                                    return {"ok": True}
                        return {"ok": False, "error": f"HTTP {r.status}: {body[:300]}"}
                    body = await r.json()
                    msg = body.get("result") or {}
                    return {"ok": True, "message_id": msg.get("message_id")}
        except Exception as e:
            return {"ok": False, "error": str(e)[:300]}

    async def remove_reply_keyboard(self, message: str = "✅", silent: bool = True) -> Dict[str, Any]:
        """حذف ReplyKeyboard با ارسال پیام کوتاه + reply_markup remove."""
        if not self.is_configured():
            return {"ok": False, "error": "not configured"}
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "disable_notification": bool(silent),
            "reply_markup": {"remove_keyboard": True},
        }
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as r:
                    return {"ok": r.status == 200}
        except Exception as e:
            return {"ok": False, "error": str(e)[:300]}

    async def set_webhook(self, webhook_url: str) -> Dict[str, Any]:
        if not self.bot_token:
            return {"ok": False, "error": "TELEGRAM_BOT_TOKEN تنظیم نشده"}
        url = f"https://api.telegram.org/bot{self.bot_token}/setWebhook"
        payload = {"url": webhook_url, "allowed_updates": ["message", "callback_query"]}
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as r:
                    body = await r.json()
                    return {"ok": bool(body.get("ok")), "result": body}
        except Exception as e:
            return {"ok": False, "error": str(e)[:300]}

    async def delete_webhook(self) -> Dict[str, Any]:
        if not self.bot_token:
            return {"ok": False, "error": "TELEGRAM_BOT_TOKEN تنظیم نشده"}
        url = f"https://api.telegram.org/bot{self.bot_token}/deleteWebhook"
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url) as r:
                    body = await r.json()
                    return {"ok": bool(body.get("ok")), "result": body}
        except Exception as e:
            return {"ok": False, "error": str(e)[:300]}


class EmailChannel(NotificationChannel):
    name = "email"

    def __init__(self, smtp_host, smtp_port, smtp_user, smtp_password, email_from, email_to):
        self.smtp_host = (smtp_host or "").strip()
        self.smtp_port = int(smtp_port or 587)
        self.smtp_user = (smtp_user or "").strip()
        self.smtp_password = (smtp_password or "").strip()
        self.email_from = (email_from or self.smtp_user or "").strip()
        self.email_to = (email_to or "").strip()

    def is_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password and self.email_to)

    def _send_sync(self, message: str, subject: Optional[str]) -> Dict[str, Any]:
        try:
            msg = EmailMessage()
            msg["Subject"] = subject or "Notification"
            msg["From"] = self.email_from
            msg["To"] = self.email_to
            msg.set_content(message)
            context = ssl.create_default_context()
            if self.smtp_port == 465:
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context, timeout=20) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=20) as server:
                    server.starttls(context=context)
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
            return {"ok": True, "channel": self.name}
        except Exception as e:
            return {"ok": False, "channel": self.name, "error": str(e)[:300]}

    async def send(
        self, message: str, *, subject: Optional[str] = None,
        silent: bool = False, reply_markup: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        # silent / reply_markup روی email بی‌اثرند — صرفاً برای interface سازگار
        if not self.is_configured():
            return {"ok": False, "channel": self.name, "error": "SMTP credentials کامل نیست"}
        return await asyncio.to_thread(self._send_sync, message, subject)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

PRIORITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def _md_escape_tg(s: str) -> str:
    """escape کاراکترهای Markdown که می‌توانند parse تلگرام را بشکنند."""
    if not s:
        return ""
    out = []
    for ch in s:
        if ch in ("_", "*", "`", "["):
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)


# 🆕 (P5) state machine برای flow چند-مرحله‌ای ربات (/new_task)
# in-memory state — اگر backend restart شود، session‌های فعال گم می‌شوند
# (timeout 10 دقیقه شدید است → cleanup خودکار)
_chat_state: Dict[str, Dict[str, Any]] = {}  # chat_id -> {phase, watched_id, idea?, expires_at}
_idea_drafts: Dict[str, Dict[str, Any]] = {}  # token -> {watched_id, idea, expires_at}
_STATE_TTL_SECONDS = 600  # 10 دقیقه

# 🆕 (telegram callback dedup) — وقتی کاربر روی «ثبت کن» چندبار کلیک می‌کند یا
# Telegram به‌خاطر کندی پاسخ webhook، callback را retry می‌کند، دومی draft را
# delete شده می‌بیند و «منقضی شده» می‌فرستد در حالی که اولی هنوز در حال
# پردازش است. این dict tokenهای در حال پردازش را track می‌کند تا تکراری‌ها
# silent skip شوند.
_processing_tokens: Dict[str, float] = {}  # token -> start_ts
_PROCESSING_TIMEOUT_SECONDS = 300  # 5 دقیقه — بعد از این پاک می‌شود


def _now_epoch() -> float:
    import time
    return time.time()


def _cleanup_expired_state() -> None:
    """حذف state و draft های منقضی — هر بار update اجرا می‌شود.

    🛡 (audit fix M1) — اگر chat یک compose buffer فعال دارد، state آن
    حفظ می‌شود (TTL compose بلندتر از state است؛ نباید state گم شود
    وقتی کاربر در حال جمع‌آوری فایل است).
    """
    now = _now_epoch()
    # ابتدا لیست chat_idهایی که compose فعال دارند
    # 🛡 (audit fix H1 CRITICAL) — snapshot dict قبل از iterate تا اگر یک
    # add_item همزمان modify کند، RuntimeError "dict changed size during
    # iteration" نگیریم.
    active_compose_chats: set = set()
    try:
        from .oversight_telegram_compose import get_compose_service
        cs = get_compose_service()
        snapshot = dict(getattr(cs, "_buffers", {}) or {})
        for cid, b in snapshot.items():
            try:
                if not b.is_expired():
                    active_compose_chats.add(cid)
            except Exception:
                continue
    except Exception:
        pass
    for k in list(_chat_state.keys()):
        if _chat_state[k].get("expires_at", 0) < now:
            if k in active_compose_chats:
                # extend state TTL تا compose زنده است
                _chat_state[k]["expires_at"] = now + _STATE_TTL_SECONDS
                continue
            del _chat_state[k]
    for k in list(_idea_drafts.keys()):
        if _idea_drafts[k].get("expires_at", 0) < now:
            del _idea_drafts[k]
    # cleanup tokenهای processing که timeout شده‌اند
    for k in list(_processing_tokens.keys()):
        if _processing_tokens[k] + _PROCESSING_TIMEOUT_SECONDS < now:
            del _processing_tokens[k]


def _short_token() -> str:
    import secrets
    return secrets.token_urlsafe(8)


# ---------------------------------------------------------------------------
# 🆕 (Daily Report) قالب‌بندی گزارش دوره‌ای
# ---------------------------------------------------------------------------

def _to_jalali_date_str(iso_str: Optional[str] = None) -> str:
    """تبدیل تاریخ به فرمت شمسی ساده برای نمایش (با fallback به Gregorian)."""
    from datetime import datetime, timezone
    if iso_str:
        try:
            dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        except Exception:
            dt = datetime.now(timezone.utc)
    else:
        dt = datetime.now(timezone.utc)
    # تلاش برای jalali — اگر کتابخانه jdatetime موجود است
    try:
        import jdatetime  # type: ignore
        jdt = jdatetime.datetime.fromgregorian(datetime=dt)
        return jdt.strftime("%Y/%m/%d")
    except Exception:
        return dt.strftime("%Y-%m-%d")


def _attention_emoji(label: str) -> str:
    return {
        "CRITICAL": "🔴",
        "HIGH": "🟠",
        "MEDIUM": "🟡",
        "LOW": "🟢",
    }.get(label, "⚪")


def _rank_emoji(idx: int) -> str:
    """emoji ranking برای 10 پروژهٔ اول."""
    medals = ["🥇", "🥈", "🥉"]
    if idx < 3:
        return medals[idx]
    return f"#{idx + 1}"


def _safe_md(text: str) -> str:
    """escape محدود برای Markdown Telegram (فقط برای رشته‌های user-controlled)."""
    if not text:
        return ""
    # escape فقط کاراکترهایی که Markdown V1 را می‌شکنند
    return (
        str(text)
        .replace("_", " ")  # underscore در Markdown V1 = italic
        .replace("*", " ")
        .replace("`", "'")
        .replace("[", "(")
        .replace("]", ")")
    )


def format_health_report_message(
    summary: Dict[str, Any], app_base_url: str = ""
) -> tuple:
    """قالب‌بندی متن گزارش روزانه + inline_keyboard.

    خروجی: (text: str, reply_markup: dict|None)
    """
    # تاریخ شمسی
    date_label = _to_jalali_date_str(summary.get("generated_at"))

    lines: List[str] = []
    lines.append(f"📊 *گزارش دوره‌ای پروژه‌ها — {date_label}*\n")
    lines.append("📈 *وضعیت کلی:*")
    lines.append(f"🗂 پروژه‌های تحت نظارت: *{summary.get('watched_count', 0)}*")
    lines.append(f"📋 مجموع تسک‌های فعال: *{summary.get('total_active_tasks', 0)}*")
    lines.append(
        f"🚨 critical: *{summary.get('total_critical', 0)}* · "
        f"⚠️ high: *{summary.get('total_high', 0)}*"
    )
    lines.append(f"✅ انجام‌شده در ۳۰ روز اخیر: *{summary.get('total_done_last_30d', 0)}*")
    lines.append(f"🏥 میانگین سلامت: *{summary.get('global_health_avg', 0)}%*")
    lines.append(f"🔒 میانگین امنیت: *{summary.get('global_security_avg', 0)}%*")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    lines.append("🏆 *رتبه‌بندی پروژه‌ها (بر اساس نیاز به توجه):*\n")

    projects = summary.get("projects", [])
    for idx, p in enumerate(projects):
        rank = _rank_emoji(idx)
        emoji = _attention_emoji(p.get("attention_label", "LOW"))
        proj_name_safe = _safe_md(p.get("project_full_name", ""))
        breakdown = p.get("tasks_priority_breakdown", {}) or {}
        last_scan = p.get("last_scan_at")
        last_scan_short = _to_jalali_date_str(last_scan) if last_scan else "—"
        depth = p.get("last_scan_depth", "—")

        lines.append(f"{rank} *{proj_name_safe}*  •  {emoji} {p.get('attention_label', 'LOW')}")
        lines.append(
            f"   📈 سلامت: *{p.get('health_score', 0)}%*  |  "
            f"🔒 امنیت: *{p.get('security_score', 0)}%*"
        )
        lines.append(
            f"   ✅ پیشرفت: *{p.get('completeness_score', 0)}%*  |  "
            f"📐 استاندارد: *{p.get('standard_score', 0)}%*"
        )
        lines.append(
            f"   📋 فعال: *{p.get('tasks_active', 0)}*  |  "
            f"✅ done: *{p.get('tasks_done', 0)}*"
        )
        lines.append(
            f"   🚨 {breakdown.get('critical', 0)} critical · "
            f"⚠️ {breakdown.get('high', 0)} high · "
            f"🟡 {breakdown.get('medium', 0)} med · "
            f"⚪ {breakdown.get('low', 0)} low"
        )
        # top critical finding (اگر موجود)
        top_crit = p.get("top_critical_findings", []) or []
        if top_crit:
            t0 = top_crit[0]
            t0_title = _safe_md(t0.get("title", "")[:80])
            lines.append(f"   ⚠️ {t0_title}")
        if p.get("scan_seen_top_count", 1) > 1:
            lines.append(f"   🔁 بزرگ‌ترین scan_seen: *{p['scan_seen_top_count']}*")
        lines.append(f"   🤖 آخرین scan: `{depth}` · {last_scan_short}")
        lines.append("")  # خط خالی بین پروژه‌ها

    # 🆕 (Creator) بخش پروژه‌های جدید
    created_30d = summary.get("projects_created_last_30d", 0)
    watched_30d = summary.get("projects_auto_watched_last_30d", 0)
    recent_created = summary.get("recent_created_projects", []) or []
    if created_30d > 0 or watched_30d > 0:
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        lines.append("🚀 *پروژه‌های جدید (۳۰ روز اخیر):*")
        lines.append(f"✅ ساخته‌شده: *{created_30d}*")
        lines.append(f"👁 خودکار تحت نظارت: *{watched_30d}*")
        if recent_created:
            lines.append("\n📦 آخرین پروژه‌ها:")
            for i, p in enumerate(recent_created, 1):
                name_safe = _safe_md(p.get("name", ""))
                source = p.get("source", "")
                src_emoji = (
                    "🚀" if "creator" in source
                    else "📥" if source == "github_import"
                    else "📌"
                )
                date_str = _to_jalali_date_str(p.get("created_at"))
                lines.append(f"{i}. {src_emoji} `{name_safe}` ({source}) — {date_str}")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    top_findings = summary.get("top_findings_global", []) or []
    if top_findings:
        lines.append("🚨 *برترین مشکلات حال حاضر (top 5):*")
        for i, f in enumerate(top_findings, 1):
            proj_name = _safe_md(f.get("project_full_name", ""))
            title = _safe_md(f.get("title", "")[:100])
            seen = f.get("scan_seen_count", 1)
            seen_str = f" · scan_seen: *{seen}*" if seen > 1 else ""
            lines.append(f"{i}. [{proj_name}] {title}{seen_str}")
        lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    recommendations = summary.get("recommendations", []) or []
    if recommendations:
        lines.append("🪜 *توصیه‌های اولویت‌دار:*")
        for r in recommendations:
            lines.append(f"• {r}")

    # 🆕 (AI Usage) بخش مصرف AI ۷ روز اخیر + موجودی
    ai_usage = summary.get("ai_usage") or {}
    if ai_usage and (ai_usage.get("week_tokens", 0) > 0 or ai_usage.get("balances")):
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("💰 *مصرف AI (۷ روز اخیر):*")
        wtok = ai_usage.get("week_tokens", 0)
        wcost = ai_usage.get("week_cost_usd", 0)
        wcnt = ai_usage.get("week_request_count", 0)
        # format helpers inline
        def _fn(n):
            if n >= 1_000_000: return f"{n/1_000_000:.2f}M"
            if n >= 1_000: return f"{n/1_000:.1f}K"
            return str(n)
        def _fc(c):
            if c < 0.01: return f"${c:.6f}"
            if c < 1: return f"${c:.4f}"
            return f"${c:.2f}"
        lines.append(f"📊 مجموع: *{_fn(wtok)}* توکن · {wcnt} request · {_fc(wcost)}")
        top_providers = (ai_usage.get("top_providers") or [])[:3]
        for p in top_providers:
            lines.append(
                f"  • `{p.get('provider', '?')}`: "
                f"{_fn(int(p.get('tokens', 0)))} tok · {_fc(float(p.get('cost', 0)))}"
            )
        # موجودی provider ها (با هشدار اگر کم)
        balances = ai_usage.get("balances") or {}
        low_balances = []
        for prov, b in balances.items():
            ptype = b.get("type")
            threshold = b.get("alert_threshold_usd", 1.0)
            if ptype == "remote_api":
                bal = b.get("remote_balance_usd", 0)
                if bal <= threshold:
                    curr = b.get("currency", "USD")
                    low_balances.append(f"🔴 `{prov}` (API): *{bal:.2f} {curr}*")
            elif ptype == "manual_budget":
                rem = b.get("remaining_estimate_usd", 0)
                if rem <= threshold:
                    low_balances.append(f"🔴 `{prov}` (budget): باقی *${rem:.2f}*")
        if low_balances:
            lines.append("⚠️ *موجودی کم:*")
            for lb in low_balances:
                lines.append(f"  {lb}")

    # هشتگ‌ها
    lines.append("")
    date_tag = date_label.replace("/", "_").replace("-", "_")
    hashtags = [
        "#daily_report",
        f"#{date_tag}",
        f"#{summary.get('watched_count', 0)}_projects",
    ]
    if summary.get("total_critical", 0) > 0:
        hashtags.append(f"#{summary['total_critical']}_critical")
    if summary.get("projects_created_last_30d", 0) > 0:
        hashtags.append(f"#{summary['projects_created_last_30d']}_new_projects")
    lines.append(" ".join(hashtags))

    text = "\n".join(lines)

    # محدودیت Telegram: 4096 char
    if len(text) > 4000:
        text = text[:3990] + "\n…[truncated — تعداد پروژه‌ها را در تنظیمات کاهش دهید]"

    # inline_keyboard
    reply_markup = None
    base = (app_base_url or "").rstrip("/")
    if base:
        rows: List[List[Dict[str, str]]] = [
            [
                {"text": "👁 باز کردن پنل", "url": f"{base}/oversight"},
                {"text": "📋 تسک‌های Critical", "url": f"{base}/oversight?tab=tasks"},
            ],
            [
                {"text": "📊 گزارش‌ها", "url": f"{base}/oversight?tab=reports"},
                {"text": "👁 پروژه‌های تحت نظارت", "url": f"{base}/oversight?tab=watched"},
            ],
        ]
        # یک ردیف per project (تا ۳ پروژهٔ critical)
        for p in projects[:3]:
            if p.get("attention_label") in ("CRITICAL", "HIGH"):
                wid = p.get("watched_id", "")
                pname = (p.get("project_full_name") or "")[:25]
                rows.append([
                    {
                        "text": f"{_attention_emoji(p.get('attention_label'))} {pname}",
                        "url": f"{base}/oversight?tab=tasks&watched={wid}",
                    }
                ])
        rows.append([{"text": "🏠 پنل", "url": f"{base}/"}])
        reply_markup = {"inline_keyboard": rows}

    return text, reply_markup


class NotificationService:
    def _build_channels(self) -> List[NotificationChannel]:
        return [
            TelegramChannel(
                bot_token=os.environ.get("TELEGRAM_BOT_TOKEN"),
                chat_id=os.environ.get("TELEGRAM_CHAT_ID"),
            ),
            EmailChannel(
                smtp_host=os.environ.get("SMTP_HOST"),
                smtp_port=int(os.environ.get("SMTP_PORT") or 587),
                smtp_user=os.environ.get("SMTP_USER"),
                smtp_password=os.environ.get("SMTP_PASSWORD"),
                email_from=os.environ.get("NOTIFICATION_EMAIL_FROM"),
                email_to=os.environ.get("NOTIFICATION_EMAIL_TO"),
            ),
        ]

    def _telegram(self) -> TelegramChannel:
        ch = self._build_channels()[0]
        return ch  # type: ignore

    def get_prefs(self) -> Dict[str, Any]:
        return _read_prefs()

    def update_prefs(self, partial: Dict[str, Any]) -> Dict[str, Any]:
        cur = _read_prefs()
        for k, v in (partial or {}).items():
            if isinstance(v, dict) and k in cur and isinstance(cur[k], dict):
                cur[k].update(v)
            else:
                cur[k] = v
        _write_prefs(cur)
        return cur

    def get_status(self) -> Dict[str, Any]:
        channels = self._build_channels()
        prefs = _read_prefs()
        status: Dict[str, Any] = {
            "prefs": prefs,
            "channels": {},
            "events_registry": {
                k: {"label": v["label"], "help": v["help"], "icon": v.get("icon", "")}
                for k, v in EVENT_REGISTRY.items()
            },
        }
        for ch in channels:
            ch_prefs = prefs.get("channels", {}).get(ch.name, {})
            status["channels"][ch.name] = {
                "configured_via_env": ch.is_configured(),
                "enabled_pref": bool(ch_prefs.get("enabled", True)),
                "ready": ch.is_configured() and bool(ch_prefs.get("enabled", True)),
            }
        return status

    async def notify_event(
        self,
        event: str,
        message: str,
        *,
        subject: Optional[str] = None,
        priority: str = "low",
        project_name: Optional[str] = None,
        watched_id: Optional[str] = None,
        extra_hashtags: Optional[List[str]] = None,
        extra_buttons: Optional[List[Dict[str, str]]] = None,
        attachment: Optional[Dict[str, Any]] = None,
        # 🆕 (Phase 5 — فاز ۸) — silent override (R6, R12)
        silent: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """ارسال نوتیفیکیشن.

        attachment (اختیاری): اگر داده شود، در کانال‌هایی که از سند پشتیبانی
        می‌کنند (مثل Telegram) فایل به‌جای متن ساده ارسال می‌شود — متن
        نوتیفیکیشن به‌عنوان caption فایل می‌رود. کانال‌های بدون پشتیبانی
        (مثل email در نسخهٔ فعلی) به ارسال متن fallback می‌کنند.

        ساختار: {"bytes": bytes, "filename": str, "mime": Optional[str]}
        """
        prefs = _read_prefs()
        events = prefs.get("events", {})
        if not events.get(event, EVENT_REGISTRY.get(event, {}).get("default_enabled", False)):
            return []
        min_pri = prefs.get("min_priority", "low")
        if PRIORITY_RANK.get(priority, 0) < PRIORITY_RANK.get(min_pri, 0):
            return []
        # ساخت متن با hashtag
        full_message = message
        if prefs.get("include_hashtags", True):
            tags = build_hashtags(
                event, project_name=project_name, priority=priority, extra=extra_hashtags
            )
            full_message = f"{message}\n\n{tags}"
        # silent based on per-event sound (sound=True ⇒ silent=False)
        # 🆕 (Phase 5 — فاز ۸) — silent param override: اگر صریحاً پاس داده،
        # event preferences را ignore کن
        if silent is None:
            sound_prefs = prefs.get("sound", {})
            with_sound = bool(sound_prefs.get(event, EVENT_REGISTRY.get(event, {}).get("default_sound", False)))
            silent = not with_sound
        else:
            silent = bool(silent)
        # inline keyboard
        reply_markup = None
        if prefs.get("include_inline_buttons", True):
            reply_markup = build_inline_keyboard(
                prefs.get("app_base_url", ""), event,
                watched_id=watched_id, extra_buttons=extra_buttons,
            )
        # ارسال
        results: List[Dict[str, Any]] = []
        for ch in self._build_channels():
            if not ch.is_configured():
                continue
            ch_prefs = prefs.get("channels", {}).get(ch.name, {})
            if not ch_prefs.get("enabled", True):
                continue
            # 🆕 اگر attachment داده شده و کانال از send_document پشتیبانی می‌کند،
            # سند را با caption=full_message بفرست. در غیر این صورت متن ساده.
            if attachment and hasattr(ch, "send_document"):
                try:
                    res = await ch.send_document(  # type: ignore[attr-defined]
                        attachment["bytes"],
                        attachment.get("filename") or "attachment",
                        caption=full_message,
                        silent=silent,
                        reply_markup=reply_markup,
                    )
                except Exception as _e:
                    # fallback به ارسال متن
                    logger.warning(f"send_document failed on {ch.name}: {_e}; falling back to text")
                    res = await ch.send(
                        full_message, subject=subject, silent=silent, reply_markup=reply_markup,
                    )
            else:
                res = await ch.send(
                    full_message, subject=subject, silent=silent, reply_markup=reply_markup,
                )
            results.append(res)
        return results

    # ====================================================================
    # 🔬 (inspector_probe Phase 1) — ارسال screenshot های اضافی به Telegram
    # ====================================================================

    async def send_extra_photos(
        self,
        photo_paths: List[str],
        captions: Optional[List[str]] = None,
        *,
        silent: bool = True,
    ) -> List[Dict[str, Any]]:
        """photo ها را روی همان کانال Telegram (اگر configured است) می‌فرستد.

        برای ضمیمه‌ی screenshot های auto-verify بعد از پیام اصلی verify.

        🆕 (Phase 2 fix) — اگر تعداد photo بیشتر از یکی باشد، از
        sendMediaGroup استفاده می‌کند تا همه در یک «آلبوم» (یک پیام)
        ارسال شوند، نه تیکه‌تیکه. اگر media_group شکست خورد، fallback
        به send_photo تک‌تک.

        خروجی: لیست نتایج (یک item به ازای هر photo که تلاش شد).
        photo هایی که خواندنی نبودند skip می‌شوند.
        """
        if not photo_paths:
            return []
        results: List[Dict[str, Any]] = []
        for ch in self._build_channels():
            if not isinstance(ch, TelegramChannel):
                continue
            if not ch.is_configured():
                continue
            # ابتدا تلاش با media_group اگر >=2
            if len(photo_paths) >= 2:
                try:
                    mg_res = await ch.send_media_group_photos(
                        photo_paths[:10], captions=captions, silent=silent,
                    )
                except Exception as e:
                    mg_res = {"ok": False, "channel": ch.name,
                              "error": f"media_group exception: {e}"}
                if mg_res.get("ok"):
                    for p in (mg_res.get("paths") or photo_paths[:10]):
                        results.append({
                            "ok": True, "channel": ch.name, "path": p,
                            "via": "media_group",
                        })
                    continue
                # media_group شکست خورد → fallback به send_photo تک‌تک
                logger.debug(
                    f"media_group failed on {ch.name}: {mg_res.get('error')} "
                    f"— falling back to individual send_photo"
                )
            # mode تک‌به‌تک (یا برای ۱ photo، یا fallback)
            for idx, p in enumerate(photo_paths):
                cap = None
                if captions and idx < len(captions):
                    cap = captions[idx]
                try:
                    res = await ch.send_photo(p, caption=cap, silent=silent)
                except Exception as e:
                    res = {"ok": False, "channel": ch.name,
                           "error": f"send_photo exception: {e}"}
                res["path"] = p
                res["via"] = "send_photo"
                results.append(res)
        return results

    # ====================================================================
    # 🔔 Reminder feature
    # ====================================================================

    async def send_reminder_due(self, task: Any) -> Optional[Dict[str, Any]]:
        """ارسال پیام «یادآوری موعد رسیده» با inline checklist + snooze/done.

        - متن پیام: title + summary (description) + lines for pending steps
        - دکمه‌ها:
            • برای هر step pending (max 8): «✅ <عنوان مرحله>»
              callback: reminder:tick:<task_id>:<step_id>
            • ردیف: «✅ همه انجام شد» — reminder:done:<task_id>
            • ردیف: «⏰ یادآوری دوباره» — reminder:snooze_pick:<task_id>
        - silent بر اساس prefs sound (reminder_due default=True یعنی صدا)
        """
        prefs = _read_prefs()
        events = prefs.get("events", {})
        if not events.get("reminder_due", EVENT_REGISTRY.get("reminder_due", {}).get("default_enabled", True)):
            return None
        sound = bool(prefs.get("sound", {}).get(
            "reminder_due",
            EVENT_REGISTRY.get("reminder_due", {}).get("default_sound", True),
        ))
        silent = not sound

        title = getattr(task, "title", "یادآوری") or "یادآوری"
        steps = getattr(task, "task_steps", []) or []
        pending = [s for s in steps if not s.get("done") and s.get("status") != "done"]

        lines: List[str] = [
            f"🔔 *یادآوری موعد رسیده*: {title}",
            "",
        ]
        raw_idea = (getattr(task, "raw_idea", "") or "")[:300]
        if raw_idea and raw_idea.strip():
            lines.append(f"📝 {raw_idea}")
            lines.append("")
        if pending:
            lines.append("✅ *آیتم‌های باقی‌مانده:*")
            for s in pending[:15]:
                stitle = (s.get("title") or s.get("scope") or "آیتم")[:120]
                lines.append(f"  • {stitle}")
        else:
            lines.append("(چک‌لیستی ثبت نشده — می‌توانی کل یادآوری را تمام شده اعلام کنی)")

        text = "\n".join(lines)

        # inline keyboard
        rows: List[List[Dict[str, str]]] = []
        for s in pending[:8]:
            sid = s.get("id")
            stitle = (s.get("title") or s.get("scope") or "آیتم")[:35]
            rows.append([{
                "text": f"✅ {stitle}",
                "callback_data": f"reminder:tick:{task.id}:{sid}",
            }])
        rows.append([
            {"text": "✅ همه انجام شد / آرشیو", "callback_data": f"reminder:done:{task.id}"},
        ])
        rows.append([
            {"text": "⏰ یادآوری دوباره", "callback_data": f"reminder:snooze_pick:{task.id}"},
        ])

        # ارسال مستقیم از طریق Telegram channel (notify_event برای inline
        # keyboard اختصاصی منعطف نیست — اینجا کنترل کامل می‌خواهیم)
        tg = self._telegram()
        if not tg.is_configured():
            logger.warning("send_reminder_due: telegram not configured")
            return None
        try:
            res = await tg.send(
                text,
                silent=silent,
                reply_markup={"inline_keyboard": rows},
            )
            return res if isinstance(res, dict) else {"ok": True}
        except Exception as e:
            logger.warning(f"send_reminder_due telegram send failed: {e}")
            return None

    async def _handle_backfill_callback(
        self, chat_id_str: str, data: str, tg: Any,
    ) -> Dict[str, Any]:
        """router برای callback_data با prefix backfill:*

        پشتیبانی:
          backfill:run_force  → re-enrich همه AC ها (Phase 3 upgrade)
          backfill:run        → backfill عادی (فقط unclassified)
        """
        try:
            parts = data.split(":")
            mode = parts[1] if len(parts) > 1 else "run"
            force = (mode == "run_force")

            # 🆕 پیام «در حال شروع»
            try:
                await tg.send(
                    "🔬 backfill در حال شروع... (تا چند دقیقه طول می‌کشد)",
                    silent=True,
                )
            except Exception:
                pass

            # state موجود را چک کن — اگر running است، یادآور
            try:
                from ..api.routes.oversight import (
                    _BACKFILL_STATE,
                    _run_backfill_ac_classification,
                )
            except Exception as e:
                await tg.send(f"⚠️ خطا در import backfill: {e}", silent=True)
                return {"ok": False, "error": str(e)}

            if _BACKFILL_STATE.get("running"):
                await tg.send(
                    f"⏳ backfill قبلی هنوز در حال اجراست "
                    f"({_BACKFILL_STATE.get('current_index', 0)}/"
                    f"{_BACKFILL_STATE.get('total', 0)})",
                    silent=True,
                )
                return {"ok": True, "already_running": True}

            # شروع backfill
            from datetime import datetime as _dt
            _BACKFILL_STATE["running"] = True
            _BACKFILL_STATE["started_at"] = _dt.utcnow().isoformat()
            _BACKFILL_STATE["finished_at"] = None
            _BACKFILL_STATE["current_index"] = 0
            _BACKFILL_STATE["total"] = 0
            _BACKFILL_STATE["summary"] = None
            _BACKFILL_STATE["error"] = None
            _BACKFILL_STATE["force"] = force
            _BACKFILL_STATE["triggered_by"] = "telegram"

            import asyncio as _asyncio_lc
            _asyncio_lc.create_task(
                _run_backfill_ac_classification(None, force=force)
            )

            mode_label = "force (re-enrich همه)" if force else "عادی"
            await tg.send(
                f"✅ backfill شروع شد ({mode_label}) — نتیجه پس از تکمیل ارسال می‌شود",
                silent=False,
            )
            return {"ok": True, "started": True, "force": force}
        except Exception as e:
            logger.warning(f"_handle_backfill_callback failed: {e}")
            try:
                await tg.send(f"⚠️ خطا در شروع backfill: {e}", silent=True)
            except Exception:
                pass
            return {"ok": False, "error": str(e)}

    async def _handle_reminder_callback(
        self, chat_id_str: str, data: str, msg: Dict[str, Any],
    ) -> Dict[str, Any]:
        """router برای callback_data با prefix reminder:*

        فرمت‌ها:
          reminder:tick:<task_id>:<step_id>
          reminder:done:<task_id>
          reminder:snooze_pick:<task_id>
          reminder:snooze:<task_id>:<delta_seconds|iso>
        """
        tg = self._telegram()
        parts = data.split(":")
        if len(parts) < 3:
            return {"ok": True, "ignored": True}
        action = parts[1]
        task_id = parts[2]

        try:
            from .oversight_service import get_oversight_service, now_iso
            ov = get_oversight_service()
        except Exception as e:
            await tg.send(f"⚠️ سرویس در دسترس نیست: {e}", silent=True)
            return {"ok": False}

        task = next((t for t in ov.tasks if t.id == task_id), None)
        if task is None or task.type != "reminder":
            await tg.send("⚠️ یادآوری یافت نشد.", silent=True)
            return {"ok": True, "handled": "reminder_not_found"}

        if action == "tick" and len(parts) >= 4:
            try:
                step_id = int(parts[3])
            except ValueError:
                return {"ok": True, "ignored": True}
            async with ov._lock:
                for s in task.task_steps:
                    if s.get("id") == step_id:
                        s["done"] = True
                        s["status"] = "done"
                        s["completion_pct"] = 100
                        s["completed_at"] = now_iso()
                        break
                task.reminder_history.append({
                    "ts": now_iso(),
                    "action": "step_ticked",
                    "step_id": step_id,
                })
                # اگر همه done شدند، خودکار done کن
                all_done = all(
                    s.get("done") or s.get("status") == "done"
                    for s in (task.task_steps or [])
                )
                if all_done:
                    task.reminder_state = "done"
                    task.archived = True
                    task.archived_at = now_iso()
                    task.reminder_history.append({
                        "ts": now_iso(), "action": "done",
                        "via": "all_steps_ticked",
                    })
                task.updated_at = now_iso()
                ov._save_tasks()
            if all_done:
                await tg.send(
                    f"✅ یادآوری «{task.title}» کامل شد و آرشیو شد.",
                    silent=True,
                )
                try:
                    await self.notify_event(
                        "reminder_done", f"✅ یادآوری «{task.title}» تمام شد.",
                        priority="low",
                    )
                except Exception:
                    pass
            else:
                pending_titles = [
                    (s.get("title") or "")[:40]
                    for s in task.task_steps if not s.get("done")
                ]
                await tg.send(
                    f"✅ آیتم انجام شد. باقی‌مانده ({len(pending_titles)}):\n"
                    + "\n".join(f"  • {t}" for t in pending_titles[:10]),
                    silent=True,
                )
            return {"ok": True, "handled": "reminder_tick"}

        if action == "done":
            async with ov._lock:
                for s in task.task_steps or []:
                    s["done"] = True
                    s["status"] = "done"
                    s["completion_pct"] = 100
                task.reminder_state = "done"
                task.archived = True
                task.archived_at = now_iso()
                task.reminder_history.append({
                    "ts": now_iso(), "action": "done", "via": "user_button",
                })
                task.updated_at = now_iso()
                ov._save_tasks()
            await tg.send(
                f"✅ یادآوری «{task.title}» تمام و آرشیو شد.", silent=True,
            )
            try:
                await self.notify_event(
                    "reminder_done", f"✅ یادآوری «{task.title}» تمام شد.",
                    priority="low",
                )
            except Exception:
                pass
            return {"ok": True, "handled": "reminder_done"}

        if action == "snooze_pick":
            rows = [
                [{"text": "⏰ ۱۵ دقیقه دیگر", "callback_data": f"reminder:snooze:{task_id}:900"}],
                [{"text": "⏰ ۱ ساعت دیگر", "callback_data": f"reminder:snooze:{task_id}:3600"}],
                [{"text": "⏰ ۳ ساعت دیگر", "callback_data": f"reminder:snooze:{task_id}:10800"}],
                [{"text": "⏰ فردا همین ساعت", "callback_data": f"reminder:snooze:{task_id}:86400"}],
                [{"text": "⏰ یک هفته دیگر", "callback_data": f"reminder:snooze:{task_id}:604800"}],
            ]
            await tg.send(
                f"⏰ چه زمانی دوباره یادآوری کنم برای «{task.title}»؟",
                silent=True,
                reply_markup={"inline_keyboard": rows},
            )
            return {"ok": True, "handled": "reminder_snooze_pick"}

        if action == "snooze" and len(parts) >= 4:
            spec = parts[3]
            from datetime import datetime as _dt, timedelta as _td, timezone as _tz
            try:
                delta = int(spec)
                new_at = _dt.now(_tz.utc) + _td(seconds=delta)
                new_at_iso = new_at.isoformat()
            except ValueError:
                # ISO خام
                try:
                    new_at = _dt.fromisoformat(spec.replace("Z", "+00:00"))
                    if new_at.tzinfo is None:
                        new_at = new_at.replace(tzinfo=_tz.utc)
                    new_at_iso = new_at.isoformat()
                except Exception:
                    await tg.send("⚠️ فرمت زمان نامعتبر.", silent=True)
                    return {"ok": True, "handled": "reminder_snooze_bad_format"}
            async with ov._lock:
                task.reminder_at = new_at_iso
                task.reminder_state = "snoozed"
                task.reminder_history.append({
                    "ts": now_iso(), "action": "snoozed", "new_at": new_at_iso,
                })
                task.updated_at = now_iso()
                ov._save_tasks()
            await tg.send(
                f"⏰ یادآوری «{task.title}» به {new_at_iso} موکول شد.",
                silent=True,
            )
            try:
                await self.notify_event(
                    "reminder_snoozed",
                    f"⏰ یادآوری «{task.title}» به {new_at_iso} موکول شد.",
                    priority="low",
                )
            except Exception:
                pass
            return {"ok": True, "handled": "reminder_snoozed"}

        return {"ok": True, "ignored": True}

    async def send_daily_report(self, summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        """ارسال گزارش روزانه به همه کانال‌های ready.

        از format_health_report_message برای ساخت متن استفاده می‌کند.
        silent بر اساس prefs.sound.daily_report تعیین می‌شود.
        """
        prefs = _read_prefs()
        # رعایت تنظیمات کاربر برای cap project count
        daily_prefs = prefs.get("daily_report", {}) or {}
        max_projects = int(daily_prefs.get("max_projects_in_report", 20) or 20)
        if "projects" in summary and isinstance(summary["projects"], list):
            summary = {**summary, "projects": summary["projects"][:max_projects]}
        # filter recommendations/top_findings بر اساس prefs
        if not daily_prefs.get("include_recommendations", True):
            summary = {**summary, "recommendations": []}
        if not daily_prefs.get("include_top_findings", True):
            summary = {**summary, "top_findings_global": []}
        if not daily_prefs.get("include_creator_section", True):
            summary = {
                **summary,
                "projects_created_last_30d": 0,
                "projects_auto_watched_last_30d": 0,
                "recent_created_projects": [],
            }

        text, reply_markup = format_health_report_message(
            summary, app_base_url=prefs.get("app_base_url", "")
        )

        # event check (می‌توان daily_report را کلاً off کرد از panel events)
        events = prefs.get("events", {})
        if not events.get("daily_report", True):
            logger.info("daily_report event disabled — skipping send")
            return []

        sound = bool(prefs.get("sound", {}).get("daily_report", False))
        silent = not sound

        results: List[Dict[str, Any]] = []
        for ch in self._build_channels():
            if not ch.is_configured():
                continue
            ch_prefs = prefs.get("channels", {}).get(ch.name, {})
            if not ch_prefs.get("enabled", True):
                continue
            res = await ch.send(
                text,
                subject=f"گزارش روزانه — {summary.get('watched_count', 0)} پروژه",
                silent=silent,
                reply_markup=reply_markup,
            )
            results.append(res)
            if res.get("ok"):
                logger.info(f"daily_report sent via {ch.name}")
            else:
                logger.warning(f"daily_report {ch.name} failed: {res.get('error')}")
        return results

    async def test_send(self, channel: Optional[str] = None) -> List[Dict[str, Any]]:
        msg = (
            "🔔 پیام تست از سیستم نوتیفیکیشن\n"
            "اگر این را می‌بینی پیکربندی درست انجام شده."
        )
        return await self.notify_event(
            "manual_test", msg, subject="تست نوتیفیکیشن",
            priority="critical",  # تست همیشه باید رد شود
        ) if not channel else await self._test_single(channel, msg)

    async def _test_single(self, channel: str, msg: str) -> List[Dict[str, Any]]:
        prefs = _read_prefs()
        for ch in self._build_channels():
            if ch.name != channel:
                continue
            if not ch.is_configured():
                return [{"ok": False, "channel": ch.name, "error": "credentials در env تنظیم نشده"}]
            sound = bool(prefs.get("sound", {}).get("manual_test", True))
            rm = build_inline_keyboard(prefs.get("app_base_url", ""), "manual_test")
            return [await ch.send(msg, subject="تست", silent=not sound, reply_markup=rm)]
        return [{"ok": False, "channel": channel, "error": "کانال ناشناخته"}]

    # -----------------------------------------------------------------------
    # Webhook handler — برای commands /start /menu /status
    # -----------------------------------------------------------------------

    async def _answer_callback(self, callback_query_id: str, text: str = "") -> None:
        """پاسخ به callback_query (برای حذف loading state دکمه).

        اگر text خالی باشد، key 'text' را در payload نمی‌گذاریم. در غیر این
        صورت بعضی کلاینت‌های تلگرام (مثل web) JSON null را به‌عنوان literal
        رشتهٔ "null" نمایش می‌دهند که toast اشتباه ایجاد می‌کند.
        """
        if not self._telegram().bot_token:
            return
        url = f"https://api.telegram.org/bot{self._telegram().bot_token}/answerCallbackQuery"
        payload: Dict[str, Any] = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text[:200]
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                await session.post(url, json=payload)
        except Exception:
            pass

    async def handle_telegram_update(self, update: Dict[str, Any]) -> Dict[str, Any]:
        """پردازش update از Telegram webhook. text commands + callback_query."""
        _cleanup_expired_state()

        # ——— callback_query (دکمه‌های inline) ———
        cq = update.get("callback_query")
        if cq:
            # 🛡 global try/except — هیچ exception نباید silent باشد
            try:
                return await self._handle_callback_query(cq)
            except Exception as e:
                logger.exception(f"callback handler crashed: {e}")
                # تلاش برای ارسال پیام خطا به کاربر
                try:
                    chat = (cq.get("message") or {}).get("chat") or {}
                    if chat.get("id"):
                        await self._telegram().send(
                            f"❌ خطا در پردازش دکمه:\n`{str(e)[:300]}`\n\n"
                            f"می‌توانید با /menu دوباره شروع کنید.",
                            silent=False,
                        )
                except Exception:
                    pass
                return {"ok": False, "handled": "callback_crash", "error": str(e)[:300]}

        # ——— message ———
        msg = update.get("message") or {}
        text = (msg.get("text") or "").strip()
        chat = (msg.get("chat") or {})
        chat_id = chat.get("id")

        # 🆕 (Compose Stage 2) — اگر این پیام media است (یا compose mode فعال
        # است و پیام text بدون command است)، آن را به compose buffer هدایت کن.
        if chat_id:
            configured_id_pre = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
            if not configured_id_pre or str(chat_id) == configured_id_pre:
                media_handled = await self._maybe_route_to_compose(str(chat_id), msg, text)
                if media_handled is not None:
                    return media_handled
        # 🆕 alias دکمه‌های persistent reply keyboard → command واقعی
        # وقتی کاربر روی دکمهٔ menu کلیک می‌کند، اگر در یک flow بود، state را پاک
        # می‌کنیم تا alias با fast-path command به‌جای text-handler flow اجرا شود.
        if text in TEXT_ALIASES:
            if chat_id:
                _chat_state.pop(str(chat_id), None)
            text = TEXT_ALIASES[text]
        if not chat_id or not text:
            return {"ok": True, "ignored": True}
        # فقط روی chat ID پیکربندی‌شده پاسخ دهیم (security)
        configured_id = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
        if configured_id and str(chat_id) != configured_id:
            logger.info(f"telegram webhook: ignoring chat {chat_id} (not configured)")
            return {"ok": True, "ignored": True}

        prefs = _read_prefs()
        base = (prefs.get("app_base_url", "") or "").rstrip("/")
        tg = self._telegram()
        chat_id_str = str(chat_id)

        # ——— /cancel (در هر زمان state را پاک می‌کند) ———
        if text == "/cancel":
            had = chat_id_str in _chat_state
            _chat_state.pop(chat_id_str, None)
            # 🆕 (Compose) — اگر compose فعال است، آن را هم cancel کن
            from .oversight_telegram_compose import get_compose_service
            compose_svc = get_compose_service()
            had_compose = compose_svc.has_active(chat_id_str)
            if had_compose:
                await compose_svc.cancel(chat_id_str)
                await tg.remove_reply_keyboard("🗑 compose لغو شد.")
            await tg.send(
                "✅ همه‌چیز لغو شد." if (had or had_compose) else "هیچ flow فعالی نبود.",
                silent=True,
            )
            return {"ok": True, "handled": "cancel"}

        # 🆕 (Compose Stage 3) — دکمه‌های ReplyKeyboard
        if text == self._COMPOSE_BTN_CANCEL:
            from .oversight_telegram_compose import get_compose_service
            compose_svc = get_compose_service()
            buf = compose_svc.get(chat_id_str)
            if buf is not None:
                await compose_svc.cancel(chat_id_str)
                await tg.remove_reply_keyboard("🗑 ساخت تسک ترکیبی لغو شد — همهٔ پیوست‌ها پاک شدند.")
            else:
                await tg.send("هیچ compose فعالی نیست.", silent=True)
            return {"ok": True, "handled": "compose_cancelled"}

        if text in (self._COMPOSE_BTN_SUBMIT, self._COMPOSE_BTN_SUBMIT_PROJECT):
            # Stage 4 این را به پایان پایپ‌لاین می‌برد
            return await self._compose_submit(chat_id_str, mode=("project" if text == self._COMPOSE_BTN_SUBMIT_PROJECT else "task"))

        # 🆕 ——— /codex (مشاهده/ساخت شناسنامهٔ پروژه از تلگرام) ———
        if text == "/codex":
            return await self._start_codex_flow(chat_id_str)

        # 🆕 ——— /usage و /balance (مصرف AI + موجودی) ———
        if text in ("/usage", "/balance"):
            return await self._show_ai_usage(chat_id_str)

        # 🆕 /codex_debug — تشخیص دقیق وضعیت برای debug
        if text == "/codex_debug":
            return await self._codex_debug(chat_id_str)

        # ——— /new_task و /new_idea (شروع flow جدید) ———
        if text in ("/new_task", "/new_idea"):
            return await self._start_new_task_flow(chat_id_str)

        # 🔔 ——— /reminder — شروع flow یادآوری ———
        # compose را با force_type="reminder" شروع می‌کند. کاربر می‌تواند
        # متن/صوت/فایل بفرستد و سپس submit کند — AI زمان را از متن
        # استخراج می‌کند (یا پیش‌فرض ۱ ساعت بعد). نیاز به انتخاب پروژه
        # ندارد چون reminder ها مستقل از repo اند.
        if text in ("/reminder", "/remind"):
            return await self._start_reminder_flow(chat_id_str)

        # 🆕 ——— /new_project و /create_project (Creator flow) ———
        if text in ("/new_project", "/create_project"):
            return await self._start_new_project_flow(chat_id_str)

        # ——— state-aware ———
        state = _chat_state.get(chat_id_str)
        if state and state.get("phase") == "awaiting_idea":
            return await self._receive_idea_text(chat_id_str, state, text)
        # 🆕 (Task Regen) phase awaiting_regen_idea — کاربر متن جدید را داد
        if state and state.get("phase") == "awaiting_regen_idea":
            task_id = state.get("task_id") or ""
            _chat_state.pop(chat_id_str, None)  # یک‌بار مصرف
            if not task_id:
                tg = self._telegram()
                await tg.send("⚠️ task_id ناشناخته است.", silent=True)
                return {"ok": True, "handled": "regen_no_task"}
            t = (text or "").strip()
            # /skip → از همان raw_idea فعلی استفاده می‌کنیم (new_raw_idea=None)
            if t.lower() in ("/skip", "skip"):
                return await self._execute_task_regen(chat_id_str, task_id, None)
            if t.lower() in ("/cancel", "cancel"):
                tg = self._telegram()
                await tg.send("❌ بازتولید لغو شد.", silent=True)
                return {"ok": True, "handled": "regen_cancel"}
            return await self._execute_task_regen(chat_id_str, task_id, t)
        # 🆕 Creator phase handlers — text-based phases (v1 — legacy)
        if state and state.get("phase") in (
            "creator_awaiting_name", "creator_awaiting_desc", "creator_awaiting_tech",
        ):
            return await self._handle_creator_phase(chat_id_str, state, text)
        # 🆕 (Creator v2) phase awaiting_idea — text کاربر = ایدهٔ پروژه
        if state and state.get("phase") == "creator_awaiting_idea":
            return await self._receive_creator_idea(chat_id_str, state, text)
        # 🆕 (Creator v2) phase awaiting_custom_name — text کاربر = نام دلخواه
        if state and state.get("phase") == "creator_awaiting_custom_name":
            return await self._receive_creator_custom_name(chat_id_str, state, text)
        # 🆕 phase awaiting_type: کاربر باید دکمهٔ inline کلیک کند، نه متن
        if state and state.get("phase") == "creator_awaiting_type":
            tg = self._telegram()
            kb = self._render_project_type_picker()
            await tg.send(
                "⚠️ لطفاً نوع پروژه را از دکمه‌های زیر انتخاب کن (نه متن):",
                silent=True,
                reply_markup=kb,
            )
            return {"ok": True, "handled": "type_needs_button"}
        # 🆕 (Creator v2) phase awaiting_model_choice — text رد می‌شود
        if state and state.get("phase") == "creator_awaiting_model_choice":
            tg = self._telegram()
            await tg.send(
                "⚠️ لطفاً مدل را از دکمه‌های inline انتخاب کنید (نه متن):",
                silent=True,
            )
            return await self._show_creator_model_picker(chat_id_str)

        if text in ("/start", "/help"):
            reply = (
                "👋 *سلام!*\n\n"
                "این ربات نوتیفیکیشن‌های سیستم نظارت پروژه است.\n\n"
                "دستورات:\n"
                "• /index — 📋 *لیست دسته‌بندی‌شدهٔ کارها* (pin‌شده، خودکار به‌روز)\n"
                "• /new\\_project یا /create\\_project — *🚀 ساخت پروژهٔ جدید* (از صفر، با push به GitHub)\n"
                "• /new\\_task یا /new\\_idea — ثبت تسک جدید با انتخاب پروژه\n"
                "• /reminder یا /remind — 🔔 ثبت یادآوری (با متن یا صوت/فایل، زمان از متن استخراج می‌شود)\n"
                "• /codex — 📚 شناسنامهٔ پروژه (مشاهده یا ساخت با AI)\n"
                "• /usage یا /balance — 💰 مصرف توکن AI و موجودی provider ها\n"
                "• /menu — منوی دسترسی سریع\n"
                "• /status — وضعیت نوتیفیکیشن\n"
                "• /cancel — لغو flow فعلی\n"
                "• /hide\\_menu — مخفی‌کردن منوی ثابت\n"
                "• /help — این پیام\n\n"
                "💡 *منوی ثابت* در پایین صفحه فعال شد — برای دسترسی سریع از آن استفاده کنید.\n"
                "ℹ️ اگر منوی پایین مخفی شد (مثلاً بعد از سوئیچ بین چت‌های مختلف)، "
                "/menu را بزنید تا دوباره فعال شود."
            )
            # 🆕 reply_markup = persistent reply keyboard (یک‌بار ست می‌شود، تا remove نشود می‌ماند)
            await tg.send(reply, silent=True, reply_markup=PERSISTENT_REPLY_KEYBOARD)
            return {"ok": True, "handled": "start"}

        # 🆕 /index — پیام pin‌شدهٔ ایندکس کارها (دسته‌بندی شده، خودکار edit)
        if text == "/index":
            return await self._send_or_edit_index_message(chat_id_str)

        # 🆕 /hide_menu — حذف persistent reply keyboard
        if text == "/hide_menu":
            await tg.send(
                "🔕 منوی ثابت مخفی شد.\nبرای فعال‌سازی مجدد: /start یا /menu",
                silent=True,
                reply_markup={"remove_keyboard": True},
            )
            return {"ok": True, "handled": "hide_menu"}

        if text == "/menu":
            reply = (
                "📋 *منوی دسترسی سریع*\n\n"
                "از دکمه‌های زیر برای رفتن به هر بخش استفاده کنید.\n"
                "برای ثبت تسک از تلگرام: /new\\_task"
            )
            if not base:
                reply += "\n\n⚠️ `app_base_url` در پنل تنظیمات ست نشده — لینک‌ها در دسترس نیستند."
                # 🆕 حتی بدون base، persistent keyboard ست می‌شود
                await tg.send(reply, silent=True, reply_markup=PERSISTENT_REPLY_KEYBOARD)
                return {"ok": True, "handled": "menu_no_url"}
            kb = {
                "inline_keyboard": [
                    [
                        {"text": "📋 ایندکس کارها", "callback_data": "menu:index"},
                    ],
                    [
                        {"text": "👁 تحت نظارت", "url": f"{base}/oversight?tab=watched"},
                        {"text": "📋 تسک‌ها", "url": f"{base}/oversight?tab=tasks"},
                    ],
                    [
                        {"text": "📊 گزارش‌ها", "url": f"{base}/oversight?tab=reports"},
                        {"text": "💡 ایده‌ها", "url": f"{base}/oversight?tab=ideas"},
                    ],
                    [
                        # 🆕 (Creator) دکمهٔ ساخت پروژه
                        {"text": "🚀 ساخت پروژه", "callback_data": "menu:new_project"},
                        {"text": "🆕 تسک جدید", "callback_data": "menu:new_task"},
                    ],
                    [
                        # 🔔 (Reminder) دکمهٔ یادآوری جدید
                        {"text": "🔔 یادآوری جدید", "callback_data": "menu:reminder"},
                    ],
                    [
                        # 🆕 (Codex) دکمهٔ شناسنامه
                        {"text": "📚 شناسنامهٔ پروژه", "callback_data": "menu:codex"},
                    ],
                    [
                        # 🆕 (AI Usage) دکمهٔ مصرف
                        {"text": "💰 مصرف AI و موجودی", "callback_data": "menu:usage"},
                    ],
                    [
                        {"text": "📦 مخازن", "url": f"{base}/oversight?tab=repos"},
                        {"text": "⚙️ تنظیمات", "url": f"{base}/settings"},
                    ],
                    [{"text": "🏠 صفحهٔ اصلی", "url": f"{base}/"}],
                ]
            }
            # 🆕 (audit-fix) همیشه persistent reply keyboard را با /menu
            # دوباره ست می‌کنیم. علت: کلاینت‌های Telegram (به‌ویژه Web)
            # گاهی keyboard state را وقتی کاربر بین چت‌های bot های مختلف
            # سوئیچ می‌کند گم می‌کنند. /menu باید این مشکل را resolve کند.
            # دو پیام: اول inline keyboard، بعد یک پیام کوتاه با reply_keyboard
            # برای re-attach.
            await tg.send(reply, silent=True, reply_markup=kb)
            await tg.send(
                "🎛 _منوی ثابت در پایین فعال است._",
                silent=True,
                reply_markup=PERSISTENT_REPLY_KEYBOARD,
            )
            return {"ok": True, "handled": "menu"}

        if text == "/status":
            enabled_events = sum(1 for v in prefs.get("events", {}).values() if v)
            total_events = len(EVENT_REGISTRY)
            sound_events = sum(1 for v in prefs.get("sound", {}).values() if v)
            ch_status = self.get_status()["channels"]
            reply = (
                "📊 *وضعیت سیستم نوتیفیکیشن*\n\n"
                f"📨 Telegram: {'✅ آماده' if ch_status['telegram']['ready'] else '❌ غیرفعال'}\n"
                f"📧 Email: {'✅ آماده' if ch_status['email']['ready'] else '❌ غیرفعال'}\n\n"
                f"🔔 رویدادهای فعال: *{enabled_events}/{total_events}*\n"
                f"🔊 با صدا: *{sound_events}*\n"
                f"🎚 حداقل اولویت: *{prefs.get('min_priority', 'low')}*"
            )
            kb = None
            if base:
                kb = {"inline_keyboard": [[{"text": "⚙️ تنظیم در پنل", "url": f"{base}/settings"}]]}
            await tg.send(reply, silent=True, reply_markup=kb)
            return {"ok": True, "handled": "status"}

        # ناشناخته
        await tg.send(
            f"❓ دستور ناشناخته: `{text[:50]}`\nبا /menu، /new\\_task یا /reminder شروع کنید.",
            silent=True,
        )
        return {"ok": True, "handled": "unknown"}

    # -----------------------------------------------------------------------
    # 🆕 (Compose Stage 2) — Telegram media routing → compose buffer
    # -----------------------------------------------------------------------

    # متن دکمه‌های ReplyKeyboard compose (Stage 3 آنها را می‌فرستد، اینجا alias‌گذاری
    # می‌شوند تا hit بگیرد)
    _COMPOSE_BTN_SUBMIT = "✅ ساخت تسک با همه پیوست‌ها"
    _COMPOSE_BTN_SUBMIT_PROJECT = "✅ ساخت پروژه با همه پیوست‌ها"
    _COMPOSE_BTN_CANCEL = "❌ لغو همه"
    _COMPOSE_BTN_TEXT_HINT = "📝 افزودن متن"

    @staticmethod
    def _detect_media(msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """تشخیص نوع media در پیام Telegram. خروجی None اگر فقط متن است.

        خروجی: {type, file_id, filename, mime_type, size, width?, height?, duration?}

        🛡 (audit fix M5) — filename نام منحصربه‌فرد با timestamp + file_unique_id
        می‌گیرد تا collision بین چند upload در یک session غیرممکن باشد.
        """
        import time as _t, uuid as _uuid
        _ts = int(_t.time() * 1000) % 1000000
        def _u(prefix: str, unique_id: str, ext: str) -> str:
            # ترکیب timestamp ms + 4-char از uuid برای uniqueness قطعی
            tail = (unique_id or _uuid.uuid4().hex[:4])[:8]
            return f"{prefix}_{_ts}_{tail}{ext}"
        # voice (.ogg recording)
        v = msg.get("voice")
        if isinstance(v, dict) and v.get("file_id"):
            return {
                "type": "voice",
                "file_id": v["file_id"],
                "filename": _u("voice", v.get("file_unique_id", ""), ".ogg"),
                "mime_type": v.get("mime_type") or "audio/ogg",
                "size": v.get("file_size"),
                "duration": v.get("duration"),
            }
        # video_note (circular video)
        vn = msg.get("video_note")
        if isinstance(vn, dict) and vn.get("file_id"):
            return {
                "type": "video_note",
                "file_id": vn["file_id"],
                "filename": _u("video_note", vn.get("file_unique_id", ""), ".mp4"),
                "mime_type": "video/mp4",
                "size": vn.get("file_size"),
                "duration": vn.get("duration"),
            }
        # video
        vd = msg.get("video")
        if isinstance(vd, dict) and vd.get("file_id"):
            return {
                "type": "video",
                "file_id": vd["file_id"],
                "filename": (vd.get("file_name") or _u("video", vd.get("file_unique_id", ""), ".mp4")),
                "mime_type": vd.get("mime_type") or "video/mp4",
                "size": vd.get("file_size"),
                "width": vd.get("width"),
                "height": vd.get("height"),
                "duration": vd.get("duration"),
            }
        # photo — لیستی از سایزها، بزرگ‌ترین را بگیر
        ph = msg.get("photo")
        if isinstance(ph, list) and ph:
            largest = max(ph, key=lambda x: (x.get("file_size") or 0))
            return {
                "type": "photo",
                "file_id": largest["file_id"],
                "filename": _u("photo", largest.get("file_unique_id", ""), ".jpg"),
                "mime_type": "image/jpeg",
                "size": largest.get("file_size"),
                "width": largest.get("width"),
                "height": largest.get("height"),
            }
        # audio (مثل mp3, m4a)
        au = msg.get("audio")
        if isinstance(au, dict) and au.get("file_id"):
            return {
                "type": "audio",
                "file_id": au["file_id"],
                "filename": (au.get("file_name") or _u("audio", au.get("file_unique_id", ""), ".mp3")),
                "mime_type": au.get("mime_type") or "audio/mpeg",
                "size": au.get("file_size"),
                "duration": au.get("duration"),
            }
        # animation (gif / mp4 animated)
        an = msg.get("animation")
        if isinstance(an, dict) and an.get("file_id"):
            return {
                "type": "animation",
                "file_id": an["file_id"],
                "filename": (an.get("file_name") or _u("animation", an.get("file_unique_id", ""), ".mp4")),
                "mime_type": an.get("mime_type") or "video/mp4",
                "size": an.get("file_size"),
                "width": an.get("width"),
                "height": an.get("height"),
                "duration": an.get("duration"),
            }
        # document (هر نوع فایل دیگر)
        doc = msg.get("document")
        if isinstance(doc, dict) and doc.get("file_id"):
            return {
                "type": "document",
                "file_id": doc["file_id"],
                "filename": doc.get("file_name") or _u("document", doc.get("file_unique_id", ""), ".bin"),
                "mime_type": doc.get("mime_type") or "application/octet-stream",
                "size": doc.get("file_size"),
            }
        return None

    async def _maybe_route_to_compose(
        self, chat_id_str: str, msg: Dict[str, Any], text: str,
    ) -> Optional[Dict[str, Any]]:
        """اگر این پیام را باید به compose buffer هدایت کنیم، انجام بده و dict
        نتیجه برگردان. اگر نه، None برگردان (تا handler عادی ادامه دهد).

        منطق:
        - اگر پیام media دارد → compose mode را auto-start کن (اگر فعال نیست)
          و آیتم را اضافه کن.
        - اگر compose mode فعال است و پیام text بدون command/alias است →
          آن را به buffer به‌عنوان text item اضافه کن.
        - اگر متن دکمهٔ ReplyKeyboard است (submit/cancel) → handler مخصوص
          (Stage 4) به آن می‌رسد، اینجا None می‌دهیم تا flow عادی ادامه یابد.
        - در غیر این صورت → None.
        """
        from .oversight_telegram_compose import (
            get_compose_service, ComposeItem,
        )

        media = self._detect_media(msg)
        # caption هم می‌تواند همراه media آمده باشد
        caption = (msg.get("caption") or "").strip()
        compose_svc = get_compose_service()
        current = compose_svc.get(chat_id_str)

        # اگر text دقیقاً برابر یکی از دکمه‌های ReplyKeyboard است، اینجا rout
        # نکنیم — handler مخصوص (Stage 4) آن را می‌گیرد
        if text in (
            self._COMPOSE_BTN_SUBMIT,
            self._COMPOSE_BTN_SUBMIT_PROJECT,
            self._COMPOSE_BTN_CANCEL,
            self._COMPOSE_BTN_TEXT_HINT,
        ):
            return None

        # /commands → flow عادی، compose را قطع نمی‌کنیم (اگر کاربر در میانهٔ
        # compose دستوری زد، یعنی می‌خواهد flow دیگری شروع شود — current buffer
        # کنار می‌رود ولی auto-cleanup با TTL یا cancel صریح اتفاق می‌افتد)
        if text and text.startswith("/"):
            return None

        if media:
            # auto-start اگر compose فعال نیست
            if current is None:
                # 🆕 (Stage 5) — تشخیص mode بر اساس chat_state فعلی.
                # 🛡 (audit fix B1 CRITICAL — refined) — compose mode=project
                # فقط در phase دقیق `creator_awaiting_idea` فعال می‌شود (همان
                # نقطه‌ای که کاربر باید idea را تایپ کند). در سایر phaseهای
                # creator (awaiting_models, awaiting_type, awaiting_name_or_skip,
                # awaiting_prompt_preview)، compose hijack نشود — به‌جای آن
                # هشدار به کاربر می‌دهیم که باید /new_project را به آن مرحله
                # برساند، یا اگر می‌خواهد تسک بسازد، /cancel کند.
                cur_state = _chat_state.get(chat_id_str) or {}
                cur_phase = cur_state.get("phase", "") or ""
                CREATOR_BLOCKED_PHASES = {
                    "creator_awaiting_models",
                    "creator_awaiting_model_choice",
                    "creator_awaiting_name",
                    "creator_awaiting_name_or_skip",
                    "creator_awaiting_custom_name",
                    "creator_awaiting_type",
                    "creator_awaiting_tech",
                    "creator_awaiting_prompt_preview",
                    "creator_awaiting_desc",
                }
                if cur_phase in CREATOR_BLOCKED_PHASES:
                    # کاربر در نیمهٔ راه /new_project است ولی هنوز نه به idea
                    # رسیده — media را به compose نبر، یک هشدار بده.
                    await self._telegram().send(
                        "⚠️ شما در میانهٔ /new_project هستید (فاز فعلی: "
                        f"`{cur_phase}`). برای پیوست فایل، یا این flow را با "
                        "/cancel ببندید، یا تا رسیدن به مرحلهٔ «ایده» صبر کنید "
                        "و آنجا فایل بفرستید.",
                        silent=False,
                    )
                    return {"ok": True, "handled": "compose_blocked_creator_phase"}
                detected_mode = "project" if cur_phase == "creator_awaiting_idea" else "task"
                # 🛡 watched_id فقط در مسیر /new_task picker معنا دارد
                inherited_watched_id = None
                if cur_phase == "awaiting_idea":
                    inherited_watched_id = cur_state.get("watched_id")
                current = await compose_svc.start(
                    chat_id_str, mode=detected_mode,
                    watched_id=inherited_watched_id,
                )
                await self._compose_send_welcome(chat_id_str, current)

            await self._compose_add_media(chat_id_str, current, media, caption)
            await self._compose_refresh_ui(chat_id_str, current)
            return {"ok": True, "handled": "compose_media_added", "type": media["type"]}

        # text فقط — اگر compose فعال است، به buffer اضافه کن
        if current is not None and text:
            await compose_svc.add_item(
                chat_id_str,
                ComposeItem(order=0, type="text", text=text),
            )
            current = compose_svc.get(chat_id_str)
            if current is not None:
                await self._compose_refresh_ui(chat_id_str, current)
            return {"ok": True, "handled": "compose_text_added"}

        return None

    async def _compose_send_welcome(self, chat_id_str: str, buf: Any) -> None:
        """پیام راهنمای اولین ورود به compose mode + ReplyKeyboard بزرگ.

        ReplyKeyboard دکمه‌های واضح در پایین صفحه (نه inline) — تا پایان
        compose mode dormant باقی می‌ماند.
        """
        from .oversight_telegram_compose import get_compose_service
        tg = self._telegram()
        submit_btn = (
            self._COMPOSE_BTN_SUBMIT
            if buf.mode == "task"
            else self._COMPOSE_BTN_SUBMIT_PROJECT
        )
        welcome = (
            "📦 *حالت ساخت "
            + ("تسک" if buf.mode == "task" else "پروژه")
            + " ترکیبی فعال شد*\n\n"
            "✅ هر تعداد فایل (صوت، ویدئو، عکس، سند، کد) و متن می‌توانی بفرستی.\n"
            "✅ ترتیب رسیدن = ترتیب در پرامپت (اولی → بخش اول).\n"
            "✅ تا زمانی که دکمهٔ زیر را نزنی، هیچ‌چیز ساخته نمی‌شود.\n\n"
            "⬇ از *دکمه‌های پایین صفحه* برای ارسال یا لغو استفاده کن."
        )
        res = await tg.send_with_reply_keyboard(
            welcome,
            keyboard_rows=[
                [submit_btn],
                [self._COMPOSE_BTN_CANCEL],
            ],
            silent=False,
        )
        if res.get("ok"):
            await get_compose_service().set_reply_keyboard_active(chat_id_str, True)

    async def _compose_refresh_ui(self, chat_id_str: str, buf: Any) -> None:
        """به‌روزرسانی UI compose — یک status message که هر بار edit می‌شود
        (به‌جای spam پیام جدید).

        - اگر status_message_id نداریم → اولین status را بفرست
        - اگر داریم → edit (با diff check برای جلوگیری از "not modified")
        - ReplyKeyboard همان قبلی باقی می‌ماند (در welcome ست شده)
        """
        from .oversight_telegram_compose import get_compose_service
        tg = self._telegram()
        compose_svc = get_compose_service()

        # اگر ReplyKeyboard هنوز فعال نشده (case کاربر بدون auto-enter از
        # awaiting_idea رسیده)، حالا فعالش کن
        if not buf.reply_keyboard_active:
            submit_btn = (
                self._COMPOSE_BTN_SUBMIT
                if buf.mode == "task"
                else self._COMPOSE_BTN_SUBMIT_PROJECT
            )
            await tg.send_with_reply_keyboard(
                "📦 آیتم اضافه شد — می‌توانی پیوست/متن بیشتر بفرستی، یا دکمهٔ زیر را بزنی.",
                keyboard_rows=[[submit_btn], [self._COMPOSE_BTN_CANCEL]],
                silent=True,
            )
            await compose_svc.set_reply_keyboard_active(chat_id_str, True)

        # ساخت متن status
        status_text = self._compose_render_status(buf)

        # اگر status_message_id داریم، edit کن
        if buf.status_message_id:
            res = await tg.edit_message_text(
                tg.chat_id, buf.status_message_id, status_text,
                parse_mode="Markdown",
            )
            if res.get("ok"):
                return
            # اگر edit fail (مثلاً پیام delete شده توسط کاربر)، یک پیام جدید بفرست
            logger.debug(f"compose: edit status failed, sending new: {res.get('error')}")

        # ارسال پیام جدید + ذخیرهٔ message_id
        send_res = await tg.send(status_text, silent=True)
        # نکته: TelegramChannel.send فعلاً message_id را برنمی‌گرداند مگر در
        # موارد خاص. در حال حاضر یک fallback نرم: اگر status_message_id نگرفتیم،
        # دفعهٔ بعد یک پیام جدید می‌رود (idempotency کامل نیست ولی spam نمی‌شود
        # چون status فقط در صورت تغییر می‌آید). در stage 4 message_id را از
        # response واقعی می‌خوانیم.
        # برای الان، یک تماس مستقیم با sendMessage که message_id را برگرداند:
        try:
            import aiohttp as _ah
            url = f"https://api.telegram.org/bot{tg.bot_token}/sendMessage"
            payload = {
                "chat_id": tg.chat_id,
                "text": status_text[:4000],
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
                "disable_notification": True,
            }
            timeout = _ah.ClientTimeout(total=15)
            async with _ah.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as r:
                    body = await r.json()
                    if body.get("ok"):
                        mid = (body.get("result") or {}).get("message_id")
                        if mid:
                            await compose_svc.set_status_message_id(chat_id_str, int(mid))
        except Exception as e:
            logger.debug(f"compose: send status (with id) failed: {e}")

    @staticmethod
    def _compose_render_status(buf: Any) -> str:
        """متن status message با همهٔ آیتم‌های فعلی."""
        files = buf.file_items_sorted()
        texts = buf.text_items_sorted()
        total_size_mb = buf.total_size_bytes() / 1024.0 / 1024.0
        header = (
            f"📦 *در حال ساخت "
            + ("تسک" if buf.mode == "task" else "پروژه")
            + f" ترکیبی* — {buf.total_files()} فایل ({total_size_mb:.2f}MB) + {len(texts)} پیام متنی\n"
            "─────────────────"
        )
        lines: List[str] = [header]
        # همهٔ items به ترتیب order
        for it in sorted(buf.items, key=lambda x: x.order):
            type_icon = {
                "voice": "🎙", "video_note": "🎬", "video": "🎞",
                "photo": "🖼", "audio": "🎵", "document": "📄",
                "animation": "🌀", "text": "📝",
            }.get(it.type, "📎")
            if it.type == "text":
                txt = (it.text or "").replace("\n", " ").replace("`", "ʼ")
                preview = txt[:80] + ("..." if len(txt) > 80 else "")
                lines.append(f"  {it.order}. {type_icon} متن: _{preview}_")
            else:
                size_kb = (it.size_bytes or 0) / 1024.0
                size_str = (
                    f"{size_kb / 1024:.1f}MB" if size_kb >= 1024 else f"{int(size_kb)}KB"
                )
                dur = (
                    f" ⏱{int(it.duration_seconds)}s"
                    if it.duration_seconds else ""
                )
                err = f" ⚠️{it.error[:50]}" if it.error else ""
                fname = (it.filename or it.type).replace("`", "ʼ")
                lines.append(
                    f"  {it.order}. {type_icon} `{fname[:50]}` ({size_str}){dur}{err}"
                )
        if not buf.items:
            lines.append("  _(هنوز آیتمی اضافه نشده)_")
        lines.append("─────────────────")
        if buf.mode == "task" and not buf.watched_id:
            lines.append("⚠️ پروژهٔ هدف انتخاب نشده — هنگام submit از تو خواسته می‌شود.")
        lines.append("⬇ از دکمه‌های پایین برای ارسال یا لغو استفاده کن.")
        return "\n".join(lines)

    async def _compose_add_media(
        self,
        chat_id_str: str,
        buf: Any,
        media: Dict[str, Any],
        caption: str = "",
    ) -> None:
        """download فایل از Telegram → start UploadSession → append chunk →
        add ComposeItem به buffer.

        اگر caption هم داشت، یک text item جدا اضافه می‌شود (با همان order).
        """
        from .oversight_telegram_compose import (
            get_compose_service, ComposeItem,
        )
        from .oversight_upload_session import (
            get_upload_session_service, DEFAULT_MAX_FILE_BYTES,
        )
        tg = self._telegram()
        compose_svc = get_compose_service()
        up_svc = get_upload_session_service()

        size = int(media.get("size") or 0)
        # محدودیت Bot API: ~20MB
        if size > 20 * 1024 * 1024:
            await tg.send(
                f"⚠️ فایل {media.get('filename', '?')} حدود {size // 1024 // 1024}MB است. "
                f"محدودیت دانلود Bot API تلگرام 20MB است.\n"
                f"برای فایل‌های بزرگ‌تر، لطفاً از پنل وب آپلود کنید.",
                silent=False,
            )
            return

        # 🛡 (audit fix M4) — getFile و download را اول انجام بده. فقط
        # اگر هر دو موفق شدند، آیتم را به buffer اضافه کن. در نتیجه
        # بافر هیچ‌گاه ComposeItem با error نخواهد داشت (مگر start_session
        # شکست بخورد که عملاً غیرممکن است).
        info = await tg.get_file(media["file_id"])
        if not info or not info.get("file_path"):
            await tg.send(
                f"❌ نتوانستم اطلاعات فایل {media.get('filename', '?')} را از تلگرام بگیرم. لطفاً دوباره ارسال کن.",
                silent=False,
            )
            return
        file_path = info["file_path"]
        actual_size = int(info.get("file_size") or size or 0)
        if actual_size <= 0:
            await tg.send(f"⚠️ فایل خالی است — نادیده گرفته شد.", silent=True)
            return

        data = await tg.download_file(file_path)
        if not data:
            await tg.send(
                f"❌ download فایل {media.get('filename', '?')} ناموفق بود. لطفاً دوباره ارسال کن.",
                silent=False,
            )
            return

        # ـ ۲) UploadSession را بساز (data آماده و موجود است)
        try:
            sess = await up_svc.start_session(
                task_draft_id=buf.task_draft_id,
                original_filename=media["filename"],
                mime_type=media["mime_type"],
                total_size=len(data),
            )
            await up_svc.append_chunk(sess.id, 0, data)
            sess2 = up_svc.get(sess.id)
            if sess2 and sess2.status != "completed":
                await up_svc.mark_completed(sess.id)
            upload_session_id = sess.id
        except Exception as e:
            logger.exception(f"compose add_media: upload failed: {e}")
            await tg.send(
                f"❌ خطای داخلی در ذخیرهٔ {media.get('filename', '?')}: {str(e)[:200]}",
                silent=False,
            )
            return  # هیچ‌چیز به buffer اضافه نمی‌کنیم

        # ـ ۳) فقط اگر همه‌چیز موفق بود، آیتم را به buffer اضافه کن
        item = ComposeItem(
            order=0,  # ست خواهد شد در add_item
            type=media["type"],
            telegram_file_id=media["file_id"],
            telegram_file_path=file_path,
            filename=media["filename"],
            mime_type=media["mime_type"],
            size_bytes=actual_size,
            upload_session_id=upload_session_id,
            width=media.get("width"),
            height=media.get("height"),
            duration_seconds=media.get("duration"),
            error=None,
        )
        await compose_svc.add_item(chat_id_str, item)

        # 5) caption (در صورت داشتن) به‌عنوان text item جدا
        if caption:
            await compose_svc.add_item(
                chat_id_str,
                ComposeItem(order=0, type="text", text=caption),
            )

    @staticmethod
    def _fmt_compose_item(it: Any) -> str:
        type_icon = {
            "voice": "🎙",
            "video_note": "🎬",
            "video": "🎞",
            "photo": "🖼",
            "audio": "🎵",
            "document": "📄",
            "animation": "🌀",
            "text": "📝",
        }.get(it.type, "📎")
        size_mb = ((it.size_bytes or 0) / 1024.0 / 1024.0)
        size_str = f"{size_mb:.2f}MB" if size_mb >= 1 else f"{(it.size_bytes or 0) // 1024}KB"
        parts = [type_icon, it.filename or it.type, f"({size_str})"]
        if it.duration_seconds:
            parts.append(f"⏱{int(it.duration_seconds)}s")
        return " ".join(parts)

    async def _compose_submit(self, chat_id_str: str, *, mode: str = "task") -> Dict[str, Any]:
        """پایپ‌لاین submit نهایی — buffer را به idea_to_prompt + create_task
        (یا new_project — Stage 5) منتقل می‌کند.

        flow:
          1. validate buffer (وجود + has items)
          2. اگر mode=task و watched_id خالی → picker پروژه + state
             `phase=compose_awaiting_watched_id` (callback همان buffer)
          3. mark_submitting=True (جلوگیری از double-click)
          4. remove_reply_keyboard
          5. idea = join(text_parts)؛ اگر خالی + فایل هست →
             intent_from_files_only=True
          6. await idea_to_prompt(idea, upload_session_ids=...)
          7. create_task با upload_session_ids
          8. finalize_after_submit (buffer پاک)
          9. _send_task_created_message (با PDF + checklist + regen button)
          10. در صورت exception → unmark + پیام خطا، buffer دست‌نخورده
        """
        from .oversight_telegram_compose import get_compose_service
        from .oversight_service import get_oversight_service
        tg = self._telegram()
        compose_svc = get_compose_service()
        buf = compose_svc.get(chat_id_str)
        if buf is None:
            await tg.send("⚠️ هیچ compose فعالی نیست. /new\\_task بزن.", silent=True)
            return {"ok": True, "handled": "compose_submit_no_buffer"}

        # validate
        if not buf.items:
            await tg.send(
                "⚠️ buffer خالی است — حداقل یک فایل یا متن بفرست تا submit ممکن شود.",
                silent=True,
            )
            return {"ok": True, "handled": "compose_submit_empty"}

        if buf.submitting:
            # double-click protection
            return {"ok": True, "handled": "compose_submit_already_running"}

        # 🛡 (audit fix M3) — atomic submit-lock قبل از همهٔ async calls، تا
        # دو callback همزمان (race) هر دو نگذرند. اگر یکی سریع‌تر mark کرد،
        # دومی در پایان if buf.submitting بالا می‌گیرد.
        await compose_svc.mark_submitting(chat_id_str, True)

        # Stage 5: mode=project مسیر دیگری دارد
        if mode == "project":
            return await self._compose_submit_project(chat_id_str, buf)

        # 🆕 task mode: اگر پروژه انتخاب نشده، picker
        if not buf.watched_id:
            # un-mark تا انتخاب پروژه مسدود نشود
            await compose_svc.mark_submitting(chat_id_str, False)
            return await self._compose_pick_project(chat_id_str, buf)

        # remove ReplyKeyboard
        await tg.remove_reply_keyboard("⏳ شروع پردازش...")

        try:
            return await self._compose_run_pipeline_task(chat_id_str, buf)
        except Exception as e:
            logger.exception(f"compose submit failed: {e}")
            # un-mark تا کاربر بتواند دوباره تلاش کند
            await compose_svc.mark_submitting(chat_id_str, False)
            # دکمه‌ها دوباره برگردانده شوند
            submit_btn = self._COMPOSE_BTN_SUBMIT
            await tg.send_with_reply_keyboard(
                f"❌ خطا در پردازش submit:\n`{str(e)[:300]}`\n\n"
                f"می‌توانی دوباره تلاش کنی یا با `{self._COMPOSE_BTN_CANCEL}` لغو کنی.",
                keyboard_rows=[[submit_btn], [self._COMPOSE_BTN_CANCEL]],
                silent=False,
            )
            return {"ok": False, "handled": "compose_submit_failed", "error": str(e)[:300]}

    async def _send_compose_vision_toggle(
        self, chat_id_str: str, buf: Any, blocked: Dict[str, Any],
    ) -> None:
        """🛡 (audit fix) — Telegram inline keyboard معادل modal فرانت‌اند.

        وقتی idea_to_prompt به‌دلیل نبود vision model fail می‌شود، این تابع
        یک پیام با inline_keyboard می‌فرستد که هر دکمه یک candidate model
        است. callback `compose_temp_activate:<model_id>:<chat_id>` آن را
        به temp-activate route می‌برد و سپس re-submit می‌کند.
        """
        tg = self._telegram()
        candidates = blocked.get("candidates", []) or []
        mime = blocked.get("mime_type") or "image/*"
        missing_files = blocked.get("missing_files", []) or []

        text_lines = [
            "🔓 *مدل بصری برای استخراج فایل پیوست لازم است*",
            "",
            f"فایل‌های زیر نیاز به vision model دارند (mime: `{mime}`):",
        ]
        for mf in missing_files[:3]:
            text_lines.append(f"  • {mf.get('filename', '?')}")
        if len(missing_files) > 3:
            text_lines.append(f"  • … و {len(missing_files) - 3} فایل دیگر")
        text_lines.append("")
        text_lines.append("یک مدل را موقتاً فعال کن — کار انجام می‌شود سپس")
        text_lines.append("خودکار غیرفعال می‌شود (با اطلاع تلگرام).")

        # inline keyboard rows
        rows: List[List[Dict[str, str]]] = []
        for i, c in enumerate(candidates[:6]):
            cid = c.get("id") or ""
            cname = (c.get("name") or cid)[:35]
            prov = c.get("provider") or ""
            star = "⭐ " if i == 0 else ""
            rows.append([{
                "text": f"{star}🔓 {cname} ({prov})",
                "callback_data": f"compose_temp_activate:{cid}",
            }])
        rows.append([
            {"text": "❌ لغو", "callback_data": "compose_cancel_picker"},
        ])

        await tg.send(
            "\n".join(text_lines),
            silent=False,
            reply_markup={"inline_keyboard": rows},
        )

    async def _compose_submit_project(
        self, chat_id_str: str, buf: Any,
    ) -> Dict[str, Any]:
        """submit برای mode=project:

        1. validate (creator state موجود است؟)
        2. resolve attachments → extracted text
        3. text_parts + extracted text → full idea (augmented)
        4. state.creator_data.idea = augmented_idea
        5. continue creator flow:
           - `_receive_creator_idea` که name picker را نشان می‌دهد
           - یا اگر name از قبل ست شده، مستقیم preview
        6. compose buffer finalize (sessions حفظ، به new project ربط می‌خورند
           پس از موفقیت _execute_creator_v2)
        """
        from .oversight_telegram_compose import get_compose_service
        from .oversight_service import get_oversight_service
        tg = self._telegram()
        compose_svc = get_compose_service()

        # state creator باید موجود باشد
        state = _chat_state.get(chat_id_str) or {}
        cdata = state.get("creator_data") or {}
        if not cdata.get("model_ids"):
            await tg.send(
                "⚠️ creator state موجود نیست. /new\\_project بزن و مدل‌ها را اول انتخاب کن.",
                silent=False,
            )
            await compose_svc.cancel(chat_id_str)
            await tg.remove_reply_keyboard("compose پاک شد.")
            return {"ok": True, "handled": "compose_project_no_creator_state"}

        # validate buffer
        if not buf.items:
            await tg.send(
                "⚠️ buffer خالی است — حداقل یک فایل یا متن بفرست.",
                silent=True,
            )
            return {"ok": True, "handled": "compose_project_empty"}

        if buf.submitting:
            return {"ok": True, "handled": "compose_project_already_running"}

        # 🛡 (audit fix M3) — قبل از حتی validate state، lock بزن
        await compose_svc.mark_submitting(chat_id_str, True)

        await tg.remove_reply_keyboard("⏳ شروع پردازش...")

        try:
            return await self._compose_run_pipeline_project(chat_id_str, buf, state)
        except Exception as e:
            logger.exception(f"compose submit project failed: {e}")
            await compose_svc.mark_submitting(chat_id_str, False)
            await tg.send_with_reply_keyboard(
                f"❌ خطا در پردازش submit پروژه:\n`{str(e)[:300]}`\n\n"
                f"می‌توانی دوباره تلاش کنی.",
                keyboard_rows=[
                    [self._COMPOSE_BTN_SUBMIT_PROJECT],
                    [self._COMPOSE_BTN_CANCEL],
                ],
                silent=False,
            )
            return {"ok": False, "handled": "compose_project_failed", "error": str(e)[:300]}

    async def _compose_run_pipeline_project(
        self, chat_id_str: str, buf: Any, state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """resolve attachments → augment idea → continue creator flow."""
        from .oversight_telegram_compose import get_compose_service
        from .oversight_service import get_oversight_service
        tg = self._telegram()
        compose_svc = get_compose_service()
        _ov = get_oversight_service()
        cdata = state.setdefault("creator_data", {})

        # متن‌ها + extraction
        text_parts: List[str] = []
        for it in buf.text_items_sorted():
            t = (it.text or "").strip()
            if t:
                text_parts.append(t)
        user_text = "\n\n".join(text_parts).strip()
        session_ids = buf.session_ids_in_order()

        if not session_ids and not user_text:
            await tg.send("⚠️ نه فایلی صحیح، نه متنی — submit ممکن نیست.", silent=True)
            await compose_svc.mark_submitting(chat_id_str, False)
            return {"ok": True, "handled": "compose_project_no_content"}

        # placeholder text-only هم OK
        if not user_text:
            user_text = (
                "[ایدهٔ متنی همراه نیست — دستورالعمل/درخواست کاربر داخل "
                "محتوای فایل‌های پیوست است.]"
            )

        # پیام شروع
        await tg.send(
            "⏳ *در حال پردازش submit پروژهٔ جدید*\n"
            f"📎 {buf.total_files()} فایل، 📝 {len(text_parts)} متن\n\n"
            "مراحل:\n"
            "  1. استخراج متن از فایل‌ها\n"
            "  2. تولید پرامپت پروژه (creator)\n"
            "  3. نمایش preview برای تأیید\n",
            silent=False,
        )

        # 1) extraction از طریق _resolve_attachments_for_idea (همان وب)
        augmented_idea = user_text
        if session_ids:
            try:
                augmented_idea, attachments_meta = await _ov._resolve_attachments_for_idea(
                    user_text, session_ids,
                )
            except Exception as e:
                logger.warning(f"compose project extraction failed: {e}")
                # ادامه با user_text ساده
                augmented_idea = user_text + f"\n\n[خطا در استخراج فایل‌ها: {str(e)[:200]}]"
                attachments_meta = []

        # 2) ذخیره در state و انتقال به phase نام
        cdata["idea"] = augmented_idea
        # auto-suggest name از augmented_idea
        import re as _re
        words = _re.findall(r"[a-zA-Z]+", augmented_idea.lower())[:3]
        suggested = "-".join(words) if words else "telegram-project"
        cdata["suggested_name"] = suggested

        state["phase"] = "creator_awaiting_name_or_skip"
        state["expires_at"] = _now_epoch() + _STATE_TTL_SECONDS
        _chat_state[chat_id_str] = state

        # 3) finalize compose (sessions حفظ — بعداً اگر لازم به new project ربط داده می‌شوند)
        await compose_svc.finalize_after_submit(chat_id_str)

        # 4) نمایش name picker
        idea_len = len(augmented_idea)
        kb = {
            "inline_keyboard": [
                [{"text": f"✅ استفاده از: {suggested}", "callback_data": "creator_use_suggested_name"}],
                [{"text": "✏️ نام دلخواه", "callback_data": "creator_custom_name"}],
                [{"text": "❌ لغو", "callback_data": "flow:cancel"}],
            ]
        }
        await tg.send(
            f"💡 *ایدهٔ پروژه از پیوست‌ها استخراج شد*\n\n"
            f"📋 طول idea: {idea_len:,} کاراکتر\n"
            f"📎 {buf.total_files()} فایل پیوست بود → متن کامل در idea ادغام شد\n\n"
            f"📦 *مرحلهٔ بعد: نام پروژه*\n"
            f"پیشنهاد: `{suggested}`",
            silent=True,
            reply_markup=kb,
        )
        return {
            "ok": True,
            "handled": "compose_project_idea_resolved",
            "idea_len": idea_len,
            "files": buf.total_files(),
        }

    async def _compose_pick_project(
        self, chat_id_str: str, buf: Any,
    ) -> Dict[str, Any]:
        """اگر watched_id ست نیست، list پروژه‌ها به‌صورت inline keyboard
        نمایش داده می‌شود. callback `compose_pick:<watched_id>` آن را ست
        می‌کند و دوباره submit را trigger می‌کند.
        """
        from .oversight_service import get_oversight_service
        tg = self._telegram()
        try:
            _ov = get_oversight_service()
            watched = list(getattr(_ov, "watched", []) or [])
        except Exception as e:
            await tg.send(f"❌ خواندن پروژه‌ها ناموفق: {e}", silent=False)
            return {"ok": False, "handled": "compose_pick_load_failed"}

        if not watched:
            await tg.send(
                "⚠️ هیچ پروژهٔ تحت نظارت موجود نیست. اول /new\\_project بزن یا پروژه‌ای را watch کن.",
                silent=False,
            )
            return {"ok": True, "handled": "compose_pick_no_watched"}

        rows: List[List[Dict[str, str]]] = []
        for w in watched[:20]:
            rows.append([{
                "text": f"📁 {w.repo_full_name[:60]}",
                "callback_data": f"compose_pick:{w.id}",
            }])
        rows.append([{"text": "❌ لغو", "callback_data": "compose_cancel_picker"}])
        await tg.send(
            "📌 *کدام پروژه را برای این تسک می‌خواهی؟*\n\n"
            "بعد از انتخاب، تسک با تمام پیوست‌های فرستاده‌شده ساخته می‌شود.",
            silent=False,
            reply_markup={"inline_keyboard": rows},
        )
        return {"ok": True, "handled": "compose_picker_shown"}

    async def _compose_run_pipeline_task(
        self, chat_id_str: str, buf: Any,
    ) -> Dict[str, Any]:
        """اصل اجرای پایپ‌لاین task mode — بعد از validate + remove_keyboard.

        🛡 (audit fix) — wrapper try/finally تضمین می‌کند که اگر
        `buf.temp_activated_model_id` ست شده (یعنی کاربر مدلی را در همین
        session موقتاً فعال کرد)، پس از اتمام pipeline (موفقیت یا خطا)
        خودکار revert می‌شود.
        """
        # capture activated model_id قبل از اجرا (در صورت finalize buf،
        # ممکن است reference بعداً به‌روز نشود).
        temp_activated_id = getattr(buf, "temp_activated_model_id", None)
        try:
            return await self._compose_run_pipeline_task_inner(chat_id_str, buf)
        finally:
            if temp_activated_id:
                try:
                    from .oversight_model_temp_activate import temp_revert_model
                    await temp_revert_model(
                        temp_activated_id,
                        trigger=f"telegram-compose-done-{chat_id_str}",
                    )
                except Exception as _rev_e:
                    logger.warning(f"compose temp revert failed: {_rev_e}")

    async def _compose_run_pipeline_task_inner(
        self, chat_id_str: str, buf: Any,
    ) -> Dict[str, Any]:
        """بدنهٔ اصلی pipeline (همان _compose_run_pipeline_task سابق)."""
        from .oversight_service import get_oversight_service
        from .oversight_telegram_compose import get_compose_service
        from .oversight_progress import get_progress_tracker
        tg = self._telegram()
        _ov = get_oversight_service()
        compose_svc = get_compose_service()
        tracker = get_progress_tracker()
        prefs = _read_prefs()
        base = (prefs.get("app_base_url", "") or "").rstrip("/")

        # 1) جمع متن‌ها — به‌ترتیب order
        text_parts: List[str] = []
        for it in buf.text_items_sorted():
            t = (it.text or "").strip()
            if t:
                text_parts.append(t)
        idea = "\n\n".join(text_parts).strip()
        files_only = (not idea) and (buf.total_files() > 0)

        # 2) upload_session_ids به ترتیب file_order
        session_ids = buf.session_ids_in_order()

        if not session_ids and not idea:
            await tg.send("⚠️ نه فایلی صحیح آپلود شده، نه متنی نوشته شده.", silent=True)
            await compose_svc.mark_submitting(chat_id_str, False)
            return {"ok": True, "handled": "compose_submit_no_content"}

        # 3) پیام شروع + register progress tracker با Telegram callback
        await tracker.start(
            buf.task_draft_id,
            stage="starting",
            total=buf.total_files() + 2,  # +1 idea_to_prompt + +1 create_task
            detail="شروع پردازش",
        )
        # send initial status message + ذخیرهٔ message_id برای edit
        status_msg_id = None
        try:
            import aiohttp as _ah
            initial_text = (
                "⏳ *در حال پردازش submit*\n"
                f"📎 {buf.total_files()} فایل ({buf.total_size_bytes() // 1024 // 1024 + 1}MB) + "
                f"{len(text_parts)} متن\n"
                f"📊 progress: 0/{buf.total_files() + 2}\n\n"
                "این پیام در حین پیشرفت به‌روز می‌شود."
            )
            url = f"https://api.telegram.org/bot{tg.bot_token}/sendMessage"
            payload = {
                "chat_id": tg.chat_id, "text": initial_text,
                "parse_mode": "Markdown", "disable_notification": False,
            }
            timeout = _ah.ClientTimeout(total=15)
            async with _ah.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as r:
                    body = await r.json()
                    if body.get("ok"):
                        status_msg_id = (body.get("result") or {}).get("message_id")
        except Exception as e:
            logger.debug(f"compose progress: initial send failed: {e}")

        # progress callback — هر بار update با throttle، پیام را edit می‌کند
        if status_msg_id:
            async def _on_progress(snap):
                try:
                    pct = int(snap.percent)
                    bar_len = 12
                    filled = int(bar_len * pct / 100)
                    bar = "█" * filled + "░" * (bar_len - filled)
                    text = (
                        f"⏳ *در حال پردازش submit*\n"
                        f"📊 `[{bar}]` {pct}%\n"
                        f"مرحله: *{snap.stage}*\n"
                        f"{snap.detail or '...'}"
                    )
                    if snap.completed:
                        if snap.error:
                            text = f"❌ *خطا*\n{snap.error[:300]}"
                        else:
                            text = f"✅ *پردازش کامل شد*\nطول: {snap.elapsed_seconds():.1f}s\n{snap.detail or ''}"
                    await tg.edit_message_text(
                        tg.chat_id, status_msg_id, text, parse_mode="Markdown",
                    )
                except Exception as e:
                    logger.debug(f"progress callback edit failed: {e}")
            tracker.register_callback(buf.task_draft_id, _on_progress)

        # 4) idea_to_prompt
        if files_only:
            # اگر idea خالی + فقط فایل: یک placeholder که به multi-pass
            # explicitly می‌گوید intent در فایل‌ها است
            idea_for_ai = (
                "[ایدهٔ متنی همراه نیست — دستورالعمل/درخواست کاربر **داخل** "
                "محتوای فایل‌های پیوست است. لطفاً متن استخراج‌شدهٔ فایل‌ها را "
                "بخوان، دستورالعمل را از آنجا برداشت کن، و یک پرامپت کامل "
                "بساز.]"
            )
        else:
            idea_for_ai = idea

        await tracker.update(
            buf.task_draft_id,
            stage="extracting_and_prompting",
            current=1,
            detail=f"استخراج {buf.total_files()} فایل و تولید پرامپت...",
            throttle_sec=2.0,
        )

        try:
            # 🛡 (audit fix #3) — Telegram compose **همیشه** multi-pass تا
            # checklist تولید شود. تسک‌های Telegram اغلب فایل‌محور هستند یا
            # idea کوتاهی دارند که heuristic auto آن را single-pass تشخیص
            # می‌دهد و چک‌لیست از دست می‌رود.
            # 🔔 (Reminder via Telegram) — اگر compose با /reminder شروع شده،
            # force_type="reminder" پاس می‌شود تا idea_to_prompt به مسیر
            # اختصاصی reminder برود (نه code-grounded).
            _force_type = getattr(buf, "force_type", None) or "other"
            preview = await _ov.idea_to_prompt(
                idea=idea_for_ai,
                watched_id=buf.watched_id,
                type_=_force_type,
                upload_session_ids=session_ids or None,
                progress_track_id=buf.task_draft_id,
                multi_pass_mode="always",
            )
        except ValueError as e:
            # 🛡 (audit fix) — اگر blocked_no_vision_model است، toggle UI
            # به جای error پیام نشان بده.
            blocked = getattr(e, "blocked_payload", None)
            if blocked:
                reason = blocked.get("reason") or "blocked_no_vision_model"

                # 🆕 (audit fix CRITICAL) — تمام استخراج‌ها fail شدند و کاربر
                # متن نفرستاد: یک پیام واضح به کاربر بفرست، نه toggle UI
                if reason == "all_extractions_failed":
                    await tracker.complete(
                        buf.task_draft_id, stage="failed",
                        error="all extractions failed",
                    )
                    failed_files = blocked.get("failed_files") or []
                    files_list = "\n".join(
                        f"  • {n}" for n in failed_files[:10]
                    ) or "  • (نام فایل‌ها در دسترس نیست)"
                    msg = (
                        "❌ <b>استخراج هیچ‌یک از فایل‌های پیوست موفق نبود.</b>\n\n"
                        f"فایل‌ها:\n{files_list}\n\n"
                        "از آنجا که متن همراه هم نفرستادید، نمی‌توانم درخواست شما "
                        "را حدس بزنم و پرامپتی بر اساس پیام‌های خطا نمی‌سازم "
                        "(تا پرامپت توهمی تولید نشود).\n\n"
                        "🔧 <b>راه‌حل‌ها:</b>\n"
                        "  1) از <code>/models</code> یک مدل بصری دیگر "
                        "(مثلاً <code>gemini-2.5-pro</code>) را به‌عنوان "
                        "default extraction تنظیم کنید و دوباره ارسال کنید.\n"
                        "  2) متن درخواست را به‌صورت تایپی همراه فایل ارسال کنید.\n"
                        "  3) یا فایل صوتی/ویدئویی را با کیفیت بالاتر یا "
                        "فرمت دیگری (mp3/wav) دوباره بفرستید."
                    )
                    try:
                        tg = self._telegram()
                        # markdown parse_mode (helper default) — تگ‌های HTML را
                        # به معادل markdown برمی‌گردانیم
                        md = (
                            msg.replace("<b>", "*").replace("</b>", "*")
                               .replace("<code>", "`").replace("</code>", "`")
                        )
                        await tg.send(md, silent=False)
                    except Exception as _send_e:
                        logger.debug(f"send all-failed notify failed: {_send_e}")
                    await compose_svc.mark_submitting(chat_id_str, False)
                    return {
                        "ok": True,
                        "handled": "compose_all_extractions_failed",
                        "failed_files": failed_files,
                    }

                await tracker.complete(
                    buf.task_draft_id, stage="blocked",
                    error="vision model unavailable",
                )
                await self._send_compose_vision_toggle(chat_id_str, buf, blocked)
                # mark_submitting را un-mark می‌کنیم تا کاربر بتواند بعد از
                # toggle دوباره submit بزند
                await compose_svc.mark_submitting(chat_id_str, False)
                return {
                    "ok": True,
                    "handled": "compose_blocked_no_vision",
                    "candidates": blocked.get("candidates", []),
                }
            await tracker.complete(
                buf.task_draft_id, stage="failed",
                error=f"idea_to_prompt failed: {e}",
            )
            raise RuntimeError(f"idea_to_prompt failed: {e}")
        except Exception as e:
            await tracker.complete(
                buf.task_draft_id, stage="failed",
                error=f"idea_to_prompt failed: {e}",
            )
            raise RuntimeError(f"idea_to_prompt failed: {e}")

        await tracker.update(
            buf.task_draft_id,
            stage="creating_task",
            current=buf.total_files() + 1,
            detail="ذخیرهٔ تسک و آماده‌سازی PDF فیدبک...",
            throttle_sec=2.0,
        )

        # 5) dedup check (find_similar_active_tasks)
        title = preview.get("title") or (text_parts[0][:80] if text_parts else "تسک ترکیبی از تلگرام")
        try:
            similar = _ov.find_similar_active_tasks(
                project_id=buf.watched_id,
                candidate_title=title,
                candidate_raw_idea=idea or title,
            )
        except Exception:
            similar = []

        # 6) create_task
        # 🐛 (raw_idea fix) — قبلاً وقتی کاربر در تلگرام فقط فایل صوتی یا PDF
        # می‌فرستاد و متن همراه نمی‌نوشت، raw_idea تسک به
        # "(از فایل پیوست)" تنزل می‌یافت و transcript صوت / extract فایل از
        # دست می‌رفت. الان از preview.raw_idea (که شامل متن کاربر +
        # محتوای کامل استخراج‌شدهٔ فایل‌هاست) استفاده می‌کنیم تا برای
        # بازتولید و نمایش در UI ایدهٔ واقعی در دسترس باشد.
        _resolved_raw_idea = (
            preview.get("raw_idea")
            or idea
            or "(از فایل پیوست)"
        )
        # 🔔 (Reminder via Telegram) — اگر force_type="reminder"، فیلدهای
        # خاص reminder را از preview استخراج کن. _idea_to_prompt_reminder
        # علاوه بر title/checklist، reminder_at و reminder_repeat_rule را
        # هم از متن کاربر استخراج می‌کند (با AI). اگر AI زمان پیدا نکرد،
        # reminder_at=None می‌ماند و create_task خودش ValueError می‌دهد
        # که در except زیر به کاربر گفته می‌شود زمان مشخص کند.
        _task_payload: Dict[str, Any] = {
            "watched_id": buf.watched_id,
            "title": title,
            "prompt": preview.get("prompt") or "",
            "raw_idea": _resolved_raw_idea,
            "type": preview.get("type") or "other",
            "priority": preview.get("priority") or "medium",
            "source": "telegram_bot_compose",
            "target_files": preview.get("target_files") or [],
            "acceptance_criteria": preview.get("acceptance_criteria") or [],
            "task_steps": preview.get("task_steps") or [],
            "overall_completion_pct": preview.get("overall_completion_pct"),
            "upload_session_ids": session_ids,
            "force_create": True,  # dedup را خود پایپ‌لاین خاص anjam داده
        }
        if (preview.get("type") or "").lower() == "reminder":
            _rem_at = preview.get("reminder_at")
            _task_payload["reminder_at"] = _rem_at
            _task_payload["reminder_repeat_rule"] = preview.get(
                "reminder_repeat_rule"
            )
            if not _rem_at:
                # زمان مشخص نیست — به‌جای fail کردن create_task، یک پیش‌فرض
                # ۱ ساعت بعد بگذار و در پیام به کاربر بگو که می‌تواند با
                # snooze زمان را تغییر دهد. این UX بهتر از خطای سخت است.
                from datetime import datetime as _dt_rem, timedelta as _td_rem, timezone as _tz_rem
                _task_payload["reminder_at"] = (
                    _dt_rem.now(_tz_rem.utc) + _td_rem(hours=1)
                ).isoformat()
                logger.info(
                    "reminder via telegram: AI زمان مشخصی استخراج نکرد — "
                    "پیش‌فرض ۱ ساعت بعد ست شد."
                )
        try:
            result = await _ov.create_task(_task_payload)
        except Exception as e:
            raise RuntimeError(f"create_task failed: {e}")

        new_task = result.get("task") or {}

        # 7) finalize compose
        await compose_svc.finalize_after_submit(chat_id_str)

        # 8) پیام نهایی با PDF + checklist + regen button
        await self._send_task_created_message(new_task, base=base)

        # 9) اگر similar matches بود، بعدش پیام informative
        if similar:
            lines = ["ℹ️ توجه: تسک‌های مشابه پیدا شد (force_create=true فعال بود):"]
            for m in similar[:3]:
                lines.append(f"  • «{m.title[:50]}» — شباهت {int(m.score * 100)}٪")
            await self._telegram().send("\n".join(lines), silent=True)

        # progress complete
        await tracker.complete(
            buf.task_draft_id, stage="done",
            detail=f"✅ تسک «{(new_task.get('title') or '')[:60]}» ساخته شد",
            result={"task_id": new_task.get("id")},
        )

        return {
            "ok": True,
            "handled": "compose_submit_done",
            "task_id": new_task.get("id"),
            "files_only": files_only,
        }

    # -----------------------------------------------------------------------
    # 🆕 (P5) /new_task flow — ثبت تسک از تلگرام با انتخاب پروژه
    # -----------------------------------------------------------------------

    async def _start_new_task_flow(self, chat_id_str: str) -> Dict[str, Any]:
        """مرحلهٔ ۱: نمایش لیست watched ها به‌صورت inline keyboard."""
        tg = self._telegram()
        try:
            from .oversight_service import get_oversight_service
            _oversight = get_oversight_service()
        except Exception as e:
            await tg.send(f"❌ خطا در بارگذاری سرویس oversight: {e}", silent=True)
            return {"ok": True, "handled": "new_task_fail"}

        watched_list = list(_oversight.watched or [])
        if not watched_list:
            await tg.send(
                "⚠️ هیچ پروژهٔ تحت نظارتی پیدا نشد.\n"
                "ابتدا در پنل وب /oversight یک پروژه اضافه کنید.",
                silent=True,
            )
            return {"ok": True, "handled": "no_watched"}

        kb = self._render_watched_picker(watched_list)
        await tg.send(
            "🆕 *تسک جدید*\n\nپروژه را انتخاب کنید:",
            silent=True,
            reply_markup=kb,
        )
        return {"ok": True, "handled": "new_task_picker", "count": len(watched_list)}

    async def _start_reminder_flow(self, chat_id_str: str) -> Dict[str, Any]:
        """🔔 شروع compose با force_type=reminder.

        بر خلاف /new_task که نیاز به انتخاب پروژه دارد، reminder ها مستقل
        از repo هستند. compose را با watched_id=None شروع می‌کنیم و کاربر
        می‌تواند مستقیماً متن/صوت/فایل بفرستد. در submit:
        - idea_to_prompt با type_=reminder → مسیر _idea_to_prompt_reminder
        - AI، title + checklist + reminder_at + reminder_repeat_rule
          را از متن استخراج می‌کند
        - create_task با type=reminder ساخته می‌شود
        """
        tg = self._telegram()
        compose_svc = get_compose_service()
        # اگر compose قبلی فعال است، اول cancel کن (replace) تا state تمیز شود
        await compose_svc.start(
            chat_id_str,
            mode="task",
            watched_id=None,
            replace=True,
            force_type="reminder",
        )
        msg = (
            "🔔 *یادآوری جدید*\n\n"
            "متن یادآوری را بفرستید (یا پیام صوتی/فایل). می‌توانید زمان "
            "را در متن مشخص کنید — مثلاً:\n"
            "  • «فردا ساعت ۹ صبح یادم بنداز قرص بخورم»\n"
            "  • «هر روز ساعت ۸ شب: مرور آلمانی»\n"
            "  • «هر جمعه: تماس با مامان»\n\n"
            "اگر زمان نگفتید، پیش‌فرض یک ساعت بعد ست می‌شود (با snooze "
            "قابل تغییر).\n\n"
            "وقتی تمام شد، روی *✅ ثبت کن* (دکمهٔ پایین کارت compose) "
            "بزنید. /cancel برای لغو."
        )
        await tg.send(msg, silent=True)
        return {"ok": True, "handled": "reminder_compose_started"}

    def _render_watched_picker(
        self, watched_list: List[Any], max_items: int = 12,
    ) -> Dict[str, Any]:
        """ساخت inline_keyboard برای انتخاب پروژه (max 12، 2 ستون)."""
        items = watched_list[:max_items]
        rows: List[List[Dict[str, str]]] = []
        for i in range(0, len(items), 2):
            row: List[Dict[str, str]] = []
            for w in items[i:i + 2]:
                # repo_full_name ممکن است طولانی باشد → برای دکمه truncate
                label = (w.repo_full_name or w.id)[:30]
                row.append({"text": f"📁 {label}", "callback_data": f"pick:{w.id}"})
            rows.append(row)
        rows.append([{"text": "❌ لغو", "callback_data": "flow:cancel"}])
        return {"inline_keyboard": rows}

    async def _receive_idea_text(
        self, chat_id_str: str, state: Dict[str, Any], text: str,
    ) -> Dict[str, Any]:
        """مرحلهٔ ۳: کاربر متن idea را فرستاده — تأیید بخواه."""
        tg = self._telegram()
        if len(text) < 5:
            await tg.send(
                "⚠️ متن خیلی کوتاه است. لطفاً ایده را با جزئیات بیشتری بنویسید "
                "(یا /cancel برای لغو).",
                silent=True,
            )
            return {"ok": True, "handled": "idea_too_short"}

        watched_id = state.get("watched_id")
        # ساخت draft token
        token = _short_token()
        _idea_drafts[token] = {
            "watched_id": watched_id,
            "idea": text,
            "expires_at": _now_epoch() + _STATE_TTL_SECONDS,
        }
        # حذف state — کاربر در مرحلهٔ تأیید است نه awaiting_idea
        _chat_state.pop(chat_id_str, None)

        # نام پروژه برای نمایش
        repo_name = state.get("repo_name") or watched_id

        preview = text[:300] + ("..." if len(text) > 300 else "")
        kb = {
            "inline_keyboard": [
                [
                    {"text": "✅ ثبت کن", "callback_data": f"confirm:{token}"},
                    {"text": "✏️ ویرایش", "callback_data": f"edit:{token}"},
                ],
                [{"text": "❌ لغو", "callback_data": "flow:cancel"}],
            ]
        }
        await tg.send(
            f"📝 *تأیید ثبت تسک*\n\n"
            f"📁 پروژه: `{repo_name}`\n\n"
            f"💭 ایده:\n{preview}\n\n"
            f"تأیید می‌کنید؟",
            silent=True,
            reply_markup=kb,
        )
        return {"ok": True, "handled": "idea_confirm_pending", "token": token}

    async def _handle_callback_query(self, cq: Dict[str, Any]) -> Dict[str, Any]:
        """پردازش inline button clicks (callback_data)."""
        data = (cq.get("data") or "").strip()
        cq_id = cq.get("id") or ""
        msg = cq.get("message") or {}
        chat = msg.get("chat") or {}
        chat_id = chat.get("id")
        if not chat_id:
            await self._answer_callback(cq_id)
            return {"ok": True, "ignored": True}

        configured_id = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
        if configured_id and str(chat_id) != configured_id:
            await self._answer_callback(cq_id)
            return {"ok": True, "ignored": True}

        chat_id_str = str(chat_id)
        tg = self._telegram()
        # 🆕 toast فوری برای callback های زمان‌بر — کاربر بلافاصله می‌بیند چیزی
        # در حال پردازش است (حتی اگر پاسخ متنی چند ثانیه طول بکشد)
        _heavy_prefixes = (
            "codex:build", "codex:view", "codex:refresh",
            "creator_confirm", "creator_regenerate_prompt",
            "task_dup:merge", "task_dup:force", "menu:index",
            "index:refresh", "confirm:", "task_regen:",
        )
        if any(data.startswith(p) for p in _heavy_prefixes):
            await self._answer_callback(cq_id, "⏳ در حال پردازش...")
        else:
            await self._answer_callback(cq_id)  # دکمه را از loading state خارج کن

        # flow:cancel
        if data == "flow:cancel":
            _chat_state.pop(chat_id_str, None)
            await tg.send("❌ flow لغو شد.", silent=True)
            return {"ok": True, "handled": "flow_cancel"}

        # 🔔 reminder:* callbacks (tick/done/snooze)
        if data.startswith("reminder:"):
            return await self._handle_reminder_callback(chat_id_str, data, msg)

        # 🆕 (Phase 3) — backfill:run_force / backfill:run
        if data.startswith("backfill:"):
            return await self._handle_backfill_callback(chat_id_str, data, tg)

        # pick:<watched_id>
        if data.startswith("pick:"):
            watched_id = data.split(":", 1)[1]
            try:
                from .oversight_service import get_oversight_service
                _oversight = get_oversight_service()
                w = next((x for x in _oversight.watched if x.id == watched_id), None)
            except Exception:
                w = None
            if not w:
                await tg.send("⚠️ پروژه یافت نشد. /new\\_task بزنید.", silent=True)
                return {"ok": True, "handled": "pick_not_found"}
            _chat_state[chat_id_str] = {
                "phase": "awaiting_idea",
                "watched_id": watched_id,
                "repo_name": w.repo_full_name,
                "expires_at": _now_epoch() + _STATE_TTL_SECONDS,
            }
            await tg.send(
                f"✅ پروژه: `{w.repo_full_name}`\n\n"
                f"✏️ حالا متن ایده/مشکل را بنویسید (یا /cancel برای لغو):",
                silent=True,
            )
            return {"ok": True, "handled": "pick_ok", "watched_id": watched_id}

        # edit:<token> — کاربر می‌خواهد متن را عوض کند
        if data.startswith("edit:"):
            token = data.split(":", 1)[1]
            draft = _idea_drafts.get(token)
            if not draft:
                await tg.send("⚠️ draft منقضی شده. /new\\_task بزنید.", silent=True)
                return {"ok": True, "handled": "edit_expired"}
            # برگشت به phase awaiting_idea
            _chat_state[chat_id_str] = {
                "phase": "awaiting_idea",
                "watched_id": draft["watched_id"],
                "expires_at": _now_epoch() + _STATE_TTL_SECONDS,
            }
            del _idea_drafts[token]
            await tg.send("✏️ متن جدید را بنویسید:", silent=True)
            return {"ok": True, "handled": "edit_back"}

        # confirm:<token> — ثبت نهایی
        if data.startswith("confirm:"):
            token = data.split(":", 1)[1]
            # 🆕 (callback dedup fix) — اگر token در حال پردازش است (دومین کلیک
            # یا retry تلگرام)، silent skip کن — نه پیام «منقضی شده». اولین
            # callback همچنان کار اصلی را انجام می‌دهد.
            if token in _processing_tokens:
                logger.debug(f"confirm: duplicate callback for token={token[:8]}.. — skipping")
                return {"ok": True, "handled": "confirm_duplicate"}
            draft = _idea_drafts.get(token)
            if not draft:
                # token نه در drafts است نه در processing — واقعاً منقضی است
                await tg.send("⚠️ draft منقضی شده. /new\\_task بزنید.", silent=True)
                return {"ok": True, "handled": "confirm_expired"}
            # atomic: حذف draft + علامت‌گذاری به‌عنوان in-progress
            del _idea_drafts[token]
            _processing_tokens[token] = _now_epoch()
            await tg.send("⏳ در حال ساخت پرامپت با AI (تا چند دقیقه، به‌ویژه با فایل پیوست)...", silent=True)
            try:
                return await self._call_idea_to_prompt(
                    chat_id_str, draft["watched_id"], draft["idea"],
                )
            finally:
                # پس از اتمام (موفقیت یا شکست)، token را پاک کن
                _processing_tokens.pop(token, None)

        # 🆕 menu shortcuts
        if data == "menu:new_project":
            return await self._start_new_project_flow(chat_id_str)
        if data == "menu:new_task":
            return await self._start_new_task_flow(chat_id_str)
        if data == "menu:reminder":
            return await self._start_reminder_flow(chat_id_str)
        if data == "menu:codex":
            return await self._start_codex_flow(chat_id_str)
        if data == "menu:usage":
            return await self._show_ai_usage(chat_id_str)
        if data == "usage:refresh_balance":
            return await self._show_ai_usage(chat_id_str, refresh=True)
        if data == "menu:index":
            return await self._send_or_edit_index_message(chat_id_str)
        if data == "index:refresh":
            return await self._send_or_edit_index_message(chat_id_str, force_refresh=True)

        # 🆕 (Codex) callbacks
        if data.startswith("codex:"):
            return await self._handle_codex_callback(chat_id_str, data)

        # 🆕 (Creator v2) name selection callbacks
        if data == "creator_use_suggested_name":
            state = _chat_state.get(chat_id_str)
            if not state or state.get("phase") != "creator_awaiting_name_or_skip":
                await tg.send("⚠️ flow منقضی شده.", silent=True)
                return {"ok": True, "handled": "name_pick_expired"}
            cdata = state.get("creator_data", {})
            cdata["name"] = cdata.get("suggested_name", "my-project")
            # transition به type picker
            state["phase"] = "creator_awaiting_type"
            state["expires_at"] = _now_epoch() + _STATE_TTL_SECONDS
            kb = self._render_project_type_picker()
            await tg.send(
                f"✅ نام: `{cdata['name']}`\n\n"
                f"📁 *مرحلهٔ ۴/۵: نوع پروژه*",
                silent=True,
                reply_markup=kb,
            )
            return {"ok": True, "handled": "use_suggested_name"}

        if data == "creator_custom_name":
            state = _chat_state.get(chat_id_str)
            if not state or state.get("phase") != "creator_awaiting_name_or_skip":
                await tg.send("⚠️ flow منقضی شده.", silent=True)
                return {"ok": True, "handled": "name_pick_expired"}
            state["phase"] = "creator_awaiting_custom_name"
            state["expires_at"] = _now_epoch() + _STATE_TTL_SECONDS
            await tg.send(
                "✏️ *نام دلخواه پروژه را وارد کنید*\n"
                "(انگلیسی، 3+ کاراکتر، فقط a-z A-Z 0-9 - _)",
                silent=True,
            )
            return {"ok": True, "handled": "ask_custom_name"}

        # 🆕 (Creator v2) model selection callbacks
        if data.startswith("creator_model:"):
            mid = data.split(":", 1)[1]
            state = _chat_state.get(chat_id_str)
            if not state or state.get("phase") != "creator_awaiting_model_choice":
                await tg.send("⚠️ flow منقضی شده. /new\\_project بزنید.", silent=True)
                return {"ok": True, "handled": "model_pick_expired"}
            cdata = state.setdefault("creator_data", {})
            sel: List[str] = list(cdata.get("model_ids", []) or [])
            if mid in sel:
                sel.remove(mid)
            else:
                sel.append(mid)
            cdata["model_ids"] = sel
            state["expires_at"] = _now_epoch() + _STATE_TTL_SECONDS
            # نمایش مجدد keyboard با وضعیت جدید
            return await self._show_creator_model_picker(chat_id_str)

        if data == "creator_models_confirm":
            state = _chat_state.get(chat_id_str)
            if not state or state.get("phase") != "creator_awaiting_model_choice":
                await tg.send("⚠️ flow منقضی شده.", silent=True)
                return {"ok": True, "handled": "confirm_expired"}
            cdata = state.get("creator_data", {})
            sel: List[str] = list(cdata.get("model_ids", []) or [])
            if not sel:
                await tg.send(
                    "⚠️ حداقل یک مدل انتخاب کنید — بدون مدل پیش‌روی ممکن نیست.",
                    silent=True,
                )
                return {"ok": True, "handled": "no_model_selected"}
            # transition به phase بعدی: awaiting_idea
            state["phase"] = "creator_awaiting_idea"
            state["expires_at"] = _now_epoch() + _STATE_TTL_SECONDS
            await tg.send(
                f"✅ *{len(sel)} مدل انتخاب شد*\n"
                + "\n".join(f"  {i+1}. `{m}`" for i, m in enumerate(sel[:5]))
                + (f"\n  ... و {len(sel) - 5} مدل دیگر" if len(sel) > 5 else "")
                + "\n\n💡 *مرحلهٔ ۲/۵: ایده پروژه را وارد کن*\n"
                + "(به زبان طبیعی — هرچه دقیق‌تر، بهتر)\n\n"
                + "مثال:\n"
                + "_«ربات تلگرام برای مدیریت لیست خرید با SQLite، شامل دستورات\n"
                + "/add /list /remove و گزارش هفتگی»_",
                silent=True,
            )
            return {"ok": True, "handled": "models_confirmed"}

        # creator_regenerate_prompt: بازتولید پرامپت با مدل بعدی
        if data.startswith("creator_regenerate_prompt:"):
            token = data.split(":", 1)[1]
            draft = _idea_drafts.get(token)
            if not draft:
                await tg.send("⚠️ draft منقضی شده.", silent=True)
                return {"ok": True, "handled": "regen_expired"}
            # rotate model_ids
            mids = list(draft.get("creator_data", {}).get("model_ids", []) or [])
            if len(mids) > 1:
                draft["creator_data"]["model_ids"] = mids[1:] + [mids[0]]
            await tg.send(
                f"🔄 *بازتولید با مدل بعدی*: `{draft['creator_data']['model_ids'][0]}`\n"
                f"⏳ در حال تولید پرامپت جدید...",
                silent=True,
            )
            return await self._generate_creator_preview(chat_id_str, token)

        # creator_edit_idea: بازگشت به phase awaiting_idea برای ویرایش
        if data.startswith("creator_edit_idea:"):
            token = data.split(":", 1)[1]
            draft = _idea_drafts.get(token)
            if not draft:
                await tg.send("⚠️ draft منقضی شده.", silent=True)
                return {"ok": True, "handled": "edit_expired"}
            # state را به awaiting_idea برگردان با حفظ model_ids و name (اگر بود)
            _chat_state[chat_id_str] = {
                "phase": "creator_awaiting_idea",
                "creator_data": {
                    "model_ids": draft.get("creator_data", {}).get("model_ids", []),
                },
                "expires_at": _now_epoch() + _STATE_TTL_SECONDS,
            }
            del _idea_drafts[token]
            await tg.send(
                "✏️ *ویرایش ایده*\n\nمتن جدید ایده را بنویس:",
                silent=True,
            )
            return {"ok": True, "handled": "edit_idea_back"}

        # creator_confirm_final:<token> — تأیید نهایی و execute
        if data.startswith("creator_confirm_final:"):
            token = data.split(":", 1)[1]
            draft = _idea_drafts.get(token)
            if not draft:
                await tg.send("⚠️ draft منقضی شده.", silent=True)
                return {"ok": True, "handled": "final_expired"}
            del _idea_drafts[token]
            return await self._execute_creator_v2(chat_id_str, draft)

        # 🆕 Creator callbacks (v1 — backward compat)
        # creator_type:<value> — انتخاب نوع پروژه
        if data.startswith("creator_type:"):
            value = data.split(":", 1)[1]
            state = _chat_state.get(chat_id_str)
            if not state or state.get("phase") != "creator_awaiting_type":
                await tg.send("⚠️ flow منقضی شده. /new\\_project بزنید.", silent=True)
                return {"ok": True, "handled": "creator_type_expired"}
            data_ = state.get("creator_data", {})
            data_["project_type"] = value
            state["creator_data"] = data_
            # 🆕 v2 flow: اگر idea موجود است، مستقیم به preview generation
            if data_.get("idea"):
                # ساخت token برای draft
                token = _short_token()
                _idea_drafts[token] = {
                    "creator_data": dict(data_),
                    "expires_at": _now_epoch() + _STATE_TTL_SECONDS,
                }
                _chat_state.pop(chat_id_str, None)
                await tg.send(
                    f"✅ نوع: `{value}`\n\n"
                    f"⏳ *مرحلهٔ ۵/۵: تولید پرامپت قوی با AI*\n"
                    f"این فرآیند ۱۵-۳۰ ثانیه طول می‌کشد...",
                    silent=True,
                )
                return await self._generate_creator_preview(chat_id_str, token)
            # v1 legacy fallback
            state["phase"] = "creator_awaiting_tech"
            state["expires_at"] = _now_epoch() + _STATE_TTL_SECONDS
            await tg.send(
                f"✅ نوع: `{value}`\n\n"
                f"🔧 *تکنولوژی‌های دلخواه را وارد کن*\n"
                f"(با کاما جدا کن، مثلاً: `pydantic, sqlite, jwt`)\n"
                f"یا /skip برای پیش‌فرض",
                silent=True,
            )
            return {"ok": True, "handled": "creator_type_ok"}

        # 🆕 (Smart Task Lifecycle) task_dup:* — پاسخ کاربر به duplicate detection
        if data.startswith("task_dup:"):
            return await self._handle_task_dup_callback(chat_id_str, data)

        # 🆕 (Task Regen) task_regen:<task_id> — بازتولید پرامپت تسک
        if data.startswith("task_regen:"):
            return await self._handle_task_regen_callback(chat_id_str, data)

        # 🆕 (Compose Stage 4) — picker پروژه هنگام submit بدون watched_id
        if data.startswith("compose_pick:"):
            watched_id = data.split(":", 1)[1]
            from .oversight_telegram_compose import get_compose_service
            cs = get_compose_service()
            buf = cs.get(chat_id_str)
            if buf is None:
                await tg.send("⚠️ compose منقضی شد.", silent=True)
                return {"ok": True, "handled": "compose_pick_expired"}
            await cs.set_watched(chat_id_str, watched_id)
            # ادامهٔ submit
            return await self._compose_submit(chat_id_str, mode=buf.mode)

        if data == "compose_cancel_picker":
            await tg.send("⏸ انتخاب پروژه لغو شد — می‌توانی همچنان آیتم بفرستی یا با ❌ لغو همه ببندی.", silent=True)
            return {"ok": True, "handled": "compose_picker_cancelled"}

        # 🛡 (audit fix) — Telegram معادل modal toggle:
        # compose_temp_activate:<model_id> → temp-activate + retry submit
        if data.startswith("compose_temp_activate:"):
            model_id = data.split(":", 1)[1].strip()
            if not model_id:
                await tg.send("⚠️ model_id خالی است.", silent=True)
                return {"ok": True, "handled": "compose_temp_activate_bad"}
            from .oversight_model_temp_activate import temp_activate_model
            try:
                res = await temp_activate_model(
                    model_id, trigger=f"telegram-compose-{chat_id_str}",
                )
                await tg.send(
                    f"✅ مدل `{res.get('name', model_id)}` موقتاً فعال شد. "
                    f"اکنون submit را دوباره اجرا می‌کنم...\n"
                    f"_(پس از اتمام، خودکار غیرفعال خواهد شد.)_",
                    silent=True,
                )
            except Exception as e:
                await tg.send(f"❌ فعال‌سازی موقت ناموفق: {str(e)[:200]}", silent=False)
                return {"ok": True, "handled": "compose_temp_activate_failed"}
            # 🆕 (audit fix) — track activated model در buffer تا پس از اتمام
            # extraction خودکار revert شود
            from .oversight_telegram_compose import get_compose_service
            cs = get_compose_service()
            # 🛡 (audit fix CRITICAL) — اگر set_temp_activated_model به‌خاطر
            # I/O fail کند (مثلاً disk full)، نباید کل callback crash کند.
            # در بدترین حالت، revert خودکار اتفاق نمی‌افتد ولی boot recovery
            # آن را پاک می‌کند. کاربر می‌تواند ادامه دهد.
            try:
                await cs.set_temp_activated_model(chat_id_str, model_id)
            except Exception as _set_e:
                logger.warning(
                    f"set_temp_activated_model failed (will skip auto-revert "
                    f"for this submission): {_set_e}"
                )
                # fallback: try direct setattr روی buf — حداقل اگر I/O فقط در
                # _save() مشکل دارد، در حافظه track می‌ماند
                try:
                    _buf_inner = cs.get(chat_id_str)
                    if _buf_inner is not None:
                        _buf_inner.temp_activated_model_id = model_id
                except Exception:
                    pass
            buf = cs.get(chat_id_str)
            if buf is None:
                await tg.send("⚠️ compose منقضی شد. دوباره فایل بفرست.", silent=True)
                return {"ok": True, "handled": "compose_expired_after_activate"}
            return await self._compose_submit(chat_id_str, mode=buf.mode)

        # creator_confirm:push:<token> یا creator_confirm:local:<token>
        if data.startswith("creator_confirm:"):
            parts = data.split(":", 2)
            if len(parts) < 3:
                await tg.send("⚠️ callback نامعتبر.", silent=True)
                return {"ok": True, "handled": "creator_confirm_bad"}
            mode = parts[1]  # 'push' یا 'local'
            token = parts[2]
            draft = _idea_drafts.get(token)
            if not draft or "creator_data" not in draft:
                await tg.send("⚠️ draft منقضی شده. /new\\_project بزنید.", silent=True)
                return {"ok": True, "handled": "creator_draft_expired"}
            del _idea_drafts[token]
            push = (mode == "push")
            return await self._execute_creator_flow(chat_id_str, draft, push_to_github=push)

        # ناشناخته
        await tg.send(f"❓ callback ناشناخته: `{data[:50]}`", silent=True)
        return {"ok": True, "handled": "unknown_callback"}

    async def _call_idea_to_prompt(
        self, chat_id_str: str, watched_id: str, idea: str,
    ) -> Dict[str, Any]:
        """فراخوانی idea_to_prompt و گزارش نتیجه به کاربر.

        🆕 (Smart Task Lifecycle): پیش از ساخت تسک، dedup check انجام می‌شود.
        اگر مشابه پیدا شد، با inline keyboard از کاربر می‌پرسد:
          [🔀 ادغام با ۱] [➕ جداگانه] [❌ انصراف]
        """
        tg = self._telegram()
        prefs = _read_prefs()
        base = (prefs.get("app_base_url", "") or "").rstrip("/")
        try:
            from .oversight_service import get_oversight_service
            _oversight = get_oversight_service()

            # ───── (1) Dedup pre-check روی متن ایدهٔ خام (سریع، بدون AI) ─────
            quick_matches = _oversight.find_similar_active_tasks(
                project_id=watched_id,
                candidate_title=idea[:120],
                candidate_raw_idea=idea,
            )
            if quick_matches:
                # متن ایده را در draft نگه دار تا پس از انتخاب کاربر استفاده شود
                token = _short_token()
                _idea_drafts[token] = {
                    "watched_id": watched_id,
                    "idea": idea,
                    "matches": [m.to_dict() for m in quick_matches[:3]],
                    "source": "telegram_bot",
                    "expires_at": _now_epoch() + _STATE_TTL_SECONDS,
                }
                rows: List[List[Dict[str, str]]] = []
                # هر match یک ردیف
                for i, m in enumerate(quick_matches[:3]):
                    rows.append([{
                        "text": f"🔀 ادغام با «{m.title[:30]}» ({int(m.score * 100)}٪)",
                        "callback_data": f"task_dup:merge:{token}:{m.task_id}",
                    }])
                rows.append([
                    {"text": "➕ ایجاد جداگانه", "callback_data": f"task_dup:force:{token}"},
                    {"text": "❌ انصراف", "callback_data": "flow:cancel"},
                ])
                lines = [
                    "⚠️ *تسک‌های مشابه پیدا شد*",
                    "",
                    f"📁 پروژه: `{next((w.repo_full_name for w in _oversight.watched if w.id == watched_id), '')}`",
                    f"💭 ایدهٔ شما: _{idea[:120]}{'...' if len(idea) > 120 else ''}_",
                    "",
                    "تسک‌های مشابهٔ موجود:",
                ]
                for i, m in enumerate(quick_matches[:3], 1):
                    lines.append(f"  {i}. «{m.title[:60]}» — {int(m.score * 100)}٪")
                lines.append("")
                lines.append("کدام را می‌خواهی؟")
                await tg.send(
                    "\n".join(lines),
                    silent=True,
                    reply_markup={"inline_keyboard": rows},
                )
                return {
                    "ok": True,
                    "handled": "duplicate_detected",
                    "matches_count": len(quick_matches),
                    "token": token,
                }

            # ───── (2) مشابه ندارد → ادامهٔ مسیر طبیعی (idea→prompt) ─────
            # 🛡 (audit fix CRITICAL #1) — همهٔ مسیرهای Telegram باید
            # multi_pass_mode='always' را پاس بدهند تا چک‌لیست تضمین شود.
            # این مسیر legacy (/new_task متنی بدون compose) از قبل گم شده بود!
            data = await _oversight.idea_to_prompt(
                idea=idea,
                watched_id=watched_id,
                type_="other",
                priority="medium",
                multi_pass_mode="always",
            )
            # ایجاد تسک از طریق create_task (با force_create=True چون قبلاً
            # dedup check کردیم و قطعاً مشابه نیست)
            result = await _oversight.create_task({
                "watched_id": watched_id,
                "title": data.get("title") or idea[:80],
                "prompt": data.get("prompt") or "",
                "raw_idea": idea,
                "type": data.get("type") or "other",
                "priority": data.get("priority") or "medium",
                "source": "telegram_bot",
                "target_files": data.get("target_files") or [],
                "acceptance_criteria": data.get("acceptance_criteria") or [],
                "force_create": True,
            })
            new_task = result.get("task") or {}

            # 🆕 پیام را با چک‌لیست + PDF (متن کامل پرامپت + جزئیات همهٔ
            # مراحل) + دکمهٔ «بازتولید پرامپت» (از همین تلگرام) بفرست.
            await self._send_task_created_message(new_task, base=base)
            return {"ok": True, "handled": "task_created", "task_id": new_task.get("id")}
        except Exception as e:
            logger.exception(f"telegram bot idea_to_prompt failed: {e}")
            await tg.send(
                f"❌ خطا در ساخت تسک:\n`{str(e)[:300]}`\n\nبعداً دوباره تلاش کنید یا از پنل وب استفاده کنید.",
                silent=False,
            )
            return {"ok": True, "handled": "task_create_failed", "error": str(e)}

    # -----------------------------------------------------------------------
    # 🆕 (Task Created Telegram Message) — پیام چک‌لیستی + PDF + دکمهٔ بازتولید
    # -----------------------------------------------------------------------

    async def _send_task_created_message(
        self, task_dict: Dict[str, Any], *, base: str = "",
    ) -> Dict[str, Any]:
        """ارسال پیام «تسک ساخته شد» با:
          • متن چک‌لیستی (عناوین کوتاه مراحل با ⬜)
          • PDF پیوست (متن کامل پرامپت + جزئیات همهٔ مراحل + AC ها)
          • دکمهٔ بازتولید پرامپت (از همین تلگرام)
        """
        tg = self._telegram()
        if not tg.is_configured():
            return {"ok": False, "error": "telegram not configured"}

        # ساخت یک namespace ساده از dict تا با getattr کار کند (builderها از
        # getattr استفاده می‌کنند تا روی هر شیء dataclass/namespace کار کنند).
        class _TaskNs:
            pass
        ns = _TaskNs()
        for k, v in (task_dict or {}).items():
            setattr(ns, k, v)

        # متن چک‌لیستی با header اختصاصی «تسک ساخته شد»
        try:
            from .oversight_verify_pdf import (
                build_verify_checklist_message,
                build_verify_report_pdf,
            )
            msg_text = build_verify_checklist_message(
                ns, None,
                header_override="✅ *تسک ساخته شد*",
                char_budget=850,
            )
        except Exception as _e:
            logger.warning(f"build_task_created_message failed: {_e}")
            msg_text = (
                f"✅ *تسک ساخته شد*\n\n"
                f"📌 _{(task_dict.get('title') or '')[:120]}_\n"
                f"📁 `{task_dict.get('project_full_name') or ''}`\n"
                f"🔖 {task_dict.get('priority') or 'medium'} • {task_dict.get('type') or 'other'}"
            )

        # تولید PDF (best-effort)
        pdf_bytes: Optional[bytes] = None
        pdf_filename: Optional[str] = None
        try:
            pdf_bytes, pdf_filename = await build_verify_report_pdf(
                ns, None, filename_prefix="task",
            )
        except Exception as _e:
            logger.warning(f"task_created pdf failed: {_e}")
            pdf_bytes = None

        # دکمه‌ها: بازتولید + لینک‌های پنل
        rows: List[List[Dict[str, str]]] = []
        task_id = task_dict.get("id")
        if task_id:
            rows.append([
                {"text": "🔄 بازتولید پرامپت", "callback_data": f"task_regen:{task_id}"},
            ])
        if base:
            rows.append([
                {"text": "📋 دیدن تسک‌ها", "url": f"{base}/oversight?tab=tasks"},
            ])
            rows.append([
                {"text": "👁 تحت نظارت", "url": f"{base}/oversight?tab=watched"},
            ])
        reply_markup = {"inline_keyboard": rows} if rows else None

        # اگر PDF داشتیم — به‌عنوان document با caption=msg_text. در غیر این
        # صورت پیام متنی ساده.
        if pdf_bytes and pdf_filename:
            res = await tg.send_document(
                pdf_bytes, pdf_filename,
                caption=msg_text,
                silent=False,
                reply_markup=reply_markup,
            )
            if not res.get("ok"):
                logger.warning(f"task_created send_document failed: {res.get('error')}")
                # fallback به متن ساده
                await tg.send(msg_text, silent=False, reply_markup=reply_markup)
            return res
        else:
            return await tg.send(msg_text, silent=False, reply_markup=reply_markup)

    async def _handle_task_regen_callback(
        self, chat_id_str: str, data: str,
    ) -> Dict[str, Any]:
        """callback پاسخ به دکمهٔ «بازتولید پرامپت» در پیام تسک ساخته‌شده.

        فرمت: `task_regen:<task_id>` — کاربر را به phase
        `awaiting_regen_idea` می‌برد تا متن جدید ایده را وارد کند.
        پس از دریافت متن، `regenerate_prompt_for_task` صدا زده می‌شود و
        پیام تسک با PDF جدید دوباره فرستاده می‌شود.
        """
        tg = self._telegram()
        parts = data.split(":", 1)
        if len(parts) != 2 or not parts[1]:
            await tg.send("⚠️ callback نامعتبر.", silent=True)
            return {"ok": True, "handled": "task_regen_bad"}
        task_id = parts[1].strip()
        # وضعیت را روی phase جدید تنظیم کن
        _chat_state[chat_id_str] = {
            "phase": "awaiting_regen_idea",
            "task_id": task_id,
            "expires_at": _now_epoch() + _STATE_TTL_SECONDS,
        }
        # عنوان فعلی تسک را نشان بده تا کاربر بداند کدام تسک را بازتولید می‌کند
        try:
            from .oversight_service import get_oversight_service
            _ov = get_oversight_service()
            cur = next((t for t in _ov.tasks if t.id == task_id), None)
            cur_title = (cur.title if cur else "")[:80] or "?"
            cur_raw = (cur.raw_idea if cur else "") or ""
        except Exception:
            cur_title = "?"
            cur_raw = ""
        snippet = (cur_raw[:200] + "…") if len(cur_raw) > 200 else cur_raw
        await tg.send(
            f"🔄 *بازتولید پرامپت*\n\n"
            f"📌 _{_md_escape_tg(cur_title)}_\n\n"
            + (f"💭 ایدهٔ خام فعلی:\n_{_md_escape_tg(snippet)}_\n\n" if cur_raw else "")
            + "✏️ متن ایدهٔ *جدید* را بنویس (یا /skip برای استفاده از همان ایدهٔ خام فعلی، یا /cancel برای لغو):",
            silent=True,
        )
        return {"ok": True, "handled": "task_regen_start", "task_id": task_id}

    async def _execute_task_regen(
        self, chat_id_str: str, task_id: str, new_raw_idea: Optional[str],
    ) -> Dict[str, Any]:
        """اجرای regenerate برای تسک با raw_idea جدید (یا همان قبلی اگر None).

        پس از موفقیت، پیام تسک با PDF جدید دوباره فرستاده می‌شود.
        """
        tg = self._telegram()
        prefs = _read_prefs()
        base = (prefs.get("app_base_url", "") or "").rstrip("/")
        try:
            from .oversight_service import get_oversight_service
            _ov = get_oversight_service()
            await tg.send("⏳ در حال بازتولید پرامپت با AI...", silent=True)
            updated = await _ov.regenerate_prompt_for_task(
                task_id,
                new_raw_idea=new_raw_idea,
            )
            if not updated:
                await tg.send("⚠️ تسک یافت نشد.", silent=True)
                return {"ok": True, "handled": "task_regen_not_found"}
            await self._send_task_created_message(updated, base=base)
            return {"ok": True, "handled": "task_regen_done", "task_id": task_id}
        except Exception as e:
            logger.exception(f"task_regen failed: {e}")
            await tg.send(
                f"❌ خطا در بازتولید: `{str(e)[:300]}`",
                silent=False,
            )
            return {"ok": True, "handled": "task_regen_failed", "error": str(e)}

    # -----------------------------------------------------------------------
    # 🆕 (Smart Task Lifecycle) task_dup:* callbacks
    # -----------------------------------------------------------------------

    async def _handle_task_dup_callback(
        self, chat_id_str: str, data: str,
    ) -> Dict[str, Any]:
        """پردازش انتخاب کاربر در مواجهه با duplicate detection:
          task_dup:merge:<token>:<task_id>  → ادغام سریع
          task_dup:force:<token>            → ایجاد جداگانه (force_create)
        """
        tg = self._telegram()
        parts = data.split(":")
        # parts[0]='task_dup', parts[1]=action
        if len(parts) < 3:
            await tg.send("⚠️ callback نامعتبر.", silent=True)
            return {"ok": True, "handled": "task_dup_bad"}
        action = parts[1]
        token = parts[2]
        # 🆕 (callback dedup) — اگر token در حال پردازش است، silent skip
        if token in _processing_tokens:
            logger.debug(f"task_dup: duplicate callback for token={token[:8]}.. — skipping")
            return {"ok": True, "handled": "task_dup_duplicate"}
        draft = _idea_drafts.get(token)
        if not draft:
            await tg.send("⚠️ draft منقضی شده. /new\\_task بزنید.", silent=True)
            return {"ok": True, "handled": "task_dup_expired"}

        idea = draft.get("idea", "")
        watched_id = draft.get("watched_id")
        source = draft.get("source", "telegram_bot")
        # یک‌بار مصرف + علامت‌گذاری processing
        del _idea_drafts[token]
        _processing_tokens[token] = _now_epoch()

        try:
            return await self._handle_task_dup_callback_inner(
                chat_id_str, action, parts, idea, watched_id, source, tg,
            )
        finally:
            _processing_tokens.pop(token, None)

    async def _handle_task_dup_callback_inner(
        self, chat_id_str: str, action: str, parts: List[str],
        idea: str, watched_id: Optional[str], source: str, tg: Any,
    ) -> Dict[str, Any]:
        """بدنهٔ اصلی task_dup callback — جدا شده تا finally token cleanup کار کند."""
        from .oversight_service import get_oversight_service
        _oversight = get_oversight_service()

        if action == "merge":
            if len(parts) < 4:
                await tg.send("⚠️ task_id در callback نیست.", silent=True)
                return {"ok": True, "handled": "task_dup_no_task_id"}
            target_task_id = parts[3]
            await tg.send(
                "⏳ در حال ادغام...",
                silent=True,
            )
            try:
                from .task_merge_service import get_task_merge_service
                merge_service = get_task_merge_service()
                merged = await merge_service.apply_merge_simple(
                    existing_task_id=target_task_id,
                    candidate_title=idea[:120],
                    candidate_raw_idea=idea,
                    candidate_prompt="",
                    candidate_acceptance_criteria=None,
                    candidate_target_files=None,
                    source=source,
                )
                if not merged:
                    await tg.send("⚠️ تسک هدف یافت نشد.", silent=True)
                    return {"ok": True, "handled": "task_dup_merge_not_found"}
                prefs = _read_prefs()
                base = (prefs.get("app_base_url", "") or "").rstrip("/")
                kb = None
                if base:
                    kb = {
                        "inline_keyboard": [
                            [{
                                "text": "📋 مشاهده در پنل",
                                "url": f"{base}/oversight?tab=tasks#{merged.get('id', '')}",
                            }],
                        ],
                    }
                await tg.send(
                    f"🔀 *ادغام انجام شد*\n\n"
                    f"📌 «{(merged.get('title') or '')[:100]}»\n"
                    f"🔁 seen: {merged.get('scan_seen_count', 1)} scan, "
                    f"{merged.get('manual_seen_count', 0)} manual\n"
                    f"🛠 merge_count: {merged.get('merge_count', 1)}",
                    silent=False,
                    reply_markup=kb,
                )
                return {"ok": True, "handled": "task_dup_merged", "task_id": merged.get("id")}
            except Exception as e:
                logger.exception(f"task_dup merge failed: {e}")
                await tg.send(f"❌ خطا در ادغام: `{str(e)[:200]}`", silent=True)
                return {"ok": True, "handled": "task_dup_merge_fail"}

        if action == "force":
            # ایجاد جداگانه — مسیر کامل idea_to_prompt + create_task با force_create
            await tg.send("⏳ ایجاد تسک جداگانه — در حال تولید پرامپت...", silent=True)
            try:
                # 🛡 (audit fix CRITICAL #1) — multi_pass_mode='always' برای checklist
                data_p = await _oversight.idea_to_prompt(
                    idea=idea,
                    watched_id=watched_id,
                    type_="other",
                    priority="medium",
                    multi_pass_mode="always",
                )
                result = await _oversight.create_task({
                    "watched_id": watched_id,
                    "title": data_p.get("title") or idea[:80],
                    "prompt": data_p.get("prompt") or "",
                    "raw_idea": idea,
                    "type": data_p.get("type") or "other",
                    "priority": data_p.get("priority") or "medium",
                    "source": source,
                    "target_files": data_p.get("target_files") or [],
                    "acceptance_criteria": data_p.get("acceptance_criteria") or [],
                    "force_create": True,
                })
                new_task = result.get("task") or {}
                prefs = _read_prefs()
                base = (prefs.get("app_base_url", "") or "").rstrip("/")
                kb = None
                if base:
                    kb = {"inline_keyboard": [
                        [{"text": "📋 دیدن تسک", "url": f"{base}/oversight?tab=tasks"}],
                    ]}
                await tg.send(
                    f"✅ *تسک جداگانه ساخته شد*\n\n"
                    f"📌 _{(new_task.get('title') or '')[:120]}_",
                    silent=False,
                    reply_markup=kb,
                )
                return {"ok": True, "handled": "task_dup_forced", "task_id": new_task.get("id")}
            except Exception as e:
                logger.exception(f"task_dup force failed: {e}")
                await tg.send(f"❌ خطا: `{str(e)[:200]}`", silent=True)
                return {"ok": True, "handled": "task_dup_force_fail"}

        await tg.send(f"⚠️ action ناشناخته: `{action}`", silent=True)
        return {"ok": True, "handled": "task_dup_unknown_action"}

    # -----------------------------------------------------------------------
    # 🆕 (Codex) /codex flow — مشاهده/ساخت شناسنامهٔ پروژه از تلگرام
    # -----------------------------------------------------------------------

    # -----------------------------------------------------------------------
    # 🆕 (Index Hub) /index — پیام pin‌شدهٔ دسته‌بندی‌شدهٔ کارها
    # -----------------------------------------------------------------------

    def _build_index_content(self) -> str:
        """ساختن متن ایندکس دسته‌بندی‌شده از تسک‌ها/ایده‌ها/پروژه‌ها."""
        try:
            from .oversight_service import get_oversight_service
            from datetime import datetime, timezone
            svc = get_oversight_service()
        except Exception as e:
            return f"❌ خطا در بارگذاری: {e}"

        # tasks فعال (نه done/cancelled/archived/verified-done)
        active = [
            t for t in svc.tasks
            if t.status not in ("done", "cancelled")
            and not getattr(t, "archived", False)
            and t.verification_status != "done"
        ]
        # done در ۷ روز اخیر
        try:
            now = datetime.now(timezone.utc)
            from datetime import timedelta
            cutoff = now - timedelta(days=7)
            recent_done = []
            for t in svc.tasks:
                if t.status == "done" or t.verification_status == "done":
                    try:
                        u = datetime.fromisoformat((t.updated_at or t.created_at).replace("Z", "+00:00"))
                        if u.tzinfo is None:
                            u = u.replace(tzinfo=timezone.utc)
                        if u >= cutoff:
                            recent_done.append(t)
                    except Exception:
                        pass
        except Exception:
            recent_done = []

        # گروه‌بندی فعال‌ها
        ideas: List[Any] = []
        by_pri: Dict[str, List[Any]] = {"critical": [], "high": [], "medium": [], "low": []}
        for t in active:
            if (t.type or "") == "idea":
                ideas.append(t)
                continue
            p = (t.priority or "medium").lower()
            if p in by_pri:
                by_pri[p].append(t)
            else:
                by_pri["medium"].append(t)

        # sort هر گروه بر اساس scan_seen_count desc و updated_at
        for k in by_pri:
            by_pri[k].sort(
                key=lambda t: (-(getattr(t, "scan_seen_count", 1) or 1), t.updated_at or ""),
                reverse=False,
            )

        # ساخت متن
        lines: List[str] = []
        # Header
        local_time = ""
        try:
            from datetime import datetime
            from zoneinfo import ZoneInfo
            local_time = datetime.now(ZoneInfo("Asia/Tehran")).strftime("%Y-%m-%d %H:%M")
        except Exception:
            try:
                local_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            except Exception:
                pass
        lines.append("📋 *ایندکس کارها*")
        if local_time:
            lines.append(f"🕒 _به‌روز: {local_time}_")
        lines.append("")

        # Summary
        lines.append("─" * 25)
        lines.append("📊 *خلاصه*")
        lines.append(f"📁 پروژه‌ها: *{len(svc.watched)}*")
        lines.append(f"📋 تسک‌های فعال: *{len(active)}*")
        if recent_done:
            lines.append(f"✅ تکمیل‌شده (۷ روز): *{len(recent_done)}*")
        lines.append(f"📦 آرشیو: *{sum(1 for t in svc.tasks if getattr(t, 'archived', False))}*")
        lines.append("")

        # Critical
        pri_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}
        for pri in ("critical", "high", "medium", "low"):
            items = by_pri[pri]
            if not items:
                continue
            lines.append("─" * 25)
            lines.append(f"{pri_emoji[pri]} *{pri.upper()}* ({len(items)})")
            cap = 8 if pri in ("critical", "high") else 5
            for t in items[:cap]:
                title = (t.title or "").strip()[:65]
                seen = getattr(t, "scan_seen_count", 1) or 1
                seen_tag = f" 🔁{seen}x" if seen > 1 else ""
                proj = (t.project_full_name or "").split("/")[-1][:20]
                # escape underscore و asterisk برای Markdown
                title_safe = title.replace("_", "\\_").replace("*", "\\*")
                proj_safe = proj.replace("_", "\\_").replace("*", "\\*")
                lines.append(f"• {title_safe}{seen_tag}")
                if proj_safe:
                    lines.append(f"   _{proj_safe}_")
            if len(items) > cap:
                lines.append(f"   ... و {len(items) - cap} مورد دیگر")
            lines.append("")

        # Ideas
        if ideas:
            lines.append("─" * 25)
            lines.append(f"💡 *ایده‌ها* ({len(ideas)})")
            for t in ideas[:6]:
                title = (t.title or "").strip()[:70]
                title_safe = title.replace("_", "\\_").replace("*", "\\*")
                lines.append(f"• {title_safe}")
            if len(ideas) > 6:
                lines.append(f"   ... و {len(ideas) - 6} ایده")
            lines.append("")

        # پروژه‌ها
        if svc.watched:
            lines.append("─" * 25)
            lines.append("📁 *پروژه‌ها*")
            for w in svc.watched[:10]:
                # شمارش تسک‌های هر پروژه
                w_active = sum(
                    1 for t in active if t.watched_id == w.id
                )
                w_done = sum(
                    1 for t in recent_done if t.watched_id == w.id
                )
                # نام داخل backtick — `_` در code formatting OK است
                # ولی اگر backtick داخل نام بود مشکل می‌شد. escape می‌کنیم.
                name = (w.repo_full_name or w.id)[:35].replace("`", "")
                badge_bits = []
                if w_active > 0:
                    badge_bits.append(f"⚡{w_active}")
                if w_done > 0:
                    badge_bits.append(f"✅{w_done}")
                badges = " ".join(badge_bits) if badge_bits else "—"
                lines.append(f"• `{name}` {badges}")
            if len(svc.watched) > 10:
                lines.append(f"   ... و {len(svc.watched) - 10} پروژهٔ دیگر")
            lines.append("")

        # Footer
        lines.append("─" * 25)
        lines.append("🔄 _این پیام خودکار به‌روز می‌شود_")
        lines.append("برای دسترسی به دکمه‌ها: /menu")

        full = "\n".join(lines)
        # Telegram limit: 4096 char
        if len(full) > 3900:
            full = full[:3890] + "\n…\n_(محتوای کامل: /menu → پنل وب)_"
        return full

    async def _send_or_edit_index_message(
        self, chat_id_str: str, *, force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """ارسال یا edit پیام ایندکس pin‌شده.

        رفتار:
          - اگر message_id قبلی موجود است → edit با محتوای جدید
          - وگرنه → send + pin + ذخیرهٔ message_id
          - اگر edit fail شد (مثلاً پیام پاک شده) → message_id را پاک کن و
            یک پیام جدید بساز.
        """
        tg = self._telegram()
        if not tg.bot_token:
            return {"ok": False, "error": "bot token تنظیم نشده"}

        content = self._build_index_content()
        import hashlib
        content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()[:16]
        kb = {
            "inline_keyboard": [
                [{"text": "🔄 به‌روزرسانی", "callback_data": "index:refresh"}],
                [{"text": "❌ بستن", "callback_data": "flow:cancel"}],
            ],
        }

        state = _read_index_state()
        prev_msg_id = state.get("message_id")
        prev_chat_id = state.get("chat_id")

        # 1) تلاش برای edit پیام موجود
        if prev_msg_id and str(prev_chat_id) == chat_id_str:
            # اگر content یکسان است، فقط notification کوتاه بدهد (skip edit)
            if state.get("last_content_hash") == content_hash and not force_refresh:
                await tg.send(
                    "📋 ایندکس از قبل به‌روز است (در پیام pin‌شده ↑)",
                    silent=True,
                )
                return {"ok": True, "skipped": "no_change", "message_id": prev_msg_id}

            edit_url = f"https://api.telegram.org/bot{tg.bot_token}/editMessageText"
            try:
                timeout = aiohttp.ClientTimeout(total=15)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(edit_url, json={
                        "chat_id": chat_id_str,
                        "message_id": prev_msg_id,
                        "text": content,
                        "parse_mode": "Markdown",
                        "disable_web_page_preview": True,
                        "reply_markup": kb,
                    }) as r:
                        if r.status == 200:
                            _write_index_state({
                                **state,
                                "last_updated": _now_epoch(),
                                "last_content_hash": content_hash,
                            })
                            # اطلاع کوتاه به کاربر (اگر force_refresh، silent)
                            if not force_refresh:
                                await tg.send(
                                    "📋 ایندکس به‌روز شد ↑ (در پیام pin‌شده)",
                                    silent=True,
                                )
                            return {"ok": True, "edited": True, "message_id": prev_msg_id}
                        else:
                            # احتمالاً پیام پاک شده — fall through به send
                            body = await r.text()
                            logger.info(f"edit index failed (will resend): {body[:200]}")
            except Exception as e:
                logger.warning(f"edit index exception: {e}")

        # 2) ارسال پیام جدید + pin
        send_url = f"https://api.telegram.org/bot{tg.bot_token}/sendMessage"
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(send_url, json={
                    "chat_id": chat_id_str,
                    "text": content,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                    "disable_notification": True,
                    "reply_markup": kb,
                }) as r:
                    body = await r.json()
                    if r.status != 200 or not body.get("ok"):
                        return {"ok": False, "error": f"send failed: {body}"}
                    new_msg_id = body.get("result", {}).get("message_id")
                # pin پیام
                if new_msg_id:
                    pin_url = f"https://api.telegram.org/bot{tg.bot_token}/pinChatMessage"
                    try:
                        async with session.post(pin_url, json={
                            "chat_id": chat_id_str,
                            "message_id": new_msg_id,
                            "disable_notification": True,
                        }) as pr:
                            pass  # موفق یا ناموفق — مهم نیست
                    except Exception as _pe:
                        logger.debug(f"pin index msg failed: {_pe}")
            _write_index_state({
                "chat_id": chat_id_str,
                "message_id": new_msg_id,
                "last_updated": _now_epoch(),
                "last_content_hash": content_hash,
                "pinned": True,
            })
            return {"ok": True, "created": True, "message_id": new_msg_id}
        except Exception as e:
            return {"ok": False, "error": str(e)[:300]}

    async def refresh_index_silently(self) -> Dict[str, Any]:
        """تابع helper برای background refresh — وقتی task تغییر می‌کند صدا زده می‌شود.

        اگر هیچ index قبلی موجود نیست، چیزی نمی‌سازد (تا کاربر مزاحم نشود).
        فقط edit می‌کند اگر message_id قبلی هست.

        اگر content یکسان با آخرین نسخهٔ ارسالی باشد، edit نمی‌زند (تا Telegram
        «message is not modified» 400 نده و log noise کم شود).
        """
        state = _read_index_state()
        chat_id = state.get("chat_id")
        msg_id = state.get("message_id")
        if not chat_id or not msg_id:
            return {"ok": True, "skipped": "no_index_yet"}
        tg = self._telegram()
        if not tg.bot_token:
            return {"ok": False, "error": "no token"}
        try:
            content = self._build_index_content()
            # hash content — skip اگر تغییری نیست
            import hashlib
            content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()[:16]
            if state.get("last_content_hash") == content_hash:
                return {"ok": True, "skipped": "no_change"}
            kb = {
                "inline_keyboard": [
                    [{"text": "🔄 به‌روزرسانی", "callback_data": "index:refresh"}],
                ],
            }
            edit_url = f"https://api.telegram.org/bot{tg.bot_token}/editMessageText"
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(edit_url, json={
                    "chat_id": chat_id,
                    "message_id": msg_id,
                    "text": content,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                    "reply_markup": kb,
                }) as r:
                    if r.status == 200:
                        _write_index_state({
                            **state,
                            "last_updated": _now_epoch(),
                            "last_content_hash": content_hash,
                        })
                        return {"ok": True, "edited": True}
                    return {"ok": False, "status": r.status}
        except Exception as e:
            logger.debug(f"refresh_index_silently failed: {e}")
            return {"ok": False, "error": str(e)[:200]}

    async def _codex_debug(self, chat_id_str: str) -> Dict[str, Any]:
        """نمایش وضعیت دقیق سیستم برای debug کردن `/codex` flow.

        کاربر می‌تواند این را اجرا کند تا ببیند:
          - کدام version از کد اجرا می‌شود
          - کدام env variables برای provider ها set است
          - چند مدل در registry موجود است
          - فیلتر نهایی چه می‌دهد
        """
        tg = self._telegram()
        import os as _os
        from datetime import datetime as _dt

        lines: List[str] = []
        lines.append("🔧 *Codex Debug Info*")
        lines.append("")
        # Version marker (تغییر در commit جدید)
        lines.append("Version: `bulletproof-v2 (d163442+)`")
        lines.append(f"Time: `{_dt.utcnow().isoformat()[:19]}Z`")
        lines.append("")

        # Step 1: env vars
        env_keys = {
            "OPENAI_API_KEY": "openai",
            "ANTHROPIC_API_KEY": "claude/anthropic",
            "CLAUDE_API_KEY": "claude (alt)",
            "GEMINI_API_KEY": "gemini",
            "GOOGLE_API_KEY": "google (alt)",
            "DEEPSEEK_API_KEY": "deepseek",
            "PERPLEXITY_API_KEY": "perplexity",
        }
        lines.append("*ENV vars:*")
        env_set = []
        for k, label in env_keys.items():
            val = (_os.environ.get(k) or "").strip()
            if val:
                lines.append(f"  ✅ `{k}` → {label} (len={len(val)})")
                env_set.append(k)
            else:
                lines.append(f"  ❌ `{k}`")
        lines.append("")

        # Step 2: registry
        try:
            from ..core.models_registry import get_enabled_models, MODEL_REGISTRY
            total = len(MODEL_REGISTRY)
            enabled = get_enabled_models() or []
            lines.append(f"*Registry:* {total} total, {len(enabled)} enabled")
            # نمونه: ۵ مدل اول
            for m in enabled[:5]:
                prov = m.provider
                prov_str = (prov.value if hasattr(prov, "value") else str(prov))
                lines.append(f"  • `{m.id}` ({prov_str})")
            if len(enabled) > 5:
                lines.append(f"  ... و {len(enabled) - 5} مدل دیگر")
        except Exception as e:
            lines.append(f"❌ Registry error: `{str(e)[:200]}`")
        lines.append("")

        # Step 3: final available
        try:
            providers_with_key = set()
            provider_env_keys = {
                "openai": ["OPENAI_API_KEY"],
                "claude": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
                "anthropic": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
                "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
                "google": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
                "deepseek": ["DEEPSEEK_API_KEY"],
                "perplexity": ["PERPLEXITY_API_KEY"],
            }
            for pname, ekeys in provider_env_keys.items():
                if any((_os.environ.get(k) or "").strip() for k in ekeys):
                    providers_with_key.add(pname.lower())
            from ..core.models_registry import get_enabled_models as _gem
            avail = []
            for model in (_gem() or []):
                prov = model.provider
                prov_str = (prov.value if hasattr(prov, "value") else str(prov)).lower()
                if prov_str in providers_with_key:
                    avail.append(model.id)
            lines.append(f"*Available (env-only):* {len(avail)} مدل")
            for mid in avail[:8]:
                lines.append(f"  ✅ `{mid}`")
        except Exception as e:
            lines.append(f"❌ Filter error: `{str(e)[:200]}`")

        # Step 4: DB filter (model_settings table)
        lines.append("")
        try:
            from ..core.database import SessionLocal
            from ..models.ai_profile import ModelSettings
            db = SessionLocal()
            try:
                rows = db.query(ModelSettings).all()
                enabled_in_db = [r.model_id for r in rows if r.enabled]
                disabled_in_db = [r.model_id for r in rows if not r.enabled]
                lines.append(f"*DB Filter:* {len(enabled_in_db)} enabled, {len(disabled_in_db)} disabled")
                for mid in enabled_in_db[:8]:
                    lines.append(f"  ✅ `{mid}`")
                if disabled_in_db:
                    lines.append("  Disabled:")
                    for mid in disabled_in_db[:5]:
                        lines.append(f"    ❌ `{mid}`")
            finally:
                db.close()
        except Exception as e:
            lines.append(f"❌ DB filter check failed: `{str(e)[:200]}`")

        lines.append("")
        lines.append("---")
        lines.append("اگر «Available models = 0» ولی ENV vars ست است،")
        lines.append("registry با ENV ناهماهنگ است — لطفاً ارسال کنید این خروجی را.")

        await tg.send("\n".join(lines), silent=True)
        return {"ok": True, "handled": "codex_debug"}

    # -----------------------------------------------------------------------
    # 🆕 (AI Usage) /usage و /balance — نمایش مصرف AI + موجودی provider ها
    # -----------------------------------------------------------------------

    async def _show_ai_usage(
        self, chat_id_str: str, *, refresh: bool = False,
    ) -> Dict[str, Any]:
        """نمایش خلاصه‌ای از مصرف AI + موجودی provider ها در تلگرام."""
        tg = self._telegram()
        try:
            # 1. summary مصرف
            from ..core.database import SessionLocal
            from ..models.ai_log import AILog
            from sqlalchemy import func
            from datetime import timedelta as _td
            db = SessionLocal()
            try:
                now = datetime.now(timezone.utc).replace(tzinfo=None)
                today = now.replace(hour=0, minute=0, second=0, microsecond=0)
                last_7d = now - _td(days=7)

                def _agg(since):
                    row = db.query(
                        func.count(AILog.id),
                        func.sum(AILog.total_tokens),
                        func.sum(AILog.cost),
                    ).filter(AILog.created_at >= since).first()
                    return {
                        "count": int((row[0] or 0) if row else 0),
                        "tokens": int((row[1] or 0) if row else 0),
                        "cost": round(float((row[2] or 0) if row else 0), 4),
                    }
                today_agg = _agg(today)
                week_agg = _agg(last_7d)

                # per-provider breakdown (آخرین ۷ روز)
                provider_rows = db.query(
                    AILog.provider,
                    func.count(AILog.id),
                    func.sum(AILog.total_tokens),
                    func.sum(AILog.cost),
                ).filter(AILog.created_at >= last_7d).group_by(AILog.provider).all()
            finally:
                db.close()
        except Exception as e:
            logger.exception(f"_show_ai_usage db error: {e}")
            await tg.send(
                f"❌ خطا در خواندن مصرف از DB:\n`{str(e)[:200]}`",
                silent=True,
            )
            return {"ok": True, "handled": "usage_db_error"}

        # 2. موجودی‌ها (با refresh اختیاری)
        try:
            from .ai_balance_service import AIBalanceService
            if refresh:
                await tg.send("⏳ در حال refresh موجودی‌ها...", silent=True)
                await AIBalanceService.check_and_notify()
            balances_state = AIBalanceService.get_all_balances()
        except Exception as e:
            logger.warning(f"_show_ai_usage balance error: {e}")
            balances_state = {}

        # 3. ساخت متن
        def _fmt_num(n):
            if n >= 1_000_000:
                return f"{n/1_000_000:.2f}M"
            if n >= 1_000:
                return f"{n/1_000:.1f}K"
            return str(n)

        def _fmt_cost(c):
            if c < 0.01:
                return f"${c:.6f}"
            if c < 1:
                return f"${c:.4f}"
            return f"${c:.2f}"

        lines: List[str] = []
        lines.append("💰 *مصرف AI و موجودی*")
        lines.append("")
        lines.append("─" * 25)
        lines.append("*📈 مصرف*")
        lines.append(
            f"📅 امروز: *{_fmt_num(today_agg['tokens'])}* توکن · "
            f"{today_agg['count']} request · {_fmt_cost(today_agg['cost'])}"
        )
        lines.append(
            f"🗓 ۷ روز: *{_fmt_num(week_agg['tokens'])}* توکن · "
            f"{week_agg['count']} request · {_fmt_cost(week_agg['cost'])}"
        )
        lines.append("")

        if provider_rows:
            lines.append("─" * 25)
            lines.append("*🤖 Per Provider (۷ روز)*")
            for prov, cnt, tok, cost in sorted(
                provider_rows, key=lambda r: -(r[2] or 0)
            ):
                lines.append(
                    f"• `{prov}`: {_fmt_num(int(tok or 0))} tok · "
                    f"{int(cnt or 0)} req · {_fmt_cost(float(cost or 0))}"
                )
            lines.append("")

        # 4. موجودی‌ها
        lines.append("─" * 25)
        lines.append("*💳 موجودی*")
        if not balances_state:
            lines.append("هنوز هیچ provider/budget تنظیم نشده.")
            lines.append("از پنل وب: /settings → 📊 مصرف AI → 💰 موجودی")
        else:
            for prov, data in balances_state.items():
                ptype = data.get("type", "")
                threshold = data.get("alert_threshold_usd", 1.0)
                if ptype == "remote_api":
                    bal = data.get("remote_balance_usd", 0)
                    curr = data.get("currency", "USD")
                    icon = "🟢" if bal > threshold else "🔴"
                    lines.append(f"{icon} `{prov}` (API): *{bal:.2f} {curr}*")
                elif ptype == "manual_budget":
                    budget = data.get("budget_usd", 0)
                    remaining = data.get("remaining_estimate_usd", 0)
                    consumed = data.get("consumed_usd", 0)
                    icon = "🟢" if remaining > threshold else "🔴"
                    pct = (consumed / budget * 100) if budget > 0 else 0
                    lines.append(
                        f"{icon} `{prov}` (manual): باقی *${remaining:.2f}* از ${budget:.2f} "
                        f"({pct:.0f}% مصرف)"
                    )

        prefs = _read_prefs()
        base = (prefs.get("app_base_url", "") or "").rstrip("/")

        # 5. inline keyboard: refresh + لینک پنل
        rows: List[List[Dict[str, str]]] = [
            [{"text": "🔄 refresh موجودی (DeepSeek API)", "callback_data": "usage:refresh_balance"}],
        ]
        if base:
            rows.append([
                {"text": "📊 پنل کامل", "url": f"{base}/settings?tab=usage"},
            ])
        rows.append([{"text": "❌ بستن", "callback_data": "flow:cancel"}])

        await tg.send(
            "\n".join(lines),
            silent=True,
            reply_markup={"inline_keyboard": rows},
        )
        return {"ok": True, "handled": "ai_usage_shown"}

    async def _start_codex_flow(self, chat_id_str: str) -> Dict[str, Any]:
        """مرحلهٔ ۱: انتخاب پروژه از لیست watched."""
        tg = self._telegram()
        try:
            from .oversight_service import get_oversight_service
            _oversight = get_oversight_service()
        except Exception as e:
            await tg.send(f"❌ خطا در بارگذاری سرویس oversight: {e}", silent=True)
            return {"ok": True, "handled": "codex_fail"}

        watched_list = list(_oversight.watched or [])
        if not watched_list:
            await tg.send(
                "⚠️ هیچ پروژهٔ تحت نظارتی پیدا نشد.\n"
                "ابتدا در پنل وب /oversight یک پروژه اضافه کنید.",
                silent=True,
            )
            return {"ok": True, "handled": "codex_no_watched"}

        # picker با callback codex:pick:<watched_id>
        items = watched_list[:12]
        rows: List[List[Dict[str, str]]] = []
        for i in range(0, len(items), 2):
            row: List[Dict[str, str]] = []
            for w in items[i:i + 2]:
                label = (w.repo_full_name or w.id)[:30]
                row.append({"text": f"📁 {label}", "callback_data": f"codex:pick:{w.id}"})
            rows.append(row)
        rows.append([{"text": "❌ لغو", "callback_data": "flow:cancel"}])

        await tg.send(
            "📚 *شناسنامهٔ پروژه (Codex)*\n\nپروژه را انتخاب کنید:",
            silent=True,
            reply_markup={"inline_keyboard": rows},
        )
        return {"ok": True, "handled": "codex_picker", "count": len(items)}

    async def _handle_codex_callback(
        self, chat_id_str: str, data: str,
    ) -> Dict[str, Any]:
        """پردازش callback های codex:* —
        codex:pick:<watched_id>       → نمایش وضعیت + گزینه‌ها
        codex:view:<watched_id>       → ارسال markdown کامل به‌عنوان فایل
        codex:build:<watched_id>      → نمایش model picker
        codex:build_model:<wid>:<mid> → اجرای refresh_codex با مدل انتخابی
        codex:refresh:<watched_id>    → alias برای build (وقتی codex از قبل هست)

        نکته: model_id می‌تواند حاوی ":" باشد (مثل "openai:gpt-4o") — برای
        build_model، parts بعد از index 2 با ":" دوباره join می‌شود.
        """
        tg = self._telegram()
        logger.info(f"codex callback: data={data}")
        parts = data.split(":")
        if len(parts) < 3:
            await tg.send("⚠️ callback نامعتبر.", silent=True)
            return {"ok": True, "handled": "codex_bad_cb"}
        action = parts[1]
        watched_id = parts[2]

        # 🆕 (BUG FIX) برای action='bm'، parts[2] یک token کوتاه است نه UUID.
        # ابتدا token را resolve می‌کنیم تا watched_id واقعی پیدا شود، سپس
        # action را به build_model تبدیل می‌کنیم و parts را reshape می‌کنیم.
        if action == "bm":
            if len(parts) < 4:
                await tg.send("⚠️ callback نامعتبر (bm).", silent=True)
                return {"ok": True, "handled": "codex_bm_bad"}
            token = parts[2]
            try:
                idx = int(parts[3])
            except Exception:
                await tg.send("⚠️ index نامعتبر در callback.", silent=True)
                return {"ok": True, "handled": "codex_bm_bad_idx"}
            draft = _idea_drafts.get(token)
            if not draft or "models" not in draft:
                await tg.send(
                    "⚠️ این انتخاب منقضی شده. لطفاً /codex بزنید و دوباره امتحان کنید.",
                    silent=True,
                )
                return {"ok": True, "handled": "codex_bm_expired"}
            models = draft.get("models") or []
            if idx < 0 or idx >= len(models):
                await tg.send("⚠️ index خارج از محدوده.", silent=True)
                return {"ok": True, "handled": "codex_bm_oob"}
            # resolve واقعی
            model_id = models[idx]
            watched_id = draft.get("watched_id") or ""
            # token را extend کن (تا اگر بازم استفاده شد منقضی نباشد)
            draft["expires_at"] = _now_epoch() + _STATE_TTL_SECONDS
            # تبدیل به build_model
            action = "build_model"
            parts = ["codex", "build_model", watched_id, model_id]

        try:
            from .oversight_service import get_oversight_service
            from .oversight_codex_service import read_codex
            _oversight = get_oversight_service()
            watched = next((w for w in _oversight.watched if w.id == watched_id), None)
        except Exception as e:
            await tg.send(f"❌ خطای backend: {e}", silent=True)
            return {"ok": True, "handled": "codex_backend_fail"}

        if not watched:
            await tg.send(
                f"⚠️ پروژه یافت نشد (id=`{watched_id[:12]}...`)",
                silent=True,
            )
            return {"ok": True, "handled": "codex_no_project"}

        # ============= pick =============
        if action == "pick":
            codex = read_codex(watched_id)
            files = codex.get("files") or {}
            n = len(files)
            stacks = ", ".join(codex.get("stacks") or []) or "نامشخص"
            model_used = codex.get("model_used") or "—"
            updated = codex.get("updated_at") or ""
            if updated:
                try:
                    from datetime import datetime
                    updated = datetime.fromisoformat(
                        updated.replace("Z", "+00:00")
                    ).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    pass

            if n == 0:
                msg = (
                    f"📚 *Codex برای* `{watched.repo_full_name}`\n\n"
                    f"⚠️ هنوز ساخته نشده است.\n\n"
                    f"شناسنامه شامل می‌شود:\n"
                    f"• توضیح کامل پروژه و کاربردها\n"
                    f"• مستندات per-file (backend + frontend)\n"
                    f"• نقشهٔ وابستگی فایل‌ها\n"
                    f"• خلاصهٔ نیازمندی‌ها بر اساس تسک‌ها\n\n"
                    f"برای ساخت با AI، روی دکمهٔ زیر کلیک کنید:"
                )
                kb = {
                    "inline_keyboard": [
                        [{"text": "🪄 ساخت با AI", "callback_data": f"codex:build:{watched_id}"}],
                        [{"text": "❌ بستن", "callback_data": "flow:cancel"}],
                    ],
                }
            else:
                # شمارش per-category + flags overview/action_items
                by_cat = codex.get("files_by_category") or {}
                cat_summary = ""
                if by_cat:
                    cat_bits = []
                    for cat, num in by_cat.items():
                        if num > 0:
                            cat_bits.append(f"{cat}: {num}")
                    if cat_bits:
                        cat_summary = "\n📂 " + " · ".join(cat_bits)
                has_overview = bool(codex.get("overview"))
                has_actions = bool(codex.get("action_items"))
                total_files = codex.get("total_repo_files") or 0
                msg = (
                    f"📚 *Codex* `{watched.repo_full_name}`\n\n"
                    f"📄 *{n}* فایل مستند"
                    + (f" (از {total_files} فایل پروژه)" if total_files else "")
                    + f"{cat_summary}\n"
                    f"🛠 Stack: `{stacks}`\n"
                    f"🎯 توضیح پروژه: {'✅' if has_overview else '❌ ندارد'}\n"
                    f"🚧 نیازمندی‌ها: {'✅' if has_actions else '❌ ندارد'}\n"
                    f"🤖 مدل آخر: `{model_used}`\n"
                    f"🕒 به‌روز: {updated or '—'}"
                )
                kb = {
                    "inline_keyboard": [
                        [{"text": "📄 مشاهدهٔ کامل (فایل md)", "callback_data": f"codex:view:{watched_id}"}],
                        [{"text": "🔄 به‌روزرسانی با AI", "callback_data": f"codex:build:{watched_id}"}],
                        [{"text": "❌ بستن", "callback_data": "flow:cancel"}],
                    ],
                }
            await tg.send(msg, silent=True, reply_markup=kb)
            return {"ok": True, "handled": "codex_pick", "files_count": n}

        # ============= view (download markdown) =============
        if action == "view":
            codex = read_codex(watched_id)
            files = codex.get("files") or {}
            if not files:
                await tg.send(
                    "⚠️ Codex هنوز ساخته نشده. ابتدا با «🪄 ساخت با AI» بسازید.",
                    silent=True,
                )
                return {"ok": True, "handled": "codex_view_empty"}
            md = self._render_codex_markdown(codex, watched.repo_full_name)
            filename = f"codex-{watched.repo_full_name.replace('/', '-')}.md"
            caption = (
                f"📚 *Codex — {watched.repo_full_name}*\n"
                f"📄 {len(files)} فایل · 🤖 {codex.get('model_used') or '—'}"
            )
            res = await tg.send_document(
                md.encode("utf-8"), filename, caption=caption, silent=True,
            )
            if not res.get("ok"):
                await tg.send(
                    f"❌ خطا در ارسال فایل: {res.get('error', '?')}",
                    silent=True,
                )
            return {"ok": True, "handled": "codex_view", "sent": bool(res.get("ok"))}

        # ============= build (نمایش model picker) =============
        if action == "build":
            # 🆕 پیام فوری progress — کاربر بلافاصله می‌داند کلیکش ثبت شد
            await tg.send("⏳ *آماده‌سازی فهرست مدل‌های AI...*", silent=True)
            # 🆕 (FIXED) ترکیب env + DB filter:
            #   1. enabled_models از registry (in-memory)
            #   2. providers_with_key از env
            #   3. *FILTER اضافی*: ModelSettings.enabled در DB (اگر دسترسی داشت)
            # DB query با timeout کوتاه. اگر timeout/error، فقط env-based filter
            # اعمال می‌شود (یعنی نمی‌توانیم disable در پنل را اعمال کنیم — fallback).
            available: List[Any] = []
            enabled_count = 0
            available_providers: List[str] = []
            db_filter_applied = False
            db_enabled_set: Optional[set] = None
            try:
                from ..core.models_registry import get_enabled_models
                enabled_models = get_enabled_models() or []
                enabled_count = len(enabled_models)
                logger.info(f"codex: get_enabled_models returned {enabled_count}")

                # Step 1: providers با API key مشخص — فقط ENV
                import os as _os
                provider_env_keys = {
                    "openai": ["OPENAI_API_KEY"],
                    "claude": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
                    "anthropic": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
                    "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
                    "google": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
                    "deepseek": ["DEEPSEEK_API_KEY"],
                    "perplexity": ["PERPLEXITY_API_KEY"],
                }
                providers_with_key = set()
                for pname, ekeys in provider_env_keys.items():
                    if any((_os.environ.get(k) or "").strip() for k in ekeys):
                        providers_with_key.add(pname.lower())
                available_providers = sorted(providers_with_key)
                logger.info(f"codex: providers with API key: {available_providers}")

                # Step 2: DB filter (با timeout کوتاه) — مدل‌های disabled در پنل را خارج کن
                # اگر DB pool exhausted/down است، خاموش skip می‌شود.
                try:
                    def _load_db_settings():
                        from ..core.database import SessionLocal
                        from ..models.ai_profile import ModelSettings
                        db = SessionLocal()
                        try:
                            rows = db.query(ModelSettings).all()
                            # ModelSettings.enabled = 1 یعنی فعال
                            return {r.model_id for r in rows if r.enabled}
                        finally:
                            db.close()
                    loop = asyncio.get_event_loop()
                    db_enabled_set = await asyncio.wait_for(
                        loop.run_in_executor(None, _load_db_settings),
                        timeout=5.0,
                    )
                    db_filter_applied = True
                    logger.info(
                        f"codex: DB filter loaded ({len(db_enabled_set)} enabled in DB)"
                    )
                except asyncio.TimeoutError:
                    logger.warning("codex: DB filter timeout (5s) — fallback to env-only")
                    db_enabled_set = None
                except Exception as _db_e:
                    logger.warning(f"codex: DB filter unavailable — fallback to env-only: {_db_e}")
                    db_enabled_set = None

                # Step 3: filter نهایی
                for model in enabled_models:
                    prov = model.provider
                    prov_str = (prov.value if hasattr(prov, "value") else str(prov)).lower()
                    # filter 1: provider با API key
                    if prov_str not in providers_with_key:
                        continue
                    # filter 2: DB enabled (اگر در دسترس بود)
                    if db_filter_applied and db_enabled_set is not None:
                        if model.id not in db_enabled_set:
                            continue
                    available.append(model)
                logger.info(
                    f"codex build: {len(available)} models available "
                    f"(db_filter={db_filter_applied})"
                )
            except Exception as e:
                logger.exception(f"codex build models enumeration failed: {e}")
                await tg.send(
                    f"❌ *خطا در شناسایی مدل‌ها*\n\n`{str(e)[:300]}`\n\n"
                    f"می‌توانید از پنل وب /settings مدل را تنظیم کنید.",
                    silent=False,
                )
                return {"ok": True, "handled": "codex_enum_fail", "error": str(e)}

            if not available:
                # تشخیص دقیق چرا خالی است
                if enabled_count == 0:
                    msg = (
                        "⚠️ *هیچ مدلی در MODEL_REGISTRY enabled نیست*\n\n"
                        "این یک خطای سیستمی است — لطفاً admin را خبر کنید."
                    )
                elif not available_providers:
                    msg = (
                        "⚠️ *هیچ کلید API در env تنظیم نشده*\n\n"
                        f"از {enabled_count} مدل registered، هیچ کدام provider با API key ندارد.\n\n"
                        "روی Render → Environment، یکی از این‌ها را اضافه کنید:\n"
                        "• `OPENAI_API_KEY`\n"
                        "• `ANTHROPIC_API_KEY`\n"
                        "• `GEMINI_API_KEY`\n"
                        "• `DEEPSEEK_API_KEY`\n"
                        "• `PERPLEXITY_API_KEY`\n\n"
                        "سپس restart service بزنید."
                    )
                else:
                    msg = (
                        f"⚠️ *هیچ مدل مطابق پیدا نشد*\n\n"
                        f"Providers با API key: `{', '.join(available_providers)}`\n"
                        f"مدل‌های enabled در registry: *{enabled_count}*\n"
                        f"ولی هیچ مدل matched نشد — احتمالاً registry با ENV ناهماهنگ است."
                    )
                await tg.send(msg, silent=False)
                return {"ok": True, "handled": "codex_no_model"}

            # picker مدل — استفاده از token + index برای callback_data کوتاه.
            # علت: callback_data در Telegram محدود به 64 byte است.
            # codex:build_model:<UUID>:<long-model-id> می‌تواند > 64 شود.
            # مثلاً claude-3-5-sonnet-20241022 → 81 byte → reject!
            # حالا: codex:bm:<8char-token>:<index> → max ~22 byte ✓
            token = _short_token()
            _idea_drafts[token] = {
                "watched_id": watched_id,
                "models": [m.id for m in available[:8]],
                "repo": watched.repo_full_name,
                "expires_at": _now_epoch() + _STATE_TTL_SECONDS,
            }
            rows: List[List[Dict[str, str]]] = []
            for i, m in enumerate(available[:8]):
                rows.append([{
                    "text": f"🤖 {m.id}",
                    "callback_data": f"codex:bm:{token}:{i}",
                }])
            rows.append([{"text": "❌ انصراف", "callback_data": "flow:cancel"}])
            # text فاقد escape pitfall (نام پروژه با _ ممکن است باشد)
            repo_safe = (watched.repo_full_name or "").replace("`", "")
            filter_note = (
                "🔍 _مطابق تنظیمات صفحهٔ «مدل‌ها»_"
                if db_filter_applied
                else "⚠️ _filter DB غیرفعال — لیست کامل registry (admin: pod restart کنید)_"
            )
            await tg.send(
                f"📚 *ساخت Codex برای* `{repo_safe}`\n\n"
                f"✅ *{len(available)} مدل فعال*. کدام مدل استفاده شود؟\n"
                f"{filter_note}\n\n"
                f"Providers: {', '.join(available_providers)}",
                silent=True,
                reply_markup={"inline_keyboard": rows},
            )
            return {
                "ok": True, "handled": "codex_model_picker",
                "available": len(available),
                "db_filter_applied": db_filter_applied,
            }

        # ============= build_model:<wid>:<mid> =============
        # نکته: action='bm' در ابتدای handler resolve می‌شود (نه اینجا).
        if action == "build_model":
            if len(parts) < 4:
                await tg.send("⚠️ model_id در callback نیست.", silent=True)
                return {"ok": True, "handled": "codex_no_mid"}
            # model_id ممکن است حاوی ":" باشد (مثل "openai:gpt-4o") — همهٔ
            # parts بعد از index 2 را با ":" join می‌کنیم
            model_id = ":".join(parts[3:])
            logger.info(f"codex build_model: watched={watched_id} model={model_id}")
            # 🆕 پیام progress واضح + پایدار
            await tg.send(
                f"⏳ *در حال ساخت Codex...*\n\n"
                f"📁 پروژه: `{watched.repo_full_name}`\n"
                f"🤖 مدل: `{model_id}`\n\n"
                f"🔍 مراحل:\n"
                f"  1️⃣ خواندن ساختار پروژه از GitHub\n"
                f"  2️⃣ انتخاب متوازن backend + frontend\n"
                f"  3️⃣ تحلیل با AI (شامل overview + dependencies + action_items)\n"
                f"  4️⃣ ذخیره و ارسال نتیجه\n\n"
                f"⏱ این فرآیند *30 تا 90 ثانیه* طول می‌کشد. منتظر بمانید...",
                silent=True,
            )
            try:
                from .oversight_codex_service import refresh_codex as _refresh_codex
                result = await _refresh_codex(
                    watched_id,
                    model_id=model_id,
                    only_changed=False,
                )
                files_n = result.get("files_documented", 0)
                new_n = result.get("newly_added", 0)
                used_model = result.get("model_used") or model_id
                used_deep = result.get("used_deep_structure", False)
                has_overview = result.get("has_overview", False)
                has_actions = result.get("has_action_items", False)
                total_files = result.get("total_repo_files", 0)
                by_cat = result.get("files_by_category") or {}
                cat_summary = ""
                if by_cat:
                    cat_bits = [f"{c}: {n}" for c, n in by_cat.items() if n > 0]
                    if cat_bits:
                        cat_summary = "\n📂 " + " · ".join(cat_bits)
                deep_warn = "" if used_deep else "\n⚠️ بدون Deep Scan — توصیه می‌شود ابتدا scan کنید."
                msg = (
                    f"✅ *Codex ساخته شد*\n\n"
                    f"📁 `{watched.repo_full_name}`\n"
                    f"📄 {files_n} فایل مستند شده ({new_n} جدید)"
                    + (f" از {total_files}" if total_files else "")
                    + cat_summary
                    + f"\n🎯 توضیح پروژه: {'✅' if has_overview else '❌'}"
                    + f"\n🚧 نیازمندی‌ها: {'✅' if has_actions else '❌'}"
                    + f"\n🤖 مدل: `{used_model}`"
                    + deep_warn
                )
                kb = {
                    "inline_keyboard": [
                        [{"text": "📄 مشاهدهٔ کامل", "callback_data": f"codex:view:{watched_id}"}],
                        [{"text": "✅ تمام", "callback_data": "flow:cancel"}],
                    ],
                }
                await tg.send(msg, silent=False, reply_markup=kb)
                return {
                    "ok": True, "handled": "codex_built",
                    "files_documented": files_n,
                    "model_used": used_model,
                }
            except Exception as e:
                logger.exception(f"codex build_model fail: {e}")
                err_text = str(e)[:500]
                # دکمه برای retry با مدل دیگر
                retry_kb = {
                    "inline_keyboard": [
                        [{"text": "🔄 امتحان دوباره با مدل دیگر", "callback_data": f"codex:build:{watched_id}"}],
                        [{"text": "❌ بستن", "callback_data": "flow:cancel"}],
                    ],
                }
                await tg.send(
                    f"❌ *خطا در ساخت Codex*\n\n"
                    f"🤖 مدل: `{model_id}`\n"
                    f"💬 خطا:\n`{err_text}`\n\n"
                    f"می‌توانید مدل دیگری امتحان کنید یا از پنل وب اقدام کنید.",
                    silent=False,
                    reply_markup=retry_kb,
                )
                return {"ok": True, "handled": "codex_build_fail", "error": err_text}

        await tg.send(f"⚠️ action ناشناخته: `{action}`", silent=True)
        return {"ok": True, "handled": "codex_unknown_action"}

    def _render_codex_markdown(self, codex: Dict[str, Any], repo_name: str) -> str:
        """تبدیل Codex به markdown با ساختار overview + files (دسته‌بندی شده) + action_items."""
        lines: List[str] = []

        # === Header ===
        lines.append(f"# 📚 Codex — {repo_name}")
        lines.append("")
        if codex.get("user_goal"):
            lines.append(f"> 🎯 **هدف کاربر**: {codex['user_goal']}")
            lines.append("")
        meta_bits: List[str] = []
        if codex.get("stacks"):
            meta_bits.append(f"**Stack**: {', '.join(codex['stacks'])}")
        if codex.get("model_used"):
            meta_bits.append(f"**مدل**: `{codex['model_used']}`")
        if codex.get("updated_at"):
            meta_bits.append(f"**به‌روز**: {codex['updated_at']}")
        if codex.get("total_repo_files"):
            meta_bits.append(
                f"**فایل‌های تحلیل‌شده**: {codex.get('files_count', 0)} از "
                f"{codex.get('total_repo_files', 0)}"
            )
        if meta_bits:
            lines.append(" · ".join(meta_bits))
            lines.append("")

        files_by_cat = codex.get("files_by_category") or {}
        if files_by_cat:
            cat_summary = " · ".join(
                f"{cat}: {n}" for cat, n in files_by_cat.items() if n > 0
            )
            lines.append(f"**توزیع**: {cat_summary}")
            lines.append("")
        lines.append("---")
        lines.append("")

        # === Overview ===
        overview = codex.get("overview") or {}
        if overview:
            lines.append("## 🎯 توضیح کلی پروژه")
            lines.append("")
            if overview.get("purpose"):
                lines.append(overview["purpose"])
                lines.append("")
            cap = overview.get("capabilities") or []
            if cap:
                lines.append("### ✨ قابلیت‌ها")
                lines.append("")
                for c in cap:
                    lines.append(f"- {c}")
                lines.append("")
            uc = overview.get("use_cases") or []
            if uc:
                lines.append("### 🎯 کاربردها")
                lines.append("")
                for u in uc:
                    lines.append(f"- {u}")
                lines.append("")
            if overview.get("target_users"):
                lines.append(f"**کاربران هدف**: {overview['target_users']}")
                lines.append("")
            ts = overview.get("tech_stack") or {}
            if ts:
                lines.append("### 🛠 Tech Stack")
                lines.append("")
                if ts.get("backend"):
                    lines.append(f"- **Backend**: {ts['backend']}")
                if ts.get("frontend"):
                    lines.append(f"- **Frontend**: {ts['frontend']}")
                if ts.get("storage"):
                    lines.append(f"- **Storage**: {ts['storage']}")
                ints = ts.get("integrations") or []
                if ints:
                    lines.append(f"- **Integrations**: {', '.join(ints)}")
                lines.append("")
            if overview.get("architecture_summary"):
                lines.append("### 🏗 معماری")
                lines.append("")
                lines.append(overview["architecture_summary"])
                lines.append("")
            kc = overview.get("key_concepts") or []
            if kc:
                lines.append("### 🔑 مفاهیم کلیدی")
                lines.append("")
                for k in kc:
                    lines.append(f"- {k}")
                lines.append("")
            lines.append("---")
            lines.append("")

        # === Files — گروه‌بندی شده ===
        files = codex.get("files") or {}
        if files:
            # دسته‌بندی فایل‌ها
            try:
                from .oversight_codex_service import _categorize_file
            except Exception:
                _categorize_file = lambda p: "other"
            grouped: Dict[str, List[str]] = {}
            for path in files.keys():
                cat = _categorize_file(path)
                grouped.setdefault(cat, []).append(path)
            # ترتیب نمایش
            order = ["backend", "frontend", "config", "docs", "scripts", "tests", "other"]
            cat_labels = {
                "backend": "🐍 Backend",
                "frontend": "⚛️ Frontend",
                "config": "⚙️ Config",
                "docs": "📖 Docs",
                "scripts": "🔧 Scripts",
                "tests": "🧪 Tests",
                "other": "📁 سایر",
            }
            lines.append(f"## 📂 فایل‌ها ({len(files)} مورد)")
            lines.append("")
            for cat in order:
                items = sorted(grouped.get(cat, []))
                if not items:
                    continue
                lines.append(f"### {cat_labels.get(cat, cat)} ({len(items)})")
                lines.append("")
                for path in items:
                    doc = files.get(path) or {}
                    if not isinstance(doc, dict):
                        continue
                    lines.append(f"#### `{path}`")
                    if doc.get("what_is_it"):
                        lines.append(f"- **این چیست؟** {doc['what_is_it']}")
                    if doc.get("what_it_does"):
                        lines.append(f"- **چه می‌کند؟** {doc['what_it_does']}")
                    uc = doc.get("use_cases") or []
                    if uc:
                        lines.append("- **کاربردها**:")
                        for u in uc:
                            lines.append(f"  - {u}")
                    dep = doc.get("depends_on") or []
                    if dep:
                        lines.append(f"- **وابسته به**: {', '.join(f'`{x}`' for x in dep)}")
                    used = doc.get("used_by") or []
                    if used:
                        lines.append(f"- **استفاده‌شده در**: {', '.join(f'`{x}`' for x in used)}")
                    # backward-compat: relations فیلد قدیمی
                    if doc.get("relations") and not (dep or used):
                        lines.append(f"- **روابط**: {doc['relations']}")
                    if doc.get("breaks_if_removed"):
                        lines.append(f"- **در صورت حذف**: {doc['breaks_if_removed']}")
                    lines.append("")
                lines.append("")

        # === Action Items ===
        action = codex.get("action_items") or {}
        if action:
            lines.append("---")
            lines.append("")
            lines.append("## 🚧 نیازمندی‌ها و بهبودها")
            lines.append("")
            if action.get("summary"):
                lines.append(f"> {action['summary']}")
                lines.append("")
            needs = action.get("needs_attention") or []
            if needs:
                lines.append("### ⚠️ موارد نیازمند توجه")
                lines.append("")
                priority_icon = {
                    "critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵",
                }
                for n in needs:
                    if isinstance(n, dict):
                        pri = (n.get("priority") or "medium").lower()
                        icon = priority_icon.get(pri, "•")
                        item = n.get("item") or ""
                        lines.append(f"- {icon} [{pri}] {item}")
                    else:
                        lines.append(f"- {n}")
                lines.append("")
            improvements = action.get("suggested_improvements") or []
            if improvements:
                lines.append("### 💡 پیشنهادات بهبود")
                lines.append("")
                for imp in improvements:
                    lines.append(f"- {imp}")
                lines.append("")
            risks = action.get("risks") or []
            if risks:
                lines.append("### ⚠️ ریسک‌ها")
                lines.append("")
                for r in risks:
                    lines.append(f"- {r}")
                lines.append("")

        return "\n".join(lines)

    # -----------------------------------------------------------------------
    # 🆕 (Creator) /new_project flow — ساخت پروژه از تلگرام
    # -----------------------------------------------------------------------

    async def _start_new_project_flow(self, chat_id_str: str) -> Dict[str, Any]:
        """🆕 مرحلهٔ ۰ flow جدید: ابتدا انتخاب مدل (اجباری)."""
        _chat_state[chat_id_str] = {
            "phase": "creator_awaiting_model_choice",
            "creator_data": {"model_ids": []},
            "expires_at": _now_epoch() + _STATE_TTL_SECONDS,
        }
        # نمایش لیست مدل‌های available
        return await self._show_creator_model_picker(chat_id_str)

    async def _show_creator_model_picker(self, chat_id_str: str) -> Dict[str, Any]:
        """نمایش inline keyboard برای انتخاب مدل‌های creator (multi-select)."""
        tg = self._telegram()
        try:
            from .ai_manager import get_ai_manager
            ai_mgr = get_ai_manager()
            available = ai_mgr.get_available_models() or []
        except Exception as e:
            logger.warning(f"creator: failed to get models: {e}")
            available = []

        if not available:
            await tg.send(
                "⚠️ هیچ مدل AI فعالی نیست. ابتدا از /settings کلید API را وارد کنید.\n"
                "/cancel برای لغو",
                silent=True,
            )
            return {"ok": True, "handled": "no_models"}

        state = _chat_state.get(chat_id_str, {})
        selected = (state.get("creator_data", {}) or {}).get("model_ids", []) or []

        # سطح کلیپ: حداکثر ۱۲ مدل نمایش داده می‌شود
        rows: List[List[Dict[str, str]]] = []
        for i in range(0, min(len(available), 12), 2):
            row: List[Dict[str, str]] = []
            for m in available[i:i + 2]:
                is_selected = m.id in selected
                label = ("✅ " if is_selected else "") + m.name[:30]
                row.append({"text": label, "callback_data": f"creator_model:{m.id}"})
            rows.append(row)
        # کنترل‌های پایین
        rows.append([
            {"text": f"✅ تأیید ({len(selected)} مدل)", "callback_data": "creator_models_confirm"},
            {"text": "❌ لغو", "callback_data": "flow:cancel"},
        ])

        await tg.send(
            "🤖 *مرحلهٔ ۱/۵: انتخاب مدل AI*\n\n"
            "حداقل یک مدل انتخاب کنید. اگر چند مدل انتخاب شد، اولی primary است و\n"
            "بقیه به ترتیب برای fallback استفاده می‌شوند.\n\n"
            f"الان انتخاب شده: *{len(selected)} مدل*",
            silent=True,
            reply_markup={"inline_keyboard": rows},
        )
        return {"ok": True, "handled": "model_picker_shown"}

    async def _handle_creator_phase(
        self, chat_id_str: str, state: Dict[str, Any], text: str,
    ) -> Dict[str, Any]:
        """مدیریت مراحل text-based در flow creator."""
        import re
        tg = self._telegram()
        phase = state.get("phase")
        data = state.get("creator_data", {})

        # phase 1: name
        if phase == "creator_awaiting_name":
            name = text.strip()
            if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]{2,}$", name):
                await tg.send(
                    "⚠️ نام نامعتبر است. باید با حرف شروع شود و فقط a-z A-Z 0-9 - _ بپذیرد (3+ کاراکتر).\n"
                    "دوباره وارد کن یا /cancel:",
                    silent=True,
                )
                return {"ok": True, "handled": "name_invalid"}
            data["name"] = name
            state["phase"] = "creator_awaiting_desc"
            state["creator_data"] = data
            state["expires_at"] = _now_epoch() + _STATE_TTL_SECONDS
            await tg.send(
                f"✅ نام: `{name}`\n\n"
                f"📋 *توضیح پروژه را وارد کن*\n"
                f"(حداقل ۱۰ کاراکتر — چه کاری انجام می‌دهد):",
                silent=True,
            )
            return {"ok": True, "handled": "name_ok"}

        # phase 2: description
        if phase == "creator_awaiting_desc":
            desc = text.strip()
            if len(desc) < 10:
                await tg.send(
                    "⚠️ توضیح خیلی کوتاه است. حداقل ۱۰ کاراکتر — جزئیات بیشتر بنویس:",
                    silent=True,
                )
                return {"ok": True, "handled": "desc_too_short"}
            data["description"] = desc
            state["phase"] = "creator_awaiting_type"
            state["creator_data"] = data
            state["expires_at"] = _now_epoch() + _STATE_TTL_SECONDS
            # ارسال inline keyboard برای انتخاب نوع
            kb = self._render_project_type_picker()
            await tg.send(
                f"✅ توضیح ذخیره شد\n\n"
                f"📁 *نوع پروژه را انتخاب کن:*",
                silent=True,
                reply_markup=kb,
            )
            return {"ok": True, "handled": "desc_ok"}

        # phase 4: technologies
        if phase == "creator_awaiting_tech":
            if text.strip().lower() in ("/skip", "skip", "ندارم", "خیر"):
                data["technologies"] = []
            else:
                techs = [t.strip() for t in text.split(",") if t.strip()]
                data["technologies"] = techs[:10]  # max 10
            state["creator_data"] = data
            # توکن برای confirm
            token = _short_token()
            _idea_drafts[token] = {
                "creator_data": data,
                "expires_at": _now_epoch() + _STATE_TTL_SECONDS,
            }
            _chat_state.pop(chat_id_str, None)
            # نمایش summary + دکمه‌های تأیید
            tech_label = ", ".join(data.get("technologies") or []) or "(پیش‌فرض)"
            summary = (
                f"📋 *تأیید نهایی*\n\n"
                f"📦 نام: `{data['name']}`\n"
                f"📁 نوع: `{data['project_type']}`\n"
                f"🔧 تکنولوژی: {tech_label}\n\n"
                f"💡 توضیح:\n_{data['description'][:300]}_\n\n"
                f"تأیید می‌کنی؟"
            )
            kb = {
                "inline_keyboard": [
                    [
                        {"text": "✅ بساز + push به GitHub", "callback_data": f"creator_confirm:push:{token}"},
                    ],
                    [
                        {"text": "📁 فقط محلی", "callback_data": f"creator_confirm:local:{token}"},
                    ],
                    [
                        {"text": "❌ لغو", "callback_data": "flow:cancel"},
                    ],
                ]
            }
            await tg.send(summary, silent=True, reply_markup=kb)
            return {"ok": True, "handled": "tech_ok"}

        # ناشناخته
        return {"ok": True, "handled": "creator_unknown_phase"}

    def _render_project_type_picker(self) -> Dict[str, Any]:
        """inline keyboard برای انتخاب نوع پروژه (۸ گزینه)."""
        types = [
            ("🐍 fastapi", "fastapi"),
            ("⚛️ nextjs", "nextjs"),
            ("⚛️ react", "react"),
            ("🐍 flask", "flask"),
            ("📦 node", "node"),
            ("🐍 cli", "cli"),
            ("🐍 python", "python"),
            ("🤖 auto-detect", "auto"),
        ]
        rows = []
        for i in range(0, len(types), 2):
            row = []
            for label, value in types[i:i + 2]:
                row.append({"text": label, "callback_data": f"creator_type:{value}"})
            rows.append(row)
        rows.append([{"text": "❌ لغو", "callback_data": "flow:cancel"}])
        return {"inline_keyboard": rows}

    async def _execute_creator_flow(
        self, chat_id_str: str, draft: Dict[str, Any], push_to_github: bool,
    ) -> Dict[str, Any]:
        """ساخت واقعی پروژه + push اختیاری + auto-watch + feedback."""
        tg = self._telegram()
        data = draft.get("creator_data", {})
        name = data.get("name", "")
        description = data.get("description", "")
        project_type = data.get("project_type", "fastapi")
        technologies = data.get("technologies", []) or []

        # auto-detect خاص: project_type=="auto" → endpoint detect-type را call کن
        if project_type == "auto":
            try:
                from ..api.routes.simple_projects import _detect_project_type
                # signature: _detect_project_type(description, name="", model_ids=None)
                detected = await _detect_project_type(
                    description=description,
                    name=name,
                )
                project_type = (detected or {}).get("project_type") or "fastapi"
            except Exception as _e:
                logger.warning(f"auto-detect failed, fallback to fastapi: {_e}")
                project_type = "fastapi"

        await tg.send(
            f"⏳ در حال ساخت پروژه `{name}` ...\n"
            f"📁 نوع: `{project_type}`\n"
            f"این فرآیند 1-3 دقیقه طول می‌کشد",
            silent=True,
        )

        try:
            from .simple_creator import get_simple_creator
            # استفاده از helper موجود در route (که signature درست را می‌داند)
            from ..api.routes.simple_projects import ai_generate as _ai_gen
            creator = get_simple_creator()

            project = await creator.create_project(
                name=name,
                description=description,
                project_type=project_type,
                technologies=technologies,
                ai_generate=_ai_gen,
            )
            # Project یک dataclass است (با .id)؛ ولی dict هم پشتیبانی کنیم
            if hasattr(project, "id"):
                project_id = project.id
            elif isinstance(project, dict):
                project_id = project.get("id")
            else:
                project_id = None
            if not project_id:
                raise RuntimeError("project.id خالی است — create_project خروجی نامعتبر")

            # اگر push_to_github
            if push_to_github:
                from ..api.routes.simple_projects import push_to_github as _push_endpoint, PushToGitHubRequest
                push_req = PushToGitHubRequest()
                push_result = await _push_endpoint(project_id, push_req)
                if not push_result.get("success"):
                    raise RuntimeError(
                        f"push failed: {push_result.get('message', 'unknown')}"
                    )
                full_name = push_result.get("full_name") or f"{push_result.get('owner')}/{push_result.get('repo')}"
                repo_url = push_result.get("repo_url", "")
                files_count = push_result.get("uploaded", 0)
                watched_id = (push_result.get("auto_watched") or {}).get("id", "")
            else:
                full_name = name
                repo_url = ""
                files_count = len(getattr(project, "files", []) or [])
                watched_id = ""

            # ساخت inline_keyboard موفقیت
            prefs = _read_prefs()
            base = (prefs.get("app_base_url", "") or "").rstrip("/")
            kb_rows = []
            if repo_url:
                kb_rows.append([{"text": "👁 GitHub repo", "url": repo_url}])
            if base:
                kb_rows.append([
                    {"text": "🏠 مرکز نظارت", "url": f"{base}/oversight"},
                    {"text": "📋 تسک‌ها", "url": f"{base}/oversight?tab=tasks"},
                ])
            kb = {"inline_keyboard": kb_rows} if kb_rows else None

            tech_label = ", ".join(technologies) or "(پیش‌فرض)"
            status_text = (
                "✓ خودکار به مرکز نظارت اضافه شد\n"
                "✓ autonomy: auto (scan خودکار)\n"
                "✓ execution: manual (apply با کلیک شما)\n"
                "✓ scan_depth: deep (تمام 12 pass)\n"
                "✓ بازه scan: 168 ساعت (هفتگی)"
            ) if push_to_github else "📁 پروژه فقط محلی است (push نشد)"

            await tg.send(
                f"✅ *پروژه با موفقیت ساخته شد*\n\n"
                f"📦 نام: `{full_name}`\n"
                + (f"🔗 GitHub: {repo_url}\n" if repo_url else "")
                + f"📁 نوع: `{project_type}`\n"
                f"🔧 تکنولوژی: {tech_label}\n"
                f"📄 فایل‌های ساخته‌شده: *{files_count}*\n\n"
                f"💡 *کارکرد:*\n_{description[:300]}_\n\n"
                f"👁 *وضعیت در مرکز نظارت:*\n{status_text}\n\n"
                f"#project_created #{project_type} #{name.replace('-', '_').replace(' ', '_')}",
                silent=False,
                reply_markup=kb,
            )
            return {"ok": True, "handled": "creator_done", "project_id": project_id}
        except Exception as e:
            logger.exception(f"creator flow failed: {e}")
            err_msg = str(e)[:300]
            await tg.send(
                f"❌ *خطا در ساخت پروژه*\n\n"
                f"📦 نام: `{name}`\n"
                f"🔍 خطا: `{err_msg}`\n\n"
                f"احتمالاً GitHub token تنظیم نشده یا AI fail شد. "
                f"از پنل وب امتحان کنید: /settings",
                silent=False,
            )
            # event creator_failed
            try:
                await self.notify_event(
                    "creator_failed",
                    f"💥 *creator flow از Telegram fail شد*\n"
                    f"📦 نام: `{name}`\n"
                    f"❌ خطا: `{err_msg}`",
                    subject="Creator failed",
                    priority="high",
                    project_name=name,
                )
            except Exception:
                pass
            return {"ok": True, "handled": "creator_failed", "error": err_msg}


    # -----------------------------------------------------------------------
    # 🆕 (Creator v2) flow جدید با idea → strong prompt → preview → execute
    # -----------------------------------------------------------------------

    async def _receive_creator_custom_name(
        self, chat_id_str: str, state: Dict[str, Any], text: str,
    ) -> Dict[str, Any]:
        """phase awaiting_custom_name: کاربر نام دلخواه نوشته."""
        import re
        tg = self._telegram()
        name = text.strip()
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]{2,}$", name):
            await tg.send(
                "⚠️ نام نامعتبر. باید با حرف شروع شود و فقط a-z A-Z 0-9 - _ بپذیرد (3+ کاراکتر).\n"
                "دوباره وارد کن یا /cancel:",
                silent=True,
            )
            return {"ok": True, "handled": "name_invalid"}
        cdata = state.setdefault("creator_data", {})
        cdata["name"] = name
        state["phase"] = "creator_awaiting_type"
        state["expires_at"] = _now_epoch() + _STATE_TTL_SECONDS
        kb = self._render_project_type_picker()
        await tg.send(
            f"✅ نام: `{name}`\n\n"
            f"📁 *مرحلهٔ ۴/۵: نوع پروژه*",
            silent=True,
            reply_markup=kb,
        )
        return {"ok": True, "handled": "custom_name_ok"}

    async def _receive_creator_idea(
        self, chat_id_str: str, state: Dict[str, Any], text: str,
    ) -> Dict[str, Any]:
        """phase awaiting_idea: کاربر idea نوشته → name را بپرس یا auto-generate."""
        tg = self._telegram()
        idea = text.strip()
        if len(idea) < 15:
            await tg.send(
                "⚠️ ایده خیلی کوتاه است. حداقل ۱۵ کاراکتر — جزئیات بیشتر بنویس:",
                silent=True,
            )
            return {"ok": True, "handled": "idea_too_short"}

        cdata = state.setdefault("creator_data", {})
        cdata["idea"] = idea
        # نام را از ایده استخراج کن (ساده) یا از کاربر بپرس
        # فعلاً auto-generate و بپرس
        import re
        # استخراج کلمات کلیدی از ایده برای name suggestion
        words = re.findall(r"[a-zA-Z]+", idea.lower())[:3]
        if not words:
            # transliterate ساده — fallback
            suggested = "my-project"
        else:
            suggested = "-".join(words)
        cdata["suggested_name"] = suggested

        # transition to awaiting_name (یا اگر کاربر فقط suggested را خواست، skip)
        state["phase"] = "creator_awaiting_name_or_skip"
        state["expires_at"] = _now_epoch() + _STATE_TTL_SECONDS

        kb = {
            "inline_keyboard": [
                [
                    {"text": f"✅ استفاده از: {suggested}", "callback_data": "creator_use_suggested_name"},
                ],
                [
                    {"text": "✏️ نام دلخواه", "callback_data": "creator_custom_name"},
                ],
                [
                    {"text": "❌ لغو", "callback_data": "flow:cancel"},
                ],
            ]
        }
        await tg.send(
            f"💡 *ایده ثبت شد*\n\n"
            f"📋 طول: {len(idea)} کاراکتر\n\n"
            f"📦 *مرحلهٔ ۳/۵: نام پروژه*\n"
            f"پیشنهاد بر اساس ایده: `{suggested}`",
            silent=True,
            reply_markup=kb,
        )
        return {"ok": True, "handled": "idea_received"}

    async def _generate_creator_preview(
        self, chat_id_str: str, draft_token: str,
    ) -> Dict[str, Any]:
        """phase awaiting_prompt_preview: تولید preview prompt با مدل انتخابی."""
        tg = self._telegram()
        draft = _idea_drafts.get(draft_token)
        if not draft:
            await tg.send("⚠️ draft منقضی شده.", silent=True)
            return {"ok": True, "handled": "draft_expired"}

        cdata = draft.get("creator_data", {})
        idea = cdata.get("idea", "")
        name = cdata.get("name", "")
        project_type = cdata.get("project_type", "auto")
        model_ids = cdata.get("model_ids", [])

        try:
            from .creator_idea_to_prompt import idea_to_strong_prompt_for_creator
            from ..api.routes.simple_projects import ai_generate
            result = await idea_to_strong_prompt_for_creator(
                idea=idea,
                name=name,
                project_type=project_type,
                technologies=cdata.get("technologies", []),
                ai_generate=ai_generate,
                model_ids=model_ids,
            )
            cdata["structured_prompt"] = result
            _idea_drafts[draft_token] = draft
        except Exception as e:
            logger.exception(f"creator preview generation failed: {e}")
            await tg.send(
                f"💥 *خطا در تولید پرامپت*\n\n`{str(e)[:300]}`\n\n"
                f"احتمالاً مدل‌های انتخابی fail شدند. /new\\_project برای شروع مجدد.",
                silent=False,
            )
            return {"ok": True, "handled": "preview_gen_failed", "error": str(e)}

        # نمایش preview با ۴ دکمه
        full_text = result.get("full_prompt_text", "")
        preview_text = full_text[:1500] + ("\n…[truncated — متن کامل در پنل]" if len(full_text) > 1500 else "")
        warnings = result.get("warnings", [])
        warn_section = ""
        if warnings:
            warn_section = "\n⚠️ *هشدارهای AI:*\n" + "\n".join(f"• {_safe_md(w)}" for w in warnings[:3])

        kb = {
            "inline_keyboard": [
                [
                    {"text": "✅ تأیید و ساخت پروژه", "callback_data": f"creator_confirm_final:{draft_token}"},
                ],
                [
                    {"text": "🔄 بازتولید با مدل بعدی", "callback_data": f"creator_regenerate_prompt:{draft_token}"},
                    {"text": "✏️ ویرایش ایده", "callback_data": f"creator_edit_idea:{draft_token}"},
                ],
                [
                    {"text": "❌ لغو", "callback_data": "flow:cancel"},
                ],
            ]
        }
        await tg.send(
            f"🪄 *پرامپت قوی تولید شد*\n\n"
            f"🤖 با مدل: `{result.get('model_used', '?')}`\n"
            f"📦 پروژه: `{name}` ({project_type})\n"
            f"{warn_section}\n\n"
            f"📋 *پیش‌نمایش:*\n```\n{preview_text}\n```\n"
            f"✅ آماده برای ساخت پروژه؟",
            silent=True,
            reply_markup=kb,
        )
        return {"ok": True, "handled": "preview_generated", "token": draft_token}

    async def _execute_creator_v2(
        self, chat_id_str: str, draft: Dict[str, Any],
    ) -> Dict[str, Any]:
        """phase نهایی: ساخت پروژه با structured_prompt + push to GitHub + auto-watch."""
        tg = self._telegram()
        cdata = draft.get("creator_data", {})
        name = cdata.get("name", "")
        idea = cdata.get("idea", "")
        project_type = cdata.get("project_type", "auto")
        model_ids = cdata.get("model_ids", [])
        structured = cdata.get("structured_prompt", {})
        technologies = (structured.get("tech_stack") or cdata.get("technologies") or [])[:15]
        if project_type == "auto":
            # از structured_prompt سعی کن detect کنی
            project_type = "python"  # fallback

        # 📊 progress message
        import time
        t0 = time.time()
        await tg.send(
            f"⏳ *در حال ساخت پروژه*\n\n"
            f"📦 نام: `{name}`\n"
            f"🤖 مدل اصلی: `{model_ids[0]}`\n"
            f"⏱ تخمین: ۱-۳ دقیقه\n\n"
            f"📋 مراحل: 1) تولید ساختار 2) ساخت فایل‌ها 3) push GitHub 4) auto-watch",
            silent=True,
        )

        try:
            from .simple_creator import get_simple_creator
            from ..api.routes.simple_projects import ai_generate, push_to_github, PushToGitHubRequest

            creator = get_simple_creator()

            # closure برای ai_generate با model_ids
            async def _gen(prompt: str) -> str:
                return await ai_generate(prompt, model_ids=model_ids)

            # ساخت پروژه با structured prompt
            full_desc = structured.get("full_prompt_text") or structured.get("structured_description") or idea
            project = await creator.create_project(
                name=name,
                description=full_desc,
                project_type=project_type,
                technologies=technologies,
                ai_generate=_gen,
            )
            project_id = project.id if hasattr(project, "id") else None
            if not project_id:
                raise RuntimeError("project.id خالی است")

            # push to GitHub (always private)
            push_result = await push_to_github(project_id, PushToGitHubRequest(private=True))
            if not push_result.get("success"):
                # failure with detail
                err = push_result.get("primary_error", "unknown")
                cat = push_result.get("error_category", "unknown")
                actions = push_result.get("suggested_actions", [])
                detail = push_result.get("error_detail", "")
                await tg.send(
                    f"💥 *خطا در ساخت پروژه*\n\n"
                    f"📦 پروژه: `{name}`\n"
                    f"🤖 مدل مصرفی: `{model_ids[0]}`\n"
                    f"🔍 مرحلهٔ شکست: *push_to_github*\n\n"
                    f"❌ *علت اصلی:*\n{err}\n\n"
                    + (f"📋 *جزئیات:*\n```\n{detail[:400]}\n```\n\n" if detail else "")
                    + (f"🛠 *اقدامات پیشنهادی:*\n" + "\n".join(f"• {a}" for a in actions[:3]) if actions else "")
                    + f"\n\n📊 *آنچه انجام شد:*\n"
                    f"✓ idea_to_prompt: موفق\n"
                    f"✓ create_files: موفق ({push_result.get('uploaded', 0) + len(push_result.get('failed', []))} فایل)\n"
                    f"✗ push_to_github: شکست\n\n"
                    f"📁 پروژهٔ local موجود — بعد از fix می‌توانید push کنید.\n"
                    f"#creator_failed #{cat}",
                    silent=False,
                )
                return {"ok": True, "handled": "push_failed"}

            # موفقیت
            full_name = push_result.get("full_name") or f"{push_result.get('owner')}/{push_result.get('repo')}"
            repo_url = push_result.get("repo_url", "")
            files_count = push_result.get("uploaded", 0)
            elapsed = int(time.time() - t0)
            elapsed_str = f"{elapsed // 60}m {elapsed % 60}s" if elapsed >= 60 else f"{elapsed}s"

            prefs = _read_prefs()
            base = (prefs.get("app_base_url", "") or "").rstrip("/")
            kb_rows = []
            if repo_url:
                kb_rows.append([{"text": "👁 GitHub repo", "url": repo_url}])
            if base:
                kb_rows.append([
                    {"text": "🏠 مرکز نظارت", "url": f"{base}/oversight"},
                    {"text": "📋 تسک‌ها", "url": f"{base}/oversight?tab=tasks"},
                ])
            kb = {"inline_keyboard": kb_rows} if kb_rows else None

            tech_label = ", ".join(technologies) or "(پیش‌فرض)"
            await tg.send(
                f"✅ *پروژه با موفقیت ساخته شد*\n\n"
                f"📦 نام: `{full_name}`\n"
                f"🤖 مدل پرامپت: `{structured.get('model_used', '?')}`\n"
                f"🤖 مدل ساخت: `{model_ids[0]}`\n"
                f"🔗 GitHub: {repo_url} (🔒 private)\n\n"
                f"📁 نوع: `{project_type}`\n"
                f"🔧 تکنولوژی: {tech_label}\n\n"
                f"📊 *آمار ساخت:*\n"
                f"• فایل‌های تولیدشده: *{files_count}*\n"
                f"• مدت زمان: *{elapsed_str}*\n\n"
                f"💡 *کارکرد:*\n_{(structured.get('structured_description') or idea)[:300]}_\n\n"
                f"👁 *وضعیت در مرکز نظارت:*\n"
                f"✓ خودکار به watched اضافه شد\n"
                f"✓ autonomy: auto · execution: manual\n\n"
                f"#project_created #{project_type} #{name.replace('-', '_')} #{elapsed_str.replace(' ', '')}",
                silent=False,
                reply_markup=kb,
            )
            return {"ok": True, "handled": "creator_v2_done", "project_id": project_id}

        except Exception as e:
            logger.exception(f"creator v2 flow failed: {e}")
            err_msg = str(e)[:300]
            await tg.send(
                f"💥 *خطا در ساخت پروژه*\n\n"
                f"📦 نام: `{name}`\n"
                f"🤖 مدل: `{model_ids[0] if model_ids else '?'}`\n"
                f"❌ علت: `{err_msg}`\n\n"
                f"از پنل وب امتحان کنید: /settings\n"
                f"#creator_failed",
                silent=False,
            )
            try:
                await self.notify_event(
                    "creator_failed",
                    f"💥 creator v2 (Telegram): {name}\n{err_msg}",
                    subject="Creator v2 failed",
                    priority="high",
                    project_name=name,
                )
            except Exception:
                pass
            return {"ok": True, "handled": "creator_v2_failed", "error": err_msg}


notification_service = NotificationService()
