"""
نقش‌های بازرس ویژه و حل‌وفصل مدل برای هر نقش (+ فعال‌سازی موقت)
================================================================

پیاده‌سازی ایدهٔ «هر مدل نقش خودش را بگیرد» (مثل subagentهای Claude Code):

  - هر «نقش» (orchestrator / coder / reviewer / verifier) یک زنجیرهٔ
    اولویت مدل دارد.
  - برای هر نقش، بهترین مدلی که هم provider-اش کلید دارد و هم در DB فعال
    است انتخاب می‌شود.
  - اگر بهترین کاندیدای یک نقش فقط «غیرفعال» باشد (کلید دارد ولی کاربر در
    /models خاموشش کرده)، می‌توان آن را **موقتاً** فعال کرد، کار را انجام
    داد، و بعد دقیقاً به حالت قبل برگرداند (status صفحهٔ /models دست‌نخورده).
  - اگر همهٔ مدل‌های لازم از قبل فعال باشند، هیچ تغییری در DB لازم نیست.

این ماژول state سراسری ندارد و امن برای استفادهٔ همزمان است (هر فراخوان
revert-info خودش را برمی‌گرداند).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..core.models_registry import get_model, ModelProvider
from ..core.logging_utils import StructuredLogger

slog = StructuredLogger(__name__, "INSPECTOR-ROLES")


# نقش‌های بازرس و زنجیرهٔ اولویت مدل هر کدام. اولین مدلِ «در دسترس + فعال»
# انتخاب می‌شود؛ اگر نبود، اولین مدلِ «در دسترس ولی غیرفعال» برای فعال‌سازی
# موقت کاندید می‌شود.
INSPECTOR_ROLE_MODELS: Dict[str, List[str]] = {
    # هماهنگ‌کننده/عامل اصلی — باید tool-calling داشته باشد (فعلاً فقط Claude).
    # اگر هیچ Claude در دسترس/قابل‌فعال‌سازی نبود، نقش unavailable می‌شود و
    # بازرس به pipeline تک‌شات معمولی برمی‌گردد.
    "orchestrator": [
        "claude-sonnet-4-6", "claude-opus-4-7", "claude-sonnet-4-20250514",
    ],
    # کدنویس — تغییر واقعی کد
    "coder": [
        "claude-sonnet-4-6", "deepseek-coder", "claude-sonnet-4-20250514",
        "gpt-4-turbo",
    ],
    # بازبین — بررسی صحت/امنیت تغییر
    "reviewer": [
        "claude-sonnet-4-6", "gpt-4-turbo", "claude-3-5-sonnet-20241022",
        "claude-sonnet-4-20250514",
    ],
    # تأییدکننده — verify نتیجه
    "verifier": [
        "claude-sonnet-4-6", "gpt-4o", "claude-opus-4-7",
        "claude-sonnet-4-20250514",
    ],
    # تحلیل‌گر اسکن — single-shot (tool-calling لازم نیست)، پس بهترین مدلِ هر
    # provider مجاز است؛ ترجیح با قوی‌ترین‌ها. برای اسکن عمیق/موردی/کوییک و
    # وقتی caller مدلی صریحاً نداده.
    "analyst": [
        "claude-sonnet-4-6", "claude-opus-4-7", "gpt-4o", "gemini-2.5-pro",
        "claude-sonnet-4-20250514", "gpt-4-turbo", "deepseek-chat",
    ],
}


def resolve_best_model(ai_manager, role: str = "analyst", exclude: Optional[List[str]] = None):
    """میان‌بُر: RoleAssignment بهترین مدل برای یک نقش را برمی‌گرداند (یا None)."""
    try:
        return resolve_role_assignments(ai_manager, roles=[role], exclude=exclude).get(role)
    except Exception:
        return None


# مدل‌هایی که برای اسکن/تحلیل عمیق «ضعیف» محسوب می‌شوند و بهتر است ارتقا یابند.
_WEAK_SCAN_HINTS = ("deepseek", "haiku", "mini", "gpt-3.5", "flash")


def pick_scan_model(ai_manager, model_id=None, model_ids=None):
    """مدل مؤثر برای یک اسکن single-model را انتخاب می‌کند (+ temp-enable در صورت لزوم).

    منطق:
      - اگر چند مدل صریح داده شده (consensus) → دست نزن (همان را برگردان).
      - اگر مدلِ فعلی قوی است (claude/gpt-4o/gemini-pro/...) → احترام بگذار.
      - اگر مدلی نبود یا ضعیف بود (deepseek/haiku/mini/flash) → به بهترین مدلِ
        تحلیلی ارتقا بده و در صورت خاموش‌بودن، موقتاً فعال کن.

    خروجی: (effective_model_id, revert_info). revert_info را باید بعد از اتمام
    اسکن به revert_temp_enables داد (در try/finally).
    """
    # consensus صریح چندمدلی → احترام
    if model_ids and len([m for m in model_ids if m]) > 1:
        return (model_id or model_ids[0]), []

    current = model_id or (model_ids[0] if model_ids else None)
    if current and not any(w in current.lower() for w in _WEAK_SCAN_HINTS):
        # مدلِ قوی صریحاً انتخاب شده → احترام بگذار
        return current, []

    asg = resolve_best_model(ai_manager, "analyst", exclude=[current] if current else None)
    if asg and asg.model_id:
        revert = apply_temp_enables([asg.model_id]) if asg.needs_temp_enable else []
        return asg.model_id, revert
    # چیز بهتری پیدا نشد → همان فعلی
    return current, []


@dataclass
class RoleAssignment:
    role: str
    model_id: Optional[str] = None       # مدل انتخاب‌شده برای این نقش
    status: str = "unavailable"          # "ready" | "needs_enable" | "unavailable"
    needs_temp_enable: bool = False      # آیا برای استفاده باید موقتاً فعال شود


def _provider_of(model_id: str) -> Optional[ModelProvider]:
    m = get_model(model_id)
    if not m:
        return None
    p = m.provider
    if isinstance(p, str):
        try:
            return ModelProvider(p)
        except ValueError:
            return None
    return p


def _provider_has_key(ai_manager, model_id: str) -> bool:
    """آیا provider این مدل کلید/سرویس فعال دارد؟"""
    prov = _provider_of(model_id)
    if prov is None:
        return False
    try:
        return prov in ai_manager._services
    except Exception:
        return False


def resolve_role_assignments(
    ai_manager,
    roles: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
) -> Dict[str, RoleAssignment]:
    """برای هر نقش، بهترین مدل را تعیین می‌کند.

    منطق برای هر نقش (به ترتیب زنجیرهٔ اولویت):
      1. اولین مدلی که در رجیستری است، provider کلید دارد، و در DB فعال است
         → status="ready".
      2. اگر چنین مدلی نبود، اولین مدلی که در رجیستری است و provider کلید دارد
         ولی در DB غیرفعال است → status="needs_enable", needs_temp_enable=True.
      3. اگر هیچ‌کدام → status="unavailable".

    exclude: مدل‌هایی که نباید انتخاب شوند (مثلاً مدلِ orchestrator، تا reviewer
    یک مدل متفاوت باشد — cross-model review).
    """
    roles = roles or list(INSPECTOR_ROLE_MODELS.keys())
    _exclude = set(exclude or [])
    out: Dict[str, RoleAssignment] = {}

    for role in roles:
        chain = INSPECTOR_ROLE_MODELS.get(role, [])
        assignment = RoleAssignment(role=role)
        first_disabled_with_key: Optional[str] = None

        for mid in chain:
            if mid in _exclude:
                continue
            if not get_model(mid):
                continue
            if not _provider_has_key(ai_manager, mid):
                continue
            # کلید دارد — حالا enabled بودن را چک کن
            try:
                enabled = ai_manager.get_enabled_status(mid)
            except Exception:
                enabled = False
            if enabled:
                assignment.model_id = mid
                assignment.status = "ready"
                assignment.needs_temp_enable = False
                break
            elif first_disabled_with_key is None:
                first_disabled_with_key = mid

        if assignment.status != "ready" and first_disabled_with_key:
            assignment.model_id = first_disabled_with_key
            assignment.status = "needs_enable"
            assignment.needs_temp_enable = True

        out[role] = assignment

    return out


def apply_temp_enables(model_ids: List[str]) -> List[Dict]:
    """مدل‌های داده‌شده را در DB موقتاً فعال می‌کند (enabled=1, temporary_enabled=1).

    یک session مستقل (SessionLocal) باز می‌کند تا به lifecycle session درخواست
    (که ممکن است در حین streaming بسته شده باشد) وابسته نباشد.

    یک لیست revert-info برمی‌گرداند که باید بعداً به revert_temp_enables داده شود
    تا دقیقاً به حالت قبل برگردد. در صورت خطا، لیست خالی برمی‌گرداند (no-op).
    """
    if not model_ids:
        return []
    from ..core.database import SessionLocal
    from ..models.ai_profile import ModelSettings

    revert: List[Dict] = []
    db = SessionLocal()
    try:
        for mid in dict.fromkeys(model_ids):  # حذف تکراری با حفظ ترتیب
            row = db.query(ModelSettings).filter(ModelSettings.model_id == mid).first()
            if row:
                # 🛡 (anti-race) اگر مدل از قبل temporary_enabled است، یعنی درخواست
                # همزمانِ دیگری مالکِ فعال‌سازی موقت است → دست نزن و revert هم نکن
                # (تا حالت نهایی توسط همان مالک اصلی بازگردانده شود).
                if int(getattr(row, "temporary_enabled", 0) or 0) == 1:
                    revert.append({"model_id": mid, "existed": True, "skip_revert": True})
                    continue
                revert.append({
                    "model_id": mid,
                    "existed": True,
                    "prev_enabled": int(row.enabled or 0),
                    "prev_temp": int(getattr(row, "temporary_enabled", 0) or 0),
                })
                row.enabled = 1
                row.temporary_enabled = 1
            else:
                revert.append({"model_id": mid, "existed": False})
                db.add(ModelSettings(model_id=mid, enabled=1, temporary_enabled=1))
        db.commit()
        slog.info("temp-enabled models for inspector task", models=list(dict.fromkeys(model_ids)))
        return revert
    except Exception as e:
        slog.warning(f"apply_temp_enables failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        return []
    finally:
        db.close()


def revert_temp_enables(revert_info: List[Dict]) -> None:
    """تغییرات apply_temp_enables را دقیقاً به حالت قبل برمی‌گرداند (session مستقل)."""
    if not revert_info:
        return
    from ..core.database import SessionLocal
    from ..models.ai_profile import ModelSettings

    db = SessionLocal()
    try:
        for info in revert_info:
            mid = info.get("model_id")
            if not mid:
                continue
            # 🛡 (anti-race) مالکیتِ فعال‌سازی موقت با درخواست دیگری بود → revert نکن
            if info.get("skip_revert"):
                continue
            row = db.query(ModelSettings).filter(ModelSettings.model_id == mid).first()
            if not info.get("existed"):
                # ما این row را ساختیم → حذفش کن
                if row:
                    db.delete(row)
            else:
                if row:
                    row.enabled = info.get("prev_enabled", 0)
                    row.temporary_enabled = info.get("prev_temp", 0)
        db.commit()
        slog.info("reverted temp-enabled models", count=len(revert_info))
    except Exception as e:
        slog.warning(f"revert_temp_enables failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
    finally:
        db.close()
