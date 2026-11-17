"""PM-INS-0025 — the Creator Engine obeys the user's constraints and runs what it built before «ساخته شد»."""

import asyncio
import json
import os
import shutil
from pathlib import Path

import pytest

from app.services import creator_selfcheck as SC

BROKEN_HTML = """<!doctype html><html><head><link rel="stylesheet" href="css/style.css"></head><body>
<input id="display" readonly>
<div><button data-value="2">2</button><button data-value="3">3</button><button data-value="+">+</button>
<button data-value="=">=</button></div>
<script src="js/calculator.js"></script>
</body></html>
"""
APP_JS = """import { calculate } from './calculator.js';
let cur = '', prev = null, op = null;
const d = document.getElementById('display');
document.querySelectorAll('button').forEach(b => b.addEventListener('click', () => {
  const v = b.dataset.value;
  if (/[0-9.]/.test(v)) { cur += v; d.value = cur; }
  else if (v === '=') { d.value = String(calculate(prev, op, parseFloat(cur))); cur = d.value; }
  else { prev = parseFloat(cur); op = v; cur = ''; }
}));
"""
CALC_OK = "export function calculate(a, op, b) { return op === '+' ? a + b : op === '-' ? a - b : op === '*' ? a * b : a / b; }\n"
CALC_BAD = "export function calculate(a, op, b) { return op === '+' ? a - b : 0; }\n"
TEST_JS = """import { test } from 'node:test';
import assert from 'node:assert/strict';
import { calculate } from '../js/calculator.js';
test('2+3', () => assert.equal(calculate(2, '+', 3), 5));
"""


def _broken_calc(root: Path, calc: str = CALC_OK) -> Path:
    """The coordinator's DeepSeek output, reduced: no type=module, app.js never loaded, commonjs + jest."""
    for d in ("js", "css", "tests"):
        (root / d).mkdir(parents=True, exist_ok=True)
    (root / "index.html").write_text(BROKEN_HTML)
    (root / "js/app.js").write_text(APP_JS)
    (root / "js/calculator.js").write_text(calc)
    (root / "css/style.css").write_text("body{}")
    (root / "tests/calculator.test.js").write_text(TEST_JS)
    (root / "package.json").write_text(json.dumps({"name": "calc", "type": "commonjs", "scripts": {"test": "jest"},
                                                   "devDependencies": {"jest": "^29"}}))
    return root


def _browser_ok() -> bool:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            kw = {"headless": True, "args": ["--no-sandbox"]}
            if os.environ.get("SELFCHECK_CHROMIUM_PATH"):
                kw["executable_path"] = os.environ["SELFCHECK_CHROMIUM_PATH"]
            p.chromium.launch(**kw).close()
        return True
    except Exception:  # noqa: BLE001
        return False


def test_constraints_come_from_the_users_words_only():
    c = SC.detect_constraints("یک ماشین‌حساب ساده با HTML/CSS/JS، بدون بک‌اند")
    assert c["no_backend"] and c["static_web"] and c["phrases"]
    assert SC.detect_constraints("ماشین حساب بدون بکند")["no_backend"]
    assert SC.detect_constraints("calculator, no backend")["no_backend"]
    assert not SC.detect_constraints("یک CRM با FastAPI و Next.js")["no_backend"]
    assert not SC.detect_constraints("یک CRM با FastAPI و Next.js")["static_web"]
    assert SC.clean_technologies(["HTML", "FastAPI", "JavaScript", "SQLite"], c) == ["HTML", "JavaScript"]


def test_new_project_prompt_has_no_repo_review_note():
    from app.services.oversight_strong_prompt import build_strong_prompt
    new = build_strong_prompt(title="ماشین‌حساب", user_goal="ماشین‌حساب بدون بک‌اند", new_project=True)
    assert "بررسی اولیهٔ خودکار" not in new and "پیاده‌سازی قبلی" not in new and "موقعیت دقیق در پروژه" not in new
    assert "پروژهٔ تازه" in new
    old = build_strong_prompt(title="x", user_goal="y")
    assert "بررسی اولیهٔ خودکار" in old  # oversight tasks on existing repos keep it


def test_backend_files_are_dropped_when_there_is_no_backend():
    c = SC.detect_constraints("بدون بک‌اند")
    planned = [{"path": p} for p in ("main.py", "requirements.txt", "tests/test_main.py", "Dockerfile", "index.html",
                                     "js/app.js", "js/calculator.js", "backend/app.js", "README.md")]
    kept, dropped = SC.filter_planned_files(planned, c, True)
    assert {f["path"] for f in kept} == {"index.html", "js/app.js", "js/calculator.js", "README.md", "package.json"}
    assert set(dropped) == {"main.py", "requirements.txt", "tests/test_main.py", "Dockerfile", "backend/app.js"}
    order = [f["path"] for f in SC.order_for_generation(kept)]
    assert order.index("js/calculator.js") < order.index("js/app.js") < order.index("index.html")


def test_the_coordinators_defects_are_found_and_fixed_without_a_model(tmp_path):
    root = _broken_calc(tmp_path / "calc")
    probs = " ".join(p["problem"] for p in SC.static_problems(root))
    assert 'type="module"' in probs and "بار نمی‌کند" in probs and '"commonjs"' in probs and "jest" in probs
    done = SC.deterministic_fixes(root, static_web=True)
    assert len(done) == 3
    html = (root / "index.html").read_text()
    assert '<script type="module" src="js/calculator.js">' in html and '<script type="module" src="js/app.js">' in html
    pkg = json.loads((root / "package.json").read_text())
    assert pkg["type"] == "module" and pkg["scripts"]["test"] == "node --test" and "devDependencies" not in pkg
    assert SC.static_problems(root) == []
    assert SC.deterministic_fixes(root, static_web=True) == []  # idempotent


@pytest.mark.skipif(not SC.node_bin(), reason="node not installed")
def test_npm_test_runs_with_node_test_runner(tmp_path):
    root = _broken_calc(tmp_path / "calc")
    SC.deterministic_fixes(root, static_web=True)
    r = SC.run_tests(root)
    assert r["ran"] and r["ok"] and r["tests"] == 1 and r["passed"] == 1
    (root / "js/calculator.js").write_text(CALC_BAD)
    r = SC.run_tests(root)
    assert r["ran"] and not r["ok"] and r["failed"] == 1


def test_model_file_blocks_are_parsed_safely():
    out = SC.parse_file_blocks("blah\n=== FILE: js/a.js ===\n```js\nexport const a = 1;\n```\n=== END FILE ===\n"
                               "=== FILE: ../etc/x ===\nbad\n=== END FILE ===\n=== FILE: project.json ===\n{}\n=== END FILE ===")
    assert out == {"js/a.js": "export const a = 1;\n"}


@pytest.mark.skipif(not (SC.node_bin() and _browser_ok()), reason="node or chromium not available")
def test_fix_loop_runs_the_page_and_fixes_until_green(tmp_path):
    root = _broken_calc(tmp_path / "calc", CALC_BAD)
    calls = []

    async def ai(prompt: str) -> str:
        calls.append(prompt)
        if "سناریو" in prompt and "FILE:" not in prompt.split("## قالبِ خروجی")[-1][:5]:
            if "ایرادها" not in prompt:
                return json.dumps([{"click": "2"}, {"click": "+"}, {"click": "3"}, {"click": "="},
                                   {"expect": "5", "in": "#display"}])
        return "=== FILE: js/calculator.js ===\n" + CALC_OK + "=== END FILE ==="

    res = asyncio.run(SC.fix_loop(root, ai=ai, description="ماشین‌حساب", constraints={"no_backend": True},
                                  static_web=True, shot_dir=tmp_path / "shots"))
    assert res["green"], res
    r0 = res["rounds"][0]
    assert not r0["green"] and r0["tests"]["failed"] == 1 and r0["browser"]["steps"] == "4/5"
    assert res["rounds"][-1]["rewritten"] == ["js/calculator.js"]
    assert res["final"]["browser"]["steps_passed"] == 5 and res["final"]["tests"]["passed"] == 1
    assert (tmp_path / "shots" / "selfcheck_1.png").exists()


def test_create_project_obeys_constraints_and_records_selfcheck(tmp_path, monkeypatch):
    from app.services.simple_creator import SimpleProjectCreator
    creator = SimpleProjectCreator(workspace=str(tmp_path / "ws"))
    seen = []

    async def ai(prompt: str):
        seen.append(prompt)
        if "خروجی باید JSON باشه" in prompt:
            return json.dumps({"files": [{"path": p} for p in (
                "main.py", "requirements.txt", "tests/test_main.py", "index.html", "js/app.js", "js/calculator.js",
                "tests/calculator.test.js", "package.json", "css/style.css")]}), "deepseek-chat"
        if "سناریو" in prompt:
            return "[]", "deepseek-chat"
        for path, body in (("js/calculator.js", CALC_OK), ("js/app.js", APP_JS), ("index.html", BROKEN_HTML),
                           ("tests/calculator.test.js", TEST_JS), ("css/style.css", "body{}"),
                           ("package.json", '{"name":"c","type":"commonjs","scripts":{"test":"jest"}}')):
            if f"فایل: {path}\n" in prompt:
                return body, "deepseek-chat"
        return "x", "deepseek-chat"

    cons = SC.detect_constraints("ماشین‌حساب بدون بک‌اند")
    project = asyncio.run(creator.create_project("test-calculator", "ماشین‌حساب بدون بک‌اند", "fullstack", ["FastAPI"],
                                                 ai_generate=ai, constraints=cons, fix_rounds=0))
    root = tmp_path / "ws" / project.id
    assert project.project_type == "static-web" and project.technologies == []
    assert not list(root.rglob("*.py")) and not (root / "requirements.txt").exists()
    assert set(project.structure["dropped_by_constraints"]) == {"main.py", "requirements.txt", "tests/test_main.py"}
    # every file saw the files written before it
    app_prompt = next(p for p in seen if "فایل: js/app.js\n" in p)
    assert "### js/calculator.js" in app_prompt
    # the mechanical defects were fixed before anything else, and project.files matches the disk
    html = next(f for f in project.files if f.path == "index.html").content
    assert 'type="module" src="js/app.js"' in html and html == (root / "index.html").read_text()
    assert project.selfcheck["rounds"][0]["auto_fixes"]
    assert not list(root.glob(".selfcheck*")) and (tmp_path / "ws" / "_selfcheck" / project.id).is_dir()
    if SC.node_bin():
        assert project.selfcheck["final"]["tests"]["ok"]
    # reload from disk keeps the record
    again = SimpleProjectCreator(workspace=str(tmp_path / "ws")).get_project(project.id)
    assert again.selfcheck["rounds"] and again.constraints["no_backend"]


def test_creator_preview_is_ticketed_and_sandboxed(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app.core import auth as A
    from app.services import simple_creator as SCR
    creator = SCR.SimpleProjectCreator(workspace=str(tmp_path / "ws"))
    monkeypatch.setattr(SCR, "_creator", creator)
    p = SCR.Project(id="proj_test1", name="calc", description="", project_type="static-web")
    creator.projects[p.id] = p
    root = _broken_calc(tmp_path / "ws" / p.id)
    (root / "project.json").write_text("{}")
    from app.main import app
    c = TestClient(app)
    path = f"{A.CREATOR_PREVIEW_PREFIX}{p.id}/{A.PREVIEW_PATH_MARK}{A.preview_ticket('creator:' + p.id)}/"
    assert A.preview_allowed(path + "index.html", "GET", {})
    assert not A.preview_allowed(path + "index.html", "POST", {})
    # an inspector ticket does not open the creator preview (and the other way round)
    bad = f"{A.CREATOR_PREVIEW_PREFIX}{p.id}/{A.PREVIEW_PATH_MARK}{A.preview_ticket(p.id)}/index.html"
    assert not A.preview_allowed(bad, "GET", {})
    assert not A.preview_allowed(f"{A.PREVIEW_PREFIX}{p.id}/{A.PREVIEW_PATH_MARK}{A.preview_ticket('creator:' + p.id)}/x",
                                 "GET", {})
    r = c.get(path + "js/app.js")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/javascript")
    assert "sandbox" in r.headers["content-security-policy"]
    assert c.get(path + "project.json").status_code == 404
    assert c.get(path + "../../etc/passwd").status_code in (404, 401)
    assert c.get(bad).status_code == 401
