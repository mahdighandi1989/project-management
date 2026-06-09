"""🐛 (Cloudflare 403 — strategy changed)

Original symptom: کاربر روی موبایل با هر تلاش chunked از Cloudflare
403 خالی می‌گرفت — حتی با pacing 350ms و retry. علتش یک rate-limiter
حساس به ریت POSTهای پشت‌سرهم `text/plain` به مسیر `/chunk` بود.

راه حل: به‌جای چند POST chunked، یک POST مستقیم با
Content-Type=application/octet-stream و body=binary encoded JSON.
سه چیز همزمان فرق می‌کند:
  1. یک request به‌جای چندین — rate-limiter trigger نمی‌شود
  2. octet-stream به‌جای text/plain — WAF signature متفاوت
  3. preflight OPTIONS اجبار می‌شود — CORS-approved request

Backend `/tasks` حالا octet-stream را هم می‌پذیرد (body bytes را دستی
JSON parse می‌کند). مسیر قدیمی `/tasks/from-draft` با draft chunked
هم در backend وجود دارد ولی frontend دیگر از آن استفاده نمی‌کند
(retain only for safety / future / direct API users).

این فایل source-level contract را pin می‌کند.
"""

from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _frontend_src() -> str:
    p = (
        Path(__file__).resolve().parents[2]
        / "frontend/src/app/oversight/page.tsx"
    )
    return p.read_text(encoding="utf-8")


def _backend_src() -> str:
    p = (
        Path(__file__).resolve().parents[1]
        / "app/api/routes/oversight.py"
    )
    return p.read_text(encoding="utf-8")


def test_backend_tasks_accepts_octet_stream():
    """POST /tasks must read raw body so any Content-Type works.

    🐛 (regression guard) — اگر کسی این را به `payload: TaskCreate`
    برگرداند، FastAPI فقط `application/json` را parse می‌کند و
    octet-stream POST از frontend با 422 fail می‌شود.
    """
    src = _backend_src()
    idx = src.find('@router.post("/tasks")')
    assert idx != -1
    body = src[idx:idx + 2500]
    assert "await request.body()" in body, (
        "handler must read raw body so it works for any content-type — "
        "without this, octet-stream POSTs from frontend get 422"
    )
    assert "json" in body.lower()
    assert "TaskCreate" in body


def test_frontend_save_uses_single_octet_stream_post():
    """savePromptAsTask must use a single direct POST with
    application/octet-stream, not chunked uploads.

    🐛 (regression guard) — chunked uploads were getting silent 403s
    from Cloudflare for this user, even with pacing + retry. The fix
    is one binary POST that bypasses the rate-limiter triggered by
    rapid text/plain POSTs to /chunk.
    """
    src = _frontend_src()
    save_idx = src.find("savePromptAsTask = async")
    assert save_idx != -1
    body = src[save_idx:save_idx + 6000]
    assert "`${API_BASE}/api/oversight/tasks`" in body, (
        "savePromptAsTask must POST directly to /tasks"
    )
    assert "application/octet-stream" in body, (
        "Content-Type must be application/octet-stream to bypass the "
        "text/plain WAF signature that was triggering Cloudflare 403s"
    )
    assert "new TextEncoder().encode(payloadJson)" in body, (
        "body must be a binary-encoded JSON (Uint8Array), not a string — "
        "otherwise the Content-Type/body mismatch defeats the workaround"
    )


def test_frontend_does_not_use_chunked_path_for_task_save():
    """The chunked code path for task save is removed. The endpoint
    `/tasks/from-draft` may still exist in backend for safety but
    frontend's savePromptAsTask should NOT use /idea-draft/start or
    /tasks/from-draft anymore.

    🐛 (regression guard) — keeping the chunked path in frontend would
    bring back the Cloudflare 403 symptom even though backend supports
    octet-stream now.
    """
    src = _frontend_src()
    save_idx = src.find("savePromptAsTask = async")
    assert save_idx != -1
    body = src[save_idx:save_idx + 6000]
    assert "/idea-draft/start" not in body, (
        "savePromptAsTask should not call /idea-draft/start anymore — "
        "single octet-stream POST replaces the chunked flow"
    )
    assert "/tasks/from-draft" not in body, (
        "savePromptAsTask should not call /tasks/from-draft anymore — "
        "single octet-stream POST to /tasks replaces it"
    )


def test_backend_keeps_tasks_from_draft_for_compat():
    """The chunked-draft endpoint stays on the backend even though
    frontend no longer uses it. Removing it would break any external
    API client that adopted the chunked pattern. Pin its presence."""
    src = _backend_src()
    assert '@router.post("/tasks/from-draft")' in src, (
        "keep /tasks/from-draft for API back-compat even though the "
        "frontend now prefers the single octet-stream POST"
    )


def test_failed_to_fetch_error_message_still_surfaces():
    """The user-visible toast still uses «network — » prefix so genuine
    network failures stay diagnosable."""
    src = _frontend_src()
    assert "network — " in src
