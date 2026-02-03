# -*- coding: utf-8 -*-
"""
API برای تحلیل و نمایش ساختار پروژه به صورت دیاگرام
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json
import uuid
import os
import re

from ...core.database import get_db
from ...models.project import Project

router = APIRouter()


# ===================== مدل‌های داده =====================

class DiagramNode(BaseModel):
    """نود در دیاگرام"""
    id: str
    type: str  # file, folder, component, function, class, api, database, etc.
    label: str
    description: Optional[str] = None
    position: Dict[str, float]  # {x: number, y: number}
    data: Optional[Dict[str, Any]] = None
    style: Optional[Dict[str, Any]] = None
    is_active: bool = False  # برای نمایش زنده


class DiagramEdge(BaseModel):
    """اتصال بین نودها"""
    id: str
    source: str
    target: str
    label: Optional[str] = None
    type: str = "default"  # default, animated, step
    style: Optional[Dict[str, Any]] = None
    animated: bool = False  # برای نمایش جریان زنده


class ProjectStructure(BaseModel):
    """ساختار کامل پروژه"""
    nodes: List[DiagramNode]
    edges: List[DiagramEdge]
    metadata: Optional[Dict[str, Any]] = None


class StructureAnalysisSettings(BaseModel):
    """تنظیمات تحلیل ساختار"""
    instruction: str = "تمام پروژه را از ریز تا درشت بررسی کن و ساختار کامل آن را استخراج کن"
    target_models: List[str] = ["all"]
    trigger_enabled: bool = True
    trigger_interval_minutes: int = 30
    trigger_interval_type: str = "minutes"
    last_analysis: Optional[str] = None
    next_analysis: Optional[str] = None
    auto_analyze_on_import: bool = True


# ===================== توابع کمکی =====================

def get_file_type_icon(filename: str) -> str:
    """آیکون مناسب برای نوع فایل"""
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    icons = {
        'py': '🐍',
        'js': '📜',
        'ts': '💠',
        'tsx': '⚛️',
        'jsx': '⚛️',
        'html': '🌐',
        'css': '🎨',
        'scss': '🎨',
        'json': '📋',
        'md': '📝',
        'yaml': '⚙️',
        'yml': '⚙️',
        'sql': '🗃️',
        'dockerfile': '🐳',
        'env': '🔒',
        'txt': '📄',
        'sh': '💻',
        'go': '🔵',
        'rs': '🦀',
        'java': '☕',
        'cpp': '⚡',
        'c': '⚡',
    }
    return icons.get(ext, '📄')


def get_node_color(node_type: str) -> str:
    """رنگ مناسب برای نوع نود"""
    colors = {
        'folder': '#6366f1',  # indigo
        'file': '#10b981',  # emerald
        'component': '#f59e0b',  # amber
        'function': '#3b82f6',  # blue
        'class': '#8b5cf6',  # violet
        'api': '#ef4444',  # red
        'database': '#06b6d4',  # cyan
        'service': '#ec4899',  # pink
        'config': '#6b7280',  # gray
        'test': '#84cc16',  # lime
        'entry': '#22c55e',  # green
    }
    return colors.get(node_type, '#9ca3af')


def analyze_file_content(content: str, filename: str) -> Dict[str, Any]:
    """تحلیل محتوای فایل برای استخراج ساختار"""
    analysis = {
        'functions': [],
        'classes': [],
        'imports': [],
        'exports': [],
        'components': [],
        'apis': [],
    }

    ext = filename.split('.')[-1].lower() if '.' in filename else ''

    # تحلیل Python
    if ext == 'py':
        # توابع
        func_pattern = r'def\s+(\w+)\s*\('
        analysis['functions'] = re.findall(func_pattern, content)

        # کلاس‌ها
        class_pattern = r'class\s+(\w+)\s*[:\(]'
        analysis['classes'] = re.findall(class_pattern, content)

        # import‌ها
        import_pattern = r'(?:from\s+[\w.]+\s+)?import\s+([\w,\s]+)'
        analysis['imports'] = re.findall(import_pattern, content)

        # API endpoints (FastAPI)
        api_pattern = r'@(?:router|app)\.(?:get|post|put|delete|patch)\s*\(["\']([^"\']+)'
        analysis['apis'] = re.findall(api_pattern, content)

    # تحلیل JavaScript/TypeScript
    elif ext in ['js', 'ts', 'jsx', 'tsx']:
        # توابع
        func_patterns = [
            r'function\s+(\w+)\s*\(',
            r'const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>',
            r'const\s+(\w+)\s*=\s*(?:async\s*)?function',
        ]
        for pattern in func_patterns:
            analysis['functions'].extend(re.findall(pattern, content))

        # کلاس‌ها و کامپوننت‌ها
        class_pattern = r'class\s+(\w+)\s*(?:extends|implements|{)'
        analysis['classes'] = re.findall(class_pattern, content)

        # React Components
        component_pattern = r'(?:export\s+)?(?:default\s+)?(?:function|const)\s+([A-Z]\w+)'
        analysis['components'] = re.findall(component_pattern, content)

        # API routes (Next.js, Express)
        api_patterns = [
            r'(?:router|app)\.(?:get|post|put|delete|patch)\s*\(["\']([^"\']+)',
            r'export\s+(?:async\s+)?function\s+(?:GET|POST|PUT|DELETE|PATCH)',
        ]
        for pattern in api_patterns:
            analysis['apis'].extend(re.findall(pattern, content))

    return analysis


def build_project_diagram(project: Project, files: List[Dict]) -> ProjectStructure:
    """ساخت دیاگرام از ساختار پروژه"""
    nodes = []
    edges = []
    folder_positions = {}

    # نود اصلی پروژه
    root_node = DiagramNode(
        id="root",
        type="entry",
        label=f"🚀 {project.name}",
        description=project.description,
        position={"x": 400, "y": 50},
        data={"project_id": project.id},
        style={"background": get_node_color('entry'), "color": "white", "fontWeight": "bold"}
    )
    nodes.append(root_node)

    # گروه‌بندی فایل‌ها بر اساس پوشه
    folders = {}
    root_files = []

    for f in files:
        path = f.get('path', '')
        parts = path.split('/')

        if len(parts) > 1:
            folder = parts[0]
            if folder not in folders:
                folders[folder] = []
            folders[folder].append(f)
        else:
            root_files.append(f)

    y_offset = 150
    x_offset = 50

    # پردازش فایل‌های ریشه
    for idx, f in enumerate(root_files[:10]):  # حداکثر 10 فایل ریشه
        filename = f.get('path', 'unknown')
        icon = get_file_type_icon(filename)

        node = DiagramNode(
            id=f"file_{filename.replace('/', '_').replace('.', '_')}",
            type="file",
            label=f"{icon} {filename}",
            position={"x": x_offset + (idx % 5) * 180, "y": y_offset},
            data={"path": filename, "size": f.get('size', 0)},
            style={"background": get_node_color('file'), "color": "white"}
        )
        nodes.append(node)

        # اتصال به ریشه
        edge = DiagramEdge(
            id=f"edge_root_{node.id}",
            source="root",
            target=node.id,
            type="smoothstep"
        )
        edges.append(edge)

    y_offset += 120

    # پردازش پوشه‌ها
    folder_idx = 0
    for folder_name, folder_files in list(folders.items())[:8]:  # حداکثر 8 پوشه
        folder_x = 100 + (folder_idx % 4) * 220
        folder_y = y_offset + (folder_idx // 4) * 300

        # نود پوشه
        folder_node = DiagramNode(
            id=f"folder_{folder_name}",
            type="folder",
            label=f"📁 {folder_name}",
            position={"x": folder_x, "y": folder_y},
            data={"file_count": len(folder_files)},
            style={"background": get_node_color('folder'), "color": "white", "fontWeight": "bold"}
        )
        nodes.append(folder_node)
        folder_positions[folder_name] = {"x": folder_x, "y": folder_y}

        # اتصال پوشه به ریشه
        edge = DiagramEdge(
            id=f"edge_root_{folder_node.id}",
            source="root",
            target=folder_node.id,
            type="smoothstep",
            animated=True
        )
        edges.append(edge)

        # فایل‌های داخل پوشه
        for file_idx, f in enumerate(folder_files[:6]):  # حداکثر 6 فایل در هر پوشه
            filepath = f.get('path', '')
            filename = filepath.split('/')[-1]
            icon = get_file_type_icon(filename)

            file_x = folder_x - 80 + (file_idx % 3) * 100
            file_y = folder_y + 80 + (file_idx // 3) * 60

            file_node = DiagramNode(
                id=f"file_{filepath.replace('/', '_').replace('.', '_')}",
                type="file",
                label=f"{icon} {filename}",
                position={"x": file_x, "y": file_y},
                data={"path": filepath, "size": f.get('size', 0)},
                style={"background": get_node_color('file'), "color": "white", "fontSize": "12px"}
            )
            nodes.append(file_node)

            # اتصال فایل به پوشه
            file_edge = DiagramEdge(
                id=f"edge_{folder_node.id}_{file_node.id}",
                source=folder_node.id,
                target=file_node.id,
                type="smoothstep"
            )
            edges.append(file_edge)

        folder_idx += 1

    # متادیتا
    metadata = {
        "total_files": len(files),
        "total_folders": len(folders),
        "analyzed_at": datetime.utcnow().isoformat(),
        "project_type": project.project_type,
    }

    return ProjectStructure(nodes=nodes, edges=edges, metadata=metadata)


def get_structure_settings(project: Project) -> StructureAnalysisSettings:
    """دریافت تنظیمات تحلیل ساختار"""
    try:
        extra = json.loads(project.extra_data) if project.extra_data else {}
        settings_data = extra.get('structure_settings', {})
        return StructureAnalysisSettings(**settings_data)
    except Exception:
        return StructureAnalysisSettings()


def save_structure_settings(db: Session, project: Project, settings: StructureAnalysisSettings):
    """ذخیره تنظیمات تحلیل ساختار"""
    try:
        extra = json.loads(project.extra_data) if project.extra_data else {}
    except Exception:
        extra = {}

    extra['structure_settings'] = settings.dict()
    project.extra_data = json.dumps(extra)
    db.commit()


def get_cached_structure(project: Project) -> Optional[ProjectStructure]:
    """دریافت ساختار کش شده"""
    try:
        extra = json.loads(project.extra_data) if project.extra_data else {}
        cached = extra.get('cached_structure')
        if cached:
            return ProjectStructure(**cached)
    except Exception:
        pass
    return None


def save_cached_structure(db: Session, project: Project, structure: ProjectStructure):
    """ذخیره ساختار در کش"""
    try:
        extra = json.loads(project.extra_data) if project.extra_data else {}
    except Exception:
        extra = {}

    extra['cached_structure'] = structure.dict()
    project.extra_data = json.dumps(extra)
    db.commit()


# ===================== API Endpoints =====================

@router.get("/{project_id}/structure")
async def get_project_structure(project_id: str, db: Session = Depends(get_db)):
    """دریافت ساختار دیاگرامی پروژه"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # دریافت تنظیمات
    settings = get_structure_settings(project)

    # بررسی کش
    cached = get_cached_structure(project)

    # دریافت فایل‌ها
    files = []
    try:
        if project.structure:
            structure_data = json.loads(project.structure) if isinstance(project.structure, str) else project.structure
            files = structure_data.get('files', [])
            if not files:
                files = structure_data.get('file_tree', [])
    except Exception:
        pass

    # اگر کش نداریم یا فایل‌ها تغییر کرده، دیاگرام جدید بساز
    if not cached or not cached.nodes:
        structure = build_project_diagram(project, files)
        save_cached_structure(db, project, structure)
    else:
        structure = cached

    return {
        "success": True,
        "structure": structure.dict(),
        "settings": settings.dict(),
        "file_count": len(files),
    }


@router.post("/{project_id}/structure/analyze")
async def analyze_project_structure(project_id: str, db: Session = Depends(get_db)):
    """تحلیل مجدد ساختار پروژه"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # دریافت فایل‌ها
    files = []
    try:
        if project.structure:
            structure_data = json.loads(project.structure) if isinstance(project.structure, str) else project.structure
            files = structure_data.get('files', [])
            if not files:
                files = structure_data.get('file_tree', [])
    except Exception:
        pass

    # ساخت دیاگرام جدید
    structure = build_project_diagram(project, files)
    save_cached_structure(db, project, structure)

    # بروزرسانی تنظیمات
    settings = get_structure_settings(project)
    settings.last_analysis = datetime.utcnow().isoformat()

    # محاسبه زمان تحلیل بعدی
    if settings.trigger_enabled:
        if settings.trigger_interval_type == "minutes":
            next_time = datetime.utcnow() + timedelta(minutes=settings.trigger_interval_minutes)
        elif settings.trigger_interval_type == "hours":
            next_time = datetime.utcnow() + timedelta(hours=settings.trigger_interval_minutes)
        else:
            next_time = datetime.utcnow() + timedelta(days=settings.trigger_interval_minutes)
        settings.next_analysis = next_time.isoformat()

    save_structure_settings(db, project, settings)

    return {
        "success": True,
        "message": "ساختار پروژه با موفقیت تحلیل شد",
        "structure": structure.dict(),
        "settings": settings.dict(),
    }


@router.put("/{project_id}/structure/settings")
async def update_structure_settings(
    project_id: str,
    settings: StructureAnalysisSettings,
    db: Session = Depends(get_db)
):
    """بروزرسانی تنظیمات تحلیل ساختار"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # محاسبه زمان تحلیل بعدی
    if settings.trigger_enabled:
        if settings.trigger_interval_type == "minutes":
            next_time = datetime.utcnow() + timedelta(minutes=settings.trigger_interval_minutes)
        elif settings.trigger_interval_type == "hours":
            next_time = datetime.utcnow() + timedelta(hours=settings.trigger_interval_minutes)
        else:
            next_time = datetime.utcnow() + timedelta(days=settings.trigger_interval_minutes)
        settings.next_analysis = next_time.isoformat()

    save_structure_settings(db, project, settings)

    return {
        "success": True,
        "message": "تنظیمات ذخیره شد",
        "settings": settings.dict(),
    }


@router.post("/{project_id}/structure/node/{node_id}/activate")
async def activate_node(project_id: str, node_id: str, active: bool = True, db: Session = Depends(get_db)):
    """فعال/غیرفعال کردن یک نود (برای نمایش زنده)"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    cached = get_cached_structure(project)
    if not cached:
        raise HTTPException(status_code=404, detail="ساختار یافت نشد")

    # بروزرسانی وضعیت نود
    for node in cached.nodes:
        if node.id == node_id:
            node.is_active = active
            break

    # بروزرسانی انیمیشن اتصالات مرتبط
    for edge in cached.edges:
        if edge.source == node_id or edge.target == node_id:
            edge.animated = active

    save_cached_structure(db, project, cached)

    return {
        "success": True,
        "message": f"نود {'فعال' if active else 'غیرفعال'} شد",
    }


@router.get("/{project_id}/structure/live")
async def get_live_status(project_id: str, db: Session = Depends(get_db)):
    """دریافت وضعیت زنده پروژه"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    cached = get_cached_structure(project)

    # 🔴 FIX: اگر کش نداریم، دیاگرام جدید بساز
    if not cached or not cached.nodes:
        files = []
        try:
            if project.structure:
                structure_data = json.loads(project.structure) if isinstance(project.structure, str) else project.structure
                files = structure_data.get('files', [])
                if not files:
                    files = structure_data.get('file_tree', [])
        except Exception:
            pass

        if files:
            cached = build_project_diagram(project, files)
            save_cached_structure(db, project, cached)
        else:
            return {"success": True, "active_nodes": [], "animated_edges": [], "message": "فایلی برای نمایش وجود ندارد"}

    active_nodes = [n.id for n in cached.nodes if n.is_active]
    animated_edges = [e.id for e in cached.edges if e.animated]

    return {
        "success": True,
        "active_nodes": active_nodes,
        "animated_edges": animated_edges,
        "total_nodes": len(cached.nodes),
        "total_edges": len(cached.edges),
    }
