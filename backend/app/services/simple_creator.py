"""
سرویس ساده تولید پروژه با AI
بدون پیچیدگی اضافی - فقط کار میکنه!
"""

import os
import json
import logging
import uuid
import asyncio
import threading

logger = logging.getLogger(__name__)
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
    # 🆕 (Reference Projects) — پروژه‌هایی که هنگام ساخت به‌عنوان منبع
    # الهام استفاده شدند. هر آیتم: {project_id, project_path, is_selected}
    selected_projects: List[Dict[str, Any]] = field(default_factory=list)

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
            "selected_projects": self.selected_projects,
        }


# ================================
# Simple Project Creator
# ================================

class SimpleProjectCreator:
    """سازنده ساده پروژه با AI"""

    def __init__(self, workspace: Optional[str] = None):
        # 🐛 (creator persistence fix) — قبلاً پیش‌فرض "./projects" بود که
        # روی Render در /app/projects قرار می‌گرفت — این مسیر ephemeral
        # است و با هر deploy کاملاً پاک می‌شد. کاربر پروژه‌های ساخته‌شدهٔ
        # خود را از دست می‌داد. render.yaml یک persistent disk روی
        # /app/storage mount کرده، پس مسیر پیش‌فرض باید زیر آن باشد.
        # ENV var SIMPLE_CREATOR_WORKSPACE برای override سفارشی.
        if workspace is None:
            workspace = os.environ.get("SIMPLE_CREATOR_WORKSPACE", "")
            if not workspace:
                # ترتیب fallback: storage مونت‌شده → relative → /tmp
                for c in ("./storage/projects", "/app/storage/projects", "./projects", "/tmp/projects"):
                    try:
                        p = Path(c)
                        p.mkdir(parents=True, exist_ok=True)
                        test = p / ".write_test"
                        test.write_text("ok", encoding="utf-8")
                        test.unlink(missing_ok=True)
                        workspace = c
                        break
                    except Exception:
                        continue
                if not workspace:
                    workspace = "/tmp/projects"
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        # 🆕 visibility: log the chosen workspace + a hint whether it's
        # on a persistent disk. Important for diagnosing
        # "projects disappeared after redeploy" — if this prints
        # /tmp or /app/projects, persistence is broken.
        try:
            import logging as _logging
            _logger = _logging.getLogger(__name__)
            _resolved = str(self.workspace.resolve())
            _is_persistent = (
                "/app/storage" in _resolved
                or "storage/projects" in _resolved
                or bool(os.environ.get("SIMPLE_CREATOR_WORKSPACE"))
            )
            _logger.info(
                "📁 SimpleProjectCreator workspace=%s persistent=%s",
                _resolved, _is_persistent,
            )
            if not _is_persistent:
                _logger.warning(
                    "⚠️ SimpleProjectCreator using EPHEMERAL workspace "
                    "(%s) — projects will vanish on container restart. "
                    "On Render, ensure /app/storage disk is mounted "
                    "(see render.yaml) so ./storage/projects becomes "
                    "persistent.", _resolved,
                )
        except Exception:
            pass
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
                                # 🆕 (Reference Projects) — اگر در meta نبود،
                                # default [] از dataclass استفاده می‌شود.
                                selected_projects=data.get("selected_projects", []) or [],
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
        ai_generate: callable = None,
        selected_projects: Optional[List[Dict[str, Any]]] = None,
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
            selected_projects=list(selected_projects or []),
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

    @staticmethod
    def _estimate_file_complexity(file_path: str, file_desc: str) -> int:
        """🆕 تخمین تقریبی تعداد token‌های لازم برای تولید فایل.

        بر اساس نوع فایل + طول توضیح + پیچیدگی نام:
        - README/config ساده: ~800 token
        - main.py / route ساده: ~2000 token
        - full app file با چند function: ~4000-8000 token
        - very complex (model + schema + business logic): ~10000+ token
        """
        base = 1500
        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
        fname = file_path.rsplit("/", 1)[-1].lower()
        # نوع فایل
        if ext in ("md", "txt", "yml", "yaml", "json", "toml", "ini", "cfg"):
            base = 800
        elif ext in ("env", "gitignore", "dockerfile") or fname.startswith("."):
            base = 400
        elif ext in ("py", "ts", "tsx", "js", "jsx", "go", "rs", "java"):
            base = 2500
        # پیچیدگی بر اساس توضیح
        desc_len = len(file_desc or "")
        base += int(desc_len * 2.5)  # توضیح طولانی‌تر = کد بیشتر
        # کلمات کلیدی complex
        for kw in ("auth", "api", "model", "schema", "service", "router", "main", "core"):
            if kw in file_path.lower() or kw in file_desc.lower():
                base += 500
        return min(base, 16000)  # cap

    async def _generate_file_in_chunks(
        self,
        project_name: str,
        project_desc: str,
        project_type: str,
        file_path: str,
        file_desc: str,
        ai_generate: callable,
        max_per_section: int = 3500,
        num_sections: int = 3,
    ) -> str:
        """🆕 برای فایل‌های بزرگ: تقسیم به chunks → concatenate.

        Strategy:
        1. AI outline تولید کند (لیست section‌ها با هدر و توضیح)
        2. هر section را با context outline تولید کن
        3. concatenate + sanitize
        """
        # 1. outline
        outline_prompt = f"""برای فایل `{file_path}` در پروژهٔ "{project_name}" (نوع: {project_type})،
ساختار را به {num_sections} section تقسیم کن.

توضیح فایل: {file_desc}
توضیح پروژه: {project_desc[:500]}

خروجی JSON:
{{
  "sections": [
    {{"index": 1, "title": "imports + constants", "outline": "..."}},
    {{"index": 2, "title": "core functions", "outline": "..."}},
    ...
  ]
}}
فقط JSON برگردان."""
        try:
            outline_resp = await ai_generate(outline_prompt)
            start = outline_resp.find("{")
            end = outline_resp.rfind("}") + 1
            outline_data = json.loads(outline_resp[start:end]) if start >= 0 else {}
        except Exception:
            outline_data = {}
        sections = outline_data.get("sections") or [
            {"index": i, "title": f"section_{i}", "outline": ""} for i in range(1, num_sections + 1)
        ]

        # 2. هر section را تولید کن
        parts: List[str] = []
        outline_summary = "\n".join(
            f"- section {s.get('index', '?')}: {s.get('title', '')} — {s.get('outline', '')[:100]}"
            for s in sections
        )
        for s in sections:
            sec_prompt = f"""فایل `{file_path}` در پروژهٔ "{project_name}" را در {len(sections)} section می‌نویسیم.
این outline کلی است:
{outline_summary}

حالا فقط **section {s.get('index', '?')}: {s.get('title', '')}** را بنویس:
{s.get('outline', '')}

⚠️ مهم:
- فقط کد همین section را خروجی بده (نه کل فایل)
- اگر این section اول است، imports/headers بنویس
- اگر section میانی است، فقط محتوا (بدون duplicate imports)
- اگر آخر است، main block / footer بنویس
- فقط کد، بدون توضیح، بدون ```"""
            try:
                resp = await ai_generate(sec_prompt)
                parts.append(resp.strip())
            except Exception as e:
                logger.warning(f"chunk {s.get('index')} of {file_path} failed: {e}")
                continue

        # 3. concatenate
        combined = "\n\n".join(parts)
        # 4. sanitize
        from .content_sanitizer import strip_reasoning_blocks, sanitize_file_content
        combined = strip_reasoning_blocks(combined)
        combined = sanitize_file_content(combined, file_path)

        # 5. validate Python files با ast
        if file_path.endswith(".py"):
            try:
                import ast
                ast.parse(combined)
            except SyntaxError as e:
                logger.warning(f"chunked {file_path} syntactically invalid: {e} — retry once")
                # one retry: full regeneration with warning
                retry_prompt = (
                    f"خروجی قبلی برای فایل `{file_path}` syntactically invalid بود ({e}).\n"
                    f"فایل را به‌طور کامل و syntactically valid بنویس.\n"
                    f"توضیح: {file_desc}"
                )
                try:
                    retry = await ai_generate(retry_prompt)
                    retry = strip_reasoning_blocks(retry.strip())
                    retry = sanitize_file_content(retry, file_path)
                    return retry
                except Exception:
                    return combined
        return combined

    async def _generate_file(
        self,
        project_name: str,
        project_desc: str,
        project_type: str,
        file_path: str,
        file_desc: str,
        ai_generate: callable,
        max_output_tokens: int = 16384,  # 🆕 budget مدل
    ) -> str:
        """تولید محتوای یک فایل با AI — با respect به token budget."""
        # 🆕 تخمین complexity → تصمیم one-shot vs chunks
        estimated = self._estimate_file_complexity(file_path, file_desc)
        # اگر تخمین > 70% max_output → chunking
        threshold = int(max_output_tokens * 0.7)
        if estimated > threshold:
            logger.info(
                f"file {file_path}: estimated {estimated} > {threshold} → chunked generation"
            )
            num_sections = max(2, min(5, (estimated // threshold) + 1))
            return await self._generate_file_in_chunks(
                project_name=project_name,
                project_desc=project_desc,
                project_type=project_type,
                file_path=file_path,
                file_desc=file_desc,
                ai_generate=ai_generate,
                num_sections=num_sections,
            )

        # one-shot
        prompt = f"""برای پروژه "{project_name}" ({project_type}) این فایل رو بنویس:

پروژه: {project_desc}
فایل: {file_path}
توضیح فایل: {file_desc}

کد کامل و قابل اجرا بنویس. فقط کد، بدون توضیح اضافی.
اگه markdown نیاز نیست، ``` نذار."""

        response = await ai_generate(prompt)

        # 🛡️ پاکسازی کامل محتوا از آلودگی reasoning/markdown (ماژول مرکزی)
        from .content_sanitizer import strip_reasoning_blocks, sanitize_file_content
        content = response.strip()
        content = strip_reasoning_blocks(content)
        content = sanitize_file_content(content, file_path)

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
    """دریافت instance سازنده پروژه (thread-safe).

    🐛 (creator persistence fix v2) — قبلاً اینجا `"./projects"` هاردکد شده
    بود که تمام منطق fallback در __init__ را دور می‌زد. روی Render مسیر
    `./projects` می‌شود `/app/projects` که ephemeral است — هر redeploy
    کاملاً پاک. کاربر گزارش داد: «پروژه‌ای که قبلاً ساخته بودم بازم رفته».

    حالا `None` پاس می‌دهیم تا __init__ سراغ candidates (به‌ترتیب اولویت:
    SIMPLE_CREATOR_WORKSPACE env → ./storage/projects → /app/storage/projects
    → ./projects → /tmp/projects) برود و اولین مسیر writable را انتخاب
    کند. روی Render، /app/storage یک persistent disk است که بین deploy ها
    حفظ می‌شود.
    """
    global _creator
    if _creator is None:
        with _creator_lock:
            # Double-check locking pattern
            if _creator is None:
                _creator = SimpleProjectCreator()  # None → use persistence fallback
    return _creator
