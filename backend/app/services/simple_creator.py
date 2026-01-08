"""
سرویس ساده تولید پروژه با AI
بدون پیچیدگی اضافی - فقط کار میکنه!
"""

import os
import json
import uuid
import asyncio
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import aiofiles

# ================================
# Data Models
# ================================

@dataclass
class ProjectFile:
    """یک فایل پروژه"""
    path: str
    content: str = ""
    language: str = ""

    def to_dict(self):
        return {"path": self.path, "content": self.content, "language": self.language}


@dataclass
class Project:
    """یک پروژه"""
    id: str
    name: str
    description: str
    project_type: str
    status: str = "creating"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    files: List[ProjectFile] = field(default_factory=list)
    structure: Dict = field(default_factory=dict)
    technologies: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "project_type": self.project_type,
            "status": self.status,
            "created_at": self.created_at,
            "files": [f.to_dict() if isinstance(f, ProjectFile) else f for f in self.files],
            "structure": self.structure,
            "technologies": self.technologies,
        }


# ================================
# Simple Project Creator
# ================================

class SimpleProjectCreator:
    """سازنده ساده پروژه با AI"""

    def __init__(self, workspace: str = "./projects"):
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.projects: Dict[str, Project] = {}
        self._load_existing_projects()

    def _load_existing_projects(self):
        """بارگذاری پروژه‌های موجود"""
        try:
            for folder in self.workspace.iterdir():
                if folder.is_dir() and folder.name.startswith("proj_"):
                    meta_file = folder / "project.json"
                    if meta_file.exists():
                        with open(meta_file) as f:
                            data = json.load(f)
                            project = Project(
                                id=data.get("id", folder.name),
                                name=data.get("name", "Unknown"),
                                description=data.get("description", ""),
                                project_type=data.get("project_type", "unknown"),
                                status=data.get("status", "created"),
                                created_at=data.get("created_at", ""),
                                files=[ProjectFile(**f) if isinstance(f, dict) else ProjectFile(path=f)
                                       for f in data.get("files", [])],
                                structure=data.get("structure", {}),
                                technologies=data.get("technologies", []),
                            )
                            self.projects[project.id] = project
        except Exception as e:
            print(f"Error loading projects: {e}")

    async def create_project(
        self,
        name: str,
        description: str,
        project_type: str,
        technologies: List[str] = None,
        ai_generate: callable = None
    ) -> Project:
        """ساخت پروژه جدید"""

        # ایجاد ID و مسیر
        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        project_path = self.workspace / project_id
        project_path.mkdir(parents=True, exist_ok=True)

        # ایجاد پروژه
        project = Project(
            id=project_id,
            name=name,
            description=description,
            project_type=project_type,
            technologies=technologies or [],
        )

        self.projects[project_id] = project

        # اگه AI داریم، فایل‌ها رو تولید کن
        if ai_generate:
            try:
                # مرحله 1: تولید ساختار
                structure = await self._generate_structure(
                    name, description, project_type, technologies, ai_generate
                )
                project.structure = structure

                # مرحله 2: تولید هر فایل
                files_to_generate = structure.get("files", [])
                for file_info in files_to_generate:
                    file_path = file_info.get("path") if isinstance(file_info, dict) else file_info
                    file_desc = file_info.get("description", "") if isinstance(file_info, dict) else ""

                    content = await self._generate_file(
                        name, description, project_type, file_path, file_desc, ai_generate
                    )

                    # ذخیره فایل
                    full_path = project_path / file_path
                    full_path.parent.mkdir(parents=True, exist_ok=True)

                    async with aiofiles.open(full_path, 'w') as f:
                        await f.write(content)

                    project.files.append(ProjectFile(
                        path=file_path,
                        content=content,
                        language=self._detect_language(file_path)
                    ))

                project.status = "created"

            except Exception as e:
                project.status = "error"
                print(f"Error generating project: {e}")

        # ذخیره metadata
        await self._save_project_meta(project)

        return project

    async def _generate_structure(
        self,
        name: str,
        description: str,
        project_type: str,
        technologies: List[str],
        ai_generate: callable
    ) -> Dict:
        """تولید ساختار پروژه با AI"""

        prompt = f"""یک پروژه {project_type} با مشخصات زیر طراحی کن:

نام: {name}
توضیحات: {description}
تکنولوژی‌ها: {', '.join(technologies or [])}

خروجی باید JSON باشه با این فرمت:
{{
    "directories": ["src", "tests", "config"],
    "files": [
        {{"path": "src/main.py", "description": "فایل اصلی"}},
        {{"path": "requirements.txt", "description": "وابستگی‌ها"}},
        {{"path": "README.md", "description": "مستندات"}}
    ],
    "entry_point": "src/main.py",
    "run_command": "python src/main.py"
}}

فقط JSON برگردون، بدون توضیح اضافی."""

        response = await ai_generate(prompt)

        # پارس JSON
        try:
            # پیدا کردن JSON در پاسخ
            text = response
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            print(f"Error parsing JSON structure: {e}")

        # ساختار پیش‌فرض
        return self._get_default_structure(project_type)

    async def _generate_file(
        self,
        project_name: str,
        project_desc: str,
        project_type: str,
        file_path: str,
        file_desc: str,
        ai_generate: callable
    ) -> str:
        """تولید محتوای یک فایل با AI"""

        prompt = f"""برای پروژه "{project_name}" ({project_type}) این فایل رو بنویس:

پروژه: {project_desc}
فایل: {file_path}
توضیح فایل: {file_desc}

کد کامل و قابل اجرا بنویس. فقط کد، بدون توضیح اضافی.
اگه markdown نیاز نیست، ``` نذار."""

        response = await ai_generate(prompt)

        # پاکسازی
        content = response.strip()

        # حذف markdown code blocks
        if content.startswith("```"):
            lines = content.split('\n')
            # حذف خط اول (```python یا ```)
            lines = lines[1:]
            # حذف خط آخر اگه ``` باشه
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = '\n'.join(lines)

        return content

    def _get_default_structure(self, project_type: str) -> Dict:
        """ساختار پیش‌فرض بر اساس نوع پروژه"""

        structures = {
            "python": {
                "directories": ["src", "tests"],
                "files": [
                    {"path": "src/main.py", "description": "فایل اصلی"},
                    {"path": "requirements.txt", "description": "وابستگی‌ها"},
                    {"path": "README.md", "description": "مستندات"},
                ],
                "entry_point": "src/main.py",
                "run_command": "python src/main.py"
            },
            "fastapi": {
                "directories": ["app", "app/api", "app/models", "tests"],
                "files": [
                    {"path": "app/main.py", "description": "نقطه ورود FastAPI"},
                    {"path": "app/api/routes.py", "description": "API routes"},
                    {"path": "app/models/schemas.py", "description": "Pydantic models"},
                    {"path": "requirements.txt", "description": "وابستگی‌ها"},
                    {"path": "Dockerfile", "description": "Docker config"},
                    {"path": "README.md", "description": "مستندات"},
                ],
                "entry_point": "app/main.py",
                "run_command": "uvicorn app.main:app --reload"
            },
            "nextjs": {
                "directories": ["src/app", "src/components", "public"],
                "files": [
                    {"path": "src/app/page.tsx", "description": "صفحه اصلی"},
                    {"path": "src/app/layout.tsx", "description": "Layout"},
                    {"path": "src/components/Header.tsx", "description": "هدر"},
                    {"path": "package.json", "description": "وابستگی‌ها"},
                    {"path": "tailwind.config.js", "description": "Tailwind config"},
                    {"path": "README.md", "description": "مستندات"},
                ],
                "entry_point": "src/app/page.tsx",
                "run_command": "npm run dev"
            },
            "react": {
                "directories": ["src", "src/components", "public"],
                "files": [
                    {"path": "src/App.tsx", "description": "کامپوننت اصلی"},
                    {"path": "src/index.tsx", "description": "نقطه ورود"},
                    {"path": "src/components/Header.tsx", "description": "هدر"},
                    {"path": "package.json", "description": "وابستگی‌ها"},
                    {"path": "README.md", "description": "مستندات"},
                ],
                "entry_point": "src/App.tsx",
                "run_command": "npm start"
            },
        }

        return structures.get(project_type, structures["python"])

    def _detect_language(self, file_path: str) -> str:
        """تشخیص زبان فایل"""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".jsx": "javascript",
            ".json": "json",
            ".md": "markdown",
            ".html": "html",
            ".css": "css",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".sh": "bash",
            ".sql": "sql",
        }
        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext, "text")

    async def _save_project_meta(self, project: Project):
        """ذخیره metadata پروژه"""
        project_path = self.workspace / project.id
        project_path.mkdir(parents=True, exist_ok=True)

        meta_file = project_path / "project.json"
        async with aiofiles.open(meta_file, 'w') as f:
            await f.write(json.dumps(project.to_dict(), ensure_ascii=False, indent=2))

    def get_project(self, project_id: str) -> Optional[Project]:
        """دریافت یک پروژه"""
        return self.projects.get(project_id)

    def list_projects(self) -> List[Project]:
        """لیست همه پروژه‌ها"""
        return list(self.projects.values())

    async def get_project_files(self, project_id: str) -> List[Dict]:
        """لیست فایل‌های یک پروژه"""
        project = self.projects.get(project_id)
        if not project:
            return []

        project_path = self.workspace / project_id
        if not project_path.exists():
            return []

        files = []
        for file_path in project_path.rglob("*"):
            if file_path.is_file() and file_path.name != "project.json":
                rel_path = file_path.relative_to(project_path)
                files.append({
                    "path": str(rel_path),
                    "size": file_path.stat().st_size,
                    "language": self._detect_language(str(rel_path))
                })

        return files

    async def get_file_content(self, project_id: str, file_path: str) -> Optional[str]:
        """خواندن محتوای یک فایل"""
        project_path = self.workspace / project_id / file_path

        if not project_path.exists():
            return None

        try:
            async with aiofiles.open(project_path, 'r') as f:
                return await f.read()
        except (IOError, OSError, UnicodeDecodeError) as e:
            print(f"Error reading file {project_path}: {e}")
            return None

    def delete_project(self, project_id: str) -> bool:
        """حذف پروژه"""
        if project_id not in self.projects:
            return False

        import shutil
        project_path = self.workspace / project_id
        if project_path.exists():
            shutil.rmtree(project_path)

        del self.projects[project_id]
        return True


# ================================
# Singleton (thread-safe)
# ================================

_creator: Optional[SimpleProjectCreator] = None
_creator_lock = threading.Lock()


def get_simple_creator() -> SimpleProjectCreator:
    """دریافت instance سازنده پروژه (thread-safe)"""
    global _creator
    if _creator is None:
        with _creator_lock:
            # Double-check locking pattern
            if _creator is None:
                _creator = SimpleProjectCreator("./projects")
    return _creator
