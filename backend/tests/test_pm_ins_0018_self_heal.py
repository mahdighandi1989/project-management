"""PM-INS-0018 — «🩹 خوداصلاح»: خطای تازهٔ پیش‌نمایش ⇒ تحلیل + diff ِ پیشنهادی (بی‌اعمال)، با تأییدِ مالک ⇒ PR / برگهٔ فوری."""

import asyncio
import json
import pathlib
import types

from app.services import self_heal as SH

PAGE = pathlib.Path(__file__).resolve().parents[2] / "frontend/src/app/projects/[id]/page.tsx"


def test_signature_collapses_numbers_urls_and_hashes():
    a = SH.error_signature("TypeError: x is undefined at https://q.onrender.com/app.3f9a1b2c.js:12:5")
    b = SH.error_signature("TypeError: x is undefined at https://q.onrender.com/app.99aa77bb.js:40:1")
    assert a == b
    assert SH.error_signature("ReferenceError: y") != a


def test_resolve_repo_from_extra_data_or_github_path():
    p = types.SimpleNamespace(extra_data=json.dumps({"owner": "o", "repo": "r"}), github_path=None)
    assert SH.resolve_repo(p) == ("o", "r")
    assert SH.resolve_repo(types.SimpleNamespace(extra_data=None, github_path="https://github.com/a/b.git")) == ("a", "b")
    assert SH.resolve_repo(types.SimpleNamespace(extra_data="bad", github_path="a/b")) == ("a", "b")
    assert SH.resolve_repo(types.SimpleNamespace(extra_data=None, github_path="")) is None


def test_pick_relevant_paths_prefers_stack_files():
    paths = ["README.md", "src/app.js", "src/player.js", "index.html", "node_modules/x/player.js", "src/util.js"]
    got = SH.pick_relevant_paths(paths, "TypeError at https://h/static/player.7a8b9c0d.js:3:9")
    assert got[0] == "src/player.js"
    assert "node_modules/x/player.js" not in got and "README.md" not in got
    assert len(got) <= SH.MAX_FILES


def test_parse_proposal_json_fenced_and_raw_diff():
    j = '```json\n{"analysis": "علت", "diff": "--- a/src/app.js\\n+++ b/src/app.js\\n@@\\n-a\\n+b", "confidence": "high"}\n```'
    p = SH.parse_proposal(j)
    assert p["analysis"] == "علت" and p["confidence"] == "high"
    assert p["files"] == [{"path": "src/app.js", "issue": ""}]
    raw = SH.parse_proposal("متن\n```diff\n--- a/x.js\n+++ b/x.js\n@@\n-1\n+2\n```")
    assert raw["diff"].startswith("--- a/x.js") and raw["files"][0]["path"] == "x.js"


def test_propose_reads_files_and_never_applies():
    calls = {"read": [], "prompt": None}

    async def list_tree(o, r):
        return ["src/app.js", "src/player.js", "docs/a.md"]

    async def read_file(o, r, path):
        calls["read"].append(path)
        return f"// {path}\nconst a = 1;"

    async def generate(mid, prompt):
        calls["prompt"] = prompt
        return json.dumps({"analysis": "x تعریف نشده", "files": [{"path": "src/player.js", "issue": "x"}],
                           "diff": "--- a/src/player.js\n+++ b/src/player.js\n@@\n-x\n+y", "confidence": "medium"})

    out = asyncio.run(SH.propose(owner="o", repo="r", error_message="ReferenceError: x at player.js:2",
                                 log_details="[error] boom", page_url="https://q.example", model_id="m",
                                 list_tree=list_tree, read_file=read_file, generate=generate))
    assert out["success"] and out["model_used"] == "m" and out["github_repo"] == "o/r"
    assert calls["read"][0] == "src/player.js" and "docs/a.md" not in calls["read"]
    assert "ReferenceError" in calls["prompt"] and "https://q.example" in calls["prompt"]
    assert out["diff"].startswith("--- a/src/player.js")
    assert "apply" not in out  # پیشنهاد فقط؛ اعمال از مسیرِ /inspector/fix با تأییدِ مالک


def test_endpoint_registered_and_frontend_wired():
    from app.api.routes import render_logs as RL
    paths = {getattr(r, "path", "") for r in RL.router.routes}
    assert any(p.endswith("/inspector/self-heal/propose") for p in paths)
    page = PAGE.read_text(encoding="utf-8")
    assert 'data-testid="inspector-self-heal-toggle"' in page
    assert "/api/render/inspector/self-heal/propose" in page
    assert "selfHealTriggerRef.current?.(" in page          # خطای تازه ⇒ خودکار
    assert "setFixModalOpen(true);  // همین پنجره تأییدِ مالک است" in page  # اعمال فقط با تأیید
    assert "inspectionApi.create(" in page and "urgent: true" in page
