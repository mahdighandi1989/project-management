"""
🔍 External System Monitor - مانیتور سامانه‌های خارجی
اتصال، رصد، شناسایی خطا و اعمال تغییرات
"""

import asyncio
import json
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import aiohttp
import logging

logger = logging.getLogger(__name__)


# =====================================
# انواع و مدل‌ها
# =====================================

class SystemStatus(str, Enum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    ERROR = "error"
    OFFLINE = "offline"


class EndpointMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class IssueType(str, Enum):
    ERROR_RESPONSE = "error_response"
    SLOW_RESPONSE = "slow_response"
    CONNECTION_FAILED = "connection_failed"
    INVALID_DATA = "invalid_data"
    SECURITY_ISSUE = "security_issue"
    CONFIGURATION_ISSUE = "configuration_issue"


class IssueSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class DiscoveredEndpoint:
    """اندپوینت کشف شده"""
    path: str
    method: EndpointMethod
    description: str = ""
    parameters: List[Dict] = field(default_factory=list)
    response_schema: Optional[Dict] = None
    requires_auth: bool = False
    last_response_time: Optional[int] = None
    last_status_code: Optional[int] = None
    error_count: int = 0


@dataclass
class SystemIssue:
    """مشکل شناسایی شده"""
    id: str
    system_id: str
    issue_type: IssueType
    severity: IssueSeverity
    title: str
    description: str
    endpoint: Optional[str] = None
    details: Dict = field(default_factory=dict)
    suggested_fix: Optional[str] = None
    auto_fixable: bool = False
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())
    resolved: bool = False
    resolved_at: Optional[str] = None


@dataclass
class ExternalSystem:
    """سامانه خارجی"""
    id: str
    name: str
    base_url: str
    description: str = ""
    auth_type: str = "none"  # none, api_key, bearer, basic
    auth_config: Dict = field(default_factory=dict)
    headers: Dict = field(default_factory=dict)
    status: SystemStatus = SystemStatus.UNKNOWN
    endpoints: List[DiscoveredEndpoint] = field(default_factory=list)
    openapi_schema: Optional[Dict] = None
    last_health_check: Optional[str] = None
    health_history: List[Dict] = field(default_factory=list)
    issues: List[SystemIssue] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class MonitoringResult:
    """نتیجه مانیتورینگ"""
    system_id: str
    timestamp: str
    status: SystemStatus
    response_time_ms: int
    endpoints_checked: int
    endpoints_healthy: int
    issues_found: List[SystemIssue]
    details: Dict = field(default_factory=dict)


# =====================================
# سرویس مانیتور سامانه‌های خارجی
# =====================================

class ExternalSystemMonitor:
    """
    مانیتور سامانه‌های خارجی

    قابلیت‌ها:
    - اتصال و کشف API
    - مانیتورینگ دوره‌ای
    - شناسایی خطاها
    - پیشنهاد و اعمال اصلاحات
    - تحلیل با AI
    """

    def __init__(self, ai_manager=None):
        self.ai_manager = ai_manager
        self.systems: Dict[str, ExternalSystem] = {}
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """دریافت یا ایجاد session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """بستن منابع"""
        # توقف همه monitoring tasks
        for task in self.monitoring_tasks.values():
            task.cancel()

        if self._session and not self._session.closed:
            await self._session.close()

    def _get_auth_headers(self, system: ExternalSystem) -> Dict:
        """ساخت هدرهای احراز هویت"""
        headers = system.headers.copy()

        if system.auth_type == "api_key":
            key_name = system.auth_config.get("key_name", "X-API-Key")
            key_value = system.auth_config.get("key_value", "")
            headers[key_name] = key_value

        elif system.auth_type == "bearer":
            token = system.auth_config.get("token", "")
            headers["Authorization"] = f"Bearer {token}"

        elif system.auth_type == "basic":
            import base64
            username = system.auth_config.get("username", "")
            password = system.auth_config.get("password", "")
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"

        return headers

    # =====================================
    # ثبت و مدیریت سامانه‌ها
    # =====================================

    async def register_system(
        self,
        name: str,
        base_url: str,
        description: str = "",
        auth_type: str = "none",
        auth_config: Dict = None,
        headers: Dict = None,
        auto_discover: bool = True
    ) -> ExternalSystem:
        """ثبت یک سامانه جدید"""
        import uuid

        system_id = f"sys_{uuid.uuid4().hex[:12]}"

        system = ExternalSystem(
            id=system_id,
            name=name,
            base_url=base_url.rstrip('/'),
            description=description,
            auth_type=auth_type,
            auth_config=auth_config or {},
            headers=headers or {}
        )

        self.systems[system_id] = system

        # کشف خودکار API
        if auto_discover:
            await self.discover_api(system_id)

        # Health check اولیه
        await self.health_check(system_id)

        return system

    def get_system(self, system_id: str) -> Optional[ExternalSystem]:
        """دریافت اطلاعات سامانه"""
        return self.systems.get(system_id)

    def list_systems(self) -> List[Dict]:
        """لیست همه سامانه‌ها"""
        return [
            {
                "id": sys.id,
                "name": sys.name,
                "base_url": sys.base_url,
                "status": sys.status.value,
                "endpoints_count": len(sys.endpoints),
                "issues_count": len([i for i in sys.issues if not i.resolved]),
                "last_check": sys.last_health_check
            }
            for sys in self.systems.values()
        ]

    def remove_system(self, system_id: str) -> bool:
        """حذف سامانه"""
        if system_id in self.monitoring_tasks:
            self.monitoring_tasks[system_id].cancel()
            del self.monitoring_tasks[system_id]

        if system_id in self.systems:
            del self.systems[system_id]
            return True
        return False

    # =====================================
    # کشف API
    # =====================================

    async def discover_api(self, system_id: str) -> Dict:
        """کشف API یک سامانه"""
        system = self.systems.get(system_id)
        if not system:
            return {"success": False, "error": "سامانه یافت نشد"}

        session = await self._get_session()
        headers = self._get_auth_headers(system)

        discovered_endpoints = []

        # مسیرهای OpenAPI/Swagger
        openapi_paths = [
            "/openapi.json",
            "/swagger.json",
            "/api/openapi.json",
            "/api/swagger.json",
            "/docs/openapi.json",
            "/api-docs",
            "/v1/openapi.json",
            "/v2/openapi.json",
            "/api/v1/openapi.json"
        ]

        # تلاش برای یافتن OpenAPI
        for path in openapi_paths:
            try:
                url = f"{system.base_url}{path}"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "openapi" in data or "swagger" in data:
                            system.openapi_schema = data

                            # استخراج endpoints
                            paths = data.get("paths", {})
                            for endpoint, methods in paths.items():
                                for method, details in methods.items():
                                    if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                                        discovered_endpoints.append(DiscoveredEndpoint(
                                            path=endpoint,
                                            method=EndpointMethod(method.upper()),
                                            description=details.get("summary", "") or details.get("description", ""),
                                            parameters=details.get("parameters", []),
                                            requires_auth="security" in details or "security" in data
                                        ))
                            break

            except Exception as e:
                logger.debug(f"OpenAPI not found at {path}: {e}")

        # اگر OpenAPI پیدا نشد، endpoint های رایج رو بررسی کن
        if not discovered_endpoints:
            common_endpoints = [
                ("/", "GET"),
                ("/health", "GET"),
                ("/api", "GET"),
                ("/api/v1", "GET"),
                ("/status", "GET"),
                ("/info", "GET"),
                ("/version", "GET")
            ]

            for path, method in common_endpoints:
                try:
                    url = f"{system.base_url}{path}"
                    start = time.time()
                    async with session.request(method, url, headers=headers) as response:
                        elapsed = int((time.time() - start) * 1000)

                        if response.status < 500:
                            discovered_endpoints.append(DiscoveredEndpoint(
                                path=path,
                                method=EndpointMethod(method),
                                description=f"Discovered via probe",
                                last_response_time=elapsed,
                                last_status_code=response.status
                            ))
                except:
                    pass

        system.endpoints = discovered_endpoints
        system.updated_at = datetime.now().isoformat()

        return {
            "success": True,
            "system_id": system_id,
            "endpoints_discovered": len(discovered_endpoints),
            "has_openapi": system.openapi_schema is not None,
            "endpoints": [
                {"path": e.path, "method": e.method.value, "description": e.description}
                for e in discovered_endpoints[:20]
            ]
        }

    # =====================================
    # Health Check و Monitoring
    # =====================================

    async def health_check(self, system_id: str) -> MonitoringResult:
        """بررسی سلامت یک سامانه"""
        system = self.systems.get(system_id)
        if not system:
            return MonitoringResult(
                system_id=system_id,
                timestamp=datetime.now().isoformat(),
                status=SystemStatus.UNKNOWN,
                response_time_ms=0,
                endpoints_checked=0,
                endpoints_healthy=0,
                issues_found=[]
            )

        session = await self._get_session()
        headers = self._get_auth_headers(system)

        issues = []
        endpoints_checked = 0
        endpoints_healthy = 0
        total_time = 0

        # بررسی endpoint اصلی
        try:
            start = time.time()
            async with session.get(system.base_url, headers=headers) as response:
                elapsed = int((time.time() - start) * 1000)
                total_time += elapsed

                endpoints_checked += 1
                if response.status < 400:
                    endpoints_healthy += 1
                else:
                    issues.append(SystemIssue(
                        id=f"issue_{system_id}_{int(time.time())}",
                        system_id=system_id,
                        issue_type=IssueType.ERROR_RESPONSE,
                        severity=IssueSeverity.ERROR if response.status >= 500 else IssueSeverity.WARNING,
                        title=f"HTTP {response.status} on root endpoint",
                        description=f"Root endpoint returned status {response.status}",
                        endpoint="/",
                        details={"status_code": response.status}
                    ))

                # بررسی زمان پاسخ
                if elapsed > 5000:
                    issues.append(SystemIssue(
                        id=f"issue_{system_id}_{int(time.time())}_slow",
                        system_id=system_id,
                        issue_type=IssueType.SLOW_RESPONSE,
                        severity=IssueSeverity.WARNING,
                        title="Slow response time",
                        description=f"Response took {elapsed}ms (> 5000ms threshold)",
                        endpoint="/",
                        details={"response_time_ms": elapsed}
                    ))

        except aiohttp.ClientConnectorError as e:
            issues.append(SystemIssue(
                id=f"issue_{system_id}_{int(time.time())}_conn",
                system_id=system_id,
                issue_type=IssueType.CONNECTION_FAILED,
                severity=IssueSeverity.CRITICAL,
                title="Connection failed",
                description=f"Could not connect to system: {str(e)}",
                details={"error": str(e)}
            ))
        except Exception as e:
            issues.append(SystemIssue(
                id=f"issue_{system_id}_{int(time.time())}_err",
                system_id=system_id,
                issue_type=IssueType.ERROR_RESPONSE,
                severity=IssueSeverity.ERROR,
                title="Health check failed",
                description=str(e),
                details={"error": str(e)}
            ))

        # بررسی endpoints معروف
        for endpoint in system.endpoints[:10]:  # حداکثر 10 endpoint
            try:
                url = f"{system.base_url}{endpoint.path}"
                start = time.time()
                async with session.request(endpoint.method.value, url, headers=headers) as response:
                    elapsed = int((time.time() - start) * 1000)
                    total_time += elapsed

                    endpoint.last_response_time = elapsed
                    endpoint.last_status_code = response.status

                    endpoints_checked += 1
                    if response.status < 400:
                        endpoints_healthy += 1
                        endpoint.error_count = 0
                    else:
                        endpoint.error_count += 1

            except Exception as e:
                endpoint.error_count += 1

        # تعیین وضعیت کلی
        if endpoints_checked == 0 or issues:
            for issue in issues:
                if issue.severity == IssueSeverity.CRITICAL:
                    status = SystemStatus.OFFLINE
                    break
            else:
                if any(i.severity == IssueSeverity.ERROR for i in issues):
                    status = SystemStatus.ERROR
                elif any(i.severity == IssueSeverity.WARNING for i in issues):
                    status = SystemStatus.DEGRADED
                else:
                    status = SystemStatus.HEALTHY
        elif endpoints_healthy == endpoints_checked:
            status = SystemStatus.HEALTHY
        elif endpoints_healthy >= endpoints_checked * 0.7:
            status = SystemStatus.DEGRADED
        else:
            status = SystemStatus.ERROR

        # بروزرسانی سیستم
        system.status = status
        system.last_health_check = datetime.now().isoformat()
        system.issues = [i for i in system.issues if not i.resolved] + issues

        # تاریخچه
        system.health_history.append({
            "timestamp": datetime.now().isoformat(),
            "status": status.value,
            "response_time_ms": total_time // max(endpoints_checked, 1),
            "issues_count": len(issues)
        })
        system.health_history = system.health_history[-100:]

        result = MonitoringResult(
            system_id=system_id,
            timestamp=datetime.now().isoformat(),
            status=status,
            response_time_ms=total_time // max(endpoints_checked, 1),
            endpoints_checked=endpoints_checked,
            endpoints_healthy=endpoints_healthy,
            issues_found=issues
        )

        return result

    async def start_monitoring(
        self,
        system_id: str,
        interval_seconds: int = 60,
        callback: Callable = None
    ):
        """شروع مانیتورینگ دوره‌ای"""
        if system_id in self.monitoring_tasks:
            return {"success": False, "error": "مانیتورینگ فعال است"}

        async def monitor_loop():
            while True:
                try:
                    result = await self.health_check(system_id)
                    if callback:
                        await callback(result)
                    await asyncio.sleep(interval_seconds)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Monitoring error for {system_id}: {e}")
                    await asyncio.sleep(interval_seconds)

        task = asyncio.create_task(monitor_loop())
        self.monitoring_tasks[system_id] = task

        return {"success": True, "message": f"مانیتورینگ شروع شد - هر {interval_seconds} ثانیه"}

    def stop_monitoring(self, system_id: str) -> Dict:
        """توقف مانیتورینگ"""
        if system_id in self.monitoring_tasks:
            self.monitoring_tasks[system_id].cancel()
            del self.monitoring_tasks[system_id]
            return {"success": True, "message": "مانیتورینگ متوقف شد"}
        return {"success": False, "error": "مانیتورینگ فعال نیست"}

    # =====================================
    # تحلیل با AI
    # =====================================

    async def analyze_with_ai(self, system_id: str) -> Dict:
        """تحلیل سامانه با AI"""
        if not self.ai_manager:
            return {"success": False, "error": "AI Manager تنظیم نشده"}

        system = self.systems.get(system_id)
        if not system:
            return {"success": False, "error": "سامانه یافت نشد"}

        # جمع‌آوری اطلاعات
        system_info = {
            "name": system.name,
            "base_url": system.base_url,
            "status": system.status.value,
            "endpoints_count": len(system.endpoints),
            "endpoints": [
                {
                    "path": e.path,
                    "method": e.method.value,
                    "last_status": e.last_status_code,
                    "response_time": e.last_response_time,
                    "errors": e.error_count
                }
                for e in system.endpoints[:20]
            ],
            "issues": [
                {
                    "type": i.issue_type.value,
                    "severity": i.severity.value,
                    "title": i.title,
                    "description": i.description
                }
                for i in system.issues if not i.resolved
            ],
            "health_history": system.health_history[-10:]
        }

        prompt = f"""این سامانه خارجی را تحلیل کن:

```json
{json.dumps(system_info, ensure_ascii=False, indent=2)}
```

موارد زیر را بررسی و گزارش بده:
1. وضعیت کلی سامانه
2. مشکلات شناسایی شده
3. علت احتمالی مشکلات
4. راه‌حل‌های پیشنهادی
5. توصیه‌های بهبود

خروجی JSON:
{{
    "overall_status": "healthy/degraded/critical",
    "summary": "خلاصه وضعیت",
    "identified_issues": [
        {{"issue": "مشکل", "cause": "علت", "solution": "راه‌حل", "priority": "high/medium/low"}}
    ],
    "recommendations": ["توصیه 1", "توصیه 2"],
    "auto_fixable_issues": [
        {{"issue": "مشکل", "fix_command": "دستور یا API call برای رفع"}}
    ]
}}"""

        try:
            response = await self.ai_manager.generate(
                model_id="gpt-4-turbo",
                prompt=prompt,
                max_tokens=2000
            )

            if response.get("success"):
                content = response.get("content", "")
                # استخراج JSON
                try:
                    start = content.find('{')
                    end = content.rfind('}') + 1
                    if start >= 0 and end > start:
                        analysis = json.loads(content[start:end])
                        return {
                            "success": True,
                            "system_id": system_id,
                            "analysis": analysis
                        }
                except:
                    pass

                return {
                    "success": True,
                    "system_id": system_id,
                    "analysis": {"raw": content}
                }

        except Exception as e:
            logger.error(f"AI analysis error: {e}")

        return {"success": False, "error": "خطا در تحلیل"}

    # =====================================
    # درخواست به سامانه
    # =====================================

    async def make_request(
        self,
        system_id: str,
        method: str,
        path: str,
        data: Any = None,
        params: Dict = None
    ) -> Dict:
        """ارسال درخواست به سامانه"""
        system = self.systems.get(system_id)
        if not system:
            return {"success": False, "error": "سامانه یافت نشد"}

        session = await self._get_session()
        headers = self._get_auth_headers(system)
        url = f"{system.base_url}{path}"

        try:
            start = time.time()
            async with session.request(
                method=method.upper(),
                url=url,
                json=data if method.upper() in ['POST', 'PUT', 'PATCH'] else None,
                params=params,
                headers=headers
            ) as response:
                elapsed = int((time.time() - start) * 1000)

                try:
                    body = await response.json()
                except:
                    body = await response.text()

                return {
                    "success": response.status < 400,
                    "status_code": response.status,
                    "response_time_ms": elapsed,
                    "data": body,
                    "headers": dict(response.headers)
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_live_logs(self, system_id: str) -> Dict:
        """دریافت لاگ‌های زنده (اگر endpoint داشته باشه)"""
        system = self.systems.get(system_id)
        if not system:
            return {"success": False, "error": "سامانه یافت نشد"}

        # تلاش برای یافتن endpoint لاگ
        log_endpoints = ["/logs", "/api/logs", "/health/logs", "/status/logs"]

        for path in log_endpoints:
            result = await self.make_request(system_id, "GET", path)
            if result.get("success"):
                return {
                    "success": True,
                    "system_id": system_id,
                    "logs": result.get("data"),
                    "endpoint": path
                }

        return {
            "success": False,
            "error": "endpoint لاگ یافت نشد",
            "suggestion": "می‌توانید endpoint لاگ را به صورت دستی مشخص کنید"
        }


# Singleton
_monitor: Optional[ExternalSystemMonitor] = None


def get_external_monitor(ai_manager=None) -> ExternalSystemMonitor:
    global _monitor
    if _monitor is None:
        _monitor = ExternalSystemMonitor(ai_manager)
    elif ai_manager and not _monitor.ai_manager:
        _monitor.ai_manager = ai_manager
    return _monitor
