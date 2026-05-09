"""
Strong Prompt Builder
=====================
سازندهٔ template پرامپت اجرایی فوق‌العاده دقیق برای تسک‌های oversight.
این template در همهٔ مسیرها (scan، idea_to_prompt، deep scan، ...) استفاده می‌شود.
"""

from __future__ import annotations
from typing import List, Optional


def build_strong_prompt(
    *,
    title: str,
    user_goal: str = "",
    description: str = "",
    proposed_action: str = "",
    context_snippet: str = "",
    target_files: Optional[List[str]] = None,
    acceptance_criteria: Optional[List[str]] = None,
    steps: Optional[List[str]] = None,
    expected_output: str = "",
    risks: str = "",
    dependencies: Optional[List[str]] = None,
    type_: str = "other",
    priority: str = "medium",
    estimate: str = "medium",
) -> str:
    """ساخت پرامپت اجرایی با ساختار استاندارد."""
    target_files = target_files or []
    acceptance_criteria = acceptance_criteria or []
    steps = steps or []
    dependencies = dependencies or []

    parts: List[str] = []

    parts.append(f"## 🎯 هدف\n{title.strip()}")

    if target_files:
        loc_lines = "\n".join(f"- `{p}`" for p in target_files if p)
        parts.append(f"## 📍 موقعیت در پروژه\n{loc_lines}")
    else:
        parts.append(
            "## 📍 موقعیت در پروژه\n_(فایل‌های دقیق هنگام اجرا شناسایی شوند)_"
        )

    parts.append(
        f"## 🧭 هدف اصلی پروژه (از یادداشت کاربر)\n"
        f"{(user_goal or '(کاربر یادداشتی ثبت نکرده است)').strip()}"
    )

    ctx_block = description.strip()
    if context_snippet:
        ctx_block = f"{ctx_block}\n\n```\n{context_snippet.strip()}\n```"
    parts.append(
        f"## 🔍 Context و وضعیت فعلی\n{ctx_block or '_(وضعیت فعلی توسط مجری بررسی شود)_'}"
    )

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

    if not steps and proposed_action:
        steps = [proposed_action]
    if steps:
        step_lines = "\n".join(f"{i + 1}. {s.strip()}" for i, s in enumerate(steps) if s)
        parts.append(f"## 🪜 مراحل اجرایی پیشنهادی\n{step_lines}")
    else:
        parts.append(
            "## 🪜 مراحل اجرایی پیشنهادی\n_(مجری بر اساس Context و معیارهای پذیرش، مراحل را تعیین کند)_"
        )

    parts.append(
        f"## 📤 خروجی مورد انتظار\n{(expected_output or 'تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.').strip()}"
    )

    parts.append(
        f"## ⚠️ ریسک‌ها و موارد احتیاط\n"
        f"{(risks or 'پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.').strip()}"
    )

    if dependencies:
        dep_lines = "\n".join(f"- {d}" for d in dependencies if d)
        parts.append(f"## 🔗 وابستگی‌ها\n{dep_lines}")
    else:
        parts.append("## 🔗 وابستگی‌ها\n_(مستقل)_")

    parts.append(
        f"## 🏷 دسته‌بندی\n- نوع: {type_}\n- اولویت: {priority}\n- تخمین زمان: {estimate}"
    )

    return "\n\n".join(parts)


def extract_target_files(prompt: str) -> List[str]:
    """استخراج فایل‌های موقعیت از یک پرامپت قوی."""
    import re

    files: List[str] = []
    match = re.search(
        r"##\s*\S*\s*موقعیت در پروژه\s*\n(.+?)(?=\n##|\Z)",
        prompt,
        re.DOTALL,
    )
    if not match:
        return files
    block = match.group(1)
    for line in block.splitlines():
        line = line.strip().lstrip("-").strip()
        line = line.strip("`").strip()
        if not line or line.startswith("_") or line.startswith("("):
            continue
        if ":" in line and "/" not in line.split(":", 1)[1]:
            line = line.split(":", 1)[0]
        if "/" in line or "." in line:
            files.append(line.strip())
    seen = set()
    out = []
    for f in files:
        if f not in seen:
            seen.add(f)
            out.append(f)
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
