"""🚨 The startup-import gap that the third audit caught.

Backstory:
- `cloud_code_service.py` self-registers in `oauth_model_registry` at
  module-import time (call to `register_oauth_dispatcher("cloud_code", ...)`
  in the bottom of the file).
- BUT nothing in app/main.py was importing `cloud_code_service` eagerly.
  Some request paths (inspector chat, capability test, models page)
  trigger the import as a side effect, but a freshly-started worker
  that hasn't yet handled such a request leaves the registry EMPTY.
- Result: when the user picks cloud_code in the "مدل‌های نظارت" picker
  on a watched project, `_ai_generate(model_id="cloud_code")` consults
  the empty registry, falls through to ai_manager, doesn't find
  cloud_code in `_services`, and silently selects the FIRST available
  ai_manager model (e.g. DeepSeek). User thinks monitoring is using
  Cloud Code but it isn't.

The audit verified this empirically:
    $ python -c "from app import main; from app.services.oauth_model_registry import is_oauth_model; print(is_oauth_model('cloud_code'))"
    False

This is exactly the kind of silent breakage that ruins parity claims.

Two-layer fix:
1. `app/main.py` eagerly imports `cloud_code_service` at startup so the
   registration runs during app boot, before any request is served.
2. `oauth_model_registry.get_oauth_dispatcher` (and the other accessors)
   now run a lazy bootstrap on first call. The bootstrap imports a
   known list of dispatcher modules. Even if main.py's import is
   removed by mistake, the first registry lookup will trigger imports
   that re-populate the registry.

These tests pin both layers so the regression can't return.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# Layer 1: main.py eagerly imports cloud_code_service
# ---------------------------------------------------------------------------


def test_main_py_eagerly_imports_cloud_code_service():
    """🚨 The eager import line must remain in app/main.py. If a future
    refactor removes it, the OAuth dispatcher won't register at startup
    and monitoring with cloud_code will silently route to DeepSeek."""
    src = (
        Path(__file__).resolve().parents[1] / "app/main.py"
    ).read_text(encoding="utf-8")
    # Allow either form: `from .services import cloud_code_service` or
    # `from app.services import cloud_code_service`.
    assert (
        "from .services import cloud_code_service" in src
        or "from app.services import cloud_code_service" in src
    ), (
        "app/main.py must eagerly import cloud_code_service to force its "
        "self-registration with oauth_model_registry. Without this, fresh "
        "worker processes leave the registry empty and monitoring with "
        "cloud_code silently falls back to DeepSeek."
    )


# ---------------------------------------------------------------------------
# Layer 2: registry lazy-bootstrap
# ---------------------------------------------------------------------------


def test_registry_has_lazy_bootstrap_mechanism():
    """The registry must have a defense-in-depth lazy bootstrap that
    imports known dispatcher modules on first access — so even if
    main.py's eager import is somehow bypassed, the first call to
    `get_oauth_dispatcher`/`is_oauth_model` triggers registration."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/services/oauth_model_registry.py"
    ).read_text(encoding="utf-8")
    assert "_bootstrap_known_dispatchers" in src
    assert "_KNOWN_DISPATCHER_MODULES" in src
    assert "cloud_code_service" in src, (
        "the bootstrap list must include cloud_code_service so it gets "
        "auto-imported on first registry access"
    )


def test_bootstrap_only_runs_once(monkeypatch):
    """The bootstrap must be idempotent — calling get_oauth_dispatcher
    repeatedly should not re-import each time (perf)."""
    from app.services import oauth_model_registry as omr

    # First call triggers bootstrap
    omr._BOOTSTRAP_DONE = False
    omr.get_oauth_dispatcher("anything")
    assert omr._BOOTSTRAP_DONE is True

    # Second call must short-circuit
    call_count = [0]

    original_import = __import__

    def _spy_import(name, *args, **kwargs):
        if "cloud_code_service" in name:
            call_count[0] += 1
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _spy_import)
    omr.get_oauth_dispatcher("cloud_code")
    omr.get_oauth_dispatcher("cloud_code")
    omr.get_oauth_dispatcher("cloud_code")
    # bootstrap already done → no further imports
    assert call_count[0] == 0


# ---------------------------------------------------------------------------
# Defense check: even with a "cold" process, the registry should work
# ---------------------------------------------------------------------------


def test_cold_registry_subprocess_picks_up_cloud_code():
    """Simulate production cold-start by spawning a fresh Python
    subprocess that imports nothing except oauth_model_registry and
    immediately queries it. The lazy bootstrap must populate cloud_code.

    This is the gold-standard test for the audit finding — a clean
    Python process verifies the registry's defense-in-depth without
    relying on any prior import side-effects in the test runner."""
    import subprocess
    import sys as _sys

    script = (
        "from app.services.oauth_model_registry import is_oauth_model;"
        "import sys;"
        "ok = is_oauth_model('cloud_code');"
        "sys.exit(0 if ok else 1)"
    )
    proc = subprocess.run(
        [_sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parents[1]),
        timeout=30,
    )
    assert proc.returncode == 0, (
        f"cold subprocess could not find cloud_code in registry. "
        f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )
