"""InspectorAgentService — high-level façade over the inspector chat engines.

The legacy inspector chat flow is spread across `inspector_agent.py` (the
local-AI agent runner with tool calling) and `render_logs.py` (the SSE
endpoints). When we added the Cloud Code (Claude OAuth) engine, the user's
task spec asked for a `chat_with_cloud_code` method on an
`InspectorAgentService` class so callers have a single canonical entry
point per engine. This module provides that class as a thin façade — it
delegates to the underlying `cloud_code_service` (and, in the future,
to the local agent runner) so endpoints and tests can pick the engine
by name without knowing which module to import.

Usage:

    svc = InspectorAgentService()
    async for chunk in svc.chat_with_cloud_code(messages, system_prompt=...):
        ...
"""

from __future__ import annotations

from typing import AsyncIterator, Dict, List, Optional

from .cloud_code_service import (
    CLOUD_CODE_DEFAULT_MODEL,
    cloud_code_complete,
    cloud_code_is_configured,
    cloud_code_stream_chat,
)


class InspectorAgentService:
    """Single entry point for inspector chat engines.

    Today exposes `chat_with_cloud_code` for the Cloud Code engine. The
    local-AI path stays in `render_logs.smart_chat` because of the
    intent-detection / selective-scan orchestration that lives inline.
    """

    @staticmethod
    def cloud_code_available() -> bool:
        return cloud_code_is_configured()

    @staticmethod
    async def chat_with_cloud_code(
        messages: List[Dict[str, str]],
        *,
        system_prompt: Optional[str] = None,
        model: str = CLOUD_CODE_DEFAULT_MODEL,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        timeout: float = 180.0,
        stream: bool = True,
    ):
        """Run an inspector chat turn through the Cloud Code (Claude OAuth)
        engine.

        - `messages` is a chronological list of `{role, content}` dicts. Roles
          other than user/assistant are dropped (system is hoisted into the
          `system_prompt` argument).
        - When `stream=True` (default), returns an async generator yielding
          plain text fragments suitable for forwarding to an SSE response.
        - When `stream=False`, awaits the full response and returns the
          assembled string.

        Raises `RuntimeError` if `CLAUDE_CODE_OAUTH_TOKEN` is not configured —
        callers should check `cloud_code_available()` first to surface a
        helpful UI message.
        """
        if stream:
            return cloud_code_stream_chat(
                messages,
                system_prompt=system_prompt,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
            )
        return await cloud_code_complete(
            messages,
            system_prompt=system_prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
        )


# Module-level singleton for callers that prefer an instance handle.
inspector_agent_service = InspectorAgentService()
