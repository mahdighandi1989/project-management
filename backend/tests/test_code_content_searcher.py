"""Bug C6 — Verify v6 meta-test #1.

Unit tests برای extract_identifiers با ۴ مثال concrete (مطابق با ۴
مثال در docstring code_content_searcher.py) + یک grep test.

AC #12 از 12 AC C6 — حداقل ۴ مثال در test پاس شوند.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import pytest
except ImportError:  # pragma: no cover — graceful when pytest absent
    pytest = None  # type: ignore[assignment]

from app.services.verify_runtime.code_content_searcher import (
    extract_identifiers,
    grep_token_in_files,
)


# ---------------------------------------------------------------------------
# extract_identifiers — ۴ مثال concrete
# ---------------------------------------------------------------------------


def test_example_1_farsi_with_python_identifier():
    """مثال ۱: ورودی فارسی + identifier پایتون."""
    text = "اضافه کردن فیلد `view_preferences` به مدل WatchedProject"
    out = extract_identifiers(text)
    assert "view_preferences" in out
    assert "WatchedProject" in out


def test_example_2_english_camelcase_stopwords_filtered():
    """مثال ۲: ورودی انگلیسی + camelCase. 'Add' به‌دلیل stop-word حذف شود."""
    text = "Add useViewPrefs hook for fetching preferences"
    out = extract_identifiers(text)
    assert "useViewPrefs" in out
    # 'Add' should be filtered by stop-words
    assert "Add" not in out and "add" not in out


def test_example_3_mixed_with_file_path():
    """مثال ۳: ورودی mixed با file path."""
    text = "تابع _record_title_change در oversight_service.py"
    out = extract_identifiers(text)
    assert "_record_title_change" in out
    assert "oversight_service" in out


def test_example_4_generic_words_filtered():
    """مثال ۴: کلمات generic — همه stop-word → خروجی خالی."""
    text = "بهبود سیستم نمایش"
    out = extract_identifiers(text)
    assert out == []


# ---------------------------------------------------------------------------
# grep_token_in_files — یک تست ساده روی in-memory cache
# ---------------------------------------------------------------------------


@(pytest.mark.asyncio if pytest is not None else (lambda f: f))
async def test_grep_token_in_files_returns_matches_from_content_cache():
    """grep_token_in_files باید روی فایل‌های موجود در file_content_cache
    کار کند (بدون نیاز به GitHub API call)."""
    file_content_cache = {
        "src/foo.py@main": (
            "def hello():\n"
            "    return 'view_preferences set'\n"
            "\n"
            "class WatchedProject:\n"
            "    pass\n"
        )
    }
    cache: dict = {}
    matches = await grep_token_in_files(
        "view_preferences",
        ["src/foo.py"],
        "owner/repo",
        "main",
        github_token="",
        cache=cache,
        file_content_cache=file_content_cache,
    )
    assert isinstance(matches, list)
    assert len(matches) >= 1
    assert matches[0]["path"] == "src/foo.py"
    assert matches[0]["line_number"] == 2
    assert "view_preferences" in matches[0]["snippet"]
