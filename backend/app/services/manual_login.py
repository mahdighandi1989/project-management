"""PM-INS-0031 — «🔐 ورودِ یک‌باره»: the owner signs in ONCE, by hand, inside a live server-side browser.

Why not inside the preview iframe: the preview is sandboxed without ``allow-same-origin`` (PM-INS-0015 — it must
not reach AI Creator's own token), so it has an opaque origin: no cookies, no localStorage, no IndexedDB, and Google
/ Firebase sign-in refuses the proxy domain anyway. So the sign-in happens in the server's own Chromium, on the
project's REAL site, and the owner drives it from the page (live frames + forwarded clicks/keys). When the owner
presses «ذخیره», the context's storage_state (cookies + localStorage + IndexedDB when the Playwright version supports
it — Firebase keeps its session there) is encrypted (AES-GCM, key derived from the server's persistent signing key)
and kept per site host on the persistent disk. 📸, the browser agent and the inspector's probes then open the site
with that state. Passwords are typed straight into the remote page; nothing typed is logged or stored.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)

IDLE_CLOSE_S = 10 * 60          # a forgotten live session closes itself
MAX_LIVE = 2                    # Render has little RAM — at most two live browsers
STATE_TTL_DAYS = 14             # the saved sign-in is reused for this long (the site may expire it earlier)
VIEWPORT = {"width": 1280, "height": 800}
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")
ALLOWED_KEYS = {"Enter", "Tab", "Backspace", "Escape", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight",
                "Delete", "Home", "End", "PageUp", "PageDown", "Space"}


def host_of(url: str) -> str:
    try:
        return (urlsplit(url or "").hostname or "").lower()
    except Exception:  # noqa: BLE001
        return ""


# ── encrypted per-host store ─────────────────────────────────────────────────

def _store_dir() -> Path:
    base = os.environ.get("MANUAL_LOGIN_DIR")
    if not base:
        try:
            from ..core.database import DATABASE_DIR
            base = os.path.join(DATABASE_DIR, "manual_login")
        except Exception:  # noqa: BLE001
            base = os.path.join(os.path.dirname(__file__), "..", "..", "storage", "manual_login")
    p = Path(base)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _key() -> bytes:
    from ..core.auth import signing_key
    return hashlib.sha256(("manual-login:" + signing_key()).encode("utf-8")).digest()


def encrypt(data: dict) -> str:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce = os.urandom(12)
    ct = AESGCM(_key()).encrypt(nonce, json.dumps(data, ensure_ascii=False).encode("utf-8"), None)
    return base64.b64encode(nonce + ct).decode("ascii")


def decrypt(blob: str) -> Optional[dict]:
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        raw = base64.b64decode(blob)
        return json.loads(AESGCM(_key()).decrypt(raw[:12], raw[12:], None).decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _file(host: str) -> Path:
    return _store_dir() / (hashlib.sha256(host.encode("utf-8")).hexdigest()[:24] + ".json")


def save_state(host: str, state: dict, *, final_url: str = "", title: str = "") -> dict:
    now = datetime.now(timezone.utc)
    meta = {
        "host": host, "saved_at": now.isoformat(), "expires_at": (now + timedelta(days=STATE_TTL_DAYS)).isoformat(),
        "cookies": len(state.get("cookies") or []), "origins": len(state.get("origins") or []),
        "final_url": final_url[:300], "title": title[:200],
    }
    _file(host).write_text(json.dumps({**meta, "blob": encrypt(state)}), encoding="utf-8")
    return meta


def status_for(host: str) -> Optional[dict]:
    p = _file(host)
    if not host or not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    d.pop("blob", None)
    try:
        d["expired"] = datetime.fromisoformat(d["expires_at"]) < datetime.now(timezone.utc)
    except Exception:  # noqa: BLE001
        d["expired"] = True
    return d


def state_for_url(url: str) -> Optional[dict]:
    """The saved, still-valid sign-in for ``url``'s site — or None."""
    host = host_of(url)
    p = _file(host) if host else None
    if not p or not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        if datetime.fromisoformat(d["expires_at"]) < datetime.now(timezone.utc):
            return None
        return decrypt(d.get("blob") or "")
    except Exception:  # noqa: BLE001
        return None


def forget(host: str) -> bool:
    p = _file(host)
    if p.exists():
        p.unlink()
        return True
    return False


# ── live sessions ────────────────────────────────────────────────────────────

@dataclass
class Live:
    id: str
    url: str
    host: str
    pw: Any = None
    browser: Any = None
    context: Any = None
    pages: list = field(default_factory=list)
    touched: float = field(default_factory=time.time)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    @property
    def page(self):
        alive = [p for p in self.pages if not p.is_closed()]
        self.pages = alive
        return alive[-1] if alive else None  # the newest tab — Google's sign-in popup while it is open


LIVE: dict[str, Live] = {}


async def _close(s: Live) -> None:
    LIVE.pop(s.id, None)
    for obj in (s.context, s.browser):
        try:
            if obj:
                await obj.close()
        except Exception:  # noqa: BLE001
            pass
    try:
        if s.pw:
            await s.pw.stop()
    except Exception:  # noqa: BLE001
        pass


async def reap() -> None:
    for s in list(LIVE.values()):
        if time.time() - s.touched > IDLE_CLOSE_S:
            await _close(s)


async def start(url: str) -> Live:
    await reap()
    if len(LIVE) >= MAX_LIVE:
        await _close(sorted(LIVE.values(), key=lambda x: x.touched)[0])
    from playwright.async_api import async_playwright
    s = Live(id=uuid.uuid4().hex[:16], url=url, host=host_of(url))
    s.pw = await async_playwright().start()
    exe = os.environ.get("MANUAL_LOGIN_CHROMIUM")  # optional (a pinned local Chromium); Render uses Playwright's own
    s.browser = await s.pw.chromium.launch(headless=True, **({"executable_path": exe} if exe else {}), args=[
        "--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"])
    prev = state_for_url(url)  # continue from an earlier sign-in, if any
    s.context = await s.browser.new_context(viewport=VIEWPORT, user_agent=UA, locale="fa-IR",
                                            **({"storage_state": prev} if prev else {}))
    s.context.on("page", lambda p: s.pages.append(p))
    page = await s.context.new_page()
    if page not in s.pages:
        s.pages.append(page)
    LIVE[s.id] = s
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:  # noqa: BLE001
        logger.info("manual_login: first load slow: %s", str(e)[:120])
    return s


def get(sid: str) -> Optional[Live]:
    return LIVE.get(sid)


async def frame(s: Live) -> dict:
    s.touched = time.time()
    async with s.lock:
        p = s.page
        if p is None:
            return {"ok": False, "error": "هیچ زبانه‌ای باز نیست"}
        img = await p.screenshot(type="jpeg", quality=60, full_page=False)
        try:
            title = await p.title()
        except Exception:  # noqa: BLE001
            title = ""
        vp = p.viewport_size
        if not vp:  # a popup (Google sign-in) has its own window size — click mapping must use it
            try:
                w, h = await p.evaluate("[innerWidth, innerHeight]")
                vp = {"width": w, "height": h}
            except Exception:  # noqa: BLE001
                vp = VIEWPORT
        return {"ok": True, "image": base64.b64encode(img).decode("ascii"), "url": p.url, "title": title,
                "tabs": len(s.pages), "viewport": vp}


async def act(s: Live, kind: str, *, x: float = 0, y: float = 0, text: str = "", key: str = "",
              dy: float = 0, url: str = "") -> str:
    """One owner input forwarded to the live page. ``text`` (may be a password) is never logged or kept."""
    s.touched = time.time()
    async with s.lock:
        p = s.page
        if p is None:
            return "هیچ زبانه‌ای باز نیست"
        if kind == "click":
            await p.mouse.click(float(x), float(y))
        elif kind == "type":
            await p.keyboard.type(text[:500], delay=15)
        elif kind == "key":
            k = " " if key == "Space" else key
            if key not in ALLOWED_KEYS:
                return "کلیدِ ناشناخته"
            await p.keyboard.press(k)
        elif kind == "scroll":
            await p.mouse.wheel(0, max(-3000.0, min(3000.0, float(dy))))
        elif kind == "back":
            await p.go_back(timeout=15000)
        elif kind == "goto":
            if host_of(url) != s.host:
                return "فقط نشانی‌های همین سایت"
            await p.goto(url, wait_until="domcontentloaded", timeout=30000)
        else:
            return "کنشِ ناشناخته"
    await asyncio.sleep(0.4)
    return ""


async def finish(s: Live) -> dict:
    """Keep the signed-in session (encrypted) and close the browser."""
    s.touched = time.time()
    async with s.lock:
        try:
            state = await s.context.storage_state(indexed_db=True)  # Playwright ≥1.51: Firebase keeps its user here
        except TypeError:
            state = await s.context.storage_state()
        main = s.pages[0] if s.pages else None
        final_url, title = (main.url, await main.title()) if main and not main.is_closed() else ("", "")
    meta = save_state(s.host, state, final_url=final_url, title=title)
    await _close(s)
    return meta


async def cancel(s: Live) -> None:
    await _close(s)
