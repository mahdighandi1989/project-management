"""
📂 GitHub Storage Service - ذخیره‌سازی فایل‌ها در GitHub
"""

import os
import json
import base64
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class GitHubFile:
    """اطلاعات فایل در GitHub"""
    path: str
    name: str
    sha: str
    size: int
    url: str
    download_url: str
    type: str  # file, dir


@dataclass
class GitHubFolder:
    """ساختار پوشه در GitHub"""
    project_id: str
    path: str
    folders: Dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class GitHubStorageService:
    """
    سرویس ذخیره‌سازی فایل‌ها در GitHub

    ساختار پوشه‌ها:
    /ai-workspace/
    ├── debates/
    │   └── {debate_id}/
    │       ├── uploaded/
    │       ├── generated/
    │       └── chunks/
    ├── projects/
    │   └── {project_id}/
    │       ├── source/
    │       ├── generated/
    │       └── outputs/
    └── exports/
    """

    def __init__(
        self,
        token: str = None,
        owner: str = None,
        repo: str = None,
        branch: str = "main",
        base_path: str = "ai-workspace"
    ):
        self.token = token or os.getenv("GITHUB_TOKEN", "")
        self.owner = owner or os.getenv("GITHUB_OWNER", "")
        self.repo = repo or os.getenv("GITHUB_REPO", "")
        self.branch = branch
        self.base_path = base_path
        self.api_base = "https://api.github.com"
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """دریافت یا ایجاد session"""
        if self._session is None or self._session.closed:
            headers = {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28"
            }
            self._session = aiohttp.ClientSession(headers=headers)
        return self._session

    async def close(self):
        """بستن session"""
        if self._session and not self._session.closed:
            await self._session.close()

    def _get_full_path(self, path: str) -> str:
        """مسیر کامل با base_path"""
        return f"{self.base_path}/{path}".strip('/')

    # =====================================
    # عملیات فایل
    # =====================================

    async def upload_file(
        self,
        content: bytes,
        path: str,
        message: str = "Upload file via AI Creator",
        encoding: str = "base64"
    ) -> Dict:
        """آپلود فایل به GitHub"""
        session = await self._get_session()
        full_path = self._get_full_path(path)
        url = f"{self.api_base}/repos/{self.owner}/{self.repo}/contents/{full_path}"

        # بررسی وجود فایل (برای گرفتن SHA در صورت بروزرسانی)
        existing_sha = await self._get_file_sha(full_path)

        # کدگذاری محتوا
        if isinstance(content, str):
            content = content.encode('utf-8')
        content_b64 = base64.b64encode(content).decode('utf-8')

        payload = {
            "message": message,
            "content": content_b64,
            "branch": self.branch
        }

        if existing_sha:
            payload["sha"] = existing_sha

        try:
            async with session.put(url, json=payload) as response:
                if response.status in [200, 201]:
                    data = await response.json()
                    return {
                        "success": True,
                        "path": full_path,
                        "sha": data.get("content", {}).get("sha"),
                        "url": data.get("content", {}).get("html_url"),
                        "download_url": data.get("content", {}).get("download_url")
                    }
                else:
                    error = await response.text()
                    logger.error(f"GitHub upload error: {error}")
                    return {"success": False, "error": error}

        except Exception as e:
            logger.error(f"Error uploading to GitHub: {e}")
            return {"success": False, "error": str(e)}

    async def download_file(self, path: str) -> Optional[bytes]:
        """دانلود فایل از GitHub"""
        session = await self._get_session()
        full_path = self._get_full_path(path)
        url = f"{self.api_base}/repos/{self.owner}/{self.repo}/contents/{full_path}"

        try:
            async with session.get(url, params={"ref": self.branch}) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("encoding") == "base64":
                        return base64.b64decode(data.get("content", ""))
                    return data.get("content", "").encode()

        except Exception as e:
            logger.error(f"Error downloading from GitHub: {e}")

        return None

    async def delete_file(self, path: str, message: str = "Delete file") -> Dict:
        """حذف فایل از GitHub"""
        session = await self._get_session()
        full_path = self._get_full_path(path)
        sha = await self._get_file_sha(full_path)

        if not sha:
            return {"success": False, "error": "فایل یافت نشد"}

        url = f"{self.api_base}/repos/{self.owner}/{self.repo}/contents/{full_path}"

        payload = {
            "message": message,
            "sha": sha,
            "branch": self.branch
        }

        try:
            async with session.delete(url, json=payload) as response:
                if response.status == 200:
                    return {"success": True, "message": "فایل حذف شد"}
                else:
                    error = await response.text()
                    return {"success": False, "error": error}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _get_file_sha(self, path: str) -> Optional[str]:
        """دریافت SHA فایل"""
        session = await self._get_session()
        url = f"{self.api_base}/repos/{self.owner}/{self.repo}/contents/{path}"

        try:
            async with session.get(url, params={"ref": self.branch}) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("sha")
        except:
            pass

        return None

    # =====================================
    # مدیریت پوشه‌ها
    # =====================================

    async def create_folder_structure(
        self,
        entity_type: str,  # debates, projects
        entity_id: str,
        subfolders: List[str] = None
    ) -> Dict:
        """ایجاد ساختار پوشه برای یک موجودیت"""

        if subfolders is None:
            if entity_type == "debates":
                subfolders = ["uploaded", "generated", "chunks"]
            elif entity_type == "projects":
                subfolders = ["source", "generated", "outputs", "docs"]
            else:
                subfolders = ["files"]

        created = []
        base = f"{entity_type}/{entity_id}"

        # ایجاد .gitkeep در هر پوشه
        for folder in subfolders:
            path = f"{base}/{folder}/.gitkeep"
            result = await self.upload_file(
                b"# Auto-generated folder",
                path,
                f"Create {entity_type}/{entity_id}/{folder} folder"
            )
            if result.get("success"):
                created.append(folder)

        return {
            "success": True,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "created_folders": created,
            "base_path": self._get_full_path(base)
        }

    async def list_folder(self, path: str) -> List[GitHubFile]:
        """لیست فایل‌های یک پوشه"""
        session = await self._get_session()
        full_path = self._get_full_path(path)
        url = f"{self.api_base}/repos/{self.owner}/{self.repo}/contents/{full_path}"

        files = []
        try:
            async with session.get(url, params={"ref": self.branch}) as response:
                if response.status == 200:
                    data = await response.json()
                    if isinstance(data, list):
                        for item in data:
                            files.append(GitHubFile(
                                path=item.get("path", ""),
                                name=item.get("name", ""),
                                sha=item.get("sha", ""),
                                size=item.get("size", 0),
                                url=item.get("html_url", ""),
                                download_url=item.get("download_url", ""),
                                type=item.get("type", "file")
                            ))

        except Exception as e:
            logger.error(f"Error listing folder: {e}")

        return files

    async def get_file(self, path: str) -> Dict:
        """دریافت محتوای یک فایل"""
        session = await self._get_session()
        full_path = self._get_full_path(path)
        url = f"{self.api_base}/repos/{self.owner}/{self.repo}/contents/{full_path}"

        try:
            async with session.get(url, params={"ref": self.branch}) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "success": True,
                        "path": path,
                        "content": data.get("content", ""),  # base64 encoded
                        "sha": data.get("sha", ""),
                        "size": data.get("size", 0)
                    }
                else:
                    return {"success": False, "error": f"HTTP {response.status}"}
        except Exception as e:
            logger.error(f"Error getting file: {e}")
            return {"success": False, "error": str(e)}

    # =====================================
    # آپلود فایل‌های بزرگ (chunked)
    # =====================================

    async def upload_large_file(
        self,
        content: bytes,
        path: str,
        chunk_size: int = 1024 * 1024  # 1MB
    ) -> Dict:
        """آپلود فایل بزرگ به صورت تکه‌ای"""

        if len(content) <= chunk_size:
            return await self.upload_file(content, path)

        # تقسیم به chunks
        chunks = []
        for i in range(0, len(content), chunk_size):
            chunk_data = content[i:i + chunk_size]
            chunks.append({
                "index": i // chunk_size,
                "data": chunk_data,
                "size": len(chunk_data)
            })

        # دریافت مسیر پایه
        base_name = path.rsplit('.', 1)[0] if '.' in path else path
        extension = path.rsplit('.', 1)[1] if '.' in path else ""
        chunks_folder = f"{base_name}_chunks"

        # آپلود manifest
        manifest = {
            "original_name": path,
            "total_size": len(content),
            "chunk_count": len(chunks),
            "chunk_size": chunk_size,
            "created_at": datetime.now().isoformat(),
            "chunks": []
        }

        # آپلود هر chunk
        for chunk in chunks:
            chunk_path = f"{chunks_folder}/chunk_{chunk['index']:04d}.bin"
            result = await self.upload_file(
                chunk["data"],
                chunk_path,
                f"Upload chunk {chunk['index'] + 1}/{len(chunks)}"
            )

            if result.get("success"):
                manifest["chunks"].append({
                    "index": chunk["index"],
                    "path": chunk_path,
                    "sha": result.get("sha"),
                    "size": chunk["size"]
                })
            else:
                return {
                    "success": False,
                    "error": f"Failed to upload chunk {chunk['index']}",
                    "partial_upload": manifest
                }

        # آپلود manifest
        manifest_path = f"{chunks_folder}/manifest.json"
        manifest_result = await self.upload_file(
            json.dumps(manifest, ensure_ascii=False).encode(),
            manifest_path,
            "Upload file manifest"
        )

        return {
            "success": True,
            "chunked": True,
            "manifest_path": manifest_path,
            "chunk_count": len(chunks),
            "total_size": len(content)
        }

    async def download_large_file(self, manifest_path: str) -> Optional[bytes]:
        """دانلود فایل بزرگ از chunks"""

        # دانلود manifest
        manifest_data = await self.download_file(manifest_path)
        if not manifest_data:
            return None

        try:
            manifest = json.loads(manifest_data.decode())
        except:
            return None

        # دانلود و ترکیب chunks
        chunks_data = {}
        for chunk_info in manifest.get("chunks", []):
            chunk_content = await self.download_file(
                chunk_info["path"].replace(self.base_path + "/", "")
            )
            if chunk_content:
                chunks_data[chunk_info["index"]] = chunk_content

        # ترکیب به ترتیب
        result = b""
        for i in range(len(chunks_data)):
            if i in chunks_data:
                result += chunks_data[i]
            else:
                logger.error(f"Missing chunk {i}")
                return None

        return result

    # =====================================
    # عملیات برای debates و projects
    # =====================================

    async def save_debate_file(
        self,
        debate_id: str,
        content: bytes,
        filename: str,
        file_type: str = "uploaded"  # uploaded, generated
    ) -> Dict:
        """ذخیره فایل برای یک مناظره"""
        path = f"debates/{debate_id}/{file_type}/{filename}"
        return await self.upload_file(
            content,
            path,
            f"Save {file_type} file for debate {debate_id}"
        )

    async def save_project_file(
        self,
        project_id: str,
        content: bytes,
        filename: str,
        file_type: str = "source"  # source, generated, outputs
    ) -> Dict:
        """ذخیره فایل برای یک پروژه"""
        path = f"projects/{project_id}/{file_type}/{filename}"
        return await self.upload_file(
            content,
            path,
            f"Save {file_type} file for project {project_id}"
        )

    async def get_debate_files(self, debate_id: str) -> Dict:
        """لیست فایل‌های یک مناظره"""
        files = {
            "uploaded": await self.list_folder(f"debates/{debate_id}/uploaded"),
            "generated": await self.list_folder(f"debates/{debate_id}/generated"),
            "chunks": await self.list_folder(f"debates/{debate_id}/chunks")
        }
        return {
            "success": True,
            "debate_id": debate_id,
            "files": {
                k: [{"name": f.name, "size": f.size, "url": f.download_url}
                    for f in v if f.name != ".gitkeep"]
                for k, v in files.items()
            }
        }

    async def get_project_files(self, project_id: str) -> Dict:
        """لیست فایل‌های یک پروژه"""
        files = {
            "source": await self.list_folder(f"projects/{project_id}/source"),
            "generated": await self.list_folder(f"projects/{project_id}/generated"),
            "outputs": await self.list_folder(f"projects/{project_id}/outputs")
        }
        return {
            "success": True,
            "project_id": project_id,
            "files": {
                k: [{"name": f.name, "size": f.size, "url": f.download_url}
                    for f in v if f.name != ".gitkeep"]
                for k, v in files.items()
            }
        }

    # =====================================
    # بررسی اتصال
    # =====================================

    async def check_connection(self) -> Dict:
        """بررسی اتصال به GitHub"""
        if not self.token or not self.owner or not self.repo:
            return {
                "success": False,
                "error": "اطلاعات GitHub تنظیم نشده",
                "configured": False
            }

        session = await self._get_session()
        url = f"{self.api_base}/repos/{self.owner}/{self.repo}"

        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "success": True,
                        "configured": True,
                        "repo": data.get("full_name"),
                        "private": data.get("private"),
                        "default_branch": data.get("default_branch")
                    }
                elif response.status == 404:
                    return {
                        "success": False,
                        "error": "Repository یافت نشد",
                        "configured": True
                    }
                elif response.status == 401:
                    return {
                        "success": False,
                        "error": "Token نامعتبر",
                        "configured": True
                    }
                else:
                    return {
                        "success": False,
                        "error": f"خطای {response.status}",
                        "configured": True
                    }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "configured": True
            }


# Singleton
_github_storage: Optional[GitHubStorageService] = None


def get_github_storage() -> GitHubStorageService:
    global _github_storage
    if _github_storage is None:
        _github_storage = GitHubStorageService()
    return _github_storage


def configure_github_storage(
    token: str = None,
    owner: str = None,
    repo: str = None,
    branch: str = "main"
) -> GitHubStorageService:
    """پیکربندی سرویس با پارامترهای جدید"""
    global _github_storage
    _github_storage = GitHubStorageService(
        token=token,
        owner=owner,
        repo=repo,
        branch=branch
    )
    return _github_storage
