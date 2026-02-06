# -*- coding: utf-8 -*-
"""
🚀 API Routes برای لاگ‌های Render

امکانات:
- دریافت لیست سرویس‌ها
- دریافت لاگ‌های زنده
- فیلتر و جستجو
- تنظیمات polling
- آرشیو و بازیابی
- WebSocket برای streaming واقعی
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks, WebSocket, WebSocketDisconnect
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
    # تنظیمات انتقال خودکار
    auto_transfer_enabled: bool = False
    auto_transfer_interval_minutes: int = 30
    auto_transfer_hours_back: int = 24  # فقط در حالت time_based استفاده می‌شود
    # حالت‌های انتقال:
    # - since_deploy: خطاهای بعد از آخرین دیپلوی (با اینتروال)
    # - time_based: خطاهای X ساعت اخیر (با اینتروال)
    # - realtime: هر خطا فوراً منتقل شود (بدون اینتروال)
    auto_transfer_mode: str = "since_deploy"


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
    try:
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
                    "auto_fetch_logs": getattr(s, 'auto_fetch_logs', True),
                    "log_retention_hours": getattr(s, 'log_retention_hours', 48),
                    "last_deploy_id": getattr(s, 'last_deploy_id', None),
                    "last_transferred_deploy_id": getattr(s, 'last_transferred_deploy_id', None)
                }
                for s in services
            ],
            "source": "database",
            "last_updated": services[0].updated_at.isoformat() if services and hasattr(services[0], 'updated_at') and services[0].updated_at else None
        }
    except Exception as e:
        slog.error("Error fetching services from database (ORM)", exception=e)
        # Fallback: استفاده از raw SQL برای ستون‌های پایه
        try:
            from sqlalchemy import text
            result = db.execute(text("SELECT id, name, type, region, status FROM render_services ORDER BY name"))
            rows = result.fetchall()
            return {
                "success": True,
                "services": [
                    {
                        "id": row[0],
                        "name": row[1],
                        "type": row[2],
                        "region": row[3],
                        "status": row[4],
                        "auto_fetch_logs": True,
                        "log_retention_hours": 48,
                        "last_deploy_id": None,
                        "last_transferred_deploy_id": None
                    }
                    for row in rows
                ],
                "source": "database_raw",
                "last_updated": None
            }
        except Exception as e2:
            slog.error("Error fetching services from database (raw SQL)", exception=e2)
            return {
                "success": False,
                "services": [],
                "error": str(e)
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
    project_id: Optional[str] = None,  # 🆕 نگاشت به پروژه
    db: Session = Depends(get_db)
):
    """
    بروزرسانی تنظیمات یک سرویس

    Args:
        project_id: ID پروژه برای نگاشت (یا null برای حذف نگاشت)
    """
    slog.api_request("PATCH", f"/render/services/{service_id}")

    service = db.query(RenderService).filter(RenderService.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="سرویس یافت نشد")

    if auto_fetch_logs is not None:
        service.auto_fetch_logs = auto_fetch_logs
    if log_retention_hours is not None:
        service.log_retention_hours = log_retention_hours

    # 🆕 بروزرسانی نگاشت به پروژه
    if project_id is not None:
        if project_id == "" or project_id == "null":
            service.project_id = None
            slog.info(f"Removed project mapping for service {service_id}")
        else:
            # بررسی وجود پروژه
            from ...models.project import Project
            project = db.query(Project).filter(Project.id == project_id).first()
            if project:
                service.project_id = project_id
                slog.info(f"Mapped service {service_id} to project {project.name}")
            else:
                raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    db.commit()

    return {
        "success": True,
        "service_id": service_id,
        "project_id": service.project_id,
        "message": "تنظیمات بروزرسانی شد"
    }


@router.get("/services/mappings")
async def get_service_project_mappings(
    db: Session = Depends(get_db)
):
    """
    دریافت وضعیت نگاشت سرویس‌ها به پروژه‌ها

    شامل:
    - سرویس‌های نگاشت شده (دستی و خودکار)
    - سرویس‌های بدون نگاشت
    - لیست پروژه‌ها برای انتخاب
    """
    from ...models.project import Project

    services = db.query(RenderService).all()
    projects = db.query(Project).all()

    mappings = []
    unmapped = []

    projects_dict = {p.id: p for p in projects}

    for service in services:
        service_info = {
            "service_id": service.id,
            "service_name": service.name,
            "service_type": service.type,
            "project_id": service.project_id,
            "project_name": None,
            "mapping_type": None
        }

        if service.project_id and service.project_id in projects_dict:
            project = projects_dict[service.project_id]
            service_info["project_name"] = project.name
            service_info["mapping_type"] = "manual"
            mappings.append(service_info)
        else:
            # تلاش برای یافتن خودکار
            search_term = service.name.split('-')[0]
            auto_project = db.query(Project).filter(
                Project.name.ilike(f"%{search_term}%")
            ).first()

            if auto_project:
                service_info["project_id"] = auto_project.id
                service_info["project_name"] = auto_project.name
                service_info["mapping_type"] = "auto"
                mappings.append(service_info)
            else:
                unmapped.append(service_info)

    return {
        "success": True,
        "mapped": mappings,
        "unmapped": unmapped,
        "total_services": len(services),
        "total_mapped": len(mappings),
        "total_unmapped": len(unmapped),
        "projects": [{"id": p.id, "name": p.name} for p in projects]
    }


@router.get("/services/by-project/{project_id}")
async def get_services_by_project(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    دریافت سرویس‌های مرتبط با یک پروژه خاص

    این endpoint برای تب بازرس ویژه استفاده می‌شود تا سرویس‌های
    یک پروژه را برای نمایش لاگ‌ها و پیش‌نمایش لود کند.

    Returns:
        - services: لیست سرویس‌ها با URL و نوع
        - frontend_url: URL فرانت‌اند برای نمایش در iframe
        - backend_services: لیست سرویس‌های بک‌اند برای نمایش لاگ
    """
    slog.api_request("GET", f"/render/services/by-project/{project_id}")

    # 1. سرویس‌های نگاشت شده به این پروژه
    services = db.query(RenderService).filter(
        RenderService.project_id == project_id
    ).all()

    # 2. اگر نگاشت دستی نداشت، جستجوی خودکار
    if not services:
        from ...models.project import Project
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            # جستجو بر اساس نام پروژه
            search_term = project.name.lower().replace(" ", "-").replace("_", "-")
            all_services = db.query(RenderService).all()
            services = [
                s for s in all_services
                if search_term in s.name.lower() or s.name.lower() in search_term
            ]

    if not services:
        return {
            "success": True,
            "services": [],
            "frontend_url": None,
            "backend_services": [],
            "message": "هیچ سرویسی برای این پروژه یافت نشد. از صفحه تنظیمات Render Logs سرویس‌ها را به این پروژه نگاشت کنید."
        }

    # 3. دسته‌بندی سرویس‌ها
    frontend_url = None
    backend_services = []
    all_web_services = []  # همه سرویس‌های وب برای fallback

    def get_service_url(s):
        """استخراج URL سرویس - اول از دیتابیس، بعد fallback به ساخت از نام"""
        # 🆕 اول از URL ذخیره شده استفاده کن
        if hasattr(s, 'service_url') and s.service_url:
            return s.service_url
        # Fallback: ساخت از نام (برای رکوردهای قدیمی)
        if s.type in ["web_service", "static_site"]:
            slug = s.name.lower().replace(" ", "-").replace("_", "-")
            return f"https://{slug}.onrender.com"
        return None

    for s in services:
        service_url = get_service_url(s)
        service_info = {
            "id": s.id,
            "name": s.name,
            "type": s.type,
            "status": s.status,
            "url": service_url,
            "dashboard_url": f"https://dashboard.render.com/web/{s.id}"
        }

        # ذخیره همه web_service ها
        if s.type in ["web_service", "static_site"]:
            all_web_services.append(service_info)

        # تشخیص فرانت‌اند vs بک‌اند
        name_lower = s.name.lower()
        is_frontend_like = any(x in name_lower for x in ["frontend", "front", "client", "ui", "static"])
        is_backend_like = any(x in name_lower for x in ["backend", "back", "api", "server"])

        if is_frontend_like and not is_backend_like:
            # فقط فرانت‌اند
            if not frontend_url and service_url:
                frontend_url = service_url
            service_info["role"] = "frontend"
        elif is_backend_like and not is_frontend_like:
            # فقط بک‌اند
            service_info["role"] = "backend"
            backend_services.append(service_info)
        else:
            # یکپارچه (هم فرانت هم بک) یا نامشخص
            # برای لاگ‌ها به عنوان بک‌اند استفاده کن
            service_info["role"] = "unified"
            backend_services.append(service_info)
            # برای پیش‌نمایش هم استفاده کن (اگر فرانت جدا نداریم)
            if not frontend_url and service_url:
                frontend_url = service_url

    # اگر فرانت‌اند پیدا نشد، اولین web_service را انتخاب کن
    if not frontend_url and all_web_services:
        frontend_url = all_web_services[0]["url"]
        # اگر این سرویس در backend_services نیست، اضافه کن
        first_web_id = all_web_services[0]["id"]
        if not any(bs["id"] == first_web_id for bs in backend_services):
            backend_services.append(all_web_services[0])

    return {
        "success": True,
        "services": [
            {
                "id": s.id,
                "name": s.name,
                "type": s.type,
                "status": s.status,
                "url": get_service_url(s),
                "role": next((bs["role"] for bs in backend_services if bs["id"] == s.id), "frontend")
            }
            for s in services
        ],
        "frontend_url": frontend_url,
        "backend_services": backend_services,
        "total": len(services)
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

    try:
        render = get_render_service()
        total_fetched = 0
        total_saved = 0
        errors = []

        # تعیین سرویس‌ها
        services = []
        try:
            if service_id:
                services = db.query(RenderService).filter(
                    RenderService.id == service_id
                ).all()
            else:
                # استفاده از filter ساده‌تر در صورت مشکل با auto_fetch_logs
                services = db.query(RenderService).all()
                # فیلتر در پایتون به جای SQL
                services = [s for s in services if getattr(s, 'auto_fetch_logs', True)]
        except Exception as e:
            slog.error("Error querying services (ORM)", exception=e)
            # Fallback: raw SQL
            try:
                from sqlalchemy import text
                if service_id:
                    result = db.execute(text("SELECT id, name FROM render_services WHERE id = :sid"), {"sid": service_id})
                else:
                    result = db.execute(text("SELECT id, name FROM render_services"))
                rows = result.fetchall()
                # ساخت شیء ساده به جای ORM model
                class SimpleService:
                    def __init__(self, id, name):
                        self.id = id
                        self.name = name
                        self.auto_fetch_logs = True
                services = [SimpleService(row[0], row[1]) for row in rows]
            except Exception as e2:
                slog.error("Error querying services (raw SQL)", exception=e2)
                services = []

        if not services:
            # اگر سرویسی نبود، اول لیست رو بگیر
            result = await render.get_services()
            if result["success"]:
                services = db.query(RenderService).all()
            else:
                return {
                    "success": False,
                    "error": result.get("error", "هیچ سرویسی یافت نشد. ابتدا لیست سرویس‌ها را بروزرسانی کنید.")
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
            "total_fetched": total_fetched,
            "total_saved": total_saved,
            "services_processed": len(services),
            "errors": errors if errors else None
        }

    except Exception as e:
        slog.error("Fetch logs failed", exception=e)
        return {
            "success": False,
            "error": str(e)
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
    try:
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
                "auto_scroll": settings.auto_scroll,
                # تنظیمات انتقال خودکار
                "auto_transfer_enabled": getattr(settings, 'auto_transfer_enabled', False),
                "auto_transfer_interval_minutes": getattr(settings, 'auto_transfer_interval_minutes', 30),
                "auto_transfer_hours_back": getattr(settings, 'auto_transfer_hours_back', 24),
                "auto_transfer_mode": getattr(settings, 'auto_transfer_mode', 'since_deploy') or 'since_deploy',
                "last_auto_transfer": settings.last_auto_transfer.isoformat() if getattr(settings, 'last_auto_transfer', None) else None
            }
        }
    except Exception as e:
        slog.error("Error fetching settings (ORM)", exception=e)
        # Fallback: مقادیر پیش‌فرض
        return {
            "success": True,
            "settings": {
                "polling_interval_seconds": 10,
                "polling_enabled": True,
                "retention_hours": 48,
                "archive_enabled": True,
                "archive_retention_days": 30,
                "default_log_levels": "info,warn,error",
                "auto_scroll": True,
                "auto_transfer_enabled": False,
                "auto_transfer_interval_minutes": 30,
                "auto_transfer_hours_back": 24,
                "auto_transfer_mode": "since_deploy",
                "last_auto_transfer": None
            },
            "source": "defaults"
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
    # تنظیمات انتقال خودکار
    settings.auto_transfer_enabled = request.auto_transfer_enabled
    settings.auto_transfer_interval_minutes = request.auto_transfer_interval_minutes
    settings.auto_transfer_hours_back = request.auto_transfer_hours_back
    settings.auto_transfer_mode = request.auto_transfer_mode

    db.commit()

    # 🆕 به‌روزرسانی scheduler برای auto-transfer
    try:
        from ...services.background_scheduler import get_background_scheduler
        scheduler = get_background_scheduler()
        await scheduler.update_auto_transfer_settings(
            enabled=request.auto_transfer_enabled,
            interval_minutes=request.auto_transfer_interval_minutes,
            hours_back=request.auto_transfer_hours_back,
            mode=request.auto_transfer_mode
        )
    except Exception as e:
        slog.warning("Failed to update scheduler", exception=e)

    slog.success("Log settings updated",
        polling_interval=request.polling_interval_seconds,
        retention_hours=request.retention_hours,
        auto_transfer_enabled=request.auto_transfer_enabled,
        auto_transfer_mode=request.auto_transfer_mode
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
        log_level=level,
        output_format=format
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
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "level": log.level or "unknown",
                "service": log.service_name or log.service_id or "unknown",
                "message": log.message or "",
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
                log.timestamp.isoformat() if log.timestamp else "",
                log.level or "unknown",
                log.service_name or log.service_id or "unknown",
                log.message or "",
                log.deploy_id or ""
            ])
        content = output.getvalue()
        media_type = "text/csv"

    else:  # txt
        lines = []
        for log in logs:
            ts = log.timestamp.strftime("%Y-%m-%d %H:%M:%S") if log.timestamp else "N/A"
            level = (log.level or "unknown").upper()
            service = log.service_name or log.service_id or "unknown"
            message = log.message or ""
            lines.append(f"[{ts}] [{level}] [{service}] {message}")
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
    since_deploy: bool = True,  # 🆕 فقط خطاهای پس از دیپلوی
    db: Session = Depends(get_db)
):
    """
    وضعیت انتقال لاگ‌های خطا

    - تعداد لاگ‌های منتقل شده
    - تعداد لاگ‌های در انتظار (فقط پس از آخرین دیپلوی)
    """
    from sqlalchemy import and_, or_

    # 🆕 دریافت زمان آخرین دیپلوی هر سرویس
    services = db.query(RenderService).all()
    # 🔴 FIX: استفاده از s.id به جای s.service_id
    service_deploy_times = {s.id: s.last_deploy_at for s in services if s.last_deploy_at}

    # Base filter for error logs
    error_filter = RenderLog.level.in_(["error", "fatal", "critical"])

    if since_deploy and service_deploy_times:
        # 🆕 فیلتر بر اساس آخرین دیپلوی هر سرویس
        conditions = []
        for service_id, deploy_time in service_deploy_times.items():
            conditions.append(
                and_(
                    RenderLog.service_id == service_id,
                    RenderLog.timestamp >= deploy_time
                )
            )
        # سرویس‌های بدون deploy_at - fallback به 24 ساعت
        # 🔴 FIX: استفاده از s.id به جای s.service_id
        services_without_deploy = [s.id for s in services if not s.last_deploy_at]
        if services_without_deploy:
            fallback_cutoff = datetime.utcnow() - timedelta(hours=24)
            conditions.append(
                and_(
                    RenderLog.service_id.in_(services_without_deploy),
                    RenderLog.timestamp >= fallback_cutoff
                )
            )

        if conditions:
            time_filter = or_(*conditions)
        else:
            time_filter = None
    else:
        time_filter = None

    # لاگ‌های خطای منتقل نشده (پس از دیپلوی)
    pending_query = db.query(RenderLog).filter(
        error_filter,
        RenderLog.transferred_to_issues == False
    )
    if time_filter is not None:
        pending_query = pending_query.filter(time_filter)
    pending_count = pending_query.count()

    # لاگ‌های منتقل شده
    transferred_count = db.query(RenderLog).filter(
        RenderLog.transferred_to_issues == True
    ).count()

    # 🆕 خطاهای تاریخی (قبل از دیپلوی) که منتقل نشده‌اند
    historical_pending = 0
    if since_deploy and service_deploy_times:
        historical_conditions = []
        for service_id, deploy_time in service_deploy_times.items():
            historical_conditions.append(
                and_(
                    RenderLog.service_id == service_id,
                    RenderLog.timestamp < deploy_time
                )
            )
        if historical_conditions:
            historical_pending = db.query(RenderLog).filter(
                error_filter,
                RenderLog.transferred_to_issues == False,
                or_(*historical_conditions)
            ).count()

    return {
        "success": True,
        "pending_errors": pending_count,
        "transferred_errors": transferred_count,
        "can_transfer": pending_count > 0,
        # 🆕 اطلاعات تکمیلی
        "since_deploy": since_deploy,
        "historical_pending": historical_pending if since_deploy else None,
        "total_pending": pending_count + historical_pending if since_deploy else pending_count
    }


from fastapi.responses import StreamingResponse
import asyncio

@router.post("/transfer-errors-stream")
async def transfer_errors_stream(
    service_ids: Optional[List[str]] = Query(None),
    hours: int = 24,
    mode: str = "since_deploy",
    force: bool = False,
    db: Session = Depends(get_db)
):
    """
    انتقال لاگ‌های خطا با گزارش پیشرفت لحظه‌ای (SSE)

    Stream events:
    - {"type": "start", "total_logs": N}
    - {"type": "progress", "current": N, "total": N, "status": "..."}
    - {"type": "log_processed", "log_id": X, "action": "transferred|merged|skipped"}
    - {"type": "complete", "transferred": N, "merged": N, "skipped": N}
    - {"type": "error", "message": "..."}

    Args:
        force: اگر True باشد، لاگ‌هایی که قبلاً منتقل شده‌اند هم مجدداً پردازش می‌شوند
    """

    async def event_generator():
        try:
            service = get_log_to_issues_service()

            # 1. شمارش لاگ‌ها
            error_logs = await service._get_error_logs(db, service_ids, hours, mode, force=force)
            total_logs = len(error_logs)

            yield f"data: {json.dumps({'type': 'start', 'total_logs': total_logs, 'message': f'شروع پردازش {total_logs} لاگ خطا...', 'force': force})}\n\n"

            if total_logs == 0:
                # DEBUG: نمایش اطلاعات بیشتر در صورت نبود لاگ
                debug_info = await service._get_debug_info(db, service_ids, hours)
                yield f"data: {json.dumps({'type': 'complete', 'transferred': 0, 'merged': 0, 'skipped': 0, 'message': 'لاگ خطایی یافت نشد', 'debug': debug_info})}\n\n"
                return

            # 2. ساخت نگاشت سرویس-پروژه
            yield f"data: {json.dumps({'type': 'progress', 'current': 0, 'total': total_logs, 'status': 'در حال نگاشت سرویس‌ها به پروژه‌ها...'})}\n\n"
            service_project_map = await service._build_service_project_map(db)

            # DEBUG: نمایش تعداد نگاشت‌ها
            yield f"data: {json.dumps({'type': 'debug', 'message': f'نگاشت سرویس-پروژه: {len(service_project_map)} مورد', 'mappings': list(service_project_map.keys())})}\n\n"

            transferred = 0
            merged = 0
            skipped = 0

            # 3. پردازش هر لاگ با گزارش پیشرفت
            for i, log in enumerate(error_logs):
                try:
                    yield f"data: {json.dumps({'type': 'progress', 'current': i + 1, 'total': total_logs, 'status': f'پردازش لاگ {i + 1} از {total_logs}...', 'service': log.service_name or 'unknown'})}\n\n"

                    result = await service._process_error_log(log, service_project_map, db)

                    action = result.get("status", "skipped")
                    if action == "transferred":
                        transferred += 1
                    elif action == "merged":
                        merged += 1
                    else:
                        skipped += 1

                    yield f"data: {json.dumps({'type': 'log_processed', 'log_id': log.id, 'action': action, 'current': i + 1, 'total': total_logs})}\n\n"

                    # کمی صبر برای جلوگیری از overload
                    await asyncio.sleep(0.1)

                except Exception as e:
                    slog.error(f"Error processing log {log.id}", exception=e)
                    skipped += 1
                    yield f"data: {json.dumps({'type': 'log_error', 'log_id': log.id, 'error': str(e)})}\n\n"

            # 4. آرشیو کردن
            if transferred > 0 or merged > 0:
                yield f"data: {json.dumps({'type': 'progress', 'current': total_logs, 'total': total_logs, 'status': 'در حال آرشیو کردن...'})}\n\n"
                await service._archive_transferred_logs(db, error_logs, service_project_map)

            db.commit()

            yield f"data: {json.dumps({'type': 'complete', 'transferred': transferred, 'merged': merged, 'skipped': skipped, 'message': f'✅ {transferred} یافته جدید منتقل شد، {merged} ایراد ادغام شد'})}\n\n"

        except Exception as e:
            slog.error("Transfer stream error", exception=e)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/archive-stale-issues")
async def archive_stale_issues_after_deploy(
    service_id: str,
    deploy_id: str,
    db: Session = Depends(get_db)
):
    """
    بایگانی خودکار ایرادات قدیمی بعد از دیپلوی جدید

    وقتی یک دیپلوی جدید شناسایی می‌شود:
    - ایرادات مربوط به دیپلوی‌های قبلی بایگانی می‌شوند
    - فقط ایرادات دیپلوی جاری باقی می‌مانند

    این endpoint را می‌توان بعد از هر دیپلوی جدید صدا زد
    """
    slog.api_request("POST", "/render/archive-stale-issues",
        service_id=service_id,
        deploy_id=deploy_id
    )

    service = get_log_to_issues_service()
    result = await service.archive_stale_issues_after_deploy(
        service_id=service_id,
        new_deploy_id=deploy_id,
        db=db
    )

    return {
        "success": True,
        **result
    }


# =====================================
# Stats Endpoints
# =====================================

@router.get("/stats")
async def get_log_stats(
    hours: int = 24,
    since_deploy: bool = True,  # 🆕 پیش‌فرض: فقط لاگ‌های بعد از آخرین دیپلوی
    db: Session = Depends(get_db)
):
    """
    آمار لاگ‌ها

    Args:
        hours: بازه زمانی (ساعت) - فقط در حالت since_deploy=False استفاده می‌شود
        since_deploy: اگر True باشد، فقط لاگ‌های بعد از آخرین دیپلوی هر سرویس شمرده می‌شوند
    """
    from sqlalchemy import func, or_, and_

    # 🆕 دریافت آخرین deploy_at هر سرویس
    services = db.query(RenderService).all()
    # 🔴 FIX: استفاده از s.id به جای s.service_id
    service_deploy_times = {s.id: s.last_deploy_at for s in services if s.last_deploy_at}

    # Base query
    if since_deploy and service_deploy_times:
        # 🆕 فیلتر بر اساس آخرین دیپلوی هر سرویس
        # لاگ‌هایی که timestamp آنها بعد از last_deploy_at سرویس مربوطه است
        conditions = []
        for service_id, deploy_time in service_deploy_times.items():
            conditions.append(
                and_(
                    RenderLog.service_id == service_id,
                    RenderLog.timestamp >= deploy_time
                )
            )
        # اگر سرویسی last_deploy_at نداشته باشد، لاگ‌های 24 ساعت اخیر آن را بگیر
        # 🔴 FIX: استفاده از s.id به جای s.service_id
        services_without_deploy = [s.id for s in services if not s.last_deploy_at]
        if services_without_deploy:
            fallback_cutoff = datetime.utcnow() - timedelta(hours=24)
            conditions.append(
                and_(
                    RenderLog.service_id.in_(services_without_deploy),
                    RenderLog.timestamp >= fallback_cutoff
                )
            )

        if conditions:
            base_filter = or_(*conditions)
        else:
            base_filter = RenderLog.timestamp >= (datetime.utcnow() - timedelta(hours=24))
    else:
        # حالت قدیمی: بر اساس hours
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        base_filter = RenderLog.timestamp >= cutoff

    # تعداد کل
    total = db.query(RenderLog).filter(base_filter).count()

    # تعداد بر اساس سطح
    level_counts = db.query(
        RenderLog.level,
        func.count(RenderLog.id)
    ).filter(base_filter).group_by(RenderLog.level).all()

    # تعداد بر اساس سرویس
    service_counts = db.query(
        RenderLog.service_id,
        RenderLog.service_name,
        func.count(RenderLog.id)
    ).filter(base_filter).group_by(RenderLog.service_id, RenderLog.service_name).all()

    # 🆕 آمار تاریخی (قبل از دیپلوی) - فقط برای نمایش
    historical_error_count = 0
    if since_deploy and service_deploy_times:
        historical_conditions = []
        for service_id, deploy_time in service_deploy_times.items():
            historical_conditions.append(
                and_(
                    RenderLog.service_id == service_id,
                    RenderLog.timestamp < deploy_time,
                    RenderLog.level == "error"
                )
            )
        if historical_conditions:
            historical_error_count = db.query(RenderLog).filter(
                or_(*historical_conditions)
            ).count()

    return {
        "success": True,
        "period_hours": hours if not since_deploy else None,
        "since_deploy": since_deploy,
        "total_logs": total,
        "by_level": {level: count for level, count in level_counts},
        "by_service": [
            {"service_id": sid, "service_name": sname, "count": count}
            for sid, sname, count in service_counts
        ],
        "error_count": next((c for l, c in level_counts if l == "error"), 0),
        "warning_count": next((c for l, c in level_counts if l == "warn"), 0),
        # 🆕 آمار تاریخی
        "historical_error_count": historical_error_count if since_deploy else None,
        "deploy_info": {
            sid: dt.isoformat() if dt else None
            for sid, dt in service_deploy_times.items()
        } if since_deploy else None
    }


# =====================================
# Scheduler Status Endpoints
# =====================================

@router.get("/scheduler/status")
async def get_scheduler_status():
    """وضعیت scheduler و job های فعال"""
    try:
        from ...services.background_scheduler import get_background_scheduler
        scheduler = get_background_scheduler()
        return {
            "success": True,
            **scheduler.get_jobs_info()
        }
    except Exception as e:
        slog.error("Failed to get scheduler status", exception=e)
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/scheduler/trigger-auto-transfer")
async def trigger_auto_transfer_now():
    """اجرای فوری auto-transfer"""
    try:
        from ...services.background_scheduler import get_background_scheduler
        scheduler = get_background_scheduler()

        # اجرای مستقیم به جای trigger job
        result = await scheduler._run_auto_transfer()

        return {
            "success": True,
            "message": "Auto-transfer executed",
            "result": result
        }
    except Exception as e:
        slog.error("Failed to trigger auto-transfer", exception=e)
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/auto-transfer/debug")
async def debug_auto_transfer(db: Session = Depends(get_db)):
    """
    🔍 تشخیص مشکلات انتقال خودکار

    بررسی می‌کند:
    1. تنظیمات auto-transfer فعال است؟
    2. scheduler اجرا می‌شود؟
    3. سرویس‌ها به پروژه نگاشت شده‌اند؟
    4. لاگ خطایی برای انتقال وجود دارد؟
    """
    from ...services.log_to_issues_service import get_log_to_issues_service
    from ...services.background_scheduler import get_background_scheduler
    from datetime import datetime, timedelta

    diagnosis = {
        "timestamp": datetime.utcnow().isoformat(),
        "settings": {},
        "scheduler": {},
        "service_mapping": {},
        "error_logs": {},
        "issues": [],
        "recommendations": []
    }

    try:
        # 1. بررسی تنظیمات
        settings = db.query(RenderLogSettings).first()
        if settings:
            diagnosis["settings"] = {
                "auto_transfer_enabled": settings.auto_transfer_enabled,
                "auto_transfer_mode": getattr(settings, 'auto_transfer_mode', 'since_deploy') or 'since_deploy',
                "auto_transfer_interval_minutes": settings.auto_transfer_interval_minutes,
                "auto_transfer_hours_back": settings.auto_transfer_hours_back,
                "last_auto_transfer": settings.last_auto_transfer.isoformat() if settings.last_auto_transfer else None
            }
            if not settings.auto_transfer_enabled:
                diagnosis["issues"].append("❌ انتقال خودکار غیرفعال است!")
                diagnosis["recommendations"].append("✅ از تب تنظیمات Render Logs، گزینه 'انتقال خودکار خطاها' را فعال کنید")
        else:
            diagnosis["settings"] = {"error": "تنظیمات یافت نشد"}
            diagnosis["issues"].append("❌ تنظیمات Render Logs ایجاد نشده")

        # 2. بررسی scheduler
        try:
            scheduler = get_background_scheduler()
            jobs_info = scheduler.get_jobs_info()
            diagnosis["scheduler"] = jobs_info

            if not jobs_info.get("running"):
                diagnosis["issues"].append("❌ Scheduler اجرا نمی‌شود!")
                diagnosis["recommendations"].append("✅ سرور را ری‌استارت کنید")
            elif not any(j["id"] == "auto_transfer_errors" for j in jobs_info.get("jobs", [])):
                diagnosis["issues"].append("⚠️ Job انتقال خودکار ثبت نشده (احتمالاً چون auto_transfer_enabled=False)")
                diagnosis["recommendations"].append("✅ انتقال خودکار را فعال کرده و ذخیره کنید")
        except Exception as se:
            diagnosis["scheduler"] = {"error": str(se)}

        # 3. بررسی نگاشت سرویس-پروژه
        try:
            service = get_log_to_issues_service()
            service_map = await service._build_service_project_map(db)

            # دریافت همه سرویس‌ها
            services = db.query(RenderService).all()

            mapped_count = 0
            unmapped_services = []

            for s in services:
                if s.id in service_map:
                    mapped_count += 1
                else:
                    unmapped_services.append({
                        "id": s.id,
                        "name": s.name,
                        "manual_project_id": s.project_id
                    })

            diagnosis["service_mapping"] = {
                "total_services": len(services),
                "mapped_services": mapped_count,
                "unmapped_services": unmapped_services,
                "mapping_details": {k: v["project_name"] for k, v in service_map.items()}
            }

            if unmapped_services:
                diagnosis["issues"].append(f"⚠️ {len(unmapped_services)} سرویس بدون نگاشت به پروژه")
                diagnosis["recommendations"].append("✅ برای هر سرویس، project_id را در تنظیمات سرویس تعیین کنید")

        except Exception as me:
            diagnosis["service_mapping"] = {"error": str(me)}

        # 4. بررسی لاگ‌های خطا
        try:
            cutoff = datetime.utcnow() - timedelta(hours=24)

            total_errors = db.query(RenderLog).filter(
                RenderLog.timestamp >= cutoff,
                RenderLog.level.in_(["error", "fatal", "critical"])
            ).count()

            transferred_errors = db.query(RenderLog).filter(
                RenderLog.timestamp >= cutoff,
                RenderLog.level.in_(["error", "fatal", "critical"]),
                RenderLog.transferred_to_issues == True
            ).count()

            not_transferred = total_errors - transferred_errors

            diagnosis["error_logs"] = {
                "period": "24 hours",
                "total_error_logs": total_errors,
                "already_transferred": transferred_errors,
                "not_transferred": not_transferred
            }

            if total_errors == 0:
                diagnosis["issues"].append("ℹ️ هیچ لاگ خطایی در ۲۴ ساعت گذشته وجود ندارد")
            elif not_transferred > 0 and settings and settings.auto_transfer_enabled:
                diagnosis["issues"].append(f"⚠️ {not_transferred} خطا منتظر انتقال هستند")
                diagnosis["recommendations"].append("✅ روی 'اجرای فوری انتقال' کلیک کنید یا منتظر اجرای خودکار بمانید")

        except Exception as le:
            diagnosis["error_logs"] = {"error": str(le)}

        # نتیجه‌گیری
        if not diagnosis["issues"]:
            diagnosis["status"] = "✅ همه چیز سالم به نظر می‌رسد"
        else:
            diagnosis["status"] = f"⚠️ {len(diagnosis['issues'])} مشکل شناسایی شد"

        return {
            "success": True,
            "diagnosis": diagnosis
        }

    except Exception as e:
        slog.error("Auto-transfer debug failed", exception=e)
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/auto-transfer/force-transfer")
async def force_transfer_all_errors(
    hours_back: int = Query(24, ge=1, le=168),
    limit: int = Query(10, ge=1, le=100),  # 🆕 محدود کردن تعداد برای تست
    db: Session = Depends(get_db)
):
    """
    🔴 انتقال اجباری خطاها با logging کامل

    - limit: حداکثر تعداد لاگ برای پردازش (برای تست)
    """
    from ...services.log_to_issues_service import get_log_to_issues_service
    from ...models.project import Project, ProjectIssue

    debug_log = []

    try:
        service = get_log_to_issues_service()
        service.initialize()

        # ریست کردن فلگ transferred برای تست
        cutoff = datetime.utcnow() - timedelta(hours=hours_back)
        reset_count = db.query(RenderLog).filter(
            RenderLog.timestamp >= cutoff,
            RenderLog.level.in_(["error", "fatal", "critical"]),
            RenderLog.transferred_to_issues == True
        ).update({RenderLog.transferred_to_issues: False})
        db.commit()
        debug_log.append(f"✅ Reset {reset_count} transferred flags")

        # شمارش ایرادات قبل
        issues_before = db.query(ProjectIssue).count()
        debug_log.append(f"📊 Issues before: {issues_before}")

        # دریافت لاگ‌های خطا (محدود)
        error_logs = db.query(RenderLog).filter(
            RenderLog.timestamp >= cutoff,
            RenderLog.level.in_(["error", "fatal", "critical"]),
            RenderLog.transferred_to_issues == False
        ).order_by(RenderLog.timestamp.desc()).limit(limit).all()

        debug_log.append(f"📋 Found {len(error_logs)} error logs to process")

        # ساخت service-project map
        service_project_map = await service._build_service_project_map(db)
        debug_log.append(f"🗺️ Service mapping: {len(service_project_map)} services mapped")

        # پردازش دستی هر لاگ با logging کامل
        transferred = 0
        merged = 0
        skipped = 0
        errors_list = []

        for i, log in enumerate(error_logs):
            try:
                debug_log.append(f"\n--- Log {i+1}/{len(error_logs)} ---")
                debug_log.append(f"   Service: {log.service_name} ({log.service_id})")
                debug_log.append(f"   Message: {(log.message or '')[:100]}...")

                # بررسی mapping
                if log.service_id not in service_project_map:
                    debug_log.append(f"   ❌ SKIPPED: service not mapped")
                    skipped += 1
                    continue

                mapping = service_project_map[log.service_id]
                project_id = mapping["project_id"]
                debug_log.append(f"   ✅ Mapped to project: {mapping['project_name']}")

                # دریافت پروژه
                project = db.query(Project).filter(Project.id == project_id).first()
                if not project:
                    debug_log.append(f"   ❌ SKIPPED: project not found")
                    skipped += 1
                    continue

                # تحلیل AI
                debug_log.append(f"   🧠 Running AI analysis...")
                ai_analysis = await service._analyze_error_with_ai(log, project)
                debug_log.append(f"   📝 AI result: {ai_analysis.get('error_type', 'unknown')}")

                # جستجوی ایراد مشابه
                existing = service._find_similar_issue_in_db(
                    db, project_id, log.message, ai_analysis.get("error_type", "")
                )

                if existing:
                    existing.occurrences = (existing.occurrences or 0) + 1
                    existing.updated_at = datetime.utcnow()
                    merged += 1
                    debug_log.append(f"   🔄 MERGED with existing issue {existing.id}")
                else:
                    # ایجاد ایراد جدید
                    priority_map = {"high": 2, "medium": 3, "low": 4, "critical": 1}
                    new_issue = ProjectIssue(
                        project_id=project_id,
                        title=ai_analysis.get("error_type", "خطای Render")[:200] or (log.message or "")[:200],
                        description=ai_analysis.get("explanation", log.message),
                        solution=ai_analysis.get("suggested_fix", "بررسی لاگ کامل"),
                        priority=priority_map.get(ai_analysis.get("priority", "medium"), 3),
                        status="open",
                        source="render_logs",
                        source_data=json.dumps({
                            "log_id": log.id,
                            "service_name": log.service_name,
                            "ai_analysis": ai_analysis
                        }, ensure_ascii=False),
                        occurrences=1,
                        created_at=datetime.utcnow()
                    )
                    db.add(new_issue)
                    transferred += 1
                    debug_log.append(f"   ✅ CREATED new issue")

                # علامت‌گذاری لاگ
                log.transferred_to_issues = True
                log.transferred_at = datetime.utcnow()

            except Exception as e:
                debug_log.append(f"   ❌ ERROR: {str(e)}")
                errors_list.append({"log_id": log.id, "error": str(e)})

        # Commit
        try:
            db.commit()
            debug_log.append(f"\n✅ Committed successfully")
        except Exception as ce:
            debug_log.append(f"\n❌ Commit failed: {str(ce)}")
            db.rollback()

        # شمارش بعد
        issues_after = db.query(ProjectIssue).count()
        debug_log.append(f"📊 Issues after: {issues_after}")
        debug_log.append(f"📊 New issues: {issues_after - issues_before}")

        return {
            "success": True,
            "summary": {
                "reset_count": reset_count,
                "logs_processed": len(error_logs),
                "transferred": transferred,
                "merged": merged,
                "skipped": skipped,
                "issues_before": issues_before,
                "issues_after": issues_after,
                "new_issues": issues_after - issues_before
            },
            "errors": errors_list,
            "debug_log": debug_log
        }

    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "debug_log": debug_log
        }


# =====================================
# WebSocket Endpoints
# =====================================

@router.websocket("/ws/stream")
async def websocket_log_stream(websocket: WebSocket):
    """
    WebSocket endpoint برای streaming لاگ‌های زنده

    Protocol:
    1. Client متصل می‌شود
    2. Client می‌تواند فیلترها را ارسال کند: {"type": "set_filters", "filters": {...}}
    3. Server لاگ‌های جدید را broadcast می‌کند: {"type": "new_logs", "logs": [...]}
    4. Client می‌تواند ping ارسال کند: {"type": "ping"}
    5. Server پاسخ می‌دهد: {"type": "pong"}
    """
    from ...services.log_stream_service import get_log_stream_service

    await websocket.accept()
    client_id = str(uuid.uuid4())

    slog.info("WebSocket client connected", client_id=client_id)

    try:
        # ثبت کلاینت
        stream_service = get_log_stream_service()
        await stream_service.register_client(client_id, websocket)

        # ارسال پیام خوش‌آمدگویی
        await websocket.send_json({
            "type": "connected",
            "client_id": client_id,
            "message": "Connected to log stream"
        })

        # حلقه دریافت پیام
        while True:
            try:
                data = await websocket.receive_json()
                msg_type = data.get("type")

                if msg_type == "set_filters":
                    # به‌روزرسانی فیلترها
                    filters = data.get("filters", {})
                    await stream_service.update_client_filters(client_id, filters)
                    await websocket.send_json({
                        "type": "filters_updated",
                        "filters": filters
                    })

                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

                elif msg_type == "start_polling":
                    await stream_service.start_polling()
                    await websocket.send_json({
                        "type": "polling_started"
                    })

                elif msg_type == "stop_polling":
                    await stream_service.stop_polling()
                    await websocket.send_json({
                        "type": "polling_stopped"
                    })

            except WebSocketDisconnect:
                break
            except Exception as e:
                slog.warning("WebSocket message error", client_id=client_id, exception=e)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        slog.error("WebSocket error", client_id=client_id, exception=e)
    finally:
        # حذف کلاینت
        await stream_service.unregister_client(client_id)
        slog.info("WebSocket client disconnected", client_id=client_id)


@router.get("/stream/status")
async def get_stream_status():
    """وضعیت سرویس streaming"""
    from ...services.log_stream_service import get_log_stream_service

    service = get_log_stream_service()
    return {
        "success": True,
        **service.get_status()
    }


@router.post("/stream/start")
async def start_server_polling():
    """شروع server-side polling"""
    from ...services.log_stream_service import get_log_stream_service

    service = get_log_stream_service()
    await service.start_polling()

    return {
        "success": True,
        "message": "Server-side polling started"
    }


@router.post("/stream/stop")
async def stop_server_polling():
    """توقف server-side polling"""
    from ...services.log_stream_service import get_log_stream_service

    service = get_log_stream_service()
    await service.stop_polling()

    return {
        "success": True,
        "message": "Server-side polling stopped"
    }


@router.get("/stream/latest")
async def get_latest_logs_for_stream(
    service_ids: Optional[List[str]] = Query(None),
    levels: Optional[List[str]] = Query(None),
    limit: int = 100,
    since_id: Optional[str] = None
):
    """
    دریافت آخرین لاگ‌ها (برای HTTP polling fallback)

    این endpoint برای کلاینت‌هایی است که نمی‌توانند
    از WebSocket استفاده کنند
    """
    from ...services.log_stream_service import get_log_stream_service

    service = get_log_stream_service()
    return await service.fetch_latest_logs(
        service_ids=service_ids,
        levels=levels,
        limit=limit,
        since_id=since_id
    )


# =====================================
# 🆕 Inspector Chat - چت با مدل‌های AI
# =====================================

class InspectorChatMessage(BaseModel):
    """یک پیام در چت بازرس"""
    role: str  # user, assistant
    content: str


class InspectorChatRequest(BaseModel):
    """درخواست چت با بازرس"""
    model_id: str
    message: str
    project_id: str
    # Context
    backend_logs: Optional[List[dict]] = None
    frontend_url: Optional[str] = None
    project_files: Optional[List[dict]] = None  # [{path, content}]
    project_structure: Optional[dict] = None
    chat_history: Optional[List[InspectorChatMessage]] = None
    # تنظیمات
    max_tokens: int = 4096
    temperature: float = 0.7
    stream: bool = False


class InspectorMultiChatRequest(BaseModel):
    """درخواست چت با چند مدل"""
    model_ids: List[str]
    message: str
    project_id: str
    # Context
    backend_logs: Optional[List[dict]] = None
    frontend_url: Optional[str] = None
    project_files: Optional[List[dict]] = None
    project_structure: Optional[dict] = None
    chat_history: Optional[List[InspectorChatMessage]] = None
    # تنظیمات
    max_tokens: int = 4096
    temperature: float = 0.7


def build_inspector_system_prompt(
    project_id: str,
    backend_logs: Optional[List[dict]] = None,
    frontend_url: Optional[str] = None,
    project_files: Optional[List[dict]] = None,
    project_structure: Optional[dict] = None,
    db: Session = None
) -> str:
    """ساخت system prompt با تمام context های پروژه"""

    prompt_parts = [
        "# 🔍 بازرس ویژه پروژه",
        "",
        "تو یک بازرس هوشمند و متخصص هستی که به تمام داده‌های پروژه دسترسی داری.",
        "وظیفه تو تحلیل، عیب‌یابی، بررسی امنیت و کمک به توسعه‌دهنده است.",
        "",
        "## دسترسی‌های تو:",
        "- لاگ‌های بک‌اند (زنده)",
        "- URL فرانت‌اند (پیش‌نمایش)",
        "- فایل‌های پروژه",
        "- ساختار پروژه",
        "",
    ]

    # اطلاعات پروژه از دیتابیس
    if db:
        try:
            from ...models.project import Project
            project = db.query(Project).filter(Project.id == project_id).first()
            if project:
                prompt_parts.extend([
                    f"## پروژه: {project.name}",
                    f"- توضیحات: {project.description or 'ندارد'}",
                    f"- نوع: {getattr(project, 'type', 'نامشخص')}",
                    f"- تاریخ ایجاد: {project.created_at}",
                    "",
                ])
        except Exception as e:
            slog.warning("Could not fetch project info", error=str(e))

    # لاگ‌های بک‌اند
    if backend_logs:
        prompt_parts.extend([
            "## 📋 لاگ‌های بک‌اند (آخرین لاگ‌ها):",
            "```",
        ])
        for log in backend_logs[-30:]:  # آخرین 30 لاگ
            level = log.get('level', 'info').upper()
            timestamp = log.get('timestamp', '')[:19]
            message = log.get('message', '')[:200]
            prompt_parts.append(f"[{timestamp}] [{level}] {message}")
        prompt_parts.extend(["```", ""])

        # خلاصه خطاها
        errors = [l for l in backend_logs if l.get('level') == 'error']
        if errors:
            prompt_parts.extend([
                f"### ⚠️ {len(errors)} خطا شناسایی شده:",
            ])
            for err in errors[-5:]:
                prompt_parts.append(f"- {err.get('message', '')[:100]}")
            prompt_parts.append("")

    # URL فرانت‌اند
    if frontend_url:
        prompt_parts.extend([
            f"## 🌐 URL فرانت‌اند:",
            f"- {frontend_url}",
            "",
        ])

    # ساختار پروژه
    if project_structure:
        prompt_parts.extend([
            "## 📁 ساختار پروژه:",
            "```",
            json.dumps(project_structure, ensure_ascii=False, indent=2)[:2000],
            "```",
            "",
        ])

    # فایل‌های پروژه
    if project_files:
        prompt_parts.extend([
            "## 📄 فایل‌های پروژه:",
        ])
        for f in project_files[:10]:  # حداکثر 10 فایل
            path = f.get('path', '')
            content = f.get('content', '')[:3000]  # حداکثر 3000 کاراکتر
            prompt_parts.extend([
                f"### {path}",
                "```",
                content,
                "```",
                "",
            ])

    prompt_parts.extend([
        "---",
        "## دستورالعمل:",
        "1. پاسخ‌ها را به فارسی بده",
        "2. اگر خطایی در لاگ‌ها دیدی، آن را تحلیل کن",
        "3. پیشنهادات عملی و کاربردی بده",
        "4. اگر کد نیاز بود، کد کامل و قابل اجرا بنویس",
        "5. امنیت را همیشه در نظر بگیر",
    ])

    return "\n".join(prompt_parts)


@router.post("/inspector/chat")
async def inspector_chat(
    request: InspectorChatRequest,
    db: Session = Depends(get_db)
):
    """
    چت با مدل AI در تب بازرس ویژه

    این endpoint تمام context های پروژه را به مدل می‌دهد:
    - لاگ‌های بک‌اند
    - URL فرانت‌اند
    - فایل‌های پروژه
    - ساختار پروژه
    """
    slog.api_request("POST", "/render/inspector/chat",
        model=request.model_id,
        project_id=request.project_id
    )

    try:
        from ...services.ai_manager import get_ai_manager
        from ...services.ai_base import Message

        ai_manager = get_ai_manager()

        # ساخت system prompt با context
        system_prompt = build_inspector_system_prompt(
            project_id=request.project_id,
            backend_logs=request.backend_logs,
            frontend_url=request.frontend_url,
            project_files=request.project_files,
            project_structure=request.project_structure,
            db=db
        )

        # ساخت messages
        messages = [Message(role="system", content=system_prompt)]

        # افزودن تاریخچه چت
        if request.chat_history:
            for msg in request.chat_history[-10:]:  # آخرین 10 پیام
                messages.append(Message(role=msg.role, content=msg.content))

        # افزودن پیام جدید کاربر
        messages.append(Message(role="user", content=request.message))

        slog.ai_call(request.model_id, "inspector chat",
            messages_count=len(messages),
            has_logs=bool(request.backend_logs),
            has_files=bool(request.project_files)
        )

        # ارسال به AI
        response = await ai_manager.generate(
            model_id=request.model_id,
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )

        slog.success("Inspector chat response generated",
            model=response.model_id,
            tokens_used=response.tokens_used
        )

        return {
            "success": True,
            "model_id": response.model_id,
            "content": response.content,
            "tokens_used": response.tokens_used,
            "latency_ms": response.latency_ms,
            "finish_reason": response.finish_reason
        }

    except Exception as e:
        slog.error("Inspector chat failed", exception=e, model=request.model_id)
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/inspector/chat/multi")
async def inspector_chat_multi(
    request: InspectorMultiChatRequest,
    db: Session = Depends(get_db)
):
    """
    چت با چند مدل AI به صورت موازی

    پاسخ همه مدل‌های انتخاب شده را برمی‌گرداند
    """
    slog.api_request("POST", "/render/inspector/chat/multi",
        models=request.model_ids,
        project_id=request.project_id
    )

    try:
        from ...services.ai_manager import get_ai_manager
        from ...services.ai_base import Message

        ai_manager = get_ai_manager()

        # ساخت system prompt با context
        system_prompt = build_inspector_system_prompt(
            project_id=request.project_id,
            backend_logs=request.backend_logs,
            frontend_url=request.frontend_url,
            project_files=request.project_files,
            project_structure=request.project_structure,
            db=db
        )

        # ساخت messages
        messages = [Message(role="system", content=system_prompt)]

        # افزودن تاریخچه چت
        if request.chat_history:
            for msg in request.chat_history[-10:]:
                messages.append(Message(role=msg.role, content=msg.content))

        # افزودن پیام جدید کاربر
        messages.append(Message(role="user", content=request.message))

        slog.ai_call(",".join(request.model_ids), "inspector multi-chat",
            models_count=len(request.model_ids)
        )

        # ارسال به همه مدل‌ها به صورت موازی
        responses = await ai_manager.generate_parallel(
            model_ids=request.model_ids,
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )

        successful = [r for r in responses if not r.error]
        slog.success("Inspector multi-chat completed",
            total=len(responses),
            successful=len(successful)
        )

        return {
            "success": True,
            "responses": [
                {
                    "model_id": r.model_id,
                    "content": r.content,
                    "tokens_used": r.tokens_used,
                    "latency_ms": r.latency_ms,
                    "error": r.error
                }
                for r in responses
            ],
            "total_models": len(request.model_ids),
            "successful_count": len(successful)
        }

    except Exception as e:
        slog.error("Inspector multi-chat failed", exception=e)
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/inspector/models")
async def get_available_models_for_inspector(db: Session = Depends(get_db)):
    """
    دریافت لیست مدل‌های موجود برای استفاده در بازرس

    همه مدل‌ها (فعال و غیرفعال) برگردانده می‌شوند
    """
    try:
        from ...core.models_registry import MODEL_REGISTRY
        from ...services.ai_manager import get_ai_manager
        from ...models.ai_profile import ModelSettings

        # دریافت provider های فعال
        available_providers = []
        try:
            ai_manager = get_ai_manager()
            available_providers = ai_manager.get_available_providers()
        except Exception as e:
            slog.warning("Could not get AI manager", error=str(e))

        # دریافت تنظیمات از دیتابیس
        db_settings = db.query(ModelSettings).all() if db else []
        settings_map = {s.model_id: s for s in db_settings}

        # گروه‌بندی بر اساس provider
        models_by_provider = {}
        models_list = []

        for model_id, model in MODEL_REGISTRY.items():
            provider = str(model.provider.value) if hasattr(model.provider, 'value') else str(model.provider)

            # بررسی فعال بودن
            setting = settings_map.get(model_id)
            is_enabled = setting.enabled if setting else True
            provider_available = provider in [str(p.value) if hasattr(p, 'value') else str(p) for p in available_providers]

            model_info = {
                "id": model_id,
                "name": model.name,
                "provider": provider,
                "context_window": getattr(model, 'context_window', 4096),
                "enabled": is_enabled and provider_available,
                "provider_available": provider_available
            }

            models_list.append(model_info)

            if provider not in models_by_provider:
                models_by_provider[provider] = []
            models_by_provider[provider].append(model_info)

        # بررسی اتصال GitHub - همان روش deploy-keys/status
        from ...models.setting import Setting
        import os

        # روش 1: از environment
        github_key = os.environ.get("GITHUB_TOKEN", "")

        # روش 2: اگر نبود، از دیتابیس بخون و در environment ست کن
        if not github_key:
            try:
                github_key = Setting.get_value(db, "api_key_github") or ""
                if github_key:
                    os.environ["GITHUB_TOKEN"] = github_key
                    slog.info("Loaded GitHub token from database and set in environment")
            except Exception as e:
                slog.warning("Failed to get GitHub token from DB", error=str(e))

        github_connected = bool(github_key) and len(github_key) > 10

        slog.info("GitHub connection check",
            has_env_token=bool(os.environ.get("GITHUB_TOKEN")),
            token_length=len(github_key) if github_key else 0,
            connected=github_connected
        )

        return {
            "success": True,
            "models": models_list,
            "models_by_provider": models_by_provider,
            "total": len(models_list),
            "available_providers": [str(p.value) if hasattr(p, 'value') else str(p) for p in available_providers],
            "github_connected": github_connected
        }

    except Exception as e:
        slog.error("Failed to get models for inspector", exception=e)
        return {
            "success": False,
            "models": [],
            "models_by_provider": {},
            "error": str(e),
            "github_connected": False
        }


# =====================================
# 🆕 انتخاب هوشمند و همکاری مدل‌ها
# =====================================

class SmartTaskRequest(BaseModel):
    """درخواست اجرای کار هوشمند"""
    task: str  # توضیح کار
    project_id: str
    auto_select: bool = True  # انتخاب خودکار مدل
    collaborative: bool = True  # همکاری مدل‌ها
    visual_mode: bool = False  # تعامل بصری با صفحه
    # Context
    backend_logs: Optional[List[dict]] = None
    frontend_url: Optional[str] = None
    project_files: Optional[List[dict]] = None
    github_repo: Optional[str] = None  # مثل owner/repo


class TaskAction(BaseModel):
    """یک اقدام در جریان کار"""
    id: str
    model_id: str
    action_type: str  # click, type, navigate, edit, read, analyze, log
    description: str
    target: Optional[str] = None  # مسیر فایل یا سلکتور CSS
    data: Optional[dict] = None
    status: str = "pending"  # pending, running, done, failed
    result: Optional[str] = None


# ذخیره وضعیت کارهای در حال اجرا (در محیط واقعی از Redis استفاده می‌شود)
active_tasks = {}
task_action_queues = {}


def analyze_task_for_model_selection(task: str) -> dict:
    """تحلیل کار برای انتخاب مدل‌های مناسب"""
    task_lower = task.lower()

    capabilities_needed = []
    suggested_models = []

    # تشخیص نیازهای کار
    if any(x in task_lower for x in ["کد", "code", "برنامه", "program", "فایل", "file", "ویرایش", "edit"]):
        capabilities_needed.append("coding")
        suggested_models.extend(["claude-3-5-sonnet", "gpt-4o", "gpt-4-turbo"])

    if any(x in task_lower for x in ["تحلیل", "analyze", "بررسی", "review", "خطا", "error", "باگ", "bug"]):
        capabilities_needed.append("analysis")
        suggested_models.extend(["claude-3-5-sonnet", "gpt-4o", "gemini-1.5-pro"])

    if any(x in task_lower for x in ["امنیت", "security", "آسیب", "vulnerability"]):
        capabilities_needed.append("security")
        suggested_models.extend(["claude-3-5-sonnet", "gpt-4o"])

    if any(x in task_lower for x in ["تست", "test", "آزمایش"]):
        capabilities_needed.append("testing")
        suggested_models.extend(["claude-3-5-sonnet", "gpt-4o"])

    if any(x in task_lower for x in ["صفحه", "page", "کلیک", "click", "بصری", "visual", "ui", "رابط"]):
        capabilities_needed.append("visual")
        suggested_models.extend(["claude-3-5-sonnet", "gpt-4o"])  # مدل‌های با قابلیت vision

    if any(x in task_lower for x in ["گیت", "git", "github", "کامیت", "commit", "پوش", "push"]):
        capabilities_needed.append("git")
        suggested_models.extend(["claude-3-5-sonnet", "gpt-4o"])

    # حذف تکراری‌ها و حفظ ترتیب
    seen = set()
    unique_models = []
    for m in suggested_models:
        if m not in seen:
            seen.add(m)
            unique_models.append(m)

    return {
        "capabilities_needed": capabilities_needed,
        "suggested_models": unique_models[:5],  # حداکثر 5 مدل
        "requires_visual": "visual" in capabilities_needed,
        "requires_git": "git" in capabilities_needed,
        "task_complexity": "complex" if len(capabilities_needed) > 2 else "simple"
    }


@router.post("/inspector/smart-task")
async def execute_smart_task(
    request: SmartTaskRequest,
    db: Session = Depends(get_db)
):
    """
    اجرای کار هوشمند با انتخاب خودکار مدل‌ها و همکاری

    این endpoint:
    1. کار را تحلیل می‌کند
    2. مدل‌های مناسب را انتخاب می‌کند
    3. مدل‌های غیرفعال را موقتاً فعال می‌کند
    4. کار را بین مدل‌ها توزیع می‌کند
    5. نتایج را جمع‌آوری می‌کند
    """
    import uuid

    slog.api_request("POST", "/render/inspector/smart-task",
        task=request.task[:100],
        project_id=request.project_id,
        auto_select=request.auto_select
    )

    task_id = str(uuid.uuid4())[:8]

    try:
        from ...core.models_registry import MODEL_REGISTRY
        from ...services.ai_manager import get_ai_manager
        from ...models.ai_profile import ModelSettings

        # 1. تحلیل کار
        analysis = analyze_task_for_model_selection(request.task)

        # 2. دریافت مدل‌های موجود
        ai_manager = get_ai_manager()
        available_providers = ai_manager.get_available_providers()
        available_provider_names = [str(p.value) if hasattr(p, 'value') else str(p) for p in available_providers]

        # تنظیمات مدل‌ها
        db_settings = db.query(ModelSettings).all()
        settings_map = {s.model_id: s for s in db_settings}

        # 3. انتخاب مدل‌ها
        selected_models = []
        temporarily_enabled = []

        if request.auto_select:
            for model_id in analysis["suggested_models"]:
                if model_id in MODEL_REGISTRY:
                    model = MODEL_REGISTRY[model_id]
                    provider = str(model.provider.value) if hasattr(model.provider, 'value') else str(model.provider)

                    if provider in available_provider_names:
                        setting = settings_map.get(model_id)
                        is_enabled = setting.enabled if setting else True

                        if is_enabled:
                            selected_models.append(model_id)
                        elif request.auto_select:
                            # 🆕 فعال کردن موقت در دیتابیس
                            selected_models.append(model_id)
                            temporarily_enabled.append(model_id)

                            # فعال‌سازی موقت در دیتابیس
                            if setting:
                                setting.enabled = True
                                setting.temporary_enabled = True  # فلگ موقت
                                db.commit()
                                slog.info(f"Temporarily enabled model: {model_id}")
                            else:
                                # ایجاد تنظیمات جدید
                                new_setting = ModelSettings(
                                    model_id=model_id,
                                    enabled=True,
                                    temporary_enabled=True
                                )
                                db.add(new_setting)
                                db.commit()
                                slog.info(f"Created temporary model settings: {model_id}")

        if not selected_models:
            # Fallback به اولین مدل موجود
            for model_id, model in MODEL_REGISTRY.items():
                provider = str(model.provider.value) if hasattr(model.provider, 'value') else str(model.provider)
                if provider in available_provider_names:
                    selected_models.append(model_id)
                    break

        # 4. ایجاد Task
        task_info = {
            "id": task_id,
            "description": request.task,
            "models": selected_models,
            "status": "running",
            "actions": [],
            "analysis": analysis,
            "temporarily_enabled": temporarily_enabled,
            "created_at": datetime.utcnow().isoformat()
        }
        active_tasks[task_id] = task_info

        # 5. اجرای کار (ساده شده - در نسخه کامل از async workers استفاده می‌شود)
        from ...services.ai_base import Message

        # ساخت system prompt برای همکاری
        collab_prompt = f"""# کار تیمی مدل‌ها

شما بخشی از یک تیم هستید که روی این کار کار می‌کنید:
{request.task}

## مدل‌های تیم:
{', '.join(selected_models)}

## قوانین همکاری:
1. هر اقدام خود را با فرمت زیر گزارش دهید:
   [ACTION] نوع: توضیح
   مثال: [ACTION] ANALYZE: در حال بررسی لاگ‌های خطا

2. قبل از ویرایش فایل، بررسی کنید که مدل دیگری روی آن کار نمی‌کند

3. نتایج را به صورت خلاصه و قابل فهم گزارش دهید

## Context پروژه:
- Frontend URL: {request.frontend_url or 'نامشخص'}
- GitHub Repo: {request.github_repo or 'نامشخص'}
"""

        if request.backend_logs:
            collab_prompt += f"\n## آخرین لاگ‌های بک‌اند:\n"
            for log in request.backend_logs[-20:]:
                collab_prompt += f"[{log.get('level', 'info').upper()}] {log.get('message', '')[:100]}\n"

        # اجرای درخواست به مدل‌های انتخاب شده
        results = []
        for model_id in selected_models:
            try:
                messages = [
                    Message(role="system", content=collab_prompt),
                    Message(role="user", content=request.task)
                ]

                response = await ai_manager.generate(
                    model_id=model_id,
                    messages=messages,
                    max_tokens=4096,
                    temperature=0.7,
                )

                # ثبت action
                action = {
                    "id": f"action_{len(task_info['actions'])}",
                    "model_id": model_id,
                    "action_type": "analyze",
                    "description": f"تحلیل و اجرای کار توسط {model_id}",
                    "status": "done",
                    "result": response.content,
                    "tokens_used": response.tokens_used
                }
                task_info["actions"].append(action)

                results.append({
                    "model_id": model_id,
                    "content": response.content,
                    "tokens_used": response.tokens_used,
                    "success": True
                })

            except Exception as e:
                slog.error(f"Model {model_id} failed", exception=e)
                results.append({
                    "model_id": model_id,
                    "content": str(e),
                    "success": False
                })

        # 6. به‌روزرسانی وضعیت
        task_info["status"] = "completed"
        task_info["results"] = results

        # 6.5. 🆕 غیرفعال کردن مدل‌های موقتاً فعال شده
        for model_id in temporarily_enabled:
            setting = db.query(ModelSettings).filter(ModelSettings.model_id == model_id).first()
            if setting and setting.temporary_enabled:
                setting.enabled = False
                setting.temporary_enabled = False
                db.commit()
                slog.info(f"Disabled temporary model: {model_id}")

        # 7. بررسی اتصال GitHub
        from ...models.setting import Setting
        import os
        github_key = os.environ.get("GITHUB_TOKEN", "")
        if not github_key:
            github_key = Setting.get_value(db, "api_key_github") or ""
            if github_key:
                os.environ["GITHUB_TOKEN"] = github_key
        github_connected = bool(github_key) and len(github_key) > 10

        # 8. ساخت پاسخ یکپارچه
        combined_content = ""
        total_tokens = 0
        for r in results:
            if r.get("success"):
                combined_content += f"\n\n**{r['model_id']}:**\n{r['content']}"
                total_tokens += r.get("tokens_used", 0)
            else:
                combined_content += f"\n\n**{r['model_id']}:** ❌ خطا: {r['content']}"

        return {
            "success": True,
            "task_id": task_id,
            "task": task_info,
            "analysis": analysis,
            "selected_models": selected_models,
            "temporarily_enabled": temporarily_enabled,
            "results": results,
            "content": combined_content.strip() or "کار انجام شد.",
            "tokens_used": total_tokens,
            "github_connected": github_connected,
            "actions": task_info["actions"]
        }

    except Exception as e:
        slog.error("Smart task failed", exception=e)
        if task_id in active_tasks:
            active_tasks[task_id]["status"] = "failed"
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/inspector/task/{task_id}")
async def get_task_status(task_id: str):
    """دریافت وضعیت یک کار"""
    if task_id not in active_tasks:
        return {
            "success": False,
            "error": "Task not found"
        }

    return {
        "success": True,
        "task": active_tasks[task_id]
    }


@router.post("/inspector/task/{task_id}/action")
async def add_task_action(task_id: str, action: TaskAction):
    """افزودن یک اقدام به کار (برای لاگ real-time)"""
    if task_id not in active_tasks:
        return {
            "success": False,
            "error": "Task not found"
        }

    active_tasks[task_id]["actions"].append({
        "id": action.id,
        "model_id": action.model_id,
        "action_type": action.action_type,
        "description": action.description,
        "target": action.target,
        "status": action.status,
        "timestamp": datetime.utcnow().isoformat()
    })

    return {
        "success": True,
        "action_count": len(active_tasks[task_id]["actions"])
    }


@router.get("/inspector/github/files/{owner}/{repo}")
async def get_github_files(
    owner: str,
    repo: str,
    path: str = "",
    db: Session = Depends(get_db)
):
    """دریافت فایل‌های GitHub برای ویرایش"""
    try:
        from ...models.setting import Setting
        import aiohttp

        # دریافت توکن GitHub
        token_setting = db.query(Setting).filter(Setting.key == "api_key_github").first()
        if not token_setting:
            return {
                "success": False,
                "error": "توکن GitHub تنظیم نشده است"
            }

        headers = {
            "Authorization": f"token {token_setting.value}",
            "Accept": "application/vnd.github.v3+json"
        }

        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "success": True,
                        "files": data if isinstance(data, list) else [data],
                        "path": path
                    }
                else:
                    error = await response.text()
                    return {
                        "success": False,
                        "error": f"GitHub API error: {response.status}"
                    }

    except Exception as e:
        slog.error("GitHub files fetch failed", exception=e)
        return {
            "success": False,
            "error": str(e)
        }


@router.put("/inspector/github/files/{owner}/{repo}")
async def update_github_file(
    owner: str,
    repo: str,
    path: str,
    content: str,
    message: str,
    sha: str,
    db: Session = Depends(get_db)
):
    """ویرایش فایل در GitHub"""
    try:
        from ...models.setting import Setting
        import aiohttp
        import base64

        # دریافت توکن GitHub
        token_setting = db.query(Setting).filter(Setting.key == "api_key_github").first()
        if not token_setting:
            return {
                "success": False,
                "error": "توکن GitHub تنظیم نشده است"
            }

        headers = {
            "Authorization": f"token {token_setting.value}",
            "Accept": "application/vnd.github.v3+json"
        }

        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"

        # محتوا باید base64 باشد
        content_b64 = base64.b64encode(content.encode()).decode()

        payload = {
            "message": message,
            "content": content_b64,
            "sha": sha
        }

        async with aiohttp.ClientSession() as session:
            async with session.put(url, headers=headers, json=payload) as response:
                if response.status in [200, 201]:
                    data = await response.json()
                    return {
                        "success": True,
                        "commit": data.get("commit", {})
                    }
                else:
                    error = await response.text()
                    return {
                        "success": False,
                        "error": f"GitHub API error: {response.status}"
                    }

    except Exception as e:
        slog.error("GitHub file update failed", exception=e)
        return {
            "success": False,
            "error": str(e)
        }


# =====================================
# 🆕 Browser Automation Endpoints
# =====================================

class BrowserActionRequest(BaseModel):
    """درخواست اکشن مرورگر"""
    session_id: str
    action: str  # analyze, click, type, scroll, find_login, login, screenshot
    params: Optional[dict] = {}


class BrowserSessionRequest(BaseModel):
    """درخواست ایجاد سشن مرورگر"""
    url: str
    session_id: Optional[str] = None


@router.post("/inspector/browser/session")
async def create_browser_session(request: BrowserSessionRequest):
    """
    ایجاد یک سشن مرورگر جدید برای کنترل با AI

    این endpoint یک مرورگر headless باز می‌کند و آماده دریافت دستورات می‌شود
    """
    import uuid
    from ...services.browser_automation import create_session

    session_id = request.session_id or str(uuid.uuid4())[:8]

    slog.api_request("POST", "/inspector/browser/session",
        url=request.url,
        session_id=session_id
    )

    try:
        session = await create_session(session_id, request.url)
        screenshot = await session.take_screenshot()
        page_info = await session.get_page_info()

        return {
            "success": True,
            "session_id": session_id,
            "page_info": page_info,
            "screenshot": screenshot,
            "message": f"مرورگر باز شد: {page_info.get('title', 'Unknown')}"
        }
    except Exception as e:
        slog.error("Browser session creation failed", exception=e)
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/inspector/browser/action")
async def execute_browser_action(request: BrowserActionRequest):
    """
    اجرای یک اکشن در مرورگر

    action types:
    - analyze: تحلیل صفحه
    - find_login: پیدا کردن فرم لاگین
    - login: انجام لاگین کامل (params: username, password)
    - click: کلیک (params: selector یا x,y)
    - type: تایپ (params: selector, text)
    - scroll: اسکرول (params: delta_y)
    - screenshot: گرفتن screenshot
    """
    from ...services.browser_automation import get_session, execute_ai_action

    slog.api_request("POST", "/inspector/browser/action",
        session_id=request.session_id,
        action=request.action
    )

    try:
        session = await get_session(request.session_id)
        if not session:
            return {
                "success": False,
                "error": "Session not found. Create a session first."
            }

        result = await execute_ai_action(session, request.action, request.params or {})

        return {
            "success": result.get("success", False),
            "action": request.action,
            "cursor_position": result.get("cursor_position"),
            "message": result.get("message", ""),
            "data": {k: v for k, v in result.items() if k not in ["success", "cursor_position", "message"]}
        }

    except Exception as e:
        slog.error("Browser action failed", exception=e)
        return {
            "success": False,
            "error": str(e)
        }


@router.delete("/inspector/browser/session/{session_id}")
async def close_browser_session(session_id: str):
    """بستن سشن مرورگر"""
    from ...services.browser_automation import close_session

    try:
        await close_session(session_id)
        return {"success": True, "message": "Session closed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


class AIInteractRequest(BaseModel):
    """درخواست تعامل AI با صفحه"""
    task: str
    url: str
    model_id: Optional[str] = None  # اگر None باشد، خودکار انتخاب می‌شود
    max_steps: Optional[int] = 10
    debug: Optional[bool] = False  # 🆕 برای دیدن پاسخ خام AI


def get_best_vision_model(ai_manager, db, allow_temporary_enable: bool = True) -> tuple:
    """
    انتخاب بهترین مدل vision موجود

    اولویت:
    1. Claude (بهترین برای تحلیل و تصمیم‌گیری)
    2. GPT-4o (قدرتمند در vision)
    3. Gemini (سریع و مقرون به صرفه)

    Returns:
        tuple: (model_id, temporarily_enabled: bool)
    """
    from ...core.models_registry import get_vision_models, MODEL_REGISTRY
    from ...models.ai_profile import ModelSettings

    # مدل‌های vision به ترتیب اولویت
    priority_order = [
        "claude-sonnet-4-20250514",
        "claude-3-5-sonnet-20241022",
        "gpt-4o",
        "gpt-4-turbo",
        "gemini-2.5-pro",
        "gemini-2.0-flash",
        "gpt-4o-mini",
    ]

    # دریافت provider های فعال
    available_providers = []
    try:
        available_providers = ai_manager.get_available_providers()
        available_provider_names = [str(p.value) if hasattr(p, 'value') else str(p) for p in available_providers]
    except:
        available_provider_names = []

    # دریافت تنظیمات مدل‌ها
    try:
        db_settings = db.query(ModelSettings).all() if db else []
        settings_map = {s.model_id: s for s in db_settings}
    except:
        settings_map = {}

    # 🆕 لیست مدل‌های غیرفعال که می‌توانند موقتاً فعال شوند
    disabled_vision_models = []

    # پیدا کردن اولین مدل فعال موجود
    for model_id in priority_order:
        if model_id in MODEL_REGISTRY:
            model = MODEL_REGISTRY[model_id]
            provider = str(model.provider.value) if hasattr(model.provider, 'value') else str(model.provider)

            # بررسی فعال بودن provider
            if provider not in available_provider_names:
                continue

            # بررسی قابلیت vision
            if not model.supports_images:
                continue

            # بررسی تنظیمات کاربر
            setting = settings_map.get(model_id)
            if setting and not setting.enabled:
                # 🆕 ذخیره برای فعال‌سازی موقت
                disabled_vision_models.append((model_id, setting))
                continue

            slog.info(f"Selected vision model (enabled): {model_id}")
            return model_id, False  # False = not temporarily enabled

    # 🆕 اگر مدل فعال پیدا نشد و اجازه فعال‌سازی موقت داریم
    if allow_temporary_enable and disabled_vision_models:
        model_id, setting = disabled_vision_models[0]  # بهترین مدل غیرفعال

        # فعال‌سازی موقت در دیتابیس
        slog.info(f"Temporarily enabling vision model: {model_id}")
        setting.enabled = True
        setting.temporary_enabled = True
        db.commit()

        return model_id, True  # True = temporarily enabled

    # Fallback به اولین مدل vision موجود
    vision_models = get_vision_models()
    for model in vision_models:
        provider = str(model.provider.value) if hasattr(model.provider, 'value') else str(model.provider)
        if provider in available_provider_names:
            return model.id, False

    return None, False


@router.post("/inspector/ai-interact")
async def ai_interact_with_page(
    request: AIInteractRequest,
    db: Session = Depends(get_db)
):
    """
    🤖 تعامل هوشمند AI با صفحه وب

    این endpoint یک AI Agent کامل است که می‌تواند هر دستوری را اجرا کند:
    - صفحه را می‌بیند (screenshot)
    - تصمیم می‌گیرد چه کاری انجام دهد
    - اقدام می‌کند (کلیک، تایپ، اسکرول)
    - نتیجه را می‌بیند و تکرار می‌کند تا task کامل شود

    مدل انتخابی:
    - اگر model_id داده نشود، بهترین مدل vision موجود انتخاب می‌شود
    - اولویت: Claude > GPT-4o > Gemini

    مثال‌ها:
    - "لاگین کن" → فرم لاگین را پیدا می‌کند و لاگین می‌کند
    - "برو به منوی Settings" → منو را پیدا می‌کند و کلیک می‌کند
    - "اسکرول کن تا قسمت Contact" → اسکرول می‌کند تا آن قسمت را پیدا کند
    - "دکمه Submit را بزن" → دکمه را پیدا می‌کند و کلیک می‌کند
    """
    import uuid
    from ...services.browser_automation import create_session, execute_ai_agent_task, close_session
    from ...services.ai_manager import get_ai_manager
    from ...models.ai_profile import ModelSettings

    session_id = str(uuid.uuid4())[:8]
    temporarily_enabled = False  # 🆕 آیا مدل موقتاً فعال شده

    # 1. دریافت AI manager
    ai_manager = get_ai_manager()

    # 2. انتخاب مدل vision (داینامیک یا مشخص شده)
    selected_model = request.model_id
    if not selected_model:
        selected_model, temporarily_enabled = get_best_vision_model(ai_manager, db)

    if not selected_model:
        return {
            "success": False,
            "error": "هیچ مدل vision فعالی یافت نشد. لطفاً API key یکی از مدل‌های vision (OpenAI, Claude, Gemini) را تنظیم کنید."
        }

    slog.api_request("POST", "/inspector/ai-interact",
        task=request.task[:100],
        url=request.url,
        model_id=selected_model,
        temporarily_enabled=temporarily_enabled
    )

    try:
        # 3. باز کردن مرورگر
        session = await create_session(session_id, request.url)
        page_info = await session.get_page_info()

        slog.info(f"Browser opened", session_id=session_id, title=page_info.get('title'), model=selected_model,
            temp_enabled=temporarily_enabled)

        # 4. اجرای task با AI Agent
        result = await execute_ai_agent_task(
            session=session,
            task=request.task,
            ai_manager=ai_manager,
            model_id=selected_model,
            max_steps=request.max_steps
        )

        # 5. فرمت کردن اکشن‌ها برای نمایش
        formatted_actions = []
        for action in result.get("actions", []):
            formatted_actions.append({
                "step": action.get("step"),
                "action": action.get("action"),
                "message": action.get("description") or action.get("thinking", "")[:100],
                "element": action.get("element", ""),
                "status": action.get("status", "done")
            })

        # 🆕 دریافت اطلاعات صفحه بعد از اجرای task (URL نهایی)
        final_page_info = await session.get_page_info()
        slog.info(f"Final page after task",
            final_url=final_page_info.get('url'),
            final_title=final_page_info.get('title')
        )

        response_data = {
            "success": result.get("success", False),
            "session_id": session_id,
            "task": request.task,
            "selected_model": selected_model,
            "actions": formatted_actions,
            "cursor_positions": result.get("cursor_positions", []),
            "final_screenshot": result.get("final_screenshot"),
            "total_steps": result.get("total_steps", 0),
            "message": f"کار انجام شد: {result.get('total_steps', 0)} مرحله (مدل: {selected_model})",
            "page_info": page_info,
            # 🆕 URL نهایی برای به‌روزرسانی iframe فرانت‌اند
            "final_url": final_page_info.get('url'),
            "final_page_info": final_page_info
        }

        # 🆕 اضافه کردن debug info
        if request.debug:
            response_data["debug"] = {
                "raw_actions": result.get("actions", []),
                "ai_responses": result.get("ai_responses", [])
            }

        # 🆕 غیرفعال کردن مدل موقتاً فعال شده
        if temporarily_enabled and selected_model:
            try:
                setting = db.query(ModelSettings).filter(ModelSettings.model_id == selected_model).first()
                if setting and setting.temporary_enabled:
                    setting.enabled = False
                    setting.temporary_enabled = False
                    db.commit()
                    slog.info(f"Disabled temporarily enabled model: {selected_model}")
            except Exception as cleanup_error:
                slog.warning(f"Failed to disable temporary model", error=str(cleanup_error))

        # 🆕 اضافه کردن اطلاعات فعال‌سازی موقت به response
        response_data["temporarily_enabled"] = temporarily_enabled

        # 🆕 بستن session مرورگر بعد از اتمام کار (جلوگیری از نشت حافظه)
        try:
            await close_session(session_id)
            slog.info(f"Browser session closed successfully: {session_id}")
        except Exception as close_error:
            slog.warning(f"Failed to close browser session", session_id=session_id, error=str(close_error))

        return response_data

    except Exception as e:
        slog.error("AI interaction failed", exception=e)

        # 🆕 غیرفعال کردن مدل موقت حتی در صورت خطا
        if temporarily_enabled and selected_model:
            try:
                setting = db.query(ModelSettings).filter(ModelSettings.model_id == selected_model).first()
                if setting and setting.temporary_enabled:
                    setting.enabled = False
                    setting.temporary_enabled = False
                    db.commit()
                    slog.info(f"Disabled temporarily enabled model after error: {selected_model}")
            except:
                pass

        try:
            await close_session(session_id)
        except:
            pass
        return {
            "success": False,
            "error": str(e),
            "actions": []
        }


# =====================================
# 🆕 اسکن بصری و کلیک مستقیم
# =====================================

class VisualScanRequest(BaseModel):
    """درخواست اسکن بصری صفحه"""
    url: str
    search_text: str  # متنی که باید پیدا شود
    click_on_find: bool = True  # آیا بعد از پیدا کردن کلیک کند


@router.post("/inspector/get-elements")
async def get_page_elements(url: str):
    """
    🔍 دریافت همه المان‌های صفحه برای اسکن واقعی در فرانت‌اند

    این endpoint صفحه را باز می‌کند و لیست همه المان‌های قابل کلیک را
    با موقعیت دقیقشان برمی‌گرداند. فرانت‌اند می‌تواند این المان‌ها را
    یکی یکی اسکن کند.
    """
    import uuid
    from ...services.browser_automation import create_session, close_session

    session_id = str(uuid.uuid4())[:8]

    slog.api_request("POST", "/inspector/get-elements", url=url)

    try:
        session = await create_session(session_id, url)

        # استخراج همه المان‌های قابل کلیک
        elements = await session.extract_interactive_elements()

        # مرتب‌سازی بر اساس موقعیت: از بالا به پایین، چپ به راست
        elements_sorted = sorted(elements, key=lambda e: (e["center_y"], e["center_x"]))

        await close_session(session_id)

        return {
            "success": True,
            "elements": elements_sorted,
            "total": len(elements_sorted)
        }

    except Exception as e:
        slog.error("Get elements failed", exception=e)
        try:
            await close_session(session_id)
        except:
            pass
        return {"success": False, "error": str(e), "elements": []}


@router.post("/inspector/find-and-click")
async def find_element_and_click(url: str, search_text: str):
    """
    🔍 جستجوی Ctrl+F style - پیدا کردن متن در صفحه و کلیک

    مثل Ctrl+F مرورگر:
    1. متن رو در صفحه جستجو میکنه
    2. اگه پیدا شد، المان رو highlight میکنه (چشمک)
    3. scroll میکنه تا دیده بشه
    4. کلیک میکنه

    برمیگردونه:
    - found_elements: لیست همه المان‌های پیدا شده با موقعیت
    - clicked_index: کدوم کلیک شد
    """
    import uuid
    from ...services.browser_automation import create_session, close_session

    session_id = str(uuid.uuid4())[:8]
    slog.api_request("POST", "/inspector/find-and-click", url=url, search_text=search_text)

    try:
        session = await create_session(session_id, url)

        if not session.page:
            await close_session(session_id)
            return {"success": False, "error": "Page not loaded"}

        page = session.page
        search_clean = search_text.strip()

        slog.info(f"🔍 Ctrl+F search for: '{search_clean}'")

        # 1. جستجوی متن با getByText (مثل Ctrl+F)
        locator = page.get_by_text(search_clean, exact=False)
        count = await locator.count()

        slog.info(f"Found {count} matches for '{search_clean}'")

        if count == 0:
            await close_session(session_id)
            return {
                "success": False,
                "error": f"'{search_text}' در این صفحه پیدا نشد",
                "found_count": 0
            }

        # 2. جمع‌آوری اطلاعات همه المان‌های پیدا شده
        found_elements = []
        for i in range(min(count, 20)):  # حداکثر 20 تا
            try:
                el = locator.nth(i)
                is_visible = await el.is_visible()
                if not is_visible:
                    continue

                box = await el.bounding_box()
                if not box or box["width"] < 3 or box["height"] < 3:
                    continue

                text = await el.text_content()
                text = (text or "").strip()[:100]

                found_elements.append({
                    "index": i,
                    "text": text,
                    "box": box,
                    "center_x": box["x"] + box["width"] / 2,
                    "center_y": box["y"] + box["height"] / 2,
                    "percent_x": round((box["x"] + box["width"]/2) / session.viewport["width"] * 100, 1),
                    "percent_y": round((box["y"] + box["height"]/2) / session.viewport["height"] * 100, 1)
                })
            except:
                continue

        if not found_elements:
            await close_session(session_id)
            return {
                "success": False,
                "error": f"'{search_text}' پیدا شد ولی visible نیست",
                "found_count": count
            }

        slog.info(f"Found {len(found_elements)} visible elements")

        # 3. پیدا کردن بهترین المان برای کلیک
        # اولویت: المان کوتاه‌تر (دقیق‌تر) و در موقعیت طبیعی
        found_elements.sort(key=lambda e: (len(e["text"]), e["center_y"]))
        best_element = found_elements[0]
        best_index = best_element["index"]

        slog.info(f"Best match: '{best_element['text'][:30]}' at ({best_element['percent_x']}%, {best_element['percent_y']}%)")

        # 4. Scroll تا المان دیده بشه
        el = locator.nth(best_index)
        await el.scroll_into_view_if_needed()
        await session.wait(300)

        # 5. Highlight animation (چشمک زدن)
        try:
            await el.evaluate("""el => {
                const originalOutline = el.style.outline;
                const originalBg = el.style.backgroundColor;
                const originalTransition = el.style.transition;

                el.style.transition = 'all 0.2s ease';
                let count = 0;
                const blink = setInterval(() => {
                    if (count % 2 === 0) {
                        el.style.outline = '3px solid #00ff00';
                        el.style.backgroundColor = 'rgba(0, 255, 0, 0.3)';
                    } else {
                        el.style.outline = originalOutline;
                        el.style.backgroundColor = originalBg;
                    }
                    count++;
                    if (count >= 6) {
                        clearInterval(blink);
                        el.style.outline = originalOutline;
                        el.style.backgroundColor = originalBg;
                        el.style.transition = originalTransition;
                    }
                }, 150);
            }""")
            await session.wait(1000)  # صبر برای انیمیشن
        except Exception as e:
            slog.warning(f"Highlight failed: {e}")

        # 6. آپدیت موقعیت بعد از scroll
        box = await el.bounding_box()
        if box:
            best_element["box"] = box
            best_element["center_x"] = box["x"] + box["width"] / 2
            best_element["center_y"] = box["y"] + box["height"] / 2
            best_element["percent_x"] = round((box["x"] + box["width"]/2) / session.viewport["width"] * 100, 1)
            best_element["percent_y"] = round((box["y"] + box["height"]/2) / session.viewport["height"] * 100, 1)

        # 7. کلیک!
        await el.click(timeout=5000)
        slog.info(f"✅ Clicked on '{best_element['text'][:30]}'")

        # 8. صبر برای navigation
        await session.wait(1500)
        new_url = page.url

        await close_session(session_id)

        return {
            "success": True,
            "found": best_element["text"],
            "found_count": len(found_elements),
            "found_elements": found_elements[:5],  # 5 تای اول برای نمایش
            "clicked_index": best_index,
            "position": best_element,
            "url_changed": new_url != url,
            "new_url": new_url
        }

    except Exception as e:
        slog.error("Find and click failed", exception=e)
        try:
            await close_session(session_id)
        except:
            pass
        return {"success": False, "error": str(e)}


@router.post("/inspector/click-at")
async def click_at_position(url: str, x: float, y: float):
    """
    🖱️ کلیک در موقعیت مشخص (پیکسل)
    """
    import uuid
    from ...services.browser_automation import create_session, close_session

    session_id = str(uuid.uuid4())[:8]

    try:
        session = await create_session(session_id, url)
        result = await session.click(x, y)
        await session.wait(1000)
        new_url = session.page.url if session.page else url
        await close_session(session_id)

        return {
            "success": True,
            "clicked_at": {"x": x, "y": y},
            "url_changed": new_url != url,
            "new_url": new_url
        }

    except Exception as e:
        slog.error("Click failed", exception=e)
        try:
            await close_session(session_id)
        except:
            pass
        return {"success": False, "error": str(e)}


@router.post("/inspector/visual-scan")
async def visual_scan_and_click(request: VisualScanRequest):
    """
    🔍 اسکن بصری صفحه با نوارهای متحرک

    این endpoint:
    1. صفحه را باز می‌کند
    2. متن مورد نظر را جستجو می‌کند
    3. مختصات اسکن را برای انیمیشن نوار برمی‌گرداند
    4. اگر click_on_find=true باشد، کلیک می‌کند

    Response شامل:
    - scan_animation: مراحل انیمیشن نوار اسکن
    - target_position: موقعیت هدف (درصد)
    - clicked: آیا کلیک شد
    """
    import uuid
    from ...services.browser_automation import create_session, close_session

    session_id = str(uuid.uuid4())[:8]

    slog.api_request("POST", "/inspector/visual-scan",
        url=request.url,
        search_text=request.search_text
    )

    try:
        # 1. باز کردن مرورگر
        session = await create_session(session_id, request.url)

        # 2. جستجوی متن
        if request.click_on_find:
            result = await session.scan_and_click_text(request.search_text)
        else:
            result = await session.find_text_on_page(request.search_text)

        # 3. ساخت انیمیشن اسکن
        # نوار عمودی از چپ به راست، نوار افقی از بالا به پایین
        scan_animation = {
            "vertical_bar": [],   # نوار عمودی - حرکت افقی
            "horizontal_bar": [], # نوار افقی - حرکت عمودی
            "intersection": None  # نقطه تقاطع (هدف)
        }

        if result.get("found") or result.get("success"):
            target = result.get("element") or result.get("clicked_element")
            if target:
                target_x = target["percent_x"]
                target_y = target["percent_y"]

                # انیمیشن نوار عمودی (از چپ به راست تا x هدف)
                for x in range(0, int(target_x) + 1, 5):
                    scan_animation["vertical_bar"].append({"x": x, "duration": 30})

                # انیمیشن نوار افقی (از بالا به پایین تا y هدف)
                for y in range(0, int(target_y) + 1, 5):
                    scan_animation["horizontal_bar"].append({"y": y, "duration": 30})

                # نقطه تقاطع
                scan_animation["intersection"] = {
                    "x": target_x,
                    "y": target_y,
                    "text": target.get("text", "")[:50]
                }

        # 4. گرفتن screenshot
        screenshot = await session.take_screenshot()

        # 5. بستن session
        await close_session(session_id)

        return {
            "success": result.get("found", False) or result.get("success", False),
            "scan_animation": scan_animation,
            "target_position": result.get("cursor_position") or (
                {"x": result["element"]["percent_x"], "y": result["element"]["percent_y"]}
                if result.get("element") else None
            ),
            "clicked": request.click_on_find and result.get("success", False),
            "url_changed": result.get("url_changed", False),
            "final_url": result.get("url", request.url),
            "total_matches": result.get("total_matches", 0),
            "screenshot": screenshot,
            "message": f"پیدا شد: {result.get('element', {}).get('text', '')[:50]}" if result.get("found") else "پیدا نشد"
        }

    except Exception as e:
        slog.error("Visual scan failed", exception=e)
        try:
            await close_session(session_id)
        except:
            pass
        return {
            "success": False,
            "error": str(e),
            "scan_animation": {"vertical_bar": [], "horizontal_bar": [], "intersection": None}
        }


# =====================================
# 🆕 بازرسی همزمان فرانت‌اند و بک‌اند
# =====================================

class SyncInspectionRequest(BaseModel):
    """درخواست بازرسی همزمان فرانت‌اند و بک‌اند"""
    task: str  # دستور کار
    project_id: str
    frontend_url: Optional[str] = None
    backend_logs: Optional[List[dict]] = None
    # مدل‌های انتخابی
    frontend_model_ids: Optional[List[str]] = None  # مدل‌های فرانت
    backend_model_ids: Optional[List[str]] = None   # مدل‌های بک‌اند
    auto_select: bool = True  # انتخاب خودکار مدل‌ها
    max_steps: int = 10


@router.post("/inspector/sync-inspection")
async def synchronized_inspection(
    request: SyncInspectionRequest,
    db: Session = Depends(get_db)
):
    """
    🔄 بازرسی همزمان فرانت‌اند و بک‌اند

    این endpoint:
    1. مدل‌های فرانت را روی صفحه پیش‌نمایش کار می‌گذارد
    2. همزمان مدل‌های بک‌اند را روی لاگ‌ها می‌گذارد
    3. نتایج هر دو را در لحظه گزارش می‌کند
    4. اگر فرانت اقدامی انجام دهد، بک‌اند لاگ مربوطه را رصد می‌کند
    """
    import asyncio
    from ...services.ai_manager import get_ai_manager
    from ...models.ai_profile import ModelSettings
    from ...services.ai_base import Message

    slog.api_request("POST", "/inspector/sync-inspection",
        task=request.task[:100],
        project_id=request.project_id
    )

    try:
        ai_manager = get_ai_manager()
        available_providers = ai_manager.get_available_providers()
        available_provider_names = [str(p.value) if hasattr(p, 'value') else str(p) for p in available_providers]

        # دریافت تنظیمات مدل‌ها
        db_settings = db.query(ModelSettings).all()
        settings_map = {s.model_id: s for s in db_settings}

        # انتخاب مدل‌ها
        frontend_models = request.frontend_model_ids or []
        backend_models = request.backend_model_ids or []

        if request.auto_select:
            # انتخاب خودکار بهترین مدل‌های vision برای فرانت
            if not frontend_models:
                # 🆕 get_best_vision_model returns tuple (model_id, temporarily_enabled)
                vision_result = get_best_vision_model(ai_manager, db)
                if vision_result and vision_result[0]:
                    frontend_models = [vision_result[0]]

            # انتخاب خودکار مدل‌های تحلیل برای بک‌اند
            if not backend_models:
                from ...core.models_registry import MODEL_REGISTRY
                analysis_models = ["claude-sonnet-4-20250514", "gpt-4o", "gemini-2.5-pro"]
                for model_id in analysis_models:
                    if model_id in MODEL_REGISTRY:
                        model = MODEL_REGISTRY[model_id]
                        provider = str(model.provider.value) if hasattr(model.provider, 'value') else str(model.provider)
                        if provider in available_provider_names:
                            setting = settings_map.get(model_id)
                            if not setting or setting.enabled:
                                backend_models = [model_id]
                                break

        # نتایج
        results = {
            "frontend": {"model": frontend_models, "actions": [], "status": "pending"},
            "backend": {"model": backend_models, "actions": [], "status": "pending"},
            "sync_events": []  # رویدادهای همگام‌سازی
        }

        # ==================
        # تابع تحلیل بک‌اند
        # ==================
        async def analyze_backend_logs():
            if not backend_models or not request.backend_logs:
                results["backend"]["status"] = "skipped"
                return

            results["backend"]["status"] = "running"

            backend_prompt = f"""شما یک تحلیل‌گر لاگ بک‌اند هستید.

## وظیفه:
{request.task}

## لاگ‌های بک‌اند:
```
"""
            for log in request.backend_logs[-50:]:
                level = log.get('level', 'info').upper()
                timestamp = log.get('timestamp', '')[:19]
                message = log.get('message', '')[:200]
                backend_prompt += f"[{timestamp}] {level}: {message}\n"

            backend_prompt += """```

## وظیفه شما:
1. لاگ‌ها را تحلیل کنید
2. خطاها و هشدارها را شناسایی کنید
3. اگر مشکلی وجود دارد، راه‌حل پیشنهاد دهید
4. گزارش مختصر بدهید

فرمت پاسخ:
- خلاصه: ...
- خطاها: ...
- پیشنهادات: ...
"""

            for model_id in backend_models:
                try:
                    messages = [
                        Message(role="system", content="شما یک تحلیل‌گر متخصص لاگ‌های سرور هستید."),
                        Message(role="user", content=backend_prompt)
                    ]

                    response = await ai_manager.generate(
                        model_id=model_id,
                        messages=messages,
                        max_tokens=2048,
                        temperature=0.3
                    )

                    results["backend"]["actions"].append({
                        "model_id": model_id,
                        "type": "analysis",
                        "content": response.content,
                        "tokens_used": response.tokens_used,
                        "success": True
                    })

                    # رویداد همگام‌سازی
                    results["sync_events"].append({
                        "time": datetime.utcnow().isoformat(),
                        "source": "backend",
                        "model": model_id,
                        "event": "تحلیل لاگ‌ها کامل شد"
                    })

                except Exception as e:
                    results["backend"]["actions"].append({
                        "model_id": model_id,
                        "type": "error",
                        "content": str(e),
                        "success": False
                    })

            results["backend"]["status"] = "completed"

        # ==================
        # تابع تعامل فرانت‌اند
        # ==================
        async def interact_with_frontend():
            if not frontend_models or not request.frontend_url:
                results["frontend"]["status"] = "skipped"
                return

            results["frontend"]["status"] = "running"

            try:
                from ...services.browser_automation import create_session, execute_ai_agent_task, close_session, PLAYWRIGHT_AVAILABLE

                if not PLAYWRIGHT_AVAILABLE:
                    results["frontend"]["status"] = "error"
                    results["frontend"]["actions"].append({
                        "type": "error",
                        "content": "Playwright not installed. Please install: pip install playwright && playwright install chromium"
                    })
                    return

                import uuid
                session_id = str(uuid.uuid4())[:8]

                session = await create_session(session_id, request.frontend_url)

                for model_id in frontend_models:
                    result = await execute_ai_agent_task(
                        session=session,
                        task=request.task,
                        ai_manager=ai_manager,
                        model_id=model_id,
                        max_steps=request.max_steps
                    )

                    results["frontend"]["actions"].append({
                        "model_id": model_id,
                        "type": "interaction",
                        "steps": result.get("actions", []),
                        "cursor_positions": result.get("cursor_positions", []),
                        "success": result.get("success", False)
                    })

                    # رویدادهای همگام‌سازی برای هر اقدام
                    for action in result.get("actions", []):
                        results["sync_events"].append({
                            "time": datetime.utcnow().isoformat(),
                            "source": "frontend",
                            "model": model_id,
                            "event": f"{action.get('action')}: {action.get('description', '')[:50]}"
                        })

                await close_session(session_id)
                results["frontend"]["status"] = "completed"

            except Exception as e:
                results["frontend"]["status"] = "error"
                results["frontend"]["actions"].append({
                    "type": "error",
                    "content": str(e)
                })

        # ==================
        # اجرای همزمان
        # ==================
        await asyncio.gather(
            analyze_backend_logs(),
            interact_with_frontend()
        )

        # بررسی اتصال GitHub
        from ...models.setting import Setting
        import os
        github_key = os.environ.get("GITHUB_TOKEN", "")
        if not github_key:
            github_key = Setting.get_value(db, "api_key_github") or ""
            if github_key:
                os.environ["GITHUB_TOKEN"] = github_key
        github_connected = bool(github_key) and len(github_key) > 10

        return {
            "success": True,
            "task": request.task,
            "results": results,
            "frontend_models": frontend_models,
            "backend_models": backend_models,
            "github_connected": github_connected,
            "message": f"بازرسی همزمان کامل شد - فرانت: {len(results['frontend']['actions'])} اقدام، بک‌اند: {len(results['backend']['actions'])} تحلیل"
        }

    except Exception as e:
        slog.error("Sync inspection failed", exception=e)
        return {
            "success": False,
            "error": str(e)
        }


# ============================================
# 🆕🆕🆕 Live Action Tracking - رصد لحظه‌ای فعالیت کاربر
# ============================================

class AnalyzeActionRequest(BaseModel):
    """درخواست تحلیل اقدام کاربر"""
    url: str
    action_type: str  # click, scroll, input
    position: dict  # {x: number, y: number}
    project_id: str
    selected_models: Optional[List[str]] = None


class AnalyzeErrorRequest(BaseModel):
    """درخواست تحلیل خطا از GitHub"""
    project_id: str
    error_message: str
    log_details: Optional[str] = None
    source_hint: Optional[str] = None
    selected_models: Optional[List[str]] = None


@router.post("/inspector/analyze-action")
async def analyze_user_action(
    request: AnalyzeActionRequest,
    db: Session = Depends(get_db)
):
    """
    🎯 تحلیل سریع اقدام کاربر - بدون Playwright

    این endpoint سریع پاسخ می‌دهد و فقط لاگ‌های بک‌اند را برای خطا چک می‌کند.
    """
    slog.api_request("POST", "/inspector/analyze-action",
        action_type=request.action_type,
        position=request.position
    )

    try:
        # تولید توضیح ساده بر اساس نوع عمل
        action_type_fa = {
            "click": "کلیک",
            "scroll": "اسکرول",
            "input": "تایپ",
            "navigate": "ناوبری"
        }

        action_description = f"{action_type_fa.get(request.action_type, 'عملیات')} در موقعیت ({request.position.get('x', 0):.0f}%, {request.position.get('y', 0):.0f}%)"

        # بررسی لاگ‌های بک‌اند برای خطا
        backend_status = None
        has_error = False
        error_info = None

        from ...models.project import Project
        project = db.query(Project).filter(Project.id == request.project_id).first()

        if project:
            # بررسی render_service_ids
            service_ids = []
            if hasattr(project, 'render_service_ids') and project.render_service_ids:
                if isinstance(project.render_service_ids, str):
                    service_ids = [s.strip() for s in project.render_service_ids.split(',') if s.strip()]
                else:
                    service_ids = project.render_service_ids

            if service_ids:
                # دریافت لاگ‌های اخیر (10 ثانیه آخر)
                recent_logs = db.query(RenderLog).filter(
                    RenderLog.service_id.in_(service_ids),
                    RenderLog.created_at >= datetime.utcnow() - timedelta(seconds=10)
                ).order_by(desc(RenderLog.created_at)).limit(5).all()

                error_log = next((log for log in recent_logs if log.level == 'error'), None)

                if error_log:
                    has_error = True
                    backend_status = {
                        "has_error": True,
                        "message": f"⚠️ خطا در بک‌اند: {error_log.message[:100] if error_log.message else 'نامشخص'}"
                    }
                    error_info = {
                        "message": error_log.message or "خطای ناشناخته",
                        "log_details": f"[{error_log.level}] {error_log.message}"
                    }
                else:
                    backend_status = {
                        "has_error": False,
                        "message": "✅ بک‌اند: عملیات موفق"
                    }

        return {
            "success": True,
            "action_type": request.action_type,
            "position": request.position,
            "action_description": action_description,
            "visual_model": None,
            "page_title": None,
            "new_url": None,
            "page_name": None,
            "backend_status": backend_status,
            "backend_model": None,
            "has_error": has_error,
            "error_info": error_info
        }

    except Exception as e:
        slog.error("Analyze action failed", exception=e)
        return {
            "success": False,
            "error": str(e),
            "action_description": f"{request.action_type} انجام شد"
        }


@router.post("/inspector/analyze-error")
async def analyze_error_from_source(
    request: AnalyzeErrorRequest,
    db: Session = Depends(get_db)
):
    """
    🔍 تحلیل عمیق خطا با بررسی کد منبع از GitHub

    این endpoint:
    1. پیام خطا را تحلیل می‌کند
    2. به GitHub پروژه مراجعه می‌کند
    3. فایل‌های مرتبط را پیدا می‌کند
    4. علت خطا را شناسایی می‌کند
    5. راه‌حل پیشنهاد می‌دهد
    """
    from ...services.ai_manager import get_ai_manager
    from ...models.project import Project
    from ...models.setting import Setting
    import os
    import httpx

    slog.api_request("POST", "/inspector/analyze-error",
        project_id=request.project_id,
        error_message=request.error_message[:100]
    )

    try:
        # دریافت پروژه
        project = db.query(Project).filter(Project.id == request.project_id).first()
        if not project:
            return {"success": False, "error": "پروژه یافت نشد"}

        # توکن GitHub
        github_token = os.environ.get("GITHUB_TOKEN", "")
        if not github_token:
            github_token = Setting.get_value(db, "api_key_github") or ""

        if not github_token:
            return {
                "success": False,
                "error": "توکن GitHub تنظیم نشده است",
                "analysis": "برای بررسی کد منبع، ابتدا توکن GitHub را در تنظیمات وارد کنید."
            }

        # استخراج owner/repo از github_path پروژه
        github_path = getattr(project, 'github_path', None)
        if not github_path:
            return {
                "success": False,
                "error": "این پروژه به GitHub متصل نیست",
                "analysis": request.error_message
            }

        # پارس کردن github_path
        github_path_clean = github_path.replace("https://github.com/", "").replace(".git", "").strip("/")
        parts = github_path_clean.split("/")
        if len(parts) < 2:
            return {"success": False, "error": f"فرمت GitHub path نامعتبر: {github_path}"}

        owner, repo = parts[0], parts[1]

        # انتخاب مدل تحلیل
        ai_manager = get_ai_manager()
        analysis_model = None

        if request.selected_models:
            analysis_model = request.selected_models[0]
        else:
            # انتخاب بهترین مدل تحلیل
            for model_id in ["claude-sonnet-4-20250514", "gpt-4o", "gemini-2.5-pro"]:
                try:
                    # تست سریع
                    analysis_model = model_id
                    break
                except:
                    continue

        if not analysis_model:
            analysis_model = "gpt-4o-mini"

        # دریافت لیست فایل‌ها از GitHub
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        source_files = []
        file_contents = {}

        async with httpx.AsyncClient() as client:
            # دریافت tree برای پیدا کردن فایل‌های مرتبط
            tree_res = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1",
                headers=headers,
                timeout=15.0
            )

            if tree_res.status_code == 200:
                tree_data = tree_res.json()
                all_files = [item["path"] for item in tree_data.get("tree", []) if item["type"] == "blob"]

                # فیلتر فایل‌های کد
                code_files = [f for f in all_files if f.endswith(('.py', '.js', '.ts', '.tsx', '.jsx', '.vue', '.go', '.rs'))]

                # پیدا کردن فایل‌های مرتبط با خطا
                error_keywords = request.error_message.lower().split()
                relevant_files = []

                for file_path in code_files[:100]:  # محدودیت
                    file_lower = file_path.lower()
                    # امتیاز بر اساس تطابق کلمات
                    score = sum(1 for kw in error_keywords if kw in file_lower and len(kw) > 3)
                    if score > 0:
                        relevant_files.append((file_path, score))

                # اگر فایل مرتبط نبود، فایل‌های اصلی را بگیر
                if not relevant_files:
                    main_files = [f for f in code_files if any(x in f.lower() for x in ['main', 'app', 'index', 'server', 'api', 'route'])]
                    relevant_files = [(f, 1) for f in main_files[:5]]

                # مرتب‌سازی بر اساس امتیاز
                relevant_files.sort(key=lambda x: -x[1])
                relevant_files = relevant_files[:5]  # حداکثر 5 فایل

                # دریافت محتوای فایل‌ها
                for file_path, _ in relevant_files:
                    try:
                        content_res = await client.get(
                            f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}",
                            headers=headers,
                            timeout=10.0
                        )
                        if content_res.status_code == 200:
                            import base64
                            content_data = content_res.json()
                            if content_data.get("encoding") == "base64":
                                content = base64.b64decode(content_data["content"]).decode('utf-8', errors='ignore')
                                file_contents[file_path] = content[:5000]  # محدودیت سایز
                                source_files.append({"path": file_path, "issue": "در حال بررسی..."})
                    except Exception as e:
                        slog.warn(f"Failed to fetch {file_path}: {e}")

        # تحلیل با AI
        from ...services.ai_base import Message

        analysis_prompt = f"""شما یک مهندس نرم‌افزار متخصص هستید که باید خطا را تحلیل کنید.

## خطای گزارش شده:
{request.error_message}

## جزئیات لاگ:
{request.log_details or 'ندارد'}

## فایل‌های کد پروژه:
"""
        for file_path, content in file_contents.items():
            analysis_prompt += f"\n### {file_path}\n```\n{content[:3000]}\n```\n"

        analysis_prompt += """

## وظیفه شما:
1. علت اصلی خطا را شناسایی کنید
2. فایل یا فایل‌های مسبب را مشخص کنید
3. راه‌حل دقیق برای رفع خطا پیشنهاد دهید

## فرمت پاسخ (JSON):
{
  "analysis": "توضیح علت خطا به فارسی",
  "source_files": [
    {"path": "مسیر فایل", "issue": "مشکل این فایل چیست"}
  ],
  "suggested_fix": "راه‌حل پیشنهادی به فارسی"
}

فقط JSON خالص برگردانید، بدون توضیح اضافی."""

        try:
            messages = [
                Message(role="system", content="شما یک مهندس نرم‌افزار متخصص در debugging هستید. پاسخ را به صورت JSON خالص برگردانید."),
                Message(role="user", content=analysis_prompt)
            ]

            response = await ai_manager.generate(
                model_id=analysis_model,
                messages=messages,
                max_tokens=2000,
                temperature=0.2
            )

            # پارس کردن پاسخ JSON
            response_text = response.content.strip()
            # حذف markdown اگر وجود دارد
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]

            result = json.loads(response_text)

            return {
                "success": True,
                "analysis": result.get("analysis", "تحلیل انجام شد"),
                "source_files": result.get("source_files", source_files),
                "suggested_fix": result.get("suggested_fix", "بررسی فایل‌های مرتبط"),
                "model_used": analysis_model,
                "detailed_report": f"تحلیل توسط {analysis_model}:\n\n{result.get('analysis', '')}"
            }

        except json.JSONDecodeError:
            # اگر JSON نبود، متن خام را برگردان
            return {
                "success": True,
                "analysis": response.content if 'response' in dir() else "خطا در تحلیل",
                "source_files": source_files,
                "suggested_fix": "بررسی فایل‌های مرتبط",
                "model_used": analysis_model,
                "detailed_report": response.content if 'response' in dir() else ""
            }

    except Exception as e:
        slog.error("Analyze error from source failed", exception=e)
        return {
            "success": False,
            "error": str(e),
            "analysis": f"خطا در تحلیل: {str(e)}"
        }


# =====================================
# 🌉 Bridge Script Injection
# تزریق اسکریپت ارتباطی به پروژه‌ها
# =====================================

class InjectBridgeRequest(BaseModel):
    """درخواست تزریق Bridge Script"""
    project_id: str
    remove: bool = False  # True = حذف اسکریپت
    custom_path: Optional[str] = None  # مسیر سفارشی به فایل HTML (مثال: "frontend/public/index.html")


# محتوای Bridge Script که به پروژه‌ها تزریق می‌شود (نسخه HTML)
INSPECTOR_BRIDGE_SCRIPT = '''
<!-- Inspector Bridge Script - Auto-injected -->
<script>
(function() {
  console.log('🌉 Inspector Bridge: Script starting...');

  // جلوگیری از اجرای چندباره
  if (window.__inspectorBridgeLoaded) {
    console.log('🌉 Inspector Bridge: Already loaded, skipping');
    return;
  }
  window.__inspectorBridgeLoaded = true;

  // بررسی اینکه آیا در iframe هستیم
  const isInIframe = window !== window.parent;
  console.log('🌉 Inspector Bridge: In iframe?', isInIframe);
  console.log('🌉 Inspector Bridge: Page URL:', window.location.href);

  // تنظیمات
  const DEBOUNCE_MS = 100;
  let lastEventTime = 0;
  let messagesSent = 0;

  // تابع ارسال پیام به parent (پنل مدیریت)
  function sendToInspector(action, data) {
    try {
      const message = {
        type: 'inspector-bridge-event',
        action: action,
        target: data.target || '',
        elementInfo: data.elementInfo || '',
        position: data.position || { xPercent: 50, yPercent: 50 },
        pageUrl: window.location.href,
        timestamp: Date.now()
      };
      window.parent.postMessage(message, '*');
      messagesSent++;
      console.log('🌉 Inspector Bridge: Sent message #' + messagesSent, action, data.elementInfo);
    } catch (e) {
      console.warn('Inspector bridge: failed to send message', e);
    }
  }

  // گرفتن اطلاعات المنت
  function getElementInfo(el) {
    if (!el) return 'عنصر ناشناخته';

    // متن المنت
    let text = (el.innerText || el.value || '').trim().slice(0, 50);

    // نوع المنت
    let type = el.tagName?.toLowerCase() || 'unknown';

    // کلاس یا آیدی
    let identifier = el.id ? '#' + el.id :
                     el.className ? '.' + el.className.split(' ')[0] : '';

    // ترجمه تگ‌های معروف به فارسی
    const tagLabels = {
      'button': 'دکمه',
      'a': 'لینک',
      'input': 'فیلد ورودی',
      'textarea': 'فیلد متن',
      'select': 'منوی انتخاب',
      'img': 'تصویر',
      'video': 'ویدیو',
      'form': 'فرم',
      'table': 'جدول',
      'div': 'بخش',
      'span': 'متن',
      'p': 'پاراگراف',
      'h1': 'عنوان اصلی',
      'h2': 'عنوان',
      'h3': 'عنوان',
      'nav': 'منوی ناوبری',
      'header': 'سربرگ',
      'footer': 'پاورقی',
      'li': 'آیتم لیست'
    };

    let typeLabel = tagLabels[type] || type;

    if (text) {
      return typeLabel + ' "' + text + '"';
    }
    return typeLabel + (identifier ? ' ' + identifier : '');
  }

  // محاسبه درصد موقعیت
  function getPositionPercent(e) {
    return {
      xPercent: (e.clientX / window.innerWidth) * 100,
      yPercent: (e.clientY / window.innerHeight) * 100
    };
  }

  // Debounce
  function shouldSend() {
    const now = Date.now();
    if (now - lastEventTime < DEBOUNCE_MS) return false;
    lastEventTime = now;
    return true;
  }

  // Event Listeners

  // کلیک
  document.addEventListener('click', function(e) {
    if (!shouldSend()) return;
    sendToInspector('click', {
      target: e.target?.tagName,
      elementInfo: getElementInfo(e.target),
      position: getPositionPercent(e)
    });
  }, true);

  // اسکرول
  let scrollTimeout;
  document.addEventListener('scroll', function(e) {
    clearTimeout(scrollTimeout);
    scrollTimeout = setTimeout(function() {
      sendToInspector('scroll', {
        elementInfo: 'صفحه',
        position: {
          xPercent: (window.scrollX / (document.body.scrollWidth - window.innerWidth)) * 100 || 0,
          yPercent: (window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100 || 0
        }
      });
    }, 200);
  }, true);

  // تایپ در فیلدها
  document.addEventListener('input', function(e) {
    if (!shouldSend()) return;
    if (e.target?.tagName === 'INPUT' || e.target?.tagName === 'TEXTAREA') {
      sendToInspector('input', {
        target: e.target?.tagName,
        elementInfo: getElementInfo(e.target),
        position: { xPercent: 50, yPercent: 50 }
      });
    }
  }, true);

  // فوکوس
  document.addEventListener('focus', function(e) {
    if (!shouldSend()) return;
    if (e.target && e.target !== document && e.target !== document.body) {
      sendToInspector('focus', {
        target: e.target?.tagName,
        elementInfo: getElementInfo(e.target),
        position: { xPercent: 50, yPercent: 50 }
      });
    }
  }, true);

  // اعلام آماده بودن
  try {
    window.parent.postMessage({
      type: 'inspector-bridge-ready',
      pageUrl: window.location.href,
      isInIframe: isInIframe,
      timestamp: Date.now()
    }, '*');
    console.log('🌉 Inspector Bridge: Ready message sent to parent');
  } catch (readyErr) {
    console.warn('🌉 Inspector Bridge: Failed to send ready message', readyErr);
  }

  console.log('🌉 Inspector Bridge: Script loaded and active!');
  console.log('🌉 Inspector Bridge: Click, scroll, or type to test');
})();
</script>
'''

# 🆕 محتوای Bridge Script برای پروژه‌های React/Next.js (نسخه JS/TS)
INSPECTOR_BRIDGE_SCRIPT_JS = '''
// 🌉 Inspector Bridge Script - Auto-injected
// این کد را در ابتدای فایل اصلی پروژه اضافه کنید
if (typeof window !== 'undefined' && !window.__inspectorBridgeLoaded) {
  window.__inspectorBridgeLoaded = true;

  const isInIframe = window !== window.parent;
  if (isInIframe) {
    console.log('🌉 Inspector Bridge: Active in iframe');

    const sendToInspector = (action, data) => {
      try {
        window.parent.postMessage({
          type: 'inspector-bridge-event',
          action,
          elementInfo: data.elementInfo || '',
          position: data.position || { xPercent: 50, yPercent: 50 },
          pageUrl: window.location.href,
          timestamp: Date.now()
        }, '*');
      } catch (e) { console.warn('Bridge send failed:', e); }
    };

    const getElementInfo = (el) => {
      if (!el) return '';
      const text = (el.innerText || el.value || '').trim().slice(0, 30);
      const tag = el.tagName?.toLowerCase() || '';
      return text ? `${tag} "${text}"` : tag;
    };

    document.addEventListener('click', (e) => {
      sendToInspector('click', { elementInfo: getElementInfo(e.target) });
    }, true);

    document.addEventListener('input', (e) => {
      if (e.target?.tagName === 'INPUT' || e.target?.tagName === 'TEXTAREA') {
        sendToInspector('input', { elementInfo: getElementInfo(e.target) });
      }
    }, true);

    let scrollTimeout;
    document.addEventListener('scroll', () => {
      clearTimeout(scrollTimeout);
      scrollTimeout = setTimeout(() => {
        sendToInspector('scroll', { elementInfo: 'صفحه' });
      }, 200);
    }, true);

    window.parent.postMessage({ type: 'inspector-bridge-ready', pageUrl: window.location.href }, '*');
  }
}
// 🌉 End of Inspector Bridge Script
'''


@router.post("/inspector/inject-bridge")
async def inject_bridge_script(
    request: InjectBridgeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    🌉 تزریق Bridge Script به پروژه

    این endpoint:
    1. فایل index.html پروژه را از GitHub دریافت می‌کند
    2. اسکریپت Bridge را به آن اضافه می‌کند
    3. تغییرات را commit و push می‌کند
    4. یک deploy جدید trigger می‌شود
    """
    from ...models.project import Project
    from ...models.setting import Setting
    import os
    import httpx
    import base64

    slog.api_request("POST", "/inspector/inject-bridge",
        project_id=request.project_id,
        remove=request.remove
    )

    try:
        # دریافت پروژه
        project = db.query(Project).filter(Project.id == request.project_id).first()
        if not project:
            return {"success": False, "error": "پروژه یافت نشد"}

        # توکن GitHub
        github_token = os.environ.get("GITHUB_TOKEN", "")
        if not github_token:
            github_token = Setting.get_value(db, "api_key_github") or ""

        if not github_token:
            return {
                "success": False,
                "error": "توکن GitHub تنظیم نشده است"
            }

        # استخراج owner/repo از github_path یا extra_data
        github_path = getattr(project, 'github_path', None)
        owner = None
        repo = None

        # اگر github_path خالی بود، چک کن شاید در extra_data باشد
        if not github_path:
            extra_data = getattr(project, 'extra_data', None)
            if extra_data:
                try:
                    extra = json.loads(extra_data) if isinstance(extra_data, str) else extra_data

                    # روش 1: github_path یا github_url مستقیم
                    github_path = extra.get('github_path') or extra.get('github_url') or extra.get('repository_url') or extra.get('source_url') or extra.get('clone_url')

                    # روش 2: owner و repo جداگانه
                    if not github_path and extra.get('owner') and extra.get('repo'):
                        owner = extra.get('owner')
                        repo = extra.get('repo')
                        github_path = f"{owner}/{repo}"

                        # 🆕 خودکار ست کردن github_path برای دفعات بعد
                        project.github_path = github_path
                        db.commit()
                        slog.info(f"Auto-set github_path from extra_data: {github_path}")
                except Exception as e:
                    slog.warn(f"Failed to parse extra_data: {e}")

        if not github_path:
            # برگرداندن اطلاعات تشخیصی
            return {
                "success": False,
                "error": "این پروژه به GitHub متصل نیست.",
                "debug_info": {
                    "project_id": project.id,
                    "project_name": project.name,
                    "github_path": getattr(project, 'github_path', 'N/A'),
                    "extra_data_preview": str(getattr(project, 'extra_data', ''))[:200] if getattr(project, 'extra_data', None) else None,
                    "hint": "برای اتصال، از قسمت تنظیمات پروژه آدرس GitHub را وارد کنید"
                }
            }

        # پارس کردن github_path که می‌تواند به فرمت‌های مختلف باشد:
        # - owner/repo
        # - https://github.com/owner/repo
        # - https://github.com/owner/repo.git
        github_path_clean = github_path.replace("https://github.com/", "").replace(".git", "").strip("/")
        parts = github_path_clean.split("/")
        if len(parts) < 2:
            return {"success": False, "error": f"فرمت GitHub path نامعتبر است: {github_path}"}

        owner, repo = parts[0], parts[1]

        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        async with httpx.AsyncClient() as client:
            index_path = None
            index_content = None
            index_sha = None
            found_html_files = []
            is_framework_without_html = False
            is_nextjs = False
            is_nuxt = False
            is_gatsby = False
            all_files = []  # لیست همه فایل‌ها
            search_error = None  # خطای جستجو
            is_js_file = False  # آیا فایل پیدا شده JS/TS است؟

            # اگر مسیر سفارشی داده شده، اول آن را امتحان کن
            if request.custom_path:
                try:
                    res = await client.get(
                        f"https://api.github.com/repos/{owner}/{repo}/contents/{request.custom_path}",
                        headers=headers,
                        timeout=10.0
                    )
                    if res.status_code == 200:
                        data = res.json()
                        if data.get("encoding") == "base64":
                            index_content = base64.b64decode(data["content"]).decode('utf-8')
                            index_sha = data["sha"]
                            index_path = request.custom_path
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"فایل در مسیر سفارشی یافت نشد: {request.custom_path}",
                        "detail": str(e)
                    }

            # 🆕 جستجوی فوق‌هوشمند: اول package.json رو بخون، بعد تصمیم بگیر
            # متغیرهای tracking برای debug
            detected_framework = None
            entry_candidates = []
            package_json_found = False
            package_json_status = None
            tree_status = None
            deps_found = {}
            default_branch = 'main'

            if not index_path:
                try:
                    slog.info(f"🔍 Smart search starting for {owner}/{repo}")

                    # 📦 مرحله ۱: خواندن package.json برای تشخیص فریم‌ورک
                    pkg_res = await client.get(
                        f"https://api.github.com/repos/{owner}/{repo}/contents/package.json",
                        headers=headers,
                        timeout=10.0
                    )
                    package_json_status = pkg_res.status_code
                    slog.info(f"📦 package.json status: {package_json_status}")

                    if pkg_res.status_code == 200:
                        package_json_found = True
                        pkg_data = pkg_res.json()
                        if pkg_data.get("encoding") == "base64":
                            pkg_content = json.loads(base64.b64decode(pkg_data["content"]).decode('utf-8'))
                            slog.info(f"📦 Found package.json: {pkg_content.get('name', 'unnamed')}")

                            # تشخیص فریم‌ورک از dependencies
                            deps = {**pkg_content.get('dependencies', {}), **pkg_content.get('devDependencies', {})}
                            # ذخیره لیست dependency ها برای debug
                            deps_found = list(deps.keys())[:20]  # فقط ۲۰ تای اول
                            slog.info(f"📦 Dependencies found: {deps_found}")

                            if 'next' in deps:
                                detected_framework = 'nextjs'
                                entry_candidates = [
                                    'pages/_app.tsx', 'pages/_app.js', 'pages/_app.jsx',
                                    'src/pages/_app.tsx', 'src/pages/_app.js',
                                    'app/layout.tsx', 'app/layout.js', 'src/app/layout.tsx', 'src/app/layout.js'
                                ]
                            elif 'nuxt' in deps:
                                detected_framework = 'nuxt'
                                entry_candidates = ['app.vue', 'layouts/default.vue', 'pages/index.vue']
                            elif 'gatsby' in deps:
                                detected_framework = 'gatsby'
                                entry_candidates = ['gatsby-browser.js', 'src/pages/index.js', 'src/pages/index.tsx']
                            elif 'vue' in deps:
                                detected_framework = 'vue'
                                entry_candidates = ['src/App.vue', 'src/main.js', 'src/main.ts', 'app/App.vue']
                            elif 'react' in deps or 'react-dom' in deps:
                                detected_framework = 'react'
                                # بررسی اینکه Vite هست یا CRA
                                if 'vite' in deps:
                                    entry_candidates = ['src/main.tsx', 'src/main.jsx', 'src/main.js', 'index.html']
                                else:
                                    entry_candidates = ['src/index.tsx', 'src/index.jsx', 'src/index.js', 'public/index.html']
                            elif 'svelte' in deps:
                                detected_framework = 'svelte'
                                entry_candidates = ['src/App.svelte', 'src/main.js', 'src/main.ts']
                            elif 'angular' in deps or '@angular/core' in deps:
                                detected_framework = 'angular'
                                entry_candidates = ['src/main.ts', 'src/index.html']

                            slog.info(f"🔧 Detected framework from package.json: {detected_framework}")
                            slog.info(f"📄 Entry candidates: {entry_candidates}")

                    # 🌳 مرحله ۲: دریافت لیست فایل‌ها
                    # اول اطلاعات ریپو رو بگیر برای default branch
                    default_branch = 'main'
                    try:
                        repo_info = await client.get(
                            f"https://api.github.com/repos/{owner}/{repo}",
                            headers=headers,
                            timeout=10.0
                        )
                        if repo_info.status_code == 200:
                            default_branch = repo_info.json().get('default_branch', 'main')
                            slog.info(f"🌿 Default branch: {default_branch}")
                    except Exception as e:
                        slog.warn(f"Failed to get repo info: {e}")

                    tree_res = await client.get(
                        f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1",
                        headers=headers,
                        timeout=15.0
                    )

                    # اگر branch پیش‌فرض کار نکرد، main و master رو امتحان کن
                    if tree_res.status_code == 404 and default_branch != 'main':
                        slog.info(f"Branch '{default_branch}' not found, trying 'main'")
                        tree_res = await client.get(
                            f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1",
                            headers=headers,
                            timeout=15.0
                        )

                    if tree_res.status_code == 404:
                        slog.info("Branch 'main' not found, trying 'master'")
                        tree_res = await client.get(
                            f"https://api.github.com/repos/{owner}/{repo}/git/trees/master?recursive=1",
                            headers=headers,
                            timeout=15.0
                        )

                    tree_status = tree_res.status_code
                    slog.info(f"🌳 GitHub tree response: {tree_status}")

                    if tree_res.status_code == 200:
                        tree_data = tree_res.json()
                        all_files = [item["path"] for item in tree_data.get("tree", []) if item["type"] == "blob"]
                        slog.info(f"📁 Total files in repo: {len(all_files)}")

                        # 🎯 مرحله ۳: پیدا کردن بهترین فایل برای تزریق

                        # اول فایل‌های HTML رو چک کن
                        html_files = [f for f in all_files if f.endswith('.html') and 'node_modules' not in f]

                        # امتیازدهی به HTML ها
                        def score_html_file(path: str) -> int:
                            score = 0
                            path_lower = path.lower()
                            if path_lower.endswith('index.html'):
                                score += 100
                            if 'public/' in path_lower:
                                score += 80
                            if 'src/' in path_lower and 'public/' not in path_lower:
                                score += 30
                            if 'dist/' in path_lower or 'build/' in path_lower:
                                score -= 50
                            return score

                        html_files_scored = [(f, score_html_file(f)) for f in html_files]
                        html_files_scored.sort(key=lambda x: -x[1])

                        # اگر HTML با امتیاز بالا پیدا شد، از اون استفاده کن
                        for html_path, score in html_files_scored:
                            if score >= 50:  # فقط HTML های خوب
                                try:
                                    content_res = await client.get(
                                        f"https://api.github.com/repos/{owner}/{repo}/contents/{html_path}",
                                        headers=headers,
                                        timeout=10.0
                                    )
                                    if content_res.status_code == 200:
                                        data = content_res.json()
                                        if data.get("encoding") == "base64":
                                            content = base64.b64decode(data["content"]).decode('utf-8')
                                            if '<html' in content.lower() or '<!doctype' in content.lower():
                                                if 'Inspector Bridge Script' not in content:
                                                    index_content = content
                                                    index_sha = data["sha"]
                                                    index_path = html_path
                                                    is_js_file = False
                                                    slog.info(f"✅ Found HTML: {html_path} (score: {score})")
                                                    break
                                except:
                                    continue

                        # 🔍 مرحله ۴: اگر HTML پیدا نشد، از entry candidates استفاده کن
                        if not index_path and entry_candidates:
                            slog.info(f"No good HTML found, trying framework entry points: {entry_candidates}")
                            for candidate in entry_candidates:
                                if candidate in all_files:
                                    try:
                                        content_res = await client.get(
                                            f"https://api.github.com/repos/{owner}/{repo}/contents/{candidate}",
                                            headers=headers,
                                            timeout=10.0
                                        )
                                        if content_res.status_code == 200:
                                            data = content_res.json()
                                            if data.get("encoding") == "base64":
                                                content = base64.b64decode(data["content"]).decode('utf-8')
                                                if 'Inspector Bridge Script' not in content:
                                                    index_content = content
                                                    index_sha = data["sha"]
                                                    index_path = candidate
                                                    is_js_file = not candidate.endswith('.html')
                                                    slog.info(f"✅ Found entry point: {candidate}")
                                                    break
                                    except Exception as e:
                                        slog.warn(f"Failed to fetch {candidate}: {e}")
                                        continue

                        # 🔎 مرحله ۵: اگر هنوز پیدا نشد، جستجوی عمومی
                        if not index_path:
                            slog.info("Trying generic search for any entry file...")
                            generic_patterns = [
                                # فایل‌های entry point رایج
                                'src/App.tsx', 'src/App.jsx', 'src/App.js',
                                'src/index.tsx', 'src/index.jsx', 'src/index.js',
                                'src/main.tsx', 'src/main.jsx', 'src/main.js', 'src/main.ts',
                                'app/App.tsx', 'app/App.js',
                                'App.tsx', 'App.js', 'App.jsx',
                                'index.tsx', 'index.js',
                                # HTML های عمومی
                                'index.html', 'public/index.html'
                            ]

                            for pattern in generic_patterns:
                                if pattern in all_files:
                                    try:
                                        content_res = await client.get(
                                            f"https://api.github.com/repos/{owner}/{repo}/contents/{pattern}",
                                            headers=headers,
                                            timeout=10.0
                                        )
                                        if content_res.status_code == 200:
                                            data = content_res.json()
                                            if data.get("encoding") == "base64":
                                                content = base64.b64decode(data["content"]).decode('utf-8')
                                                if 'Inspector Bridge Script' not in content:
                                                    index_content = content
                                                    index_sha = data["sha"]
                                                    index_path = pattern
                                                    is_js_file = not pattern.endswith('.html')
                                                    slog.info(f"✅ Found via generic search: {pattern}")
                                                    break
                                    except:
                                        continue

                        # 📝 ذخیره اطلاعات برای نمایش به کاربر
                        found_html_files = [f for f, _ in html_files_scored[:10]]
                        if detected_framework:
                            is_framework_without_html = detected_framework in ['nextjs', 'nuxt', 'gatsby']
                            is_nextjs = detected_framework == 'nextjs'
                            is_nuxt = detected_framework == 'nuxt'
                            is_gatsby = detected_framework == 'gatsby'

                except Exception as e:
                    slog.warn(f"Smart HTML search failed: {e}")
                    found_html_files = []
                    is_framework_without_html = False
                    search_error = str(e)

            if not index_path:
                # تشخیص بهتر نوع مشکل
                # 🔍 اطلاعات فریم‌ورک برای نمایش
                framework_name = None
                if detected_framework:
                    framework_map = {
                        'nextjs': 'Next.js',
                        'nuxt': 'Nuxt',
                        'gatsby': 'Gatsby',
                        'react': 'React',
                        'vue': 'Vue',
                        'svelte': 'Svelte',
                        'angular': 'Angular'
                    }
                    framework_name = framework_map.get(detected_framework, detected_framework)

                error_response = {
                    "success": False,
                    "need_custom_path": True,
                    "found_html_files": found_html_files,  # همیشه برگردون
                    "framework_detected": framework_name,
                    # 🔍 Debug info - اطلاعات کامل برای عیب‌یابی
                    "debug": {
                        "github_path": f"{owner}/{repo}",
                        "default_branch": default_branch,
                        "total_files_found": len(all_files),
                        "html_files_count": len(found_html_files),
                        "search_error": search_error,
                        "detected_framework_raw": detected_framework,
                        "entry_candidates": entry_candidates,
                        "files_sample": all_files[:20] if all_files else [],
                        "package_json_found": package_json_found,
                        "package_json_status": package_json_status,
                        "tree_status": tree_status,
                        "deps_sample": deps_found[:10] if isinstance(deps_found, list) else []
                    }
                }

                if is_framework_without_html:
                    error_response["error"] = "این پروژه از فریم‌ورکی استفاده می‌کند که HTML در زمان build ساخته می‌شود"
                    error_response["hint"] = "برای این نوع پروژه‌ها، باید فایل _document.js یا _app.js را ویرایش کنید یا از روش دیگری استفاده کنید"
                    error_response["alternative_hint"] = "می‌توانید اسکریپت Bridge را مستقیماً در کد پروژه اضافه کنید"
                elif found_html_files:
                    error_response["error"] = "فایل HTML اصلی به‌صورت خودکار پیدا نشد"
                    error_response["hint"] = "فایل‌های HTML زیر پیدا شدند - یکی را انتخاب کنید:"
                else:
                    error_response["error"] = "هیچ فایل HTML در پروژه یافت نشد"
                    error_response["hint"] = "مسیر فایل HTML را دستی وارد کنید یا مطمئن شوید پروژه فایل HTML دارد"

                return error_response

            # بررسی وجود اسکریپت قبلی
            bridge_marker = "Inspector Bridge Script"
            has_bridge = bridge_marker in index_content

            if request.remove:
                # حذف اسکریپت
                if not has_bridge:
                    return {"success": True, "message": "اسکریپت از قبل حذف شده است"}

                # حذف اسکریپت با regex
                import re
                if is_js_file:
                    # حذف نسخه JS
                    new_content = re.sub(
                        r'// 🌉 Inspector Bridge Script - Auto-injected.*?// 🌉 End of Inspector Bridge Script\n?',
                        '',
                        index_content,
                        flags=re.DOTALL
                    )
                else:
                    # حذف نسخه HTML
                    new_content = re.sub(
                        r'<!-- Inspector Bridge Script - Auto-injected -->.*?</script>',
                        '',
                        index_content,
                        flags=re.DOTALL
                    )
                commit_message = "🔧 Remove Inspector Bridge Script"
            else:
                # اضافه کردن اسکریپت
                if has_bridge:
                    return {"success": True, "message": "اسکریپت از قبل تزریق شده است", "already_injected": True}

                if is_js_file:
                    # 🆕 تزریق نسخه JS/TS - در ابتدای فایل
                    slog.info(f"Injecting JS version into {index_path}")
                    new_content = INSPECTOR_BRIDGE_SCRIPT_JS + "\n" + index_content
                    commit_message = "🌉 Add Inspector Bridge Script (JS version)"
                else:
                    # تزریق نسخه HTML - قبل از </head> یا </body>
                    if "</head>" in index_content:
                        new_content = index_content.replace("</head>", INSPECTOR_BRIDGE_SCRIPT + "\n</head>")
                    elif "</body>" in index_content:
                        new_content = index_content.replace("</body>", INSPECTOR_BRIDGE_SCRIPT + "\n</body>")
                    else:
                        new_content = index_content + "\n" + INSPECTOR_BRIDGE_SCRIPT
                    commit_message = "🌉 Add Inspector Bridge Script for live tracking"

            # آپدیت فایل در GitHub
            update_res = await client.put(
                f"https://api.github.com/repos/{owner}/{repo}/contents/{index_path}",
                headers=headers,
                json={
                    "message": commit_message,
                    "content": base64.b64encode(new_content.encode('utf-8')).decode('utf-8'),
                    "sha": index_sha,
                    "branch": "main"
                },
                timeout=15.0
            )

            if update_res.status_code in [200, 201]:
                slog.info(f"Bridge script {'removed' if request.remove else 'injected'} successfully",
                    project_id=request.project_id,
                    file_path=index_path
                )

                return {
                    "success": True,
                    "message": "اسکریپت با موفقیت حذف شد" if request.remove else "اسکریپت با موفقیت تزریق شد",
                    "file_path": index_path,
                    "commit_url": update_res.json().get("commit", {}).get("html_url"),
                    "note": "پس از deploy مجدد، تغییرات اعمال می‌شود"
                }
            else:
                error_msg = update_res.json().get("message", "خطای ناشناخته")
                return {
                    "success": False,
                    "error": f"خطا در آپدیت فایل: {error_msg}"
                }

    except Exception as e:
        slog.error("Inject bridge script failed", exception=e)
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/inspector/bridge-status/{project_id}")
async def check_bridge_status(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    🔍 بررسی وضعیت Bridge Script در پروژه
    """
    from ...models.project import Project
    from ...models.setting import Setting
    import os
    import httpx
    import base64

    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"success": False, "error": "پروژه یافت نشد"}

        github_token = os.environ.get("GITHUB_TOKEN", "")
        if not github_token:
            github_token = Setting.get_value(db, "api_key_github") or ""

        if not github_token:
            return {"success": False, "has_bridge": False, "error": "توکن GitHub تنظیم نشده"}

        github_path = getattr(project, 'github_path', None)
        if not github_path:
            return {"success": False, "has_bridge": False, "error": "پروژه به GitHub متصل نیست"}

        github_path_clean = github_path.replace("https://github.com/", "").replace(".git", "").strip("/")
        parts = github_path_clean.split("/")
        if len(parts) < 2:
            return {"success": False, "error": f"فرمت GitHub path نامعتبر: {github_path}"}

        owner, repo = parts[0], parts[1]

        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        possible_paths = ["index.html", "public/index.html", "src/index.html"]

        async with httpx.AsyncClient() as client:
            for path in possible_paths:
                try:
                    res = await client.get(
                        f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
                        headers=headers,
                        timeout=10.0
                    )
                    if res.status_code == 200:
                        data = res.json()
                        if data.get("encoding") == "base64":
                            content = base64.b64decode(data["content"]).decode('utf-8')
                            has_bridge = "Inspector Bridge Script - Auto-injected" in content
                            return {
                                "success": True,
                                "has_bridge": has_bridge,
                                "file_path": path
                            }
                except:
                    continue

        return {
            "success": True,
            "has_bridge": False,
            "error": "فایل index.html یافت نشد"
        }

    except Exception as e:
        slog.error("Check bridge status failed", exception=e)
        return {"success": False, "error": str(e)}


class SetGitHubPathRequest(BaseModel):
    """درخواست تنظیم آدرس GitHub برای پروژه"""
    project_id: str
    github_path: str  # مثال: owner/repo یا https://github.com/owner/repo


@router.post("/inspector/set-github-path")
async def set_project_github_path(
    request: SetGitHubPathRequest,
    db: Session = Depends(get_db)
):
    """
    🔗 تنظیم آدرس GitHub برای پروژه

    این endpoint برای پروژه‌هایی که github_path ندارند یا اشتباه است.
    """
    from ...models.project import Project

    slog.api_request("POST", "/inspector/set-github-path",
        project_id=request.project_id,
        github_path=request.github_path
    )

    try:
        project = db.query(Project).filter(Project.id == request.project_id).first()
        if not project:
            return {"success": False, "error": "پروژه یافت نشد"}

        # نرمال‌سازی github_path
        github_path = request.github_path.strip()
        github_path = github_path.replace("https://github.com/", "").replace(".git", "").strip("/")

        # اعتبارسنجی فرمت
        parts = github_path.split("/")
        if len(parts) < 2:
            return {"success": False, "error": "فرمت نامعتبر. باید به شکل owner/repo باشد"}

        # ذخیره
        project.github_path = github_path
        db.commit()

        slog.info(f"GitHub path set for project", project_id=request.project_id, github_path=github_path)

        return {
            "success": True,
            "message": f"آدرس GitHub با موفقیت تنظیم شد: {github_path}",
            "github_path": github_path
        }

    except Exception as e:
        slog.error("Set GitHub path failed", exception=e)
        return {"success": False, "error": str(e)}


@router.get("/inspector/debug-bridge/{project_id}")
async def debug_bridge_injection(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    🔍 Debug endpoint برای بررسی وضعیت Bridge Script

    نشان می‌دهد:
    - آیا پروژه به GitHub متصل است
    - کدام فایل HTML پیدا شده
    - آیا Bridge Script در فایل هست
    - محتوای فایل (قسمتی از آن)
    """
    from ...models.project import Project
    from ...models.setting import Setting
    import os
    import httpx
    import base64

    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"success": False, "error": "پروژه یافت نشد"}

        result = {
            "project_id": project_id,
            "project_name": project.name,
            "github_path": project.github_path,
            "project_type": project.project_type,
        }

        # چک توکن
        github_token = os.environ.get("GITHUB_TOKEN", "")
        if not github_token:
            github_token = Setting.get_value(db, "api_key_github") or ""

        if not github_token:
            result["error"] = "توکن GitHub تنظیم نشده"
            return result

        github_path = project.github_path
        if not github_path:
            # تلاش برای استخراج از extra_data
            extra_data = getattr(project, 'extra_data', None)
            if extra_data:
                try:
                    extra = json.loads(extra_data) if isinstance(extra_data, str) else extra_data
                    if extra.get('owner') and extra.get('repo'):
                        github_path = f"{extra['owner']}/{extra['repo']}"
                        result["github_path_source"] = "extra_data"
                except:
                    pass

        if not github_path:
            result["error"] = "github_path یافت نشد"
            return result

        github_path_clean = github_path.replace("https://github.com/", "").replace(".git", "").strip("/")
        parts = github_path_clean.split("/")
        if len(parts) < 2:
            result["error"] = f"فرمت نامعتبر: {github_path}"
            return result

        owner, repo = parts[0], parts[1]
        result["owner"] = owner
        result["repo"] = repo

        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        async with httpx.AsyncClient() as client:
            # دریافت لیست فایل‌ها
            tree_res = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1",
                headers=headers,
                timeout=15.0
            )

            if tree_res.status_code == 404:
                tree_res = await client.get(
                    f"https://api.github.com/repos/{owner}/{repo}/git/trees/master?recursive=1",
                    headers=headers,
                    timeout=15.0
                )

            if tree_res.status_code != 200:
                result["error"] = f"خطا در دریافت فایل‌ها: {tree_res.status_code}"
                return result

            tree_data = tree_res.json()
            all_files = [item["path"] for item in tree_data.get("tree", []) if item["type"] == "blob"]
            html_files = [f for f in all_files if f.endswith('.html')]

            result["total_files"] = len(all_files)
            result["html_files"] = html_files

            # بررسی هر فایل HTML برای وجود Bridge
            files_with_bridge = []
            for html_path in html_files[:10]:  # حداکثر 10 فایل
                try:
                    content_res = await client.get(
                        f"https://api.github.com/repos/{owner}/{repo}/contents/{html_path}",
                        headers=headers,
                        timeout=10.0
                    )
                    if content_res.status_code == 200:
                        data = content_res.json()
                        if data.get("encoding") == "base64":
                            content = base64.b64decode(data["content"]).decode('utf-8')
                            has_bridge = "Inspector Bridge Script" in content
                            if has_bridge:
                                files_with_bridge.append({
                                    "path": html_path,
                                    "has_bridge": True,
                                    "preview": content[:500] + "..." if len(content) > 500 else content
                                })
                except:
                    continue

            result["files_with_bridge"] = files_with_bridge
            result["bridge_injected"] = len(files_with_bridge) > 0

            if not files_with_bridge:
                result["message"] = "Bridge Script در هیچ فایل HTML یافت نشد!"
            else:
                result["message"] = f"Bridge Script در {len(files_with_bridge)} فایل یافت شد"

            # 🔍 بررسی سایت دیپلوی شده
            preview_url = project.preview_url
            if preview_url:
                result["preview_url"] = preview_url
                try:
                    deployed_res = await client.get(
                        preview_url,
                        timeout=15.0,
                        follow_redirects=True
                    )
                    if deployed_res.status_code == 200:
                        deployed_html = deployed_res.text
                        result["deployed_has_bridge"] = "Inspector Bridge Script" in deployed_html
                        result["deployed_has_bridge_marker"] = "__inspectorBridgeLoaded" in deployed_html

                        # اگر در سورس هست ولی در دیپلوی نیست
                        if result["bridge_injected"] and not result["deployed_has_bridge"]:
                            result["diagnosis"] = "⚠️ اسکریپت در GitHub هست ولی در سایت دیپلوی شده نیست! احتمالاً deploy هنوز انجام نشده یا build process اسکریپت را حذف کرده"
                        elif result["deployed_has_bridge"]:
                            result["diagnosis"] = "✅ اسکریپت در سایت دیپلوی شده موجود است"
                        else:
                            result["diagnosis"] = "❌ اسکریپت نه در GitHub و نه در سایت دیپلوی شده موجود است"
                    else:
                        result["deployed_check_error"] = f"HTTP {deployed_res.status_code}"
                except Exception as deploy_check_err:
                    result["deployed_check_error"] = str(deploy_check_err)
            else:
                result["preview_url"] = None
                result["diagnosis"] = "⚠️ URL پیش‌نمایش پروژه تنظیم نشده"

        return result

    except Exception as e:
        slog.error("Debug bridge failed", exception=e)
        return {"success": False, "error": str(e)}
