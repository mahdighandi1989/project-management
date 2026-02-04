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

        # بررسی اتصال GitHub
        from ...models.setting import Setting
        github_token = db.query(Setting).filter(Setting.key == "api_key_github").first()
        github_connected = github_token and github_token.value and len(github_token.value) > 10

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
                            # فعال کردن موقت
                            selected_models.append(model_id)
                            temporarily_enabled.append(model_id)

                            # در محیط واقعی: آپدیت موقت دیتابیس
                            slog.info(f"Temporarily enabling model: {model_id}")

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

        # 7. بررسی اتصال GitHub
        from ...models.setting import Setting
        github_token = db.query(Setting).filter(Setting.key == "api_key_github").first()
        github_connected = github_token and github_token.value and len(github_token.value) > 10

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


def get_best_vision_model(ai_manager, db) -> Optional[str]:
    """
    انتخاب بهترین مدل vision موجود

    اولویت:
    1. Claude (بهترین برای تحلیل و تصمیم‌گیری)
    2. GPT-4o (قدرتمند در vision)
    3. Gemini (سریع و مقرون به صرفه)
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

    # پیدا کردن اولین مدل موجود
    for model_id in priority_order:
        if model_id in MODEL_REGISTRY:
            model = MODEL_REGISTRY[model_id]
            provider = str(model.provider.value) if hasattr(model.provider, 'value') else str(model.provider)

            # بررسی فعال بودن provider
            if provider not in available_provider_names:
                continue

            # بررسی تنظیمات کاربر
            setting = settings_map.get(model_id)
            if setting and not setting.enabled:
                continue

            # بررسی قابلیت vision
            if model.supports_images:
                slog.info(f"Selected vision model: {model_id}")
                return model_id

    # Fallback به اولین مدل vision موجود
    vision_models = get_vision_models()
    for model in vision_models:
        provider = str(model.provider.value) if hasattr(model.provider, 'value') else str(model.provider)
        if provider in available_provider_names:
            return model.id

    return None


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

    session_id = str(uuid.uuid4())[:8]

    # 1. دریافت AI manager
    ai_manager = get_ai_manager()

    # 2. انتخاب مدل vision (داینامیک یا مشخص شده)
    selected_model = request.model_id
    if not selected_model:
        selected_model = get_best_vision_model(ai_manager, db)

    if not selected_model:
        return {
            "success": False,
            "error": "هیچ مدل vision فعالی یافت نشد. لطفاً API key یکی از مدل‌های vision (OpenAI, Claude, Gemini) را تنظیم کنید."
        }

    slog.api_request("POST", "/inspector/ai-interact",
        task=request.task[:100],
        url=request.url,
        model_id=selected_model
    )

    try:
        # 3. باز کردن مرورگر
        session = await create_session(session_id, request.url)
        page_info = await session.get_page_info()

        slog.info(f"Browser opened", session_id=session_id, title=page_info.get('title'), model=selected_model)

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

        return {
            "success": result.get("success", False),
            "session_id": session_id,
            "task": request.task,
            "selected_model": selected_model,  # 🆕 نمایش مدل انتخاب شده
            "actions": formatted_actions,
            "cursor_positions": result.get("cursor_positions", []),
            "final_screenshot": result.get("final_screenshot"),
            "total_steps": result.get("total_steps", 0),
            "message": f"کار انجام شد: {result.get('total_steps', 0)} مرحله (مدل: {selected_model})",
            "page_info": page_info
        }

    except Exception as e:
        slog.error("AI interaction failed", exception=e)
        try:
            await close_session(session_id)
        except:
            pass
        return {
            "success": False,
            "error": str(e),
            "actions": []
        }

