"""«عاملِ مرورگر» ِ بازرس ویژه — API (behind the login wall like everything else). See services/browser_agent.py."""

from __future__ import annotations

import asyncio
import os
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ...services import browser_agent as BA

router = APIRouter(prefix="/inspector-agent", tags=["Inspector browser agent"])
_TASKS: set = set()  # keep references so runs are not garbage-collected mid-flight


def _enabled() -> bool:
    return os.environ.get("BROWSER_AGENT_ENABLED", "1") != "0"


class RunIn(BaseModel):
    task: str = Field(..., min_length=3, max_length=4000)
    start_url: str = Field(..., min_length=8, max_length=2000)
    allowed_hosts: List[str] = Field(default_factory=list)
    model_id: Optional[str] = None
    project_id: Optional[str] = None
    max_steps: int = BA.MAX_STEPS_DEFAULT


class Reply(BaseModel):
    approve: Optional[bool] = None
    text: Optional[str] = None


@router.get("/models")
async def models() -> List[Dict[str, Any]]:
    from ...services.assistant import available_models

    return [{**m, "vision": BA.model_supports_vision(m["id"])} for m in available_models()]


@router.post("/runs")
async def start(body: RunIn) -> Dict[str, Any]:
    if not _enabled():
        raise HTTPException(503, "عاملِ مرورگر خاموش است (BROWSER_AGENT_ENABLED=0)")
    if not re.match(r"^https?://", body.start_url):
        raise HTTPException(400, "نشانیِ شروع باید http/https باشد")
    if BA.is_busy():
        raise HTTPException(409, "یک اجرای دیگر در جریان است — یکی‌یکی (حافظهٔ سرور محدود است)")
    model_id = body.model_id
    if not model_id:
        from ...services.assistant import available_models

        ms = available_models()
        if not ms:
            raise HTTPException(503, "هیچ مدلِ فعالی نیست — در «مدل‌ها و تنظیمات» کلید بگذارید")
        model_id = ms[0]["id"]
    run = BA.new_run(body.task, body.start_url, body.allowed_hosts, model_id=model_id, project_id=body.project_id)
    model = await BA.default_model(model_id)
    t = asyncio.create_task(BA.run_agent(run, model, vision=BA.model_supports_vision(model_id), max_steps=body.max_steps))
    _TASKS.add(t)
    t.add_done_callback(_TASKS.discard)
    return {"run_id": run.id, "model_id": model_id, "allowed_hosts": run.allowed_hosts}


@router.get("/runs")
async def runs(limit: int = Query(30, ge=1, le=200)) -> List[Dict[str, Any]]:
    return BA.list_runs(limit)


@router.get("/runs/{run_id}")
async def get_run(run_id: str, after: int = Query(0, ge=0)) -> Dict[str, Any]:
    run = BA.RUNS.get(run_id)
    if run:
        return run.public(after)
    d = BA.load_run(run_id)
    if d is None:
        raise HTTPException(404, "اجرا یافت نشد")
    d["steps"] = [s for s in d.get("steps", []) if s.get("n", 0) > after]
    return d


@router.post("/runs/{run_id}/reply")
async def reply(run_id: str, body: Reply) -> Dict[str, Any]:
    value: Any = body.approve if body.approve is not None else (body.text or "")
    if not BA.reply(run_id, value):
        raise HTTPException(409, "این اجرا منتظرِ پاسخ نیست")
    return {"ok": True}


@router.post("/runs/{run_id}/cancel")
async def cancel(run_id: str) -> Dict[str, Any]:
    run = BA.RUNS.get(run_id)
    if not run:
        raise HTTPException(404, "اجرا یافت نشد")
    run.cancel = True
    BA.reply(run_id, None)  # a run waiting for approval stops too
    return {"ok": True}


@router.get("/runs/{run_id}/shots/{name}")
async def shot(run_id: str, name: str):
    if not re.match(r"^[a-f0-9]{8,32}$", run_id) or not re.match(r"^\d{1,3}\.jpg$", name):
        raise HTTPException(404, "یافت نشد")
    p = BA.SHOTS_ROOT / run_id / name
    if not p.is_file():
        raise HTTPException(404, "یافت نشد")
    return FileResponse(p, media_type="image/jpeg")
