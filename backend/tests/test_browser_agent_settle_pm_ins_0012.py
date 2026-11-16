# -*- coding: utf-8 -*-
"""PM-INS-0012 (2026-11-16): live acceptance run read «۰ گفت‌وگو، ۰ مناظره» on /archive — the click was a client-side
route whose data arrives by fetch AFTER domcontentloaded, and the agent observed before it landed. The agent must
wait for the page's own requests to go quiet before the next observation. Real Chromium; skipped when unavailable."""
import asyncio
import http.server
import re
import socketserver
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import browser_agent as BA  # noqa: E402
from tests.test_browser_agent import _browser, _id, _run, _scripted  # noqa: E402

PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>خانه</title></head><body>
<nav><button type="button" id="go" onclick="history.pushState({}, '', '/archive'); document.getElementById('n').innerText='0';
 fetch('/slow').then(r => r.json()).then(d => { document.getElementById('n').innerText = 'گفت‌وگو: ' + d.c; });">آرشیو</button></nav>
<div id="n"></div></body></html>"""


@pytest.fixture(scope="module")
def spa():
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            if self.path == "/slow":
                time.sleep(1.5)
                body, ctype = b'{"c": 1}', "application/json"
            else:
                body, ctype = PAGE.encode(), "text/html; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), H)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/"
    srv.shutdown()


def test_observes_after_client_side_data_arrives(spa, tmp_path, monkeypatch):
    monkeypatch.setenv("BROWSER_AGENT_STORAGE", str(tmp_path / "runs"))
    monkeypatch.setattr(BA, "SHOTS_ROOT", tmp_path / "shots")
    model, st = _scripted([
        lambda o: '{"thought":"menu","action":{"type":"click","id":%d}}' % _id(o, "button", "آرشیو"),
        lambda o: '{"thought":"read","action":{"type":"done","success":true,"summary":"%s"}}'
        % (re.search(r"گفت‌وگو: \d+", o).group(0) if re.search(r"گفت‌وگو: \d+", o) else "خالی"),
    ])

    async def go():
        pw, b = await _browser()
        try:
            return await BA.run_agent(BA.new_run("تعداد گفت‌وگوها", spa, []), model, browser=b)
        finally:
            await b.close()
            await pw.stop()

    run = _run(go())
    assert run.status == "done", (run.status, run.summary)
    assert run.summary == "گفت‌وگو: 1", st["prompts"][-1][:800]


def test_settle_gives_up_within_budget_when_the_network_never_quiets():
    class P:
        def on(self, *_a):
            pass

    w = BA._NetWatch(P())
    w.inflight = 1  # e.g. a long poll that never ends

    t0 = time.monotonic()
    assert asyncio.run(w.settle(budget_ms=400)) is False
    assert time.monotonic() - t0 < 2
