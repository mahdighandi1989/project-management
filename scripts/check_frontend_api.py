#!/usr/bin/env python3
"""Does every API call in the frontend reach a real backend route?

    python3 scripts/check_frontend_api.py [frontend files or dirs …]   # default: all of frontend/src

Reads the backend's OpenAPI (imports ``app.main`` — no server needed) and every
``/api/...`` string literal / template in the given frontend files, then lists the
calls that match NO route (``${…}`` and ``{param}`` match any one segment, a template
ending in ``${…}`` may also match a query string). For ``fetch(`` calls the HTTP method
is read from a ``method: '…'`` within the next lines (default GET) and checked too —
that is how «PUT /api/config» (405) was found. Built for the
owner's plan item 6 (2026-11-15: «همه زیرقسمت‌ها … کار میکنه یا نه درست بررسی بشه»)
and reusable for any page. Exit 1 when something is unmatched.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FE = ROOT / "frontend" / "src"
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("AUTH_DISABLED", "1")
os.environ.setdefault("DATABASE_DIR", "/tmp/check-frontend-api-db")
os.makedirs(os.environ["DATABASE_DIR"], exist_ok=True)

CALL = re.compile(r"""[`'"](?:\$\{[A-Za-z_.()]+\})?(/api/[^`'"\s?#]*)""")


METHOD = re.compile(r"""method:\s*['"`]([A-Za-z]+)['"`]""")


class Route:
    def __init__(self, rx: re.Pattern, methods: set[str]):
        self.rx, self.methods, self.pattern = rx, methods, rx.pattern

    def match(self, s: str):
        return self.rx.match(s)


def backend_routes() -> list[Route]:
    import logging

    logging.disable(logging.CRITICAL)
    from app.main import app  # noqa: PLC0415

    pats = []
    for path, ops in app.openapi()["paths"].items():
        rx = re.sub(r"\\\{[^/]+?\\\}", "[^/]+", re.escape(path.rstrip("/")))
        pats.append(Route(re.compile("^" + rx + "/?$"), {m.upper() for m in ops}))
    return pats


def frontend_calls(targets: list[Path]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    files: list[Path] = []
    for t in targets:
        files += [t] if t.is_file() else [p for p in t.rglob("*.ts*")]
    for f in files:
        lines = f.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines, 1):
            for m in CALL.finditer(line):
                method = ""
                if "fetch(" in line:
                    window = "\n".join(lines[i - 1:i + 6])
                    # stop at the next call so a later fetch's method is not borrowed
                    nxt = window.find("fetch(", window.find("fetch(") + 6)
                    mm = METHOD.search(window if nxt < 0 else window[:nxt])
                    method = mm.group(1).upper() if mm else "GET"
                out.setdefault((m.group(1), method), []).append(f"{f.relative_to(ROOT)}:{i}")
    return out


def matches(call: str, pats: list[Route], method: str = "") -> bool:
    if method:
        pats = [p for p in pats if method in p.methods]
    c = re.sub(r"\$\{[^}]*\}", "X", call).rstrip("/")
    if any(p.match(c) for p in pats):
        return True
    # `${base}/api/x/${id}${suffix}` — the last placeholder may be a query string or empty
    if call.endswith("}"):
        trimmed = re.sub(r"/?\$\{[^}]*\}$", "", call)
        trimmed = re.sub(r"\$\{[^}]*\}", "X", trimmed).rstrip("/")
        return any(p.match(trimmed) for p in pats) or any(p.pattern.startswith("^" + re.escape(trimmed)) for p in pats)
    return False


#: verified by hand (2026-11-15) — comments, `${…}` expressions the regex cannot resolve, a WebSocket; not calls
KNOWN_FALSE = {"/api/...", "/api/auth/", "/api/handbook/*", "/api/inspector-agent",
               "/api/oversight/repos${forceRefresh", "/api/oversight/runtime/backfill-ac-classification${force",
               "/api/oversight/watched/${w.id}/claude-runner/${path}", "/api/render/ws/bridge/${projectId}",
               "/api/render/inspector/proxy/"}  # (PM-INS-0030) the proxy PREFIX in frontend/src/middleware.ts, not a call


def main(argv: list[str]) -> int:
    targets = [Path(a).resolve() for a in argv] or [FE]
    pats = backend_routes()
    calls = frontend_calls(targets)
    bad = {k: w for k, w in calls.items() if k[0] not in KNOWN_FALSE and not matches(k[0], pats, k[1])}
    print(f"{len(calls)} distinct API calls, {len(pats)} backend routes, {len(bad)} unmatched")
    for (c, method), where in sorted(bad.items()):
        exists = matches(c, pats)
        why = f"{method or '?'} not allowed (path exists)" if exists and method else (method or "?")
        print(f"  ✗ {why:32} {c}   ← {', '.join(where[:3])}{' …' if len(where) > 3 else ''}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
