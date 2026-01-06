"""
Capability Detector & Self-Upgrade Service
تشخیص قابلیت‌های سیستم و ارتقای خودکار

Features:
- تشخیص اینکه سیستم قادر به اجرای یک پروژه هست یا نه
- شناسایی نیازمندی‌های missing
- ذخیره نیازمندی‌ها در GitHub برای ارتقای خودکار
- بررسی و نصب خودکار در deployment بعدی
"""

import asyncio
import logging
import os
import json
import platform
import shutil
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class CapabilityType(Enum):
    """انواع قابلیت‌ها"""
    RUNTIME = "runtime"           # Node.js, Python, Go, etc.
    DATABASE = "database"         # PostgreSQL, MongoDB, Redis, etc.
    SERVICE = "service"           # Docker, Kubernetes, etc.
    TOOL = "tool"                 # Git, npm, pip, etc.
    LIBRARY = "library"           # System libraries
    HARDWARE = "hardware"         # GPU, memory, etc.


class CapabilityStatus(Enum):
    """وضعیت قابلیت"""
    AVAILABLE = "available"
    MISSING = "missing"
    OUTDATED = "outdated"
    UNSUPPORTED = "unsupported"


@dataclass
class Capability:
    """تعریف یک قابلیت"""
    name: str
    type: CapabilityType
    version: Optional[str] = None
    status: CapabilityStatus = CapabilityStatus.MISSING
    check_command: Optional[str] = None
    install_command: Optional[str] = None
    docker_image: Optional[str] = None
    description: str = ""


@dataclass
class ProjectRequirements:
    """نیازمندی‌های یک پروژه"""
    project_id: str
    project_type: str
    required_capabilities: List[Capability] = field(default_factory=list)
    optional_capabilities: List[Capability] = field(default_factory=list)
    missing_capabilities: List[Capability] = field(default_factory=list)
    can_run: bool = False
    can_run_with_docker: bool = False
    upgrade_needed: bool = False
    notes: List[str] = field(default_factory=list)


@dataclass
class SystemCapabilities:
    """قابلیت‌های فعلی سیستم"""
    os_type: str
    os_version: str
    architecture: str
    docker_available: bool
    docker_version: Optional[str]
    available_runtimes: Dict[str, str] = field(default_factory=dict)
    available_databases: Dict[str, str] = field(default_factory=dict)
    available_tools: Dict[str, str] = field(default_factory=dict)
    memory_mb: int = 0
    cpu_cores: int = 0


# تعریف قابلیت‌های شناخته شده
KNOWN_CAPABILITIES: Dict[str, Capability] = {
    # Runtimes
    "nodejs": Capability(
        name="Node.js",
        type=CapabilityType.RUNTIME,
        check_command="node --version",
        install_command="curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt-get install -y nodejs",
        docker_image="node:20-alpine",
        description="JavaScript runtime"
    ),
    "python": Capability(
        name="Python",
        type=CapabilityType.RUNTIME,
        check_command="python3 --version",
        install_command="apt-get install -y python3 python3-pip",
        docker_image="python:3.11-slim",
        description="Python runtime"
    ),
    "go": Capability(
        name="Go",
        type=CapabilityType.RUNTIME,
        check_command="go version",
        install_command="apt-get install -y golang",
        docker_image="golang:1.21-alpine",
        description="Go runtime"
    ),
    "rust": Capability(
        name="Rust",
        type=CapabilityType.RUNTIME,
        check_command="rustc --version",
        install_command="curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh",
        docker_image="rust:1.73-alpine",
        description="Rust runtime"
    ),
    "java": Capability(
        name="Java",
        type=CapabilityType.RUNTIME,
        check_command="java --version",
        install_command="apt-get install -y openjdk-17-jdk",
        docker_image="openjdk:17-slim",
        description="Java runtime"
    ),

    # Databases
    "postgresql": Capability(
        name="PostgreSQL",
        type=CapabilityType.DATABASE,
        check_command="psql --version",
        docker_image="postgres:15-alpine",
        description="PostgreSQL database"
    ),
    "mongodb": Capability(
        name="MongoDB",
        type=CapabilityType.DATABASE,
        check_command="mongod --version",
        docker_image="mongo:6",
        description="MongoDB database"
    ),
    "redis": Capability(
        name="Redis",
        type=CapabilityType.DATABASE,
        check_command="redis-cli --version",
        docker_image="redis:7-alpine",
        description="Redis cache/database"
    ),
    "mysql": Capability(
        name="MySQL",
        type=CapabilityType.DATABASE,
        check_command="mysql --version",
        docker_image="mysql:8",
        description="MySQL database"
    ),

    # Services
    "docker": Capability(
        name="Docker",
        type=CapabilityType.SERVICE,
        check_command="docker --version",
        description="Container runtime"
    ),
    "nginx": Capability(
        name="Nginx",
        type=CapabilityType.SERVICE,
        check_command="nginx -v",
        docker_image="nginx:alpine",
        description="Web server"
    ),

    # Tools
    "git": Capability(
        name="Git",
        type=CapabilityType.TOOL,
        check_command="git --version",
        install_command="apt-get install -y git",
        description="Version control"
    ),
    "npm": Capability(
        name="npm",
        type=CapabilityType.TOOL,
        check_command="npm --version",
        description="Node package manager"
    ),
    "pip": Capability(
        name="pip",
        type=CapabilityType.TOOL,
        check_command="pip3 --version",
        description="Python package manager"
    ),
}


# نیازمندی‌های پیش‌فرض بر اساس نوع پروژه
PROJECT_TYPE_REQUIREMENTS: Dict[str, List[str]] = {
    "web_app": ["nodejs", "npm"],
    "nextjs": ["nodejs", "npm"],
    "react": ["nodejs", "npm"],
    "vue": ["nodejs", "npm"],
    "api_service": ["python", "pip"],
    "fastapi": ["python", "pip"],
    "django": ["python", "pip"],
    "express": ["nodejs", "npm"],
    "mobile_app": ["nodejs", "npm"],
    "ml_project": ["python", "pip"],
    "data_pipeline": ["python", "pip"],
    "static": [],  # No special requirements
    "docker": ["docker"],
}


class CapabilityDetector:
    """سرویس تشخیص قابلیت‌ها"""

    def __init__(self):
        self._initialized = False
        self._system_capabilities: Optional[SystemCapabilities] = None
        self._github_storage = None
        self._upgrade_requirements_path = "system/upgrade-requirements"

    def initialize(self, github_storage=None):
        """مقداردهی اولیه"""
        self._github_storage = github_storage
        self._scan_system_capabilities()
        self._initialized = True
        logger.info("CapabilityDetector initialized")

    def _scan_system_capabilities(self):
        """اسکن قابلیت‌های سیستم"""
        import subprocess
        import psutil

        self._system_capabilities = SystemCapabilities(
            os_type=platform.system(),
            os_version=platform.release(),
            architecture=platform.machine(),
            docker_available=False,
            docker_version=None,
            memory_mb=psutil.virtual_memory().total // (1024 * 1024) if hasattr(psutil, 'virtual_memory') else 0,
            cpu_cores=os.cpu_count() or 1
        )

        # بررسی Docker
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self._system_capabilities.docker_available = True
                self._system_capabilities.docker_version = result.stdout.strip()
        except Exception:
            pass

        # بررسی runtime های موجود
        for cap_id, cap in KNOWN_CAPABILITIES.items():
            if cap.type == CapabilityType.RUNTIME and cap.check_command:
                version = self._check_capability_version(cap.check_command)
                if version:
                    self._system_capabilities.available_runtimes[cap_id] = version

            elif cap.type == CapabilityType.DATABASE and cap.check_command:
                version = self._check_capability_version(cap.check_command)
                if version:
                    self._system_capabilities.available_databases[cap_id] = version

            elif cap.type == CapabilityType.TOOL and cap.check_command:
                version = self._check_capability_version(cap.check_command)
                if version:
                    self._system_capabilities.available_tools[cap_id] = version

    def _check_capability_version(self, command: str) -> Optional[str]:
        """بررسی نسخه یک قابلیت"""
        import subprocess
        try:
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip() or result.stderr.strip()
        except Exception:
            pass
        return None

    def get_system_capabilities(self) -> SystemCapabilities:
        """دریافت قابلیت‌های سیستم"""
        if not self._system_capabilities:
            self._scan_system_capabilities()
        return self._system_capabilities

    async def analyze_project_requirements(
        self,
        project_id: str,
        project_type: str,
        files: List[Dict]
    ) -> ProjectRequirements:
        """
        تحلیل نیازمندی‌های یک پروژه و بررسی قابلیت اجرا
        """
        requirements = ProjectRequirements(
            project_id=project_id,
            project_type=project_type
        )

        # استخراج نیازمندی‌ها از فایل‌ها
        detected_requirements = await self._detect_requirements_from_files(files)

        # اضافه کردن نیازمندی‌های پیش‌فرض نوع پروژه
        default_reqs = PROJECT_TYPE_REQUIREMENTS.get(project_type, [])
        all_required = set(detected_requirements + default_reqs)

        # بررسی هر نیازمندی
        for req_id in all_required:
            if req_id in KNOWN_CAPABILITIES:
                cap = KNOWN_CAPABILITIES[req_id]
                cap_copy = Capability(
                    name=cap.name,
                    type=cap.type,
                    version=cap.version,
                    check_command=cap.check_command,
                    install_command=cap.install_command,
                    docker_image=cap.docker_image,
                    description=cap.description
                )

                # بررسی موجود بودن
                is_available = self._is_capability_available(req_id)
                cap_copy.status = CapabilityStatus.AVAILABLE if is_available else CapabilityStatus.MISSING

                requirements.required_capabilities.append(cap_copy)

                if not is_available:
                    requirements.missing_capabilities.append(cap_copy)

        # تصمیم‌گیری درباره قابلیت اجرا
        if not requirements.missing_capabilities:
            requirements.can_run = True
            requirements.notes.append("همه نیازمندی‌ها موجود است")
        elif self._system_capabilities and self._system_capabilities.docker_available:
            # بررسی اینکه آیا با Docker قابل اجراست
            all_have_docker_image = all(
                cap.docker_image for cap in requirements.missing_capabilities
            )
            if all_have_docker_image:
                requirements.can_run_with_docker = True
                requirements.notes.append("با Docker قابل اجرا است")
            else:
                requirements.upgrade_needed = True
                requirements.notes.append("نیاز به ارتقای سیستم دارد")
        else:
            requirements.upgrade_needed = True
            requirements.notes.append("Docker در دسترس نیست - نیاز به ارتقا")

        return requirements

    async def _detect_requirements_from_files(self, files: List[Dict]) -> List[str]:
        """تشخیص نیازمندی‌ها از روی فایل‌های پروژه"""
        requirements = []

        file_names = {f.get("name", "").lower(): f for f in files}

        # package.json -> Node.js
        if "package.json" in file_names:
            requirements.append("nodejs")
            requirements.append("npm")
            content = file_names["package.json"].get("content", "")
            if isinstance(content, str):
                # بررسی dependencies خاص
                if "prisma" in content.lower():
                    requirements.append("postgresql")
                if "mongoose" in content.lower():
                    requirements.append("mongodb")
                if "redis" in content.lower() or "ioredis" in content.lower():
                    requirements.append("redis")

        # requirements.txt -> Python
        if "requirements.txt" in file_names:
            requirements.append("python")
            requirements.append("pip")
            content = file_names["requirements.txt"].get("content", "")
            if isinstance(content, str):
                if "psycopg" in content.lower() or "sqlalchemy" in content.lower():
                    requirements.append("postgresql")
                if "pymongo" in content.lower():
                    requirements.append("mongodb")
                if "redis" in content.lower():
                    requirements.append("redis")

        # go.mod -> Go
        if "go.mod" in file_names:
            requirements.append("go")

        # Cargo.toml -> Rust
        if "cargo.toml" in file_names:
            requirements.append("rust")

        # pom.xml or build.gradle -> Java
        if "pom.xml" in file_names or "build.gradle" in file_names:
            requirements.append("java")

        # docker-compose.yml -> analyze services
        if "docker-compose.yml" in file_names or "docker-compose.yaml" in file_names:
            requirements.append("docker")
            content = file_names.get("docker-compose.yml", file_names.get("docker-compose.yaml", {})).get("content", "")
            if isinstance(content, str):
                if "postgres" in content.lower():
                    requirements.append("postgresql")
                if "mongo" in content.lower():
                    requirements.append("mongodb")
                if "redis" in content.lower():
                    requirements.append("redis")
                if "mysql" in content.lower():
                    requirements.append("mysql")

        return list(set(requirements))

    def _is_capability_available(self, capability_id: str) -> bool:
        """بررسی موجود بودن یک قابلیت"""
        if not self._system_capabilities:
            return False

        cap = KNOWN_CAPABILITIES.get(capability_id)
        if not cap:
            return False

        if cap.type == CapabilityType.RUNTIME:
            return capability_id in self._system_capabilities.available_runtimes
        elif cap.type == CapabilityType.DATABASE:
            return capability_id in self._system_capabilities.available_databases
        elif cap.type == CapabilityType.TOOL:
            return capability_id in self._system_capabilities.available_tools
        elif cap.type == CapabilityType.SERVICE:
            if capability_id == "docker":
                return self._system_capabilities.docker_available
        return False

    async def save_upgrade_requirements(
        self,
        project_id: str,
        requirements: ProjectRequirements
    ) -> bool:
        """
        ذخیره نیازمندی‌های ارتقا در GitHub
        برای نصب خودکار در deployment بعدی
        """
        if not self._github_storage or not requirements.missing_capabilities:
            return False

        try:
            # ساخت محتوای فایل نیازمندی‌ها
            upgrade_data = {
                "project_id": project_id,
                "project_type": requirements.project_type,
                "requested_at": datetime.now().isoformat(),
                "missing_capabilities": [
                    {
                        "id": cap.name.lower().replace(" ", "_"),
                        "name": cap.name,
                        "type": cap.type.value,
                        "install_command": cap.install_command,
                        "docker_image": cap.docker_image,
                        "description": cap.description
                    }
                    for cap in requirements.missing_capabilities
                ],
                "notes": requirements.notes
            }

            # ذخیره در GitHub
            file_path = f"{self._upgrade_requirements_path}/{project_id}.json"
            content = json.dumps(upgrade_data, indent=2, ensure_ascii=False)

            await self._github_storage.upload_file(
                content.encode('utf-8'),
                file_path,
                f"Add upgrade requirements for project {project_id}"
            )

            logger.info(f"Saved upgrade requirements for {project_id}")
            return True

        except Exception as e:
            logger.error(f"Error saving upgrade requirements: {e}")
            return False

    async def check_and_apply_upgrades(self) -> Dict[str, Any]:
        """
        بررسی و اعمال ارتقاها در startup
        این متد در زمان deploy اجرا می‌شود
        """
        results = {
            "checked": 0,
            "applied": 0,
            "failed": 0,
            "details": []
        }

        if not self._github_storage:
            return results

        try:
            # خواندن فایل‌های نیازمندی
            files = await self._github_storage.list_folder(self._upgrade_requirements_path)

            for file_info in files:
                if not file_info.name.endswith('.json'):
                    continue

                results["checked"] += 1

                try:
                    # خواندن فایل
                    file_content = await self._github_storage.get_file(
                        f"{self._upgrade_requirements_path}/{file_info.name}"
                    )

                    if file_content.get("success"):
                        import base64
                        content = base64.b64decode(file_content["content"]).decode('utf-8')
                        upgrade_data = json.loads(content)

                        # بررسی هر capability
                        for cap_data in upgrade_data.get("missing_capabilities", []):
                            cap_id = cap_data.get("id")

                            # اگر الان موجود است، skip
                            if self._is_capability_available(cap_id):
                                results["details"].append({
                                    "capability": cap_id,
                                    "status": "already_available"
                                })
                                continue

                            # نصب با Docker image اگر موجود است
                            if cap_data.get("docker_image"):
                                # Pull Docker image
                                success = await self._pull_docker_image(cap_data["docker_image"])
                                results["details"].append({
                                    "capability": cap_id,
                                    "status": "docker_pulled" if success else "docker_failed",
                                    "image": cap_data["docker_image"]
                                })
                                if success:
                                    results["applied"] += 1
                                else:
                                    results["failed"] += 1
                            else:
                                results["details"].append({
                                    "capability": cap_id,
                                    "status": "manual_install_required"
                                })

                except Exception as e:
                    results["failed"] += 1
                    results["details"].append({
                        "file": file_info.name,
                        "status": "error",
                        "error": str(e)
                    })

        except Exception as e:
            logger.error(f"Error checking upgrades: {e}")
            results["error"] = str(e)

        return results

    async def _pull_docker_image(self, image: str) -> bool:
        """Pull یک Docker image"""
        if not self._system_capabilities or not self._system_capabilities.docker_available:
            return False

        try:
            process = await asyncio.create_subprocess_exec(
                "docker", "pull", image,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(process.communicate(), timeout=300)
            return process.returncode == 0
        except Exception as e:
            logger.error(f"Error pulling Docker image {image}: {e}")
            return False

    def get_capability_summary(self) -> Dict[str, Any]:
        """خلاصه قابلیت‌های سیستم"""
        if not self._system_capabilities:
            self._scan_system_capabilities()

        return {
            "system": {
                "os": f"{self._system_capabilities.os_type} {self._system_capabilities.os_version}",
                "architecture": self._system_capabilities.architecture,
                "memory_mb": self._system_capabilities.memory_mb,
                "cpu_cores": self._system_capabilities.cpu_cores
            },
            "docker": {
                "available": self._system_capabilities.docker_available,
                "version": self._system_capabilities.docker_version
            },
            "runtimes": self._system_capabilities.available_runtimes,
            "databases": self._system_capabilities.available_databases,
            "tools": self._system_capabilities.available_tools,
            "supported_project_types": [
                ptype for ptype, reqs in PROJECT_TYPE_REQUIREMENTS.items()
                if all(self._is_capability_available(r) or
                       (self._system_capabilities.docker_available and
                        KNOWN_CAPABILITIES.get(r, Capability(name="", type=CapabilityType.RUNTIME)).docker_image)
                       for r in reqs)
            ]
        }


# Singleton instance
_capability_detector: Optional[CapabilityDetector] = None


def get_capability_detector() -> CapabilityDetector:
    """دریافت instance سرویس"""
    global _capability_detector
    if _capability_detector is None:
        _capability_detector = CapabilityDetector()
    return _capability_detector
