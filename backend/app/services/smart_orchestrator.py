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
        self.github_storage = None  # Will be set by orchestrator

    def set_github_storage(self, github_storage):
        """Set GitHub storage for saving generated files"""
        self.github_storage = github_storage

    async def load_workflow_from_github(self, project_id: str) -> Optional[Dict]:
        """
        بارگذاری نتایج workflow از GitHub
        """
        if not self.github_storage:
            return None

        try:
            result = await self.github_storage.get_file(f"projects/{project_id}/generated/workflow_results.json")
            if result.get("success") and result.get("content"):
                import base64
                content = base64.b64decode(result["content"]).decode('utf-8')
                workflow_data = json.loads(content)

                # بازسازی workflow در memory
                self.active_workflows[project_id] = {
                    "analysis": workflow_data.get("analysis", {}),
                    "status": workflow_data.get("status", "completed"),
                    "started_at": workflow_data.get("started_at"),
                    "completed_at": workflow_data.get("completed_at"),
                    "progress": 100,
                    "current_step": "done",
                    "total_files": workflow_data.get("total_files", 0),
                    "competition_mode": workflow_data.get("competition_mode", False),
                    "num_models": workflow_data.get("num_models", 1),
                    "results": workflow_data.get("files", [])
                }

                logger.info(f"Loaded workflow from GitHub for project {project_id}")
                return self.active_workflows[project_id]
        except Exception as e:
            logger.warning(f"Could not load workflow from GitHub: {e}")

        return None

    async def get_workflow_with_fallback(self, project_id: str) -> Optional[Dict]:
        """
        دریافت workflow - اول از memory، بعد از GitHub
        """
        # اول چک کن در memory هست
        if project_id in self.active_workflows:
            return self.active_workflows[project_id]

        # اگه نبود از GitHub بارگذاری کن
        return await self.load_workflow_from_github(project_id)

    async def generate_with_competition(
        self,
        task_description: str,
        task_category: TaskCategory = TaskCategory.CODE_GENERATION,
        num_models: int = 3
    ) -> Dict:
        """
        تولید با رقابت چند مدل

        - انتخاب چند مدل متنوع
        - اجرای موازی
        - ارزیابی و مقایسه
        - انتخاب بهترین
        """
        import asyncio

        # انتخاب مدل‌های متنوع
        models = self.model_selector.select_multiple_models(
            task_category,
            count=num_models,
            diversity=True
        )

        if not models:
            return {"success": False, "error": "مدلی در دسترس نیست"}

        logger.info(f"🏁 Starting competition with {len(models)} models: {[m[0] for m in models]}")

        # اجرای موازی روی همه مدل‌ها
        async def run_model(model_id: str, confidence: float) -> Dict:
            try:
                start_time = datetime.now()
                response = await self.model_selector.ai_manager.generate(
                    model_id=model_id,
                    messages=[Message(role="user", content=task_description)],
                    max_tokens=4000
                )
                end_time = datetime.now()
                duration_ms = (end_time - start_time).total_seconds() * 1000

                if response.content and not response.error:
                    return {
                        "model_id": model_id,
                        "success": True,
                        "output": response.content,
                        "confidence": confidence,
                        "duration_ms": duration_ms
                    }
                else:
                    return {
                        "model_id": model_id,
                        "success": False,
                        "error": response.error or "خروجی خالی",
                        "duration_ms": duration_ms
                    }
            except Exception as e:
                logger.error(f"Error running model {model_id}: {e}")
                return {
                    "model_id": model_id,
                    "success": False,
                    "error": str(e),
                    "duration_ms": 0
                }

        # اجرای همزمان
        tasks = [run_model(model_id, confidence) for model_id, confidence in models]
        results = await asyncio.gather(*tasks)

        # فیلتر نتایج موفق
        successful_results = [r for r in results if r["success"]]

        if not successful_results:
            return {
                "success": False,
                "error": "هیچ مدلی موفق نشد",
                "all_results": results
            }

        if len(successful_results) == 1:
            # فقط یک مدل موفق شد
            winner = successful_results[0]
            return {
                "success": True,
                "winner": winner["model_id"],
                "output": winner["output"],
                "score": 75,  # امتیاز پیش‌فرض
                "competition": {
                    "participants": len(models),
                    "successful": 1,
                    "results": results
                }
            }

        # مقایسه خروجی‌ها توسط مدل ناظر
        outputs = {r["model_id"]: r["output"] for r in successful_results}
        comparison = await self.supervisor.compare_outputs(task_description, outputs)

        best_model = comparison.get("best_model")
        best_score = comparison.get("best_score", 0)

        # پیدا کردن خروجی برنده
        winner_output = outputs.get(best_model, successful_results[0]["output"])

        # بروزرسانی عملکرد مدل‌ها
        for model_id, eval_data in comparison.get("evaluations", {}).items():
            self.model_selector.update_performance(
                model_id,
                task_category,
                eval_data.get("overall", 50)
            )

        logger.info(f"🏆 Competition winner: {best_model} with score {best_score}")

        return {
            "success": True,
            "winner": best_model,
            "output": winner_output,
            "score": best_score,
            "competition": {
                "participants": len(models),
                "successful": len(successful_results),
                "rankings": comparison.get("rankings", []),
                "all_results": [
                    {
                        "model_id": r["model_id"],
                        "success": r["success"],
                        "duration_ms": r.get("duration_ms", 0),
                        "score": comparison.get("evaluations", {}).get(r["model_id"], {}).get("overall", 0) if r["success"] else 0,
                        "error": r.get("error")
                    }
                    for r in results
                ]
            }
        }

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

    async def analyze_project_state(self, project_id: str) -> Dict:
        """
        تحلیل وضعیت فعلی پروژه - خودآگاهی کامل

        Returns:
            - existing_files: فایل‌های موجود
            - missing_files: فایل‌های مورد نیاز که وجود ندارند
            - current_phase: فاز فعلی
            - overall_progress: پیشرفت کلی
            - recommendations: پیشنهادات
        """
        state = {
            "project_id": project_id,
            "existing_files": [],
            "missing_files": [],
            "current_phase": None,
            "current_phase_index": 0,
            "total_phases": 0,
            "overall_progress": 0,
            "phase_progress": {},
            "recommendations": [],
            "ready_for_next_phase": False,
            "needs_building": False
        }

        try:
            # دریافت اطلاعات پروژه
            project_data = self.project_service.get_project(project_id)
            if not project_data.get("success"):
                return {"success": False, "error": "پروژه یافت نشد"}

            project = project_data["project"]
            phases = project.get("phases", [])
            state["total_phases"] = len(phases)
            state["current_phase_index"] = project.get("current_phase_index", 0)

            if phases and state["current_phase_index"] < len(phases):
                state["current_phase"] = phases[state["current_phase_index"]]

            # بررسی فایل‌های موجود در GitHub
            if self.github_storage:
                try:
                    project_files = await self.github_storage.get_project_files(project_id)
                    for folder_type, files in project_files.get("files", {}).items():
                        for file_info in files:
                            if file_info.get("name") and file_info["name"] != ".gitkeep":
                                state["existing_files"].append({
                                    "path": f"{folder_type}/{file_info['name']}",
                                    "name": file_info["name"],
                                    "folder": folder_type,
                                    "size": file_info.get("size", 0)
                                })
                except Exception as e:
                    logger.warning(f"Could not get project files from GitHub: {e}")

            # بررسی workflow برای فایل‌های مورد نیاز
            workflow = self.active_workflows.get(project_id)
            if workflow:
                analysis = workflow.get("analysis", {})
                estimated_files = analysis.get("estimated_files", [])

                existing_paths = [f["name"] for f in state["existing_files"]]

                for file_path in estimated_files:
                    file_name = file_path.rsplit("/", 1)[-1] if "/" in file_path else file_path
                    if file_name not in existing_paths and file_path not in existing_paths:
                        state["missing_files"].append(file_path)

                # محاسبه پیشرفت
                if estimated_files:
                    built_count = len(estimated_files) - len(state["missing_files"])
                    state["overall_progress"] = int((built_count / len(estimated_files)) * 100)

            # پیشنهادات
            if not state["existing_files"]:
                state["recommendations"].append("هنوز هیچ فایلی ساخته نشده. از 'ساخت خودکار' استفاده کنید.")
                state["needs_building"] = True
            elif state["missing_files"]:
                state["recommendations"].append(f"{len(state['missing_files'])} فایل هنوز ساخته نشده.")
                state["needs_building"] = True
            else:
                state["recommendations"].append("همه فایل‌ها ساخته شده‌اند!")
                state["ready_for_next_phase"] = True

            # بررسی آمادگی برای فاز بعدی
            if state["current_phase"]:
                phase_files_built = sum(1 for f in state["existing_files"]
                                       if any(tech in f["name"].lower() for tech in ["backend", "api", "server"])
                                       if state["current_phase"].get("name", "").lower() in ["backend", "توسعه backend"])

            state["success"] = True
            return state

        except Exception as e:
            logger.error(f"Error analyzing project state: {e}")
            return {"success": False, "error": str(e)}

    async def _update_project_progress_auto(self, project_id: str, progress: int):
        """
        بروزرسانی خودکار پیشرفت پروژه بر اساس فایل‌های ساخته شده
        """
        try:
            project_data = self.project_service.get_project(project_id)
            if not project_data.get("success"):
                return

            project = project_data["project"]
            phases = project.get("phases", [])
            current_phase_index = project.get("current_phase_index", 0)

            if phases and current_phase_index < len(phases):
                # بروزرسانی پیشرفت فاز فعلی
                self.project_service.update_phase_progress(project_id, progress)
                logger.info(f"📊 Auto-updated project {project_id} progress to {progress}%")

                # اگر پیشرفت 100% شد، به فاز بعدی برو
                if progress >= 100 and current_phase_index < len(phases) - 1:
                    self.project_service.start_next_phase(project_id)
                    logger.info(f"🚀 Auto-advanced to next phase for project {project_id}")

        except Exception as e:
            logger.warning(f"Could not auto-update project progress: {e}")

    async def auto_build_project(
        self,
        project_id: str,
        github_repo: str = None,
        use_competition: bool = True,
        num_models: int = 3,
        force_rebuild: bool = False
    ) -> Dict:
        """
        ساخت خودکار پروژه با رقابت چند مدل - نسخه هوشمند

        Args:
            project_id: شناسه پروژه
            github_repo: مخزن GitHub (اختیاری)
            use_competition: استفاده از حالت رقابتی (پیش‌فرض: True)
            num_models: تعداد مدل‌ها در رقابت (پیش‌فرض: 3)
            force_rebuild: بازسازی اجباری همه فایل‌ها (پیش‌فرض: False)
        """
        workflow = self.active_workflows.get(project_id)
        if not workflow:
            return {"success": False, "error": "Workflow یافت نشد. ابتدا پروژه را با smart_project_setup ایجاد کنید."}

        # 🧠 خودآگاهی: بررسی وضعیت فعلی پروژه
        workflow["status"] = "analyzing"
        workflow["current_step"] = "🔍 تحلیل وضعیت پروژه..."

        project_state = await self.analyze_project_state(project_id)
        existing_file_names = [f["name"] for f in project_state.get("existing_files", [])]

        logger.info(f"🧠 Project state: {len(existing_file_names)} existing files, {len(project_state.get('missing_files', []))} missing")

        analysis = workflow["analysis"]
        results = []
        engine_project_id = None

        # Update workflow status
        workflow["status"] = "starting"
        workflow["started_at"] = datetime.now().isoformat()
        workflow["current_step"] = "initializing"
        workflow["progress"] = 0
        workflow["results"] = []
        workflow["competition_mode"] = use_competition
        workflow["num_models"] = num_models
        workflow["skipped_files"] = []  # فایل‌هایی که skip شدند

        # ایجاد پروژه در Creator Engine (اگر موجود باشد)
        workflow["current_step"] = "creating_engine_project"
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

        # 🧠 هوشمند: فقط فایل‌هایی که وجود ندارند را بساز
        if not force_rebuild:
            files_to_build = []
            for file_path in estimated_files:
                file_name = file_path.rsplit("/", 1)[-1] if "/" in file_path else file_path
                if file_name not in existing_file_names:
                    files_to_build.append(file_path)
                else:
                    workflow["skipped_files"].append({
                        "path": file_path,
                        "reason": "already_exists"
                    })
                    logger.info(f"⏭️ Skipping {file_path} - already exists")
        else:
            files_to_build = estimated_files
            logger.info(f"🔄 Force rebuild mode - rebuilding all {len(files_to_build)} files")

        # اگر همه فایل‌ها قبلاً ساخته شده‌اند
        if not files_to_build:
            workflow["status"] = "completed"
            workflow["progress"] = 100
            workflow["current_step"] = "✅ همه فایل‌ها قبلاً ساخته شده‌اند"
            workflow["completed_at"] = datetime.now().isoformat()

            # بروزرسانی پیشرفت پروژه
            await self._update_project_progress_auto(project_id, 100)

            return {
                "success": True,
                "project_id": project_id,
                "message": "همه فایل‌ها قبلاً ساخته شده‌اند! نیازی به ساخت مجدد نیست.",
                "existing_files": len(existing_file_names),
                "skipped_files": workflow["skipped_files"]
            }

        # جایگزینی estimated_files با files_to_build
        estimated_files = files_to_build

        if not estimated_files:
            # اگر فایلی مشخص نشده، بر اساس فازها تولید کن
            workflow["status"] = "completed"
            workflow["progress"] = 100
            workflow["current_step"] = "done"
            return {
                "success": True,
                "project_id": project_id,
                "engine_project_id": engine_project_id,
                "message": "پروژه آماده است. فایل‌های مشخصی برای تولید خودکار وجود ندارد.",
                "phases": analysis.get("phases", [])
            }

        total_files = len(estimated_files)
        workflow["total_files"] = total_files
        workflow["status"] = "building"

        for idx, file_path in enumerate(estimated_files):
            # Update progress
            workflow["current_file"] = file_path
            workflow["current_file_index"] = idx + 1
            workflow["current_step"] = f"🏁 رقابت مدل‌ها برای {file_path}" if use_competition else f"generating_{file_path}"
            workflow["progress"] = int((idx / total_files) * 100)

            try:
                task_description = f"""فایل {file_path} را برای پروژه '{analysis.get('project_name', 'project')}' بنویس.

توضیحات پروژه: {analysis.get('description', '')}

هدف: {analysis.get('goal', '')}

تکنولوژی‌ها: {', '.join(analysis.get('technologies', []))}

فقط کد را بنویس، بدون توضیح اضافی."""

                if use_competition:
                    # حالت رقابتی - چند مدل با هم رقابت می‌کنند
                    file_result = await self.generate_with_competition(
                        task_description,
                        TaskCategory.CODE_GENERATION,
                        num_models=num_models
                    )
                else:
                    # حالت عادی
                    file_result = await self.execute_with_monitoring(
                        project_id,
                        task_description,
                        TaskCategory.CODE_GENERATION
                    )

                if file_result.get("success"):
                    output = file_result.get("revised_output") or file_result.get("output", "")

                    # ذخیره فایل در GitHub
                    github_saved = False
                    if self.github_storage:
                        try:
                            content_bytes = output.encode('utf-8')
                            gh_result = await self.github_storage.save_project_file(
                                project_id,
                                content_bytes,
                                file_path,
                                "generated"
                            )
                            github_saved = gh_result.get("success", False)
                            logger.info(f"GitHub save result for {file_path}: {github_saved}")
                        except Exception as e:
                            logger.warning(f"Could not save file to GitHub: {e}")

                    # ذخیره فایل در Creator Engine (اگر موجود باشد)
                    if self.creator_engine and self.creator_engine.file_manager:
                        try:
                            await self.creator_engine.file_manager.write_file(file_path, output)
                        except Exception as e:
                            logger.warning(f"Could not write file to Creator Engine: {e}")

                    # استخراج اطلاعات رقابت
                    competition_data = file_result.get("competition", {})
                    winner_model = file_result.get("winner", "unknown")
                    score = file_result.get("score", file_result.get("evaluation", {}).get("score", 0))

                    file_info = {
                        "file": file_path,
                        "status": "created",
                        "score": score,
                        "content_preview": output[:200] if output else "",
                        "content": output,
                        "github_saved": github_saved,
                        # اطلاعات رقابت
                        "winner_model": winner_model,
                        "competition": {
                            "participants": competition_data.get("participants", 1),
                            "successful": competition_data.get("successful", 1),
                            "rankings": competition_data.get("rankings", []),
                            "all_results": competition_data.get("all_results", [])
                        } if use_competition else None
                    }
                    results.append(file_info)
                    workflow["results"].append(file_info)
                else:
                    file_info = {
                        "file": file_path,
                        "status": "failed",
                        "error": file_result.get("error", "Unknown error")
                    }
                    results.append(file_info)
                    workflow["results"].append(file_info)
            except Exception as e:
                logger.error(f"Error creating file {file_path}: {e}")
                file_info = {
                    "file": file_path,
                    "status": "failed",
                    "error": str(e)
                }
                results.append(file_info)
                workflow["results"].append(file_info)

        workflow["status"] = "completed"
        workflow["progress"] = 100
        workflow["current_step"] = "done"
        workflow["completed_at"] = datetime.now().isoformat()

        # 🧠 بروزرسانی خودکار پیشرفت پروژه
        success_count = len([r for r in results if r.get("status") == "created"])
        total_count = len(estimated_files) + len(workflow.get("skipped_files", []))
        if total_count > 0:
            auto_progress = int((success_count + len(workflow.get("skipped_files", []))) / total_count * 100)
            await self._update_project_progress_auto(project_id, auto_progress)

        # ذخیره نتایج workflow در GitHub برای ماندگاری
        if self.github_storage:
            try:
                # ذخیره خلاصه workflow (بدون محتوای کامل فایل‌ها برای کاهش حجم)
                workflow_summary = {
                    "project_id": project_id,
                    "status": workflow["status"],
                    "started_at": workflow.get("started_at"),
                    "completed_at": workflow["completed_at"],
                    "competition_mode": use_competition,
                    "num_models": num_models,
                    "total_files": workflow.get("total_files", 0),
                    "analysis": workflow.get("analysis", {}),
                    "files": [
                        {
                            "file": r.get("file"),
                            "status": r.get("status"),
                            "score": r.get("score", 0),
                            "winner_model": r.get("winner_model"),
                            "github_saved": r.get("github_saved", False),
                            "competition": r.get("competition"),
                            "error": r.get("error")
                        }
                        for r in results
                    ]
                }
                workflow_json = json.dumps(workflow_summary, ensure_ascii=False, indent=2)
                await self.github_storage.save_project_file(
                    project_id,
                    workflow_json.encode('utf-8'),
                    "workflow_results.json",
                    "generated"
                )
                logger.info(f"Workflow results saved to GitHub for project {project_id}")
            except Exception as e:
                logger.warning(f"Could not save workflow results to GitHub: {e}")

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
