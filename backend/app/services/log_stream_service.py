# -*- coding: utf-8 -*-
"""
📡 Log Stream Service
سرویس streaming لاگ‌ها به صورت real-time با WebSocket

قابلیت‌ها:
1. اتصال WebSocket برای لاگ‌های زنده
2. Server-side polling از Render API
3. Broadcast به همه clients متصل
4. فیلتر بر اساس سرویس و سطح لاگ
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field
import aiohttp

from ..core.logging_utils import StructuredLogger
from ..core.database import SessionLocal
from ..models.render_log import RenderLog, RenderService, RenderLogSettings

logger = logging.getLogger(__name__)
slog = StructuredLogger(__name__, "LOG_STREAM")


@dataclass
class WebSocketClient:
    """نماینده یک کلاینت WebSocket"""
    websocket: Any
    filters: Dict = field(default_factory=dict)
    connected_at: datetime = field(default_factory=datetime.utcnow)


class LogStreamService:
    """
    سرویس streaming لاگ‌های Render

    Features:
    - Server-side polling از Render API
    - Broadcasting به همه WebSocket clients
    - فیلتر بر اساس service و level
    - ذخیره در دیتابیس
    """

    RENDER_API = "https://api.render.com/v1"

    def __init__(self):
        self.clients: Dict[str, WebSocketClient] = {}  # client_id -> client
        self.is_polling = False
        self._poll_task: Optional[asyncio.Task] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_log_ids: Set[str] = set()  # برای جلوگیری از duplicate

    async def _get_session(self) -> aiohttp.ClientSession:
        """دریافت یا ایجاد HTTP session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def _get_render_token(self) -> Optional[str]:
        """دریافت Render API token"""
        return os.environ.get("RENDER_API_KEY")

    # =====================================
    # WebSocket Client Management
    # =====================================

    async def register_client(
        self,
        client_id: str,
        websocket: Any,
        filters: Dict = None
    ):
        """ثبت کلاینت جدید"""
        self.clients[client_id] = WebSocketClient(
            websocket=websocket,
            filters=filters or {}
        )
        slog.info("Client registered", client_id=client_id, total_clients=len(self.clients))

        # شروع polling اگر فعال نیست
        if not self.is_polling and self.clients:
            await self.start_polling()

    async def unregister_client(self, client_id: str):
        """حذف کلاینت"""
        if client_id in self.clients:
            del self.clients[client_id]
            slog.info("Client unregistered", client_id=client_id, total_clients=len(self.clients))

        # توقف polling اگر کلاینتی نیست
        if not self.clients and self.is_polling:
            await self.stop_polling()

    async def update_client_filters(self, client_id: str, filters: Dict):
        """به‌روزرسانی فیلترهای کلاینت"""
        if client_id in self.clients:
            self.clients[client_id].filters = filters

    # =====================================
    # Server-Side Polling
    # =====================================

    async def start_polling(self):
        """شروع polling از Render"""
        if self.is_polling:
            return

        self.is_polling = True
        self._poll_task = asyncio.create_task(self._polling_loop())
        slog.success("Server-side polling started")

    async def stop_polling(self):
        """توقف polling"""
        self.is_polling = False
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        slog.info("Server-side polling stopped")

    async def _polling_loop(self):
        """حلقه polling"""
        db = SessionLocal()
        try:
            # دریافت تنظیمات
            settings = db.query(RenderLogSettings).first()
            interval = settings.polling_interval_seconds if settings else 10

            while self.is_polling:
                try:
                    # Fetch لاگ‌های جدید
                    new_logs = await self._fetch_new_logs(db)

                    if new_logs:
                        # ذخیره در دیتابیس
                        await self._save_logs(db, new_logs)

                        # Broadcast به کلاینت‌ها
                        await self._broadcast_logs(new_logs)

                except Exception as e:
                    slog.error("Polling error", exception=e)

                await asyncio.sleep(interval)

        finally:
            db.close()

    async def _fetch_new_logs(self, db) -> List[Dict]:
        """دریافت لاگ‌های جدید از Render API"""
        token = self._get_render_token()
        if not token:
            return []

        session = await self._get_session()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }

        new_logs = []

        # دریافت سرویس‌های فعال
        services = db.query(RenderService).filter(
            RenderService.auto_fetch_logs == True
        ).all()

        for service in services:
            try:
                url = f"{self.RENDER_API}/services/{service.id}/logs"
                params = {
                    "limit": 50,
                    "direction": "backward"  # جدیدترین اول
                }

                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        logs = data if isinstance(data, list) else data.get("logs", [])

                        for log in logs:
                            log_id = log.get("id") or f"{service.id}_{log.get('timestamp')}"

                            # بررسی duplicate
                            if log_id not in self._last_log_ids:
                                self._last_log_ids.add(log_id)

                                # محدود کردن سایز cache
                                if len(self._last_log_ids) > 10000:
                                    self._last_log_ids = set(list(self._last_log_ids)[-5000:])

                                new_logs.append({
                                    "id": log_id,
                                    "service_id": service.id,
                                    "service_name": service.name,
                                    "timestamp": log.get("timestamp"),
                                    "level": log.get("level", "info"),
                                    "message": log.get("message", ""),
                                    "deploy_id": log.get("deployId"),
                                    "instance_id": log.get("instanceId")
                                })

            except Exception as e:
                slog.warning("Failed to fetch logs for service",
                    service_id=service.id, exception=e)

        return new_logs

    async def _save_logs(self, db, logs: List[Dict]):
        """ذخیره لاگ‌ها در دیتابیس"""
        try:
            for log_data in logs:
                # بررسی duplicate در دیتابیس
                existing = db.query(RenderLog).filter(
                    RenderLog.id == log_data["id"]
                ).first()

                if not existing:
                    log = RenderLog(
                        id=log_data["id"],
                        service_id=log_data["service_id"],
                        service_name=log_data["service_name"],
                        timestamp=datetime.fromisoformat(log_data["timestamp"].replace("Z", "+00:00"))
                            if log_data.get("timestamp") else datetime.utcnow(),
                        level=log_data.get("level", "info"),
                        message=log_data.get("message", ""),
                        deploy_id=log_data.get("deploy_id"),
                        instance_id=log_data.get("instance_id")
                    )
                    db.add(log)

            db.commit()

        except Exception as e:
            slog.error("Failed to save logs", exception=e)
            db.rollback()

    async def _broadcast_logs(self, logs: List[Dict]):
        """ارسال لاگ‌ها به همه کلاینت‌های متصل"""
        if not self.clients:
            return

        disconnected = []

        for client_id, client in self.clients.items():
            try:
                # فیلتر بر اساس تنظیمات کلاینت
                filtered_logs = self._filter_logs_for_client(logs, client.filters)

                if filtered_logs:
                    message = json.dumps({
                        "type": "new_logs",
                        "logs": filtered_logs,
                        "count": len(filtered_logs),
                        "timestamp": datetime.utcnow().isoformat()
                    })

                    await client.websocket.send_text(message)

            except Exception as e:
                slog.warning("Failed to send to client", client_id=client_id, exception=e)
                disconnected.append(client_id)

        # حذف کلاینت‌های disconnect شده
        for client_id in disconnected:
            await self.unregister_client(client_id)

    def _filter_logs_for_client(self, logs: List[Dict], filters: Dict) -> List[Dict]:
        """فیلتر لاگ‌ها بر اساس تنظیمات کلاینت"""
        filtered = logs

        # فیلتر service
        service_ids = filters.get("service_ids")
        if service_ids:
            filtered = [l for l in filtered if l.get("service_id") in service_ids]

        # فیلتر level
        levels = filters.get("levels")
        if levels:
            filtered = [l for l in filtered if l.get("level") in levels]

        # فیلتر search
        search = filters.get("search")
        if search:
            search_lower = search.lower()
            filtered = [l for l in filtered if search_lower in (l.get("message") or "").lower()]

        return filtered

    # =====================================
    # Manual Fetch (برای کلاینت‌های HTTP)
    # =====================================

    async def fetch_latest_logs(
        self,
        service_ids: List[str] = None,
        levels: List[str] = None,
        limit: int = 100,
        since_id: str = None
    ) -> Dict[str, Any]:
        """
        دریافت آخرین لاگ‌ها (برای HTTP polling)

        این متد برای کلاینت‌هایی است که نمی‌توانند
        از WebSocket استفاده کنند
        """
        db = SessionLocal()
        try:
            query = db.query(RenderLog)

            if service_ids:
                query = query.filter(RenderLog.service_id.in_(service_ids))

            if levels:
                query = query.filter(RenderLog.level.in_(levels))

            if since_id:
                # لاگ‌های بعد از یک ID خاص
                ref_log = db.query(RenderLog).filter(RenderLog.id == since_id).first()
                if ref_log:
                    query = query.filter(RenderLog.timestamp > ref_log.timestamp)

            logs = query.order_by(RenderLog.timestamp.desc()).limit(limit).all()

            return {
                "success": True,
                "logs": [
                    {
                        "id": log.id,
                        "service_id": log.service_id,
                        "service_name": log.service_name,
                        "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                        "level": log.level,
                        "message": log.message,
                        "deploy_id": log.deploy_id
                    }
                    for log in reversed(logs)  # جدیدترین آخر
                ],
                "count": len(logs),
                "has_more": len(logs) == limit
            }

        except Exception as e:
            slog.error("Failed to fetch logs", exception=e)
            return {"success": False, "error": str(e)}

        finally:
            db.close()

    def get_status(self) -> Dict[str, Any]:
        """وضعیت سرویس"""
        return {
            "is_polling": self.is_polling,
            "connected_clients": len(self.clients),
            "clients": [
                {
                    "id": cid,
                    "connected_at": c.connected_at.isoformat(),
                    "filters": c.filters
                }
                for cid, c in self.clients.items()
            ]
        }


# =====================================================
# Singleton Instance
# =====================================================

_log_stream_instance: Optional[LogStreamService] = None


def get_log_stream_service() -> LogStreamService:
    """دریافت نمونه LogStreamService"""
    global _log_stream_instance
    if _log_stream_instance is None:
        _log_stream_instance = LogStreamService()
    return _log_stream_instance
