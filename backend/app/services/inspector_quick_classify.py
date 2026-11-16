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
