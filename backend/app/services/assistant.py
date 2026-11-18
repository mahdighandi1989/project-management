"""«دستیار» — the roaming assistant on every page (owner, 2026-11-15, plan item 2).

It replaces the «مناظره» page in the menu (the debate page and API stay, quarantined,
reachable from «آرشیو»). The assistant is meant to know the whole project and stay
current after every small change, so NOTHING about the project is hard-coded here:
every question re-reads, live,

* the site map and the help text of the page the owner is on — sent by the frontend
  from ``frontend/src/lib/siteMap.ts`` (the same registry that draws the menu, the home
  page and the help circle, so a new page is known the moment it ships);
* the newest entries of ``docs/WORKLOG.md`` and the newest commits on GitHub ``main``
  (``repo_docs``) — every session/model/human that changes the project logs there;
* the WORKLOG sections that match the question (simple term retrieval);
* live counts: watched repos and their tasks («اتاق فرمان»), open «نظارت و سرکشی» sheets.

The assistant only READS and advises. Conversations are kept (small JSON files) so
«آرشیو» can list them; «چند مدل» asks several models at once — the debate idea kept
inside the chat.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from . import repo_docs

logger = logging.getLogger(__name__)

MAX_TURNS = 16
MAX_CHARS = 6000
MAX_CONVERSATIONS = 300
WORKLOG_PATH = "docs/WORKLOG.md"

#: fast/cheap first — the first available one is the default
PREFERRED = (
    "claude-haiku", "gemini-2.5-flash", "gemini-flash", "gpt-4o-mini", "deepseek-chat",
    "claude-sonnet", "gpt-4o", "gemini-2.5-pro",
)


def _storage() -> Path:
    env = os.environ.get("ASSISTANT_STORAGE_PATH")
    p = Path(env) if env else Path(__file__).resolve().parents[2] / "storage" / "assistant"
    p.mkdir(parents=True, exist_ok=True)
    return p


# -- WORKLOG parsing ------------------------------------------------------------------------
_HEAD = re.compile(r"^#{2,3} (?=\S)", re.M)


def worklog_sections(text: str) -> list[dict[str, str]]:
    """Split the work log into entries (``## …`` / ``### …``), oldest first. The header is skipped."""
    parts = _HEAD.split(text)
    heads = _HEAD.findall(text)
    out = []
    for body in parts[1:] if len(parts) > 1 else []:
        title, _, rest = body.partition("\n")
        out.append({"title": title.strip(), "body": rest.strip()})
    del heads
    return out


_STOP = set("و در به از که را با این آن است بود برای یا هم تا بر چه چی کی کجا چرا من تو ما شما او های ها می یک کن کنم کنی بگو بده بدی بهم برام درباره راجع صفحه".split())


def _terms(text: str) -> list[str]:
    words = [w for w in re.findall(r"[\w‌]+", text or "") if len(w) >= 3 and w not in _STOP]
    out: list[str] = []
    for w in words:
        if w not in out:
            out.append(w)
    return out[:10]


def _matching(sections: list[dict[str, str]], question: str, k: int = 3) -> list[dict[str, str]]:
    terms = _terms(question)
    if not terms:
        return []
    scored = []
    for i, s in enumerate(sections):
        blob = (s["title"] + "\n" + s["body"]).lower()
        score = sum(blob.count(t.lower()) for t in terms)
        if score:
            scored.append((score, i, s))
    scored.sort(key=lambda x: (-x[0], -x[1]))
    return [s for _, _, s in scored[:k]]


def _clip(s: str, n: int) -> str:
    return s if len(s) <= n else s[:n] + " …"


# -- live context ---------------------------------------------------------------------------
async def _live_counts() -> str:
    lines = []
    try:
        from .oversight_service import get_oversight_service

        svc = get_oversight_service()
        watched = await svc.list_watched()
        tasks = await svc.list_tasks()
        by_status: dict[str, int] = {}
        for t in tasks:
            by_status[t.get("status", "?")] = by_status.get(t.get("status", "?"), 0) + 1
        lines.append(f"- «اتاق فرمان» — **تسک‌ها** (کارهای ساخته‌شده برای مخازن؛ «برگه» نیستند): {len(watched)} مخزنِ تحتِ پایش؛ "
                     f"تسک‌ها بر اساسِ وضعیت (awaiting_review = منتظرِ بازبینیِ تسک، نه برگه): "
                     + "، ".join(f"{k}={v}" for k, v in sorted(by_status.items())))
        if watched:
            lines.append("  مخازن: " + "، ".join(w.get("repo_full_name", "?") for w in watched[:15]))
    except Exception as e:  # noqa: BLE001
        lines.append(f"- «اتاق فرمان»: خوانده نشد ({type(e).__name__})")
    try:
        from datetime import timedelta as _td

        from ..core.database import SessionLocal
        from ..models.inspection import InspectionReport

        # PM-INS-0020 — the assistant answered «آخرین برگه 0018، ۲۶۷ در انتظار» (real: 0019 and 1): it got bare status
        # counts and mixed them with the command-room TASKS. Now: labelled, the same numbers the page shows, the
        # newest sheets by number with their Dubai time.
        db = SessionLocal()
        try:
            rows = db.query(InspectionReport.number, InspectionReport.status, InspectionReport.title,
                            InspectionReport.created_at, InspectionReport.urgent_at).all()
        finally:
            db.close()
        counts: dict[str, int] = {}
        for _n, st, _t, _c, _u in rows:
            counts[st] = counts.get(st, 0) + 1
        fa_status = {"open": "در انتظارِ ناظر", "answered": "ناظر پاسخ داد", "approved": "تأییدِ مالک",
                     "filed": "بایگانی"}
        newest = sorted(rows, key=lambda r: r[0] or 0, reverse=True)[:5]

        def _dubai(dt):
            return (dt + _td(hours=4)).strftime("%Y-%m-%d %H:%M") + " دبی" if dt else "?"

        lines.append(
            "- «نظارت و سرکشی» — **برگه‌ها** (گزارش‌های مالک برای ناظر؛ با «تسکِ اتاق فرمان» فرق دارند): "
            f"کل {len(rows)}؛ " + "، ".join(f"{fa_status.get(k, k)}={v}" for k, v in counts.items())
        )
        for n, st, t, c, u in newest:
            lines.append(f"  - PM-INS-{(n or 0):04d} · {fa_status.get(st, st)}{' · فوری' if u else ''} · {_dubai(c)} · {_clip(t or '', 90)}")
    except Exception as e:  # noqa: BLE001
        lines.append(f"- «نظارت و سرکشی»: خوانده نشد ({type(e).__name__})")
    return "\n".join(lines)


async def build_context(question: str, page: dict[str, Any], site_map: list[dict[str, Any]]) -> dict[str, Any]:
    """Everything the model sees besides the conversation — returned too, so the UI can show «از کجا می‌داند»."""
    sources: list[str] = []
    try:
        text, src = await asyncio.to_thread(repo_docs.read_text, WORKLOG_PATH)
        sections = worklog_sections(text)
        sources.append(f"WORKLOG ({src}, {len(sections)} ورودی)")
    except Exception:  # noqa: BLE001
        sections = []
    commits = await asyncio.to_thread(repo_docs.recent_commits, 15)
    if commits:
        sources.append(f"GitHub commits ({len(commits)})")
    counts = await _live_counts()
    sources.append("وضعیتِ زندهٔ اتاق فرمان و نظارت")

    newest = sections[-6:]
    matched = [s for s in _matching(sections, question) if s not in newest]

    site_lines = []
    for item in site_map[:80]:
        site_lines.append(f"- {item.get('href')} — {item.get('label')}: {_clip(str(item.get('desc') or ''), 200)}")

    parts = [
        "## نقشهٔ صفحه‌های برنامه (زنده، از رجیستریِ منو)\n" + ("\n".join(site_lines) or "(ارسال نشد)"),
        f"## صفحه‌ای که کاربر الان در آن است\n{page.get('path', '?')} — {page.get('label', '')}\n"
        + _clip(str(page.get("help") or ""), 1500),
        "## وضعیتِ زنده\n" + counts,
        "## تازه‌ترین ورودی‌های دفترِ کار (docs/WORKLOG.md، جدیدترین آخر)\n"
        + "\n\n".join(f"### {s['title']}\n{_clip(s['body'], 900)}" for s in newest),
    ]
    if matched:
        parts.append("## ورودی‌های مرتبط با پرسش در دفترِ کار\n"
                     + "\n\n".join(f"### {s['title']}\n{_clip(s['body'], 1200)}" for s in matched))
    if commits:
        parts.append("## تازه‌ترین کامیت‌ها روی main\n"
                     + "\n".join(f"- {c['date'][:16]} {c['sha']} {c['message']}" for c in commits))
    # PM-INS-0028 — relevant experiences from «مرکز دانش» (usage is recorded there)
    exp_line = ""
    try:
        from .knowledge_center_service import experience_context

        kc = await experience_context(question, "assistant", str(page.get("path") or ""))
        if kc.get("block"):
            parts.append(kc["block"])
            exp_line = kc["line"]
            sources.append(f"مرکز دانش ({len(kc['entries'])} تجربه)")
    except Exception:  # noqa: BLE001
        pass
    return {"text": "\n\n".join(parts), "sources": sources, "experiences_line": exp_line}


SYSTEM = """تو «دستیار» ِ برنامهٔ AI Creator Engine (پروژهٔ project-management) هستی: یک چتِ سیار که در همهٔ صفحه‌ها هست.
کارت: راهنماییِ دقیق دربارهٔ همین برنامه و پروژه‌هایش — هر صفحه چه می‌کند، کجا چه کاری انجام می‌شود، آخرین تغییرات چه بوده،
گامِ بعدی چیست — و کمک در هر کارِ دیگری که کاربر بخواهد.
قواعد:
- فارسی، روشن و کوتاه جواب بده. برای صفحه‌ها پیوندِ مارک‌داون بده، مثل [اتاق فرمان](/oversight).
- آنچه دربارهٔ برنامه می‌گویی فقط از «بافتِ زنده» ِ زیر است؛ اگر در آن نیست، صادقانه بگو «در داده‌هایم نیست» و بگو کجا را ببیند.
- تو فقط می‌خوانی و راهنمایی می‌کنی؛ هیچ تغییری خودت اعمال نمی‌کنی. برای گزارشِ ایراد، «نظارت و سرکشی» را پیشنهاد کن.
- رمز، کلید یا ایمیل هرگز تکرار نکن.
- «برگه» (PM-INS-…، صفحهٔ «نظارت و سرکشی») و «تسک» (اتاق فرمان) دو چیزِ جدا هستند؛ عددِ یکی را برای دیگری نگو. «آخرین برگه» = بزرگ‌ترین
  شمارهٔ PM-INS در بافتِ زنده. زمان‌ها را به وقتِ دبی بگو (در بافت آمده).
"""


# -- models -------------------------------------------------------------------------------
def available_models() -> list[dict[str, Any]]:
    try:
        from .ai_manager import get_ai_manager

        models = get_ai_manager().get_available_models()
    except Exception as e:  # noqa: BLE001
        logger.warning("assistant: models unavailable: %s", e)
        return []
    out = []
    for m in models:
        if getattr(m, "is_image_generator", False):
            continue
        prov = m.provider.value if hasattr(m.provider, "value") else str(m.provider)
        out.append({"id": m.id, "name": m.name, "provider": prov, "vision": bool(getattr(m, "supports_images", False))})

    def rank(m: dict[str, Any]) -> int:
        for i, p in enumerate(PREFERRED):
            if m["id"].startswith(p):
                return i
        return len(PREFERRED)

    out.sort(key=rank)
    return out


async def _generate(model_id: str, fallbacks: list[str], system: str, turns: list[dict[str, str]]) -> dict[str, Any]:
    from .ai_base import Message
    from .ai_manager import get_ai_manager

    msgs = [Message(role="system", content=system)] + [Message(role=t["role"], content=t["content"]) for t in turns]
    ids = [model_id] + [f for f in fallbacks if f != model_id]
    r = await get_ai_manager().generate_with_fallback(model_ids=ids, messages=msgs, max_tokens=2048, temperature=0.4)
    return {"model_id": r.model_id, "content": r.content, "latency_ms": r.latency_ms, "tokens": r.tokens_used}


def _clean_turns(history: list[dict[str, Any]], message: str) -> list[dict[str, str]]:
    turns = []
    for t in history[-MAX_TURNS:]:
        role = t.get("role")
        if role in ("user", "assistant") and str(t.get("content") or "").strip():
            turns.append({"role": role, "content": _clip(str(t["content"]), MAX_CHARS)})
    turns.append({"role": "user", "content": _clip(message, MAX_CHARS)})
    return turns


async def ask(message: str, history: list[dict[str, Any]], page: dict[str, Any], site_map: list[dict[str, Any]],
              model_ids: Optional[list[str]] = None, conversation_id: Optional[str] = None) -> dict[str, Any]:
    if not message.strip():
        raise ValueError("پیام خالی است")
    models = available_models()
    if not models:
        raise RuntimeError("هیچ مدلِ فعالی نیست — کلیدِ یک ارائه‌دهنده را در «مدل‌ها و تنظیمات» وارد کنید.")
    all_ids = [m["id"] for m in models]
    chosen = [m for m in (model_ids or []) if m in all_ids] or [all_ids[0]]
    ctx = await build_context(message, page or {}, site_map or [])
    system = SYSTEM + "\n\n# بافتِ زنده\n" + ctx["text"]
    turns = _clean_turns(history or [], message)

    if len(chosen) == 1:
        answers = [await _generate(chosen[0], all_ids[:4], system, turns)]
    else:
        async def one(mid: str) -> dict[str, Any]:
            try:
                return await _generate(mid, [], system, turns)
            except Exception as e:  # noqa: BLE001
                return {"model_id": mid, "content": "", "error": str(e)[:300]}
        answers = list(await asyncio.gather(*(one(m) for m in chosen[:4])))

    if ctx.get("experiences_line"):
        for a in answers:
            if a.get("content"):
                a["content"] = a["content"].rstrip() + "\n\n" + ctx["experiences_line"]
    conv = save_turn(conversation_id, page, message, answers)
    return {"conversation_id": conv["id"], "answers": answers, "sources": ctx["sources"]}


# -- conversations (for «آرشیو») -------------------------------------------------------------
_SAFE_ID = re.compile(r"^[a-f0-9]{8,40}$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_turn(conversation_id: Optional[str], page: dict[str, Any], message: str, answers: list[dict[str, Any]]) -> dict[str, Any]:
    conv = get_conversation(conversation_id) if conversation_id else None
    if conv is None:
        conv = {"id": uuid.uuid4().hex[:16], "created_at": _now(), "title": _clip(message.strip().splitlines()[0], 80),
                "messages": []}
    conv["updated_at"] = _now()
    conv["messages"].append({"role": "user", "content": message, "page": (page or {}).get("path", ""), "at": _now()})
    for a in answers:
        conv["messages"].append({"role": "assistant", "content": a.get("content", ""), "model_id": a.get("model_id"),
                                 "error": a.get("error"), "at": _now()})
    try:
        (_storage() / f"{conv['id']}.json").write_text(json.dumps(conv, ensure_ascii=False), encoding="utf-8")
        _prune()
    except OSError as e:
        logger.warning("assistant: could not save conversation: %s", e)
    return conv


def _prune() -> None:
    files = sorted(_storage().glob("*.json"), key=lambda p: p.stat().st_mtime)
    for p in files[:-MAX_CONVERSATIONS]:
        p.unlink(missing_ok=True)


def get_conversation(cid: Optional[str]) -> Optional[dict[str, Any]]:
    if not cid or not _SAFE_ID.match(cid):
        return None
    p = _storage() / f"{cid}.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def list_conversations() -> list[dict[str, Any]]:
    out = []
    for p in _storage().glob("*.json"):
        try:
            c = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        out.append({"id": c.get("id"), "title": c.get("title", ""), "created_at": c.get("created_at"),
                    "updated_at": c.get("updated_at"), "messages_count": len(c.get("messages") or [])})
    out.sort(key=lambda c: c.get("updated_at") or "", reverse=True)
    return out


def delete_conversation(cid: str) -> bool:
    """Archive, never destroy: the file moves to ``deleted/`` (owner rule: nothing is removed)."""
    if not _SAFE_ID.match(cid or ""):
        return False
    p = _storage() / f"{cid}.json"
    if not p.is_file():
        return False
    d = _storage() / "deleted"
    d.mkdir(exist_ok=True)
    p.rename(d / p.name)
    return True
