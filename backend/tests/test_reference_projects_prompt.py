"""Tests for the reference-projects → system-prompt instructions.

The user reported using the existing reference-projects feature
(panel + Telegram pickers) to point a task at features in OTHER
projects so the generated prompt knows to draw inspiration from them.
The fusion text was being injected into the user idea, but the
system prompt the AI received did not contain ANY instruction about
what to do with that section — risking either:
  (a) the AI silently dropping the reference block when synthesising
      the final task description, or
  (b) the AI blindly copy-pasting reference patterns into the
      current project without adapting them to its stack/naming/
      dependencies.

This file locks in the fix: when the user idea contains the fusion
header ("## 📚 پروژه‌های مرجع" or "Reference Projects"), the
system prompt MUST include a reference-aware rule block that tells
the AI to (1) preserve the reference section in description,
(2) add an explicit "adapt to current stack" warning in
proposed_action, (3) call out mixing risks in risks, (4) describe
the stack differences in tech_context, and (5) add a verifiable
acceptance criterion for adaptation. It must also forbid using
reference file paths as edit targets.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _extract_system_prompt_template() -> str:
    """Return the raw system-prompt template body from
    oversight_service.idea_to_prompt — including all conditional
    blocks (attachment, reference) and their surrounding fences."""
    src_path = (
        Path(__file__).resolve().parents[1]
        / "app/services/oversight_service.py"
    )
    src = src_path.read_text(encoding="utf-8")
    return src


# ---------------------------------------------------------------------------
# Reference block presence + content
# ---------------------------------------------------------------------------


def test_reference_block_defined_in_idea_to_prompt():
    """The conditional `_reference_block` must exist and be wired into
    the system_prompt template."""
    src = _extract_system_prompt_template()
    assert "_reference_block = " in src
    assert "{_reference_block}" in src, (
        "the reference block string must appear in the system_prompt template"
    )


def test_reference_block_triggers_on_fusion_header():
    """Detection: presence of the fusion header in the idea triggers the block."""
    src = _extract_system_prompt_template()
    # The detection must look for the fusion header that reference_project_service
    # writes — either the Persian title or "Reference Projects".
    pattern = re.compile(
        r'if\s+"##\s*📚\s*پروژه‌های مرجع".*?in\s+idea\s*or\s+'
        r'"Reference Projects"\s*in\s+idea\s*:',
        re.DOTALL,
    )
    assert pattern.search(src), (
        "the trigger condition must check for both the Persian header and "
        "the English 'Reference Projects' marker"
    )


def test_reference_block_covers_five_concrete_obligations():
    """The block must spell out concrete obligations so the AI doesn't
    paraphrase them away. Specifically:
      1. Mention reference projects in description (no silent drop)
      2. Warn about adapt-to-current-stack in proposed_action
      3. Call out mixing risk in risks
      4. Note stack differences in tech_context
      5. Add an adaptation criterion in acceptance_criteria
    """
    src = _extract_system_prompt_template()
    # Pull the literal of _reference_block — anything between the
    # conditional assignment and the next attachment/template marker.
    m = re.search(
        r'if "## 📚 پروژه‌های مرجع".*?_reference_block\s*=\s*\((.*?)\n\s+\)',
        src,
        re.DOTALL,
    )
    assert m, "could not locate _reference_block literal body"
    block_text = m.group(1)

    required_signals = [
        # 1. description preservation
        "description",
        # 2. proposed_action adaptation warning
        "proposed_action",
        # 3. risks mixing warning
        "risks",
        # 4. tech_context stack differences
        "tech_context",
        # 5. acceptance criterion for adaptation
        "acceptance_criteria",
    ]
    for kw in required_signals:
        assert kw in block_text, (
            f"reference block must mention `{kw}` so the AI has explicit "
            f"per-field guidance"
        )

    # The block must also forbid reusing reference paths as edit targets.
    assert "target_locations" in block_text, (
        "block must say target_locations applies only to the CURRENT project"
    )
    # And must explicitly say "do not blind copy".
    assert "کورکورانه" in block_text or "blind" in block_text.lower(), (
        "block must explicitly forbid blind-copy of reference syntax/dependency"
    )


def test_reference_block_only_fires_when_idea_has_fusion_header():
    """Soft contract test — the source must show the detection is gated
    by the idea content. We do this by asserting both the detection
    pattern and the default empty assignment are present and ordered."""
    src = _extract_system_prompt_template()
    # default empty
    assert '_reference_block = ""' in src or "_reference_block = ''" in src

    # The default must come BEFORE the conditional override.
    default_pos = src.find('_reference_block = ""')
    if default_pos == -1:
        default_pos = src.find("_reference_block = ''")
    cond_pos = src.find('if "## 📚 پروژه‌های مرجع"')
    assert 0 < default_pos < cond_pos, (
        "default empty assignment must precede the conditional override"
    )


# ---------------------------------------------------------------------------
# Service-level: build_fusion_text already carries inline cautions
# ---------------------------------------------------------------------------


def test_fusion_text_already_carries_user_facing_cautions():
    """Defense in depth — even if the system_prompt rule block were
    stripped or the AI ignored it, the fusion text itself contains
    Persian cautions to the AI that get embedded in the user message.
    Lock these in so future refactors don't water them down."""
    from app.services.reference_project_service import (
        get_reference_project_service,
        ProjectExtract,
        ClassifiedInfo,
    )
    svc = get_reference_project_service()
    classified = ClassifiedInfo()  # all fields default to []
    extracts = [
        ProjectExtract(
            project_id="some-watched-id",
            project_path="owner/repo",
            branch="main",
            scanned_files=10,
            total_files_in_repo=50,
            files=[],
            error=None,
            focus_notes="فقط الگوی auth flow این پروژه",
        ),
    ]
    text, _ = svc.build_fusion_text(
        extracts, classified,
        task_summary="auth در پروژهٔ مقصد",
        current_project_profile="Stack: Next.js App Router + FastAPI",
    )
    # The fusion text MUST tell the AI it's inspiration not blind copy.
    assert "الهام" in text or "inspiration" in text.lower()
    assert "کپی" in text  # cautions against blind copy
    # And the user's focus_notes must appear so the AI knows the
    # specific aspect to draw from.
    assert "auth flow" in text
    # current project profile must be in there with its "current wins" framing.
    assert "Next.js App Router" in text
    assert "پروژهٔ فعلی برنده" in text or "پروژهٔ فعلی" in text
