# -*- coding: utf-8 -*-
"""The owner's four decisions (2026-11-15, «خودت بهترین رو طبق خواسته‌های قبلی انجام بده»)."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_explicit_owner_actions_pass_the_auto_run_gate():
    from app.services.prompt_github_sync import _resolve_repo_and_branch

    w = SimpleNamespace(repo_full_name="o/r", claude_runner_enabled=False, prompt_sync_enabled=True, default_branch="master")
    assert _resolve_repo_and_branch(w) is None                       # automatic work: still gated
    assert _resolve_repo_and_branch(w, explicit=True) == ("o", "r", "master")  # the owner's click: allowed, own branch


def test_runner_prompt_pushes_to_the_checked_out_branch_not_main():
    from app.services import claude_runner_bootstrap as b

    assert "git push origin main" not in b.MASTER_PROMPT
    assert 'git rev-parse --abbrev-ref HEAD' in b.MASTER_PROMPT


def test_run_task_never_marks_done():
    src = (Path(__file__).resolve().parents[1] / "app/services/oversight_service.py").read_text(encoding="utf-8")
    block = src[src.index("# وضعیت نهایی"):src.index("async with self._lock:", src.index("# وضعیت نهایی"))]
    assert 'final_status = "done"' not in block and 'final_status = "awaiting_review"' in block


def test_runtime_upgrade_needs_real_passes_over_half_the_acs():
    from app.services.oversight_verifier import _enough_real_passes

    task = SimpleNamespace(acceptance_criteria=["a", "b", "c", "d"])
    home = SimpleNamespace(ac_id="system_home")
    p = lambda i: SimpleNamespace(ac_id=f"ac{i}")  # noqa: E731
    assert not _enough_real_passes([home], task)               # the synthetic «homepage loads» alone: no
    assert not _enough_real_passes([home, p(1)], task)          # 1 of 4 ACs: no
    assert _enough_real_passes([p(1), p(2)], task)              # 2 of 4: yes
    # (changed on purpose 2026-11-15, «موارد باز»): no stored ACs ⇒ 2 distinct ACs are needed, not one lucky pass
    assert not _enough_real_passes([p(1)], SimpleNamespace(acceptance_criteria=[]))
    assert _enough_real_passes([p(1), p(2)], SimpleNamespace(acceptance_criteria=[]))
    # the same AC passing in two probe families counts once; task steps do not count
    assert not _enough_real_passes([SimpleNamespace(ac_id="ac01_x"), SimpleNamespace(ac_id="code_ac1"),
                                    SimpleNamespace(ac_id="step_3")], task)
