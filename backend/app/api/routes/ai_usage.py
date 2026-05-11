"""AI Usage tracking API.

Endpoints (همه prefix=/api/ai-usage):

GET  /stats?days=30              آمار کلی مصرف per provider/model
GET  /timeseries?days=7&granularity=day   نمودار مصرف در زمان
GET  /recent?limit=50            لیست لاگ‌های اخیر
GET  /leaks?days=7               تشخیص نشتی (مصرف بدون خروجی مفید)
GET  /by-model?days=30           breakdown per model
GET  /summary                    خلاصهٔ کلی (برای داشبورد)
GET  /balances                   موجودی همهٔ providers (DeepSeek API + manual budgets)
POST /balances/refresh           force refresh + alert check
POST /balances/{provider}/budget تنظیم/به‌روزرسانی budget دستی
POST /balances/{provider}/threshold  تنظیم آستانهٔ alert
DELETE /balances/{provider}      حذف budget یک provider

تمام داده‌ها از جدول ai_logs (که Tile 1 پر می‌کند) می‌آیند.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, case

from ...core.database import get_db
from ...models.ai_log import AILog

router = APIRouter(prefix="/ai-usage", tags=["ai-usage"])


# ============================================================
# /stats — آمار کلی per provider
# ============================================================

@router.get("/stats")
async def get_stats(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """آمار aggregated مصرف per provider در N روز اخیر."""
    since = datetime.utcnow() - timedelta(days=days)
    rows = db.query(
        AILog.provider,
        func.count(AILog.id).label("request_count"),
        func.sum(AILog.input_tokens).label("input_tokens"),
        func.sum(AILog.output_tokens).label("output_tokens"),
        func.sum(AILog.total_tokens).label("total_tokens"),
        func.sum(AILog.cost).label("total_cost"),
        func.avg(AILog.latency_ms).label("avg_latency"),
        func.sum(
            case((AILog.status == "error", 1), else_=0)  # SQLAlchemy portable
        ).label("error_count"),
    ).filter(AILog.created_at >= since).group_by(AILog.provider).all()

    providers: List[Dict[str, Any]] = []
    grand_total_tokens = 0
    grand_total_cost = 0.0
    grand_request_count = 0
    for r in rows:
        total = int(r.total_tokens or 0)
        cost = float(r.total_cost or 0)
        rc = int(r.request_count or 0)
        ec = int(r.error_count or 0)
        providers.append({
            "provider": r.provider,
            "request_count": rc,
            "input_tokens": int(r.input_tokens or 0),
            "output_tokens": int(r.output_tokens or 0),
            "total_tokens": total,
            "total_cost_usd": round(cost, 6),
            "avg_latency_ms": round(float(r.avg_latency or 0), 1),
            "error_count": ec,
            "error_rate": round(ec / rc, 4) if rc > 0 else 0,
        })
        grand_total_tokens += total
        grand_total_cost += cost
        grand_request_count += rc

    providers.sort(key=lambda x: -x["total_tokens"])
    return {
        "days": days,
        "since": since.isoformat(),
        "providers": providers,
        "totals": {
            "request_count": grand_request_count,
            "total_tokens": grand_total_tokens,
            "total_cost_usd": round(grand_total_cost, 4),
        },
    }


# ============================================================
# /timeseries — نمودار مصرف در زمان
# ============================================================

@router.get("/timeseries")
async def get_timeseries(
    days: int = Query(7, ge=1, le=90),
    granularity: str = Query("day", regex="^(hour|day)$"),
    provider: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """مصرف per granularity (day یا hour) برای نمودار."""
    since = datetime.utcnow() - timedelta(days=days)
    fmt = "%Y-%m-%d" if granularity == "day" else "%Y-%m-%d %H:00"
    # SQLite strftime
    date_expr = func.strftime(fmt, AILog.created_at).label("bucket")
    q = db.query(
        date_expr,
        func.sum(AILog.total_tokens).label("tokens"),
        func.sum(AILog.cost).label("cost"),
        func.count(AILog.id).label("count"),
    ).filter(AILog.created_at >= since)
    if provider:
        q = q.filter(AILog.provider == provider)
    rows = q.group_by(date_expr).order_by(date_expr).all()
    return {
        "days": days,
        "granularity": granularity,
        "provider": provider,
        "points": [
            {
                "bucket": r.bucket,
                "tokens": int(r.tokens or 0),
                "cost_usd": round(float(r.cost or 0), 6),
                "count": int(r.count or 0),
            }
            for r in rows
        ],
    }


# ============================================================
# /recent — لاگ‌های اخیر
# ============================================================

@router.get("/recent")
async def get_recent(
    limit: int = Query(50, ge=1, le=500),
    provider: Optional[str] = None,
    model: Optional[str] = None,
    status: Optional[str] = None,
    project_id: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """لیست N لاگ اخیر با فیلتر."""
    q = db.query(AILog)
    if provider:
        q = q.filter(AILog.provider == provider)
    if model:
        q = q.filter(AILog.model == model)
    if status:
        q = q.filter(AILog.status == status)
    if project_id:
        q = q.filter(AILog.project_id == project_id)
    rows = q.order_by(desc(AILog.created_at)).limit(limit).all()
    return {
        "count": len(rows),
        "items": [r.to_dict() for r in rows],
    }


# ============================================================
# /leaks — تشخیص نشتی
# ============================================================

@router.get("/leaks")
async def get_leaks(
    days: int = Query(7, ge=1, le=30),
    min_tokens: int = Query(1000, ge=100),
    max_output_ratio: float = Query(0.1, gt=0, le=1.0),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """تشخیص نشتی: درخواست‌هایی با مصرف زیاد ولی خروجی کم.

    تعریف نشتی:
      - total_tokens >= min_tokens (پیش‌فرض 1000)
      - output_tokens / total_tokens <= max_output_ratio (پیش‌فرض 10%)
        یعنی بیشتر مصرف برای input بوده ولی خروجی کم/خالی است
      - یا status='error' با مصرف توکن > 0 (شکست در میان فرآیند)

    این نشانگر: prompt های خیلی طولانی، context window اشباع شده،
    یا response truncate شده.
    """
    since = datetime.utcnow() - timedelta(days=days)
    # حالت ۱: input سنگین، output کم
    # فیلتر در SQL تا حد امکان: output * 1000 <= total * (ratio * 1000)
    # multiplication برای جلوگیری از float precision در SQLite
    ratio_int = max(1, int(max_output_ratio * 1000))
    leaks_query = db.query(AILog).filter(
        AILog.created_at >= since,
        AILog.total_tokens >= min_tokens,
        AILog.status != "error",
        (AILog.output_tokens * 1000) <= (AILog.total_tokens * ratio_int),
    ).order_by(desc(AILog.total_tokens)).limit(200).all()
    leaks: List[Dict[str, Any]] = []
    for log in leaks_query:
        total = log.total_tokens or 0
        out = log.output_tokens or 0
        ratio = (out / total) if total > 0 else 0
        if True:  # filter already applied in SQL
            leaks.append({
                "id": log.id,
                "provider": log.provider,
                "model": log.model,
                "input_tokens": log.input_tokens or 0,
                "output_tokens": out,
                "total_tokens": total,
                "output_ratio": round(ratio, 4),
                "cost_usd": round(float(log.cost or 0), 6),
                "latency_ms": log.latency_ms or 0,
                "created_at": log.created_at.isoformat() if log.created_at else None,
                "leak_reason": "low_output_ratio",
                "prompt_preview": (log.prompt or "")[:200],
            })

    # حالت ۲: error با مصرف توکن > 0
    error_query = db.query(AILog).filter(
        AILog.created_at >= since,
        AILog.status == "error",
        AILog.total_tokens > 0,
    ).all()
    for log in error_query:
        leaks.append({
            "id": log.id,
            "provider": log.provider,
            "model": log.model,
            "input_tokens": log.input_tokens or 0,
            "output_tokens": log.output_tokens or 0,
            "total_tokens": log.total_tokens or 0,
            "output_ratio": 0,
            "cost_usd": round(float(log.cost or 0), 6),
            "latency_ms": log.latency_ms or 0,
            "created_at": log.created_at.isoformat() if log.created_at else None,
            "leak_reason": "error_with_consumption",
            "error_message": (log.error_message or "")[:200],
            "prompt_preview": (log.prompt or "")[:200],
        })

    # مرتب‌سازی: بدترین (بیشترین token wasted) اول
    leaks.sort(key=lambda l: -l["total_tokens"])

    total_wasted_tokens = sum(l["total_tokens"] - l["output_tokens"] for l in leaks)
    total_wasted_cost = sum(l["cost_usd"] for l in leaks)
    return {
        "days": days,
        "config": {
            "min_tokens": min_tokens,
            "max_output_ratio": max_output_ratio,
        },
        "leaks_count": len(leaks),
        "total_wasted_tokens_est": total_wasted_tokens,
        "total_wasted_cost_usd_est": round(total_wasted_cost, 4),
        "leaks": leaks[:100],  # cap به ۱۰۰ تا
    }


# ============================================================
# /by-model — breakdown per model
# ============================================================

@router.get("/by-model")
async def get_by_model(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """breakdown مصرف per model_id."""
    since = datetime.utcnow() - timedelta(days=days)
    rows = db.query(
        AILog.provider,
        AILog.model,
        func.count(AILog.id).label("request_count"),
        func.sum(AILog.total_tokens).label("total_tokens"),
        func.sum(AILog.cost).label("total_cost"),
        func.avg(AILog.latency_ms).label("avg_latency"),
    ).filter(AILog.created_at >= since).group_by(AILog.provider, AILog.model).all()

    models = [
        {
            "provider": r.provider,
            "model": r.model,
            "request_count": int(r.request_count or 0),
            "total_tokens": int(r.total_tokens or 0),
            "total_cost_usd": round(float(r.total_cost or 0), 6),
            "avg_latency_ms": round(float(r.avg_latency or 0), 1),
        }
        for r in rows
    ]
    models.sort(key=lambda x: -x["total_tokens"])
    return {
        "days": days,
        "models": models,
    }


# ============================================================
# /summary — خلاصه برای dashboard widget
# ============================================================

@router.get("/summary")
async def get_summary(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """خلاصهٔ کلی برای widget داشبورد."""
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    last_7d = now - timedelta(days=7)
    last_30d = now - timedelta(days=30)

    def _aggregate(since: datetime) -> Dict[str, Any]:
        row = db.query(
            func.count(AILog.id).label("count"),
            func.sum(AILog.total_tokens).label("tokens"),
            func.sum(AILog.cost).label("cost"),
        ).filter(AILog.created_at >= since).first()
        return {
            "count": int(row.count or 0) if row else 0,
            "tokens": int(row.tokens or 0) if row else 0,
            "cost_usd": round(float(row.cost or 0), 4) if row else 0.0,
        }

    today_stats = _aggregate(today)
    last_7d_stats = _aggregate(last_7d)
    last_30d_stats = _aggregate(last_30d)

    # آخرین فعالیت
    latest = db.query(AILog).order_by(desc(AILog.created_at)).first()
    last_request_at = latest.created_at.isoformat() if latest and latest.created_at else None

    # تعداد providerهای فعال
    distinct_providers = db.query(AILog.provider).filter(
        AILog.created_at >= last_30d
    ).distinct().count()

    return {
        "today": today_stats,
        "last_7d": last_7d_stats,
        "last_30d": last_30d_stats,
        "last_request_at": last_request_at,
        "distinct_providers_30d": distinct_providers,
    }


# ============================================================
# Balance endpoints (Tile 3)
# ============================================================

from pydantic import BaseModel


class BudgetRequest(BaseModel):
    budget_usd: float
    alert_threshold_usd: Optional[float] = None
    reset_at: Optional[str] = None  # ISO datetime — اگر None، الان


class ThresholdRequest(BaseModel):
    threshold_usd: float


@router.get("/balances")
async def get_balances() -> Dict[str, Any]:
    """موجودی همهٔ providers (state ذخیره‌شده).

    برای refresh و call API، از POST /balances/refresh استفاده کنید.
    """
    from ...services.ai_balance_service import AIBalanceService, PROVIDERS_WITH_REMOTE_API
    state = AIBalanceService.get_all_balances()
    # ضمیمهٔ metadata: کدام provider ها API دارند، کدام نیاز به manual
    return {
        "balances": state,
        "providers_with_remote_api": list(PROVIDERS_WITH_REMOTE_API),
        "manual_only_providers": ["openai", "claude", "anthropic", "gemini", "google", "perplexity"],
    }


@router.post("/balances/refresh")
async def refresh_balances() -> Dict[str, Any]:
    """Force refresh — DeepSeek API + محاسبهٔ remaining برای manual budgets.

    اگر balance < threshold باشد، event ai_balance_low فاير می‌شود (با dedup 24h).
    """
    from ...services.ai_balance_service import AIBalanceService
    return await AIBalanceService.check_and_notify()


@router.post("/balances/{provider}/budget")
async def set_budget(provider: str, payload: BudgetRequest) -> Dict[str, Any]:
    """تنظیم budget دستی برای provider (همه به‌جز DeepSeek که API دارد)."""
    from ...services.ai_balance_service import AIBalanceService
    if payload.budget_usd < 0:
        raise HTTPException(status_code=400, detail="budget_usd باید مثبت باشد")
    result = AIBalanceService.set_manual_budget(
        provider=provider.lower().strip(),
        budget_usd=payload.budget_usd,
        reset_at=payload.reset_at,
        alert_threshold_usd=payload.alert_threshold_usd,
    )
    return {"ok": True, "provider": provider, "state": result}


@router.post("/balances/{provider}/threshold")
async def set_threshold(provider: str, payload: ThresholdRequest) -> Dict[str, Any]:
    """فقط آستانهٔ alert را تنظیم می‌کند (بدون تغییر budget)."""
    from ...services.ai_balance_service import AIBalanceService
    if payload.threshold_usd < 0:
        raise HTTPException(status_code=400, detail="threshold_usd باید مثبت باشد")
    result = AIBalanceService.set_threshold(provider.lower().strip(), payload.threshold_usd)
    return {"ok": True, "provider": provider, "state": result}


@router.delete("/balances/{provider}")
async def delete_balance(provider: str) -> Dict[str, Any]:
    """حذف budget یک provider."""
    from ...services.ai_balance_service import AIBalanceService
    ok = AIBalanceService.remove_provider(provider.lower().strip())
    return {"ok": ok, "provider": provider}
