"""PM-INS-0039 — the resolution status of an experience is decided from its text.

The owner's finding: 342 of 393 catalog entries were «unknown» because the
status was read only from a frontmatter key that task-written experiences do
not carry, so the «وضعیت» filter was useless. These tests pin: the rules, the
«unknown only without evidence» promise, the one-time backfill of entries
indexed before the classifier, the cheap-model path for ambiguous text, and
the /command-room → /oversight redirect asked for in the same ticket.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_ROOT = Path(__file__).resolve().parents[2]

from app.services.knowledge_status import (  # noqa: E402
    build_model_prompt, infer_resolution_status, parse_model_answer,
)

SOLVED = """# A weaker match gets its own review-only lane

## 🎯 چالش / Challenge
تطبیقِ ضعیف با تطبیقِ قطعی در یک فهرست قاطی می‌شد و کاربر اشتباهی تأیید می‌کرد.

## 💡 راه‌حل / Solution
۱. تطبیقِ ضعیف در ستونِ جدا و فقط‌خواندنی نشان داده می‌شود و هرگز خودکار اعمال نمی‌شود.
۲. تأییدِ آن فقط با کلیکِ صریحِ کاربر و ثبت در تاریخچه انجام می‌گیرد.

## ⚠️ نکات حیاتی / Pitfalls
تلاشِ اول با آستانهٔ بالاتر حل نشد چون داده‌های مرزی باز هم رد می‌شدند.
"""

PARTIAL = SOLVED + """
## Open questions
- هنوز روشن نیست با رکوردهای تکراریِ قدیمی چه باید کرد.
"""

OPEN = """# Flaky upload on mobile

## 🎯 چالش / Challenge
آپلود روی موبایل گاهی قطع می‌شود. سه فرضیه آزموده شد و مشکل هنوز حل نشده است؛ ریشه پیدا نشد.
"""

NO_EVIDENCE = """# یادداشت

چند نکتهٔ پراکنده دربارهٔ ابزارها.
"""


def test_solution_section_without_open_signal_is_solved_and_says_why():
    status, source, evidence = infer_resolution_status({}, SOLVED)
    assert (status, source) == ("solved", "text")
    assert "راه" in evidence and "نویسه" in evidence


def test_failed_attempt_told_in_pitfalls_does_not_unsolve_it():
    """«حل نشد» inside the story of an earlier attempt is not an open problem."""
    assert infer_resolution_status({}, SOLVED)[0] == "solved"


def test_solution_plus_open_heading_is_ambiguous_partial():
    status, source, evidence = infer_resolution_status({}, PARTIAL)
    assert (status, source) == ("partial", "ambiguous")
    assert "open questions" in evidence


def test_no_solution_and_explicit_unresolved_sentence_is_open():
    status, source, evidence = infer_resolution_status({}, OPEN)
    assert (status, source) == ("open", "text")
    assert "هنوز حل نشده" in evidence


def test_unknown_only_when_the_text_gives_no_evidence():
    status, source, evidence = infer_resolution_status({}, NO_EVIDENCE)
    assert (status, source) == ("unknown", "none")
    assert "شاهدی در متن نیست" in evidence
    assert infer_resolution_status({}, "")[0] == "unknown"


def test_frontmatter_is_never_overridden():
    assert infer_resolution_status({"resolution_status": "Regressed"}, SOLVED)[:2] == ("regressed", "frontmatter")
    # «unknown» written by hand is not a decision — the text still speaks.
    assert infer_resolution_status({"resolution_status": "unknown"}, SOLVED)[0] == "solved"


def test_resolution_block_beats_the_guess():
    body = SOLVED + "\n## ✅ Resolution\n- Status: partial\n- Evidence: «یک مورد مانده»\n"
    assert infer_resolution_status({}, body)[:2] == ("partial", "resolution-section")


def test_placeholder_solution_and_code_fences_are_not_evidence():
    assert infer_resolution_status({}, "# T\n\n## Solution\nTBD\n")[0] == "unknown"
    fenced = "# T\n\n## Notes\n```\n## Solution\n" + "x" * 300 + "\nStatus: solved\n```\n"
    assert infer_resolution_status({}, fenced)[0] == "unknown"


def test_every_experience_in_this_repo_is_classified():
    """Real files, real format: none of them may stay «unknown»."""
    from app.services.knowledge_center_service import _parse_frontmatter
    files = [p for p in (_ROOT / "experiences").glob("*.md") if p.name.lower() != "readme.md"]
    assert len(files) >= 7
    for p in files:
        meta, content = _parse_frontmatter(p.read_text(encoding="utf-8"))
        status, _src, evidence = infer_resolution_status(meta, content)
        assert status != "unknown", f"{p.name}: {evidence}"


def test_model_answer_parsing_is_strict():
    assert parse_model_answer("STATUS: solved — راه‌حلِ نهایی اعمال شده") == ("solved", "راه‌حلِ نهایی اعمال شده")
    assert parse_model_answer("**Status:** `partial` - one item left")[0] == "partial"
    assert parse_model_answer("I think it is fine") == ("", "")
    assert "partial" in build_model_prompt("t", "c", "e") and "STATUS:" in build_model_prompt("t", "c", "e")


# ── sync: classification at extraction time + one-time backfill ─────────────


@pytest.fixture
def kc(tmp_path, monkeypatch):
    from app.services import knowledge_center_service as kcs
    monkeypatch.setattr(kcs, "INDEX_FILE", tmp_path / "kc.json")
    monkeypatch.setattr(kcs, "USAGE_FILE", tmp_path / "kc_usage.json")
    monkeypatch.setattr(kcs, "SETTINGS_FILE", tmp_path / "kc_settings.json")
    return kcs


def _fm(body: str, extra: str = "") -> str:
    return f'---\ntitle: "T"\ntags: [x]\nsource:\n  type: "claude-code-task"\n{extra}---\n\n{body}'


def _run_sync(kc, files, model=None):
    svc = kc.KnowledgeCenterService()
    fetched = []

    async def fake_list(*a, **k):
        return [{"name": n, "path": f"experiences/{n}", "sha": sha} for n, (sha, _b) in files.items()]

    async def fake_get(owner, repo, path, token):
        fetched.append(path)
        return files[path.split("/")[-1]][1]

    async def no_model(*a, **k):
        raise RuntimeError("no model configured")

    osv = SimpleNamespace(watched=[SimpleNamespace(id="w1", repo_full_name="owner/alpha")])
    with patch("app.services.oversight_service.get_oversight_service", return_value=osv), \
         patch("app.services.oversight_service.get_github_token", return_value="tok"), \
         patch.object(svc, "_gh_list_directory", fake_list), \
         patch.object(svc, "_gh_get_file_content", fake_get), \
         patch("app.api.routes.simple_projects.ai_generate_with_meta", model or no_model):
        res = asyncio.run(svc.sync_from_projects())
    by_path = {e["path"].split("/")[-1]: e for e in json.loads(kc.INDEX_FILE.read_text(encoding="utf-8"))["entries"]}
    return res, by_path, fetched


def test_sync_classifies_new_files_from_their_text(kc):
    files = {
        "solved.md": ("s1", _fm(SOLVED)), "open.md": ("s2", _fm(OPEN)),
        "none.md": ("s3", _fm(NO_EVIDENCE)),
        "fm.md": ("s4", _fm(NO_EVIDENCE, 'resolution_status: "partial"\n')),
    }
    res, e, _ = _run_sync(kc, files)
    assert {k: v["resolution_status"] for k, v in e.items()} == {
        "solved.md": "solved", "open.md": "open", "none.md": "unknown", "fm.md": "partial"}
    assert e["solved.md"]["status_source"] == "text" and e["solved.md"]["status_evidence"]
    assert e["fm.md"]["status_source"] == "frontmatter"
    assert res["resolutions"] == {"solved": 1, "open": 1, "unknown": 1, "partial": 1}
    assert res["reclassified"] == 3
    facets = dict(kc.KnowledgeCenterService().list_entries(resolution_status="solved")["facets"]["resolutions"])
    assert facets == {"solved": 1, "open": 1, "unknown": 1, "partial": 1}


def test_backfill_rereads_old_unknown_entries_once_and_deletes_nothing(kc):
    """An entry indexed before the classifier (same blob sha, status unknown, no
    ``status_checked_hash``) is re-read ONCE; its id and other fields survive."""
    body = _fm(SOLVED)
    old = {
        "id": "keep-me", "project_id": "w1", "project_full_name": "owner/alpha",
        "path": "experiences/solved.md", "title": "T", "tags": ["x"], "summary": "AI summary",
        "content_hash": kc._hash(body), "git_sha": "s1", "resolution_status": "unknown",
        "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-02T00:00:00Z",
        "last_processed_hash": kc._hash(body), "last_processed_by": "m",
    }
    kc.INDEX_FILE.write_text(json.dumps({"entries": [old]}), encoding="utf-8")
    files = {"solved.md": ("s1", body)}
    res1, e1, fetched1 = _run_sync(kc, files)
    assert fetched1 == ["experiences/solved.md"]
    got = e1["solved.md"]
    assert got["resolution_status"] == "solved" and got["id"] == "keep-me"
    assert got["updated_at"] == "2026-01-02T00:00:00Z"          # content did not change
    assert got["last_processed_hash"] == old["last_processed_hash"]  # no AI re-processing triggered
    assert res1["reclassified"] == 1 and res1["updated"] == 0 and len(e1) == 1
    res2, e2, fetched2 = _run_sync(kc, files)
    assert fetched2 == [] and res2["reclassified"] == 0
    assert e2["solved.md"]["resolution_status"] == "solved"


def test_unreadable_file_keeps_the_entry_untouched_and_is_retried(kc):
    old = {"id": "a", "project_id": "w1", "project_full_name": "owner/alpha", "path": "experiences/solved.md",
           "title": "Kept", "content_hash": "h", "git_sha": "s1", "resolution_status": "unknown",
           "updated_at": "2026-01-02T00:00:00Z"}
    kc.INDEX_FILE.write_text(json.dumps({"entries": [old]}), encoding="utf-8")
    res, e, fetched = _run_sync(kc, {"solved.md": ("s1", "")})
    assert fetched and e["solved.md"]["title"] == "Kept" and e["solved.md"]["content_hash"] == "h"
    assert "status_checked_hash" not in e["solved.md"]  # ⇒ next sync tries again
    assert res["projects"][0]["unread"] == 1


def test_ambiguous_text_asks_the_model_and_falls_back_to_partial(kc):
    files = {"p.md": ("s1", _fm(PARTIAL))}
    _res, e, _ = _run_sync(kc, files)  # model unavailable
    assert (e["p.md"]["resolution_status"], e["p.md"]["status_source"]) == ("partial", "ambiguous")

    kc.INDEX_FILE.unlink()
    asked = []

    async def model(prompt, model_ids=None, max_tokens=0):
        asked.append(prompt)
        return "STATUS: solved — پرسشِ باز به موضوعِ دیگری مربوط است", "cheap-model"

    _res, e, _ = _run_sync(kc, files, model=model)
    assert len(asked) == 1 and "Open questions" in asked[0]
    assert (e["p.md"]["resolution_status"], e["p.md"]["status_source"]) == ("solved", "model")
    assert "cheap-model" in e["p.md"]["status_evidence"]


# ── supervisor run 13: the leftovers of PM-INS-0039 (24 «unknown», false «partial») ──

NESTED = """# وضعیتی که نمی‌تواند دروغ بگوید

## 🎯 چالش / Challenge
وضعیتِ «پاسخ داده شد» با «حل شد» یکی گرفته می‌شد.

## 💡 راه‌حل / Solution — سه نقص

### ۱. وضعیت از نتیجه جدا شد
رنگِ کارت فقط می‌گوید نوبتِ کیست؛ نتیجه نشانِ جداست و بی‌مدرک پذیرفته نمی‌شود.

### ۲. ادعای موفقیت بها دارد
«درست شد» بدونِ تصویرِ بعد در API رد می‌شود و برگه به صفِ بدهی برمی‌گردد.

## ⚠️ Pitfalls
هیچ.
"""

RULE_ONLY = """## Problem
A late response for an old filter overwrote the list the user was looking at.

## Rule
Tag every request with the filter it was sent for and drop a response whose tag is no longer the current one.
"""

HEADLESS = ("یک فرم مقدارِ پیش‌فرض را از منبعی جدا از هم‌خانواده‌هایش می‌خواند و کاربر دو عددِ متفاوت می‌دید. "
            "قاعده: هر فرمِ یک خانواده همان منبعی را بخواند که بقیه می‌خوانند، و اگر منبع نبود خطا بدهد نه مقدارِ ساختگی. " * 2)


def test_solution_written_under_sub_headings_counts_as_the_solution():
    status, source, evidence = infer_resolution_status({}, NESTED)
    assert (status, source) == ("solved", "text") and "راه حل" in evidence


def test_title_level_heading_does_not_swallow_the_whole_file():
    text = "# The fix that was never found\n\n## Notes\n" + "We looked at many things for a long time. " * 5
    assert infer_resolution_status({}, text)[0] == "unknown"


def test_rule_heading_is_a_reusable_lesson():
    status, source, evidence = infer_resolution_status({}, RULE_ONLY)
    assert (status, source) == ("solved", "text") and "rule" in evidence


@pytest.mark.parametrize("sentence", [
    "Each field is answered or still open. A reply fills what it fills.",
    "One «still broken» verdict (a throttled run) is reported as a warning.",
    'Treat a same-bar tie, or "still open", as a needs-review warning.',
    "It was hidden from a child, but the direct view still opened it before the change.",
])
def test_a_quoted_or_enumerated_state_is_not_an_open_signal(sentence):
    status, source, _ = infer_resolution_status({}, SOLVED + "\n## Notes\n" + sentence + "\n")
    assert (status, source) == ("solved", "text")


def test_a_tool_name_quoted_in_a_heading_is_not_an_open_signal():
    text = SOLVED + "\n## Update — ابزارهای «تکمیلِ ناتمام‌ها» و «بازنویسی لحن»\nهر دو ابزار از همان مسیرِ مرور می‌گذرند.\n"
    assert infer_resolution_status({}, text)[:2] == ("solved", "text")


def test_a_real_open_sentence_still_makes_it_partial():
    text = SOLVED + "\n## Notes\nA third question is still open: what to do with old rows.\n"
    assert infer_resolution_status({}, text)[:2] == ("partial", "ambiguous")


def test_text_without_any_shape_is_given_to_the_model_and_the_reason_is_kept(kc):
    files = {"h.md": ("s1", _fm(HEADLESS)), "none.md": ("s2", _fm(NO_EVIDENCE))}
    _res, e, _ = _run_sync(kc, files)  # model unavailable
    assert (e["h.md"]["resolution_status"], e["h.md"]["status_source"]) == ("unknown", "none")
    assert "مدل پاسخ نداد" in e["h.md"]["status_evidence"] and "no model configured" in e["h.md"]["status_evidence"]
    assert "مدل" not in e["none.md"]["status_evidence"]  # too short to be worth a call

    kc.INDEX_FILE.unlink()
    asked = []

    async def model(prompt, model_ids=None, max_tokens=0):
        asked.append(prompt)
        return "STATUS: solved — قاعدهٔ نهایی نوشته شده است", "cheap-model"

    _res, e, _ = _run_sync(kc, files, model=model)
    assert len(asked) == 1
    assert (e["h.md"]["resolution_status"], e["h.md"]["status_source"]) == ("solved", "model")
    assert e["none.md"]["resolution_status"] == "unknown"


def test_a_rule_change_rereads_every_entry_once(kc):
    """An entry stamped by the previous rules (plain content hash) is judged again."""
    body = _fm(NESTED)
    old = {"id": "keep", "project_id": "w1", "project_full_name": "owner/alpha", "path": "experiences/n.md",
           "title": "T", "content_hash": kc._hash(body), "git_sha": "s1", "resolution_status": "unknown",
           "status_source": "none", "status_checked_hash": kc._hash(body), "updated_at": "2026-01-02T00:00:00Z"}
    kc.INDEX_FILE.write_text(json.dumps({"entries": [old]}), encoding="utf-8")
    files = {"n.md": ("s1", body)}
    res1, e1, fetched1 = _run_sync(kc, files)
    assert fetched1 == ["experiences/n.md"] and res1["reclassified"] == 1
    assert e1["n.md"]["resolution_status"] == "solved" and e1["n.md"]["id"] == "keep"
    assert e1["n.md"]["updated_at"] == "2026-01-02T00:00:00Z"
    _res2, _e2, fetched2 = _run_sync(kc, files)
    assert fetched2 == []


def test_assistant_context_states_each_experience_status(kc):
    kc.INDEX_FILE.write_text(json.dumps({"entries": [{
        "id": "px1", "project_full_name": "owner/alpha", "path": "experiences/x.md",
        "title": "Headless Chromium behind a TLS proxy", "tags": ["playwright", "chromium", "proxy"],
        "summary": "s", "resolution_status": "partial"}]}), encoding="utf-8")
    out = asyncio.run(kc.experience_context("playwright chromium proxy", "test", fetch_body=False))
    assert "وضعیت: نیمه‌حل" in out["block"] and "راه‌حلِ قطعی معرفی نکن" in out["block"]


# ── /command-room → /oversight ───────────────────────────────────────────────


def test_command_room_redirects_to_oversight():
    cfg = (_ROOT / "frontend/next.config.js").read_text(encoding="utf-8")
    assert "async redirects()" in cfg
    assert "source: '/command-room', destination: '/oversight'" in cfg
    assert "source: '/command-room/:path*', destination: '/oversight'" in cfg
    assert (_ROOT / "frontend/src/app/oversight/page.tsx").exists()


def test_catalog_shows_the_evidence_behind_a_status():
    page = (_ROOT / "frontend/src/app/knowledge-center/page.tsx").read_text(encoding="utf-8")
    assert 'data-testid="kc-status-evidence"' in page and "status_evidence" in page
