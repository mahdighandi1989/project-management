"""PM-INS-0021 — quran-web-app-v1's bridge 2.4 is switched off in its production build
(`if ('%VITE_ENABLE_INSPECTOR_BRIDGE%' !== 'true') return;`) and reads its WS address only from
`window.__INSPECTOR_WS_URL__`. The preview proxy must switch it on for the owner's view and set the address first.
The fixture is the real deployed index.html of quran-web-app (2026-11-17)."""

from pathlib import Path

from app.api.routes import render_logs as RL

HTML = (Path(__file__).parent / "fixtures" / "quran_bridge_v24_index.html").read_text(encoding="utf-8")
PID = "gh_mahdighandi1989_quran_web_app_v1"


def test_analysis_of_the_real_quran_page():
    a = RL.analyze_bridge_html(HTML)
    assert a == {"present": True, "version": "2.4", "build_disabled": True, "ws_source": "window", "ws_url": None}


def test_proxy_switches_it_on_and_sets_the_address_before_the_script(monkeypatch):
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://ai-creator-backend-q677.onrender.com")
    out = RL._enable_project_bridge(HTML, PID)
    assert "%VITE_ENABLE_INSPECTOR_BRIDGE%" not in out and "if ('true' !== 'true') return;" in out
    setter = f'window.__INSPECTOR_WS_URL__="wss://ai-creator-backend-q677.onrender.com/api/render/ws/bridge/{PID}"'
    assert setter in out and out.index(setter) < out.index("Inspector Bridge Script")
    assert RL.analyze_bridge_html(out)["build_disabled"] is False


def test_pages_without_a_bridge_are_untouched():
    plain = "<html><head><title>x</title></head><body>hi</body></html>"
    assert RL._enable_project_bridge(plain, PID) == plain


def test_proxy_route_calls_it():
    import inspect
    assert "_enable_project_bridge(html, project_id)" in inspect.getsource(RL.inspector_page_proxy)


def test_ticket_in_the_asset_path_opens_only_that_project(monkeypatch):
    """Module scripts from the sandboxed preview carry no cookie — the ticket rides in the path (live 401 on
    /assets/index-CjLBx5Le.js left the quran app blank, 2026-11-17)."""
    from app.core import auth
    t = auth.preview_ticket(PID)
    ok = f"/api/render/inspector/proxy/{PID}/~pt~{t}/assets/index-CjLBx5Le.js"
    assert auth.preview_allowed(ok, "GET", {})
    assert not auth.preview_allowed(ok, "POST", {})
    assert not auth.preview_allowed(f"/api/render/inspector/proxy/other_project/~pt~{t}/assets/x.js", "GET", {})
    assert not auth.preview_allowed(f"/api/render/inspector/proxy/{PID}/~pt~1.bad/assets/x.js", "GET", {})
    assert not auth.preview_allowed(f"/api/render/inspector/proxy/{PID}/assets/x.js", "GET", {})


def test_proxy_rewrites_assets_with_the_ticket_and_strips_it_upstream():
    import inspect
    src = inspect.getsource(RL.inspector_page_proxy)
    assert "path.startswith(PREVIEW_PATH_MARK)" in src and "asset_prefix" in src
    assert '"Access-Control-Allow-Origin": "*"' in src
