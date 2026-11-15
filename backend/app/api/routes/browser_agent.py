"""«عاملِ مرورگر» ِ بازرس ویژه — API (behind the login wall like everything else). See services/browser_agent.py."""

from __future__ import annotations

import asyncio
import os
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ...services import browser_agent as BA

router = APIRouter(prefix="/inspector-agent", tags=["Inspector browser agent"])
_TASKS: set = set()  # keep references so runs are not garbage-collected mid-flight


def _enabled() -> bool:
    return os.environ.get("BROWSER_AGENT_ENABLED", "1") != "0"


class RunIn(BaseModel):
    task: str = Field(..., min_length=3, max_length=4000)
    start_url: str = Field(..., min_length=8, max_length=2000)
    allowed_hosts: List[str] = Field(default_factory=list)
    model_id: Optional[str] = None
    project_id: Optional[str] = None
    max_steps: int = BA.MAX_STEPS_DEFAULT
    use_login: bool = True  # sign in first with the project's Auth Recipe («اتاق فرمان» card), when it has one
    # (2026-11-15, PM-INS-0012) the start page is THIS app (same site as the caller's page): with no Auth Recipe, sign the
    # agent in with the caller's own session (their bearer token → the app's localStorage key in the agent's throwaway
    # browser context). Never a broader identity than the person who pressed «شروع».
    use_session: bool = False
    session_storage_key: str = "pm.auth.token"


class Reply(BaseModel):
    approve: Optional[bool] = None
    text: Optional[str] = None


@router.get("/models")
async def models() -> List[Dict[str, Any]]:
    from ...services.assistant import available_models

    return [{**m, "vision": BA.model_supports_vision(m["id"])} for m in available_models()]


def _own_session_state(request: Request, start_url: str, key: str) -> Optional[dict]:
    """storage_state carrying the caller's own token for the start page's origin — only when the start page is the
    same site the request came from (Origin header), so a token never goes to a third-party site."""
    from urllib.parse import urlparse

    auth = request.headers.get("authorization", "")
    token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
    origin = request.headers.get("origin", "") or ""
    su, ou = urlparse(start_url), urlparse(origin)
    if not token or not ou.netloc or su.netloc.lower() != ou.netloc.lower() or not re.match(r"^[\w.\-]{1,64}$", key or ""):
        return None
    return {"cookies": [], "origins": [{"origin": f"{su.scheme}://{su.netloc}", "localStorage": [{"name": key, "value": token}]}]}


@router.post("/runs")
async def start(body: RunIn, request: Request) -> Dict[str, Any]:
    if not _enabled():
        raise HTTPException(503, "عاملِ مرورگر خاموش است (BROWSER_AGENT_ENABLED=0)")
    if not re.match(r"^https?://", body.start_url):
        raise HTTPException(400, "نشانیِ شروع باید http/https باشد")
    if BA.is_busy():
        raise HTTPException(409, "یک اجرای دیگر در جریان است — یکی‌یکی (حافظهٔ سرور محدود است)")
    model_id = body.model_id
    if not model_id:
        from ...services.assistant import available_models

        ms = available_models()
        if not ms:
            raise HTTPException(503, "هیچ مدلِ فعالی نیست — در «مدل‌ها و تنظیمات» کلید بگذارید")
        model_id = ms[0]["id"]
    run = BA.new_run(body.task, body.start_url, body.allowed_hosts, model_id=model_id, project_id=body.project_id)
    model = await BA.default_model(model_id)
    state, login_note = (await BA.login_state_for(body.start_url)) if body.use_login else (None, "")
    if body.use_login and state is None:
        _own = _own_session_state(request, body.start_url, body.session_storage_key) if body.use_session else None
        if _own is not None:
            state, login_note = _own, "🔑 با نشستِ واردشدهٔ خودِ شما (همین مرورگر) وارد شد — Auth Recipe لازم نشد"
        elif not login_note:
            login_note = ("⚠️ برای این سایت Auth Recipe ای در «اتاق فرمان» نیست — عامل بدونِ ورود شروع کرد؛ "
                          "اگر صفحه ورود خواست، Recipe را در کارتِ همان پروژه بگذارید")
    if login_note:
        run.summary = login_note
    t = asyncio.create_task(BA.run_agent(run, model, vision=BA.model_supports_vision(model_id), max_steps=body.max_steps,
                                         storage_state=state))
    _TASKS.add(t)
    t.add_done_callback(_TASKS.discard)
    return {"run_id": run.id, "model_id": model_id, "allowed_hosts": run.allowed_hosts, "login": login_note}


@router.get("/runs")
async def runs(limit: int = Query(30, ge=1, le=200)) -> List[Dict[str, Any]]:
    return BA.list_runs(limit)


@router.get("/runs/{run_id}")
async def get_run(run_id: str, after: int = Query(0, ge=0)) -> Dict[str, Any]:
    run = BA.RUNS.get(run_id)
    if run:
        return run.public(after)
    d = BA.load_run(run_id)
    if d is None:
        raise HTTPException(404, "اجرا یافت نشد")
    d["steps"] = [s for s in d.get("steps", []) if s.get("n", 0) > after]
    return d


@router.post("/runs/{run_id}/reply")
async def reply(run_id: str, body: Reply) -> Dict[str, Any]:
    value: Any = body.approve if body.approve is not None else (body.text or "")
    if not BA.reply(run_id, value):
        raise HTTPException(409, "این اجرا منتظرِ پاسخ نیست")
    return {"ok": True}


@router.post("/runs/{run_id}/cancel")
async def cancel(run_id: str) -> Dict[str, Any]:
    run = BA.RUNS.get(run_id)
    if not run:
        raise HTTPException(404, "اجرا یافت نشد")
    run.cancel = True
    BA.reply(run_id, None)  # a run waiting for approval stops too
    return {"ok": True}


@router.get("/runs/{run_id}/shots/{name}")
async def shot(run_id: str, name: str):
    if not re.match(r"^[a-f0-9]{8,32}$", run_id) or not re.match(r"^\d{1,3}\.jpg$", name):
        raise HTTPException(404, "یافت نشد")
    p = BA.SHOTS_ROOT / run_id / name
    if not p.is_file():
        raise HTTPException(404, "یافت نشد")
    return FileResponse(p, media_type="image/jpeg")


# ------------------------------------------------------------------------------------------------------------------
# «نمای سرور» — the inspector screen's self-healing fallback (2026-11-15): when the proxied iframe cannot show the
# project's site (framing refused, dynamic chunks, an error page), the panel switches to periodic screenshots taken
# by the shared server Chromium. Read-only: one GET of the URL, no clicks; only http(s); same one-at-a-time limit.
# ------------------------------------------------------------------------------------------------------------------
_SNAP_LOCK = asyncio.Lock()


@router.get("/snapshot")
async def snapshot(url: str = Query(..., min_length=8, max_length=2000), width: int = Query(1280, ge=320, le=1920)):
    from fastapi.responses import Response

    if not re.match(r"^https?://", url):
        raise HTTPException(400, "فقط http/https")
    if _SNAP_LOCK.locked() or BA.is_busy():
        raise HTTPException(409, "مرورگرِ سرور مشغول است — چند ثانیهٔ دیگر")
    async with _SNAP_LOCK:
        from ...services.verify_runtime.browser_pool import get_browser_pool

        browser = await get_browser_pool().get_browser()
        if browser is None:
            raise HTTPException(503, "Chromium ِ سرور در دسترس نیست")
        ctx = await browser.new_context(viewport={"width": width, "height": int(width * 0.625)}, locale="fa-IR")
        try:
            page = await ctx.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20_000)
                await page.wait_for_timeout(800)
            except Exception as e:  # noqa: BLE001 — still screenshot whatever loaded
                if page.url in ("about:blank", ""):
                    raise HTTPException(502, f"باز نشد: {str(e).splitlines()[0][:150]}")
            jpg = await page.screenshot(type="jpeg", quality=60)
            return Response(jpg, media_type="image/jpeg", headers={"Cache-Control": "no-store", "X-Final-Url": page.url})
        finally:
            await ctx.close()
