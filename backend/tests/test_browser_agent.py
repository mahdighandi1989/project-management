# -*- coding: utf-8 -*-
"""«عاملِ مرورگر» ِ بازرس ویژه (2026-11-15, owner plan item 12): the loop with REAL Chromium against a local page and
a scripted «weak model» that only reads the text observation. Skipped when Chromium cannot launch."""
import asyncio
import http.server
import re
import socketserver
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import browser_agent as BA  # noqa: E402

FORM = """<!doctype html><html><head><meta charset="utf-8"><title>فرم</title></head><body>
<h1>ثبتِ سفارش</h1>
<form onsubmit="event.preventDefault(); document.getElementById('out').innerText =
  'saved:' + email.value + ':' + plan.value + ':' + terms.checked; return false;">
  <label for="email">ایمیل</label><input id="email" name="email" required>
  <label for="plan">پلن</label><select id="plan"><option>رایگان</option><option>حرفه‌ای</option></select>
  <label><input type="checkbox" id="terms"> قوانین را می‌پذیرم</label>
  <button type="submit">ثبت</button>
</form>
<a href="http://evil.example/steal">لینکِ بیرونی</a>
<div id="out"></div></body></html>"""


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    root = tmp_path_factory.mktemp("site")
    (root / "index.html").write_text(FORM, encoding="utf-8")

    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(root), **k)

        def log_message(self, *a):
            pass

    srv = socketserver.TCPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/index.html"
    srv.shutdown()


async def _browser():
    from playwright.async_api import async_playwright

    pw = await async_playwright().start()
    exe = Path("/opt/pw-browsers/chromium")
    try:
        b = await pw.chromium.launch(headless=True, **({"executable_path": str(exe)} if exe.exists() else {}))
    except Exception as e:  # noqa: BLE001
        await pw.stop()
        pytest.skip(f"Chromium unavailable: {e}")
    return pw, b


def _id(obs: str, role: str, name: str) -> int:
    m = re.search(rf'^\[(\d+)\] {role} "[^"]*{re.escape(name)}', obs, re.M)
    assert m, f"{role} {name} not in observation:\n{obs[:1500]}"
    return int(m.group(1))


def _scripted(steps):
    """A model that answers each turn with steps[i](observation) — no knowledge beyond the text it is given."""
    state = {"i": 0, "prompts": []}

    async def model(system, user, shot):
        state["prompts"].append(user)
        f = steps[min(state["i"], len(steps) - 1)]
        state["i"] += 1
        return f(user)
    return model, state


def _run(coro):
    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(coro)


def test_fills_a_form_and_waits_for_approval_before_submitting(site, tmp_path, monkeypatch):
    monkeypatch.setenv("BROWSER_AGENT_STORAGE", str(tmp_path / "runs"))
    monkeypatch.setattr(BA, "SHOTS_ROOT", tmp_path / "shots")
    model, st = _scripted([
        lambda o: '{"thought":"email first","action":{"type":"type","id":%d,"text":"a@b.c"}}' % _id(o, "textbox", "ایمیل"),
        lambda o: 'Sure! ```json\n{"thought":"plan","action":{"type":"select","id":%d,"option":"حرفه‌ای"}}\n```' % _id(o, "select", "پلن"),
        lambda o: "{'thought': 'terms', 'action': {'type': 'check', 'id': %d, 'on': true,}}" % _id(o, "checkbox", "قوانین"),
        lambda o: '{"thought":"submit","action":{"type":"click","id":%d}}' % _id(o, "button", "ثبت"),
        lambda o: '{"thought":"saved","action":{"type":"done","success":true,"summary":"%s"}}'
        % re.search(r"saved:[^\n]*", o).group(0),
    ])

    async def go():
        pw, b = await _browser()
        try:
            run = BA.new_run("سفارشِ حرفه‌ای با ایمیل a@b.c ثبت کن", site, [])
            task = asyncio.create_task(BA.run_agent(run, model, browser=b))
            for _ in range(200):
                await asyncio.sleep(0.05)
                if run.status == "waiting_confirm":
                    assert "ثبت" in run.pending["text"]
                    assert BA.reply(run.id, True)
                    break
            return await asyncio.wait_for(task, 60)
        finally:
            await b.close()
            await pw.stop()

    run = _run(go())
    assert run.status == "done", (run.status, run.summary, [(s.action, s.result) for s in run.steps])
    assert run.summary == "saved:a@b.c:حرفه‌ای:true"
    assert [s.action["type"] for s in run.steps] == ["type", "select", "check", "click", "done"]
    assert all(s.shot for s in run.steps)
    assert (tmp_path / "shots" / run.id / "1.jpg").is_file()
    assert BA.load_run(run.id)["status"] == "done"  # persisted log
    # the model saw a compact numbered list, never raw HTML
    assert "<form" not in st["prompts"][0] and '] textbox "ایمیل"' in st["prompts"][0]


def test_offsite_navigation_is_blocked_and_bad_json_twice_fails(site, tmp_path, monkeypatch):
    monkeypatch.setenv("BROWSER_AGENT_STORAGE", str(tmp_path / "runs"))
    monkeypatch.setattr(BA, "SHOTS_ROOT", tmp_path / "shots")
    model, _ = _scripted([
        lambda o: '{"thought":"leave","action":{"type":"goto","url":"http://evil.example/x"}}',
        lambda o: "I think I should click something",
        lambda o: '{"action":{"type":"click","id":999}}',
    ])

    async def go():
        pw, b = await _browser()
        try:
            run = BA.new_run("t", site, [])
            return await BA.run_agent(run, model, browser=b)
        finally:
            await b.close()
            await pw.stop()

    run = _run(go())
    assert run.steps[0].ok is False and "مجاز نیست" in run.steps[0].result
    assert run.status == "failed" and "نامعتبر" in run.summary


def test_stuck_is_detected(site, tmp_path, monkeypatch):
    monkeypatch.setenv("BROWSER_AGENT_STORAGE", str(tmp_path / "runs"))
    monkeypatch.setattr(BA, "SHOTS_ROOT", tmp_path / "shots")
    model, _ = _scripted([lambda o: '{"thought":"scroll","action":{"type":"wait","ms":200}}'])

    async def go():
        pw, b = await _browser()
        try:
            return await BA.run_agent(BA.new_run("t", site, []), model, browser=b)
        finally:
            await b.close()
            await pw.stop()

    run = _run(go())
    assert run.status == "stuck" and len(run.steps) == 3


def test_policy_units():
    assert BA.host_allowed("https://a.example.com/x", {"example.com"})
    assert not BA.host_allowed("https://example.com.evil.io/", {"example.com"})
    assert BA.needs_confirmation({"type": "click", "element": {"name": "حذفِ حساب"}})
    assert BA.needs_confirmation({"type": "click", "element": {"name": "بعدی"}}) is None
    with pytest.raises(BA.ActionError):
        BA.validate_action({"action": {"type": "type", "id": 1, "secret_ref": "DATABASE_URL"}}, {"elements": [{"id": 1}]})
    assert BA.resolve_secret("SECRET_KEY") == ""


def test_api_end_to_end_through_the_shared_pool(site, tmp_path, monkeypatch):
    """POST /runs → background run on the shared Chromium pool → GET /runs/{id} → screenshot."""
    import time as _t

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.routes import browser_agent as routes
    from app.services.verify_runtime import browser_pool

    if Path("/opt/pw-browsers/chromium").exists():
        monkeypatch.setenv("CHROMIUM_EXECUTABLE", "/opt/pw-browsers/chromium")
    monkeypatch.setenv("BROWSER_AGENT_STORAGE", str(tmp_path / "runs"))
    monkeypatch.setattr(BA, "SHOTS_ROOT", tmp_path / "shots")
    monkeypatch.setattr(browser_pool, "_pool", None, raising=False)

    async def fake_default_model(model_id):
        async def m(system, user, shot):
            if "saved:" not in user and "typed" not in user:
                return '{"thought":"email","action":{"type":"type","id":%d,"text":"x@y.z"}}' % _id(user, "textbox", "ایمیل")
            return '{"thought":"ok","action":{"type":"done","success":true,"summary":"filled"}}'
        return m

    monkeypatch.setattr(BA, "default_model", fake_default_model)
    monkeypatch.setattr(BA, "model_supports_vision", lambda mid: False)
    app = FastAPI()
    app.include_router(routes.router, prefix="/api")
    with TestClient(app) as c:
        r = c.post("/api/inspector-agent/runs", json={"task": "fill the email", "start_url": site, "model_id": "fake"})
        if r.status_code == 503:
            pytest.skip(r.text)
        rid = r.json()["run_id"]
        d = {}
        for _ in range(150):
            d = c.get(f"/api/inspector-agent/runs/{rid}").json()
            if d["status"] not in ("starting", "running"):
                break
            _t.sleep(0.2)
        if d["status"] == "failed" and "Chromium" in d.get("summary", ""):
            pytest.skip(d["summary"])
        assert d["status"] == "done", d
        assert c.get(f"/api/inspector-agent/runs/{rid}/shots/1.jpg").headers["content-type"] == "image/jpeg"
        assert c.get(f"/api/inspector-agent/runs/{rid}?after=1").json()["steps"][0]["n"] == 2
        assert c.get("/api/inspector-agent/runs").json()[0]["id"] == rid
        assert c.post("/api/inspector-agent/runs", json={"task": "x y z", "start_url": "ftp://a.example.com/"}).status_code == 400
        assert c.get(f"/api/inspector-agent/runs/{rid}/shots/..%2F..%2Fetc").status_code == 404


def test_snapshot_endpoint(site, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.routes import browser_agent as routes
    from app.services.verify_runtime import browser_pool

    if Path("/opt/pw-browsers/chromium").exists():
        monkeypatch.setenv("CHROMIUM_EXECUTABLE", "/opt/pw-browsers/chromium")
    monkeypatch.setattr(browser_pool, "_pool", None, raising=False)
    app = FastAPI()
    app.include_router(routes.router, prefix="/api")
    with TestClient(app) as c:
        r = c.get("/api/inspector-agent/snapshot", params={"url": site})
        if r.status_code == 503:
            pytest.skip(r.text)
        assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg" and r.content[:2] == b"\xff\xd8"
        assert c.get("/api/inspector-agent/snapshot", params={"url": "file:///etc/passwd"}).status_code in (400, 422)
