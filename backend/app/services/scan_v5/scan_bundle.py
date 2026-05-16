"""Phase 5 — Scan Bundle Generator (R6, R12).

ساخت یک HTML/PDF کامل از نتایج scan v5 برای ضمیمه به Telegram message.
شامل:
  - inventory summary (12 layers)
  - stale findings (structural + semantic)
  - delta (add/remove/modify/...)
  - logic audit (coherence + anti-patterns)
  - effectiveness (outcome-based)
  - notification audit
  - runtime state (routes_alive, routes_404)
  - inspector session reference
  - lista of tasks created

دو تابع:
- build_scan_bundle_md(watched, scan_v5_inventory, created_tasks) -> bytes (HTML)
- build_scan_bundle_pdf(...) -> (bytes, ext) — PDF با fallback به HTML
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_MAX_SIZE_BYTES = 5_000_000  # 5MB cap (Telegram allows ~50MB; we leave headroom)
_PDF_RENDER_SEM = asyncio.Semaphore(2)


def _safe(v: Any, limit: int = 500) -> str:
    try:
        s = str(v) if v is not None else ""
    except Exception:
        s = "<unstringable>"
    return s[:limit] + ("…" if len(s) > limit else "")


def _section(title: str, body: str) -> str:
    return f"\n## {title}\n\n{body}\n"


def build_scan_bundle_md(
    watched: Any,
    scan_v5_inventory: Dict[str, Any],
    created_tasks: List[Dict[str, Any]],
    all_findings: Optional[List[Dict[str, Any]]] = None,
) -> bytes:
    """ساخت HTML bundle از scan v5 خروجی.

    Returns: bytes (UTF-8 با BOM, RTL HTML)
    """
    parts: List[str] = []

    repo_name = _safe(
        getattr(watched, "repo_full_name", "") or getattr(watched, "name", "scan"),
        100,
    )

    parts.append(f"# 🔬 Scan v5 Bundle — {repo_name}\n")
    parts.append(
        f"_فایل تولیدشده در: {datetime.now(timezone.utc).isoformat()}_\n"
    )

    # ── meta ──
    meta = scan_v5_inventory.get("_meta") or {}
    counts = meta.get("counts") or {}
    if counts:
        rows = "\n".join(f"- **{k}:** {v}" for k, v in sorted(counts.items()))
        parts.append(_section("۱. خلاصهٔ inventory (۱۲ لایه)", rows))

    # ── 2. delta ──
    delta = scan_v5_inventory.get("_delta") or {}
    delta_summary = delta.get("summary") or {}
    if delta_summary and not delta_summary.get("first_scan"):
        rows = (
            f"- ➕ **add:** {delta_summary.get('add', 0)}\n"
            f"- ➖ **remove:** {delta_summary.get('remove', 0)}\n"
            f"- ✏️ **modify:** {delta_summary.get('modify', 0)}\n"
            f"- 🔀 **rename:** {delta_summary.get('rename', 0)}\n"
            f"- 📦 **move:** {delta_summary.get('move', 0)}\n"
            f"- 🪧 **signature_change:** {delta_summary.get('signature_change', 0)}"
        )
        parts.append(_section("۲. تغییرات از scan قبلی", rows))
    elif delta_summary.get("first_scan"):
        parts.append(_section("۲. تغییرات از scan قبلی", "(اولین scan — baseline)"))

    # ── 3. stale ──
    stale = scan_v5_inventory.get("_stale") or {}
    stale_summary = stale.get("summary") or {}
    if stale_summary:
        rows_lines: List[str] = [
            f"**خلاصه:** {stale_summary.get('structural_total', 0)} structural + "
            f"{stale_summary.get('semantic_total', 0)} semantic"
        ]
        by_kind = stale_summary.get("by_kind") or {}
        if by_kind:
            rows_lines.append("\n**به تفکیک نوع:**")
            for k, c in sorted(by_kind.items(), key=lambda x: -x[1]):
                rows_lines.append(f"- {k}: {c}")
        # 🆕 همه‌ی items (نه top 8) — کاربر می‌خواهد همه را ببیند
        structural = stale.get("structural") or []
        semantic = stale.get("semantic") or []
        # ابتدا group by kind برای خوانایی
        from collections import defaultdict as _dd
        by_kind_items: Dict[str, List[Dict[str, Any]]] = _dd(list)
        for it in structural + semantic:
            by_kind_items[it.get("kind", "?")].append(it)
        for kind in sorted(by_kind_items.keys()):
            items_of_kind = by_kind_items[kind]
            rows_lines.append(f"\n**{kind} ({len(items_of_kind)}):**")
            for it in items_of_kind[:50]:  # تا 50 per kind
                target = (
                    it.get("file")
                    or it.get("route")
                    or it.get("path")
                    or it.get("label")
                    or "?"
                )
                rows_lines.append(f"- {_safe(target, 100)}: {_safe(it.get('reason', ''), 80)}")
            if len(items_of_kind) > 50:
                rows_lines.append(f"  _… و {len(items_of_kind) - 50} مورد دیگر_")
        parts.append(_section("۳. Stale & Forgotten Options (R8)", "\n".join(rows_lines)))

    # ── 4. anti-patterns ──
    aps = scan_v5_inventory.get("_anti_patterns") or []
    if aps:
        from collections import Counter
        kinds = Counter(a.get("kind", "?") for a in aps)
        body = "**خلاصه:** " + ", ".join(f"{k}: {c}" for k, c in kinds.most_common(15))
        # 🆕 group by kind، تا 30 نمونه از هر نوع
        body += "\n\n**به تفکیک نوع:**"
        ap_by_kind: Dict[str, List[Dict[str, Any]]] = {}
        for ap in aps:
            ap_by_kind.setdefault(ap.get("kind", "?"), []).append(ap)
        for kind, items in ap_by_kind.items():
            body += f"\n\n**{kind} ({len(items)}):**\n"
            for ap in items[:30]:
                _line = ap.get("line")
                _line_str = f" line {_line}" if _line else ""
                _file_str = _safe(ap.get("file", "?"), 60)
                _reason_str = _safe(ap.get("reason") or ap.get("description", ""), 150)
                body += f"- `{_file_str}`{_line_str}: {_reason_str}\n"
            if len(items) > 30:
                body += f"  _… و {len(items) - 30} مورد دیگر_\n"
        parts.append(_section("۴. Anti-patterns منطقی (R10)", body))

    # ── 5. coherence ──
    coh = scan_v5_inventory.get("_coherence") or {}
    coh_issues = coh.get("issues") or []
    if coh_issues or coh.get("pipelines_detected"):
        body = ""
        pipes = coh.get("pipelines_detected") or []
        if pipes:
            body += "**Pipelines تشخیص داده‌شده:**\n"
            for p in pipes:
                body += f"- {p.get('category', '?')}: {p.get('component_count', 0)} component\n"
        if coh_issues:
            body += "\n**مشکلات coherence:**\n"
            for ci in coh_issues[:6]:
                body += (
                    f"- [{ci.get('priority', '?')}] **{_safe(ci.get('title', ''), 100)}**\n"
                    f"  - {_safe(ci.get('description', ''), 200)}\n"
                    f"  - 🛠 {_safe(ci.get('suggested_fix', ''), 150)}\n"
                )
        parts.append(_section("۵. Pipeline Coherence (R10)", body))

    # ── 6. effectiveness ──
    eff = scan_v5_inventory.get("_effectiveness_issues") or []
    outcome = scan_v5_inventory.get("_outcome_data") or {}
    if eff or outcome.get("project_type"):
        body = (
            f"**نوع پروژه:** {outcome.get('project_type', '?')}\n"
            f"**error_rate (30d):** {outcome.get('error_rate_30d', '?')}\n"
        )
        if eff:
            body += "\n**Effectiveness Issues:**\n"
            for e in eff[:5]:
                body += (
                    f"- [{e.get('priority', '?')}] **{_safe(e.get('title', ''), 100)}**\n"
                    f"  - 🎯 outcome target: {_safe(e.get('outcome_target', ''), 150)}\n"
                    f"  - 📊 current: {_safe(e.get('current_state', ''), 150)}\n"
                )
        parts.append(_section("۶. Effectiveness (R11)", body))

    # ── 7. notification audit ──
    notif = scan_v5_inventory.get("_notif_audit") or {}
    notif_summary = notif.get("summary") or {}
    if notif_summary.get("total_issues"):
        body = (
            f"**کل calls:** {notif_summary.get('total_calls', 0)}\n"
            f"**کل issue:** {notif_summary.get('total_issues', 0)}\n"
            f"- missing silent flag: {notif_summary.get('missing_silent_flag', 0)}\n"
            f"- missing event type: {notif_summary.get('missing_event_type', 0)}\n"
            f"- critical/silent mismatch: {notif_summary.get('critical_silent_mismatch', 0)}\n"
            f"- missing critical events: {notif_summary.get('missing_critical_events', 0)}\n"
        )
        si = notif.get("structural_issues") or []
        if si:
            body += "\n**نمونه‌ها:**\n"
            for n in si[:6]:
                body += f"- `{n.get('kind', '?')}` در `{_safe(n.get('file', '?'), 60)}`:{n.get('line', '?')}\n"
        parts.append(_section("۷. Notification Audit (R12)", body))

    # ── 8. runtime state ──
    rt = scan_v5_inventory.get("_runtime_state") or {}
    if rt:
        body = (
            f"- ✅ routes alive: {len(rt.get('routes_alive', []))}\n"
            f"- ❌ routes 404: {len(rt.get('routes_404', []))}\n"
            f"- 📞 endpoints called (30d): {len(rt.get('endpoints_called_recently', []))}\n"
            f"- 🔇 endpoints never called: {len(rt.get('endpoints_never_called', []))}\n"
            f"- 📸 screenshots: {len(rt.get('screenshots', []))}\n"
        )
        r404 = rt.get("routes_404") or []
        if r404:
            body += "\n**Dead routes:**\n"
            for r in r404[:5]:
                body += f"- {r.get('route', '?')} → status {r.get('status', '?')}\n"
        parts.append(_section("۸. Runtime State (R14)", body))

    # ── 9. tasks created ──
    if created_tasks:
        # group by _pass (phase5_* or legacy)
        from collections import Counter
        passes = Counter(
            (
                (t.get("created_by_scan_metadata") or {}).get("pass")
                or "?"
            )
            for t in created_tasks
        )
        # 🆕 group by priority too
        priorities = Counter((t.get("priority") or "?") for t in created_tasks)
        # 🆕 group by type
        types = Counter((t.get("type") or "?") for t in created_tasks)

        body = f"**کل تسک‌های ایجادشده:** {len(created_tasks)}\n\n"
        body += "**به تفکیک priority:**\n"
        for p, c in priorities.most_common():
            body += f"- {p}: {c}\n"
        body += "\n**به تفکیک type:**\n"
        for t_, c in types.most_common():
            body += f"- {t_}: {c}\n"
        body += "\n**به تفکیک pass:**\n"
        for p, c in passes.most_common():
            body += f"- {p}: {c}\n"
        parts.append(_section("۹. خلاصه تسک‌های ایجاد شده", body))

        # 🆕 (Phase 5 — bug 12) — فهرست کامل تسک‌ها با پرامپت و چک‌لیست
        # هر تسک یک sub-section با: title + priority + type + target_files
        # + prompt کامل (یا cap به ۴۰۰۰ کاراکتر) + acceptance_criteria به‌صورت
        # checklist قابل تیک. تسک‌ها به‌ترتیب priority (critical→low) مرتب می‌شوند.
        PRIO = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_tasks = sorted(
            created_tasks,
            key=lambda x: (
                PRIO.get((x.get("priority") or "medium").lower(), 2),
                (x.get("type") or ""),
            ),
        )
        # حداکثر ۳۰۰ تسک با پرامپت کامل، بعد از آن فقط title.
        FULL_LIMIT = 300
        for idx, t in enumerate(sorted_tasks[:FULL_LIMIT], start=1):
            title = _safe(t.get("title", "?"), 200)
            priority = t.get("priority", "?")
            type_ = t.get("type", "?")
            tid = (t.get("id") or "?")[:8]
            target_files = t.get("target_files") or []
            prompt_full = t.get("prompt") or ""
            # cap prompt at 4000 chars per task to keep bundle ≤1.5MB
            if len(prompt_full) > 4000:
                prompt_short = prompt_full[:4000] + "\n\n[... trimmed به 4000 char؛ پرامپت کامل در UI تسک ...]"
            else:
                prompt_short = prompt_full
            ac_items = t.get("acceptance_criteria") or []

            task_body_parts: List[str] = []
            task_body_parts.append(f"**🆔 ID:** `{tid}…`")
            task_body_parts.append(f"**🎯 priority:** `{priority}`")
            task_body_parts.append(f"**📂 type:** `{type_}`")
            if target_files:
                task_body_parts.append(
                    "**📁 target_files:** "
                    + ", ".join(f"`{p}`" for p in target_files[:5])
                    + (f" (+{len(target_files)-5} more)" if len(target_files) > 5 else "")
                )
            task_body_parts.append("")
            task_body_parts.append("### 📜 پرامپت کامل (Executable prompt)")
            task_body_parts.append("")
            task_body_parts.append("```")
            task_body_parts.append(prompt_short or "(پرامپت خالی)")
            task_body_parts.append("```")
            task_body_parts.append("")
            if ac_items:
                task_body_parts.append("### ✅ Acceptance Criteria (Checklist)")
                task_body_parts.append("")
                for ac in ac_items:
                    if isinstance(ac, dict):
                        txt = (ac.get("text") or "").strip()
                        signal = (ac.get("acceptance_signal") or "").strip()
                        if txt:
                            task_body_parts.append(f"- [ ] {txt}")
                            if signal:
                                task_body_parts.append(f"  - 🔍 signal: _{signal}_")
                    else:
                        task_body_parts.append(f"- [ ] {str(ac).strip()}")
                task_body_parts.append("")
            parts.append(_section(
                f"۹.{idx} {title}", "\n".join(task_body_parts)
            ))

        if len(created_tasks) > FULL_LIMIT:
            remaining = created_tasks[FULL_LIMIT:]
            body = f"**{len(remaining)} تسک باقی‌مانده (فقط title):**\n\n"
            for t in remaining:
                title = _safe(t.get("title", "?"), 120)
                priority = t.get("priority", "?")
                type_ = t.get("type", "?")
                tid = (t.get("id") or "?")[:8]
                body += f"- [{priority:8}] `{type_}` — {title} (id: `{tid}…`)\n"
            parts.append(_section("۹.* تسک‌های دیگر (خلاصه)", body))

    # ── 10. Inspector session reference ──
    sid = scan_v5_inventory.get("_scan_session_id")
    if sid:
        parts.append(_section(
            "۱۰. Inspector Session",
            f"شناسهٔ session: **#{sid}**\n\n"
            f"در tab «بازرس ویژه» می‌توانید پیام‌های کامل، screenshot ها و "
            f"خروجی AI calls این scan را ببینید.",
        ))

    # ══════════════════════════════════════════════════════════════════════
    # 🆕 (Phase 5 — bug 29) — بخش‌های گسترش‌یافتهٔ گزارش جامع
    # درخواست کاربر: هر pass و هر phase 5 layer باید با جزئیات کامل بیاید.
    # ══════════════════════════════════════════════════════════════════════

    # ── 11. Bidirectional Dependency Impact (downstream + upstream + added) ──
    _ci = scan_v5_inventory.get("_change_impact") or []
    _ui = scan_v5_inventory.get("_upstream_impact") or []
    _ar = scan_v5_inventory.get("_added_ripple") or []
    if _ci or _ui or _ar:
        body = (
            f"**خلاصه:** "
            f"⚠️ {len(_ci)} downstream · "
            f"⬆️ {len(_ui)} upstream · "
            f"🧩 {len(_ar)} added-file ripple\n"
        )
        if _ci:
            body += "\n**⚠️ Downstream impact (dependents در خطر):**\n"
            for item in _ci[:30]:
                _ch = _safe(item.get("changed_file", "?"), 70)
                _dep = _safe(item.get("dependent_file", "?"), 70)
                _risk = item.get("risk", "?")
                _reason = _safe(item.get("reason", ""), 140)
                body += f"- `{_ch}` → `{_dep}` [risk: {_risk}]: {_reason}\n"
            if len(_ci) > 30:
                body += f"  _… و {len(_ci) - 30} مورد دیگر_\n"
        if _ui:
            body += "\n**⬆️ Upstream impact (وابستگی‌ها نیازمند update):**\n"
            for item in _ui[:30]:
                _ch = _safe(item.get("changed_file", "?"), 70)
                _up = _safe(item.get("upstream_file", "?"), 70)
                _risk = item.get("risk", "?")
                _reason = _safe(item.get("reason", ""), 140)
                body += f"- `{_ch}` ← `{_up}` [risk: {_risk}]: {_reason}\n"
            if len(_ui) > 30:
                body += f"  _… و {len(_ui) - 30} مورد دیگر_\n"
        if _ar:
            body += "\n**🧩 Added-file ripple (orphan / missing companion):**\n"
            for item in _ar[:30]:
                _added = _safe(item.get("added_file", "?"), 70)
                _ity = item.get("issue_type", "?")
                _reason = _safe(item.get("reason", ""), 140)
                body += f"- `{_added}` [{_ity}]: {_reason}\n"
            if len(_ar) > 30:
                body += f"  _… و {len(_ar) - 30} مورد دیگر_\n"
        parts.append(_section("۱۱. Bidirectional Dependency Impact (R7+R10)", body))

    # ── 12. Cleanup tasks (subset) ──
    if created_tasks:
        cleanup = [t for t in created_tasks if (t.get("type") or "").lower() == "cleanup"]
        if cleanup:
            body = f"**{len(cleanup)} cleanup task:**\n\n"
            for t in cleanup[:30]:
                body += (
                    f"- [{t.get('priority', '?')}] "
                    f"{_safe(t.get('title', '?'), 140)}\n"
                )
            parts.append(_section("۱۲. Cleanup Tasks", body))

    # ── 13. گزارش تفصیلی per-category (۶ گروه اصلی pass ها) ──
    # mapping از pass name به گروه کاربر:
    _CAT_MAP = {
        "🔒 امنیت": ["security", "security_deep"],
        "🛠 کیفیت": ["quality"],
        "🧪 تست": ["coverage"],
        "✅ کامل بودن": ["completeness"],
        "🧩 منطق/هم‌راستایی": [
            "logical_alignment", "cross_stack", "dependency", "integrity",
        ],
        "⚙️ صحت رفتاری": ["functional_correctness", "frontend", "backend"],
    }
    _findings_all = all_findings or []
    if _findings_all:
        cat_intro = (
            f"**کل findings این scan:** {len(_findings_all)}\n\n"
            "هر یافته زیر شامل: مسیر فایل، severity، توضیح، توصیه.\n"
        )
        parts.append(_section("۱۳. گزارش تفصیلی per-category", cat_intro))
        for cat_label, pass_names in _CAT_MAP.items():
            # جمع‌آوری findings آن گروه
            cat_findings = [
                f for f in _findings_all
                if (f.get("_pass") or "").lower() in [p.lower() for p in pass_names]
            ]
            if not cat_findings:
                parts.append(_section(f"  {cat_label}", "_(یافته‌ای در این گروه ثبت نشد)_"))
                continue
            # group by severity
            from collections import Counter
            sev_count = Counter(
                (f.get("severity") or f.get("priority") or "medium").lower()
                for f in cat_findings
            )
            sev_summary = " · ".join(f"{s}: {c}" for s, c in sev_count.most_common())
            body = f"**{len(cat_findings)} یافته** ({sev_summary})\n\n"
            # sort by severity desc
            _SEV = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
            cat_findings = sorted(
                cat_findings,
                key=lambda x: _SEV.get(
                    (x.get("severity") or x.get("priority") or "medium").lower(), 2
                ),
            )
            for f in cat_findings[:60]:  # تا ۶۰ مورد per category
                _sev = (f.get("severity") or f.get("priority") or "medium").lower()
                _title = _safe(f.get("title") or f.get("description", ""), 180)
                _files = f.get("target_files") or []
                _file_str = _safe(_files[0], 80) if _files else "(no file)"
                _line = f.get("line") or ""
                _line_str = f":{_line}" if _line else ""
                _reason = _safe(
                    f.get("description") or f.get("reason", ""), 250,
                )
                _rec = _safe(f.get("proposed_action") or f.get("recommendation", ""), 200)
                body += (
                    f"### [{_sev}] {_title}\n"
                    f"- 📂 **file:** `{_file_str}{_line_str}`\n"
                    f"- 📝 **توضیح:** {_reason}\n"
                )
                if _rec:
                    body += f"- 🛠 **توصیه:** {_rec}\n"
                body += "\n"
            if len(cat_findings) > 60:
                body += f"_… و {len(cat_findings) - 60} مورد دیگر در این گروه_\n"
            parts.append(_section(f"  {cat_label}", body))

    # ══════════════════════════════════════════════════════════════════════

    # ── compose HTML ──
    full_md = "".join(parts)
    title_html = _safe(repo_name, 200)
    escaped = (
        full_md.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
    html = (
        '<!DOCTYPE html>\n'
        '<html lang="fa" dir="rtl">\n'
        '<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<title>Scan Bundle — {title_html}</title>\n'
        '<style>\n'
        '  body { font-family: Tahoma, Vazir, Arial, sans-serif; '
        '         max-width: 1000px; margin: 1em auto; padding: 0 1em; '
        '         line-height: 1.7; color: #222; background: #fafafa; }\n'
        '  pre { white-space: pre-wrap; word-wrap: break-word; '
        '        background: #fff; border: 1px solid #ddd; '
        '        border-radius: 6px; padding: 1em; font-family: '
        '        Consolas, monospace; font-size: 13px; '
        '        direction: ltr; text-align: left; }\n'
        '  h1 { font-size: 22px; color: #6b21a8; }\n'
        '  h2 { font-size: 17px; color: #7c3aed; border-bottom: 1px solid #ddd; padding-bottom: 4px; }\n'
        '  code { background: #f3f4f6; padding: 1px 4px; border-radius: 3px; font-family: Consolas, monospace; }\n'
        '</style>\n'
        '</head>\n'
        '<body>\n'
        '<pre>' + escaped + '</pre>\n'
        '</body>\n'
        '</html>\n'
    )
    encoded = b"\xef\xbb\xbf" + html.encode("utf-8")
    if len(encoded) > _MAX_SIZE_BYTES:
        cut = _MAX_SIZE_BYTES - 500
        warn = "\n\n---\n_⚠️ trim شد به سقف ۱.۵MB_\n"
        encoded = (encoded[:cut] + warn.encode("utf-8"))
    return encoded


def _wrap_html_bom(html_doc: str) -> bytes:
    return b"\xef\xbb\xbf" + html_doc.encode("utf-8")


async def build_scan_bundle_pdf(
    watched: Any,
    scan_v5_inventory: Dict[str, Any],
    created_tasks: List[Dict[str, Any]],
    all_findings: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[bytes, str]:
    """ساخت PDF با Playwright fallback به HTML."""
    html_bytes = build_scan_bundle_md(
        watched, scan_v5_inventory, created_tasks, all_findings=all_findings,
    )
    if html_bytes.startswith(b"\xef\xbb\xbf"):
        html_bytes = html_bytes[3:]
    try:
        html_doc = html_bytes.decode("utf-8")
    except Exception:
        return html_bytes, ".html"

    try:
        try:
            from playwright.async_api import async_playwright  # noqa
        except ImportError:
            logger.debug("scan_bundle: playwright unavailable → html fallback")
            return _wrap_html_bom(html_doc), ".html"

        async with _PDF_RENDER_SEM:
            from playwright.async_api import async_playwright
            playwright = await async_playwright().start()
            try:
                browser = await playwright.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox"],
                )
                context = await browser.new_context()
                page = await context.new_page()
                await page.set_content(html_doc, wait_until="networkidle")
                pdf_bytes = await page.pdf(
                    format="A4",
                    margin={"top": "1cm", "right": "1cm", "bottom": "1cm", "left": "1cm"},
                    print_background=True,
                )
                await browser.close()
                return pdf_bytes, ".pdf"
            finally:
                await playwright.stop()
    except Exception as e:
        logger.warning(f"scan_bundle pdf failed: {e} — html fallback")
        return _wrap_html_bom(html_doc), ".html"
