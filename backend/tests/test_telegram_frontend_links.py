# -*- coding: utf-8 -*-
"""The Telegram bot and the frontend move together (owner, 2026-11-15, plan item 7: «سیم‌کشیِ پروژه به قابلیت‌های
ربات تلگرامش نباید به هم بخوره … همگام باید با هم پیشرفت کنن»).

Every inline-keyboard / message link the backend builds as ``f"{base}/<page>?tab=<x>"`` must
  1. point at a page that exists in ``frontend/src/app`` (a renamed/moved page breaks this test), and
  2. use a ``tab`` value that page really reads from the URL.
Also: the bot's webhook stays public (Telegram cannot sign in) and its handler module imports.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "frontend" / "src" / "app"
BACKEND = ROOT / "backend" / "app"

LINK = re.compile(r"\{(?:base|app_base|app_base_url|frontend_base)\}(/[A-Za-z0-9_\-/]*)(\?[^\"'}\s]*)?")

#: page → (file that reads ?tab=, the list literal of accepted tabs is found next to `get('tab')`)
TAB_READERS = {
    "/oversight": ROOT / "frontend/src/app/oversight/page.tsx",
    "/settings": ROOT / "frontend/src/components/views/SettingsView.tsx",
    "/archive": ROOT / "frontend/src/app/archive/page.tsx",
}


def _links():
    out = []
    for f in BACKEND.rglob("*.py"):
        for line in f.read_text(encoding="utf-8").splitlines():
            if "url" not in line.lower():
                continue  # `{base}` also builds file paths in scanners; only links (url=…, "url": …) count
            for m in LINK.finditer(line):
                path, query = m.group(1), m.group(2) or ""
                if re.match(r"^/(get|set|send|delete|edit|answer)[A-Z]", path) or path.startswith("/api/"):
                    continue  # Telegram Bot API methods (getMe, setWebhook…) and API calls, not frontend pages
                out.append((f.relative_to(ROOT).as_posix(), path, query))
    return out


def _page_exists(path: str) -> bool:
    path = path.rstrip("/") or "/"
    if path == "/":
        return (APP / "page.tsx").is_file()
    return (APP / path.lstrip("/") / "page.tsx").is_file()


def _accepted_tabs(page: str) -> set[str]:
    src = TAB_READERS[page].read_text(encoding="utf-8")
    i = src.find("get('tab')")
    assert i >= 0, f"{TAB_READERS[page]} does not read ?tab= from the URL"
    window = src[i: i + 600]
    lst = re.search(r"\[([^\]]+)\]\.includes", window)
    assert lst, f"no accepted-tab list near get('tab') in {TAB_READERS[page]}"
    return set(re.findall(r"'([a-z_]+)'", lst.group(1)))


def test_links_were_found():
    links = _links()
    assert len(links) >= 10, links  # the bot really builds panel links; a broken regex would pass everything


def test_every_telegram_link_points_at_a_real_page():
    bad = [(f, p) for f, p, _ in _links() if not _page_exists(p)]
    assert not bad, f"Telegram links to pages that do not exist: {bad}"


def test_every_tab_in_a_telegram_link_is_read_by_that_page():
    bad = []
    for f, path, query in _links():
        tab = re.search(r"[?&]tab=([a-z_]+)", query)
        if not tab:
            continue
        page = path.rstrip("/")
        assert page in TAB_READERS, f"{f}: link with ?tab= to {page}, which has no registered tab reader"
        if tab.group(1) not in _accepted_tabs(page):
            bad.append((f, path, tab.group(1)))
    assert not bad, f"tabs the page does not accept: {bad}"


def test_webhook_stays_public_and_handler_imports():
    from app.core import auth
    from app.api.routes import notifications  # noqa: F401
    from app.services import notification_service  # noqa: F401

    assert "/api/notifications/telegram/webhook" in auth.PUBLIC
