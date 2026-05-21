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
import uuid
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

    🆕 (v2 audit B3) — cap به ۲۰ scan_complete پیام آخر برای avoid کندی
    در session هایی با چندین scan در طول زمان.
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
            .order_by(InspectorMessage.id.desc())
            .limit(20)
            .all()
        )
        # reverse برای حفظ ترتیب chronological
        msgs = list(reversed(msgs))
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


_OVERSIZED_THRESHOLD = 30000  # بایت — بالاتر از این، whole-file خطرناک است


# 🆕 (v3 model fix) — resolve model_id با fallback به مدل‌های موجود
# جای استفاده از hardcoded "claude-sonnet-4-6" که ممکن است در registry
# کاربر نباشد.
def _resolve_model_with_fallback(preferred: Optional[str]) -> Optional[str]:
    """مدل قابل استفاده پیدا می‌کند.

    1. اگر preferred داده شده و در registry است، آن را برمی‌گرداند
    2. وگرنه یک fallback از registry پیدا می‌کند (اول Claude Sonnet ها،
       سپس GPT, سپس هر مدل دیگری)
    3. اگر هیچ‌کدام نیست، None
    """
    try:
        from ..core.models_registry import MODEL_REGISTRY, get_model
    except Exception:
        return preferred  # نمی‌توانیم validate کنیم، خود preferred را برگردان

    # اگر preferred داده شده، آن را چک کن
    if preferred:
        if get_model(preferred):
            return preferred
        # شاید match جزئی (مثل claude-sonnet در registry با key claude-sonnet-3.5)
        pref_low = preferred.lower()
        for mid in MODEL_REGISTRY.keys():
            if pref_low in mid.lower() or mid.lower() in pref_low:
                logger.info(f"model fallback: {preferred} → {mid}")
                return mid

    # هیچ preferred یا match نشد — یک مدل sensible default پیدا کن
    # اولویت: claude-sonnet > claude-opus > gpt-4 > هرچیزی
    priorities = ["claude-sonnet", "claude-opus", "claude-haiku", "gpt-4o", "gpt-4", "gpt"]
    for prio in priorities:
        for mid in MODEL_REGISTRY.keys():
            if prio in mid.lower():
                logger.info(f"model fallback: no preferred, using {mid}")
                return mid

    # هر مدلی موجود است
    if MODEL_REGISTRY:
        first = next(iter(MODEL_REGISTRY.keys()))
        logger.info(f"model fallback: last resort, using {first}")
        return first

    return None


# 🆕 (v2 M5) — fetch dep files (package.json, requirements.txt, …)
async def _fetch_dep_files(http_session, repo: str, headers: Dict[str, str], branch: str) -> Dict[str, str]:
    """فایل‌های Dependency manifest را برای dep-awareness در prompt fetch می‌کند."""
    dep_paths = [
        "package.json", "requirements.txt", "pyproject.toml", "Pipfile",
        "frontend/package.json", "backend/requirements.txt",
        "go.mod", "Cargo.toml",
    ]
    result: Dict[str, str] = {}
    try:
        from .oversight_deep_scan_service import _fetch_file_content
    except Exception:
        return result
    for p in dep_paths:
        try:
            c = await _fetch_file_content(http_session, repo, p, headers, branch, 12000)
            if c:
                result[p] = c
        except Exception:
            continue
    return result


# ─── prompt builder for code generation ───────────────────────────
def _build_codegen_prompt(
    proposal: Dict[str, Any],
    current_files: Dict[str, str],
) -> Tuple[str, List[str]]:
    """prompt تولید کد + لیست فایل‌های oversized (نیازمند patch mode).

    Returns: (prompt_str, oversized_file_paths)
    """
    strong = proposal.get("strong_prompt") or ""
    target_files = proposal.get("target_files") or []
    if not target_files:
        target_files = [
            tl.get("path") for tl in (proposal.get("target_locations") or [])
            if isinstance(tl, dict) and tl.get("path")
        ]

    files_blob_parts: List[str] = []
    oversized_files: List[str] = []
    for path in target_files:
        content = current_files.get(path, "")
        if not content:
            files_blob_parts.append(
                f"=== فایل {path} ===\n"
                f"(فایل وجود ندارد یا قابل خواندن نیست — اگر لازم بود فایل جدید بساز)"
            )
            continue
        # 🆕 (v2 M3) — فایل بزرگ: whole-file rewrite خطرناک است
        if len(content) > _OVERSIZED_THRESHOLD:
            oversized_files.append(path)
            files_blob_parts.append(
                f"=== فایل {path} (⚠️ {len(content):,} بایت — OVERSIZED) ===\n"
                f"این فایل برای whole-file rewrite بزرگ‌تر از حد امن است.\n"
                f"فقط `change_kind: \"patch\"` با ساختار "
                f"`sections: [{{find: \"متن دقیق فعلی\", replace: \"متن جایگزین\"}}]` "
                f"در changes برگردان. هرگز whole-file content برای این فایل نده.\n\n"
                f"شروع فایل (۵۰۰۰ بایت اول):\n```\n{content[:5000]}\n```\n\n"
                f"پایان فایل (۵۰۰۰ بایت آخر):\n```\n{content[-5000:]}\n```"
            )
        else:
            files_blob_parts.append(f"=== فایل فعلی: {path} ===\n```\n{content}\n```")

    files_blob = "\n\n".join(files_blob_parts) if files_blob_parts else "(فایلی برای ویرایش مشخص نیست)"

    # 🆕 (v2 M5) — dep file awareness
    dep_blob = ""
    known_dep_names = ("package.json", "requirements.txt", "pyproject.toml",
                        "Pipfile", "go.mod", "Cargo.toml")
    known_deps = {k: v for k, v in current_files.items()
                  if k.split("/")[-1] in known_dep_names}
    if known_deps:
        dep_blob = "\n\n".join(
            f"=== {p} (dependency manifest) ===\n```\n{c[:5000]}\n```"
            for p, c in known_deps.items()
        )

    oversized_hint = ""
    if oversized_files:
        oversized_hint = (
            "\n🚨 **بسیار مهم — فایل‌های OVERSIZED**: برای فایل‌های زیر "
            f"({', '.join(oversized_files)}) فقط `change_kind: \"patch\"` "
            "با ساختار `sections: [{find, replace}]` بفرست. "
            "`find` باید رشته‌ای **یکتا** در فایل باشد (نه چندبار تکرار)."
        )

    return (f"""تو یک Senior Software Engineer هستی. وظیفه‌ات اعمال **دقیق** تغییرات روی فایل‌های زیر بر اساس درخواست است.

# 📋 دستورالعمل کامل (strong prompt)
{strong}

# 📁 محتوای فعلی فایل‌های target
{files_blob}

# 📦 فایل‌های Dependency فعلی
{dep_blob or '(یافت نشد)'}

# 🎯 خروجی موردانتظار — فقط JSON خالص (بدون متن اضافی، بدون ```)
{{
  "changes": [
    {{
      "path": "مسیر دقیق فایل از ریشهٔ ریپو",
      "change_kind": "modify | create | delete | patch",
      "content": "محتوای کامل فایل (فقط اگر change_kind در ['modify','create'])",
      "sections": [{{"find": "متن دقیق فعلی", "replace": "متن جایگزین"}}],  // فقط اگر change_kind=='patch'
      "summary": "خلاصهٔ ۱-۲ خطی تغییری که در این فایل اعمال شد"
    }}
  ],
  "overall_summary": "خلاصهٔ کلی تمام تغییرات — برای commit message",
  "risks": "ریسک‌ها/هشدارهایی که توسعه‌دهنده باید بداند",
  "tests_or_manual_steps": ["گام‌های تست/اعتبارسنجی پس از merge"]
}}

🚨 **بسیار مهم — Whole-file vs Patch**:
- برای فایل‌های معمولی (< 30KB): `change_kind: "modify"` + `content` کامل
- برای فایل‌های OVERSIZED بالا: `change_kind: "patch"` + `sections` با find/replace.
  `find` رشته‌ای یکتا، بدون whitespace ابتدا/انتها
- اگر فایلی نباید تغییر کند، در `changes` نگذار
- مسیرها دقیقاً مثل فایل‌های فعلی بالا
- فقط JSON برگردان، هیچ متن اضافه‌ای قبل/بعد JSON نباشد

🚨 **Dependency Awareness — حیاتی**:
- اگر `import X` یا `from X import` جدیدی اضافه می‌کنی، بررسی کن X در
  dependency manifest هست
- اگر نه: یک change برای dep manifest هم در changes بگذار (با version
  مناسب)
- import داخلی (از فایل دیگر در همین repo) نیاز به dep update ندارد
- اضافه کردن import بدون update dep file = deploy failure
{oversized_hint}
""",
        oversized_files)


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

    # (audit fix M3) — proposal بدون target_files نباید به AI پاس شود؛
    # AI ممکن است فایل‌های جعلی بسازد.
    _tf = (proposal.get("target_files") or []) + [
        t.get("path") for t in (proposal.get("target_locations") or [])
        if isinstance(t, dict) and t.get("path")
    ]
    if not [p for p in _tf if p]:
        _update_proposal_in_message(message_id, proposal_id, {
            "execution_status": "failed",
            "execution_error": "proposal بدون target_files قابل اجرا نیست — مدل scan نتوانست فایل هدف تشخیص دهد",
            "executed_at": _now_iso(),
        })
        return {
            "success": False,
            "error": "این پیشنهاد فایل هدف ندارد. لطفاً scan موردی را با مسیر مشخص‌تر در پیام تکرار کنید.",
            "code": "no_target_files",
        }

    # repo info
    repo = _resolve_repo_for_session(session_id)
    if not repo:
        return {"success": False, "error": "repo شناسایی نشد"}

    # fetch فایل‌های target
    current_files: Dict[str, str] = {}
    try:
        import aiohttp
        from .oversight_deep_scan_service import _fetch_file_content, _gh_get_json, GITHUB_API
        from .oversight_service import get_github_token
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
                    # 🆕 (v2 M3) — حداکثر ۱۲۰KB تا مدل بتواند کل فایل را
                    # ببیند حتی اگر oversized باشد (در prompt هنوز با
                    # 5KB+5KB نشانه‌گذاری می‌شود ولی patch detection
                    # روی محتوای کامل کار می‌کند).
                    content = await _fetch_file_content(http_session, repo, path, headers, branch, 120000)
                    if content:
                        current_files[path] = content
                except Exception as fe:
                    logger.debug(f"fetch {path} failed: {fe}")
                    continue
            # 🆕 (v2 M5) — fetch dep files
            try:
                dep_files = await _fetch_dep_files(http_session, repo, headers, branch)
                current_files.update(dep_files)
            except Exception as dfe:
                logger.debug(f"fetch dep files failed: {dfe}")
    except Exception as e:
        logger.warning(f"run_proposal: fetching files failed: {e}")
        # ادامه بده با current_files خالی — مدل ممکن است فایل از اول بسازد

    # build prompt
    prompt, _oversized_files = _build_codegen_prompt(proposal, current_files)

    # generate code
    try:
        from .ai_manager import get_ai_manager
        from .ai_base import Message
        ai_manager = get_ai_manager()
        # 🆕 (v3 model fix) — resolve مدل با fallback
        resolved_model = _resolve_model_with_fallback(model_id)
        if not resolved_model:
            raise RuntimeError(
                "هیچ مدل قابل استفاده‌ای پیدا نشد. لطفاً در inspector settings "
                "یک مدل انتخاب کنید یا API keys را در settings تنظیم کنید."
            )
        response = await ai_manager.generate(
            model_id=resolved_model,
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

    # success — process changes
    changes = result_json.get("changes") or []
    # accept patch | modify | create | delete
    valid_changes: List[Dict[str, Any]] = []
    # 🆕 (v2 audit A2 fix) — empty content protection
    # قبلاً `if "content" in c` پاس می‌داد content=None یا ""، نتیجه commit
    # یک فایل صفر بایتی روی GitHub. الان صریح content معنادار می‌خواهیم
    # (مگر برای delete یا patch).
    empty_content_rejected: List[str] = []
    for c in changes:
        if not isinstance(c, dict) or not c.get("path"):
            continue
        kind = c.get("change_kind", "modify")
        if kind == "patch":
            if isinstance(c.get("sections"), list) and c.get("sections"):
                valid_changes.append(c)
        elif kind == "delete":
            valid_changes.append(c)
        elif kind in ("modify", "create"):
            content_val = c.get("content")
            # رد content خالی/None که فایل را به zero-byte truncate می‌کند
            if not isinstance(content_val, str) or not content_val.strip():
                empty_content_rejected.append(c.get("path", ""))
                continue
            valid_changes.append(c)
    diff_summary = result_json.get("overall_summary", "")[:1000]

    if empty_content_rejected:
        logger.warning(
            f"run_proposal: rejected {len(empty_content_rejected)} change(s) with empty content: "
            f"{empty_content_rejected[:5]}"
        )

    # 🆕 (v2 M3) — رد whole-file برای oversized files
    _oversized_set = set(_oversized_files or [])
    if _oversized_set:
        new_valid: List[Dict[str, Any]] = []
        rejected_oversized: List[str] = []
        for ch in valid_changes:
            if ch.get("path") in _oversized_set and ch.get("change_kind") != "patch":
                rejected_oversized.append(ch.get("path", ""))
                continue
            new_valid.append(ch)
        if rejected_oversized:
            logger.warning(
                f"run_proposal: rejected whole-file for oversized: {rejected_oversized}"
            )
        valid_changes = new_valid

    # 🆕 (v2 M4) — syntax validation pre-stage
    syntax_errors: List[Dict[str, str]] = []
    for ch in valid_changes:
        if ch.get("change_kind") in ("delete", "patch"):
            continue  # patch با apply-all چک می‌شود؛ delete content ندارد
        path = ch.get("path", "")
        content = ch.get("content", "")
        if not content:
            continue
        low = path.lower()
        try:
            if low.endswith(".py"):
                import ast
                ast.parse(content)
            elif low.endswith(".json"):
                json.loads(content)
            elif low.endswith((".yaml", ".yml")):
                try:
                    import yaml
                    yaml.safe_load(content)
                except ImportError:
                    pass
            elif low.endswith((".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")):
                # 🆕 (v2 audit) — balance check برای TS/JS با false-positive
                # بالا روی regex/template literal/string ها. به همین دلیل
                # فقط در صورت اختلاف **شدید** (> 3) trigger می‌شود تا
                # gross errors گرفته شود ولی فایل‌های سالم با regex های
                # نامتوازن داخل string ها blocked نشوند.
                # برای دقت واقعی، باید parser واقعی (node --check / tsc)
                # استفاده شود که در runtime container دسترسی نداریم.
                _diff_brace = abs(content.count("{") - content.count("}"))
                _diff_paren = abs(content.count("(") - content.count(")"))
                _diff_bracket = abs(content.count("[") - content.count("]"))
                if _diff_brace > 3:
                    raise SyntaxError(f"unbalanced braces (diff={_diff_brace}) in {path}")
                if _diff_paren > 3:
                    raise SyntaxError(f"unbalanced parens (diff={_diff_paren}) in {path}")
                if _diff_bracket > 3:
                    raise SyntaxError(f"unbalanced brackets (diff={_diff_bracket}) in {path}")
        except SyntaxError as se:
            syntax_errors.append({"path": path, "error": str(se)[:300]})
        except (json.JSONDecodeError, ValueError) as ve:
            syntax_errors.append({"path": path, "error": str(ve)[:300]})
        except Exception as ve:
            # هر خطای دیگر را در validation سختگیر نگیر
            logger.debug(f"syntax check unexpected error for {path}: {ve}")

    if syntax_errors:
        _update_proposal_in_message(message_id, proposal_id, {
            "execution_status": "failed_syntax",
            "execution_error": "syntax تولید شده توسط مدل نامعتبر است",
            "syntax_errors": syntax_errors,
            "executed_at": _now_iso(),
            "raw_response": (response.content or "")[:2000],
        })
        log_scan_message(
            session_id=session_id,
            role="assistant",
            content=(
                f"❌ پیشنهاد «{proposal.get('title', '')[:80]}» syntax errors دارد:\n\n"
                + "\n".join(f"- `{e['path']}`: {e['error']}" for e in syntax_errors)
                + "\n\nلطفاً دکمهٔ «↻ بازاجرا» را بزنید یا با scan جدید تکرار کنید."
            ),
            action_type="proposal_failed",
            model_id=response.model_id if 'response' in locals() else model_id,
            extra_data={
                "kind": "proposal_executed",
                "proposal_id": proposal_id,
                "status": "failed_syntax",
                "syntax_errors": syntax_errors,
            },
        )
        return {
            "success": False,
            "error": "syntax_validation_failed",
            "syntax_errors": syntax_errors,
            "code": "failed_syntax",
        }

    # 🆕 (v2 audit A2 fix) — اگر بعد از همه فیلترها (oversized rejection +
    # syntax check + empty content rejection) هیچ change معتبری نماند،
    # proposal را failed علامت بزن. در غیر این صورت applied_locally با
    # لیست خالی staged → apply-all چیزی برای commit ندارد ولی proposal
    # موفق به نظر می‌رسد.
    if not valid_changes:
        err = "هیچ change معتبری از مدل دریافت نشد"
        if empty_content_rejected:
            err += f" (همه فایل‌ها با content خالی رد شدند: {empty_content_rejected[:3]})"
        _update_proposal_in_message(message_id, proposal_id, {
            "execution_status": "failed",
            "execution_error": err,
            "executed_at": _now_iso(),
            "raw_response": (response.content or "")[:2000],
        })
        log_scan_message(
            session_id=session_id,
            role="assistant",
            content=(
                f"❌ پیشنهاد «{proposal.get('title', '')[:80]}» — مدل هیچ change معتبری "
                f"تولید نکرد:\n{err}\n\nلطفاً «↻ بازاجرا» را بزنید."
            ),
            action_type="proposal_failed",
            model_id=response.model_id if 'response' in locals() else model_id,
            extra_data={
                "kind": "proposal_executed",
                "proposal_id": proposal_id,
                "status": "failed",
                "error": err,
            },
        )
        return {"success": False, "error": err, "code": "no_valid_changes"}

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
    branch_strategy: str = "new_pr",
    model_id: Optional[str] = None,
    force_apply: bool = False,
    selected_proposal_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """همهٔ proposalهای staged session را با یک PR/commit به GitHub می‌فرستد.

    🆕 (v3)
    - `force_apply=True`: consistency check blocking issues را به warnings
      تبدیل می‌کند تا apply انجام شود (با تأیید کاربر)
    - `selected_proposal_ids`: اگر داده شد، فقط همان proposals apply
      می‌شوند، نه همه staged
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

    # 🆕 (v2 M3) — patch resolution: تبدیل change_kind=patch به محتوای کامل
    try:
        from .oversight_service import get_github_token as _ggt
        _token_for_patch = _ggt()
    except Exception:
        _token_for_patch = ""

    # 🆕 (v2 audit) — اگر patch داریم ولی token خالی است، fast-fail با
    # پیام واضح. در غیر این صورت `_fetch_file_content` با headers خالی
    # روی repo خصوصی None برمی‌گرداند و کاربر پیام مبهم patch_fetch_failed
    # می‌گیرد.
    _has_patches = any(ch.get("change_kind") == "patch" for ch in files_map.values())
    if _has_patches and not _token_for_patch:
        log_scan_message(
            session_id=session_id,
            role="assistant",
            content=(
                "⛔ **GitHub token موجود نیست** — برای patch resolution نیاز است.\n\n"
                "برخی از proposalها در حالت patch (برای فایل‌های بزرگ) ساخته شدند که "
                "نیاز به fetch محتوای فعلی از GitHub دارند. لطفاً GITHUB_TOKEN را در "
                "settings تنظیم کنید."
            ),
            action_type="apply_all_failed",
            extra_data={
                "kind": "apply_all_result",
                "status": "missing_github_token",
                "code": "missing_github_token",
            },
        )
        return {"success": False, "code": "missing_github_token", "error": "GitHub token موجود نیست"}

    _patch_resolution = await _resolve_patches_in_files_map(
        files_map=files_map,
        repo=repo,
        token=_token_for_patch,
    )
    if not _patch_resolution.get("success"):
        log_scan_message(
            session_id=session_id,
            role="assistant",
            content=(
                f"❌ خطا در patch resolution:\n```\n"
                f"{_patch_resolution.get('error', '')}\n```\n\n"
                f"دلیل احتمالی: متن `find` در patch چندبار match می‌کند یا "
                f"یافت نمی‌شود. لطفاً proposal مربوطه را با «↻ بازاجرا» تکرار کنید."
            ),
            action_type="apply_all_failed",
            extra_data={
                "kind": "apply_all_result",
                "status": "patch_resolution_failed",
                "error": _patch_resolution.get("error"),
                "code": _patch_resolution.get("code"),
            },
        )
        return _patch_resolution

    # 🆕 (v2 M6) — Cross-proposal consistency check قبل از commit
    consistency = await _validate_cross_proposal_consistency(
        staged_files=files_map,
        proposals=[s[0] for s in staged],
        model_id=model_id,
    )
    # 🆕 (v2 audit D1 fix) — صریح هم به blocking_issues و هم is_safe_to_apply نگاه کن
    _has_blockers = bool(consistency.get("blocking_issues"))
    _safe_flag = consistency.get("is_safe_to_apply")
    # 🆕 (v3) — اگر force_apply=True، blocking_issues را به warnings
    # تبدیل کن تا apply ادامه یابد
    if force_apply and (_has_blockers or _safe_flag is False):
        _forced_warnings = (consistency.get("warnings") or []) + (consistency.get("blocking_issues") or [])
        consistency = {
            **consistency,
            "blocking_issues": [],
            "warnings": _forced_warnings,
            "force_apply_override": True,
        }
        _has_blockers = False
        _safe_flag = True
        logger.warning(f"apply_all: force_apply override — {len(_forced_warnings)} consistency issue ignored")
    if _has_blockers or _safe_flag is False:
        # 🆕 (v2 audit D3 fix) — affected_files ممکن است string باشد
        def _normalize_files(v: Any) -> List[str]:
            if isinstance(v, list):
                return [str(x) for x in v]
            if isinstance(v, str):
                return [v]
            return []
        # اگر فقط is_safe_to_apply=false بود و blocking_issues خالی،
        # یک placeholder issue بساز
        blocking = consistency.get("blocking_issues") or []
        if not blocking and _safe_flag is False:
            blocking = [{
                "severity": "error",
                "kind": "unsafe_to_apply",
                "description": consistency.get("summary") or "AI reviewer گزارش کرد changes ایمن نیستند",
                "affected_files": [],
            }]
        issues_text = "\n".join(
            f"- ❌ **{iss.get('severity', 'error').upper()}** "
            f"({iss.get('kind', '')}): {iss.get('description', '')[:300]}\n"
            f"  فایل‌ها: {', '.join(_normalize_files(iss.get('affected_files')))}"
            for iss in blocking
        )
        log_scan_message(
            session_id=session_id,
            role="assistant",
            content=(
                f"⛔ **اعمال تغییرات block شد — تغییرات روی هم سازگار نیستند**\n\n"
                f"{issues_text}\n\n"
                f"### ⚙️ گزینه‌ها:\n"
                f"1. **بهتر**: یک پیام جدید با درخواست کوچک‌تر بفرستید (مثلاً «فقط فایل runtime.txt بساز»)\n"
                f"2. **پیشنهاد‌های مرتبط را بازاجرا**: روی «↻ بازاجرا» در proposal خاص کلیک کنید\n"
                f"3. **Override**: اگر می‌دانید مشکلی نیست، با گزینهٔ «⚠️ اعمال علی‌رغم warnings» (force_apply) "
                f"   دوباره تلاش کنید — این warnings را نادیده می‌گیرد و apply می‌کند"
            ),
            action_type="apply_all_blocked",
            extra_data={
                "kind": "apply_all_result",
                "status": "blocked_consistency",
                "blocking_issues": blocking,
                "warnings": consistency.get("warnings", []),
            },
        )
        return {
            "success": False,
            "code": "consistency_check_failed",
            "blocking_issues": blocking,
        }
    consistency_warnings = consistency.get("warnings", [])

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
        from .oversight_service import get_github_token
        token = get_github_token()
        pr_service = get_github_pr_service()
        # (audit fix M1) — uuid suffix برای جلوگیری از collision در apply-all
        # های هم‌زمان روی همان session در همان ثانیه.
        _branch_suffix = uuid.uuid4().hex[:6]
        branch_name = f"inspector-scan/{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{session_id}-{_branch_suffix}"
        pr_result = await pr_service.create_pr_with_changes(
            github_path=repo,
            branch_name=branch_name,
            title=commit_message[:100],
            description=_build_pr_description(staged, commit_message, warnings=consistency_warnings),
            files=files_list,
            token=token,
        )
        if not pr_result.get("success"):
            err = pr_result.get("error") or "خطای ناشناخته از GitHub"
            code = pr_result.get("code", "github_error")
            # 🆕 (v2 audit E2) — partial commit awareness
            partial_committed = pr_result.get("files_committed") or pr_result.get("files_committed_before_failure")
            extra_msg = ""
            if code == "branch_already_exists":
                extra_msg = (
                    "\n\n⚠️ Branch از قبل وجود دارد. این معمولاً نشانهٔ apply ناقص قبلی است. "
                    "می‌توانید روی GitHub branch قدیمی را پاک کنید و دوباره apply-all را بزنید."
                )
            elif code == "file_commit_failed":
                failed_file = pr_result.get("failed_file", "?")
                extra_msg = (
                    f"\n\n⚠️ commit در فایل `{failed_file}` شکست خورد. "
                    f"branch ناقص پاک شد ({'بله' if pr_result.get('branch_cleanup_attempted') else 'تلاش نشد'})."
                )
                if partial_committed:
                    extra_msg += f"\nفایل‌های قبل از شکست committed شدند: {', '.join(partial_committed[:5])}"
            elif code == "pr_creation_failed":
                extra_msg = (
                    "\n\n⚠️ فایل‌ها commit شدند اما PR ساخته نشد. "
                    f"می‌توانید PR را روی branch `{pr_result.get('branch', branch_name)}` "
                    "به‌صورت دستی روی GitHub بسازید."
                )
            log_scan_message(
                session_id=session_id,
                role="assistant",
                content=f"❌ خطا در اعمال تغییرات به GitHub:\n```\n{err}\n```{extra_msg}",
                action_type="apply_all_failed",
                extra_data={
                    "kind": "apply_all_result",
                    "status": "failed",
                    "error": err[:500],
                    "code": code,
                    "partial_committed": partial_committed,
                    "branch": pr_result.get("branch", branch_name),
                },
            )
            # برای pr_creation_failed، proposalها را نگه‌داریم applied_locally
            # تا کاربر بتواند PR را دستی باز کند یا apply-all مجدد بزند با
            # branch جدید (که فایل‌های قبلی override خواهند شد)
            return {"success": False, "error": err, "code": code, "partial_committed": partial_committed}
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
    warnings: Optional[List[Dict[str, Any]]] = None,
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

    # 🆕 (v2 M6) — warnings از consistency check
    if warnings:
        parts.append("\n### ⚠️ Warnings از consistency check")
        for w in warnings[:10]:
            kind = w.get("kind", "")
            desc = (w.get("description") or "")[:300]
            files = w.get("affected_files") or []
            parts.append(f"- **{kind}**: {desc}")
            if files:
                parts.append(f"  فایل‌ها: {', '.join(files[:5])}")

    # 🆕 (v2 N4) — multi-proposal path collisions
    path_to_titles: Dict[str, List[str]] = {}
    for prop, ch, _mid in staged:
        p = ch.get("path")
        if p:
            t = prop.get("title", "")
            if t and t not in path_to_titles.get(p, []):
                path_to_titles.setdefault(p, []).append(t)
    collisions = {p: titles for p, titles in path_to_titles.items() if len(titles) > 1}
    if collisions:
        parts.append("\n### ⚠️ Multi-proposal collisions (last-wins)")
        for p, titles in list(collisions.items())[:5]:
            parts.append(f"- `{p}` توسط چند proposal تغییر داده شد:")
            for t in titles:
                parts.append(f"  - {t[:120]}")

    parts.append("\n*این PR توسط بازرس ویژه (Inspector) و اسکن موردی AI ساخته شده است.*")
    return "\n".join(parts)


# ─── (v2 M3) Patch resolution ─────────────────────────────────────
async def _resolve_patches_in_files_map(
    *,
    files_map: Dict[str, Dict[str, Any]],
    repo: str,
    token: str,
) -> Dict[str, Any]:
    """change_kind=patch را با fetch محتوای فعلی و find/replace تبدیل به modify.

    Returns: {success: bool, error?: str, code?: str}
    """
    patch_paths = [p for p, ch in files_map.items() if ch.get("change_kind") == "patch"]
    if not patch_paths:
        return {"success": True}

    try:
        import aiohttp
        from .oversight_deep_scan_service import _fetch_file_content, _gh_get_json, GITHUB_API
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"} if token else {}
        async with aiohttp.ClientSession() as http_session:
            info = await _gh_get_json(http_session, f"{GITHUB_API}/repos/{repo}", headers)
            branch = (info or {}).get("default_branch") or "main"
            for path in patch_paths:
                ch = files_map[path]
                sections = ch.get("sections") or []
                if not sections:
                    return {
                        "success": False,
                        "error": f"patch برای {path} sections خالی دارد",
                        "code": "patch_no_sections",
                    }
                current = await _fetch_file_content(http_session, repo, path, headers, branch, 200000)
                if current is None:
                    return {
                        "success": False,
                        "error": f"محتوای فعلی {path} برای patch قابل دریافت نیست",
                        "code": "patch_fetch_failed",
                    }
                # 🆕 (v2 audit C1 fix) — CRLF normalization
                # اگر فایل CRLF دارد ولی AI با LF تولید کرده (یا برعکس)،
                # `find_str not in current` همیشه True می‌شد. هر دو طرف را
                # به LF normalize می‌کنیم. در پایان line-ending فایل اصلی
                # حفظ می‌شود اگر CRLF بود.
                _had_crlf = "\r\n" in current
                new_content = current.replace("\r\n", "\n") if _had_crlf else current
                for sec in sections:
                    if not isinstance(sec, dict):
                        continue
                    find_str = (sec.get("find") or "").replace("\r\n", "\n")
                    repl_str = (sec.get("replace") or "").replace("\r\n", "\n")
                    if not find_str:
                        return {
                            "success": False,
                            "error": f"patch برای {path}: find خالی است",
                            "code": "patch_empty_find",
                        }
                    if find_str not in new_content:
                        return {
                            "success": False,
                            "error": (
                                f"patch برای {path}: '{find_str[:80]}...' در فایل پیدا نشد. "
                                f"بازاجرا کنید یا scan را با مسیر دقیق‌تر تکرار کنید."
                            ),
                            "code": "patch_find_failed",
                        }
                    if new_content.count(find_str) > 1:
                        return {
                            "success": False,
                            "error": f"patch برای {path}: '{find_str[:80]}...' چندبار match می‌شود (ambiguous)",
                            "code": "patch_ambiguous",
                        }
                    new_content = new_content.replace(find_str, repl_str, 1)
                # بازگرداندن line-ending اگر فایل اصلی CRLF بود
                if _had_crlf:
                    new_content = new_content.replace("\n", "\r\n")
                # تبدیل به modify
                files_map[path] = {
                    **ch,
                    "content": new_content,
                    "change_kind": "modify",
                    "_resolved_from_patch": True,
                }
        return {"success": True}
    except Exception as e:
        logger.exception(f"patch resolution failed: {e}")
        return {"success": False, "error": str(e)[:300], "code": "patch_resolver_error"}


# ─── (v2 M6) Cross-proposal consistency check ──────────────────────
async def _validate_cross_proposal_consistency(
    *,
    staged_files: Dict[str, Dict[str, Any]],
    proposals: List[Dict[str, Any]],
    model_id: Optional[str] = None,
) -> Dict[str, Any]:
    """LLM check برای rename inconsistency, API break, duplicate logic.

    fail-open: اگر AI خراب شد، یا timeout/parse fail → اجازه apply می‌دهد.
    """
    import asyncio as _asyncio
    if len(staged_files) <= 1:
        return {"blocking_issues": [], "warnings": []}

    # 🆕 (v2 audit D2 fix) — اگر تعداد فایل از cap بیشتر است، صریح به LLM
    # بگو تا برای فایل‌های نمایش‌داده‌نشده ادعای ناسازگاری نکند.
    _file_cap = 15
    _total_files = len(staged_files)
    _truncated = _total_files > _file_cap
    _shown_paths: List[str] = []
    changes_blob_parts: List[str] = []
    for path, ch in list(staged_files.items())[:_file_cap]:
        _shown_paths.append(path)
        content = (ch.get("content") or "")[:8000]
        kind = ch.get("change_kind", "modify")
        summary = ch.get("summary", "")
        changes_blob_parts.append(
            f"=== {path} ({kind}) ===\n"
            f"خلاصه: {summary[:200]}\n\n```\n{content}\n```"
        )

    proposal_titles = "\n".join(
        f"- {p.get('title', '')[:120]}" for p in proposals[:10]
    )

    _truncation_note = ""
    if _truncated:
        _hidden = [p for p in staged_files.keys() if p not in _shown_paths][:20]
        _truncation_note = (
            f"\n\n⚠️ **TRUNCATION**: این فقط ۱۵ فایل اول از {_total_files} فایل کل است.\n"
            f"فایل‌های نمایش‌داده‌نشده:\n"
            + "\n".join(f"  - {p}" for p in _hidden)
            + "\n\nبرای فایل‌های نمایش‌داده‌نشده، مشکل ادعا نکن. اگر symbol هایی "
            "ارجاع داده‌شده که در فایل‌های شناخته‌شده تعریف نشده‌اند، احتمالاً در "
            "فایل‌های نمایش‌داده‌نشده هستند — این را در `warnings` بگذار نه `blocking_issues`."
        )

    prompt = (
        "تو یک Senior Code Reviewer هستی. این مجموعه تغییرات قرار است "
        "**با هم** در یک PR commit شوند. بررسی کن آیا روی هم سازگار هستند.\n\n"
        f"# پیشنهاد‌ها\n{proposal_titles}\n\n"
        f"# تغییرات\n{chr(10).join(changes_blob_parts)}{_truncation_note}\n\n"
        "# بررسی کن:\n"
        "1. Rename inconsistency (تابعی rename شده ولی فایل دیگر از نام قدیم استفاده می‌کند)\n"
        "2. API contract break (signature عوض شده ولی caller به‌روز نیست)\n"
        "3. Duplicate logic (دو فایل قابلیت مشابه به دو روش)\n"
        "4. Import mismatch (importی که در مقصد ندیده می‌شود)\n"
        "5. Type/schema mismatch\n"
        "6. Dead code\n\n"
        "# خروجی — فقط JSON خالص\n"
        '{"blocking_issues": [{"severity": "error", "kind": "...", "description": "...", "affected_files": ["..."]}],\n'
        ' "warnings": [{"severity": "warning", "kind": "...", "description": "...", "affected_files": ["..."]}],\n'
        ' "is_safe_to_apply": true,\n'
        ' "summary": "..."}\n'
        "اگر مشکلی نیست، آرایه‌ها خالی + is_safe_to_apply=true."
    )

    try:
        from .ai_manager import get_ai_manager
        from .ai_base import Message
        ai_manager = get_ai_manager()
        # 🆕 (v3 model fix) — اگر model_id داده نشد یا در registry نیست،
        # یک fallback پیدا کن. claude-sonnet-4-6 ممکن است در deployment
        # کاربر نباشد. _resolve_model_with_fallback از registry می‌خواند.
        resolved_model = _resolve_model_with_fallback(model_id)
        if not resolved_model:
            logger.warning("consistency check: no usable model found; fail-open")
            return {"blocking_issues": [], "warnings": [], "no_model": True}
        response = await _asyncio.wait_for(
            ai_manager.generate(
                model_id=resolved_model,
                messages=[Message(role="user", content=prompt)],
                max_tokens=4000,
                temperature=0.1,
            ),
            timeout=90.0,
        )
        result = _extract_json_from_ai(response.content or "")
        if not result:
            logger.warning("consistency check: AI response not parseable; fail-open")
            return {"blocking_issues": [], "warnings": [], "parse_failed": True}
        return {
            "blocking_issues": result.get("blocking_issues") or [],
            "warnings": result.get("warnings") or [],
            "is_safe_to_apply": result.get("is_safe_to_apply", True),
            "summary": result.get("summary", ""),
        }
    except _asyncio.TimeoutError:
        logger.warning("consistency check timeout; fail-open")
        return {"blocking_issues": [], "warnings": [], "timeout": True}
    except Exception as e:
        logger.warning(f"consistency check failed: {e}; fail-open")
        return {"blocking_issues": [], "warnings": [], "check_error": str(e)[:200]}
