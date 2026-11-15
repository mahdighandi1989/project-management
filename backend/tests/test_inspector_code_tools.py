# -*- coding: utf-8 -*-
"""«بازرس ویژه» for weak models (2026-11-15, owner plan item 12): numbered ranges, outline, search, and find-texts
verified against the real file before an action plan is accepted."""
import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import inspector_code_tools as ct  # noqa: E402

BIG_PY = "\n".join([f"# filler line {i}" for i in range(1, 3001)]
                   + ["", "@router.get(\"/health\")", "async def health():", "    return {'ok': True}", "",
                      "class Thing:", "    def method(self):", "        return 42"])


def test_numbered_range_and_caps():
    text, a, b, total = ct.numbered("a\nb\nc\nd", 2, 3)
    assert (a, b, total) == (2, 3, 4)
    assert text.splitlines() == ["2| b", "3| c"]
    _, a, b, _ = ct.numbered(BIG_PY, 10, 5000)
    assert b - a + 1 == ct.MAX_RANGE_LINES


def test_outline_python_ts_md():
    ol = ct.outline("x.py", BIG_PY)
    assert any("def health" in o for o in ol) and any("class Thing" in o for o in ol)
    assert any("route get /health" in o for o in ol)
    ts = "import x\nexport default function Page() {\n}\nconst onSave = useCallback(async () => {}, []);\ninterface Props {}\n"
    tol = ct.outline("p.tsx", ts)
    assert tol[0].startswith("2:") and any(o.startswith("4:") for o in tol) and any(o.startswith("5:") for o in tol)
    assert ct.outline("a.md", "# T\n\n## Sec") == ["1: # T", "3: ## Sec"]


def test_search_regex_and_literal():
    hits = ct.search({"a.py": BIG_PY}, r"def \w+\(")
    assert any(h.startswith("a.py:3003") for h in hits)
    assert ct.search({"a.py": "x = (1"}, "(1")  # invalid regex ⇒ literal


def test_check_sections_reports_misses_with_closest_real_text():
    content = "def a():\n    return 1\n\ndef b():\n    return 2\n"
    assert ct.check_sections(content, [{"find": "def b():\n    return 2", "replace": ""}]) == []
    assert ct.check_sections(content, [{"find": "def  b():\n        return 2", "replace": ""}]) == []  # whitespace only
    misses = ct.check_sections(content, [{"find": "def b():\n    return 3", "replace": ""}])
    assert len(misses) == 1 and "return 2" in misses[0]["closest"][0]
    assert "find" in ct.explain_misses("x.py", misses)


class _GH:
    def __init__(self, files):
        self.files = files

    async def get_file_content(self, owner, repo, path, branch=None, token=None):
        return {"success": path in self.files, "content": self.files.get(path, "")}


class _AI:
    """A scripted 'weak model': submits a wrong find, then reads the range and submits the right one."""

    def __init__(self):
        self.turn = 0
        self.seen = []

    async def generate(self, model_id, messages, **kw):
        self.turn += 1
        self.seen.append(messages[-1])
        calls = {
            1: [{"id": "1", "name": "read_file", "input": {"path": "big.py"}}],
            2: [{"id": "2", "name": "submit_action_plan", "input": {"analysis": "fix", "files": [
                {"path": "big.py", "operation": "modify_sections", "sections": [{"find": "return {'ok': False}", "replace": "x"}]}]}}],
            3: [{"id": "3", "name": "read_file", "input": {"path": "big.py", "start_line": 3002, "end_line": 3004}}],
            4: [{"id": "4", "name": "submit_action_plan", "input": {"analysis": "fix", "files": [
                {"path": "big.py", "operation": "modify_sections", "sections": [{"find": "    return {'ok': True}", "replace": "    return {'ok': 1}"}]}]}}],
        }.get(self.turn, [])
        return SimpleNamespace(content="", tool_calls=calls, tokens_used=1)


def test_agent_rejects_wrong_find_then_accepts_corrected_plan():
    from app.services.inspector_agent import run_inspector_agent

    ai = _AI()

    async def run():
        events = []
        async for ev in run_inspector_agent(ai_manager=ai, github_svc=_GH({"big.py": BIG_PY}), model_id="weak",
                                            owner="o", repo="r", token=None, branch="main", system_prompt="s",
                                            user_prompt="u", file_list=["big.py"], max_iterations=8):
            events.append(ev)
        return events

    events = asyncio.run(run())
    result = events[-1][1]
    assert result["stop_reason"] == "submitted"
    assert result["action_plan"]["files"][0]["sections"][0]["find"] == "    return {'ok': True}"
    assert any(e[0] == "progress" and e[1].get("step") == "agent_find_check" for e in events)
    # the big file came back as outline + head, not a silent cut
    first_read = str(ai.seen[1])
    assert "نقشهٔ کاملِ فایل" in first_read and "def health" in first_read


def test_single_shot_plan_survives_weak_model_json():
    from app.api.routes.render_logs import _extract_all_action_plans_from_response

    content = ('analysis…\n```json\n{"files": [{"path": "a.py", "operation": "modify", "content": "l1\nl2"},], '
               '"commit_message": "m"}```')
    plan = _extract_all_action_plans_from_response(content)
    assert plan and plan["files"][0]["content"] == "l1\nl2" and plan["commit_message"] == "m"
