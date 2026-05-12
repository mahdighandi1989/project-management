"""
Strong Prompt Builder
=====================
سازندهٔ template پرامپت اجرایی فوق‌العاده دقیق برای تسک‌های oversight.
این template در همهٔ مسیرها (scan، idea_to_prompt، deep scan، ...) استفاده می‌شود.

ساختار خروجی:
  🎯 هدف
  📍 موقعیت دقیق در پروژه (با file:line و snippet)
  🧭 هدف اصلی پروژه (یادداشت کاربر)
  🧱 پشتهٔ فناوری و معماری
  🔗 فایل‌های مرتبط (cross-references)
  🌐 نقشهٔ وابستگی‌ها
  🔍 Context و وضعیت فعلی
  ✅ معیار پذیرش (Acceptance Criteria)
  🪜 مراحل اجرایی پیشنهادی
  💡 نمونه‌های قبل/بعد (اختیاری)
  📤 خروجی مورد انتظار
  🧪 دستورات اعتبارسنجی
  ⚠️ ریسک‌ها و موارد احتیاط
  🔗 وابستگی‌های تسکی
  🏷 دسته‌بندی
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any, Union


# ─────────────────────────────────────────────────────────────────────────────
# DISCLAIMER — همیشه ابتدای هر پرامپت تولیدشده درج می‌شود.
# هدف: مدل اجراکنندهٔ خارجی (Cursor, ChatGPT, Claude Code, ...) متوجه باشد که:
#   1. این پرامپت بر اساس بررسی اولیه است — قطعی نیست
#   2. مسئولیت بررسی مستقل با خود مدل است
#   3. اگر کار طولانی است، چند کامیت متوالی مجاز است (skip ممنوع)
# ─────────────────────────────────────────────────────────────────────────────

EXECUTOR_DISCLAIMER = """## ⚠️ یادداشت مهم برای مدل اجراکننده — قبل از شروع بخوان

این پرامپت بر اساس یک **بررسی اولیهٔ خودکار** از repo ساخته شده — ممکن است
حاوی اشتباه، تشخیص نادرست، یا حذف موارد مهم باشد. به‌عنوان منبع نهایی به
آن استناد نکن.

🔍 **مسئولیت تو (مدل اجراکننده):**
- پیش از هر تغییر، خودت ساختار repo، فایل‌های ذکرشده، و وابستگی‌های آن‌ها را
  مستقل بررسی کن.
- اگر تشخیص دادی موقعیت ذکرشده در پرامپت اشتباه است یا فایل دیگری مناسب‌تر
  است، بر اساس قضاوت خودت عمل کن — این پرامپت نمی‌تواند بهانهٔ کار اشتباه
  باشد ("خودت گفتی" قابل قبول نیست).
- اگر معیارهای پذیرش (AC) مبهم/ناقص بودند، بهترین تفسیر را انتخاب کن و در
  commit message توضیح بده.

📦 **اگر کار طولانی است:**
- **خلاصه‌اش نکن.** همه را به‌طور کامل انجام بده.
- اگر یک کامیت گنجایش ندارد، در **چندین کامیت متوالی** انجام بده — ولی
  هیچ بخشی را skip نکن.
- ترتیب کامیت‌ها را منطقی نگه‌دار (foundation → core → integration → tests).
- در آخر یک checklist از همه‌ی کامیت‌ها در PR description بنویس.

---
"""


def _normalize_locations(
    target_locations: Optional[List[Union[Dict[str, Any], str]]],
    legacy_target_files: Optional[List[str]],
) -> List[Dict[str, Any]]:
    """ادغام target_locations جدید (dict) و target_files قدیمی (str) به ساختار یکسان."""
    out: List[Dict[str, Any]] = []
    if target_locations:
        for item in target_locations:
            if isinstance(item, str):
                out.append({"path": item})
            elif isinstance(item, dict) and item.get("path"):
                out.append({k: v for k, v in item.items() if v not in (None, "")})
    if legacy_target_files:
        existing = {o.get("path") for o in out}
        for p in legacy_target_files:
            if p and p not in existing:
                out.append({"path": p})
    return out


def _format_location(loc: Dict[str, Any]) -> str:
    """فرمت یک ردیف موقعیت با مسیر:خط، نام تابع/کلاس، و snippet کد."""
    path = (loc.get("path") or "").strip()
    if not path:
        return ""
    lines = (loc.get("lines") or loc.get("line_range") or "").strip()
    line_start = loc.get("line_start")
    line_end = loc.get("line_end")
    if not lines and line_start:
        lines = str(line_start) + (f"-{line_end}" if line_end and line_end != line_start else "")
    symbol = (loc.get("symbol") or loc.get("function") or loc.get("class") or "").strip()
    snippet = (loc.get("snippet") or loc.get("code_snippet") or "").strip()
    note = (loc.get("note") or loc.get("reason") or "").strip()

    label = f"`{path}"
    if lines:
        label += f":{lines}"
    label += "`"
    if symbol:
        label += f" — `{symbol}`"
    if note:
        label += f" — {note}"

    out = f"- {label}"
    if snippet:
        # detect language for fence
        lang = ""
        low = path.lower()
        if low.endswith((".ts", ".tsx")):
            lang = "tsx"
        elif low.endswith(".js") or low.endswith(".jsx"):
            lang = "jsx"
        elif low.endswith(".py"):
            lang = "python"
        elif low.endswith((".json",)):
            lang = "json"
        elif low.endswith((".sql",)):
            lang = "sql"
        elif low.endswith((".md",)):
            lang = "markdown"
        out += f"\n  ```{lang}\n  " + snippet.replace("\n", "\n  ") + "\n  ```"
    return out


def _format_related_files(related: List[Dict[str, Any]]) -> str:
    """فرمت لیست فایل‌های مرتبط با ذکر دلیل (imports / imported_by / calls / shares_state)."""
    lines: List[str] = []
    for r in related:
        if isinstance(r, str):
            lines.append(f"- `{r}`")
            continue
        path = (r.get("path") or "").strip()
        if not path:
            continue
        reason = (r.get("reason") or r.get("relation") or "").strip()
        ref_line = (r.get("at_line") or r.get("line") or "").strip() if isinstance(r.get("at_line") or r.get("line"), str) else r.get("at_line") or r.get("line")
        suffix = ""
        if ref_line:
            suffix += f" (سطر {ref_line})"
        if reason:
            lines.append(f"- `{path}`{suffix} — {reason}")
        else:
            lines.append(f"- `{path}`{suffix}")
    return "\n".join(lines)


def build_strong_prompt(
    *,
    title: str,
    user_goal: str = "",
    raw_user_request: str = "",  # 🆕 متن خام کاربر (verbatim) — هرگز خلاصه نشود
    description: str = "",
    proposed_action: str = "",
    context_snippet: str = "",
    target_files: Optional[List[str]] = None,
    target_locations: Optional[List[Union[Dict[str, Any], str]]] = None,
    related_files: Optional[List[Union[Dict[str, Any], str]]] = None,
    dependency_summary: str = "",
    tech_context: str = "",
    before_after_examples: Optional[List[Dict[str, str]]] = None,
    acceptance_criteria: Optional[List[str]] = None,
    steps: Optional[List[str]] = None,
    validation_commands: Optional[List[str]] = None,
    expected_output: str = "",
    risks: str = "",
    dependencies: Optional[List[str]] = None,
    type_: str = "other",
    priority: str = "medium",
    estimate: str = "medium",
) -> str:
    """ساخت پرامپت اجرایی با ساختار استاندارد و عمق بالا برای ابزارهای کدنویس خارجی.

    🆕 پارامتر raw_user_request (مهم):
      متن خام کاربر — اگر داده شود، **به‌صورت verbatim** در ابتدای پرامپت
      قرار می‌گیرد (هرگز خلاصه/تغییر نمی‌کند). این تضمین می‌کند URLs،
      آدرس‌ها، نام‌ها، کلمات کلیدی هرگز گم نشوند، حتی اگر AI ضعیف باشد.

    پارامترهای کلیدی:
    - target_locations: لیست dictهای {"path","lines","line_start","line_end","symbol","snippet","note"}
      جایگزین قوی‌تر برای target_files (که فقط مسیر می‌گیرد).
    - related_files: لیست dictهای {"path","reason","at_line"} — برای راهنمایی به فایل‌های اطراف
      که این تسک با آنها در ارتباط است (importها، callerها، state share).
    - dependency_summary: متن کوتاه دربارهٔ نقش این بخش در نقشهٔ وابستگی‌های پروژه.
    - tech_context: پشتهٔ فناوری/معماری مرتبط (مثل "Next.js 14 App Router + FastAPI + SQLAlchemy").
    - before_after_examples: لیست {"label","before","after"} — نمونه قبل/بعد کد.
    - validation_commands: دستورات shell که برای verify باید موفق اجرا شوند.
    """
    target_files = target_files or []
    acceptance_criteria = acceptance_criteria or []
    steps = steps or []
    dependencies = dependencies or []
    validation_commands = validation_commands or []
    before_after_examples = before_after_examples or []

    locations = _normalize_locations(target_locations, target_files)

    parts: List[str] = []

    # === ⚠️ DISCLAIMER (همیشه ابتدای پرامپت — قبل از هر چیز دیگر) ===
    parts.append(EXECUTOR_DISCLAIMER)

    # === 📥 درخواست خام کاربر (verbatim — هرگز خلاصه نشود) ===
    # این بخش حیاتی است: تضمین می‌کند URL ها، آدرس‌ها، نام‌ها، context کامل
    # کاربر در پرامپت نهایی می‌مانند، حتی اگر AI در ساختاردهی ضعیف باشد.
    if raw_user_request and raw_user_request.strip():
        parts.append(
            "## 📥 درخواست خام کاربر (verbatim — همان متنی که کاربر نوشت)\n"
            "_(همهٔ URL ها، آدرس‌ها، نام‌ها، و کلمات کلیدی در این متن دست‌نخورده هستند. "
            "بخش‌های بعدی توسط AI ساختار داده شده‌اند و ممکن است ناقص باشند — این متن مرجع اصلی است.)_\n\n"
            "```\n"
            f"{raw_user_request.strip()}\n"
            "```"
        )

    parts.append(f"## 🎯 هدف (خلاصه ساختاریافته)\n{title.strip()}")

    # === موقعیت دقیق ===
    if locations:
        loc_lines = "\n".join(_format_location(l) for l in locations if l.get("path"))
        parts.append(
            "## 📍 موقعیت دقیق در پروژه\n"
            "_(file:line — symbol — snippet)_\n\n"
            f"{loc_lines}"
        )
    else:
        parts.append(
            "## 📍 موقعیت دقیق در پروژه\n"
            "_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_"
        )

    parts.append(
        f"## 🧭 هدف اصلی پروژه (از یادداشت کاربر)\n"
        f"{(user_goal or '(کاربر یادداشتی ثبت نکرده است)').strip()}"
    )

    if tech_context:
        parts.append(f"## 🧱 پشتهٔ فناوری و معماری\n{tech_context.strip()}")

    # === فایل‌های مرتبط (cross-references) ===
    related_norm: List[Dict[str, Any]] = []
    if related_files:
        for r in related_files:
            if isinstance(r, str):
                related_norm.append({"path": r})
            elif isinstance(r, dict):
                related_norm.append(r)
    if related_norm:
        parts.append(
            "## 🔗 فایل‌های مرتبط (Cross-references)\n"
            "_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_\n\n"
            f"{_format_related_files(related_norm)}"
        )

    if dependency_summary:
        parts.append(f"## 🌐 نقشهٔ وابستگی‌ها\n{dependency_summary.strip()}")

    # === Context ===
    ctx_block = description.strip()
    if context_snippet:
        ctx_block = f"{ctx_block}\n\n```\n{context_snippet.strip()}\n```"
    parts.append(
        f"## 🔍 Context و وضعیت فعلی\n{ctx_block or '_(وضعیت فعلی توسط مجری بررسی شود)_'}"
    )

    # === Acceptance criteria ===
    ac_lines: List[str] = []
    for c in acceptance_criteria:
        c = c.strip()
        if c:
            ac_lines.append(f"- [ ] {c}")
    standard_ac = [
        "- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)",
        "- [ ] linter بدون warning عبور می‌کند",
        "- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)",
    ]
    for s in standard_ac:
        if s not in ac_lines:
            ac_lines.append(s)
    parts.append("## ✅ معیار پذیرش (Acceptance Criteria)\n" + "\n".join(ac_lines))

    # === Steps ===
    if not steps and proposed_action:
        steps = [proposed_action]
    if steps:
        step_lines = "\n".join(f"{i + 1}. {s.strip()}" for i, s in enumerate(steps) if s)
        parts.append(f"## 🪜 مراحل اجرایی پیشنهادی\n{step_lines}")
    else:
        parts.append(
            "## 🪜 مراحل اجرایی پیشنهادی\n_(مجری بر اساس Context و معیارهای پذیرش، مراحل را تعیین کند)_"
        )

    # === Before/after examples ===
    if before_after_examples:
        ex_chunks: List[str] = []
        for i, ex in enumerate(before_after_examples, 1):
            label = (ex.get("label") or f"نمونه {i}").strip()
            before = (ex.get("before") or "").strip()
            after = (ex.get("after") or "").strip()
            block = f"**{label}**"
            if before:
                block += f"\n\n_قبل:_\n```\n{before}\n```"
            if after:
                block += f"\n\n_بعد:_\n```\n{after}\n```"
            ex_chunks.append(block)
        parts.append("## 💡 نمونه‌های قبل/بعد\n" + "\n\n".join(ex_chunks))

    parts.append(
        f"## 📤 خروجی مورد انتظار\n{(expected_output or 'تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.').strip()}"
    )

    # === Validation commands ===
    if validation_commands:
        cmd_lines = "\n".join(f"- `{c.strip()}`" for c in validation_commands if c.strip())
        parts.append(f"## 🧪 دستورات اعتبارسنجی\n{cmd_lines}")

    parts.append(
        f"## ⚠️ ریسک‌ها و موارد احتیاط\n"
        f"{(risks or 'پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.').strip()}"
    )

    if dependencies:
        dep_lines = "\n".join(f"- {d}" for d in dependencies if d)
        parts.append(f"## 🔗 وابستگی‌های تسکی\n{dep_lines}")
    else:
        parts.append("## 🔗 وابستگی‌های تسکی\n_(مستقل)_")

    parts.append(
        f"## 🏷 دسته‌بندی\n- نوع: {type_}\n- اولویت: {priority}\n- تخمین زمان: {estimate}"
    )

    return "\n\n".join(parts)


def extract_target_files(prompt: str) -> List[str]:
    """استخراج فایل‌های موقعیت از یک پرامپت قوی (فقط path، حتی اگر `path:line` باشد).

    سازگار با هر دو فرمت:
      ## 📍 موقعیت دقیق در پروژه       (نسخهٔ جدید)
      ## 📍 موقعیت در پروژه               (نسخهٔ قدیمی)
    """
    import re

    files: List[str] = []
    match = re.search(
        r"##\s*\S*\s*موقعیت(?:\s+دقیق)?\s+در پروژه[^\n]*\n(.+?)(?=\n##|\Z)",
        prompt,
        re.DOTALL,
    )
    if not match:
        return files
    block = match.group(1)
    # فقط خط‌های اصلی (نه snippetهای داخل code-fence)
    in_fence = False
    for raw in block.splitlines():
        line = raw.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        line = line.lstrip("-").strip()
        # اولین قطعه‌ای که داخل backtick است معمولاً path یا path:line است
        m = re.search(r"`([^`]+)`", line)
        if m:
            tok = m.group(1).strip()
        else:
            tok = line
        if not tok or tok.startswith("_") or tok.startswith("("):
            continue
        # تفکیک path:line — فقط path را نگه می‌داریم
        if ":" in tok:
            head, tail = tok.split(":", 1)
            # اگر دم رشته شامل "/" نیست → احتمالاً line range است → فقط head
            if "/" not in tail:
                tok = head
        # حذف symbol بعد از path (مثل `path` — `func`)
        tok = tok.split(" ")[0].strip("`").strip()
        if "/" in tok or "." in tok:
            files.append(tok)
    seen = set()
    out = []
    for f in files:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def extract_target_locations(prompt: str) -> List[Dict[str, Any]]:
    """استخراج موقعیت‌های دقیق (path + line range + symbol) از پرامپت — برای استفادهٔ verifier."""
    import re

    locations: List[Dict[str, Any]] = []
    match = re.search(
        r"##\s*\S*\s*موقعیت(?:\s+دقیق)?\s+در پروژه[^\n]*\n(.+?)(?=\n##|\Z)",
        prompt,
        re.DOTALL,
    )
    if not match:
        return locations
    block = match.group(1)
    in_fence = False
    for raw in block.splitlines():
        line = raw.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not line.startswith("-"):
            continue
        rest = line.lstrip("-").strip()
        # اول backtick: path[:line]
        m = re.search(r"`([^`]+)`", rest)
        if not m:
            continue
        tok = m.group(1).strip()
        path = tok
        lines_str = ""
        if ":" in tok:
            head, tail = tok.split(":", 1)
            if "/" not in tail:
                path = head
                lines_str = tail
        # دوم backtick (اگر بود): symbol
        rest_after = rest[m.end():]
        sym = ""
        m2 = re.search(r"`([^`]+)`", rest_after)
        if m2:
            sym = m2.group(1).strip()
        if "/" in path or "." in path:
            loc = {"path": path}
            if lines_str:
                loc["lines"] = lines_str
            if sym:
                loc["symbol"] = sym
            locations.append(loc)
    # dedup
    seen = set()
    out: List[Dict[str, Any]] = []
    for l in locations:
        key = (l.get("path"), l.get("lines"), l.get("symbol"))
        if key not in seen:
            seen.add(key)
            out.append(l)
    return out


def extract_acceptance_criteria(prompt: str) -> List[str]:
    """استخراج معیارهای پذیرش از یک پرامپت قوی."""
    import re

    match = re.search(
        r"##\s*\S*\s*معیار پذیرش.*?\n(.+?)(?=\n##|\Z)",
        prompt,
        re.DOTALL,
    )
    if not match:
        return []
    block = match.group(1)
    items: List[str] = []
    for line in block.splitlines():
        s = line.strip()
        m = re.match(r"^-\s*\[[ xX]\]\s*(.+)$", s)
        if m:
            items.append(m.group(1).strip())
            continue
        m = re.match(r"^-\s+(.+)$", s)
        if m and not s.startswith("-_"):
            items.append(m.group(1).strip())
    return items
