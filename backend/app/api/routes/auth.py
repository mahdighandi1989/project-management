"""Sign-in with Google and the people allowed in — see ``core/auth.py`` for the why."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...core import auth as A
from ...core.database import get_db
from ...models.app_user import AppUser

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/config")
def config():
    """Public: what the login screen needs (the client id is public by design)."""
    return {"google_client_id": A.google_client_id() or None, "auth_enforced": A.auth_enforced(),
            "owners_configured": bool(A.admin_emails())}


class GoogleIn(BaseModel):
    credential: str = Field(..., min_length=20, max_length=5000)


@router.post("/google")
def google_login(body: GoogleIn, db: Session = Depends(get_db)):
    try:
        ident = A.verify_google_credential(body.credential)
    except A.AuthError as exc:
        raise HTTPException(exc.status, exc.detail) from None
    u = db.query(AppUser).filter(AppUser.email == ident["email"]).first()
    if u is None:
        u = AppUser(email=ident["email"], role="member", status="pending", token_version=0, login_count=0)
        db.add(u)
    if u.google_sub and u.google_sub != ident["sub"]:
        raise HTTPException(409, "این ایمیل به حسابِ گوگلِ دیگری متصل است")
    u.google_sub = ident["sub"]
    u.name = ident["name"] or u.name
    u.picture = ident["picture"] or u.picture
    if ident["email"] in A.admin_emails():
        u.role, u.status = "owner", "approved"
    u.last_login_at = datetime.utcnow()
    u.login_count = int(u.login_count or 0) + 1
    db.commit()
    db.refresh(u)
    if u.status == "blocked":
        raise HTTPException(403, "دسترسیِ این حساب مسدود است")
    if u.status != "approved":
        raise HTTPException(403, "درخواستِ دسترسیِ شما ثبت شد — منتظرِ تأییدِ مالک بمانید")
    token = A.create_token(sub=str(u.id), email=u.email, role=u.role, ver=int(u.token_version or 0))
    return {"access_token": token, "token_type": "bearer", "user": u.to_dict()}


@router.get("/me")
def me(request: Request, db: Session = Depends(get_db)):
    email = getattr(request.state, "auth_email", "") or ""
    role = getattr(request.state, "auth_role", "") or ""
    u = db.query(AppUser).filter(AppUser.email == email).first() if email else None
    return {"authenticated": bool(role), "role": role, "user": u.to_dict() if u else None,
            "auth_enforced": A.auth_enforced()}


def _owner(request: Request) -> None:
    if not A.auth_enforced():
        return
    if getattr(request.state, "auth_role", "") != "owner":
        raise HTTPException(403, "فقط مالک")


@router.post("/logout-all")
def logout_all(request: Request, db: Session = Depends(get_db)):
    email = getattr(request.state, "auth_email", "") or ""
    u = db.query(AppUser).filter(AppUser.email == email).first() if email else None
    if u is None:
        raise HTTPException(401, "وارد نشده‌اید")
    u.token_version = int(u.token_version or 0) + 1
    db.commit()
    return {"ok": True}


@router.get("/users")
def users(request: Request, db: Session = Depends(get_db)):
    _owner(request)
    rows = db.query(AppUser).order_by(AppUser.status.desc(), AppUser.created_at.desc()).all()
    return {"users": [u.to_dict() for u in rows], "owners_from_env": sorted(A.admin_emails())}


class UserPatch(BaseModel):
    status: str | None = Field(None, pattern="^(approved|pending|blocked)$")
    role: str | None = Field(None, pattern="^(owner|member)$")
    revoke_sessions: bool = False


@router.patch("/users/{user_id}")
def update_user(user_id: int, body: UserPatch, request: Request, db: Session = Depends(get_db)):
    _owner(request)
    u = db.query(AppUser).filter(AppUser.id == user_id).first()
    if u is None:
        raise HTTPException(404, "کاربر پیدا نشد")
    if u.email in A.admin_emails() and (body.status in ("pending", "blocked") or body.role == "member"):
        raise HTTPException(422, "مالکِ تعریف‌شده در ADMIN_EMAILS از این‌جا تغییر نمی‌کند")
    if body.status:
        u.status = body.status
    if body.role:
        u.role = body.role
    if body.revoke_sessions or body.status in ("pending", "blocked"):
        u.token_version = int(u.token_version or 0) + 1
    db.commit()
    return {"ok": True, "user": u.to_dict()}


@router.post("/supervisor-session")
def supervisor_session(request: Request):
    """The supervisor Routine's headless browser needs to see the pages too: the
    supervisor token buys a short session with the `supervisor` role (which the
    inspection API still refuses for ticks, deletes and urgent marks)."""
    if A.machine_caller({k.lower(): v for k, v in request.headers.items()}) != "supervisor":
        raise HTTPException(403, "فقط ناظر")
    return {"access_token": A.create_token(sub="0", email="supervisor@routine", role="supervisor"),
            "token_type": "bearer"}
