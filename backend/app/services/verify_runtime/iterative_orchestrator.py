"""Verify v6 — iterative_orchestrator

Iterative refinement با ۳ سطح (standard probes → aggressive content grep →
strong model escalation) با confidence-weighted aggregate.

طبق Bug C6 v2 — گپ ۴ (Iterative orchestrator) + گپ ۶ (Confidence-weighted
verdict) + کاستی ۲ (Model escalation tier صریح).
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .context_builder import VerifyContext

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ProbeResult
# ---------------------------------------------------------------------------


@dataclass
class ProbeResult:
    """نتیجهٔ یک probe (یا یک aggregate)."""
    probe_name: str
    verdict: str  # "done" | "partial" | "not_done" | "unclear"
    confidence: float  # 0.0..1.0
    evidence: List[str] = field(default_factory=list)
    error: Optional[str] = None
    elapsed_ms: int = 0


_VALID_VERDICTS = {"done", "partial", "not_done", "unclear"}


# ---------------------------------------------------------------------------
# WEIGHTS_BY_PROBE — گپ ۶
# ---------------------------------------------------------------------------


WEIGHTS_BY_PROBE: Dict[str, float] = {
    "content_grep_strong": 3.0,  # ≥۲ identifier در ≥۱ فایل
    "content_grep_weak": 1.5,    # ۱ identifier
    "code_aware_basename": 1.0,  # فقط basename match
    "playwright": 2.0,           # deterministic
    "ai_verifier": 1.0,
    "vision_frontend": 0.5,
    "vision_backend": 0.0,       # vision در backend = weight 0
    "strong_model": 2.5,         # iteration 3
}


def _get_weight(r: ProbeResult, weights: Optional[Dict[str, float]] = None) -> float:
    """دریافت وزن probe بر اساس نام (یا weights override از config)."""
    w = weights if isinstance(weights, dict) else WEIGHTS_BY_PROBE
    return float(w.get(r.probe_name, 1.0))


# ---------------------------------------------------------------------------
# aggregate_verdicts — confidence-weighted vote
# ---------------------------------------------------------------------------


def aggregate_verdicts(
    results: List[ProbeResult],
    *,
    weights: Optional[Dict[str, float]] = None,
) -> ProbeResult:
    """رأی‌گیری وزنی روی نتایج چند probe.

    - حذف unclear و error
    - score هر verdict = sum(weight × confidence)
    - winner = verdict با بیشترین score
    - final_confidence = score_winner / total_weight
    - evidence جمع‌آوری از probeهای winner (cap 10)
    """
    valid = [
        r for r in results
        if isinstance(r, ProbeResult)
        and r.verdict in ("done", "partial", "not_done")
        and not r.error
    ]
    if not valid:
        return ProbeResult(
            probe_name="aggregate",
            verdict="unclear",
            confidence=0.0,
            evidence=["all probes inconclusive"],
        )

    scores: Dict[str, float] = {"done": 0.0, "partial": 0.0, "not_done": 0.0}
    total_weight = 0.0
    for r in valid:
        w = _get_weight(r, weights) * max(0.0, min(1.0, r.confidence))
        scores[r.verdict] = scores.get(r.verdict, 0.0) + w
        total_weight += w

    winner = max(scores, key=lambda k: scores[k])
    final_conf = (scores[winner] / total_weight) if total_weight > 0 else 0.0
    evidence: List[str] = []
    for r in valid:
        if r.verdict == winner:
            evidence.extend(r.evidence or [])

    return ProbeResult(
        probe_name="aggregate",
        verdict=winner,
        confidence=round(final_conf, 4),
        evidence=evidence[:10],
    )


# ---------------------------------------------------------------------------
# Model availability check (برای strong model escalation)
# ---------------------------------------------------------------------------


def _model_available(model_id: str) -> bool:
    """بررسی موجود بودن model در MODEL_REGISTRY و معتبر بودن API key.

    اگر models_registry وجود نداشت یا check نتوانست انجام شود، False
    برمی‌گردد (graceful — caller fallback خواهد کرد).
    """
    if not model_id:
        return False
    try:
        from ...core import models_registry  # type: ignore
    except Exception:
        return False
    registry = getattr(models_registry, "MODEL_REGISTRY", None)
    if not isinstance(registry, dict):
        return False
    if model_id not in registry:
        return False
    # api key check
    info = registry.get(model_id) or {}
    provider = info.get("provider") if isinstance(info, dict) else None
    if not provider:
        return True
    # ساده‌ترین چک: env var با نام PROVIDER_API_KEY
    import os
    env_var = f"{str(provider).upper().replace('-', '_')}_API_KEY"
    return bool(os.environ.get(env_var, "").strip())


# ---------------------------------------------------------------------------
# _strong_model_judgment — Iteration 3 (کاستی ۲ — Model escalation tier صریح)
# ---------------------------------------------------------------------------


async def _strong_model_judgment(
    ac: Dict[str, Any],
    context: "VerifyContext",
    prior_results: List[ProbeResult],
) -> ProbeResult:
    """استفاده از model tier بالاتر برای judgment نهایی iteration 3.

    chain:
    1. تلاش با "gpt-4o" (اگر در MODEL_REGISTRY و key موجود)
    2. fallback به "claude-opus-4-7" یا "claude-sonnet-4-6"
    3. fallback به DEFAULT_EXTRACTION_MODEL_ID (no escalation possible —
       با warning log، fail نمی‌کند)

    خروجی همیشه یک ProbeResult با probe_name="strong_model".
    """
    start = time.monotonic()
    strong_pref = list(context.config.strong_model_preference) if context.config else [
        "gpt-4o", "claude-opus-4-7", "claude-sonnet-4-6",
    ]

    model_id: Optional[str] = None
    for cand in strong_pref:
        if _model_available(cand):
            model_id = cand
            break

    fallback_used = False
    if not model_id:
        try:
            from ...core.models_registry import pick_best_extraction_model
            model_id = pick_best_extraction_model()
            fallback_used = True
        except Exception:
            model_id = None

    if not model_id:
        logger.warning(
            "_strong_model_judgment: no strong model available and no fallback — "
            "returning unclear (edge case v2: strong model unavailable)"
        )
        return ProbeResult(
            probe_name="strong_model",
            verdict="unclear",
            confidence=0.0,
            evidence=["no strong model available"],
            elapsed_ms=int((time.monotonic() - start) * 1000),
        )

    # ساخت prompt با ورودی‌های کامل
    ac_text = str(ac.get("text", "") if isinstance(ac, dict) else ac)
    prompt_parts: List[str] = []
    prompt_parts.append("شما در حال قضاوت نهایی یک AC (Acceptance Criterion) هستید.")
    prompt_parts.append(f"AC: {ac_text}")

    # evidence از iterations قبل
    if prior_results:
        prompt_parts.append("\nشواهد از iterations قبل:")
        for i, r in enumerate(prior_results[:20], 1):
            prompt_parts.append(
                f"  [{i}] probe={r.probe_name} verdict={r.verdict} "
                f"confidence={r.confidence:.2f}"
            )
            for ev in (r.evidence or [])[:3]:
                prompt_parts.append(f"      - {ev[:200]}")

    # file snippets cap 50KB
    snippets: List[str] = []
    total_size = 0
    for key, content in (context.file_content_cache or {}).items():
        if total_size >= 50_000:
            break
        snippet = content[:5000]
        snippets.append(f"--- {key} ---\n{snippet}")
        total_size += len(snippet)
    if snippets:
        prompt_parts.append("\nfile content snippets:")
        prompt_parts.append("\n".join(snippets)[:50_000])

    # repo_tree subset مرتبط (cap 500 path)
    if context.repo_tree:
        prompt_parts.append("\nrepo_tree (subset):")
        prompt_parts.append("\n".join(context.repo_tree[:500]))

    # task.prompt full cap 50KB
    if context.prompt_full:
        prompt_parts.append("\ntask.prompt:")
        prompt_parts.append(context.prompt_full[:50_000])

    prompt_parts.append(
        "\nبا توجه به شواهد بالا، verdict نهایی برای این AC چیست؟\n"
        "خروجی فقط JSON: {\"verdict\": \"done|partial|not_done\", "
        "\"confidence\": 0.0..1.0, \"reason\": \"...\"}"
    )

    full_prompt = "\n".join(prompt_parts)
    context.ai_calls_count += 1

    # فراخوانی AI
    verdict = "unclear"
    confidence = 0.0
    reason = ""
    try:
        from ..ai_manager import ai_manager
        resp = await ai_manager.generate(
            model_id=model_id,
            prompt=full_prompt,
            max_tokens=600,
            temperature=0.2,
        )
        text = (resp or {}).get("text", "") if isinstance(resp, dict) else str(resp or "")
        # parse JSON
        import re as _re, json as _json
        m = _re.search(r"\{[^{}]*\"verdict\"[^{}]*\}", text, _re.DOTALL)
        if m:
            try:
                parsed = _json.loads(m.group(0))
                v = str(parsed.get("verdict", "")).lower().strip()
                if v in {"done", "partial", "not_done"}:
                    verdict = v
                c = parsed.get("confidence", 0.0)
                if isinstance(c, (int, float)):
                    confidence = max(0.0, min(1.0, float(c)))
                reason = str(parsed.get("reason", ""))[:300]
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"_strong_model_judgment AI call failed: {e}")
        return ProbeResult(
            probe_name="strong_model",
            verdict="unclear",
            confidence=0.0,
            evidence=[f"AI call failed: {e}"],
            error=str(e),
            elapsed_ms=int((time.monotonic() - start) * 1000),
        )

    note = f" (fallback model)" if fallback_used else ""
    return ProbeResult(
        probe_name="strong_model",
        verdict=verdict,
        confidence=confidence,
        evidence=[f"strong_model={model_id}{note}", reason] if reason else [f"strong_model={model_id}{note}"],
        elapsed_ms=int((time.monotonic() - start) * 1000),
    )


# ---------------------------------------------------------------------------
# iterative_verify_step — entry-point برای یک AC/step
# ---------------------------------------------------------------------------


async def iterative_verify_step(
    step: Dict[str, Any],
    context: "VerifyContext",
    *,
    max_iterations: int = 3,
) -> Tuple[ProbeResult, List[ProbeResult]]:
    """اعتبارسنجی iterative یک AC/step با ۳ سطح.

    خروجی: (final_aggregated_result, all_iteration_results)

    - Iteration 1 (~5-10s): vision (frontend/fullstack), code_aware,
      content_grep, playwright (if URL). آستانه 0.8
    - Iteration 2 (~15-30s): aggressive content_grep با scope گسترش‌یافته
      و top-25 identifiers + AI rerun. آستانه 0.7
    - Iteration 3 (~30-60s): _strong_model_judgment با full context.
      finalize unconditionally (max 3).
    """
    cfg = context.config
    max_iter = min(max(1, max_iterations), cfg.max_iterations if cfg else 3)
    all_results: List[ProbeResult] = []

    # ---- Iteration 1 ----
    iter1_probes = await _run_iteration_1(step, context)
    all_results.extend(iter1_probes)
    weights = cfg.weights if cfg else None
    agg1 = aggregate_verdicts(iter1_probes, weights=weights)
    context.append_trace({
        "phase": "iteration_1_aggregate",
        "verdict": agg1.verdict,
        "confidence": agg1.confidence,
        "probe_count": len(iter1_probes),
    })
    threshold1 = cfg.iter1_confidence_threshold if cfg else 0.8
    if agg1.confidence >= threshold1:
        context.append_trace({
            "phase": "finalize",
            "iteration": 1,
            "reason": f"confidence {agg1.confidence:.2f} >= {threshold1}",
        })
        return agg1, all_results

    if max_iter < 2:
        return agg1, all_results

    # ---- Iteration 2 ----
    iter2_probes = await _run_iteration_2(step, context, iter1_probes)
    all_results.extend(iter2_probes)
    agg2 = aggregate_verdicts(iter1_probes + iter2_probes, weights=weights)
    context.append_trace({
        "phase": "iteration_2_aggregate",
        "verdict": agg2.verdict,
        "confidence": agg2.confidence,
        "probe_count_new": len(iter2_probes),
    })
    threshold2 = cfg.iter2_confidence_threshold if cfg else 0.7
    if agg2.confidence >= threshold2:
        context.append_trace({
            "phase": "finalize",
            "iteration": 2,
            "reason": f"confidence {agg2.confidence:.2f} >= {threshold2}",
        })
        return agg2, all_results

    if max_iter < 3:
        return agg2, all_results

    # ---- Iteration 3: strong model ----
    iter3 = await _strong_model_judgment(step, context, all_results)
    all_results.append(iter3)
    # combine strong_model with prior (همان وزن‌ها)
    agg3 = aggregate_verdicts(all_results, weights=weights)
    context.append_trace({
        "phase": "iteration_3_strong_model",
        "verdict": agg3.verdict,
        "confidence": agg3.confidence,
    })
    return agg3, all_results


# ---------------------------------------------------------------------------
# Iteration helpers
# ---------------------------------------------------------------------------


async def _run_iteration_1(
    step: Dict[str, Any], context: "VerifyContext"
) -> List[ProbeResult]:
    """iteration 1: standard probes.

    این تابع به‌جای صدا زدن probe های واقعی (Playwright/vision سنگین)،
    یک signal سبک می‌سازد از روی state موجود — content_grep از روی
    cache، code_aware از روی target_files basename match. probe های
    وقت‌گیر در runner.py اصلی (که integration بعداً اتفاق می‌افتد) صدا
    زده می‌شوند.
    """
    results: List[ProbeResult] = []
    start = time.monotonic()
    try:
        from .code_content_searcher import smart_grep_for_ac, extract_identifiers
    except Exception:
        return results

    task = context.task
    repo_full_name = ""
    if context.watched is not None:
        repo_full_name = getattr(context.watched, "repo_full_name", "") or ""
    if not repo_full_name:
        repo_full_name = getattr(task, "project_full_name", "") or ""
    target_files = list(getattr(task, "target_files", None) or [])
    branch = (getattr(context.watched, "default_branch", None) or "main") if context.watched else "main"

    ac_text = str(step.get("text", "") if isinstance(step, dict) else step)
    if not ac_text:
        return results

    # content_grep probe
    if repo_full_name and target_files and context.config.enable_content_grep:
        try:
            grep_out = await smart_grep_for_ac(
                ac_text, target_files, repo_full_name, branch, context=context,
            )
            num_idents = len(grep_out)
            files_with_match: set = set()
            for matches in grep_out.values():
                for m in matches:
                    files_with_match.add(m.get("path", ""))
            if num_idents >= 2 and len(files_with_match) >= 1:
                probe_name = "content_grep_strong"
                verdict = "done"
                confidence = 0.85
            elif num_idents == 1:
                probe_name = "content_grep_weak"
                verdict = "partial"
                confidence = 0.55
            else:
                probe_name = "content_grep_weak"
                verdict = "not_done"
                confidence = 0.5
            results.append(ProbeResult(
                probe_name=probe_name,
                verdict=verdict,
                confidence=confidence,
                evidence=[
                    f"identifiers matched: {num_idents}",
                    f"files with match: {sorted(files_with_match)[:5]}",
                ],
                elapsed_ms=int((time.monotonic() - start) * 1000),
            ))
        except Exception as e:
            results.append(ProbeResult(
                probe_name="content_grep_weak",
                verdict="unclear",
                confidence=0.0,
                error=str(e),
            ))

    # code_aware probe (basename match سبک)
    identifiers = extract_identifiers(ac_text)
    basename_hits = 0
    for path in target_files[:20]:
        base = path.rsplit("/", 1)[-1].rsplit(".", 1)[0].lower()
        for ident in identifiers:
            if ident.lower() in base:
                basename_hits += 1
                break
    if target_files:
        verdict = "done" if basename_hits >= 1 else "not_done"
        confidence = 0.6 if basename_hits >= 1 else 0.4
        results.append(ProbeResult(
            probe_name="code_aware_basename",
            verdict=verdict,
            confidence=confidence,
            evidence=[f"basename hits: {basename_hits}/{len(target_files)}"],
        ))

    return results


async def _run_iteration_2(
    step: Dict[str, Any],
    context: "VerifyContext",
    prior: List[ProbeResult],
) -> List[ProbeResult]:
    """iteration 2: aggressive content grep + AI rerun.

    - file scope گسترش می‌یابد: full repo_tree با filter به:
      1) extensions مرتبط (py/tsx/ts/jsx/js)
      2) paths که با AC text overlap دارند (folder name)
      3) cap: iter2_max_extra_files (default 50)
    - top-K identifiers بالاتر (iter2_max_identifiers default 25)
    - AI rerun را به strong_model_judgment محول می‌کنیم (iter 3 از این
      نتیجه استفاده می‌کند)
    """
    results: List[ProbeResult] = []
    start = time.monotonic()
    try:
        from .code_content_searcher import smart_grep_for_ac, grep_token_in_files, extract_identifiers
    except Exception:
        return results

    cfg = context.config
    task = context.task
    repo_full_name = ""
    if context.watched is not None:
        repo_full_name = getattr(context.watched, "repo_full_name", "") or ""
    if not repo_full_name:
        repo_full_name = getattr(task, "project_full_name", "") or ""
    branch = (getattr(context.watched, "default_branch", None) or "main") if context.watched else "main"

    ac_text = str(step.get("text", "") if isinstance(step, dict) else step)
    if not ac_text or not repo_full_name:
        return results

    # گسترش file scope
    relevant_exts = (".py", ".tsx", ".ts", ".jsx", ".js")
    extended_files: List[str] = []
    target_set = set(getattr(task, "target_files", None) or [])
    ac_lower = ac_text.lower()
    # extract folder/path hints from AC text
    import re as _re
    path_hints = set(m.group(1).lower() for m in _re.finditer(r"\b([a-z_][\w/]*)/", ac_lower))

    for path in context.repo_tree:
        if path in target_set:
            continue
        if not path.endswith(relevant_exts):
            continue
        plower = path.lower()
        overlap_score = 0
        for hint in path_hints:
            if hint and hint in plower:
                overlap_score += 1
        # هم extension مرتبط + هم overlap (یا حداقل extension مرتبط)
        if overlap_score > 0:
            extended_files.append(path)
        elif len(extended_files) < (cfg.iter2_max_extra_files // 2 if cfg else 25):
            extended_files.append(path)
        if len(extended_files) >= (cfg.iter2_max_extra_files if cfg else 50):
            break

    if not extended_files:
        return results

    # top-K identifiers بالاتر
    top_k = cfg.iter2_max_identifiers if cfg else 25
    identifiers = extract_identifiers(ac_text)[:top_k]
    if not identifiers:
        return results

    try:
        from ..github_storage import get_github_token
        github_token = get_github_token() or ""
    except Exception:
        github_token = ""

    matched_idents = 0
    matched_files: set = set()
    for ident in identifiers:
        matches = await grep_token_in_files(
            ident,
            extended_files,
            repo_full_name,
            branch,
            github_token=github_token,
            cache=context.file_grep_cache,
            file_content_cache=context.file_content_cache,
        )
        context.grep_calls_count += 1
        if matches:
            matched_idents += 1
            for m in matches[:5]:
                matched_files.add(m.get("path", ""))

    if matched_idents >= 2:
        verdict = "done"
        confidence = 0.75
        probe_name = "content_grep_strong"
    elif matched_idents == 1:
        verdict = "partial"
        confidence = 0.55
        probe_name = "content_grep_weak"
    else:
        verdict = "not_done"
        confidence = 0.5
        probe_name = "content_grep_weak"

    results.append(ProbeResult(
        probe_name=probe_name,
        verdict=verdict,
        confidence=confidence,
        evidence=[
            f"iter2 extended scope: {len(extended_files)} files",
            f"iter2 identifiers matched: {matched_idents}/{len(identifiers)}",
            f"matched files: {sorted(matched_files)[:5]}",
        ],
        elapsed_ms=int((time.monotonic() - start) * 1000),
    ))
    return results


__all__ = [
    "ProbeResult",
    "WEIGHTS_BY_PROBE",
    "aggregate_verdicts",
    "iterative_verify_step",
    "_strong_model_judgment",
]
