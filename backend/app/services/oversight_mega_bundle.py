"""Phase 2 — ساخت یک فایل HTML/PDF کامل از همه‌ی اطلاعات verify.

این فایل برای ارسال به‌عنوان ضمیمه‌ی تلگرام استفاده می‌شود تا کاربر
بتواند در یک پیوست واحد به همه‌ی اطلاعات تسک و آخرین verify دسترسی
داشته باشد: raw_idea + checklist + steps + prompt قدیم/جدید +
شواهد همه‌ی probe ها + console logs + backend URLs و logs +
analyses.

دو تابع:
- build_mega_bundle_md(task, report) -> bytes (HTML)
- build_mega_bundle_pdf(task, report) -> (bytes, ext) — PDF با
  fallback به HTML اگر playwright در دسترس نباشد.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# سقف اندازه‌ی نهایی (به byte) — اگر بیشتر شد، trim می‌کنیم
_MAX_SIZE_BYTES = 1_000_000  # 1MB


def _safe_str(v: Any, limit: int = 500) -> str:
    """تبدیل ایمن به str با cap."""
    try:
        s = str(v) if v is not None else ""
    except Exception:
        s = "<unstringable>"
    if limit and len(s) > limit:
        return s[:limit] + "…"
    return s


def _md_section(title: str, body: str) -> str:
    return f"\n## {title}\n\n{body}\n"


def _md_code_block(content: str, lang: str = "") -> str:
    return f"```{lang}\n{content}\n```"


def _fmt_iso(value: Any) -> str:
    if not value:
        return "—"
    try:
        s = str(value)
        # cut microseconds for readability
        if "T" in s and "." in s:
            base, _ = s.split(".", 1)
            return base.replace("T", " ")
        return s.replace("T", " ")[:20]
    except Exception:
        return _safe_str(value, 30)


def build_mega_bundle_md(task: Any, report: Any) -> bytes:
    """ساخت فایل HTML از task + report (نام تابع برای backward-compat حفظ شده).

    خروجی HTML با UTF-8 BOM + RTL + lang="fa" تا روی موبایل/مرورگر تلگرام
    فارسی درست رندر شود (نه mojibake). محتوای مارک‌داون داخل <pre> با
    styling مناسب نمایش داده می‌شود.

    Args:
      task: OversightTask
      report: OversightReport

    Returns:
      bytes (UTF-8 encoded HTML with BOM)
    """
    parts: List[str] = []

    # --- header ---
    title = _safe_str(getattr(task, "title", "") or getattr(task, "id", "task"), 120)
    parts.append(f"# 📦 Bundle کامل — {title}\n")
    parts.append(
        f"_فایل تولیدشده در: {datetime.now(timezone.utc).isoformat()}_\n"
    )

    # --- 1) شناسه‌ی تسک ---
    try:
        identity_rows = [
            f"- **id:** `{_safe_str(getattr(task, 'id', ''), 64)}`",
            f"- **project:** {_safe_str(getattr(task, 'project_full_name', ''), 100)}",
            f"- **watched_id:** {_safe_str(getattr(task, 'watched_id', ''), 64)}",
            f"- **type:** {_safe_str(getattr(task, 'type', ''), 30)}",
            f"- **priority:** {_safe_str(getattr(task, 'priority', ''), 30)}",
            f"- **status:** {_safe_str(getattr(task, 'status', ''), 30)}",
            f"- **verification_status:** {_safe_str(getattr(task, 'verification_status', ''), 30)}",
            f"- **last_verified_at:** {_fmt_iso(getattr(task, 'last_verified_at', None))}",
            f"- **followup_round:** {_safe_str(getattr(task, 'followup_round', 0), 10)}",
            f"- **source:** {_safe_str(getattr(task, 'source', ''), 30)}",
            f"- **execution_mode:** {_safe_str(getattr(task, 'execution_mode', ''), 30)}",
            f"- **runs_count:** {_safe_str(getattr(task, 'runs_count', 0), 10)}",
            f"- **created_at:** {_fmt_iso(getattr(task, 'created_at', None))}",
            f"- **updated_at:** {_fmt_iso(getattr(task, 'updated_at', None))}",
        ]
        parts.append(_md_section("۱. شناسه‌ی تسک", "\n".join(identity_rows)))
    except Exception as e:
        logger.debug(f"mega_bundle identity failed: {e}")

    # --- 2) raw_idea ---
    try:
        raw = _safe_str(getattr(task, "raw_idea", "") or "", 10000)
        if raw.strip():
            parts.append(_md_section(
                "۲. ایده‌ی خام (raw_idea)",
                _md_code_block(raw)
            ))
    except Exception as e:
        logger.debug(f"mega_bundle raw_idea failed: {e}")

    # --- 3) acceptance_criteria checklist ---
    try:
        acs = list(getattr(task, "acceptance_criteria", None) or [])
        if acs:
            ac_lines = []
            for i, ac in enumerate(acs):
                if isinstance(ac, dict):
                    text = _safe_str(ac.get("text") or "", 300)
                    method = _safe_str(ac.get("verify_method") or "static", 30)
                    last = _safe_str(ac.get("last_status") or "—", 20)
                    emoji = {"passed": "✅", "failed": "❌", "error": "⚠️",
                             "skipped": "⏭", "—": "·"}.get(last, "·")
                    ac_lines.append(f"- {emoji} **[{method}]** «{text}» — last: `{last}`")
                else:
                    ac_lines.append(f"- · «{_safe_str(ac, 300)}»")
            parts.append(_md_section(
                f"۳. چک‌لیست acceptance_criteria ({len(acs)})",
                "\n".join(ac_lines)
            ))
    except Exception as e:
        logger.debug(f"mega_bundle ACs failed: {e}")

    # --- 4) task_steps ---
    try:
        steps = list(getattr(task, "task_steps", None) or [])
        if steps:
            step_lines = ["| # | عنوان | وضعیت | % | scope |", "|---|---|---|---|---|"]
            for s in steps:
                if not isinstance(s, dict):
                    continue
                sid = _safe_str(s.get("id", ""), 5)
                stitle = _safe_str(s.get("title", ""), 80).replace("|", "/")
                sstatus = _safe_str(s.get("status", ""), 20)
                scomp = _safe_str(s.get("completion_pct", ""), 5)
                sscope = _safe_str(s.get("scope", ""), 100).replace("|", "/")
                step_lines.append(f"| {sid} | {stitle} | {sstatus} | {scomp} | {sscope} |")
            parts.append(_md_section(f"۴. مراحل (task_steps) — {len(steps)}", "\n".join(step_lines)))
    except Exception as e:
        logger.debug(f"mega_bundle steps failed: {e}")

    # --- 5) prompt فعلی ---
    try:
        prompt_now = _safe_str(getattr(task, "prompt", "") or "", 30000)
        history = getattr(task, "prompt_history", None) or []
        version_label = f"نسخه #{len(history) + 1}" if history else "نسخه‌ی فعلی"
        parts.append(_md_section(
            f"۵. پرامپت فعلی ({version_label})",
            _md_code_block(prompt_now)
        ))
    except Exception as e:
        logger.debug(f"mega_bundle current prompt failed: {e}")

    # --- 6) تاریخچه‌ی پرامپت‌ها ---
    try:
        history = list(getattr(task, "prompt_history", None) or [])
        if history:
            hist_parts: List[str] = []
            # newest archived first
            for i, h in enumerate(reversed(history)):
                if not isinstance(h, dict):
                    continue
                ridx = len(history) - i
                reason = _safe_str(h.get("reason", ""), 30)
                archived = _fmt_iso(h.get("archived_at"))
                status_at = _safe_str(h.get("verify_status_at_archive", ""), 30)
                round_n = _safe_str(h.get("round", 0), 5)
                old_prompt = _safe_str(h.get("prompt", ""), 30000)
                hist_parts.append(
                    f"### نسخه #{ridx} — {reason}\n\n"
                    f"- بایگانی: {archived}\n"
                    f"- وضعیت آن لحظه: `{status_at}`\n"
                    f"- round: {round_n}\n\n"
                    + _md_code_block(old_prompt)
                )
            parts.append(_md_section(
                f"۶. تاریخچه‌ی پرامپت‌ها ({len(history)})",
                "\n\n".join(hist_parts)
            ))
    except Exception as e:
        logger.debug(f"mega_bundle history failed: {e}")

    # --- 7) report فعلی ---
    try:
        report_lines = [
            f"- **status:** `{_safe_str(getattr(report, 'status', ''), 20)}`",
            f"- **confidence_score:** {_safe_str(getattr(report, 'confidence_score', 0), 10)}",
            f"- **run_at:** {_fmt_iso(getattr(report, 'run_at', None))}",
            f"- **model_id:** {_safe_str(getattr(report, 'model_id', ''), 50)}",
        ]
        done = list(getattr(report, "done_parts", None) or [])
        remaining = list(getattr(report, "remaining_parts", None) or [])
        next_actions = list(getattr(report, "next_actions", None) or [])
        if done:
            report_lines.append(f"\n**✅ انجام‌شده ({len(done)}):**")
            # 🆕 (bug 30 v3) — cap به ۲۰۰ بالا برد تا برای تسک‌های بزرگ هم
            # همهٔ موارد در گزارش بیایند
            for d in done[:200]:
                report_lines.append(f"- {_safe_str(d, 300)}")
        if remaining:
            report_lines.append(f"\n**⏳ باقی‌مانده ({len(remaining)}):**")
            for d in remaining[:200]:
                report_lines.append(f"- {_safe_str(d, 300)}")
        if next_actions:
            report_lines.append(f"\n**🪜 اقدامات بعدی ({len(next_actions)}):**")
            for d in next_actions[:200]:
                report_lines.append(f"- {_safe_str(d, 300)}")
        # summary اگر در evidence هست
        ev = getattr(report, "evidence", None) or {}
        if isinstance(ev, dict) and ev.get("summary"):
            report_lines.append(f"\n**📝 خلاصه:** {_safe_str(ev['summary'], 1500)}")
        parts.append(_md_section("۷. گزارش verify فعلی", "\n".join(report_lines)))
    except Exception as e:
        logger.debug(f"mega_bundle report failed: {e}")

    # --- 8) runtime probes (دانه‌ی به دانه) ---
    try:
        ev = getattr(report, "evidence", None) or {}
        probes = ev.get("runtime_probes", []) if isinstance(ev, dict) else []
        if isinstance(probes, list) and probes:
            probe_parts: List[str] = []
            for idx, p in enumerate(probes, start=1):
                if not isinstance(p, dict):
                    continue
                method = _safe_str(p.get("method", ""), 30)
                status = _safe_str(p.get("status", ""), 20)
                duration = _safe_str(p.get("duration_ms", 0), 10)
                ac_text = _safe_str(p.get("ac_text", ""), 300)
                pev = p.get("evidence") or {}
                # شناسایی step probe vs system probe vs AC probe
                marker = ""
                if isinstance(pev, dict):
                    if pev.get("step_id"):
                        marker = f" 🪜 [step #{pev.get('step_id')}]"
                    elif p.get("ac_id") == "system_home":
                        marker = " 🏠 [system]"
                emoji = {"passed": "✅", "failed": "❌", "error": "⚠️",
                         "skipped": "⏭"}.get(status, "·")
                pb_lines = [
                    f"### probe {idx}{marker} — {emoji} `{method}` — `{status}` — {duration}ms",
                    f"- **AC/step:** «{ac_text}»",
                ]
                if isinstance(pev, dict):
                    if pev.get("step_inferred_route"):
                        pb_lines.append(f"- **route (inferred):** `{pev['step_inferred_route']}`")
                    if pev.get("final_url"):
                        pb_lines.append(f"- **frontend URL ناوبری‌شده:** {_safe_str(pev['final_url'], 300)}")
                    # actions_taken
                    acts = pev.get("actions_taken") or []
                    if isinstance(acts, list) and acts:
                        pb_lines.append("- **actions_taken:**")
                        for a in acts[:10]:
                            if isinstance(a, dict):
                                pb_lines.append(
                                    f"  - `{a.get('action','')}` "
                                    f"{a.get('url') or a.get('selector') or a.get('label') or ''} "
                                    f"({a.get('duration_ms', 0)}ms, success={a.get('success', '?')})"
                                )
                    # assertion_results
                    assertions = pev.get("assertion_results") or []
                    if isinstance(assertions, list) and assertions:
                        pb_lines.append("- **assertion_results:**")
                        for asr in assertions[:10]:
                            if isinstance(asr, dict):
                                m = "✓" if asr.get("met") else "✗"
                                pb_lines.append(
                                    f"  - {m} {_safe_str(asr.get('expectation', ''), 100)}"
                                    f" — {_safe_str(asr.get('reason', ''), 150)}"
                                )
                    # backend URLs called
                    be_urls = pev.get("backend_urls_called") or []
                    if isinstance(be_urls, list) and be_urls:
                        pb_lines.append("- **backend URLs فراخوانی‌شده:**")
                        for bu in be_urls[:20]:
                            if isinstance(bu, dict):
                                pb_lines.append(
                                    f"  - `{bu.get('method', 'GET')}` "
                                    f"{_safe_str(bu.get('url', ''), 250)} → "
                                    f"{bu.get('status', '?')}"
                                )
                    # console errors
                    ce = pev.get("console_errors") or []
                    if isinstance(ce, list) and ce:
                        pb_lines.append(f"- **console errors ({len(ce)}):**")
                        for c in ce[:10]:
                            if isinstance(c, dict):
                                pb_lines.append(
                                    f"  - `[{c.get('level', '?')}]` "
                                    f"{_safe_str(c.get('message', ''), 200)}"
                                )
                    # backend log summary
                    if pev.get("backend_log_summary"):
                        pb_lines.append(
                            f"- **backend log summary:** "
                            f"{_safe_str(pev['backend_log_summary'], 600)}"
                        )
                    # screenshots: label + vision + feature_present
                    shots = pev.get("screenshots") or []
                    if isinstance(shots, list) and shots:
                        pb_lines.append("- **screenshots:**")
                        for s in shots:
                            if isinstance(s, dict):
                                label = _safe_str(s.get("label", ""), 50)
                                vd = _safe_str(s.get("vision_description", ""), 2000)
                                vs = _safe_str(s.get("vision_source", ""), 40)
                                archived = "✅ آرشیو شده در تلگرام" if s.get("archived_to_telegram") else "روی دیسک"
                                # 🆕 (Phase 2 fix 3) — feature_present
                                fp = _safe_str(s.get("vision_feature_present", ""), 20).lower()
                                fp_reason = _safe_str(s.get("vision_feature_reason", ""), 500)
                                fp_emoji = {
                                    "yes": "✅ YES",
                                    "no": "❌ NO",
                                    "unclear": "❓ UNCLEAR",
                                }.get(fp, "")
                                pb_lines.append(f"  - **{label}** ({archived}, source=`{vs}`)")
                                if fp_emoji and fp != "unclear":
                                    pb_lines.append(
                                        f"    - feature_present: {fp_emoji}"
                                        + (f" — {fp_reason}" if fp_reason else "")
                                    )
                                if vd:
                                    pb_lines.append(f"    > {vd}")
                    # inspector session deep-link reference
                    if pev.get("inspector_session_id"):
                        pb_lines.append(
                            f"- **inspector_session_id:** {pev['inspector_session_id']}"
                        )
                    # error_message
                    if p.get("error_message"):
                        pb_lines.append(f"- **error:** {_safe_str(p['error_message'], 300)}")
                probe_parts.append("\n".join(pb_lines))
            parts.append(_md_section(
                f"۸. شواهد runtime probes ({len(probes)})",
                "\n\n".join(probe_parts)
            ))
    except Exception as e:
        logger.debug(f"mega_bundle probes failed: {e}")

    # --- 8.1) Smart Navigation decisions (Phase 4) ---
    try:
        ev = getattr(report, "evidence", None) or {}
        probes = ev.get("runtime_probes", []) if isinstance(ev, dict) else []
        nav_lines: List[str] = []
        for p in probes:
            if not isinstance(p, dict):
                continue
            pev = p.get("evidence") or {}
            if not isinstance(pev, dict):
                continue
            sn = pev.get("smart_nav")
            if not isinstance(sn, dict):
                continue
            label = _safe_str(pev.get("step_title") or p.get("ac_text", ""), 80)
            conf = _safe_str(sn.get("confidence", ""), 20)
            href = _safe_str(sn.get("chosen_href", ""), 200)
            text = _safe_str(sn.get("chosen_text", ""), 80)
            reason = _safe_str(sn.get("reason", ""), 200)
            links_count = sn.get("links_count", 0)
            dur = sn.get("duration_ms", 0)
            nav_lines.append(
                f"- 🧭 **{label}** → `{href}` "
                f"(link=«{text}», confidence={conf}, links={links_count}, {dur}ms)\n"
                f"  - reason: {reason}"
            )
        if nav_lines:
            parts.append(_md_section(
                f"۸.۱ تصمیم‌های Smart Navigation ({len(nav_lines)})",
                "\n".join(nav_lines),
            ))
    except Exception as e:
        logger.debug(f"mega_bundle smart_nav failed: {e}")

    # --- 8.2) Backend Log Analysis (Phase 4) ---
    try:
        ev = getattr(report, "evidence", None) or {}
        probes = ev.get("runtime_probes", []) if isinstance(ev, dict) else []
        bl_lines: List[str] = []
        for p in probes:
            if not isinstance(p, dict):
                continue
            if p.get("method") != "backend_log":
                continue
            pev = p.get("evidence") or {}
            if not isinstance(pev, dict):
                continue
            ac_text = _safe_str(p.get("ac_text", ""), 200)
            verdict = _safe_str(pev.get("verdict", ""), 40)
            verdict_emoji = {
                "deployed_working": "✅",
                "deployed_with_errors": "⚠️",
                "deployed_not_called": "🔇",
                "not_deployed": "❌",
                "unclear": "❓",
            }.get(verdict, "·")
            eps = pev.get("endpoints_extracted") or []
            syms = pev.get("symbols_extracted") or []
            reason = _safe_str(pev.get("reason", ""), 300)
            evidence_lines = pev.get("evidence_lines") or []
            log_count = pev.get("log_count", 0)
            window_h = pev.get("log_window_hours", 0)
            # endpoints به‌صورت dict {method, path} یا str می‌آیند
            eps_text = ", ".join(
                f"{e.get('method', '*')} {e.get('path', '')}"
                if isinstance(e, dict) else str(e)
                for e in eps[:6]
            ) or "—"
            syms_text = ", ".join(str(s) for s in syms[:6]) or "—"
            bl_lines.append(
                f"### {verdict_emoji} `{verdict}` — «{ac_text}»\n"
                f"- **endpoints:** {eps_text}\n"
                f"- **symbols:** {syms_text}\n"
                f"- **logs scanned:** {log_count} (window={window_h}h)\n"
                f"- **reason:** {reason}"
            )
            if evidence_lines:
                bl_lines.append("- **evidence_lines:**")
                for ln in evidence_lines[:5]:
                    bl_lines.append(f"  - `{_safe_str(ln, 250)}`")
        if bl_lines:
            parts.append(_md_section(
                "۸.۲ تحلیل Backend Logs",
                "\n\n".join(bl_lines),
            ))
    except Exception as e:
        logger.debug(f"mega_bundle backend_log failed: {e}")

    # --- 8.3) Code-aware Verdict (Phase 4) ---
    try:
        ev = getattr(report, "evidence", None) or {}
        probes = ev.get("runtime_probes", []) if isinstance(ev, dict) else []
        ca_lines: List[str] = []
        for p in probes:
            if not isinstance(p, dict):
                continue
            if p.get("method") != "code_analysis":
                continue
            pev = p.get("evidence") or {}
            if not isinstance(pev, dict):
                continue
            ac_text = _safe_str(p.get("ac_text", ""), 200)
            verdict = _safe_str(pev.get("code_verdict", ""), 40)
            verdict_emoji = {
                "implemented": "✅",
                "partial": "🟡",
                "not_found": "❌",
                "unclear": "❓",
            }.get(verdict, "·")
            commits = pev.get("matching_commits") or []
            key_changes = pev.get("key_changes") or []
            reason = _safe_str(pev.get("reason", ""), 300)
            ca_lines.append(
                f"### {verdict_emoji} `{verdict}` — «{ac_text}»\n"
                f"- **matching commits:** "
                f"{', '.join(f'`{c}`' for c in commits[:6]) or '—'}\n"
                f"- **reason:** {reason}"
            )
            if key_changes:
                ca_lines.append("- **key changes:**")
                for kc in key_changes[:6]:
                    ca_lines.append(f"  - `{_safe_str(kc, 200)}`")
        if ca_lines:
            parts.append(_md_section(
                "۸.۳ تحلیل Code-aware (commit diffs)",
                "\n\n".join(ca_lines),
            ))
    except Exception as e:
        logger.debug(f"mega_bundle code_aware failed: {e}")

    # --- 9) URLs (aggregate) ---
    try:
        ev = getattr(report, "evidence", None) or {}
        probes = ev.get("runtime_probes", []) if isinstance(ev, dict) else []
        all_frontend_urls: List[str] = []
        all_backend_urls: List[Dict[str, Any]] = []
        for p in probes:
            if not isinstance(p, dict):
                continue
            pev = p.get("evidence") or {}
            if not isinstance(pev, dict):
                continue
            fu = pev.get("final_url")
            if fu and fu not in all_frontend_urls:
                all_frontend_urls.append(fu)
            for bu in (pev.get("backend_urls_called") or []):
                if isinstance(bu, dict):
                    # dedup by url
                    if not any(
                        x.get("url") == bu.get("url") and x.get("method") == bu.get("method")
                        for x in all_backend_urls
                    ):
                        all_backend_urls.append(bu)
        url_lines: List[str] = []
        if all_frontend_urls:
            url_lines.append(f"**Frontend URLs ناوبری‌شده ({len(all_frontend_urls)}):**")
            for u in all_frontend_urls:
                url_lines.append(f"- {_safe_str(u, 300)}")
        if all_backend_urls:
            url_lines.append(f"\n**Backend URLs فراخوانی‌شده ({len(all_backend_urls)}):**")
            for b in all_backend_urls[:50]:
                url_lines.append(
                    f"- `{b.get('method', 'GET')}` "
                    f"{_safe_str(b.get('url', ''), 250)} → {b.get('status', '?')}"
                )
        if url_lines:
            parts.append(_md_section("۹. URL ها (aggregate)", "\n".join(url_lines)))
    except Exception as e:
        logger.debug(f"mega_bundle urls failed: {e}")

    # --- 10) AI verifier raw response (debug) ---
    try:
        raw_resp = _safe_str(getattr(report, "raw_response", "") or "", 3000)
        if raw_resp.strip():
            parts.append(_md_section(
                "۱۰. AI verifier raw response (debug)",
                _md_code_block(raw_resp, "json")
            ))
    except Exception as e:
        logger.debug(f"mega_bundle raw_resp failed: {e}")

    # --- compose ---
    full_md = "".join(parts)
    # 🆕 (encoding fix) — تبدیل به HTML با charset utf-8 + RTL تا روی
    # تلگرام/موبایل فارسی به‌جای mojibake درست رندر شود.
    title_for_html = _safe_str(
        getattr(task, "title", "") or getattr(task, "id", "task"), 200,
    )
    # escape برای امنیت — تنها &, <, > تبدیل می‌شوند تا متن preserved بماند
    escaped = (
        full_md.replace("&", "&amp;")
               .replace("<", "&lt;")
               .replace(">", "&gt;")
    )
    html = (
        '<!DOCTYPE html>\n'
        '<html lang="fa" dir="rtl">\n'
        '<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<title>Bundle — {title_for_html}</title>\n'
        '<style>\n'
        '  body { font-family: Tahoma, Vazir, Arial, sans-serif; '
        '         max-width: 980px; margin: 1em auto; padding: 0 1em; '
        '         line-height: 1.6; color: #222; background: #fafafa; }\n'
        '  pre { white-space: pre-wrap; word-wrap: break-word; '
        '        background: #fff; border: 1px solid #ddd; '
        '        border-radius: 6px; padding: 1em; font-family: '
        '        Consolas, "Vazir Code", "Courier New", monospace; '
        '        font-size: 13px; direction: ltr; text-align: left; }\n'
        '  .rtl-text { direction: rtl; text-align: right; }\n'
        '  h1 { font-size: 20px; }\n'
        '</style>\n'
        '</head>\n'
        '<body>\n'
        '<pre>' + escaped + '</pre>\n'
        '</body>\n'
        '</html>\n'
    )
    # BOM + utf-8 برای حداکثر سازگاری
    encoded = b"\xef\xbb\xbf" + html.encode("utf-8")
    if len(encoded) > _MAX_SIZE_BYTES:
        # trim نهایی — هشدار trim در پایان
        cut = _MAX_SIZE_BYTES - 500
        warn_msg = (
            "\n\n---\n_⚠️ این فایل به سقف ۱MB رسیده — "
            "برای دیدن کامل، به منابع DB مراجعه شود._\n"
        )
        # بدون BOM این بار چون قبلاً اضافه شده
        encoded = encoded[:cut] + warn_msg.encode("utf-8") + b"</pre></body></html>"
    return encoded


# ---------------------------------------------------------------------------
# 🆕 (Phase 2 fix 2) — PDF builder with HTML fallback
# ---------------------------------------------------------------------------

# سقف اندازه‌ی PDF (5MB — Telegram تا 20MB قبول می‌کند)
_MAX_PDF_BYTES = 5_000_000

# سمافور برای رندر PDF — تنها یک playwright render همزمان
import asyncio as _asyncio  # noqa: E402
_PDF_RENDER_SEM = _asyncio.Semaphore(1)


async def build_mega_bundle_pdf(task: Any, report: Any) -> Tuple[bytes, str]:
    """ساخت bundle به‌صورت PDF (اگر Playwright در دسترس) یا fallback به HTML.

    Returns: (bytes, extension) — extension به صورت ".pdf" یا ".html"

    این تابع از همان pattern build_verify_report_pdf استفاده می‌کند:
    HTML → set_content در Chromium → page.pdf().
    """
    # ابتدا HTML build کن (همان منطق build_mega_bundle_md)
    html_bytes = build_mega_bundle_md(task, report)
    # BOM را حذف کن چون داخل set_content مشکل ساز است
    if html_bytes.startswith(b"\xef\xbb\xbf"):
        html_bytes = html_bytes[3:]
    try:
        html_doc = html_bytes.decode("utf-8")
    except Exception as e:
        logger.warning(f"mega_bundle: decode html failed: {e}")
        return html_bytes, ".html"

    # تلاش برای PDF با playwright
    try:
        try:
            from playwright.async_api import async_playwright  # noqa: F401
        except ImportError:
            logger.debug("mega_bundle pdf: playwright not installed — fallback to html")
            return _wrap_html_bom(html_doc), ".html"

        async with _PDF_RENDER_SEM:
            from playwright.async_api import async_playwright
            playwright = await async_playwright().start()
            try:
                browser = await playwright.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox"],
                )
                try:
                    context = await browser.new_context()
                    page = await context.new_page()
                    await page.set_content(
                        html_doc, wait_until="domcontentloaded", timeout=8000,
                    )
                    try:
                        await page.wait_for_timeout(600)
                    except Exception:
                        pass
                    pdf_bytes = await page.pdf(
                        format="A4",
                        margin={"top": "12mm", "right": "12mm",
                                "bottom": "12mm", "left": "12mm"},
                        print_background=True,
                    )
                    if len(pdf_bytes) > _MAX_PDF_BYTES:
                        # خیلی بزرگ شد — fallback به html
                        logger.warning(
                            f"mega_bundle pdf too large ({len(pdf_bytes)} bytes) "
                            f"— fallback to html"
                        )
                        return _wrap_html_bom(html_doc), ".html"
                    return pdf_bytes, ".pdf"
                finally:
                    try:
                        await browser.close()
                    except Exception:
                        pass
            finally:
                try:
                    await playwright.stop()
                except Exception:
                    pass
    except Exception as e:
        logger.warning(
            f"mega_bundle pdf render failed ({e}) — fallback to html"
        )
        return _wrap_html_bom(html_doc), ".html"


def _wrap_html_bom(html_doc: str) -> bytes:
    """fallback: html را با UTF-8 BOM encode کن."""
    return b"\xef\xbb\xbf" + html_doc.encode("utf-8")
