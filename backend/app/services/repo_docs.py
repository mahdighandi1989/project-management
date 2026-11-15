"""Read this repository's own Markdown/docs and recent commits — LIVE from GitHub.

Why GitHub and not the disk: the backend image on Render is built from ``./backend``
only (``dockerContext: ./backend``), so ``docs/`` is not inside the container. Reading
the files from GitHub ``main`` also means the in-app handbook / work log / assistant
are always exactly what is on GitHub, with no extra deploy (owner, 2026-11-15:
«با گیت‌هاب متصل باشد و همزمان سینک شود»).

Order of sources for a file: GitHub (cached ``TTL`` seconds) → local checkout (dev,
tests) → the last copy that was fetched (if GitHub is briefly unreachable).
The repo is public; ``GITHUB_TOKEN`` is used when set only to lift the rate limit.
"""

from __future__ import annotations

import base64
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

#: ``owner/name`` of THIS project (not a secret). Override with ``SELF_REPO``.
DEFAULT_REPO = "mahdighandi1989/project-management"
TTL = int(os.environ.get("REPO_DOCS_TTL", "90"))
_REPO_ROOT = Path(__file__).resolve().parents[3]  # backend/app/services → repo root

_cache: dict[str, tuple[float, Any]] = {}


def repo() -> str:
    return (os.environ.get("SELF_REPO") or DEFAULT_REPO).strip()


def branch() -> str:
    return (os.environ.get("SELF_REPO_BRANCH") or "main").strip()


def _offline() -> bool:
    # tests and local runs never call GitHub unless asked to
    return os.environ.get("REPO_DOCS_OFFLINE", "") == "1" or "PYTEST_CURRENT_TEST" in os.environ


def _headers() -> dict[str, str]:
    h = {"Accept": "application/vnd.github+json", "User-Agent": "project-management-docs"}
    try:
        from .oversight_service import get_github_token

        tok = get_github_token()
    except Exception:  # noqa: BLE001
        tok = os.environ.get("GITHUB_TOKEN", "")
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def _get_json(url: str, params: Optional[dict] = None) -> Any:
    with httpx.Client(timeout=12) as c:
        r = c.get(url, headers=_headers(), params=params)
        r.raise_for_status()
        return r.json()


def _cached(key: str, fetch, ttl: int = TTL):
    now = time.time()
    hit = _cache.get(key)
    if hit and now - hit[0] < ttl:
        return hit[1], "cache"
    try:
        val = fetch()
        _cache[key] = (now, val)
        return val, "github"
    except Exception as e:  # noqa: BLE001
        logger.info("repo_docs: %s failed (%s)", key, e)
        if hit:
            return hit[1], "stale"
        raise


def local_path(path: str) -> Path:
    return _REPO_ROOT / path


def read_text(path: str) -> tuple[str, str]:
    """``(content, source)`` for a repo-relative path; raises FileNotFoundError."""
    path = path.lstrip("/")
    if ".." in Path(path).parts:
        raise FileNotFoundError(path)
    if not _offline():
        try:
            def fetch():
                data = _get_json(f"https://api.github.com/repos/{repo()}/contents/{path}", {"ref": branch()})
                if isinstance(data, dict) and data.get("encoding") == "base64":
                    return base64.b64decode(data["content"]).decode("utf-8", "replace")
                if isinstance(data, dict) and data.get("download_url"):
                    with httpx.Client(timeout=20) as c:
                        r = c.get(data["download_url"], headers=_headers())
                        r.raise_for_status()
                        return r.text
                raise FileNotFoundError(path)
            text, src = _cached(f"file:{path}", fetch)
            return text, src
        except Exception:  # noqa: BLE001
            pass
    lp = local_path(path)
    if lp.is_file():
        return lp.read_text(encoding="utf-8"), "local"
    raise FileNotFoundError(path)


def list_dir(path: str) -> list[dict[str, Any]]:
    """Entries ``{name, path, type}`` of a repo directory (GitHub, falling back to local)."""
    path = path.strip("/")
    if not _offline():
        try:
            data, _ = _cached(
                f"dir:{path}",
                lambda: _get_json(f"https://api.github.com/repos/{repo()}/contents/{path}", {"ref": branch()}),
            )
            if isinstance(data, list):
                return [{"name": d["name"], "path": d["path"], "type": d["type"]} for d in data]
        except Exception:  # noqa: BLE001
            pass
    lp = local_path(path)
    if lp.is_dir():
        return [
            {"name": p.name, "path": f"{path}/{p.name}", "type": "dir" if p.is_dir() else "file"}
            for p in sorted(lp.iterdir())
        ]
    return []


def recent_commits(n: int = 20, path: Optional[str] = None) -> list[dict[str, Any]]:
    """The newest commits on ``main`` (``sha``, ``date``, ``message``, ``author``)."""
    if _offline():
        return []
    params: dict[str, Any] = {"sha": branch(), "per_page": max(1, min(n, 100))}
    if path:
        params["path"] = path
    try:
        data, _ = _cached(
            f"commits:{path or ''}:{n}",
            lambda: _get_json(f"https://api.github.com/repos/{repo()}/commits", params),
            ttl=60,
        )
    except Exception:  # noqa: BLE001
        return []
    out = []
    for c in data or []:
        commit = c.get("commit") or {}
        out.append({
            "sha": (c.get("sha") or "")[:7],
            "date": (commit.get("author") or {}).get("date", ""),
            "message": (commit.get("message") or "").split("\n")[0][:200],
            "author": (commit.get("author") or {}).get("name", ""),
            "url": c.get("html_url", ""),
        })
    return out


def clear_cache() -> None:
    _cache.clear()
