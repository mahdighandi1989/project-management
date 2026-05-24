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
        self._owner_id: Optional[str] = None  # 🆕 Owner ID برای API لاگ

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

                        # 🆕 استخراج و ذخیره owner ID
                        owner_id = service.get("ownerId")
                        if owner_id and not self._owner_id:
                            self._owner_id = owner_id
                            slog.info("Owner ID extracted", owner_id=owner_id)

                        # 🆕 استخراج URL واقعی سرویس
                        service_url = None
                        service_details = service.get("serviceDetails", {})
                        if service_details:
                            # web services have url in serviceDetails
                            service_url = service_details.get("url")

                        # Fallback: ساخت URL از slug یا name
                        if not service_url:
                            slug = service.get("slug") or service.get("name", "").lower().replace(" ", "-").replace("_", "-")
                            service_type = service.get("type", "")
                            if service_type in ["web_service", "static_site"]:
                                service_url = f"https://{slug}.onrender.com"

                        services.append({
                            "id": service.get("id"),
                            "name": service.get("name"),
                            "type": service.get("type"),
                            "region": service.get("region"),
                            "status": service.get("suspended") == "not_suspended" and "deployed" or service.get("suspended"),
                            "created_at": service.get("createdAt"),
                            "updated_at": service.get("updatedAt"),
                            "owner_id": owner_id,
                            "service_url": service_url,  # 🆕 URL واقعی
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

            # 🆕 اگر owner_id نداریم، اول سرویس‌ها را بگیر
            if not self._owner_id:
                slog.info("Owner ID not cached, fetching services first")
                await self.get_services()

            if not self._owner_id:
                slog.error("Could not determine owner ID")
                return {
                    "success": False,
                    "logs": [],
                    "error": "شناسه مالک سرویس‌ها یافت نشد"
                }

            # ساخت پارامترها
            params = {
                "ownerId": self._owner_id,  # 🆕 اضافه شد
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
                    # 🔧 Fix: Handle null/None logs response
                    logs_data = data.get("logs") or []
                    for log_entry in logs_data:
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
        """ذخیره سرویس‌ها در دیتابیس (با حذف سرویس‌های حذف شده)"""
        try:
            db = SessionLocal()
            from ..models.render_log import RenderService

            # شناسه سرویس‌های فعلی از API
            api_service_ids = {service["id"] for service in services}

            for service in services:
                existing = db.query(RenderService).filter(
                    RenderService.id == service["id"]
                ).first()

                if existing:
                    existing.name = service["name"]
                    existing.type = service["type"]
                    existing.region = service["region"]
                    existing.status = service["status"]
                    # 🆕 آپدیت URL سرویس
                    if service.get("service_url"):
                        existing.service_url = service["service_url"]
                else:
                    new_service = RenderService(
                        id=service["id"],
                        name=service["name"],
                        type=service["type"],
                        region=service["region"],
                        status=service["status"],
                        service_url=service.get("service_url")  # 🆕 URL سرویس
                    )
                    db.add(new_service)

            # حذف سرویس‌هایی که دیگر در Render وجود ندارند
            deleted_count = db.query(RenderService).filter(
                ~RenderService.id.in_(api_service_ids)
            ).delete(synchronize_session='fetch')

            if deleted_count > 0:
                slog.info("Removed stale services from database", deleted=deleted_count)

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

            if saved_count > 0:
                slog.info("Logs saved to database", new_count=saved_count, total=len(logs))

                # بررسی حالت realtime برای انتقال فوری خطاها
                await self._check_realtime_transfer(db, logs)

            db.close()

            return saved_count

        except Exception as e:
            slog.error("Failed to save logs to database", exception=e)
            return 0

    async def _check_realtime_transfer(self, db, logs: List[Dict]):
        """
        بررسی و انتقال فوری خطاها در حالت realtime

        - اگر auto_transfer_mode = "realtime" باشد
        - خطاها فوراً به تب ایرادات منتقل می‌شوند
        """
        try:
            from ..models.render_log import RenderLogSettings, RenderLog
            from .log_to_issues_service import get_log_to_issues_service

            # بررسی تنظیمات
            settings = db.query(RenderLogSettings).first()
            if not settings:
                return

            is_realtime = (
                getattr(settings, 'auto_transfer_enabled', False) and
                getattr(settings, 'auto_transfer_mode', 'since_deploy') == 'realtime'
            )

            if not is_realtime:
                return

            # فیلتر لاگ‌های خطا
            error_logs = [
                log for log in logs
                if log.get("level", "").lower() in ["error", "fatal", "critical"]
            ]

            if not error_logs:
                return

            slog.info(f"[REALTIME] Transferring {len(error_logs)} error logs immediately...")

            # دریافت لاگ‌های ذخیره شده از دیتابیس
            error_log_ids = [log["id"] for log in error_logs]
            db_logs = db.query(RenderLog).filter(RenderLog.id.in_(error_log_ids)).all()

            if not db_logs:
                return

            # انتقال فوری
            service = get_log_to_issues_service()
            service_project_map = await service._build_service_project_map(db)

            transferred = 0
            merged = 0

            for log in db_logs:
                try:
                    result = await service._process_error_log(log, service_project_map, db)
                    if result.get("status") == "transferred":
                        transferred += 1
                    elif result.get("status") == "merged":
                        merged += 1
                except Exception as e:
                    slog.warning(f"[REALTIME] Failed to transfer log {log.id}", exception=e)

            db.commit()
            slog.info(f"[REALTIME] Transferred: {transferred}, Merged: {merged}")

        except Exception as e:
            slog.error("[REALTIME] Error in realtime transfer", exception=e)

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

    # ============================================================
    # 🆕 Render mutation methods (Phase 2 — Inspector independence)
    # ============================================================

    async def get_env_vars(self, service_id: str) -> Dict[str, Any]:
        """دریافت لیست متغیرهای محیطی یک سرویس"""
        slog.start("Fetching env vars", service_id=service_id)

        if not self._load_api_key():
            return {"success": False, "env_vars": [], "error": "کلید API رندر یافت نشد"}

        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/services/{service_id}/env-vars"

            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    env_vars = []
                    for item in data:
                        ev = item.get("envVar", item)
                        env_vars.append({"key": ev.get("key"), "value": ev.get("value")})
                    return {"success": True, "env_vars": env_vars, "error": None}
                else:
                    err = await response.text()
                    slog.error("Failed to get env vars", status=response.status, error=err)
                    return {"success": False, "env_vars": [], "error": f"HTTP {response.status}: {err}"}
        except Exception as e:
            slog.error("Exception fetching env vars", exception=e)
            return {"success": False, "env_vars": [], "error": str(e)}

    async def set_env_var(self, service_id: str, key: str, value: str) -> Dict[str, Any]:
        """تنظیم یا به‌روزرسانی یک متغیر محیطی (PUT — idempotent)"""
        slog.start("Setting env var", service_id=service_id, key=key)

        if not self._load_api_key():
            return {"success": False, "error": "کلید API رندر یافت نشد"}
        if not key or not isinstance(key, str):
            return {"success": False, "error": "کلید env_var نامعتبر است"}

        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/services/{service_id}/env-vars/{key}"
            payload = {"value": str(value) if value is not None else ""}

            async with session.put(url, json=payload) as response:
                body = await response.text()
                if response.status in (200, 201):
                    slog.success("Env var set", service_id=service_id, key=key)
                    return {"success": True, "key": key, "error": None}
                else:
                    slog.error("Failed to set env var", status=response.status, error=body)
                    return {"success": False, "error": f"HTTP {response.status}: {body}"}
        except Exception as e:
            slog.error("Exception setting env var", exception=e)
            return {"success": False, "error": str(e)}

    async def set_env_vars_bulk(self, service_id: str, vars_dict: Dict[str, str]) -> Dict[str, Any]:
        """تنظیم چندین متغیر به‌طور همزمان"""
        if not vars_dict:
            return {"success": False, "error": "هیچ متغیری ارائه نشده"}

        results = {}
        ok_count = 0
        for k, v in vars_dict.items():
            r = await self.set_env_var(service_id, k, v)
            results[k] = r
            if r.get("success"):
                ok_count += 1

        return {
            "success": ok_count == len(vars_dict),
            "set_count": ok_count,
            "total": len(vars_dict),
            "details": results,
            "error": None if ok_count == len(vars_dict) else f"{len(vars_dict) - ok_count} متغیر ست نشد"
        }

    async def restart_service(self, service_id: str) -> Dict[str, Any]:
        """ری‌استارت یک سرویس (بدون دیپلوی مجدد)"""
        slog.start("Restarting service", service_id=service_id)

        if not self._load_api_key():
            return {"success": False, "error": "کلید API رندر یافت نشد"}

        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/services/{service_id}/restart"

            async with session.post(url) as response:
                body = await response.text()
                if response.status in (200, 202):
                    slog.success("Service restart triggered", service_id=service_id)
                    return {"success": True, "service_id": service_id, "error": None}
                else:
                    slog.error("Failed to restart service", status=response.status, error=body)
                    return {"success": False, "error": f"HTTP {response.status}: {body}"}
        except Exception as e:
            slog.error("Exception restarting service", exception=e)
            return {"success": False, "error": str(e)}

    async def trigger_deploy(self, service_id: str, clear_cache: bool = False) -> Dict[str, Any]:
        """آغاز یک دیپلوی جدید"""
        slog.start("Triggering deploy", service_id=service_id, clear_cache=clear_cache)

        if not self._load_api_key():
            return {"success": False, "error": "کلید API رندر یافت نشد"}

        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/services/{service_id}/deploys"
            payload = {"clearCache": "clear" if clear_cache else "do_not_clear"}

            async with session.post(url, json=payload) as response:
                body_text = await response.text()
                if response.status in (200, 201, 202):
                    try:
                        data = json.loads(body_text) if body_text else {}
                    except Exception:
                        data = {}
                    deploy_id = data.get("id") if isinstance(data, dict) else None
                    slog.success("Deploy triggered", service_id=service_id, deploy_id=deploy_id)
                    return {"success": True, "service_id": service_id, "deploy_id": deploy_id, "error": None}
                else:
                    slog.error("Failed to trigger deploy", status=response.status, error=body_text)
                    return {"success": False, "error": f"HTTP {response.status}: {body_text}"}
        except Exception as e:
            slog.error("Exception triggering deploy", exception=e)
            return {"success": False, "error": str(e)}

    # ════════════════════════════════════════════════════════════════════
    # 🆕 (postgres-ops) — PostgreSQL database operations
    # transcript کاربر نشون داد inspector نمی‌تونست خودش DB بسازه چون
    # tool نداشت. Render API این رو پشتیبانی می‌کنه.
    # ════════════════════════════════════════════════════════════════════
    async def list_postgres(self) -> Dict[str, Any]:
        """لیست همهٔ PostgreSQL databases (owner-level)."""
        if not self._load_api_key():
            return {"success": False, "databases": [], "error": "کلید API رندر یافت نشد"}
        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/postgres?limit=100"
            async with session.get(url) as response:
                body_text = await response.text()
                if response.status == 200:
                    raw = json.loads(body_text) if body_text else []
                    # Render API گاهی [{ "postgres": {...}, "cursor": ... }] برمی‌گردونه
                    items = []
                    for entry in raw:
                        if isinstance(entry, dict):
                            pg = entry.get("postgres") if "postgres" in entry else entry
                            if isinstance(pg, dict):
                                items.append({
                                    "id": pg.get("id"),
                                    "name": pg.get("name"),
                                    "status": pg.get("status"),
                                    "plan": pg.get("plan"),
                                    "region": pg.get("region"),
                                    "version": pg.get("version"),
                                    "suspended": pg.get("suspended"),
                                    "createdAt": pg.get("createdAt"),
                                })
                    return {"success": True, "databases": items, "error": None}
                return {"success": False, "databases": [], "error": f"HTTP {response.status}: {body_text[:200]}"}
        except Exception as e:
            return {"success": False, "databases": [], "error": str(e)}

    async def get_postgres(self, postgres_id: str) -> Dict[str, Any]:
        """جزئیات یک PostgreSQL database."""
        if not self._load_api_key():
            return {"success": False, "error": "کلید API رندر یافت نشد"}
        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/postgres/{postgres_id}"
            async with session.get(url) as response:
                body_text = await response.text()
                if response.status == 200:
                    data = json.loads(body_text) if body_text else {}
                    return {"success": True, "database": data, "error": None}
                return {"success": False, "error": f"HTTP {response.status}: {body_text[:200]}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_postgres_connection_info(self, postgres_id: str) -> Dict[str, Any]:
        """دریافت connection string (internal + external) یک DB."""
        if not self._load_api_key():
            return {"success": False, "error": "کلید API رندر یافت نشد"}
        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/postgres/{postgres_id}/connection-info"
            async with session.get(url) as response:
                body_text = await response.text()
                if response.status == 200:
                    data = json.loads(body_text) if body_text else {}
                    return {
                        "success": True,
                        "internal_url": data.get("internalConnectionString"),
                        "external_url": data.get("externalConnectionString"),
                        "psql_command": data.get("psqlCommand"),
                        "error": None,
                    }
                return {"success": False, "error": f"HTTP {response.status}: {body_text[:200]}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def create_postgres(
        self,
        *,
        name: str,
        owner_id: str,
        plan: str = "free",
        region: str = "oregon",
        version: str = "16",
        database_name: Optional[str] = None,
        database_user: Optional[str] = None,
    ) -> Dict[str, Any]:
        """ایجاد یک PostgreSQL database جدید.

        Args:
            name: نام readable (نه id)
            owner_id: ownerId از Render account — برای پیدا کردنش از get_services() اولین سرویس
            plan: 'free' یا 'starter' یا 'standard' و ...
            region: 'oregon'، 'frankfurt'، 'singapore' و ...
            version: '14'، '15'، '16'
            database_name: نام DB داخل instance (default: name)
            database_user: نام user (default: random)
        """
        if not self._load_api_key():
            return {"success": False, "error": "کلید API رندر یافت نشد"}
        slog.start("Creating Postgres", name=name, plan=plan, region=region)
        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/postgres"
            payload = {
                "name": name,
                "ownerId": owner_id,
                "plan": plan,
                "region": region,
                "version": version,
            }
            if database_name:
                payload["databaseName"] = database_name
            if database_user:
                payload["databaseUser"] = database_user
            async with session.post(url, json=payload) as response:
                body_text = await response.text()
                if response.status in (200, 201, 202):
                    try:
                        data = json.loads(body_text) if body_text else {}
                    except Exception:
                        data = {}
                    pg_id = data.get("id") if isinstance(data, dict) else None
                    slog.success("Postgres created", id=pg_id, name=name)
                    return {
                        "success": True,
                        "postgres_id": pg_id,
                        "name": name,
                        "status": data.get("status"),
                        "note": "ایجاد شد. provisioning ~1-3 دقیقه طول می‌کشه. بعدش با get_postgres_connection_info می‌تونی URL رو بگیری.",
                        "error": None,
                    }
                slog.error("Failed to create postgres", status=response.status, body=body_text[:300])
                return {"success": False, "error": f"HTTP {response.status}: {body_text[:300]}"}
        except Exception as e:
            slog.error("Exception creating postgres", exception=e)
            return {"success": False, "error": str(e)}

    async def get_owner_id_from_services(self) -> Optional[str]:
        """ownerId رو از اولین سرویس استخراج می‌کنه (برای create_postgres)."""
        res = await self.get_services()
        if not res.get("success"):
            return None
        for s in res.get("services") or []:
            # ممکنه ownerId در serviceDetails یا روی خود service باشه
            for key in ("ownerId", "owner_id"):
                if s.get(key):
                    return s.get(key)
            details = s.get("serviceDetails") or {}
            for key in ("ownerId", "owner_id"):
                if details.get(key):
                    return details.get(key)
        # تلاش با endpoint owners
        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/owners"
            async with session.get(url) as response:
                if response.status == 200:
                    raw = await response.json()
                    if isinstance(raw, list) and raw:
                        first = raw[0]
                        if isinstance(first, dict):
                            owner = first.get("owner") if "owner" in first else first
                            if isinstance(owner, dict):
                                return owner.get("id")
        except Exception:
            pass
        return None


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
