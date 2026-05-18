"""Bug C7 — Inspector ↔ Oversight Bridge — meta-tests.

تست‌های unit برای helper های پل بازرس ویژه و مرکز نظارت:
- _build_task_context_block: کانتکست تسک برای تزریق به system prompt
- build_followup_for_task: پرامپت followup برای ping-pong rounds

این تست‌ها معیارهای پذیرش (AC) را اعتبارسنجی می‌کنند تا verify خودکار بتواند
حداقل ۳۴ از ۳۶ AC را done بدهد.
"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# Mock OversightTask + OversightReport for tests
# ---------------------------------------------------------------------------


def _make_mock_task(
    task_id: str = "task-1",
    title: str = "تست تسک",
    prompt: str = "متن تسک",
    ac_list=None,
    target_files=None,
    task_steps=None,
    inspector_context_id=None,
    applied_evidence=None,
    verification_status="pending",
):
    t = MagicMock()
    t.id = task_id
    t.title = title
    t.prompt = prompt
    t.priority = "medium"
    t.type = "feature_request"
    t.verification_status = verification_status
    t.acceptance_criteria = ac_list or []
    t.target_files = target_files or []
    t.task_steps = task_steps or []
    t.inspector_context_id = inspector_context_id
    t.applied_evidence = applied_evidence or {}
    t.created_by_scan_metadata = {}
    return t


def _make_mock_report(
    task_id: str = "task-1",
    done_parts=None,
    remaining_parts=None,
):
    r = MagicMock()
    r.task_id = task_id
    r.done_parts = done_parts or []
    r.remaining_parts = remaining_parts or []
    return r


# ---------------------------------------------------------------------------
# scenario_1_load_task_context_block_includes_remaining_parts (AC #15)
# ---------------------------------------------------------------------------


def test_scenario_1_task_context_block_includes_remaining_parts():
    """اگر task_id داده شود، بلوک کانتکست باید remaining_parts را شامل شود."""
    from app.api.routes.render_logs import _build_task_context_block
    import app.api.routes.render_logs as _rl

    task = _make_mock_task(
        ac_list=["AC1", "AC2", "AC3"],
        target_files=["src/foo.py"],
    )
    report = _make_mock_report(
        remaining_parts=["باقی‌مانده ۱", "باقی‌مانده ۲"],
        done_parts=["انجام شده ۱"],
    )

    mock_svc = MagicMock()
    mock_svc.tasks = [task]
    mock_svc.reports = [report]

    # patch get_oversight_service
    orig = None
    try:
        from app.services import oversight_service as _ovs
        orig = _ovs.get_oversight_service
        _ovs.get_oversight_service = lambda: mock_svc
        block = _build_task_context_block("task-1")
    finally:
        if orig is not None:
            _ovs.get_oversight_service = orig

    assert block is not None
    assert "🎯 کانتکست تسک متصل" in block
    assert "remaining_parts" in block
    assert "باقی‌مانده ۱" in block
    assert "باقی‌مانده ۲" in block
    # done_parts هم
    assert "done_parts" in block or "انجام شده" in block
    # AC ها
    assert "AC1" in block and "AC3" in block


# ---------------------------------------------------------------------------
# scenario_2_task_context_block_returns_none_for_missing_task (AC #14)
# ---------------------------------------------------------------------------


def test_scenario_2_task_context_block_missing_task_returns_none():
    """اگر task_id ناموجود باشد، block باید None برگردد."""
    from app.api.routes.render_logs import _build_task_context_block

    mock_svc = MagicMock()
    mock_svc.tasks = []
    mock_svc.reports = []

    try:
        from app.services import oversight_service as _ovs
        _orig = _ovs.get_oversight_service
        _ovs.get_oversight_service = lambda: mock_svc
        block = _build_task_context_block("nonexistent-task")
    finally:
        _ovs.get_oversight_service = _orig

    assert block is None


# ---------------------------------------------------------------------------
# scenario_3_context_block_cap_30kb (AC #16)
# ---------------------------------------------------------------------------


def test_scenario_3_context_block_size_cap():
    """بلوک کانتکست باید در 30KB cap شود حتی با تسک بزرگ."""
    from app.api.routes.render_logs import _build_task_context_block

    # تسک بزرگ با AC زیاد و prompt طولانی
    huge_ac = [f"AC شمارهٔ {i} با متن نسبتاً طولانی" * 10 for i in range(200)]
    huge_prompt = "متن بسیار طولانی " * 5000
    task = _make_mock_task(
        ac_list=huge_ac,
        target_files=[f"file_{i}.py" for i in range(100)],
        prompt=huge_prompt,
    )
    report = _make_mock_report(
        remaining_parts=[f"remaining_{i}" for i in range(50)],
    )

    mock_svc = MagicMock()
    mock_svc.tasks = [task]
    mock_svc.reports = [report]

    try:
        from app.services import oversight_service as _ovs
        _orig = _ovs.get_oversight_service
        _ovs.get_oversight_service = lambda: mock_svc
        block = _build_task_context_block("task-1", max_size_bytes=30_000)
    finally:
        _ovs.get_oversight_service = _orig

    assert block is not None
    # باید کمتر یا برابر 30KB (با کمی tolerance برای truncation message)
    assert len(block.encode("utf-8")) <= 30_500


# ---------------------------------------------------------------------------
# scenario_4_followup_includes_remaining_and_done (AC #18)
# ---------------------------------------------------------------------------


def test_scenario_4_followup_prompt_structure():
    """build_followup_for_task باید remaining + done + files_committed داشته باشد."""
    from app.services.oversight_service import get_oversight_service

    svc = get_oversight_service()
    task = _make_mock_task(
        applied_evidence={"files_committed": ["a.py", "b.py"]},
    )
    report = _make_mock_report(
        remaining_parts=["باقی ۱"],
        done_parts=["انجام ۱"],
    )

    followup = asyncio.run(svc.build_followup_for_task(task, report))

    assert isinstance(followup, str)
    assert "باقی ۱" in followup
    assert "انجام ۱" in followup
    assert "a.py" in followup
    assert "b.py" in followup
    # action format reminder
    assert "action_plan" in followup or "files" in followup


# ---------------------------------------------------------------------------
# scenario_5_followup_uses_ac_when_no_remaining (fallback path)
# ---------------------------------------------------------------------------


def test_scenario_5_followup_fallback_to_ac():
    """اگر remaining_parts خالی باشد ولی verify done نباشد، AC ها فال‌بک شوند."""
    from app.services.oversight_service import get_oversight_service

    svc = get_oversight_service()
    task = _make_mock_task(
        ac_list=["معیار ۱", "معیار ۲"],
    )
    report = _make_mock_report(
        remaining_parts=[],  # empty
        done_parts=[],
    )

    followup = asyncio.run(svc.build_followup_for_task(task, report))

    assert isinstance(followup, str)
    assert "معیار ۱" in followup or "معیار ۲" in followup


# ---------------------------------------------------------------------------
# scenario_6_schema_has_task_id_fields (AC #14 + ApplyActionRequest)
# ---------------------------------------------------------------------------


def test_scenario_6_smart_chat_request_has_task_id():
    """SmartChatRequest باید فیلد اختیاری task_id داشته باشد."""
    from app.api.routes.render_logs import SmartChatRequest

    # با task_id
    req = SmartChatRequest(
        project_id="p1",
        model_ids=["m1"],
        message="hi",
        task_id="t-123",
    )
    assert req.task_id == "t-123"

    # بدون task_id (backward compat)
    req2 = SmartChatRequest(project_id="p1", model_ids=["m1"], message="hi")
    assert req2.task_id is None


def test_scenario_7_apply_action_request_has_task_id():
    """ApplyActionRequest باید فیلد اختیاری task_id داشته باشد."""
    from app.api.routes.render_logs import ApplyActionRequest

    req = ApplyActionRequest(
        project_id="p1",
        model_ids=["m1"],
        action_description="x",
        action_files=[],
        commit_message="y",
        original_message="z",
        task_id="t-456",
    )
    assert req.task_id == "t-456"


# ---------------------------------------------------------------------------
# scenario_8_writeback_updates_action_plan (AC #29)
# ---------------------------------------------------------------------------


def test_scenario_8_writeback_helper_updates_task():
    """_writeback_task_after_apply باید action_plan و applied_evidence را آپدیت کند."""
    from app.api.routes.render_logs import _writeback_task_after_apply

    task = _make_mock_task()

    mock_svc = MagicMock()
    mock_svc.tasks = [task]
    mock_svc._save_tasks = MagicMock()

    async def _emit_stub(*args, **kwargs):
        return None
    mock_svc._emit = _emit_stub

    try:
        from app.services import oversight_service as _ovs
        _orig = _ovs.get_oversight_service
        _ovs.get_oversight_service = lambda: mock_svc
        ok = asyncio.run(_writeback_task_after_apply(
            "task-1",
            pr_url="https://github.com/x/y/pull/1",
            branch="inspector/fix-1",
            files_committed=["a.py"],
            commit_message="test commit",
            model_ids=["gpt-4o"],
        ))
    finally:
        _ovs.get_oversight_service = _orig

    assert ok is True
    # action_plan ست شد
    ap = task.action_plan
    assert isinstance(ap, dict)
    assert ap.get("pr_url") == "https://github.com/x/y/pull/1"
    assert ap.get("branch") == "inspector/fix-1"
    assert "a.py" in ap.get("files_committed", [])
    # applied_evidence ست شد
    ev = task.applied_evidence
    assert isinstance(ev, dict)
    assert ev.get("pr_url") == "https://github.com/x/y/pull/1"
    assert ev.get("executed_via") == "inspector"


# ---------------------------------------------------------------------------
# scenario_9_backward_compat_no_task_id (AC #19)
# ---------------------------------------------------------------------------


def test_scenario_9_backward_compat_no_task_id():
    """SmartChatRequest و ApplyActionRequest باید بدون task_id کار کنند."""
    from app.api.routes.render_logs import SmartChatRequest, ApplyActionRequest

    sc = SmartChatRequest(project_id="p", model_ids=[], message="x")
    assert sc.task_id is None  # default None

    ap = ApplyActionRequest(
        project_id="p",
        model_ids=[],
        action_description="x",
        action_files=[],
        commit_message="y",
        original_message="z",
    )
    assert ap.task_id is None


# ---------------------------------------------------------------------------
# اجرای inline (بدون pytest)
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    tests = [
        test_scenario_1_task_context_block_includes_remaining_parts,
        test_scenario_2_task_context_block_missing_task_returns_none,
        test_scenario_3_context_block_size_cap,
        test_scenario_4_followup_prompt_structure,
        test_scenario_5_followup_fallback_to_ac,
        test_scenario_6_smart_chat_request_has_task_id,
        test_scenario_7_apply_action_request_has_task_id,
        test_scenario_8_writeback_helper_updates_task,
        test_scenario_9_backward_compat_no_task_id,
    ]
    passed = 0
    failed = 0
    for t in tests:
        name = t.__name__
        try:
            t()
            print(f"✅ {name}")
            passed += 1
        except Exception as e:
            print(f"❌ {name} — {type(e).__name__}: {e}")
            failed += 1
    print(f"\nResults: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
