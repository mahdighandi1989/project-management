"""
Runtime Executor Service
اجرای پروژه‌های تولید شده در محیط Docker ایزوله

Features:
- Docker container management
- Resource limits (CPU, RAM)
- Port management
- Log streaming
- Project-specific environments
"""

import asyncio
import logging
import os
import json
import uuid
import shutil
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class RuntimeType(Enum):
    """انواع runtime های پشتیبانی شده"""
    NODEJS = "nodejs"
    PYTHON = "python"
    NEXTJS = "nextjs"
    FASTAPI = "fastapi"
    REACT = "react"
    VUE = "vue"
    STATIC = "static"
    DOCKER = "docker"


class ContainerStatus(Enum):
    """وضعیت container"""
    PENDING = "pending"
    BUILDING = "building"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class RuntimeConfig:
    """پیکربندی runtime"""
    type: RuntimeType
    port: int
    memory_limit: str = "512m"
    cpu_limit: float = 0.5
    timeout: int = 3600  # 1 hour
    env_vars: Dict[str, str] = field(default_factory=dict)
    build_command: str = ""
    start_command: str = ""
    working_dir: str = "/app"


@dataclass
class RunningProject:
    """اطلاعات پروژه در حال اجرا"""
    project_id: str
    container_id: Optional[str]
    status: ContainerStatus
    port: int
    url: str
    runtime_type: RuntimeType
    started_at: Optional[datetime]
    logs: List[str] = field(default_factory=list)
    error: Optional[str] = None


# تنظیمات پیش‌فرض برای هر نوع runtime
RUNTIME_CONFIGS: Dict[RuntimeType, Dict[str, Any]] = {
    RuntimeType.NODEJS: {
        "image": "node:20-alpine",
        "build_cmd": "npm install",
        "start_cmd": "npm start",
        "port": 3000,
        "memory": "512m",
        "cpu": 0.5
    },
    RuntimeType.NEXTJS: {
        "image": "node:20-alpine",
        "build_cmd": "npm install && npm run build",
        "start_cmd": "npm run start",
        "port": 3000,
        "memory": "1g",
        "cpu": 1.0
    },
    RuntimeType.REACT: {
        "image": "node:20-alpine",
        "build_cmd": "npm install",
        "start_cmd": "npm run dev",
        "port": 5173,
        "memory": "512m",
        "cpu": 0.5
    },
    RuntimeType.VUE: {
        "image": "node:20-alpine",
        "build_cmd": "npm install",
        "start_cmd": "npm run dev",
        "port": 5173,
        "memory": "512m",
        "cpu": 0.5
    },
    RuntimeType.PYTHON: {
        "image": "python:3.11-slim",
        "build_cmd": "pip install -r requirements.txt",
        "start_cmd": "python main.py",
        "port": 8080,
        "memory": "512m",
        "cpu": 0.5
    },
    RuntimeType.FASTAPI: {
        "image": "python:3.11-slim",
        "build_cmd": "pip install -r requirements.txt",
        "start_cmd": "uvicorn main:app --host 0.0.0.0 --port 8000",
        "port": 8000,
        "memory": "512m",
        "cpu": 0.5
    },
    RuntimeType.STATIC: {
        "image": "nginx:alpine",
        "build_cmd": "",
        "start_cmd": "",
        "port": 80,
        "memory": "128m",
        "cpu": 0.2
    },
    RuntimeType.DOCKER: {
        "image": None,  # Uses project's Dockerfile
        "build_cmd": "",
        "start_cmd": "",
        "port": 8080,
        "memory": "1g",
        "cpu": 1.0
    }
}


class RuntimeExecutor:
    """سرویس اجرای پروژه‌ها"""

    def __init__(self):
        self._initialized = False
        self._docker_available = False
        self._running_projects: Dict[str, RunningProject] = {}
        self._port_pool: List[int] = list(range(10000, 10100))  # پورت‌های قابل استفاده
        self._used_ports: Dict[str, int] = {}  # project_id -> port
        self._workspace_dir = "/tmp/runtime_workspace"
        self._github_storage = None

    def initialize(self, github_storage=None):
        """مقداردهی اولیه"""
        self._github_storage = github_storage
        self._check_docker_availability()
        self._ensure_workspace()
        self._initialized = True
        logger.info(f"RuntimeExecutor initialized. Docker available: {self._docker_available}")

    def _check_docker_availability(self):
        """بررسی در دسترس بودن Docker"""
        try:
            import subprocess
            result = subprocess.run(
                ["docker", "version", "--format", "{{.Server.Version}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            self._docker_available = result.returncode == 0
            if self._docker_available:
                logger.info(f"Docker version: {result.stdout.strip()}")
        except Exception as e:
            logger.warning(f"Docker not available: {e}")
            self._docker_available = False

    def _ensure_workspace(self):
        """ایجاد پوشه workspace"""
        os.makedirs(self._workspace_dir, exist_ok=True)

    def is_docker_available(self) -> bool:
        """آیا Docker در دسترس است؟"""
        return self._docker_available

    def _get_available_port(self) -> int:
        """دریافت پورت خالی"""
        for port in self._port_pool:
            if port not in self._used_ports.values():
                return port
        raise RuntimeError("No available ports")

    def _release_port(self, project_id: str):
        """آزادسازی پورت"""
        if project_id in self._used_ports:
            del self._used_ports[project_id]

    async def detect_runtime_type(self, project_id: str, files: List[Dict]) -> RuntimeType:
        """
        تشخیص نوع runtime بر اساس فایل‌های پروژه
        """
        file_names = [f.get("name", "").lower() for f in files]

        # بررسی Dockerfile
        if "dockerfile" in file_names:
            return RuntimeType.DOCKER

        # بررسی package.json برای Node.js projects
        if "package.json" in file_names:
            # خواندن محتوای package.json برای تشخیص دقیق‌تر
            for f in files:
                if f.get("name", "").lower() == "package.json":
                    content = f.get("content", "")
                    if isinstance(content, str):
                        if "next" in content.lower():
                            return RuntimeType.NEXTJS
                        elif "react" in content.lower():
                            return RuntimeType.REACT
                        elif "vue" in content.lower():
                            return RuntimeType.VUE
            return RuntimeType.NODEJS

        # بررسی requirements.txt برای Python
        if "requirements.txt" in file_names:
            for f in files:
                if f.get("name", "").lower() == "requirements.txt":
                    content = f.get("content", "")
                    if isinstance(content, str):
                        if "fastapi" in content.lower() or "uvicorn" in content.lower():
                            return RuntimeType.FASTAPI
            return RuntimeType.PYTHON

        # بررسی main.py
        if "main.py" in file_names:
            return RuntimeType.PYTHON

        # بررسی index.html برای static
        if "index.html" in file_names:
            return RuntimeType.STATIC

        return RuntimeType.STATIC  # پیش‌فرض

    async def prepare_project_files(self, project_id: str, files: List[Dict]) -> str:
        """
        آماده‌سازی فایل‌های پروژه در workspace
        """
        project_dir = os.path.join(self._workspace_dir, project_id)

        # پاک کردن پوشه قبلی
        if os.path.exists(project_dir):
            shutil.rmtree(project_dir)
        os.makedirs(project_dir)

        # کپی فایل‌ها
        for file_info in files:
            file_name = file_info.get("name", "")
            content = file_info.get("content", "")
            folder = file_info.get("folder", "")

            if not file_name or file_name == ".gitkeep":
                continue

            # ایجاد پوشه در صورت نیاز
            if folder:
                folder_path = os.path.join(project_dir, folder)
                os.makedirs(folder_path, exist_ok=True)
                file_path = os.path.join(folder_path, file_name)
            else:
                file_path = os.path.join(project_dir, file_name)

            # نوشتن فایل
            try:
                if isinstance(content, bytes):
                    with open(file_path, 'wb') as f:
                        f.write(content)
                else:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
            except Exception as e:
                logger.error(f"Error writing file {file_name}: {e}")

        return project_dir

    async def start_project(
        self,
        project_id: str,
        files: List[Dict],
        runtime_type: Optional[RuntimeType] = None,
        custom_port: Optional[int] = None
    ) -> RunningProject:
        """
        اجرای پروژه در Docker container
        """
        if not self._docker_available:
            raise RuntimeError("Docker is not available. Please install Docker to run projects.")

        # بررسی پروژه در حال اجرا
        if project_id in self._running_projects:
            existing = self._running_projects[project_id]
            if existing.status == ContainerStatus.RUNNING:
                return existing

        # تشخیص نوع runtime
        if not runtime_type:
            runtime_type = await self.detect_runtime_type(project_id, files)

        # دریافت پورت
        port = custom_port or self._get_available_port()
        self._used_ports[project_id] = port

        # ایجاد رکورد پروژه
        running_project = RunningProject(
            project_id=project_id,
            container_id=None,
            status=ContainerStatus.BUILDING,
            port=port,
            url=f"http://localhost:{port}",
            runtime_type=runtime_type,
            started_at=None
        )
        self._running_projects[project_id] = running_project

        try:
            # آماده‌سازی فایل‌ها
            project_dir = await self.prepare_project_files(project_id, files)
            running_project.logs.append(f"Files prepared in {project_dir}")

            # دریافت تنظیمات runtime
            config = RUNTIME_CONFIGS.get(runtime_type, RUNTIME_CONFIGS[RuntimeType.STATIC])

            # ایجاد Dockerfile اگر وجود ندارد
            dockerfile_path = os.path.join(project_dir, "Dockerfile")
            if not os.path.exists(dockerfile_path) and runtime_type != RuntimeType.DOCKER:
                await self._generate_dockerfile(project_dir, runtime_type, config)
                running_project.logs.append("Generated Dockerfile")

            # Build container
            container_name = f"project_{project_id}_{uuid.uuid4().hex[:8]}"
            image_name = f"project_{project_id}:latest"

            # Build
            running_project.status = ContainerStatus.BUILDING
            build_result = await self._run_docker_command([
                "docker", "build", "-t", image_name, project_dir
            ])
            running_project.logs.extend(build_result.get("logs", []))

            if not build_result.get("success"):
                running_project.status = ContainerStatus.ERROR
                running_project.error = build_result.get("error", "Build failed")
                return running_project

            # Run container
            running_project.status = ContainerStatus.STARTING
            internal_port = config.get("port", 3000)

            run_cmd = [
                "docker", "run", "-d",
                "--name", container_name,
                "-p", f"{port}:{internal_port}",
                "--memory", config.get("memory", "512m"),
                "--cpus", str(config.get("cpu", 0.5)),
                "--restart", "unless-stopped",
                image_name
            ]

            run_result = await self._run_docker_command(run_cmd)
            running_project.logs.extend(run_result.get("logs", []))

            if run_result.get("success"):
                running_project.container_id = run_result.get("output", "").strip()
                running_project.status = ContainerStatus.RUNNING
                running_project.started_at = datetime.now()
                running_project.logs.append(f"Container started: {container_name}")
                running_project.logs.append(f"Access at: http://localhost:{port}")
            else:
                running_project.status = ContainerStatus.ERROR
                running_project.error = run_result.get("error", "Failed to start container")

        except Exception as e:
            logger.error(f"Error starting project {project_id}: {e}")
            running_project.status = ContainerStatus.ERROR
            running_project.error = str(e)

        return running_project

    async def _generate_dockerfile(self, project_dir: str, runtime_type: RuntimeType, config: Dict):
        """تولید Dockerfile بر اساس نوع runtime"""
        dockerfile_content = ""

        if runtime_type in [RuntimeType.NODEJS, RuntimeType.REACT, RuntimeType.VUE]:
            dockerfile_content = f"""FROM {config['image']}
WORKDIR /app
COPY package*.json ./
RUN {config['build_cmd']}
COPY . .
EXPOSE {config['port']}
CMD {json.dumps(config['start_cmd'].split())}
"""
        elif runtime_type == RuntimeType.NEXTJS:
            dockerfile_content = f"""FROM {config['image']}
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE {config['port']}
CMD ["npm", "run", "start"]
"""
        elif runtime_type in [RuntimeType.PYTHON, RuntimeType.FASTAPI]:
            start_cmd_parts = config['start_cmd'].split()
            dockerfile_content = f"""FROM {config['image']}
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE {config['port']}
CMD {json.dumps(start_cmd_parts)}
"""
        elif runtime_type == RuntimeType.STATIC:
            dockerfile_content = """FROM nginx:alpine
COPY . /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
"""

        dockerfile_path = os.path.join(project_dir, "Dockerfile")
        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile_content)

    async def _run_docker_command(self, cmd: List[str]) -> Dict:
        """اجرای دستور Docker"""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=600  # 10 minutes
            )

            return {
                "success": process.returncode == 0,
                "output": stdout.decode() if stdout else "",
                "error": stderr.decode() if stderr else "",
                "logs": [
                    l for l in (stdout.decode() if stdout else "").split("\n") if l.strip()
                ]
            }
        except asyncio.TimeoutError:
            return {"success": False, "error": "Command timed out", "logs": []}
        except Exception as e:
            return {"success": False, "error": str(e), "logs": []}

    async def stop_project(self, project_id: str) -> bool:
        """توقف پروژه"""
        if project_id not in self._running_projects:
            return False

        running = self._running_projects[project_id]

        if running.container_id:
            running.status = ContainerStatus.STOPPING

            # Stop container
            await self._run_docker_command([
                "docker", "stop", running.container_id
            ])

            # Remove container
            await self._run_docker_command([
                "docker", "rm", running.container_id
            ])

        running.status = ContainerStatus.STOPPED
        self._release_port(project_id)

        # پاک کردن workspace
        project_dir = os.path.join(self._workspace_dir, project_id)
        if os.path.exists(project_dir):
            shutil.rmtree(project_dir)

        return True

    async def get_project_logs(self, project_id: str, lines: int = 100) -> List[str]:
        """دریافت لاگ‌های پروژه"""
        if project_id not in self._running_projects:
            return []

        running = self._running_projects[project_id]

        if not running.container_id:
            return running.logs

        result = await self._run_docker_command([
            "docker", "logs", "--tail", str(lines), running.container_id
        ])

        return result.get("logs", []) + running.logs

    def get_running_project(self, project_id: str) -> Optional[RunningProject]:
        """دریافت اطلاعات پروژه در حال اجرا"""
        return self._running_projects.get(project_id)

    def get_all_running_projects(self) -> Dict[str, RunningProject]:
        """لیست همه پروژه‌های در حال اجرا"""
        return self._running_projects.copy()

    async def cleanup_all(self):
        """توقف همه پروژه‌ها"""
        for project_id in list(self._running_projects.keys()):
            await self.stop_project(project_id)


# Singleton instance
_runtime_executor: Optional[RuntimeExecutor] = None


def get_runtime_executor() -> RuntimeExecutor:
    """دریافت instance سرویس"""
    global _runtime_executor
    if _runtime_executor is None:
        _runtime_executor = RuntimeExecutor()
    return _runtime_executor
