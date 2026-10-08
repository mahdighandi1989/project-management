"""Google Drive — the ONLY durable home for inspection files and screenshots.

THE OWNER'S RULE (2026-10-08): «با اپلود شدنِ حجمِ زیادِ فایل‌ها نمی‌خوام تو
بک‌اند ذخیره بشه … فایل‌ها در پوشهٔ این پروژه ثبت بشه با رفرنسِ مشخص و در
فولدر و جای مشخص و لینک شه … در بک‌اند چیزی رو نگه ندار». The Render disk of
this service is 1 GB and holds the SQLite database; bulk bytes do not belong
there. Layout in the owner's Drive:

    My Drive / <GOOGLE_DRIVE_ROOT_FOLDER, default "project-management">
        / نظارت و سرکشی / گزارش-0007 / PM-INS-0007-F01 — نمونه.docx
                                     / PM-INS-0007-F01 — نمونه.docx.متن.txt
                                     / تصویرها / PM-INS-0007-S01-before.jpg
        / سطلِ حذف‌شده /     (removed files are MOVED here, never deleted)

HOW IT AUTHENTICATES — no secret in the repo, two ways, first one that works:

1. Environment on Render: ``GOOGLE_CLIENT_ID`` + ``GOOGLE_CLIENT_SECRET`` +
   ``GOOGLE_DRIVE_REFRESH_TOKEN``. Simplest when the owner already has a
   refresh token (e.g. from the OAuth Playground with their own client).
2. One click in the app («نظارت و سرکشی › فضای ذخیره‌سازی › اتصال»): the
   browser gets an authorization code from Google Identity Services (redirect
   URI ``postmessage``), the server exchanges it and keeps the refresh token
   ENCRYPTED (Fernet) in the ``settings`` table. Needs the client id/secret
   above and this site's origin registered on that OAuth client.

Least privilege: scope ``drive.file`` — the app sees only files and folders it
created itself. That is also why it creates its own project folder: a folder
made by hand would be invisible to it.

Plain REST over httpx (already a dependency); resumable uploads in 8 MB pieces;
downloads streamed. Every failure raises ``DriveError`` with a Persian reason
that says WHAT to fix — callers record it on the row (``store_note``).
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import os
import secrets
import threading
import time
from datetime import datetime
from typing import BinaryIO, Iterator, Optional

import httpx

logger = logging.getLogger("app.gdrive")

SCOPE_FILE = "https://www.googleapis.com/auth/drive.file"
SCOPES = f"openid email {SCOPE_FILE}"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
API = "https://www.googleapis.com/drive/v3"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
FOLDER_MIME = "application/vnd.google-apps.folder"
PIECE = 8 * 1024 * 1024  # resumable piece; must be a multiple of 256 KiB

KEY_AUTH = "inspection.gdrive_auth"        # encrypted {"refresh_token","email","connected_at"}
KEY_FOLDERS = "inspection.gdrive_folders"  # {"a/b/c": folder_id}
INSPECTION_DIR = "نظارت و سرکشی"
TRASH_DIR = "سطلِ حذف‌شده"

_lock = threading.Lock()
_access: dict = {"token": None, "exp": 0.0, "rt": None}


class DriveError(Exception):
    """A Drive call failed or Drive is not connected; the message says why (Persian)."""


def root_folder() -> str:
    return (os.environ.get("GOOGLE_DRIVE_ROOT_FOLDER") or "project-management").strip() or "project-management"


def client_id() -> str:
    return (os.environ.get("GOOGLE_CLIENT_ID") or "").strip()


def _client_secret() -> str:
    return (os.environ.get("GOOGLE_CLIENT_SECRET") or "").strip()


def client_configured() -> bool:
    return bool(client_id() and _client_secret())


# ---------------------------------------------------------------------------
# settings rows (the existing key/value table — no new table for this)
# ---------------------------------------------------------------------------
def _get(db, key: str) -> Optional[str]:
    from ..models.setting import Setting

    row = db.query(Setting).filter(Setting.key == key).first()
    return row.value if row else None


def _put(db, key: str, value: str, *, secret: bool = False) -> None:
    from ..models.setting import Setting

    row = db.query(Setting).filter(Setting.key == key).first()
    if row is None:
        db.add(Setting(key=key, value=value, value_type="string", category="storage",
                       description="«نظارت و سرکشی» — گوگل درایو", is_secret=secret))
    else:
        row.value = value
        row.updated_at = datetime.utcnow()


def _fernet():
    """Encryption for the stored refresh token.

    The key is derived from a server-side secret that already exists on Render
    (``DRIVE_TOKEN_KEY`` if set, else ``ADMIN_TOKEN`` / ``EXTERNAL_TOOL_TOKEN``).
    With none of them, a random key is created once beside the database on the
    persistent disk — never in the repo."""
    from cryptography.fernet import Fernet

    seed = ""
    for name in ("DRIVE_TOKEN_KEY", "ADMIN_TOKEN", "EXTERNAL_TOOL_TOKEN"):
        seed = (os.environ.get(name) or "").strip()
        if seed:
            break
    if not seed:
        from ..core.database import DATABASE_DIR

        path = os.path.join(DATABASE_DIR, ".inspection_drive_key")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                seed = fh.read().strip()
        except OSError:
            seed = secrets.token_urlsafe(48)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(seed)
    key = base64.urlsafe_b64encode(hashlib.sha256(("gdrive:" + seed).encode()).digest())
    return Fernet(key)


def _load_auth(db) -> dict:
    raw = _get(db, KEY_AUTH)
    if not raw:
        return {}
    try:
        return json.loads(_fernet().decrypt(raw.encode()).decode())
    except Exception:  # noqa: BLE001 - the key changed: treat as disconnected, loudly
        logger.warning("Drive credentials could not be decrypted (key changed?)")
        return {"broken": True}


def _save_auth(db, data: Optional[dict]) -> None:
    value = _fernet().encrypt(json.dumps(data).encode()).decode() if data else ""
    _put(db, KEY_AUTH, value, secret=True)
    with _lock:
        _access.update(token=None, exp=0.0, rt=None)


def _refresh_token(db) -> tuple[str, str]:
    """(refresh_token, source) — env first, then the in-app connection."""
    env_rt = (os.environ.get("GOOGLE_DRIVE_REFRESH_TOKEN") or "").strip()
    if env_rt:
        return env_rt, "env"
    auth = _load_auth(db)
    return (auth.get("refresh_token") or ""), "app"


def is_connected(db) -> bool:
    rt, _ = _refresh_token(db)
    return bool(rt and client_configured())


def status(db) -> dict:
    rt, source = _refresh_token(db)
    auth = _load_auth(db) if source == "app" else {}
    folders = _folders(db)
    root = folders.get(root_folder())
    insp = folders.get(f"{root_folder()}/{INSPECTION_DIR}")
    missing = []
    if not client_id():
        missing.append("GOOGLE_CLIENT_ID")
    if not _client_secret():
        missing.append("GOOGLE_CLIENT_SECRET")
    if not rt:
        missing.append("GOOGLE_DRIVE_REFRESH_TOKEN (یا اتصال از همین صفحه)")
    return {
        "client_configured": client_configured(),
        "client_id": client_id() or None,          # public by design (used by the browser)
        "connected": bool(rt and client_configured()),
        "source": source if rt else None,
        "broken": bool(auth.get("broken")),
        "account": auth.get("email"),
        "connected_at": auth.get("connected_at"),
        "root_folder": root_folder(),
        "root_folder_id": root,
        "root_folder_link": f"https://drive.google.com/drive/folders/{root}" if root else None,
        "inspection_folder_link": f"https://drive.google.com/drive/folders/{insp}" if insp else None,
        "scope": SCOPES,
        "missing": missing,
    }


# ---------------------------------------------------------------------------
# OAuth
# ---------------------------------------------------------------------------
def connect(db, code: str) -> dict:
    """Exchange the browser's authorization code for a refresh token and keep it."""
    if not client_configured():
        raise DriveError("GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET روی سرورِ Render تنظیم نشده — اتصال ممکن نیست")
    r = httpx.post(TOKEN_URL, data={
        "code": code, "client_id": client_id(), "client_secret": _client_secret(),
        "redirect_uri": "postmessage", "grant_type": "authorization_code",
    }, timeout=30)
    if r.status_code != 200:
        raise DriveError(f"گوگل کد را نپذیرفت ({r.status_code}): {r.text[:200]}")
    tok = r.json()
    granted = set((tok.get("scope") or "").split())
    if SCOPE_FILE not in granted:
        raise DriveError("اجازهٔ دسترسی به درایو داده نشد — هنگامِ تأیید، تیکِ «درایو» را بزن")
    if not tok.get("refresh_token"):
        raise DriveError("گوگل توکنِ ماندگار نداد — دوباره «اتصال» را بزن (صفحهٔ تأیید باید کامل نمایش داده شود)")
    return _store_connection(db, tok["refresh_token"], tok.get("id_token"))


def connect_refresh_token(db, refresh_token: str) -> dict:
    """The manual path: the owner pastes a refresh token made for this client."""
    if not client_configured():
        raise DriveError("GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET روی سرورِ Render تنظیم نشده")
    r = httpx.post(TOKEN_URL, data={
        "client_id": client_id(), "client_secret": _client_secret(),
        "refresh_token": refresh_token.strip(), "grant_type": "refresh_token",
    }, timeout=30)
    if r.status_code != 200:
        raise DriveError(f"این توکن با این کلاینت کار نکرد ({r.status_code}): {r.text[:200]}")
    scope = set((r.json().get("scope") or "").split())
    if scope and not ({SCOPE_FILE, "https://www.googleapis.com/auth/drive"} & scope):
        raise DriveError("این توکن دسترسیِ درایو ندارد (scope ِ drive.file یا drive لازم است)")
    return _store_connection(db, refresh_token.strip(), None)


def _store_connection(db, refresh_token: str, id_token: Optional[str]) -> dict:
    email = None
    if id_token:
        try:
            payload = id_token.split(".")[1]
            email = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))).get("email")
        except Exception:  # noqa: BLE001 - informational only
            email = None
    _save_auth(db, {"refresh_token": refresh_token, "email": email,
                    "connected_at": datetime.utcnow().isoformat() + "Z"})
    _put(db, KEY_FOLDERS, "{}")  # folder ids belong to the previous account, if any
    db.commit()
    ensure_folder(db, [root_folder(), INSPECTION_DIR])
    db.commit()
    return status(db)


def disconnect(db) -> None:
    auth = _load_auth(db)
    rt = auth.get("refresh_token")
    if rt:
        try:
            httpx.post(REVOKE_URL, data={"token": rt}, timeout=15)
        except httpx.HTTPError:
            pass  # revoking is a courtesy; forgetting it locally is what matters
    _save_auth(db, None)
    _put(db, KEY_FOLDERS, "{}")
    db.commit()


def _token(db) -> str:
    rt, _ = _refresh_token(db)
    if not rt or not client_configured():
        raise DriveError("گوگل درایو متصل نیست (نظارت و سرکشی › فضای ذخیره‌سازی)")
    with _lock:
        if _access["token"] and _access["rt"] == rt and _access["exp"] > time.time() + 60:
            return _access["token"]
    r = httpx.post(TOKEN_URL, data={
        "client_id": client_id(), "client_secret": _client_secret(),
        "refresh_token": rt, "grant_type": "refresh_token",
    }, timeout=30)
    if r.status_code != 200:
        raise DriveError(f"توکنِ درایو تمدید نشد ({r.status_code}) — شاید دسترسی لغو شده؛ دوباره متصل کن")
    data = r.json()
    with _lock:
        _access.update(token=data["access_token"], exp=time.time() + int(data.get("expires_in", 3600)), rt=rt)
    return data["access_token"]


def _h(db) -> dict:
    return {"Authorization": f"Bearer {_token(db)}"}


# ---------------------------------------------------------------------------
# folders
# ---------------------------------------------------------------------------
def _folders(db) -> dict:
    raw = _get(db, KEY_FOLDERS)
    try:
        return json.loads(raw) if raw else {}
    except ValueError:
        return {}


def _q(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'")


def ensure_folder(db, parts: list[str]) -> str:
    """The folder at ``parts`` (created when missing), ids cached in settings.
    A cached id that no longer exists (deleted by hand) is re-created."""
    cache = _folders(db)
    parent = "root"
    for i in range(len(parts)):
        key = "/".join(parts[: i + 1])
        fid = cache.get(key)
        if fid:
            r = httpx.get(f"{API}/files/{fid}", params={"fields": "id,trashed"}, headers=_h(db), timeout=30)
            if r.status_code == 200 and not r.json().get("trashed"):
                parent = fid
                continue
        name = parts[i]
        r = httpx.get(f"{API}/files", params={
            "q": f"name = '{_q(name)}' and mimeType = '{FOLDER_MIME}' and '{parent}' in parents and trashed = false",
            "fields": "files(id)", "pageSize": 1,
        }, headers=_h(db), timeout=30)
        found = r.json().get("files") if r.status_code == 200 else None
        if found:
            fid = found[0]["id"]
        else:
            r = httpx.post(f"{API}/files", params={"fields": "id"}, headers=_h(db), timeout=30,
                           json={"name": name, "mimeType": FOLDER_MIME, "parents": [parent]})
            if r.status_code not in (200, 201):
                raise DriveError(f"ساختِ پوشهٔ «{name}» در درایو ممکن نشد ({r.status_code})")
            fid = r.json()["id"]
        cache[key] = fid
        parent = fid
    _put(db, KEY_FOLDERS, json.dumps(cache, ensure_ascii=False))
    return parent


def report_folder_parts(report_number: int, *sub: str) -> list[str]:
    return [root_folder(), INSPECTION_DIR, f"گزارش-{int(report_number):04d}", *sub]


def folder_link(folder_id: str) -> str:
    return f"https://drive.google.com/drive/folders/{folder_id}" if folder_id else ""


# ---------------------------------------------------------------------------
# files
# ---------------------------------------------------------------------------
def upload(db, src: BinaryIO, *, name: str, mime: str, parent: str, size: int,
           description: str = "") -> dict:
    """Resumable, streamed upload. Returns {id, link, md5}."""
    src.seek(0)
    meta = {"name": name, "parents": [parent]}
    if description:
        meta["description"] = description[:900]
    start = httpx.post(UPLOAD, params={"uploadType": "resumable", "fields": "id,webViewLink,md5Checksum"},
                       headers={**_h(db), "X-Upload-Content-Type": mime or "application/octet-stream",
                                "X-Upload-Content-Length": str(size),
                                "Content-Type": "application/json; charset=UTF-8"},
                       json=meta, timeout=60)
    if start.status_code != 200 or not start.headers.get("location"):
        raise DriveError(f"شروعِ آپلود در درایو ممکن نشد ({start.status_code}): {start.text[:200]}")
    session_url = start.headers["location"]
    sent = 0
    with httpx.Client(timeout=300) as c:
        while True:
            piece = src.read(PIECE)
            end = sent + len(piece) - 1
            headers = {"Content-Length": str(len(piece))}
            if size:
                headers["Content-Range"] = f"bytes {sent}-{end}/{size}" if piece else f"bytes */{size}"
            r = c.put(session_url, content=piece, headers=headers)
            sent += len(piece)
            if r.status_code in (200, 201):
                data = r.json()
                return {"id": data["id"], "link": data.get("webViewLink") or "",
                        "md5": data.get("md5Checksum") or ""}
            if r.status_code != 308:
                raise DriveError(f"آپلود در درایو قطع شد ({r.status_code})")
            if not piece:
                raise DriveError("آپلود در درایو کامل نشد")


def upload_bytes(db, data: bytes, *, name: str, mime: str, parent: str, description: str = "") -> dict:
    return upload(db, io.BytesIO(data), name=name, mime=mime, parent=parent, size=len(data),
                  description=description)


def iter_download(db, file_id: str) -> Iterator[bytes]:
    """The file's bytes, streamed. Raises DriveError BEFORE yielding when unreachable."""
    client = httpx.Client(timeout=300)
    req = client.build_request("GET", f"{API}/files/{file_id}", params={"alt": "media"}, headers=_h(db))
    resp = client.send(req, stream=True)
    if resp.status_code != 200:
        resp.close()
        client.close()
        raise DriveError(f"فایل از درایو گرفته نشد ({resp.status_code}) — شاید دستی حذف شده")

    def gen() -> Iterator[bytes]:
        try:
            yield from resp.iter_bytes(1024 * 1024)
        finally:
            resp.close()
            client.close()

    return gen()


def download_bytes(db, file_id: str) -> bytes:
    return b"".join(iter_download(db, file_id))


def move_to_folder(db, file_id: str, parts: list[str]) -> None:
    """Move a file (keeping it) into the folder at ``parts``."""
    target = ensure_folder(db, parts)
    meta = httpx.get(f"{API}/files/{file_id}", params={"fields": "parents"}, headers=_h(db), timeout=30)
    parents = ",".join(meta.json().get("parents", [])) if meta.status_code == 200 else ""
    r = httpx.patch(f"{API}/files/{file_id}", params={"addParents": target, "removeParents": parents},
                    headers=_h(db), json={}, timeout=30)
    if r.status_code != 200:
        raise DriveError(f"جابه‌جاییِ فایل در درایو ممکن نشد ({r.status_code})")


def move_to_trash_folder(db, file_id: str) -> None:
    """Quarantine, not deletion: the file is moved into «سطلِ حذف‌شده»."""
    move_to_folder(db, file_id, [root_folder(), TRASH_DIR])
