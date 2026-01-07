"""
📦 Unified Storage Service - لایه ذخیره‌سازی یکپارچه
ترکیب ذخیره‌سازی محلی + GitHub + آماده‌سازی برای Deploy
"""

import os
import json
import shutil
import asyncio
import aiofiles
import aiohttp
import base64
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProjectFile:
    """اطلاعات یک فایل در پروژه"""
    path: str
    name: str
    content: Optional[str] = None
    size: int = 0
    is_binary: bool = False
    language: Optional[str] = None
    last_modified: str = field(default_factory=lambda: datetime.now().isoformat())
    checksum: Optional[str] = None


@dataclass
class ProjectConfig:
    """تنظیمات پروژه"""
    id: str
    name: str
    description: str = ""
    project_type: str = "unknown"  # python, javascript, react, fastapi, etc.
    technologies: List[str] = field(default_factory=list)
    entry_point: Optional[str] = None  # main.py, index.js, etc.
    build_command: Optional[str] = None
    start_command: Optional[str] = None
    port: int = 8000
    env_vars: Dict[str, str] = field(default_factory=dict)
    dependencies: Dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    github_synced: bool = False
    render_deployed: bool = False
    render_service_id: Optional[str] = None
    render_url: Optional[str] = None


class UnifiedStorageService:
    """
    سرویس ذخیره‌سازی یکپارچه

    قابلیت‌ها:
    1. ذخیره‌سازی محلی سریع
    2. سینک خودکار با GitHub
    3. آماده‌سازی برای Deploy به Render
    4. مدیریت فایل‌های پروژه
    5. تشخیص نوع پروژه

    ساختار:
    workspace/
    ├── projects/
    │   └── {project_id}/
    │       ├── .project.json      # تنظیمات پروژه
    │       ├── src/               # کد منبع
    │       ├── generated/         # فایل‌های تولید شده
    │       └── diagrams/          # نمودارها
    └── cache/
        └── github/                # کش GitHub
    """

    # نوع فایل‌ها به زبان
    LANGUAGE_MAP = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'javascript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.go': 'go',
        '.rs': 'rust',
        '.rb': 'ruby',
        '.php': 'php',
        '.cs': 'csharp',
        '.cpp': 'cpp',
        '.c': 'c',
        '.html': 'html',
        '.css': 'css',
        '.json': 'json',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.md': 'markdown',
        '.sql': 'sql',
        '.sh': 'bash',
        '.dockerfile': 'dockerfile',
        '.mq4': 'mql4',
        '.mq5': 'mql5',
    }

    # تشخیص نوع پروژه از فایل‌ها
    PROJECT_TYPE_PATTERNS = {
        'react': ['package.json', 'src/App.jsx', 'src/App.tsx'],
        'nextjs': ['next.config.js', 'next.config.mjs', 'pages/', 'app/'],
        'vue': ['vue.config.js', 'src/App.vue'],
        'fastapi': ['main.py', 'requirements.txt', 'app/'],
        'django': ['manage.py', 'settings.py'],
        'flask': ['app.py', 'requirements.txt'],
        'express': ['package.json', 'server.js', 'index.js'],
        'python': ['main.py', 'setup.py', 'requirements.txt'],
        'nodejs': ['package.json', 'index.js'],
    }

    def __init__(
        self,
        workspace_path: str = "./workspace",
        github_token: Optional[str] = None,
        github_owner: Optional[str] = None,
        github_repo: Optional[str] = None,
        render_api_key: Optional[str] = None,
        auto_sync: bool = False
    ):
        self.workspace_path = Path(workspace_path)
        self.projects_path = self.workspace_path / "projects"
        self.cache_path = self.workspace_path / "cache"

        # GitHub settings
        self.github_token = github_token or os.getenv("GITHUB_TOKEN", "")
        self.github_owner = github_owner or os.getenv("GITHUB_OWNER", "")
        self.github_repo = github_repo or os.getenv("GITHUB_REPO", "")
        self.github_branch = "main"

        # Render settings
        self.render_api_key = render_api_key or os.getenv("RENDER_API_KEY", "")

        self.auto_sync = auto_sync
        self._session: Optional[aiohttp.ClientSession] = None

        # ایجاد ساختار پوشه‌ها
        self._ensure_structure()

    def _ensure_structure(self):
        """ایجاد ساختار پوشه‌ها"""
        self.projects_path.mkdir(parents=True, exist_ok=True)
        self.cache_path.mkdir(parents=True, exist_ok=True)
        (self.cache_path / "github").mkdir(exist_ok=True)

    async def _get_session(self) -> aiohttp.ClientSession:
        """دریافت یا ایجاد HTTP session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """بستن session"""
        if self._session and not self._session.closed:
            await self._session.close()

    # =====================================
    # 📁 مدیریت پروژه‌ها
    # =====================================

    async def create_project(
        self,
        name: str,
        description: str = "",
        project_type: str = "unknown",
        technologies: List[str] = None
    ) -> ProjectConfig:
        """ایجاد پروژه جدید"""
        project_id = f"proj_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hashlib.md5(name.encode()).hexdigest()[:6]}"

        project_path = self.projects_path / project_id
        project_path.mkdir(parents=True, exist_ok=True)
        (project_path / "src").mkdir(exist_ok=True)
        (project_path / "generated").mkdir(exist_ok=True)
        (project_path / "diagrams").mkdir(exist_ok=True)

        # تنظیمات پیش‌فرض بر اساس نوع پروژه
        config = self._get_default_config(project_type)

        project_config = ProjectConfig(
            id=project_id,
            name=name,
            description=description,
            project_type=project_type,
            technologies=technologies or [],
            entry_point=config.get("entry_point"),
            build_command=config.get("build_command"),
            start_command=config.get("start_command"),
            port=config.get("port", 8000)
        )

        # ذخیره تنظیمات
        await self._save_project_config(project_id, project_config)

        logger.info(f"Project created: {project_id} ({name})")
        return project_config

    def _get_default_config(self, project_type: str) -> Dict:
        """تنظیمات پیش‌فرض برای هر نوع پروژه"""
        configs = {
            "python": {
                "entry_point": "main.py",
                "build_command": "pip install -r requirements.txt",
                "start_command": "python main.py",
                "port": 8000
            },
            "fastapi": {
                "entry_point": "main.py",
                "build_command": "pip install -r requirements.txt",
                "start_command": "uvicorn main:app --host 0.0.0.0 --port $PORT",
                "port": 8000
            },
            "flask": {
                "entry_point": "app.py",
                "build_command": "pip install -r requirements.txt",
                "start_command": "gunicorn app:app --bind 0.0.0.0:$PORT",
                "port": 5000
            },
            "react": {
                "entry_point": "src/index.js",
                "build_command": "npm install && npm run build",
                "start_command": "npm start",
                "port": 3000
            },
            "nextjs": {
                "entry_point": "pages/index.js",
                "build_command": "npm install && npm run build",
                "start_command": "npm start",
                "port": 3000
            },
            "express": {
                "entry_point": "index.js",
                "build_command": "npm install",
                "start_command": "node index.js",
                "port": 3000
            },
            "nodejs": {
                "entry_point": "index.js",
                "build_command": "npm install",
                "start_command": "node index.js",
                "port": 3000
            }
        }
        return configs.get(project_type, {
            "entry_point": "main.py",
            "start_command": "python main.py",
            "port": 8000
        })

    async def _save_project_config(self, project_id: str, config: ProjectConfig):
        """ذخیره تنظیمات پروژه"""
        config_path = self.projects_path / project_id / ".project.json"
        config.updated_at = datetime.now().isoformat()

        async with aiofiles.open(config_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(asdict(config), ensure_ascii=False, indent=2))

    async def get_project_config(self, project_id: str) -> Optional[ProjectConfig]:
        """دریافت تنظیمات پروژه"""
        config_path = self.projects_path / project_id / ".project.json"

        if not config_path.exists():
            return None

        async with aiofiles.open(config_path, 'r', encoding='utf-8') as f:
            data = json.loads(await f.read())
            return ProjectConfig(**data)

    async def list_projects(self) -> List[ProjectConfig]:
        """لیست همه پروژه‌ها"""
        projects = []

        if not self.projects_path.exists():
            return projects

        for project_dir in self.projects_path.iterdir():
            if project_dir.is_dir():
                config = await self.get_project_config(project_dir.name)
                if config:
                    projects.append(config)

        return sorted(projects, key=lambda p: p.updated_at, reverse=True)

    async def delete_project(self, project_id: str) -> bool:
        """حذف پروژه"""
        project_path = self.projects_path / project_id

        if project_path.exists():
            shutil.rmtree(project_path)
            logger.info(f"Project deleted: {project_id}")
            return True
        return False

    # =====================================
    # 📄 مدیریت فایل‌ها
    # =====================================

    async def save_file(
        self,
        project_id: str,
        file_path: str,
        content: Union[str, bytes],
        folder: str = "src"
    ) -> ProjectFile:
        """ذخیره فایل در پروژه"""
        # مسیر کامل
        full_path = self.projects_path / project_id / folder / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # تشخیص نوع محتوا
        is_binary = isinstance(content, bytes)

        if is_binary:
            async with aiofiles.open(full_path, 'wb') as f:
                await f.write(content)
        else:
            async with aiofiles.open(full_path, 'w', encoding='utf-8') as f:
                await f.write(content)

        # زبان فایل
        ext = Path(file_path).suffix.lower()
        language = self.LANGUAGE_MAP.get(ext)

        # checksum
        if is_binary:
            checksum = hashlib.md5(content).hexdigest()
        else:
            checksum = hashlib.md5(content.encode()).hexdigest()

        file_info = ProjectFile(
            path=f"{folder}/{file_path}",
            name=Path(file_path).name,
            size=len(content),
            is_binary=is_binary,
            language=language,
            checksum=checksum
        )

        # بروزرسانی زمان پروژه
        config = await self.get_project_config(project_id)
        if config:
            config.updated_at = datetime.now().isoformat()
            await self._save_project_config(project_id, config)

        # سینک خودکار با GitHub
        if self.auto_sync and self.github_token:
            await self._sync_file_to_github(project_id, file_path, content, folder)

        logger.info(f"File saved: {project_id}/{folder}/{file_path}")
        return file_info

    async def read_file(
        self,
        project_id: str,
        file_path: str,
        folder: str = "src"
    ) -> Optional[str]:
        """خواندن فایل از پروژه"""
        full_path = self.projects_path / project_id / folder / file_path

        if not full_path.exists():
            return None

        try:
            async with aiofiles.open(full_path, 'r', encoding='utf-8') as f:
                return await f.read()
        except UnicodeDecodeError:
            # فایل باینری
            return None

    async def list_files(
        self,
        project_id: str,
        folder: str = None,
        recursive: bool = True
    ) -> List[ProjectFile]:
        """لیست فایل‌های پروژه"""
        if folder:
            base_path = self.projects_path / project_id / folder
        else:
            base_path = self.projects_path / project_id

        if not base_path.exists():
            return []

        files = []

        if recursive:
            for file_path in base_path.rglob("*"):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    rel_path = file_path.relative_to(self.projects_path / project_id)
                    ext = file_path.suffix.lower()

                    files.append(ProjectFile(
                        path=str(rel_path),
                        name=file_path.name,
                        size=file_path.stat().st_size,
                        language=self.LANGUAGE_MAP.get(ext),
                        last_modified=datetime.fromtimestamp(
                            file_path.stat().st_mtime
                        ).isoformat()
                    ))
        else:
            for file_path in base_path.iterdir():
                if file_path.is_file() and not file_path.name.startswith('.'):
                    rel_path = file_path.relative_to(self.projects_path / project_id)
                    ext = file_path.suffix.lower()

                    files.append(ProjectFile(
                        path=str(rel_path),
                        name=file_path.name,
                        size=file_path.stat().st_size,
                        language=self.LANGUAGE_MAP.get(ext),
                        last_modified=datetime.fromtimestamp(
                            file_path.stat().st_mtime
                        ).isoformat()
                    ))

        return sorted(files, key=lambda f: f.path)

    async def delete_file(
        self,
        project_id: str,
        file_path: str,
        folder: str = "src"
    ) -> bool:
        """حذف فایل از پروژه"""
        full_path = self.projects_path / project_id / folder / file_path

        if full_path.exists():
            full_path.unlink()
            logger.info(f"File deleted: {project_id}/{folder}/{file_path}")
            return True
        return False

    # =====================================
    # 🔍 تشخیص نوع پروژه
    # =====================================

    async def detect_project_type(self, project_id: str) -> str:
        """تشخیص خودکار نوع پروژه از فایل‌ها"""
        files = await self.list_files(project_id)
        file_names = [f.path for f in files]

        for project_type, patterns in self.PROJECT_TYPE_PATTERNS.items():
            matches = sum(1 for p in patterns if any(p in f for f in file_names))
            if matches >= 2:
                return project_type

        # تشخیص از پسوند فایل‌ها
        extensions = [Path(f.path).suffix.lower() for f in files]

        if '.py' in extensions:
            if any('requirements.txt' in f for f in file_names):
                return 'python'
            return 'python'
        elif '.js' in extensions or '.ts' in extensions:
            if any('package.json' in f for f in file_names):
                return 'nodejs'
            return 'javascript'

        return 'unknown'

    # =====================================
    # 🔄 سینک با GitHub
    # =====================================

    async def _sync_file_to_github(
        self,
        project_id: str,
        file_path: str,
        content: Union[str, bytes],
        folder: str
    ):
        """سینک فایل با GitHub"""
        if not self.github_token or not self.github_owner or not self.github_repo:
            return

        session = await self._get_session()

        github_path = f"projects/{project_id}/{folder}/{file_path}"
        url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents/{github_path}"

        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        # کدگذاری محتوا
        if isinstance(content, str):
            content = content.encode('utf-8')
        content_b64 = base64.b64encode(content).decode('utf-8')

        # بررسی وجود فایل
        sha = None
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                sha = data.get("sha")

        payload = {
            "message": f"Update {file_path}",
            "content": content_b64,
            "branch": self.github_branch
        }
        if sha:
            payload["sha"] = sha

        async with session.put(url, headers=headers, json=payload) as response:
            if response.status in [200, 201]:
                logger.info(f"Synced to GitHub: {github_path}")
            else:
                error = await response.text()
                logger.error(f"GitHub sync error: {error}")

    async def sync_project_to_github(self, project_id: str) -> Dict:
        """سینک کامل پروژه با GitHub"""
        if not self.github_token:
            return {"success": False, "error": "GitHub token not configured"}

        files = await self.list_files(project_id)
        synced = 0
        errors = []

        for file_info in files:
            content = await self.read_file(
                project_id,
                file_info.path.split('/', 1)[1] if '/' in file_info.path else file_info.path,
                folder=file_info.path.split('/')[0] if '/' in file_info.path else 'src'
            )
            if content:
                try:
                    await self._sync_file_to_github(
                        project_id,
                        file_info.name,
                        content,
                        file_info.path.split('/')[0] if '/' in file_info.path else 'src'
                    )
                    synced += 1
                except Exception as e:
                    errors.append(str(e))

        # بروزرسانی وضعیت
        config = await self.get_project_config(project_id)
        if config:
            config.github_synced = True
            await self._save_project_config(project_id, config)

        return {
            "success": True,
            "synced_files": synced,
            "errors": errors
        }

    # =====================================
    # 🚀 Deploy به Render
    # =====================================

    async def prepare_for_render(self, project_id: str) -> Dict:
        """آماده‌سازی پروژه برای Deploy به Render"""
        config = await self.get_project_config(project_id)
        if not config:
            return {"success": False, "error": "Project not found"}

        project_path = self.projects_path / project_id

        # تشخیص نوع پروژه
        project_type = await self.detect_project_type(project_id)

        # ایجاد render.yaml
        render_config = self._generate_render_yaml(config, project_type)

        render_yaml_path = project_path / "render.yaml"
        async with aiofiles.open(render_yaml_path, 'w', encoding='utf-8') as f:
            await f.write(render_config)

        # ایجاد Dockerfile اگر نیاز باشه
        if project_type in ['python', 'fastapi', 'flask']:
            dockerfile = self._generate_dockerfile(config, project_type)
            dockerfile_path = project_path / "Dockerfile"
            async with aiofiles.open(dockerfile_path, 'w', encoding='utf-8') as f:
                await f.write(dockerfile)

        # ایجاد .env.example
        env_example = self._generate_env_example(config)
        env_path = project_path / ".env.example"
        async with aiofiles.open(env_path, 'w', encoding='utf-8') as f:
            await f.write(env_example)

        return {
            "success": True,
            "files_created": ["render.yaml", "Dockerfile", ".env.example"],
            "project_type": project_type,
            "ready_for_deploy": True
        }

    def _generate_render_yaml(self, config: ProjectConfig, project_type: str) -> str:
        """تولید فایل render.yaml"""
        if project_type in ['python', 'fastapi', 'flask']:
            return f"""services:
  - type: web
    name: {config.name.lower().replace(' ', '-')}
    env: python
    buildCommand: {config.build_command or 'pip install -r requirements.txt'}
    startCommand: {config.start_command or 'python main.py'}
    envVars:
      - key: PYTHON_VERSION
        value: "3.11"
      - key: PORT
        value: "{config.port}"
"""
        elif project_type in ['nodejs', 'express', 'react', 'nextjs']:
            return f"""services:
  - type: web
    name: {config.name.lower().replace(' ', '-')}
    env: node
    buildCommand: {config.build_command or 'npm install'}
    startCommand: {config.start_command or 'npm start'}
    envVars:
      - key: NODE_VERSION
        value: "18"
      - key: PORT
        value: "{config.port}"
"""
        else:
            return f"""services:
  - type: web
    name: {config.name.lower().replace(' ', '-')}
    env: docker
    dockerfilePath: ./Dockerfile
    envVars:
      - key: PORT
        value: "{config.port}"
"""

    def _generate_dockerfile(self, config: ProjectConfig, project_type: str) -> str:
        """تولید Dockerfile"""
        if project_type in ['python', 'fastapi']:
            return f"""FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE {config.port}

CMD {json.dumps(config.start_command.split() if config.start_command else ['python', 'main.py'])}
"""
        elif project_type == 'flask':
            return f"""FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

EXPOSE {config.port}

CMD ["gunicorn", "-b", "0.0.0.0:{config.port}", "app:app"]
"""
        else:
            return f"""FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt 2>/dev/null || true

EXPOSE {config.port}

CMD ["python", "main.py"]
"""

    def _generate_env_example(self, config: ProjectConfig) -> str:
        """تولید .env.example"""
        lines = [
            f"# Environment variables for {config.name}",
            f"PORT={config.port}",
            ""
        ]

        for key, value in config.env_vars.items():
            lines.append(f"{key}={value}")

        return "\n".join(lines)

    async def deploy_to_render(self, project_id: str) -> Dict:
        """
        Deploy مستقیم به Render
        نیاز به API key رندر دارد
        """
        if not self.render_api_key:
            return {"success": False, "error": "Render API key not configured"}

        config = await self.get_project_config(project_id)
        if not config:
            return {"success": False, "error": "Project not found"}

        # اول باید پروژه روی GitHub باشه
        if not config.github_synced:
            sync_result = await self.sync_project_to_github(project_id)
            if not sync_result.get("success"):
                return {"success": False, "error": "Failed to sync to GitHub first"}

        # آماده‌سازی فایل‌های Render
        await self.prepare_for_render(project_id)

        # ایجاد سرویس در Render
        session = await self._get_session()

        headers = {
            "Authorization": f"Bearer {self.render_api_key}",
            "Content-Type": "application/json"
        }

        # تشخیص نوع پروژه برای انتخاب environment
        project_type = await self.detect_project_type(project_id)

        service_data = {
            "type": "web_service",
            "name": config.name.lower().replace(' ', '-'),
            "repo": f"https://github.com/{self.github_owner}/{self.github_repo}",
            "branch": self.github_branch,
            "rootDir": f"projects/{project_id}",
            "envVars": [{"key": k, "value": v} for k, v in config.env_vars.items()],
            "serviceDetails": {
                "env": "python" if project_type in ['python', 'fastapi', 'flask'] else "node",
                "buildCommand": config.build_command,
                "startCommand": config.start_command
            }
        }

        try:
            async with session.post(
                "https://api.render.com/v1/services",
                headers=headers,
                json=service_data
            ) as response:
                if response.status in [200, 201]:
                    data = await response.json()

                    # بروزرسانی تنظیمات پروژه
                    config.render_deployed = True
                    config.render_service_id = data.get("service", {}).get("id")
                    config.render_url = data.get("service", {}).get("url")
                    await self._save_project_config(project_id, config)

                    return {
                        "success": True,
                        "service_id": config.render_service_id,
                        "url": config.render_url,
                        "message": "Deployment started!"
                    }
                else:
                    error = await response.text()
                    return {"success": False, "error": error}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_render_deploy_status(self, project_id: str) -> Dict:
        """وضعیت Deploy در Render"""
        if not self.render_api_key:
            return {"success": False, "error": "Render API key not configured"}

        config = await self.get_project_config(project_id)
        if not config or not config.render_service_id:
            return {"success": False, "error": "Project not deployed"}

        session = await self._get_session()

        headers = {
            "Authorization": f"Bearer {self.render_api_key}"
        }

        try:
            # دریافت اطلاعات سرویس
            async with session.get(
                f"https://api.render.com/v1/services/{config.render_service_id}",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "success": True,
                        "status": data.get("service", {}).get("suspended", "unknown"),
                        "url": config.render_url,
                        "service_id": config.render_service_id
                    }
                else:
                    return {"success": False, "error": "Failed to get status"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    # =====================================
    # 📊 نمودارها
    # =====================================

    async def save_diagram(
        self,
        project_id: str,
        diagram_type: str,
        content: str,
        name: str = None
    ) -> str:
        """ذخیره نمودار پروژه"""
        name = name or f"{diagram_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        file_path = f"{name}.mmd"

        await self.save_file(project_id, file_path, content, folder="diagrams")
        return file_path

    async def list_diagrams(self, project_id: str) -> List[ProjectFile]:
        """لیست نمودارهای پروژه"""
        return await self.list_files(project_id, folder="diagrams")

    async def get_diagram(self, project_id: str, name: str) -> Optional[str]:
        """دریافت محتوای نمودار"""
        return await self.read_file(project_id, name, folder="diagrams")

    # =====================================
    # 📦 Export/Import
    # =====================================

    async def export_project(self, project_id: str) -> Optional[bytes]:
        """Export پروژه به ZIP"""
        import io
        import zipfile

        project_path = self.projects_path / project_id
        if not project_path.exists():
            return None

        buffer = io.BytesIO()

        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in project_path.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(project_path)
                    zf.write(file_path, arcname)

        buffer.seek(0)
        return buffer.getvalue()

    async def import_project(
        self,
        zip_content: bytes,
        name: str
    ) -> Optional[ProjectConfig]:
        """Import پروژه از ZIP"""
        import io
        import zipfile

        # ایجاد پروژه جدید
        config = await self.create_project(name)
        project_path = self.projects_path / config.id

        buffer = io.BytesIO(zip_content)

        with zipfile.ZipFile(buffer, 'r') as zf:
            zf.extractall(project_path)

        # تشخیص نوع پروژه
        project_type = await self.detect_project_type(config.id)
        config.project_type = project_type

        # بروزرسانی تنظیمات
        default_config = self._get_default_config(project_type)
        config.entry_point = default_config.get("entry_point")
        config.build_command = default_config.get("build_command")
        config.start_command = default_config.get("start_command")
        config.port = default_config.get("port", 8000)

        await self._save_project_config(config.id, config)

        return config


# سینگلتون برای استفاده در سراسر برنامه
_storage_instance: Optional[UnifiedStorageService] = None


def get_unified_storage() -> UnifiedStorageService:
    """دریافت instance ذخیره‌سازی"""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = UnifiedStorageService()
    return _storage_instance


def configure_unified_storage(
    workspace_path: str = "./workspace",
    github_token: str = None,
    github_owner: str = None,
    github_repo: str = None,
    render_api_key: str = None,
    auto_sync: bool = False
):
    """پیکربندی ذخیره‌سازی"""
    global _storage_instance
    _storage_instance = UnifiedStorageService(
        workspace_path=workspace_path,
        github_token=github_token,
        github_owner=github_owner,
        github_repo=github_repo,
        render_api_key=render_api_key,
        auto_sync=auto_sync
    )
    return _storage_instance
