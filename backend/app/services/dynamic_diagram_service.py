"""
📊 Dynamic Diagram Service - سرویس نمودار داینامیک
تولید خودکار نمودارهای Mermaid از کد پروژه
"""

import os
import re
import ast
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class DiagramInfo:
    """اطلاعات یک نمودار"""
    id: str
    name: str
    type: str  # flowchart, class, sequence, er, state, mindmap
    content: str  # محتوای Mermaid
    source_files: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    auto_generated: bool = True


class CodeAnalyzer:
    """
    تحلیل‌گر کد برای استخراج ساختار
    """

    @staticmethod
    def analyze_python_file(content: str, file_path: str) -> Dict:
        """تحلیل فایل پایتون"""
        result = {
            "classes": [],
            "functions": [],
            "imports": [],
            "variables": [],
            "calls": []
        }

        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                # کلاس‌ها
                if isinstance(node, ast.ClassDef):
                    class_info = {
                        "name": node.name,
                        "bases": [b.id if isinstance(b, ast.Name) else str(b) for b in node.bases],
                        "methods": [],
                        "attributes": []
                    }

                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_info = {
                                "name": item.name,
                                "args": [a.arg for a in item.args.args if a.arg != 'self'],
                                "returns": ast.unparse(item.returns) if item.returns else None,
                                "is_async": isinstance(item, ast.AsyncFunctionDef)
                            }
                            class_info["methods"].append(method_info)

                        elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                            class_info["attributes"].append({
                                "name": item.target.id,
                                "type": ast.unparse(item.annotation) if item.annotation else None
                            })

                    result["classes"].append(class_info)

                # توابع (نه متدها)
                elif isinstance(node, ast.FunctionDef) and not isinstance(node, ast.AsyncFunctionDef):
                    if not any(c for c in result["classes"] if node.name in [m["name"] for m in c.get("methods", [])]):
                        result["functions"].append({
                            "name": node.name,
                            "args": [a.arg for a in node.args.args],
                            "returns": ast.unparse(node.returns) if node.returns else None
                        })

                # Imports
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        result["imports"].append(alias.name)

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        result["imports"].append(node.module)

        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")

        return result

    @staticmethod
    def analyze_javascript_file(content: str, file_path: str) -> Dict:
        """تحلیل فایل JavaScript/TypeScript"""
        result = {
            "classes": [],
            "functions": [],
            "imports": [],
            "exports": [],
            "components": []  # برای React
        }

        # کلاس‌ها
        class_pattern = r'class\s+(\w+)(?:\s+extends\s+(\w+))?\s*\{'
        for match in re.finditer(class_pattern, content):
            result["classes"].append({
                "name": match.group(1),
                "bases": [match.group(2)] if match.group(2) else [],
                "methods": []
            })

        # توابع
        func_patterns = [
            r'function\s+(\w+)\s*\([^)]*\)',
            r'const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>',
            r'const\s+(\w+)\s*=\s*(?:async\s*)?function',
        ]

        for pattern in func_patterns:
            for match in re.finditer(pattern, content):
                func_name = match.group(1)
                if func_name not in [f["name"] for f in result["functions"]]:
                    result["functions"].append({"name": func_name, "args": []})

        # Imports
        import_pattern = r'import\s+(?:{[^}]+}|\w+)\s+from\s+[\'"]([^\'"]+)[\'"]'
        for match in re.finditer(import_pattern, content):
            result["imports"].append(match.group(1))

        # React Components
        component_pattern = r'(?:export\s+)?(?:default\s+)?(?:function|const)\s+(\w+)\s*[=\(].*?(?:return|=>)\s*\(?[\s\n]*<'
        for match in re.finditer(component_pattern, content, re.MULTILINE | re.DOTALL):
            result["components"].append({"name": match.group(1)})

        return result


class DynamicDiagramService:
    """
    سرویس تولید نمودار داینامیک

    قابلیت‌ها:
    1. تحلیل کد و استخراج ساختار
    2. تولید نمودار کلاس (Class Diagram)
    3. تولید نمودار جریان (Flowchart)
    4. تولید نمودار توالی (Sequence)
    5. تولید نمودار ER (Entity Relationship)
    6. تولید نقشه ذهنی (Mind Map)
    7. تولید نمودار وضعیت (State Diagram)
    8. بروزرسانی خودکار نمودارها
    """

    def __init__(self, storage_service=None):
        self.storage = storage_service
        self.analyzer = CodeAnalyzer()
        self._diagrams_cache: Dict[str, List[DiagramInfo]] = {}

    async def analyze_project(self, project_id: str, project_path: Path) -> Dict:
        """تحلیل کامل پروژه"""
        result = {
            "classes": [],
            "functions": [],
            "imports": [],
            "components": [],
            "files_analyzed": 0,
            "languages": set()
        }

        if not project_path.exists():
            return result

        for file_path in project_path.rglob("*"):
            if file_path.is_file():
                ext = file_path.suffix.lower()

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except:
                    continue

                if ext == '.py':
                    analysis = self.analyzer.analyze_python_file(content, str(file_path))
                    result["languages"].add("python")

                elif ext in ['.js', '.jsx', '.ts', '.tsx']:
                    analysis = self.analyzer.analyze_javascript_file(content, str(file_path))
                    result["languages"].add("javascript" if ext in ['.js', '.jsx'] else "typescript")

                else:
                    continue

                # ادغام نتایج
                for cls in analysis.get("classes", []):
                    cls["file"] = str(file_path.relative_to(project_path))
                    result["classes"].append(cls)

                for func in analysis.get("functions", []):
                    func["file"] = str(file_path.relative_to(project_path))
                    result["functions"].append(func)

                result["imports"].extend(analysis.get("imports", []))
                result["components"].extend(analysis.get("components", []))
                result["files_analyzed"] += 1

        result["languages"] = list(result["languages"])
        return result

    def generate_class_diagram(self, analysis: Dict, project_name: str = "Project") -> str:
        """تولید نمودار کلاس از تحلیل"""
        lines = ["classDiagram"]

        classes = analysis.get("classes", [])

        if not classes:
            # اگر کلاسی نداریم، از توابع استفاده کنیم
            lines.append(f"    class {project_name} {{")
            for func in analysis.get("functions", [])[:10]:
                args = ", ".join(func.get("args", [])[:3])
                lines.append(f"        +{func['name']}({args})")
            lines.append("    }")
            return "\n".join(lines)

        # کلاس‌ها
        for cls in classes:
            class_name = cls["name"].replace(" ", "_")
            lines.append(f"    class {class_name} {{")

            # attributes
            for attr in cls.get("attributes", [])[:5]:
                attr_type = attr.get("type", "any")
                lines.append(f"        +{attr['name']}: {attr_type}")

            # methods
            for method in cls.get("methods", [])[:8]:
                args = ", ".join(method.get("args", [])[:3])
                returns = method.get("returns", "void")
                prefix = "+" if not method["name"].startswith("_") else "-"
                lines.append(f"        {prefix}{method['name']}({args}): {returns}")

            lines.append("    }")

            # وراثت
            for base in cls.get("bases", []):
                if base and base not in ['object', 'Object']:
                    lines.append(f"    {base} <|-- {class_name}")

        return "\n".join(lines)

    def generate_flowchart(self, analysis: Dict, title: str = "Project Flow") -> str:
        """تولید نمودار جریان"""
        lines = ["flowchart TD"]

        # شروع
        lines.append("    Start([شروع]) --> Init")

        functions = analysis.get("functions", [])
        classes = analysis.get("classes", [])

        if classes:
            lines.append("    Init[Initialize] --> Classes")
            lines.append("    subgraph Classes[کلاس‌ها]")

            for i, cls in enumerate(classes[:6]):
                class_name = cls["name"].replace(" ", "_")
                if i == 0:
                    lines.append(f"        C{i}[{class_name}]")
                else:
                    lines.append(f"        C{i-1} --> C{i}[{class_name}]")

            lines.append("    end")
            lines.append("    Classes --> Process")

        elif functions:
            lines.append("    Init[Initialize] --> Functions")
            lines.append("    subgraph Functions[توابع]")

            for i, func in enumerate(functions[:8]):
                if i == 0:
                    lines.append(f"        F{i}[{func['name']}]")
                else:
                    lines.append(f"        F{i-1} --> F{i}[{func['name']}]")

            lines.append("    end")
            lines.append("    Functions --> Process")

        else:
            lines.append("    Init[Initialize] --> Process")

        lines.append("    Process[پردازش] --> Output")
        lines.append("    Output[خروجی] --> End([پایان])")

        return "\n".join(lines)

    def generate_sequence_diagram(self, analysis: Dict, scenario: str = "Main Flow") -> str:
        """تولید نمودار توالی"""
        lines = ["sequenceDiagram"]

        classes = analysis.get("classes", [])
        functions = analysis.get("functions", [])

        participants = []

        # شرکت‌کنندگان
        if classes:
            for cls in classes[:4]:
                participants.append(cls["name"])
                lines.append(f"    participant {cls['name']}")
        else:
            participants = ["Client", "Server", "Database"]
            for p in participants:
                lines.append(f"    participant {p}")

        # تعاملات
        if len(participants) >= 2:
            lines.append(f"    {participants[0]}->>+{participants[1]}: درخواست")
            lines.append(f"    {participants[1]}-->>-{participants[0]}: پاسخ")

            if len(participants) >= 3:
                lines.append(f"    {participants[1]}->>+{participants[2]}: query")
                lines.append(f"    {participants[2]}-->>-{participants[1]}: result")

        return "\n".join(lines)

    def generate_er_diagram(self, analysis: Dict) -> str:
        """تولید نمودار ER"""
        lines = ["erDiagram"]

        classes = analysis.get("classes", [])

        if not classes:
            # نمودار پیش‌فرض
            lines.append("    USER ||--o{ PROJECT : owns")
            lines.append("    PROJECT ||--|{ FILE : contains")
            lines.append("    USER {")
            lines.append("        int id PK")
            lines.append("        string name")
            lines.append("    }")
            lines.append("    PROJECT {")
            lines.append("        int id PK")
            lines.append("        string name")
            lines.append("        int user_id FK")
            lines.append("    }")
            return "\n".join(lines)

        # از کلاس‌ها entity بسازیم
        for cls in classes[:6]:
            entity_name = cls["name"].upper().replace(" ", "_")
            lines.append(f"    {entity_name} {{")

            for attr in cls.get("attributes", [])[:5]:
                attr_type = attr.get("type", "string")
                if attr_type in ['int', 'str', 'bool', 'float']:
                    attr_type = attr_type.replace('str', 'string')
                else:
                    attr_type = "string"
                lines.append(f"        {attr_type} {attr['name']}")

            lines.append("    }")

        # روابط بین entity ها
        for i, cls in enumerate(classes[:5]):
            for base in cls.get("bases", []):
                if base in [c["name"] for c in classes]:
                    lines.append(f"    {base.upper()} ||--o{{ {cls['name'].upper()} : extends")

        return "\n".join(lines)

    def generate_mindmap(self, analysis: Dict, project_name: str = "Project") -> str:
        """تولید نقشه ذهنی"""
        lines = ["mindmap"]
        lines.append(f"    root(({project_name}))")

        classes = analysis.get("classes", [])
        functions = analysis.get("functions", [])
        imports = analysis.get("imports", [])
        languages = analysis.get("languages", [])

        if languages:
            lines.append("        (Languages)")
            for lang in languages[:3]:
                lines.append(f"            [{lang}]")

        if classes:
            lines.append("        (Classes)")
            for cls in classes[:5]:
                lines.append(f"            [{cls['name']}]")
                for method in cls.get("methods", [])[:3]:
                    lines.append(f"                ({method['name']})")

        if functions:
            lines.append("        (Functions)")
            for func in functions[:6]:
                lines.append(f"            [{func['name']}]")

        if imports:
            lines.append("        (Dependencies)")
            unique_imports = list(set(imports))[:5]
            for imp in unique_imports:
                # فقط نام اصلی ماژول
                module_name = imp.split('.')[0]
                lines.append(f"            [{module_name}]")

        return "\n".join(lines)

    def generate_state_diagram(self, analysis: Dict) -> str:
        """تولید نمودار وضعیت"""
        lines = ["stateDiagram-v2"]

        # وضعیت‌های استاندارد یک پروژه
        states = [
            ("Idle", "بیکار"),
            ("Loading", "در حال بارگذاری"),
            ("Processing", "در حال پردازش"),
            ("Success", "موفق"),
            ("Error", "خطا")
        ]

        lines.append("    [*] --> Idle")

        for state, label in states:
            lines.append(f"    {state}: {label}")

        lines.append("    Idle --> Loading: شروع")
        lines.append("    Loading --> Processing: داده آماده")
        lines.append("    Processing --> Success: تکمیل")
        lines.append("    Processing --> Error: خطا")
        lines.append("    Success --> [*]")
        lines.append("    Error --> Idle: تلاش مجدد")

        return "\n".join(lines)

    async def generate_all_diagrams(
        self,
        project_id: str,
        project_path: Path,
        project_name: str = "Project"
    ) -> List[DiagramInfo]:
        """تولید همه نمودارها برای یک پروژه"""
        analysis = await self.analyze_project(project_id, project_path)

        diagrams = []
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # نمودار کلاس
        class_diagram = self.generate_class_diagram(analysis, project_name)
        diagrams.append(DiagramInfo(
            id=f"class_{timestamp}",
            name="Class Diagram",
            type="class",
            content=class_diagram,
            source_files=[f["file"] for f in analysis.get("classes", []) if "file" in f]
        ))

        # نمودار جریان
        flowchart = self.generate_flowchart(analysis, project_name)
        diagrams.append(DiagramInfo(
            id=f"flow_{timestamp}",
            name="Flowchart",
            type="flowchart",
            content=flowchart
        ))

        # نمودار توالی
        sequence = self.generate_sequence_diagram(analysis)
        diagrams.append(DiagramInfo(
            id=f"seq_{timestamp}",
            name="Sequence Diagram",
            type="sequence",
            content=sequence
        ))

        # نمودار ER
        er = self.generate_er_diagram(analysis)
        diagrams.append(DiagramInfo(
            id=f"er_{timestamp}",
            name="ER Diagram",
            type="er",
            content=er
        ))

        # نقشه ذهنی
        mindmap = self.generate_mindmap(analysis, project_name)
        diagrams.append(DiagramInfo(
            id=f"mind_{timestamp}",
            name="Mind Map",
            type="mindmap",
            content=mindmap
        ))

        # نمودار وضعیت
        state = self.generate_state_diagram(analysis)
        diagrams.append(DiagramInfo(
            id=f"state_{timestamp}",
            name="State Diagram",
            type="state",
            content=state
        ))

        # کش کردن
        self._diagrams_cache[project_id] = diagrams

        return diagrams

    def get_cached_diagrams(self, project_id: str) -> List[DiagramInfo]:
        """دریافت نمودارهای کش شده"""
        return self._diagrams_cache.get(project_id, [])

    async def update_diagram(
        self,
        project_id: str,
        diagram_type: str,
        project_path: Path,
        project_name: str = "Project"
    ) -> Optional[DiagramInfo]:
        """بروزرسانی یک نمودار خاص"""
        analysis = await self.analyze_project(project_id, project_path)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if diagram_type == "class":
            content = self.generate_class_diagram(analysis, project_name)
        elif diagram_type == "flowchart":
            content = self.generate_flowchart(analysis, project_name)
        elif diagram_type == "sequence":
            content = self.generate_sequence_diagram(analysis)
        elif diagram_type == "er":
            content = self.generate_er_diagram(analysis)
        elif diagram_type == "mindmap":
            content = self.generate_mindmap(analysis, project_name)
        elif diagram_type == "state":
            content = self.generate_state_diagram(analysis)
        else:
            return None

        diagram = DiagramInfo(
            id=f"{diagram_type}_{timestamp}",
            name=f"{diagram_type.title()} Diagram",
            type=diagram_type,
            content=content
        )

        # بروزرسانی کش
        if project_id in self._diagrams_cache:
            self._diagrams_cache[project_id] = [
                d for d in self._diagrams_cache[project_id]
                if d.type != diagram_type
            ]
            self._diagrams_cache[project_id].append(diagram)

        return diagram

    def generate_custom_diagram(
        self,
        diagram_type: str,
        data: Dict
    ) -> str:
        """تولید نمودار سفارشی از داده"""
        if diagram_type == "flowchart":
            return self._custom_flowchart(data)
        elif diagram_type == "sequence":
            return self._custom_sequence(data)
        elif diagram_type == "gantt":
            return self._custom_gantt(data)
        else:
            return f"graph TD\n    A[{data.get('title', 'Diagram')}]"

    def _custom_flowchart(self, data: Dict) -> str:
        """نمودار جریان سفارشی"""
        lines = ["flowchart TD"]

        nodes = data.get("nodes", [])
        edges = data.get("edges", [])

        for node in nodes:
            node_id = node.get("id", "N")
            label = node.get("label", "Node")
            shape = node.get("shape", "rect")

            if shape == "circle":
                lines.append(f"    {node_id}(({label}))")
            elif shape == "diamond":
                lines.append(f"    {node_id}{{{label}}}")
            else:
                lines.append(f"    {node_id}[{label}]")

        for edge in edges:
            source = edge.get("from", "A")
            target = edge.get("to", "B")
            label = edge.get("label", "")

            if label:
                lines.append(f"    {source} -->|{label}| {target}")
            else:
                lines.append(f"    {source} --> {target}")

        return "\n".join(lines)

    def _custom_sequence(self, data: Dict) -> str:
        """نمودار توالی سفارشی"""
        lines = ["sequenceDiagram"]

        participants = data.get("participants", [])
        messages = data.get("messages", [])

        for p in participants:
            lines.append(f"    participant {p}")

        for msg in messages:
            sender = msg.get("from", "A")
            receiver = msg.get("to", "B")
            text = msg.get("text", "message")
            msg_type = msg.get("type", "sync")

            if msg_type == "async":
                lines.append(f"    {sender}-->>+{receiver}: {text}")
            else:
                lines.append(f"    {sender}->>+{receiver}: {text}")

        return "\n".join(lines)

    def _custom_gantt(self, data: Dict) -> str:
        """نمودار گانت سفارشی"""
        lines = ["gantt"]
        lines.append(f"    title {data.get('title', 'Project Timeline')}")
        lines.append("    dateFormat YYYY-MM-DD")

        sections = data.get("sections", [])

        for section in sections:
            lines.append(f"    section {section.get('name', 'Section')}")

            for task in section.get("tasks", []):
                task_name = task.get("name", "Task")
                duration = task.get("duration", "1d")
                status = task.get("status", "")

                if status:
                    lines.append(f"    {task_name}: {status}, {duration}")
                else:
                    lines.append(f"    {task_name}: {duration}")

        return "\n".join(lines)


# سینگلتون
_diagram_service: Optional[DynamicDiagramService] = None


def get_diagram_service() -> DynamicDiagramService:
    """دریافت سرویس نمودار"""
    global _diagram_service
    if _diagram_service is None:
        _diagram_service = DynamicDiagramService()
    return _diagram_service
