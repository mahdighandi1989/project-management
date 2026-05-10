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

        # ——— /new_task و /new_idea (شروع flow جدید) ———
        if text in ("/new_task", "/new_idea"):
            return await self._start_new_task_flow(chat_id_str)

        # ——— state-aware: اگر در phase awaiting_idea هستیم، text = idea ———
        state = _chat_state.get(chat_id_str)
        if state and state.get("phase") == "awaiting_idea":
            return await self._receive_idea_text(chat_id_str, state, text)

        if text in ("/start", "/help"):
            reply = (
                "👋 *سلام!*\n\n"
                "این ربات نوتیفیکیشن‌های سیستم نظارت پروژه است.\n\n"
                "دستورات:\n"
                "• /new\\_task یا /new\\_idea — ثبت تسک جدید با انتخاب پروژه\n"
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

        # ناشناخته
        await tg.send(f"❓ callback ناشناخته: `{data[:50]}`", silent=True)
        return {"ok": True, "handled": "unknown_callback"}

    async def _call_idea_to_prompt(
        self, chat_id_str: str, watched_id: str, idea: str,
    ) -> Dict[str, Any]:
        """فراخوانی idea_to_prompt و گزارش نتیجه به کاربر."""
        tg = self._telegram()
        prefs = _read_prefs()
        base = (prefs.get("app_base_url", "") or "").rstrip("/")
        try:
            from .oversight_service import get_oversight_service
            _oversight = get_oversight_service()
            data = await _oversight.idea_to_prompt(
                idea=idea,
                watched_id=watched_id,
                type_="other",
                priority="medium",
            )
            # data شامل title/prompt/... است؛ task واقعی باید ساخته شود
            # idea_to_prompt تسک نمی‌سازد — فقط prompt تولید می‌کند
            # برای ساخت task، service.create_task یا منطق مشابه
            from .oversight_service import OversightTask
            from datetime import datetime, timezone
            import uuid as _uuid
            new_task = OversightTask(
                id=str(_uuid.uuid4()),
                watched_id=watched_id,
                project_full_name=next(
                    (w.repo_full_name for w in _oversight.watched if w.id == watched_id), ""
                ),
                title=data.get("title") or idea[:80],
                prompt=data.get("prompt") or "",
                raw_idea=idea,
                type=data.get("type") or "other",
                priority=data.get("priority") or "medium",
                source="telegram_bot",
                target_files=data.get("target_files") or [],
                acceptance_criteria=data.get("acceptance_criteria") or [],
            )
            async with _oversight._lock:
                _oversight.tasks.insert(0, new_task)
                _oversight._save_tasks()

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
                f"📌 _{new_task.title[:120]}_\n"
                f"📁 `{new_task.project_full_name}`\n"
                f"🔖 {new_task.priority} • {new_task.type}\n\n"
                f"در پنل قابل مشاهده، اجرا و verify است.",
                silent=False,  # موفقیت با صدا
                reply_markup=kb,
            )
            return {"ok": True, "handled": "task_created", "task_id": new_task.id}
        except Exception as e:
            logger.exception(f"telegram bot idea_to_prompt failed: {e}")
            await tg.send(
                f"❌ خطا در ساخت تسک:\n`{str(e)[:300]}`\n\nبعداً دوباره تلاش کنید یا از پنل وب استفاده کنید.",
                silent=False,
            )
            return {"ok": True, "handled": "task_create_failed", "error": str(e)}


notification_service = NotificationService()
