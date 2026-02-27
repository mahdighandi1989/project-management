"""
🚀 AI CREATOR ENGINE - موتور خالق هوشمند
سنگ‌بنای اصلی سیستم

این ماژول هسته اصلی سیستم است که:
- اجرای دستورات سیستمی
- مدیریت فایل‌ها و Git
- هماهنگی مدل‌های AI
- اتصال به سرویس‌های خارجی

طراحی شده برای گسترش‌پذیری بی‌نهایت
"""

import os
import sys
import json
import asyncio
import subprocess
import tempfile
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, Union
from pathlib import Path
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
import uuid
import aiohttp
import aiofiles

# =====================================
# 🎯 CORE TYPES & ENUMS
# =====================================

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskType(str, Enum):
    COMMAND = "command"          # اجرای دستور سیستمی
    CODE_GEN = "code_generation" # تولید کد
    FILE_OP = "file_operation"   # عملیات فایل
    GIT_OP = "git_operation"     # عملیات Git
    API_CALL = "api_call"        # فراخوانی API خارجی
    AI_QUERY = "ai_query"        # پرس‌وجو از AI
    ANALYSIS = "analysis"        # تحلیل داده/کد
    BUILD = "build"              # ساخت پروژه
    RUN = "run"                  # اجرای برنامه

class AgentRole(str, Enum):
    ARCHITECT = "architect"      # طراح معماری
    CODER = "coder"              # کدنویس
    REVIEWER = "reviewer"        # بازبین
    TESTER = "tester"            # تست‌کننده
    DEPLOYER = "deployer"        # استقرار
    ANALYZER = "analyzer"        # تحلیلگر
    CONNECTOR = "connector"      # اتصال‌دهنده
    ORCHESTRATOR = "orchestrator" # هماهنگ‌کننده


@dataclass
class TaskResult:
    """نتیجه یک تسک"""
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_ms: int = 0
    metadata: Dict = field(default_factory=dict)


@dataclass
class Task:
    """تعریف یک تسک"""
    id: str
    type: TaskType
    description: str
    payload: Dict
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[TaskResult] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    parent_task_id: Optional[str] = None
    subtasks: List[str] = field(default_factory=list)
    assigned_model: Optional[str] = None
    assigned_role: Optional[AgentRole] = None


# =====================================
# 🔧 COMMAND EXECUTOR - اجراکننده دستورات
# =====================================

class CommandExecutor:
    """
    اجرای امن دستورات سیستمی
    با قابلیت timeout، logging و sandbox
    """

    def __init__(self, workspace_dir: str = None, timeout: int = 300):
        self.workspace_dir = workspace_dir or tempfile.mkdtemp(prefix="creator_")
        self.timeout = timeout
        self.history: List[Dict] = []

    async def execute(
        self,
        command: str,
        cwd: str = None,
        env: Dict[str, str] = None,
        capture_output: bool = True,
        shell: bool = True
    ) -> TaskResult:
        """اجرای یک دستور"""
        start_time = datetime.now()
        working_dir = cwd or self.workspace_dir

        try:
            # ایجاد محیط
            exec_env = os.environ.copy()
            if env:
                exec_env.update(env)

            # اجرای دستور
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE if capture_output else None,
                stderr=asyncio.subprocess.PIPE if capture_output else None,
                cwd=working_dir,
                env=exec_env
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return TaskResult(
                    success=False,
                    error=f"Command timed out after {self.timeout}s",
                    duration_ms=self.timeout * 1000
                )

            duration = int((datetime.now() - start_time).total_seconds() * 1000)

            # ذخیره در تاریخچه
            self.history.append({
                "command": command,
                "cwd": working_dir,
                "exit_code": process.returncode,
                "timestamp": start_time.isoformat(),
                "duration_ms": duration
            })

            if process.returncode == 0:
                return TaskResult(
                    success=True,
                    output=stdout.decode('utf-8', errors='replace') if stdout else "",
                    duration_ms=duration,
                    metadata={"exit_code": process.returncode}
                )
            else:
                return TaskResult(
                    success=False,
                    output=stdout.decode('utf-8', errors='replace') if stdout else "",
                    error=stderr.decode('utf-8', errors='replace') if stderr else "Unknown error",
                    duration_ms=duration,
                    metadata={"exit_code": process.returncode}
                )

        except Exception as e:
            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            return TaskResult(
                success=False,
                error=str(e),
                duration_ms=duration
            )

    async def execute_script(self, script: str, language: str = "bash") -> TaskResult:
        """اجرای یک اسکریپت"""
        # ایجاد فایل موقت
        ext = {"bash": ".sh", "python": ".py", "node": ".js"}.get(language, ".txt")
        script_path = os.path.join(self.workspace_dir, f"script_{uuid.uuid4().hex[:8]}{ext}")

        async with aiofiles.open(script_path, 'w') as f:
            await f.write(script)

        # تعیین interpreter
        interpreters = {
            "bash": "bash",
            "python": "python3",
            "node": "node",
            "sh": "sh"
        }
        interpreter = interpreters.get(language, "bash")

        result = await self.execute(f"{interpreter} {script_path}")

        # پاکسازی
        try:
            os.remove(script_path)
        except (OSError, IOError):
            pass  # Ignore cleanup errors

        return result


# =====================================
# 📁 FILE MANAGER - مدیریت فایل
# =====================================

class FileManager:
    """
    مدیریت فایل‌ها و دایرکتوری‌ها
    با قابلیت‌های پیشرفته
    """

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, path: str) -> Path:
        """تبدیل مسیر نسبی به مطلق و امن"""
        resolved = (self.base_path / path).resolve()
        # امنیت: اطمینان از عدم خروج از base_path
        if not str(resolved).startswith(str(self.base_path)):
            raise ValueError(f"Path {path} is outside workspace")
        return resolved

    async def read_file(self, path: str) -> TaskResult:
        """خواندن فایل"""
        try:
            file_path = self._resolve_path(path)
            if not file_path.exists():
                return TaskResult(success=False, error=f"File not found: {path}")

            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()

            return TaskResult(
                success=True,
                output=content,
                metadata={"path": str(file_path), "size": len(content)}
            )
        except Exception as e:
            return TaskResult(success=False, error=str(e))

    async def write_file(self, path: str, content: str, create_dirs: bool = True) -> TaskResult:
        """نوشتن فایل"""
        try:
            file_path = self._resolve_path(path)

            if create_dirs:
                file_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)

            return TaskResult(
                success=True,
                output=f"File written: {path}",
                metadata={"path": str(file_path), "size": len(content)}
            )
        except Exception as e:
            return TaskResult(success=False, error=str(e))

    async def list_files(self, path: str = ".", pattern: str = "*", recursive: bool = False) -> TaskResult:
        """لیست فایل‌ها"""
        try:
            dir_path = self._resolve_path(path)
            if not dir_path.is_dir():
                return TaskResult(success=False, error=f"Not a directory: {path}")

            if recursive:
                files = list(dir_path.rglob(pattern))
            else:
                files = list(dir_path.glob(pattern))

            file_list = []
            for f in files:
                rel_path = f.relative_to(self.base_path)
                file_list.append({
                    "path": str(rel_path),
                    "name": f.name,
                    "is_dir": f.is_dir(),
                    "size": f.stat().st_size if f.is_file() else 0
                })

            return TaskResult(success=True, output=file_list)
        except Exception as e:
            return TaskResult(success=False, error=str(e))

    async def delete(self, path: str) -> TaskResult:
        """حذف فایل یا دایرکتوری"""
        try:
            target = self._resolve_path(path)
            if not target.exists():
                return TaskResult(success=False, error=f"Not found: {path}")

            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()

            return TaskResult(success=True, output=f"Deleted: {path}")
        except Exception as e:
            return TaskResult(success=False, error=str(e))

    async def copy(self, src: str, dst: str) -> TaskResult:
        """کپی فایل یا دایرکتوری"""
        try:
            src_path = self._resolve_path(src)
            dst_path = self._resolve_path(dst)

            if not src_path.exists():
                return TaskResult(success=False, error=f"Source not found: {src}")

            dst_path.parent.mkdir(parents=True, exist_ok=True)

            if src_path.is_dir():
                shutil.copytree(src_path, dst_path)
            else:
                shutil.copy2(src_path, dst_path)

            return TaskResult(success=True, output=f"Copied: {src} -> {dst}")
        except Exception as e:
            return TaskResult(success=False, error=str(e))

    def get_tree(self, path: str = ".", max_depth: int = 3) -> Dict:
        """دریافت ساختار درختی"""
        def build_tree(dir_path: Path, depth: int = 0) -> Dict:
            if depth > max_depth:
                return {"name": "...", "type": "truncated"}

            result = {
                "name": dir_path.name or str(dir_path),
                "type": "directory",
                "children": []
            }

            try:
                for item in sorted(dir_path.iterdir()):
                    if item.name.startswith('.'):
                        continue
                    if item.is_dir():
                        result["children"].append(build_tree(item, depth + 1))
                    else:
                        result["children"].append({
                            "name": item.name,
                            "type": "file",
                            "size": item.stat().st_size
                        })
            except PermissionError:
                pass

            return result

        try:
            target = self._resolve_path(path)
            return build_tree(target)
        except Exception as e:
            return {"error": str(e)}


# =====================================
# 🔀 GIT MANAGER - مدیریت Git
# =====================================

class GitManager:
    """
    مدیریت کامل Git
    clone, commit, push, pull, branch, ...
    """

    def __init__(self, executor: CommandExecutor):
        self.executor = executor

    async def clone(self, url: str, path: str = None, branch: str = None) -> TaskResult:
        """Clone یک repo"""
        cmd = f"git clone {url}"
        if branch:
            cmd += f" -b {branch}"
        if path:
            cmd += f" {path}"
        return await self.executor.execute(cmd)

    async def init(self, path: str = ".") -> TaskResult:
        """Initialize یک repo جدید"""
        return await self.executor.execute(f"git init", cwd=path)

    async def status(self, path: str = ".") -> TaskResult:
        """وضعیت repo"""
        return await self.executor.execute("git status --porcelain", cwd=path)

    async def add(self, files: Union[str, List[str]] = ".", path: str = ".") -> TaskResult:
        """اضافه کردن فایل‌ها به staging"""
        if isinstance(files, list):
            files = " ".join(files)
        return await self.executor.execute(f"git add {files}", cwd=path)

    async def commit(self, message: str, path: str = ".") -> TaskResult:
        """ایجاد commit"""
        # Escape کردن پیام
        message = message.replace('"', '\\"')
        return await self.executor.execute(f'git commit -m "{message}"', cwd=path)

    async def push(self, remote: str = "origin", branch: str = None, path: str = ".") -> TaskResult:
        """Push به remote"""
        cmd = f"git push {remote}"
        if branch:
            cmd += f" {branch}"
        return await self.executor.execute(cmd, cwd=path)

    async def pull(self, remote: str = "origin", branch: str = None, path: str = ".") -> TaskResult:
        """Pull از remote"""
        cmd = f"git pull {remote}"
        if branch:
            cmd += f" {branch}"
        return await self.executor.execute(cmd, cwd=path)

    async def branch(self, name: str = None, path: str = ".", create: bool = False) -> TaskResult:
        """مدیریت branch"""
        if name:
            if create:
                cmd = f"git checkout -b {name}"
            else:
                cmd = f"git checkout {name}"
        else:
            cmd = "git branch -a"
        return await self.executor.execute(cmd, cwd=path)

    async def log(self, count: int = 10, path: str = ".") -> TaskResult:
        """تاریخچه commit"""
        return await self.executor.execute(
            f"git log --oneline -n {count}",
            cwd=path
        )

    async def diff(self, path: str = ".", staged: bool = False) -> TaskResult:
        """تغییرات"""
        cmd = "git diff --staged" if staged else "git diff"
        return await self.executor.execute(cmd, cwd=path)


# =====================================
# 🌐 EXTERNAL CONNECTOR - اتصال به سرویس‌های خارجی
# =====================================

@dataclass
class ExternalService:
    """تعریف یک سرویس خارجی"""
    id: str
    name: str
    base_url: str
    auth_type: str = "none"  # none, api_key, bearer, basic
    auth_config: Dict = field(default_factory=dict)
    headers: Dict = field(default_factory=dict)
    discovered_endpoints: List[Dict] = field(default_factory=list)
    schema: Optional[Dict] = None
    status: str = "unknown"


class ExternalConnector:
    """
    اتصال به سرویس‌های خارجی
    با قابلیت کشف خودکار API
    """

    def __init__(self):
        self.services: Dict[str, ExternalService] = {}
        self.session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

    def register_service(
        self,
        name: str,
        base_url: str,
        auth_type: str = "none",
        auth_config: Dict = None,
        headers: Dict = None
    ) -> str:
        """ثبت یک سرویس جدید"""
        service_id = f"svc_{uuid.uuid4().hex[:8]}"
        self.services[service_id] = ExternalService(
            id=service_id,
            name=name,
            base_url=base_url.rstrip('/'),
            auth_type=auth_type,
            auth_config=auth_config or {},
            headers=headers or {}
        )
        return service_id

    def _get_auth_headers(self, service: ExternalService) -> Dict:
        """ساخت هدرهای احراز هویت"""
        headers = service.headers.copy()

        if service.auth_type == "api_key":
            key_name = service.auth_config.get("key_name", "X-API-Key")
            key_value = service.auth_config.get("key_value", "")
            headers[key_name] = key_value

        elif service.auth_type == "bearer":
            token = service.auth_config.get("token", "")
            headers["Authorization"] = f"Bearer {token}"

        elif service.auth_type == "basic":
            import base64
            username = service.auth_config.get("username", "")
            password = service.auth_config.get("password", "")
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"

        return headers

    async def request(
        self,
        service_id: str,
        method: str,
        endpoint: str,
        data: Any = None,
        params: Dict = None,
        extra_headers: Dict = None
    ) -> TaskResult:
        """ارسال درخواست به سرویس"""
        await self._ensure_session()

        service = self.services.get(service_id)
        if not service:
            return TaskResult(success=False, error=f"Service not found: {service_id}")

        url = f"{service.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_auth_headers(service)
        if extra_headers:
            headers.update(extra_headers)

        try:
            async with self.session.request(
                method=method.upper(),
                url=url,
                json=data if method.upper() in ['POST', 'PUT', 'PATCH'] else None,
                params=params,
                headers=headers
            ) as response:
                try:
                    body = await response.json()
                except (json.JSONDecodeError, aiohttp.ContentTypeError, ValueError):
                    body = await response.text()

                return TaskResult(
                    success=response.status < 400,
                    output=body,
                    metadata={
                        "status_code": response.status,
                        "headers": dict(response.headers),
                        "url": str(response.url)
                    }
                )

        except Exception as e:
            return TaskResult(success=False, error=str(e))

    async def discover_api(self, service_id: str) -> TaskResult:
        """کشف خودکار API یک سرویس"""
        service = self.services.get(service_id)
        if not service:
            return TaskResult(success=False, error=f"Service not found: {service_id}")

        discovered = []

        # تلاش برای یافتن OpenAPI/Swagger
        common_paths = [
            "/openapi.json",
            "/swagger.json",
            "/api/openapi.json",
            "/api/swagger.json",
            "/docs/openapi.json",
            "/api-docs",
            "/v1/openapi.json",
            "/v2/openapi.json"
        ]

        for path in common_paths:
            result = await self.request(service_id, "GET", path)
            if result.success and isinstance(result.output, dict):
                if "openapi" in result.output or "swagger" in result.output:
                    service.schema = result.output
                    service.status = "connected"

                    # استخراج endpoints
                    paths = result.output.get("paths", {})
                    for endpoint, methods in paths.items():
                        for method, details in methods.items():
                            if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                                discovered.append({
                                    "method": method.upper(),
                                    "path": endpoint,
                                    "summary": details.get("summary", ""),
                                    "parameters": details.get("parameters", [])
                                })

                    service.discovered_endpoints = discovered
                    return TaskResult(
                        success=True,
                        output={
                            "schema_found": True,
                            "endpoints_count": len(discovered),
                            "endpoints": discovered[:20]  # اولین 20 تا
                        }
                    )

        # اگر schema پیدا نشد، health check ساده
        health_result = await self.request(service_id, "GET", "/")
        service.status = "connected" if health_result.success else "error"

        return TaskResult(
            success=health_result.success,
            output={
                "schema_found": False,
                "health_check": health_result.success,
                "response": health_result.output if health_result.success else health_result.error
            }
        )

    async def analyze_service(self, service_id: str) -> Dict:
        """تحلیل کامل یک سرویس"""
        service = self.services.get(service_id)
        if not service:
            return {"error": "Service not found"}

        # کشف API
        discovery = await self.discover_api(service_id)

        analysis = {
            "service_id": service_id,
            "name": service.name,
            "base_url": service.base_url,
            "status": service.status,
            "auth_type": service.auth_type,
            "has_schema": service.schema is not None,
            "endpoints_discovered": len(service.discovered_endpoints),
            "discovery_result": discovery.output
        }

        # اگر schema داریم، اطلاعات بیشتر
        if service.schema:
            analysis["api_info"] = {
                "title": service.schema.get("info", {}).get("title", "Unknown"),
                "version": service.schema.get("info", {}).get("version", "Unknown"),
                "description": service.schema.get("info", {}).get("description", "")[:200]
            }

        return analysis


# =====================================
# 🧠 AI ORCHESTRATOR - هماهنگ‌کننده مدل‌ها
# =====================================

class AIOrchestrator:
    """
    هماهنگی و مدیریت چندین مدل AI
    برای همکاری در تولید کد و محتوا
    """

    def __init__(self, ai_manager):
        self.ai_manager = ai_manager
        self.active_agents: Dict[str, Dict] = {}

    async def create_agent(
        self,
        role: AgentRole,
        model_id: str = None,
        system_prompt: str = None
    ) -> str:
        """ایجاد یک agent جدید"""
        agent_id = f"agent_{uuid.uuid4().hex[:8]}"

        # انتخاب مدل مناسب بر اساس نقش
        if not model_id:
            model_id = self._select_model_for_role(role)

        # تعریف system prompt بر اساس نقش
        if not system_prompt:
            system_prompt = self._get_role_prompt(role)

        self.active_agents[agent_id] = {
            "id": agent_id,
            "role": role,
            "model_id": model_id,
            "system_prompt": system_prompt,
            "conversation_history": [],
            "created_at": datetime.now().isoformat()
        }

        return agent_id

    def _select_model_for_role(self, role: AgentRole) -> str:
        """انتخاب بهترین مدل برای هر نقش"""
        role_model_preferences = {
            AgentRole.ARCHITECT: ["claude-sonnet-4-20250514", "gpt-4-turbo", "gemini-2.5-pro"],
            AgentRole.CODER: ["deepseek-coder", "claude-sonnet-4-20250514", "gpt-4-turbo"],
            AgentRole.REVIEWER: ["gpt-4-turbo", "claude-3-5-sonnet-20241022"],
            AgentRole.TESTER: ["deepseek-chat", "gpt-4o-mini"],
            AgentRole.ANALYZER: ["gemini-2.5-pro", "claude-sonnet-4-20250514"],
            AgentRole.ORCHESTRATOR: ["claude-sonnet-4-20250514", "gpt-4o"]
        }

        preferences = role_model_preferences.get(role, ["gpt-4-turbo"])
        available = self.ai_manager.get_available_models()

        for model in preferences:
            if model in [m.get("id") for m in available]:
                return model

        # fallback به اولین مدل موجود
        return available[0]["id"] if available else "gpt-4-turbo"

    def _get_role_prompt(self, role: AgentRole) -> str:
        """دریافت system prompt برای هر نقش"""
        prompts = {
            AgentRole.ARCHITECT: """شما یک معمار نرم‌افزار ارشد هستید.
وظایف شما:
- طراحی معماری سیستم‌ها
- تعیین ساختار پروژه
- انتخاب تکنولوژی‌ها
- تعریف الگوهای طراحی
همیشه معماری تمیز و قابل گسترش طراحی کنید.""",

            AgentRole.CODER: """شما یک برنامه‌نویس حرفه‌ای هستید.
وظایف شما:
- نوشتن کد تمیز و بهینه
- رعایت best practices
- مستندسازی مناسب
- مدیریت خطاها
کد کامل و قابل اجرا تولید کنید.""",

            AgentRole.REVIEWER: """شما یک بازبین کد حرفه‌ای هستید.
وظایف شما:
- بررسی کیفیت کد
- یافتن باگ‌ها و مشکلات
- پیشنهاد بهبود
- بررسی امنیت
صادقانه و دقیق بررسی کنید.""",

            AgentRole.TESTER: """شما یک متخصص تست نرم‌افزار هستید.
وظایف شما:
- نوشتن تست‌های جامع
- تست‌های واحد و یکپارچگی
- edge cases
- گزارش نتایج
پوشش کامل تست ایجاد کنید.""",

            AgentRole.ANALYZER: """شما یک تحلیلگر سیستم هستید.
وظایف شما:
- تحلیل کد موجود
- درک ساختار سیستم
- شناسایی الگوها
- استخراج اطلاعات
تحلیل دقیق و جامع ارائه دهید.""",

            AgentRole.ORCHESTRATOR: """شما هماهنگ‌کننده تیم هستید.
وظایف شما:
- تقسیم کار بین اعضا
- ترکیب نتایج
- حل تعارضات
- اطمینان از یکپارچگی
همه را هماهنگ نگه دارید."""
        }

        return prompts.get(role, "شما یک دستیار هوشمند هستید.")

    async def query_agent(
        self,
        agent_id: str,
        message: str,
        context: Dict = None
    ) -> TaskResult:
        """پرس‌وجو از یک agent"""
        agent = self.active_agents.get(agent_id)
        if not agent:
            return TaskResult(success=False, error=f"Agent not found: {agent_id}")

        # ساخت پیام با context
        full_message = message
        if context:
            context_str = json.dumps(context, ensure_ascii=False, indent=2)
            full_message = f"Context:\n```json\n{context_str}\n```\n\n{message}"

        # اضافه به تاریخچه
        agent["conversation_history"].append({
            "role": "user",
            "content": full_message
        })

        try:
            # فراخوانی مدل
            response = await self.ai_manager.generate(
                model_id=agent["model_id"],
                prompt=full_message,
                system_prompt=agent["system_prompt"],
                max_tokens=4000
            )

            if response.get("success"):
                content = response.get("content", "")
                agent["conversation_history"].append({
                    "role": "assistant",
                    "content": content
                })
                return TaskResult(
                    success=True,
                    output=content,
                    metadata={
                        "model": agent["model_id"],
                        "role": agent["role"].value,
                        "tokens": response.get("usage", {})
                    }
                )
            else:
                return TaskResult(success=False, error=response.get("error", "Unknown error"))

        except Exception as e:
            return TaskResult(success=False, error=str(e))

    async def collaborative_generate(
        self,
        task_description: str,
        roles: List[AgentRole] = None,
        iterations: int = 2
    ) -> TaskResult:
        """تولید همکارانه با چندین agent"""
        if not roles:
            roles = [AgentRole.ARCHITECT, AgentRole.CODER, AgentRole.REVIEWER]

        # ایجاد agents
        agents = {}
        for role in roles:
            agent_id = await self.create_agent(role)
            agents[role] = agent_id

        results = []
        current_output = ""

        for iteration in range(iterations):
            iteration_results = {}

            for role in roles:
                agent_id = agents[role]

                # ساخت پیام با خروجی‌های قبلی
                if iteration == 0:
                    message = f"وظیفه:\n{task_description}"
                else:
                    message = f"""وظیفه اصلی:\n{task_description}

خروجی‌های قبلی:
{current_output}

لطفاً بر اساس نقش خود ({role.value}) بهبود دهید یا ادامه دهید."""

                result = await self.query_agent(agent_id, message)
                iteration_results[role.value] = result.output if result.success else result.error

            # ترکیب نتایج
            current_output = json.dumps(iteration_results, ensure_ascii=False, indent=2)
            results.append({"iteration": iteration + 1, "results": iteration_results})

        return TaskResult(
            success=True,
            output={
                "task": task_description,
                "iterations": results,
                "final_output": current_output
            }
        )


# =====================================
# 🏗️ PROJECT CREATOR - خالق پروژه
# =====================================

class ProjectCreator:
    """
    ایجاد پروژه‌های کامل از صفر
    با استفاده از AI و اتوماسیون
    """

    def __init__(
        self,
        workspace_base: str,
        executor: CommandExecutor,
        file_manager: FileManager,
        git_manager: GitManager,
        ai_orchestrator: AIOrchestrator
    ):
        self.workspace_base = Path(workspace_base)
        self.executor = executor
        self.file_manager = file_manager
        self.git_manager = git_manager
        self.ai_orchestrator = ai_orchestrator
        self.active_projects: Dict[str, Dict] = {}

    async def create_project(
        self,
        name: str,
        description: str,
        project_type: str,
        technologies: List[str] = None,
        features: List[str] = None
    ) -> TaskResult:
        """ایجاد یک پروژه کامل"""
        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        project_path = self.workspace_base / name

        # ایجاد دایرکتوری
        project_path.mkdir(parents=True, exist_ok=True)

        self.active_projects[project_id] = {
            "id": project_id,
            "name": name,
            "path": str(project_path),
            "type": project_type,
            "technologies": technologies or [],
            "features": features or [],
            "description": description,
            "created_at": datetime.now().isoformat(),
            "status": "creating",
            "files": []
        }

        # استفاده از AI برای تولید ساختار
        architect_agent = await self.ai_orchestrator.create_agent(AgentRole.ARCHITECT)

        structure_prompt = f"""یک پروژه {project_type} با نام "{name}" طراحی کن.

توضیحات: {description}

تکنولوژی‌ها: {', '.join(technologies or ['مناسب انتخاب کن'])}
قابلیت‌ها: {', '.join(features or [])}

خروجی مورد نظر (JSON):
{{
    "structure": {{
        "directories": ["لیست پوشه‌ها"],
        "files": [
            {{"path": "مسیر فایل", "description": "توضیح"}}
        ]
    }},
    "dependencies": {{"name": "version"}},
    "scripts": {{"script_name": "command"}},
    "config_files": ["لیست فایل‌های config"]
}}

فقط JSON برگردان."""

        structure_result = await self.ai_orchestrator.query_agent(
            architect_agent,
            structure_prompt
        )

        if not structure_result.success:
            return TaskResult(success=False, error=f"Failed to generate structure: {structure_result.error}")

        # پارس ساختار
        try:
            # استخراج JSON از پاسخ
            output = structure_result.output
            start = output.find('{')
            end = output.rfind('}') + 1
            if start >= 0 and end > start:
                structure = json.loads(output[start:end])
            else:
                structure = {"structure": {"directories": ["src"], "files": []}, "dependencies": {}}
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.warning(f"Could not parse project structure JSON: {e}")
            structure = {"structure": {"directories": ["src"], "files": []}, "dependencies": {}}

        # ایجاد دایرکتوری‌ها
        for dir_path in structure.get("structure", {}).get("directories", []):
            (project_path / dir_path).mkdir(parents=True, exist_ok=True)

        # Git init
        await self.git_manager.init(str(project_path))

        # ایجاد README
        readme_content = f"""# {name}

{description}

## نوع پروژه
{project_type}

## تکنولوژی‌ها
{chr(10).join(['- ' + t for t in (technologies or [])])}

## قابلیت‌ها
{chr(10).join(['- ' + f for f in (features or [])])}

---
ایجاد شده توسط AI Creator Engine
"""
        await self.file_manager.write_file(
            str(project_path / "README.md"),
            readme_content
        )

        self.active_projects[project_id]["status"] = "created"
        self.active_projects[project_id]["structure"] = structure

        return TaskResult(
            success=True,
            output={
                "project_id": project_id,
                "name": name,
                "path": str(project_path),
                "structure": structure
            }
        )

    async def generate_file(
        self,
        project_id: str,
        file_path: str,
        description: str
    ) -> TaskResult:
        """تولید یک فایل با AI"""
        project = self.active_projects.get(project_id)
        if not project:
            return TaskResult(success=False, error="Project not found")

        coder_agent = await self.ai_orchestrator.create_agent(AgentRole.CODER)

        # تشخیص زبان از پسوند
        ext = Path(file_path).suffix.lower()
        language_map = {
            '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript',
            '.jsx': 'React JSX', '.tsx': 'React TSX', '.html': 'HTML',
            '.css': 'CSS', '.json': 'JSON', '.yaml': 'YAML', '.yml': 'YAML',
            '.sql': 'SQL', '.sh': 'Bash', '.go': 'Go', '.rs': 'Rust'
        }
        language = language_map.get(ext, 'text')

        prompt = f"""فایل زیر را برای پروژه "{project['name']}" بنویس:

فایل: {file_path}
زبان: {language}
توضیحات: {description}

پروژه: {project.get('type', 'general')}
تکنولوژی‌ها: {', '.join(project.get('technologies', []))}

فقط کد را برگردان، بدون توضیحات اضافی.
کد باید کامل و قابل اجرا باشد."""

        result = await self.ai_orchestrator.query_agent(coder_agent, prompt)

        if result.success:
            # استخراج کد از پاسخ
            code = result.output

            # 🛡️ پاکسازی کامل محتوا از آلودگی reasoning/markdown (ماژول مرکزی)
            from .content_sanitizer import strip_reasoning_blocks, sanitize_file_content
            code = strip_reasoning_blocks(code)
            code = sanitize_file_content(code, file_path)

            full_path = Path(project['path']) / file_path
            await self.file_manager.write_file(str(full_path), code)

            project['files'].append(file_path)

            return TaskResult(
                success=True,
                output={"path": file_path, "content_length": len(code)}
            )
        else:
            return result

    async def run_project(
        self,
        project_id: str,
        command: str = None
    ) -> TaskResult:
        """اجرای پروژه"""
        project = self.active_projects.get(project_id)
        if not project:
            return TaskResult(success=False, error="Project not found")

        project_path = project['path']

        # تشخیص نوع پروژه و دستور اجرا
        if not command:
            project_type = project.get('type', '').lower()
            if project_type in ['python', 'fastapi', 'flask', 'django']:
                command = "python main.py"
            elif project_type in ['node', 'nodejs', 'express', 'nextjs', 'react']:
                command = "npm run dev"
            else:
                command = "echo 'No run command specified'"

        return await self.executor.execute(command, cwd=project_path)


# =====================================
# 🎮 MAIN ENGINE - موتور اصلی
# =====================================

class CreatorEngine:
    """
    موتور خالق اصلی
    نقطه ورود برای همه عملیات
    """

    def __init__(self, workspace_base: str = "./workspaces"):
        self.workspace_base = Path(workspace_base)
        self.workspace_base.mkdir(parents=True, exist_ok=True)

        # اجزای سیستم
        self.executor = CommandExecutor(str(self.workspace_base))
        self.file_manager = FileManager(str(self.workspace_base))
        self.git_manager = GitManager(self.executor)
        self.connector = ExternalConnector()
        self.ai_orchestrator = None  # بعداً initialize می‌شود
        self.project_creator = None  # بعداً initialize می‌شود

        # تاریخچه تسک‌ها
        self.tasks: Dict[str, Task] = {}

    def initialize(self, ai_manager):
        """Initialize با AI Manager"""
        self.ai_orchestrator = AIOrchestrator(ai_manager)
        self.project_creator = ProjectCreator(
            str(self.workspace_base),
            self.executor,
            self.file_manager,
            self.git_manager,
            self.ai_orchestrator
        )

    async def execute_task(self, task: Task) -> TaskResult:
        """اجرای یک تسک"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now().isoformat()
        self.tasks[task.id] = task

        try:
            if task.type == TaskType.COMMAND:
                result = await self.executor.execute(task.payload.get("command", ""))

            elif task.type == TaskType.FILE_OP:
                op = task.payload.get("operation", "read")
                path = task.payload.get("path", "")
                if op == "read":
                    result = await self.file_manager.read_file(path)
                elif op == "write":
                    result = await self.file_manager.write_file(path, task.payload.get("content", ""))
                elif op == "list":
                    result = await self.file_manager.list_files(path)
                elif op == "delete":
                    result = await self.file_manager.delete(path)
                else:
                    result = TaskResult(success=False, error=f"Unknown file operation: {op}")

            elif task.type == TaskType.GIT_OP:
                op = task.payload.get("operation", "status")
                path = task.payload.get("path", ".")
                if op == "clone":
                    result = await self.git_manager.clone(task.payload.get("url", ""), path)
                elif op == "status":
                    result = await self.git_manager.status(path)
                elif op == "commit":
                    result = await self.git_manager.commit(task.payload.get("message", "Update"), path)
                elif op == "push":
                    result = await self.git_manager.push(path=path)
                elif op == "pull":
                    result = await self.git_manager.pull(path=path)
                else:
                    result = TaskResult(success=False, error=f"Unknown git operation: {op}")

            elif task.type == TaskType.API_CALL:
                service_id = task.payload.get("service_id", "")
                result = await self.connector.request(
                    service_id,
                    task.payload.get("method", "GET"),
                    task.payload.get("endpoint", "/"),
                    task.payload.get("data"),
                    task.payload.get("params")
                )

            elif task.type == TaskType.AI_QUERY:
                if not self.ai_orchestrator:
                    result = TaskResult(success=False, error="AI not initialized")
                else:
                    agent_id = task.payload.get("agent_id")
                    if not agent_id:
                        agent_id = await self.ai_orchestrator.create_agent(
                            AgentRole(task.payload.get("role", "coder"))
                        )
                    result = await self.ai_orchestrator.query_agent(
                        agent_id,
                        task.payload.get("message", ""),
                        task.payload.get("context")
                    )

            elif task.type == TaskType.CODE_GEN:
                if not self.project_creator:
                    result = TaskResult(success=False, error="Project creator not initialized")
                else:
                    result = await self.project_creator.generate_file(
                        task.payload.get("project_id", ""),
                        task.payload.get("file_path", ""),
                        task.payload.get("description", "")
                    )

            else:
                result = TaskResult(success=False, error=f"Unknown task type: {task.type}")

        except Exception as e:
            result = TaskResult(success=False, error=str(e))

        task.result = result
        task.status = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
        task.completed_at = datetime.now().isoformat()

        return result

    async def close(self):
        """بستن منابع"""
        await self.connector.close()


# Singleton instance
_engine: Optional[CreatorEngine] = None

def get_creator_engine() -> CreatorEngine:
    global _engine
    if _engine is None:
        _engine = CreatorEngine()
    return _engine
