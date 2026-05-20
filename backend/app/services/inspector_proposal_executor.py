"""
🆕 (inspector-scan) Proposal executor — یک proposal از scan موردی Inspector
را با AI به کد قابل اعمال تبدیل می‌کند، و دکمهٔ «اعمال همه تغییرات» همه
proposalهای staged را با یک PR/commit به GitHub می‌فرستد.

طراحی:
- run_proposal(session_id, proposal_id, model_id):
    * proposal را از InspectorMessage پیدا می‌کند
    * فایل‌های target را از GitHub fetch می‌کند (محتوای فعلی)
    * AI را با strong_prompt + محتوای فعلی فراخوانی می‌کند تا فایل‌های
      جدید کامل تولید کند (نه patch)
    * نتیجه را به‌عنوان staging در یک InspectorMessage جدید با
      `kind=proposal_executed` لاگ می‌کند
- apply_all(session_id, commit_message, ...):
    * همهٔ proposalهای staging را جمع می‌کند
    * با github_pr_service.create_pr_with_changes (یا create_or_update_file)
      یک branch + commit + PR (یا commit مستقیم) می‌سازد
    * نتیجه را به‌عنوان آخرین پیام با `kind=apply_all_result` لاگ می‌کند
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── pull proposal payload from session messages ──────────────────
def _find_proposal_in_session(
    session_id: int, proposal_id: str
) -> Optional[Tuple[Dict[str, Any], int]]:
    """proposal را در InspectorMessage های session پیدا می‌کند.

    Returns: (proposal_dict, message_id) یا None.
    """
    try:
        from ..core.database import SessionLocal
        from ..models.inspector_session import InspectorMessage
    except Exception:
        return None

    db = SessionLocal()
    try:
        msgs = (
            db.query(InspectorMessage)
            .filter(InspectorMessage.session_id == int(session_id))
            .filter(InspectorMessage.action_type == "scan_complete")
            .order_by(InspectorMessage.id.desc())
            .limit(20)
            .all()
        )
        for m in msgs:
            try:
                ed = json.loads(m.extra_data) if isinstance(m.extra_data, str) else (m.extra_data or {})
            except Exception:
                continue
            for p in (ed.get("scan_proposals") or []):
                if str(p.get("proposal_id")) == str(proposal_id):
                    return p, m.id
        return None
    finally:
        db.close()


def _find_session_proposals(session_id: int) -> List[Tuple[Dict[str, Any], int]]:
    """همهٔ proposalهای session را برمی‌گرداند (با message_id برای آپدیت).

    دقت: اگر چند scan_complete باشد، همه proposalها برگردانده می‌شوند.
    """
    try:
        from ..core.database import SessionLocal
        from ..models.inspector_session import InspectorMessage
    except Exception:
        return []
    db = SessionLocal()
    out: List[Tuple[Dict[str, Any], int]] = []
    try:
        msgs = (
            db.query(InspectorMessage)
            .filter(InspectorMessage.session_id == int(session_id))
            .filter(InspectorMessage.action_type == "scan_complete")
            .order_by(InspectorMessage.id.asc())
            .all()
        )
        for m in msgs:
            try:
                ed = json.loads(m.extra_data) if isinstance(m.extra_data, str) else (m.extra_data or {})
            except Exception:
                continue
            for p in (ed.get("scan_proposals") or []):
                out.append((p, m.id))
        return out
    finally:
        db.close()


def _update_proposal_in_message(message_id: int, proposal_id: str, updates: Dict[str, Any]) -> bool:
    """proposal مشخصی در یک InspectorMessage را در DB آپدیت می‌کند."""
    try:
        from ..core.database import SessionLocal
        from ..models.inspector_session import InspectorMessage
    except Exception:
        return False
    db = SessionLocal()
    try:
        m = db.query(InspectorMessage).filter(InspectorMessage.id == int(message_id)).first()
        if not m:
            return False
        try:
            ed = json.loads(m.extra_data) if isinstance(m.extra_data, str) else (m.extra_data or {})
        except Exception:
            ed = {}
        proposals = ed.get("scan_proposals") or []
        changed = False
        for p in proposals:
            if str(p.get("proposal_id")) == str(proposal_id):
                p.update(updates)
                changed = True
                break
        if not changed:
            return False
        ed["scan_proposals"] = proposals
        m.extra_data = json.dumps(ed, ensure_ascii=False)
        db.commit()
        return True
    except Exception as e:
        logger.warning(f"_update_proposal_in_message failed: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def _resolve_repo_for_session(session_id: int) -> Optional[str]:
    """از session_id به repo_full_name (owner/repo) برسد."""
    try:
        from ..core.database import SessionLocal
        from ..models.inspector_session import InspectorSession
        from ..models.project import Project
    except Exception:
        return None
    db = SessionLocal()
    try:
        s = db.query(InspectorSession).filter(InspectorSession.id == int(session_id)).first()
        if not s:
            return None
        proj = db.query(Project).filter(Project.id == s.project_id).first()
        if proj is None:
            try:
                proj = db.query(Project).filter(Project.id == int(s.project_id)).first()
            except (ValueError, TypeError):
                proj = None
        if not proj:
            return None
        if proj.github_path:
            return proj.github_path.strip()
        if proj.github_url and "github.com/" in proj.github_url:
            tail = proj.github_url.split("github.com/", 1)[1].rstrip("/").rstrip(".git")
            if tail.count("/") >= 1:
                return "/".join(tail.split("/")[:2])
        return None
    finally:
        db.close()


# ─── prompt builder for code generation ───────────────────────────
def _build_codegen_prompt(
    proposal: Dict[str, Any],
    current_files: Dict[str, str],
) -> str:
    """prompt تولید کد بر اساس strong_prompt + محتوای فعلی فایل‌ها."""
    strong = proposal.get("strong_prompt") or ""
    target_files = proposal.get("target_files") or []
    if not target_files:
        target_files = [
            tl.get("path") for tl in (proposal.get("target_locations") or [])
            if isinstance(tl, dict) and tl.get("path")
        ]

    files_blob_parts: List[str] = []
    for path in target_files:
        content = current_files.get(path, "")
        if content:
            # حداکثر ۲۰KB در prompt
            snippet = content[:20000]
            files_blob_parts.append(
                f"=== فایل فعلی: {path} ===\n```\n{snippet}\n```"
            )
        else:
            files_blob_parts.append(
                f"=== فایل {path} ===\n(فایل وجود ندارد یا قابل خواندن نیست — اگر لازم بود می‌توانی فایل جدید بسازی)"
            )
    files_blob = "\n\n".join(files_blob_parts) if files_blob_parts else "(فایلی برای ویرایش مشخص نیست)"

    return f"""تو یک Senior Software Engineer هستی. وظیفه‌ات اعمال **دقیق** تغییرات روی فایل‌های زیر بر اساس درخواست است.

# 📋 دستورالعمل کامل (strong prompt)
{strong}

# 📁 محتوای فعلی فایل‌ها
{files_blob}

# 🎯 خروجی موردانتظار — فقط JSON خالص (بدون متن اضافی، بدون ```)
{{
  "changes": [
    {{
      "path": "مسیر دقیق فایل از ریشهٔ ریپو",
      "content": "محتوای **کامل** و **جدید** فایل پس از تغییر — کل فایل، نه فقط diff",
      "change_kind": "modify | create | delete",
      "summary": "خلاصهٔ ۱-۲ خطی تغییری که در این فایل اعمال شد"
    }}
  ],
  "overall_summary": "خلاصهٔ کلی تمام تغییرات — برای commit message کوتاه استفاده می‌شود",
  "risks": "ریسک‌ها/هشدارهایی که توسعه‌دهنده باید بداند",
  "tests_or_manual_steps": ["گام‌های تست/اعتبارسنجی پس از merge"]
}}

🚨 **بسیار مهم**:
- محتوای کامل فایل را برگردان، نه patch/diff
- اگر فایلی نباید تغییر کند، آن را در `changes` نگذار
- مسیرها دقیقاً مثل فایل‌های فعلی بالا باشند
- فقط JSON برگردان، هیچ متن اضافه‌ای قبل/بعد JSON نباشد
"""


# ─── extract JSON from AI response (resilient) ────────────────────
def _extract_json_from_ai(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    # try direct parse
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    # try removing markdown code fences
    cleaned = re.sub(r"^```(?:json)?\s*", "", text)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    # try extracting between first { and last }
    s = text.find("{")
    e = text.rfind("}")
    if s != -1 and e != -1 and e > s:
        try:
            return json.loads(text[s:e + 1])
        except Exception:
            pass
    return None


# ─── main: run a single proposal ──────────────────────────────────
async def run_proposal(
    *,
    session_id: int,
    proposal_id: str,
    model_id: Optional[str] = None,
) -> Dict[str, Any]:
    """proposal مشخص را با AI به code-ready تبدیل می‌کند و در session لاگ می‌کند.

    Returns: {success, proposal_id, changed_files, diff_summary, error?}
    """
    from .scan_v5.scan_inspector_session import log_scan_message

    found = _find_proposal_in_session(session_id, proposal_id)
    if not found:
        return {"success": False, "error": "proposal یافت نشد", "code": "proposal_not_found"}
    proposal, message_id = found

    # repo info
    repo = _resolve_repo_for_session(session_id)
    if not repo:
        return {"success": False, "error": "repo شناسایی نشد"}

    # fetch فایل‌های target
    current_files: Dict[str, str] = {}
    try:
        import aiohttp
        from .oversight_deep_scan_service import _fetch_file_content, _gh_get_json, GITHUB_API
        from ..core.config import get_github_token
        token = get_github_token()
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"} if token else {}
        info = await _gh_get_json_safe(GITHUB_API, repo, headers)
        branch = (info or {}).get("default_branch") or "main"
        target_files = proposal.get("target_files") or []
        if not target_files:
            target_files = [
                tl.get("path") for tl in (proposal.get("target_locations") or [])
                if isinstance(tl, dict) and tl.get("path")
            ]
        async with aiohttp.ClientSession() as http_session:
            for path in target_files[:12]:  # cap reasonable
                if not path:
                    continue
                try:
                    content = await _fetch_file_content(http_session, repo, path, headers, branch, 30000)
                    if content:
                        current_files[path] = content
                except Exception as fe:
                    logger.debug(f"fetch {path} failed: {fe}")
                    continue
    except Exception as e:
        logger.warning(f"run_proposal: fetching files failed: {e}")
        # ادامه بده با current_files خالی — مدل ممکن است فایل از اول بسازد

    # build prompt
    prompt = _build_codegen_prompt(proposal, current_files)

    # generate code
    try:
        from .ai_manager import get_ai_manager
        from .ai_base import Message
        ai_manager = get_ai_manager()
        response = await ai_manager.generate(
            model_id=model_id or "claude-sonnet-4-6",
            messages=[Message(role="user", content=prompt)],
            max_tokens=16000,
            temperature=0.2,
        )
        result_json = _extract_json_from_ai(response.content or "")
    except Exception as e:
        logger.exception(f"run_proposal AI call failed: {e}")
        _update_proposal_in_message(message_id, proposal_id, {
            "execution_status": "failed",
            "execution_error": str(e)[:500],
            "executed_at": _now_iso(),
        })
        log_scan_message(
            session_id=session_id,
            role="assistant",
            content=f"❌ خطا در اجرای پیشنهاد «{proposal.get('title', '')[:100]}»:\n```\n{str(e)[:400]}\n```",
            action_type="proposal_failed",
            model_id=model_id,
            extra_data={"kind": "proposal_executed", "proposal_id": proposal_id, "status": "failed", "error": str(e)[:500]},
        )
        return {"success": False, "error": str(e)[:300]}

    if not result_json or not isinstance(result_json.get("changes"), list):
        err_msg = "خروجی مدل قابل تجزیه نبود (انتظار JSON با فیلد changes)"
        _update_proposal_in_message(message_id, proposal_id, {
            "execution_status": "failed",
            "execution_error": err_msg,
            "executed_at": _now_iso(),
            "raw_response": (response.content or "")[:2000],
        })
        log_scan_message(
            session_id=session_id,
            role="assistant",
            content=f"❌ {err_msg} — پیشنهاد «{proposal.get('title', '')[:100]}»",
            action_type="proposal_failed",
            model_id=model_id,
            extra_data={"kind": "proposal_executed", "proposal_id": proposal_id, "status": "failed"},
        )
        return {"success": False, "error": err_msg}

    # success — store staging
    changes = result_json.get("changes") or []
    valid_changes = [
        c for c in changes
        if isinstance(c, dict) and c.get("path") and ("content" in c or c.get("change_kind") == "delete")
    ]
    diff_summary = result_json.get("overall_summary", "")[:1000]

    _update_proposal_in_message(message_id, proposal_id, {
        "execution_status": "applied_locally",
        "executed_at": _now_iso(),
        "staged_changes": valid_changes,
        "diff_summary": diff_summary,
        "risks": result_json.get("risks", "")[:1000],
        "manual_steps": (result_json.get("tests_or_manual_steps") or [])[:10],
        "execution_model_id": response.model_id if 'response' in locals() else model_id,
    })

    # لاگ پیام نتیجه
    changes_lines = "\n".join(
        f"- `{c.get('change_kind', 'modify')}` **{c.get('path')}** — {c.get('summary', '')[:200]}"
        for c in valid_changes
    )
    log_scan_message(
        session_id=session_id,
        role="assistant",
        content=(
            f"✅ پیشنهاد «{proposal.get('title', '')[:100]}» اجرا شد (staged):\n\n"
            f"{changes_lines}\n\n"
            f"**خلاصه:** {diff_summary}\n\n"
            f"این تغییرات هنوز commit نشده‌اند. برای اعمال نهایی، روی «✨ اعمال همهٔ تغییرات» کلیک کنید."
        ),
        action_type="proposal_executed",
        model_id=response.model_id if 'response' in locals() else model_id,
        extra_data={
            "kind": "proposal_executed",
            "proposal_id": proposal_id,
            "status": "applied_locally",
            "changed_files": [c.get("path") for c in valid_changes],
            "diff_summary": diff_summary,
        },
    )

    return {
        "success": True,
        "proposal_id": proposal_id,
        "changed_files": [c.get("path") for c in valid_changes],
        "diff_summary": diff_summary,
        "status": "applied_locally",
    }


# ─── helper: safer JSON fetch ──────────────────────────────────────
async def _gh_get_json_safe(api_base: str, repo: str, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
    try:
        import aiohttp
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{api_base}/repos/{repo}", headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as r:
                if r.status == 200:
                    return await r.json()
    except Exception:
        return None
    return None


# ─── apply-all: bundle staged changes + commit/push ────────────────
async def apply_all_staged(
    *,
    session_id: int,
    commit_message: Optional[str] = None,
    include_unexecuted: bool = False,
    branch_strategy: str = "new_pr",  # "new_pr" | "default_branch_commit"
    model_id: Optional[str] = None,
) -> Dict[str, Any]:
    """همهٔ proposalهای staged session را با یک PR/commit به GitHub می‌فرستد.

    اگر include_unexecuted=True، proposalهای pending را ابتدا با run_proposal
    اجرا می‌کنیم (با همان model_id).
    """
    from .scan_v5.scan_inspector_session import log_scan_message

    # 1) اول unexecuted ها را اجرا کن اگر لازم است
    if include_unexecuted:
        for prop, _mid in _find_session_proposals(session_id):
            if prop.get("execution_status") in ("pending", None):
                try:
                    await run_proposal(
                        session_id=session_id,
                        proposal_id=prop["proposal_id"],
                        model_id=model_id,
                    )
                except Exception as e:
                    logger.warning(f"apply_all: run_proposal {prop.get('proposal_id')} failed: {e}")

    # 2) جمع‌آوری همهٔ staged changes
    all_proposals = _find_session_proposals(session_id)
    staged: List[Tuple[Dict[str, Any], Dict[str, Any], int]] = []
    # هر مدخل: (proposal, change, message_id)
    for prop, mid in all_proposals:
        if prop.get("execution_status") != "applied_locally":
            continue
        for ch in (prop.get("staged_changes") or []):
            if isinstance(ch, dict) and ch.get("path"):
                staged.append((prop, ch, mid))

    if not staged:
        msg = "هیچ تغییر staged ای برای اعمال موجود نیست. ابتدا حداقل یک پیشنهاد را «اجرا با AI» کنید."
        log_scan_message(
            session_id=session_id,
            role="assistant",
            content=f"⚠️ {msg}",
            action_type="apply_all_skipped",
            extra_data={"kind": "apply_all_result", "status": "skipped", "reason": "no_staged"},
        )
        return {"success": False, "error": msg, "code": "no_staged"}

    # 3) deduplicate by path (آخرین change برای هر path برنده)
    files_map: Dict[str, Dict[str, Any]] = {}
    proposals_used: List[str] = []
    for prop, ch, _mid in staged:
        path = ch.get("path")
        if path:
            files_map[path] = ch
            if prop.get("proposal_id") not in proposals_used:
                proposals_used.append(prop["proposal_id"])

    # 4) repo info
    repo = _resolve_repo_for_session(session_id)
    if not repo:
        return {"success": False, "error": "repo برای session پیدا نشد"}
    owner, _, repo_name = repo.partition("/")
    if not owner or not repo_name:
        return {"success": False, "error": "repo_full_name نامعتبر"}

    # 5) commit_message اگر داده نشده، AI generate
    if not commit_message:
        commit_message = _auto_commit_message(staged)

    # 6) build files list برای create_pr_with_changes
    files_list = [
        {"path": path, "content": ch.get("content", "")}
        for path, ch in files_map.items()
        if ch.get("change_kind") != "delete"
    ]
    # توجه: delete در این مسیر پشتیبانی نمی‌شود — github_pr_service فقط create_or_update دارد

    # 7) فراخوانی github
    try:
        from .github_pr_service import get_github_pr_service
        from ..core.config import get_github_token
        token = get_github_token()
        pr_service = get_github_pr_service()
        branch_name = f"inspector-scan/{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{session_id}"
        pr_result = await pr_service.create_pr_with_changes(
            github_path=repo,
            branch_name=branch_name,
            title=commit_message[:100],
            description=_build_pr_description(staged, commit_message),
            files=files_list,
            token=token,
        )
        if not pr_result.get("success"):
            err = pr_result.get("error") or "خطای ناشناخته از GitHub"
            log_scan_message(
                session_id=session_id,
                role="assistant",
                content=f"❌ خطا در اعمال تغییرات به GitHub:\n```\n{err}\n```",
                action_type="apply_all_failed",
                extra_data={"kind": "apply_all_result", "status": "failed", "error": err[:500]},
            )
            return {"success": False, "error": err}
    except Exception as e:
        logger.exception(f"apply_all GitHub call failed: {e}")
        log_scan_message(
            session_id=session_id,
            role="assistant",
            content=f"❌ خطا در ارتباط با GitHub:\n```\n{str(e)[:400]}\n```",
            action_type="apply_all_failed",
            extra_data={"kind": "apply_all_result", "status": "failed", "error": str(e)[:500]},
        )
        return {"success": False, "error": str(e)[:300]}

    # 8) به‌روزرسانی proposalها به committed
    for prop, _ch, mid in staged:
        if prop.get("execution_status") == "applied_locally":
            _update_proposal_in_message(mid, prop["proposal_id"], {
                "execution_status": "committed_and_pushed",
                "committed_at": _now_iso(),
                "pr_url": pr_result.get("pr_url"),
                "branch": branch_name,
            })

    # 9) لاگ پیام نهایی
    pr_url = pr_result.get("pr_url") or pr_result.get("html_url") or ""
    log_scan_message(
        session_id=session_id,
        role="assistant",
        content=(
            f"✅ **همهٔ تغییرات اعمال شد**\n\n"
            f"- branch: `{branch_name}`\n"
            f"- فایل‌های تغییر یافته: {len(files_list)}\n"
            f"- پیشنهاد‌های شامل: {len(proposals_used)}\n"
            f"- commit message: {commit_message[:200]}\n\n"
            + (f"🔗 PR: {pr_url}" if pr_url else "(PR URL در دسترس نیست)")
        ),
        action_type="apply_all_result",
        extra_data={
            "kind": "apply_all_result",
            "status": "committed_and_pushed",
            "branch": branch_name,
            "pr_url": pr_url,
            "files_committed": [c["path"] for c in files_list],
            "proposals_used": proposals_used,
            "commit_message": commit_message,
        },
    )

    return {
        "success": True,
        "branch": branch_name,
        "pr_url": pr_url,
        "files_committed": [c["path"] for c in files_list],
        "proposals_used": proposals_used,
    }


def _auto_commit_message(staged: List[Tuple[Dict[str, Any], Dict[str, Any], int]]) -> str:
    """commit message ساده از proposal titles."""
    titles = list({s[0].get("title", "")[:80] for s in staged if s[0].get("title")})[:3]
    if not titles:
        return "اعمال تغییرات از اسکن موردی Inspector"
    return "اسکن موردی: " + " / ".join(titles)


def _build_pr_description(
    staged: List[Tuple[Dict[str, Any], Dict[str, Any], int]],
    commit_message: str,
) -> str:
    parts: List[str] = [
        "## اعمال تغییرات از اسکن موردی Inspector\n",
        f"**خلاصه:** {commit_message}\n",
        "### پیشنهاد‌های اعمال‌شده\n",
    ]
    seen = set()
    for prop, _ch, _mid in staged:
        pid = prop.get("proposal_id")
        if pid in seen:
            continue
        seen.add(pid)
        parts.append(f"- **{prop.get('title', '')[:120]}**")
        if prop.get("diff_summary"):
            parts.append(f"  - {prop.get('diff_summary', '')[:200]}")
    parts.append("\n*این PR توسط بازرس ویژه (Inspector) و اسکن موردی AI ساخته شده است.*")
    return "\n".join(parts)
