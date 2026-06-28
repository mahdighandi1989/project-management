"""🐛 (sync-gated-on-runner) — کاربر گزارش داد که حتی وقتی «اجرای
خودکار» (claude_runner_enabled) خاموش بوده، روی هر startup backend
ده‌ها commit «chore(prompt): sync task ...» روی ریپوی همهٔ پروژه‌های
تحت نظر push می‌شده، و CI آن ریپوها fail می‌شده. علت: bootstrap_sync و
sync per-task فقط `prompt_sync_enabled` (پیش‌فرض True) را چک می‌کردند،
نه `claude_runner_enabled`.

Fix: master gate در `_resolve_repo_and_branch` + bootstrap. هیچ sync
بدون runner enabled.

این فایل source-level contract را pin می‌کند تا کسی این behavior را
silently برنگرداند.
"""

from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _read(rel: str) -> str:
    return (
        Path(__file__).resolve().parents[1] / rel
    ).read_text(encoding="utf-8")


def test_resolve_repo_gates_on_claude_runner_enabled():
    """source-level pin: `_resolve_repo_and_branch` must reject any
    watched whose `claude_runner_enabled` is False — otherwise bootstrap
    and every per-task sync still spams the user's repos."""
    src = _read("app/services/prompt_github_sync.py")
    idx = src.find("def _resolve_repo_and_branch")
    assert idx != -1
    body = src[idx:idx + 2500]
    # The new master gate must check claude_runner_enabled
    assert 'getattr(watched, "claude_runner_enabled", False)' in body, (
        "_resolve_repo_and_branch must check claude_runner_enabled — "
        "without this gate, redeploys spam user repos with task-sync "
        "commits even when «اجرای خودکار» is OFF"
    )
    # And it must default to False (not True) when the attribute is
    # absent — otherwise legacy watched objects without the flag
    # bypass the gate.
    assert 'getattr(watched, "claude_runner_enabled", False)' in body, (
        "default for missing claude_runner_enabled must be False — "
        "True would defeat the purpose of the gate for legacy objects"
    )


def test_prompt_sync_enabled_check_still_present():
    """Sanity: the existing prompt_sync_enabled gate (which lets a user
    opt out per-project) must still exist; the new runner check is
    additional, not a replacement."""
    src = _read("app/services/prompt_github_sync.py")
    idx = src.find("def _resolve_repo_and_branch")
    body = src[idx:idx + 2500]
    assert 'getattr(watched, "prompt_sync_enabled", True)' in body, (
        "prompt_sync_enabled gate must still exist as a per-project "
        "opt-out"
    )


def test_bootstrap_counts_only_runner_enabled_projects():
    """source-level pin: the startup bootstrap loop must count only
    projects with claude_runner_enabled=True. Without this gate, every
    redeploy synced ALL watched projects even though their runners
    were disabled, generating commit spam + CI failures across every
    repo under oversight."""
    src = _read("app/main.py")
    idx = src.find("_prompt_sync_bootstrap")
    assert idx != -1
    body = src[idx:idx + 3500]
    assert 'getattr(w, "claude_runner_enabled", False)' in body, (
        "bootstrap must check claude_runner_enabled per-project — "
        "otherwise redeploy = spam commits on every watched repo"
    )
    # And the no-op log message should make the cause obvious in
    # production logs.
    assert "claude_runner_enabled=True" in body, (
        "bootstrap should log a clear reason when it skips — makes "
        "future debugging easy"
    )


def test_scheduler_syncable_filter_excludes_runner_disabled():
    """source-level pin: the periodic prompt-sync scheduler in
    oversight_service.py must filter OUT tasks whose watched project
    has claude_runner_enabled=False — BEFORE the throttle picks the
    top 5.

    Without this, every scheduler tick logged misleading
    «dispatched 5 task(s) to N project(s)» even though the actual
    GitHub writes were silently no-op'd downstream by
    _resolve_repo_and_branch. That made debugging «why is the repo
    still being touched» impossible from logs alone."""
    src = _read("app/services/oversight_service.py")
    # Find the syncable-partition loop
    idx = src.find("syncable: List")
    assert idx != -1, "syncable filter loop not found in oversight_service"
    # The runner gate should sit inside the loop (between the existing
    # prompt_sync_enabled check and syncable.append).
    body = src[idx:idx + 1500]
    assert 'getattr(watched, "claude_runner_enabled", False)' in body, (
        "scheduler must also filter on claude_runner_enabled — without "
        "this, every tick dispatches throttled work that gets no-op'd "
        "downstream and pollutes logs with misleading 'dispatched N' lines"
    )
