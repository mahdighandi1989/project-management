"""
سرویس تولید نمودار داینامیک
Dynamic Diagram Generation Service
"""

from typing import Dict, List, Optional, Any
from enum import Enum


class DiagramType(str, Enum):
    FLOWCHART = "flowchart"
    SEQUENCE = "sequence"
    CLASS = "class"
    STATE = "state"
    ER = "er"
    GANTT = "gantt"
    PIE = "pie"
    MINDMAP = "mindmap"
    ARCHITECTURE = "architecture"
    COMPONENT = "component"


class DiagramService:
    """سرویس تولید نمودارهای Mermaid"""

    def __init__(self):
        self.theme = "default"

    # =====================================
    # نمودار پروژه
    # =====================================

    def generate_project_flowchart(self, project: Dict) -> str:
        """تولید نمودار جریان پروژه"""
        phases = project.get("phases", [])
        if not phases:
            return "flowchart TB\n  A[پروژه خالی]"

        diagram = "flowchart TB\n"
        diagram += "  classDef completed fill:#4CAF50,stroke:#2E7D32,color:#fff\n"
        diagram += "  classDef inProgress fill:#2196F3,stroke:#1565C0,color:#fff\n"
        diagram += "  classDef pending fill:#9E9E9E,stroke:#616161,color:#fff\n"
        diagram += "  classDef failed fill:#F44336,stroke:#C62828,color:#fff\n"
        diagram += "  classDef paused fill:#FF9800,stroke:#EF6C00,color:#fff\n\n"

        # گره شروع
        diagram += f'  start((🚀 شروع)):::completed\n'

        # فازها
        for i, phase in enumerate(phases):
            phase_id = phase.get("id", f"p{i}")
            name = phase.get("name", f"فاز {i+1}")
            status = phase.get("status", "pending")
            progress = phase.get("progress", 0)

            # شکل گره بر اساس وضعیت
            if status == "completed":
                shape = f"[✅ {name}]"
                css_class = "completed"
            elif status == "in_progress":
                shape = f"[🔄 {name} ({progress}%)]"
                css_class = "inProgress"
            elif status == "failed":
                shape = f"[❌ {name}]"
                css_class = "failed"
            elif status == "paused":
                shape = f"[⏸️ {name}]"
                css_class = "paused"
            else:
                shape = f"[⏳ {name}]"
                css_class = "pending"

            diagram += f"  {phase_id}{shape}:::{css_class}\n"

        # گره پایان
        all_completed = all(p.get("status") == "completed" for p in phases)
        end_class = "completed" if all_completed else "pending"
        diagram += f"  endNode((🏁 پایان)):::{end_class}\n\n"

        # اتصالات
        if phases:
            diagram += f"  start --> {phases[0].get('id', 'p0')}\n"
            for i in range(len(phases) - 1):
                current_id = phases[i].get("id", f"p{i}")
                next_id = phases[i + 1].get("id", f"p{i+1}")
                diagram += f"  {current_id} --> {next_id}\n"
            diagram += f"  {phases[-1].get('id', 'pLast')} --> endNode\n"

        return diagram

    # =====================================
    # نمودار معماری
    # =====================================

    def generate_architecture_diagram(
        self,
        components: List[Dict],
        connections: List[Dict] = []
    ) -> str:
        """تولید نمودار معماری سیستم"""
        diagram = "flowchart TB\n"
        diagram += "  subgraph Frontend[\"🖥️ Frontend\"]\n"
        diagram += "    UI[React/Next.js]\n"
        diagram += "    State[State Management]\n"
        diagram += "  end\n\n"

        diagram += "  subgraph Backend[\"⚙️ Backend\"]\n"
        diagram += "    API[FastAPI]\n"
        diagram += "    Services[Services Layer]\n"
        diagram += "  end\n\n"

        diagram += "  subgraph AI[\"🤖 AI Layer\"]\n"
        for comp in components:
            if comp.get("type") == "ai":
                comp_id = comp.get("id", "ai")
                name = comp.get("name", "AI Service")
                diagram += f"    {comp_id}[{name}]\n"
        diagram += "  end\n\n"

        diagram += "  subgraph Data[\"💾 Data\"]\n"
        diagram += "    DB[(Database)]\n"
        diagram += "    Cache[(Cache)]\n"
        diagram += "  end\n\n"

        # اتصالات پیش‌فرض
        diagram += "  UI --> State\n"
        diagram += "  State --> API\n"
        diagram += "  API --> Services\n"
        diagram += "  Services --> AI\n"
        diagram += "  Services --> DB\n"
        diagram += "  Services --> Cache\n"

        # اتصالات سفارشی
        for conn in connections:
            source = conn.get("from", "")
            target = conn.get("to", "")
            label = conn.get("label", "")
            if source and target:
                if label:
                    diagram += f"  {source} -->|{label}| {target}\n"
                else:
                    diagram += f"  {source} --> {target}\n"

        return diagram

    # =====================================
    # نمودار کلاس
    # =====================================

    def generate_class_diagram(self, classes: List[Dict]) -> str:
        """تولید نمودار کلاس از کد"""
        diagram = "classDiagram\n"

        for cls in classes:
            class_name = cls.get("name", "UnknownClass")
            diagram += f"  class {class_name} {{\n"

            # خصوصیات
            for prop in cls.get("properties", []):
                visibility = prop.get("visibility", "+")
                prop_name = prop.get("name", "")
                prop_type = prop.get("type", "any")
                diagram += f"    {visibility}{prop_type} {prop_name}\n"

            # متدها
            for method in cls.get("methods", []):
                visibility = method.get("visibility", "+")
                method_name = method.get("name", "")
                return_type = method.get("return_type", "void")
                params = method.get("params", "")
                diagram += f"    {visibility}{method_name}({params}) {return_type}\n"

            diagram += "  }\n\n"

        # روابط
        for cls in classes:
            class_name = cls.get("name", "")
            for rel in cls.get("relations", []):
                rel_type = rel.get("type", "-->")  # --> , ..|> , --|> , *-- , o--
                target = rel.get("target", "")
                if target:
                    diagram += f"  {class_name} {rel_type} {target}\n"

        return diagram

    # =====================================
    # نمودار توالی
    # =====================================

    def generate_sequence_diagram(
        self,
        participants: List[str],
        messages: List[Dict]
    ) -> str:
        """تولید نمودار توالی"""
        diagram = "sequenceDiagram\n"

        # شرکت‌کنندگان
        for p in participants:
            diagram += f"  participant {p}\n"
        diagram += "\n"

        # پیام‌ها
        for msg in messages:
            sender = msg.get("from", "")
            receiver = msg.get("to", "")
            message = msg.get("message", "")
            msg_type = msg.get("type", "solid")  # solid, dotted, async

            arrow = "->>" if msg_type == "async" else "-->" if msg_type == "dotted" else "->>"

            if sender and receiver:
                diagram += f"  {sender}{arrow}{receiver}: {message}\n"

                # پاسخ اگر موجود باشد
                if msg.get("response"):
                    diagram += f"  {receiver}-->>{sender}: {msg['response']}\n"

        return diagram

    # =====================================
    # نمودار Gantt
    # =====================================

    def generate_gantt_chart(
        self,
        title: str,
        tasks: List[Dict]
    ) -> str:
        """تولید نمودار Gantt"""
        diagram = "gantt\n"
        diagram += f"  title {title}\n"
        diagram += "  dateFormat YYYY-MM-DD\n"
        diagram += "  axisFormat %m/%d\n\n"

        current_section = None
        for task in tasks:
            section = task.get("section", "")
            if section != current_section:
                diagram += f"  section {section}\n"
                current_section = section

            task_name = task.get("name", "Task")
            task_id = task.get("id", "")
            duration = task.get("duration", "1d")
            start = task.get("start", "")
            status = task.get("status", "")

            # وضعیت
            status_prefix = ""
            if status == "done":
                status_prefix = "done, "
            elif status == "active":
                status_prefix = "active, "
            elif status == "crit":
                status_prefix = "crit, "

            if start:
                diagram += f"    {task_name}: {status_prefix}{task_id}, {start}, {duration}\n"
            elif task.get("after"):
                after = task.get("after")
                diagram += f"    {task_name}: {status_prefix}{task_id}, after {after}, {duration}\n"
            else:
                diagram += f"    {task_name}: {status_prefix}{task_id}, {duration}\n"

        return diagram

    # =====================================
    # نمودار ER (Entity-Relationship)
    # =====================================

    def generate_er_diagram(self, entities: List[Dict]) -> str:
        """تولید نمودار ER"""
        diagram = "erDiagram\n"

        # موجودیت‌ها
        for entity in entities:
            entity_name = entity.get("name", "ENTITY")
            diagram += f"  {entity_name} {{\n"

            for field in entity.get("fields", []):
                field_type = field.get("type", "string")
                field_name = field.get("name", "field")
                key = field.get("key", "")
                diagram += f"    {field_type} {field_name}"
                if key:
                    diagram += f" {key}"
                diagram += "\n"

            diagram += "  }\n\n"

        # روابط
        for entity in entities:
            entity_name = entity.get("name", "")
            for rel in entity.get("relations", []):
                target = rel.get("target", "")
                cardinality = rel.get("cardinality", "||--o{")
                label = rel.get("label", "has")
                if target:
                    diagram += f"  {entity_name} {cardinality} {target} : {label}\n"

        return diagram

    # =====================================
    # نمودار ذهنی (Mind Map)
    # =====================================

    def generate_mindmap(self, root: str, nodes: List[Dict]) -> str:
        """تولید نمودار ذهنی"""
        diagram = "mindmap\n"
        diagram += f"  root(({root}))\n"

        def add_node(node: Dict, level: int = 2):
            result = ""
            indent = "  " * level
            name = node.get("name", "Node")
            children = node.get("children", [])

            result += f"{indent}{name}\n"
            for child in children:
                result += add_node(child, level + 1)
            return result

        for node in nodes:
            diagram += add_node(node)

        return diagram

    # =====================================
    # نمودار دایره‌ای (Pie)
    # =====================================

    def generate_pie_chart(self, title: str, data: Dict[str, float]) -> str:
        """تولید نمودار دایره‌ای"""
        diagram = "pie showData\n"
        diagram += f'  title {title}\n'

        for label, value in data.items():
            diagram += f'  "{label}" : {value}\n'

        return diagram

    # =====================================
    # نمودار وضعیت (State)
    # =====================================

    def generate_state_diagram(
        self,
        states: List[Dict],
        transitions: List[Dict]
    ) -> str:
        """تولید نمودار وضعیت"""
        diagram = "stateDiagram-v2\n"

        # حالت‌ها
        for state in states:
            state_id = state.get("id", "")
            label = state.get("label", state_id)
            state_type = state.get("type", "normal")

            if state_type == "start":
                diagram += f"  [*] --> {state_id}\n"
            elif state_type == "end":
                diagram += f"  {state_id} --> [*]\n"
            else:
                diagram += f"  {state_id}: {label}\n"

        diagram += "\n"

        # انتقال‌ها
        for trans in transitions:
            source = trans.get("from", "")
            target = trans.get("to", "")
            label = trans.get("label", "")

            if source and target:
                if label:
                    diagram += f"  {source} --> {target}: {label}\n"
                else:
                    diagram += f"  {source} --> {target}\n"

        return diagram

    # =====================================
    # تحلیل کد و تولید نمودار
    # =====================================

    def analyze_code_structure(self, code: str, language: str = "python") -> Dict:
        """تحلیل ساختار کد و استخراج اطلاعات برای نمودار"""
        result = {
            "classes": [],
            "functions": [],
            "imports": [],
            "dependencies": []
        }

        lines = code.split("\n")

        if language == "python":
            current_class = None
            for line in lines:
                stripped = line.strip()

                # import
                if stripped.startswith("import ") or stripped.startswith("from "):
                    result["imports"].append(stripped)

                # class
                elif stripped.startswith("class "):
                    match = stripped[6:].split("(")[0].split(":")[0]
                    current_class = {
                        "name": match.strip(),
                        "methods": [],
                        "properties": []
                    }
                    result["classes"].append(current_class)

                # method/function
                elif stripped.startswith("def "):
                    method_name = stripped[4:].split("(")[0]
                    if current_class:
                        current_class["methods"].append({"name": method_name, "visibility": "+"})
                    else:
                        result["functions"].append(method_name)

        return result

    def code_to_class_diagram(self, code: str, language: str = "python") -> str:
        """تبدیل کد به نمودار کلاس"""
        analysis = self.analyze_code_structure(code, language)
        return self.generate_class_diagram(analysis["classes"])


# سرویس سینگلتون
_diagram_service: Optional[DiagramService] = None

def get_diagram_service() -> DiagramService:
    global _diagram_service
    if _diagram_service is None:
        _diagram_service = DiagramService()
    return _diagram_service
