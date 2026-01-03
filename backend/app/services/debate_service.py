"""
سیستم مناظره و همکاری هوش مصنوعی
قلب اصلی سیستم - مدیریت مناظره، امتیازدهی و داوری
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from datetime import datetime
from enum import Enum
import asyncio
import uuid

from .ai_manager import get_ai_manager, AIManager
from .ai_base import Message, AIResponse
from ..core.roles import (
    RoleType, AIRole, WorkMode, WorkModeConfig,
    ROLES_REGISTRY, WORK_MODES, get_role, get_mode_config
)
from ..core.models_registry import AIModel, get_model


class DebateStatus(str, Enum):
    """وضعیت مناظره"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    SCORING = "scoring"
    JUDGING = "judging"
    SUMMARIZING = "summarizing"
    COMPLETED = "completed"
    FAILED = "failed"


class RoundResponse(BaseModel):
    """پاسخ یک مدل در یک دور"""
    round_number: int
    model_id: str
    model_name: str
    role: RoleType
    role_name: str
    role_icon: str
    content: str
    tokens_used: int = 0
    latency_ms: int = 0
    timestamp: datetime = datetime.now()
    error: Optional[str] = None


class ScoreResult(BaseModel):
    """نتیجه امتیازدهی"""
    scorer_model: str
    target_model: str
    accuracy: int = 0
    completeness: int = 0
    clarity: int = 0
    creativity: int = 0
    relevance: int = 0
    total: int = 0
    feedback: str = ""


class JudgeResult(BaseModel):
    """نتیجه داوری"""
    judge_model: str
    winner: str
    reasoning: str
    detailed_analysis: str = ""
    scores: Dict[str, int] = {}


class DebateSession(BaseModel):
    """یک جلسه مناظره"""
    id: str
    prompt: str
    mode: WorkMode
    status: DebateStatus = DebateStatus.PENDING
    models: List[str] = []
    role_assignments: Dict[str, RoleType] = {}
    rounds: List[List[RoundResponse]] = []
    scores: List[ScoreResult] = []
    judge_result: Optional[JudgeResult] = None
    summary: str = ""
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    metadata: Dict[str, Any] = {}

    class Config:
        use_enum_values = True


class DebateService:
    """سرویس اصلی مناظره"""

    def __init__(self, ai_manager: Optional[AIManager] = None):
        self.ai_manager = ai_manager or get_ai_manager()
        self._sessions: Dict[str, DebateSession] = {}

    async def create_session(
        self,
        prompt: str,
        mode: WorkMode = WorkMode.AUTO,
        models: Optional[List[str]] = None,
        attachments: Optional[List[Dict]] = None,
    ) -> DebateSession:
        """ایجاد یک جلسه مناظره جدید"""
        session_id = f"debate_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # انتخاب مدل‌ها
        if not models:
            mode_config = get_mode_config(mode)
            max_models = len(mode_config.default_roles) if mode_config else 3
            selected = self.ai_manager.smart_select_models(prompt, max_models=max_models)
            models = [m.id for m in selected]

        if not models:
            raise ValueError("No models available")

        # تخصیص نقش‌ها
        mode_config = get_mode_config(mode)
        role_assignments = {}
        default_roles = mode_config.default_roles if mode_config else [RoleType.RESPONDER]

        for i, model_id in enumerate(models):
            role = default_roles[i % len(default_roles)]
            role_assignments[model_id] = role

        session = DebateSession(
            id=session_id,
            prompt=prompt,
            mode=mode,
            models=models,
            role_assignments=role_assignments,
            metadata={
                "attachments_count": len(attachments) if attachments else 0,
            }
        )

        self._sessions[session_id] = session
        return session

    async def run_round(
        self,
        session: DebateSession,
        round_number: int,
        context: Optional[str] = None,
    ) -> List[RoundResponse]:
        """اجرای یک دور از مناظره"""
        session.status = DebateStatus.RUNNING
        session.updated_at = datetime.now()

        responses = []

        for model_id in session.models:
            role_type = session.role_assignments.get(model_id, RoleType.RESPONDER)
            role = get_role(role_type)

            # ساخت پیام‌ها
            messages = self._build_round_messages(
                session, round_number, model_id, role, context
            )

            try:
                response = await self.ai_manager.generate(
                    model_id,
                    messages,
                    max_tokens=4000,
                    temperature=0.7
                )

                round_response = RoundResponse(
                    round_number=round_number,
                    model_id=model_id,
                    model_name=get_model(model_id).name if get_model(model_id) else model_id,
                    role=role_type,
                    role_name=role.name_fa if role else "پاسخ‌دهنده",
                    role_icon=role.icon if role else "💬",
                    content=response.content,
                    tokens_used=response.tokens_used,
                    latency_ms=response.latency_ms,
                )

            except Exception as e:
                round_response = RoundResponse(
                    round_number=round_number,
                    model_id=model_id,
                    model_name=get_model(model_id).name if get_model(model_id) else model_id,
                    role=role_type,
                    role_name=role.name_fa if role else "پاسخ‌دهنده",
                    role_icon=role.icon if role else "💬",
                    content="",
                    error=str(e)
                )

            responses.append(round_response)

        session.rounds.append(responses)
        session.updated_at = datetime.now()

        return responses

    def _build_round_messages(
        self,
        session: DebateSession,
        round_number: int,
        model_id: str,
        role: Optional[AIRole],
        context: Optional[str] = None,
    ) -> List[Message]:
        """ساخت پیام‌ها برای یک دور"""
        messages = []

        # System prompt از نقش
        if role:
            messages.append(Message(role="system", content=role.system_prompt))

        # Context از دورهای قبلی
        if round_number > 1 and session.rounds:
            prev_context = self._build_previous_rounds_context(session, model_id)
            if prev_context:
                messages.append(Message(
                    role="user",
                    content=f"پاسخ‌های قبلی:\n{prev_context}"
                ))

        # Context اضافی
        if context:
            messages.append(Message(role="user", content=f"زمینه اضافی:\n{context}"))

        # پرامپت اصلی
        mode_config = get_mode_config(session.mode)
        round_instruction = ""

        if round_number == 1:
            round_instruction = "این دور اول است. لطفاً پاسخ اولیه خود را ارائه دهید."
        elif round_number == 2 and mode_config and mode_config.rounds >= 2:
            round_instruction = "این دور دوم است. با توجه به پاسخ‌های قبلی، نظر خود را تکمیل یا اصلاح کنید."
        else:
            round_instruction = f"این دور {round_number} است. ادامه دهید."

        messages.append(Message(
            role="user",
            content=f"""
{round_instruction}

پرامپت اصلی:
{session.prompt}

لطفاً پاسخ کامل و دقیق بدهید.
"""
        ))

        return messages

    def _build_previous_rounds_context(self, session: DebateSession, current_model: str) -> str:
        """ساخت context از دورهای قبلی"""
        context_parts = []

        for round_responses in session.rounds:
            for resp in round_responses:
                if resp.model_id != current_model and resp.content:
                    context_parts.append(
                        f"**{resp.role_icon} {resp.model_name} ({resp.role_name}):**\n{resp.content[:2000]}..."
                        if len(resp.content) > 2000 else
                        f"**{resp.role_icon} {resp.model_name} ({resp.role_name}):**\n{resp.content}"
                    )

        return "\n\n---\n\n".join(context_parts)

    async def run_scoring(self, session: DebateSession) -> List[ScoreResult]:
        """امتیازدهی متقابل"""
        session.status = DebateStatus.SCORING
        session.updated_at = datetime.now()

        scores = []

        # هر مدل به بقیه امتیاز می‌دهد
        for scorer_model in session.models:
            for target_model in session.models:
                if scorer_model == target_model:
                    continue

                # پاسخ‌های هدف
                target_responses = self._get_model_responses(session, target_model)
                if not target_responses:
                    continue

                score = await self._score_responses(
                    scorer_model, target_model, target_responses, session.prompt
                )
                scores.append(score)

        session.scores = scores
        session.updated_at = datetime.now()

        return scores

    async def _score_responses(
        self,
        scorer_model: str,
        target_model: str,
        responses: List[RoundResponse],
        original_prompt: str
    ) -> ScoreResult:
        """امتیازدهی یک مدل به پاسخ‌های مدل دیگر"""
        responses_text = "\n\n".join([
            f"دور {r.round_number}: {r.content}" for r in responses if r.content
        ])

        scoring_prompt = f"""
لطفاً پاسخ‌های زیر را بر اساس معیارهای زیر از 0 تا 100 امتیاز دهید:

**پرامپت اصلی:** {original_prompt[:500]}

**پاسخ‌ها:**
{responses_text[:3000]}

**معیارها:**
1. دقت (Accuracy): صحت اطلاعات
2. کامل بودن (Completeness): پوشش همه جنبه‌ها
3. وضوح (Clarity): شفافیت و خوانایی
4. خلاقیت (Creativity): نوآوری در پاسخ
5. مرتبط بودن (Relevance): ارتباط با سوال

پاسخ را دقیقاً در این فرمت JSON بدهید:
{{"accuracy": عدد, "completeness": عدد, "clarity": عدد, "creativity": عدد, "relevance": عدد, "feedback": "بازخورد کوتاه"}}
"""

        try:
            response = await self.ai_manager.generate(
                scorer_model,
                [Message(role="user", content=scoring_prompt)],
                max_tokens=500,
                temperature=0.3
            )

            # پارس JSON
            import json
            import re

            json_match = re.search(r'\{[^}]+\}', response.content)
            if json_match:
                data = json.loads(json_match.group())
                return ScoreResult(
                    scorer_model=scorer_model,
                    target_model=target_model,
                    accuracy=data.get("accuracy", 50),
                    completeness=data.get("completeness", 50),
                    clarity=data.get("clarity", 50),
                    creativity=data.get("creativity", 50),
                    relevance=data.get("relevance", 50),
                    total=sum([
                        data.get("accuracy", 50),
                        data.get("completeness", 50),
                        data.get("clarity", 50),
                        data.get("creativity", 50),
                        data.get("relevance", 50)
                    ]) // 5,
                    feedback=data.get("feedback", "")
                )

        except Exception as e:
            pass

        return ScoreResult(
            scorer_model=scorer_model,
            target_model=target_model,
            total=50,
            feedback="خطا در امتیازدهی"
        )

    async def run_judging(self, session: DebateSession) -> JudgeResult:
        """داوری نهایی"""
        session.status = DebateStatus.JUDGING
        session.updated_at = datetime.now()

        # انتخاب داور (مدلی که در مناظره نبوده یا اولین مدل موجود)
        available_models = self.ai_manager.get_available_models()
        judge_model = None

        for model in available_models:
            if model.id not in session.models:
                judge_model = model.id
                break

        if not judge_model:
            judge_model = session.models[0]

        # ساخت خلاصه پاسخ‌ها
        all_responses = self._build_all_responses_summary(session)
        scores_summary = self._build_scores_summary(session)

        judging_prompt = f"""
به عنوان داور بی‌طرف، مناظره زیر را ارزیابی کنید:

**سوال اصلی:** {session.prompt[:500]}

**پاسخ‌های شرکت‌کنندگان:**
{all_responses}

**امتیازات داده شده:**
{scores_summary}

لطفاً:
1. برنده را مشخص کنید
2. دلیل انتخاب خود را توضیح دهید
3. تحلیل جامعی ارائه دهید

پاسخ را در این فرمت بدهید:
برنده: [نام مدل]
دلیل: [توضیح کوتاه]
تحلیل: [تحلیل جامع]
"""

        try:
            response = await self.ai_manager.generate(
                judge_model,
                [Message(role="user", content=judging_prompt)],
                max_tokens=1500,
                temperature=0.5
            )

            # پارس نتیجه
            content = response.content
            winner = session.models[0]  # پیش‌فرض
            reasoning = ""
            analysis = ""

            lines = content.split('\n')
            for line in lines:
                if 'برنده:' in line or 'Winner:' in line.lower():
                    # یافتن نام مدل
                    for model_id in session.models:
                        if model_id in line or get_model(model_id).name in line:
                            winner = model_id
                            break
                elif 'دلیل:' in line or 'Reason:' in line.lower():
                    reasoning = line.split(':', 1)[-1].strip()
                elif 'تحلیل:' in line or 'Analysis:' in line.lower():
                    analysis = line.split(':', 1)[-1].strip()

            if not reasoning:
                reasoning = content[:500]

            result = JudgeResult(
                judge_model=judge_model,
                winner=winner,
                reasoning=reasoning,
                detailed_analysis=analysis or content
            )

        except Exception as e:
            result = JudgeResult(
                judge_model=judge_model,
                winner=session.models[0],
                reasoning=f"خطا در داوری: {str(e)}"
            )

        session.judge_result = result
        session.updated_at = datetime.now()

        return result

    async def run_summary(self, session: DebateSession) -> str:
        """خلاصه‌نویسی نهایی"""
        session.status = DebateStatus.SUMMARIZING
        session.updated_at = datetime.now()

        # انتخاب مدل خلاصه‌نویس
        summary_model = session.models[0]

        all_responses = self._build_all_responses_summary(session)

        summary_prompt = f"""
لطفاً خلاصه‌ای جامع از مناظره زیر ارائه دهید:

**سوال:** {session.prompt[:500]}

**پاسخ‌ها:**
{all_responses}

**برنده:** {session.judge_result.winner if session.judge_result else 'نامشخص'}

خلاصه باید شامل:
- نکات کلیدی هر طرف
- نقاط قوت و ضعف
- نتیجه‌گیری نهایی
"""

        try:
            response = await self.ai_manager.generate(
                summary_model,
                [Message(role="user", content=summary_prompt)],
                max_tokens=2000,
                temperature=0.5
            )
            session.summary = response.content

        except Exception as e:
            session.summary = f"خطا در خلاصه‌نویسی: {str(e)}"

        session.status = DebateStatus.COMPLETED
        session.updated_at = datetime.now()

        return session.summary

    async def run_full_debate(self, session: DebateSession) -> DebateSession:
        """اجرای کامل یک مناظره"""
        mode_config = get_mode_config(session.mode)

        # اجرای دورها
        for round_num in range(1, (mode_config.rounds if mode_config else 1) + 1):
            await self.run_round(session, round_num)

        # امتیازدهی
        if mode_config and mode_config.scoring:
            await self.run_scoring(session)

        # داوری
        if mode_config and mode_config.judge:
            await self.run_judging(session)

        # خلاصه
        if mode_config and mode_config.summary:
            await self.run_summary(session)

        return session

    def _get_model_responses(self, session: DebateSession, model_id: str) -> List[RoundResponse]:
        """دریافت همه پاسخ‌های یک مدل"""
        responses = []
        for round_responses in session.rounds:
            for resp in round_responses:
                if resp.model_id == model_id:
                    responses.append(resp)
        return responses

    def _build_all_responses_summary(self, session: DebateSession) -> str:
        """ساخت خلاصه همه پاسخ‌ها"""
        parts = []
        for round_num, round_responses in enumerate(session.rounds, 1):
            parts.append(f"\n=== دور {round_num} ===")
            for resp in round_responses:
                if resp.content:
                    content_preview = resp.content[:1000] + "..." if len(resp.content) > 1000 else resp.content
                    parts.append(f"\n{resp.role_icon} **{resp.model_name}** ({resp.role_name}):\n{content_preview}")
        return "\n".join(parts)

    def _build_scores_summary(self, session: DebateSession) -> str:
        """ساخت خلاصه امتیازات"""
        if not session.scores:
            return "بدون امتیاز"

        parts = []
        for score in session.scores:
            parts.append(f"- {score.scorer_model} → {score.target_model}: {score.total}/100")
        return "\n".join(parts)

    def get_session(self, session_id: str) -> Optional[DebateSession]:
        """دریافت یک جلسه"""
        return self._sessions.get(session_id)

    def list_sessions(self) -> List[DebateSession]:
        """لیست همه جلسات"""
        return list(self._sessions.values())


# Singleton instance
_debate_service: Optional[DebateService] = None


def get_debate_service() -> DebateService:
    """دریافت instance سرویس مناظره"""
    global _debate_service
    if _debate_service is None:
        _debate_service = DebateService()
    return _debate_service
