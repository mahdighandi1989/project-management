"""Registry of non-API-key model dispatchers.

Most AI providers in this codebase route through `ai_manager.generate(model_id=...)`,
which dispatches based on the model's provider field and uses an API key
from env. That's the right pattern for metered providers (OpenAI, Anthropic,
Gemini, DeepSeek, OpenRouter, Groq, Perplexity).

Some providers don't fit that mold:
  - `cloud_code` uses an OAuth subscription token (CLAUDE_CODE_OAUTH_TOKEN).
    Calls go through `cloud_code_complete`, not Anthropic's standard API.
  - Hypothetical future additions: a Gemini OAuth flow, a Cohere subscription,
    etc.

For these, `ai_manager` is the wrong dispatch path — it doesn't know they exist.
We register their dispatcher functions here. `OversightService._ai_generate`
and `_ai_generate_multi` consult this registry before falling through to
`ai_manager`, so any consumer that calls `_ai_generate(model_id=...)` works
transparently with both API-key and OAuth models.

═════════════════════════════════════════════════════════════════════════════
EXTENSIBILITY: adding a new non-API-key model
═════════════════════════════════════════════════════════════════════════════

Suppose a Gemini OAuth flow lands. To wire it into the existing
selected_models picker on the oversight page (no other code changes):

  1. Define a dispatcher in a service module:

        async def _dispatch_gemini_oauth(
            prompt: str, *, max_tokens: int, temperature: float,
        ) -> str:
            from .gemini_oauth_service import gemini_oauth_complete
            if not gemini_oauth_is_configured():
                raise RuntimeError("GEMINI_OAUTH_TOKEN env var is not set")
            return await gemini_oauth_complete(
                prompt, max_tokens=max_tokens, temperature=temperature,
            )

  2. Register it here:

        from .gemini_oauth_service import _dispatch_gemini_oauth
        register_oauth_dispatcher("gemini_oauth", _dispatch_gemini_oauth)

  3. Add the entry to `core/models_registry.py:MODEL_REGISTRY` so the
     models page surfaces it.

  4. Done — every site that calls `_ai_generate(model_id="gemini_oauth")`
     now routes through the dispatcher. Auto-runner, single-task button,
     inspector chat, deep_scan, verify, consensus mode — all transparent.
"""

from __future__ import annotations

import logging
from typing import Awaitable, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# Type alias for a dispatcher: takes prompt + kwargs, returns response text.
OAuthDispatcher = Callable[..., Awaitable[str]]

_REGISTRY: Dict[str, OAuthDispatcher] = {}
_BOOTSTRAP_DONE: bool = False
_KNOWN_DISPATCHER_MODULES: tuple = (
    "app.services.cloud_code_service",
    # add future OAuth model modules here; they'll be eagerly imported
    # on first registry access so their `register_oauth_dispatcher` runs
)


def _bootstrap_known_dispatchers() -> None:
    """🚨 (audit fix) — Belt-and-suspenders eager import.

    `cloud_code_service` (and future OAuth model modules) self-register
    via `register_oauth_dispatcher` at import time. Normally the eager
    import in `app/main.py` ensures this happens at startup. But if that
    line is ever removed or a different entry-point bypasses main.py,
    consumers of this registry would silently see "no dispatcher" and
    fall back to the wrong model.

    This bootstrap runs ONCE on first registry access and imports each
    known module. Import errors are swallowed (the dispatcher just won't
    register, which the existing tests/consumers handle gracefully).
    """
    global _BOOTSTRAP_DONE
    if _BOOTSTRAP_DONE:
        return
    _BOOTSTRAP_DONE = True
    for mod_path in _KNOWN_DISPATCHER_MODULES:
        try:
            __import__(mod_path)
        except Exception as e:
            logger.debug(
                "oauth_model_registry: lazy-bootstrap of %s failed: %s",
                mod_path, e,
            )


def register_oauth_dispatcher(model_id: str, dispatcher: OAuthDispatcher) -> None:
    """Register a non-API-key model.

    Call this once at module import time (e.g., near the dispatcher's
    function definition).
    """
    if model_id in _REGISTRY:
        logger.debug(
            "register_oauth_dispatcher: %s already registered, overwriting",
            model_id,
        )
    _REGISTRY[model_id] = dispatcher


def get_oauth_dispatcher(model_id: str) -> Optional[OAuthDispatcher]:
    """Return the dispatcher for this model_id, or None if it's a regular
    API-key model (caller should fall through to ai_manager)."""
    _bootstrap_known_dispatchers()
    return _REGISTRY.get(model_id)


def is_oauth_model(model_id: str) -> bool:
    """Quick predicate: is this model_id served by an OAuth dispatcher?"""
    _bootstrap_known_dispatchers()
    return model_id in _REGISTRY


def list_registered_oauth_models() -> list:
    """For diagnostics — returns a list of registered OAuth model ids."""
    _bootstrap_known_dispatchers()
    return sorted(_REGISTRY.keys())
