"""Compact prompt for weaker models in the «بازرس ویژه» chat (2026-11-15)."""

import inspect

from app.api.routes import render_logs as RL
from app.services import inspector_compact_prompt as C


def _gi():
    return RL._build_general_instructions_list("p", "fastapi", "o/r")


def test_every_rule_has_a_short_form_or_is_already_short():
    for inst in _gi():
        full = inst.get("prompt_detail", inst["content"])
        assert inst["id"] in C.SHORT_RULES or len(full) < 400, f"rule {inst['id']} has no short form"


def test_compact_rules_are_a_fraction_and_keep_the_formats():
    full = RL._build_general_instructions_text(_gi())
    short = C.compact_general_instructions(_gi())
    assert len(full) > 20_000 and len(short) < 5_000
    for must in ("modify_sections", '"find"', "ask_user", "render_actions", "route_to", "runtime.txt",
                 "user_clarification", "به فارسی"):
        assert must in short, must
    # a rule that has no short form is kept whole, never dropped
    extra = _gi() + [{"id": "sys_new_rule", "title": "تازه", "content": "قاعدهٔ تازهٔ مالک"}]
    assert "قاعدهٔ تازهٔ مالک" in C.compact_general_instructions(extra)


def test_which_models_are_compact(monkeypatch):
    monkeypatch.delenv("INSPECTOR_COMPACT_PROMPT", raising=False)
    assert not C.is_compact_model("claude-sonnet-4-6", 200_000)
    assert C.is_compact_model("deepseek-chat", 64_000)
    assert C.is_compact_model("gpt-4o-mini", 128_000)
    assert C.is_compact_model("qwen-2.5-coder", None)
    monkeypatch.setenv("INSPECTOR_COMPACT_PROMPT", "0")
    assert not C.is_compact_model("deepseek-chat", 64_000)
    monkeypatch.setenv("INSPECTOR_COMPACT_PROMPT", "1")
    assert C.is_compact_model("claude-sonnet-4-6", 200_000)


def test_repo_map_lists_real_files_relevant_dirs_first():
    files = [f"frontend/src/components/C{i}.tsx" for i in range(40)] + [
        "backend/app/services/oversight_service.py", "backend/app/api/routes/oversight.py", "README.md"]
    m = C.build_repo_map(files, "خطا در oversight_service هنگام ذخیره", max_chars=600)
    lines = m.splitlines()
    assert lines[1].startswith("backend/app/services/: oversight_service.py")
    assert "README.md" in m or "…" in m
    assert len(m) <= 700
    big = C.build_repo_map([f"d{i}/f{j}.py" for i in range(200) for j in range(5)], "", max_chars=1500)
    assert "list_files" in big and len(big) < 1700


def test_compact_agent_prompt_adds_render_only_when_relevant():
    gi = C.compact_general_instructions(_gi())
    plain = C.agent_system_compact("o", "r", gi, "map", "دکمهٔ ذخیره کار نمی‌کند")
    dep = C.agent_system_compact("o", "r", gi, "map", "deploy fail شد: Connection refused به DATABASE_URL")
    assert "render_list_services" not in plain and "render_list_postgres" not in plain
    assert "render_get_deploy_logs" in dep and "render_create_postgres" in dep
    assert "preflight_check" in plain and "submit_action_plan" in plain and len(plain) < 7_000


def test_wired_into_the_chat():
    src = inspect.getsource(RL)
    assert "is_compact_model(primary_model" in src and "agent_system_compact(" in src and "build_repo_map(" in src
