"""Phase 6 — bug C3: Post-Verify Intelligent Task Consolidation Engine.

بعد از پایان Bulk Verify، تسک‌هایی که done نشده‌اند (not_done + partial +
needs_clarification + regressed) بر اساس ماهیت و شباهت در super-task های
بزرگ‌تر تجمیع می‌شوند. هیچ خلاصه‌سازی انجام نمی‌شود — متن کامل idea_prompt
هر source task در super-task حفظ می‌شود.

API عمومی:
    build_candidate_fingerprint(task) -> dict
    mechanical_precluster(candidates) -> list[cluster]
    consolidate_remaining_tasks(
        watched_id, candidates, mode, verify_model_id,
        live_preclusters, service, state
    ) -> dict
    unmerge_super_task(super_task_id, service) -> dict
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# تنظیمات داخلی
_AI_CLUSTER_BATCH_SIZE = 40
_AI_CLUSTER_TIMEOUT_S = 60
_AI_CHECKLIST_TIMEOUT_S = 30
_MAX_CANDIDATES = 200  # ایمنی: اگر بیش از این، فقط top-N by priority
_MIN_CANDIDATES_TO_RUN = 5
_MIN_CLUSTER_SIZE = 2
_PRECLUSTER_FILES_JACCARD = 0.5
_PRECLUSTER_TITLE_TRIGRAM = 0.7

_PRIORITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


# ────────────────────────────────────────────────────────────────────
# Phase 1 (الف): جمع‌آوری fingerprint
# ────────────────────────────────────────────────────────────────────

def build_candidate_fingerprint(task: Any) -> Dict[str, Any]:
    """fingerprint غنی برای کاندیدای consolidation.

    منابع:
      - task.* (مستقیم)
      - task_steps (تفکیک به completed_parts و remaining_parts)
      - applied_evidence.files یا similar
    """
    # وضعیت per-step
    completed_parts: List[str] = []
    remaining_parts: List[str] = []
    for s in (getattr(task, "task_steps", None) or []):
        if not isinstance(s, dict):
            continue
        _st = str(s.get("status") or "").lower()
        _title = s.get("title") or s.get("id") or ""
        if _st == "done":
            completed_parts.append(_title)
        else:
            _r = s.get("remaining") or ""
            remaining_parts.append(f"{_title}" + (f" — {_r}" if _r else ""))

    # files touched (از applied_evidence یا target_files یا verification_history)
    files: Set[str] = set()
    for f in (getattr(task, "target_files", None) or []):
        if isinstance(f, str) and f.strip():
            files.add(f.strip())
    _ae = getattr(task, "applied_evidence", None) or {}
    if isinstance(_ae, dict):
        for f in (_ae.get("files") or []):
            if isinstance(f, str) and f.strip():
                files.add(f.strip())
    # آخرین verification report می‌تواند evidence files داشته باشد
    _vh = getattr(task, "verification_history", None) or []
    if _vh and isinstance(_vh, list):
        for entry in _vh[-3:]:
            if not isinstance(entry, dict):
                continue
            for f in (entry.get("files") or []):
                if isinstance(f, str) and f.strip():
                    files.add(f.strip())

    return {
        "task_id": getattr(task, "id", ""),
        "title": (getattr(task, "title", "") or "")[:200],
        "idea_prompt": getattr(task, "prompt", "") or getattr(task, "raw_idea", "") or "",
        "priority": (getattr(task, "priority", "medium") or "medium").lower(),
        "tags": list(getattr(task, "tags", []) or []),
        "type": getattr(task, "type", "other") or "other",
        "acceptance_criteria": list(getattr(task, "acceptance_criteria", []) or []),
        "task_steps": list(getattr(task, "task_steps", []) or []),
        "completed_parts": completed_parts,
        "remaining_parts": remaining_parts,
        "files_touched": sorted(files),
        "verification_status": getattr(task, "verification_status", "pending") or "pending",
        "status": getattr(task, "status", "pending") or "pending",
        "created_at": getattr(task, "created_at", "") or "",
        "creation_context": getattr(task, "created_by_scan_metadata", None) or {},
        "watched_id": getattr(task, "watched_id", "") or getattr(task, "project_full_name", ""),
    }


# ────────────────────────────────────────────────────────────────────
# Phase 1 (ب): Mechanical pre-cluster (no AI)
# ────────────────────────────────────────────────────────────────────

def _norm_token(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def _trigrams(s: str) -> Set[str]:
    s = _norm_token(s)
    if len(s) < 3:
        return {s} if s else set()
    return {s[i : i + 3] for i in range(len(s) - 2)}


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 0.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def mechanical_precluster(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """گروه‌بندی mechanical بر اساس files / tags / title trigram.

    خروجی: لیست cluster، هر کدام:
      {cluster_id, kind: "files"|"tags"|"title", task_ids: [...], rationale}
    یک task می‌تواند در چند pre-cluster باشد — این فقط hint است.
    """
    if not candidates:
        return []

    out: List[Dict[str, Any]] = []
    cid = 0

    # 1) same-file groups
    by_file: Dict[str, List[str]] = {}
    files_per_task: Dict[str, Set[str]] = {}
    for c in candidates:
        files_per_task[c["task_id"]] = set(c.get("files_touched") or [])
    task_ids = [c["task_id"] for c in candidates]
    file_visited: Set[str] = set()
    for i, tid_i in enumerate(task_ids):
        if tid_i in file_visited:
            continue
        fi = files_per_task[tid_i]
        if not fi:
            continue
        group = [tid_i]
        for tid_j in task_ids[i + 1 :]:
            if tid_j in file_visited:
                continue
            fj = files_per_task[tid_j]
            if not fj:
                continue
            if _jaccard(fi, fj) >= _PRECLUSTER_FILES_JACCARD:
                group.append(tid_j)
        if len(group) >= _MIN_CLUSTER_SIZE:
            cid += 1
            for tid in group:
                file_visited.add(tid)
            out.append({
                "cluster_id": f"pre_files_{cid}",
                "kind": "files",
                "task_ids": group,
                "rationale": f"اشتراک فایل با Jaccard ≥ {_PRECLUSTER_FILES_JACCARD}",
            })

    # 2) same-tag groups (هر tag یک گروه می‌سازد)
    tag_to_tasks: Dict[str, List[str]] = {}
    for c in candidates:
        for t in (c.get("tags") or []):
            tkey = _norm_token(str(t))
            if not tkey or tkey in ("consolidated", "merged", "post_verify_merge"):
                continue
            tag_to_tasks.setdefault(tkey, []).append(c["task_id"])
    for tag, tids in tag_to_tasks.items():
        # dedup
        tids = list(dict.fromkeys(tids))
        if len(tids) >= _MIN_CLUSTER_SIZE:
            cid += 1
            out.append({
                "cluster_id": f"pre_tag_{cid}",
                "kind": "tags",
                "task_ids": tids,
                "rationale": f"tag مشترک: {tag}",
            })

    # 3) title-trigram groups
    trigrams_per_task: Dict[str, Set[str]] = {
        c["task_id"]: _trigrams(c.get("title") or "") for c in candidates
    }
    title_visited: Set[str] = set()
    for i, tid_i in enumerate(task_ids):
        if tid_i in title_visited:
            continue
        ti = trigrams_per_task[tid_i]
        if len(ti) < 3:
            continue
        group = [tid_i]
        for tid_j in task_ids[i + 1 :]:
            if tid_j in title_visited:
                continue
            tj = trigrams_per_task[tid_j]
            if len(tj) < 3:
                continue
            if _jaccard(ti, tj) >= _PRECLUSTER_TITLE_TRIGRAM:
                group.append(tid_j)
        if len(group) >= _MIN_CLUSTER_SIZE:
            cid += 1
            for tid in group:
                title_visited.add(tid)
            out.append({
                "cluster_id": f"pre_title_{cid}",
                "kind": "title",
                "task_ids": group,
                "rationale": f"شباهت عنوان (trigram Jaccard ≥ {_PRECLUSTER_TITLE_TRIGRAM})",
            })

    return out


# ────────────────────────────────────────────────────────────────────
# Phase 2: AI clustering
# ────────────────────────────────────────────────────────────────────

async def _ai_cluster_batch(
    batch: List[Dict[str, Any]],
    pre_hints: List[Dict[str, Any]],
    verify_model_id: Optional[str],
) -> Optional[Dict[str, Any]]:
    """یک batch از کاندیدها را به AI می‌دهد و clusterها را برمی‌گرداند.

    None اگر AI ناموفق بود — caller باید fallback به mechanical بزند.
    """
    try:
        from .ai_manager import get_ai_manager
        from .ai_base import Message
    except Exception as e:
        logger.warning(f"consolidation: ai imports failed: {e}")
        return None

    if not verify_model_id:
        try:
            from ..core.models_registry import DEFAULT_EXTRACTION_MODEL_ID
            verify_model_id = DEFAULT_EXTRACTION_MODEL_ID
        except Exception:
            return None

    # ساخت لیست کاندیدها برای prompt
    items_block_lines: List[str] = []
    for i, c in enumerate(batch):
        _idea_snippet = (c.get("idea_prompt") or "")[:400].replace("\n", " ")
        _files = ", ".join((c.get("files_touched") or [])[:6])
        _tags = ", ".join((c.get("tags") or [])[:6])
        _vs = c.get("verification_status") or "?"
        _rp = "; ".join((c.get("remaining_parts") or [])[:4])
        items_block_lines.append(
            f"[{i}] id={c['task_id']} | "
            f"title={c.get('title', '')[:90]} | "
            f"type={c.get('type', '?')} | "
            f"priority={c.get('priority', '?')} | "
            f"verify_status={_vs} | "
            f"tags=[{_tags}] | "
            f"files=[{_files}] | "
            f"remaining=[{_rp}] | "
            f"idea_snippet={_idea_snippet}"
        )
    items_block = "\n".join(items_block_lines)

    # pre-hint برای کمک به AI
    hints_block = ""
    if pre_hints:
        _h_lines: List[str] = []
        for h in pre_hints[:20]:
            _ids = [t for t in (h.get("task_ids") or []) if any(c["task_id"] == t for c in batch)]
            if len(_ids) >= 2:
                _h_lines.append(
                    f"- {h.get('kind', '?')}: {h.get('rationale', '')} "
                    f"→ tasks: {', '.join(_ids[:8])}"
                )
        if _h_lines:
            hints_block = "\n\n🔍 pre-cluster hints (mechanical، فقط راهنما):\n" + "\n".join(_h_lines)

    prompt = (
        "تو در نقش یک Task Consolidator هستی. هدف: تسک‌های زیر را بر اساس "
        "**ماهیت و شباهت** در چند cluster بزرگ‌تر دسته‌بندی کنی.\n\n"
        "📋 قوانین:\n"
        "1. هر cluster حداقل ۲ تسک. تسک‌هایی که در هیچ cluster جا نمی‌گیرند "
        "را در unclustered_task_ids بگذار.\n"
        "2. **تسک‌های با verify_status='partial' را حتماً در همان clusterهایی "
        "قرار بده که با not_done ها هم‌موضوع هستند. هرگز برای partialها "
        "cluster مجزا نساز** مگر اینکه واقعاً هیچ not_done هم‌موضوعی نباشد.\n"
        "3. clusters باید بر اساس theme واقعی باشند (مثلاً 'بهبود سیستم "
        "notification' یا 'refactor backend auth')، نه فقط tag مشترک.\n"
        "4. هر cluster باید priority، type و estimated_difficulty داشته "
        "باشد. priority از max(priority تسک‌های داخلش) محاسبه شود.\n"
        "5. mixed_partial_and_not_done = True اگر cluster هم partial هم "
        "not_done داشته باشد.\n"
        "6. suggested_super_title باید **توصیفی و عملیاتی** باشد، نه کلی.\n\n"
        f"📦 کاندیدها ({len(batch)} تسک):\n{items_block}"
        f"{hints_block}\n\n"
        "خروجی JSON خالص (بدون متن اضافه، بدون markdown):\n"
        "{\n"
        '  "clusters": [\n'
        '    {\n'
        '      "cluster_id": "c1",\n'
        '      "theme": "...",\n'
        '      "rationale": "...",\n'
        '      "task_ids": ["..."],\n'
        '      "suggested_super_title": "...",\n'
        '      "priority": "critical|high|medium|low",\n'
        '      "type": "frontend|backend|fullstack|infra|other",\n'
        '      "estimated_difficulty": "small|medium|large",\n'
        '      "mixed_partial_and_not_done": true\n'
        '    }\n'
        '  ],\n'
        '  "unclustered_task_ids": ["..."]\n'
        "}"
    )

    try:
        mgr = get_ai_manager()
        resp = await asyncio.wait_for(
            mgr.generate(
                model_id=verify_model_id,
                messages=[Message(role="user", content=prompt)],
                max_tokens=4000,
                temperature=0.2,
                allow_fallback=True,
            ),
            timeout=_AI_CLUSTER_TIMEOUT_S,
        )
        raw = (resp.content or "").strip()
    except asyncio.TimeoutError:
        logger.warning("consolidation: AI cluster call timed out")
        return None
    except Exception as e:
        logger.warning(f"consolidation: AI cluster call failed: {e}")
        return None

    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end <= start:
        logger.warning("consolidation: AI returned non-JSON")
        return None
    try:
        data = json.loads(raw[start : end + 1])
    except Exception as e:
        logger.warning(f"consolidation: JSON parse failed: {e}")
        return None
    if not isinstance(data, dict):
        return None
    return data


def _validate_clusters(
    ai_result: Dict[str, Any],
    candidates: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """validation روی خروجی AI.

    - task_idهای ناشناخته drop می‌شوند
    - تکرار task_id در چند cluster: اولی برنده
    - cluster های تک‌تسکی drop → اعضایشان به unclustered

    خروجی: (valid_clusters, unclustered_task_ids)
    """
    valid_ids = {c["task_id"] for c in candidates}
    clusters_raw = ai_result.get("clusters") or []
    unclustered_raw = ai_result.get("unclustered_task_ids") or []
    if not isinstance(clusters_raw, list):
        clusters_raw = []
    if not isinstance(unclustered_raw, list):
        unclustered_raw = []

    seen_ids: Set[str] = set()
    valid_clusters: List[Dict[str, Any]] = []
    for cl in clusters_raw:
        if not isinstance(cl, dict):
            continue
        raw_ids = cl.get("task_ids") or []
        if not isinstance(raw_ids, list):
            continue
        clean_ids: List[str] = []
        for tid in raw_ids:
            if not isinstance(tid, str):
                continue
            if tid not in valid_ids:
                continue
            if tid in seen_ids:
                continue  # اولی برنده
            seen_ids.add(tid)
            clean_ids.append(tid)
        if len(clean_ids) < _MIN_CLUSTER_SIZE:
            # cluster تک‌تسکی → اعضا به unclustered برمی‌گردند
            for tid in clean_ids:
                seen_ids.discard(tid)
            continue
        valid_clusters.append({
            "cluster_id": str(cl.get("cluster_id") or f"c_{len(valid_clusters) + 1}"),
            "theme": str(cl.get("theme") or "")[:200],
            "rationale": str(cl.get("rationale") or "")[:500],
            "task_ids": clean_ids,
            "suggested_super_title": str(cl.get("suggested_super_title") or "")[:200],
            "priority": str(cl.get("priority") or "medium").lower(),
            "type": str(cl.get("type") or "other").lower(),
            "estimated_difficulty": str(cl.get("estimated_difficulty") or "medium").lower(),
            "mixed_partial_and_not_done": bool(cl.get("mixed_partial_and_not_done", False)),
        })

    # هر چه در seen نیست → unclustered
    unclustered = [tid for tid in valid_ids if tid not in seen_ids]
    return valid_clusters, unclustered


# ────────────────────────────────────────────────────────────────────
# Super-task construction
# ────────────────────────────────────────────────────────────────────

def _safe_str(v: Any, max_len: int = 1000) -> str:
    """تبدیل ایمن هر مقدار به string قابل strip.

    🐛 (C4 fix) — بسیاری از فیلدها (مثل verify_plan در ACهای ساختاریافته)
    می‌توانند dict باشند. ()`dict or ""` به dict ارزیابی می‌شود (truthy)،
    سپس `.strip()` روی dict خطا می‌اندازد:
        'dict' object has no attribute 'strip'
    این تابع dict/list/None را به str ایمن تبدیل می‌کند.
    """
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, (dict, list)):
        try:
            return json.dumps(v, ensure_ascii=False)[:max_len]
        except Exception:
            return str(v)[:max_len]
    try:
        return str(v).strip()[:max_len]
    except Exception:
        return ""


def _format_step_summary(step: Dict[str, Any]) -> str:
    _title = _safe_str(step.get("title") or step.get("id") or "", max_len=200)
    _scope = _safe_str(step.get("scope") or "", max_len=200)
    if _scope:
        return f"{_title} — {_scope[:200]}"
    return _title


def _format_ac(ac: Any) -> str:
    """فرمت AC به متن — مقاوم در برابر dict های nested.

    🐛 (C4 fix) — قبلاً (ac.get("verify_plan") or "").strip() اگر verify_plan
    یک dict بود (مثل {"steps":[...], "detection_signal":"..."})، چون dict
    truthy است، strip روی dict خطا می‌داد. حالا با _safe_str ایمن است.
    """
    if isinstance(ac, str):
        return ac.strip()
    if isinstance(ac, dict):
        _text = _safe_str(ac.get("text"), max_len=500)
        _vm = _safe_str(ac.get("verify_method"), max_len=200)
        _vp = _safe_str(ac.get("verify_plan"), max_len=500)
        out = _text
        if _vm:
            out += f" [verify_method={_vm}]"
        if _vp:
            out += f" [verify_plan={_vp[:200]}]"
        return out
    return _safe_str(ac)


def _build_merged_idea_prompt(
    cluster: Dict[str, Any],
    source_candidates: List[Dict[str, Any]],
) -> str:
    """ساخت idea_prompt تلفیقی — هیچ خلاصه‌سازی، متن کامل همه source ها.

    این متن به‌عنوان ورودی `_ai_plan_steps_from_idea` استفاده می‌شود.
    """
    N = len(source_candidates)
    parts: List[str] = []
    parts.append(
        f"🧬 این یک تسک تلفیقی است — از {N} تسک منفرد ساخته شده.\n"
        f"📌 دلیل تلفیق (rationale توسط AI): {cluster.get('rationale') or '-'}\n"
        f"🎯 theme: {cluster.get('theme') or '-'}\n"
        f"💎 estimated_difficulty: {cluster.get('estimated_difficulty') or 'medium'}\n"
    )

    # ترتیب: critical → high → medium → low
    sorted_src = sorted(
        source_candidates,
        key=lambda c: _PRIORITY_RANK.get((c.get("priority") or "medium").lower(), 9),
    )

    for idx, c in enumerate(sorted_src, start=1):
        _acs = "\n".join(f"  - {_format_ac(a)}" for a in (c.get("acceptance_criteria") or []))
        if not _acs:
            _acs = "  (هیچ AC ثبت نشده بود)"
        _completed = "\n".join(f"  - {s}" for s in (c.get("completed_parts") or []))
        if not _completed:
            _completed = "  (هیچ مرحله‌ای قبلاً done نشده بود)"
        _remaining = "\n".join(f"  - {s}" for s in (c.get("remaining_parts") or []))
        if not _remaining:
            _remaining = "  (همهٔ مراحل remaining هستند)"
        _files = ", ".join(c.get("files_touched") or []) or "-"

        parts.append(
            "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"تسک {idx} از {N}\n"
            f"  id: {c['task_id']}\n"
            f"  عنوان اصلی: {c.get('title', '')}\n"
            f"  اولویت اصلی: {c.get('priority', 'medium')}\n"
            f"  وضعیت verify قبلی: {c.get('verification_status', 'pending')}\n"
            f"  فایل‌های دخیل: {_files}\n\n"
            "📋 acceptance_criteria کامل:\n"
            f"{_acs}\n\n"
            "📝 idea_prompt اصلی (بدون تغییر و بدون خلاصه‌سازی):\n"
            f"{c.get('idea_prompt', '')}\n\n"
            "✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):\n"
            f"{_completed}\n\n"
            "🔧 مراحل remaining که در super-task باید انجام شوند:\n"
            f"{_remaining}\n"
        )

    parts.append(
        "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 نکات استاندارد (همان bullet هایی که در ساخت پرامپت‌های معمولی "
        "پروژه رعایت می‌شود — وراثت کامل، نه کپی):\n"
        "- ساختار AC ها: acceptance_criteria با verify_method و verify_plan "
        "و evidence_locations برای هر AC\n"
        "- edge cases را در نظر بگیر و در پرامپت ذکر کن\n"
        "- وابستگی‌ها را اول حل کن (dependency-aware ordering)\n"
        "- اگر بخشی از یکی از تسک‌ها قبلاً done است (pre_done در بالا)، "
        "تکرار نکن — فقط روی remaining_parts تمرکز کن\n"
        f"- در commit message: `merged-from: {', '.join(c['task_id'] for c in sorted_src)}`\n"
        "- task_steps را با dependency-aware ordering مرتب کن\n"
        "- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود\n"
        "- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند\n"
    )
    return "".join(parts)


def _merge_acceptance_criteria(
    source_candidates: List[Dict[str, Any]],
) -> List[Any]:
    """union AC ها با dedup روی متن normalize شده."""
    seen: Set[str] = set()
    out: List[Any] = []
    for c in source_candidates:
        for ac in (c.get("acceptance_criteria") or []):
            _text = ""
            if isinstance(ac, str):
                _text = ac
            elif isinstance(ac, dict):
                _text = ac.get("text") or ""
            _key = _norm_token(_text)[:300]
            if not _key or _key in seen:
                continue
            seen.add(_key)
            out.append(ac)
    return out


# ────────────────────────────────────────────────────────────────────
# Phase 3: Intelligent Checklist (conditional)
# ────────────────────────────────────────────────────────────────────

async def _ai_build_checklist(
    super_title: str,
    merged_idea_prompt: str,
    verify_model_id: Optional[str],
) -> Optional[List[Dict[str, Any]]]:
    """یک checklist با ۵-۱۵ آیتم می‌سازد. None اگر AI ناموفق بود."""
    try:
        from .ai_manager import get_ai_manager
        from .ai_base import Message
    except Exception:
        return None

    if not verify_model_id:
        try:
            from ..core.models_registry import DEFAULT_EXTRACTION_MODEL_ID
            verify_model_id = DEFAULT_EXTRACTION_MODEL_ID
        except Exception:
            return None

    # برای جا کردن در context، idea_prompt را truncate موضعی می‌کنیم
    _truncated_idea = merged_idea_prompt
    if len(_truncated_idea) > 6000:
        _truncated_idea = _truncated_idea[:6000] + "\n... [truncated for checklist only]"

    prompt = (
        "برای super-task زیر یک checklist عملیاتی با ۵ تا ۱۵ آیتم بساز. "
        "هر آیتم یک کار ملموس و قابل tick زدن باشد، نه شعار کلی. "
        "اولویت‌بندی هوشمند انجام بده (پیش‌نیازها اول).\n\n"
        f"📌 عنوان: {super_title}\n\n"
        f"📝 شرح تلفیقی:\n{_truncated_idea}\n\n"
        "خروجی JSON خالص:\n"
        "{\n"
        '  "items": [\n'
        '    {"text": "...", "priority": "low|medium|high"},\n'
        '    ...\n'
        '  ]\n'
        "}"
    )

    try:
        mgr = get_ai_manager()
        resp = await asyncio.wait_for(
            mgr.generate(
                model_id=verify_model_id,
                messages=[Message(role="user", content=prompt)],
                max_tokens=1500,
                temperature=0.2,
                allow_fallback=True,
            ),
            timeout=_AI_CHECKLIST_TIMEOUT_S,
        )
        raw = (resp.content or "").strip()
    except asyncio.TimeoutError:
        return None
    except Exception as e:
        logger.warning(f"consolidation: checklist AI failed: {e}")
        return None

    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(raw[start : end + 1])
    except Exception:
        return None
    items_raw = (data or {}).get("items") or []
    if not isinstance(items_raw, list):
        return None
    out: List[Dict[str, Any]] = []
    for i, it in enumerate(items_raw[:15]):
        if not isinstance(it, dict):
            continue
        _text = str(it.get("text") or "").strip()
        if not _text:
            continue
        _prio = str(it.get("priority") or "medium").lower()
        if _prio not in ("low", "medium", "high"):
            _prio = "medium"
        out.append({
            "id": f"chk_{i + 1}",
            "text": _text[:400],
            "priority": _prio,
            "done": False,
        })
    return out if out else None


# ────────────────────────────────────────────────────────────────────
# Build & persist super-task
# ────────────────────────────────────────────────────────────────────

def _max_priority(candidates: List[Dict[str, Any]]) -> str:
    best = 9
    chosen = "medium"
    for c in candidates:
        p = (c.get("priority") or "medium").lower()
        r = _PRIORITY_RANK.get(p, 9)
        if r < best:
            best = r
            chosen = p
    return chosen


async def _build_super_task(
    cluster: Dict[str, Any],
    source_candidates: List[Dict[str, Any]],
    source_task_objs: List[Any],
    watched_obj: Any,
    verify_model_id: Optional[str],
    mode: str,
    service: Any,
) -> Optional[Any]:
    """یک super-task می‌سازد، آن را به service.tasks اضافه می‌کند،
    و source taskها را آرشیو می‌کند. خروجی: super-task object یا None."""
    if not source_candidates or not source_task_objs:
        return None

    # 🧬 ساخت idea_prompt تلفیقی
    merged_idea = _build_merged_idea_prompt(cluster, source_candidates)

    # 📝 task_steps via existing pipeline (bug 30 v2 chunking)
    super_title = (
        cluster.get("suggested_super_title")
        or f"تلفیق: {cluster.get('theme') or 'cluster'} ({len(source_candidates)} تسک)"
    )
    task_steps: List[Dict[str, Any]] = []
    try:
        if hasattr(service, "_ai_plan_steps_from_idea"):
            _steps = await service._ai_plan_steps_from_idea(
                idea=merged_idea,
                user_goal=super_title,
                model_id=verify_model_id,
            )
            if isinstance(_steps, list):
                task_steps = _steps
    except Exception as e:
        logger.warning(f"consolidation: planning steps failed: {e}")
        task_steps = []

    # ✅ pre_done marking — مراحلی که در همهٔ sourceها done بودند
    # (برای دقت بالا فقط مراحل با عنوان مشترک — keyed by normalized title)
    _all_done_titles: Set[str] = set()
    _any_remaining_titles: Set[str] = set()
    for c in source_candidates:
        for d in (c.get("completed_parts") or []):
            _all_done_titles.add(_norm_token(d.split(" — ", 1)[0]))
        for r in (c.get("remaining_parts") or []):
            _any_remaining_titles.add(_norm_token(r.split(" — ", 1)[0]))
    # یک step pre_done است اگر title آن در همهٔ done بود و در هیچ remaining نبود
    for s in task_steps:
        if not isinstance(s, dict):
            continue
        _t = _norm_token(s.get("title") or "")
        if _t and _t in _all_done_titles and _t not in _any_remaining_titles:
            s["pre_done"] = True
            s["status"] = s.get("status") or "done"

    # 📋 AC merge
    merged_acs = _merge_acceptance_criteria(source_candidates)

    # 🎯 priority / type
    super_priority = cluster.get("priority") or _max_priority(source_candidates)
    super_type = cluster.get("type") or "other"

    # 🏷 tags
    tag_set: Set[str] = set()
    for c in source_candidates:
        for t in (c.get("tags") or []):
            if isinstance(t, str) and t.strip():
                tag_set.add(t.strip())
    tag_set.update(["consolidated", "post_verify_merge"])
    merged_tags = sorted(tag_set)

    # 📸 snapshot کامل source ها برای undo
    snapshot: Dict[str, Any] = {}
    for t in source_task_objs:
        try:
            snapshot[getattr(t, "id", "?")] = asdict(t)
        except Exception:
            try:
                snapshot[getattr(t, "id", "?")] = t.to_dict()  # type: ignore[attr-defined]
            except Exception:
                continue

    # ساخت OversightTask
    try:
        from .oversight_service import OversightTask, now_iso
    except Exception as e:
        logger.error(f"consolidation: cannot import OversightTask: {e}")
        return None

    # یک id بساز که با pattern قبلی سازگار باشد
    import uuid as _uuid
    new_id = f"task_{_uuid.uuid4().hex[:12]}"

    # source و identifier — از source تسک‌ها inherit کن
    first_src = source_task_objs[0]
    watched_id = getattr(first_src, "watched_id", "") or getattr(watched_obj, "id", "")
    project_full_name = getattr(first_src, "project_full_name", "") or getattr(
        watched_obj, "repo_full_name", ""
    )

    consolidation_meta = {
        "cluster_theme": cluster.get("theme") or "",
        "rationale": cluster.get("rationale") or "",
        "created_during_bulk_verify_at": now_iso(),
        "mode": mode,
        "estimated_difficulty": cluster.get("estimated_difficulty") or "medium",
        "mixed_partial_and_not_done": bool(
            cluster.get("mixed_partial_and_not_done", False)
        ),
        "source_count": len(source_task_objs),
    }

    # 🆕 EXECUTOR_DISCLAIMER را به ابتدای prompt اضافه کن (super-tasks تا قبل
    # از این به‌صورت raw مستقیم prompt را می‌گذاشتند و disclaimer شامل
    # یادداشت‌های وابستگی‌ها و همگام‌سازی را از دست می‌دادند). idempotency check
    # سازگار با همان منطق idea_to_prompt و سایر مسیرهای تولید پرامپت است.
    try:
        from .oversight_strong_prompt import EXECUTOR_DISCLAIMER
        if "یادداشت مهم برای مدل اجراکننده" not in merged_idea[:500]:
            super_prompt = EXECUTOR_DISCLAIMER + "\n" + merged_idea
        else:
            super_prompt = merged_idea
    except Exception as _e:
        logger.debug(f"_build_super_task: EXECUTOR_DISCLAIMER prepend skipped: {_e}")
        super_prompt = merged_idea

    super_task = OversightTask(
        id=new_id,
        watched_id=watched_id,
        project_full_name=project_full_name,
        title=super_title[:200],
        prompt=super_prompt,
        raw_idea=merged_idea,
        type=super_type if super_type in (
            "idea", "bug", "feature_request", "refactor", "docs", "reminder", "other"
        ) else "other",
        priority=super_priority if super_priority in ("low", "medium", "high", "critical") else "medium",
        status="pending",
        source="auto_consolidation",
        tags=merged_tags,
        acceptance_criteria=merged_acs,
        task_steps=task_steps,
        verification_status="pending",
        merged_from=[c["task_id"] for c in source_candidates],
        merged_from_snapshot=snapshot,
        consolidation_meta=consolidation_meta,
    )

    # 🧠 checklist هوشمند (conditional)
    try:
        _ck_mode = (getattr(watched_obj, "auto_task_checklist_mode", "auto") or "auto").lower()
        _difficulty = (cluster.get("estimated_difficulty") or "medium").lower()
        _should_build = (
            _ck_mode != "never"
            and _difficulty in ("medium", "large")
            and len(source_task_objs) >= 3
        )
        if _ck_mode == "always":
            _should_build = True  # always overrides difficulty/count
        if _should_build:
            cl = await _ai_build_checklist(super_title, merged_idea, verify_model_id)
            if cl:
                super_task.intelligent_checklist = cl
    except Exception as e:
        logger.warning(f"consolidation: checklist build failed: {e}")

    # ➕ ثبت در service
    async with service._lock:
        service.tasks.append(super_task)

        # 🗄 آرشیو source ها
        archive_ts = now_iso()
        for t in source_task_objs:
            try:
                t.archived = True
                t.archived_at = archive_ts
                t.archive_reason = "merged_into_consolidated_task"
                t.merged_into = new_id
                _tags = list(getattr(t, "tags", None) or [])
                if "merged" not in _tags:
                    _tags.append("merged")
                t.tags = _tags
                t.updated_at = archive_ts
            except Exception as e:
                logger.warning(f"consolidation: archive failed for {getattr(t, 'id', '?')}: {e}")

        service._save_tasks()

    # 🆕 (C5 — بند ۱۱) — title re-assess برای super-task بعد از build
    # AI cluster ممکن است suggested_super_title generic داده باشد. این پاس
    # با AI سبک عنوان را بازنگری می‌کند (طبق همان منطق post-verify).
    try:
        if hasattr(service, "_ai_reassess_title"):
            await service._ai_reassess_title(
                super_task, triggered_by="consolidation",
                model_id=verify_model_id,
            )
    except Exception as e:
        logger.debug(f"consolidation: super-task title reassess failed: {e}")

    return super_task


# ────────────────────────────────────────────────────────────────────
# Public API: main entry
# ────────────────────────────────────────────────────────────────────

# lock module-level برای جلوگیری از concurrent
_CONSOLIDATION_LOCK = asyncio.Lock()


def _select_top_candidates(
    candidates: List[Dict[str, Any]],
    limit: int,
) -> List[Dict[str, Any]]:
    """اگر تعداد > limit، بر اساس priority انتخاب کن."""
    if len(candidates) <= limit:
        return candidates
    sorted_c = sorted(
        candidates,
        key=lambda c: _PRIORITY_RANK.get((c.get("priority") or "medium").lower(), 9),
    )
    return sorted_c[:limit]


async def consolidate_remaining_tasks(
    watched_id: str,
    candidates: List[Dict[str, Any]],
    *,
    mode: str,
    verify_model_id: Optional[str],
    live_preclusters: Optional[List[Dict[str, Any]]] = None,
    service: Any,
    state: Dict[str, Any],
) -> Dict[str, Any]:
    """نقطهٔ ورود اصلی consolidation.

    state: یک dict که caller برای reporting به‌روز می‌کند. این تابع
    آن را با کلیدهای زیر آپدیت می‌کند:
      enabled, ran, phase, candidates_count, live_pre_cluster_count,
      clusters_created, super_tasks_created, tasks_archived, ai_calls,
      error, started_at, finished_at
    """
    from .oversight_service import now_iso

    state.update({
        "enabled": True,
        "ran": False,
        "phase": "idle",
        "candidates_count": len(candidates),
        "live_pre_cluster_count": len(live_preclusters or []),
        "clusters_created": 0,
        "super_tasks_created": [],
        "tasks_archived": 0,
        "ai_calls": 0,
        "error": None,
        "started_at": now_iso(),
        "finished_at": None,
    })

    if len(candidates) < _MIN_CANDIDATES_TO_RUN:
        state["error"] = f"candidates < {_MIN_CANDIDATES_TO_RUN}, skipped"
        state["finished_at"] = now_iso()
        return state

    # cap
    if len(candidates) > _MAX_CANDIDATES:
        candidates = _select_top_candidates(candidates, _MAX_CANDIDATES)
        state["candidates_count"] = len(candidates)
        state["capped_to"] = _MAX_CANDIDATES

    # lock — اگر همزمان consolidation دیگری در حال اجراست، skip
    if _CONSOLIDATION_LOCK.locked():
        state["error"] = "another consolidation in progress"
        state["finished_at"] = now_iso()
        return state

    async with _CONSOLIDATION_LOCK:
        try:
            state["phase"] = "clustering"
            state["ran"] = True

            # AI clustering در batchها
            all_clusters: List[Dict[str, Any]] = []
            for i in range(0, len(candidates), _AI_CLUSTER_BATCH_SIZE):
                batch = candidates[i : i + _AI_CLUSTER_BATCH_SIZE]
                pre_hints = live_preclusters or []
                ai_result = await _ai_cluster_batch(batch, pre_hints, verify_model_id)
                state["ai_calls"] += 1
                if ai_result is None:
                    # fallback به mechanical فقط برای این batch
                    logger.warning(
                        "consolidation: AI failed on batch %d, fallback to mechanical",
                        i // _AI_CLUSTER_BATCH_SIZE,
                    )
                    _mech = mechanical_precluster(batch)
                    # تبدیل mechanical به فرمت AI cluster
                    for m in _mech:
                        all_clusters.append({
                            "cluster_id": m["cluster_id"],
                            "theme": f"mechanical:{m['kind']}",
                            "rationale": m.get("rationale", ""),
                            "task_ids": m["task_ids"],
                            "suggested_super_title": "",
                            "priority": "medium",
                            "type": "other",
                            "estimated_difficulty": "medium",
                            "mixed_partial_and_not_done": False,
                        })
                else:
                    batch_clusters, _ = _validate_clusters(
                        ai_result, batch
                    )
                    all_clusters.extend(batch_clusters)

            if not all_clusters:
                state["error"] = "no valid clusters formed"
                state["phase"] = "done"
                state["finished_at"] = now_iso()
                return state

            # global validation — جلوگیری از تکرار task_id بین batchها
            global_seen: Set[str] = set()
            deduped_clusters: List[Dict[str, Any]] = []
            for cl in all_clusters:
                _ids = [tid for tid in cl["task_ids"] if tid not in global_seen]
                if len(_ids) < _MIN_CLUSTER_SIZE:
                    continue
                for tid in _ids:
                    global_seen.add(tid)
                cl["task_ids"] = _ids
                deduped_clusters.append(cl)
            all_clusters = deduped_clusters

            state["clusters_created"] = len(all_clusters)
            state["phase"] = "building"

            # ساخت super-task ها
            candidate_by_id = {c["task_id"]: c for c in candidates}

            # دسترسی به watched
            watched_obj = None
            try:
                watched_obj = service._find_watched(watched_id)
            except Exception:
                pass

            # تسک‌های زنده برای آرشیو
            tasks_by_id = {t.id: t for t in service.tasks}

            # 🐛 (C4 fix) — هر cluster در try/except جداگانه ساخته می‌شود تا
            # یک خطا در یکی، بقیه را نشکند. قبلاً یک bug در _format_ac کل
            # ۲۳ cluster را با هم خراب می‌کرد.
            cluster_failures: List[str] = []
            for cl_idx, cl in enumerate(all_clusters):
                try:
                    src_cands = [
                        candidate_by_id[tid] for tid in cl["task_ids"]
                        if tid in candidate_by_id
                    ]
                    src_objs = [
                        tasks_by_id[tid] for tid in cl["task_ids"]
                        if tid in tasks_by_id and not getattr(tasks_by_id[tid], "archived", False)
                    ]
                    if len(src_objs) < _MIN_CLUSTER_SIZE:
                        continue
                    # 🛡 ایمنی: فقط تسک‌های done-نشده آرشیو شوند
                    src_objs = [
                        t for t in src_objs
                        if (getattr(t, "verification_status", "pending") or "pending").lower() != "done"
                    ]
                    if len(src_objs) < _MIN_CLUSTER_SIZE:
                        continue
                    # 🛡 ایمنی: فقط source = auto_scan
                    src_objs = [
                        t for t in src_objs
                        if (getattr(t, "source", "user") or "user").lower() == "auto_scan"
                    ]
                    if len(src_objs) < _MIN_CLUSTER_SIZE:
                        continue
                    # کاندیدهای مرتبط را هم به همان لیست تسک‌های آرشیو می‌رسانیم
                    src_ids_final = {t.id for t in src_objs}
                    src_cands_filtered = [c for c in src_cands if c["task_id"] in src_ids_final]
                    super_task = await _build_super_task(
                        cluster=cl,
                        source_candidates=src_cands_filtered,
                        source_task_objs=src_objs,
                        watched_obj=watched_obj,
                        verify_model_id=verify_model_id,
                        mode=mode,
                        service=service,
                    )
                    if super_task is not None:
                        state["super_tasks_created"].append(super_task.id)
                        state["tasks_archived"] += len(src_objs)
                except Exception as _cl_e:
                    _cid = cl.get("cluster_id", f"#{cl_idx}")
                    _msg = f"cluster {_cid}: {type(_cl_e).__name__}: {str(_cl_e)[:200]}"
                    cluster_failures.append(_msg)
                    logger.exception(f"consolidation: cluster build failed — {_msg}")
                    continue

            if cluster_failures:
                state["cluster_failures"] = cluster_failures[:20]  # حداکثر 20 نگه دار

            state["phase"] = "done"
        except Exception as e:
            logger.exception(f"consolidation: unexpected error: {e}")
            state["error"] = str(e)[:500]
            state["phase"] = "done"
        finally:
            state["finished_at"] = now_iso()

    return state


# ────────────────────────────────────────────────────────────────────
# Undo (unmerge)
# ────────────────────────────────────────────────────────────────────

async def unmerge_super_task(super_task_id: str, service: Any) -> Dict[str, Any]:
    """آرشیو معکوس: super-task آرشیو می‌شود و source ها از snapshot
    به حالت قبل (archived=False, merged_into=None) برمی‌گردند.

    خروجی: {ok, restored: [...], error?}
    """
    from .oversight_service import now_iso

    super_task = next((t for t in service.tasks if t.id == super_task_id), None)
    if super_task is None:
        return {"ok": False, "error": "super-task not found"}
    if (getattr(super_task, "source", "") or "").lower() != "auto_consolidation":
        return {"ok": False, "error": "not a consolidated super-task"}
    snapshot = getattr(super_task, "merged_from_snapshot", None) or {}
    if not snapshot:
        return {"ok": False, "error": "no snapshot — cannot undo"}

    restored: List[str] = []
    async with service._lock:
        tasks_by_id = {t.id: t for t in service.tasks}
        ts = now_iso()
        for src_id, snap in snapshot.items():
            t = tasks_by_id.get(src_id)
            if t is None:
                # ممکن است حذف شده باشد — skip
                continue
            try:
                # بازگرداندن از آرشیو
                t.archived = False
                t.archived_at = None
                t.archive_reason = None
                t.merged_into = None
                _tags = list(getattr(t, "tags", None) or [])
                if "merged" in _tags:
                    _tags = [x for x in _tags if x != "merged"]
                t.tags = _tags
                t.updated_at = ts
                restored.append(src_id)
            except Exception as e:
                logger.warning(f"unmerge: failed for {src_id}: {e}")

        # آرشیو super-task
        super_task.archived = True
        super_task.archived_at = ts
        super_task.archive_reason = "unmerged_by_user"
        super_task.updated_at = ts

        service._save_tasks()

    return {"ok": True, "restored": restored, "super_task_id": super_task_id}
