"""
API routes for Diagram Generation
مسیرهای API برای تولید نمودار
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from ...services.diagram_service import get_diagram_service, DiagramType

router = APIRouter(prefix="/diagrams", tags=["Diagrams"])


# =====================================
# مدل‌های درخواست
# =====================================

class ArchitectureRequest(BaseModel):
    components: List[Dict] = []
    connections: List[Dict] = []


class ClassDiagramRequest(BaseModel):
    classes: List[Dict]


class SequenceRequest(BaseModel):
    participants: List[str]
    messages: List[Dict]


class GanttRequest(BaseModel):
    title: str
    tasks: List[Dict]


class ERDiagramRequest(BaseModel):
    entities: List[Dict]


class MindmapRequest(BaseModel):
    root: str
    nodes: List[Dict]


class PieChartRequest(BaseModel):
    title: str
    data: Dict[str, float]


class StateRequest(BaseModel):
    states: List[Dict]
    transitions: List[Dict]


class CodeAnalysisRequest(BaseModel):
    code: str
    language: str = "python"


# =====================================
# نمودارها
# =====================================

@router.get("/types")
async def get_diagram_types():
    """لیست انواع نمودار"""
    return {
        "success": True,
        "types": [
            {"id": "flowchart", "name": "نمودار جریان", "icon": "📊"},
            {"id": "sequence", "name": "نمودار توالی", "icon": "📋"},
            {"id": "class", "name": "نمودار کلاس", "icon": "🏗️"},
            {"id": "state", "name": "نمودار وضعیت", "icon": "🔄"},
            {"id": "er", "name": "نمودار ER", "icon": "🗄️"},
            {"id": "gantt", "name": "نمودار Gantt", "icon": "📅"},
            {"id": "pie", "name": "نمودار دایره‌ای", "icon": "🥧"},
            {"id": "mindmap", "name": "نقشه ذهنی", "icon": "🧠"},
            {"id": "architecture", "name": "نمودار معماری", "icon": "🏛️"},
        ]
    }


@router.post("/architecture")
async def generate_architecture(request: ArchitectureRequest):
    """تولید نمودار معماری"""
    service = get_diagram_service()
    diagram = service.generate_architecture_diagram(
        components=request.components,
        connections=request.connections
    )
    return {"success": True, "mermaid": diagram, "type": "architecture"}


@router.post("/class")
async def generate_class_diagram(request: ClassDiagramRequest):
    """تولید نمودار کلاس"""
    service = get_diagram_service()
    diagram = service.generate_class_diagram(request.classes)
    return {"success": True, "mermaid": diagram, "type": "class"}


@router.post("/sequence")
async def generate_sequence_diagram(request: SequenceRequest):
    """تولید نمودار توالی"""
    service = get_diagram_service()
    diagram = service.generate_sequence_diagram(
        participants=request.participants,
        messages=request.messages
    )
    return {"success": True, "mermaid": diagram, "type": "sequence"}


@router.post("/gantt")
async def generate_gantt_chart(request: GanttRequest):
    """تولید نمودار Gantt"""
    service = get_diagram_service()
    diagram = service.generate_gantt_chart(
        title=request.title,
        tasks=request.tasks
    )
    return {"success": True, "mermaid": diagram, "type": "gantt"}


@router.post("/er")
async def generate_er_diagram(request: ERDiagramRequest):
    """تولید نمودار ER"""
    service = get_diagram_service()
    diagram = service.generate_er_diagram(request.entities)
    return {"success": True, "mermaid": diagram, "type": "er"}


@router.post("/mindmap")
async def generate_mindmap(request: MindmapRequest):
    """تولید نقشه ذهنی"""
    service = get_diagram_service()
    diagram = service.generate_mindmap(
        root=request.root,
        nodes=request.nodes
    )
    return {"success": True, "mermaid": diagram, "type": "mindmap"}


@router.post("/pie")
async def generate_pie_chart(request: PieChartRequest):
    """تولید نمودار دایره‌ای"""
    service = get_diagram_service()
    diagram = service.generate_pie_chart(
        title=request.title,
        data=request.data
    )
    return {"success": True, "mermaid": diagram, "type": "pie"}


@router.post("/state")
async def generate_state_diagram(request: StateRequest):
    """تولید نمودار وضعیت"""
    service = get_diagram_service()
    diagram = service.generate_state_diagram(
        states=request.states,
        transitions=request.transitions
    )
    return {"success": True, "mermaid": diagram, "type": "state"}


# =====================================
# تحلیل کد
# =====================================

@router.post("/analyze-code")
async def analyze_code(request: CodeAnalysisRequest):
    """تحلیل کد و تولید نمودار کلاس"""
    service = get_diagram_service()
    analysis = service.analyze_code_structure(
        code=request.code,
        language=request.language
    )
    class_diagram = service.code_to_class_diagram(
        code=request.code,
        language=request.language
    )

    return {
        "success": True,
        "analysis": analysis,
        "class_diagram": class_diagram
    }


# =====================================
# نمونه نمودارها
# =====================================

@router.get("/examples/{diagram_type}")
async def get_diagram_example(diagram_type: str):
    """دریافت نمونه نمودار"""
    service = get_diagram_service()

    examples = {
        "flowchart": """flowchart TB
    A[شروع] --> B{تصمیم‌گیری}
    B -->|بله| C[انجام کار]
    B -->|خیر| D[پایان]
    C --> D""",

        "sequence": """sequenceDiagram
    participant کاربر
    participant سرور
    participant دیتابیس
    کاربر->>سرور: درخواست
    سرور->>دیتابیس: کوئری
    دیتابیس-->>سرور: نتیجه
    سرور-->>کاربر: پاسخ""",

        "class": """classDiagram
    class User {
        +string name
        +string email
        +login()
        +logout()
    }
    class Product {
        +string title
        +float price
        +getDetails()
    }
    User --> Product : buys""",

        "gantt": """gantt
    title برنامه پروژه
    dateFormat YYYY-MM-DD
    section فاز ۱
    طراحی: done, a1, 2024-01-01, 7d
    توسعه: active, a2, after a1, 14d
    section فاز ۲
    تست: a3, after a2, 7d
    استقرار: a4, after a3, 3d""",

        "mindmap": """mindmap
    root((پروژه))
        Backend
            API
            Database
            Auth
        Frontend
            UI
            State
            Routing
        DevOps
            CI/CD
            Monitoring"""
    }

    if diagram_type not in examples:
        raise HTTPException(status_code=404, detail="نوع نمودار یافت نشد")

    return {
        "success": True,
        "diagram_type": diagram_type,
        "mermaid": examples[diagram_type]
    }


# =====================================
# اتصال خودکار به پروژه‌ها
# =====================================

@router.get("/projects")
async def list_diagram_projects():
    """لیست پروژه‌های قابل دسترس برای رسم خودکار نمودار."""
    items = []

    # پروژه‌های محلی (simple_creator)
    try:
        from ...services.simple_creator import get_simple_creator
        creator = get_simple_creator()
        for p in creator.list_projects():
            items.append({
                "source": "local",
                "id": p.id,
                "name": p.name,
                "description": p.description or "",
                "language": p.project_type or "",
                "files_count": len(p.files) if hasattr(p, "files") and p.files else 0,
            })
    except Exception:
        pass

    # پروژه‌های تحت نظارت (oversight)
    try:
        from ...services.oversight_service import get_oversight_service
        ov = get_oversight_service()
        for w in ov.watched:
            items.append({
                "source": "github",
                "id": w.id,
                "name": w.repo_full_name,
                "description": w.user_notes or "",
                "language": w.language or "",
                "url": w.repo_url,
            })
    except Exception:
        pass

    return {"success": True, "items": items, "count": len(items)}


class AutoDiagramRequest(BaseModel):
    source: str  # 'local' | 'github'
    id: str  # local project id, OR oversight watched_id, OR a "owner/repo" string
    diagram_type: str = "tree"  # tree | class | architecture | flowchart
    model_id: Optional[str] = None
    max_files: int = 60


def _build_tree_mermaid(paths: List[str], root_label: str = "/", max_nodes: int = 80) -> str:
    """ساخت Mermaid flowchart از لیست path فایل‌ها."""
    paths = [p for p in paths if p][:max_nodes]
    lines = ["flowchart LR", f"  ROOT[/{root_label}/]"]
    seen: Dict[str, str] = {"": "ROOT"}
    counter = 0

    def _node_id() -> str:
        nonlocal counter
        counter += 1
        return f"N{counter}"

    for p in paths:
        parts = [s for s in p.split("/") if s]
        parent_key = ""
        for i, part in enumerate(parts):
            current_key = "/".join(parts[: i + 1])
            if current_key not in seen:
                node_id = _node_id()
                seen[current_key] = node_id
                # برچسب: فایل/پوشه
                is_file = (i == len(parts) - 1) and ("." in part)
                label = part.replace('"', "'")
                if is_file:
                    lines.append(f'  {node_id}["📄 {label}"]')
                else:
                    lines.append(f'  {node_id}[["📁 {label}"]]')
                lines.append(f"  {seen[parent_key]} --> {node_id}")
            parent_key = current_key

    return "\n".join(lines)


async def _get_project_payload(source: str, id_: str) -> Dict[str, Any]:
    """دریافت اطلاعات پروژه از منبع مناسب."""
    payload: Dict[str, Any] = {"name": "", "description": "", "language": "", "files": [], "package_files": {}, "readme": ""}

    if source == "local":
        from ...services.simple_creator import get_simple_creator
        creator = get_simple_creator()
        project = creator.get_project(id_)
        if not project:
            raise HTTPException(status_code=404, detail="پروژه محلی یافت نشد")

        payload["name"] = project.name
        payload["description"] = project.description or ""
        payload["language"] = project.project_type or ""

        try:
            files = await creator.get_project_files(id_)
            payload["files"] = [f.get("path") for f in files if f.get("path")][:300]
        except Exception:
            payload["files"] = [getattr(f, "path", None) for f in (project.files or []) if getattr(f, "path", None)][:300]

        # خواندن فایل‌های package برای architecture
        for fname in ("package.json", "requirements.txt", "pyproject.toml"):
            try:
                content = await creator.get_file_content(id_, fname)
                if content:
                    payload["package_files"][fname] = content[:5000]
            except Exception:
                pass

        try:
            readme = await creator.get_file_content(id_, "README.md")
            if readme:
                payload["readme"] = readme[:6000]
        except Exception:
            pass

        return payload

    if source == "github":
        from ...services.oversight_service import get_oversight_service
        ov = get_oversight_service()

        # id ممکن است watched_id یا "owner/repo" باشد
        watched = next((w for w in ov.watched if w.id == id_), None)
        repo_full_name = watched.repo_full_name if watched else id_

        if "/" not in repo_full_name:
            raise HTTPException(status_code=400, detail="نام مخزن باید به‌شکل owner/repo باشد")

        ctx = await ov.build_project_context(repo_full_name)
        payload["name"] = repo_full_name
        payload["description"] = ctx.get("description") or ""
        payload["language"] = ctx.get("language") or ""
        payload["files"] = ctx.get("files_sample") or []
        payload["package_files"] = ctx.get("package_files") or {}
        payload["readme"] = ctx.get("readme") or ""
        return payload

    raise HTTPException(status_code=400, detail="منبع نامعتبر است (باید local یا github باشد)")


@router.post("/auto-from-project")
async def auto_diagram_from_project(request: AutoDiagramRequest):
    """رسم خودکار نمودار از یک پروژه (محلی یا GitHub)."""
    payload = await _get_project_payload(request.source, request.id)
    diagram_type = (request.diagram_type or "tree").lower()

    # نوع tree: بدون AI، مستقیم از path‌ها
    if diagram_type == "tree":
        if not payload["files"]:
            raise HTTPException(status_code=400, detail="فایلی برای رسم درخت نیست")
        mermaid = _build_tree_mermaid(payload["files"], root_label=payload["name"][:40] or "/", max_nodes=request.max_files)
        return {
            "success": True,
            "mermaid": mermaid,
            "type": "flowchart",
            "project_name": payload["name"],
        }

    # سایر انواع: نیاز به AI داریم
    from ...services.oversight_service import get_oversight_service
    ov = get_oversight_service()

    files_summary = "\n".join(payload["files"][:60])
    pkg_summary = ""
    for fname, content in payload["package_files"].items():
        pkg_summary += f"\n=== {fname} ===\n{content[:2500]}"

    if diagram_type == "class":
        prompt = f"""تو یک معمار نرم‌افزار هستی. بر اساس ساختار این پروژه یک نمودار کلاس Mermaid بساز.

# پروژه
{payload['name']}
زبان: {payload['language']}
{payload['description'][:500]}

# فایل‌ها
{files_summary}

# README (بخشی)
{payload['readme'][:2500]}

# خروجی
فقط کد Mermaid معتبر برگردان (بدون ```mermaid... و بدون توضیح اضافی). با classDiagram شروع کن.
حداکثر ۱۰ کلاس اصلی را بگنجان با ارتباطات بینشان."""
    elif diagram_type == "architecture":
        prompt = f"""تو یک معمار نرم‌افزار هستی. بر اساس این پروژه یک نمودار معماری Mermaid (flowchart LR) بساز که اجزای اصلی و ارتباطشان را نشان دهد.

# پروژه
{payload['name']}
زبان: {payload['language']}
{payload['description'][:500]}

# فایل‌های وابستگی
{pkg_summary[:3000]}

# نمونه فایل‌ها
{files_summary}

# README
{payload['readme'][:2000]}

# خروجی
فقط کد Mermaid معتبر برگردان (با flowchart LR شروع کن). اجزایی مثل API، Database، Frontend، External services را با اتصالات نشان بده."""
    elif diagram_type == "flowchart":
        prompt = f"""تو یک تحلیلگر نرم‌افزار هستی. بر اساس این پروژه یک flowchart از مسیر اصلی اجرا (entry point → main flow) بساز.

# پروژه
{payload['name']}
زبان: {payload['language']}
{payload['description'][:500]}

# فایل‌ها
{files_summary}

# README
{payload['readme'][:2500]}

# خروجی
فقط کد Mermaid معتبر برگردان. با `flowchart TD` شروع کن. حداکثر ۱۲ نود."""
    elif diagram_type == "sequence":
        prompt = f"""تو یک معمار نرم‌افزار هستی. بر اساس این پروژه یک sequenceDiagram از مسیر اصلی request/response بساز.

# پروژه
{payload['name']}
{payload['description'][:500]}

# README
{payload['readme'][:3000]}

# فایل‌ها
{files_summary}

# خروجی
فقط کد Mermaid معتبر برگردان (با sequenceDiagram شروع کن)."""
    else:
        raise HTTPException(status_code=400, detail=f"نوع نمودار '{diagram_type}' پشتیبانی نمی‌شود")

    try:
        response = await ov._ai_generate(
            prompt,
            model_id=request.model_id,
            max_tokens=2500,
            temperature=0.3,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در تولید با AI: {e}")

    # تمیزکاری ```mermaid... ```
    cleaned = response.strip()
    if cleaned.startswith("```"):
        # حذف اولین خط ```... و آخرین خط ```
        cleaned = cleaned.split("\n", 1)[-1]
        if "```" in cleaned:
            cleaned = cleaned.rsplit("```", 1)[0]
    cleaned = cleaned.strip()

    return {
        "success": True,
        "mermaid": cleaned,
        "type": diagram_type,
        "project_name": payload["name"],
        "raw_response": response[:4000],
    }
