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

    async def handle_telegram_update(self, update: Dict[str, Any]) -> Dict[str, Any]:
        """پردازش update از Telegram webhook. فقط text commands را handle می‌کند."""
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

        if text in ("/start", "/help"):
            reply = (
                "👋 *سلام!*\n\n"
                "این ربات نوتیفیکیشن‌های سیستم نظارت پروژه است.\n\n"
                "دستورات:\n"
                "• /menu — منوی دسترسی سریع\n"
                "• /status — وضعیت نوتیفیکیشن\n"
                "• /help — این پیام"
            )
            kb = build_inline_keyboard(base, "manual_test") if base else None
            await tg.send(reply, silent=True, reply_markup=kb)
            return {"ok": True, "handled": "start"}

        if text == "/menu":
            reply = "📋 *منوی دسترسی سریع*\n\nاز دکمه‌های زیر برای رفتن به هر بخش استفاده کنید:"
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
            f"❓ دستور ناشناخته: `{text[:50]}`\nبا /menu شروع کنید.",
            silent=True,
        )
        return {"ok": True, "handled": "unknown"}


notification_service = NotificationService()
