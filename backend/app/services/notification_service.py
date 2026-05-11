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
        data.add_field(
            "document", file_bytes,
            filename=filename, content_type="text/markdown",
        )
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, data=data) as r:
                    if r.status != 200:
                        body = await r.text()
                        return {"ok": False, "channel": self.name, "error": f"HTTP {r.status}: {body[:300]}"}
                    return {"ok": True, "channel": self.name, "filename": filename}
        except Exception as e:
            return {"ok": False, "channel": self.name, "error": str(e)[:300]}

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


# 🆕 (P5) state machine برای flow چند-مرحله‌ای ربات (/new_task)
# in-memory state — اگر backend restart شود، session‌های فعال گم می‌شوند
# (timeout 10 دقیقه شدید است → cleanup خودکار)
_chat_state: Dict[str, Dict[str, Any]] = {}  # chat_id -> {phase, watched_id, idea?, expires_at}
_idea_drafts: Dict[str, Dict[str, Any]] = {}  # token -> {watched_id, idea, expires_at}
_STATE_TTL_SECONDS = 600  # 10 دقیقه


def _now_epoch() -> float:
    import time
    return time.time()


def _cleanup_expired_state() -> None:
    """حذف state و draft های منقضی — هر بار update اجرا می‌شود."""
    now = _now_epoch()
    for k in list(_chat_state.keys()):
        if _chat_state[k].get("expires_at", 0) < now:
            del _chat_state[k]
    for k in list(_idea_drafts.keys()):
        if _idea_drafts[k].get("expires_at", 0) < now:
            del _idea_drafts[k]


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
    ) -> List[Dict[str, Any]]:
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
        sound_prefs = prefs.get("sound", {})
        with_sound = bool(sound_prefs.get(event, EVENT_REGISTRY.get(event, {}).get("default_sound", False)))
        silent = not with_sound
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
            res = await ch.send(
                full_message, subject=subject, silent=silent, reply_markup=reply_markup,
            )
            results.append(res)
        return results

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
        """پاسخ به callback_query (برای حذف loading state دکمه)."""
        if not self._telegram().bot_token:
            return
        url = f"https://api.telegram.org/bot{self._telegram().bot_token}/answerCallbackQuery"
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                await session.post(url, json={
                    "callback_query_id": callback_query_id,
                    "text": text[:200] if text else None,
                })
        except Exception:
            pass

    async def handle_telegram_update(self, update: Dict[str, Any]) -> Dict[str, Any]:
        """پردازش update از Telegram webhook. text commands + callback_query."""
        _cleanup_expired_state()

        # ——— callback_query (دکمه‌های inline) ———
        cq = update.get("callback_query")
        if cq:
            return await self._handle_callback_query(cq)

        # ——— message ———
        msg = update.get("message") or {}
        text = (msg.get("text") or "").strip()
        chat = (msg.get("chat") or {})
        chat_id = chat.get("id")
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
            await tg.send(
                "✅ flow لغو شد." if had else "هیچ flow فعالی نبود.",
                silent=True,
            )
            return {"ok": True, "handled": "cancel"}

        # 🆕 ——— /codex (مشاهده/ساخت شناسنامهٔ پروژه از تلگرام) ———
        if text == "/codex":
            return await self._start_codex_flow(chat_id_str)

        # ——— /new_task و /new_idea (شروع flow جدید) ———
        if text in ("/new_task", "/new_idea"):
            return await self._start_new_task_flow(chat_id_str)

        # 🆕 ——— /new_project و /create_project (Creator flow) ———
        if text in ("/new_project", "/create_project"):
            return await self._start_new_project_flow(chat_id_str)

        # ——— state-aware ———
        state = _chat_state.get(chat_id_str)
        if state and state.get("phase") == "awaiting_idea":
            return await self._receive_idea_text(chat_id_str, state, text)
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
                "• /new\\_project یا /create\\_project — *🚀 ساخت پروژهٔ جدید* (از صفر، با push به GitHub)\n"
                "• /new\\_task یا /new\\_idea — ثبت تسک جدید با انتخاب پروژه\n"
                "• /codex — 📚 شناسنامهٔ پروژه (مشاهده یا ساخت با AI)\n"
                "• /menu — منوی دسترسی سریع\n"
                "• /status — وضعیت نوتیفیکیشن\n"
                "• /cancel — لغو flow فعلی\n"
                "• /help — این پیام"
            )
            kb = build_inline_keyboard(base, "manual_test") if base else None
            await tg.send(reply, silent=True, reply_markup=kb)
            return {"ok": True, "handled": "start"}

        if text == "/menu":
            reply = (
                "📋 *منوی دسترسی سریع*\n\n"
                "از دکمه‌های زیر برای رفتن به هر بخش استفاده کنید.\n"
                "برای ثبت تسک از تلگرام: /new\\_task"
            )
            if not base:
                reply += "\n\n⚠️ `app_base_url` در پنل تنظیمات ست نشده — لینک‌ها در دسترس نیستند."
                await tg.send(reply, silent=True)
                return {"ok": True, "handled": "menu_no_url"}
            kb = {
                "inline_keyboard": [
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
                        # 🆕 (Codex) دکمهٔ شناسنامه
                        {"text": "📚 شناسنامهٔ پروژه", "callback_data": "menu:codex"},
                    ],
                    [
                        {"text": "📦 مخازن", "url": f"{base}/oversight?tab=repos"},
                        {"text": "⚙️ تنظیمات", "url": f"{base}/settings"},
                    ],
                    [{"text": "🏠 صفحهٔ اصلی", "url": f"{base}/"}],
                ]
            }
            await tg.send(reply, silent=True, reply_markup=kb)
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
            f"❓ دستور ناشناخته: `{text[:50]}`\nبا /menu یا /new\\_task شروع کنید.",
            silent=True,
        )
        return {"ok": True, "handled": "unknown"}

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
        await self._answer_callback(cq_id)  # دکمه را از loading state خارج کن

        # flow:cancel
        if data == "flow:cancel":
            _chat_state.pop(chat_id_str, None)
            await tg.send("❌ flow لغو شد.", silent=True)
            return {"ok": True, "handled": "flow_cancel"}

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
            draft = _idea_drafts.get(token)
            if not draft:
                await tg.send("⚠️ draft منقضی شده. /new\\_task بزنید.", silent=True)
                return {"ok": True, "handled": "confirm_expired"}
            # حذف draft (یک‌بار مصرف)
            del _idea_drafts[token]
            await tg.send("⏳ در حال ساخت پرامپت با AI (15-30 ثانیه)...", silent=True)
            return await self._call_idea_to_prompt(
                chat_id_str, draft["watched_id"], draft["idea"],
            )

        # 🆕 menu shortcuts
        if data == "menu:new_project":
            return await self._start_new_project_flow(chat_id_str)
        if data == "menu:new_task":
            return await self._start_new_task_flow(chat_id_str)
        if data == "menu:codex":
            return await self._start_codex_flow(chat_id_str)

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
            data = await _oversight.idea_to_prompt(
                idea=idea,
                watched_id=watched_id,
                type_="other",
                priority="medium",
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

            # پاسخ به کاربر با لینک
            kb = None
            if base:
                kb = {
                    "inline_keyboard": [
                        [{"text": "📋 دیدن تسک‌ها", "url": f"{base}/oversight?tab=tasks"}],
                        [{"text": "👁 تحت نظارت", "url": f"{base}/oversight?tab=watched"}],
                    ]
                }
            await tg.send(
                f"✅ *تسک ساخته شد*\n\n"
                f"📌 _{(new_task.get('title') or '')[:120]}_\n"
                f"📁 `{new_task.get('project_full_name') or ''}`\n"
                f"🔖 {new_task.get('priority') or 'medium'} • {new_task.get('type') or 'other'}\n\n"
                f"در پنل قابل مشاهده، اجرا و verify است.",
                silent=False,  # موفقیت با صدا
                reply_markup=kb,
            )
            return {"ok": True, "handled": "task_created", "task_id": new_task.get("id")}
        except Exception as e:
            logger.exception(f"telegram bot idea_to_prompt failed: {e}")
            await tg.send(
                f"❌ خطا در ساخت تسک:\n`{str(e)[:300]}`\n\nبعداً دوباره تلاش کنید یا از پنل وب استفاده کنید.",
                silent=False,
            )
            return {"ok": True, "handled": "task_create_failed", "error": str(e)}

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
        draft = _idea_drafts.get(token)
        if not draft:
            await tg.send("⚠️ draft منقضی شده. /new\\_task بزنید.", silent=True)
            return {"ok": True, "handled": "task_dup_expired"}

        idea = draft.get("idea", "")
        watched_id = draft.get("watched_id")
        source = draft.get("source", "telegram_bot")
        # یک‌بار مصرف
        del _idea_drafts[token]

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
                data_p = await _oversight.idea_to_prompt(
                    idea=idea,
                    watched_id=watched_id,
                    type_="other",
                    priority="medium",
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
        """
        tg = self._telegram()
        parts = data.split(":")
        if len(parts) < 3:
            await tg.send("⚠️ callback نامعتبر.", silent=True)
            return {"ok": True, "handled": "codex_bad_cb"}
        action = parts[1]
        watched_id = parts[2]

        try:
            from .oversight_service import get_oversight_service
            from .oversight_codex_service import read_codex
            _oversight = get_oversight_service()
            watched = next((w for w in _oversight.watched if w.id == watched_id), None)
        except Exception as e:
            await tg.send(f"❌ خطای backend: {e}", silent=True)
            return {"ok": True, "handled": "codex_backend_fail"}

        if not watched:
            await tg.send("⚠️ پروژه یافت نشد.", silent=True)
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
            try:
                from .ai_manager import get_ai_manager
                ai_mgr = get_ai_manager()
                available = ai_mgr.get_available_models() or []
            except Exception as e:
                logger.warning(f"codex build: cannot load models: {e}")
                available = []
            if not available:
                await tg.send(
                    "⚠️ هیچ مدل AI فعالی نیست. ابتدا از پنل /settings یک کلید API "
                    "(OpenAI/Anthropic/Gemini/DeepSeek) وارد کنید.",
                    silent=True,
                )
                return {"ok": True, "handled": "codex_no_model"}

            # picker مدل — یک callback per model
            rows: List[List[Dict[str, str]]] = []
            for m in available[:8]:  # max 8 model
                rows.append([{
                    "text": f"🤖 {m.id}",
                    "callback_data": f"codex:build_model:{watched_id}:{m.id}",
                }])
            rows.append([{"text": "❌ انصراف", "callback_data": "flow:cancel"}])
            await tg.send(
                f"📚 *ساخت Codex برای* `{watched.repo_full_name}`\n\n"
                f"کدام مدل AI استفاده شود؟",
                silent=True,
                reply_markup={"inline_keyboard": rows},
            )
            return {"ok": True, "handled": "codex_model_picker", "available": len(available)}

        # ============= build_model:<wid>:<mid> =============
        if action == "build_model":
            if len(parts) < 4:
                await tg.send("⚠️ model_id در callback نیست.", silent=True)
                return {"ok": True, "handled": "codex_no_mid"}
            model_id = parts[3]
            await tg.send(
                f"⏳ *ساخت Codex با* `{model_id}`...\n"
                f"این فرآیند 30 تا 60 ثانیه طول می‌کشد.",
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
                err_text = str(e)[:500]
                await tg.send(
                    f"❌ *خطا در ساخت Codex*\n\n"
                    f"`{err_text}`\n\n"
                    f"می‌توانید مدل دیگری امتحان کنید یا از پنل وب اقدام کنید.",
                    silent=False,
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
