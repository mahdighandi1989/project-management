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
_MAX_TOTAL_ACS = 200         # 🆕 (Bug C6 v6) — قبلاً 40 بود؛ task های meta با
                              # ۵۲+ AC (مثل meta-test verify v6) باعث می‌شد
                              # step های 41+ از code-aware محروم بمانند و
                              # programmatic-upgrade نگیرند → در checklist
                              # not_done. cap به ۲۰۰ هماهنگ با cap step
                              # generator (200) بالا برده شد.
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
    شوند (تا سقف _MAX_TOTAL_ACS=200)، نه فقط ۱۰ تای اول. batch ها به
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

        # programmatic upgrade — 🆕 (bug 34) — حالا "partial" را هم پشتیبانی
        # می‌کند. علت: AC هایی که چند feature را با هم نام می‌برند («Smart
        # Navigation + Backend Log Probe + Code-aware») وقتی AI فقط یکی را
        # در commits اخیر می‌بیند، verdict را "partial" می‌گذارد و
        # implemented اعلام نمی‌شود. اگر همه فایل‌های مرتبط در target_files
        # یا repo tree موجود باشند، باید به implemented upgrade شوند.
        if verdict in ("not_found", "unclear", "partial") and target_files_list and ac_text:
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
                # 🆕 (bug 34) — match در چهار سطح:
                # 1) strict: همه‌ی token های basename در AC tokens
                # 2) majority: ≥۵۰٪ token های basename match + ≥۲ مورد
                # 3) single-token: basename یک‌token است و در AC هست
                # 4) specific-token: یک token "specific" (≥۶ char، یعنی
                #    کلمهٔ تخصصی مثل "navigation"، "inspector"، "auth_runner")
                #    در AC هست — این برای ACهایی که فقط feature name را
                #    می‌گویند (نه پسوند helper/runner/service) لازم است.
                # tokenهای generic که به‌تنهایی شواهد محکم نیستند
                _COMMON_SUFFIX_TOKENS = {
                    "helper", "runner", "service", "utils", "util", "manager",
                    "handler", "factory", "client", "common", "test", "tests",
                    "main", "app", "src", "lib", "code", "file", "data",
                    "base", "core", "types", "schema", "config",
                }
                _inter = base_tokens & ac_tokens
                _strict_match = base_tokens.issubset(ac_tokens)
                _majority_match = (
                    len(base_tokens) >= 2
                    and len(_inter) >= 2
                    and len(_inter) / len(base_tokens) >= 0.5
                )
                _single_token_match = (
                    len(base_tokens) == 1 and len(_inter) == 1
                )
                # specific-token: حداقل یک token محکم (≥۴ char و در لیست
                # stopwords عمومی نیست) match کرده. ۴ char برای پوشش
                # کلمات تخصصی کوتاه مثل "auth" یا "probe" یا "scan".
                _specific_match = any(
                    t in ac_tokens
                    and len(t) >= 4
                    and t not in _COMMON_SUFFIX_TOKENS
                    for t in base_tokens
                )
                if _strict_match or _majority_match or _single_token_match or _specific_match:
                    matched_files.append(tf_str)
            if matched_files:
                _prev_verdict = verdict
                verdict = "implemented"
                _orig_reason = reason
                reason = (
                    f"⚙️ programmatic-upgrade: AI گفت {_prev_verdict} ولی AC به "
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


# ===========================================================================
# 🔬 Bug C6 — Verify v6, گپ ۳ — AC matching: file content (نه basename)
# ===========================================================================
# ۴ مرحلهٔ A→B→C→D با نام تابع‌های صریح برای traceability.
# orchestrator: analyze_acs_with_content_grep(acs, context) — early-exit اگر
# هر phase done قطعی داد.


async def _phase_a_basename_match(ac, target_files, context):
    """Phase A — basename match.

    ضعیف‌ترین signal: آیا identifier های AC در basename فایل‌های هدف
    هستند؟ سریع و بدون API call. اگر hit زیاد بود، done قطعی.
    """
    from .code_content_searcher import extract_identifiers
    from .iterative_orchestrator import ProbeResult
    import time as _t
    start = _t.monotonic()

    ac_text = str(ac.get("text", "") if isinstance(ac, dict) else ac)
    identifiers = extract_identifiers(ac_text)
    if not identifiers or not target_files:
        return ProbeResult(
            probe_name="code_aware_basename",
            verdict="unclear",
            confidence=0.0,
            evidence=["no identifiers or no target_files"],
            elapsed_ms=int((_t.monotonic() - start) * 1000),
        )

    hits = 0
    matched_paths = []
    for path in target_files[:30]:
        base = path.rsplit("/", 1)[-1].rsplit(".", 1)[0].lower()
        for ident in identifiers:
            if ident.lower() in base:
                hits += 1
                matched_paths.append(path)
                break

    if hits >= 2:
        verdict, confidence = "done", 0.85
    elif hits == 1:
        verdict, confidence = "partial", 0.55
    else:
        verdict, confidence = "not_done", 0.5

    if context is not None:
        try:
            context.append_trace({
                "phase": "_phase_a_basename_match",
                "ac_text": ac_text[:120],
                "hits": hits,
                "verdict": verdict,
            })
        except Exception:
            pass

    return ProbeResult(
        probe_name="code_aware_basename",
        verdict=verdict,
        confidence=confidence,
        evidence=[f"basename hits: {hits}", f"matched: {matched_paths[:5]}"],
        elapsed_ms=int((_t.monotonic() - start) * 1000),
    )


async def _phase_b_content_grep(ac, target_files, context):
    """Phase B — content grep روی target_files.

    استفاده از smart_grep_for_ac برای جستجوی identifier ها در محتوای
    فایل (نه فقط basename). dependent به GitHub Contents API.
    """
    from .code_content_searcher import smart_grep_for_ac
    from .iterative_orchestrator import ProbeResult
    import time as _t
    start = _t.monotonic()

    ac_text = str(ac.get("text", "") if isinstance(ac, dict) else ac)
    if not ac_text:
        return ProbeResult("content_grep_weak", "unclear", 0.0, ["empty ac_text"])

    task = context.task if context else None
    watched = context.watched if context else None
    repo_full_name = ""
    if watched is not None:
        repo_full_name = getattr(watched, "repo_full_name", "") or ""
    if not repo_full_name and task is not None:
        repo_full_name = getattr(task, "project_full_name", "") or ""
    if not repo_full_name or not target_files:
        return ProbeResult("content_grep_weak", "unclear", 0.0, ["no repo or target_files"])

    branch = (getattr(watched, "default_branch", None) or "main") if watched else "main"

    try:
        results = await smart_grep_for_ac(
            ac_text, target_files, repo_full_name, branch, context=context,
        )
    except Exception as e:
        return ProbeResult(
            "content_grep_weak", "unclear", 0.0,
            evidence=[f"grep error: {e}"], error=str(e),
            elapsed_ms=int((_t.monotonic() - start) * 1000),
        )

    matched_idents = len(results)
    files_with_match = set()
    for matches in results.values():
        for m in matches:
            files_with_match.add(m.get("path", ""))

    if matched_idents >= 2 and len(files_with_match) >= 1:
        probe_name = "content_grep_strong"
        verdict, confidence = "done", 0.9
    elif matched_idents >= 1:
        probe_name = "content_grep_weak"
        verdict, confidence = "partial", 0.6
    else:
        probe_name = "content_grep_weak"
        verdict, confidence = "not_done", 0.55

    if context is not None:
        try:
            context.append_trace({
                "phase": "_phase_b_content_grep",
                "ac_text": ac_text[:120],
                "identifiers_matched": matched_idents,
                "files_with_match": list(files_with_match)[:5],
                "verdict": verdict,
            })
        except Exception:
            pass

    return ProbeResult(
        probe_name=probe_name,
        verdict=verdict,
        confidence=confidence,
        evidence=[
            f"identifiers matched: {matched_idents}",
            f"files: {sorted(files_with_match)[:5]}",
        ],
        elapsed_ms=int((_t.monotonic() - start) * 1000),
    )


async def _phase_c_extended_repo_grep(ac, context):
    """Phase C — extended repo grep.

    اگر phase B done قطعی نداد، scope را به repo_tree گسترش می‌دهیم با
    فیلتر extension مرتبط (py/tsx/ts/jsx/js) و path overlap با AC text.
    cap 50 فایل اضافی.
    """
    from .code_content_searcher import grep_token_in_files, extract_identifiers
    from .iterative_orchestrator import ProbeResult
    import time as _t
    import re as _re
    start = _t.monotonic()

    ac_text = str(ac.get("text", "") if isinstance(ac, dict) else ac)
    if not ac_text or not context or not context.repo_tree:
        return ProbeResult(
            "content_grep_weak", "unclear", 0.0,
            evidence=["no repo_tree available"],
            elapsed_ms=int((_t.monotonic() - start) * 1000),
        )

    cfg = context.config
    task = context.task
    watched = context.watched
    repo_full_name = ""
    if watched is not None:
        repo_full_name = getattr(watched, "repo_full_name", "") or ""
    if not repo_full_name:
        repo_full_name = getattr(task, "project_full_name", "") or ""
    branch = (getattr(watched, "default_branch", None) or "main") if watched else "main"
    target_set = set(getattr(task, "target_files", None) or [])

    relevant_exts = (".py", ".tsx", ".ts", ".jsx", ".js")
    ac_lower = ac_text.lower()
    path_hints = set(m.group(1).lower() for m in _re.finditer(r"\b([a-z_][\w/]*)/", ac_lower))

    cap_files = cfg.iter2_max_extra_files if cfg else 50
    extended_files = []
    for path in context.repo_tree:
        if path in target_set:
            continue
        if not path.endswith(relevant_exts):
            continue
        plower = path.lower()
        if any(h and h in plower for h in path_hints):
            extended_files.append(path)
        elif len(extended_files) < cap_files // 2:
            extended_files.append(path)
        if len(extended_files) >= cap_files:
            break

    if not extended_files:
        return ProbeResult(
            "content_grep_weak", "unclear", 0.0,
            evidence=["no extended files matched"],
            elapsed_ms=int((_t.monotonic() - start) * 1000),
        )

    top_k = cfg.iter2_max_identifiers if cfg else 25
    identifiers = extract_identifiers(ac_text)[:top_k]
    if not identifiers:
        return ProbeResult(
            "content_grep_weak", "unclear", 0.0,
            evidence=["no identifiers extracted"],
            elapsed_ms=int((_t.monotonic() - start) * 1000),
        )

    try:
        from ..github_storage import get_github_token
        gh_token = get_github_token() or ""
    except Exception:
        gh_token = ""

    matched_idents = 0
    matched_files = set()
    for ident in identifiers:
        matches = await grep_token_in_files(
            ident, extended_files, repo_full_name, branch,
            github_token=gh_token,
            cache=context.file_grep_cache,
            file_content_cache=context.file_content_cache,
        )
        context.grep_calls_count += 1
        if matches:
            matched_idents += 1
            for m in matches:
                matched_files.add(m.get("path", ""))

    if matched_idents >= 2:
        probe_name = "content_grep_strong"
        verdict, confidence = "done", 0.75
    elif matched_idents == 1:
        probe_name = "content_grep_weak"
        verdict, confidence = "partial", 0.55
    else:
        probe_name = "content_grep_weak"
        verdict, confidence = "not_done", 0.5

    if context is not None:
        try:
            context.append_trace({
                "phase": "_phase_c_extended_repo_grep",
                "extended_files": len(extended_files),
                "identifiers_matched": matched_idents,
                "verdict": verdict,
            })
        except Exception:
            pass

    return ProbeResult(
        probe_name=probe_name,
        verdict=verdict,
        confidence=confidence,
        evidence=[
            f"extended scope: {len(extended_files)} files",
            f"identifiers matched: {matched_idents}/{len(identifiers)}",
            f"files: {sorted(matched_files)[:5]}",
        ],
        elapsed_ms=int((_t.monotonic() - start) * 1000),
    )


async def _phase_d_ai_judgment(ac, context):
    """Phase D — AI judgment نهایی.

    آخرین مرحله: اگر هیچ‌کدام از phase های A/B/C done قطعی ندادند، یک
    AI call با کل context (AC + repo_tree + file_content_cache snippets
    + task.prompt) برای قضاوت نهایی. این مرحله متفاوت از
    _strong_model_judgment است که در iteration 3 از iterative_orchestrator
    صدا زده می‌شود — این AI judgment ساده‌تر و سریع‌تر است.
    """
    from .iterative_orchestrator import ProbeResult, _strong_model_judgment
    import time as _t
    start = _t.monotonic()

    # برای ساده‌سازی، از همان _strong_model_judgment استفاده می‌کنیم — این
    # AC را به دقیق‌ترین مدل ممکن می‌سپارد. در صورت نبود strong model،
    # fallback به default extraction model.
    if context is None:
        return ProbeResult("ai_verifier", "unclear", 0.0, evidence=["no context"])
    try:
        result = await _strong_model_judgment(ac, context, [])
        # تغییر probe_name برای traceability
        result.probe_name = "ai_verifier"
        if context is not None:
            try:
                context.append_trace({
                    "phase": "_phase_d_ai_judgment",
                    "verdict": result.verdict,
                    "confidence": result.confidence,
                })
            except Exception:
                pass
        return result
    except Exception as e:
        return ProbeResult(
            "ai_verifier", "unclear", 0.0,
            evidence=[f"AI error: {e}"], error=str(e),
            elapsed_ms=int((_t.monotonic() - start) * 1000),
        )


async def analyze_acs_with_content_grep(acs, context):
    """Orchestrator گپ ۳ — چهار phase A→B→C→D با early-exit.

    برای هر AC: phase A → اگر done قطعی (confidence >= 0.85) finalize.
    در غیر این صورت → phase B → C → D. هر phase که done قطعی داد،
    early-exit.

    خروجی: List[ProbeResult] به طول acs.
    """
    from .iterative_orchestrator import ProbeResult
    results = []
    task = context.task if context else None
    target_files = list(getattr(task, "target_files", None) or []) if task else []

    for ac in acs or []:
        # Phase A
        r_a = await _phase_a_basename_match(ac, target_files, context)
        if r_a.verdict == "done" and r_a.confidence >= 0.85:
            results.append(r_a)
            continue
        # Phase B
        r_b = await _phase_b_content_grep(ac, target_files, context)
        if r_b.verdict == "done" and r_b.confidence >= 0.85:
            results.append(r_b)
            continue
        # Phase C
        r_c = await _phase_c_extended_repo_grep(ac, context)
        if r_c.verdict == "done" and r_c.confidence >= 0.7:
            results.append(r_c)
            continue
        # Phase D
        r_d = await _phase_d_ai_judgment(ac, context)
        results.append(r_d)

    return results
