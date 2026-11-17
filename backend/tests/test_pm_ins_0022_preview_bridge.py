"""PM-INS-0022 — every project gets the bridge in the PREVIEW, without a commit in its repo."""

import inspect
from pathlib import Path

from app.api.routes import render_logs as RL

PLAIN = '<html><head><title>x</title></head><body><div id="root"></div><script src="/a.js"></script></body></html>'


def test_a_page_without_bridge_gets_the_current_template(monkeypatch):
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://ai-creator-backend-q677.onrender.com")
    out = RL._inject_preview_bridge(PLAIN, "gh_mahdighandi1989_detective_1")
    a = RL.analyze_bridge_html(out)
    assert a["present"] and a["version"] == RL.INSPECTOR_BRIDGE_VERSION
    assert a["ws_url"] == "wss://ai-creator-backend-q677.onrender.com/api/render/ws/bridge/gh_mahdighandi1989_detective_1"
    assert "__BRIDGE_" not in out and "injected by the preview proxy" in out
    assert out.index("Inspector Bridge Script") < out.index("</body>")


def test_a_page_with_its_own_bridge_is_left_alone():
    q = (Path(__file__).parent / "fixtures" / "quran_bridge_v24_index.html").read_text(encoding="utf-8")
    assert RL._inject_preview_bridge(q, "p") == q


def test_wired_into_the_proxy_and_the_diagnosis():
    assert "_inject_preview_bridge(html, project_id)" in inspect.getsource(RL.inspector_page_proxy)
    src = inspect.getsource(RL)
    assert 'result["bridge_source"] = "preview_injection"' in src
