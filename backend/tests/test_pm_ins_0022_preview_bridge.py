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


def test_next_absolute_paths_stay_inside_the_project_preview():
    ap = "/api/render/inspector/proxy/P/~pt~T"
    js = 'r.p="/_next/";a=\'/_next/x.js\';b="\\"/_next/c.js\\"";u=url(/_next/m.woff)'
    out = RL._rewrite_next_paths(js, ap)
    assert '"/_next/' not in out and "'/_next/" not in out and "url(/_next/" not in out
    assert out.count(ap + "/_next/") == 4
    already = f'src="{ap}/_next/x.js"'
    assert RL._rewrite_next_paths(already, ap) == already


def test_svg_clicks_do_not_crash_the_bridge():
    assert "el.className.split(' ')[0] : '';" not in RL.INSPECTOR_BRIDGE_SCRIPT.replace(
        "(typeof el.className === 'string' && el.className) ? '.' + el.className.split(' ')[0] : '';", "")


def test_page_fetches_go_through_the_ticketed_prefix():
    assert '.replace("__PROXY__", asset_prefix)' in inspect.getsource(RL.inspector_page_proxy)


def test_next_client_navigation_stays_in_the_preview():
    src = inspect.getsource(RL.inspector_page_proxy)
    assert '"rsc", "next-router-state-tree"' in src and '"x-component"' in src and '"text/plain"' in src
    assert "u instanceof URL" in RL._PROXY_MONITOR_SCRIPT_TEMPLATE and "pushState" in RL._PROXY_MONITOR_SCRIPT_TEMPLATE


def test_next_pages_see_their_own_path():
    t = RL._PROXY_MONITOR_SCRIPT_TEMPLATE
    assert "STRIP='__STRIP__'==='1'" in t and "if(!STRIP)['pushState','replaceState']" in t
    assert '.replace("__STRIP__", "1" if _is_next else "0")' in inspect.getsource(RL.inspector_page_proxy)
