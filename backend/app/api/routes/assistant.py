"""«دستیار» — the roaming assistant API (behind the login wall like everything else)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...services import assistant

router = APIRouter(prefix="/assistant", tags=["Assistant"])


class AskRequest(BaseModel):
    message: str
    history: List[Dict[str, Any]] = Field(default_factory=list)
    page: Dict[str, Any] = Field(default_factory=dict)
    site_map: List[Dict[str, Any]] = Field(default_factory=list)
    model_ids: Optional[List[str]] = None
    conversation_id: Optional[str] = None


@router.get("/models")
async def models():
    return assistant.available_models()


@router.post("/ask")
async def ask(req: AskRequest):
    try:
        return await assistant.ask(req.message, req.history, req.page, req.site_map, req.model_ids, req.conversation_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"پاسخِ مدل نیامد: {str(e)[:300]}")


@router.get("/conversations")
async def conversations():
    return assistant.list_conversations()


@router.get("/conversations/{cid}")
async def conversation(cid: str):
    c = assistant.get_conversation(cid)
    if c is None:
        raise HTTPException(404, "گفت‌وگو یافت نشد")
    return c


@router.delete("/conversations/{cid}")
async def archive_conversation(cid: str):
    if not assistant.delete_conversation(cid):
        raise HTTPException(404, "گفت‌وگو یافت نشد")
    return {"ok": True}
