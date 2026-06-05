# -*- coding: utf-8 -*-
"""
📚 Knowledge Center Service — مرکز دانش / دانشنامهٔ تجربیات

این سرویس قابلیت‌های صفحهٔ «مرکز دانش» را پیاده می‌کند:

فاز ۱ — سینک پوشهٔ تجربیات (experiences):
  - برای هر پروژهٔ تحت نظارت (مرکز نظارت / oversight)، یک پوشهٔ
    `experiences/` در ریشهٔ مخزن آن ساخته می‌شود (GitHub یا local).
    عملیات idempotent است: فقط اگر پوشه نبود ساخته می‌شود.
  - هر پروژهٔ جدیدی که تحت نظارت قرار می‌گیرد بلافاصله پوشهٔ
    experiences اش ساخته می‌شود (hook در oversight_service.add_watched).
  - `sync_experiences()` محتوای پوشه‌های experiences همهٔ پروژه‌ها را
    می‌خواند و در index مرکز دانش (entries.json) ذخیره/به‌روز می‌کند.

فاز ۲ — ایمپورت و استخراج تجربه از چت‌ها:
  - `import_chat()` فایل‌های چت (txt/md/html/pdf) را می‌پذیرد، با chunking
    از محدودیت توکن عبور می‌کند، با AI فعال (Claude Code token و …) چالش/
    راه‌حل را استخراج می‌کند و به دانشنامه اضافه می‌کند.
  - منطق merge/dedup: اگر موضوع مشابهی از قبل وجود داشت، دادهٔ مفید جدید
    ادغام می‌شود (نه تکراری، نه overwrite) و reference منبع ثبت می‌شود.

ساختار entry در index:
  {
    "id": str,
    "title": str,
    "category": str,
    "summary": str,
    "content": str,                # markdown متن کامل تجربه
    "source": "experiences_folder" | "chat_import",
    "project": Optional[str],       # repo_full_name برای منبع پوشه
    "references": [ {"source": str, "added_at": iso} ],
    "tags": [str],
    "created_at": iso,
    "updated_at": iso,
  }
"""

from __future__ import annotations

import os
import re
import json
import uuid
import asyncio
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# نام‌های پذیرفته‌شده برای پوشهٔ تجربیات (همان چیزی که کاربر گفت:
# «اکسپرینس، اکسپرینسز یا تجربیات»). برای ساخت از اولی استفاده می‌کنیم،
# ولی هنگام خواندن همهٔ این نام‌ها را تشخیص می‌دهیم.
EXPERIENCES_DIRNAME = "experiences"
EXPERIENCES_ALIASES = ("experiences", "experience", "تجربیات")

# نگه‌دارندهٔ پوشهٔ خالی در GitHub (git پوشهٔ خالی را نگه نمی‌دارد)
GITKEEP_NAME = ".gitkeep"
GITKEEP_CONTENT = (
    "# پوشهٔ تجربیات (Experiences)\n\n"
    "این پوشه توسط «مرکز دانش» ساخته شده است. هر فایل تجربه که اینجا قرار\n"
    "بگیرد به‌صورت منظم با صفحهٔ مرکز دانش سینک می‌شود.\n"
)

# حداکثر اندازهٔ chunk برای عبور از محدودیت توکن (تقریبی بر اساس کاراکتر).
# ~12k کاراکتر ≈ 3-4k توکن — برای اغلب مدل‌ها امن است.
DEFAULT_CHUNK_CHARS = 12000


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_storage_dir() -> Path:
    """مسیر قابل‌نوشتن برای ذخیرهٔ index مرکز دانش. مشابه oversight با fallback."""
    candidates = [
        os.environ.get("KNOWLEDGE_CENTER_STORAGE", "").strip(),
        os.environ.get("OVERSIGHT_STORAGE", "").strip(),
        "./storage/knowledge_center",
        "/tmp/knowledge_center",
    ]
    for c in candidates:
        if not c:
            continue
        try:
            p = Path(c)
            # اگر مسیر oversight بود، یک زیرپوشه بساز تا قاطی نشود
            if c == os.environ.get("OVERSIGHT_STORAGE", "").strip() and c:
                p = p / "knowledge_center"
            p.mkdir(parents=True, exist_ok=True)
            test = p / ".write_test"
            test.write_text("ok", encoding="utf-8")
            test.unlink(missing_ok=True)
            return p
        except Exception as e:
            logger.warning(f"knowledge_center storage path '{c}' not writable: {e}")
            continue
    logger.warning("knowledge_center: no writable storage — using /tmp ephemeral")
    return Path("/tmp")


STORAGE_DIR = _resolve_storage_dir()
ENTRIES_FILE = STORAGE_DIR / "entries.json"


def _normalize_topic_key(title: str) -> str:
    """کلید نرمال‌شده برای dedup/merge بر اساس عنوان موضوع.

    حروف کوچک، حذف نشانه‌گذاری، فشرده‌سازی فاصله‌ها. مثال کاربر:
    «لاگین کردن با جیمیل» در چت‌های مختلف باید یک کلید بدهد.
    """
    if not title:
        return ""
    t = title.strip().lower()
    # حذف نشانه‌گذاری رایج (فارسی و لاتین)
    t = re.sub(r"[،؛؟!\"#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


# ============================================================
# File parsing — txt / md / html / pdf
# ============================================================

def _strip_html(html: str) -> str:
    """تبدیل HTML به متن ساده بدون وابستگی به bs4 (که در requirements نیست)."""
    # حذف script/style
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    # تبدیل break/paragraph به newline برای حفظ ساختار
    html = re.sub(r"(?i)<(br|/p|/div|/li|/tr|/h[1-6])\s*/?>", "\n", html)
    # حذف بقیهٔ تگ‌ها
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    # decode چند entity رایج
    entities = {
        "&nbsp;": " ", "&amp;": "&", "&lt;": "<", "&gt;": ">",
        "&quot;": '"', "&#39;": "'", "&apos;": "'",
    }
    for k, v in entities.items():
        text = text.replace(k, v)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


def _parse_pdf(content: bytes) -> str:
    """استخراج متن از PDF با pypdf (در requirements موجود است)."""
    try:
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(content))
        parts: List[str] = []
        for page in reader.pages:
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                continue
        return "\n\n".join(parts).strip()
    except Exception as e:
        logger.warning(f"pdf parse failed: {e}")
        return ""


def parse_file_to_text(filename: str, content: bytes, mime: str = "") -> str:
    """تبدیل فایل آپلودشده (txt/md/html/pdf) به متن خام.

    فرمت بر اساس extension و mime تشخیص داده می‌شود.
    """
    name = (filename or "").lower()
    mime = (mime or "").lower()

    is_pdf = name.endswith(".pdf") or "pdf" in mime
    is_html = name.endswith((".html", ".htm")) or "html" in mime
    # txt, md و هر چیز دیگر → متن مستقیم

    if is_pdf:
        return _parse_pdf(content)

    # decode متن
    try:
        text = content.decode("utf-8")
    except Exception:
        try:
            text = content.decode("utf-8", errors="ignore")
        except Exception:
            text = ""

    if is_html:
        return _strip_html(text)

    return text.strip()


def chunk_text(text: str, max_chars: int = DEFAULT_CHUNK_CHARS) -> List[str]:
    """تقسیم متن به chunkهای قابل‌مدیریت برای عبور از محدودیت توکن.

    سعی می‌کند روی مرز پاراگراف بشکند تا context هر chunk حفظ شود.
    """
    text = text or ""
    if len(text) <= max_chars:
        return [text] if text.strip() else []

    chunks: List[str] = []
    paragraphs = text.split("\n\n")
    current = ""
    for para in paragraphs:
        # اگر خود پاراگراف از max بزرگ‌تر بود، به‌اجبار تکه‌تکه کن
        if len(para) > max_chars:
            if current.strip():
                chunks.append(current.strip())
                current = ""
            for i in range(0, len(para), max_chars):
                chunks.append(para[i:i + max_chars].strip())
            continue
        if len(current) + len(para) + 2 > max_chars:
            if current.strip():
                chunks.append(current.strip())
            current = para
        else:
            current = f"{current}\n\n{para}" if current else para
    if current.strip():
        chunks.append(current.strip())
    return [c for c in chunks if c.strip()]


# ============================================================
# Service
# ============================================================

class KnowledgeCenterService:
    """سرویس مرکز دانش — سینک تجربیات + ایمپورت/استخراج چت + merge/dedup."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: List[Dict[str, Any]] = []
        self._load()

    # ---------- persistence ----------

    def _load(self) -> None:
        try:
            if ENTRIES_FILE.exists():
                data = json.loads(ENTRIES_FILE.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self._entries = data.get("entries", []) or []
                elif isinstance(data, list):
                    self._entries = data
        except Exception as e:
            logger.warning(f"knowledge_center: failed to load entries: {e}")
            self._entries = []

    def _save(self) -> None:
        try:
            ENTRIES_FILE.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "version": 1,
                "generated_at": _now_iso(),
                "total": len(self._entries),
                "entries": self._entries,
            }
            tmp = ENTRIES_FILE.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            tmp.replace(ENTRIES_FILE)
        except Exception as e:
            logger.warning(f"knowledge_center: failed to save entries: {e}")

    # ---------- read API ----------

    def get_entries(self, category: Optional[str] = None) -> Dict[str, Any]:
        """لیست فهرست‌بندی‌شدهٔ تجربیات + TOC + دسته‌بندی.

        خروجی برای صفحهٔ دانشنامه‌ای (TOC + categorized list).
        """
        with self._lock:
            entries = list(self._entries)

        if category:
            entries = [e for e in entries if e.get("category") == category]

        # دسته‌بندی
        categories: Dict[str, List[Dict[str, Any]]] = {}
        for e in entries:
            cat = e.get("category") or "عمومی"
            categories.setdefault(cat, []).append(e)

        # TOC: فهرست عنوان‌ها گروه‌بندی‌شده بر اساس دسته
        toc = [
            {
                "category": cat,
                "count": len(items),
                "items": [
                    {"id": it["id"], "title": it.get("title", "")}
                    for it in items
                ],
            }
            for cat, items in sorted(categories.items())
        ]

        return {
            "total": len(entries),
            "entries": entries,
            "categories": sorted(categories.keys()),
            "toc": toc,
        }

    def get_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            for e in self._entries:
                if e.get("id") == entry_id:
                    return dict(e)
        return None

    # ---------- merge / dedup ----------

    def _find_existing_by_topic(self, title: str) -> Optional[Dict[str, Any]]:
        key = _normalize_topic_key(title)
        if not key:
            return None
        for e in self._entries:
            if _normalize_topic_key(e.get("title", "")) == key:
                return e
        return None

    def upsert_entry(self, new_entry: Dict[str, Any]) -> Dict[str, Any]:
        """افزودن یا ادغام یک تجربه (منطق merge/dedup).

        اگر موضوع مشابهی از قبل موجود باشد:
          - داده‌های مفید جدید به content موجود اضافه (append) می‌شوند،
            بدون حذف چیزی و بدون overwrite.
          - reference منبع جدید ثبت می‌شود.
        در غیر این‌صورت یک entry جدید ساخته می‌شود.

        thread-safe و persist می‌کند.
        """
        with self._lock:
            return self._upsert_entry_locked(new_entry, persist=True)

    def _upsert_entry_locked(
        self, new_entry: Dict[str, Any], persist: bool = True
    ) -> Dict[str, Any]:
        title = (new_entry.get("title") or "").strip() or "تجربهٔ بدون عنوان"
        content = (new_entry.get("content") or "").strip()
        source = new_entry.get("source") or "manual"
        source_ref = new_entry.get("source_ref") or new_entry.get("project") or source
        now = _now_iso()

        existing = self._find_existing_by_topic(title)
        if existing is not None:
            # merge — فقط اگر دادهٔ جدید قبلاً نبوده اضافه کن (جلوگیری از تکرار)
            existing_content = existing.get("content", "") or ""
            merged = existing_content
            if content and content not in existing_content:
                merged = (
                    f"{existing_content}\n\n---\n\n"
                    f"### افزوده‌شده از: {source_ref} ({now[:10]})\n\n{content}"
                ).strip()
            existing["content"] = merged
            # ثبت reference منبع
            refs = existing.setdefault("references", [])
            if not any(r.get("source") == source_ref for r in refs):
                refs.append({"source": source_ref, "added_at": now})
            # ادغام tagها
            tags = set(existing.get("tags", []) or [])
            tags.update(new_entry.get("tags", []) or [])
            existing["tags"] = sorted(tags)
            existing["updated_at"] = now
            if persist:
                self._save()
            return dict(existing)

        entry = {
            "id": new_entry.get("id") or str(uuid.uuid4()),
            "title": title,
            "category": new_entry.get("category") or "عمومی",
            "summary": (new_entry.get("summary") or "").strip(),
            "content": content,
            "source": source,
            "project": new_entry.get("project"),
            "references": [{"source": source_ref, "added_at": now}],
            "tags": sorted(set(new_entry.get("tags", []) or [])),
            "created_at": now,
            "updated_at": now,
        }
        self._entries.append(entry)
        if persist:
            self._save()
        return dict(entry)

    # ---------- experiences folder (GitHub / local) ----------

    async def ensure_experiences_folder(
        self, project: Dict[str, Any]
    ) -> Dict[str, Any]:
        """ساخت پوشهٔ `experiences/` در مخزن یک پروژهٔ تحت نظارت.

        idempotent — فقط اگر پوشه نبود ساخته می‌شود (با ثبت .gitkeep).
        پروژه می‌تواند GitHub (repo_full_name) یا local (local_path) باشد.

        Args:
            project: dict پروژهٔ watched شامل repo_full_name / repo_url /
                     default_branch و یا local_path.
        Returns:
            {"success": bool, "created": bool, "location": str, "error"?: str}
        """
        repo_full_name = (project.get("repo_full_name") or "").strip()
        local_path = (project.get("local_path") or "").strip()
        branch = project.get("default_branch") or "main"

        # حالت local — پوشهٔ فایل‌سیستمی
        if local_path and not repo_full_name:
            try:
                folder = Path(local_path) / EXPERIENCES_DIRNAME
                created = not folder.exists()
                folder.mkdir(parents=True, exist_ok=True)
                keep = folder / GITKEEP_NAME
                if not keep.exists():
                    keep.write_text(GITKEEP_CONTENT, encoding="utf-8")
                return {
                    "success": True,
                    "created": created,
                    "location": str(folder),
                }
            except Exception as e:
                return {"success": False, "created": False, "error": str(e)}

        if not repo_full_name or "/" not in repo_full_name:
            return {
                "success": False,
                "created": False,
                "error": "no repo_full_name or local_path",
            }

        # حالت GitHub — از طریق contents API (idempotent)
        try:
            from .github_pr_service import get_github_pr_service
            gh = get_github_pr_service()
            owner, repo = repo_full_name.split("/", 1)

            keep_path = f"{EXPERIENCES_DIRNAME}/{GITKEEP_NAME}"
            # بررسی وجود — اگر هست، no-op
            existing_sha = await gh.get_file_sha(owner, repo, keep_path, branch)
            if existing_sha:
                return {
                    "success": True,
                    "created": False,
                    "location": f"{repo_full_name}/{EXPERIENCES_DIRNAME}",
                }
            # هم‌چنین اگر هر فایل دیگری داخل پوشه باشد، یعنی پوشه از قبل هست
            listing = await self.list_experience_files(project)
            if listing.get("success") and listing.get("files"):
                return {
                    "success": True,
                    "created": False,
                    "location": f"{repo_full_name}/{EXPERIENCES_DIRNAME}",
                }

            result = await gh.create_or_update_file(
                owner=owner,
                repo=repo,
                path=keep_path,
                content=GITKEEP_CONTENT,
                message="chore(knowledge-center): ساخت پوشهٔ experiences",
                branch=branch,
            )
            if result.get("success"):
                return {
                    "success": True,
                    "created": True,
                    "location": f"{repo_full_name}/{EXPERIENCES_DIRNAME}",
                }
            return {
                "success": False,
                "created": False,
                "error": result.get("error", "github create failed"),
            }
        except Exception as e:
            logger.warning(
                f"ensure_experiences_folder failed for {repo_full_name}: {e}"
            )
            return {"success": False, "created": False, "error": str(e)}

    async def ensure_all_experiences_folders(self) -> Dict[str, Any]:
        """برای همهٔ پروژه‌های تحت نظارت، پوشهٔ experiences را تضمین می‌کند."""
        projects = await self._get_watched_projects()
        results: List[Dict[str, Any]] = []
        created = 0
        for p in projects:
            r = await self.ensure_experiences_folder(p)
            r["project"] = p.get("repo_full_name") or p.get("local_path")
            results.append(r)
            if r.get("created"):
                created += 1
        return {
            "success": True,
            "total_projects": len(projects),
            "folders_created": created,
            "results": results,
        }

    async def list_experience_files(
        self, project: Dict[str, Any]
    ) -> Dict[str, Any]:
        """لیست فایل‌های داخل پوشهٔ experiences یک پروژه (GitHub یا local)."""
        repo_full_name = (project.get("repo_full_name") or "").strip()
        local_path = (project.get("local_path") or "").strip()
        branch = project.get("default_branch") or "main"

        if local_path and not repo_full_name:
            files: List[Dict[str, Any]] = []
            for alias in EXPERIENCES_ALIASES:
                folder = Path(local_path) / alias
                if folder.is_dir():
                    for f in sorted(folder.glob("*")):
                        if f.is_file() and f.name != GITKEEP_NAME:
                            files.append({"name": f.name, "path": str(f)})
                    break
            return {"success": True, "files": files}

        if not repo_full_name or "/" not in repo_full_name:
            return {"success": False, "files": [], "error": "no repo"}

        try:
            from .github_pr_service import get_github_pr_service
            gh = get_github_pr_service()
            owner, repo = repo_full_name.split("/", 1)
            headers = gh._get_headers()
            for alias in EXPERIENCES_ALIASES:
                url = f"{gh.GITHUB_API}/repos/{owner}/{repo}/contents/{alias}"
                if branch:
                    url += f"?ref={branch}"
                res = await gh._gh_request("GET", url, headers=headers)
                if res.get("ok") and isinstance(res.get("body_json"), list):
                    files = [
                        {"name": it.get("name"), "path": it.get("path")}
                        for it in res["body_json"]
                        if it.get("type") == "file" and it.get("name") != GITKEEP_NAME
                    ]
                    return {"success": True, "files": files, "dir": alias}
            return {"success": True, "files": []}
        except Exception as e:
            return {"success": False, "files": [], "error": str(e)}

    async def _read_experience_file(
        self, project: Dict[str, Any], file_path: str
    ) -> str:
        repo_full_name = (project.get("repo_full_name") or "").strip()
        local_path = (project.get("local_path") or "").strip()
        branch = project.get("default_branch") or "main"

        if local_path and not repo_full_name:
            try:
                return Path(file_path).read_text(encoding="utf-8")
            except Exception:
                return ""
        try:
            from .github_pr_service import get_github_pr_service
            gh = get_github_pr_service()
            owner, repo = repo_full_name.split("/", 1)
            res = await gh.get_file_content(owner, repo, file_path, branch)
            return res.get("content", "") if res.get("success") else ""
        except Exception:
            return ""

    async def sync_experiences(self) -> Dict[str, Any]:
        """محتوای پوشه‌های experiences همهٔ پروژه‌ها را می‌خواند و در index
        مرکز دانش ذخیره/به‌روز می‌کند (سینک).

        هر فایل تجربه به یک entry تبدیل می‌شود؛ منطق merge/dedup اعمال
        می‌شود تا موضوعات تکراری ادغام شوند.
        """
        projects = await self._get_watched_projects()
        synced = 0
        for p in projects:
            listing = await self.list_experience_files(p)
            if not listing.get("success"):
                continue
            for f in listing.get("files", []):
                fpath = f.get("path") or ""
                if not fpath:
                    continue
                content = await self._read_experience_file(p, fpath)
                if not content.strip():
                    continue
                title, summary = self._derive_title_summary(
                    content, fallback=f.get("name", "")
                )
                self.upsert_entry({
                    "title": title,
                    "category": self._guess_category(content, title),
                    "summary": summary,
                    "content": content,
                    "source": "experiences_folder",
                    "project": p.get("repo_full_name") or p.get("local_path"),
                    "source_ref": f"{p.get('repo_full_name') or p.get('local_path')}/{fpath}",
                })
                synced += 1
        return {"success": True, "files_synced": synced, "total": len(self._entries)}

    # ---------- chat import / AI extraction ----------

    async def import_chat(
        self,
        filename: str,
        content: bytes,
        mime: str = "",
    ) -> Dict[str, Any]:
        """ایمپورت یک فایل چت و استخراج تجربیات.

        فرمت‌های txt/md/html/pdf را می‌پذیرد، با chunking از محدودیت توکن
        عبور می‌کند، با AI فعال چالش/راه‌حل را استخراج می‌کند و با merge/
        dedup به دانشنامه اضافه می‌کند.
        """
        text = parse_file_to_text(filename, content, mime)
        if not text.strip():
            return {
                "success": False,
                "error": "فایل خالی است یا قابل استخراج نبود",
                "entries": [],
            }

        chunks = chunk_text(text)
        extracted: List[Dict[str, Any]] = []
        for idx, chunk in enumerate(chunks):
            items = await self._extract_experiences(chunk, filename, idx, len(chunks))
            extracted.extend(items)

        # merge/dedup
        saved: List[Dict[str, Any]] = []
        for item in extracted:
            item.setdefault("source", "chat_import")
            item.setdefault("source_ref", filename)
            saved.append(self.upsert_entry(item))

        return {
            "success": True,
            "filename": filename,
            "chunks": len(chunks),
            "extracted": len(extracted),
            "entries": saved,
            "total": len(self._entries),
        }

    async def _extract_experiences(
        self, chunk: str, filename: str, idx: int, total: int
    ) -> List[Dict[str, Any]]:
        """استخراج تجربه از یک chunk چت — اول با AI، در صورت شکست heuristic."""
        ai_items = await self._extract_with_ai(chunk, filename)
        if ai_items:
            return ai_items
        return self._heuristic_extract(chunk, filename, idx, total)

    async def _extract_with_ai(
        self, chunk: str, filename: str
    ) -> List[Dict[str, Any]]:
        """استفاده از AI فعال (Claude Code token و …) برای استخراج چالش/راه‌حل.

        خروجی JSON: لیستی از {title, category, summary, content, tags}.
        تجربه باید general نوشته شود (نه مختص یک پروژهٔ خاص).
        در صورت نبود AI یا خطا، لیست خالی برمی‌گرداند (caller به heuristic
        برمی‌گردد).
        """
        try:
            from .ai_manager import get_ai_manager
            from .ai_base import Message

            manager = get_ai_manager()
            providers = manager.get_available_providers()
            if not providers:
                return []
            models = manager.get_available_models()
            if not models:
                return []
            model_id = models[0].id if hasattr(models[0], "id") else str(models[0])

            system_prompt = (
                "تو یک دستیار استخراج دانش هستی. از متن چت زیر، تجربیات قابل‌"
                "استفادهٔ مجدد را استخراج کن: چه چالشی بوده، آیا حل شده و چگونه. "
                "تجربه را general بنویس (به نام پروژهٔ خاص اشاره نکن؛ بگو چنین "
                "مشکلی چگونه حل می‌شود تا در موارد مشابه قابل استفاده باشد). "
                "خروجی فقط JSON معتبر باشد به شکل آرایه‌ای از اشیاء با کلیدهای: "
                "title (عنوان موضوع), category (دسته), summary (خلاصهٔ یک‌خطی), "
                "content (markdown کامل راه‌حل), tags (آرایهٔ برچسب). اگر هیچ "
                "تجربهٔ ارزشمندی نبود، آرایهٔ خالی [] بده."
            )
            user_prompt = f"متن چت (فایل: {filename}):\n\n{chunk}"

            resp = await manager.generate(
                model_id=model_id,
                messages=[
                    Message(role="system", content=system_prompt),
                    Message(role="user", content=user_prompt),
                ],
                max_tokens=4096,
                temperature=0.2,
                task_type="extraction",
            )
            content = (resp.content or "").strip()
            items = self._parse_ai_json(content)
            # نرمال‌سازی
            out: List[Dict[str, Any]] = []
            for it in items:
                if not isinstance(it, dict):
                    continue
                title = (it.get("title") or "").strip()
                body = (it.get("content") or "").strip()
                if not title and not body:
                    continue
                out.append({
                    "title": title or "تجربهٔ استخراج‌شده",
                    "category": (it.get("category") or "عمومی").strip(),
                    "summary": (it.get("summary") or "").strip(),
                    "content": body or title,
                    "tags": it.get("tags") or [],
                    "source": "chat_import",
                    "source_ref": filename,
                })
            return out
        except Exception as e:
            logger.debug(f"AI extraction unavailable/failed: {e}")
            return []

    @staticmethod
    def _parse_ai_json(content: str) -> List[Any]:
        """استخراج آرایهٔ JSON از خروجی مدل (با حذف code fence احتمالی)."""
        if not content:
            return []
        # حذف ```json ... ```
        m = re.search(r"```(?:json)?\s*(.*?)```", content, re.DOTALL)
        if m:
            content = m.group(1).strip()
        # پیدا کردن اولین [ تا آخرین ]
        start = content.find("[")
        end = content.rfind("]")
        if start != -1 and end != -1 and end > start:
            content = content[start:end + 1]
        try:
            data = json.loads(content)
            return data if isinstance(data, list) else [data]
        except Exception:
            return []

    def _heuristic_extract(
        self, chunk: str, filename: str, idx: int, total: int
    ) -> List[Dict[str, Any]]:
        """استخراج پایه بدون AI — یک تجربه per chunk می‌سازد.

        این fallback تضمین می‌کند ایمپورت حتی بدون AI فعال کار کند
        (مثلاً در محیط تست) و داده از دست نرود.
        """
        title, summary = self._derive_title_summary(chunk, fallback=filename)
        if total > 1:
            title = f"{title} (بخش {idx + 1}/{total})"
        return [{
            "title": title,
            "category": self._guess_category(chunk, title),
            "summary": summary,
            "content": chunk,
            "tags": [],
            "source": "chat_import",
            "source_ref": filename,
        }]

    # ---------- helpers ----------

    @staticmethod
    def _derive_title_summary(content: str, fallback: str = "") -> Tuple[str, str]:
        """استخراج عنوان و خلاصه از متن (اولین heading یا اولین خط معنادار)."""
        lines = [l.strip() for l in (content or "").splitlines() if l.strip()]
        title = ""
        for l in lines:
            # markdown heading
            mh = re.match(r"^#{1,6}\s+(.*)", l)
            if mh:
                title = mh.group(1).strip()
                break
        if not title and lines:
            title = lines[0][:120]
        if not title:
            title = Path(fallback).stem if fallback else "تجربه"
        # خلاصه: اولین چند خط غیر-heading
        body_lines = [l for l in lines if not l.startswith("#")]
        summary = " ".join(body_lines)[:240] if body_lines else title[:240]
        return title.strip(), summary.strip()

    @staticmethod
    def _guess_category(content: str, title: str) -> str:
        """حدس دستهٔ تجربه بر اساس کلیدواژه‌ها — برای دسته‌بندی دانشنامه."""
        text = f"{title}\n{content}".lower()
        rules = [
            ("احراز هویت", ["login", "auth", "oauth", "jwt", "session", "لاگین", "ورود", "احراز"]),
            ("پایگاه داده", ["database", "sql", "postgres", "migration", "query", "دیتابیس", "مهاجرت"]),
            ("استقرار", ["deploy", "docker", "render", "ci/cd", "kubernetes", "استقرار", "دیپلوی"]),
            ("فرانت‌اند", ["react", "next", "css", "component", "frontend", "فرانت", "کامپوننت"]),
            ("بک‌اند/API", ["api", "endpoint", "fastapi", "rest", "graphql", "بک‌اند", "اندپوینت"]),
            ("تست", ["test", "pytest", "jest", "e2e", "تست"]),
            ("امنیت", ["security", "xss", "csrf", "vulnerab", "امنیت", "آسیب‌پذیری"]),
            ("هوش مصنوعی", ["ai", "llm", "prompt", "token", "model", "هوش مصنوعی", "مدل"]),
        ]
        for cat, kws in rules:
            if any(kw in text for kw in kws):
                return cat
        return "عمومی"

    async def _get_watched_projects(self) -> List[Dict[str, Any]]:
        """دریافت لیست پروژه‌های تحت نظارت از سرویس مرکز نظارت (oversight).

        lazy import برای جلوگیری از circular import.
        """
        try:
            from .oversight_service import get_oversight_service
            svc = get_oversight_service()
            watched = await svc.list_watched()
            return watched or []
        except Exception as e:
            logger.warning(f"knowledge_center: cannot read watched projects: {e}")
            return []


_kc_instance: Optional[KnowledgeCenterService] = None


def get_knowledge_center_service() -> KnowledgeCenterService:
    """دریافت نمونهٔ singleton سرویس مرکز دانش."""
    global _kc_instance
    if _kc_instance is None:
        _kc_instance = KnowledgeCenterService()
    return _kc_instance
