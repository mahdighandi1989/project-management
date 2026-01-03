"""
API routes برای سیستم مناظره
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

from ...services.debate_service import (
    get_debate_service,
    DebateSession,
    DebateStatus,
    RoundResponse,
    ScoreResult,
    JudgeResult
)
from ...core.roles import WorkMode

router = APIRouter(prefix="/debate", tags=["Debate"])


# ===========================================
# Request/Response Models
# ===========================================

class CreateDebateRequest(BaseModel):
    """درخواست ایجاد مناظره"""
    prompt: str
    mode: str = "auto"
    models: Optional[List[str]] = None
    attachments: Optional[List[Dict[str, Any]]] = None


class DebateResponse(BaseModel):
    """پاسخ مناظره"""
    id: str
    prompt: str
    mode: str
    status: str
    models: List[str]
    role_assignments: Dict[str, str]
    rounds_count: int
    scores_count: int
    has_judge: bool
    has_summary: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_session(cls, session: DebateSession) -> "DebateResponse":
        return cls(
            id=session.id,
            prompt=session.prompt[:200] + "..." if len(session.prompt) > 200 else session.prompt,
            mode=session.mode.value if isinstance(session.mode, WorkMode) else session.mode,
            status=session.status.value if isinstance(session.status, DebateStatus) else session.status,
            models=session.models,
            role_assignments={k: v.value if hasattr(v, 'value') else v for k, v in session.role_assignments.items()},
            rounds_count=len(session.rounds),
            scores_count=len(session.scores),
            has_judge=session.judge_result is not None,
            has_summary=bool(session.summary),
            created_at=session.created_at,
            updated_at=session.updated_at,
        )


class DebateDetailResponse(BaseModel):
    """جزئیات کامل مناظره"""
    id: str
    prompt: str
    mode: str
    status: str
    models: List[str]
    role_assignments: Dict[str, str]
    rounds: List[List[Dict]]
    scores: List[Dict]
    judge_result: Optional[Dict]
    summary: str
    created_at: datetime
    updated_at: datetime


class RunRoundRequest(BaseModel):
    """درخواست اجرای یک دور"""
    round_number: int = 1
    context: Optional[str] = None


# ===========================================
# Endpoints
# ===========================================

@router.post("/create", response_model=DebateResponse)
async def create_debate(request: CreateDebateRequest):
    """ایجاد یک مناظره جدید"""
    try:
        service = get_debate_service()

        # تبدیل mode به enum
        try:
            mode = WorkMode(request.mode.lower())
        except ValueError:
            mode = WorkMode.AUTO

        session = await service.create_session(
            prompt=request.prompt,
            mode=mode,
            models=request.models,
            attachments=request.attachments,
        )

        return DebateResponse.from_session(session)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{debate_id}/run-round", response_model=List[Dict])
async def run_round(debate_id: str, request: RunRoundRequest):
    """اجرای یک دور از مناظره"""
    try:
        service = get_debate_service()
        session = service.get_session(debate_id)

        if not session:
            raise HTTPException(status_code=404, detail="Debate not found")

        responses = await service.run_round(
            session,
            round_number=request.round_number,
            context=request.context
        )

        return [r.model_dump() for r in responses]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{debate_id}/run-full")
async def run_full_debate(debate_id: str, background_tasks: BackgroundTasks):
    """اجرای کامل مناظره در پس‌زمینه"""
    try:
        service = get_debate_service()
        session = service.get_session(debate_id)

        if not session:
            raise HTTPException(status_code=404, detail="Debate not found")

        # اجرا در پس‌زمینه
        background_tasks.add_task(service.run_full_debate, session)

        return {"message": "Debate started", "debate_id": debate_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{debate_id}/score")
async def run_scoring(debate_id: str):
    """امتیازدهی"""
    try:
        service = get_debate_service()
        session = service.get_session(debate_id)

        if not session:
            raise HTTPException(status_code=404, detail="Debate not found")

        scores = await service.run_scoring(session)
        return [s.model_dump() for s in scores]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{debate_id}/judge")
async def run_judging(debate_id: str):
    """داوری"""
    try:
        service = get_debate_service()
        session = service.get_session(debate_id)

        if not session:
            raise HTTPException(status_code=404, detail="Debate not found")

        result = await service.run_judging(session)
        return result.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{debate_id}/summary")
async def run_summary(debate_id: str):
    """خلاصه‌نویسی"""
    try:
        service = get_debate_service()
        session = service.get_session(debate_id)

        if not session:
            raise HTTPException(status_code=404, detail="Debate not found")

        summary = await service.run_summary(session)
        return {"summary": summary}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{debate_id}", response_model=DebateDetailResponse)
async def get_debate(debate_id: str):
    """دریافت جزئیات مناظره"""
    try:
        service = get_debate_service()
        session = service.get_session(debate_id)

        if not session:
            raise HTTPException(status_code=404, detail="Debate not found")

        return DebateDetailResponse(
            id=session.id,
            prompt=session.prompt,
            mode=session.mode.value if isinstance(session.mode, WorkMode) else session.mode,
            status=session.status.value if isinstance(session.status, DebateStatus) else session.status,
            models=session.models,
            role_assignments={k: v.value if hasattr(v, 'value') else v for k, v in session.role_assignments.items()},
            rounds=[[r.model_dump() for r in round_resp] for round_resp in session.rounds],
            scores=[s.model_dump() for s in session.scores],
            judge_result=session.judge_result.model_dump() if session.judge_result else None,
            summary=session.summary,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[DebateResponse])
async def list_debates():
    """لیست همه مناظرات"""
    try:
        service = get_debate_service()
        sessions = service.list_sessions()
        return [DebateResponse.from_session(s) for s in sessions]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
