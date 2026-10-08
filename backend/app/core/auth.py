"""Sign-in with Google, and a wall in front of the whole API.

THE OWNER'S RULE (2026-10-08): «میخوام مثل این دو پروژه بتونم با گوگل لاگین کنم و
بدون لاگین چیزی نشون نده». Modelled on Detective-1 / ALLIN1 (read-only references).

HOW IT WORKS
* The browser gets a Google ID token from Google Identity Services and sends it
  to ``POST /api/auth/google``. The server verifies it with Google (audience =
  ``GOOGLE_CLIENT_ID``, verified e-mail) and answers with this app's own signed
  session token (HS256, 30 days, revocable via ``token_version``).
* Who may enter: e-mails in ``ADMIN_EMAILS`` (owners, comma separated) are always
  approved; anyone else is recorded as ``pending`` until an owner approves them on
  the «کاربران» page. Nothing personal is written in the repo — only env vars.
* ``AuthWall`` (ASGI middleware) refuses every HTTP request without a valid
  session, EXCEPT: preflight OPTIONS, the public auth endpoints, ``/health``,
  the Telegram webhook, and machine callers that present their own secret —
  ``X-External-Token`` (= ``EXTERNAL_TOOL_TOKEN``/``ADMIN_TOKEN``, the GitHub
  workflow), ``X-Admin-Token`` (= ``ADMIN_TOKEN``) and ``X-Supervisor-Token``
  (the supervisor Routine). WebSockets (the inspector bridge in other apps) are
  untouched. ``<img>``/download links may carry ``?access_token=`` on GET.

WHEN IT IS ON
The wall turns on by itself as soon as ``ADMIN_EMAILS`` is set on the server —
before that nobody could sign in as owner, and turning it on would lock the owner
out of their own app. ``AUTH_DISABLED=1`` is the emergency switch (ALLIN1 has the
same one, deliberately).
"""

from __future__ import annotations

import hmac
import logging
import os
import secrets
import time
from typing import Optional

import httpx
from jose import JWTError, jwt

logger = logging.getLogger("app.auth")

ALGORITHM = "HS256"
TOKEN_DAYS = int(os.environ.get("AUTH_TOKEN_DAYS", "30"))
TOKENINFO = "https://oauth2.googleapis.com/tokeninfo"

#: Exact paths (or prefixes ending in "/") reachable without a session.
PUBLIC = (
    "/health",
    "/api/auth/config",
    "/api/auth/google",
    "/api/auth/supervisor-session",
    "/api/notifications/telegram/webhook",
)


def admin_emails() -> set[str]:
    raw = os.environ.get("ADMIN_EMAILS", "") + "," + os.environ.get("OWNER_EMAIL", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def google_client_id() -> str:
    return (os.environ.get("GOOGLE_CLIENT_ID") or "").strip()


def auth_enforced() -> bool:
    if os.environ.get("AUTH_DISABLED", "").strip().lower() in ("1", "true", "yes"):
        return False
    return bool(admin_emails())


# ---------------------------------------------------------------------------
# signing key — SECRET_KEY if strong, else one random key kept on the
# persistent disk beside the database (never in the repo)
# ---------------------------------------------------------------------------
_key: Optional[str] = None


def signing_key() -> str:
    global _key
    if _key:
        return _key
    env = (os.environ.get("SECRET_KEY") or "").strip()
    if len(env) >= 32:
        _key = env
        return _key
    from .database import DATABASE_DIR

    path = os.path.join(DATABASE_DIR, ".auth_signing_key")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            _key = fh.read().strip()
    except OSError:
        _key = ""
    if len(_key) < 32:
        _key = secrets.token_urlsafe(48)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(_key)
    return _key


def create_token(*, sub: str, email: str, role: str, ver: int = 0) -> str:
    now = int(time.time())
    return jwt.encode({"sub": sub, "email": email, "role": role, "ver": ver,
                       "iat": now, "exp": now + TOKEN_DAYS * 86400}, signing_key(), algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, signing_key(), algorithms=[ALGORITHM])
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# Google
# ---------------------------------------------------------------------------
class AuthError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status, self.detail = status, detail


def verify_google_credential(credential: str) -> dict:
    """Ask Google itself whether this ID token is genuine and meant for us."""
    cid = google_client_id()
    if not cid:
        raise AuthError(503, "ورود با گوگل پیکربندی نشده است (GOOGLE_CLIENT_ID روی Render)")
    try:
        r = httpx.get(TOKENINFO, params={"id_token": credential}, timeout=20)
    except httpx.HTTPError as exc:
        raise AuthError(502, f"گوگل در دسترس نبود: {exc}") from exc
    if r.status_code != 200:
        raise AuthError(401, "توکنِ گوگل نامعتبر است")
    info = r.json()
    if info.get("aud") != cid:
        raise AuthError(401, "این توکن برای این برنامه صادر نشده است")
    if info.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise AuthError(401, "صادرکنندهٔ توکن نامعتبر است")
    if str(info.get("email_verified")).lower() != "true" or not info.get("email"):
        raise AuthError(401, "ایمیلِ حسابِ گوگل تأیید نشده است")
    try:
        if int(info.get("exp", 0)) < time.time():
            raise AuthError(401, "توکنِ گوگل منقضی شده است")
    except ValueError:
        pass
    return {"sub": str(info["sub"]), "email": str(info["email"]).lower(),
            "name": info.get("name") or "", "picture": info.get("picture") or ""}


# ---------------------------------------------------------------------------
# machine callers
# ---------------------------------------------------------------------------
def _eq(a: str, b: str) -> bool:
    return bool(a and b and hmac.compare_digest(a, b))


def supervisor_secret() -> str:
    return ((os.environ.get("SUPERVISOR_TOKEN") or "").strip()
            or (os.environ.get("EXTERNAL_TOOL_TOKEN") or "").strip())


def machine_caller(headers: dict) -> Optional[str]:
    """`supervisor` / `external` / `admin` when the request carries a valid secret."""
    ext = (os.environ.get("EXTERNAL_TOOL_TOKEN") or "").strip()
    adm = (os.environ.get("ADMIN_TOKEN") or "").strip()
    sup = supervisor_secret()
    if _eq(headers.get("x-supervisor-token", ""), sup):
        return "supervisor"
    x = headers.get("x-external-token", "")
    if _eq(x, ext) or _eq(x, adm):
        return "external"
    if _eq(headers.get("x-admin-token", ""), adm):
        return "admin"
    return None


def session_from(headers: dict, query: str, method: str) -> Optional[dict]:
    """The decoded, still-valid session of this request, or None."""
    auth = headers.get("authorization", "")
    token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
    if not token and method in ("GET", "HEAD") and "access_token=" in query:
        from urllib.parse import parse_qs

        token = (parse_qs(query).get("access_token") or [""])[0]
    if not token:
        return None
    claims = decode_token(token)
    if not claims:
        return None
    if claims.get("role") == "supervisor":
        return claims
    # revocation and approval are checked against the database row
    from .database import SessionLocal
    from ..models.app_user import AppUser

    db = SessionLocal()
    try:
        u = db.query(AppUser).filter(AppUser.id == int(claims.get("sub", 0))).first()
        if u is None or u.status != "approved" or int(u.token_version or 0) != int(claims.get("ver", -1)):
            return None
        claims["role"] = u.role
        return claims
    except Exception:  # noqa: BLE001 - a broken row must not open the wall
        return None
    finally:
        db.close()


class AuthWall:
    """Pure ASGI middleware: HTTP only (WebSockets pass untouched)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        method = scope.get("method", "GET")
        path = scope.get("path", "")
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        state = scope.setdefault("state", {})
        role = machine_caller(headers)
        claims = None if role else session_from(headers, scope.get("query_string", b"").decode("latin-1"), method)
        if claims:
            role = "supervisor" if claims.get("role") == "supervisor" else (claims.get("role") or "member")
            state["auth_email"] = claims.get("email", "")
        state["auth_role"] = role or ""
        if (not auth_enforced() or method == "OPTIONS" or path == "/" or role
                or any(path == p or (p.endswith("/") and path.startswith(p)) for p in PUBLIC)):
            return await self.app(scope, receive, send)
        body = b'{"detail":"\\u0628\\u0631\\u0627\\u06cc \\u062f\\u06cc\\u062f\\u0646 \\u0628\\u0627\\u06cc\\u062f \\u0648\\u0627\\u0631\\u062f \\u0634\\u0648\\u06cc","auth_required":true}'
        await send({"type": "http.response.start", "status": 401,
                    "headers": [(b"content-type", b"application/json"), (b"www-authenticate", b"Bearer")]})
        await send({"type": "http.response.body", "body": body})
