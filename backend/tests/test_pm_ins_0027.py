"""PM-INS-0027: «فایل X را بساز و این خط را بنویس» goes straight to a plain action_plan — never a deep scan."""

import inspect

from app.services.inspector_intent_resolver import _is_simple_file_op

COORD = ("در فایلِ docs/COORDINATOR_TEST.md (اگر نیست بساز) دقیقاً این یک خط را بنویس و هیچ فایلِ دیگری را تغییر نده: "
         "«آزمونِ هماهنگ‌کننده» سپس اعمال کن (شاخهٔ جدا + PR، بدونِ ادغام)")


def test_the_coordinators_request_is_a_simple_file_op():
    assert _is_simple_file_op(COORD)
    assert _is_simple_file_op("write one line to docs/NOTE.md")
    assert _is_simple_file_op("در README.md این خط را بنویس: سلام")
    assert not _is_simple_file_op("امنیت پروژه را بررسی کن")
    assert not _is_simple_file_op("این صفحه باگ دارد")


def test_smart_chat_decides_on_the_users_own_words_not_the_structured_prompt():
    from app.api.routes import render_logs as R
    src = inspect.getsource(R)
    i = src.index('_orig_msg = (getattr(request, "original_message", None) or "").strip()')
    j = src.index("intent = resolve_intent_from_chat_context(", i)
    block = src[i:j]
    assert "_simple_op(_orig_msg or request.message)" in block and "raise _SkipIntentPath()" in block
    assert "original_message" in R.SmartChatRequest.model_fields


def test_a_simple_file_op_is_not_split_into_steps_and_empty_files_are_reported():
    from app.api.routes import render_logs as R
    src = inspect.getsource(R)
    i = src.index("# (PM-INS-0027) «فایلِ X را بساز و این خط را بنویس» is ONE action")
    assert "steps = []" in src[i:i + 600] and "_sfo(request.message" in src[i:i + 600]
    assert "محتوای فایل در action_plan خالی است" in src
    assert "pr_svc.delete_branch(" in src


def test_only_inspector_branches_can_be_deleted():
    import asyncio
    from app.services.github_pr_service import GitHubPRService
    svc = GitHubPRService.__new__(GitHubPRService)
    called = []

    async def fake(method, url, headers=None, json_body=None):
        called.append((method, url))
        return {"status": 204}
    svc._gh_request = fake
    svc._get_headers = lambda token=None: {}
    assert not asyncio.run(svc.delete_branch("o", "r", "main"))["success"] and not called
    assert asyncio.run(svc.delete_branch("o", "r", "inspector/smart-fix-1"))["success"]
    assert called[0][0] == "DELETE" and called[0][1].endswith("/git/refs/heads/inspector/smart-fix-1")
