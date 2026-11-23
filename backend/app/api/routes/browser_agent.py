"""«عاملِ مرورگر» ِ بازرس ویژه — API (behind the login wall like everything else). See services/browser_agent.py."""

from __future__ import annotations

import asyncio
import os
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from ...services import browser_agent as BA

import logging

logger = logging.getLogger(__name__)

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
        from ...services import manual_login as ML

        _st = ML.state_for_url(url)  # PM-INS-0031: the owner's one-time sign-in for this site, if saved
        ctx = await browser.new_context(viewport={"width": width, "height": int(width * 0.625)}, locale="fa-IR",
                                        **({"storage_state": _st} if _st else {}))
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


# ── PM-INS-0031 «🔐 ورودِ یک‌باره» — live server browser the owner signs in with, once per site ─────────────────

class LoginStartIn(BaseModel):
    project_id: Optional[str] = None
    url: Optional[str] = Field(None, max_length=2000)


class LoginActIn(BaseModel):
    kind: str = Field(..., pattern=r"^(click|type|key|scroll|back|goto)$")
    x: float = 0
    y: float = 0
    text: str = Field("", max_length=500)
    key: str = Field("", max_length=20)
    dy: float = 0
    url: str = Field("", max_length=2000)


def _login_url(body_url: Optional[str], project_id: Optional[str]) -> str:
    url = (body_url or "").strip()
    if not url and project_id:
        from ...core.database import SessionLocal
        from .render_logs import resolve_preview_frontend_url

        db = SessionLocal()
        try:
            url = resolve_preview_frontend_url(db, project_id) or ""
        finally:
            db.close()
    if not re.match(r"^https?://", url):
        raise HTTPException(400, "نشانیِ سایتِ واقعیِ پروژه پیدا نشد — اول پیش‌نمایش را «روشن» کنید")
    return url


def _live(sid: str):
    from ...services import manual_login as ML

    s = ML.get(sid)
    if s is None:
        raise HTTPException(404, "این پنجرهٔ ورود بسته شده (۱۰ دقیقه بی‌کاری) — دوباره «🔐 ورودِ یک‌باره» بزنید")
    return s


@router.get("/login/status")
async def login_status(project_id: Optional[str] = None, url: Optional[str] = None) -> Dict[str, Any]:
    from ...services import manual_login as ML

    await ML.reap()  # PM-INS-0033: close a forgotten live browser early (Render RAM)
    try:
        u = _login_url(url, project_id)
    except HTTPException:
        return {"url": "", "saved": None}
    return {"url": u, "host": ML.host_of(u), "saved": ML.status_for(ML.host_of(u))}


@router.post("/login/start")
async def login_start(body: LoginStartIn) -> Dict[str, Any]:
    from ...services import manual_login as ML

    u = _login_url(body.url, body.project_id)
    try:
        s = await ML.start(u)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(503, f"مرورگرِ سرور باز نشد: {str(e).splitlines()[0][:160]}")
    return {"session_id": s.id, "url": u, "host": s.host, "viewport": ML.VIEWPORT}


@router.get("/login/{sid}/frame")
async def login_frame(sid: str) -> Dict[str, Any]:
    from ...services import manual_login as ML

    try:
        return await ML.frame(_live(sid))
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e).splitlines()[0][:160]}


@router.post("/login/{sid}/act")
async def login_act(sid: str, body: LoginActIn) -> Dict[str, Any]:
    from ...services import manual_login as ML

    try:
        err = await ML.act(_live(sid), body.kind, x=body.x, y=body.y, text=body.text, key=body.key, dy=body.dy,
                           url=body.url)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        err = str(e).splitlines()[0][:160]
    return {"ok": not err, "error": err}


@router.post("/login/{sid}/save")
async def login_save(sid: str) -> Dict[str, Any]:
    from ...services import manual_login as ML

    meta = await ML.finish(_live(sid))
    return {"ok": True, "saved": meta}


@router.post("/login/{sid}/cancel")
async def login_cancel(sid: str) -> Dict[str, Any]:
    from ...services import manual_login as ML

    s = ML.get(sid)
    if s:
        await ML.cancel(s)
    return {"ok": True}


@router.post("/login/forget")
async def login_forget(body: LoginStartIn) -> Dict[str, Any]:
    from ...services import manual_login as ML

    return {"ok": ML.forget(ML.host_of(_login_url(body.url, body.project_id)))}


# ── PM-INS-0033 «📥 انتقالِ ورود از کرومِ خودِ مالک» — one-site bookmarklet + single-use ticket ─────────────────────

@router.get("/login/saved")
async def login_saved() -> Dict[str, Any]:
    """Every saved sign-in (metadata only) — the per-site table: source, expiry, 🗑."""
    from ...services import manual_login as ML

    await ML.reap()  # also close a forgotten live browser (Render RAM — PM-INS-0033 503 at 23:05)
    return {"saved": ML.list_saved(), "ttl_days": ML.STATE_TTL_DAYS}


@router.post("/login/import-ticket")
async def login_import_ticket(body: LoginStartIn) -> Dict[str, Any]:
    """A single-use, 15-minute ticket bound to ONE site; the page turns it into that site's bookmarklet."""
    from ...services import manual_login as ML

    u = _login_url(body.url, body.project_id)
    host = ML.host_of(u)
    if not host:
        raise HTTPException(400, "میزبانِ سایت پیدا نشد")
    t = ML.issue_import_ticket(host)
    return {**t, "url": u, "ttl_s": ML.IMPORT_TICKET_TTL_S, "import_path": "/api/inspector-agent/login/import"}


def _import_page(ok: bool, msg: str) -> HTMLResponse:
    import html as _h

    color = "#059669" if ok else "#dc2626"
    body = (f'<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width,initial-scale=1"><title>انتقالِ ورود</title></head>'
            f'<body style="font-family:Tahoma,sans-serif;background:#f8fafc;padding:24px">'
            f'<div style="max-width:560px;margin:auto;background:#fff;border:2px solid {color};border-radius:12px;padding:20px">'
            f'<h2 style="color:{color};margin-top:0">{"✅ ورود منتقل شد" if ok else "❌ انتقال انجام نشد"}</h2>'
            f'<p style="line-height:1.9">{_h.escape(msg)}</p>'
            f'<p style="color:#64748b;font-size:13px">این زبانه را ببندید. در AI Creator «📸 عکس» یا «🖱 عامل» را بزنید تا صفحهٔ داخلی دیده شود.</p>'
            f'</div></body></html>')
    return HTMLResponse(body, status_code=200 if ok else 400,
                        headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})


# PM-INS-0036 (دورِ ۲): سایتِ پروژه با CSP ِ `form-action 'self'` / `connect-src 'self'` جلوی فرم و fetch ِ بوک‌مارک به
# این سرور را می‌گیرد (Detective-1 همین را دارد) ⇒ زبانهٔ تازه با GET باز می‌شد و «Method Not Allowed» می‌داد.
# حالا بوک‌مارک همین صفحه را با window.open باز می‌کند (CSP جلوی ناوبری را نمی‌گیرد) و داده را با postMessage
# می‌دهد؛ این صفحه خودش (هم‌مبدأ) POST می‌کند. origin را مرورگر گواهی می‌کند (event.origin)، نه خودِ داده.
_IMPORT_RECEIVER = """<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>انتقالِ ورود</title></head>
<body style="font-family:Tahoma,sans-serif;background:#f8fafc;padding:24px">
<div style="max-width:560px;margin:auto;background:#fff;border:2px solid #6366f1;border-radius:12px;padding:20px">
<h2 style="color:#4f46e5;margin-top:0">📥 انتقالِ ورود</h2><p id="m" style="line-height:1.9">⏳ در حالِ گرفتنِ ورود از سایت…</p></div>
<script>(function(){
var m=document.getElementById('m'),done=false,op=window.opener;
if(!op){m.innerHTML='این نشانی به‌تنهایی کاری نمی‌کند (و اگر با یک بوک‌مارکِ قدیمی به این‌جا رسیدید: آن بوک‌مارک دیگر کار نمی‌کند).<br><br><b>چه کنم؟</b> بوک‌مارکِ قدیمیِ «📥 ورود به AI Creator» را از نوارِ کروم حذف کنید (راست‌کلیک ⇐ Delete)، در AI Creator دوباره «📥 از کرومِ من» را بزنید و دکمهٔ آبیِ تازه را به نوار بکشید.';return}
var iv=setInterval(function(){if(!done){try{op.postMessage({pmImport:'ready'},'*')}catch(e){}}},300);
window.addEventListener('message',function(ev){
if(done||ev.source!==op||!ev.data||ev.data.pmImport!=='data')return;
done=true;clearInterval(iv);var d;
try{d=JSON.parse(ev.data.d);d.origin=ev.origin}catch(e){m.textContent='❌ دادهٔ رسیده خوانده نشد';return}
m.textContent='⏳ در حالِ ذخیرهٔ رمزنگاری‌شده روی سرور…';
fetch(location.pathname,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded;charset=UTF-8'},
body:new URLSearchParams({t:String(ev.data.t||''),d:JSON.stringify(d)}).toString()})
.then(function(r){return r.text()}).then(function(h){document.open();document.write(h);document.close()})
.catch(function(e){m.textContent='❌ ارسال به سرور نشد: '+e+' — دوباره روی بوک‌مارک بزنید'})});
setTimeout(function(){if(!done){clearInterval(iv);m.textContent='❌ داده‌ای از سایت نرسید. این زبانه را ببندید، به زبانهٔ سایت برگردید و دوباره روی بوک‌مارک کلیک کنید.'}},90000);
})();</script></body></html>"""


@router.get("/login/import")
async def login_import_receiver() -> HTMLResponse:
    """PUBLIC static page (no data, no secret): receives the bookmarklet's dump by postMessage from the tab that opened
    it and POSTs it same-origin to the route below. Opened directly (or by an old bookmark) it explains what to do."""
    return HTMLResponse(_IMPORT_RECEIVER, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})


@router.post("/login/import")
async def login_import(request: Request):
    """PUBLIC (registered in core/auth.PUBLIC): reached from the project's own site in the owner's Chrome, so it carries
    no AI Creator session — the single-use host-bound ticket is the credential. Fields are read by hand (no 422 echo)
    and never logged."""
    from ...services import manual_login as ML

    try:
        form = await request.form()
        tok = str(form.get("t") or "")
        payload = str(form.get("d") or "")
    except Exception:  # noqa: BLE001
        return _import_page(False, "فرم خوانده نشد")
    try:
        meta = ML.import_from_browser(tok, payload)
    except ValueError as e:
        return _import_page(False, str(e))
    except Exception as e:  # noqa: BLE001
        logger.warning("login import failed: %s", type(e).__name__)  # type only — never the value
        return _import_page(False, "خطای سرور در ذخیره")
    return _import_page(True, (
        f"نشستِ «{meta['host']}» رمزنگاری‌شده روی سرور ذخیره شد: {meta['local_storage']} کلیدِ localStorage، "
        f"{meta['indexed_db']} رکوردِ IndexedDB، {meta['cookies']} کوکی. اعتبار تا {meta['expires_at'][:10]} "
        f"(حذفِ یک‌کلیکی: 🗑 در «🔐 ورود»)."))
