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
