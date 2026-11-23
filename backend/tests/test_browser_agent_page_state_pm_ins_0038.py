# -*- coding: utf-8 -*-
"""PM-INS-0038 (owner, 2026-11-23): on quran-web-app the browser agent searched «رحمن» in a server browser that was not
signed in (no dataset loaded) and reported «تعداد نتایج: ۰» as a fact; the owner's signed-in Chrome shows 64.

Real Chromium against a local page shaped like that site (a «ورود با گوگل» button, a form-less search box, the
dataset in localStorage) and a scripted «weak model» that reads only the text observation:

* signed out + empty  ⇒ the run ends «unreliable» with the reason, never «0» as a fact — even when the model says 0;
* a session carrying the data ⇒ the real count, «done», evidence quoted from the page and verified against it;
* typing + Enter in the search box never waits for approval; a real form submit still does;
* `done` is held back while the page is still loading and the answer is read from the settled page.
"""
import asyncio
import http.server
import json
import re
import socketserver
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import browser_agent as BA  # noqa: E402

PAGE = """<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><title>مرکز دادهٔ قرآن</title></head><body>
<button id="auth" type="button"></button>
<h2>ورود منابع داده</h2>
<input id="q" placeholder="جستجو در کلمات...">
<div id="out">نتایج: ٠</div>
<script>
const data = JSON.parse(localStorage.getItem('ds') || '[]');
document.getElementById('auth').innerText = localStorage.getItem('user') ? 'خروج' : 'ورود با گوگل';
const q = document.getElementById('q'), out = document.getElementById('out');
q.addEventListener('keydown', (e) => {
  if (e.key !== 'Enter') return;
  const hits = data.filter((v) => v.includes(q.value));
  const show = () => { out.innerText = 'نتایج: ' + hits.length.toLocaleString('ar-EG') + (hits[0] ? '\\n' + hits[0] : ''); };
  if (location.search.includes('slow')) { out.innerText = 'در حال جستجو…'; setTimeout(show, 1500); } else show();
});
</script></body></html>"""

VERSES = ["الفاتحة — آیه ١ بِسْمِ اللَّهِ الرحمن الرَّحِيمِ"] + [f"سوره {i} الرحمن" for i in range(63)] + ["بی‌ربط"]


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    root = tmp_path_factory.mktemp("quran")
    (root / "index.html").write_text(PAGE, encoding="utf-8")

    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(root), **k)

        def log_message(self, *a):
            pass

    srv = socketserver.TCPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def _id(obs: str, role: str, name: str) -> int:
    m = re.search(rf'^\[(\d+)\] {role} "[^"]*{re.escape(name)}', obs, re.M)
    assert m, f"{role} {name} not in observation:\n{obs[:1500]}"
    return int(m.group(1))


def _scripted(steps):
    state = {"i": 0, "prompts": []}

    async def model(system, user, shot):
        state["prompts"].append(user)
        f = steps[min(state["i"], len(steps) - 1)]
        state["i"] += 1
        return f(user)
    return model, state


def _go(url, model, tmp_path, monkeypatch, storage_state=None):
    monkeypatch.setenv("BROWSER_AGENT_STORAGE", str(tmp_path / "runs"))
    monkeypatch.setattr(BA, "SHOTS_ROOT", tmp_path / "shots")

    async def go():
        from playwright.async_api import async_playwright

        pw = await async_playwright().start()
        exe = Path("/opt/pw-browsers/chromium")
        try:
            b = await pw.chromium.launch(headless=True, **({"executable_path": str(exe)} if exe.exists() else {}))
        except Exception as e:  # noqa: BLE001
            await pw.stop()
            pytest.skip(f"Chromium unavailable: {e}")
        try:
            run = BA.new_run("رحمن را جستجو کن و بگو چند نتیجه و اولین آیه", url, [])
            # 40 s: a run that waited for approval (10 min) would time out here
            return await asyncio.wait_for(BA.run_agent(run, model, browser=b, storage_state=storage_state), 40)
        finally:
            await b.close()
            await pw.stop()

    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(go())


def _search(o):
    return '{"thought":"search","action":{"type":"type","id":%d,"text":"رحمن","submit":true}}' % _id(o, "textbox", "جستجو")


def _read_count(o):
    """The weak model: reports whatever «نتایج: N» it sees, as a fact, quoting it."""
    m = re.search(r"نتایج: (\S+)", o.split("Visible text")[-1])
    first = re.search(r"نتایج: \S+\n(.+)", o.split("Visible text")[-1])
    return json.dumps({"thought": "read", "action": {
        "type": "done", "success": True, "evidence": m.group(0),
        "summary": f"تعداد نتایج: {m.group(1)}." + (f" اولین: {first.group(1)}" if first and m.group(1) != "٠" else " اولین آیه پیدا نشد.")}},
        ensure_ascii=False)


def test_signed_out_empty_page_is_reported_unreliable_not_zero(site, tmp_path, monkeypatch):
    model, st = _scripted([_search, _read_count])
    run = _go(site + "/index.html", model, tmp_path, monkeypatch)
    assert [s.action["type"] for s in run.steps] == ["type", "done"]          # search typed with NO approval step
    assert run.status == "unreliable" and run.reliable is False, (run.status, run.summary)
    assert run.summary.startswith("⚠️ نتیجه قابل اعتماد نیست چون") and "ورود با گوگل" in run.summary
    assert "گفتهٔ مدل (تأییدنشده)" in run.summary                             # the model's «0» is kept, but not as fact
    ev = run.evidence
    assert ev["signin"] == "out" and ev["quote_verified"] and "نتایج: ٠" in ev["line"] and site in ev["line"]
    assert "مرکز دادهٔ قرآن" in ev["line"] and "وارد نشده" in ev["line"]
    # the model was told, before answering, what the page can and cannot prove
    assert "PAGE STATE" in st["prompts"][1] and "NOT signed in" in st["prompts"][1] and "NOT a fact" in st["prompts"][1]
    saved = BA.load_run(run.id)
    assert saved["status"] == "unreliable" and saved["evidence"]["line"] == ev["line"]
    assert BA.list_runs()[0]["reliable"] is False


def test_with_a_transferred_session_the_real_count_is_reported_with_evidence(site, tmp_path, monkeypatch):
    state = {"cookies": [], "origins": [{"origin": site, "localStorage": [
        {"name": "user", "value": "owner"}, {"name": "ds", "value": json.dumps(VERSES, ensure_ascii=False)}]}]}
    model, st = _scripted([_search, _read_count])
    run = _go(site + "/index.html", model, tmp_path, monkeypatch, storage_state=state)
    assert run.status == "done" and run.reliable is True, (run.status, run.summary)
    assert "٦٤" in run.summary and "الفاتحة — آیه ١" in run.summary
    assert run.evidence["signin"] == "in" and run.evidence["session"] and run.evidence["quote_verified"]
    assert "نتایج: ٦٤" in run.evidence["line"] and "واردشده" in run.evidence["line"]
    assert "NOT a fact" not in st["prompts"][1]


def test_done_waits_for_a_result_that_is_still_loading(site, tmp_path, monkeypatch):
    state = {"cookies": [], "origins": [{"origin": site, "localStorage": [
        {"name": "user", "value": "owner"}, {"name": "ds", "value": json.dumps(VERSES, ensure_ascii=False)}]}]}

    def hasty(o):  # answers while the page still says «در حال جستجو…»
        if "در حال جستجو" in o:
            return '{"thought":"nothing yet","action":{"type":"done","success":true,"summary":"نتیجه‌ای نیامد","evidence":"در حال جستجو"}}'
        return _read_count(o)

    model, st = _scripted([_search, hasty])
    run = _go(site + "/index.html?slow", model, tmp_path, monkeypatch, storage_state=state)
    assert run.status == "done" and "٦٤" in run.summary, (run.status, run.summary, [(s.action, s.result) for s in run.steps])
    assert any("پایان نگه داشته شد" in s.result for s in run.steps)
    assert "loading: " in st["prompts"][1] and "use wait" in st["prompts"][1]


def test_a_done_without_evidence_gets_one_reminder_then_the_engines_own_line(site, tmp_path, monkeypatch):
    model, st = _scripted([lambda o: '{"thought":"x","action":{"type":"done","success":true,"summary":"صفحه باز شد"}}'])
    run = _go(site + "/index.html", model, tmp_path, monkeypatch)
    assert len(st["prompts"]) == 2 and 'done needs "evidence"' in st["prompts"][1]
    # nothing zero was claimed, but the page itself shows an empty marker on a signed-out page ⇒ still flagged
    assert run.status == "unreliable" and "موتور از صفحه برداشت" in run.evidence["line"]


def test_policy_search_is_safe_real_submits_still_ask():
    box = {"role": "textbox", "name": "جستجو در کلمات...", "type": "text", "search": True}
    assert BA.needs_confirmation({"type": "type", "submit": True, "element": box}) is None
    assert BA.needs_confirmation({"type": "click", "element": {"name": "جستجو", "submits": True, "search": True}}) is None
    # everything that could write still waits for the owner
    assert BA.needs_confirmation({"type": "type", "submit": True, "element": {"role": "textbox", "name": "ایمیل", "type": "text"}})
    assert BA.needs_confirmation({"type": "click", "element": {"name": "ثبت", "submits": True}})
    assert BA.needs_confirmation({"type": "click", "element": {"name": "حذفِ همه", "search": True}})
    assert BA.needs_confirmation({"type": "type", "element": {"type": "password", "search": False}})


def test_search_flag_only_where_enter_cannot_submit_something_else(tmp_path, monkeypatch):
    html = """<!doctype html><meta charset="utf-8"><body>
    <input id="free" type="search" placeholder="x">
    <form><input name="q" placeholder="Search"><button type="submit">Go</button></form>
    <form method="post"><input name="q" placeholder="جستجو"><button type="submit">ثبت</button></form>
    <form><input placeholder="جستجوی نام"><input name="email" placeholder="ایمیل"><button type="submit">ارسال</button></form>
    </body>"""

    async def go():
        from playwright.async_api import async_playwright

        pw = await async_playwright().start()
        exe = Path("/opt/pw-browsers/chromium")
        try:
            b = await pw.chromium.launch(headless=True, **({"executable_path": str(exe)} if exe.exists() else {}))
        except Exception as e:  # noqa: BLE001
            await pw.stop()
            pytest.skip(f"Chromium unavailable: {e}")
        try:
            page = await b.new_page()
            await page.set_content(html)
            return await page.evaluate(BA.OBSERVE_JS, 80)
        finally:
            await b.close()
            await pw.stop()

    obs = asyncio.get_event_loop_policy().new_event_loop().run_until_complete(go())
    flags = [(e["role"], e["name"], bool(e.get("search"))) for e in obs["elements"]]
    assert flags == [("textbox", "x", True), ("textbox", "Search", True), ("button", "Go", True),
                     ("textbox", "جستجو", False), ("button", "ثبت", False),
                     ("textbox", "جستجوی نام", False), ("textbox", "ایمیل", False), ("button", "ارسال", False)], flags


def test_page_state_units():
    quran = {"url": "https://q.example/search", "title": "t", "text": "ورود منابع داده\nنتایج: ٠\nصفحه: ١ / ١",
             "elements": [{"id": 1, "role": "button", "tag": "button", "name": "ورود با گوگل"}]}
    st = BA.assess_page(quran, blocked={"api.q.example": 2, "www.google-analytics.com": 9})
    assert st["signin"] == "out" and st["empty"] == "نتایج: ٠" and st["blocked"] == {"api.q.example": 2}
    assert len(BA.doubt_reasons(st)) == 2
    # a heading that merely contains «ورود» is not a sign-in prompt; no marker, no claim ⇒ nothing to doubt
    plain = {"url": "https://q.example/", "title": "t", "text": "ورود منابع داده\nنتایج: ١٠", "elements": [
        {"id": 1, "role": "button", "tag": "button", "name": "ورود منابع داده"}]}
    st2 = BA.assess_page(plain)
    assert st2["signin"] == "unknown" and not st2["empty"] and BA.doubt_reasons(st2, "۱۰ نتیجه آمد") == []
    # signed out but the answer is not an empty reading ⇒ reported normally (the evidence line still says «وارد نشده»)
    assert BA.doubt_reasons(BA.assess_page({**quran, "text": "عنوان: مرکز حفظ"}), "عنوانِ صفحه «مرکز حفظ» است") == []
    # the model says zero on a signed-out page even without a marker ⇒ doubted
    assert BA.doubt_reasons(BA.assess_page({**quran, "text": "—"}), "تعداد نتایج: ۰")
    # a real zero on a signed-in page stays a fact
    inn = {"url": "https://q.example/", "title": "t", "text": "نتایج: 0", "elements": [{"id": 1, "role": "button", "tag": "button", "name": "خروج"}]}
    assert BA.doubt_reasons(BA.assess_page(inn, session=True), "۰ نتیجه") == []
    assert BA.quote_on_page("نتایج: 0", quran) and not BA.quote_on_page("نتایج: 64", quran)
    assert BA.validate_action({"action": {"type": "done", "summary": "s", "evidence": "e"}}, {"elements": []})["evidence"] == "e"
