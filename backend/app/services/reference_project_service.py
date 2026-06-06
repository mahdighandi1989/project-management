# -*- coding: utf-8 -*-
"""
🔍 Reference Project Service
سرویس استخراج، دسته‌بندی، و fusion اطلاعات از پروژه‌های مرجع.

این سرویس سه مرحله‌ی اصلی plan را پوشش می‌دهد:
- Step 5: اسکن پروژه‌های منتخب (لیست فایل‌ها + محتوای فایل‌های مهم)
- Step 6: دسته‌بندی اطلاعات استخراج‌شده (معماری، models، APIها، services، UI)
- Step 7: تولید context fusion برای ادغام در پرامپت نهایی

**معماری**:
سرویس بدون state است. هر فراخوانی یک snapshot از پروژه‌های انتخاب‌شده می‌سازد.

**Cache + Limits**:
برای جلوگیری از overload GitHub API:
- per-repo حداکثر `max_files_per_repo` فایل خوانده می‌شود (default: 30)
- per-file حداکثر `max_file_chars` کاراکتر نگه‌داری می‌شود (default: 8000)
- جمع پاسخ به max_total_chars محدود می‌شود (default: 80000)

**استفاده**:

```python
from .reference_project_service import ReferenceProjectService

svc = ReferenceProjectService()
context = await svc.build_reference_context(
    selected_projects=[
        {"project_id": "w-foo", "project_path": "owner/repo1", "is_selected": True},
    ],
    task_summary="پیاده‌سازی auth با OAuth",
    token=github_token,
)
# context شامل: per-project summary + classified info + fusion-ready text
```
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

from .github_storage import GitHubStorageService, GitHubFile

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

# فایل‌های قابل-اسکن (همه text-based و معمول در dev)
SCANNABLE_EXTENSIONS = {
    # backend
    ".py", ".js", ".ts", ".tsx", ".jsx", ".vue", ".svelte",
    ".go", ".rs", ".java", ".kt", ".scala", ".rb", ".php",
    ".cs", ".cpp", ".c", ".h", ".hpp", ".swift", ".dart",
    ".ex", ".exs", ".clj", ".elm",
    # config
    ".json", ".yaml", ".yml", ".toml", ".ini", ".env",
    # docs
    ".md", ".rst", ".txt",
    # web
    ".html", ".css", ".scss", ".less",
    # data
    ".sql", ".graphql", ".proto",
    # build
    ".dockerfile", "Dockerfile", "Makefile",
}

# مسیرهایی که اسکن نمی‌شوند (noise)
EXCLUDED_PATH_PATTERNS = [
    "node_modules/", ".git/", "dist/", "build/", "__pycache__/",
    ".next/", ".vite/", "target/", ".venv/", "venv/", ".cache/",
    "coverage/", ".pytest_cache/", "vendor/", "test-results/",
    "playwright-report/", ".turbo/", "out/",
]

# فایل‌های "مهم" که اولویت اسکن بالاتری دارند (signal-dense)
HIGH_PRIORITY_PATTERNS = [
    "README", "ARCHITECTURE", "CONTRIBUTING",
    "package.json", "pyproject.toml", "requirements.txt", "Cargo.toml",
    "go.mod", "pom.xml", "Gemfile", "composer.json",
    "schema.prisma", "models.py", "schema.py", "schemas/", "models/",
    "router", "routes", "api/", "endpoints/", "controllers/",
    "service", "services/", "domain/", "core/",
    "config", "settings.py", ".env.example", "docker-compose",
    "main.py", "app.py", "index.ts", "index.js",
]


# ----------------------------------------------------------------------
# Data structures
# ----------------------------------------------------------------------

@dataclass
class FileSummary:
    """خلاصه‌ی یک فایل اسکن‌شده."""
    path: str
    size: int
    content_excerpt: str = ""   # نخستین max_file_chars
    is_truncated: bool = False
    # طبقه‌بندی (heuristic-based):
    category: str = "other"     # backend|frontend|config|docs|test|migration|other
    role: str = ""              # model|service|route|component|util|...


@dataclass
class ProjectExtract:
    """نتیجه اسکن یک پروژه مرجع."""
    project_id: str
    project_path: str           # repo_full_name
    branch: str = "main"
    files: List[FileSummary] = field(default_factory=list)
    total_files_in_repo: int = 0
    scanned_files: int = 0
    error: Optional[str] = None
    # 🆕 (focus_notes) — متن کاربر دربارهٔ نقطهٔ تمرکز در این پروژه.
    # مثلاً «فقط از auth و middleware الهام بگیر». scanner از این متن
    # برای boost اولویت فایل‌های مرتبط استفاده می‌کند و در fusion
    # نمایش داده می‌شود.
    focus_notes: str = ""


@dataclass
class ClassifiedInfo:
    """اطلاعات دسته‌بندی‌شده از یک یا چند پروژه."""
    architecture_docs: List[FileSummary] = field(default_factory=list)
    backend_models: List[FileSummary] = field(default_factory=list)
    backend_services: List[FileSummary] = field(default_factory=list)
    backend_routes: List[FileSummary] = field(default_factory=list)
    frontend_components: List[FileSummary] = field(default_factory=list)
    frontend_pages: List[FileSummary] = field(default_factory=list)
    config_files: List[FileSummary] = field(default_factory=list)
    other: List[FileSummary] = field(default_factory=list)


@dataclass
class ReferenceContext:
    """خروجی نهایی fusion — آماده برای اضافه‌شدن به پرامپت."""
    project_extracts: List[ProjectExtract]
    classified: ClassifiedInfo
    fusion_text: str            # متن آماده برای inject در پرامپت
    total_chars: int            # برای enforcement
    truncated_at_total_limit: bool = False


# ----------------------------------------------------------------------
# Service
# ----------------------------------------------------------------------

class ReferenceProjectService:
    """سرویس مدیریت پروژه‌های مرجع."""

    def __init__(
        self,
        *,
        # 🚨 (Render edge timeout fix) — قبلاً 30 فایل per repo بود. هر فایل
        # یک GitHub fetch می‌خواهد و sequential در batch خوانده می‌شود؛
        # روی Render free-tier با چند پروژهٔ مرجع همزمان به 20-40s می‌رسید
        # و کل /tasks/from-idea را به بالای 100s می‌برد → edge timeout
        # → user 403 می‌گرفت. 12 فایل با اولویت بالا برای الهام کاملاً کافی است
        # (README + 5 منبع اصلی + 6 ساختاری) و scan را در ~10s نگه می‌دارد.
        max_files_per_repo: int = 12,
        max_file_chars: int = 8000,
        max_total_chars: int = 80000,
    ):
        self.max_files_per_repo = max_files_per_repo
        self.max_file_chars = max_file_chars
        self.max_total_chars = max_total_chars

    # ---------------- Step 5: Scan ----------------

    @staticmethod
    def _parse_repo(repo_full_name: str) -> Tuple[str, str]:
        """تجزیه `owner/repo`."""
        s = (repo_full_name or "").replace(".git", "").strip("/")
        if "/" not in s:
            return ("", "")
        owner, _, repo = s.partition("/")
        return (owner.strip(), repo.strip())

    @staticmethod
    def _is_scannable(path: str) -> bool:
        """آیا این فایل قابل اسکن است؟"""
        lower = path.lower()
        for excl in EXCLUDED_PATH_PATTERNS:
            if excl in lower:
                return False
        # extension check
        for ext in SCANNABLE_EXTENSIONS:
            if lower.endswith(ext.lower()) or path.endswith(ext):
                return True
        # نام فایل بدون extension (مثل Dockerfile, Makefile)
        name = path.split("/")[-1]
        if name in {"Dockerfile", "Makefile", "Procfile"}:
            return True
        return False

    # 🆕 (focus_notes) — استخراج keyword های مفید از متن focus کاربر برای
    # تقویت scoring مسیر فایل‌ها. stopword ها حذف می‌شوند و فقط toolکنsهای
    # ≥3 کاراکتر نگه داشته می‌شوند.
    _FOCUS_STOPWORDS = {
        # فارسی
        "از", "این", "آن", "که", "را", "به", "با", "در", "بر", "یا", "و",
        "هم", "اگر", "تا", "ولی", "اما", "چون", "همان", "همه", "هر", "فقط",
        "فقط", "یعنی", "همچنین", "نه", "می‌خوام", "میخوام", "بگیر", "الهام",
        "بخش", "قسمت", "نقطه", "تمرکز", "روی", "نگاه", "کن", "نکن",
        # English
        "the", "and", "or", "but", "for", "with", "from", "into", "only",
        "just", "all", "any", "some", "this", "that", "those", "these",
        "is", "are", "was", "were", "be", "been", "being", "have", "has",
        "had", "do", "does", "did", "will", "would", "should", "could",
        "look", "see", "use", "used", "take", "make", "made", "want",
        "focus", "inspiration", "inspire", "inspired", "part", "parts",
    }

    @classmethod
    def _extract_focus_keywords(cls, focus_notes: str) -> List[str]:
        """استخراج keyword های قابل match در path از focus_notes."""
        if not focus_notes or not focus_notes.strip():
            return []
        # تبدیل به lowercase + جداسازی با whitespace و علائم نگارشی
        cleaned = re.sub(r"[^\w/\.\-_]+", " ", focus_notes.lower())
        tokens = [t.strip() for t in cleaned.split() if t.strip()]
        # فیلتر stopword + طول ≥3
        kws: List[str] = []
        seen: set = set()
        for t in tokens:
            if len(t) < 3:
                continue
            if t in cls._FOCUS_STOPWORDS:
                continue
            if t in seen:
                continue
            seen.add(t)
            kws.append(t)
        return kws[:20]  # cap

    @staticmethod
    def _priority_score(path: str, focus_keywords: Optional[List[str]] = None) -> int:
        """اولویت این فایل برای انتخاب (بالاتر = مهم‌تر).

        🆕 (focus_notes) — اگر focus_keywords پاس داده شود، هر keyword که در
        path پیدا شود +20 امتیاز اضافه می‌کند (وزن دو برابر HIGH_PRIORITY)
        تا فایل‌های مرتبط با focus کاربر به top برسند.
        """
        score = 0
        lower = path.lower()
        for pattern in HIGH_PRIORITY_PATTERNS:
            if pattern.lower() in lower:
                score += 10
        # 🆕 focus boost
        if focus_keywords:
            for kw in focus_keywords:
                if kw in lower:
                    score += 20
        # مسیرهای کم‌عمق مهم‌تر
        depth = path.count("/")
        score -= depth
        # فایل‌های کوچک‌تر مهم‌ترند (signal-dense)
        # ولی این در stage بعد بر اساس size اعمال می‌شود
        return score

    async def scan_project(
        self,
        project_id: str,
        repo_full_name: str,
        *,
        token: str,
        branch: str = "main",
        focus_notes: str = "",
    ) -> ProjectExtract:
        """اسکن یک پروژه — لیست فایل‌ها + محتوای فایل‌های با اولویت بالا.

        🆕 (focus_notes) — اگر کاربر متن focus داده باشد، scoring فایل‌ها
        توسط keyword های آن متن boost می‌شود تا فایل‌های مرتبط (مثلاً
        `auth/*` وقتی کاربر «auth» نوشته) به top برسند.
        """
        owner, repo = self._parse_repo(repo_full_name)
        extract = ProjectExtract(
            project_id=project_id,
            project_path=repo_full_name,
            branch=branch,
            focus_notes=focus_notes or "",
        )
        focus_keywords = self._extract_focus_keywords(focus_notes)
        if not owner or not repo:
            extract.error = f"invalid repo_full_name: {repo_full_name}"
            return extract
        if not token:
            extract.error = "no GitHub token available"
            return extract

        try:
            storage = GitHubStorageService(
                token=token,
                owner=owner,
                repo=repo,
                branch=branch,
                base_path="",  # بدون base_path — مسیر مستقیم در ریپو
            )
            try:
                # list_folder("", recursive=True) → همه فایل‌ها در ریشه
                # برخی recursive listing را GitHub با Tree API بهتر انجام می‌دهد،
                # ولی list_folder موجود کافی است برای اولین نسخه.
                root_files = await storage.list_folder("", recursive=True)
            finally:
                await storage.close()

            # فیلتر scannable و سپس مرتب بر اساس priority
            scannable = [f for f in root_files if f.type == "file" and self._is_scannable(f.path)]
            extract.total_files_in_repo = len(root_files)

            # مرتب‌سازی بر اساس priority (با focus boost) سپس size صعودی
            scannable.sort(
                key=lambda f: (-self._priority_score(f.path, focus_keywords), f.size)
            )

            # محدود به max_files_per_repo
            selected = scannable[: self.max_files_per_repo]

            # خواندن محتوای هر فایل (parallel در batch‌های کوچک)
            file_summaries: List[FileSummary] = []
            for f in selected:
                summary = FileSummary(
                    path=f.path,
                    size=f.size,
                )
                # دسته‌بندی فایل
                summary.category, summary.role = self._classify_file_path(f.path)
                file_summaries.append(summary)

            # batch read محتوا (مستقل از scan، چون list_folder خود محتوای فایل را نمی‌دهد)
            # برای جلوگیری از فشار: حداکثر 10 concurrent
            sem = asyncio.Semaphore(10)
            storage2 = GitHubStorageService(
                token=token,
                owner=owner,
                repo=repo,
                branch=branch,
                base_path="",
            )

            async def _fetch(fs: FileSummary) -> None:
                async with sem:
                    try:
                        result = await storage2.get_file(fs.path)
                        if result and result.get("content") is not None:
                            content = str(result["content"])
                            if len(content) > self.max_file_chars:
                                fs.content_excerpt = content[: self.max_file_chars]
                                fs.is_truncated = True
                            else:
                                fs.content_excerpt = content
                    except Exception as e:
                        logger.debug(f"scan: get_file failed {fs.path}: {e}")

            try:
                await asyncio.gather(*(_fetch(fs) for fs in file_summaries))
            finally:
                await storage2.close()

            extract.files = file_summaries
            extract.scanned_files = len(file_summaries)
        except Exception as e:
            logger.warning(f"scan_project failed for {repo_full_name}: {e}")
            extract.error = str(e)

        return extract

    # ---------------- Step 6: Classify ----------------

    @staticmethod
    def _classify_file_path(path: str) -> Tuple[str, str]:
        """طبقه‌بندی heuristic فایل بر اساس مسیر (نه محتوا).

        return (category, role)
        category: backend|frontend|config|docs|test|migration|other
        role: model|service|route|component|util|...
        """
        lower = path.lower()

        # category
        if any(p in lower for p in ["frontend/", "src/components/", "src/pages/", "src/app/", "src/views/", ".tsx", ".jsx", ".vue", ".svelte"]):
            category = "frontend"
        elif any(p in lower for p in ["backend/", "app/", "api/", "server/", "src/services/", "src/lib/"]):
            category = "backend"
        elif any(p in lower for p in ["test/", "tests/", "__tests__/", "spec/", "_test.", ".spec.", ".test."]):
            category = "test"
        elif any(p in lower for p in ["migration", "alembic/", "/db/", "/sql/"]):
            category = "migration"
        elif any(p in lower for p in ["docs/", "doc/"]) or lower.endswith(".md"):
            category = "docs"
        elif any(p in lower for p in ["config", ".env", "docker", "ci/", ".github/", "settings"]):
            category = "config"
        else:
            category = "other"

        # role
        if "model" in lower or "schema" in lower:
            role = "model"
        elif any(p in lower for p in ["service.", "services/", "/service/"]):
            role = "service"
        elif any(p in lower for p in ["route", "router", "endpoint", "controller", "/api/"]):
            role = "route"
        elif any(p in lower for p in ["component", "/components/"]):
            role = "component"
        elif any(p in lower for p in ["/pages/", "/views/", "/app/"]):
            role = "page"
        elif any(p in lower for p in ["util", "helper", "lib"]):
            role = "util"
        elif "main" in lower or "index" in lower or "app.py" in lower:
            role = "entry"
        else:
            role = ""

        return (category, role)

    def classify(self, extracts: List[ProjectExtract]) -> ClassifiedInfo:
        """دسته‌بندی همه فایل‌های اسکن‌شده در buckets منطقی."""
        info = ClassifiedInfo()
        for extract in extracts:
            for fs in extract.files:
                cat, role = fs.category, fs.role
                # docs و architecture
                if cat == "docs" and any(
                    k in fs.path.upper() for k in ["README", "ARCHITECTURE"]
                ):
                    info.architecture_docs.append(fs)
                elif role == "model":
                    info.backend_models.append(fs)
                elif role == "service":
                    info.backend_services.append(fs)
                elif role == "route":
                    info.backend_routes.append(fs)
                elif role == "component":
                    info.frontend_components.append(fs)
                elif role == "page" and cat == "frontend":
                    info.frontend_pages.append(fs)
                elif cat == "config":
                    info.config_files.append(fs)
                else:
                    info.other.append(fs)
        return info

    # ---------------- Step 7: Fusion ----------------

    def build_fusion_text(
        self,
        extracts: List[ProjectExtract],
        classified: ClassifiedInfo,
        task_summary: str = "",
        current_project_profile: str = "",
    ) -> Tuple[str, bool]:
        """متن نهایی برای ادغام در پرامپت. respect max_total_chars.

        Returns (text, truncated)
        """
        lines: List[str] = []
        lines.append("## 📚 پروژه‌های مرجع (Reference Projects)")
        lines.append("")
        lines.append(
            "کاربر این پروژه‌ها را به‌عنوان منبع الهام برای این تسک انتخاب "
            "کرده است. هدف از این بخش: الگوها، معماری، یا منطق این پروژه‌ها "
            "را در نظر بگیر و در پیاده‌سازی **پروژهٔ فعلی** اعمال کن — نه "
            "کپی کردن صرف."
        )
        lines.append("")
        if task_summary:
            lines.append(f"**کار درخواست‌شده روی پروژهٔ فعلی:** {task_summary}")
            lines.append("")

        # 🆕 (current_project_profile) — قبل از مراجع، شناسنامهٔ پروژهٔ فعلی
        # را نمایش بده. AI باید **اول** این بخش را بخواند تا تفاوت‌های stack/
        # naming/dependency با مراجع را بفهمد.
        if current_project_profile and current_project_profile.strip():
            lines.append("### 🏠 شناسنامهٔ پروژهٔ فعلی (مرجع اصلی برای پیاده‌سازی)")
            lines.append("")
            lines.append(
                "**هرگاه بین پروژهٔ فعلی و پروژه‌های مرجع تفاوت بود (stack، "
                "نام‌گذاری، dependency)، پروژهٔ فعلی برنده است. هرگز syntax "
                "یا dependency پروژه‌های مرجع را کورکورانه به پروژهٔ فعلی نیاور.**"
            )
            lines.append("")
            lines.append(current_project_profile.strip())
            lines.append("")
            lines.append("---")
            lines.append("")

        # خلاصه‌ی پروژه‌های اسکن‌شده
        lines.append("### پروژه‌های اسکن‌شده")
        lines.append("")
        for extract in extracts:
            if extract.error:
                lines.append(
                    f"- ❌ `{extract.project_path}` — خطا در اسکن: {extract.error}"
                )
            else:
                lines.append(
                    f"- ✅ `{extract.project_path}` — "
                    f"{extract.scanned_files} فایل اسکن‌شده "
                    f"(از {extract.total_files_in_repo} کل)"
                )
            # 🆕 (focus_notes) — صراحت دهی روی نقطهٔ تمرکز کاربر برای این پروژه.
            # AI باید **فقط** الگوهای مرتبط با focus_notes را برداشت کند.
            if extract.focus_notes and extract.focus_notes.strip():
                lines.append(
                    f"  - 🎯 **نقطهٔ تمرکز کاربر**: "
                    f"_{extract.focus_notes.strip()}_"
                )
                lines.append(
                    f"    (فایل‌های اسکن‌شده بالا با اولویت بر اساس همین "
                    f"تمرکز انتخاب شده‌اند — به بقیهٔ پروژه توجه نکن مگر "
                    f"برای زمینه.)"
                )
        lines.append("")

        def _section(title: str, items: List[FileSummary], emoji: str = "📁") -> None:
            if not items:
                return
            lines.append(f"### {emoji} {title} ({len(items)} فایل)")
            lines.append("")
            for fs in items[:8]:  # حداکثر 8 فایل per category در fusion
                lines.append(f"**`{fs.path}`** ({fs.size} bytes)")
                if fs.content_excerpt:
                    # کوتاه نگه‌داری برای fusion
                    excerpt_short = fs.content_excerpt[:1500]
                    lines.append(f"```")
                    lines.append(excerpt_short)
                    if len(fs.content_excerpt) > 1500:
                        lines.append("...")
                    lines.append(f"```")
                lines.append("")

        _section("معماری و مستندات", classified.architecture_docs, "🏛")
        _section("مدل‌های Backend", classified.backend_models, "🧬")
        _section("سرویس‌های Backend", classified.backend_services, "⚙️")
        _section("Route ها و Endpoint ها", classified.backend_routes, "🔗")
        _section("Component های Frontend", classified.frontend_components, "🧩")
        _section("صفحات Frontend", classified.frontend_pages, "🖼")
        _section("Config", classified.config_files, "🔧")

        # دستورالعمل ادغام
        lines.append("---")
        lines.append("")
        lines.append("### 💡 دستورالعمل ادغام")
        lines.append("")
        lines.append(
            "- الگوهای بالا را **شناسایی** کن: ساختار فایل‌ها، نام‌گذاری، "
            "patternهای معماری، روش‌های handle errors، …"
        )
        lines.append(
            "- اما **در پروژهٔ فعلی** پیاده‌سازی کن — با stack، نام‌گذاری، "
            "و سبک کد همان پروژه. نه stack پروژه‌های مرجع."
        )
        lines.append(
            "- اگر پروژه‌های مرجع stack متفاوت دارند (مثلاً Vue ولی پروژه "
            "فعلی React)، **منطق** را منتقل کن نه syntax را."
        )
        lines.append("")

        text = "\n".join(lines)
        truncated = False
        if len(text) > self.max_total_chars:
            text = text[: self.max_total_chars] + "\n\n... [truncated at max_total_chars]"
            truncated = True
        return text, truncated

    # ---------------- High-level entrypoint ----------------

    async def build_reference_context(
        self,
        selected_projects: List[Dict[str, Any]],
        *,
        task_summary: str = "",
        token: str = "",
        watched_lookup: Optional[Dict[str, Any]] = None,
        current_project_profile: str = "",
    ) -> ReferenceContext:
        """نقطهٔ ورود اصلی — یک snapshot کامل از پروژه‌های مرجع می‌سازد.

        Args:
          selected_projects: لیست {project_id, project_path, is_selected}
          task_summary: خلاصهٔ کار درخواستی (برای زمینه)
          token: GitHub token
          watched_lookup: اختیاری — dict از project_id → WatchedProject
              برای دسترسی به default_branch هر پروژه (اگر بدون آن، default 'main')

        Returns:
          ReferenceContext با همه‌ی اطلاعات + fusion_text آماده
        """
        # فیلتر فقط selected
        active = [
            sp for sp in (selected_projects or [])
            if sp.get("is_selected") and sp.get("project_path")
        ]
        if not active:
            return ReferenceContext(
                project_extracts=[],
                classified=ClassifiedInfo(),
                fusion_text="",
                total_chars=0,
            )

        # اسکن هر پروژه به‌صورت موازی
        async def _scan_one(sp: Dict[str, Any]) -> ProjectExtract:
            branch = "main"
            if watched_lookup:
                watched = watched_lookup.get(sp.get("project_id", ""))
                if watched is not None:
                    branch = getattr(watched, "default_branch", None) or "main"
            return await self.scan_project(
                project_id=sp.get("project_id", ""),
                repo_full_name=sp.get("project_path", ""),
                token=token,
                branch=branch,
                focus_notes=str(sp.get("focus_notes") or ""),
            )

        extracts = await asyncio.gather(*(_scan_one(sp) for sp in active))

        # دسته‌بندی
        classified = self.classify(extracts)

        # fusion
        fusion_text, truncated = self.build_fusion_text(
            extracts,
            classified,
            task_summary=task_summary,
            current_project_profile=current_project_profile,
        )

        return ReferenceContext(
            project_extracts=extracts,
            classified=classified,
            fusion_text=fusion_text,
            total_chars=len(fusion_text),
            truncated_at_total_limit=truncated,
        )


# Singleton
_service_instance: Optional[ReferenceProjectService] = None


def get_reference_project_service() -> ReferenceProjectService:
    """دریافت instance singleton سرویس."""
    global _service_instance
    if _service_instance is None:
        _service_instance = ReferenceProjectService()
    return _service_instance
