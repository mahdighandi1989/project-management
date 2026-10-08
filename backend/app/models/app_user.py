"""Who may use the app — people who signed in with Google.

Owners come from ``ADMIN_EMAILS`` on the server and are approved automatically;
anyone else is ``pending`` until an owner approves them («کاربران»).
``token_version`` revokes every session of a user at once.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from ..core.database import Base


class AppUser(Base):
    __tablename__ = "app_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(200), default="")
    picture = Column(String(500), default="")
    google_sub = Column(String(64), index=True, default="")
    #: owner · member
    role = Column(String(20), default="member")
    #: approved · pending · blocked
    status = Column(String(20), default="pending")
    token_version = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    login_count = Column(Integer, default=0)

    def to_dict(self) -> dict:
        iso = lambda d: (d.replace(microsecond=0).isoformat() + "Z") if d else None  # noqa: E731
        return {"id": self.id, "email": self.email, "name": self.name or "", "picture": self.picture or "",
                "role": self.role, "status": self.status, "created_at": iso(self.created_at),
                "last_login_at": iso(self.last_login_at), "login_count": int(self.login_count or 0)}
