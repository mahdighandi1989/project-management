"""
API routes برای چت ساده با AI
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import asyncio

from ...services.ai_manager import get_ai_manager
from ...services.ai_base import Message

router = APIRouter(prefix="/chat", tags=["Chat"])


# ===========================================
# Request/Response Models
# ===========================================

class ChatMessage(BaseModel):
    """یک پیام در چت"""
    role: str  # system, user, assistant
    content: str
    images: Optional[List[str]] = None


class ChatRequest(BaseModel):
    """درخواست چت"""
    model_id: str
    messages: List[ChatMessage]
    max_tokens: int = 4096
    temperature: float = 0.7
    stream: bool = False


class ChatResponse(BaseModel):
    """پاسخ چت"""
    model_id: str
    content: str
    tokens_used: int
    latency_ms: int
    finish_reason: str


class MultiChatRequest(BaseModel):
    """درخواست چت با چند مدل"""
    model_ids: List[str]
    messages: List[ChatMessage]
    max_tokens: int = 4096
    temperature: float = 0.7


# ===========================================
# Endpoints
# ===========================================

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """چت با یک مدل"""
    try:
        ai_manager = get_ai_manager()

        messages = [
            Message(role=m.role, content=m.content, images=m.images)
            for m in request.messages
        ]

        response = await ai_manager.generate(
            model_id=request.model_id,
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )

        return ChatResponse(
            model_id=response.model_id,
            content=response.content,
            tokens_used=response.tokens_used,
            latency_ms=response.latency_ms,
            finish_reason=response.finish_reason,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """چت با streaming"""
    try:
        ai_manager = get_ai_manager()

        messages = [
            Message(role=m.role, content=m.content, images=m.images)
            for m in request.messages
        ]

        # دریافت سرویس مستقیم
        from ...core.models_registry import get_model
        model = get_model(request.model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")

        service = ai_manager._services.get(model.provider)
        if not service:
            raise HTTPException(status_code=400, detail="Provider not available")

        async def generate():
            try:
                async for chunk in service.generate_stream(
                    request.model_id,
                    messages,
                    request.max_tokens,
                    request.temperature,
                ):
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/multi", response_model=List[ChatResponse])
async def chat_multi(request: MultiChatRequest):
    """چت با چند مدل به صورت موازی"""
    try:
        ai_manager = get_ai_manager()

        messages = [
            Message(role=m.role, content=m.content, images=m.images)
            for m in request.messages
        ]

        responses = await ai_manager.generate_parallel(
            model_ids=request.model_ids,
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )

        return [ChatResponse(
            model_id=r.model_id,
            content=r.content,
            tokens_used=r.tokens_used,
            latency_ms=r.latency_ms,
            finish_reason=r.finish_reason or ("error" if r.error else ""),
        ) for r in responses]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/with-fallback", response_model=ChatResponse)
async def chat_with_fallback(request: MultiChatRequest):
    """چت با fallback در صورت خطا"""
    try:
        ai_manager = get_ai_manager()

        messages = [
            Message(role=m.role, content=m.content, images=m.images)
            for m in request.messages
        ]

        response = await ai_manager.generate_with_fallback(
            model_ids=request.model_ids,
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )

        return ChatResponse(
            model_id=response.model_id,
            content=response.content,
            tokens_used=response.tokens_used,
            latency_ms=response.latency_ms,
            finish_reason=response.finish_reason,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
