"""
🧠 Smart Orchestrator - هماهنگ‌کننده هوشمند
مدیریت هوشمند مدل‌ها، نظارت، و یکپارچگی پروژه‌ها با موتور خالق
"""

import asyncio
import json
import uuid
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

from .ai_base import Message  # اضافه شد

logger = logging.getLogger(__name__)


# =====================================
# 📊 انواع وظایف و امتیازدهی
# =====================================

class TaskCategory(str, Enum):
    """دسته‌بندی وظایف برای انتخاب هوشمند مدل"""
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    ARCHITECTURE = "architecture"
    ANALYSIS = "analysis"
    CREATIVE = "creative"
    RESEARCH = "research"
    DEBUGGING = "debugging"
    DOCUMENTATION = "documentation"
    DATA_PROCESSING = "data_processing"
    IMAGE_ANALYSIS = "image_analysis"
    FILE_ANALYSIS = "file_analysis"


class EvaluationCriteria(str, Enum):
    """معیارهای ارزیابی"""
    ACCURACY = "accuracy"           # صحت و درستی
    COMPLETENESS = "completeness"   # کامل بودن
    RELEVANCE = "relevance"         # مرتبط بودن
    CREATIVITY = "creativity"       # خلاقیت
    EFFICIENCY = "efficiency"       # کارایی
    CLARITY = "clarity"             # وضوح
    FEASIBILITY = "feasibility"     # عملی بودن


@dataclass
class ModelPerformance:
    """عملکرد یک مدل"""
    model_id: str
    total_tasks: int = 0
    successful_tasks: int = 0
    average_score: float = 0.0
    scores_by_category: Dict[str, float] = field(default_factory=dict)
    average_response_time: float = 0.0
    last_used: Optional[str] = None
    feedback_history: List[Dict] = field(default_factory=list)


@dataclass
class TaskEvaluation:
    """ارزیابی یک وظیفه"""
    task_id: str
    model_id: str
    evaluator_model_id: str
    scores: Dict[str, float]  # معیار -> امتیاز
    overall_score: float
    feedback: str
    suggestions: List[str]
    is_acceptable: bool
    evaluated_at: str


# =====================================
# 🎯 Smart Model Selector - انتخاب هوشمند مدل
# =====================================

class SmartModelSelector:
    """
    انتخاب هوشمند مدل بر اساس:
    - نوع وظیفه
    - تاریخچه عملکرد
    - در دسترس بودن
    - هزینه
    """

    # تخصص مدل‌ها برای هر نوع وظیفه (0-100)
    MODEL_SPECIALTIES = {
        "claude-sonnet-4-20250514": {
            TaskCategory.CODE_GENERATION: 95,
            TaskCategory.CODE_REVIEW: 95,
            TaskCategory.ARCHITECTURE: 95,
            TaskCategory.ANALYSIS: 95,
            TaskCategory.CREATIVE: 90,
            TaskCategory.RESEARCH: 90,
            TaskCategory.DEBUGGING: 90,
            TaskCategory.DOCUMENTATION: 85,
        },
        "gpt-4-turbo": {
            TaskCategory.CODE_GENERATION: 90,
            TaskCategory.CODE_REVIEW: 90,
            TaskCategory.ARCHITECTURE: 92,
            TaskCategory.ANALYSIS: 90,
            TaskCategory.CREATIVE: 88,
            TaskCategory.RESEARCH: 92,
            TaskCategory.DEBUGGING: 88,
            TaskCategory.DOCUMENTATION: 90,
        },
        "gpt-4o": {
            TaskCategory.CODE_GENERATION: 88,
            TaskCategory.CODE_REVIEW: 88,
            TaskCategory.ANALYSIS: 92,
            TaskCategory.IMAGE_ANALYSIS: 95,
            TaskCategory.CREATIVE: 85,
            TaskCategory.FILE_ANALYSIS: 90,
        },
        "deepseek-coder": {
            TaskCategory.CODE_GENERATION: 92,
            TaskCategory.CODE_REVIEW: 88,
            TaskCategory.DEBUGGING: 92,
            TaskCategory.ARCHITECTURE: 80,
        },
        "deepseek-chat": {
            TaskCategory.ANALYSIS: 85,
            TaskCategory.RESEARCH: 85,
            TaskCategory.CREATIVE: 80,
        },
        "gemini-2.5-pro": {
            TaskCategory.ANALYSIS: 90,
            TaskCategory.RESEARCH: 92,
            TaskCategory.CODE_GENERATION: 85,
            TaskCategory.DATA_PROCESSING: 92,
            TaskCategory.FILE_ANALYSIS: 90,
        },
        "gemini-2.0-flash": {
            TaskCategory.ANALYSIS: 85,
            TaskCategory.RESEARCH: 85,
            TaskCategory.DATA_PROCESSING: 88,
        },
    }

    def __init__(self, ai_manager):
        self.ai_manager = ai_manager
        self.performance_history: Dict[str, ModelPerformance] = {}
        self._load_performance_history()

    def _load_performance_history(self):
        """بارگذاری تاریخچه عملکرد"""
        # در آینده از دیتابیس خوانده می‌شود
        pass

    def _save_performance_history(self):
        """ذخیره تاریخچه عملکرد"""
        pass

    def select_best_model(
        self,
        task_category: TaskCategory,
        requirements: Dict = None,
        exclude_models: List[str] = None
    ) -> Tuple[str, float]:
        """
        انتخاب بهترین مدل برای یک وظیفه

        Returns:
            Tuple[model_id, confidence_score]
        """
        available_models = self.ai_manager.get_available_providers()
        exclude_models = exclude_models or []
        requirements = requirements or {}

        candidates = []

        for model_id, specialties in self.MODEL_SPECIALTIES.items():
            # بررسی در دسترس بودن
            provider = model_id.split('-')[0]
            if provider not in ['claude', 'gpt', 'deepseek', 'gemini']:
                provider_map = {
                    'claude': 'anthropic',
                    'gpt': 'openai',
                    'deepseek': 'deepseek',
                    'gemini': 'google'
                }
                for prefix, prov in provider_map.items():
                    if model_id.startswith(prefix):
                        provider = prov
                        break

            if provider not in available_models:
                continue

            if model_id in exclude_models:
                continue

            # امتیاز تخصص
            specialty_score = specialties.get(task_category, 50)

            # امتیاز تاریخچه
            history_score = 75  # پیش‌فرض
            if model_id in self.performance_history:
                perf = self.performance_history[model_id]
                category_score = perf.scores_by_category.get(task_category.value)
                if category_score:
                    history_score = category_score
                elif perf.average_score > 0:
                    history_score = perf.average_score

            # امتیاز نهایی (وزن‌دار)
            final_score = (specialty_score * 0.6) + (history_score * 0.4)

            candidates.append((model_id, final_score))

        if not candidates:
            # fallback
            return "gpt-4-turbo", 50.0

        # مرتب‌سازی و انتخاب بهترین
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0]

    def select_multiple_models(
        self,
        task_category: TaskCategory,
        count: int = 3,
        diversity: bool = True
    ) -> List[Tuple[str, float]]:
        """
        انتخاب چند مدل برای مقایسه یا همکاری
        """
        selected = []
        exclude = []
        used_providers = set()

        for _ in range(count):
            model_id, score = self.select_best_model(
                task_category,
                exclude_models=exclude
            )

            if diversity:
                # تنوع در provider
                provider = model_id.split('-')[0]
                if provider in used_providers and len(selected) < count:
                    exclude.append(model_id)
                    continue
                used_providers.add(provider)

            selected.append((model_id, score))
            exclude.append(model_id)

        return selected

    def update_performance(
        self,
        model_id: str,
        task_category: TaskCategory,
        score: float,
        response_time: float = 0
    ):
        """بروزرسانی عملکرد مدل"""
        if model_id not in self.performance_history:
            self.performance_history[model_id] = ModelPerformance(model_id=model_id)

        perf = self.performance_history[model_id]
        perf.total_tasks += 1
        if score >= 70:
            perf.successful_tasks += 1

        # بروزرسانی میانگین
        old_total = perf.average_score * (perf.total_tasks - 1)
        perf.average_score = (old_total + score) / perf.total_tasks

        # بروزرسانی امتیاز دسته
        cat_key = task_category.value
        if cat_key in perf.scores_by_category:
            old_score = perf.scores_by_category[cat_key]
            # میانگین متحرک
            perf.scores_by_category[cat_key] = (old_score * 0.7) + (score * 0.3)
        else:
            perf.scores_by_category[cat_key] = score

        perf.last_used = datetime.now().isoformat()
        self._save_performance_history()


# =====================================
# 👁️ Supervisor Model - مدل ناظر
# =====================================

class SupervisorModel:
    """
    مدل ناظر برای:
    - ارزیابی خروجی مدل‌ها
    - امتیازدهی
    - تشخیص انحراف
    - پیشنهاد اصلاح
    """

    EVALUATION_PROMPT = """تو یک ارزیاب حرفه‌ای هستی. وظیفه زیر را بررسی و امتیازدهی کن.

📋 وظیفه اصلی:
{task_description}

📝 خروجی مدل {model_id}:
{model_output}

🎯 معیارهای ارزیابی:
1. صحت (accuracy): آیا خروجی درست و بدون خطاست؟
2. کامل بودن (completeness): آیا همه موارد خواسته شده پوشش داده شده؟
3. مرتبط بودن (relevance): آیا خروجی مرتبط با وظیفه است؟
4. وضوح (clarity): آیا خروجی واضح و قابل فهم است؟
5. عملی بودن (feasibility): آیا خروجی قابل اجراست؟

📊 خروجی مورد نظر (JSON):
{{
    "scores": {{
        "accuracy": 0-100,
        "completeness": 0-100,
        "relevance": 0-100,
        "clarity": 0-100,
        "feasibility": 0-100
    }},
    "overall_score": 0-100,
    "is_acceptable": true/false,
    "feedback": "توضیح کلی",
    "issues": ["مشکل 1", "مشکل 2"],
    "suggestions": ["پیشنهاد 1", "پیشنهاد 2"],
    "needs_revision": true/false
}}

فقط JSON برگردان."""

    DEVIATION_CHECK_PROMPT = """بررسی کن آیا این خروجی از هدف اصلی پروژه منحرف شده یا نه.

🎯 هدف پروژه:
{project_goal}

📋 وظیفه فعلی:
{current_task}

📝 خروجی تولید شده:
{output}

📊 خروجی مورد نظر (JSON):
{{
    "is_deviated": true/false,
    "deviation_type": "none/minor/major/critical",
    "deviation_description": "توضیح انحراف",
    "correction_needed": true/false,
    "correction_suggestions": ["پیشنهاد 1", "پیشنهاد 2"],
    "alignment_score": 0-100
}}

فقط JSON برگردان."""

    def __init__(self, ai_manager, model_selector: SmartModelSelector):
        self.ai_manager = ai_manager
        self.model_selector = model_selector
        self.evaluation_history: List[TaskEvaluation] = []

    async def evaluate_output(
        self,
        task_description: str,
        model_id: str,
        model_output: str,
        task_category: TaskCategory = TaskCategory.CODE_GENERATION
    ) -> TaskEvaluation:
        """ارزیابی خروجی یک مدل"""

        # انتخاب مدل ناظر (متفاوت از مدل اصلی)
        evaluator_id, _ = self.model_selector.select_best_model(
            TaskCategory.CODE_REVIEW,
            exclude_models=[model_id]
        )

        prompt = self.EVALUATION_PROMPT.format(
            task_description=task_description,
            model_id=model_id,
            model_output=model_output[:4000]  # محدودیت طول
        )

        try:
            response = await self.ai_manager.generate(
                model_id=evaluator_id,
                messages=[Message(role="user", content=prompt)],
                max_tokens=1500
            )

            if response.content and not response.error:
                content = response.content
                # استخراج JSON
                result = self._extract_json(content)

                if result:
                    evaluation = TaskEvaluation(
                        task_id=f"eval_{uuid.uuid4().hex[:8]}",
                        model_id=model_id,
                        evaluator_model_id=evaluator_id,
                        scores=result.get("scores", {}),
                        overall_score=result.get("overall_score", 50),
                        feedback=result.get("feedback", ""),
                        suggestions=result.get("suggestions", []),
                        is_acceptable=result.get("is_acceptable", True),
                        evaluated_at=datetime.now().isoformat()
                    )

                    # بروزرسانی عملکرد
                    self.model_selector.update_performance(
                        model_id,
                        task_category,
                        evaluation.overall_score
                    )

                    self.evaluation_history.append(evaluation)
                    return evaluation

        except Exception as e:
            logger.error(f"Error evaluating output: {e}")

        # ارزیابی پیش‌فرض
        return TaskEvaluation(
            task_id=f"eval_{uuid.uuid4().hex[:8]}",
            model_id=model_id,
            evaluator_model_id=evaluator_id,
            scores={},
            overall_score=70,
            feedback="ارزیابی خودکار انجام نشد",
            suggestions=[],
            is_acceptable=True,
            evaluated_at=datetime.now().isoformat()
        )

    async def check_deviation(
        self,
        project_goal: str,
        current_task: str,
        output: str
    ) -> Dict:
        """بررسی انحراف از هدف"""

        evaluator_id, _ = self.model_selector.select_best_model(TaskCategory.ANALYSIS)

        prompt = self.DEVIATION_CHECK_PROMPT.format(
            project_goal=project_goal,
            current_task=current_task,
            output=output[:3000]
        )

        try:
            response = await self.ai_manager.generate(
                model_id=evaluator_id,
                messages=[Message(role="user", content=prompt)],
                max_tokens=1000
            )

            if response.content and not response.error:
                result = self._extract_json(response.content)
                if result:
                    return result

        except Exception as e:
            logger.error(f"Error checking deviation: {e}")

        return {
            "is_deviated": False,
            "deviation_type": "none",
            "alignment_score": 80
        }

    async def compare_outputs(
        self,
        task_description: str,
        outputs: Dict[str, str]  # model_id -> output
    ) -> Dict:
        """مقایسه خروجی چند مدل و انتخاب بهترین"""

        evaluations = {}
        for model_id, output in outputs.items():
            eval_result = await self.evaluate_output(
                task_description,
                model_id,
                output
            )
            evaluations[model_id] = eval_result

        # رتبه‌بندی
        ranked = sorted(
            evaluations.items(),
            key=lambda x: x[1].overall_score,
            reverse=True
        )

        return {
            "rankings": [
                {
                    "rank": i + 1,
                    "model_id": model_id,
                    "score": eval_obj.overall_score,
                    "feedback": eval_obj.feedback
                }
                for i, (model_id, eval_obj) in enumerate(ranked)
            ],
            "best_model": ranked[0][0] if ranked else None,
            "best_score": ranked[0][1].overall_score if ranked else 0,
            "evaluations": {
                model_id: {
                    "scores": eval_obj.scores,
                    "overall": eval_obj.overall_score,
                    "acceptable": eval_obj.is_acceptable
                }
                for model_id, eval_obj in evaluations.items()
            }
        }

    def _extract_json(self, text: str) -> Optional[Dict]:
        """استخراج JSON از متن با چند روش مختلف"""
        import re

        if not text:
            return None

        logger.info(f"_extract_json called, input length: {len(text)}")

        # روش 1: اول سعی کن مستقیم parse کنی
        try:
            return json.loads(text)
        except:
            pass

        # روش 2: حذف همه backticks و کلمه json - روش ساده و مطمئن
        cleaned = text.replace('```json', '').replace('```', '').replace('`', '')
        cleaned = re.sub(r'\bjson\b', '', cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.strip()

        logger.info(f"Cleaned text (first 200): {cleaned[:200] if len(cleaned) > 200 else cleaned}")

        try:
            return json.loads(cleaned)
        except:
            pass

        # روش 3: پیدا کردن JSON با balanced braces
        start = cleaned.find('{')
        if start == -1:
            logger.warning("No opening brace found")
            return None

        depth = 0
        end = -1
        in_string = False
        escape_next = False

        for i, char in enumerate(cleaned[start:], start):
            if escape_next:
                escape_next = False
                continue
            if char == '\\':
                escape_next = True
                continue
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break

        if end > start:
            json_str = cleaned[start:end]
            try:
                result = json.loads(json_str)
                logger.info(f"JSON parsed OK with balanced braces!")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")

        # روش 4: آخرین تلاش با rfind
        end2 = cleaned.rfind('}') + 1
        if end2 > start:
            try:
                result = json.loads(cleaned[start:end2])
                logger.info(f"JSON parsed OK with rfind!")
                return result
            except:
                pass

        logger.error(f"All JSON extraction methods failed")
        return None


# =====================================
# 📁 File Chunker - تقسیم‌کننده فایل
# =====================================

class FileChunker:
    """
    تقسیم فایل‌های بزرگ برای پردازش
    """

    # حداکثر سایز هر chunk (به بایت)
    MAX_CHUNK_SIZE = 1024 * 1024  # 1MB برای متن
    MAX_VIDEO_CHUNK_SIZE = 50 * 1024 * 1024  # 50MB برای ویدیو

    # فرمت‌های قابل تقسیم
    CHUNKABLE_TEXT = {'.txt', '.md', '.json', '.csv', '.log', '.xml', '.html'}
    CHUNKABLE_CODE = {'.py', '.js', '.ts', '.java', '.cpp', '.go', '.rs'}
    CHUNKABLE_MEDIA = {'.mp4', '.avi', '.mov', '.webm', '.mp3', '.wav'}

    @staticmethod
    def should_chunk(file_size: int, extension: str) -> bool:
        """آیا فایل نیاز به تقسیم دارد؟"""
        if extension in FileChunker.CHUNKABLE_MEDIA:
            return file_size > FileChunker.MAX_VIDEO_CHUNK_SIZE
        return file_size > FileChunker.MAX_CHUNK_SIZE

    @staticmethod
    def calculate_chunks(file_size: int, extension: str) -> int:
        """تعداد chunk‌های مورد نیاز"""
        if extension in FileChunker.CHUNKABLE_MEDIA:
            chunk_size = FileChunker.MAX_VIDEO_CHUNK_SIZE
        else:
            chunk_size = FileChunker.MAX_CHUNK_SIZE

        return (file_size + chunk_size - 1) // chunk_size

    @staticmethod
    async def chunk_text_file(content: bytes, extension: str) -> List[Dict]:
        """تقسیم فایل متنی"""
        text = content.decode('utf-8', errors='replace')
        chunks = []

        if extension in FileChunker.CHUNKABLE_CODE:
            # تقسیم بر اساس توابع/کلاس‌ها
            chunks = FileChunker._chunk_code(text, extension)
        else:
            # تقسیم بر اساس خطوط
            lines = text.split('\n')
            current_chunk = []
            current_size = 0

            for line in lines:
                line_size = len(line.encode('utf-8'))
                if current_size + line_size > FileChunker.MAX_CHUNK_SIZE:
                    if current_chunk:
                        chunks.append({
                            "content": '\n'.join(current_chunk),
                            "lines": len(current_chunk),
                            "size": current_size
                        })
                    current_chunk = [line]
                    current_size = line_size
                else:
                    current_chunk.append(line)
                    current_size += line_size

            if current_chunk:
                chunks.append({
                    "content": '\n'.join(current_chunk),
                    "lines": len(current_chunk),
                    "size": current_size
                })

        return chunks

    @staticmethod
    def _chunk_code(code: str, extension: str) -> List[Dict]:
        """تقسیم کد بر اساس ساختار"""
        chunks = []

        # الگوهای تقسیم برای زبان‌های مختلف
        if extension == '.py':
            # تقسیم بر اساس توابع و کلاس‌ها
            import re
            pattern = r'^(class |def |async def )'
            lines = code.split('\n')
            current_chunk = []

            for line in lines:
                if re.match(pattern, line) and current_chunk:
                    chunks.append({
                        "content": '\n'.join(current_chunk),
                        "type": "code_block"
                    })
                    current_chunk = []
                current_chunk.append(line)

            if current_chunk:
                chunks.append({
                    "content": '\n'.join(current_chunk),
                    "type": "code_block"
                })
        else:
            # تقسیم ساده بر اساس سایز
            chunk_size = FileChunker.MAX_CHUNK_SIZE
            for i in range(0, len(code), chunk_size):
                chunks.append({
                    "content": code[i:i + chunk_size],
                    "type": "raw"
                })

        return chunks

    @staticmethod
    async def chunk_binary_file(content: bytes) -> List[Dict]:
        """تقسیم فایل باینری"""
        chunks = []
        chunk_size = FileChunker.MAX_VIDEO_CHUNK_SIZE

        for i in range(0, len(content), chunk_size):
            chunk_data = content[i:i + chunk_size]
            chunks.append({
                "index": i // chunk_size,
                "size": len(chunk_data),
                "checksum": hashlib.md5(chunk_data).hexdigest(),
                "data": chunk_data  # در عمل باید ذخیره شود
            })

        return chunks


# =====================================
# 🔗 Project-Engine Integrator - یکپارچه‌کننده
# =====================================

class ProjectEngineIntegrator:
    """
    یکپارچگی عمیق بین Projects و Creator Engine
    """

    def __init__(
        self,
        project_service,
        creator_engine,
        model_selector: SmartModelSelector,
        supervisor: SupervisorModel
    ):
        self.project_service = project_service
        self.creator_engine = creator_engine
        self.model_selector = model_selector
        self.supervisor = supervisor
        self.active_workflows: Dict[str, Dict] = {}

    async def smart_project_setup(
        self,
        user_request: str
    ) -> Dict:
        """
        راه‌اندازی هوشمند پروژه از یک درخواست ساده
        """
        # تحلیل درخواست با AI
        try:
            analyzer_id, _ = self.model_selector.select_best_model(TaskCategory.ANALYSIS)
            logger.info(f"Selected analyzer model: {analyzer_id}")
        except Exception as e:
            logger.error(f"Error selecting model: {e}")
            return {"success": False, "error": f"خطا در انتخاب مدل: {str(e)}"}

        analysis_prompt = f"""درخواست کاربر را تحلیل کن و اطلاعات پروژه استخراج کن:

درخواست: {user_request}

خروجی JSON:
{{
    "project_name": "نام پیشنهادی",
    "project_type": "web_app/api_service/mobile_app/ml_project/data_pipeline/custom",
    "description": "توضیح کامل",
    "goal": "هدف اصلی",
    "complexity": "simple/medium/complex",
    "technologies": ["تکنولوژی 1", "تکنولوژی 2"],
    "features": ["قابلیت 1", "قابلیت 2"],
    "phases": [
        {{"name": "نام فاز", "description": "توضیح", "steps": ["گام 1", "گام 2"]}}
    ],
    "estimated_files": ["فایل 1", "فایل 2"],
    "risks": ["ریسک 1"],
    "success_criteria": ["معیار 1"]
}}"""

        try:
            # استفاده از ai_manager از model_selector به جای مسیر پیچیده creator_engine
            logger.info(f"Calling AI generate with model: {analyzer_id}")
            response = await self.model_selector.ai_manager.generate(
                model_id=analyzer_id,
                messages=[Message(role="user", content=analysis_prompt)],
                max_tokens=4000  # افزایش برای پاسخ‌های طولانی‌تر
            )
            logger.info(f"AI response received, length: {len(response.content) if response.content else 0}, error: {response.error}")

            if response.error:
                return {"success": False, "error": f"خطا از مدل AI: {response.error}"}

            if not response.content:
                return {"success": False, "error": "پاسخی از مدل AI دریافت نشد"}

            # لاگ کامل پاسخ برای debug
            logger.info(f"Full AI response: {response.content}")

            analysis = self._extract_json(response.content)
            logger.info(f"JSON extraction result: {bool(analysis)}, type: {type(analysis)}")

            if not analysis:
                # اگر JSON استخراج نشد، خود پاسخ را نشان بده
                return {"success": False, "error": f"خطا در استخراج JSON از پاسخ AI. پاسخ دریافتی: {response.content[:500]}"}

            # ایجاد پروژه
            project_result = self.project_service.create_project(
                name=analysis.get("project_name", "پروژه جدید"),
                description=analysis.get("description", ""),
                project_type=analysis.get("project_type", "custom"),
                goal=analysis.get("goal", ""),
                complexity=analysis.get("complexity", "medium"),
                custom_phases=analysis.get("phases")
            )

            if not project_result.get("success"):
                return {"success": False, "error": f"خطا در ایجاد پروژه: {project_result.get('error', 'نامشخص')}"}

            project_id = project_result["project_id"]

            # شروع workflow
            self.active_workflows[project_id] = {
                "analysis": analysis,
                "status": "initialized",
                "current_phase": 0,
                "started_at": datetime.now().isoformat()
            }

            return {
                "success": True,
                "project_id": project_id,
                "analysis": analysis,
                "message": f"پروژه '{analysis.get('project_name')}' با موفقیت ایجاد شد"
            }

        except Exception as e:
            logger.error(f"Error in smart project setup: {e}", exc_info=True)
            return {"success": False, "error": f"خطا در تحلیل درخواست: {str(e)}"}

    async def execute_with_monitoring(
        self,
        project_id: str,
        task_description: str,
        task_category: TaskCategory = TaskCategory.CODE_GENERATION
    ) -> Dict:
        """
        اجرای وظیفه با نظارت و بازخورد
        """
        project_data = self.project_service.get_project(project_id)
        if not project_data.get("success"):
            return {"success": False, "error": "پروژه یافت نشد"}

        project = project_data["project"]
        project_goal = project.get("goal", "")

        # انتخاب مدل
        model_id, confidence = self.model_selector.select_best_model(task_category)

        # اجرای وظیفه
        try:
            # استفاده از ai_manager از model_selector
            response = await self.model_selector.ai_manager.generate(
                model_id=model_id,
                messages=[Message(role="user", content=task_description)],
                max_tokens=4000
            )

            if response.content and not response.error:
                output = response.content

                # ارزیابی توسط ناظر
                evaluation = await self.supervisor.evaluate_output(
                    task_description,
                    model_id,
                    output,
                    task_category
                )

                # بررسی انحراف
                deviation = await self.supervisor.check_deviation(
                    project_goal,
                    task_description,
                    output
                )

                # تصمیم‌گیری
                needs_revision = (
                    not evaluation.is_acceptable or
                    deviation.get("is_deviated", False)
                )

                result = {
                    "success": True,
                    "output": output,
                    "model_used": model_id,
                    "confidence": confidence,
                    "evaluation": {
                        "score": evaluation.overall_score,
                        "feedback": evaluation.feedback,
                        "acceptable": evaluation.is_acceptable,
                        "suggestions": evaluation.suggestions
                    },
                    "deviation": deviation,
                    "needs_revision": needs_revision
                }

                # ذخیره مکالمه
                self.project_service.add_conversation(
                    project_id,
                    task_description,
                    [{
                        "model": model_id,
                        "content": output,
                        "score": evaluation.overall_score
                    }]
                )

                # اگر نیاز به بازنگری باشد
                if needs_revision and evaluation.overall_score < 60:
                    # تلاش مجدد با مدل دیگر
                    alt_model_id, _ = self.model_selector.select_best_model(
                        task_category,
                        exclude_models=[model_id]
                    )

                    revision_prompt = f"""وظیفه اصلی:
{task_description}

پاسخ قبلی مشکلات زیر را داشت:
{evaluation.feedback}

پیشنهادات:
{chr(10).join(evaluation.suggestions)}

لطفاً با رفع این مشکلات پاسخ بهتری ارائه بده."""

                    # استفاده از ai_manager از model_selector
                    revised_response = await self.model_selector.ai_manager.generate(
                        model_id=alt_model_id,
                        messages=[Message(role="user", content=revision_prompt)],
                        max_tokens=4000
                    )

                    if revised_response.content and not revised_response.error:
                        result["revised_output"] = revised_response.content
                        result["revised_by"] = alt_model_id

                return result

        except Exception as e:
            logger.error(f"Error in execute_with_monitoring: {e}")
            return {"success": False, "error": str(e)}

        return {"success": False, "error": "خطا در اجرا"}

    async def auto_build_project(
        self,
        project_id: str,
        github_repo: str = None
    ) -> Dict:
        """
        ساخت خودکار پروژه با نظارت مستمر
        """
        workflow = self.active_workflows.get(project_id)
        if not workflow:
            return {"success": False, "error": "Workflow یافت نشد. ابتدا پروژه را با smart_project_setup ایجاد کنید."}

        analysis = workflow["analysis"]
        results = []
        engine_project_id = None

        # ایجاد پروژه در Creator Engine (اگر موجود باشد)
        if self.creator_engine and self.creator_engine.project_creator:
            try:
                engine_result = await self.creator_engine.project_creator.create_project(
                    name=analysis.get("project_name", "project"),
                    description=analysis.get("description", ""),
                    project_type=analysis.get("project_type", "custom"),
                    technologies=analysis.get("technologies", []),
                    features=analysis.get("features", [])
                )
                if engine_result.success:
                    engine_project_id = engine_result.output.get("project_id")
            except Exception as e:
                logger.warning(f"Could not create project in Creator Engine: {e}")
        else:
            logger.warning("Creator Engine project_creator not initialized, skipping engine project creation")

        # تولید فایل‌های اصلی
        estimated_files = analysis.get("estimated_files", [])

        if not estimated_files:
            # اگر فایلی مشخص نشده، بر اساس فازها تولید کن
            workflow["status"] = "ready"
            return {
                "success": True,
                "project_id": project_id,
                "engine_project_id": engine_project_id,
                "message": "پروژه آماده است. فایل‌های مشخصی برای تولید خودکار وجود ندارد.",
                "phases": analysis.get("phases", [])
            }

        for file_path in estimated_files:
            try:
                file_result = await self.execute_with_monitoring(
                    project_id,
                    f"فایل {file_path} را برای پروژه '{analysis.get('project_name', 'project')}' بنویس. توضیحات پروژه: {analysis.get('description', '')}",
                    TaskCategory.CODE_GENERATION
                )

                if file_result.get("success"):
                    output = file_result.get("revised_output") or file_result.get("output", "")

                    # ذخیره فایل (اگر Creator Engine موجود باشد)
                    if self.creator_engine and self.creator_engine.file_manager:
                        try:
                            await self.creator_engine.file_manager.write_file(file_path, output)
                        except Exception as e:
                            logger.warning(f"Could not write file to Creator Engine: {e}")

                    results.append({
                        "file": file_path,
                        "status": "created",
                        "score": file_result.get("evaluation", {}).get("score", 0),
                        "content_preview": output[:200] if output else ""
                    })
                else:
                    results.append({
                        "file": file_path,
                        "status": "failed",
                        "error": file_result.get("error", "Unknown error")
                    })
            except Exception as e:
                logger.error(f"Error creating file {file_path}: {e}")
                results.append({
                    "file": file_path,
                    "status": "failed",
                    "error": str(e)
                })

        workflow["status"] = "building"
        workflow["results"] = results

        return {
            "success": True,
            "project_id": project_id,
            "engine_project_id": engine_project_id,
            "files_created": len([r for r in results if r["status"] == "created"]),
            "files_failed": len([r for r in results if r["status"] == "failed"]),
            "results": results
        }

    def _extract_json(self, text: str) -> Optional[Dict]:
        """استخراج JSON از متن با چند روش مختلف"""
        import re

        if not text:
            return None

        logger.info(f"_extract_json called, input length: {len(text)}")

        # روش 1: اول سعی کن مستقیم parse کنی
        try:
            return json.loads(text)
        except:
            pass

        # روش 2: حذف همه backticks و کلمه json - روش ساده و مطمئن
        cleaned = text.replace('```json', '').replace('```', '').replace('`', '')
        cleaned = re.sub(r'\bjson\b', '', cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.strip()

        logger.info(f"Cleaned text (first 200): {cleaned[:200] if len(cleaned) > 200 else cleaned}")

        try:
            return json.loads(cleaned)
        except:
            pass

        # روش 3: پیدا کردن JSON با balanced braces
        start = cleaned.find('{')
        if start == -1:
            logger.warning("No opening brace found")
            return None

        depth = 0
        end = -1
        in_string = False
        escape_next = False

        for i, char in enumerate(cleaned[start:], start):
            if escape_next:
                escape_next = False
                continue
            if char == '\\':
                escape_next = True
                continue
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break

        if end > start:
            json_str = cleaned[start:end]
            try:
                result = json.loads(json_str)
                logger.info(f"JSON parsed OK with balanced braces!")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")

        # روش 4: آخرین تلاش با rfind
        end2 = cleaned.rfind('}') + 1
        if end2 > start:
            try:
                result = json.loads(cleaned[start:end2])
                logger.info(f"JSON parsed OK with rfind!")
                return result
            except:
                pass

        logger.error(f"All JSON extraction methods failed")
        return None


# =====================================
# 🎮 Main Orchestrator - هماهنگ‌کننده اصلی
# =====================================

class SmartOrchestrator:
    """
    نقطه ورود اصلی برای همه قابلیت‌های هوشمند
    """

    _instance = None

    def __init__(self):
        self.model_selector: Optional[SmartModelSelector] = None
        self.supervisor: Optional[SupervisorModel] = None
        self.integrator: Optional[ProjectEngineIntegrator] = None
        self.file_chunker = FileChunker()
        self.initialized = False

    @classmethod
    def get_instance(cls) -> 'SmartOrchestrator':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def initialize(self, ai_manager, project_service, creator_engine):
        """مقداردهی اولیه با وابستگی‌ها"""
        self.model_selector = SmartModelSelector(ai_manager)
        self.supervisor = SupervisorModel(ai_manager, self.model_selector)
        self.integrator = ProjectEngineIntegrator(
            project_service,
            creator_engine,
            self.model_selector,
            self.supervisor
        )
        self.initialized = True
        logger.info("SmartOrchestrator initialized successfully")

    def is_initialized(self) -> bool:
        return self.initialized

    # دسترسی آسان به قابلیت‌ها
    async def smart_setup(self, request: str) -> Dict:
        """راه‌اندازی هوشمند پروژه"""
        if not self.initialized:
            return {"success": False, "error": "سیستم مقداردهی نشده"}
        return await self.integrator.smart_project_setup(request)

    async def execute_task(
        self,
        project_id: str,
        task: str,
        category: TaskCategory = TaskCategory.CODE_GENERATION
    ) -> Dict:
        """اجرای وظیفه با نظارت"""
        if not self.initialized:
            return {"success": False, "error": "سیستم مقداردهی نشده"}
        return await self.integrator.execute_with_monitoring(project_id, task, category)

    async def evaluate(
        self,
        task: str,
        model_id: str,
        output: str
    ) -> TaskEvaluation:
        """ارزیابی خروجی"""
        if not self.initialized:
            raise RuntimeError("سیستم مقداردهی نشده")
        return await self.supervisor.evaluate_output(task, model_id, output)

    def select_model(
        self,
        category: TaskCategory,
        exclude: List[str] = None
    ) -> Tuple[str, float]:
        """انتخاب مدل"""
        if not self.initialized:
            return "gpt-4-turbo", 50.0
        return self.model_selector.select_best_model(category, exclude_models=exclude)

    async def compare_models(
        self,
        task: str,
        outputs: Dict[str, str]
    ) -> Dict:
        """مقایسه خروجی مدل‌ها"""
        if not self.initialized:
            return {"success": False, "error": "سیستم مقداردهی نشده"}
        return await self.supervisor.compare_outputs(task, outputs)

    async def auto_build(
        self,
        project_id: str,
        github_repo: str = None
    ) -> Dict:
        """ساخت خودکار پروژه"""
        if not self.initialized:
            return {"success": False, "error": "سیستم مقداردهی نشده"}
        return await self.integrator.auto_build_project(project_id, github_repo)


# Singleton accessor
def get_smart_orchestrator() -> SmartOrchestrator:
    return SmartOrchestrator.get_instance()
