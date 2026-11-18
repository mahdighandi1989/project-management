"""PM-INS-0030: «📸 عکس» shoots the project's real site, never AI Creator's own sign-in page."""

from app.api.routes import render_logs as R


def test_proxy_and_own_host_urls_map_to_the_real_site(monkeypatch):
    monkeypatch.setattr(R, "resolve_preview_frontend_url", lambda db, pid: "https://detective-1-frontend.onrender.com")
    t = R._screenshot_target
    assert t(None, "p", "https://ai-creator-frontend.onrender.com/login?next=%2Fapi%2Frender%2Finspector%2Fproxy%2Fp")[0] \
        == "https://detective-1-frontend.onrender.com/"
    assert t(None, "p", "https://ai-creator-frontend.onrender.com/api/render/inspector/proxy/p/people?x=1")[0] \
        == "https://detective-1-frontend.onrender.com/people?x=1"
    assert t(None, "p", "/api/render/inspector/proxy/p/~pt~123.abc/assets/a.js")[0] \
        == "https://detective-1-frontend.onrender.com/assets/a.js"
    # a real site URL is left alone
    assert t(None, "p", "https://detective-1-frontend.onrender.com/about") == ("https://detective-1-frontend.onrender.com/about", "")


def test_login_pages_are_flagged():
    assert R._looks_like_login({"url": "https://x/login?next=/a", "title": "AI Creator"})
    assert R._looks_like_login({"url": "https://x/", "title": "ورود"})
    assert not R._looks_like_login({"url": "https://x/", "title": "Detective-1 — دانشنامه"})
