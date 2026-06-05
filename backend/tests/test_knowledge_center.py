# -*- coding: utf-8 -*-
"""Tests for the Knowledge Center (مرکز دانش) feature.

پوشش:
  - parsing فرمت‌های مختلف (txt/md/html) و chunking برای فایل حجیم
  - منطق merge/dedup هنگام افزودن تجربهٔ تکراری (ادغام + reference)
  - ساختار خروجی entries (TOC + categories) برای صفحهٔ دانشنامه‌ای
  - ensure_experiences_folder برای پروژهٔ local
  - ایمپورت چت (با fallback heuristic وقتی AI فعال نیست)
  - endpoint GET /api/knowledge-center/entries با status 200
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# 🔒 ایزوله کردن storage قبل از import سرویس (تا روی repo ننویسد)
os.environ["KNOWLEDGE_CENTER_STORAGE"] = tempfile.mkdtemp(prefix="kc_test_")

import pytest  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import knowledge_center_service as kc  # noqa: E402
from app.services.knowledge_center_service import (  # noqa: E402
    KnowledgeCenterService,
    parse_file_to_text,
    chunk_text,
    _normalize_topic_key,
)


@pytest.fixture
def svc(tmp_path, monkeypatch):
    """نمونهٔ تازهٔ سرویس با storage ایزوله per-test."""
    entries_file = tmp_path / "entries.json"
    monkeypatch.setattr(kc, "ENTRIES_FILE", entries_file)
    return KnowledgeCenterService()


# ---------------------------------------------------------------------------
# parsing + chunking
# ---------------------------------------------------------------------------

def test_parse_txt():
    text = parse_file_to_text("note.txt", "سلام دنیا".encode("utf-8"), "text/plain")
    assert "سلام دنیا" in text


def test_parse_md():
    md = "# عنوان\n\nمتن تجربه".encode("utf-8")
    text = parse_file_to_text("exp.md", md, "text/markdown")
    assert "# عنوان" in text
    assert "متن تجربه" in text


def test_parse_html_strips_tags():
    html = "<html><body><h1>سلام</h1><p>پاراگراف</p><script>x=1</script></body></html>"
    text = parse_file_to_text("c.html", html.encode("utf-8"), "text/html")
    assert "سلام" in text
    assert "پاراگراف" in text
    assert "<h1>" not in text
    assert "x=1" not in text  # script باید حذف شود


def test_chunk_small_text_single():
    chunks = chunk_text("کوتاه")
    assert chunks == ["کوتاه"]


def test_chunk_large_text_splits():
    big = ("پاراگراف نمونه. " * 2000)  # > DEFAULT_CHUNK_CHARS
    chunks = chunk_text(big, max_chars=1000)
    assert len(chunks) > 1
    assert all(len(c) <= 1000 for c in chunks)


def test_normalize_topic_key():
    a = _normalize_topic_key("لاگین کردن با جیمیل!")
    b = _normalize_topic_key("لاگین کردن با جیمیل")
    assert a == b


# ---------------------------------------------------------------------------
# merge / dedup
# ---------------------------------------------------------------------------

def test_upsert_creates_entry(svc):
    e = svc.upsert_entry({
        "title": "اتصال به دیتابیس",
        "content": "راه حل اول",
        "source": "chat_import",
        "source_ref": "chat1.txt",
    })
    assert e["id"]
    assert e["title"] == "اتصال به دیتابیس"
    assert len(svc.get_entries()["entries"]) == 1


def test_upsert_merges_same_topic(svc):
    svc.upsert_entry({
        "title": "لاگین با جیمیل",
        "content": "راه حل قدیمی",
        "source": "chat_import",
        "source_ref": "chatA.txt",
    })
    merged = svc.upsert_entry({
        "title": "لاگین با جیمیل!",  # همان موضوع، نشانه‌گذاری متفاوت
        "content": "نکتهٔ جدید مفید",
        "source": "chat_import",
        "source_ref": "chatB.txt",
    })
    # فقط یک entry باید باشد (dedup)
    entries = svc.get_entries()["entries"]
    assert len(entries) == 1
    # هر دو محتوا حفظ شده (چیزی حذف نشده)
    assert "راه حل قدیمی" in merged["content"]
    assert "نکتهٔ جدید مفید" in merged["content"]
    # reference هر دو منبع ثبت شده
    sources = {r["source"] for r in merged["references"]}
    assert "chatA.txt" in sources
    assert "chatB.txt" in sources


def test_upsert_duplicate_content_not_repeated(svc):
    svc.upsert_entry({"title": "X", "content": "همان متن", "source_ref": "a"})
    e = svc.upsert_entry({"title": "X", "content": "همان متن", "source_ref": "a"})
    # متن تکراری نباید دوباره append شود
    assert e["content"].count("همان متن") == 1


# ---------------------------------------------------------------------------
# entries listing (TOC + categories)
# ---------------------------------------------------------------------------

def test_get_entries_toc_and_categories(svc):
    svc.upsert_entry({"title": "ورود با OAuth", "content": "auth login oauth", "source_ref": "a"})
    svc.upsert_entry({"title": "مهاجرت دیتابیس", "content": "database migration sql", "source_ref": "b"})
    result = svc.get_entries()
    assert result["total"] == 2
    assert "categories" in result
    assert "toc" in result
    # TOC باید گروه‌بندی‌شده باشد
    assert len(result["toc"]) >= 1
    for group in result["toc"]:
        assert "category" in group
        assert "items" in group


def test_get_entry_by_id(svc):
    e = svc.upsert_entry({"title": "تست", "content": "x", "source_ref": "a"})
    fetched = svc.get_entry(e["id"])
    assert fetched is not None
    assert fetched["id"] == e["id"]
    assert svc.get_entry("nonexistent") is None


# ---------------------------------------------------------------------------
# ensure_experiences_folder (local) — AC4
# ---------------------------------------------------------------------------

def test_service_has_ensure_method(svc):
    assert hasattr(svc, "ensure_experiences_folder")
    assert callable(svc.ensure_experiences_folder)


@pytest.mark.asyncio
async def test_ensure_experiences_folder_local(svc, tmp_path):
    proj_dir = tmp_path / "myproject"
    proj_dir.mkdir()
    result = await svc.ensure_experiences_folder({"local_path": str(proj_dir)})
    assert result["success"] is True
    assert result["created"] is True
    folder = proj_dir / "experiences"
    assert folder.is_dir()
    assert (folder / ".gitkeep").exists()
    # idempotent — بار دوم created=False
    result2 = await svc.ensure_experiences_folder({"local_path": str(proj_dir)})
    assert result2["success"] is True
    assert result2["created"] is False


# ---------------------------------------------------------------------------
# import_chat (heuristic fallback — بدون AI فعال)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_import_chat_creates_entries(svc, monkeypatch):
    # مطمئن شو AI در دسترس نیست → heuristic
    async def _no_ai(*a, **k):
        return []
    monkeypatch.setattr(svc, "_extract_with_ai", _no_ai)

    content = "# لاگین با گوگل\n\nچالش: ورود کاربر. راه‌حل: استفاده از OAuth.".encode("utf-8")
    result = await svc.import_chat("chat_export.md", content, "text/markdown")
    assert result["success"] is True
    assert result["extracted"] >= 1
    assert len(svc.get_entries()["entries"]) >= 1


@pytest.mark.asyncio
async def test_import_chat_empty_fails(svc):
    result = await svc.import_chat("empty.txt", b"   ", "text/plain")
    assert result["success"] is False


@pytest.mark.asyncio
async def test_import_chat_chunks_large(svc, monkeypatch):
    async def _no_ai(*a, **k):
        return []
    monkeypatch.setattr(svc, "_extract_with_ai", _no_ai)
    big = ("خط نمونه برای تست chunking.\n\n" * 3000).encode("utf-8")
    result = await svc.import_chat("big.txt", big, "text/plain")
    assert result["success"] is True
    assert result["chunks"] > 1


# ---------------------------------------------------------------------------
# endpoint — AC3: GET /api/knowledge-center/entries → 200
# ---------------------------------------------------------------------------

def test_endpoint_entries_200(monkeypatch, tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.routes import knowledge_center as kc_route

    # سرویس ایزوله برای endpoint
    monkeypatch.setattr(kc, "ENTRIES_FILE", tmp_path / "ep_entries.json")
    fresh = KnowledgeCenterService()
    fresh.upsert_entry({"title": "نمونه", "content": "x", "source_ref": "a"})
    monkeypatch.setattr(kc, "get_knowledge_center_service", lambda: fresh)
    monkeypatch.setattr(kc_route, "get_knowledge_center_service", lambda: fresh)

    app = FastAPI()
    app.include_router(kc_route.router, prefix="/api")
    client = TestClient(app)

    resp = client.get("/api/knowledge-center/entries")
    assert resp.status_code == 200
    data = resp.json()
    assert "entries" in data
    assert "toc" in data
    assert "categories" in data


def test_endpoint_import(monkeypatch, tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.routes import knowledge_center as kc_route

    monkeypatch.setattr(kc, "ENTRIES_FILE", tmp_path / "ep_import.json")
    fresh = KnowledgeCenterService()

    async def _no_ai(*a, **k):
        return []
    monkeypatch.setattr(fresh, "_extract_with_ai", _no_ai)
    monkeypatch.setattr(kc_route, "get_knowledge_center_service", lambda: fresh)

    app = FastAPI()
    app.include_router(kc_route.router, prefix="/api")
    client = TestClient(app)

    resp = client.post(
        "/api/knowledge-center/import",
        files={"file": ("chat.txt", b"# Topic\n\nuseful solution", "text/plain")},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True
