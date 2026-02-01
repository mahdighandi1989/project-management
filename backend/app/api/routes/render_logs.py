# -*- coding: utf-8 -*-
"""
🚀 API Routes برای لاگ‌های Render

امکانات:
- دریافت لیست سرویس‌ها
- دریافت لاگ‌های زنده
- فیلتر و جستجو
- تنظیمات polling
- آرشیو و بازیابی
"""

import json
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from ...core.database import get_db
from ...core.logging_utils import StructuredLogger
from ...services.render_service import get_render_service, reset_render_service
from ...models.render_log import RenderLog, RenderService, RenderLogSettings, RenderLogArchive

slog = StructuredLogger(__name__, "RENDER-API")

router = APIRouter(prefix="/api/render", tags=["Render Logs"])


# =====================================
# Request/Response Models
# =====================================

class LogFilterRequest(BaseModel):
    """فیلتر لاگ‌ها"""
    service_ids: Optional[List[str]] = None
    levels: Optional[List[str]] = None  # info, warn, error, debug
    search: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = 100
    offset: int = 0


class LogSettingsRequest(BaseModel):
    """تنظیمات لاگ"""
    polling_interval_seconds: int = 10
    polling_enabled: bool = True
    retention_hours: int = 48
    archive_enabled: bool = True
    archive_retention_days: int = 30
    default_log_levels: str = "info,warn,error"
    auto_scroll: bool = True


# =====================================
# Services Endpoints
# =====================================

@router.get("/services")
async def get_services(
    refresh: bool = False,
    db: Session = Depends(get_db)
):
    """
    دریافت لیست سرویس‌های Render

    - refresh=True: دریافت مستقیم از API
    - refresh=False: استفاده از cache دیتابیس
    """
    slog.api_request("GET", "/render/services", refresh=refresh)

    if refresh:
        # دریافت از API
        render = get_render_service()
        result = await render.get_services()

        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "خطا در دریافت سرویس‌ها")
            )

        return result

    # دریافت از دیتابیس
    services = db.query(RenderService).order_by(RenderService.name).all()

    return {
        "success": True,
        "services": [
            {
                "id": s.id,
                "name": s.name,
                "type": s.type,
                "region": s.region,
                "status": s.status,
                "auto_fetch_logs": s.auto_fetch_logs,
                "log_retention_hours": s.log_retention_hours
            }
            for s in services
        ],
        "source": "database",
        "last_updated": services[0].updated_at.isoformat() if services else None
    }


@router.post("/services/refresh")
async def refresh_services():
    """
    بروزرسانی لیست سرویس‌ها از Render API
    """
    slog.api_request("POST", "/render/services/refresh")

    render = get_render_service()
    result = await render.get_services()

    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "خطا در بروزرسانی سرویس‌ها")
        )

    return result


@router.patch("/services/{service_id}")
async def update_service_settings(
    service_id: str,
    auto_fetch_logs: Optional[bool] = None,
    log_retention_hours: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    بروزرسانی تنظیمات یک سرویس
    """
    slog.api_request("PATCH", f"/render/services/{service_id}")

    service = db.query(RenderService).filter(RenderService.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="سرویس یافت نشد")

    if auto_fetch_logs is not None:
        service.auto_fetch_logs = auto_fetch_logs
    if log_retention_hours is not None:
        service.log_retention_hours = log_retention_hours

    db.commit()

    return {
        "success": True,
        "service_id": service_id,
        "message": "تنظیمات بروزرسانی شد"
    }


# =====================================
# Logs Endpoints
# =====================================

@router.get("/logs")
async def get_logs(
    service_id: Optional[str] = None,
    service_ids: Optional[List[str]] = Query(None),
    level: Optional[str] = None,
    search: Optional[str] = None,
    minutes: int = 30,
    hours: Optional[int] = None,
    limit: int = 200,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    دریافت لاگ‌ها از دیتابیس

    Args:
        service_id: فیلتر بر اساس سرویس (تک سرویس)
        service_ids: فیلتر بر اساس چند سرویس
        level: فیلتر سطح (info,warn,error,debug)
        search: جستجو در متن
        minutes: لاگ‌های X دقیقه اخیر
        hours: لاگ‌های X ساعت اخیر (اولویت بالاتر)
        limit: تعداد
        offset: صفحه‌بندی
    """
    slog.api_request("GET", "/render/logs",
        service_id=service_id,
        service_ids=service_ids,
        log_level=level,
        minutes=minutes
    )

    # ساخت کوئری
    query = db.query(RenderLog)

    # فیلتر زمانی
    if hours:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
    else:
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    query = query.filter(RenderLog.timestamp >= cutoff)

    # فیلتر سرویس - پشتیبانی از چند سرویس
    if service_ids and len(service_ids) > 0:
        query = query.filter(RenderLog.service_id.in_(service_ids))
    elif service_id:
        query = query.filter(RenderLog.service_id == service_id)

    # فیلتر سطح
    if level:
        levels = level.split(",")
        query = query.filter(RenderLog.level.in_(levels))

    # جستجو
    if search:
        query = query.filter(RenderLog.message.ilike(f"%{search}%"))

    # تعداد کل
    total = query.count()

    # مرتب‌سازی و صفحه‌بندی
    logs = query.order_by(desc(RenderLog.timestamp))\
        .offset(offset)\
        .limit(limit)\
        .all()

    return {
        "success": True,
        "logs": [
            {
                "id": log.id,
                "service_id": log.service_id,
                "service_name": log.service_name,
                "timestamp": log.timestamp.isoformat(),
                "level": log.level,
                "message": log.message,
                "deploy_id": log.deploy_id,
                "instance_id": log.instance_id
            }
            for log in logs
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total
    }


@router.post("/logs/fetch")
async def fetch_new_logs(
    service_id: Optional[str] = None,
    limit: int = 100,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    دریافت لاگ‌های جدید از Render API و ذخیره در دیتابیس

    - اگر service_id داده نشه، همه سرویس‌ها بررسی می‌شن
    """
    slog.api_request("POST", "/render/logs/fetch",
        service_id=service_id,
        limit=limit
    )

    render = get_render_service()
    total_fetched = 0
    total_saved = 0
    errors = []

    # تعیین سرویس‌ها
    if service_id:
        services = db.query(RenderService).filter(
            RenderService.id == service_id
        ).all()
    else:
        services = db.query(RenderService).filter(
            RenderService.auto_fetch_logs == True
        ).all()

    if not services:
        # اگر سرویسی نبود، اول لیست رو بگیر
        result = await render.get_services()
        if result["success"]:
            services = db.query(RenderService).all()
        else:
            return {
                "success": False,
                "error": "هیچ سرویسی یافت نشد. ابتدا لیست سرویس‌ها را بروزرسانی کنید."
            }

    # دریافت لاگ برای هر سرویس
    for service in services:
        try:
            result = await render.get_logs(
                service_id=service.id,
                limit=limit,
                direction="backward"
            )

            if result["success"]:
                total_fetched += len(result["logs"])

                # ذخیره در دیتابیس
                saved = await render.save_logs_to_db(
                    result["logs"],
                    service_name=service.name
                )
                total_saved += saved

            else:
                errors.append({
                    "service_id": service.id,
                    "service_name": service.name,
                    "error": result.get("error")
                })

        except Exception as e:
            errors.append({
                "service_id": service.id,
                "service_name": service.name,
                "error": str(e)
            })

    slog.success("Logs fetched",
        total_fetched=total_fetched,
        total_saved=total_saved,
        errors_count=len(errors)
    )

    return {
        "success": True,
        "fetched": total_fetched,
        "saved": total_saved,
        "services_checked": len(services),
        "errors": errors if errors else None
    }


@router.get("/logs/live")
async def get_live_logs(
    service_id: Optional[str] = None,
    since_id: Optional[str] = None,
    since_timestamp: Optional[str] = None,
    levels: str = "info,warn,error",
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    دریافت لاگ‌های جدید (برای polling)

    Args:
        since_id: لاگ‌های بعد از این ID
        since_timestamp: لاگ‌های بعد از این زمان
        levels: سطوح لاگ
        limit: حداکثر تعداد
    """
    query = db.query(RenderLog)

    # فیلتر سرویس
    if service_id:
        query = query.filter(RenderLog.service_id == service_id)

    # فیلتر زمانی
    if since_timestamp:
        try:
            ts = datetime.fromisoformat(since_timestamp.replace("Z", "+00:00"))
            query = query.filter(RenderLog.timestamp > ts)
        except:
            pass

    # فیلتر سطح
    if levels:
        level_list = levels.split(",")
        query = query.filter(RenderLog.level.in_(level_list))

    # مرتب‌سازی و محدود کردن
    logs = query.order_by(desc(RenderLog.timestamp)).limit(limit).all()

    # معکوس کردن برای ترتیب زمانی
    logs = list(reversed(logs))

    return {
        "success": True,
        "logs": [
            {
                "id": log.id,
                "service_id": log.service_id,
                "service_name": log.service_name,
                "timestamp": log.timestamp.isoformat(),
                "level": log.level,
                "message": log.message,
                "deploy_id": log.deploy_id
            }
            for log in logs
        ],
        "latest_timestamp": logs[-1].timestamp.isoformat() if logs else None,
        "count": len(logs)
    }


@router.post("/logs/search")
async def search_logs(
    request: LogFilterRequest,
    db: Session = Depends(get_db)
):
    """
    جستجوی پیشرفته در لاگ‌ها
    """
    slog.api_request("POST", "/render/logs/search",
        search=request.search,
        levels=request.levels
    )

    query = db.query(RenderLog)

    # فیلتر سرویس‌ها
    if request.service_ids:
        query = query.filter(RenderLog.service_id.in_(request.service_ids))

    # فیلتر سطح
    if request.levels:
        query = query.filter(RenderLog.level.in_(request.levels))

    # فیلتر زمانی
    if request.start_time:
        query = query.filter(RenderLog.timestamp >= request.start_time)
    if request.end_time:
        query = query.filter(RenderLog.timestamp <= request.end_time)

    # جستجوی متنی
    if request.search:
        query = query.filter(RenderLog.message.ilike(f"%{request.search}%"))

    # شمارش
    total = query.count()

    # نتایج
    logs = query.order_by(desc(RenderLog.timestamp))\
        .offset(request.offset)\
        .limit(request.limit)\
        .all()

    return {
        "success": True,
        "logs": [
            {
                "id": log.id,
                "service_id": log.service_id,
                "service_name": log.service_name,
                "timestamp": log.timestamp.isoformat(),
                "level": log.level,
                "message": log.message,
                "deploy_id": log.deploy_id
            }
            for log in logs
        ],
        "total": total,
        "has_more": request.offset + request.limit < total
    }


# =====================================
# Settings Endpoints
# =====================================

@router.get("/settings")
async def get_log_settings(db: Session = Depends(get_db)):
    """دریافت تنظیمات لاگ"""
    settings = db.query(RenderLogSettings).first()

    if not settings:
        # ایجاد تنظیمات پیش‌فرض
        settings = RenderLogSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return {
        "success": True,
        "settings": {
            "polling_interval_seconds": settings.polling_interval_seconds,
            "polling_enabled": settings.polling_enabled,
            "retention_hours": settings.retention_hours,
            "archive_enabled": settings.archive_enabled,
            "archive_retention_days": settings.archive_retention_days,
            "default_log_levels": settings.default_log_levels,
            "auto_scroll": settings.auto_scroll
        }
    }


@router.put("/settings")
async def update_log_settings(
    request: LogSettingsRequest,
    db: Session = Depends(get_db)
):
    """بروزرسانی تنظیمات لاگ"""
    slog.api_request("PUT", "/render/settings")

    settings = db.query(RenderLogSettings).first()
    if not settings:
        settings = RenderLogSettings()
        db.add(settings)

    settings.polling_interval_seconds = request.polling_interval_seconds
    settings.polling_enabled = request.polling_enabled
    settings.retention_hours = request.retention_hours
    settings.archive_enabled = request.archive_enabled
    settings.archive_retention_days = request.archive_retention_days
    settings.default_log_levels = request.default_log_levels
    settings.auto_scroll = request.auto_scroll

    db.commit()

    slog.success("Log settings updated",
        polling_interval=request.polling_interval_seconds,
        retention_hours=request.retention_hours
    )

    return {
        "success": True,
        "message": "تنظیمات ذخیره شد"
    }


# =====================================
# Download Endpoint
# =====================================

from fastapi.responses import Response
import csv
import io

@router.get("/logs/download")
async def download_logs(
    service_ids: Optional[List[str]] = Query(None),
    hours: Optional[int] = None,
    limit: Optional[int] = None,
    level: Optional[str] = None,
    after_deploy: bool = False,
    format: str = "json",
    db: Session = Depends(get_db)
):
    """
    دانلود لاگ‌ها با فیلترهای مختلف

    Args:
        service_ids: لیست سرویس‌ها
        hours: بازه زمانی (ساعت)
        limit: تعداد لاگ
        level: سطح لاگ (error, warn, info)
        after_deploy: فقط لاگ‌های بعد از آخرین دیپلوی
        format: فرمت خروجی (json, txt, csv)
    """
    slog.api_request("GET", "/render/logs/download",
        service_ids=service_ids,
        hours=hours,
        limit=limit,
        level=level,
        format=format
    )

    query = db.query(RenderLog)

    # فیلتر سرویس
    if service_ids and len(service_ids) > 0:
        query = query.filter(RenderLog.service_id.in_(service_ids))

    # فیلتر زمانی
    if hours:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        query = query.filter(RenderLog.timestamp >= cutoff)

    # فیلتر سطح
    if level:
        if level == "error":
            query = query.filter(RenderLog.level == "error")
        elif level == "warn":
            query = query.filter(RenderLog.level.in_(["error", "warn"]))

    # فیلتر بعد از آخرین دیپلوی
    if after_deploy:
        # پیدا کردن آخرین دیپلوی موفق
        last_deploy = db.query(RenderLog).filter(
            RenderLog.message.ilike("%deploy%success%")
        ).order_by(desc(RenderLog.timestamp)).first()
        if last_deploy:
            query = query.filter(RenderLog.timestamp >= last_deploy.timestamp)

    # مرتب‌سازی
    query = query.order_by(RenderLog.timestamp)

    # محدود کردن تعداد
    if limit:
        query = query.limit(limit)
    else:
        query = query.limit(10000)  # حداکثر 10000 لاگ

    logs = query.all()

    # تبدیل به فرمت مناسب
    if format == "json":
        import json
        content = json.dumps([
            {
                "timestamp": log.timestamp.isoformat(),
                "level": log.level,
                "service": log.service_name or log.service_id,
                "message": log.message,
                "deploy_id": log.deploy_id
            }
            for log in logs
        ], ensure_ascii=False, indent=2)
        media_type = "application/json"

    elif format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["timestamp", "level", "service", "message", "deploy_id"])
        for log in logs:
            writer.writerow([
                log.timestamp.isoformat(),
                log.level,
                log.service_name or log.service_id,
                log.message,
                log.deploy_id or ""
            ])
        content = output.getvalue()
        media_type = "text/csv"

    else:  # txt
        lines = []
        for log in logs:
            ts = log.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            lines.append(f"[{ts}] [{log.level.upper()}] [{log.service_name or log.service_id}] {log.message}")
        content = "\n".join(lines)
        media_type = "text/plain"

    return Response(
        content=content.encode("utf-8"),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="render-logs.{format}"'
        }
    )


# =====================================
# Cleanup & Archive Endpoints
# =====================================

@router.post("/cleanup")
async def cleanup_old_logs(
    retention_hours: int = 48,
    db: Session = Depends(get_db)
):
    """
    پاکسازی لاگ‌های قدیمی و آرشیو
    """
    slog.api_request("POST", "/render/cleanup",
        retention_hours=retention_hours
    )

    render = get_render_service()
    result = await render.cleanup_old_logs(retention_hours)

    return {
        "success": True,
        "archived": result.get("archived", 0),
        "deleted": result.get("deleted", 0),
        "message": f"{result.get('deleted', 0)} لاگ حذف و {result.get('archived', 0)} آرشیو شد"
    }


@router.get("/archives")
async def get_archives(
    service_id: Optional[str] = None,
    service_ids: Optional[List[str]] = Query(None),
    db: Session = Depends(get_db)
):
    """دریافت لیست آرشیوها"""
    query = db.query(RenderLogArchive)

    # پشتیبانی از چند سرویس
    if service_ids and len(service_ids) > 0:
        query = query.filter(RenderLogArchive.service_id.in_(service_ids))
    elif service_id:
        query = query.filter(RenderLogArchive.service_id == service_id)

    archives = query.order_by(desc(RenderLogArchive.archived_at)).limit(100).all()

    return {
        "success": True,
        "archives": [
            {
                "id": a.id,
                "service_id": a.service_id,
                "start_time": a.start_time.isoformat(),
                "end_time": a.end_time.isoformat(),
                "logs_count": a.logs_count,
                "size_bytes": a.size_bytes,
                "archived_at": a.archived_at.isoformat()
            }
            for a in archives
        ]
    }


@router.get("/archives/{archive_id}")
async def get_archive_content(
    archive_id: int,
    db: Session = Depends(get_db)
):
    """دریافت محتوای یک آرشیو"""
    archive = db.query(RenderLogArchive).filter(
        RenderLogArchive.id == archive_id
    ).first()

    if not archive:
        raise HTTPException(status_code=404, detail="آرشیو یافت نشد")

    render = get_render_service()
    logs = await render.get_archived_logs(
        service_id=archive.service_id,
        start_time=archive.start_time,
        end_time=archive.end_time
    )

    return {
        "success": True,
        "archive_id": archive_id,
        "service_id": archive.service_id,
        "start_time": archive.start_time.isoformat(),
        "end_time": archive.end_time.isoformat(),
        "logs": logs
    }


# =====================================
# Log to Issues Transfer
# =====================================

from ...services.log_to_issues_service import get_log_to_issues_service

@router.post("/transfer-errors")
async def transfer_errors_to_issues(
    service_ids: Optional[List[str]] = Query(None),
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """
    انتقال لاگ‌های خطا به تب ایرادات پروژه‌ها

    - فقط پروژه‌های ایمپورت شده
    - تحلیل AI برای توضیح خطا
    - جستجوی ایرادات مشابه و ادغام
    """
    slog.api_request("POST", "/render/transfer-errors",
        service_ids=service_ids,
        hours=hours
    )

    service = get_log_to_issues_service()
    result = await service.transfer_error_logs(
        service_ids=service_ids,
        hours=hours,
        auto_mode=False,
        db=db
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "خطا در انتقال لاگ‌ها")
        )

    return result


@router.get("/transfer-status")
async def get_transfer_status(
    db: Session = Depends(get_db)
):
    """
    وضعیت انتقال لاگ‌های خطا

    - تعداد لاگ‌های منتقل شده
    - تعداد لاگ‌های در انتظار
    """
    # لاگ‌های خطای منتقل نشده
    pending_count = db.query(RenderLog).filter(
        RenderLog.level.in_(["error", "fatal", "critical"]),
        RenderLog.transferred_to_issues == False
    ).count()

    # لاگ‌های منتقل شده
    transferred_count = db.query(RenderLog).filter(
        RenderLog.transferred_to_issues == True
    ).count()

    return {
        "success": True,
        "pending_errors": pending_count,
        "transferred_errors": transferred_count,
        "can_transfer": pending_count > 0
    }


# =====================================
# Stats Endpoints
# =====================================

@router.get("/stats")
async def get_log_stats(
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """آمار لاگ‌ها"""
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    # تعداد کل
    total = db.query(RenderLog).filter(RenderLog.timestamp >= cutoff).count()

    # تعداد بر اساس سطح
    from sqlalchemy import func
    level_counts = db.query(
        RenderLog.level,
        func.count(RenderLog.id)
    ).filter(
        RenderLog.timestamp >= cutoff
    ).group_by(RenderLog.level).all()

    # تعداد بر اساس سرویس
    service_counts = db.query(
        RenderLog.service_id,
        RenderLog.service_name,
        func.count(RenderLog.id)
    ).filter(
        RenderLog.timestamp >= cutoff
    ).group_by(RenderLog.service_id, RenderLog.service_name).all()

    return {
        "success": True,
        "period_hours": hours,
        "total_logs": total,
        "by_level": {level: count for level, count in level_counts},
        "by_service": [
            {"service_id": sid, "service_name": sname, "count": count}
            for sid, sname, count in service_counts
        ],
        "error_count": next((c for l, c in level_counts if l == "error"), 0),
        "warning_count": next((c for l, c in level_counts if l == "warn"), 0)
    }
