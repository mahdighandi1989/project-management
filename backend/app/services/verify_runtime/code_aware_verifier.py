"""Phase 4 — Code-aware Verifier (per-AC commit analysis).

برای هر AC، در یک batch AI call، بررسی می‌شود که آیا commit های اخیر
این AC را پیاده کرده‌اند یا نه. این مکمل AI verifier موجود است که در
سطح task کار می‌کند.

API اصلی:
    analyze_acs_with_commit_diffs(task, acs, repo_full_name, token,
                                  verify_model_id) -> List[Dict]

خروجی: یک list به طول acs، هر item:
{
  "ac_index": int,
  "ac_text": str,
  "code_verdict": "implemented" | "partial" | "not_found" | "unclear",
  "matching_commits": List[str],  # SHA های ۷ کاراکتری
  "key_changes": List[str],       # ۲-۵ تغییر کلیدی به‌صورت متن
  "reason": str,                  # یک جمله توضیح
}

این تابع per-AC AI call نمی‌زند — یک AI call batch برای حداکثر ۱۰ AC.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# محدودیت‌ها
_MAX_ACS_PER_BATCH = 10
_MAX_COMMITS_TO_FETCH = 60  # 🆕 از 20 به 60 — feature های قدیمی‌تر هم در بازه می‌آیند
_MAX_FILES_PER_COMMIT = 8
_MAX_PATCH_CHARS = 1200  # هر patch trim شود تا context AI نشکند
_AI_TIMEOUT_S = 45  # 🆕 با 60 commit، AI زمان بیشتری می‌خواهد
_REPO_TREE_CACHE_TTL = 300  # ۵ دقیقه


async def analyze_acs_with_commit_diffs(
    task: Any,
    acs: List[Any],
    repo_full_name: str,
    token: str,
    verify_model_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """تحلیل per-AC با commit diffs (batch AI call).

    شکست‌خوردگی مجاز:
    - GitHub API fail → همه‌ی نتایج با code_verdict="unclear"
    - AI fail → همه با code_verdict="unclear"
    - acs خالی → []
    """
    if not acs:
        return []

    # commits اخیر را با diff fetch کن
    commits_with_diff = await _fetch_recent_commits_with_diff(
        repo_full_name, token, limit=_MAX_COMMITS_TO_FETCH,
    )
    if not commits_with_diff:
        return [
            _build_unclear_result(i, ac, reason="no recent commits found")
            for i, ac in enumerate(acs[:_MAX_ACS_PER_BATCH])
        ]

    # AC ها را به متن خام تبدیل کن
    ac_texts: List[str] = []
    for ac in acs[:_MAX_ACS_PER_BATCH]:
        if isinstance(ac, dict):
            ac_texts.append(str(ac.get("text") or "").strip())
        else:
            ac_texts.append(str(ac).strip())
    ac_texts = [t for t in ac_texts if t]
    if not ac_texts:
        return []

    # AI call batch
    try:
        results = await _ai_analyze_batch(
            ac_texts=ac_texts,
            commits=commits_with_diff,
            target_files=list(task.target_files or []),
            verify_model_id=verify_model_id,
        )
    except Exception as e:
        logger.warning(f"code_aware_verifier AI batch failed: {e}")
        return [
            _build_unclear_result(i, ac, reason=f"AI batch failed: {str(e)[:100]}")
            for i, ac in enumerate(acs[:_MAX_ACS_PER_BATCH])
        ]

    # نتایج را با input AC ها sync کن
    final: List[Dict[str, Any]] = []
    for i, ac in enumerate(acs[:_MAX_ACS_PER_BATCH]):
        ac_text = ac_texts[i] if i < len(ac_texts) else ""
        ai_item = results.get(i, {}) if isinstance(results, dict) else {}
        final.append({
            "ac_index": i,
            "ac_text": ac_text,
            "code_verdict": _norm_verdict(ai_item.get("verdict")),
            "matching_commits": list(ai_item.get("matching_commits") or [])[:5],
            "key_changes": list(ai_item.get("key_changes") or [])[:5],
            "reason": str(ai_item.get("reason") or "")[:400],
        })
    return final


async def _fetch_recent_commits_with_diff(
    repo_full_name: str, token: str, limit: int = 20,
) -> List[Dict[str, Any]]:
    """commits اخیر را به همراه diff فایل‌هایشان fetch کن."""
    import aiohttp
    from ..oversight_service import GITHUB_API

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # 1. لیست commit ها
    list_url = f"{GITHUB_API}/repos/{repo_full_name}/commits?per_page={limit}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(list_url, headers=headers, timeout=30) as r:
                if r.status != 200:
                    logger.debug(f"github commits list failed: {r.status}")
                    return []
                commits_raw = await r.json()
    except Exception as e:
        logger.debug(f"github commits list exception: {e}")
        return []

    if not isinstance(commits_raw, list):
        return []

    # 2. برای هر commit، diff خلاصه‌شده (بدون patch کامل، فقط files با
    # filename + status + patch[:1500])
    out: List[Dict[str, Any]] = []
    for c in commits_raw[:limit]:
        sha = str(c.get("sha") or "")
        if not sha:
            continue
        try:
            detail_url = f"{GITHUB_API}/repos/{repo_full_name}/commits/{sha}"
            async with aiohttp.ClientSession() as session:
                async with session.get(detail_url, headers=headers, timeout=20) as r2:
                    if r2.status != 200:
                        continue
                    detail = await r2.json()
        except Exception:
            continue
        files = detail.get("files") or []
        files_summary: List[Dict[str, str]] = []
        for f in files[:_MAX_FILES_PER_COMMIT]:
            if not isinstance(f, dict):
                continue
            patch = str(f.get("patch") or "")[:_MAX_PATCH_CHARS]
            files_summary.append({
                "filename": str(f.get("filename") or ""),
                "status": str(f.get("status") or ""),
                "additions": int(f.get("additions") or 0),
                "deletions": int(f.get("deletions") or 0),
                "patch": patch,
            })
        out.append({
            "sha": sha[:7],
            "message": (detail.get("commit", {}).get("message") or "").split("\n")[0][:200],
            "date": (detail.get("commit", {}).get("author") or {}).get("date", ""),
            "files": files_summary,
        })
        # یک‌کم تنفس تا rate-limit نخوریم
        await asyncio.sleep(0.05)
    return out


async def _ai_analyze_batch(
    ac_texts: List[str],
    commits: List[Dict[str, Any]],
    target_files: List[str],
    verify_model_id: Optional[str],
) -> Dict[int, Dict[str, Any]]:
    """یک AI call batch با همه‌ی AC ها + همه‌ی commit ها."""
    try:
        from ..ai_manager import get_ai_manager
        from ..ai_base import Message
    except Exception as e:
        logger.debug(f"code_aware_verifier: ai_manager import failed: {e}")
        return {}

    # اگر verify_model_id ندادی، از registry بگیر
    if not verify_model_id:
        try:
            from ...core.models_registry import DEFAULT_EXTRACTION_MODEL_ID
            verify_model_id = DEFAULT_EXTRACTION_MODEL_ID
        except Exception:
            pass
    if not verify_model_id:
        return {}

    # متن AC ها — همراه index
    ac_block = "\n".join(
        f"[AC #{i}] {t}" for i, t in enumerate(ac_texts)
    )

    # متن commit ها — sha + message + files با patch
    commits_block_parts: List[str] = []
    for c in commits:
        files_lines = []
        for f in c.get("files", []):
            files_lines.append(
                f"  📄 {f.get('filename', '')} "
                f"({f.get('status', '')}, +{f.get('additions', 0)}/-{f.get('deletions', 0)})"
            )
            if f.get("patch"):
                files_lines.append(f"    ```\n{f['patch'][:1200]}\n    ```")
        files_block = "\n".join(files_lines) if files_lines else "  (no files)"
        commits_block_parts.append(
            f"### commit {c.get('sha', '')}: {c.get('message', '')}\n"
            f"date: {c.get('date', '')}\n"
            f"{files_block}"
        )
    commits_block = "\n\n".join(commits_block_parts)

    target_files_text = ", ".join(target_files[:15]) or "(none)"

    prompt = (
        "تو یک Code Reviewer هستی. وظیفه‌ات بررسی این است که آیا AC های زیر\n"
        "در repo پیاده شده‌اند یا نه. تشخیص خود را با شواهد صریح ثابت کن.\n\n"
        f"📁 فایل‌های هدف تسک (target_files از task metadata — این‌ها\n"
        f"    فایل‌هایی هستند که قبلاً یا در این تسک باید ساخته شوند):\n"
        f"    {target_files_text}\n\n"
        f"📋 AC ها (با index):\n{ac_block}\n\n"
        f"📦 commit های اخیر (تا {len(commits)} commit):\n{commits_block}\n\n"
        "⚠️ راهنمای verdict:\n"
        "- 'implemented': یا diff های اخیر این AC را صریحاً پیاده کرده‌اند،\n"
        "  **یا** فایل/تابع/endpoint مرتبط در target_files ذکر شده (یعنی\n"
        "  قبلاً ساخته شده ولی در ۶۰ commit اخیر تغییر نکرده). در این\n"
        "  حالت matching_commits می‌تواند خالی باشد و در reason ذکر کن\n"
        "  «پیش‌ساخته در target_files».\n"
        "- 'partial': بخشی پیاده شده ولی ناقص (مثلاً مدل ساخته شده ولی\n"
        "  endpoint نه).\n"
        "- 'not_found': نه در diff های اخیر و نه در target_files نشانه‌ای\n"
        "  از این AC نیست — احتمالاً ساخته نشده.\n"
        "- 'unclear': مطمئن نیستی یا اطلاعات کافی نیست.\n\n"
        "🛑 قانون مهم: اگر یک AC به فایلی اشاره می‌کند که در target_files\n"
        "   لیست شده ولی در commit ها diff ندارد، عموماً 'implemented'\n"
        "   است (نه 'not_found') — چون فایل وجود دارد فقط جدید نیست.\n\n"
        "خروجی فقط JSON خالص (بدون ``` یا متن دیگر):\n"
        "{\n"
        '  "results": [\n'
        '    {\n'
        '      "ac_index": 0,\n'
        '      "verdict": "implemented|partial|not_found|unclear",\n'
        '      "matching_commits": ["sha1", "sha2"],\n'
        '      "key_changes": ["+def create_X():", "+ async def handle..."],\n'
        '      "reason": "یک جمله توضیح"\n'
        '    },\n'
        '    ...\n'
        '  ]\n'
        "}\n\n"
        "همان index هایی که در AC ها داده شد را در پاسخ حفظ کن."
    )

    try:
        mgr = get_ai_manager()
        resp = await asyncio.wait_for(
            mgr.generate(
                model_id=verify_model_id,
                messages=[Message(role="user", content=prompt)],
                max_tokens=4000,
                temperature=0.1,
                allow_fallback=True,
            ),
            timeout=_AI_TIMEOUT_S,
        )
        raw = (resp.content or "").strip()
    except asyncio.TimeoutError:
        logger.warning("code_aware_verifier AI timeout")
        return {}
    except Exception as e:
        logger.warning(f"code_aware_verifier AI call failed: {e}")
        return {}

    # parse JSON
    if raw.startswith("```"):
        # حذف fence
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end <= start:
        return {}
    try:
        data = json.loads(raw[start:end + 1])
    except Exception as e:
        logger.debug(f"code_aware_verifier JSON parse failed: {e}")
        return {}

    results = data.get("results", [])
    if not isinstance(results, list):
        return {}
    out: Dict[int, Dict[str, Any]] = {}
    for item in results:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("ac_index"))
        except (TypeError, ValueError):
            continue
        out[idx] = item
    return out


def _norm_verdict(v: Any) -> str:
    s = str(v or "unclear").strip().lower()
    if s not in ("implemented", "partial", "not_found", "unclear"):
        return "unclear"
    return s


def _build_unclear_result(
    idx: int, ac: Any, reason: str = "",
) -> Dict[str, Any]:
    """نتیجه‌ی default 'unclear' برای fallback."""
    ac_text = str(ac.get("text") if isinstance(ac, dict) else ac).strip()
    return {
        "ac_index": idx,
        "ac_text": ac_text,
        "code_verdict": "unclear",
        "matching_commits": [],
        "key_changes": [],
        "reason": reason or "no analysis",
    }
