"""(PM-INS-0007) Deterministic pre-classifier for the inspector chat.

The LLM classifier is told "when in doubt ⇒ ACTION", so a plain lookup like
«آخرین commit چیست؟» went down the expensive agent path (~51k tokens) on a
cheaper model. A short message that is clearly a question and mentions no
problem, error or change request is answered as a QUESTION without asking a
model at all. Anything ambiguous still goes to the LLM classifier.
"""
from __future__ import annotations

import re

_PROBLEM_WORDS = (
    # Persian: broken / error / fix / change / build
    "کار نمی", "کار نمي", "کارنمی", "خراب", "خطا", "ارور", "اشکال", "ایراد", "باگ", "مشکل",
    "درست کن", "درستش", "اصلاح", "رفع", "تغییر بده", "عوض کن", "اضافه کن", "حذف کن", "بساز",
    "بنویس", "پیاده", "اعمال", "دیپلوی کن", "ریستارت", "برگرد", "برگردون", "چرا",
    # English
    "error", "bug", "broken", "fail", "crash", "fix", "exception", "traceback", "not working",
    "add ", "remove ", "delete ", "create ", "implement", "deploy", "revert", "why",
)

_QUESTION_MARKERS = (
    "چیست", "چیه", "چی است", "چه ", "کدام", "کدوم", "کی ", "کجا", "چند", "چطور", "چگونه",
    "آیا", "بگو", "نشان بده", "نشون بده", "لیست",
    "what", "which", "when", "who", "how many", "show me", "list ",
)

_MAX_LEN = 160


def is_simple_info_question(message: str) -> bool:
    """True ⇒ a short, problem-free lookup question (no model needed to classify it)."""
    text = (message or "").strip()
    if not text or len(text) > _MAX_LEN or "\n" in text:
        return False
    low = text.lower()
    if any(w in low for w in _PROBLEM_WORDS):
        return False
    if re.search(r"(traceback|stack trace|\w+error\b|status \d{3})", low):
        return False
    asks = text.endswith(("?", "؟")) or any(m in low for m in _QUESTION_MARKERS)
    return asks


# (PM-INS-0029) «کوتاه بگو چه کنم؟ (فقط پاسخ، تغییر فایل نه)» — a how-to question that NAMES a problem («کار نمی‌کند»،
# «خطای ERR_…») is still a question. It went to a deep scan (semantic_only_vague, 0 paths) and no answer came for minutes.
_ANSWER_ONLY = (
    "فقط پاسخ", "فقط جواب", "فقط توضیح", "فقط بگو", "تغییر فایل نه", "فایل را تغییر نده", "فایلی را تغییر نده",
    "بدون تغییر فایل", "بدونِ تغییرِ فایل", "بدون تغییر کد", "کدی تغییر نده", "چیزی تغییر نده", "دست نزن",
    "just answer", "only answer", "answer only", "no file change", "no code change", "don't change", "do not change",
    "without changing",
)
_HOWTO = ("چه کنم", "چکار کنم", "چی کار کنم", "چیکار کنم", "چه باید کرد", "چطور", "چگونه", "راه حل چیست", "راه‌حل چیست",
          "چه کار کنم", "how do i", "how can i", "what should i", "how to ")
_CHANGE_ASK = ("درست کن", "درستش کن", "اصلاح کن", "اعمال کن", "بساز", "بنویس", "اضافه کن", "حذف کن", "عوض کن",
               "تغییر بده", "پیاده کن", "پیاده‌سازی کن", "commit", "push", " pr", "fix it", "implement", "create ", "add ",
               "change the", "update the")


def is_answer_only(message: str) -> bool:
    """True ⇒ the user wants a TEXT answer: an explicit «فقط پاسخ / تغییر فایل نه», or a short how-to question
    («چه کنم؟», «چطور …؟») that asks for no change. Never a scan, never an action_plan."""
    text = (message or "").strip()
    if not text or len(text) > 600:
        return False
    low = text.lower()
    if any(m in low for m in _ANSWER_ONLY):
        return True
    if any(c in low for c in _CHANGE_ASK):
        return False
    return text.rstrip(" ).»").endswith(("?", "؟")) and any(h in low for h in _HOWTO)
