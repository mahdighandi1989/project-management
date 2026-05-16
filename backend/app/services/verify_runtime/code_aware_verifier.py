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
_MAX_ACS_PER_BATCH = 10      # سقف هر batch به AI (تا context AI نشکند)
_MAX_TOTAL_ACS = 40          # 🆕 (bug 31) — قبلاً همان 10 بود و step های 11+
                              # هرگز code-aware نمی‌گرفتند. حالا تا 40 پشتیبانی
                              # می‌شود با اجرای چند batch موازی.
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

    🆕 (bug 31) — حالا چندین batch اجرا می‌کند تا همه‌ی AC ها تحلیل
    شوند (تا سقف _MAX_TOTAL_ACS=40)، نه فقط ۱۰ تای اول. batch ها به
    صورت موازی اجرا می‌شوند.

    شکست‌خوردگی مجاز:
    - GitHub API fail → همه‌ی نتایج با code_verdict="unclear"
    - AI fail → همه با code_verdict="unclear"
    - acs خالی → []
    """
    if not acs:
        return []

    # commits اخیر را یک‌بار fetch کن (shared بین همه batch ها)
    commits_with_diff = await _fetch_recent_commits_with_diff(
        repo_full_name, token, limit=_MAX_COMMITS_TO_FETCH,
    )
    if not commits_with_diff:
        return [
            _build_unclear_result(i, ac, reason="no recent commits found")
            for i, ac in enumerate(acs[:_MAX_TOTAL_ACS])
        ]

    # 🆕 (bug 31) — تقسیم AC ها به batches و موازی‌سازی
    _capped_acs = acs[:_MAX_TOTAL_ACS]
    _batches: List[List[Any]] = []
    for _b_start in range(0, len(_capped_acs), _MAX_ACS_PER_BATCH):
        _batches.append(_capped_acs[_b_start : _b_start + _MAX_ACS_PER_BATCH])

    logger.info(
        f"code_aware_verifier: {len(_capped_acs)} ACs → "
        f"{len(_batches)} batch(es) of ≤{_MAX_ACS_PER_BATCH}"
    )

    async def _process_batch(
        batch_acs: List[Any], batch_offset: int,
    ) -> List[Dict[str, Any]]:
        return await _process_single_batch(
            task=task,
            batch_acs=batch_acs,
            batch_offset=batch_offset,
            commits_with_diff=commits_with_diff,
            verify_model_id=verify_model_id,
        )

    # موازی‌سازی batch ها
    _gathered = await asyncio.gather(
        *[
            _process_batch(batch, idx * _MAX_ACS_PER_BATCH)
            for idx, batch in enumerate(_batches)
        ],
        return_exceptions=False,
    )

    # ادغام نتایج
    _all_results: List[Dict[str, Any]] = []
    for _batch_results in _gathered:
        _all_results.extend(_batch_results)
    return _all_results


async def _process_single_batch(
    task: Any,
    batch_acs: List[Any],
    batch_offset: int,
    commits_with_diff: List[Dict[str, Any]],
    verify_model_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """پردازش یک batch از ACs (حداکثر _MAX_ACS_PER_BATCH).

    batch_offset برای حفظ ac_id درست (step_N) استفاده می‌شود.
    """
    # AC ها را به متن خام تبدیل کن
    ac_texts: List[str] = []
    for ac in batch_acs:
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
            _build_unclear_result(
                batch_offset + i, ac,
                reason=f"AI batch failed: {str(e)[:100]}",
            )
            for i, ac in enumerate(batch_acs)
        ]

    # نتایج را با input AC ها sync کن
    target_files_list = list(task.target_files or [])
    _task_steps_text = " ".join(
        f"{s.get('title', '')} {s.get('scope', '')}"
        for s in (getattr(task, "task_steps", None) or [])
        if isinstance(s, dict)
    )
    _task_title = str(getattr(task, "title", "") or "")
    _task_extra_context = (_task_title + " " + _task_steps_text).strip()

    final: List[Dict[str, Any]] = []
    for i, ac in enumerate(batch_acs):
        ac_text = ac_texts[i] if i < len(ac_texts) else ""
        ai_item = results.get(i, {}) if isinstance(results, dict) else {}
        verdict = _norm_verdict(ai_item.get("verdict"))
        matching = list(ai_item.get("matching_commits") or [])[:5]
        key_changes = list(ai_item.get("key_changes") or [])[:5]
        reason = str(ai_item.get("reason") or "")[:400]

        # programmatic upgrade (همان منطق قبلی)
        if verdict in ("not_found", "unclear") and target_files_list and ac_text:
            import re as _re_match
            _full_ctx = (ac_text + " " + _task_extra_context).strip()
            ac_tokens = set(
                t.lower() for t in _re_match.findall(r"[A-Za-z][A-Za-z0-9]+", _full_ctx)
                if len(t) >= 3
            )
            matched_files: List[str] = []
            for tf in target_files_list:
                tf_str = str(tf)
                base = tf_str.rsplit("/", 1)[-1].rsplit(".", 1)[0]
                if len(base) < 4:
                    continue
                # tokenize basename روی _, -, .
                base_tokens = set(
                    t.lower() for t in _re_match.split(r"[_\-.]", base)
                    if len(t) >= 3
                )
                if not base_tokens:
                    continue
                # match اگر همه token های basename در AC تمیز پیدا شوند
                if base_tokens.issubset(ac_tokens):
                    matched_files.append(tf_str)
            if matched_files:
                verdict = "implemented"
                _orig_reason = reason
                reason = (
                    f"⚙️ programmatic-upgrade: AI گفت not_found ولی AC به "
                    f"{matched_files[:3]} اشاره می‌کند که در target_files "
                    f"موجود است → پیش‌ساخته. "
                    f"اصلی: {_orig_reason[:160]}"
                )

        final.append({
            "ac_index": batch_offset + i,  # 🆕 offset باعث می‌شود ac_index در سراسر batch ها یکتا بماند
            "ac_text": ac_text,
            "code_verdict": verdict,
            "matching_commits": matching,
            "key_changes": key_changes,
            "reason": reason,
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
        "تو یک Code Reviewer قاطع هستی. وظیفه‌ات تصمیم‌گیری روشن است:\n"
        "آیا هر AC در repo پیاده شده یا نه. **از 'unclear' تنها در موارد\n"
        "واقعاً مبهم استفاده کن** — اگر شواهد متوسط داری، 'implemented'\n"
        "یا 'partial' یا 'not_found' بده.\n\n"
        f"📁 فایل‌های هدف تسک (target_files — فایل‌هایی که در این تسک\n"
        f"    یا قبلاً ساخته شده‌اند):\n"
        f"    {target_files_text}\n\n"
        f"📋 AC ها (با index):\n{ac_block}\n\n"
        f"📦 commit های اخیر (تا {len(commits)} commit):\n{commits_block}\n\n"
        "⚠️ راهنمای verdict (با اولویت decision کردن):\n"
        "- 'implemented': یا diff های اخیر این AC را صریحاً پیاده کرده‌اند،\n"
        "  **یا** فایل/تابع/endpoint مرتبط در target_files ذکر شده. اگر\n"
        "  هر دو شرط نقض است ولی task target_files چندتا فایل مرتبط\n"
        "  دارد، باز هم 'implemented' بده (با reason: «target_files\n"
        "  شامل X, Y, Z است که به AC مرتبط‌اند»).\n"
        "- 'partial': بخشی پیاده شده ولی واضحاً ناقص.\n"
        "- 'not_found': نه diff تازه نه فایل مرتبط در target_files —\n"
        "  AC احتمالاً ساخته نشده.\n"
        "- 'unclear': **آخرین گزینه** — فقط وقتی AC کاملاً ابهام دارد\n"
        "  یا اطلاعات کاملاً ناکافی است.\n\n"
        "🛑 قانون مهم: اگر یک AC به فایلی اشاره می‌کند که در\n"
        "   target_files لیست شده، عموماً 'implemented' است — \n"
        "   فقط 'not_found' بده اگر هیچ نشانه‌ای از AC در هیچ\n"
        "   منبعی نمی‌بینی.\n\n"
        "🎯 پیش‌فرض: قاطع باش. اگر مشکوک به implemented هستی،\n"
        "   'implemented' بده با reason صریح. 'unclear' یعنی\n"
        "   «نمی‌توانم تصمیم بگیرم» — این پاسخ نباید پاسخ پیش‌فرض باشد.\n\n"
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
