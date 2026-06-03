"""Bug C6 Addendum — Verify v7 meta-tests.

تست‌های unit برای helper های Verify v7:
  - _classify_task_type
  - _get_weights_for_task
  - _resolve_done_remaining_contradictions_v7
  - _jaccard_word_similarity
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# _classify_task_type
# ---------------------------------------------------------------------------


def _make_task(target_files=None, prompt: str = "", title: str = ""):
    t = MagicMock()
    t.target_files = target_files or []
    t.prompt = prompt
    t.title = title
    return t


def test_classify_pure_backend():
    from app.services.verify_runtime.iterative_orchestrator import _classify_task_type
    t = _make_task(target_files=[
        "backend/app/api/routes/render_logs.py",
        "backend/app/services/oversight_service.py",
    ])
    assert _classify_task_type(t) == "pure_backend"


def test_classify_pure_frontend():
    from app.services.verify_runtime.iterative_orchestrator import _classify_task_type
    t = _make_task(target_files=[
        "frontend/src/app/oversight/page.tsx",
        "frontend/src/app/projects/[id]/page.tsx",
    ])
    assert _classify_task_type(t) == "pure_frontend"


def test_classify_fullstack():
    from app.services.verify_runtime.iterative_orchestrator import _classify_task_type
    t = _make_task(target_files=[
        "backend/app/api/routes/render_logs.py",
        "frontend/src/app/oversight/page.tsx",
    ])
    assert _classify_task_type(t) == "fullstack"


def test_classify_infra():
    from app.services.verify_runtime.iterative_orchestrator import _classify_task_type
    t = _make_task(target_files=[
        "Dockerfile",
        ".github/workflows/ci.yml",
        "docker-compose.yml",
    ])
    assert _classify_task_type(t) == "infra"


def test_classify_docs_only():
    from app.services.verify_runtime.iterative_orchestrator import _classify_task_type
    t = _make_task(target_files=["README.md", "CHANGELOG.md", "docs/spec.txt"])
    assert _classify_task_type(t) == "docs_only"


def test_classify_test_only():
    from app.services.verify_runtime.iterative_orchestrator import _classify_task_type
    t = _make_task(target_files=[
        "backend/tests/test_iterative_orchestrator.py",
        "backend/tests/test_verify_v7.py",
    ])
    assert _classify_task_type(t) == "test_only"


def test_classify_empty_target_files_uses_prompt_heuristic():
    from app.services.verify_runtime.iterative_orchestrator import _classify_task_type
    # backend keywords in prompt
    t = _make_task(target_files=[], prompt="Add a new endpoint to FastAPI router with SQLAlchemy")
    assert _classify_task_type(t) == "pure_backend"
    # frontend keywords
    t2 = _make_task(target_files=[], prompt="Add a new React component with useState and Tailwind")
    assert _classify_task_type(t2) == "pure_frontend"
    # neither
    t3 = _make_task(target_files=[], prompt="general improvement")
    assert _classify_task_type(t3) == "mixed_unknown"


# ---------------------------------------------------------------------------
# _get_weights_for_task
# ---------------------------------------------------------------------------


def test_weights_backend_deprioritizes_ui():
    from app.services.verify_runtime.iterative_orchestrator import _get_weights_for_task
    t = _make_task(target_files=["backend/app/api/routes/x.py"])
    w = _get_weights_for_task(t)
    assert w["ui_interaction"] == 0.1
    assert w["code_aware_basename"] == 2.5
    assert w["api_probe"] == 2.0


def test_weights_frontend_prioritizes_ui():
    from app.services.verify_runtime.iterative_orchestrator import _get_weights_for_task
    t = _make_task(target_files=["frontend/src/page.tsx"])
    w = _get_weights_for_task(t)
    assert w["ui_interaction"] == 2.0
    assert w["playwright"] == 2.5


def test_weights_docs_only_skips_probes():
    from app.services.verify_runtime.iterative_orchestrator import _get_weights_for_task
    t = _make_task(target_files=["README.md"])
    w = _get_weights_for_task(t)
    assert w["ui_interaction"] == 0.0
    assert w["api_probe"] == 0.0
    assert w["code_aware_basename"] == 3.0


def test_weights_fallback_for_unknown():
    from app.services.verify_runtime.iterative_orchestrator import (
        _get_weights_for_task, WEIGHTS_BY_PROBE,
    )
    t = _make_task(target_files=[], prompt="vague stuff")
    w = _get_weights_for_task(t)
    # برای mixed_unknown از WEIGHTS_BY_PROBE استفاده می‌شود
    assert w["content_grep_strong"] == WEIGHTS_BY_PROBE["content_grep_strong"]


# ---------------------------------------------------------------------------
# _resolve_done_remaining_contradictions_v7
# ---------------------------------------------------------------------------


def test_resolver_removes_contradicting_remaining():
    """🆕 (Verify v8 Tighten) — resolver حالا conservative است. Jaccard
    threshold از 0.5 → 0.7 رفته (در commit fc19d4a، برای فیکس باگ کاربر
    که 9/9 done ولی 11 آیتم در remaining داشت). آیتم‌هایی که فقط چند
    کلمه مشترک دارند (Jaccard 0.5-0.7) دیگر merge نمی‌شوند — به‌جایش
    consistency guard در سطح بالاتر (verify_task) جلوی auto-archive
    کاذب را می‌گیرد.

    برای مرج کردن: Jaccard ≥ 0.7 یا substring ≥ 40 char لازم است.
    """
    from app.services.oversight_verifier import (
        _resolve_done_remaining_contradictions_v7,
        _jaccard_word_similarity,
    )
    # حالت ۱: شباهت متوسط (Jaccard ~0.55) — دیگر merge نمی‌شود
    done_mid = ["فاز 0 — بازرسی کیفیت و باگ‌یابی بازرس ویژه پیاده‌سازی شد"]
    remaining_mid = ["فاز 0: بازرسی کیفیت بازرس ویژه انجام نشده"]
    sim = _jaccard_word_similarity(done_mid[0].lower(), remaining_mid[0].lower())
    assert 0.5 <= sim < 0.7  # exactly the case we DON'T merge anymore
    out = _resolve_done_remaining_contradictions_v7(done_mid, remaining_mid)
    assert len(out) == 1  # safety guard wins

    # حالت ۲: شباهت قوی (Jaccard ≥ 0.7) — همچنان merge می‌شود
    done_high = ["فاز ۳ اتصال مرکز نظارت بازرس انجام شد"]
    remaining_high = ["فاز ۳ اتصال مرکز نظارت بازرس انجام نشده"]
    sim_high = _jaccard_word_similarity(done_high[0].lower(), remaining_high[0].lower())
    assert sim_high >= 0.7
    out_high = _resolve_done_remaining_contradictions_v7(done_high, remaining_high)
    assert len(out_high) == 0


def test_resolver_does_not_merge_distinct_features_sharing_words():
    """Regression for the original user-reported bug: 9/9 checklist done
    but 11 distinct items left in remaining were getting silently merged
    by the loose Jaccard threshold. Two items that talk about *different*
    features but share common words (endpoint, اضافه, پروژه) must STAY
    separate now."""
    from app.services.oversight_verifier import _resolve_done_remaining_contradictions_v7
    done = ["endpoint /chat-stream اضافه شد به پروژه backend"]
    remaining = ["endpoint /chat-cloud-code اضافه نشده به پروژه backend"]
    out = _resolve_done_remaining_contradictions_v7(done, remaining)
    # کلمات مشترک زیادند ولی موضوع متفاوت است — نباید merge شود
    assert len(out) == 1
    assert "cloud-code" in out[0]


def test_resolver_preserves_truly_remaining_items():
    from app.services.oversight_verifier import _resolve_done_remaining_contradictions_v7
    done = ["فاز 1 — verify v6 پیاده شد"]
    remaining = ["یک feature کاملاً متفاوت که هنوز باید انجام شود"]
    out = _resolve_done_remaining_contradictions_v7(done, remaining)
    assert len(out) == 1  # متن متفاوت → باید بماند


def test_resolver_code_aware_implemented_wins():
    from app.services.oversight_verifier import _resolve_done_remaining_contradictions_v7
    done: list = []
    remaining = ["فاز 3: اتصال مرکز نظارت به بازرس ویژه انجام نشده"]
    step_code_verdicts = {
        3: {"verdict": "implemented", "reason": "همهٔ AC files موجود اند"}
    }
    task_steps_list = [
        {"id": 3, "title": "فاز 3: اتصال مرکز نظارت به بازرس ویژه", "scope": ""},
    ]
    out = _resolve_done_remaining_contradictions_v7(
        done, remaining,
        step_code_verdicts=step_code_verdicts,
        task_steps_list=task_steps_list,
    )
    # code-aware گفته implemented → از remaining حذف شود
    assert len(out) == 0


def test_jaccard_similarity():
    from app.services.oversight_verifier import _jaccard_word_similarity
    # متن یکسان
    assert _jaccard_word_similarity("hello world test", "hello world test") == 1.0
    # هیچ کلمهٔ مشترکی نیست
    assert _jaccard_word_similarity("abc def", "ghi jkl") == 0.0
    # نیمی مشترک
    sim = _jaccard_word_similarity("alpha beta gamma", "alpha beta delta")
    assert 0.4 < sim < 0.7
    # خالی
    assert _jaccard_word_similarity("", "anything") == 0.0


# ---------------------------------------------------------------------------
# inline runner
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    tests = [
        test_classify_pure_backend,
        test_classify_pure_frontend,
        test_classify_fullstack,
        test_classify_infra,
        test_classify_docs_only,
        test_classify_test_only,
        test_classify_empty_target_files_uses_prompt_heuristic,
        test_weights_backend_deprioritizes_ui,
        test_weights_frontend_prioritizes_ui,
        test_weights_docs_only_skips_probes,
        test_weights_fallback_for_unknown,
        test_resolver_removes_contradicting_remaining,
        test_resolver_preserves_truly_remaining_items,
        test_resolver_code_aware_implemented_wins,
        test_jaccard_similarity,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"✅ {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"❌ {t.__name__} — {type(e).__name__}: {e}")
            failed += 1
    print(f"\nResults: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
