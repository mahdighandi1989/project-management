#!/usr/bin/env python3
"""Shared HTTP client for the supervisor's tools — WHERE production is and HOW the
supervisor identifies itself, resolved without anything written in the repo.

Modelled on Detective-1's `scripts/supervisor/client.py` (read-only reference).

Resolution order (first that works wins):

1. Environment: ``PM_SUPERVISOR_API_BASE`` (e.g. ``https://<backend>``) and
   ``PM_SUPERVISOR_TOKEN``. Deliberately NOT ``SUPERVISOR_API_*``: those belong
   to another project's supervisor in the same Claude environment.
2. Render API: the backend service's public URL and its env var
   ``SUPERVISOR_TOKEN`` (falling back to ``EXTERNAL_TOOL_TOKEN``, which the
   server accepts the same way), read through api.render.com — the Claude
   environment's network proxy authenticates that host. The secret lives ONLY
   on Render; here it is held in memory, never printed or written to disk.

Every failure says WHAT to fix, and callers exit with code 3 — «could not look»
must never look like «looked and found nothing».
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

RENDER_API = "https://api.render.com/v1"
#: ai-creator-backend / ai-creator-frontend on Render (service ids, not secrets).
BACKEND_SERVICE_ID = os.getenv("PM_RENDER_BACKEND_ID", "srv-d5cmo824d50c7387c50g")
FRONTEND_SERVICE_ID = os.getenv("PM_RENDER_FRONTEND_ID", "srv-d5cn3e3e5dus738o8b6g")
TIMEOUT = float(os.getenv("PM_SUPERVISOR_TIMEOUT", "120"))


class SupervisorError(RuntimeError):
    """Carries WHAT to fix, not just that something failed."""


def _http(url: str, *, data: bytes | None = None, headers: dict | None = None, method: str = "GET",
          timeout: float = TIMEOUT) -> tuple[int, bytes, dict]:
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers or {})
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise SupervisorError(f"به «{url.split('?')[0]}» نرسیدم ({getattr(e, 'reason', e)}) — شبکهٔ محیط یا سرور") from e


def _render_get(path: str):
    headers = {"Accept": "application/json"}
    key = os.getenv("RENDER_API_KEY")
    if key:
        headers["Authorization"] = f"Bearer {key}"
    st, raw, _ = _http(f"{RENDER_API}{path}", headers=headers)
    if st != 200:
        raise SupervisorError(
            f"Render API پاسخِ HTTP {st} داد برای {path} — دسترسیِ api.render.com در این محیط برقرار است؟")
    return json.loads(raw or b"null")


def _service_url(service_id: str) -> str:
    svc = _render_get(f"/services/{service_id}")
    url = ((svc or {}).get("serviceDetails") or {}).get("url") or ""
    if not url:
        raise SupervisorError(f"آدرسِ عمومیِ سرویسِ {service_id} از Render خوانده نشد")
    return url.rstrip("/")


def frontend_url() -> str:
    env = (os.getenv("PM_FRONTEND_URL") or "").strip().rstrip("/")
    return env or _service_url(FRONTEND_SERVICE_ID)


class Client:
    def __init__(self) -> None:
        self.base = (os.getenv("PM_SUPERVISOR_API_BASE") or "").strip().rstrip("/")
        self._token = (os.getenv("PM_SUPERVISOR_TOKEN") or "").strip()
        self.source = "env"
        if not self.base or not self._token:
            self._from_render()

    def _from_render(self) -> None:
        if not self.base:
            self.base = _service_url(BACKEND_SERVICE_ID)
        if self._token:
            return
        env: dict = {}
        cursor = None
        for _ in range(10):
            page = _render_get(f"/services/{BACKEND_SERVICE_ID}/env-vars?limit=100"
                               + (f"&cursor={urllib.parse.quote(cursor)}" if cursor else ""))
            for item in page or []:
                ev = item.get("envVar") or {}
                env[ev.get("key")] = ev.get("value")
            cursor = (page[-1].get("cursor") if page else None)
            if not page or len(page) < 100:
                break
        self._token = (env.get("SUPERVISOR_TOKEN") or env.get("EXTERNAL_TOOL_TOKEN") or "").strip()
        if not self._token:
            raise SupervisorError(
                "نه SUPERVISOR_TOKEN روی سرویسِ بک‌اند در Render هست نه EXTERNAL_TOOL_TOKEN — ناظر هویت ندارد")
        self.source = "render"

    # -- calls ----------------------------------------------------------------
    def raw(self, path: str, *, data: bytes | None = None, headers: dict | None = None,
            method: str = "GET", timeout: float = TIMEOUT) -> tuple[int, bytes, dict]:
        h = {"X-Supervisor-Token": self._token}
        h.update(headers or {})
        last: tuple[int, bytes, dict] = (0, b"", {})
        for attempt in range(4):  # a cold Render instance can take a while to wake
            try:
                last = _http(f"{self.base}{path}", data=data, headers=h, method=method, timeout=timeout)
            except SupervisorError:
                if attempt == 3:
                    raise
                time.sleep(10 * (attempt + 1))
                continue
            if last[0] in (502, 503, 504) and attempt < 3:
                time.sleep(10 * (attempt + 1))
                continue
            return last
        return last

    def api(self, path: str, *, body: dict | None = None, method: str | None = None) -> dict:
        data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
        headers = {"Content-Type": "application/json"} if data is not None else {}
        st, raw, _ = self.raw(path, data=data, headers=headers,
                              method=method or ("POST" if data is not None else "GET"))
        if st == 404:
            raise SupervisorError(f"«{path}» پیدا نشد (۴۰۴): {_detail(raw)} — هنوز دیپلوی نشده؟")
        if st == 403:
            raise SupervisorError(f"«{path}» رد شد (۴۰۳): {_detail(raw)}")
        if st not in (200, 201):
            raise SupervisorError(f"«{path}» پاسخِ HTTP {st} داد: {_detail(raw)}")
        return json.loads(raw or b"{}")

    def whoami(self) -> dict:
        me = self.api("/api/inspection/whoami")
        if not me.get("supervisor"):
            raise SupervisorError(
                "سرور این توکن را «ناظر» نشناخت — SUPERVISOR_TOKEN (یا EXTERNAL_TOOL_TOKEN) روی Render با "
                "آنچه این اسکریپت می‌فرستد یکی نیست")
        return me


def _detail(raw: bytes) -> str:
    try:
        return str((json.loads(raw) or {}).get("detail") or raw[:200])
    except Exception:  # noqa: BLE001
        return str(raw[:200])
