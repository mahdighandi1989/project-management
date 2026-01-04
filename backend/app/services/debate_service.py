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
    SYNTHESIZING = "synthesizing"  # فاز ترکیب خروجی‌ها
    GENERATING = "generating"      # تولید فایل نهایی
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


class SynthesizedOutput(BaseModel):
    """خروجی ترکیب شده نهایی"""
    content: str
    code_blocks: List[Dict[str, str]] = []  # [{language, code, filename}]
    key_points: List[str] = []
    recommendations: List[str] = []
    synthesizer_model: str = ""


class GeneratedFile(BaseModel):
    """فایل تولید شده"""
    filename: str
    content: str
    language: str = ""
    description: str = ""


class DebateSession(BaseModel):
    """یک جلسه مناظره"""
    id: str
    prompt: str
    mode: WorkMode
    detected_mode: Optional[WorkMode] = None  # حالت تشخیص داده شده
    status: DebateStatus = DebateStatus.PENDING
    models: List[str] = []
    role_assignments: Dict[str, RoleType] = {}
    rounds: List[List[RoundResponse]] = []
    scores: List[ScoreResult] = []
    judge_result: Optional[JudgeResult] = None
    synthesized_output: Optional[SynthesizedOutput] = None  # خروجی ترکیب شده
    generated_files: List[GeneratedFile] = []  # فایل‌های تولید شده
    summary: str = ""
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    metadata: Dict[str, Any] = {}
    # فایل‌های پیوست شده - محتوا ذخیره می‌شود
    attachments: List[Dict[str, Any]] = []

    class Config:
        use_enum_values = True


class DebateService:
    """سرویس اصلی مناظره"""

    # کلمات کلیدی برای تشخیص حالت
    DEBATE_KEYWORDS = ['مناظره', 'بحث', 'دفاع', 'مخالف', 'موافق', 'debate', 'argue', 'versus', 'vs']
    COLLAB_KEYWORDS = ['بررسی', 'تحلیل', 'کد', 'فایل', 'بهبود', 'اصلاح', 'review', 'analyze', 'code', 'file', 'improve', 'fix', 'create', 'write', 'generate', 'تولید', 'بنویس', 'بساز']
    RESEARCH_KEYWORDS = ['تحقیق', 'بررسی عمیق', 'research', 'investigate', 'study']
    QUICK_KEYWORDS = ['سریع', 'خلاصه', 'کوتاه', 'quick', 'short', 'brief', 'fast']

    def __init__(self, ai_manager: Optional[AIManager] = None):
        self.ai_manager = ai_manager or get_ai_manager()
        self._sessions: Dict[str, DebateSession] = {}

    def _detect_optimal_mode(self, prompt: str, attachments: Optional[List[Dict]] = None) -> WorkMode:
        """تشخیص هوشمند بهترین حالت کاری بر اساس پرامپت و فایل‌ها"""
        prompt_lower = prompt.lower()
        has_files = bool(attachments and len(attachments) > 0)
        has_code_files = False

        if attachments:
            code_extensions = {'.py', '.js', '.ts', '.mq4', '.mq5', '.mqh', '.java', '.cpp', '.c', '.go', '.rs', '.cs'}
            for att in attachments:
                filename = att.get('filename', att.get('name', ''))
                ext = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
                if ext in code_extensions:
                    has_code_files = True
                    break

        # اگر فایل کد پیوست شده، حالت همکاری بهتره
        if has_code_files:
            return WorkMode.COLLABORATION

        # بررسی کلمات کلیدی
        debate_score = sum(1 for kw in self.DEBATE_KEYWORDS if kw in prompt_lower)
        collab_score = sum(1 for kw in self.COLLAB_KEYWORDS if kw in prompt_lower)
        research_score = sum(1 for kw in self.RESEARCH_KEYWORDS if kw in prompt_lower)
        quick_score = sum(1 for kw in self.QUICK_KEYWORDS if kw in prompt_lower)

        # اگر فایل داریم، همکاری ترجیح داده میشه
        if has_files:
            collab_score += 2

        scores = {
            WorkMode.DEBATE: debate_score,
            WorkMode.COLLABORATION: collab_score,
            WorkMode.DEEP_RESEARCH: research_score,
            WorkMode.QUICK: quick_score,
        }

        max_score = max(scores.values())
        if max_score == 0:
            # اگر هیچ تشخیصی نیست، بر اساس طول پرامپت تصمیم بگیر
            if len(prompt) < 50:
                return WorkMode.QUICK
            elif has_files:
                return WorkMode.COLLABORATION
            else:
                return WorkMode.COLLABORATION  # پیش‌فرض همکاری به جای مناظره

        return max(scores, key=scores.get)

    async def create_session(
        self,
        prompt: str,
        mode: WorkMode = WorkMode.AUTO,
        models: Optional[List[str]] = None,
        attachments: Optional[List[Dict]] = None,
    ) -> DebateSession:
        """ایجاد یک جلسه مناظره جدید"""
        session_id = f"debate_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # تشخیص هوشمند حالت کاری
        detected_mode = None
        actual_mode = mode
        if mode == WorkMode.AUTO:
            detected_mode = self._detect_optimal_mode(prompt, attachments)
            actual_mode = detected_mode

        # انتخاب مدل‌ها بر اساس حالت واقعی
        mode_config = get_mode_config(actual_mode)
        if not models:
            max_models = len(mode_config.default_roles) if mode_config else 3
            selected = self.ai_manager.smart_select_models(prompt, max_models=max_models)
            models = [m.id for m in selected]

        if not models:
            raise ValueError("No models available")

        # تخصیص نقش‌ها بر اساس حالت واقعی
        role_assignments = {}
        default_roles = mode_config.default_roles if mode_config else [RoleType.RESPONDER]

        for i, model_id in enumerate(models):
            role = default_roles[i % len(default_roles)]
            role_assignments[model_id] = role

        session = DebateSession(
            id=session_id,
            prompt=prompt,
            mode=actual_mode,  # حالت واقعی که استفاده میشه
            detected_mode=detected_mode,  # چه حالتی تشخیص داده شد
            models=models,
            role_assignments=role_assignments,
            attachments=attachments or [],
            metadata={
                "attachments_count": len(attachments) if attachments else 0,
                "original_mode": mode.value if mode else "auto",
                "detected_mode": detected_mode.value if detected_mode else None,
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

        # *** اضافه کردن محتوای فایل‌های پیوست شده ***
        if session.attachments and round_number == 1:
            attachments_content = self._build_attachments_content(session.attachments)
            if attachments_content:
                messages.append(Message(
                    role="user",
                    content=f"📎 **فایل‌های پیوست شده:**\n\n{attachments_content}"
                ))

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

        # ساخت پیام اصلی با اشاره به فایل‌ها
        attachment_note = ""
        if session.attachments:
            attachment_note = f"\n\n⚠️ توجه: {len(session.attachments)} فایل پیوست شده است. لطفاً محتوای آن‌ها را در پاسخ خود لحاظ کنید."

        messages.append(Message(
            role="user",
            content=f"""
{round_instruction}

پرامپت اصلی:
{session.prompt}{attachment_note}

لطفاً پاسخ کامل و دقیق بدهید.
"""
        ))

        return messages

    def _build_attachments_content(self, attachments: List[Dict[str, Any]]) -> str:
        """ساخت محتوای فایل‌های پیوست برای ارسال به مدل"""
        parts = []

        for i, att in enumerate(attachments, 1):
            filename = att.get('filename', att.get('name', f'فایل {i}'))
            content = att.get('content', '')
            file_type = att.get('type', att.get('file_category', 'unknown'))

            if content:
                # محدود کردن سایز محتوا برای جلوگیری از overflow
                max_content_length = 50000  # حدود 50KB متن
                if len(content) > max_content_length:
                    content = content[:max_content_length] + f"\n\n... [ادامه فایل - {len(content) - max_content_length} کاراکتر دیگر] ..."

                parts.append(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 **فایل {i}: {filename}**
نوع: {file_type}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```
{content}
```
""")
            else:
                parts.append(f"📄 **فایل {i}: {filename}** (محتوا در دسترس نیست)")

        return "\n".join(parts)

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

    async def run_synthesis(self, session: DebateSession) -> SynthesizedOutput:
        """ترکیب خروجی‌های همه مدل‌ها به یک نتیجه یکپارچه"""
        session.status = DebateStatus.SYNTHESIZING
        session.updated_at = datetime.now()

        # انتخاب مدل ترکیب‌کننده (قوی‌ترین مدل)
        synth_model = session.models[0]
        all_responses = self._build_all_responses_summary(session)

        # استخراج بلوک‌های کد از پاسخ‌ها
        import re
        code_blocks = []
        for round_responses in session.rounds:
            for resp in round_responses:
                if resp.content:
                    # یافتن بلوک‌های کد
                    matches = re.findall(r'```(\w+)?\n(.*?)```', resp.content, re.DOTALL)
                    for match in matches:
                        lang = match[0] or 'text'
                        code = match[1].strip()
                        if len(code) > 50:  # فقط کدهای معنادار
                            code_blocks.append({
                                'language': lang,
                                'code': code,
                                'source_model': resp.model_id
                            })

        synthesis_prompt = f"""
شما باید تمام پاسخ‌های زیر را ترکیب کرده و یک خروجی نهایی یکپارچه تولید کنید.

**درخواست اصلی:**
{session.prompt[:1000]}

**پاسخ‌های دریافتی:**
{all_responses}

**وظیفه شما:**
1. نقاط قوت هر پاسخ را شناسایی کنید
2. بهترین ایده‌ها و کدها را ترکیب کنید
3. یک خروجی نهایی کامل و یکپارچه تولید کنید

اگر کدی درخواست شده، کد نهایی کامل و قابل اجرا بدهید.
اگر تحلیل درخواست شده، تحلیل جامع و ساختارمند ارائه دهید.

خروجی شما باید:
- کامل و آماده استفاده باشد
- بهترین ایده‌های همه مدل‌ها را شامل شود
- خطاها و کمبودها را برطرف کرده باشد
"""

        try:
            response = await self.ai_manager.generate(
                synth_model,
                [Message(role="user", content=synthesis_prompt)],
                max_tokens=8000,
                temperature=0.3
            )

            # استخراج نکات کلیدی و توصیه‌ها
            key_points = []
            recommendations = []

            # یافتن بلوک‌های کد در خروجی ترکیب شده
            final_code_blocks = []
            matches = re.findall(r'```(\w+)?\n(.*?)```', response.content, re.DOTALL)
            for match in matches:
                lang = match[0] or 'text'
                code = match[1].strip()
                if len(code) > 50:
                    final_code_blocks.append({
                        'language': lang,
                        'code': code,
                        'filename': f'output.{lang}' if lang != 'text' else 'output.txt'
                    })

            output = SynthesizedOutput(
                content=response.content,
                code_blocks=final_code_blocks,
                key_points=key_points,
                recommendations=recommendations,
                synthesizer_model=synth_model
            )

            session.synthesized_output = output
            session.updated_at = datetime.now()

            return output

        except Exception as e:
            output = SynthesizedOutput(
                content=f"خطا در ترکیب: {str(e)}",
                synthesizer_model=synth_model
            )
            session.synthesized_output = output
            return output

    async def run_file_generation(self, session: DebateSession) -> List[GeneratedFile]:
        """تولید فایل‌های نهایی از خروجی ترکیب شده"""
        session.status = DebateStatus.GENERATING
        session.updated_at = datetime.now()

        generated_files = []

        # اگر خروجی ترکیب شده داریم
        if session.synthesized_output:
            synth = session.synthesized_output

            # تولید فایل‌های کد
            for i, cb in enumerate(synth.code_blocks):
                lang = cb.get('language', 'text')
                code = cb.get('code', '')

                # تعیین نام فایل
                ext_map = {
                    'python': 'py', 'py': 'py',
                    'javascript': 'js', 'js': 'js',
                    'typescript': 'ts', 'ts': 'ts',
                    'mq5': 'mq5', 'mq4': 'mq4', 'mqh': 'mqh',
                    'java': 'java', 'cpp': 'cpp', 'c': 'c',
                    'go': 'go', 'rust': 'rs', 'csharp': 'cs',
                    'html': 'html', 'css': 'css', 'json': 'json',
                    'yaml': 'yaml', 'yml': 'yml', 'sql': 'sql',
                }
                ext = ext_map.get(lang.lower(), 'txt')
                filename = cb.get('filename', f'output_{i+1}.{ext}')

                generated_files.append(GeneratedFile(
                    filename=filename,
                    content=code,
                    language=lang,
                    description=f"کد {lang} تولید شده"
                ))

            # فایل خلاصه کامل
            generated_files.append(GeneratedFile(
                filename='synthesis_report.md',
                content=synth.content,
                language='markdown',
                description='گزارش کامل ترکیب شده'
            ))

        # اگر فایل اصلی پیوست شده بود، نسخه اصلاح شده بساز
        if session.attachments:
            for att in session.attachments:
                orig_name = att.get('filename', att.get('name', 'file'))
                # یافتن کد مربوط به این فایل در خروجی
                if session.synthesized_output:
                    for cb in session.synthesized_output.code_blocks:
                        # اگر زبان کد با فایل اصلی مطابقت داره
                        if orig_name.endswith(('.mq5', '.mq4', '.mqh')) and cb.get('language') in ['mq5', 'mq4', 'mqh', 'cpp', 'c']:
                            # نسخه بهبود یافته
                            generated_files.append(GeneratedFile(
                                filename=f'improved_{orig_name}',
                                content=cb.get('code', ''),
                                language=cb.get('language', ''),
                                description=f'نسخه بهبود یافته {orig_name}'
                            ))
                            break

        session.generated_files = generated_files
        session.updated_at = datetime.now()

        return generated_files

    async def run_full_debate(self, session: DebateSession) -> DebateSession:
        """اجرای کامل یک مناظره/همکاری"""
        mode_config = get_mode_config(session.mode)

        # اجرای دورها
        num_rounds = mode_config.rounds if mode_config else 1
        for round_num in range(1, num_rounds + 1):
            await self.run_round(session, round_num)

        # ترکیب خروجی‌ها (همیشه اجرا میشه)
        await self.run_synthesis(session)

        # تولید فایل‌های نهایی (اگر کد یا فایل درخواست شده)
        if session.attachments or self._needs_file_generation(session):
            await self.run_file_generation(session)

        # امتیازدهی (فقط برای مناظره)
        if mode_config and mode_config.scoring and session.mode == WorkMode.DEBATE:
            await self.run_scoring(session)

        # داوری (فقط برای مناظره)
        if mode_config and mode_config.judge and session.mode == WorkMode.DEBATE:
            await self.run_judging(session)

        # خلاصه
        if mode_config and mode_config.summary:
            await self.run_summary(session)

        return session

    def _needs_file_generation(self, session: DebateSession) -> bool:
        """آیا نیاز به تولید فایل هست؟"""
        prompt_lower = session.prompt.lower()
        code_keywords = ['کد', 'code', 'فایل', 'file', 'تولید', 'generate', 'بنویس', 'write', 'بساز', 'create']
        return any(kw in prompt_lower for kw in code_keywords)

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
