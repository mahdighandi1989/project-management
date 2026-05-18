"""Bug C6 — Verify v6 meta-test #2.

Unit tests برای aggregate_verdicts با ۵ سناریو concrete.

AC #12 از 12 AC C6 — حداقل ۵ سناریو در test پاس شوند.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import pytest  # noqa: F401
except ImportError:  # pragma: no cover
    pass

from app.services.verify_runtime.iterative_orchestrator import (
    ProbeResult,
    WEIGHTS_BY_PROBE,
    aggregate_verdicts,
)


# ---------------------------------------------------------------------------
# aggregate_verdicts — ۵ سناریو
# ---------------------------------------------------------------------------


def test_scenario_1_all_done_unanimous():
    """سناریو ۱: همه probes done → done قطعی با confidence 1.0."""
    results = [
        ProbeResult("content_grep_strong", "done", 0.9, ["e1"]),
        ProbeResult("code_aware_basename", "done", 0.8, ["e2"]),
        ProbeResult("ai_verifier", "done", 0.85, ["e3"]),
    ]
    out = aggregate_verdicts(results)
    assert out.verdict == "done"
    assert out.confidence > 0.95
    # evidence جمع‌آوری شده
    assert any("e1" in str(e) or "e2" in str(e) or "e3" in str(e) for e in out.evidence)


def test_scenario_2_strong_signal_wins_split():
    """سناریو ۲: content_grep_strong (weight 3.0) vs ai_verifier (1.0). done باید برنده شود."""
    results = [
        ProbeResult("content_grep_strong", "done", 0.9, ["strong evidence"]),
        ProbeResult("ai_verifier", "not_done", 0.9, ["weak evidence"]),
    ]
    out = aggregate_verdicts(results)
    assert out.verdict == "done"
    # 3.0*0.9=2.7 vs 1.0*0.9=0.9 → done score / total = 2.7/3.6 = 0.75
    assert out.confidence > 0.7


def test_scenario_3_empty_results_unclear():
    """سناریو ۳: لیست خالی → unclear با confidence 0.0."""
    out = aggregate_verdicts([])
    assert out.verdict == "unclear"
    assert out.confidence == 0.0
    assert any("inconclusive" in str(e).lower() for e in out.evidence)


def test_scenario_4_all_errors_unclear():
    """سناریو ۴: همه probes error دارند → unclear."""
    results = [
        ProbeResult("playwright", "done", 0.9, [], error="browser crashed"),
        ProbeResult("ai_verifier", "done", 0.8, [], error="timeout"),
    ]
    out = aggregate_verdicts(results)
    assert out.verdict == "unclear"


def test_scenario_5_strong_model_overrides_weak():
    """سناریو ۵: strong_model (weight 2.5) با not_done باید روی
    content_grep_weak (weight 1.5) با done غلبه کند."""
    results = [
        ProbeResult("content_grep_weak", "done", 0.6, ["partial match"]),
        ProbeResult("strong_model", "not_done", 0.8, ["AI judges incomplete"]),
    ]
    out = aggregate_verdicts(results)
    # 1.5*0.6=0.9 done vs 2.5*0.8=2.0 not_done → not_done wins
    assert out.verdict == "not_done"


# ---------------------------------------------------------------------------
# WEIGHTS_BY_PROBE — sanity check طبق پرامپت C6
# ---------------------------------------------------------------------------


def test_weights_by_probe_canonical_values():
    """طبق پرامپت C6 v2 — وزن‌های دقیق."""
    assert WEIGHTS_BY_PROBE["content_grep_strong"] == 3.0
    assert WEIGHTS_BY_PROBE["content_grep_weak"] == 1.5
    assert WEIGHTS_BY_PROBE["code_aware_basename"] == 1.0
    assert WEIGHTS_BY_PROBE["playwright"] == 2.0
    assert WEIGHTS_BY_PROBE["ai_verifier"] == 1.0
    assert WEIGHTS_BY_PROBE["vision_frontend"] == 0.5
    assert WEIGHTS_BY_PROBE["vision_backend"] == 0.0
    assert WEIGHTS_BY_PROBE["strong_model"] == 2.5
