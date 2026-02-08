"""
🚀 Deploy Service - سرویس Deploy یک‌کلیکه
Deploy خودکار به Render، Railway و سرویس‌های دیگر
"""

import os
import json
import asyncio
import aiohttp
import base64
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DeployProvider(str, Enum):
    """پلتفرم‌های Deploy"""
    RENDER = "render"
    RAILWAY = "railway"
    VERCEL = "vercel"
    FLY = "fly"


class DeployStatus(str, Enum):
    """وضعیت Deploy"""
    PENDING = "pending"
    BUILDING = "building"
    DEPLOYING = "deploying"
    LIVE = "live"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class DeployConfig:
    """تنظیمات Deploy"""
    provider: DeployProvider
    api_key: str
    project_name: str
    project_type: str  # python, nodejs, static
    build_command: Optional[str] = None
    start_command: Optional[str] = None
    env_vars: Dict[str, str] = field(default_factory=dict)
    port: int = 8000
    auto_deploy: bool = True
    branch: str = "main"


@dataclass
class Deployment:
    """اطلاعات یک Deployment"""
    id: str
    project_id: str
    provider: DeployProvider
    service_id: Optional[str] = None
    status: DeployStatus = DeployStatus.PENDING
    url: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None


class RenderDeployService:
    """
    سرویس Deploy به Render.com

    قابلیت‌ها:
    1. ایجاد سرویس جدید
    2. Deploy از GitHub
    3. Deploy مستقیم کد
    4. مانیتورینگ وضعیت
    5. مدیریت environment variables
    """

    API_BASE = "https://api.render.com/v1"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("RENDER_API_KEY", "")
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """دریافت HTTP session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            })
        return self._session

    async def close(self):
        """بستن session"""
        if self._session and not self._session.closed:
            await self._session.close()

    def is_configured(self) -> bool:
        """آیا API key تنظیم شده؟"""
        return bool(self.api_key)

    async def list_services(self) -> List[Dict]:
        """لیست سرویس‌های موجود در Render"""
        if not self.is_configured():
            return []

        session = await self._get_session()

        try:
            async with session.get(f"{self.API_BASE}/services") as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    return []
        except Exception as e:
            logger.error(f"Error listing services: {e}")
            return []

    async def create_service(
        self,
        name: str,
        project_type: str,
        github_repo_url: str = None,
        github_branch: str = "main",
        root_dir: str = ".",
        build_command: str = None,
        start_command: str = None,
        env_vars: Dict[str, str] = None,
        auto_deploy: bool = True,
        service_type: str = "web_service",
        publish_path: str = None,
    ) -> Dict:
        """
        ایجاد سرویس جدید در Render
        service_type: "web_service" یا "static_site"
        """
        if not self.is_configured():
            return {"success": False, "error": "Render API key not configured"}

        session = await self._get_session()

        # دریافت ownerId از Render API (الزامی برای ایجاد سرویس)
        owner_id = None
        try:
            async with session.get(f"{self.API_BASE}/owners") as owner_resp:
                if owner_resp.status == 200:
                    owners = await owner_resp.json()
                    if owners and len(owners) > 0:
                        first_owner = owners[0]
                        owner_id = first_owner.get("owner", {}).get("id") or first_owner.get("id")
        except Exception:
            pass

        if not owner_id:
            return {"success": False, "error": "Owner ID دریافت نشد. لطفاً API Key رندر را بررسی کنید."}

        # تنظیمات بر اساس نوع پروژه
        if project_type in ['python', 'fastapi', 'flask', 'django']:
            env = "python"
            build_cmd = build_command or "pip install --upgrade pip setuptools && pip install -r requirements.txt"
            start_cmd = start_command or "python main.py"
        elif project_type in ['nodejs', 'express', 'react', 'nextjs', 'vite']:
            env = "node"
            build_cmd = build_command or "npm install && npm run build"
            start_cmd = start_command or "npm start"
        else:
            env = "docker"
            build_cmd = build_command
            start_cmd = start_command

        if service_type == "static_site":
            # Static Site: فقط build و publish path
            service_data = {
                "type": "static_site",
                "name": name.lower().replace(' ', '-').replace('_', '-'),
                "ownerId": owner_id,
                "autoDeploy": "yes" if auto_deploy else "no",
                "serviceDetails": {
                    "buildCommand": build_cmd,
                    "publishPath": publish_path or "dist",
                }
            }
        else:
            # Web Service: نیاز به env و startCommand
            service_data = {
                "type": "web_service",
                "name": name.lower().replace(' ', '-').replace('_', '-'),
                "ownerId": owner_id,
                "autoDeploy": "yes" if auto_deploy else "no",
                "serviceDetails": {
                    "env": env,
                    "envSpecificDetails": {
                        "buildCommand": build_cmd,
                        "startCommand": start_cmd
                    }
                }
            }

        # اگر repo داریم
        if github_repo_url:
            service_data["repo"] = github_repo_url
            service_data["branch"] = github_branch
            if root_dir and root_dir != ".":
                service_data["rootDir"] = root_dir

        # Environment variables
        if env_vars:
            service_data["envVars"] = [
                {"key": k, "value": v} for k, v in env_vars.items()
            ]

        try:
            async with session.post(
                f"{self.API_BASE}/services",
                json=service_data
            ) as response:
                response_text = await response.text()

                if response.status in [200, 201]:
                    data = json.loads(response_text)
                    service = data.get("service", data)

                    svc_type = service.get("type", "web_service")
                    svc_id = service.get("id")
                    dash_prefix = "static" if svc_type == "static_site" else "web"

                    # برای static_site: اضافه کردن SPA rewrite rule از طریق API
                    if svc_type == "static_site" and svc_id:
                        try:
                            rewrite_data = {
                                "source": "/*",
                                "destination": "/index.html",
                                "action": "rewrite",
                            }
                            async with session.post(
                                f"{self.API_BASE}/services/{svc_id}/routes",
                                json=rewrite_data
                            ) as rw_resp:
                                if rw_resp.status in [200, 201]:
                                    logger.info(f"SPA rewrite rule added for {svc_id}")
                                else:
                                    logger.warning(f"Failed to add rewrite rule: {await rw_resp.text()}")
                        except Exception as rw_err:
                            logger.warning(f"Rewrite rule error: {rw_err}")

                    return {
                        "success": True,
                        "service_id": svc_id,
                        "name": service.get("name"),
                        "url": service.get("serviceDetails", {}).get("url"),
                        "status": service.get("suspended"),
                        "dashboard_url": f"https://dashboard.render.com/{dash_prefix}/{svc_id}",
                        "service_type": svc_type,
                    }
                else:
                    return {
                        "success": False,
                        "error": response_text,
                        "status_code": response.status
                    }

        except Exception as e:
            logger.error(f"Error creating service: {e}")
            return {"success": False, "error": str(e)}

    async def deploy_from_files(
        self,
        service_id: str,
        files: Dict[str, str]
    ) -> Dict:
        """
        Deploy مستقیم فایل‌ها به یک سرویس موجود

        این متد از طریق API مستقیم کار نمی‌کنه
        باید از طریق GitHub انجام بشه
        """
        return {
            "success": False,
            "error": "Direct file deployment not supported. Please sync to GitHub first."
        }

    async def get_service(self, service_id: str) -> Dict:
        """دریافت اطلاعات سرویس"""
        if not self.is_configured():
            return {"success": False, "error": "Not configured"}

        session = await self._get_session()

        try:
            async with session.get(f"{self.API_BASE}/services/{service_id}") as response:
                if response.status == 200:
                    data = await response.json()
                    return {"success": True, "service": data}
                else:
                    return {"success": False, "error": await response.text()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_deploy_status(self, service_id: str) -> Dict:
        """وضعیت Deploy سرویس"""
        if not self.is_configured():
            return {"success": False, "error": "Not configured"}

        session = await self._get_session()

        try:
            # دریافت آخرین deploy
            async with session.get(
                f"{self.API_BASE}/services/{service_id}/deploys",
                params={"limit": 1}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    deploys = data if isinstance(data, list) else data.get("deploys", [])

                    if deploys:
                        latest = deploys[0].get("deploy", deploys[0])
                        return {
                            "success": True,
                            "deploy_id": latest.get("id"),
                            "status": latest.get("status"),
                            "created_at": latest.get("createdAt"),
                            "finished_at": latest.get("finishedAt")
                        }
                    else:
                        return {
                            "success": True,
                            "status": "no_deploys",
                            "message": "No deployments found"
                        }
                else:
                    return {"success": False, "error": await response.text()}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def trigger_deploy(self, service_id: str, clear_cache: bool = False) -> Dict:
        """Trigger یک Deploy جدید"""
        if not self.is_configured():
            return {"success": False, "error": "Not configured"}

        session = await self._get_session()

        try:
            async with session.post(
                f"{self.API_BASE}/services/{service_id}/deploys",
                json={"clearCache": "clear" if clear_cache else "do_not_clear"}
            ) as response:
                if response.status in [200, 201]:
                    data = await response.json()
                    return {
                        "success": True,
                        "deploy_id": data.get("deploy", data).get("id"),
                        "status": data.get("deploy", data).get("status")
                    }
                else:
                    return {"success": False, "error": await response.text()}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def suspend_service(self, service_id: str) -> Dict:
        """متوقف کردن سرویس"""
        if not self.is_configured():
            return {"success": False, "error": "Not configured"}

        session = await self._get_session()

        try:
            async with session.post(
                f"{self.API_BASE}/services/{service_id}/suspend"
            ) as response:
                if response.status == 200:
                    return {"success": True, "message": "Service suspended"}
                else:
                    return {"success": False, "error": await response.text()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def resume_service(self, service_id: str) -> Dict:
        """راه‌اندازی مجدد سرویس"""
        if not self.is_configured():
            return {"success": False, "error": "Not configured"}

        session = await self._get_session()

        try:
            async with session.post(
                f"{self.API_BASE}/services/{service_id}/resume"
            ) as response:
                if response.status == 200:
                    return {"success": True, "message": "Service resumed"}
                else:
                    return {"success": False, "error": await response.text()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def delete_service(self, service_id: str) -> Dict:
        """حذف سرویس"""
        if not self.is_configured():
            return {"success": False, "error": "Not configured"}

        session = await self._get_session()

        try:
            async with session.delete(
                f"{self.API_BASE}/services/{service_id}"
            ) as response:
                if response.status in [200, 204]:
                    return {"success": True, "message": "Service deleted"}
                else:
                    return {"success": False, "error": await response.text()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_logs(self, service_id: str, lines: int = 100) -> Dict:
        """دریافت لاگ‌های سرویس"""
        if not self.is_configured():
            return {"success": False, "error": "Not configured"}

        session = await self._get_session()

        try:
            async with session.get(
                f"{self.API_BASE}/services/{service_id}/logs",
                params={"limit": lines}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "success": True,
                        "logs": data
                    }
                else:
                    return {"success": False, "error": await response.text()}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def update_env_vars(
        self,
        service_id: str,
        env_vars: Dict[str, str]
    ) -> Dict:
        """بروزرسانی Environment Variables"""
        if not self.is_configured():
            return {"success": False, "error": "Not configured"}

        session = await self._get_session()

        try:
            # دریافت env vars فعلی
            async with session.get(
                f"{self.API_BASE}/services/{service_id}/env-vars"
            ) as response:
                if response.status != 200:
                    return {"success": False, "error": "Failed to get current env vars"}

                current_vars = await response.json()

            # بروزرسانی
            for key, value in env_vars.items():
                existing = next(
                    (v for v in current_vars if v.get("key") == key),
                    None
                )

                if existing:
                    # بروزرسانی موجود
                    async with session.put(
                        f"{self.API_BASE}/services/{service_id}/env-vars/{existing['id']}",
                        json={"value": value}
                    ) as resp:
                        pass
                else:
                    # ایجاد جدید
                    async with session.post(
                        f"{self.API_BASE}/services/{service_id}/env-vars",
                        json={"key": key, "value": value}
                    ) as resp:
                        pass

            return {"success": True, "message": "Environment variables updated"}

        except Exception as e:
            return {"success": False, "error": str(e)}


class DeployManager:
    """
    مدیر Deploy - هماهنگ‌کننده همه پلتفرم‌ها
    """

    def __init__(self):
        self.render = RenderDeployService()
        self._deployments: Dict[str, Deployment] = {}

    def configure_render(self, api_key: str):
        """تنظیم Render API key"""
        self.render = RenderDeployService(api_key)

    async def quick_deploy(
        self,
        project_id: str,
        project_name: str,
        project_type: str,
        github_repo_url: str,
        github_branch: str = "main",
        root_dir: str = ".",
        env_vars: Dict[str, str] = None,
        provider: DeployProvider = DeployProvider.RENDER
    ) -> Deployment:
        """
        Deploy سریع یک پروژه

        این متد:
        1. سرویس رو ایجاد می‌کنه
        2. Deploy رو شروع می‌کنه
        3. اطلاعات رو برمی‌گردونه
        """
        deployment_id = f"deploy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        deployment = Deployment(
            id=deployment_id,
            project_id=project_id,
            provider=provider
        )

        if provider == DeployProvider.RENDER:
            result = await self.render.create_service(
                name=project_name,
                project_type=project_type,
                github_repo_url=github_repo_url,
                github_branch=github_branch,
                root_dir=root_dir,
                env_vars=env_vars
            )

            if result.get("success"):
                deployment.service_id = result.get("service_id")
                deployment.url = result.get("url")
                deployment.status = DeployStatus.BUILDING
            else:
                deployment.status = DeployStatus.FAILED
                deployment.error = result.get("error")

        self._deployments[deployment_id] = deployment
        return deployment

    async def get_deployment(self, deployment_id: str) -> Optional[Deployment]:
        """دریافت اطلاعات Deployment"""
        return self._deployments.get(deployment_id)

    async def check_deployment_status(self, deployment_id: str) -> Deployment:
        """بررسی وضعیت Deployment"""
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            return None

        if deployment.provider == DeployProvider.RENDER and deployment.service_id:
            status = await self.render.get_deploy_status(deployment.service_id)
            if status.get("success"):
                render_status = status.get("status", "unknown")

                if render_status == "live":
                    deployment.status = DeployStatus.LIVE
                elif render_status in ["build_in_progress", "update_in_progress"]:
                    deployment.status = DeployStatus.BUILDING
                elif render_status == "deactivated":
                    deployment.status = DeployStatus.STOPPED
                elif render_status in ["build_failed", "canceled"]:
                    deployment.status = DeployStatus.FAILED

                deployment.updated_at = datetime.now().isoformat()

        return deployment

    async def list_deployed_projects(self) -> List[Dict]:
        """لیست پروژه‌های Deploy شده"""
        services = await self.render.list_services()
        return services

    async def stop_deployment(self, deployment_id: str) -> Dict:
        """متوقف کردن Deployment"""
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            return {"success": False, "error": "Deployment not found"}

        if deployment.provider == DeployProvider.RENDER and deployment.service_id:
            result = await self.render.suspend_service(deployment.service_id)
            if result.get("success"):
                deployment.status = DeployStatus.STOPPED
            return result

        return {"success": False, "error": "Unsupported provider"}

    async def restart_deployment(self, deployment_id: str) -> Dict:
        """راه‌اندازی مجدد Deployment"""
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            return {"success": False, "error": "Deployment not found"}

        if deployment.provider == DeployProvider.RENDER and deployment.service_id:
            result = await self.render.resume_service(deployment.service_id)
            if result.get("success"):
                deployment.status = DeployStatus.BUILDING
            return result

        return {"success": False, "error": "Unsupported provider"}


# سینگلتون (thread-safe)
_deploy_manager: Optional[DeployManager] = None
_deploy_manager_lock = threading.Lock()


def get_deploy_manager() -> DeployManager:
    """دریافت Deploy Manager (thread-safe)"""
    global _deploy_manager
    if _deploy_manager is None:
        with _deploy_manager_lock:
            # Double-check locking pattern
            if _deploy_manager is None:
                _deploy_manager = DeployManager()
    return _deploy_manager


def configure_deploy_manager(render_api_key: str = None):
    """پیکربندی Deploy Manager"""
    manager = get_deploy_manager()
    if render_api_key:
        manager.configure_render(render_api_key)
    return manager
