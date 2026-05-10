"""سرویس مرکزی نوتیفیکیشن

پشتیبانی از کانال‌های Telegram و Email.
- credentials از environment variables (در core/config.py)
- toggleهای event-level در فایل JSON ذخیره می‌شوند (notification_prefs.json)
- اگر env var نباشد، آن کانال silent skip می‌شود (هیچ exception نمی‌اندازد)

استفاده:
    from app.services.notification_service import notification_service
    await notification_service.notify_event("verify_done", "تسک X done شد", subject="...")
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
# Storage برای event-prefs (آیا verify_done notify شود؟ و …)
# ---------------------------------------------------------------------------

def _resolve_storage_dir() -> Path:
    """همان pattern oversight_service — fallback تا یک مسیر قابل نوشتن پیدا شود."""
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

DEFAULT_PREFS: Dict[str, Any] = {
    "events": {
        "verify_done": True,        # پس از پایان verify
        "scan_done": True,          # پس از پایان Deep Scan
        "task_failed": False,       # وقتی verify status = regressed/error
        "manual_test": True,        # برای دکمهٔ "تست ارسال"
    },
    "channels": {
        "telegram": {"enabled": True},   # اگر env var هست → فعال
        "email": {"enabled": True},
    },
    # min severity: only notify اگر یافته/تسک با priority بالاتر از این باشد
    "min_priority": "low",  # low | medium | high | critical
}


def _read_prefs() -> Dict[str, Any]:
    try:
        if _PREFS_FILE.exists():
            with open(_PREFS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # merge با defaults
            merged = json.loads(json.dumps(DEFAULT_PREFS))  # deep copy
            for k, v in data.items():
                if isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
                    merged[k].update(v)
                else:
                    merged[k] = v
            return merged
    except Exception as e:
        logger.warning(f"notification: read prefs failed: {e}")
    return json.loads(json.dumps(DEFAULT_PREFS))


def _write_prefs(prefs: Dict[str, Any]) -> None:
    try:
        tmp = _PREFS_FILE.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2)
        tmp.replace(_PREFS_FILE)
    except Exception as e:
        logger.warning(f"notification: write prefs failed: {e}")


# ---------------------------------------------------------------------------
# Channels
# ---------------------------------------------------------------------------

class NotificationChannel(ABC):
    name: str = "abstract"

    @abstractmethod
    async def send(self, message: str, subject: Optional[str] = None) -> Dict[str, Any]:
        """خروجی: {ok: bool, error?: str, channel: str}"""
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

    async def send(self, message: str, subject: Optional[str] = None) -> Dict[str, Any]:
        if not self.is_configured():
            return {"ok": False, "channel": self.name, "error": "TELEGRAM_BOT_TOKEN یا TELEGRAM_CHAT_ID تنظیم نشده"}
        text = f"*{subject}*\n\n{message}" if subject else message
        # Telegram محدودیت 4096 کاراکتر دارد
        if len(text) > 4000:
            text = text[:3990] + "\n…[truncated]"
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as r:
                    if r.status != 200:
                        body = await r.text()
                        return {"ok": False, "channel": self.name, "error": f"HTTP {r.status}: {body[:300]}"}
                    return {"ok": True, "channel": self.name}
        except Exception as e:
            return {"ok": False, "channel": self.name, "error": str(e)[:300]}


class EmailChannel(NotificationChannel):
    name = "email"

    def __init__(
        self,
        smtp_host: Optional[str],
        smtp_port: Optional[int],
        smtp_user: Optional[str],
        smtp_password: Optional[str],
        email_from: Optional[str],
        email_to: Optional[str],
    ):
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

    async def send(self, message: str, subject: Optional[str] = None) -> Dict[str, Any]:
        if not self.is_configured():
            return {
                "ok": False,
                "channel": self.name,
                "error": "SMTP credentials کامل تنظیم نشده‌اند (host/user/password/to)",
            }
        # smtplib sync است — در thread pool اجرا می‌کنیم
        return await asyncio.to_thread(self._send_sync, message, subject)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

PRIORITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


class NotificationService:
    def __init__(self):
        self._prefs_cache: Optional[Dict[str, Any]] = None

    def _build_channels(self) -> List[NotificationChannel]:
        channels: List[NotificationChannel] = []
        channels.append(
            TelegramChannel(
                bot_token=os.environ.get("TELEGRAM_BOT_TOKEN"),
                chat_id=os.environ.get("TELEGRAM_CHAT_ID"),
            )
        )
        channels.append(
            EmailChannel(
                smtp_host=os.environ.get("SMTP_HOST"),
                smtp_port=int(os.environ.get("SMTP_PORT") or 587),
                smtp_user=os.environ.get("SMTP_USER"),
                smtp_password=os.environ.get("SMTP_PASSWORD"),
                email_from=os.environ.get("NOTIFICATION_EMAIL_FROM"),
                email_to=os.environ.get("NOTIFICATION_EMAIL_TO"),
            )
        )
        return channels

    def get_prefs(self) -> Dict[str, Any]:
        return _read_prefs()

    def update_prefs(self, partial: Dict[str, Any]) -> Dict[str, Any]:
        cur = _read_prefs()
        # merge کم‌عمق
        for k, v in (partial or {}).items():
            if isinstance(v, dict) and k in cur and isinstance(cur[k], dict):
                cur[k].update(v)
            else:
                cur[k] = v
        _write_prefs(cur)
        return cur

    def get_status(self) -> Dict[str, Any]:
        """برای UI: کدام کانال env-configured است + prefs فعلی."""
        channels = self._build_channels()
        prefs = _read_prefs()
        status: Dict[str, Any] = {
            "prefs": prefs,
            "channels": {},
        }
        for ch in channels:
            ch_prefs = prefs.get("channels", {}).get(ch.name, {})
            status["channels"][ch.name] = {
                "configured_via_env": ch.is_configured(),
                "enabled_pref": bool(ch_prefs.get("enabled", True)),
                "ready": ch.is_configured() and bool(ch_prefs.get("enabled", True)),
            }
        return status

    async def send_to_all(self, message: str, subject: Optional[str] = None) -> List[Dict[str, Any]]:
        """ارسال به تمام کانال‌های ready (configured + enabled). silent skip برای کانال‌های ناآماده."""
        prefs = _read_prefs()
        results: List[Dict[str, Any]] = []
        for ch in self._build_channels():
            if not ch.is_configured():
                continue
            ch_prefs = prefs.get("channels", {}).get(ch.name, {})
            if not ch_prefs.get("enabled", True):
                continue
            res = await ch.send(message, subject=subject)
            results.append(res)
            if res.get("ok"):
                logger.info(f"notification sent via {ch.name}")
            else:
                logger.warning(f"notification {ch.name} failed: {res.get('error')}")
        return results

    async def notify_event(
        self,
        event: str,
        message: str,
        *,
        subject: Optional[str] = None,
        priority: str = "low",
    ) -> List[Dict[str, Any]]:
        """نوتیفیکیشن مشروط به prefs. اگر event off یا priority پایین‌تر از min، silent skip."""
        prefs = _read_prefs()
        events = prefs.get("events", {})
        if not events.get(event, True):
            return []
        min_pri = prefs.get("min_priority", "low")
        if PRIORITY_RANK.get(priority, 0) < PRIORITY_RANK.get(min_pri, 0):
            return []
        return await self.send_to_all(message, subject=subject)

    async def test_send(self, channel: Optional[str] = None) -> List[Dict[str, Any]]:
        """دکمهٔ تست — ارسال یک پیام نمونه. اگر channel مشخص شود، فقط همان."""
        msg = (
            "🔔 پیام تست از سیستم نوتیفیکیشن\n"
            "اگر این را می‌بینی یعنی پیکربندی درست انجام شده."
        )
        subj = "تست نوتیفیکیشن"
        if channel:
            for ch in self._build_channels():
                if ch.name == channel:
                    if not ch.is_configured():
                        return [{
                            "ok": False,
                            "channel": ch.name,
                            "error": "credentials در environment تنظیم نشده‌اند",
                        }]
                    return [await ch.send(msg, subject=subj)]
            return [{"ok": False, "channel": channel, "error": "کانال ناشناخته"}]
        return await self.send_to_all(msg, subject=subj)


# instance سراسری — همان pattern oversight
notification_service = NotificationService()
