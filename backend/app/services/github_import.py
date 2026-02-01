"""
GitHub Import Service
سرویس وارد کردن پروژه از GitHub (public و private)
"""

import os
import json
import base64
import asyncio
import logging
import aiohttp
from typing import Dict, List, Optional, Any
from datetime import datetime
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class GitHubImportService:
    """سرویس import پروژه از GitHub"""

    GITHUB_API = "https://api.github.com"

    def __init__(self):
        self.default_token = os.environ.get("GITHUB_TOKEN", "")
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """دریافت یا ایجاد session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """بستن session"""
        if self._session and not self._session.closed:
            await self._session.close()

    def _get_headers(self, token: str = None) -> Dict[str, str]:
        """ساخت headers برای درخواست"""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AI-Creator-Engine/1.0"
        }
        use_token = token or self.default_token
        if use_token:
            headers["Authorization"] = f"token {use_token}"
        return headers

    def parse_github_url(self, url: str) -> Dict[str, str]:
        """
        استخراج owner و repo از URL
        پشتیبانی از:
        - https://github.com/owner/repo
        - https://github.com/owner/repo.git
        - git@github.com:owner/repo.git
        - owner/repo
        """
        url = url.strip()

        # حالت owner/repo
        if "/" in url and not url.startswith("http") and not url.startswith("git@"):
            parts = url.split("/")
            if len(parts) >= 2:
                return {"owner": parts[0], "repo": parts[1].replace(".git", "")}

        # حالت git@github.com:owner/repo.git
        if url.startswith("git@"):
            try:
                path = url.split(":")[1]
                parts = path.replace(".git", "").split("/")
                return {"owner": parts[0], "repo": parts[1]}
            except (IndexError, ValueError):
                pass

        # حالت https://github.com/owner/repo
        try:
            parsed = urlparse(url)
            if parsed.netloc in ["github.com", "www.github.com"]:
                parts = parsed.path.strip("/").split("/")
                if len(parts) >= 2:
                    return {"owner": parts[0], "repo": parts[1].replace(".git", "")}
        except (ValueError, AttributeError):
            pass

        return {"owner": "", "repo": ""}

    async def check_repo_access(
        self, owner: str, repo: str, token: str = None
    ) -> Dict[str, Any]:
        """
        بررسی دسترسی به repository
        برمی‌گرداند: اطلاعات repo یا خطا
        """
        session = await self._get_session()
        headers = self._get_headers(token)

        try:
            url = f"{self.GITHUB_API}/repos/{owner}/{repo}"
            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "success": True,
                        "accessible": True,
                        "private": data.get("private", False),
                        "repo_info": {
                            "id": data.get("id"),
                            "name": data.get("name"),
                            "full_name": data.get("full_name"),
                            "description": data.get("description"),
                            "private": data.get("private"),
                            "html_url": data.get("html_url"),
                            "clone_url": data.get("clone_url"),
                            "default_branch": data.get("default_branch", "main"),
                            "language": data.get("language"),
                            "languages_url": data.get("languages_url"),
                            "size": data.get("size"),
                            "stargazers_count": data.get("stargazers_count"),
                            "forks_count": data.get("forks_count"),
                            "created_at": data.get("created_at"),
                            "updated_at": data.get("updated_at"),
                            "pushed_at": data.get("pushed_at"),
                            "topics": data.get("topics", []),
                            "owner": {
                                "login": data.get("owner", {}).get("login"),
                                "avatar_url": data.get("owner", {}).get("avatar_url"),
                            }
                        }
                    }
                elif response.status == 404:
                    return {
                        "success": False,
                        "accessible": False,
                        "error": "Repository not found یا دسترسی ندارید",
                        "hint": "اگر ریپو private است، توکن GitHub وارد کنید"
                    }
                elif response.status == 401:
                    return {
                        "success": False,
                        "accessible": False,
                        "error": "توکن نامعتبر است",
                        "hint": "توکن GitHub خود را بررسی کنید"
                    }
                elif response.status == 403:
                    return {
                        "success": False,
                        "accessible": False,
                        "error": "دسترسی ممنوع - Rate limit یا عدم مجوز",
                        "hint": "کمی صبر کنید یا توکن معتبر وارد کنید"
                    }
                else:
                    return {
                        "success": False,
                        "accessible": False,
                        "error": f"خطای غیرمنتظره: {response.status}"
                    }

        except asyncio.TimeoutError:
            return {"success": False, "error": "Timeout - اتصال برقرار نشد"}
        except aiohttp.ClientError as e:
            return {"success": False, "error": f"خطای شبکه: {str(e)}"}

    async def get_repo_languages(
        self, owner: str, repo: str, token: str = None
    ) -> Dict[str, int]:
        """دریافت زبان‌های استفاده شده در repo"""
        session = await self._get_session()
        headers = self._get_headers(token)

        try:
            url = f"{self.GITHUB_API}/repos/{owner}/{repo}/languages"
            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    return await response.json()
        except (asyncio.TimeoutError, aiohttp.ClientError):
            pass
        return {}

    async def get_repo_tree(
        self, owner: str, repo: str, branch: str = None, token: str = None
    ) -> Dict[str, Any]:
        """
        دریافت ساختار کامل فایل‌های repository
        """
        session = await self._get_session()
        headers = self._get_headers(token)

        # اگر branch مشخص نشده، اول default branch رو بگیر
        if not branch:
            access = await self.check_repo_access(owner, repo, token)
            if access.get("success"):
                branch = access["repo_info"].get("default_branch", "main")
            else:
                branch = "main"

        try:
            # دریافت tree با recursive
            url = f"{self.GITHUB_API}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
            async with session.get(url, headers=headers, timeout=60) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "success": True,
                        "sha": data.get("sha"),
                        "truncated": data.get("truncated", False),
                        "tree": data.get("tree", [])
                    }
                else:
                    return {
                        "success": False,
                        "error": f"خطا در دریافت ساختار: {response.status}"
                    }

        except asyncio.TimeoutError:
            return {"success": False, "error": "Timeout"}
        except aiohttp.ClientError as e:
            return {"success": False, "error": str(e)}

    async def get_file_content(
        self, owner: str, repo: str, path: str, branch: str = None, token: str = None
    ) -> Dict[str, Any]:
        """
        دریافت محتوای یک فایل
        """
        session = await self._get_session()
        headers = self._get_headers(token)

        try:
            url = f"{self.GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
            if branch:
                url += f"?ref={branch}"

            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()

                    # فقط فایل‌ها رو برگردون (نه directory)
                    if data.get("type") != "file":
                        return {"success": False, "error": "این یک فایل نیست"}

                    # decode محتوا
                    content = ""
                    if data.get("content"):
                        try:
                            content = base64.b64decode(data["content"]).decode("utf-8")
                        except (UnicodeDecodeError, ValueError):
                            # فایل باینری
                            content = "[Binary file]"

                    return {
                        "success": True,
                        "path": data.get("path"),
                        "name": data.get("name"),
                        "size": data.get("size"),
                        "sha": data.get("sha"),
                        "content": content,
                        "encoding": data.get("encoding"),
                        "download_url": data.get("download_url"),
                    }
                elif response.status == 404:
                    return {"success": False, "error": "فایل یافت نشد"}
                else:
                    return {"success": False, "error": f"خطا: {response.status}"}

        except asyncio.TimeoutError:
            return {"success": False, "error": "Timeout"}
        except aiohttp.ClientError as e:
            return {"success": False, "error": str(e)}

    async def import_repository(
        self,
        url_or_path: str,
        token: str = None,
        include_files: bool = True,
        max_file_size: int = 500000,  # 500KB
        excluded_dirs: List[str] = None,
        excluded_extensions: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Import کامل یک repository

        Args:
            url_or_path: URL یا owner/repo
            token: توکن GitHub (برای private repos)
            include_files: آیا فایل‌ها هم دانلود شوند
            max_file_size: حداکثر سایز فایل برای دانلود (bytes)
            excluded_dirs: پوشه‌هایی که نباید import شوند
            excluded_extensions: پسوندهایی که نباید import شوند

        Returns:
            اطلاعات کامل پروژه شامل فایل‌ها
        """
        # پیش‌فرض‌ها
        if excluded_dirs is None:
            excluded_dirs = [
                "node_modules", ".git", "__pycache__", ".venv", "venv",
                "dist", "build", ".next", ".cache", "coverage",
                ".idea", ".vscode", "vendor", "packages"
            ]
        if excluded_extensions is None:
            excluded_extensions = [
                ".pyc", ".pyo", ".so", ".dll", ".exe", ".bin",
                ".jpg", ".jpeg", ".png", ".gif", ".ico", ".svg",
                ".mp3", ".mp4", ".wav", ".avi", ".mov",
                ".zip", ".tar", ".gz", ".rar", ".7z",
                ".pdf", ".doc", ".docx", ".xls", ".xlsx",
                ".lock", ".log"
            ]

        # پارس URL
        parsed = self.parse_github_url(url_or_path)
        owner = parsed.get("owner")
        repo = parsed.get("repo")

        if not owner or not repo:
            return {"success": False, "error": "URL نامعتبر است"}

        # بررسی دسترسی
        access = await self.check_repo_access(owner, repo, token)
        if not access.get("success"):
            return access

        repo_info = access["repo_info"]
        branch = repo_info.get("default_branch", "main")

        # دریافت زبان‌ها
        languages = await self.get_repo_languages(owner, repo, token)

        # آماده‌سازی نتیجه
        result = {
            "success": True,
            "project_id": f"gh_{owner}_{repo}".replace("-", "_").lower(),
            "name": repo_info.get("name"),
            "description": repo_info.get("description") or "",
            "source": "github",
            "source_url": repo_info.get("html_url"),
            "clone_url": repo_info.get("clone_url"),
            "owner": owner,
            "repo": repo,
            "branch": branch,
            "private": repo_info.get("private", False),
            "languages": languages,
            "primary_language": repo_info.get("language"),
            "topics": repo_info.get("topics", []),
            "stats": {
                "stars": repo_info.get("stargazers_count", 0),
                "forks": repo_info.get("forks_count", 0),
                "size_kb": repo_info.get("size", 0),
            },
            "dates": {
                "created": repo_info.get("created_at"),
                "updated": repo_info.get("updated_at"),
                "pushed": repo_info.get("pushed_at"),
            },
            "files": [],
            "file_tree": [],
            "imported_at": datetime.now().isoformat(),
        }

        # دریافت ساختار فایل‌ها
        if include_files:
            tree_result = await self.get_repo_tree(owner, repo, branch, token)

            if tree_result.get("success"):
                all_files = tree_result.get("tree", [])

                # فیلتر فایل‌ها
                filtered_files = []
                for item in all_files:
                    if item.get("type") != "blob":
                        continue

                    path = item.get("path", "")

                    # چک excluded directories
                    skip = False
                    for excluded in excluded_dirs:
                        if path.startswith(f"{excluded}/") or f"/{excluded}/" in path:
                            skip = True
                            break
                    if skip:
                        continue

                    # چک excluded extensions
                    for ext in excluded_extensions:
                        if path.lower().endswith(ext):
                            skip = True
                            break
                    if skip:
                        continue

                    # چک سایز
                    size = item.get("size", 0)
                    if size > max_file_size:
                        continue

                    filtered_files.append({
                        "path": path,
                        "size": size,
                        "sha": item.get("sha"),
                    })

                result["file_tree"] = filtered_files
                result["stats"]["file_count"] = len(filtered_files)

                # دانلود محتوای فایل‌های مهم (محدود)
                important_files = [
                    "README.md", "readme.md", "README.MD",
                    "package.json", "requirements.txt", "Cargo.toml",
                    "go.mod", "pom.xml", "build.gradle",
                    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
                    ".env.example", "config.json", "config.yaml",
                    "Makefile", "CMakeLists.txt",
                ]

                # 🆕 مرتب‌سازی هوشمند: اول فایل‌های frontend و backend را قرار بده
                def sort_priority(f):
                    path = f.get("path", "")
                    # اولویت فایل‌های frontend
                    if "frontend/" in path or "src/components/" in path or "src/app/" in path:
                        return 0
                    # اولویت فایل‌های backend
                    if "backend/" in path or "/api/" in path or "/routes/" in path:
                        return 1
                    # فایل‌های کد
                    if path.endswith((".tsx", ".jsx", ".ts", ".js", ".py")):
                        return 2
                    return 3

                sorted_files = sorted(filtered_files, key=sort_priority)

                for file_info in sorted_files[:100]:  # 🔴 افزایش از 50 به 100 فایل
                    path = file_info["path"]
                    filename = path.split("/")[-1]

                    # 🆕 همیشه فایل‌های frontend را دانلود کن
                    is_frontend = (
                        "frontend/" in path or
                        "/components/" in path or
                        "/src/app/" in path or
                        path.endswith((".tsx", ".jsx"))
                    )

                    # فقط فایل‌های مهم و کد رو دانلود کن
                    should_download = (
                        is_frontend or  # 🆕 فایل‌های frontend همیشه
                        filename in important_files or
                        path.endswith((".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".c", ".cpp", ".h")) or
                        file_info["size"] < 50000  # فایل‌های کوچک
                    )

                    if should_download:
                        content_result = await self.get_file_content(
                            owner, repo, path, branch, token
                        )
                        if content_result.get("success"):
                            result["files"].append({
                                "path": path,
                                "content": content_result.get("content", ""),
                                "size": content_result.get("size", 0),
                            })

                        # کمی تاخیر برای جلوگیری از rate limit
                        await asyncio.sleep(0.1)

        return result

    async def save_imported_project(self, import_result: Dict) -> Dict[str, Any]:
        """
        ذخیره پروژه import شده در دیتابیس
        """
        if not import_result.get("success"):
            return import_result

        try:
            from ..core.database import SessionLocal
            from ..models.project import Project, ProjectFile

            db = SessionLocal()
            try:
                project_id = import_result["project_id"]

                # چک وجود پروژه
                existing = db.query(Project).filter(Project.id == project_id).first()

                # آماده‌سازی داده‌ها
                technologies = list(import_result.get("languages", {}).keys())
                structure = {
                    "file_tree": import_result.get("file_tree", []),
                    "branch": import_result.get("branch"),
                }
                metadata = {
                    "source": "github",
                    "source_url": import_result.get("source_url"),
                    "clone_url": import_result.get("clone_url"),
                    "owner": import_result.get("owner"),
                    "repo": import_result.get("repo"),
                    "private": import_result.get("private"),
                    "stats": import_result.get("stats"),
                    "dates": import_result.get("dates"),
                    "topics": import_result.get("topics"),
                    "primary_language": import_result.get("primary_language"),
                }

                if existing:
                    # بروزرسانی
                    existing.name = import_result["name"]
                    existing.description = import_result.get("description", "")
                    existing.technologies = json.dumps(technologies, ensure_ascii=False)
                    existing.structure = json.dumps(structure, ensure_ascii=False)
                    existing.extra_data = json.dumps(metadata, ensure_ascii=False)
                    existing.status = "imported"
                else:
                    # ایجاد جدید
                    project = Project(
                        id=project_id,
                        name=import_result["name"],
                        description=import_result.get("description", ""),
                        project_type="github_import",
                        status="imported",
                        technologies=json.dumps(technologies, ensure_ascii=False),
                        features=json.dumps(import_result.get("topics", []), ensure_ascii=False),
                        structure=json.dumps(structure, ensure_ascii=False),
                        extra_data=json.dumps(metadata, ensure_ascii=False),
                    )
                    db.add(project)

                # ذخیره فایل‌ها
                for file_data in import_result.get("files", []):
                    existing_file = db.query(ProjectFile).filter(
                        ProjectFile.project_id == project_id,
                        ProjectFile.file_path == file_data["path"]
                    ).first()

                    if existing_file:
                        existing_file.content = file_data.get("content", "")
                        existing_file.size = file_data.get("size", 0)
                    else:
                        file_ext = file_data["path"].split(".")[-1] if "." in file_data["path"] else ""
                        project_file = ProjectFile(
                            project_id=project_id,
                            file_path=file_data["path"],
                            content=file_data.get("content", ""),
                            file_type=file_ext,
                            size=file_data.get("size", 0),
                            github_url=f"{import_result.get('source_url')}/blob/{import_result.get('branch')}/{file_data['path']}"
                        )
                        db.add(project_file)

                db.commit()

                return {
                    "success": True,
                    "project_id": project_id,
                    "name": import_result["name"],
                    "files_saved": len(import_result.get("files", [])),
                    "message": "پروژه با موفقیت ذخیره شد"
                }

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error saving imported project: {e}")
            return {"success": False, "error": str(e)}


# Singleton
_github_import_service: Optional[GitHubImportService] = None


def get_github_import_service() -> GitHubImportService:
    global _github_import_service
    if _github_import_service is None:
        _github_import_service = GitHubImportService()
    return _github_import_service
