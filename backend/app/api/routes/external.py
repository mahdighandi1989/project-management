"""
🔍 External System Monitor API Routes
مسیرهای مانیتور سامانه‌های خارجی
"""

from fastapi import APIRouter, HTTPException, Form, Query, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/external", tags=["External Systems"])


# =====================================
# Request Models
# =====================================

class RegisterSystemRequest(BaseModel):
    """ثبت سامانه جدید"""
    name: str
    base_url: str
    description: str = ""
    auth_type: str = "none"  # none, api_key, bearer, basic
    auth_config: Dict = {}
    headers: Dict = {}
    auto_discover: bool = True


class MakeRequestRequest(BaseModel):
    """ارسال درخواست"""
    method: str = "GET"
    path: str = "/"
    data: Optional[Dict] = None
    params: Optional[Dict] = None


class StartMonitoringRequest(BaseModel):
    """شروع مانیتورینگ"""
    interval_seconds: int = 60


# =====================================
# Helper
# =====================================

def get_monitor():
    """دریافت monitor service"""
    from ...services.external_monitor import get_external_monitor
    from ...services.ai_manager import get_ai_manager

    try:
        ai_manager = get_ai_manager()
        return get_external_monitor(ai_manager)
    except:
        return get_external_monitor()


# =====================================
# System Management Endpoints
# =====================================

@router.get("/systems")
async def list_systems():
    """لیست همه سامانه‌های ثبت شده"""
    try:
        monitor = get_monitor()
        systems = monitor.list_systems()

        return {
            "success": True,
            "systems": systems,
            "count": len(systems)
        }
    except Exception as e:
        logger.error(f"Error listing systems: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/systems")
async def register_system(request: RegisterSystemRequest):
    """
    ثبت یک سامانه خارجی جدید

    نوع‌های احراز هویت:
    - none: بدون احراز هویت
    - api_key: با کلید API (نیاز به key_name و key_value در auth_config)
    - bearer: با Bearer token (نیاز به token در auth_config)
    - basic: با username/password (نیاز به username و password در auth_config)
    """
    try:
        monitor = get_monitor()

        system = await monitor.register_system(
            name=request.name,
            base_url=request.base_url,
            description=request.description,
            auth_type=request.auth_type,
            auth_config=request.auth_config,
            headers=request.headers,
            auto_discover=request.auto_discover
        )

        return {
            "success": True,
            "message": f"سامانه '{request.name}' ثبت شد",
            "system": {
                "id": system.id,
                "name": system.name,
                "base_url": system.base_url,
                "status": system.status.value,
                "endpoints_discovered": len(system.endpoints)
            }
        }
    except Exception as e:
        logger.error(f"Error registering system: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/systems/{system_id}")
async def get_system_details(system_id: str):
    """دریافت جزئیات یک سامانه"""
    try:
        from dataclasses import asdict
        monitor = get_monitor()
        system = monitor.get_system(system_id)

        if not system:
            raise HTTPException(status_code=404, detail="سامانه یافت نشد")

        return {
            "success": True,
            "system": {
                "id": system.id,
                "name": system.name,
                "base_url": system.base_url,
                "description": system.description,
                "status": system.status.value,
                "auth_type": system.auth_type,
                "last_health_check": system.last_health_check,
                "endpoints": [
                    {
                        "path": e.path,
                        "method": e.method.value,
                        "description": e.description,
                        "last_status": e.last_status_code,
                        "response_time": e.last_response_time,
                        "error_count": e.error_count
                    }
                    for e in system.endpoints
                ],
                "issues": [
                    {
                        "id": i.id,
                        "type": i.issue_type.value,
                        "severity": i.severity.value,
                        "title": i.title,
                        "description": i.description,
                        "resolved": i.resolved
                    }
                    for i in system.issues
                ],
                "has_openapi": system.openapi_schema is not None,
                "created_at": system.created_at,
                "updated_at": system.updated_at
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting system: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/systems/{system_id}")
async def remove_system(system_id: str):
    """حذف سامانه"""
    try:
        monitor = get_monitor()
        success = monitor.remove_system(system_id)

        if not success:
            raise HTTPException(status_code=404, detail="سامانه یافت نشد")

        return {
            "success": True,
            "message": "سامانه حذف شد"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================
# Discovery & Health Check
# =====================================

@router.post("/systems/{system_id}/discover")
async def discover_api(system_id: str):
    """کشف API سامانه"""
    try:
        monitor = get_monitor()
        result = await monitor.discover_api(system_id)
        return result
    except Exception as e:
        logger.error(f"Error discovering API: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/systems/{system_id}/health-check")
async def health_check(system_id: str):
    """بررسی سلامت سامانه"""
    try:
        monitor = get_monitor()
        result = await monitor.health_check(system_id)

        return {
            "success": True,
            "system_id": result.system_id,
            "status": result.status.value,
            "response_time_ms": result.response_time_ms,
            "endpoints_checked": result.endpoints_checked,
            "endpoints_healthy": result.endpoints_healthy,
            "issues": [
                {
                    "type": i.issue_type.value,
                    "severity": i.severity.value,
                    "title": i.title,
                    "description": i.description
                }
                for i in result.issues_found
            ]
        }
    except Exception as e:
        logger.error(f"Error health checking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/systems/{system_id}/history")
async def get_health_history(system_id: str, limit: int = 50):
    """دریافت تاریخچه سلامت"""
    try:
        monitor = get_monitor()
        system = monitor.get_system(system_id)

        if not system:
            raise HTTPException(status_code=404, detail="سامانه یافت نشد")

        return {
            "success": True,
            "system_id": system_id,
            "history": system.health_history[-limit:]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================
# Monitoring
# =====================================

@router.post("/systems/{system_id}/monitoring/start")
async def start_monitoring(
    system_id: str,
    request: StartMonitoringRequest,
    background_tasks: BackgroundTasks
):
    """شروع مانیتورینگ دوره‌ای"""
    try:
        monitor = get_monitor()

        # بررسی وجود سامانه
        if not monitor.get_system(system_id):
            raise HTTPException(status_code=404, detail="سامانه یافت نشد")

        result = await monitor.start_monitoring(
            system_id,
            interval_seconds=request.interval_seconds
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/systems/{system_id}/monitoring/stop")
async def stop_monitoring(system_id: str):
    """توقف مانیتورینگ"""
    try:
        monitor = get_monitor()
        return monitor.stop_monitoring(system_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================
# AI Analysis
# =====================================

@router.post("/systems/{system_id}/analyze")
async def analyze_with_ai(system_id: str):
    """
    تحلیل سامانه با AI

    شامل:
    - بررسی وضعیت کلی
    - شناسایی مشکلات
    - پیشنهاد راه‌حل
    - تشخیص مشکلات قابل رفع خودکار
    """
    try:
        monitor = get_monitor()
        result = await monitor.analyze_with_ai(system_id)
        return result
    except Exception as e:
        logger.error(f"Error analyzing with AI: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================
# Direct Requests
# =====================================

@router.post("/systems/{system_id}/request")
async def make_request_to_system(system_id: str, request: MakeRequestRequest):
    """
    ارسال درخواست مستقیم به سامانه

    برای تست endpoint ها یا اعمال تغییرات
    """
    try:
        monitor = get_monitor()
        result = await monitor.make_request(
            system_id=system_id,
            method=request.method,
            path=request.path,
            data=request.data,
            params=request.params
        )
        return result
    except Exception as e:
        logger.error(f"Error making request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/systems/{system_id}/logs")
async def get_system_logs(system_id: str):
    """دریافت لاگ‌های سامانه (اگر endpoint داشته باشه)"""
    try:
        monitor = get_monitor()
        result = await monitor.get_live_logs(system_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================
# Quick Connect (بدون ثبت دائم)
# =====================================

@router.post("/quick-check")
async def quick_health_check(
    url: str = Form(...),
    auth_type: str = Form(default="none"),
    auth_value: str = Form(default="")
):
    """
    بررسی سریع یک URL بدون ثبت در سیستم

    برای تست سریع سامانه‌ها
    """
    try:
        import aiohttp
        import time

        headers = {}
        if auth_type == "bearer" and auth_value:
            headers["Authorization"] = f"Bearer {auth_value}"
        elif auth_type == "api_key" and auth_value:
            headers["X-API-Key"] = auth_value

        timeout = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            start = time.time()

            try:
                async with session.get(url, headers=headers) as response:
                    elapsed = int((time.time() - start) * 1000)

                    try:
                        body = await response.json()
                    except:
                        body = await response.text()

                    return {
                        "success": response.status < 400,
                        "url": url,
                        "status_code": response.status,
                        "response_time_ms": elapsed,
                        "content_type": response.headers.get("Content-Type", ""),
                        "response_preview": str(body)[:500] if body else None
                    }

            except aiohttp.ClientConnectorError as e:
                return {
                    "success": False,
                    "url": url,
                    "error": "اتصال برقرار نشد",
                    "details": str(e)
                }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/systems/{system_id}/openapi")
async def get_openapi_schema(system_id: str):
    """دریافت OpenAPI schema سامانه (اگر موجود باشه)"""
    try:
        monitor = get_monitor()
        system = monitor.get_system(system_id)

        if not system:
            raise HTTPException(status_code=404, detail="سامانه یافت نشد")

        if not system.openapi_schema:
            return {
                "success": False,
                "message": "OpenAPI schema برای این سامانه یافت نشد"
            }

        return {
            "success": True,
            "system_id": system_id,
            "openapi": system.openapi_schema
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
