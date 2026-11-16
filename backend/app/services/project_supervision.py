"""(PM-INS-0013) «نظارت و سرکشیِ همان پروژه» + «فیدِ رویدادِ همهٔ پروژه‌ها» — read-only, live from GitHub.

Owner (2026-11-15): «برای هر پروژه یک تب "نظارت و سرکشیِ همان پروژه" … برگه‌های باز/فوری/پاسخ‌داده و زمانِ دورِ
بعدیِ ناظرِ همان پروژه را زنده نشان دهد (فقط‌خواندنی کافی است، اول)» و «هر ایجاد/تغییر/حذفِ فایل یا کامیت در هر ۹
ریپو در یک فیدِ رویداد».

Where each piece comes from — nothing is invented:
* THIS project's board lives in our own DB (the route reads it directly).
* A sibling project's board lives on ITS server. It is read only when the owner has set
  ``PROJECT_SUPERVISION_SOURCES`` (JSON ``{"owner/repo": {"base": "https://…", "token_env": "ENV_NAME"}}``) — the
  token itself stays in that env var on Render, never in code. Without it the tab says so plainly.
* What every repo has in git (``docs/supervisor/*`` prompts + their version/updated frontmatter, the
  ``supervisor-pending/*`` branches, recent commits that name a sheet ``…-INS-…``) is read from GitHub.
* The event feed is the commits of every watched repo, with the files each one added/modified/removed.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

API = "https://api.github.com"
TTL = int(os.environ.get("PROJECT_SUPERVISION_TTL", "300"))
_cache: dict[str, tuple[float, Any]] = {}
_SHEET_RE = re.compile(r"\b([A-Z]{2,8}-INS-\d{3,5})\b")
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")


def valid_repo(full: str) -> bool:
    return bool(_REPO_RE.match(full or "")) and ".." not in full


def _offline() -> bool:
    return os.environ.get("REPO_DOCS_OFFLINE", "") == "1" or "PYTEST_CURRENT_TEST" in os.environ


def _headers() -> dict[str, str]:
    h = {"Accept": "application/vnd.github+json", "User-Agent": "project-management-supervision"}
    try:
        from .oversight_service import get_github_token

        tok = get_github_token()
    except Exception:  # noqa: BLE001
        tok = os.environ.get("GITHUB_TOKEN", "")
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def _gh(path: str, params: Optional[dict] = None) -> Any:
    with httpx.Client(timeout=12) as c:
        r = c.get(f"{API}{path}", headers=_headers(), params=params)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()


def _cached(key: str, fetch, ttl: int = TTL) -> tuple[Any, str]:
    now = time.time()
    hit = _cache.get(key)
    if hit and now - hit[0] < ttl:
        return hit[1], "cache"
    if _offline():
        return (hit[1], "stale") if hit else (None, "offline")
    try:
        val = fetch()
        _cache[key] = (now, val)
        return val, "github"
    except Exception as e:  # noqa: BLE001
        logger.info("project_supervision: %s failed (%s)", key, e)
        return (hit[1], "stale") if hit else (None, f"error: {type(e).__name__}")


# ---------------------------------------------------------------------------
# the repos — every watched repo of «اتاق فرمان» + this one
# ---------------------------------------------------------------------------
def watched_repos() -> list[str]:
    from .repo_docs import repo as self_repo

    out: list[str] = []
    try:
        from .oversight_service import get_oversight_service

        for w in get_oversight_service().watched:
            name = (getattr(w, "repo_full_name", "") or "").strip()
            if valid_repo(name) and name not in out:
                out.append(name)
    except Exception as e:  # noqa: BLE001 - the list is best-effort; this repo is always there
        logger.info("project_supervision: watched list failed (%s)", e)
    me = self_repo()
    if me not in out:
        out.append(me)
    return out


def is_self(full: str) -> bool:
    from .repo_docs import repo as self_repo

    return full.lower() == self_repo().lower()


# ---------------------------------------------------------------------------
# what git holds about a repo's supervisor
# ---------------------------------------------------------------------------
def parse_frontmatter(text: str) -> dict[str, str]:
    """``version``/``updated``/``name`` from a leading ``---`` YAML block (flat keys only)."""
    out: dict[str, str] = {}
    if not text or not text.startswith("---"):
        return out
    end = text.find("\n---", 3)
    if end < 0:
        return out
    for line in text[3:end].splitlines():
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line.strip())
        if m and m.group(2) and not m.group(2).startswith(("-", "[")):
            out[m.group(1)] = m.group(2).strip().strip('"')
    return out


def _file_text(full: str, path: str) -> Optional[str]:
    import base64

    data = _gh(f"/repos/{full}/contents/{path}")
    if not data or not isinstance(data, dict) or data.get("encoding") != "base64":
        return None
    try:
        return base64.b64decode(data.get("content") or "").decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return None


def supervisor_in_git(full: str) -> dict:
    def fetch() -> dict:
        listing = _gh(f"/repos/{full}/contents/docs/supervisor") or []
        names = [x.get("name") for x in listing if isinstance(x, dict)] if isinstance(listing, list) else []
        prompts = []
        for fname in ("URGENT_PROMPT.md", "PROMPT.md"):
            if fname in names:
                fm = parse_frontmatter(_file_text(full, f"docs/supervisor/{fname}") or "")
                prompts.append({"file": f"docs/supervisor/{fname}", "version": fm.get("version", ""),
                                "updated": fm.get("updated", ""), "name": fm.get("name", "")})
        branches = _gh(f"/repos/{full}/branches", {"per_page": 100}) or []
        pending = [b.get("name") for b in branches
                   if isinstance(b, dict) and str(b.get("name", "")).startswith("supervisor-pending/")]
        commits = _gh(f"/repos/{full}/commits", {"per_page": 60}) or []
        sheets: list[dict] = []
        for c in commits if isinstance(commits, list) else []:
            msg = ((c.get("commit") or {}).get("message") or "").split("\n", 1)[0]
            refs = sorted(set(_SHEET_RE.findall(msg)))
            if refs or "supervisor" in msg.lower():
                sheets.append({"sha": (c.get("sha") or "")[:7], "message": msg[:200], "sheets": refs,
                               "date": ((c.get("commit") or {}).get("committer") or {}).get("date", ""),
                               "url": c.get("html_url", "")})
        return {"has_supervisor_dir": bool(names), "files": names[:40], "prompts": prompts,
                "pending_branches": pending, "supervisor_commits": sheets[:20]}

    val, src = _cached(f"git:{full}", fetch)
    return {"source": src, **(val or {"has_supervisor_dir": None, "files": [], "prompts": [],
                                      "pending_branches": [], "supervisor_commits": []})}


# ---------------------------------------------------------------------------
# a sibling project's live board, on its own server (opt-in by env)
# ---------------------------------------------------------------------------
def _sources() -> dict:
    try:
        d = json.loads(os.environ.get("PROJECT_SUPERVISION_SOURCES", "") or "{}")
        return {k.lower(): v for k, v in d.items() if isinstance(v, dict)} if isinstance(d, dict) else {}
    except ValueError:
        return {}


def remote_board(full: str) -> dict:
    cfg = _sources().get(full.lower())
    if not cfg or not str(cfg.get("base", "")).startswith("https://"):
        return {"configured": False,
                "reason": "نشانیِ سرورِ این پروژه و توکنِ خواندنش در PROJECT_SUPERVISION_SOURCES ِ Render تنظیم نشده"}
    base = str(cfg["base"]).rstrip("/")
    tok = os.environ.get(str(cfg.get("token_env", "")), "") if cfg.get("token_env") else ""

    def fetch() -> dict:
        h = {"X-Supervisor-Token": tok} if tok else {}
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base}/api/inspection", headers=h, params={"limit": 200})
            r.raise_for_status()
            board = r.json()
            sched = {}
            try:
                s = c.get(f"{base}/api/inspection/schedule", headers=h)
                if s.status_code == 200:
                    sched = s.json()
            except Exception:  # noqa: BLE001
                pass
        return summarize_board(board, sched)

    val, src = _cached(f"board:{full}", fetch, ttl=60)
    if val is None:
        return {"configured": True, "ok": False, "reason": f"سرورِ پروژه پاسخ نداد ({src})"}
    return {"configured": True, "ok": True, "source": src, **val}


def summarize_board(board: dict, sched: dict) -> dict:
    """The same shape for our board and a sibling's: counts + the open/urgent/answered sheets + next round."""
    reports = list((board or {}).get("reports") or [])

    def slim(r: dict) -> dict:
        notes = r.get("notes") or []
        last = notes[-1] if notes else {}
        return {"number": r.get("number"), "ref": r.get("ref") or r.get("reference") or "",
                "title": (r.get("title") or (notes[0].get("text") if notes else "") or "")[:160],
                "status": r.get("status"), "urgent": bool(r.get("urgent") or r.get("urgent_waiting")),
                "page_label": r.get("page_label") or r.get("page") or "",
                "outcome": (r.get("glow") or {}).get("tone") or last.get("outcome") or "",
                "updated": r.get("updated_at") or last.get("at") or r.get("created_at") or ""}

    items = [slim(r) for r in reports]
    return {
        "counts": (board or {}).get("counts") or {},
        "urgent_waiting": (board or {}).get("urgent_waiting", sum(1 for i in items if i["urgent"])),
        "open": [i for i in items if i["status"] == "open"][:30],
        "urgent": [i for i in items if i["urgent"]][:30],
        "answered": [i for i in items if i["status"] == "answered"][:30],
        "next_round": ((sched or {}).get("urgent") or {}).get("next_round"),
        "next_full": ((sched or {}).get("full") or {}).get("next_at"),
        "crons": {"urgent": ((sched or {}).get("urgent") or {}).get("cron_utc"),
                  "full": ((sched or {}).get("full") or {}).get("cron_utc")},
    }


# ---------------------------------------------------------------------------
# «فیدِ رویدادِ همهٔ پروژه‌ها»
# ---------------------------------------------------------------------------
def _repo_events(full: str, per_repo: int, detail: int) -> list[dict]:
    def fetch() -> list[dict]:
        commits = _gh(f"/repos/{full}/commits", {"per_page": per_repo}) or []
        out = []
        for i, c in enumerate(commits if isinstance(commits, list) else []):
            sha = c.get("sha") or ""
            cm = c.get("commit") or {}
            ev = {"repo": full, "sha": sha[:7], "url": c.get("html_url", ""),
                  "message": (cm.get("message") or "").split("\n", 1)[0][:200],
                  "author": ((cm.get("author") or {}).get("name") or ""),
                  "date": ((cm.get("committer") or {}).get("date") or ""),
                  "files": None}
            if i < detail:
                try:
                    d = _gh(f"/repos/{full}/commits/{sha}") or {}
                    ev["files"] = [{"path": f.get("filename"), "status": f.get("status"),
                                    "additions": f.get("additions", 0), "deletions": f.get("deletions", 0)}
                                   for f in (d.get("files") or [])[:40]]
                except Exception:  # noqa: BLE001 - the commit line is still shown without its files
                    pass
            out.append(ev)
        return out

    val, _src = _cached(f"feed:{full}:{per_repo}:{detail}", fetch)
    return val or []


def event_feed(limit: int = 60, per_repo: int = 12, detail: int = 6, repo: Optional[str] = None) -> dict:
    repos = [repo] if repo else watched_repos()
    errors: list[str] = []
    events: list[dict] = []
    with ThreadPoolExecutor(max_workers=min(6, max(1, len(repos)))) as ex:
        for full, evs in zip(repos, ex.map(lambda r: _repo_events(r, per_repo, detail), repos)):
            if not evs:
                errors.append(full)
            events.extend(evs)
    events.sort(key=lambda e: e.get("date") or "", reverse=True)
    counts = {"added": 0, "modified": 0, "removed": 0, "renamed": 0}
    for e in events:
        for f in e.get("files") or []:
            k = f.get("status") or ""
            if k in counts:
                counts[k] += 1
    return {"ok": True, "repos": repos, "unreachable": errors, "events": events[:limit],
            "file_counts": counts, "offline": _offline()}
