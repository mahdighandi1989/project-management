# -*- coding: utf-8 -*-
"""
🚀 سرویس ارتباط با Render API

امکانات:
- دریافت لیست سرویس‌ها
- دریافت لاگ‌های سرویس‌ها
- ذخیره لاگ‌ها در دیتابیس
- مدیریت آرشیو و retention
"""

import asyncio
import aiohttp
import json
import gzip
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import hashlib

from ..core.logging_utils import StructuredLogger
from ..core.database import SessionLocal

slog = StructuredLogger(__name__, "RENDER")


class RenderAPIService:
    """سرویس ارتباط با Render API"""

    BASE_URL = "https://api.render.com/v1"

    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """دریافت session HTTP"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Accept": "application/json"
                }
            )
        return self._session

    async def close(self):
        """بستن session"""
        if self._session and not self._session.closed:
            await self._session.close()

    def _load_api_key(self) -> bool:
        """بارگذاری API key از دیتابیس"""
        if self.api_key:
            return True

        try:
            db = SessionLocal()
            from ..models.setting import Setting
            setting = db.query(Setting).filter(Setting.key == "api_key_render").first()
            db.close()

            if setting and setting.value:
                self.api_key = setting.value
                slog.info("Render API key loaded from database")
                return True
            else:
                slog.warning("No Render API key found in database")
                return False
        except Exception as e:
            slog.error("Failed to load Render API key", exception=e)
            return False

    async def get_services(self) -> Dict[str, Any]:
        """
        دریافت لیست همه سرویس‌های Render

        Returns:
            {
                "success": bool,
                "services": [
                    {
                        "id": "srv-xxxxx",
                        "name": "my-backend",
                        "type": "web_service",
                        "region": "oregon",
                        "status": "deployed"
                    }
                ],
                "error": str | None
            }
        """
        slog.start("Fetching Render services")

        if not self._load_api_key():
            return {
                "success": False,
                "services": [],
                "error": "کلید API رندر یافت نشد"
            }

        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/services"

            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()

                    services = []
                    for item in data:
                        service = item.get("service", {})
                        services.append({
                            "id": service.get("id"),
                            "name": service.get("name"),
                            "type": service.get("type"),
                            "region": service.get("region"),
                            "status": service.get("suspended") == "not_suspended" and "deployed" or service.get("suspended"),
                            "created_at": service.get("createdAt"),
                            "updated_at": service.get("updatedAt"),
                            "dashboard_url": f"https://dashboard.render.com/{service.get('type', 'web')}/{service.get('id')}"
                        })

                    slog.success("Services fetched", count=len(services))

                    # ذخیره در دیتابیس
                    await self._save_services_to_db(services)

                    return {
                        "success": True,
                        "services": services,
                        "error": None
                    }

                elif response.status == 401:
                    slog.error("Render API unauthorized - check API key")
                    return {
                        "success": False,
                        "services": [],
                        "error": "کلید API رندر نامعتبر است"
                    }

                elif response.status == 429:
                    slog.warning("Render API rate limited")
                    return {
                        "success": False,
                        "services": [],
                        "error": "محدودیت درخواست - لطفاً کمی صبر کنید"
                    }

                else:
                    error_text = await response.text()
                    slog.error("Render API error",
                        status=response.status,
                        error=error_text[:200]
                    )
                    return {
                        "success": False,
                        "services": [],
                        "error": f"خطای API: {response.status}"
                    }

        except aiohttp.ClientError as e:
            slog.error("Network error fetching services", exception=e)
            return {
                "success": False,
                "services": [],
                "error": f"خطای شبکه: {str(e)}"
            }
        except Exception as e:
            slog.error("Unexpected error fetching services", exception=e)
            return {
                "success": False,
                "services": [],
                "error": str(e)
            }

    async def get_logs(
        self,
        service_id: str,
        limit: int = 100,
        start_time: datetime = None,
        end_time: datetime = None,
        direction: str = "backward"  # backward = newest first
    ) -> Dict[str, Any]:
        """
        دریافت لاگ‌های یک سرویس

        Args:
            service_id: شناسه سرویس (srv-xxxxx)
            limit: تعداد لاگ‌ها
            start_time: زمان شروع
            end_time: زمان پایان
            direction: جهت (backward=جدیدترین اول)

        Returns:
            {
                "success": bool,
                "logs": [...],
                "has_more": bool,
                "next_start_time": str,
                "next_end_time": str,
                "error": str | None
            }
        """
        slog.start("Fetching logs",
            service_id=service_id,
            limit=limit,
            direction=direction
        )

        if not self._load_api_key():
            return {
                "success": False,
                "logs": [],
                "error": "کلید API رندر یافت نشد"
            }

        try:
            session = await self._get_session()

            # ساخت پارامترها
            params = {
                "resource": service_id,
                "limit": min(limit, 500),  # حداکثر Render
                "direction": direction
            }

            if start_time:
                params["startTime"] = start_time.isoformat() + "Z"
            if end_time:
                params["endTime"] = end_time.isoformat() + "Z"

            url = f"{self.BASE_URL}/logs"

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    logs = []
                    for log_entry in data.get("logs", []):
                        # تشخیص سطح لاگ
                        message = log_entry.get("message", "")
                        level = self._detect_log_level(message)

                        # ایجاد ID یکتا
                        log_id = hashlib.md5(
                            f"{service_id}_{log_entry.get('timestamp')}_{message[:50]}".encode()
                        ).hexdigest()[:16]

                        logs.append({
                            "id": f"rlog_{log_id}",
                            "service_id": service_id,
                            "timestamp": log_entry.get("timestamp"),
                            "level": level,
                            "message": message,
                            "deploy_id": log_entry.get("deployID"),
                            "instance_id": log_entry.get("instanceID"),
                        })

                    slog.success("Logs fetched",
                        service_id=service_id,
                        count=len(logs),
                        has_more=data.get("hasMore", False)
                    )

                    return {
                        "success": True,
                        "logs": logs,
                        "has_more": data.get("hasMore", False),
                        "next_start_time": data.get("nextStartTime"),
                        "next_end_time": data.get("nextEndTime"),
                        "error": None
                    }

                elif response.status == 401:
                    return {
                        "success": False,
                        "logs": [],
                        "error": "کلید API رندر نامعتبر است"
                    }

                elif response.status == 429:
                    return {
                        "success": False,
                        "logs": [],
                        "error": "محدودیت درخواست - لطفاً کمی صبر کنید"
                    }

                else:
                    error_text = await response.text()
                    slog.error("Render logs API error",
                        status=response.status,
                        error=error_text[:200]
                    )
                    return {
                        "success": False,
                        "logs": [],
                        "error": f"خطای API: {response.status}"
                    }

        except Exception as e:
            slog.error("Error fetching logs", exception=e)
            return {
                "success": False,
                "logs": [],
                "error": str(e)
            }

    def _detect_log_level(self, message: str) -> str:
        """تشخیص سطح لاگ از محتوای پیام"""
        message_lower = message.lower()

        if any(kw in message_lower for kw in ["error", "exception", "failed", "خطا", "failure"]):
            return "error"
        elif any(kw in message_lower for kw in ["warn", "warning", "هشدار"]):
            return "warn"
        elif any(kw in message_lower for kw in ["debug", "trace"]):
            return "debug"
        else:
            return "info"

    async def _save_services_to_db(self, services: List[Dict]):
        """ذخیره سرویس‌ها در دیتابیس"""
        try:
            db = SessionLocal()
            from ..models.render_log import RenderService

            for service in services:
                existing = db.query(RenderService).filter(
                    RenderService.id == service["id"]
                ).first()

                if existing:
                    existing.name = service["name"]
                    existing.type = service["type"]
                    existing.region = service["region"]
                    existing.status = service["status"]
                else:
                    new_service = RenderService(
                        id=service["id"],
                        name=service["name"],
                        type=service["type"],
                        region=service["region"],
                        status=service["status"]
                    )
                    db.add(new_service)

            db.commit()
            db.close()
            slog.info("Services saved to database", count=len(services))

        except Exception as e:
            slog.error("Failed to save services to database", exception=e)

    async def save_logs_to_db(self, logs: List[Dict], service_name: str = None):
        """ذخیره لاگ‌ها در دیتابیس"""
        if not logs:
            return 0

        try:
            db = SessionLocal()
            from ..models.render_log import RenderLog

            saved_count = 0
            for log in logs:
                # چک کردن تکراری
                existing = db.query(RenderLog).filter(
                    RenderLog.id == log["id"]
                ).first()

                if not existing:
                    try:
                        timestamp = datetime.fromisoformat(
                            log["timestamp"].replace("Z", "+00:00")
                        )
                    except:
                        timestamp = datetime.utcnow()

                    new_log = RenderLog(
                        id=log["id"],
                        service_id=log["service_id"],
                        service_name=service_name,
                        timestamp=timestamp,
                        level=log["level"],
                        message=log["message"],
                        deploy_id=log.get("deploy_id"),
                        instance_id=log.get("instance_id")
                    )
                    db.add(new_log)
                    saved_count += 1

            db.commit()
            db.close()

            if saved_count > 0:
                slog.info("Logs saved to database", new_count=saved_count, total=len(logs))

            return saved_count

        except Exception as e:
            slog.error("Failed to save logs to database", exception=e)
            return 0

    async def cleanup_old_logs(self, retention_hours: int = 48):
        """پاکسازی لاگ‌های قدیمی و آرشیو"""
        try:
            db = SessionLocal()
            from ..models.render_log import RenderLog, RenderLogArchive

            cutoff_time = datetime.utcnow() - timedelta(hours=retention_hours)

            # دریافت لاگ‌های قدیمی برای آرشیو
            old_logs = db.query(RenderLog).filter(
                RenderLog.timestamp < cutoff_time
            ).order_by(RenderLog.timestamp).all()

            if not old_logs:
                db.close()
                return {"archived": 0, "deleted": 0}

            # گروه‌بندی بر اساس سرویس
            logs_by_service = {}
            for log in old_logs:
                if log.service_id not in logs_by_service:
                    logs_by_service[log.service_id] = []
                logs_by_service[log.service_id].append({
                    "timestamp": log.timestamp.isoformat(),
                    "level": log.level,
                    "message": log.message,
                    "deploy_id": log.deploy_id
                })

            # آرشیو کردن
            archived_count = 0
            for service_id, service_logs in logs_by_service.items():
                # فشرده‌سازی
                json_data = json.dumps(service_logs, ensure_ascii=False)
                compressed = gzip.compress(json_data.encode('utf-8'))
                encoded = base64.b64encode(compressed).decode('ascii')

                archive = RenderLogArchive(
                    service_id=service_id,
                    start_time=datetime.fromisoformat(service_logs[0]["timestamp"]),
                    end_time=datetime.fromisoformat(service_logs[-1]["timestamp"]),
                    logs_count=len(service_logs),
                    compressed_data=encoded,
                    size_bytes=len(json_data)
                )
                db.add(archive)
                archived_count += len(service_logs)

            # حذف لاگ‌های آرشیو شده
            deleted = db.query(RenderLog).filter(
                RenderLog.timestamp < cutoff_time
            ).delete()

            db.commit()
            db.close()

            slog.info("Old logs cleaned up",
                archived=archived_count,
                deleted=deleted
            )

            return {"archived": archived_count, "deleted": deleted}

        except Exception as e:
            slog.error("Failed to cleanup old logs", exception=e)
            return {"archived": 0, "deleted": 0, "error": str(e)}

    async def get_archived_logs(
        self,
        service_id: str = None,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> List[Dict]:
        """دریافت لاگ‌های آرشیو شده"""
        try:
            db = SessionLocal()
            from ..models.render_log import RenderLogArchive

            query = db.query(RenderLogArchive)

            if service_id:
                query = query.filter(RenderLogArchive.service_id == service_id)
            if start_time:
                query = query.filter(RenderLogArchive.end_time >= start_time)
            if end_time:
                query = query.filter(RenderLogArchive.start_time <= end_time)

            archives = query.order_by(RenderLogArchive.start_time.desc()).all()

            result = []
            for archive in archives:
                # دیکد و decompress
                try:
                    compressed = base64.b64decode(archive.compressed_data)
                    decompressed = gzip.decompress(compressed)
                    logs = json.loads(decompressed.decode('utf-8'))
                    result.extend(logs)
                except Exception as e:
                    slog.warning("Failed to decompress archive",
                        archive_id=archive.id,
                        error=str(e)
                    )

            db.close()
            return result

        except Exception as e:
            slog.error("Failed to get archived logs", exception=e)
            return []


# Singleton instance
_render_service: Optional[RenderAPIService] = None


def get_render_service() -> RenderAPIService:
    """دریافت instance سرویس Render"""
    global _render_service
    if _render_service is None:
        _render_service = RenderAPIService()
    return _render_service


async def reset_render_service():
    """ریست سرویس برای بارگذاری مجدد API key"""
    global _render_service
    if _render_service:
        await _render_service.close()
    _render_service = None
    return get_render_service()
