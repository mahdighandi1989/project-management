"""PM-INS-0039 — the resolution status of an experience, decided from its TEXT.

Before this, the catalog took ``resolution_status`` only from the frontmatter.
Experiences written at the end of a coding task almost never carry that key, so
~87% of the catalog sat at «unknown» and the «وضعیت» filter (and the assistant)
could not tell a solved experience from an unfinished one.

``infer_resolution_status`` reads the whole file and returns
``(status, source, evidence)``:

* ``frontmatter`` — the author wrote it; never overridden.
* ``resolution-section`` — a «## ✅ Resolution» block with ``Status: …``.
* ``text`` — the body has a real solution section (⇒ solved), or says in so
  many words that it is unfinished (⇒ open).
* ``ambiguous`` — a solution AND an explicit «still open» signal. The caller may
  ask a cheap model; without one the honest answer is ``partial``.
* ``none`` — no evidence either way ⇒ ``unknown`` (the only case it remains).

Every decision carries a one-line evidence string that the catalog shows, so a
wrong label can be traced to the sentence that caused it.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

VALID = ("solved", "partial", "open", "regressed", "unknown")
DECIDED = ("solved", "partial", "open", "regressed")

_ZW = "‌‍‎‏"
_KASRA = "ِ"


def _norm(text: str) -> str:
    """Lower-case, drop ZWNJ/kasra so «راه‌حل» / «راه حل» / «کارِ» all match."""
    out = (text or "").lower()
    for ch in _ZW:
        out = out.replace(ch, " ")
    out = out.replace(_KASRA, "")
    return re.sub(r"[ \t]+", " ", out)


_FENCE = re.compile(r"```.*?```", re.S)
_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")

# A heading that introduces what was actually done.
_SOLUTION_H = re.compile(
    r"راه ?حل|رفع|اصلاح|درمان|چه کردیم|چه شد|نتیجه|"
    r"solution|\bfix(es|ed)?\b|\bresol|what worked|remedy|the pattern|approach|outcome"
)
# A heading that turns the fix into a reusable rule — written only once it worked.
_APPLY_H = re.compile(
    r"چطور در جای دیگر|چگونه در جای دیگر|اعمال کنیم|قاعده|درس|"
    r"how to apply|applies when|lesson|takeaway|rule of thumb|checklist"
)
# A heading that lists what is still owed.
_OPEN_H = re.compile(
    r"حل نشده|ناتمام|نیمه ?کاره|کار مانده|باقی ?مانده|هنوز باز|پرسش باز|سوال باز|"
    r"open question|unresolved|unsolved|still open|remaining work|\btodo\b|not yet (fixed|solved|resolved)"
)
# A sentence that says, in so many words, that the problem is not closed.
_OPEN_TEXT = re.compile(
    r"هنوز حل نشده|هنوز رفع نشده|هنوز باز است|مشکل پابرجاست|ریشه (هنوز )?پیدا نشد|علت (هنوز )?(روشن|معلوم|مشخص) نیست|"
    r"not yet (fixed|solved|resolved)|still (unresolved|unsolved|open|failing|broken)|"
    r"remains (open|unresolved|unfixed)|root cause (is )?(still )?unknown|work in progress|no fix yet"
)
_STATUS_LINE = re.compile(
    r"(?:^|\n)[ \t>*\-]*\**(?:resolution[_ ]status|status|وضعیت)\**[ \t]*[:：][ \t]*[`\"'*]*"
    r"(solved|partial|open|regressed)\b"
)
#: Fewer characters than this under a solution heading is a placeholder, not a solution.
MIN_SOLUTION_CHARS = 80


def _sections(content: str) -> List[Tuple[str, str]]:
    """``[(normalised heading, body without code fences)]`` — text before the
    first heading comes back under an empty heading."""
    out: List[Tuple[str, List[str]]] = [("", [])]
    in_fence = False
    for line in (content or "").splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out[-1][1].append(line)
            continue
        m = None if in_fence else _HEADING.match(line)
        if m:
            out.append((_norm(m.group(2)), []))
        else:
            out[-1][1].append(line)
    return [(h, _FENCE.sub(" ", "\n".join(body))) for h, body in out]


def _quote(text: str, match: "re.Match[str]") -> str:
    start = max(0, match.start() - 30)
    return re.sub(r"\s+", " ", text[start:match.end() + 30]).strip()


def infer_resolution_status(meta: Dict[str, Any], content: str) -> Tuple[str, str, str]:
    """``(status, source, evidence)`` for one experience file. Pure; no I/O."""
    raw = str((meta or {}).get("resolution_status") or "").strip().lower()
    if raw in DECIDED:
        return raw, "frontmatter", "نویسنده در سرآیندِ فایل نوشته است"

    sections = _sections(content)

    # 1) An explicit «Resolution» block wins over anything we could guess.
    for heading, body in sections:
        if "resolution" in heading or "وضعیت" in heading:
            m = _STATUS_LINE.search(_norm(body))
            if m:
                return m.group(1), "resolution-section", f"بخشِ Resolution: «Status: {m.group(1)}»"
    m = _STATUS_LINE.search(_norm(_FENCE.sub(" ", content or "")))
    if m:
        return m.group(1), "resolution-section", f"خطِ وضعیت در متن: «{m.group(1)}»"

    solution_chars = 0
    solution_heading = ""
    apply_heading = ""
    open_signals: List[str] = []
    for heading, body in sections:
        nbody = _norm(body)
        if heading and _OPEN_H.search(heading) and nbody.strip():
            open_signals.append(f"سرفصلِ «{heading[:60]}»")
        elif heading and _SOLUTION_H.search(heading):
            size = len(re.sub(r"\s+", "", body))
            if size > solution_chars:
                solution_chars, solution_heading = size, heading
        elif heading and _APPLY_H.search(heading) and len(nbody.strip()) >= MIN_SOLUTION_CHARS:
            apply_heading = apply_heading or heading
        hit = _OPEN_TEXT.search(nbody)
        if hit and len(open_signals) < 3:
            open_signals.append(f"«{_quote(nbody, hit)}»")

    has_solution = solution_chars >= MIN_SOLUTION_CHARS
    if has_solution and open_signals:
        return ("partial", "ambiguous",
                f"راه‌حل دارد («{solution_heading[:50]}») ولی نشانهٔ ناتمامی هم هست: {open_signals[0]}")
    if has_solution:
        return ("solved", "text",
                f"بخشِ راه‌حل دارد («{solution_heading[:50]}»، {solution_chars} نویسه) و هیچ نشانهٔ ناتمامی در متن نیست")
    if open_signals:
        return "open", "text", f"راه‌حلی ثبت نشده و متن می‌گوید ناتمام است: {open_signals[0]}"
    if apply_heading:
        return ("solved", "text",
                f"درسِ قابلِ‌اعمال نوشته شده («{apply_heading[:50]}») و هیچ نشانهٔ ناتمامی در متن نیست")
    headings = "، ".join(h[:30] for h, _ in sections if h)[:200]
    return "unknown", "none", ("شاهدی در متن نیست — نه بخشِ راه‌حل، نه خطِ وضعیت"
                               + (f" (سرفصل‌ها: {headings})" if headings else " (فایل سرفصل ندارد)"))


def build_model_prompt(title: str, content: str, evidence: str) -> str:
    """The question for a cheap model — asked ONLY for ``ambiguous`` files."""
    return (
        "این متنِ یک «تجربهٔ مهندسی» است. فقط بر اساسِ شواهدِ خودِ متن بگو وضعیتِ مسئله چیست.\n"
        "solved = راه‌حلِ نهایی اعمال شده و کار می‌کند (اشاره به تلاش‌های شکست‌خوردهٔ قبلی، آن را ناتمام نمی‌کند).\n"
        "partial = راه‌حل هست ولی بخشی صریحاً باز مانده.\n"
        "open = راه‌حلِ کارآمدی ثبت نشده.\n"
        "regressed = حل شده بود و دوباره برگشته.\n"
        "اگر مطمئن نیستی partial بگو، نه solved.\n"
        f"تشخیصِ قاعده‌ای تا این‌جا: {evidence}\n\n"
        f"# عنوان\n{title}\n\n# متن\n{(content or '')[:6000]}\n\n"
        "خروجی فقط یک خط، دقیقاً به این شکل:\nSTATUS: <solved|partial|open|regressed> — <دلیل در یک جملهٔ کوتاه>"
    )


_MODEL_ANSWER = re.compile(r"status\**\s*[:：]\s*[`\"'* ]*(solved|partial|open|regressed)\b[`\"'*]*\s*[—\-:،,]*\s*(.*)", re.I)


def parse_model_answer(answer: str) -> Tuple[str, str]:
    """``(status, reason)`` or ``("", "")`` when the model did not answer in form."""
    m = _MODEL_ANSWER.search(answer or "")
    if not m:
        return "", ""
    return m.group(1).lower(), re.sub(r"\s+", " ", m.group(2)).strip()[:200]
