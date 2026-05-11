"""AI Balance Service — موجودی شارژ و budgets دستی.

ویژگی‌ها:
  - DeepSeek: API واقعی `GET /user/balance` (تنها provider با public balance API)
  - OpenAI/Anthropic/Gemini/Perplexity: tracking دستی — کاربر budget تنظیم می‌کند،
    سرویس مصرف را از ai_logs بر اساس created_at >= reset_at محاسبه می‌کند
  - alert با event `ai_balance_low` با dedup (هر provider حداکثر یک alert per روز)

Storage: storage/oversight/ai_balance.json
{
  "deepseek": {
    "type": "remote_api",
    "remote_balance_usd": 4.23,
    "currency": "USD",
    "last_checked_at": "2026-05-11T14:00:00Z",
    "alert_threshold_usd": 1.0,
    "alert_last_sent_at": null,
  },
  "openai": {
    "type": "manual_budget",
    "budget_usd": 10.0,
    "budget_reset_at": "2026-05-01T00:00:00Z",  # شروع محاسبهٔ مصرف
    "alert_threshold_usd": 1.0,
    "alert_last_sent_at": null,
  },
  ...
}
"""

from __future__ import annotations

import os
import json
import logging
import aiohttp
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# storage path
try:
    from .oversight_service import STORAGE_DIR
    _BALANCE_FILE = STORAGE_DIR / "ai_balance.json"
except Exception:
    _BALANCE_FILE = Path("/tmp/ai_balance.json")


PROVIDERS_WITH_REMOTE_API = {"deepseek"}  # فقط این یکی public API موجودی دارد


def _read_state() -> Dict[str, Any]:
    try:
        if _BALANCE_FILE.exists():
            with open(_BALANCE_FILE, "r", encoding="utf-8") as f:
                return json.load(f) or {}
    except Exception as e:
        logger.warning(f"balance state read failed: {e}")
    return {}


def _write_state(state: Dict[str, Any]) -> None:
    try:
        _BALANCE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = _BALANCE_FILE.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        tmp.replace(_BALANCE_FILE)
    except Exception as e:
        logger.warning(f"balance state write failed: {e}")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# DeepSeek API
# ============================================================

async def fetch_deepseek_balance() -> Optional[Dict[str, Any]]:
    """خواندن موجودی از DeepSeek API.

    Endpoint: GET https://api.deepseek.com/user/balance
    Response example:
      {
        "is_available": true,
        "balance_infos": [
          {"currency": "USD", "total_balance": "4.23", "granted_balance": "0", "topped_up_balance": "4.23"}
        ]
      }

    خروجی: {"currency": "USD", "total_balance": 4.23, "topped_up": 4.23, "granted": 0.0}
    یا None در صورت خطا.
    """
    api_key = (os.environ.get("DEEPSEEK_API_KEY") or "").strip()
    if not api_key:
        logger.debug("deepseek balance: no API key in env")
        return None
    url = "https://api.deepseek.com/user/balance"
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers={"Authorization": f"Bearer {api_key}"}) as r:
                if r.status != 200:
                    body = await r.text()
                    logger.warning(f"deepseek balance API HTTP {r.status}: {body[:200]}")
                    return None
                data = await r.json()
                infos = data.get("balance_infos") or []
                # ترجیح USD، اگر نبود اولین
                usd = next((i for i in infos if (i.get("currency") or "").upper() == "USD"), None)
                pick = usd or (infos[0] if infos else None)
                if not pick:
                    return None
                return {
                    "currency": pick.get("currency", "USD"),
                    "total_balance": float(pick.get("total_balance") or 0),
                    "topped_up": float(pick.get("topped_up_balance") or 0),
                    "granted": float(pick.get("granted_balance") or 0),
                    "is_available": bool(data.get("is_available", True)),
                }
    except Exception as e:
        logger.warning(f"deepseek balance API error: {e}")
        return None


# ============================================================
# Budget service
# ============================================================

class AIBalanceService:
    """مدیریت موجودی و budget هر provider."""

    DEFAULT_THRESHOLD_USD = 1.0

    @staticmethod
    def get_all_balances() -> Dict[str, Any]:
        """خواندن state کامل (بدون refresh)."""
        return _read_state()

    @staticmethod
    def set_manual_budget(
        provider: str,
        budget_usd: float,
        reset_at: Optional[str] = None,
        alert_threshold_usd: Optional[float] = None,
    ) -> Dict[str, Any]:
        """کاربر دستی budget یک provider را تنظیم می‌کند.

        برای providerهایی که API balance ندارند (همه به‌جز DeepSeek).
        reset_at: زمان شروع محاسبهٔ مصرف از ai_logs (پیش‌فرض: الان).
        """
        state = _read_state()
        cur = state.get(provider, {})
        cur.update({
            "type": "manual_budget",
            "budget_usd": float(budget_usd),
            "budget_reset_at": reset_at or _now_iso(),
            "alert_threshold_usd": (
                float(alert_threshold_usd)
                if alert_threshold_usd is not None
                else cur.get("alert_threshold_usd", AIBalanceService.DEFAULT_THRESHOLD_USD)
            ),
            "alert_last_sent_at": None,  # reset alert
            "updated_at": _now_iso(),
        })
        state[provider] = cur
        _write_state(state)
        return cur

    @staticmethod
    def set_threshold(provider: str, threshold_usd: float) -> Dict[str, Any]:
        """تنظیم آستانهٔ alert برای یک provider."""
        state = _read_state()
        cur = state.get(provider, {})
        cur["alert_threshold_usd"] = float(threshold_usd)
        cur["updated_at"] = _now_iso()
        state[provider] = cur
        _write_state(state)
        return cur

    @staticmethod
    def remove_provider(provider: str) -> bool:
        """حذف budget یک provider."""
        state = _read_state()
        if provider in state:
            del state[provider]
            _write_state(state)
            return True
        return False

    @staticmethod
    def _get_consumed_usd_since(provider: str, since_iso: str) -> float:
        """جمع cost از ai_logs برای provider از زمان since_iso."""
        try:
            from ..core.database import SessionLocal
            from ..models.ai_log import AILog
            from sqlalchemy import func
            since_dt = datetime.fromisoformat(since_iso.replace("Z", "+00:00"))
            # SQLAlchemy expects timezone-naive for SQLite comparison با created_at
            if since_dt.tzinfo is not None:
                since_dt = since_dt.replace(tzinfo=None)
            db = SessionLocal()
            try:
                row = db.query(func.sum(AILog.cost)).filter(
                    AILog.provider == provider,
                    AILog.created_at >= since_dt,
                ).first()
                return round(float(row[0] or 0), 6) if row else 0.0
            finally:
                db.close()
        except Exception as e:
            logger.debug(f"_get_consumed_usd_since failed for {provider}: {e}")
            return 0.0

    @classmethod
    async def refresh_all(cls) -> Dict[str, Any]:
        """به‌روزرسانی موجودی همهٔ providers.

        - برای deepseek: API call
        - برای بقیه: محاسبهٔ remaining = budget - consumed_since_reset
        خروجی شامل وضعیت همه + لیست alertهای جدید.
        """
        state = _read_state()
        results: Dict[str, Any] = {}
        alerts: List[Dict[str, Any]] = []

        # 1) DeepSeek از API
        deepseek_data = await fetch_deepseek_balance()
        if deepseek_data is not None:
            cur = state.get("deepseek", {})
            threshold = float(
                cur.get("alert_threshold_usd", cls.DEFAULT_THRESHOLD_USD)
            )
            balance_usd = deepseek_data["total_balance"]
            cur.update({
                "type": "remote_api",
                "remote_balance_usd": balance_usd,
                "currency": deepseek_data["currency"],
                "is_available": deepseek_data["is_available"],
                "last_checked_at": _now_iso(),
                "alert_threshold_usd": threshold,
            })
            state["deepseek"] = cur
            results["deepseek"] = cur
            # alert check
            if balance_usd <= threshold:
                if cls._should_alert(cur):
                    alerts.append({
                        "provider": "deepseek",
                        "type": "remote_api",
                        "balance_usd": balance_usd,
                        "threshold_usd": threshold,
                        "currency": deepseek_data["currency"],
                    })
                    cur["alert_last_sent_at"] = _now_iso()

        # 2) بقیه — manual budget (اگر تنظیم شده)
        for provider, cur in list(state.items()):
            if provider == "deepseek":
                continue  # قبلاً انجام شد
            if cur.get("type") != "manual_budget":
                continue
            budget = float(cur.get("budget_usd") or 0)
            reset_at = cur.get("budget_reset_at") or _now_iso()
            consumed = cls._get_consumed_usd_since(provider, reset_at)
            remaining = max(0.0, budget - consumed)
            threshold = float(cur.get("alert_threshold_usd", cls.DEFAULT_THRESHOLD_USD))
            cur.update({
                "consumed_usd": consumed,
                "remaining_estimate_usd": round(remaining, 6),
                "last_checked_at": _now_iso(),
            })
            state[provider] = cur
            results[provider] = cur
            if remaining <= threshold:
                if cls._should_alert(cur):
                    alerts.append({
                        "provider": provider,
                        "type": "manual_budget",
                        "budget_usd": budget,
                        "consumed_usd": consumed,
                        "remaining_usd": remaining,
                        "threshold_usd": threshold,
                    })
                    cur["alert_last_sent_at"] = _now_iso()

        _write_state(state)
        return {
            "balances": results,
            "alerts": alerts,
            "checked_at": _now_iso(),
        }

    @staticmethod
    def _should_alert(provider_state: Dict[str, Any]) -> bool:
        """تشخیص اینکه آیا الان alert باید فرستاده شود (با dedup روزانه)."""
        last_sent = provider_state.get("alert_last_sent_at")
        if not last_sent:
            return True
        try:
            last_dt = datetime.fromisoformat(last_sent.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            return (now - last_dt) >= timedelta(hours=24)
        except Exception:
            return True

    @classmethod
    async def check_and_notify(cls) -> Dict[str, Any]:
        """refresh + ارسال notification برای هر alert."""
        result = await cls.refresh_all()
        alerts = result.get("alerts") or []
        for alert in alerts:
            try:
                from .notification_service import notification_service
                provider = alert["provider"]
                if alert["type"] == "remote_api":
                    curr = alert.get("currency", "USD")
                    currency_note = ""
                    if curr.upper() != "USD":
                        currency_note = (
                            f"\n⚠️ توجه: واحد پول `{curr}` است ولی threshold به USD است — "
                            f"اگر می‌خواهی hashtag دقیق باشد، threshold را به همان واحد تنظیم کن."
                        )
                    msg = (
                        f"💰 *موجودی کم — {provider}*\n\n"
                        f"موجودی فعلی: *{alert['balance_usd']:.2f} {curr}*\n"
                        f"آستانه: {alert['threshold_usd']:.2f} USD"
                        f"{currency_note}\n\n"
                        f"⚠️ لطفاً اکانت `{provider}` را شارژ کنید."
                    )
                else:
                    msg = (
                        f"💰 *Budget رو به اتمام — {provider}*\n\n"
                        f"Budget: ${alert['budget_usd']:.2f}\n"
                        f"مصرف: ${alert['consumed_usd']:.2f}\n"
                        f"باقی‌مانده (تخمینی): *${alert['remaining_usd']:.2f}*\n"
                        f"آستانه: ${alert['threshold_usd']:.2f}\n\n"
                        f"⚠️ احتمالاً اکانت `{provider}` در حال اتمام شارژ است."
                    )
                await notification_service.notify_event(
                    "ai_balance_low",
                    msg,
                    subject=f"موجودی کم — {provider}",
                    priority="high",
                )
            except Exception as e:
                logger.warning(f"ai_balance_low notify failed for {provider}: {e}")
        return result
