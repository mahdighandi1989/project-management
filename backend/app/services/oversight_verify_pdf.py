"""
Oversight Verify PDF Export
============================
تولید PDF از گزارش verify یک تسک — شامل چک‌لیست مراحل (با تیک)،
متن کامل پرامپت، done/remaining/next_actions، و evidence.

از playwright (موجود در dependencies) برای رندر HTML→PDF استفاده می‌کند
چون از Persian/RTL به‌صورت native پشتیبانی می‌کند.

اگر playwright در دسترس نباشد (مثلاً در تست‌های unit بدون browser)،
fallback به متن plain که با فرمت .txt به‌جای .pdf فرستاده می‌شود.

نکات runtime:
- از `wait_until="domcontentloaded"` استفاده می‌شود (نه `networkidle`) چون
  CDN فونت ممکن است در محیط Render قابل دسترسی نباشد و `networkidle`
  تا ۱۵ ثانیه بلاک می‌کند. فونت‌های fallback (Tahoma/Arial) Persian را
  درست رندر می‌کنند.
- یک Semaphore سراسری PDF generation را serialize می‌کند تا چند verify
  هم‌زمان OOM نکنند (هر playwright instance ~150-250MB).
"""

from __future__ import annotations

import asyncio
import html
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# 🔒 PDF generation یک منبع سنگین است — chromium instance حدود 200MB RAM
# می‌گیرد. این semaphore تضمین می‌کند فقط یک render هم‌زمان رخ دهد تا روی
# پلتفرم‌هایی با RAM محدود (مثل Render free tier) OOM نشویم.
_PDF_RENDER_SEMAPHORE = asyncio.Semaphore(1)


_STATUS_BADGE = {
    "done": ("✅", "DONE", "#16a34a"),
    "partial": ("🟡", "PARTIAL", "#d97706"),
    "not_done": ("❌", "NOT_DONE", "#dc2626"),
    "regressed": ("🔴", "REGRESSED", "#b91c1c"),
    "error": ("⚠️", "ERROR", "#7c3aed"),
    "pending": ("⬜", "PENDING", "#6b7280"),
}

_STEP_MARK = {
    "done": ("✅", "#16a34a"),
    "partial": ("🟡", "#d97706"),
    "not_done": ("❌", "#dc2626"),
    "error": ("⚠️", "#7c3aed"),
    "pending": ("⬜", "#6b7280"),
}


def _esc(s: Any) -> str:
    return html.escape(str(s or ""), quote=True)


def _short_title(title: str, max_len: int = 80) -> str:
    """عنوان کوتاه برای summary lines."""
    t = (title or "").strip().replace("\n", " ")
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip() + "…"


def _md_escape(s: str) -> str:
    """escape کاراکترهای Markdown که می‌توانند parse caption تلگرام را
    بشکنند: `_`، `*`، `` ` ``، `[`. (parser legacy Markdown تلگرام)."""
    if not s:
        return ""
    out = []
    for ch in s:
        if ch in ("_", "*", "`", "["):
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)


def build_verify_checklist_message(
    task: Any,
    report: Any,
    *,
    max_steps_inline: int = 30,
    char_budget: int = 900,
    header_override: Optional[str] = None,
) -> str:
    """ساخت متن چک‌لیستی برای caption پیام تلگرام (≤ ~900 char).

    عناوین کوتاه نگه داشته می‌شوند — جزئیات کامل در PDF پیوست است.

    اگر `report` None باشد (مثلاً برای تسک تازه ساخته‌شده که هنوز verify
    نشده)، حالت "task created" استفاده می‌شود — وضعیت‌ها صرفاً pending هستند
    و بخش‌های done/remaining/next_actions نمایش داده نمی‌شوند.
    """
    lines: List[str] = []
    title = getattr(task, "title", "") or ""
    project = getattr(task, "project_full_name", "") or ""
    priority = getattr(task, "priority", "") or ""
    task_type = getattr(task, "type", "") or ""
    streak = getattr(task, "confirmation_streak", 0) or 0
    confidence = float(getattr(report, "confidence_score", 0.0) or 0.0) if report else 0.0

    if header_override:
        lines.append(header_override)
    else:
        status = getattr(task, "verification_status", None) or (
            getattr(report, "status", "?") if report else "pending"
        )
        emoji, label, _ = _STATUS_BADGE.get(status, ("ℹ️", status, "#000"))
        lines.append(f"{emoji} *Verify: {label.lower()}*")
    # عنوان داخل `_..._` (italic) — کاراکترهای _ * ` [ را escape کن تا
    # parser Markdown تلگرام نشکند (مثلاً برای task با underscore در نام).
    lines.append(f"📌 _{_md_escape(_short_title(title, 100))}_")
    if project:
        # backticks برای code — کافیست خود backtick داخل project نباشد
        safe_project = project.replace("`", "ʼ")
        lines.append(f"📁 `{safe_project}`")
    meta_bits = []
    if priority:
        meta_bits.append(f"priority: *{_md_escape(priority)}*")
    if task_type:
        meta_bits.append(f"نوع: `{task_type.replace('`', 'ʼ')}`")
    if streak:
        meta_bits.append(f"streak: {streak}")
    if confidence > 0:
        meta_bits.append(f"اعتماد: {int(confidence * 100)}%")
    if meta_bits:
        lines.append("🔖 " + " • ".join(meta_bits))

    # 🆕 چک‌لیست مراحل — هستهٔ این feature
    steps = list(getattr(task, "task_steps", None) or [])
    overall = getattr(task, "overall_completion_pct", None)
    if steps:
        done_n = sum(1 for s in steps if (s.get("status") or "").lower() == "done")
        total = len(steps)
        header = f"\n📋 *چک‌لیست ({done_n}/{total}"
        if overall is not None:
            header += f" • {overall}%"
        header += "):*"
        lines.append(header)
        # هر مرحله یک خط — عنوان کوتاه (≤60 char)
        shown = 0
        for s in steps:
            if shown >= max_steps_inline:
                lines.append(f"… و {total - shown} مرحلهٔ دیگر (متن کامل در PDF)")
                break
            st = (s.get("status") or "pending").lower()
            mark, _ = _STEP_MARK.get(st, ("⬜", "#6b7280"))
            sid = s.get("id", "?")
            t_short = _md_escape(_short_title(s.get("title") or "", 70))
            line = f"{mark} مرحله {sid}: {t_short}"
            # اگر partial و remaining خیلی کوتاه است، یک hint اضافه کن
            if st in ("partial", "not_done") and s.get("remaining"):
                rem = _md_escape(_short_title(s.get("remaining"), 50))
                line += f"\n    ⏳ {rem}"
            lines.append(line)
            shown += 1
    else:
        # تسک بدون چک‌لیست — fallback به done/remaining قدیمی (فقط اگر report موجود است)
        if report is not None:
            done_parts = list(getattr(report, "done_parts", None) or [])
            remaining_parts = list(getattr(report, "remaining_parts", None) or [])
            if done_parts:
                lines.append(f"\n✅ *انجام‌شده ({len(done_parts)}):*")
                for item in done_parts[:5]:
                    lines.append(f"• {_md_escape(_short_title(str(item), 110))}")
            if remaining_parts:
                lines.append(f"\n⏳ *باقی‌مانده ({len(remaining_parts)}):*")
                for item in remaining_parts[:5]:
                    lines.append(f"• {_md_escape(_short_title(str(item), 110))}")

    # PR link (compact)
    applied = getattr(task, "applied_evidence", None) or {}
    pr_url = applied.get("pr_url") if isinstance(applied, dict) else None
    if pr_url:
        lines.append(f"\n🔗 PR: {pr_url}")

    text = "\n".join(lines)
    # محدودیت سخت caption — متن بلندتر در PDF می‌رود
    if len(text) > char_budget:
        text = text[: char_budget - 30] + "\n… (جزئیات کامل در PDF پیوست)"
    return text


def _build_verify_report_html(task: Any, report: Any) -> str:
    """ساخت HTML با ساختار RTL برای رندر به PDF.

    اگر report=None باشد (تسک تازه ساخته‌شده)، حالت "task brief" تولید
    می‌شود: متن کامل پرامپت + چک‌لیست مراحل (همه pending) + AC ها.
    """
    title = getattr(task, "title", "") or ""
    project = getattr(task, "project_full_name", "") or ""
    priority = getattr(task, "priority", "") or ""
    task_type = getattr(task, "type", "") or ""
    streak = getattr(task, "confirmation_streak", 0) or 0
    streak_required = getattr(task, "confirmation_streak_required", None)
    status = getattr(task, "verification_status", None) or (
        getattr(report, "status", "?") if report else "pending"
    )
    confidence = float(getattr(report, "confidence_score", 0.0) or 0.0) if report else 0.0
    last_verified = getattr(task, "last_verified_at", "") or ""
    overall = getattr(task, "overall_completion_pct", None)
    prompt = getattr(task, "prompt", "") or ""
    raw_idea = getattr(task, "raw_idea", "") or ""

    emoji, label, color = _STATUS_BADGE.get(status, ("ℹ️", status, "#374151"))
    steps = list(getattr(task, "task_steps", None) or [])
    if report is not None:
        done_parts = list(getattr(report, "done_parts", None) or [])
        remaining_parts = list(getattr(report, "remaining_parts", None) or [])
        next_actions = list(getattr(report, "next_actions", None) or [])
        evidence = getattr(report, "evidence", None) or {}
        summary = ""
        if isinstance(evidence, dict):
            summary = str(evidence.get("summary") or evidence.get("ai_summary") or "")
    else:
        done_parts = []
        remaining_parts = []
        next_actions = []
        summary = ""
    acs = list(getattr(task, "acceptance_criteria", None) or [])
    target_files = list(getattr(task, "target_files", None) or [])

    # ───── checklist HTML
    if steps:
        done_n = sum(1 for s in steps if (s.get("status") or "").lower() == "done")
        progress_pct = (
            overall if isinstance(overall, int)
            else int(round(sum(int(s.get("completion_pct", 0) or 0) for s in steps) / max(1, len(steps))))
        )
        bar_color = "#16a34a" if progress_pct >= 100 else ("#6366f1" if progress_pct >= 60 else ("#f59e0b" if progress_pct >= 30 else "#ef4444"))
        steps_rows: List[str] = []
        for s in steps:
            st = (s.get("status") or "pending").lower()
            mark, mc = _STEP_MARK.get(st, ("⬜", "#6b7280"))
            sid = _esc(s.get("id", "?"))
            stitle = _esc(s.get("title") or "")
            scope = _esc(s.get("scope") or "")
            pct = int(s.get("completion_pct", 0) or 0)
            remaining = _esc(s.get("remaining") or "")
            step_evidence = _esc(s.get("evidence") or "")
            last_v = _esc(s.get("last_verified_at") or "")
            title_class = "step-title done" if st == "done" else "step-title"
            details_parts: List[str] = []
            if scope:
                details_parts.append(f'<div class="step-scope">📝 {scope}</div>')
            if st != "done" and remaining:
                details_parts.append(f'<div class="step-remaining">⏳ <b>باقی‌مانده:</b> {remaining}</div>')
            if step_evidence:
                details_parts.append(f'<div class="step-evidence">📎 <b>شواهد:</b> {step_evidence}</div>')
            if last_v:
                details_parts.append(f'<div class="step-meta">⏱ آخرین verify: {last_v}</div>')
            details = "\n".join(details_parts)
            steps_rows.append(f"""
            <div class="step-row" style="border-right: 4px solid {mc}">
              <div class="step-head">
                <span class="step-mark">{mark}</span>
                <span class="{title_class}">مرحله {sid}: {stitle}</span>
                <span class="step-pct">{pct}%</span>
              </div>
              {details}
            </div>
            """)
        checklist_html = f"""
        <section>
          <h2>📋 چک‌لیست مراحل ({done_n}/{len(steps)} انجام‌شده — پیشرفت کلی: {progress_pct}%)</h2>
          <div class="progress-bar"><div class="progress-fill" style="width:{max(2, min(100, progress_pct))}%; background:{bar_color}"></div></div>
          {''.join(steps_rows)}
        </section>
        """
    else:
        checklist_html = ""

    # ───── done/remaining/next_actions
    def _bullets(items: List[str]) -> str:
        if not items:
            return '<p class="muted">—</p>'
        return "<ul>" + "".join(f"<li>{_esc(x)}</li>" for x in items) + "</ul>"

    done_html = f'<section><h2>✅ بخش‌های انجام‌شده ({len(done_parts)})</h2>{_bullets(done_parts)}</section>' if done_parts else ""
    remaining_html = f'<section><h2>⏳ بخش‌های باقی‌مانده ({len(remaining_parts)})</h2>{_bullets(remaining_parts)}</section>' if remaining_parts else ""
    next_html = f'<section><h2>🪜 اقدامات بعدی پیشنهادی</h2>{_bullets(next_actions)}</section>' if next_actions else ""
    acs_html = f'<section><h2>🎯 معیارهای پذیرش</h2>{_bullets(acs)}</section>' if acs else ""
    tf_html = f'<section><h2>📂 فایل‌های هدف</h2>{_bullets(target_files)}</section>' if target_files else ""
    summary_html = f'<section><h2>💬 خلاصهٔ verifier</h2><blockquote>{_esc(summary)}</blockquote></section>' if summary else ""
    raw_idea_html = f'<section><h2>💡 ایدهٔ خام</h2><pre>{_esc(raw_idea)}</pre></section>' if raw_idea else ""

    # ───── full prompt
    prompt_html = f'<section><h2>📜 پرامپت کامل تسک</h2><pre class="prompt">{_esc(prompt)}</pre></section>' if prompt else ""

    streak_str = f"{streak}" + (f"/{streak_required}" if streak_required else "")

    return f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<title>{_esc(title) or "Verify Report"}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;700&display=swap');
* {{ box-sizing: border-box; }}
body {{
  font-family: 'Vazirmatn', Tahoma, Arial, sans-serif;
  direction: rtl;
  color: #1f2937;
  margin: 0;
  padding: 24px 28px;
  line-height: 1.7;
  font-size: 12px;
}}
h1 {{ font-size: 18px; margin: 0 0 4px; color: #111827; }}
h2 {{ font-size: 14px; margin: 16px 0 8px; color: #1f2937; border-bottom: 1px solid #e5e7eb; padding-bottom: 4px; }}
.header {{ border-bottom: 2px solid {color}; padding-bottom: 10px; margin-bottom: 14px; }}
.badge {{
  display: inline-block; padding: 2px 10px; border-radius: 999px;
  background: {color}22; color: {color}; font-weight: 700; font-size: 11px;
}}
.meta {{ font-size: 11px; color: #4b5563; margin-top: 4px; }}
.meta b {{ color: #1f2937; }}
.muted {{ color: #9ca3af; font-style: italic; }}
ul {{ margin: 4px 0 4px 0; padding-right: 20px; }}
li {{ margin: 3px 0; }}
pre {{
  white-space: pre-wrap; word-break: break-word;
  background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px;
  padding: 8px 10px; font-family: 'Vazirmatn', monospace;
  font-size: 10.5px; max-width: 100%;
}}
pre.prompt {{ font-size: 10px; line-height: 1.6; }}
blockquote {{
  margin: 4px 0; padding: 6px 12px; border-right: 3px solid #6366f1;
  background: #eef2ff; color: #312e81; border-radius: 4px;
}}
.progress-bar {{
  height: 6px; background: #e5e7eb; border-radius: 999px; overflow: hidden;
  margin: 4px 0 10px;
}}
.progress-fill {{ height: 100%; }}
.step-row {{
  margin: 6px 0; padding: 6px 10px; background: #f9fafb;
  border-radius: 4px;
}}
.step-head {{
  display: flex; align-items: center; gap: 8px;
  font-weight: 600; font-size: 12px;
}}
.step-mark {{ font-size: 14px; }}
.step-title {{ flex: 1; }}
.step-title.done {{ color: #6b7280; text-decoration: line-through; }}
.step-pct {{
  font-size: 10px; color: #4b5563; background: #fff; border: 1px solid #d1d5db;
  padding: 1px 6px; border-radius: 999px;
}}
.step-scope {{ font-size: 10.5px; color: #4b5563; margin: 4px 0 2px; }}
.step-remaining {{ font-size: 10.5px; color: #92400e; background: #fef3c7;
  padding: 4px 8px; border-radius: 4px; margin: 4px 0; }}
.step-evidence {{ font-size: 10.5px; color: #166534; background: #dcfce7;
  padding: 4px 8px; border-radius: 4px; margin: 4px 0; }}
.step-meta {{ font-size: 9.5px; color: #9ca3af; margin-top: 2px; }}
section {{ margin: 10px 0; }}
.footer {{
  margin-top: 22px; padding-top: 8px; border-top: 1px solid #e5e7eb;
  font-size: 9.5px; color: #9ca3af; text-align: center;
}}
</style>
</head>
<body>
  <div class="header">
    <h1>{_esc(title) or "Verify Report"}</h1>
    <div class="meta">
      <span class="badge">{emoji} {label}</span>
      &nbsp;• <b>پروژه:</b> {_esc(project) or '—'}
      &nbsp;• <b>priority:</b> {_esc(priority) or '—'}
      &nbsp;• <b>نوع:</b> {_esc(task_type) or '—'}
      &nbsp;• <b>streak:</b> {_esc(streak_str)}
      &nbsp;• <b>اعتماد:</b> {int(confidence * 100)}%
      &nbsp;• <b>آخرین verify:</b> {_esc(last_verified) or '—'}
    </div>
  </div>

  {summary_html}
  {checklist_html}
  {done_html}
  {remaining_html}
  {next_html}
  {acs_html}
  {tf_html}
  {raw_idea_html}
  {prompt_html}

  <div class="footer">
    گزارش خودکار سامانهٔ نظارت — برای جزئیات بیشتر به /oversight مراجعه کنید
  </div>
</body>
</html>
"""


async def build_verify_report_pdf(
    task: Any, report: Any = None, *, filename_prefix: str = "verify",
) -> Tuple[bytes, str]:
    """تولید PDF از گزارش verify (یا brief تسک اگر report=None).
    خروجی: (bytes, filename).

    اگر playwright در دسترس نباشد، خروجی به‌صورت HTML خام برمی‌گردد
    (filename با پسوند .html). استفاده‌کننده می‌تواند آن را به‌عنوان
    سند ارسال کند (telegram سند به هر فرمتی می‌پذیرد).

    `filename_prefix` پیشوند نام فایل را تعیین می‌کند ("verify" یا "task").
    """
    html_doc = _build_verify_report_html(task, report)
    safe_title = (getattr(task, "title", "") or filename_prefix).strip()[:50]
    safe_title = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in safe_title) or filename_prefix
    filename_base = f"{filename_prefix}-{safe_title}-{(getattr(task, 'id', '') or '')[:8]}"

    try:
        from .browser_automation import PLAYWRIGHT_AVAILABLE  # noqa
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("playwright not available")
        from playwright.async_api import async_playwright
        # 🔒 serialize کن — جلوگیری از چند chromium instance هم‌زمان
        async with _PDF_RENDER_SEMAPHORE:
            playwright = await async_playwright().start()
            try:
                browser = await playwright.chromium.launch(
                    headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"]
                )
                try:
                    context = await browser.new_context()
                    page = await context.new_page()
                    # ⚠ از `networkidle` استفاده نکن — اگر CDN فونت قابل
                    # دسترسی نباشد، تا ۱۵ ثانیه می‌چرخد. `domcontentloaded`
                    # سریع است و فونت‌های fallback (Tahoma/Arial) Persian
                    # را به‌خوبی رندر می‌کنند.
                    await page.set_content(
                        html_doc,
                        wait_until="domcontentloaded",
                        timeout=8000,
                    )
                    # یک فرصت کوتاه به مرورگر بده تا CSS را اعمال کند
                    # (شامل تلاش غیرblocking برای فونت). اگر CDN در دسترس
                    # نبود، بعد از 600ms با fallback ادامه می‌دهیم.
                    try:
                        await page.wait_for_timeout(600)
                    except Exception:
                        pass
                    pdf_bytes = await page.pdf(
                        format="A4",
                        margin={"top": "15mm", "right": "15mm", "bottom": "15mm", "left": "15mm"},
                        print_background=True,
                    )
                    return pdf_bytes, f"{filename_base}.pdf"
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
        logger.warning(f"PDF render via playwright failed ({e}); falling back to HTML attachment")
        return html_doc.encode("utf-8"), f"{filename_base}.html"
