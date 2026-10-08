#!/usr/bin/env python3
"""A real Chromium for the supervisor — opening production pages through the
Claude environment's egress proxy, trusting exactly that proxy's CA.

Shared by `screenshot.py` (the «after» picture) and `surface_scan.py` (the map of
every page). Ported from Detective-1 (`scripts/supervisor/screenshot.py`).
Never run `playwright install` here — the browsers are in /opt/pw-browsers.
"""
from __future__ import annotations

import base64
import hashlib
import os
import subprocess
from pathlib import Path

PROXY_CA = Path("/root/.ccr/agent-proxy-ca.crt")


def trust_args() -> list[str]:
    """Chromium does not read the system CA bundle the way curl/python do, so it
    is told to trust ONE extra key: the environment proxy's CA, pinned by its
    public-key hash. Verification stays on for everything else."""
    if not PROXY_CA.exists():
        return []
    try:
        der = subprocess.run(
            "openssl x509 -in %s -pubkey -noout | openssl pkey -pubin -outform der" % PROXY_CA,
            shell=True, check=True, capture_output=True).stdout
        spki = base64.b64encode(hashlib.sha256(der).digest()).decode()
        return [f"--ignore-certificate-errors-spki-list={spki}"]
    except Exception:  # noqa: BLE001 - without it the page simply fails to open, loudly
        return []


def launch(p):
    proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
    opts: dict = {"args": trust_args()}
    if proxy:
        opts["proxy"] = {"server": proxy, "bypass": "localhost,127.0.0.1"}
    exe = Path("/opt/pw-browsers/chromium")
    try:
        return p.chromium.launch(**opts)
    except Exception:  # noqa: BLE001 - a pinned playwright that wants another build
        if exe.exists():
            return p.chromium.launch(executable_path=str(exe), **opts)
        raise


def open_page(browser, url: str, *, width: int = 1366, height: int = 900, wait_ms: int = 2500):
    """Open ``url`` with the inspection overlays switched OFF (so the picture shows
    the page, not our highlights) and dark mode off. Returns (page, errors)."""
    ctx = browser.new_context(viewport={"width": width, "height": height}, locale="fa-IR")
    ctx.add_init_script(
        "try{localStorage.setItem('pm.inspection.highlights','0');"
        "localStorage.setItem('pm.inspection.active','0');"
        "localStorage.setItem('darkMode','false');}catch(e){}")
    page = ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)[:300]))
    page.goto(url, wait_until="networkidle", timeout=180_000)
    page.wait_for_timeout(wait_ms)
    return page, errors
