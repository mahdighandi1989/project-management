"""
🚀 API Routes for Creator Engine
مسیرهای API برای موتور خالق
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid

from ...services.creator_engine import (
    get_creator_engine,
    Task,
    TaskType,
    TaskStatus,
    AgentRole,
    ExternalService
)
from ...services.ai_manager import get_ai_manager

router = APIRouter(prefix="/creator", tags=["Creator Engine"])


# =====================================
# مدل‌های درخواست
# =====================================

class ExecuteCommandRequest(BaseModel):
    command: str
    cwd: Optional[str] = None
    timeout: Optional[int] = 300


class FileOperationRequest(BaseModel):
    operation: str  # read, write, list, delete, copy
    path: str
    content: Optional[str] = None
    destination: Optional[str] = None
    pattern: Optional[str] = "*"
    recursive: Optional[bool] = False


class GitOperationRequest(BaseModel):
    operation: str  # clone, init, status, add, commit, push, pull, branch, log
    path: Optional[str] = "."
    url: Optional[str] = None
    message: Optional[str] = None
    branch: Optional[str] = None
    files: Optional[List[str]] = None


class RegisterServiceRequest(BaseModel):
    name: str
    base_url: str
    auth_type: str = "none"  # none, api_key, bearer, basic
    auth_config: Optional[Dict] = None
    headers: Optional[Dict] = None


class ServiceRequestModel(BaseModel):
    method: str = "GET"
    endpoint: str = "/"
    data: Optional[Dict] = None
    params: Optional[Dict] = None


class CreateAgentRequest(BaseModel):
    role: str  # architect, coder, reviewer, tester, analyzer, orchestrator
    model_id: Optional[str] = None
    system_prompt: Optional[str] = None


class QueryAgentRequest(BaseModel):
    message: str
    context: Optional[Dict] = None


class CreateProjectRequest(BaseModel):
    name: str
    description: str
    project_type: str  # python, node, react, fastapi, nextjs, etc.
    technologies: Optional[List[str]] = None
    features: Optional[List[str]] = None


class GenerateFileRequest(BaseModel):
    file_path: str
    description: str


class CollaborativeTaskRequest(BaseModel):
    description: str
    roles: Optional[List[str]] = None
    iterations: Optional[int] = 2


# =====================================
# Initialization
# =====================================

@router.on_event("startup")
async def startup():
    """Initialize engine with AI manager"""
    engine = get_creator_engine()
    ai_manager = get_ai_manager()
    engine.initialize(ai_manager)


# =====================================
# 🔧 Command Execution
# =====================================

@router.post("/execute")
async def execute_command(request: ExecuteCommandRequest):
    """اجرای یک دستور سیستمی"""
    engine = get_creator_engine()
    result = await engine.executor.execute(
        command=request.command,
        cwd=request.cwd
    )

    return {
        "success": result.success,
        "output": result.output,
        "error": result.error,
        "duration_ms": result.duration_ms,
        "metadata": result.metadata
    }


@router.post("/execute-script")
async def execute_script(script: str, language: str = "bash"):
    """اجرای یک اسکریپت"""
    engine = get_creator_engine()
    result = await engine.executor.execute_script(script, language)

    return {
        "success": result.success,
        "output": result.output,
        "error": result.error,
        "duration_ms": result.duration_ms
    }


# =====================================
# 📁 File Operations
# =====================================

@router.post("/files")
async def file_operation(request: FileOperationRequest):
    """عملیات فایل"""
    engine = get_creator_engine()
    fm = engine.file_manager

    if request.operation == "read":
        result = await fm.read_file(request.path)
    elif request.operation == "write":
        result = await fm.write_file(request.path, request.content or "")
    elif request.operation == "list":
        result = await fm.list_files(request.path, request.pattern, request.recursive)
    elif request.operation == "delete":
        result = await fm.delete(request.path)
    elif request.operation == "copy":
        result = await fm.copy(request.path, request.destination or "")
    else:
        raise HTTPException(status_code=400, detail=f"Unknown operation: {request.operation}")

    return {
        "success": result.success,
        "output": result.output,
        "error": result.error,
        "metadata": result.metadata
    }


@router.get("/files/tree")
async def get_file_tree(path: str = ".", max_depth: int = 3):
    """ساختار درختی فایل‌ها"""
    engine = get_creator_engine()
    tree = engine.file_manager.get_tree(path, max_depth)
    return {"success": True, "tree": tree}


# =====================================
# 🔀 Git Operations
# =====================================

@router.post("/git")
async def git_operation(request: GitOperationRequest):
    """عملیات Git"""
    engine = get_creator_engine()
    git = engine.git_manager

    if request.operation == "clone":
        result = await git.clone(request.url or "", request.path, request.branch)
    elif request.operation == "init":
        result = await git.init(request.path)
    elif request.operation == "status":
        result = await git.status(request.path)
    elif request.operation == "add":
        result = await git.add(request.files or ".", request.path)
    elif request.operation == "commit":
        result = await git.commit(request.message or "Update", request.path)
    elif request.operation == "push":
        result = await git.push(path=request.path, branch=request.branch)
    elif request.operation == "pull":
        result = await git.pull(path=request.path, branch=request.branch)
    elif request.operation == "branch":
        result = await git.branch(request.branch, request.path)
    elif request.operation == "log":
        result = await git.log(10, request.path)
    elif request.operation == "diff":
        result = await git.diff(request.path)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown git operation: {request.operation}")

    return {
        "success": result.success,
        "output": result.output,
        "error": result.error,
        "metadata": result.metadata
    }


# =====================================
# 🌐 External Services
# =====================================

@router.post("/services")
async def register_service(request: RegisterServiceRequest):
    """ثبت یک سرویس خارجی"""
    engine = get_creator_engine()
    service_id = engine.connector.register_service(
        name=request.name,
        base_url=request.base_url,
        auth_type=request.auth_type,
        auth_config=request.auth_config,
        headers=request.headers
    )

    return {
        "success": True,
        "service_id": service_id,
        "message": f"Service '{request.name}' registered"
    }


@router.get("/services")
async def list_services():
    """لیست سرویس‌های ثبت شده"""
    engine = get_creator_engine()
    services = [
        {
            "id": s.id,
            "name": s.name,
            "base_url": s.base_url,
            "status": s.status,
            "endpoints_count": len(s.discovered_endpoints)
        }
        for s in engine.connector.services.values()
    ]
    return {"success": True, "services": services, "count": len(services)}


@router.post("/services/{service_id}/request")
async def call_service(service_id: str, request: ServiceRequestModel):
    """فراخوانی API یک سرویس"""
    engine = get_creator_engine()
    result = await engine.connector.request(
        service_id,
        request.method,
        request.endpoint,
        request.data,
        request.params
    )

    return {
        "success": result.success,
        "data": result.output,
        "error": result.error,
        "metadata": result.metadata
    }


@router.post("/services/{service_id}/discover")
async def discover_service(service_id: str):
    """کشف خودکار API سرویس"""
    engine = get_creator_engine()
    result = await engine.connector.discover_api(service_id)

    return {
        "success": result.success,
        "discovery": result.output,
        "error": result.error
    }


@router.get("/services/{service_id}/analyze")
async def analyze_service(service_id: str):
    """تحلیل کامل سرویس"""
    engine = get_creator_engine()
    analysis = await engine.connector.analyze_service(service_id)
    return {"success": True, "analysis": analysis}


# =====================================
# 🧠 AI Agents
# =====================================

@router.post("/agents")
async def create_agent(request: CreateAgentRequest):
    """ایجاد یک agent جدید"""
    engine = get_creator_engine()
    if not engine.ai_orchestrator:
        raise HTTPException(status_code=500, detail="AI not initialized")

    try:
        role = AgentRole(request.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {request.role}")

    agent_id = await engine.ai_orchestrator.create_agent(
        role=role,
        model_id=request.model_id,
        system_prompt=request.system_prompt
    )

    agent = engine.ai_orchestrator.active_agents.get(agent_id)

    return {
        "success": True,
        "agent_id": agent_id,
        "role": request.role,
        "model": agent.get("model_id") if agent else None
    }


@router.get("/agents")
async def list_agents():
    """لیست agents فعال"""
    engine = get_creator_engine()
    if not engine.ai_orchestrator:
        return {"success": True, "agents": [], "count": 0}

    agents = [
        {
            "id": a["id"],
            "role": a["role"].value,
            "model": a["model_id"],
            "created_at": a["created_at"],
            "messages_count": len(a["conversation_history"])
        }
        for a in engine.ai_orchestrator.active_agents.values()
    ]

    return {"success": True, "agents": agents, "count": len(agents)}


@router.post("/agents/{agent_id}/query")
async def query_agent(agent_id: str, request: QueryAgentRequest):
    """پرس‌وجو از agent"""
    engine = get_creator_engine()
    if not engine.ai_orchestrator:
        raise HTTPException(status_code=500, detail="AI not initialized")

    result = await engine.ai_orchestrator.query_agent(
        agent_id,
        request.message,
        request.context
    )

    return {
        "success": result.success,
        "response": result.output,
        "error": result.error,
        "metadata": result.metadata
    }


@router.post("/agents/collaborative")
async def collaborative_task(request: CollaborativeTaskRequest):
    """تسک همکارانه با چندین agent"""
    engine = get_creator_engine()
    if not engine.ai_orchestrator:
        raise HTTPException(status_code=500, detail="AI not initialized")

    roles = None
    if request.roles:
        try:
            roles = [AgentRole(r) for r in request.roles]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid role: {e}")

    result = await engine.ai_orchestrator.collaborative_generate(
        task_description=request.description,
        roles=roles,
        iterations=request.iterations
    )

    return {
        "success": result.success,
        "result": result.output,
        "error": result.error
    }


# =====================================
# 🏗️ Project Creation
# =====================================

@router.post("/projects/create")
async def create_project(request: CreateProjectRequest):
    """ایجاد یک پروژه جدید"""
    engine = get_creator_engine()
    if not engine.project_creator:
        raise HTTPException(status_code=500, detail="Project creator not initialized")

    result = await engine.project_creator.create_project(
        name=request.name,
        description=request.description,
        project_type=request.project_type,
        technologies=request.technologies,
        features=request.features
    )

    return {
        "success": result.success,
        "project": result.output,
        "error": result.error
    }


@router.get("/projects/active")
async def list_active_projects():
    """لیست پروژه‌های فعال"""
    engine = get_creator_engine()
    if not engine.project_creator:
        return {"success": True, "projects": [], "count": 0}

    projects = list(engine.project_creator.active_projects.values())
    return {"success": True, "projects": projects, "count": len(projects)}


@router.get("/projects/{project_id}")
async def get_project_details(project_id: str):
    """جزئیات پروژه"""
    engine = get_creator_engine()
    if not engine.project_creator:
        raise HTTPException(status_code=500, detail="Project creator not initialized")

    project = engine.project_creator.active_projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return {"success": True, "project": project}


@router.post("/projects/{project_id}/generate-file")
async def generate_project_file(project_id: str, request: GenerateFileRequest):
    """تولید یک فایل برای پروژه"""
    engine = get_creator_engine()
    if not engine.project_creator:
        raise HTTPException(status_code=500, detail="Project creator not initialized")

    result = await engine.project_creator.generate_file(
        project_id,
        request.file_path,
        request.description
    )

    return {
        "success": result.success,
        "file": result.output,
        "error": result.error
    }


@router.post("/projects/{project_id}/run")
async def run_project(project_id: str, command: Optional[str] = None):
    """اجرای پروژه"""
    engine = get_creator_engine()
    if not engine.project_creator:
        raise HTTPException(status_code=500, detail="Project creator not initialized")

    result = await engine.project_creator.run_project(project_id, command)

    return {
        "success": result.success,
        "output": result.output,
        "error": result.error
    }


# =====================================
# 📊 Workspace Info
# =====================================

@router.get("/workspace/info")
async def get_workspace_info():
    """اطلاعات workspace"""
    engine = get_creator_engine()

    return {
        "success": True,
        "workspace": str(engine.workspace_base),
        "command_history_count": len(engine.executor.history),
        "active_services": len(engine.connector.services),
        "active_agents": len(engine.ai_orchestrator.active_agents) if engine.ai_orchestrator else 0,
        "active_projects": len(engine.project_creator.active_projects) if engine.project_creator else 0,
        "tasks_count": len(engine.tasks)
    }


@router.get("/workspace/history")
async def get_command_history(limit: int = 50):
    """تاریخچه دستورات"""
    engine = get_creator_engine()
    history = engine.executor.history[-limit:]
    return {"success": True, "history": history, "count": len(history)}
