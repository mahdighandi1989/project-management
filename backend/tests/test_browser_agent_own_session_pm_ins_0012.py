"""PM-INS-0012 — the browser agent on THIS app signs in with the caller's own session, and never hands the token
to a site other than the one the request came from."""
from starlette.requests import Request

from app.api.routes import browser_agent as R


def _req(headers):
    raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    return Request({"type": "http", "method": "POST", "path": "/", "headers": raw, "query_string": b""})


def test_same_site_gets_the_callers_token_in_local_storage():
    st = R._own_session_state(_req({"authorization": "Bearer abc.def", "origin": "https://app.example.com"}),
                              "https://app.example.com/projects", "pm.auth.token")
    assert st == {"cookies": [], "origins": [{"origin": "https://app.example.com",
                                             "localStorage": [{"name": "pm.auth.token", "value": "abc.def"}]}]}


def test_other_site_or_no_token_gets_nothing():
    assert R._own_session_state(_req({"authorization": "Bearer abc", "origin": "https://app.example.com"}),
                                "https://evil.example.org/", "pm.auth.token") is None
    assert R._own_session_state(_req({"origin": "https://app.example.com"}),
                                "https://app.example.com/", "pm.auth.token") is None
    assert R._own_session_state(_req({"authorization": "Bearer abc", "origin": "https://app.example.com"}),
                                "https://app.example.com/", "bad key!") is None
