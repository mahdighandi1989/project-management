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

_MAX_SIZE_BYTES = 1_500_000  # 1.5MB cap
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
        body = f"**کل تسک‌های ایجادشده:** {len(created_tasks)}\n\n"
        body += "**به تفکیک pass:**\n"
        for p, c in passes.most_common():
            body += f"- {p}: {c}\n"
        body += "\n**لیست تسک‌ها (top 20):**\n"
        for t in created_tasks[:20]:
            title = _safe(t.get("title", "?"), 100)
            priority = t.get("priority", "?")
            type_ = t.get("type", "?")
            tid = t.get("id", "?")[:8]
            body += f"- [{priority:8}] `{type_}` — {title} (id: `{tid}`)\n"
        if len(created_tasks) > 20:
            body += f"\n_... و {len(created_tasks) - 20} تسک دیگر_\n"
        parts.append(_section("۹. تسک‌های ایجاد شده", body))

    # ── 10. Inspector session reference ──
    sid = scan_v5_inventory.get("_scan_session_id")
    if sid:
        parts.append(_section(
            "۱۰. Inspector Session",
            f"شناسهٔ session: **#{sid}**\n\n"
            f"در tab «بازرس ویژه» می‌توانید پیام‌های کامل، screenshot ها و "
            f"خروجی AI calls این scan را ببینید.",
        ))

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
) -> Tuple[bytes, str]:
    """ساخت PDF با Playwright fallback به HTML."""
    html_bytes = build_scan_bundle_md(watched, scan_v5_inventory, created_tasks)
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
