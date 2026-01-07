"""
🔗 External Project Connector - اتصال به پروژه‌های خارجی
اتصال به ریپوهای GitHub خصوصی و اپ‌های مستقر شده روی Render/Railway
"""

import asyncio
import json
import base64
import aiohttp
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging
import os

logger = logging.getLogger(__name__)


# =====================================
# انواع و مدل‌ها
# =====================================

class ProjectSourceType(str, Enum):
    GITHUB = "github"
    GITLAB = "gitlab"
    RENDER = "render"
    RAILWAY = "railway"
    VERCEL = "vercel"
    CUSTOM_URL = "custom_url"


class ConnectionStatus(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    AUTH_REQUIRED = "auth_required"


@dataclass
class ExternalProject:
    """پروژه خارجی متصل شده"""
    id: str
    name: str
    source_type: ProjectSourceType
    source_url: str
    description: str = ""

    # Authentication
    auth_token: Optional[str] = None
    auth_method: str = "token"  # token, oauth, personal_access_token

    # GitHub specific
    github_owner: Optional[str] = None
    github_repo: Optional[str] = None
    github_branch: str = "main"
    is_private: bool = False

    # Deployment specific
    deploy_url: Optional[str] = None
    deploy_service: Optional[str] = None  # render, railway, vercel
    deploy_service_id: Optional[str] = None

    # Status
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    last_sync: Optional[str] = None
    last_error: Optional[str] = None

    # Cached data
    files_cache: List[Dict] = field(default_factory=list)
    structure_cache: Dict = field(default_factory=dict)
    readme_content: Optional[str] = None

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class FileInfo:
    """اطلاعات فایل"""
    path: str
    name: str
    type: str  # file, dir
    size: int = 0
    content: Optional[str] = None
    sha: Optional[str] = None


class ExternalProjectConnector:
    """
    مدیریت اتصال به پروژه‌های خارجی
    - GitHub (public/private)
    - GitLab
    - Render
    - Railway
    - Vercel
    """

    def __init__(self, ai_manager=None):
        self.ai_manager = ai_manager
        self.projects: Dict[str, ExternalProject] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self._storage_path = "./data/external_projects"

        # Create storage directory
        os.makedirs(self._storage_path, exist_ok=True)

        # Load saved projects
        self._load_projects()

    async def _ensure_session(self):
        """اطمینان از وجود session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()

    async def close(self):
        """بستن session"""
        if self.session and not self.session.closed:
            await self.session.close()

    def _load_projects(self):
        """بارگذاری پروژه‌های ذخیره شده"""
        try:
            registry_path = os.path.join(self._storage_path, "registry.json")
            if os.path.exists(registry_path):
                with open(registry_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for proj_data in data.get("projects", []):
                        # Don't load tokens from file for security
                        proj_data.pop("auth_token", None)
                        proj = ExternalProject(**proj_data)
                        self.projects[proj.id] = proj
                logger.info(f"Loaded {len(self.projects)} external projects")
        except Exception as e:
            logger.error(f"Error loading external projects: {e}")

    def _save_projects(self):
        """ذخیره پروژه‌ها"""
        try:
            registry_path = os.path.join(self._storage_path, "registry.json")
            # Don't save auth tokens to file
            data = {
                "projects": [
                    {k: v for k, v in asdict(p).items() if k != "auth_token"}
                    for p in self.projects.values()
                ],
                "saved_at": datetime.now().isoformat()
            }
            with open(registry_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving external projects: {e}")

    # =====================================
    # GitHub Integration
    # =====================================

    async def connect_github_repo(
        self,
        repo_url: str,
        token: Optional[str] = None,
        branch: str = "main"
    ) -> Dict:
        """
        اتصال به ریپوی GitHub

        Args:
            repo_url: آدرس ریپو (https://github.com/owner/repo)
            token: Personal Access Token برای ریپوهای خصوصی
            branch: شاخه مورد نظر

        Returns:
            نتیجه اتصال با اطلاعات پروژه
        """
        await self._ensure_session()

        # Parse GitHub URL
        parsed = self._parse_github_url(repo_url)
        if not parsed:
            return {
                "success": False,
                "error": "آدرس GitHub نامعتبر است. فرمت صحیح: https://github.com/owner/repo"
            }

        owner, repo = parsed["owner"], parsed["repo"]
        project_id = f"github_{owner}_{repo}"

        # Check if already connected
        if project_id in self.projects:
            existing = self.projects[project_id]
            if token:
                existing.auth_token = token
            return {
                "success": True,
                "message": "این ریپو قبلاً متصل شده",
                "project": asdict(existing),
                "already_connected": True
            }

        # Test connection
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"token {token}"

        try:
            async with self.session.get(api_url, headers=headers) as resp:
                if resp.status == 404:
                    return {
                        "success": False,
                        "error": "ریپو یافت نشد. اگر خصوصی است، توکن معتبر وارد کنید.",
                        "needs_auth": True
                    }
                elif resp.status == 401:
                    return {
                        "success": False,
                        "error": "توکن نامعتبر است",
                        "needs_auth": True
                    }
                elif resp.status != 200:
                    return {
                        "success": False,
                        "error": f"خطا در اتصال: HTTP {resp.status}"
                    }

                repo_data = await resp.json()
        except Exception as e:
            return {
                "success": False,
                "error": f"خطا در اتصال: {str(e)}"
            }

        # Create project
        project = ExternalProject(
            id=project_id,
            name=repo_data.get("name", repo),
            source_type=ProjectSourceType.GITHUB,
            source_url=repo_url,
            description=repo_data.get("description", ""),
            auth_token=token,
            github_owner=owner,
            github_repo=repo,
            github_branch=branch,
            is_private=repo_data.get("private", False),
            status=ConnectionStatus.CONNECTED,
            last_sync=datetime.now().isoformat()
        )

        # Get README
        readme = await self._get_github_readme(owner, repo, token)
        if readme:
            project.readme_content = readme

        # Get file structure
        structure = await self._get_github_tree(owner, repo, branch, token)
        if structure:
            project.structure_cache = structure
            project.files_cache = structure.get("files", [])

        # Save
        self.projects[project_id] = project
        self._save_projects()

        return {
            "success": True,
            "project": asdict(project),
            "message": f"✅ متصل شد به {owner}/{repo}",
            "file_count": len(project.files_cache),
            "is_private": project.is_private
        }

    def _parse_github_url(self, url: str) -> Optional[Dict]:
        """پارس آدرس GitHub"""
        import re

        patterns = [
            r'github\.com[/:]([^/]+)/([^/\s\.]+)',
            r'^([^/]+)/([^/\s\.]+)$'  # owner/repo format
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                repo = match.group(2)
                if repo.endswith('.git'):
                    repo = repo[:-4]
                return {"owner": match.group(1), "repo": repo}

        return None

    async def _get_github_readme(
        self,
        owner: str,
        repo: str,
        token: Optional[str] = None
    ) -> Optional[str]:
        """دریافت محتوای README"""
        await self._ensure_session()

        api_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"token {token}"

        try:
            async with self.session.get(api_url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = data.get("content", "")
                    if content:
                        return base64.b64decode(content).decode('utf-8')
        except Exception as e:
            logger.warning(f"Could not get README: {e}")

        return None

    async def _get_github_tree(
        self,
        owner: str,
        repo: str,
        branch: str,
        token: Optional[str] = None
    ) -> Optional[Dict]:
        """دریافت ساختار فایل‌های ریپو"""
        await self._ensure_session()

        api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"token {token}"

        try:
            async with self.session.get(api_url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    tree = data.get("tree", [])

                    files = []
                    directories = set()

                    for item in tree:
                        path = item.get("path", "")
                        item_type = item.get("type", "")

                        if item_type == "blob":
                            files.append({
                                "path": path,
                                "name": path.split("/")[-1],
                                "type": "file",
                                "size": item.get("size", 0),
                                "sha": item.get("sha")
                            })
                        elif item_type == "tree":
                            directories.add(path)

                    return {
                        "files": files,
                        "directories": list(directories),
                        "total_files": len(files),
                        "total_dirs": len(directories)
                    }
        except Exception as e:
            logger.error(f"Error getting tree: {e}")

        return None

    async def get_file_content(
        self,
        project_id: str,
        file_path: str
    ) -> Dict:
        """دریافت محتوای یک فایل از پروژه متصل شده"""
        project = self.projects.get(project_id)
        if not project:
            return {"success": False, "error": "پروژه یافت نشد"}

        if project.source_type == ProjectSourceType.GITHUB:
            return await self._get_github_file_content(project, file_path)

        return {"success": False, "error": "نوع پروژه پشتیبانی نمیشود"}

    async def _get_github_file_content(
        self,
        project: ExternalProject,
        file_path: str
    ) -> Dict:
        """دریافت محتوای فایل از GitHub"""
        await self._ensure_session()

        api_url = f"https://api.github.com/repos/{project.github_owner}/{project.github_repo}/contents/{file_path}"
        headers = {"Accept": "application/vnd.github.v3+json"}
        if project.auth_token:
            headers["Authorization"] = f"token {project.auth_token}"

        params = {"ref": project.github_branch}

        try:
            async with self.session.get(api_url, headers=headers, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = data.get("content", "")
                    if content:
                        decoded = base64.b64decode(content).decode('utf-8')
                        return {
                            "success": True,
                            "content": decoded,
                            "path": file_path,
                            "size": data.get("size", 0),
                            "sha": data.get("sha")
                        }
                elif resp.status == 404:
                    return {"success": False, "error": "فایل یافت نشد"}
                else:
                    return {"success": False, "error": f"خطا: HTTP {resp.status}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =====================================
    # Render Integration
    # =====================================

    async def connect_render_app(
        self,
        service_url: str,
        api_key: Optional[str] = None,
        service_id: Optional[str] = None
    ) -> Dict:
        """
        اتصال به اپلیکیشن مستقر شده روی Render
        """
        await self._ensure_session()

        project_id = f"render_{service_url.replace('https://', '').replace('.', '_').replace('/', '_')}"

        # Test connection to the app
        try:
            async with self.session.get(service_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                app_status = "healthy" if resp.status == 200 else "degraded"
        except Exception as e:
            app_status = "offline"
            logger.warning(f"Could not reach Render app: {e}")

        # If API key provided, get service info
        service_info = None
        if api_key and service_id:
            service_info = await self._get_render_service_info(api_key, service_id)

        project = ExternalProject(
            id=project_id,
            name=service_info.get("name", service_url) if service_info else service_url,
            source_type=ProjectSourceType.RENDER,
            source_url=service_url,
            description=service_info.get("description", "") if service_info else "",
            auth_token=api_key,
            deploy_url=service_url,
            deploy_service="render",
            deploy_service_id=service_id,
            status=ConnectionStatus.CONNECTED if app_status == "healthy" else ConnectionStatus.ERROR,
            last_sync=datetime.now().isoformat()
        )

        self.projects[project_id] = project
        self._save_projects()

        return {
            "success": True,
            "project": asdict(project),
            "app_status": app_status,
            "message": f"✅ متصل شد به {service_url}"
        }

    async def _get_render_service_info(
        self,
        api_key: str,
        service_id: str
    ) -> Optional[Dict]:
        """دریافت اطلاعات سرویس از Render API"""
        await self._ensure_session()

        api_url = f"https://api.render.com/v1/services/{service_id}"
        headers = {"Authorization": f"Bearer {api_key}"}

        try:
            async with self.session.get(api_url, headers=headers) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.error(f"Error getting Render service info: {e}")

        return None

    # =====================================
    # Project Management
    # =====================================

    def list_projects(self) -> Dict:
        """لیست همه پروژه‌های متصل شده"""
        projects = []
        for p in self.projects.values():
            proj_dict = asdict(p)
            proj_dict.pop("auth_token", None)  # Don't expose tokens
            projects.append(proj_dict)

        return {
            "success": True,
            "projects": projects,
            "count": len(projects)
        }

    def get_project(self, project_id: str) -> Dict:
        """دریافت اطلاعات یک پروژه"""
        project = self.projects.get(project_id)
        if not project:
            return {"success": False, "error": "پروژه یافت نشد"}

        proj_dict = asdict(project)
        proj_dict.pop("auth_token", None)
        return {"success": True, "project": proj_dict}

    def disconnect_project(self, project_id: str) -> Dict:
        """قطع اتصال از پروژه"""
        if project_id not in self.projects:
            return {"success": False, "error": "پروژه یافت نشد"}

        del self.projects[project_id]
        self._save_projects()

        return {"success": True, "message": "اتصال قطع شد"}

    async def sync_project(self, project_id: str) -> Dict:
        """بروزرسانی اطلاعات پروژه"""
        project = self.projects.get(project_id)
        if not project:
            return {"success": False, "error": "پروژه یافت نشد"}

        if project.source_type == ProjectSourceType.GITHUB:
            # Re-fetch structure
            structure = await self._get_github_tree(
                project.github_owner,
                project.github_repo,
                project.github_branch,
                project.auth_token
            )
            if structure:
                project.structure_cache = structure
                project.files_cache = structure.get("files", [])
                project.last_sync = datetime.now().isoformat()
                self._save_projects()
                return {
                    "success": True,
                    "message": "سینک شد",
                    "file_count": len(project.files_cache)
                }

        return {"success": False, "error": "سینک ناموفق"}

    # =====================================
    # AI Analysis Integration
    # =====================================

    async def analyze_project(
        self,
        project_id: str,
        analysis_type: str = "overview"
    ) -> Dict:
        """
        تحلیل پروژه با AI

        analysis_type:
        - overview: بررسی کلی پروژه
        - issues: شناسایی مشکلات
        - suggestions: پیشنهادات بهبود
        - architecture: تحلیل معماری
        """
        project = self.projects.get(project_id)
        if not project:
            return {"success": False, "error": "پروژه یافت نشد"}

        if not self.ai_manager:
            return {"success": False, "error": "AI Manager در دسترس نیست"}

        # Build context
        context = f"""پروژه: {project.name}
نوع: {project.source_type}
آدرس: {project.source_url}

توضیحات: {project.description}

README:
{project.readme_content[:2000] if project.readme_content else 'ندارد'}

تعداد فایل‌ها: {len(project.files_cache)}

ساختار فایل‌ها:
{self._format_file_structure(project.files_cache[:50])}
"""

        prompts = {
            "overview": f"""این پروژه را بررسی کن و یک خلاصه کامل بده:
{context}

شامل:
1. هدف پروژه
2. تکنولوژی‌های استفاده شده
3. ساختار کلی
4. نقاط قوت و ضعف""",

            "issues": f"""مشکلات احتمالی این پروژه را شناسایی کن:
{context}

شامل:
1. مشکلات ساختاری
2. فایل‌های گمشده احتمالی
3. مشکلات امنیتی
4. مشکلات کارایی""",

            "suggestions": f"""پیشنهادات بهبود برای این پروژه:
{context}

شامل:
1. بهبود ساختار
2. افزودن ویژگی‌ها
3. بهینه‌سازی
4. مستندسازی"""
        }

        prompt = prompts.get(analysis_type, prompts["overview"])

        try:
            from .ai_base import Message
            response = await self.ai_manager.generate(
                model_id="gpt-4-turbo",
                messages=[Message(role="user", content=prompt)],
                max_tokens=2000
            )

            if response.content and not response.error:
                return {
                    "success": True,
                    "analysis_type": analysis_type,
                    "result": response.content,
                    "project_name": project.name
                }
        except Exception as e:
            logger.error(f"AI analysis error: {e}")

        return {"success": False, "error": "تحلیل ناموفق بود"}

    def _format_file_structure(self, files: List[Dict]) -> str:
        """فرمت کردن ساختار فایل‌ها برای نمایش"""
        lines = []
        for f in files:
            path = f.get("path", "")
            size = f.get("size", 0)
            lines.append(f"  {path} ({size} bytes)")
        return "\n".join(lines)


# Singleton instance
_connector_instance: Optional[ExternalProjectConnector] = None


def get_external_project_connector(ai_manager=None) -> ExternalProjectConnector:
    """دریافت نمونه singleton"""
    global _connector_instance
    if _connector_instance is None:
        _connector_instance = ExternalProjectConnector(ai_manager)
    elif ai_manager and _connector_instance.ai_manager is None:
        _connector_instance.ai_manager = ai_manager
    return _connector_instance
